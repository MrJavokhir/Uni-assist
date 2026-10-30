"""Filtr: davlat + daraja + yo'nalish + reyting + o'qish tili
bo'yicha dasturlarni tanlaydi, keyin til bali bo'yicha uch toifaga ajratadi:

  🟢 Mos   — til talabi bajarilgan (yoki dasturda til talabi yo'q)
  🟡 Yaqin — talabga OZGINA yetmaydi (IELTS 0.5 gacha, TOEFL 8 ball gacha)
             yoki foydalanuvchi o'z balini kiritmagan — kartada nima
             yetishmasligi yoziladi
  yashirin — talabdan ANCHA past: ro'yxatga umuman tushmaydi

Ilgari ball kiritilganda yetmaydigan hamma dastur yashirilardi va "Yaqin"
toifasi amalda doim bo'sh qolardi ("131 mos, 0 yaqin"). Endi kichik farq
ko'rsatiladi — odam aynan qaysi dasturlarga sal ko'proq harakat bilan
kirishi mumkinligini ko'radi; katta farqdagilar esa avvalgidek ko'rinmaydi.

GPA moslikka TA'SIR QILMAYDI: filtr (qadamli onboarding) GPA so'ramaydi.
Profilda avvaldan saqlangan GPA bo'lsa ham e'tiborga olinmaydi — uni
o'zgartirib bo'lmaydigan joydan dasturlarni yashirishi noto'g'ri bo'lardi.
Dastur sahifasida minimal GPA faqat ma'lumot sifatida ko'rsatiladi.

🔴 (o'tgan deadline) chaqiruvchi tomonda ko'rsatilmaydi.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Country,
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
    # Talabdan ANCHA past — ro'yxatga tushmaydi.
    excluded: bool = False


# Til talabi kalitlari (kartada "Yetishmayapti: IELTS" deb chiqadi).
LANGUAGE_MISSING_KEYS = frozenset({"ielts", "toefl", "ielts_toefl"})

# "Yaqin" chegaralari: shundan kam yetishmasa dastur ko'rsatiladi.
IELTS_CLOSE_GAP = 0.5
TOEFL_CLOSE_GAP = 8


class Gap(str, Enum):
    MET = "met"
    UNKNOWN = "unknown"  # foydalanuvchi o'z balini kiritmagan
    CLOSE = "close"
    FAR = "far"

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

    # Yashirin davlat universitetlari tavsiya qilinmaydi.
    stmt = stmt.where(University.country.has(Country.hidden.is_(False)))
    if user.target_countries:
        country_ids = [c.id for c in user.target_countries]
        stmt = stmt.where(University.country_id.in_(country_ids))

    if user.degree_level is not None:
        stmt = stmt.where(Program.degree_level == user.degree_level)

    # Yo'nalish ma'lumotnomadan tanlanadi — ID bo'yicha tenglik. Yo'nalishi
    # biriktirilmagan (field_id NULL) dasturlar bu filtrga tushmaydi.
    if user.field_id is not None:
        stmt = stmt.where(Program.field_id == user.field_id)

    # Reytingi kiritilmagan universitetlar chiqarib tashlanmaydi: ma'lumot
    # yo'qligi "mos emas" degani emas — aks holda admin reytinglarni to'ldirib
    # bo'lguncha filtr deyarli hamma narsani yashirardi.
    if user.university_rank_range is not None:
        top, bottom = RANK_BOUNDS[user.university_rank_range]
        in_range = University.ranking >= top
        if bottom is not None:
            in_range = in_range & (University.ranking <= bottom)
        stmt = stmt.where(or_(University.ranking.is_(None), in_range))

    # O'qish tili — aniq tenglik. Bu yerda "ma'lumot yo'q" degan holat
    # yo'q: `language_of_instruction` majburiy ustun, ya'ni har bir
    # dasturda to'ldirilgan. Shuning uchun reyting singari "NULL ni
    # qoldirish" istisnosi kerak emas.
    if user.study_language:
        stmt = stmt.where(Program.language_of_instruction == user.study_language)

    # Ariza to'lovi bo'yicha filtr YO'Q: onboarding'da bu savol olib tashlangan.
    # Profilda avvaldan saqlangan "faqat bepul" ham e'tiborga olinmaydi —
    # uni o'zgartirib bo'lmaydigan joydan dasturlarni yashirishi noto'g'ri.

    result = await session.execute(stmt)
    programs = result.unique().scalars().all()

    best_ielts = _best_score(user, LanguageCertType.IELTS)
    best_toefl = _best_score(user, LanguageCertType.TOEFL)

    results = [_classify(program, best_ielts, best_toefl) for program in programs]
    return [r for r in results if not r.excluded]


def _best_score(user: User, cert_type: LanguageCertType) -> float | None:
    scores = [
        float(cert.score) for cert in user.language_certificates if cert.type == cert_type
    ]
    return max(scores) if scores else None


def _classify(
    program: Program,
    best_ielts: float | None,
    best_toefl: float | None,
) -> MatchResult:
    now = datetime.now(UTC)
    close_deadline = next(
        (d for d in program.deadlines if d.type == DeadlineType.APPLICATION_CLOSE), None
    )
    if close_deadline is not None and close_deadline.date_utc < now:
        return MatchResult(program=program, level=MatchLevel.RED, missing=["deadline"])

    missing: list[str] = []
    gaps: list[Gap] = []

    req = program.requirement
    if req is not None:
        key, gap = _language_gap(req.ielts_min, req.toefl_min, best_ielts, best_toefl)
        if gap is not Gap.MET:
            missing.append(key)
            gaps.append(gap)


    if Gap.FAR in gaps:
        return MatchResult(program=program, level=MatchLevel.YELLOW, missing=missing, excluded=True)
    if missing:
        return MatchResult(program=program, level=MatchLevel.YELLOW, missing=missing)
    return MatchResult(program=program, level=MatchLevel.GREEN, missing=[])


def _language_gap(
    ielts_min: float | None,
    toefl_min: int | None,
    best_ielts: float | None,
    best_toefl: float | None,
) -> tuple[str, Gap]:
    """Til talabi qanchalik bajarilgan.

    Dastur IELTS ham, TOEFL ham qabul qilsa — ulardan BIRI yetarli.
    Kalitlar: "ielts", "toefl" yoki ikkalasi qabul qilinsa "ielts_toefl".
    """
    accepted = []
    if ielts_min is not None:
        accepted.append(("ielts", float(ielts_min), best_ielts, IELTS_CLOSE_GAP))
    if toefl_min is not None:
        accepted.append(("toefl", float(toefl_min), best_toefl, TOEFL_CLOSE_GAP))
    if not accepted:
        return "", Gap.MET

    key = "_".join(name for name, _, _, _ in accepted)
    with_score = [(m, s, c) for _, m, s, c in accepted if s is not None]
    if any(score >= minimum for minimum, score, _ in with_score):
        return key, Gap.MET
    if not with_score:
        # Hech qanday til bali kiritilmagan bo'lsa — noma'lum (ko'rsatiladi).
        # Boshqa sertifikati bor-u, dastur uni qabul qilmasa — mos emas.
        has_any = best_ielts is not None or best_toefl is not None
        return key, Gap.FAR if has_any else Gap.UNKNOWN
    if any(minimum - score <= close for minimum, score, close in with_score):
        return key, Gap.CLOSE
    return key, Gap.FAR
