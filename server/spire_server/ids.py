"""UUIDv7 identifiers for standalone Spire."""
from __future__ import annotations

import os
import time
from typing import Annotated
import uuid

from pydantic import AfterValidator


def _validate_uuid(value: str) -> str:
    return str(uuid.UUID(str(value)))


Id = Annotated[str, AfterValidator(_validate_uuid)]


def new_id() -> str:
    """Generate a monotonic-friendly UUIDv7 string."""
    ms = int(time.time() * 1000)
    rand = os.urandom(10)
    value = (ms & 0xFFFFFFFFFFFF) << 80
    value |= 0x7 << 76
    value |= (int.from_bytes(rand[:2], 'big') & 0x0FFF) << 64
    value |= 0x2 << 62
    value |= int.from_bytes(rand[2:], 'big') & 0x3FFFFFFFFFFFFFFF
    return str(uuid.UUID(int=value))
