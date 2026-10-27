from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr | None
    is_active: bool
    auth_provider: str
    model_config = {"from_attributes": True}


class CareerProfileRequest(BaseModel):
    headline: str | None = Field(default=None, max_length=200)
    professional_summary: str | None = None
    current_location: str | None = Field(default=None, max_length=160)
    preferred_locations: list[str] | None = None
    preferred_work_modes: list[str] | None = None
    target_roles: list[str] | None = None
    years_experience: float | None = Field(default=None, ge=0, le=99.9)
    is_open_to_opportunities: bool = False
    is_user_confirmed: bool | None = None


class CareerProfileResponse(CareerProfileRequest):
    id: UUID
    user_id: UUID
    is_user_confirmed: bool
    confirmed_at: datetime | None = None
    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    file_size_bytes: int | None
    checksum_sha256: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ProcessingJobResponse(BaseModel):
    id: UUID
    resume_id: UUID | None
    job_type: str
    status: str
    attempt_count: int
    max_attempts: int
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    model_config = {"from_attributes": True}
