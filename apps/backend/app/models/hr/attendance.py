import uuid
from datetime import date, datetime, time

from sqlalchemy import TIMESTAMP, Date, ForeignKey, String, Time, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, schema_column, schema_table_args

MODULE_UUID = Uuid(as_uuid=True)
TENANT_UUID = String(36)


class VacationRequest(Base):
    __tablename__ = "vacation_requests"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        MODULE_UUID, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        MODULE_UUID,
        ForeignKey(schema_column("employees"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    days: Mapped[int] = mapped_column(nullable=False, default=1)
    request_type: Mapped[str] = mapped_column(String(30), nullable=False, default="vacaciones")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente", index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(MODULE_UUID, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="vacations", lazy="select")


class TimeEntry(Base):
    __tablename__ = "time_entries"
    __table_args__ = schema_table_args()

    id: Mapped[uuid.UUID] = mapped_column(
        MODULE_UUID, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        MODULE_UUID,
        ForeignKey(schema_column("employees"), ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    clock_in_time: Mapped[time] = mapped_column(Time, nullable=False)
    clock_out_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    entry_type: Mapped[str] = mapped_column(String(30), nullable=False, default="trabajo")
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    employee: Mapped["Employee"] = relationship(
        "Employee", back_populates="time_entries", lazy="select"
    )
