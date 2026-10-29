from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's query")
    history: List[ChatMessage] = Field(default_factory=list, description="Previous conversation turns")
    contextRoleId: Optional[str] = Field(None, description="Currently selected career role if any")


class ChatResponse(BaseModel):
    reply: str
    suggestedQuestions: List[str] = Field(default_factory=list)
    mode: str = Field(..., description="'ai_model' or 'expert_rules'")
    modelName: str
