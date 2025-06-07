import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import users, conversations, messages, streaming

app = FastAPI(
    title="5mins-learning-app API",
    description="API for quick learning on any topic",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(streaming.router, prefix="/api/stream", tags=["streaming"])

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint to verify the API is running
    """
    return {
        "status": "ok",
        "version": app.version,
        "environment": os.getenv("ENV", "development")
    }

if __name__ == "__main__":
    import uvicorn
    
    # Run the application with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload during development
    )
