"""Resume Analyzer & Intelligence Studio API Router.

Endpoints:
- POST /api/resume/upload: Uploads and parses PDF/DOCX/TXT resume
- POST /api/resume/analyze: Executes 4-pillar scoring & JD match and persists in PostgreSQL
- POST /api/resume/correct/{id}: Updates user-corrected extraction and recalculates scores
- POST /api/resume/rewrite-bullet: AI Improvement Studio bullet point rewriter
- POST /api/resume/sync-to-roadmap/{id}: Directly syncs resume missing skills into personalized roadmap
- GET  /api/resume/history: Retrieves user's saved resume analyses
- GET  /api/resume/history/{id}: Retrieves single analysis breakdown
- DELETE /api/resume/history/{id}: Deletes an analysis record
- GET  /api/resume/report/{id}/download: Generates and streams downloadable PDF report
"""

import io
import logging
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from database.models import CareerRole, Skill, User
from backend.app.config import app_settings
from backend.app.dependencies import get_current_user

logger = logging.getLogger("pathify.resume")
from backend.app.schemas.resume import (
    BulletRewriteRequest,
    BulletRewriteResponse,
    ResumeAnalyzeRequest,
    ResumeAnalyzeResponse,
    ResumeCorrectionRequest,
    ResumeHistoryItem,
    ResumeHistoryResponse,
    ResumeUploadResponse,
    SyncRoadmapResponse,
)
from backend.app.services.resume_improver import (
    ACTION_VERBS,
    analyze_bullet_impact,
    generate_xyz_rewrites,
)
from backend.app.services.resume_parser import (
    extract_raw_text,
    parse_resume,
)
from backend.app.services.resume_pdf_service import generate_resume_pdf_report
from backend.app.services.resume_service import (
    analyze_resume_data,
    delete_resume_analysis,
    get_resume_analysis_by_id,
    get_user_resume_history,
    save_resume_analysis,
    sync_missing_skills_to_roadmap,
)
from backend.app.services.role_service import get_role_by_id_or_slug

router = APIRouter(
    prefix="/api/resume",
    tags=["Resume Analyzer & Intelligence Studio"],
)

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and parse a resume file (PDF, DOCX, TXT)",
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Securely uploads, validates, and extracts text & structural sections from a resume."""
    filename = file.filename or "uploaded_resume.pdf"
    content_type = file.content_type or "application/octet-stream"

    # Extension validation
    lower_name = filename.lower()
    valid_ext = lower_name.endswith((".pdf", ".docx", ".doc", ".txt"))
    if not valid_ext and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a PDF (.pdf), Microsoft Word (.docx), or plain text (.txt) resume.",
        )

    # Read file bytes with size constraint
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty. Please select a valid resume document.",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 5 MB limit. Please upload a smaller document.",
        )

    # Load normalized skill names from PostgreSQL for entity matching
    skills_res = await session.execute(select(Skill.name))
    known_skills = list(skills_res.scalars().all())

    try:
        raw_text = extract_raw_text(file_bytes, filename, content_type)
        parsed = parse_resume(raw_text, reference_skills=known_skills)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        logger.exception(f"Unexpected error while parsing resume: {exc}")
        detail_msg = (
            f"An unexpected error occurred while parsing the resume: {str(exc)}"
            if app_settings.debug
            else "An unexpected error occurred while parsing the resume. Please ensure the document is not corrupted."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg,
        )

    # Sanitize filename for display
    clean_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)

    return ResumeUploadResponse(
        success=True,
        filename=clean_filename,
        file_size_bytes=file_size,
        file_type=content_type,
        raw_text=raw_text,
        parsed=parsed,
        message="Resume extracted and structured successfully.",
    )


@router.post(
    "/analyze",
    response_model=ResumeAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute complete four-pillar scoring and save analysis",
)
async def analyze_resume_endpoint(
    payload: ResumeAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Executes 4-pillar ATS scoring, JD matching, and persists the analysis in PostgreSQL."""
    if not payload.raw_text or not payload.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume text provided for analysis.",
        )

    # Resolve target career role if provided
    role: Optional[CareerRole] = None
    role_id_uuid: Optional[uuid.UUID] = None
    if payload.role_id:
        role = await get_role_by_id_or_slug(session, payload.role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target career role '{payload.role_id}' not found.",
            )
        role_id_uuid = role.id

    # Load normalized skills for matching
    skills_res = await session.execute(select(Skill.name))
    known_skills = list(skills_res.scalars().all())

    # Execute 4-pillar analysis
    analysis_data = analyze_resume_data(
        raw_text=payload.raw_text,
        filename=payload.filename or "Resume.pdf",
        file_size_bytes=payload.file_size_bytes or len(payload.raw_text.encode("utf-8")),
        file_type=payload.file_type or "application/pdf",
        role=role,
        job_description=payload.job_description,
        reference_skills=known_skills,
    )

    # If user passed corrected skills, merge them into extracted skills
    if payload.corrected_skills is not None:
        analysis_data["parsed_data"]["extracted_skills"] = sorted(list(set(payload.corrected_skills)))

    # Persist in PostgreSQL for authenticated user
    analysis_record = await save_resume_analysis(
        session=session,
        user_id=current_user.id,
        analysis_dict=analysis_data,
        role_id=role_id_uuid,
        job_description=payload.job_description,
    )

    return ResumeAnalyzeResponse(
        success=True,
        id=str(analysis_record.id),
        filename=analysis_record.filename,
        target_role_title=role.title if role else "General Technical Pathway",
        overall_score=analysis_record.overall_score,
        pillar_formatting_score=analysis_record.pillar_formatting_score,
        pillar_content_score=analysis_record.pillar_content_score,
        pillar_skills_score=analysis_record.pillar_skills_score,
        pillar_experience_score=analysis_record.pillar_experience_score,
        jd_match_percentage=analysis_record.jd_match_percentage,
        score_breakdown=analysis_record.score_breakdown,
        matched_skills=analysis_record.matched_skills,
        missing_skills=analysis_record.missing_skills,
        jd_match=analysis_data["jd_match"],
        improvement_recommendations=analysis_record.improvement_recommendations,
        parsed_data=analysis_record.parsed_data,
        created_at=analysis_record.created_at.isoformat() if analysis_record.created_at else None,
    )


@router.post(
    "/correct/{analysis_id}",
    response_model=ResumeAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user-corrected extraction fields and recalculate scores",
)
async def correct_resume_analysis(
    analysis_id: uuid.UUID,
    payload: ResumeCorrectionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Allows candidate to correct extraction errors (contact info, skills, experience) and recalculates."""
    analysis = await get_resume_analysis_by_id(session, analysis_id, current_user.id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis not found or unauthorized.",
        )

    # Update parsed data with corrections
    current_parsed = dict(analysis.parsed_data)
    if payload.contact:
        current_parsed["contact"] = payload.contact.model_dump()
    if payload.extracted_skills is not None:
        current_parsed["extracted_skills"] = payload.extracted_skills
    if payload.experience_bullets is not None:
        current_parsed["bullets"] = payload.experience_bullets

    # Role resolution
    role = analysis.role
    if payload.role_id:
        role = await get_role_by_id_or_slug(session, payload.role_id)

    # Re-run analysis
    skills_res = await session.execute(select(Skill.name))
    known_skills = list(skills_res.scalars().all())

    recalc = analyze_resume_data(
        raw_text=analysis.raw_text or "",
        filename=analysis.filename,
        file_size_bytes=analysis.file_size_bytes,
        file_type=analysis.file_type,
        role=role,
        job_description=payload.job_description or analysis.target_job_description,
        reference_skills=known_skills,
    )
    recalc["parsed_data"] = current_parsed

    # Update record
    analysis.role_id = role.id if role else None
    analysis.parsed_data = current_parsed
    analysis.overall_score = recalc["overall_score"]
    analysis.pillar_formatting_score = recalc["pillar_formatting_score"]
    analysis.pillar_content_score = recalc["pillar_content_score"]
    analysis.pillar_skills_score = recalc["pillar_skills_score"]
    analysis.pillar_experience_score = recalc["pillar_experience_score"]
    analysis.score_breakdown = recalc["score_breakdown"]
    analysis.matched_skills = recalc["matched_skills"]
    analysis.missing_skills = recalc["missing_skills"]
    analysis.jd_match_percentage = recalc["jd_match"].get("match_percentage")
    analysis.improvement_recommendations = recalc["improvement_recommendations"]

    await session.commit()
    await session.refresh(analysis)

    return ResumeAnalyzeResponse(
        success=True,
        id=str(analysis.id),
        filename=analysis.filename,
        target_role_title=role.title if role else "General Technical Pathway",
        overall_score=analysis.overall_score,
        pillar_formatting_score=analysis.pillar_formatting_score,
        pillar_content_score=analysis.pillar_content_score,
        pillar_skills_score=analysis.pillar_skills_score,
        pillar_experience_score=analysis.pillar_experience_score,
        jd_match_percentage=analysis.jd_match_percentage,
        score_breakdown=analysis.score_breakdown,
        matched_skills=analysis.matched_skills,
        missing_skills=analysis.missing_skills,
        jd_match=recalc["jd_match"],
        improvement_recommendations=analysis.improvement_recommendations,
        parsed_data=analysis.parsed_data,
        created_at=analysis.created_at.isoformat() if analysis.created_at else None,
    )


@router.post(
    "/rewrite-bullet",
    response_model=BulletRewriteResponse,
    status_code=status.HTTP_200_OK,
    summary="AI Improvement Studio: Rewrite bullet points using the XYZ formula",
)
async def rewrite_bullet_point(
    payload: BulletRewriteRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyzes a bullet point and returns high-impact rewrites following Google's XYZ formula."""
    if not payload.bullet_text or len(payload.bullet_text.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a bullet point sentence with at least 5 characters.",
        )

    impact = analyze_bullet_impact(payload.bullet_text)
    rewrites = generate_xyz_rewrites(payload.bullet_text, payload.target_role)

    # Sample top recommended action verbs
    sample_verbs = [v for sublist in ACTION_VERBS.values() for v in sublist[:2]]

    return BulletRewriteResponse(
        success=True,
        impact_analysis=impact,
        rewrites=rewrites,
        recommended_action_verbs=sample_verbs,
    )


@router.post(
    "/sync-to-roadmap/{analysis_id}",
    response_model=SyncRoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync missing skills from resume analysis into the user's Personalized Roadmap",
)
async def sync_to_roadmap(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """One-click integration: Adds missing skills from resume analysis into active career roadmap."""
    analysis = await get_resume_analysis_by_id(session, analysis_id, current_user.id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis record not found.",
        )

    try:
        sync_result = await sync_missing_skills_to_roadmap(session, analysis, current_user)
        return SyncRoadmapResponse(
            success=True,
            roadmap_id=sync_result["roadmap_id"],
            added_milestones=sync_result["added_milestones"],
            message=sync_result["message"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get(
    "/history",
    response_model=ResumeHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve user's previous resume analyses",
)
async def get_history(
    limit: int = 15,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Returns past resume analyses with scores and upload timestamps."""
    records = await get_user_resume_history(session, current_user.id, limit=limit)
    items: List[ResumeHistoryItem] = []

    for r in records:
        items.append(ResumeHistoryItem(
            id=str(r.id),
            filename=r.filename,
            file_type=r.file_type,
            role_title=r.role.title if r.role else "General",
            overall_score=r.overall_score,
            pillar_formatting_score=r.pillar_formatting_score,
            pillar_content_score=r.pillar_content_score,
            pillar_skills_score=r.pillar_skills_score,
            pillar_experience_score=r.pillar_experience_score,
            jd_match_percentage=r.jd_match_percentage,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M"),
        ))

    return ResumeHistoryResponse(success=True, total=len(items), history=items)


@router.get(
    "/history/{analysis_id}",
    response_model=ResumeAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve single resume analysis breakdown",
)
async def get_history_detail(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve details for a specific analysis."""
    analysis = await get_resume_analysis_by_id(session, analysis_id, current_user.id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis not found.",
        )

    return ResumeAnalyzeResponse(
        success=True,
        id=str(analysis.id),
        filename=analysis.filename,
        target_role_title=analysis.role.title if analysis.role else "General Technical Pathway",
        overall_score=analysis.overall_score,
        pillar_formatting_score=analysis.pillar_formatting_score,
        pillar_content_score=analysis.pillar_content_score,
        pillar_skills_score=analysis.pillar_skills_score,
        pillar_experience_score=analysis.pillar_experience_score,
        jd_match_percentage=analysis.jd_match_percentage,
        score_breakdown=analysis.score_breakdown,
        matched_skills=analysis.matched_skills,
        missing_skills=analysis.missing_skills,
        jd_match={
            "match_percentage": analysis.jd_match_percentage,
            "matched_keywords": [],
            "missing_keywords": [],
            "summary": "Historical analysis record.",
        },
        improvement_recommendations=analysis.improvement_recommendations,
        parsed_data=analysis.parsed_data,
        created_at=analysis.created_at.isoformat() if analysis.created_at else None,
    )


@router.delete(
    "/history/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an analysis record",
)
async def delete_history_item(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Deletes a saved resume analysis."""
    deleted = await delete_resume_analysis(session, analysis_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis not found or unauthorized.",
        )
    return {"success": True, "message": "Resume analysis deleted successfully."}


@router.get(
    "/report/{analysis_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Generate and stream downloadable PDF Intelligence Report",
)
async def download_pdf_report(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Generates an executive PDF report for the resume analysis and streams it as attachment."""
    analysis = await get_resume_analysis_by_id(session, analysis_id, current_user.id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis not found.",
        )

    try:
        pdf_bytes = generate_resume_pdf_report(analysis)
    except Exception as exc:
        logger.exception(f"Failed to generate PDF report: {exc}")
        detail_msg = (
            f"Failed to generate PDF report: {str(exc)}"
            if app_settings.debug
            else "Failed to generate PDF report. Please try again later."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg,
        )

    clean_filename = re.sub(r"[^a-zA-Z0-9_-]", "_", analysis.filename.replace(".pdf", "").replace(".docx", ""))
    download_name = f"Pathify_ATS_Report_{clean_filename}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
