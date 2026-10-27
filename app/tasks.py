from datetime import datetime, timezone

from sqlalchemy import select

from .celery_app import celery_app
from .db.session import SessionLocal
from .education_persistence import ensure_education_persisted
from .education_recovery import recover_education_from_text
from .models.core import ProcessingJob, Resume
from .models.career import CareerProfile, ResumeExtraction
from .resume_processing import deterministic_extract, extract_pdf_text, llm_extract, process_resume, persist_extraction
from .storage import resume_storage


@celery_app.task(bind=True, name="app.tasks.process_resume_job")
def process_resume_job(self, job_id: str):
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job or job.status in {"succeeded", "cancelled"}:
            return
        job.status = "running"
        job.attempt_count += 1
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        try:
            # A confirmed profile is user-owned. New resume submissions still
            # get a fresh extraction/evidence record, but must not overwrite
            # anything the user has already confirmed.
            resume = db.get(Resume, job.resume_id) if job.resume_id else None
            profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == job.user_id))
            if profile and profile.is_user_confirmed and resume:
                content = resume_storage.read(resume.storage_key)
                text = extract_pdf_text(content)
                data = llm_extract(text)
                extraction = db.scalar(select(ResumeExtraction).where(ResumeExtraction.resume_id == resume.id, ResumeExtraction.extractor_version == "r1-v1"))
                if not extraction:
                    extraction = ResumeExtraction(resume_id=resume.id, extractor_version="r1-v1", status="pending")
                    db.add(extraction)
                    db.flush()
                extraction.extracted_data = data
                extraction.status = "succeeded"
                extraction.completed_at = datetime.now(timezone.utc)
                extraction.error_code = None
                extraction.error_message = None
            else:
                process_resume(db, job)

                # R1 postcondition: if extraction contains education, at least one
                # corresponding education row must exist before the job succeeds.
                resume = db.get(Resume, job.resume_id) if job.resume_id else None
                if resume:
                    extraction = db.scalar(
                        select(ResumeExtraction).where(
                            ResumeExtraction.resume_id == resume.id,
                            ResumeExtraction.extractor_version == "r1-v1",
                        )
                    )
                    if extraction and extraction.extracted_data:
                        ensure_education_persisted(db, resume, extraction.extracted_data)

            job.status = "succeeded"
            job.finished_at = datetime.now(timezone.utc)
            job.error_code = None
            job.error_message = None
            db.commit()
        except Exception as exc:
            db.rollback()

            # Recover malformed education from the same stored PDF rather than
            # burning Celery retries on a deterministic provider-shape problem.
            if isinstance(exc, ValueError) and str(exc).startswith("R1 education item could not be normalized"):
                try:
                    job = db.get(ProcessingJob, job.id)
                    resume = db.get(Resume, job.resume_id) if job.resume_id else None
                    profile = db.scalar(select(CareerProfile).where(CareerProfile.user_id == job.user_id))
                    if resume and not (profile and profile.is_user_confirmed):
                        content = resume_storage.read(resume.storage_key)
                        text = extract_pdf_text(content)
                        recovered_education = recover_education_from_text(text)
                        if not recovered_education:
                            recovered_education = deterministic_extract(text).get("education", [])
                        if recovered_education:
                            extraction_data = llm_extract(text)
                            if not isinstance(extraction_data, dict):
                                extraction_data = deterministic_extract(text)
                            extraction_data["education"] = recovered_education
                            persist_extraction(db, resume, extraction_data)
                            extraction = db.scalar(select(ResumeExtraction).where(ResumeExtraction.resume_id == resume.id, ResumeExtraction.extractor_version == "r1-v1"))
                            if not extraction:
                                extraction = ResumeExtraction(resume_id=resume.id, extractor_version="r1-v1", status="pending")
                                db.add(extraction)
                                db.flush()
                            extraction.extracted_data = extraction_data
                            extraction.status = "succeeded"
                            extraction.completed_at = datetime.now(timezone.utc)
                            extraction.error_code = None
                            extraction.error_message = None
                            job.status = "succeeded"
                            job.finished_at = datetime.now(timezone.utc)
                            job.error_code = None
                            job.error_message = None
                            db.commit()
                            return
                except Exception:
                    db.rollback()

            job = db.get(ProcessingJob, job.id)
            job.error_code = "PROCESSING_FAILED"
            job.error_message = str(exc)[:500]
            if job.attempt_count < job.max_attempts:
                job.status = "queued"
                db.commit()
                raise self.retry(exc=exc, countdown=min(60 * (2 ** (job.attempt_count - 1)), 900))
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise
    finally:
        db.close()
