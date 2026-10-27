from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4
import secrets

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from .config import settings
from .db import get_db
from .models.core import User, Resume, ProcessingJob
from .models.career import CareerProfile, ResumeExtraction
from .schemas import CareerProfileRequest, CareerProfileResponse, ProcessingJobResponse, RegisterRequest, ResumeResponse, UserResponse
from .security import create_access_token, decode_access_token, hash_password, verify_password
from .storage import resume_storage
from .tasks import process_resume_job

app = FastAPI(title="FuturePath AI API", version="0.4.0")
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret, same_site="lax", https_only=settings.cookie_secure)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])

oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(name="google", client_id=settings.google_client_id, client_secret=settings.google_client_secret, server_metadata_url="https://accounts.google.com/.well-known/openid-configuration", client_kwargs={"scope": "openid email profile"})


def set_session_cookie(response: Response, user_id: UUID) -> None:
    token = create_access_token(str(user_id))
    response.set_cookie(key=settings.auth_cookie_name, value=token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.jwt_expire_minutes * 60, path="/")


def get_current_user(request: Request, db: Session) -> User:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    try:
        user = db.get(User, UUID(user_id))
    except (ValueError, TypeError):
        user = None
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is unavailable.")
    return user


@app.get("/health")
def health():
    return {"status": "ok", "service": "futurepath-ai-api"}


@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    username, email = payload.username.strip(), payload.email.lower().strip()
    if db.scalar(select(User).where(or_(User.username == username, User.email == email))):
        raise HTTPException(status_code=409, detail="Username or email is already registered.")
    user = User(username=username, email=email, password_hash=hash_password(payload.password), auth_provider="password", auth_subject=username)
    db.add(user)
    db.commit(); db.refresh(user)
    return user


@app.post("/auth/login")
def login(response: Response, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identity = form.username.strip()
    user = db.scalar(select(User).where(or_(User.username == identity, User.email == identity.lower())))
    if not user or not user.is_active or not user.password_hash or not verify_password(form.password, user.password_hash):
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
        info = token.get("userinfo") or await oauth.google.userinfo(token=token)
    except Exception:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified. Please try again.")
    email, subject = (info.get("email") or "").lower().strip(), str(info.get("sub") or "").strip()
    if not email or not info.get("email_verified", False) or not subject:
        raise HTTPException(status_code=403, detail="A verified Google identity is required.")
    user = db.scalar(select(User).where(User.auth_provider == "google", User.auth_subject == subject))
    if not user:
        user = db.scalar(select(User).where(User.email == email))
    if not user:
        base = (email.split("@")[0] or "futurepath")[:70]
        username, suffix = base, 1
        while db.scalar(select(User).where(User.username == username)):
            suffix += 1; username = f"{base[:70-len(str(suffix))]}{suffix}"
        user = User(username=username, email=email, password_hash=hash_password(secrets.token_urlsafe(48)), auth_provider="google", auth_subject=subject)
        db.add(user)
    else:
        user.email = email; user.auth_provider = "google"; user.auth_subject = subject
    db.commit(); db.refresh(user)
    response = RedirectResponse(url=f"{settings.frontend_url.rstrip('/')}/welcome")
    set_session_cookie(response, user.id)
    return response


@app.get("/auth/me", response_model=UserResponse)
def current_user(request: Request, db: Session = Depends(get_db)):
    return get_current_user(request, db)


@app.get("/career-profile", response_model=CareerProfileResponse | None)
def get_career_profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return db.scalar(select(CareerProfile).where(CareerProfile.user_id == user.id))


@app.put("/career-profile", response_model=CareerProfileResponse)
def upsert_career_profile(payload: CareerProfileRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == user.id))
    if not profile:
        profile = CareerProfile(user_id=user.id, **payload.model_dump()); db.add(profile)
    else:
        for key, value in payload.model_dump().items(): setattr(profile, key, value)
    db.commit(); db.refresh(profile)
    return profile


@app.post("/resumes", response_model=ResumeResponse, status_code=202)
async def upload_resume(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if file.content_type != "application/pdf" or not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF resumes are supported.")
    content = await file.read(settings.max_resume_size_mb * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Resume file is empty.")
    if len(content) > settings.max_resume_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Resume exceeds the {settings.max_resume_size_mb} MB limit.")
    checksum = sha256(content).hexdigest()
    resume_id = uuid4()
    storage_key = resume_storage.key_for(user.id, resume_id)
    resume = Resume(id=resume_id, user_id=user.id, original_filename=Path(file.filename or "resume.pdf").name[:255], content_type="application/pdf", file_size_bytes=len(content), storage_key=storage_key, checksum_sha256=checksum)
    db.add(resume); db.flush()
    job = ProcessingJob(user_id=user.id, resume_id=resume.id, job_type="resume_extraction", status="queued")
    db.add(job)
    try:
        resume_storage.save(storage_key, content)
        db.commit()
    except Exception:
        db.rollback(); resume_storage.delete(storage_key)
        raise HTTPException(status_code=500, detail="Could not store resume.")
    process_resume_job.delay(str(job.id))
    return resume


@app.get("/resumes", response_model=list[ResumeResponse])
def list_resumes(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return list(db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())).all())


@app.get("/resumes/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: UUID, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if not resume: raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


@app.get("/resumes/{resume_id}/processing-job", response_model=ProcessingJobResponse | None)
def get_resume_job(resume_id: UUID, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if not resume: raise HTTPException(status_code=404, detail="Resume not found.")
    return db.scalar(select(ProcessingJob).where(ProcessingJob.resume_id == resume.id).order_by(ProcessingJob.created_at.desc()))


@app.get("/processing-jobs/{job_id}", response_model=ProcessingJobResponse)
def get_job(job_id: UUID, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id, ProcessingJob.user_id == user.id))
    if not job: raise HTTPException(status_code=404, detail="Processing job not found.")
    return job


@app.post("/processing-jobs/{job_id}/retry", response_model=ProcessingJobResponse)
def retry_job(job_id: UUID, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id, ProcessingJob.user_id == user.id))
    if not job: raise HTTPException(status_code=404, detail="Processing job not found.")
    if job.status not in {"failed", "cancelled"}: raise HTTPException(status_code=409, detail="Only failed or cancelled jobs can be retried.")
    job.status = "queued"; job.error_code = None; job.error_message = None; job.finished_at = None
    db.commit(); db.refresh(job)
    process_resume_job.delay(str(job.id))
    return job


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    return {"authenticated": False}


from .r1_routes import router as r1_router
app.include_router(r1_router)
