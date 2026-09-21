from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Country,
    DegreeLevel,
    Field,
    GpaScale,
    LanguageCertType,
    Program,
    SavedProgram,
    SavedProgramStatus,
    Scholarship,
    UiLanguage,
    University,
    UniversityRankRange,
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
    FieldOut,
    GpaConvertOut,
    LanguageCertOut,
    MatchProgramOut,
    ProfileIn,
    ProfileOut,
    ProgramCostOut,
    ProgramDeadlineOut,
    ProgramDetailOut,
    ProgramRequirementOut,
    SavedOut,
    SavedStatusIn,
    ScholarshipDeadlineOut,
    ScholarshipOut,
)

router = APIRouter()


def _country_out(country: Country) -> CountryOut:
    return CountryOut(
        id=country.id,
        name_uz=country.name_uz,
        name_ru=country.name_ru,
        name_en=country.name_en,
        iso_code=country.iso_code,
    )


def _field_out(field: Field | None) -> FieldOut | None:
    if field is None:
        return None
    return FieldOut(
        id=field.id,
        code=field.code,
        name_uz=field.name_uz,
        name_ru=field.name_ru,
        name_en=field.name_en,
    )


def _localized_notes(program: Program, lang: str) -> str | None:
    """Erkin izohni foydalanuvchi tilida qaytaradi, bo'lmasa o'zbekchasini.

    `notes` ustuni o'zbekcha (asosiy til), `notes_ru`/`notes_en` esa tarjimalar.
    """
    by_lang = {"ru": program.notes_ru, "en": program.notes_en}
    return by_lang.get(lang) or program.notes


def _localized_description(scholarship: Scholarship, lang: str) -> str | None:
    """Grant tavsifini foydalanuvchi tilida, bo'lmasa o'zbekchasida."""
    by_lang = {"ru": scholarship.description_ru, "en": scholarship.description_en}
    return by_lang.get(lang) or scholarship.description


def _favicon(url: str | None) -> str | None:
    """Sayt manzilidan logotip havolasi (Google favicon xizmati)."""
    if not url:
        return None
    domain = url.split("//")[-1].split("/")[0].strip()
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128" if domain else None


def _scholarship_logo(scholarship: Scholarship) -> str | None:
    """Grant logotipi: admin kiritgani, bo'lmasa rasmiy sayt domenidan."""
    return scholarship.logo_url or _favicon(scholarship.source_url)


def _logo_url(university: University) -> str | None:
    """Universitet logotipi.

    Admin `logo_url` kiritgan bo'lsa — o'sha. Bo'lmasa rasmiy sayt domenidan
    Google favicon xizmati orqali avtomatik olinadi: shunda 78 ta universitet
    uchun ham qo'lda rasm yuklash shart emas. Rasm yuklanmasa Mini App
    universitet nomining bosh harflarini chizadi.
    """
    return university.logo_url or _favicon(university.website)


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
    return await get_or_create_user(
        session,
        tg_user["id"],
        tg_user.get("username"),
        language_code=tg_user.get("language_code"),
    )


@router.get("/me", response_model=ProfileOut)
async def get_me(user: User = Depends(get_current_user)) -> ProfileOut:
    return ProfileOut(
        ui_language=user.ui_language.value,
        degree_level=user.degree_level.value if user.degree_level else None,
        field_id=user.field_id,
        gpa_raw=float(user.gpa_raw) if user.gpa_raw is not None else None,
        gpa_scale=user.gpa_scale.value if user.gpa_scale else None,
        university_rank_range=(
            user.university_rank_range.value if user.university_rank_range else None
        ),
        application_fee_ok=user.application_fee_ok,
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

    if "field_id" in payload.model_fields_set:
        if payload.field_id is not None and await session.get(Field, payload.field_id) is None:
            raise HTTPException(status_code=422, detail="Noto'g'ri yo'nalish")
        user.field_id = payload.field_id

    if payload.gpa_raw is not None and payload.gpa_scale is not None:
        try:
            user.gpa_scale = GpaScale(payload.gpa_scale)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Noto'g'ri GPA shkalasi") from exc
        user.gpa_raw = payload.gpa_raw

    # Bo'sh satr = "farqi yo'q" (tanlov tozalanadi); yuborilmasa o'zgarmaydi.
    if payload.university_rank_range is not None:
        if payload.university_rank_range:
            try:
                user.university_rank_range = UniversityRankRange(payload.university_rank_range)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Noto'g'ri reyting oralig'i") from exc
        else:
            user.university_rank_range = None

    if payload.application_fee_ok is not None:
        user.application_fee_ok = payload.application_fee_ok

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


@router.post("/me/reset", response_model=ProfileOut)
async def reset_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    """Profilni tozalaydi — saqlangan dasturlarga tegmaydi.

    Interfeys tili ham saqlanib qoladi: uni tozalash foydalanuvchini birdan
    boshqa tilga o'tkazib yuborardi.
    """
    user.degree_level = None
    user.field_id = None
    user.gpa_raw = None
    user.gpa_scale = None
    user.university_rank_range = None
    user.application_fee_ok = None

    for certificate in list(user.language_certificates):
        await session.delete(certificate)
    await session.commit()

    await set_target_countries(session, user, [])
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
        uk=result.uk,
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


@router.get("/majors", response_model=list[FieldOut])
async def list_majors(
    degree_level: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[FieldOut]:
    """Profilda tanlash uchun yo'nalishlar (`fields` ma'lumotnomasidan).

    Faqat katalogda kamida bitta dasturi bor yo'nalishlar qaytadi (daraja
    berilsa — o'sha darajadagi dasturi borlari): bo'sh yo'nalishni tanlagan
    foydalanuvchi hech narsa topmay qolardi.
    """
    has_program = select(Program.id).where(Program.field_id == Field.id)
    if degree_level:
        try:
            has_program = has_program.where(Program.degree_level == DegreeLevel(degree_level))
        except ValueError:
            pass
    stmt = select(Field).where(has_program.exists()).order_by(Field.sort_order, Field.name_en)
    return [_field_out(f) for f in (await session.execute(stmt)).scalars().all()]


@router.get("/programs/{program_id}", response_model=ProgramDetailOut)
async def get_program(
    program_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProgramDetailOut:
    """Dastur kartasi bosilganda ochiladigan to'liq ma'lumot."""
    program = (
        await session.execute(
            select(Program)
            .options(
                selectinload(Program.university).selectinload(University.country),
                selectinload(Program.field),
                selectinload(Program.requirement),
                selectinload(Program.cost),
                selectinload(Program.deadlines),
            )
            .where(Program.id == program_id)
        )
    ).scalar_one_or_none()
    if program is None:
        raise HTTPException(status_code=404, detail="Dastur topilmadi")

    now = datetime.now(UTC)
    requirement = program.requirement
    cost = program.cost

    return ProgramDetailOut(
        id=program.id,
        name=program.name,
        abbreviation=program.abbreviation,
        university=program.university.name,
        university_website=program.university.website,
        university_logo=_logo_url(program.university),
        university_ranking=program.university.ranking,
        city=program.university.city,
        country=_country_out(program.university.country),
        degree_level=program.degree_level.value,
        field=_field_out(program.field),
        language_of_instruction=program.language_of_instruction,
        duration_years=float(program.duration_years),
        intake_term=program.intake_term,
        notes=_localized_notes(program, user.ui_language.value),
        missing_fields=list(program.missing_fields or []),
        required_documents=list(program.required_documents or []),
        has_scholarship=program.has_scholarship,
        scholarship_url=program.scholarship_url,
        has_application_fee=program.has_application_fee,
        application_fee_amount=(
            float(program.application_fee_amount)
            if program.application_fee_amount is not None
            else None
        ),
        application_fee_currency=program.application_fee_currency,
        requirements=[
            line.strip() for line in (program.requirements_text or "").splitlines() if line.strip()
        ],
        requirement=(
            ProgramRequirementOut(
                ielts_min=float(requirement.ielts_min)
                if requirement.ielts_min is not None
                else None,
                toefl_min=requirement.toefl_min,
                gre_required=requirement.gre_required,
                gre_min=requirement.gre_min,
                prereq_major=requirement.prereq_major,
            )
            if requirement
            else None
        ),
        cost=(
            ProgramCostOut(
                tuition_amount=float(cost.tuition_amount),
                currency=cost.currency,
                last_checked=cost.last_checked.isoformat(),
            )
            if cost
            else None
        ),
        deadlines=[
            ProgramDeadlineOut(
                type=d.type.value,
                date=format_tashkent(d.date_utc),
                days_left=(d.date_utc.date() - now.date()).days,
                intake_term=d.intake_term,
            )
            for d in sorted(program.deadlines, key=lambda d: d.date_utc)
        ],
        source_url=program.source_url,
        verified_at=program.verified_at.date().isoformat(),
        saved=any(sp.program_id == program.id for sp in user.saved_programs),
    )


@router.get("/scholarships", response_model=list[ScholarshipOut])
async def list_scholarships(
    country_id: int | None = None,
    user: User = Depends(get_current_user),
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
                description=_localized_description(scholarship, user.ui_language.value),
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
                logo=_scholarship_logo(scholarship),
                stipend_max=float(scholarship.stipend_max)
                if scholarship.stipend_max is not None
                else None,
                stipend_period=scholarship.stipend_period,
                ielts_min=float(scholarship.ielts_min)
                if scholarship.ielts_min is not None
                else None,
                toefl_min=scholarship.toefl_min,
                work_experience_years=scholarship.work_experience_years,
                degree_levels=list(scholarship.degree_levels or []),
                study_language=scholarship.study_language,
                duration_min_years=float(scholarship.duration_min_years)
                if scholarship.duration_min_years is not None
                else None,
                duration_max_years=float(scholarship.duration_max_years)
                if scholarship.duration_max_years is not None
                else None,
                selection_stages=scholarship.selection_stages,
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
                university_logo=_logo_url(program.university),
                country=_country_out(program.university.country),
                degree_level=program.degree_level.value,
                level=result.level.value,
                missing=result.missing,
                saved=program.id in saved_ids,
                tuition_amount=float(program.cost.tuition_amount) if program.cost else None,
                tuition_currency=program.cost.currency if program.cost else None,
                ielts_min=float(program.requirement.ielts_min)
                if program.requirement and program.requirement.ielts_min is not None
                else None,
                toefl_min=program.requirement.toefl_min if program.requirement else None,
                university_ranking=program.university.ranking,
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
                university_logo=_logo_url(program.university),
                country=_country_out(program.university.country),
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
