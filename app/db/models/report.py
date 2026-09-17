import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, str_enum

if TYPE_CHECKING:
    from app.db.models.program import Program
    from app.db.models.scholarship import Scholarship
    from app.db.models.user import User


class ReportStatus(str, enum.Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"


class Report(TimestampMixin, Base):
    """Foydalanuvchi 'Ma'lumot noto'g'ri' tugmasini bosganda yaratiladigan signal."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int | None] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), nullable=True
    )
    scholarship_id: Mapped[int | None] = mapped_column(
        ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        str_enum(ReportStatus, "report_status"), nullable=False, default=ReportStatus.NEW
    )

    program: Mapped["Program"] = relationship()
    scholarship: Mapped["Scholarship"] = relationship()
    user: Mapped["User"] = relationship()

    def __str__(self) -> str:
        target = f"program={self.program_id}" if self.program_id else f"scholarship={self.scholarship_id}"
        return f"Report #{self.id} ({target})"
