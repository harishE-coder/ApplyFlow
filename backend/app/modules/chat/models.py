"""
Chat models — ChatRoom, ChatMessage, ChatRead.
One chat room per Service Client. Messages are scoped to rooms.
Read tracking uses a cursor (last read message per user per room).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.clients.models import Client  # noqa: F401
from app.modules.users.models import User  # noqa: F401


class ChatRoom(Base):
    """One chat room per Service Client."""
    __tablename__ = "chat_rooms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, read_only, archived
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )

    # Relationships
    client: Mapped["Client"] = relationship(lazy="selectin")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="room", lazy="noload",
    )


class ChatMessage(Base):
    """Individual chat message within a room."""
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_rooms.id"), nullable=False, index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attachment_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "resume", "pdf", "file", None
    attachment_reference: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # resume_id, drive_file_id, or download reference
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), index=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    room: Mapped["ChatRoom"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship(lazy="selectin")


class ChatRead(Base):
    """
    Tracks each user's read position per chat room using cursor-based last_read_message_id.
    Unread count = messages in room with created_at > cursor message created_at.
    """
    __tablename__ = "chat_reads"
    __table_args__ = (
        UniqueConstraint("user_id", "room_id", name="uq_chat_read_user_room"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_rooms.id"), nullable=False, index=True
    )
    last_read_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chat_messages.id"), nullable=True
    )
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")
    room: Mapped["ChatRoom"] = relationship(lazy="selectin")
    last_read_message: Mapped["ChatMessage"] = relationship(lazy="selectin")
