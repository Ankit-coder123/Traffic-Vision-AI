import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Security: 'admin' is only self-assignable for the very first account
    # ever created (a standard "bootstrap admin" pattern) -- this is how
    # simulator.py creates its seed admin account on first run. Every
    # signup after that is restricted to 'operator' or 'user', regardless
    # of what role is requested, so the public can never mint new admins.
    is_first_user = db.query(models.User).count() == 0
    if is_first_user and user_in.role == "admin":
        role = "admin"
    else:
        role = user_in.role if user_in.role in ("operator", "user") else "user"

    new_user = models.User(
        name=user_in.name,
        email=user_in.email,
        password_hash=security.hash_password(user_in.password),
        role=role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm expects 'username' and 'password' fields
    # we treat 'username' as the email here
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/google", response_model=schemas.Token)
def google_login(payload: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Sign in (or auto-sign-up) with Google. The frontend uses Google
    Identity Services to get a signed ID token directly from Google --
    this endpoint verifies that token server-side and either logs the
    matching user in, or creates a new account for a first-time Google
    sign-in.

    Google-created accounts always get role='user' (same restriction as
    public signup) -- there's no path from here to 'operator' or 'admin'.
    Password login for a Google-created account isn't possible in practice:
    password_hash is set to a hash of a random, never-shared secret rather
    than left empty, since the column is NOT NULL and there's no separate
    'auth_provider' flag on the users table (see docs/ARCHITECTURE.md for
    why we're avoiding schema changes that create_all() can't apply to an
    already-existing table).
    """
    claims = security.verify_google_token(payload.credential)
    email = claims["email"]
    name = claims.get("name") or email.split("@")[0]

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            name=name,
            email=email,
            password_hash=security.hash_password(secrets.token_urlsafe(32)),
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UserOut)
def update_profile(
    payload: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Edit your own name and/or change your password. Email is deliberately
    NOT editable here -- it's both the login identifier and the unique key
    other tables (incidents, saved routes) trace back to; changing it
    without a verification flow (confirm the new address is real, isn't
    already taken, etc.) is a bigger feature than this project needs right
    now. Google-authenticated accounts can still change their name/password
    the same way as anyone else -- there's no restriction tied to how the
    account was created.
    """
    if payload.name is not None:
        stripped = payload.name.strip()
        if not stripped:
            raise HTTPException(status_code=422, detail="Name cannot be empty")
        current_user.name = stripped

    if payload.new_password is not None:
        if not payload.current_password:
            raise HTTPException(
                status_code=400,
                detail="current_password is required to set a new password",
            )
        if not security.verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        if len(payload.new_password) < 8:
            raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
        current_user.password_hash = security.hash_password(payload.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user
