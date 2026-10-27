from typing import List, Optional
from pydantic import BaseModel, Field
from .skill_gap import SkillGapAnalysis


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Student full name")
    education: Optional[str] = Field(None, description="Education background")
    skills: List[str] = Field(default_factory=list, description="List of student skills")
    targetRoleId: str = Field(..., description="Target career role identifier (e.g. role-1)")


class ProfileData(BaseModel):
    id: str
    name: str
    education: Optional[str] = None
    skills: List[str]
    targetRoleId: str
    targetRoleTitle: str
    createdAt: str


class ProfileCreateResponse(BaseModel):
    success: bool = True
    message: str = "Student profile created successfully (temporary in-memory storage)"
    profile: ProfileData


class ProfileDetailResponse(BaseModel):
    success: bool = True
    profile: ProfileData


class ProfileSkillGapResponse(BaseModel):
    success: bool = True
    profileId: str
    studentName: str
    roleId: str
    roleTitle: str
    analysis: SkillGapAnalysis
    matchedSkills: List[str]
    missingSkills: List[str]
