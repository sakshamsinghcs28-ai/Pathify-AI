"""Pydantic schemas for Resume Analyzer and Intelligence Studio."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResumeContactInfo(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    portfolio: Optional[str] = ""
    location: Optional[str] = ""


class ResumeSections(BaseModel):
    summary: Optional[str] = ""
    experience: Optional[str] = ""
    education: Optional[str] = ""
    skills: Optional[str] = ""
    projects: Optional[str] = ""
    certifications: Optional[str] = ""


class ResumeParsedData(BaseModel):
    contact: ResumeContactInfo = Field(default_factory=ResumeContactInfo)
    sections: ResumeSections = Field(default_factory=ResumeSections)
    bullets: List[str] = Field(default_factory=list)
    extracted_skills: List[str] = Field(default_factory=list)
    word_count: int = 0
    line_count: int = 0


class ResumeUploadResponse(BaseModel):
    success: bool = True
    filename: str
    file_size_bytes: int
    file_type: str
    raw_text: str
    parsed: ResumeParsedData
    message: str = "Resume parsed successfully."


class ResumeAnalyzeRequest(BaseModel):
    filename: Optional[str] = "Uploaded_Resume.pdf"
    file_size_bytes: Optional[int] = 0
    file_type: Optional[str] = "application/pdf"
    raw_text: str
    role_id: Optional[str] = None
    job_description: Optional[str] = None
    corrected_skills: Optional[List[str]] = None


class PillarScoreDetail(BaseModel):
    score: float
    name: str
    description: str
    findings: List[Dict[str, str]] = Field(default_factory=list)
    metrics_percentage: Optional[float] = None
    action_verb_percentage: Optional[float] = None
    total_bullets_analyzed: Optional[int] = None
    matched_count: Optional[int] = None
    missing_count: Optional[int] = None


class ScoreBreakdown(BaseModel):
    formatting: PillarScoreDetail
    content: PillarScoreDetail
    skills: PillarScoreDetail
    experience: PillarScoreDetail


class JDMatchResult(BaseModel):
    match_percentage: Optional[float] = None
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    summary: str = ""


class ResumeAnalyzeResponse(BaseModel):
    success: bool = True
    id: Optional[str] = None
    filename: str
    target_role_title: Optional[str] = None
    overall_score: float
    pillar_formatting_score: float
    pillar_content_score: float
    pillar_skills_score: float
    pillar_experience_score: float
    jd_match_percentage: Optional[float] = None
    score_breakdown: ScoreBreakdown
    matched_skills: List[Dict[str, Any]] = Field(default_factory=list)
    missing_skills: List[Dict[str, Any]] = Field(default_factory=list)
    jd_match: JDMatchResult
    improvement_recommendations: List[Dict[str, str]] = Field(default_factory=list)
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class ResumeCorrectionRequest(BaseModel):
    contact: Optional[ResumeContactInfo] = None
    extracted_skills: Optional[List[str]] = None
    experience_bullets: Optional[List[str]] = None
    role_id: Optional[str] = None
    job_description: Optional[str] = None


class BulletRewriteRequest(BaseModel):
    bullet_text: str
    target_role: Optional[str] = None


class BulletRewriteResponse(BaseModel):
    success: bool = True
    impact_analysis: Dict[str, Any]
    rewrites: List[Dict[str, Any]]
    recommended_action_verbs: List[str]


class ResumeHistoryItem(BaseModel):
    id: str
    filename: str
    file_type: str
    role_title: Optional[str] = "General"
    overall_score: float
    pillar_formatting_score: float
    pillar_content_score: float
    pillar_skills_score: float
    pillar_experience_score: float
    jd_match_percentage: Optional[float] = None
    created_at: str


class ResumeHistoryResponse(BaseModel):
    success: bool = True
    total: int
    history: List[ResumeHistoryItem]


class SyncRoadmapResponse(BaseModel):
    success: bool
    roadmap_id: str
    added_milestones: List[str]
    message: str
