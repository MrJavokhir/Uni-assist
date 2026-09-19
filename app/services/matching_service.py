"""Oddiy filtr: davlat + GPA + til sertifikati bo'yicha dasturlarni
🟢 Mos / 🟡 Yaqin / 🔴 Mos emas toifalariga ajratadi.

🔴 toifadagilar (tuzatib bo'lmaydigan to'siqlar — yosh, o'tgan deadline)
chaqiruvchi tomonda (bot handler) foydalanuvchiga ko'rsatilmaydi.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import DeadlineType, LanguageCertType, Program, University, User
from app.services.gpa_converter import to_us4


class MatchLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class MatchResult:
    program: Program
    level: MatchLevel
    missing: list[str] = field(default_factory=list)


async def find_matches(session: AsyncSession, user: User) -> list[MatchResult]:
    stmt = select(Program).join(Program.university).options(
        selectinload(Program.university).selectinload(University.country),
        selectinload(Program.requirement),
        selectinload(Program.deadlines),
    )

    if user.target_countries:
        country_ids = [c.id for c in user.target_countries]
        stmt = stmt.where(University.country_id.in_(country_ids))

    if user.degree_level is not None:
        stmt = stmt.where(Program.degree_level == user.degree_level)

    # Yo'nalish profilda katalogdagi qiymatlardan tanlanadi, shuning uchun
    # qat'iy (registrga sezgir bo'lmagan) tenglik xavfsiz. Ilgari `major`
    # saqlanardi-yu, moslik qidiruvida umuman ishlatilmasdi.
    if user.major:
        stmt = stmt.where(func.lower(Program.field_of_study) == user.major.strip().lower())

    result = await session.execute(stmt)
    programs = result.unique().scalars().all()

    best_ielts = _best_score(user, LanguageCertType.IELTS)

    return [_classify(program, user, best_ielts) for program in programs]


def _best_score(user: User, cert_type: LanguageCertType) -> float | None:
    scores = [
        float(cert.score) for cert in user.language_certificates if cert.type == cert_type
    ]
    return max(scores) if scores else None


def _classify(program: Program, user: User, best_ielts: float | None) -> MatchResult:
    red_reasons: list[str] = []
    missing: list[str] = []

    now = datetime.now(UTC)
    close_deadline = next(
        (d for d in program.deadlines if d.type == DeadlineType.APPLICATION_CLOSE), None
    )
    if close_deadline is not None and close_deadline.date_utc < now:
        red_reasons.append("deadline")

    req = program.requirement
    if req is not None:
        if req.age_limit is not None and user.age is not None and user.age > req.age_limit:
            red_reasons.append("age")

        if req.gpa_min is not None and req.gpa_scale is not None:
            if user.gpa_raw is not None and user.gpa_scale is not None:
                user_us4 = to_us4(float(user.gpa_raw), user.gpa_scale)
                req_us4 = to_us4(float(req.gpa_min), req.gpa_scale)
                if user_us4 < req_us4:
                    missing.append("gpa")
            else:
                missing.append("gpa")

        if req.ielts_min is not None:
            if best_ielts is not None:
                if best_ielts < float(req.ielts_min):
                    missing.append("ielts")
            else:
                missing.append("ielts")

    if red_reasons:
        return MatchResult(program=program, level=MatchLevel.RED, missing=red_reasons)
    if missing:
        return MatchResult(program=program, level=MatchLevel.YELLOW, missing=missing)
    return MatchResult(program=program, level=MatchLevel.GREEN, missing=[])
