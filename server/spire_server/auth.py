"""LinkChat session delegation adapter for the standalone Spire server."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import threading
import time

from fastapi import HTTPException, Request
import httpx

from spire_server.config import get_settings

COOKIE_NAME = 'linkchat_session'


class SpireApiError(HTTPException):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        super().__init__(status, message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class SpireUser:
    id: str
    username: str
    nickname: str
    role: str = 'MEMBER'


@dataclass(frozen=True)
class SpirePrincipal:
    user: SpireUser
    token_id: str | None = None
    can_control: bool = True
    can_read_game: bool = True

    @property
    def is_token(self) -> bool:
        return self.token_id is not None


_CACHE_LOCK = threading.Lock()
_SESSION_CACHE: dict[str, tuple[SpireUser, float]] = {}


def clear_auth_cache() -> None:
    with _CACHE_LOCK:
        _SESSION_CACHE.clear()


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    token = parts[1].strip()
    return token or None


def _token_cache_key(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _fetch_linkchat_user(token: str) -> SpireUser:
    settings = get_settings()
    url = settings.linkchat_auth_url.rstrip('/') + '/api/users/me'
    try:
        response = httpx.get(
            url,
            headers={'Authorization': f'Bearer {token}'},
            timeout=settings.auth_timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise SpireApiError(503, 'auth_unavailable', 'LinkChat 认证服务暂不可用，请稍后重试。', retryable=True) from error

    if response.status_code in (401, 403):
        raise SpireApiError(401, 'invalid_token', '登录已过期或账号不可用，请重新登录。')
    if response.status_code >= 500:
        raise SpireApiError(503, 'auth_unavailable', 'LinkChat 认证服务异常，请稍后重试。', retryable=True)
    if response.status_code != 200:
        raise SpireApiError(401, 'invalid_token', '无法验证 LinkChat 会话。')

    try:
        data = response.json()
        uid = str(data['id'])
        username = str(data.get('username') or uid)
        nickname = str(data.get('nickname') or username)
        role = str(data.get('role') or 'MEMBER')
    except Exception as error:
        raise SpireApiError(502, 'auth_invalid_response', 'LinkChat 认证响应无效。', retryable=True) from error

    if role == 'BANNED':
        raise SpireApiError(403, 'account_banned', '账号已封禁。')
    return SpireUser(id=uid, username=username, nickname=nickname, role=role)


def authenticate_session(token: str | None) -> SpirePrincipal:
    if not token or not token.strip():
        raise SpireApiError(401, 'unauthenticated', '请先登录 LinkChat 账号。')
    token = token.strip()
    settings = get_settings()
    ttl = settings.auth_cache_ttl_seconds
    key = _token_cache_key(token)
    now = time.monotonic()
    if ttl > 0:
        with _CACHE_LOCK:
            cached = _SESSION_CACHE.get(key)
            if cached and cached[1] > now:
                return SpirePrincipal(user=cached[0])
    user = _fetch_linkchat_user(token)
    if ttl > 0:
        with _CACHE_LOCK:
            if len(_SESSION_CACHE) >= 4096:
                expired = [k for k, (_, exp) in _SESSION_CACHE.items() if exp <= now]
                for k in expired:
                    _SESSION_CACHE.pop(k, None)
                if len(_SESSION_CACHE) >= 4096:
                    _SESSION_CACHE.clear()
            _SESSION_CACHE[key] = (user, now + ttl)
    return SpirePrincipal(user=user)


def spire_identity(request: Request) -> SpirePrincipal:
    token = extract_bearer_token(request.headers.get('authorization')) or request.cookies.get(COOKIE_NAME)
    return authenticate_session(token)


def authorize_spire(principal: SpirePrincipal, control: bool = False) -> None:
    return None
