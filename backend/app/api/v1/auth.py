from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import secrets
import string

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import User
from app.schemas.auth import TokenResponse, UserResponse
from app.api.deps import get_current_user

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth = OAuth()

if settings.GITHUB_CLIENT_ID:
    oauth.register(
        name="github",
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

if settings.GOOGLE_CLIENT_ID:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_or_create_user(
    db: AsyncSession,
    email: str,
    name: str,
    avatar_url: Optional[str] = None,
    oauth_provider: Optional[str] = None,
    oauth_id: Optional[str] = None,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.name = name or user.name
        user.avatar_url = avatar_url or user.avatar_url
    else:
        user = User(
            email=email,
            name=name,
            avatar_url=avatar_url,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            is_verified=True,
        )
        db.add(user)
    await db.flush()
    return user


@router.get("/login/{provider}")
async def login(request: Request, provider: str):
    if provider not in oauth._clients:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not configured")
    redirect_uri = request.url_for("auth_callback", provider=provider)
    return await oauth[provider].authorize_redirect(request, redirect_uri)


@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(request: Request, provider: str, db: AsyncSession = Depends(get_db)):
    if provider not in oauth._clients:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not configured")

    token = await oauth[provider].authorize_access_token(request)
    if provider == "github":
        resp = await oauth[provider].get("user", token=token)
        profile = resp.json()
        email = profile.get("email") or f"{profile['login']}@github.local"
        name = profile.get("name") or profile["login"]
        avatar_url = profile.get("avatar_url")
        oauth_id = str(profile["id"])
    else:
        resp = await oauth[provider].get("userinfo", token=token)
        profile = resp.json()
        email = profile["email"]
        name = profile.get("name", "")
        avatar_url = profile.get("picture")
        oauth_id = profile["sub"]

    user = await get_or_create_user(
        db=db,
        email=email,
        name=name,
        avatar_url=avatar_url,
        oauth_provider=provider,
        oauth_id=oauth_id,
    )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    redirect_url = f"{settings.CORS_ORIGINS[0]}/auth/callback?token={access_token}"
    return RedirectResponse(url=redirect_url)


@router.post("/register", response_model=TokenResponse)
async def register(
    email: str,
    password: str,
    name: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        name=name,
        hashed_password=pwd_context.hash(password),
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login_email(
    email: str,
    password: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)