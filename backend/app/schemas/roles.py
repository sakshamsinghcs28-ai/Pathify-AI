from typing import List
from pydantic import BaseModel


class RoleItem(BaseModel):
    id: str
    title: str
    category: str
    description: str
    requiredSkills: List[str]


class RolesResponse(BaseModel):
    success: bool = True
    message: str = "Temporary sample career roles (mock data for development)"
    totalRoles: int
    roles: List[RoleItem]
