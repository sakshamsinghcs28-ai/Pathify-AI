from typing import List, Optional
from pydantic import BaseModel, Field


class RoadmapStep(BaseModel):
    stepNumber: int
    skill: str
    learningGoal: str
    practiceTask: str
    estimatedDuration: str
    completed: bool = False
    priority: Optional[str] = "High"
    importance: Optional[str] = "required"


class RoadmapSummary(BaseModel):
    totalRequiredSkills: int
    acquiredSkillsCount: int
    missingSkillsCount: int
    totalRoadmapSteps: int
    completedMilestonesCount: int = 0
    completionPercentage: int = 0


class ToggleMilestoneRequest(BaseModel):
    roleId: Optional[str] = Field(None, description="Target career role identifier (e.g. role-1, role-3)")
    stepNumber: int = Field(..., description="1-based step number or milestone index")
    completed: Optional[bool] = Field(None, description="Explicit target completion state. If omitted, flips current state.")


class ProfileRoadmapResponse(BaseModel):
    success: bool = True
    profileId: str
    studentName: str
    targetRoleId: str
    targetRoleTitle: str
    notice: str = "Temporary demo roadmap for development purposes. Not live industry data or AI-generated."
    summary: RoadmapSummary
    roadmap: List[RoadmapStep]
