from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ExperienceInput(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=160)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str = Field(default="", max_length=5000)


class EducationInput(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    degree: str = Field(min_length=1, max_length=160)
    field_of_study: str = Field(default="", max_length=160)
    start_date: date | None = None
    end_date: date | None = None


class SkillInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    proficiency: str = Field(default="", max_length=50)


class CareerProfileUpsert(BaseModel):
    full_name: str = Field(default="", max_length=160)
    headline: str = Field(default="", max_length=240)
    summary: str = Field(default="", max_length=5000)
    location: str = Field(default="", max_length=160)
    target_role: str = Field(default="", max_length=160)
    target_industry: str = Field(default="", max_length=160)
    career_interests: str = Field(default="", max_length=2000)
    experiences: list[ExperienceInput] = Field(default_factory=list)
    education: list[EducationInput] = Field(default_factory=list)
    skills: list[SkillInput] = Field(default_factory=list)


class ExperienceResponse(ExperienceInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EducationResponse(EducationInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SkillResponse(SkillInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CareerProfileResponse(BaseModel):
    id: int
    full_name: str
    headline: str
    summary: str
    location: str
    target_role: str
    target_industry: str
    career_interests: str
    experiences: list[ExperienceResponse]
    education: list[EducationResponse]
    skills: list[SkillResponse]
    model_config = ConfigDict(from_attributes=True)
