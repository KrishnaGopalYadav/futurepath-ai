from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models.career import UserSkill
from .models.core import Resume, User
from .r1_profile import confirm_profile, profile_snapshot
from .security import decode_access_token

router = APIRouter(prefix="/r1", tags=["r1-career-profile"])


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
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


def _serialize_model(item):
    if not item:
        return None
    result = {}
    for column in item.__table__.columns:
        value = getattr(item, column.name)
        if isinstance(value, date):
            value = value.isoformat()
        result[column.name] = value
    return result


@router.get("/career-profile")
def get_r1_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    snapshot = profile_snapshot(db, user.id)
    resume_ids = {x.source_resume_id for group in (snapshot["experiences"], snapshot["education"], snapshot["projects"], snapshot["certifications"]) for x in group if x.source_resume_id}
    resume_ids.update(x["source_resume_id"] for x in snapshot["skills"] if x["source_resume_id"])
    evidence = {}
    if resume_ids:
        for resume in db.scalars(select(Resume).where(Resume.id.in_(resume_ids), Resume.user_id == user.id)).all():
            evidence[str(resume.id)] = {"id": str(resume.id), "filename": resume.original_filename, "created_at": resume.created_at}
    return {
        "confirmed": bool(snapshot["profile"] and snapshot["profile"].is_user_confirmed),
        "profile": _serialize_model(snapshot["profile"]),
        "experiences": [_serialize_model(x) for x in snapshot["experiences"]],
        "education": [_serialize_model(x) for x in snapshot["education"]],
        "projects": [_serialize_model(x) for x in snapshot["projects"]],
        "certifications": [_serialize_model(x) for x in snapshot["certifications"]],
        "skills": [{**x, "id": str(x["id"]), "skill_id": str(x["skill_id"]), "source_resume_id": str(x["source_resume_id"]) if x["source_resume_id"] else None} for x in snapshot["skills"]],
        "evidence": evidence,
    }


@router.post("/career-profile/confirm")
def confirm_r1_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    profile = confirm_profile(db, user.id)
    snapshot = profile_snapshot(db, user.id)
    for model in snapshot["experiences"] + snapshot["education"] + snapshot["projects"] + snapshot["certifications"]:
        model.is_user_confirmed = True
    for skill in snapshot["skills"]:
        row = db.get(UserSkill, UUID(skill["id"]))
        if row:
            row.is_user_confirmed = True
    db.commit()
    return {"confirmed": True, "confirmed_at": profile.confirmed_at}
