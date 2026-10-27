import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class CareerProfile(Base):
    __tablename__ = "career_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_career_profiles_user_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    headline: Mapped[str | None] = mapped_column(String(200))
    professional_summary: Mapped[str | None] = mapped_column(Text)
    current_location: Mapped[str | None] = mapped_column(String(160))
    preferred_locations: Mapped[list | None] = mapped_column(JSONB)
    preferred_work_modes: Mapped[list | None] = mapped_column(JSONB)
    target_roles: Mapped[list | None] = mapped_column(JSONB)
    years_experience: Mapped[float | None] = mapped_column(Numeric(4,1))
    is_open_to_opportunities: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class Experience(Base):
    __tablename__ = "experiences"
    __table_args__ = (CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="ck_experiences_dates"), Index("ix_experiences_user_dates", "user_id", "start_date"))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(40))
    location: Mapped[str | None] = mapped_column(String(160))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    description: Mapped[str | None] = mapped_column(Text)
    achievements: Mapped[list | None] = mapped_column(JSONB)
    source_resume_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"))
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class Education(Base):
    __tablename__ = "education"
    __table_args__ = (CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="ck_education_dates"), Index("ix_education_user_dates", "user_id", "start_date"))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    institution: Mapped[str] = mapped_column(String(240), nullable=False)
    qualification: Mapped[str | None] = mapped_column(String(160))
    field_of_study: Mapped[str | None] = mapped_column(String(160))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    grade: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    source_resume_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"))
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = (Index("ix_certifications_user_name", "user_id", "name"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_organization: Mapped[str | None] = mapped_column(String(200))
    credential_id: Mapped[str | None] = mapped_column(String(160))
    credential_url: Mapped[str | None] = mapped_column(String(500))
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    does_not_expire: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    source_resume_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"))
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_user_name", "user_id", "name"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list | None] = mapped_column(JSONB)
    project_url: Mapped[str | None] = mapped_column(String(500))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    source_resume_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"))
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_skills_normalized_name"), Index("ix_skills_category", "category"))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skills_user_skill"), CheckConstraint("proficiency_level IS NULL OR proficiency_level BETWEEN 1 AND 5", name="ck_user_skills_proficiency"), CheckConstraint("years_experience IS NULL OR years_experience >= 0", name="ck_user_skills_years"), Index("ix_user_skills_skill_id", "skill_id"))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False)
    proficiency_level: Mapped[int | None] = mapped_column(Integer)
    years_experience: Mapped[float | None] = mapped_column(Numeric(4,1))
    last_used_date: Mapped[date | None] = mapped_column(Date)
    evidence_notes: Mapped[str | None] = mapped_column(Text)
    source_resume_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"))
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class ResumeExtraction(Base):
    __tablename__ = "resume_extractions"
    __table_args__ = (UniqueConstraint("resume_id", "extractor_version", name="uq_resume_extractions_resume_version"), CheckConstraint("status IN ('pending','succeeded','failed')", name="ck_resume_extractions_status"), Index("ix_resume_extractions_status_created", "status", "created_at"))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    extracted_data: Mapped[dict | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
