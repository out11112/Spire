"""Standalone FastAPI entry point for Spire."""
from __future__ import annotations

from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
import uvicorn

from linkchat_spire import service as spire_service
from spire_server.auth import SpireApiError
from spire_server.config import get_settings
from spire_server.db import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    spire_service.migrate(engine)
    yield


app = FastAPI(title='Spire Server', version='0.1.0', lifespan=lifespan)
app.include_router(spire_service.router)


@app.middleware('http')
async def attach_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers.setdefault('X-Request-Id', request.state.request_id)
    return response


@app.exception_handler(SpireApiError)
async def spire_error_handler(request: Request, exc: SpireApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'error': {
                'code': exc.code,
                'message': str(exc.detail),
                'retryable': exc.retryable,
            },
            'requestId': getattr(request.state, 'request_id', ''),
        },
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    codes = {400: 'invalid_request', 401: 'invalid_token', 403: 'forbidden', 404: 'not_found', 409: 'conflict', 422: 'invalid_request'}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'error': {
                'code': getattr(exc, 'code', codes.get(exc.status_code, 'request_failed')),
                'message': str(exc.detail),
                'retryable': getattr(exc, 'retryable', False),
            },
            'requestId': getattr(request.state, 'request_id', ''),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            'error': {
                'code': 'invalid_request',
                'message': '请求参数无效',
                'retryable': False,
            },
            'requestId': getattr(request.state, 'request_id', ''),
        },
    )


@app.get('/health')
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        db_status = 'connected'
    except Exception:
        db_status = 'disconnected'
    return {
        'status': 'ok',
        'database': db_status,
        'protocol': spire_service.PROTOCOL_VERSION,
        'rules': spire_service.RULES_VERSION,
        'content': spire_service.CONTENT_VERSION,
    }


def run():
    settings = get_settings()
    uvicorn.run('spire_server.main:app', host=settings.spire_host, port=settings.spire_port, workers=1)


if __name__ == '__main__':
    run()
