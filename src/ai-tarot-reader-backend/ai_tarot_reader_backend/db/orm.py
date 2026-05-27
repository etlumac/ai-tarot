import uuid
from typing import Optional, List

from sqlalchemy import (
    String, ForeignKey, Text, LargeBinary, ARRAY, Enum, func,
    TIMESTAMP, Integer, Column
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship, declarative_mixin
)

from ai_tarot_reader_backend.entities.enums import (
    ToneType, SessionStageType, SessionStatusType, ThemeType,
    MessageRoleType, UIThemeType
)
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


class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sessions: Mapped[List["SessionModel"]] = relationship(
        "SessionModel", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.name}>"


class ImageModel(Base):
    __tablename__ = "images"

    image_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ui_theme: Mapped[UIThemeType] = mapped_column(
        Enum(UIThemeType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    image: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    def __repr__(self) -> str:
        return f"<Image card_id={self.card_id}>"


class SessionModel(Base, BaseTimestamp):
    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    tone: Mapped[ToneType] = mapped_column(Enum(ToneType), nullable=False)
    status: Mapped[SessionStatusType] = mapped_column(
        Enum(SessionStatusType),
        nullable=False,
        default=SessionStatusType.PENDING
    )
    stage: Mapped[SessionStageType] = mapped_column(Enum(SessionStageType), nullable=False)
    theme: Mapped[Optional[ThemeType]] = mapped_column(Enum(ThemeType), nullable=True)

    prediction_cards: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)
    clarification_card: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="sessions")
    messages: Mapped[List["MessageModel"]] = relationship("MessageModel", back_populates="session")

    def __repr__(self) -> str:
        return f"<Session {self.title}>"


class MessageModel(Base, BaseTimestamp):
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid7
    )
    role: Mapped[MessageRoleType] = mapped_column(Enum(MessageRoleType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False
    )

    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message role={self.role}>"