import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), nullable=True)
    role = Column(String, nullable=False)  # 'user'|'assistant'|'system'|'tool'
    content = Column(Text, nullable=True)
    content_type = Column(String, default="text")
    # 'metadata' is reserved on declarative classes; use 'metadata_' attribute
    metadata_ = Column('metadata', JSONB, nullable=True)
    attachment_url = Column(String, nullable=True)
    reply_to_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    tokens = Column(Integer, nullable=True)
    model = Column(String, nullable=True)
    deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    conversation = relationship("Conversation", back_populates="messages")


# index to support fast retrieval by conversation + created_at desc
Index("idx_messages_conversation_created", Message.conversation_id, Message.created_at.desc())
