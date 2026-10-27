from typing import List
from pydantic import BaseModel, Field


class SkillGapRequest(BaseModel):
    roleId: str = Field(..., description="The role identifier (e.g. role-1 or UUID)")
    skills: List[str] = Field(default_factory=list, description="List of user skill names")


class SkillGapAnalysis(BaseModel):
    totalRequiredSkills: int
    matchedCount: int
    missingCount: int
    matchPercentage: str
    explanation: str


class SkillGapResponse(BaseModel):
    success: bool = True
    roleId: str
    roleTitle: str
    analysis: SkillGapAnalysis
    matchedSkills: List[str]
    missingSkills: List[str]
