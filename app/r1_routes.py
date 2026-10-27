import hashlib
import json
from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models.core import Resume, User
from .r1_profile import confirm_profile, profile_snapshot, save_user_corrections
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


def _snapshot_json(snapshot: dict) -> str:
    def default(value):
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        return str(value)
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=default)


def _refresh_embedding_state(db: Session, user_id: UUID, snapshot: dict) -> None:
    canonical = _snapshot_json({
        "profile": _serialize_model(snapshot["profile"]),
        "experiences": [_serialize_model(x) for x in snapshot["experiences"]],
        "education": [_serialize_model(x) for x in snapshot["education"]],
        "projects": [_serialize_model(x) for x in snapshot["projects"]],
        "certifications": [_serialize_model(x) for x in snapshot["certifications"]],
        "skills": snapshot["skills"],
    })
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    db.execute(text("""
        INSERT INTO career_profile_embeddings
            (id, user_id, content_hash, embedding_model, dimensions, status, embedding)
        VALUES
            (:id, :user_id, :content_hash, 'pending-r1-foundation', 0, 'pending', NULL)
        ON CONFLICT (user_id) DO UPDATE SET
            content_hash = EXCLUDED.content_hash,
            status = CASE WHEN career_profile_embeddings.content_hash = EXCLUDED.content_hash
                          THEN career_profile_embeddings.status ELSE 'pending' END,
            updated_at = now()
    """), {"id": str(uuid4()), "user_id": str(user_id), "content_hash": content_hash})


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


@router.put("/career-profile")
def update_r1_profile(payload: dict, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="R1 profile payload must be an object.")
    try:
        profile = save_user_corrections(db, user.id, payload)
        db.commit()
        snapshot = profile_snapshot(db, user.id)
        _refresh_embedding_state(db, user.id, snapshot)
        db.commit()
        db.refresh(profile)
        return {"saved": True, "confirmed": bool(profile.is_user_confirmed), "profile_id": str(profile.id)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Could not save R1 profile: {exc}") from exc


@router.post("/career-profile/confirm")
def confirm_r1_profile(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    profile = confirm_profile(db, user.id)
    snapshot = profile_snapshot(db, user.id)
    _refresh_embedding_state(db, user.id, snapshot)
    db.commit()
    return {"confirmed": True, "confirmed_at": profile.confirmed_at}
