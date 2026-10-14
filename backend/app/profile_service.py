from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .profile_models import CareerProfile, Education, Experience, ProfileSkill
from .profile_schemas import CareerProfileUpsert


def get_profile(db: Session, user_id: int) -> CareerProfile | None:
    return db.scalar(select(CareerProfile).where(CareerProfile.user_id == user_id))


def upsert_profile(db: Session, user_id: int, payload: CareerProfileUpsert) -> CareerProfile:
    profile = get_profile(db, user_id)
    if profile is None:
        profile = CareerProfile(user_id=user_id)
        db.add(profile)
        db.flush()

    profile.full_name = payload.full_name.strip()
    profile.headline = payload.headline.strip()
    profile.summary = payload.summary.strip()
    profile.location = payload.location.strip()
    profile.target_role = payload.target_role.strip()
    profile.target_industry = payload.target_industry.strip()
    profile.career_interests = payload.career_interests.strip()

    profile.experiences.clear()
    profile.education.clear()
    profile.skills.clear()
    db.flush()

    for item in payload.experiences:
        profile.experiences.append(Experience(**item.model_dump()))
    for item in payload.education:
        profile.education.append(Education(**item.model_dump()))
    for item in payload.skills:
        profile.skills.append(ProfileSkill(**item.model_dump()))

    db.commit()
    db.refresh(profile)
    return profile
