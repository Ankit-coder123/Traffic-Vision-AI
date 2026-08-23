from datetime import datetime, timedelta
from typing import Optional
import hashlib
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

# --- Config ---
# Reads from env (set via .env locally, or the `backend` service's
# environment in docker-compose.yml). Falls back to an obviously-fake dev
# value so local `python -m uvicorn` still works without extra setup --
# but that fallback must never be used in a real deployment.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Use this as a dependency on routes that only admins should access."""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def require_operator_or_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Use this for actions meant for traffic staff (operators/admins) but
    not the general public -- e.g. reporting a real-world incident."""
    if current_user.role not in (models.UserRole.admin, models.UserRole.operator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin privileges required",
        )
    return current_user


# --- Google Sign-In ---
# GOOGLE_CLIENT_ID is public (it's embedded in the frontend bundle too --
# that's normal for OAuth "client" IDs, unlike a client *secret*). We use
# the "ID token" flow: Google Identity Services on the frontend returns a
# signed JWT directly to the browser, which POSTs it here for verification.
# No client secret or server-side redirect exchange needed for this flow.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


def verify_google_token(credential: str) -> dict:
    """Verifies a Google ID token's signature/audience/issuer and returns
    its claims (email, name, email_verified, ...). Raises HTTPException on
    anything invalid -- expired token, wrong audience, tampered signature."""
    # Imported lazily so the rest of the app still works even if a
    # deployment hasn't installed google-auth / configured Google sign-in.
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google sign-in isn't configured on this server (GOOGLE_CLIENT_ID missing).",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google sign-in token",
        )

    if not claims.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account email is not verified",
        )

    return claims


# --- Password reset ---
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30


def generate_password_reset_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash). The raw token goes in the emailed
    link and is never stored; only its SHA-256 hash is saved, same idea as
    never storing a plaintext password."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def hash_reset_token(raw_token: str) -> str:
    """Hashes an incoming raw token from a reset link the same way, so it
    can be looked up by token_hash."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
