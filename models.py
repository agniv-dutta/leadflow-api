from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, event, func, insert, inspect
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"
    CONVERTED = "converted"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_status", native_enum=False),
        nullable=False,
        default=LeadStatus.NEW,
        index=True,
    )


class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_activity_previous_status", native_enum=False),
        nullable=False,
        index=True,
    )
    new_status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_activity_new_status", native_enum=False),
        nullable=False,
        index=True,
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


@event.listens_for(Lead, "after_update")
def log_lead_status_change(mapper, connection, target):
    status_history = inspect(target).attrs.status.history
    if not status_history.has_changes():
        return

    previous_status = status_history.deleted[0] if status_history.deleted else None
    new_status = status_history.added[0] if status_history.added else None
    if previous_status is None or new_status is None:
        return

    connection.execute(
        insert(LeadActivity.__table__).values(
            lead_id=target.id,
            previous_status=previous_status,
            new_status=new_status,
            changed_at=datetime.now(timezone.utc),
        )
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
