from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models.career import CareerProfile, Certification, Education, Experience, Project, Skill, UserSkill, ResumeExtraction
from .models.core import Resume
from .r1_profile import confirm_profile, profile_snapshot
from .schemas import CareerProfileRequest, CareerProfileResponse
from .main import get_current_user

router = APIRouter(prefix="/r1", tags=["r1-career-profile"])


def _serialize_model(item):
    result = {}
    for column in item.__table__.columns:
        value = getattr(item, column.name)
        if isinstance(value, (date,)):
            value = value.isoformat()
        result[column.name] = value
    return result


@router.get("/career-profile")
def get_r1_profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    snapshot = profile_snapshot(db, user.id)
    resume_ids = {x.source_resume_id for group in (snapshot["experiences"], snapshot["education"], snapshot["projects"], snapshot["certifications"]) for x in group if x.source_resume_id}
    resume_ids.update(x["source_resume_id"] for x in snapshot["skills"] if x["source_resume_id"])
    resumes = {}
    if resume_ids:
        for resume in db.scalars(select(Resume).where(Resume.id.in_(resume_ids), Resume.user_id == user.id)).all():
            resumes[str(resume.id)] = {"id": str(resume.id), "filename": resume.original_filename, "created_at": resume.created_at}
    return {
        "confirmed": bool(snapshot["profile"] and snapshot["profile"].is_user_confirmed),
        "profile": _serialize_model(snapshot["profile"]) if snapshot["profile"] else None,
        "experiences": [_serialize_model(x) for x in snapshot["experiences"]],
        "education": [_serialize_model(x) for x in snapshot["education"]],
        "projects": [_serialize_model(x) for x in snapshot["projects"]],
        "certifications": [_serialize_model(x) for x in snapshot["certifications"]],
        "skills": [{**x, "id": str(x["id"]), "skill_id": str(x["skill_id"]), "source_resume_id": str(x["source_resume_id"]) if x["source_resume_id"] else None} for x in snapshot["skills"]],
        "evidence": resumes,
    }


@router.post("/career-profile/confirm", response_model=CareerProfileResponse)
def confirm_r1_profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return confirm_profile(db, user.id)
