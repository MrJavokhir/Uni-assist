from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Country,
    DegreeLevel,
    GpaScale,
    LanguageCertType,
    Program,
    SavedProgram,
    SavedProgramStatus,
    Scholarship,
    UiLanguage,
    University,
    User,
)
from app.db.session import get_session
from app.services.gpa_converter import convert as convert_gpa
from app.services.matching_service import MatchLevel, find_matches
from app.services.timezone_utils import format_tashkent
from app.services.user_service import (
    get_or_create_user,
    set_target_countries,
    upsert_language_certificate,
)
from app.webapp.auth import InitDataError, validate_init_data
from app.webapp.schemas import (
    CountryOut,
    GpaConvertOut,
    LanguageCertOut,
    MatchProgramOut,
    ProfileIn,
    ProfileOut,
    SavedOut,
    SavedStatusIn,
    ScholarshipDeadlineOut,
    ScholarshipOut,
)

router = APIRouter()


async def get_current_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        result = validate_init_data(x_telegram_init_data)
    except InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    # Majburiy kanal obunasi ATAYLAB faqat bot tomonida tekshiriladi (/start):
    # Mini App'ga kirish tugmasi o'sha tekshiruvdan keyin beriladi, shuning
    # uchun ilova ichida yana to'sib turish foydalanuvchini ikki marta
    # to'xtatardi. Qarang: app/bot/middlewares.py
    tg_user = result["user"]
    return await get_or_create_user(session, tg_user["id"], tg_user.get("username"))


@router.get("/me", response_model=ProfileOut)
async def get_me(user: User = Depends(get_current_user)) -> ProfileOut:
    return ProfileOut(
        ui_language=user.ui_language.value,
        degree_level=user.degree_level.value if user.degree_level else None,
        major=user.major,
        gpa_raw=float(user.gpa_raw) if user.gpa_raw is not None else None,
        gpa_scale=user.gpa_scale.value if user.gpa_scale else None,
        budget_max=float(user.budget_max) if user.budget_max is not None else None,
        budget_currency=user.budget_currency,
        age=user.age,
        target_country_ids=[c.id for c in user.target_countries],
        language_certificates=[
            LanguageCertOut(type=c.type.value, score=float(c.score)) for c in user.language_certificates
        ],
    )


@router.patch("/me", response_model=ProfileOut)
async def update_me(
    payload: ProfileIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    if payload.ui_language is not None:
        try:
            user.ui_language = UiLanguage(payload.ui_language)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Noto'g'ri til") from exc

    if payload.degree_level is not None:
        try:
            user.degree_level = DegreeLevel(payload.degree_level)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Noto'g'ri daraja") from exc

    if payload.major is not None:
        user.major = payload.major.strip() or None

    if payload.gpa_raw is not None and payload.gpa_scale is not None:
        try:
            user.gpa_scale = GpaScale(payload.gpa_scale)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Noto'g'ri GPA shkalasi") from exc
        user.gpa_raw = payload.gpa_raw

    if payload.budget_max is not None:
        user.budget_max = payload.budget_max
        user.budget_currency = "USD"

    if payload.age is not None:
        user.age = payload.age

    await session.commit()

    if payload.target_country_ids is not None:
        await set_target_countries(session, user, payload.target_country_ids)

    if payload.language_cert_type is not None and payload.language_cert_score is not None:
        try:
            cert_type = LanguageCertType(payload.language_cert_type)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Noto'g'ri sertifikat turi") from exc
        await upsert_language_certificate(session, user, cert_type, payload.language_cert_score)

    # session'da expire_on_commit=False bo'lgani uchun `user`dagi allaqachon
    # yuklangan relationship'lar (target_countries/language_certificates)
    # commit'lardan keyin o'zi yangilanmaydi — javobdan oldin qo'lda yangilaymiz.
    await session.refresh(user, attribute_names=["target_countries", "language_certificates"])
    return await get_me(user)


@router.get("/gpa/convert", response_model=GpaConvertOut)
async def gpa_convert(value: float, scale: str) -> GpaConvertOut:
    try:
        gpa_scale = GpaScale(scale)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Noto'g'ri GPA shkalasi") from exc

    result = convert_gpa(value, gpa_scale)
    return GpaConvertOut(
        us4=result.us4,
        ects=result.ects,
        bavarian=result.bavarian,
        disclaimer=(
            "Bu — taxminiy hisob-kitob. Yakuniy GPA'ni universitet yoki tan olish idorasi "
            "(WES, Uni-Assist, ANABIN) belgilaydi. Rasmiy ariza uchun shu raqamga to'liq tayanmang."
        ),
    )


@router.get("/countries", response_model=list[CountryOut])
async def list_countries(session: AsyncSession = Depends(get_session)) -> list[CountryOut]:
    countries = (await session.execute(select(Country).order_by(Country.name_uz))).scalars().all()
    return [
        CountryOut(id=c.id, name_uz=c.name_uz, name_ru=c.name_ru, name_en=c.name_en, iso_code=c.iso_code)
        for c in countries
    ]


@router.get("/majors", response_model=list[str])
async def list_majors(
    degree_level: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Katalogda mavjud yo'nalishlar ro'yxati.

    Profilda foydalanuvchi yo'nalishni qo'lda yozmaydi — shu ro'yxatdan
    tanlaydi. Aks holda "Kompyuter injiniringi" kabi erkin matn hech qaysi
    dasturga to'g'ri kelmay, moslik qidiruvi bo'sh natija berardi.
    """
    stmt = select(distinct(Program.field_of_study)).order_by(Program.field_of_study)
    if degree_level:
        try:
            stmt = stmt.where(Program.degree_level == DegreeLevel(degree_level))
        except ValueError:
            pass
    return list((await session.execute(stmt)).scalars().all())


@router.get("/scholarships", response_model=list[ScholarshipOut])
async def list_scholarships(
    country_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ScholarshipOut]:
    """Davlat stipendiyalari — dasturga bog'liq bo'lmagan holda.

    `country_id` berilsa, faqat shu davlatga tegishli grantlar qaytariladi.
    """
    stmt = (
        select(Scholarship)
        .options(
            selectinload(Scholarship.countries),
            selectinload(Scholarship.deadlines),
        )
        .order_by(Scholarship.name)
    )
    if country_id is not None:
        stmt = stmt.where(Scholarship.countries.any(Country.id == country_id))

    scholarships = (await session.execute(stmt)).scalars().all()

    now = datetime.now(UTC)
    output = []
    for scholarship in scholarships:
        upcoming = [d for d in scholarship.deadlines if d.date_utc >= now]
        candidates = upcoming or list(scholarship.deadlines)
        nearest = min(candidates, key=lambda d: d.date_utc) if candidates else None

        output.append(
            ScholarshipOut(
                id=scholarship.id,
                name=scholarship.name,
                description=scholarship.description,
                coverage_type=scholarship.coverage_type.value,
                coverage_percent=scholarship.coverage_percent,
                stipend_amount=(
                    float(scholarship.stipend_amount)
                    if scholarship.stipend_amount is not None
                    else None
                ),
                currency=scholarship.currency,
                extras_flight=scholarship.extras_flight,
                extras_insurance=scholarship.extras_insurance,
                extras_dormitory=scholarship.extras_dormitory,
                extras_language_course=scholarship.extras_language_course,
                citizenship_eligible=scholarship.citizenship_eligible,
                countries=[
                    CountryOut(
                        id=c.id,
                        name_uz=c.name_uz,
                        name_ru=c.name_ru,
                        name_en=c.name_en,
                        iso_code=c.iso_code,
                    )
                    for c in scholarship.countries
                ],
                age_limit=scholarship.age_limit,
                university_choice=scholarship.university_choice.value,
                application_linked_to_program=scholarship.application_linked_to_program,
                source_url=scholarship.source_url,
                nearest_deadline=format_tashkent(nearest.date_utc) if nearest else None,
                nearest_deadline_days_left=(
                    (nearest.date_utc.date() - now.date()).days if nearest else None
                ),
                deadlines=[
                    ScholarshipDeadlineOut(
                        type=d.type.value,
                        date=format_tashkent(d.date_utc),
                        days_left=(d.date_utc.date() - now.date()).days,
                        intake_term=d.intake_term,
                    )
                    for d in sorted(scholarship.deadlines, key=lambda d: d.date_utc)
                ],
            )
        )
    return output


@router.get("/match", response_model=list[MatchProgramOut])
async def get_matches(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[MatchProgramOut]:
    results = await find_matches(session, user)
    saved_ids = {sp.program_id for sp in user.saved_programs}

    output = []
    for result in results:
        if result.level == MatchLevel.RED:
            continue
        program = result.program
        output.append(
            MatchProgramOut(
                id=program.id,
                name=program.name,
                abbreviation=program.abbreviation,
                university=program.university.name,
                country=program.university.country.name_uz,
                degree_level=program.degree_level.value,
                level=result.level.value,
                missing=result.missing,
                saved=program.id in saved_ids,
            )
        )
    return output


@router.post("/saved/{program_id}", status_code=201)
async def save_program(
    program_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(SavedProgram).where(
        SavedProgram.user_id == user.id, SavedProgram.program_id == program_id
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        program_exists = await session.get(Program, program_id)
        if program_exists is None:
            raise HTTPException(status_code=404, detail="Dastur topilmadi")
        session.add(
            SavedProgram(
                user_id=user.id,
                program_id=program_id,
                status=SavedProgramStatus.PLANNING,
                reminders_active=True,
            )
        )
        await session.commit()
    return {"saved": True}


@router.get("/saved", response_model=list[SavedOut])
async def list_saved(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[SavedOut]:
    stmt = (
        select(SavedProgram)
        .where(SavedProgram.user_id == user.id)
        .options(
            selectinload(SavedProgram.program)
            .selectinload(Program.university)
            .selectinload(University.country),
            selectinload(SavedProgram.program).selectinload(Program.deadlines),
        )
        .order_by(SavedProgram.created_at.desc())
    )
    saved_programs = (await session.execute(stmt)).scalars().all()

    output = []
    for saved in saved_programs:
        program = saved.program
        now = datetime.now(UTC)
        upcoming = [d for d in program.deadlines if d.date_utc >= now]
        candidates = upcoming or list(program.deadlines)
        nearest = min(candidates, key=lambda d: d.date_utc) if candidates else None
        days_left = (nearest.date_utc.date() - now.date()).days if nearest else None

        output.append(
            SavedOut(
                id=saved.id,
                program_id=program.id,
                program_name=program.name,
                university=program.university.name,
                country=program.university.country.name_uz,
                status=saved.status.value,
                reminders_active=saved.reminders_active,
                nearest_deadline=format_tashkent(nearest.date_utc) if nearest else None,
                nearest_deadline_days_left=days_left,
            )
        )
    return output


@router.patch("/saved/{saved_id}")
async def update_saved_status(
    saved_id: int,
    payload: SavedStatusIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(SavedProgram).where(SavedProgram.id == saved_id, SavedProgram.user_id == user.id)
    saved = (await session.execute(stmt)).scalar_one_or_none()
    if saved is None:
        raise HTTPException(status_code=404, detail="Topilmadi")

    try:
        saved.status = SavedProgramStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Noto'g'ri holat") from exc

    if saved.status == SavedProgramStatus.APPLIED:
        saved.reminders_active = False

    await session.commit()
    return {"status": saved.status.value}


@router.delete("/saved/{saved_id}")
async def delete_saved(
    saved_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = select(SavedProgram).where(SavedProgram.id == saved_id, SavedProgram.user_id == user.id)
    saved = (await session.execute(stmt)).scalar_one_or_none()
    if saved is not None:
        await session.delete(saved)
        await session.commit()
    return {"deleted": True}
