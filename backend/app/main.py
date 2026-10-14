from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from .config import settings
from .db import Base, engine, get_db
from .models import User
from .profile_models import CareerProfile
from .profile_schemas import CareerProfileResponse, CareerProfileUpsert
from .profile_service import get_profile, upsert_profile
from .schemas import RegisterRequest, UserResponse
from .security import create_access_token, decode_access_token, hash_password, verify_password

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FuturePath AI API", version="0.3.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret,
    same_site="lax",
    https_only=settings.cookie_secure,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def set_session_cookie(response: Response, user_id: int) -> None:
    token = create_access_token(str(user_id))
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def get_current_user(request: Request, db: Session) -> User:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is unavailable.")
    return user


@app.get("/health")
def health():
    return {"status": "ok", "service": "futurepath-ai-api"}


@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    email = payload.email.lower().strip()
    exists = db.scalar(select(User).where(or_(User.username == username, User.email == email)))
    if exists:
        raise HTTPException(status_code=409, detail="Username or email is already registered.")
    user = User(username=username, email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login")
def login(response: Response, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identity = form.username.strip()
    user = db.scalar(select(User).where(or_(User.username == identity, User.email == identity.lower())))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username/email or password.")
    set_session_cookie(response, user.id)
    return {"authenticated": True, "user": UserResponse.model_validate(user)}


@app.get("/auth/google/login")
async def google_login(request: Request):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google SSO is not configured on this deployment.")
    redirect_uri = f"{settings.backend_url.rstrip('/')}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google SSO is not configured on this deployment.")
    try:
        token = await oauth.google.authorize_access_token(request)
        info = token.get("userinfo")
        if not info:
            info = await oauth.google.userinfo(token=token)
    except Exception:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified. Please try again.")
    email = (info.get("email") or "").lower().strip()
    if not email or not info.get("email_verified", False):
        raise HTTPException(status_code=403, detail="A verified Google email is required.")
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        base_username = (email.split("@")[0] or "futurepath")[:70]
        username = base_username
        suffix = 1
        while db.scalar(select(User).where(User.username == username)):
            suffix += 1
            username = f"{base_username[:70-len(str(suffix))]}{suffix}"
        user = User(username=username, email=email, password_hash=hash_password(__import__("secrets").token_urlsafe(48)))
        db.add(user)
        db.commit()
        db.refresh(user)
    response = RedirectResponse(url=f"{settings.frontend_url.rstrip('/')}/welcome")
    set_session_cookie(response, user.id)
    return response


@app.get("/auth/me", response_model=UserResponse)
def current_user(request: Request, db: Session = Depends(get_db)):
    return get_current_user(request, db)


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    return {"authenticated": False}


@app.get("/profile", response_model=CareerProfileResponse | None)
def read_profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return get_profile(db, user.id)


@app.put("/profile", response_model=CareerProfileResponse)
def save_profile(payload: CareerProfileUpsert, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return upsert_profile(db, user.id, payload)
