import uuid
from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

# Import shared Base so all models share the same metadata used by init_db()
from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    # 'metadata' is a reserved attribute on SQLAlchemy declarative classes
    # use attribute name 'metadata_' mapped to the DB column 'metadata'
    metadata_ = Column('metadata', JSONB, nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationship for convenience; lazy loading will work when used with AsyncSession
    messages = relationship("Message", back_populates="conversation", lazy="selectin")
