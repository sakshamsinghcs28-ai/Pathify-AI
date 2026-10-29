from fastapi import APIRouter
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_service import process_chat_message

router = APIRouter(tags=["AI Career Chatbot"])


@router.post("/api/chat", response_model=ChatResponse)
async def chat_with_advisor(payload: ChatRequest):
    """Interactive career coaching and skill roadmap chatbot."""
    return await process_chat_message(
        message=payload.message,
        history=payload.history,
        context_role_id=payload.contextRoleId,
    )
