from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse, TokenPair, RefreshRequest
from app.services.auth_service import create_user, authenticate_user, create_token_pair, rotate_refresh_token, revoke_refresh
from app.repositories.auth import SessionRepository, RefreshTokenRepository
from app.core.security import get_current_user
from app.core.login_protection import login_protection

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = create_user(db=db, payload=payload)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.full_name,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenPair)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or getattr(request.client, "host", None)
    rate_check = login_protection.check(client_ip, form_data.username)
    if not rate_check.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(rate_check.retry_after_seconds or 0)},
        )

    payload = LoginRequest(email=form_data.username, password=form_data.password)
    try:
        user = authenticate_user(db=db, payload=payload)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            login_protection.record_failure(client_ip, form_data.username)
        raise

    login_protection.record_success(client_ip, form_data.username)
    return create_token_pair(db=db, user=user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    tokens = rotate_refresh_token(db=db, refresh_token_str=payload.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    revoke_refresh(db=db, refresh_token_str=payload.refresh_token)
    return None


@router.post("/logout_all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    session_repo = SessionRepository(db)
    refresh_repo = RefreshTokenRepository(db)
    session_repo.revoke_all_for_user(current_user.id)
    refresh_repo.revoke_all_for_user(current_user.id)
    return None
