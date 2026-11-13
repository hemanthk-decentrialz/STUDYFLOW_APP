from hashlib import sha256
from secrets import token_urlsafe

from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

password_hasher = PasswordHash.recommended()
# Verify a dummy hash for unknown emails to avoid a fast failure path.
_dummy_hash = password_hasher.hash(token_urlsafe(32))


async def hash_password(password: str) -> str:
    return await run_in_threadpool(password_hasher.hash, password)


async def verify_password(password: str, stored_hash: str | None) -> bool:
    valid = await run_in_threadpool(password_hasher.verify, password, stored_hash or _dummy_hash)
    return stored_hash is not None and valid


def create_session_token() -> str:
    return token_urlsafe(32)


def digest_session_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
