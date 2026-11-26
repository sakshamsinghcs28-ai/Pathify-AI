from datetime import datetime
from typing import Any, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


ProficiencyLevelStr = Literal["Beginner", "Intermediate", "Advanced", "Expert"]


class SkillProficiencyInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=160, description="Skill name")
    level: str = Field(default="Intermediate", description="Beginner, Intermediate, Advanced, Expert")

    @field_validator("level")
    @classmethod
    def normalize_level(cls, v: str) -> str:
        cleaned = v.strip().capitalize()
        valid = {"Beginner", "Intermediate", "Advanced", "Expert"}
        if cleaned not in valid:
            return "Intermediate"
        return cleaned


class ExperienceInput(BaseModel):
    projectsCount: int = Field(default=0, ge=0, le=50, description="Number of relevant projects completed")
    internshipMonths: int = Field(default=0, ge=0, le=120, description="Months of relevant internship experience")
    description: Optional[str] = Field(None, max_length=1000, description="Optional brief description of experience")


class SkillGapRequest(BaseModel):
    roleId: str = Field(..., min_length=1, description="The role identifier (e.g. role-1 or UUID)")
    skills: List[Union[SkillProficiencyInput, str]] = Field(
        default_factory=list,
        description="List of user skills, either plain strings or {name, level} objects",
    )
    experience: Optional[ExperienceInput] = Field(
        default=None,
        description="Optional applied project and internship experience",
    )


class MatchedSkillDetail(BaseModel):
    name: str
    userLevel: str
    requiredLevel: str
    category: str = "technical"
    scoreWeight: float
    importance: str = "required"


class ImprovingSkillDetail(BaseModel):
    name: str
    userLevel: str
    requiredLevel: str
    gap: int
    category: str = "technical"
    scoreWeight: float
    importance: str = "required"


class MissingSkillDetail(BaseModel):
    name: str
    requiredLevel: str
    priority: Literal["High", "Medium", "Low"]
    importance: str
    category: str = "technical"
    scoreWeight: float


class RecommendationDetail(BaseModel):
    skill: str
    priority: Literal["High", "Medium", "Low"]
    type: Literal["acquire_missing", "upskill_level"]
    action: str
    estimatedHours: int


class SkillGapAnalysis(BaseModel):
    totalRequiredSkills: int
    matchedCount: int
    missingCount: int
    improvingCount: int = 0
    matchPercentage: str
    explanation: str
    readinessScore: float = 0.0
    baseTechnicalScore: float = 0.0
    experienceBonus: float = 0.0
    weightedScore: float = 0.0
    totalPossibleWeight: float = 0.0


class SkillGapResponse(BaseModel):
    success: bool = True
    roleId: str
    roleTitle: str
    assessmentId: Optional[str] = None
    createdAt: Optional[str] = None
    analysis: SkillGapAnalysis
    matchedSkills: List[str]
    missingSkills: List[str]
    improvingSkills: List[str] = Field(default_factory=list)
    detailedMatched: List[MatchedSkillDetail] = Field(default_factory=list)
    detailedImproving: List[ImprovingSkillDetail] = Field(default_factory=list)
    detailedMissing: List[MissingSkillDetail] = Field(default_factory=list)
    recommendations: List[RecommendationDetail] = Field(default_factory=list)


class AssessmentHistoryItem(BaseModel):
    id: str
    roleId: str
    roleTitle: str
    readinessScore: float
    matchPercentage: str
    createdAt: str
    matchedCount: int
    improvingCount: int
    missingCount: int


class AssessmentHistoryResponse(BaseModel):
    success: bool = True
    total: int
    assessments: List[AssessmentHistoryItem]
