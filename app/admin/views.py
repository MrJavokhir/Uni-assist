from sqladmin import ModelView
from sqladmin.filters import BooleanFilter, StaticValuesFilter
from starlette.requests import Request

from app.admin.filters import RelationshipFilter
from app.admin.formatters import (
    enum_label,
    format_bool,
    format_program_labels,
    format_university_wizard_link,
    format_verified_at,
)
from app.db.models import (
    Country,
    CoverageType,
    DeadlineType,
    DegreeLevel,
    LanguageCertType,
    Program,
    Report,
    ReportStatus,
    RequiredChannel,
    SavedProgramStatus,
    Scholarship,
    ScholarshipDeadline,
    UiLanguage,
    University,
    User,
)
from app.services.redis_client import redis_client
from app.services.subscription_service import clear_all_cache, derive_chat_id

# Enum ustunlar bazada `.value` sifatida saqlanadi (str_enum), shuning uchun
# filtr qiymatlari ham aynan shu qiymatlar bo'lishi kerak.
_DEGREE_LABELS = {
    DegreeLevel.BACHELOR: "Bakalavr",
    DegreeLevel.MASTER: "Magistratura",
    DegreeLevel.PHD: "PhD",
}
_COVERAGE_LABELS = {
    CoverageType.FULL: "To'liq",
    CoverageType.PARTIAL: "Qisman",
    CoverageType.CONTRACT_ONLY: "Faqat kontrakt",
}
_SAVED_STATUS_LABELS = {
    SavedProgramStatus.PLANNING: "Rejalashtirilmoqda",
    SavedProgramStatus.APPLIED: "Ariza berilgan",
    SavedProgramStatus.REJECTED: "Rad etilgan",
    SavedProgramStatus.ACCEPTED: "Qabul qilingan",
}
_REPORT_STATUS_LABELS = {
    ReportStatus.NEW: "Yangi",
    ReportStatus.REVIEWED: "Ko'rib chiqilgan",
    ReportStatus.RESOLVED: "Hal qilingan",
}
_DEADLINE_LABELS = {
    DeadlineType.APPLICATION_OPEN: "Ariza ochilishi",
    DeadlineType.APPLICATION_CLOSE: "Ariza yopilishi",
    DeadlineType.DOCUMENT: "Hujjat topshirish",
    DeadlineType.VISA: "Viza",
}
_UI_LANG_LABELS = {
    UiLanguage.UZ: "O'zbekcha",
    UiLanguage.RU: "Ruscha",
    UiLanguage.EN: "Inglizcha",
}
_CERT_LABELS = {
    LanguageCertType.IELTS: "IELTS",
    LanguageCertType.TOEFL: "TOEFL",
    LanguageCertType.DELE: "DELE",
    LanguageCertType.TESTDAF: "TestDaF",
    LanguageCertType.OTHER: "Boshqa",
}

# Ko'p jadvalda takrorlanadigan ustun nomlari
_COMMON_LABELS = {
    "id": "ID",
    "created_at": "Yaratilgan",
    "updated_at": "Yangilangan",
    "verified_at": "Tekshirilgan",
    "verified_by": "Kim tekshirgan",
    "source_url": "Manba havolasi",
}


def _choices(labels: dict) -> list[tuple[str, str]]:
    return [(member.value, label) for member, label in labels.items()]


def _labels(**extra: str) -> dict[str, str]:
    return {**_COMMON_LABELS, **extra}

# Yon menyuda `category` ATAYLAB ishlatilmaydi — hamma sahifa bitta tekis
# ro'yxatda turadi. Ochilib-yopiladigan bo'limlar har bir sahifaga yetib
# borish uchun ortiqcha bosish talab qilardi.
#
# Dastur talablari/xarajatlari/muddatlari uchun alohida sahifa YO'Q: ular
# "Universitet qo'shish" sehrgarida, o'z dasturi bilan bitta joyda kiritiladi.
# Foydalanuvchining sertifikat/test/saqlangan dasturlari ham alohida sahifa
# emas — ular "Foydalanuvchilar" sahifasining tafsilot ko'rinishida ko'rinadi.


class CountryAdmin(ModelView, model=Country):
    """Davlatlar — ma'lumotnoma ro'yxati.

    Yon menyuda KO'RSATILMAYDI: 14 ta davlat seed orqali kiritilgan va deyarli
    hech qachon tahrirlanmaydi, menyuda esa ortiqcha joy egallardi. Sahifa
    manzili ishlayveradi (/admin/country/list) va boshqa bo'limlardagi
    "Davlat" havolalari ham shu yerga olib keladi.
    """

    name = "Davlat"
    name_plural = "Davlatlar"
    icon = "fa-solid fa-flag"

    def is_visible(self, request: Request) -> bool:
        return False

    column_list = [Country.id, Country.name_uz, Country.name_ru, Country.name_en, Country.iso_code]
    column_searchable_list = [Country.name_uz, Country.name_ru, Country.name_en, Country.iso_code]
    column_sortable_list = [Country.name_uz, Country.iso_code]
    form_columns = [Country.name_uz, Country.name_ru, Country.name_en, Country.iso_code]
    column_labels = _labels(
        name_uz="Nomi (uz)", name_ru="Nomi (ru)", name_en="Nomi (en)", iso_code="ISO kodi"
    )


class UniversityAdmin(ModelView, model=University):
    name = "Universitet"
    name_plural = "Universitetlar"
    icon = "fa-solid fa-building-columns"

    # Universitetni tahrirlashning YAGONA yo'li — "Universitet qo'shish"
    # sehrgari (nom ustiga bosiladi). SQLAdmin'ning o'z ko'rish/tahrirlash
    # sahifalari o'chirilgan: ular faqat universitetning o'z maydonlarini
    # ko'rsatardi, dasturlarini esa yo'q — natijada admin qaysi biriga
    # bosishni bilmay chalkashardi.
    can_view_details = False
    can_edit = False

    column_list = [
        University.id,
        University.name,
        University.country,
        University.city,
        University.website,
    ]
    column_details_list = [
        University.id,
        University.name,
        University.country,
        University.city,
        University.website,
        University.timezone,
        University.programs,
    ]
    column_searchable_list = [University.name, University.city]
    column_sortable_list = [University.name, University.city]
    form_columns = [
        University.country,
        University.name,
        University.city,
        University.website,
        University.logo_url,
        University.timezone,
    ]
    form_args = {
        "logo_url": {
            "description": (
                "Bo'sh qoldiring — logotip rasmiy sayt domenidan avtomatik olinadi. "
                "Boshqa rasm kerak bo'lsagina to'g'ridan-to'g'ri havolasini kiriting."
            )
        }
    }
    column_labels = _labels(
        name="Nomi",
        country="Davlat",
        city="Shahar",
        website="Veb-sayt",
        logo_url="Logotip havolasi",
        timezone="Vaqt zonasi",
        programs="Dasturlar",
    )
    # Nom sehrgarga olib boradi: universitetni dasturlari bilan birga
    # tahrirlashning yagona joyi o'sha.
    column_formatters = {University.name: format_university_wizard_link}
    # Dasturlar ro'yxati faqat tafsilot sahifasida — ro'yxatda to'liq nomlar
    # ustunga sig'maydi va jadvalni o'qib bo'lmay qoladi.
    column_formatters_detail = {University.programs: format_program_labels}


class ProgramAdmin(ModelView, model=Program):
    name = "Dastur"
    name_plural = "Dasturlar"
    icon = "fa-solid fa-graduation-cap"

    column_list = [
        Program.id,
        Program.university,
        Program.name,
        Program.abbreviation,
        Program.degree_level,
        Program.field_of_study,
        Program.intake_term,
        Program.verified_at,
    ]
    column_details_list = [
        Program.id,
        Program.university,
        Program.name,
        Program.abbreviation,
        Program.degree_level,
        Program.field_of_study,
        Program.language_of_instruction,
        Program.duration_years,
        Program.intake_term,
        Program.notes,
        Program.requirement,
        Program.cost,
        Program.deadlines,
        Program.scholarships,
        Program.source_url,
        Program.verified_at,
        Program.verified_by,
    ]
    # Qisqartma ham qidiriladi — talabalar "MBA", "LLM" deb izlashadi.
    column_searchable_list = [Program.name, Program.abbreviation, Program.field_of_study]
    column_sortable_list = [Program.name, Program.verified_at]
    column_filters = [
        StaticValuesFilter(Program.degree_level, values=_choices(_DEGREE_LABELS), title="Daraja")
    ]
    form_columns = [
        Program.university,
        Program.name,
        Program.abbreviation,
        Program.degree_level,
        Program.field_of_study,
        Program.language_of_instruction,
        Program.duration_years,
        Program.intake_term,
        Program.notes,
        Program.notes_ru,
        Program.notes_en,
        Program.source_url,
        Program.verified_at,
        Program.verified_by,
    ]
    form_args = {
        "abbreviation": {"description": "Diplom qisqartmasi: MBA, LLM, B.Sc., M.Eng."},
        "notes": {"description": "Asosiy til. Tarjimalar bo'sh bo'lsa Mini App shuni ko'rsatadi."},
        "notes_ru": {"description": "Bo'sh qoldirilsa o'zbekchasi ko'rsatiladi."},
        "notes_en": {"description": "Bo'sh qoldirilsa o'zbekchasi ko'rsatiladi."},
    }
    column_labels = _labels(
        name="Dastur nomi",
        abbreviation="Qisqartma",
        university="Universitet",
        degree_level="Daraja",
        field_of_study="Yo'nalish",
        language_of_instruction="O'qitish tili",
        duration_years="Davomiyligi (yil)",
        intake_term="Qabul davri",
        notes="Izoh (o'zbekcha)",
        notes_ru="Izoh (ruscha)",
        notes_en="Izoh (inglizcha)",
        missing_fields="To'ldirilmagan maydonlar",
        requirement="Talablar",
        cost="Xarajat",
        deadlines="Muddatlar",
        scholarships="Grantlar",
    )
    column_formatters = {
        Program.verified_at: format_verified_at,
        Program.degree_level: enum_label(_DEGREE_LABELS),
    }
    column_formatters_detail = {
        Program.verified_at: format_verified_at,
        Program.degree_level: enum_label(_DEGREE_LABELS),
    }


class ScholarshipAdmin(ModelView, model=Scholarship):
    name = "Grant"
    name_plural = "Grantlar"
    icon = "fa-solid fa-hand-holding-dollar"

    column_list = [
        Scholarship.id,
        Scholarship.name,
        Scholarship.countries,
        Scholarship.coverage_type,
        Scholarship.citizenship_eligible,
        Scholarship.verified_at,
    ]
    column_details_list = [
        Scholarship.id,
        Scholarship.name,
        Scholarship.countries,
        Scholarship.description,
        Scholarship.coverage_type,
        Scholarship.coverage_percent,
        Scholarship.stipend_amount,
        Scholarship.currency,
        Scholarship.extras_flight,
        Scholarship.extras_insurance,
        Scholarship.extras_dormitory,
        Scholarship.extras_language_course,
        Scholarship.age_limit,
        Scholarship.citizenship_eligible,
        Scholarship.university_choice,
        Scholarship.application_linked_to_program,
        Scholarship.programs,
        Scholarship.deadlines,
        Scholarship.source_url,
        Scholarship.verified_at,
        Scholarship.verified_by,
    ]
    column_searchable_list = [Scholarship.name]
    column_sortable_list = [Scholarship.name, Scholarship.verified_at]
    column_filters = [
        RelationshipFilter(
            Scholarship.countries, Country, Country.name_uz, title="Davlat", parameter_name="country"
        ),
        StaticValuesFilter(
            Scholarship.coverage_type, values=_choices(_COVERAGE_LABELS), title="Qamrov"
        ),
        BooleanFilter(Scholarship.citizenship_eligible, title="O'zbekiston fuqarolari uchun"),
    ]
    form_columns = [
        Scholarship.name,
        Scholarship.countries,
        Scholarship.description,
        Scholarship.coverage_type,
        Scholarship.coverage_percent,
        Scholarship.stipend_amount,
        Scholarship.currency,
        Scholarship.extras_flight,
        Scholarship.extras_insurance,
        Scholarship.extras_dormitory,
        Scholarship.extras_language_course,
        Scholarship.age_limit,
        Scholarship.citizenship_eligible,
        Scholarship.university_choice,
        Scholarship.application_linked_to_program,
        Scholarship.programs,
        Scholarship.source_url,
        Scholarship.verified_at,
        Scholarship.verified_by,
    ]
    column_labels = _labels(
        name="Grant nomi",
        countries="Davlat",
        description="Tavsif",
        coverage_type="Qamrov turi",
        coverage_percent="Qamrov (%)",
        stipend_amount="Stipendiya",
        currency="Valyuta",
        extras_flight="Aviachipta",
        extras_insurance="Sug'urta",
        extras_dormitory="Yotoqxona",
        extras_language_course="Til kursi",
        age_limit="Yosh chegarasi",
        citizenship_eligible="O'zbekiston uchun ochiq",
        university_choice="Universitetni kim tanlaydi",
        application_linked_to_program="Alohida ariza kerak",
        programs="Dasturlar",
        deadlines="Muddatlar",
    )
    _scholarship_formatters = {
        Scholarship.verified_at: format_verified_at,
        Scholarship.coverage_type: enum_label(_COVERAGE_LABELS),
        Scholarship.citizenship_eligible: format_bool,
    }
    column_formatters = _scholarship_formatters
    column_formatters_detail = _scholarship_formatters


class ScholarshipDeadlineAdmin(ModelView, model=ScholarshipDeadline):
    name = "Grant muddati"
    name_plural = "Grant muddatlari"
    icon = "fa-solid fa-calendar-check"

    column_list = [
        ScholarshipDeadline.id,
        ScholarshipDeadline.scholarship,
        ScholarshipDeadline.type,
        ScholarshipDeadline.date_utc,
        ScholarshipDeadline.intake_term,
    ]
    column_sortable_list = [ScholarshipDeadline.date_utc]
    form_columns = [
        ScholarshipDeadline.scholarship,
        ScholarshipDeadline.type,
        ScholarshipDeadline.date_utc,
        ScholarshipDeadline.intake_term,
    ]
    column_labels = _labels(
        scholarship="Grant", type="Muddat turi", date_utc="Sana (UTC)", intake_term="Qabul davri"
    )
    column_formatters = {ScholarshipDeadline.type: enum_label(_DEADLINE_LABELS)}
    column_formatters_detail = {ScholarshipDeadline.type: enum_label(_DEADLINE_LABELS)}


class UserAdmin(ModelView, model=User):
    name = "Foydalanuvchi"
    name_plural = "Foydalanuvchilar"
    icon = "fa-solid fa-user"
    can_create = False

    column_list = [
        User.id,
        User.telegram_id,
        User.username,
        User.ui_language,
        User.degree_level,
        User.major,
        User.created_at,
    ]
    column_details_list = [
        User.id,
        User.telegram_id,
        User.username,
        User.ui_language,
        User.gpa_raw,
        User.gpa_scale,
        User.degree_level,
        User.major,
        User.budget_max,
        User.budget_currency,
        User.age,
        User.university_rank_range,
        User.application_fee_ok,
        User.target_countries,
        User.language_certificates,
        User.other_tests,
        User.saved_programs,
        User.created_at,
    ]
    column_searchable_list = [User.username]
    form_columns = [
        User.username,
        User.ui_language,
        User.gpa_raw,
        User.gpa_scale,
        User.degree_level,
        User.major,
        User.budget_max,
        User.budget_currency,
        User.age,
        User.university_rank_range,
        User.application_fee_ok,
        User.target_countries,
    ]
    column_labels = _labels(
        telegram_id="Telegram ID",
        username="Username",
        ui_language="Til",
        gpa_raw="GPA",
        gpa_scale="GPA tizimi",
        degree_level="Daraja",
        major="Yo'nalish",
        budget_max="Byudjet",
        budget_currency="Valyuta",
        age="Yosh",
        university_rank_range="Universitet reytingi",
        application_fee_ok="Ariza to'loviga rozi",
        target_countries="Maqsad davlatlar",
        language_certificates="Til sertifikatlari",
        other_tests="Boshqa testlar",
        saved_programs="Saqlangan dasturlar",
    )
    _user_formatters = {
        User.ui_language: enum_label(_UI_LANG_LABELS),
        User.degree_level: enum_label(_DEGREE_LABELS),
    }
    column_formatters = _user_formatters
    column_formatters_detail = _user_formatters

class ReportAdmin(ModelView, model=Report):
    """Foydalanuvchidan kelgan 'ma'lumot noto'g'ri' signallari."""

    name = "Signal"
    name_plural = "Ma'lumot noto'g'ri signallari"
    icon = "fa-solid fa-triangle-exclamation"
    can_create = False

    column_list = [
        Report.id,
        Report.program,
        Report.scholarship,
        Report.user,
        Report.comment,
        Report.status,
        Report.created_at,
    ]
    column_default_sort = [(Report.created_at, True)]
    column_filters = [
        StaticValuesFilter(Report.status, values=_choices(_REPORT_STATUS_LABELS), title="Holat")
    ]
    form_columns = [Report.status]
    column_labels = _labels(
        program="Dastur",
        scholarship="Grant",
        user="Kim yubordi",
        comment="Izoh",
        status="Holat",
    )
    column_formatters = {Report.status: enum_label(_REPORT_STATUS_LABELS)}
    column_formatters_detail = {Report.status: enum_label(_REPORT_STATUS_LABELS)}


class RequiredChannelAdmin(ModelView, model=RequiredChannel):
    """Botdan foydalanish uchun majburiy obuna kanallari.

    Bu yerga kanal havolasini kiritish kifoya — ochiq kanallar uchun
    `chat_id` (@username) havoladan avtomatik aniqlanadi. Yopiq kanallarda
    (t.me/+...) havoladan username chiqmaydi, shuning uchun raqamli chat_id
    (masalan -1001234567890) ni qo'lda kiritish kerak.

    MUHIM: tekshiruv ishlashi uchun bot kanalda administrator bo'lishi shart.
    """

    name = "Majburiy kanal"
    name_plural = "Majburiy kanallar"
    icon = "fa-solid fa-bullhorn"

    column_list = [
        RequiredChannel.id,
        RequiredChannel.title,
        RequiredChannel.invite_url,
        RequiredChannel.chat_id,
        RequiredChannel.is_active,
    ]
    column_searchable_list = [RequiredChannel.title, RequiredChannel.invite_url]
    column_default_sort = [(RequiredChannel.id, False)]
    column_filters = [BooleanFilter(RequiredChannel.is_active, title="Faol")]
    form_columns = [
        RequiredChannel.title,
        RequiredChannel.invite_url,
        RequiredChannel.chat_id,
        RequiredChannel.is_active,
    ]
    column_labels = _labels(
        title="Kanal nomi",
        invite_url="Kanal havolasi",
        chat_id="Chat ID (@username yoki -100...)",
        is_active="Faol",
    )
    form_args = {
        "invite_url": {"description": "Masalan: https://t.me/uniassist_uz"},
        "chat_id": {
            "description": (
                "Bo'sh qoldiring — ochiq kanal uchun havoladan avtomatik olinadi. "
                "Yopiq kanal uchun raqamli ID kiriting (-1001234567890)."
            )
        },
        "is_active": {"description": "O'chirilsa, bu kanalga obuna talab qilinmaydi."},
    }
    column_formatters = {RequiredChannel.is_active: format_bool}
    column_formatters_detail = {RequiredChannel.is_active: format_bool}

    async def on_model_change(
        self, data: dict, model: RequiredChannel, is_created: bool, request: Request
    ) -> None:
        url = (data.get("invite_url") or "").strip()
        chat_id = (data.get("chat_id") or "").strip()

        if not chat_id:
            derived = derive_chat_id(url)
            if not derived:
                raise ValueError(
                    "Bu yopiq kanal havolasiga o'xshaydi — havoladan @username aniqlanmadi. "
                    "Iltimos, kanalning raqamli Chat ID sini (-100... ko'rinishida) kiriting."
                )
            chat_id = derived

        data["invite_url"] = url
        data["chat_id"] = chat_id

    async def after_model_change(
        self, data: dict, model: RequiredChannel, is_created: bool, request: Request
    ) -> None:
        # Kanallar ro'yxati o'zgardi — eski "obuna bo'lgan" keshi bekor qilinadi.
        await clear_all_cache(redis_client)

    async def after_model_delete(self, model: RequiredChannel, request: Request) -> None:
        await clear_all_cache(redis_client)
