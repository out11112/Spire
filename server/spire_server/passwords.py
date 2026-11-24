"""Password hashing for Spire room passwords (stdlib scrypt)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

_PREFIX = 'scrypt$'


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=32)
    return _PREFIX + base64.b64encode(salt).decode('ascii') + '$' + base64.b64encode(derived).decode('ascii')


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith(_PREFIX):
        return False
    parts = stored[len(_PREFIX):].split('$')
    if len(parts) != 2:
        return False
    try:
        salt = base64.b64decode(parts[0])
        expected = base64.b64decode(parts[1])
    except Exception:
        return False
    derived = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=len(expected))
    return hmac.compare_digest(derived, expected)
