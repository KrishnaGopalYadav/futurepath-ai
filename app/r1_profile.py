"""R1 career-profile read/write helpers.

User-confirmed profile data is authoritative. Resume extraction is evidence and
must never silently overwrite a confirmed value.
"""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models.career import CareerProfile, Certification, Education, Experience, Project, Skill, UserSkill

COLLECTIONS = {
    "experiences": Experience,
    "education": Education,
    "projects": Project,
    "certifications": Certification,
    "skills": UserSkill,
}


def profile_snapshot(db: Session, user_id: UUID) -> dict[str, Any]:
    profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == user_id))
    experiences = list(db.scalars(select(Experience).where(Experience.user_id == user_id).order_by(Experience.start_date.desc().nullslast())).all())
    education = list(db.scalars(select(Education).where(Education.user_id == user_id).order_by(Education.start_date.desc().nullslast())).all())
    projects = list(db.scalars(select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())).all())
    certifications = list(db.scalars(select(Certification).where(Certification.user_id == user_id).order_by(Certification.issue_date.desc().nullslast())).all())
    skills = list(db.execute(select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id).where(UserSkill.user_id == user_id).order_by(Skill.normalized_name)).all())
    return {
        "profile": profile,
        "experiences": experiences,
        "education": education,
        "projects": projects,
        "certifications": certifications,
        "skills": [{"id": us.id, "skill_id": skill.id, "name": skill.name, "category": skill.category, "proficiency_level": us.proficiency_level, "years_experience": float(us.years_experience) if us.years_experience is not None else None, "last_used_date": us.last_used_date, "evidence_notes": us.evidence_notes, "source_resume_id": us.source_resume_id, "is_user_confirmed": us.is_user_confirmed} for us, skill in skills],
    }


def confirm_profile(db: Session, user_id: UUID) -> CareerProfile:
    profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == user_id))
    if not profile:
        profile = CareerProfile(user_id=user_id)
        db.add(profile)
    profile.is_user_confirmed = True
    profile.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
