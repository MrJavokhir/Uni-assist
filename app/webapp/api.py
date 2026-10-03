import logging
from datetime import UTC, datetime
from decimal import Decimal
from html import escape

from aiogram import Bot
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import (
    INSTRUCTION_LANGUAGES,
    AdmissionService,
    Country,
    DegreeLevel,
    Field,
    GpaScale,
    LanguageCertType,
    Program,
    SavedProgram,
    SavedProgramStatus,
    Scholarship,
    ServiceKind,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceSlot,
    UiLanguage,
    University,
    UniversityRankRange,
    User,
)
from app.db.session import get_session
from app.services import booking_service, kit_service, payment_service, referral_service
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
    FeedbackIn,
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
    ServiceDeliveryResult,
    ServiceOut,
    ServiceRequestIn,
    ServiceRequestResult,
    SlotOut,
)

logger = logging.getLogger(__name__)

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


def _localized(record: object, field: str, lang: str) -> str | None:
    """`<field>`, `<field>_ru`, `<field>_en` dan foydalanuvchi tilidagisi.

    Asosiy ustun o'zbekcha; tarjimasi bo'sh bo'lsa o'zbekchasiga qaytadi —
    bo'sh joy ko'rsatgandan ko'ra tushunarli matn yaxshiroq.
    """
    if lang in ("ru", "en"):
        translated = getattr(record, f"{field}_{lang}", None)
        if translated:
            return translated
    return getattr(record, field)


def _localized_uz(record: object, field: str, lang: str) -> str | None:
    """Uchala tili ham qo'shimchali ustunlar uchun til tanlash.

    `_localized()` dan farqi: u asosiy ustunni QO'SHIMCHASIZ deb hisoblaydi
    (`Program.notes` + `notes_ru`/`notes_en`). Ma'lumotnoma jadvallarida esa
    o'zbekchasi ham qo'shimchali bo'ladi (`Field.name_uz` kabi) — u yerda
    `_localized()` mavjud bo'lmagan `record.name` ni so'rab AttributeError
    beradi.
    """
    if lang in ("ru", "en"):
        translated = getattr(record, f"{field}_{lang}", None)
        if translated:
            return translated
    return getattr(record, f"{field}_uz")


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


# Bot foydalanuvchi nomi Telegram'ning `initDataUnsafe` da YO'Q, shuning
# uchun serverdan aniqlanadi. Jarayon davomida o'zgarmaydi — bir marta
# so'ralib keshlanadi, aks holda har bir /me so'rovida Telegram'ga
# murojaat qilinardi.
_bot_username: str | None = None
_bot_username_checked = False


async def _get_bot_username() -> str | None:
    global _bot_username, _bot_username_checked
    if _bot_username_checked:
        return _bot_username
    _bot_username_checked = True
    if not settings.bot_token:
        return None
    bot = Bot(token=settings.bot_token)
    try:
        me = await bot.get_me()
        _bot_username = me.username
    except Exception:
        logger.exception("Bot foydalanuvchi nomini aniqlab bo'lmadi")
    finally:
        await bot.session.close()
    return _bot_username


async def _profile_out(session: AsyncSession, user: User) -> ProfileOut:
    """Profil javobi. Valyuta to'lov sozlamalaridan olinadi — balans va
    narxlar hamma joyda bir xil valyutada ko'rsatilishi uchun."""
    settings_row = await payment_service.get_settings(session)
    bot_username = await _get_bot_username()
    return ProfileOut(
        balance=float(user.balance or 0),
        balance_currency=settings_row.currency,
        is_blocked=bool(user.is_blocked),
        bot_username=bot_username,
        referral_link=referral_service.build_link(bot_username, user.telegram_id),
        referral_bonus=float(settings_row.referral_bonus or 0),
        referral_count=await referral_service.count_invited(session, user),
        ui_language=user.ui_language.value,
        degree_level=user.degree_level.value if user.degree_level else None,
        field_id=user.field_id,
        gpa_raw=float(user.gpa_raw) if user.gpa_raw is not None else None,
        gpa_scale=user.gpa_scale.value if user.gpa_scale else None,
        university_rank_range=(
            user.university_rank_range.value if user.university_rank_range else None
        ),
        application_fee_ok=user.application_fee_ok,
        study_language=user.study_language,
        target_country_ids=[c.id for c in user.target_countries],
        language_certificates=[
            LanguageCertOut(type=c.type.value, score=float(c.score)) for c in user.language_certificates
        ],
    )


@router.get("/me", response_model=ProfileOut)
async def get_me(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> ProfileOut:
    return await _profile_out(session, user)


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

    # Bo'sh satr = "farqi yo'q"; yuborilmasa o'zgarmaydi.
    if payload.study_language is not None:
        if payload.study_language and payload.study_language not in INSTRUCTION_LANGUAGES:
            # Ro'yxatdan tashqari qiymat hech bir dasturga to'g'ri kelmaydi
            # va filtr jimgina bo'sh ro'yxat qaytarardi.
            raise HTTPException(status_code=422, detail="Noto'g'ri o'qish tili")
        user.study_language = payload.study_language or None

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
    return await _profile_out(session, user)


# Qidiruvni chegaralaydigan maydonlar. "Filtrni tozalash" AYNAN shu
# ro'yxat bo'yicha ishlaydi.
#
# Ilgari har biri qo'lda yozilgan edi va o'qish tili qo'shilganda u
# tozalashga tushmay qolgandi: foydalanuvchi "Filtrni tozalash" bossa ham
# profil bo'shamas, ilova esa filtr qo'yilgan holatda qolaverardi — ya'ni
# "profilni to'ldiring" taklifi boshqa chiqmasdi.
RESETTABLE_FILTER_FIELDS = (
    "degree_level",
    "field_id",
    "gpa_raw",
    "gpa_scale",
    "university_rank_range",
    "application_fee_ok",
    "study_language",
)


@router.post("/me/reset", response_model=ProfileOut)
async def reset_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    """Profilni tozalaydi — saqlangan dasturlarga tegmaydi.

    Interfeys tili ham saqlanib qoladi: uni tozalash foydalanuvchini birdan
    boshqa tilga o'tkazib yuborardi.
    """
    for field_name in RESETTABLE_FILTER_FIELDS:
        setattr(user, field_name, None)

    for certificate in list(user.language_certificates):
        await session.delete(certificate)
    await session.commit()

    await set_target_countries(session, user, [])
    await session.refresh(user, attribute_names=["target_countries", "language_certificates"])
    return await _profile_out(session, user)


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


@router.get("/languages", response_model=list[str])
async def list_languages(session: AsyncSession = Depends(get_session)) -> list[str]:
    """Katalogda HAQIQATAN uchraydigan o'qish tillari.

    To'liq ro'yxat (`INSTRUCTION_LANGUAGES`) emas: unda hozircha birorta
    dastur yo'q tillar ham bor va ularni tanlagan odam bo'sh ro'yxat
    ko'rardi. Nomlarni Mini App o'zi tarjima qiladi (app.js: LANGUAGE_NAMES),
    shuning uchun bu yerda kanonik qiymatlar qaytariladi.
    """
    stmt = (
        select(Program.language_of_instruction)
        .distinct()
        .order_by(Program.language_of_instruction)
    )
    values = (await session.execute(stmt)).scalars().all()
    # Ro'yxatda yo'q qiymat (eski ma'lumot) filtrda tanlansa, PATCH /me uni
    # rad etardi — shuning uchun bu yerda ham chiqarib tashlanadi.
    return [value for value in values if value in INSTRUCTION_LANGUAGES]


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
        # Mashhur grantlar tepada: alifbo tartibi yolg'iz o'zi yomon edi —
        # ro'yxat "ADB-Japan" bilan boshlanib, o'rtasini 27 ta Erasmus Mundus
        # dasturi egallardi. Teng `sort_order` da alifbo tartibi saqlanadi.
        .order_by(Scholarship.sort_order, Scholarship.name)
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
                universities_text=_localized(
                    scholarship, "universities_text", user.ui_language.value
                ),
                selected_by=_localized(scholarship, "selected_by", user.ui_language.value),
                requirements_text=_localized(
                    scholarship, "requirements_text", user.ui_language.value
                ),
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


# ============ Admission Kit ============
#
# Xizmatlar katalogi bazada turadi va adminkadan boshqariladi (matn, narx,
# tartib, faollik). Shuning uchun matnlar SERVER tomonida foydalanuvchi
# tiliga o'giriladi — Mini App'dagi lug'at bu yerda yordam bera olmaydi.
#
# Xizmatning turi `AdmissionService.kind` maydonida:
#   FILE     -> narx balansdan yechiladi va PDF botda yuboriladi;
#   REQUEST  -> narx yechiladi, keyin admin foydalanuvchi bilan bog'lanadi.
#               `requires_booking` yoqilgan bo'lsa (1:1 mentor), avval
#               bo'sh vaqtlardan biri tanlanadi va band qilinadi.
#
# Qulf SERVERDA tekshiriladi. Ilovadagi qulf faqat ko'rinish: fayl berish
# oldidan egalik har safar qaytadan so'raladi.


def _slot_label(slot: ServiceSlot | None, lang: str) -> str | None:
    """Band qilingan vaqtning bir qatorlik ko'rinishi: "05.10.2026, dushanba 14:00"."""
    if slot is None:
        return None
    date_label, time_label = booking_service.labels(slot, lang)
    return f"{date_label} {time_label}"


@router.get("/services", response_model=list[ServiceOut])
async def list_services(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[ServiceOut]:
    stmt = (
        select(AdmissionService)
        .where(AdmissionService.is_active.is_(True))
        .order_by(AdmissionService.sort_order, AdmissionService.id)
    )
    services = (await session.execute(stmt)).scalars().all()

    requested_rows = (
        await session.execute(
            select(ServiceRequest.service_id).where(ServiceRequest.user_id == user.id)
        )
    ).scalars().all()
    requested = set(requested_rows)

    # Bo'sh vaqtlar bir so'rovda sanaladi: har qator uchun alohida
    # so'rov yuborish ro'yxatni sekinlashtirardi.
    slot_counts = await booking_service.free_counts(session)

    lang = user.ui_language.value
    return [
        ServiceOut(
            id=service.id,
            code=service.code,
            title=_localized_uz(service, "title", lang),
            description=_localized_uz(service, "description", lang),
            price_amount=float(service.price_amount) if service.price_amount is not None else None,
            price_currency=service.price_currency,
            price_note=_localized_uz(service, "price_note", lang),
            kind=service.kind.value,
            requested=service.id in requested,
            # `service.file` modelda selectin bilan yuklanadi, baytlarsiz —
            # bu yerda faqat metama'lumot ishlatiladi.
            has_file=service.file is not None,
            file_name=service.file.filename if service.file else None,
            file_size=service.file.size_bytes if service.file else None,
            requires_booking=service.requires_booking,
            free_slots=slot_counts.get(service.id, 0),
            unlock_invites=service.unlock_invites,
        )
        for service in services
    ]


@router.get("/services/{service_id}/slots", response_model=list[SlotOut])
async def list_slots(
    service_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SlotOut]:
    """Xizmatning bo'sh uchrashuv vaqtlari.

    Alohida endpoint: vaqtlar tez o'zgaradi (boshqa birov band qilishi
    mumkin), shuning uchun ular xizmatlar ro'yxati bilan birga emas,
    foydalanuvchi tanlash oynasini ochganda o'qiladi.
    """
    service = await session.get(AdmissionService, service_id)
    if service is None or not service.is_active:
        raise HTTPException(status_code=404, detail="Xizmat topilmadi")

    lang = user.ui_language.value
    slots = await booking_service.free_slots(session, service_id)
    result = []
    for slot in slots:
        date_label, time_label = booking_service.labels(slot, lang)
        result.append(
            SlotOut(
                id=slot.id,
                date_label=date_label,
                time_label=time_label,
                duration_minutes=slot.duration_minutes,
                note=slot.note,
            )
        )
    return result


@router.post("/services/{service_id}/request", response_model=ServiceRequestResult, status_code=201)
async def request_service(
    service_id: int,
    payload: ServiceRequestIn | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ServiceRequestResult:
    service = await session.get(AdmissionService, service_id)
    if service is None or not service.is_active:
        raise HTTPException(status_code=404, detail="Xizmat topilmadi")

    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Hisobingiz bloklangan")

    # Ikki marta bosilsa yangi yozuv YARATILMAYDI va pul QAYTA YECHILMAYDI.
    # Tugma bosilgandan keyin o'chsa ham, tarmoq uzilib qayta yuborilsa ham
    # foydalanuvchidan ikki marta olinmasligi kerak.
    existing = (
        await session.execute(
            select(ServiceRequest).where(
                ServiceRequest.user_id == user.id, ServiceRequest.service_id == service_id
            )
        )
    ).scalar_one_or_none()
    has_file = service.file is not None
    is_file_service = service.kind == ServiceKind.FILE

    if is_file_service and not has_file:
        # Fayl xizmati, lekin PDF hali yuklanmagan. Pul olib, berishga
        # narsa bo'lmasligi kerak — ilova bunday xizmatni "tez orada" deb
        # ko'rsatadi, bu esa o'sha qoidaning server tomondagi nusxasi.
        raise HTTPException(status_code=409, detail="Qo'llanma hali tayyor emas")

    if existing is not None:
        # Takroriy bosish: yangi vaqt band qilinmaydi va pul yechilmaydi.
        booked = existing.slot
        return ServiceRequestResult(
            requested=True,
            balance=float(user.balance or 0),
            has_file=has_file,
            slot_label=_slot_label(booked, user.ui_language.value) if booked else None,
        )

    needs_slot = service.requires_booking and not is_file_service
    slot_id = payload.slot_id if payload else None
    if needs_slot and slot_id is None:
        # Vaqtsiz pul olib bo'lmaydi: odam to'lab, keyin "qachon?" degan
        # savol bilan qolardi.
        raise HTTPException(status_code=400, detail="Uchrashuv vaqtini tanlang")

    # Do'st taklif qilib ochish. Tekshiruv SERVERDA: ilovadagi hisoblagich
    # faqat ko'rsatish uchun va unga ishonib bo'lmaydi.
    unlocked_by_invites = False
    if service.unlock_invites > 0:
        invites = await referral_service.count_invited(session, user)
        unlocked_by_invites = invites >= service.unlock_invites

    if unlocked_by_invites:
        # Pul yechilmaydi va balans tarixiga yozuv tushmaydi — yechim
        # bo'lmagan joyda nol summali qator faqat chalkashtirardi.
        # "Nega bepul oldi" degan savolga `unlocked_by_invites` javob beradi.
        new_balance = Decimal(str(user.balance or 0))
    else:
        try:
            new_balance = await payment_service.charge_service(session, user, service)
        except payment_service.InsufficientBalance as exc:
            # 402 Payment Required — Mini App shu kod bo'yicha "balansni
            # to'ldiring" oynasini ko'rsatadi.
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "insufficient_balance",
                    "needed": float(exc.needed),
                    "available": float(exc.available),
                },
            ) from exc

    service_request = ServiceRequest(
        user_id=user.id,
        service_id=service_id,
        # Fayl o'sha zahoti yetkaziladi, adminning qiladigan ishi
        # yo'q — yozuv darhol yopiq holatda. Adminka ro'yxatida faqat
        # qo'lda bajariladigan xizmatlar ko'rinadi.
        status=(ServiceRequestStatus.DONE if is_file_service else ServiceRequestStatus.NEW),
        unlocked_by_invites=unlocked_by_invites,
    )
    session.add(service_request)
    await session.flush()

    slot_label = None
    if needs_slot:
        try:
            await booking_service.claim(session, slot_id, service_id, service_request.id)
        except booking_service.SlotTaken as exc:
            # Hali COMMIT qilinmagan: xato bilan chiqish yechilgan pulni
            # ham, yaratilgan so'rovni ham bekor qiladi.
            raise HTTPException(status_code=409, detail={"error": "slot_taken"}) from exc
        slot = await session.get(ServiceSlot, slot_id)
        slot_label = _slot_label(slot, user.ui_language.value)

    await session.commit()
    return ServiceRequestResult(
        requested=True,
        balance=float(new_balance),
        charged=(
            None
            if unlocked_by_invites or service.price_amount is None
            else float(service.price_amount)
        ),
        has_file=has_file,
        slot_label=slot_label,
        unlocked_by_invites=unlocked_by_invites,
    )


@router.post("/services/{service_id}/deliver", response_model=ServiceDeliveryResult)
async def deliver_service_file(
    service_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ServiceDeliveryResult:
    """Sotib olingan PDF'ni bot suhbatiga yuboradi.

    Nega fayl HTTP orqali berilmaydi: Mini App Telegram'ning ichki
    brauzerida ochiladi, u yerda PDF yuklab olish iOS'da ishonchsiz. Bot
    orqali yuborilgan fayl esa suhbatda qoladi — istalgan vaqtda qayta
    ochiladi va ilova kerak bo'lmaydi.

    Sotib olish bilan YUBORISH ataylab ajratilgan: Telegram yuborishda
    xato bersa, xarid kuchda qoladi va foydalanuvchi tugmani qayta bosib
    faylni oladi.
    """
    service = await session.get(AdmissionService, service_id)
    if service is None or not service.is_active:
        raise HTTPException(status_code=404, detail="Xizmat topilmadi")

    if not await kit_service.owns(session, user, service_id):
        raise HTTPException(status_code=403, detail="Bu qo'llanma hali sotib olinmagan")

    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="Bot sozlanmagan")

    bot = Bot(token=settings.bot_token)
    try:
        row = await kit_service.deliver_file(session, bot, user, service)
    except Exception as exc:
        logger.exception("PDF yuborilmadi: xizmat=%s, user=%s", service_id, user.id)
        raise HTTPException(
            status_code=502, detail="Faylni yuborib bo'lmadi, birozdan keyin urinib ko'ring"
        ) from exc
    finally:
        await bot.session.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Bu xizmatda fayl yo'q")

    # Keshlangan Telegram file_id shu yerda saqlanadi.
    await session.commit()
    return ServiceDeliveryResult(sent=True, file_name=row.filename)


@router.post("/feedback", status_code=201)
async def send_feedback(
    payload: FeedbackIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Foydalanuvchi fikri — to'g'ridan-to'g'ri bot adminlariga yuboriladi.

    Alohida jadval ATAYLAB yaratilmadi: fikr o'qilib, javob berilishi kerak
    bo'lgan narsa. Adminkada yotganidan ko'ra Telegram'ga darhol yetgani
    foydaliroq.
    """
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Matn bo'sh")
    if len(text) > 2000:
        text = text[:2000] + "..."

    admin_ids = await payment_service.active_admin_ids(session)
    if not admin_ids or not settings.bot_token:
        logger.warning("Fikr yuborilmadi: bot adminlari ro'yxati yoki token bo'sh")
        return {"sent": False}

    bot = Bot(token=settings.bot_token)
    try:
        header = (
            "💬 <b>Yangi fikr</b>\n\n"
            f"👤 @{user.username or '—'}\n"
            f"🆔 <code>{user.telegram_id}</code>\n\n"
        )
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, header + escape(text), parse_mode="HTML")
            except Exception:
                logger.exception("Adminga fikr yetmadi: %s", admin_id)
    finally:
        await bot.session.close()
    return {"sent": True}
