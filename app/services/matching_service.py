"""Oddiy filtr: davlat + daraja + yo'nalish + reyting + ariza to'lovi bo'yicha
dasturlarni tanlaydi va til sertifikati bo'yicha
🟢 Mos / 🟡 Yaqin / 🔴 Mos emas toifalariga ajratadi.

🔴 toifadagilar (tuzatib bo'lmaydigan to'siq — o'tgan deadline)
chaqiruvchi tomonda foydalanuvchiga ko'rsatilmaydi.

GPA va yosh chegarasi endi hisobga olinmaydi: admin panelda bu maydonlar
yuritilmaydi, eski (seed) qiymatlar esa adminga ko'rinmagan holda natijaga
ta'sir qilib qolardi.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    DeadlineType,
    LanguageCertType,
    Program,
    University,
    UniversityRankRange,
    User,
)


class MatchLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class MatchResult:
    program: Program
    level: MatchLevel
    missing: list[str] = field(default_factory=list)


# Profildagi reyting oralig'i -> (eng yuqori o'rin, eng quyi o'rin). None = chegarasiz.
RANK_BOUNDS: dict[UniversityRankRange, tuple[int, int | None]] = {
    UniversityRankRange.TOP_100: (1, 100),
    UniversityRankRange.TOP_300: (101, 300),
    UniversityRankRange.TOP_500: (301, 500),
    UniversityRankRange.BELOW_500: (501, None),
}


async def find_matches(session: AsyncSession, user: User) -> list[MatchResult]:
    stmt = select(Program).join(Program.university).options(
        selectinload(Program.university).selectinload(University.country),
        selectinload(Program.requirement),
        # Kontrakt narxi ro'yxat kartasida ko'rsatiladi — bo'lmasa har bir
        # dastur uchun alohida so'rov ketardi (N+1).
        selectinload(Program.cost),
        selectinload(Program.deadlines),
    )

    if user.target_countries:
        country_ids = [c.id for c in user.target_countries]
        stmt = stmt.where(University.country_id.in_(country_ids))

    if user.degree_level is not None:
        stmt = stmt.where(Program.degree_level == user.degree_level)

    # Yo'nalish profilda katalogdagi qiymatlardan tanlanadi, shuning uchun
    # qat'iy (registrga sezgir bo'lmagan) tenglik xavfsiz.
    if user.major:
        stmt = stmt.where(func.lower(Program.field_of_study) == user.major.strip().lower())

    # Reytingi kiritilmagan universitetlar chiqarib tashlanmaydi: ma'lumot
    # yo'qligi "mos emas" degani emas — aks holda admin reytinglarni to'ldirib
    # bo'lguncha filtr deyarli hamma narsani yashirardi.
    if user.university_rank_range is not None:
        top, bottom = RANK_BOUNDS[user.university_rank_range]
        in_range = University.ranking >= top
        if bottom is not None:
            in_range = in_range & (University.ranking <= bottom)
        stmt = stmt.where(or_(University.ranking.is_(None), in_range))

    # Ariza to'loviga rozi bo'lmagan foydalanuvchiga to'lovli dasturlar
    # ko'rsatilmaydi. Tekshirilmagan (None) dasturlar qoladi.
    if user.application_fee_ok is False:
        stmt = stmt.where(
            or_(Program.has_application_fee.is_(None), Program.has_application_fee == false())
        )

    result = await session.execute(stmt)
    programs = result.unique().scalars().all()

    best_ielts = _best_score(user, LanguageCertType.IELTS)
    best_toefl = _best_score(user, LanguageCertType.TOEFL)

    return [_classify(program, best_ielts, best_toefl) for program in programs]


def _best_score(user: User, cert_type: LanguageCertType) -> float | None:
    scores = [
        float(cert.score) for cert in user.language_certificates if cert.type == cert_type
    ]
    return max(scores) if scores else None


def _classify(
    program: Program, best_ielts: float | None, best_toefl: float | None
) -> MatchResult:
    now = datetime.now(UTC)
    close_deadline = next(
        (d for d in program.deadlines if d.type == DeadlineType.APPLICATION_CLOSE), None
    )
    if close_deadline is not None and close_deadline.date_utc < now:
        return MatchResult(program=program, level=MatchLevel.RED, missing=["deadline"])

    missing: list[str] = []
    req = program.requirement
    if req is not None:
        language_gap = _language_gap(req.ielts_min, req.toefl_min, best_ielts, best_toefl)
        if language_gap:
            missing.append(language_gap)

    if missing:
        return MatchResult(program=program, level=MatchLevel.YELLOW, missing=missing)
    return MatchResult(program=program, level=MatchLevel.GREEN, missing=[])


def _language_gap(
    ielts_min: float | None,
    toefl_min: int | None,
    best_ielts: float | None,
    best_toefl: float | None,
) -> str | None:
    """Til talabi bajarilmagan bo'lsa yetishmayotgan sertifikat kalitini qaytaradi.

    Dastur IELTS ham, TOEFL ham qabul qilsa — ulardan BIRI yetarli.
    Kalitlar: "ielts", "toefl" yoki ikkalasi qabul qilinsa "ielts_toefl".
    """
    accepted = []
    if ielts_min is not None:
        accepted.append(("ielts", float(ielts_min), best_ielts))
    if toefl_min is not None:
        accepted.append(("toefl", float(toefl_min), best_toefl))
    if not accepted:
        return None

    if any(score is not None and score >= minimum for _, minimum, score in accepted):
        return None
    return "_".join(key for key, _, _ in accepted)
