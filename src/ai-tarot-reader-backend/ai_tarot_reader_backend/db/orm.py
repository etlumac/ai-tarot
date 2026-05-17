import uuid

from sqlalchemy import (
    Column, String, ForeignKey,
    Text, LargeBinary, ARRAY, Enum, func, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_mixin
from ai_tarot_reader_backend.entities.enums import ToneType, SessionStageType, SessionStatusType, ThemeType, \
    MessageRoleType, UIThemeType
from ai_tarot_reader_backend.core.database import Base

@declarative_mixin
class BaseTimestamp:
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)
    ip_address = Column(String(45), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    sessions = relationship("Session", back_populates="user")

    def __repr__(self):
        return f"<User {self.name}>"


class Image(Base):
    __tablename__ = "images"

    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)

    card_id = Column(UUID(as_uuid=True), nullable=False)

    ui_theme = Column(Enum(UIThemeType), nullable=False)
    image = Column(LargeBinary, nullable=False)

    def __repr__(self):
        return f"<Image card_id={self.card_id}>"


class Session(Base, BaseTimestamp):
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)

    tone = Column(Enum(ToneType), nullable=False)
    status = Column(Enum(SessionStatusType), nullable=False, default=SessionStatusType.PENDING)
    stage = Column(Enum(SessionStageType), nullable=False)
    theme = Column(Enum(ThemeType), nullable=True)

    prediction_cards = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    clarification_card = Column(UUID(as_uuid=True), nullable=True)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    title = Column(String(255), nullable=True)

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")

    def __repr__(self):
        return f"<Session {self.title}>"


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)

    role = Column(Enum(MessageRoleType), nullable=False)
    content = Column(Text, nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False
    )

    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message role={self.role}>"
