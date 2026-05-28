import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
import psycopg

DSN = os.environ.get("DAM_DSN", "postgresql://dam:dam@localhost:15432/dam")

router = APIRouter(prefix="/auth", tags=["auth"])

ph = PasswordHasher()

ROLE_LEVEL = {"viewer": 1, "editor": 2, "admin": 3}


@dataclass
class User:
    id: int
    username: str
    role: str


def hash_password(plain: str) -> str:
    return ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, plain)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def issue_token(user_id: int, name: Optional[str] = None, expires_at: Optional[datetime] = None) -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO api_tokens(user_id, token_hash, name, expires_at) VALUES(%s, %s, %s, %s)",
                (user_id, token_hash, name, expires_at)
            )
        conn.commit()

    return raw_token, token_hash


def require_user(min_role: str = "viewer"):
    async def _require_user(authorization: Optional[str] = Header(None)) -> User:
        if not authorization:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header format")

        raw_token = parts[1]
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.username, u.role
                    FROM api_tokens t
                    JOIN users u ON u.id = t.user_id
                    WHERE t.token_hash = %s
                      AND t.revoked_at IS NULL
                      AND (t.expires_at IS NULL OR t.expires_at > now())
                    """,
                    (token_hash,)
                )
                row = cur.fetchone()

                if not row:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

                user_id, username, role = row

                if ROLE_LEVEL.get(role, 0) < ROLE_LEVEL.get(min_role, 0):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

                cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user_id,))

            conn.commit()

        return User(id=user_id, username=username, role=role)

    return _require_user


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash, role FROM users WHERE username = %s", (req.username,))
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        user_id, password_hash, role = row

        if not verify_password(req.password, password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    raw_token, _ = issue_token(user_id)
    return LoginResponse(token=raw_token, username=req.username, role=role)
