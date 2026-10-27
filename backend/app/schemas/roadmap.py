from typing import List
from pydantic import BaseModel


class RoadmapStep(BaseModel):
    stepNumber: int
    skill: str
    learningGoal: str
    practiceTask: str
    estimatedDuration: str


class RoadmapSummary(BaseModel):
    totalRequiredSkills: int
    acquiredSkillsCount: int
    missingSkillsCount: int
    totalRoadmapSteps: int


class ProfileRoadmapResponse(BaseModel):
    success: bool = True
    profileId: str
    studentName: str
    targetRoleId: str
    targetRoleTitle: str
    notice: str = "Temporary demo roadmap for development purposes. Not live industry data or AI-generated."
    summary: RoadmapSummary
    roadmap: List[RoadmapStep]
