import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

class Message(Base):
    """
    Database model for storing a single message (from user, system, or LLM)
    """
    __tablename__ = "messages"
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey('messages.message_id'), nullable=True, index=True)
    llm_id = Column(String(50), nullable=True)
    llm_metadata = Column(JSONB, nullable=True)  # Raw metadata from LLM responses
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    replies = relationship("Message", backref="parent", remote_side=[message_id])
