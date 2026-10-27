"""R1 career-profile read/write helpers.

Resume extraction is evidence. User-confirmed career data is authoritative and
must never be silently replaced by later resume processing.
"""
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models.career import CareerProfile, Certification, Education, Experience, Project, Skill, UserSkill


def profile_snapshot(db: Session, user_id: UUID) -> dict[str, Any]:
    profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == user_id))
    experiences = list(db.scalars(select(Experience).where(Experience.user_id == user_id).order_by(Experience.start_date.desc().nullslast())).all())
    education = list(db.scalars(select(Education).where(Education.user_id == user_id).order_by(Education.start_date.desc().nullslast())).all())
    projects = list(db.scalars(select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())).all())
    certifications = list(db.scalars(select(Certification).where(Certification.user_id == user_id).order_by(Certification.issue_date.desc().nullslast())).all())
    skills = list(db.execute(select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id).where(UserSkill.user_id == user_id).order_by(Skill.normalized_name)).all())
    return {
        "profile": profile, "experiences": experiences, "education": education,
        "projects": projects, "certifications": certifications,
        "skills": [{"id": us.id, "skill_id": skill.id, "name": skill.name, "category": skill.category,
                    "proficiency_level": us.proficiency_level,
                    "years_experience": float(us.years_experience) if us.years_experience is not None else None,
                    "last_used_date": us.last_used_date, "evidence_notes": us.evidence_notes,
                    "source_resume_id": us.source_resume_id, "is_user_confirmed": us.is_user_confirmed}
                   for us, skill in skills],
    }


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _set_model(model: Any, values: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if field in values:
            value = values[field]
            if field in {"start_date", "end_date", "issue_date", "expiry_date", "last_used_date"}:
                value = _date(value)
            setattr(model, field, value)


def save_user_corrections(db: Session, user_id: UUID, payload: dict[str, Any]) -> CareerProfile:
    """Persist the complete user-edited R1 snapshot without auto-confirming it."""
    profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == user_id))
    if not profile:
        profile = CareerProfile(user_id=user_id)
        db.add(profile)
        db.flush()
    _set_model(profile, payload.get("profile") or {}, ("headline", "professional_summary", "current_location", "preferred_locations", "preferred_work_modes", "target_roles", "years_experience", "is_open_to_opportunities"))

    specs = {
        "experiences": (Experience, ("company_name", "job_title", "employment_type", "location", "start_date", "end_date", "is_current", "description", "achievements")),
        "education": (Education, ("institution", "qualification", "field_of_study", "start_date", "end_date", "grade", "description")),
        "projects": (Project, ("name", "role", "description", "technologies", "project_url", "start_date", "end_date")),
        "certifications": (Certification, ("name", "issuing_organization", "credential_id", "credential_url", "issue_date", "expiry_date", "does_not_expire")),
    }
    for key, (model_cls, fields) in specs.items():
        rows = payload.get(key) or []
        existing = {str(x.id): x for x in db.scalars(select(model_cls).where(model_cls.user_id == user_id)).all()}
        retained = set()
        for item in rows:
            if not isinstance(item, dict):
                continue
            row = existing.get(str(item.get("id"))) if item.get("id") else None
            if row is None:
                row = model_cls(user_id=user_id)
                db.add(row)
            _set_model(row, item, fields)
            row.is_user_confirmed = False
            retained.add(str(row.id))
        for row_id, row in existing.items():
            if row_id not in retained:
                db.delete(row)

    existing_skills = {str(x.id): x for x in db.scalars(select(UserSkill).where(UserSkill.user_id == user_id)).all()}
    retained_skills = set()
    for item in payload.get("skills") or []:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        row = existing_skills.get(str(item.get("id"))) if item.get("id") else None
        normalized = " ".join(str(item["name"]).strip().lower().split())
        skill = db.scalar(select(Skill).where(Skill.normalized_name == normalized))
        if not skill:
            skill = Skill(name=str(item["name"]).strip()[:120], normalized_name=normalized[:120], category=item.get("category"))
            db.add(skill)
            db.flush()
        if row is None:
            row = UserSkill(user_id=user_id, skill_id=skill.id)
            db.add(row)
        else:
            row.skill_id = skill.id
        _set_model(row, item, ("proficiency_level", "years_experience", "last_used_date", "evidence_notes"))
        row.is_user_confirmed = False
        retained_skills.add(str(row.id))
    for row_id, row in existing_skills.items():
        if row_id not in retained_skills:
            db.delete(row)
    db.flush()
    return profile


def confirm_profile(db: Session, user_id: UUID) -> CareerProfile:
    profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == user_id))
    if not profile:
        profile = CareerProfile(user_id=user_id)
        db.add(profile)
    profile.is_user_confirmed = True
    profile.confirmed_at = datetime.now(timezone.utc)
    for model_cls in (Experience, Education, Project, Certification):
        for row in db.scalars(select(model_cls).where(model_cls.user_id == user_id)).all():
            row.is_user_confirmed = True
    for row in db.scalars(select(UserSkill).where(UserSkill.user_id == user_id)).all():
        row.is_user_confirmed = True
    db.commit()
    db.refresh(profile)
    return profile
