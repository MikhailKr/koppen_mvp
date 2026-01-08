"""Chat API endpoint for AI agent interactions."""

import logging
import traceback

from pydantic import BaseModel
from fastapi import APIRouter

from app.core.deps import CurrentUser, DatabaseSession
from app.services.ai_agent_service import AIAgentService

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str
    conversation_history: list[dict[str, str]] | None = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str
    success: bool = True


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ChatResponse:
    """
    Chat with the AI agent about wind farms and forecasts.
    
    The agent can:
    - List your wind farms
    - Get detailed information about specific wind farms
    - Retrieve and analyze forecasts
    - Calculate forecast accuracy metrics (MAE, RMSE, MAPE, bias)
    - Summarize generation data
    """
    try:
        logger.info(f"Chat request from user {current_user.id}: {request.message[:100]}")
        agent = AIAgentService()
        response = await agent.chat(
            message=request.message,
            session=session,
            user_id=current_user.id,
            conversation_history=request.conversation_history,
        )
        logger.info(f"Chat response: {response[:200] if response else 'None'}")
        return ChatResponse(response=response, success=True)
    except Exception as e:
        logger.error(f"Chat error: {str(e)}\n{traceback.format_exc()}")
        return ChatResponse(response=f"Error: {str(e)}", success=False)



