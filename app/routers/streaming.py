from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.schemas.conversation import StreamRequest

router = APIRouter(prefix="/streaming")

@router.post("/generate")
async def stream_generation(
    request: StreamRequest
):
    """
    Stream generation endpoint (placeholder)
    
    This is a placeholder for the streaming API endpoint.
    It will be implemented in a future task.
    """
    return {
        "status": "not_implemented",
        "message": "Streaming API not yet implemented"
    }
