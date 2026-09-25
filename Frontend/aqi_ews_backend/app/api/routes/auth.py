"""
app/api/routes/auth.py
POST /api/auth/register  — create account
POST /api/auth/login     — get JWT token
GET  /api/auth/me        — current user profile
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.services import user_service
from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email or phone + password.
    Returns a JWT token immediately so the frontend can redirect to the dashboard.
    """
    try:
        user = user_service.create_user(db, req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    token = create_access_token(subject=user.email or user.phone)
    return TokenResponse(
        access_token=token,
        user_name=user.full_name.split()[0].capitalize(),
        user_email=user.email,
        user_phone=user.phone,
        user_location=user.address,
        user_latitude=user.latitude,
        user_longitude=user.longitude,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email/phone + password.
    Returns a JWT access token.
    """
    user = user_service.authenticate_user(db, req.contact, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your email/phone and password.",
        )

    token = create_access_token(subject=user.email or user.phone)
    return TokenResponse(
        access_token=token,
        user_name=user.full_name.split()[0].capitalize(),
        user_email=user.email,
        user_phone=user.phone,
        user_location=user.address,
        user_latitude=user.latitude,
        user_longitude=user.longitude,
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user
