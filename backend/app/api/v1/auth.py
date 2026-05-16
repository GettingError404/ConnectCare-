from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse, TokenPair, RefreshRequest
from app.services.auth_service import create_user, authenticate_user, create_token_pair, rotate_refresh_token, revoke_refresh
from app.repositories.auth import SessionRepository, RefreshTokenRepository
from app.core.security import get_current_user

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
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = (request.headers.get("content-type") or "").lower()

    try:
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            # Swagger OAuth2 sends username/password + optional grant_type.
            payload = LoginRequest(
                email=form.get("username") or form.get("email") or "",
                password=form.get("password") or "",
            )
        else:
            body = await request.json()
            payload = LoginRequest.model_validate(body)
    except (ValidationError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid login payload")

    user = authenticate_user(db=db, payload=payload)
    tokens = create_token_pair(db=db, user=user)
    return tokens


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
