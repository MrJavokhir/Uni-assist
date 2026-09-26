from aiogram import Bot
from sqladmin import ModelView
from sqladmin.filters import BooleanFilter, StaticValuesFilter
from starlette.requests import Request
from wtforms import SelectField
from wtforms.validators import InputRequired

from app.admin.filters import DistinctValuesFilter, IsNullFilter, RelationshipFilter
from app.admin.formatters import (
    enum_label,
    format_bool,
    format_program_labels,
    format_program_wizard_link,
    format_ranking,
    format_scholarship_wizard_link,
    format_university_wizard_link,
    format_verified_at,
)
from app.config import settings
from app.db.models import (
    INSTRUCTION_LANGUAGES,
    AdmissionService,
    BalanceTransaction,
    BotAdmin,
    Country,
    CoverageType,
    DeadlineType,
    DegreeLevel,
    Field,
    LanguageCertType,
    Payment,
    PaymentSettings,
    PaymentStatus,
    Program,
    RequiredChannel,
    SavedProgramStatus,
    Scholarship,
    ScholarshipDeadline,
    ServiceRequest,
    ServiceRequestStatus,
    TransactionKind,
    UiLanguage,
    University,
    User,
)
from app.services.redis_client import redis_client
from app.services.subscription_service import (
    clear_all_cache,
    derive_chat_id,
    normalize_chat_id,
    verify_channel_access,
)

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
_PAYMENT_STATUS_LABELS = {
    PaymentStatus.AWAITING_RECEIPT: "Chek kutilmoqda",
    PaymentStatus.SUBMITTED: "Tekshiruvda",
    PaymentStatus.APPROVED: "Tasdiqlangan",
    PaymentStatus.REJECTED: "Rad etilgan",
}
_TRANSACTION_KIND_LABELS = {
    TransactionKind.TOPUP: "To'ldirish",
    TransactionKind.SERVICE: "Xizmat uchun",
    TransactionKind.ADJUSTMENT: "Qo'lda to'g'irlash",
}
_SERVICE_REQUEST_LABELS = {
    ServiceRequestStatus.NEW: "Yangi",
    ServiceRequestStatus.CONTACTED: "Bog'lanildi",
    ServiceRequestStatus.DONE: "Bajarildi",
    ServiceRequestStatus.CANCELLED: "Bekor qilindi",
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

# Yon menyu asosan TEKIS: ochilib-yopiladigan bo'limlar har bir sahifaga
# yetib borish uchun ortiqcha bosish talab qiladi.
#
# Istisno — bir-biriga bog'liq, doim ketma-ket ishlatiladigan bo'limlar.
# Ular menyuda alohida qator bo'lib, qolganlarini pastga surib yuborardi:
#   "To'lovlar"      — sozlama -> to'lov -> balans tarixi
#   "Admission Kit"  — xizmatlar -> ularga kelgan so'rovlar
# Qolgan hamma sahifa tekis ro'yxatda qoladi.
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


class FieldAdmin(ModelView, model=Field):
    """Yo'nalishlar ma'lumotnomasi — dastur va profil shu ro'yxatdan tanlaydi.

    `code` CSV import/eksportning kaliti: uni o'zgartirish eski CSV fayllarni
    buzadi. Yo'nalish o'chirilsa, unga bog'langan dasturlar "Yo'nalishi yo'q"
    filtriga tushadi (FK ON DELETE SET NULL).
    """

    name = "Yo'nalish"
    name_plural = "Yo'nalishlar"
    icon = "fa-solid fa-layer-group"

    column_list = [Field.id, Field.code, Field.name_uz, Field.name_ru, Field.name_en, Field.sort_order]
    column_searchable_list = [Field.code, Field.name_uz, Field.name_ru, Field.name_en]
    column_sortable_list = [Field.code, Field.name_uz, Field.sort_order]
    column_default_sort = [(Field.sort_order, False)]
    form_columns = [Field.code, Field.name_uz, Field.name_ru, Field.name_en, Field.sort_order]
    form_args = {
        "code": {
            "description": (
                "Lotin kichik harflar va _ (masalan cs_it). CSV import shu kod bilan ishlaydi — "
                "keyin o'zgartirmang."
            )
        },
        "sort_order": {"description": "Ro'yxatdagi o'rni: kichigi yuqorida."},
    }
    column_labels = _labels(
        code="Kod",
        name_uz="Nomi (uz)",
        name_ru="Nomi (ru)",
        name_en="Nomi (en)",
        sort_order="Tartib",
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
        University.ranking,
        University.website,
    ]
    column_details_list = [
        University.id,
        University.name,
        University.country,
        University.city,
        University.ranking,
        University.website,
        University.timezone,
        University.programs,
    ]
    column_searchable_list = [University.name, University.city]
    column_sortable_list = [University.name, University.city, University.ranking]
    column_filters = [
        RelationshipFilter(
            University.country, Country, Country.name_uz, title="Davlatlar", parameter_name="country"
        ),
    ]
    form_columns = [
        University.country,
        University.name,
        University.city,
        University.website,
        University.logo_url,
        University.timezone,
        University.ranking,
    ]
    form_args = {
        "ranking": {
            "description": "QS World University Rankings'dagi o'rni. Reytingda bo'lmasa bo'sh qoldiring."
        },
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
        ranking="Reyting (QS)",
        programs="Dasturlar",
    )
    # Nom sehrgarga olib boradi: universitetni dasturlari bilan birga
    # tahrirlashning yagona joyi o'sha.
    column_formatters = {
        University.name: format_university_wizard_link,
        University.ranking: format_ranking,
    }
    # Dasturlar ro'yxati faqat tafsilot sahifasida — ro'yxatda to'liq nomlar
    # ustunga sig'maydi va jadvalni o'qib bo'lmay qoladi.
    column_formatters_detail = {University.programs: format_program_labels}


class ProgramAdmin(ModelView, model=Program):
    name = "Dastur"
    name_plural = "Dasturlar"
    icon = "fa-solid fa-graduation-cap"

    # Tahrirlash universitet sehrgarida (dastur nomi o'sha yerga olib boradi):
    # oddiy forma til sertifikati, xarajat va muddatlarni tahrirlay olmaydi.
    can_edit = False

    column_list = [
        Program.id,
        Program.university,
        Program.name,
        Program.abbreviation,
        Program.degree_level,
        Program.field,
        Program.intake_term,
        Program.verified_at,
    ]
    column_details_list = [
        Program.id,
        Program.university,
        Program.name,
        Program.abbreviation,
        Program.degree_level,
        Program.field,
        Program.field_of_study_legacy,
        Program.language_of_instruction,
        Program.duration_years,
        Program.intake_term,
        Program.notes,
        Program.requirement,
        Program.required_documents,
        Program.requirements_text,
        Program.cost,
        Program.has_application_fee,
        Program.application_fee_amount,
        Program.application_fee_currency,
        Program.deadlines,
        Program.has_scholarship,
        Program.scholarship_url,
        Program.scholarships,
        Program.source_url,
        Program.verified_at,
        Program.verified_by,
    ]
    # Qisqartma ham qidiriladi — talabalar "MBA", "LLM" deb izlashadi.
    column_searchable_list = [Program.name, Program.abbreviation]
    column_sortable_list = [Program.name, Program.verified_at]
    column_filters = [
        DistinctValuesFilter(Program.name, title="Dasturlar"),
        StaticValuesFilter(Program.degree_level, values=_choices(_DEGREE_LABELS), title="Daraja"),
        # Migratsiyada ma'lumotnomaga mos kelmagan dasturlar — admin qo'lda
        # yo'nalish biriktiradi (eski qiymat tafsilotda ko'rinadi).
        IsNullFilter(
            Program.field_id,
            title="Yo'nalish",
            label="Yo'nalishi yo'q",
            parameter_name="no_field",
        ),
        # "seed-unverified" dasturlarni topib, qo'lda tekshirish/o'chirish uchun.
        DistinctValuesFilter(Program.verified_by, title="Kim tekshirgan"),
    ]
    form_columns = [
        Program.university,
        Program.name,
        Program.abbreviation,
        Program.degree_level,
        Program.field,
        Program.language_of_instruction,
        Program.duration_years,
        Program.intake_term,
        Program.notes,
        Program.notes_ru,
        Program.notes_en,
        Program.requirements_text,
        Program.has_application_fee,
        Program.application_fee_amount,
        Program.application_fee_currency,
        Program.has_scholarship,
        Program.scholarship_url,
        Program.source_url,
        Program.verified_at,
        Program.verified_by,
    ]
    # Yo'nalish va til — faqat ro'yxatdan, majburiy (erkin matn katalogni
    # parchalab yuborardi).
    form_overrides = {"language_of_instruction": SelectField}
    form_args = {
        "field": {"validators": [InputRequired(message="Yo'nalishni tanlang")]},
        "language_of_instruction": {
            "choices": [("", "— tanlang —"), *INSTRUCTION_LANGUAGES.items()],
            "validators": [InputRequired(message="O'qitish tilini tanlang")],
        },
        "requirements_text": {"description": "Har qatorga bittadan talab."},
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
        field="Yo'nalish",
        field_of_study_legacy="Eski yo'nalish (matn)",
        language_of_instruction="O'qitish tili",
        duration_years="Davomiyligi (yil)",
        intake_term="Qabul davri",
        notes="Izoh (o'zbekcha)",
        notes_ru="Izoh (ruscha)",
        notes_en="Izoh (inglizcha)",
        missing_fields="To'ldirilmagan maydonlar",
        requirement="Til sertifikati / GRE",
        requirements_text="Qo'shimcha talablar",
        required_documents="Ariza uchun hujjatlar",
        cost="Xarajat",
        has_application_fee="Ariza to'lovi",
        application_fee_amount="Ariza to'lovi summasi",
        application_fee_currency="Ariza to'lovi valyutasi",
        deadlines="Muddatlar",
        has_scholarship="Dastur stipendiyasi",
        scholarship_url="Stipendiya havolasi",
        scholarships="Grantlar",
    )
    column_formatters = {
        Program.name: format_program_wizard_link,
        Program.verified_at: format_verified_at,
        Program.degree_level: enum_label(_DEGREE_LABELS),
    }
    column_formatters_detail = {
        Program.verified_at: format_verified_at,
        Program.degree_level: enum_label(_DEGREE_LABELS),
        Program.has_application_fee: format_bool,
        Program.has_scholarship: format_bool,
    }


class ScholarshipAdmin(ModelView, model=Scholarship):
    """Grantlar — yon menyudagi YAGONA grant bo'limi.

    Ilgari uchta alohida bo'lim bor edi: "Grant qo'shish" (sehrgar),
    "Grantlar" (ro'yxat) va "Grant muddatlari". Uchalasi ham bitta narsaga
    tegishli bo'lgani uchun admin qaysi biriga kirishni bilmay chalkashardi.
    Endi hammasi shu ro'yxat orqali: nom ustiga bosilsa sehrgar ochiladi,
    muddatlar ham o'sha yerda tahrirlanadi.
    """

    name = "Grant"
    name_plural = "Grantlar"
    icon = "fa-solid fa-hand-holding-dollar"

    # Tahrirlashning yagona yo'li — sehrgar. SQLAdmin'ning o'z formasi
    # grantning yarmini ko'rsatadi (IELTS, o'qish tili, daraja, davomiylik,
    # tanlov bosqichlari, muddatlar unda yo'q) — ikkisi yonma-yon turganda
    # qaysi biri to'liq ekani bilinmasdi.
    can_edit = False
    can_view_details = False

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
        Scholarship.study_language,
        Scholarship.degree_levels,
        Scholarship.duration_min_years,
        Scholarship.duration_max_years,
        Scholarship.ielts_min,
        Scholarship.toefl_min,
        Scholarship.work_experience_years,
        Scholarship.selection_stages,
        Scholarship.universities_text,
        Scholarship.selected_by,
        Scholarship.requirements_text,
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
        study_language="O'qish tili",
        degree_levels="Darajalar",
        duration_min_years="Davomiyligi (dan)",
        duration_max_years="Davomiyligi (gacha)",
        ielts_min="IELTS (kamida)",
        toefl_min="TOEFL iBT",
        work_experience_years="Ish tajribasi (yil)",
        selection_stages="Tanlov bosqichlari",
        universities_text="Qaysi universitetda",
        universities_text_ru="Qaysi universitetda (ru)",
        universities_text_en="Qaysi universitetda (en)",
        selected_by="Kim tanlaydi",
        selected_by_ru="Kim tanlaydi (ru)",
        selected_by_en="Kim tanlaydi (en)",
        requirements_text="Talablar",
        requirements_text_ru="Talablar (ru)",
        requirements_text_en="Talablar (en)",
    )
    _scholarship_formatters = {
        Scholarship.name: format_scholarship_wizard_link,
        Scholarship.verified_at: format_verified_at,
        Scholarship.coverage_type: enum_label(_COVERAGE_LABELS),
        Scholarship.citizenship_eligible: format_bool,
    }
    column_formatters = _scholarship_formatters
    column_formatters_detail = _scholarship_formatters


class ScholarshipDeadlineAdmin(ModelView, model=ScholarshipDeadline):
    """Grant muddatlari — yon menyuda KO'RSATILMAYDI.

    Muddatlar grant sehrgarida, grantning o'z formasi ichida tahrirlanadi —
    alohida bo'lim bo'lib turgani ortiqcha edi va "qaysi grantga tegishli"
    degan savolni tug'dirardi. Sahifa manzili ishlayveradi
    (/admin/scholarship-deadline/list) — bazani tekshirish uchun asqotadi.
    """

    name = "Grant muddati"
    name_plural = "Grant muddatlari"
    icon = "fa-solid fa-calendar-check"

    def is_visible(self, request: Request) -> bool:
        return False

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

    # Ro'yxatda faqat foydalanuvchini TANIB OLADIGAN ustunlar. Til, daraja va
    # yo'nalish bu yerdan olib tashlandi: ular profil ma'lumoti va ko'pchilikda
    # bo'sh ("—") turardi, jadvalni esa kengaytirib yuborardi. Kerak bo'lsa
    # tafsilot sahifasida hammasi bor.
    column_list = [
        User.id,
        User.telegram_id,
        User.username,
        User.balance,
        User.is_blocked,
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
        User.field,
        User.major_legacy,
        User.budget_max,
        User.budget_currency,
        User.age,
        User.university_rank_range,
        User.application_fee_ok,
        User.balance,
        User.is_blocked,
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
        User.field,
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
        field="Yo'nalish",
        major_legacy="Eski yo'nalish (matn)",
        budget_max="Byudjet",
        budget_currency="Valyuta",
        age="Yosh",
        university_rank_range="Universitet reytingi",
        application_fee_ok="Ariza to'loviga rozi",
        balance="Balans",
        is_blocked="Bloklangan",
        target_countries="Maqsad davlatlar",
        language_certificates="Til sertifikatlari",
        other_tests="Boshqa testlar",
        saved_programs="Saqlangan dasturlar",
    )
    _user_formatters = {
        User.ui_language: enum_label(_UI_LANG_LABELS),
        User.degree_level: enum_label(_DEGREE_LABELS),
        User.is_blocked: format_bool,
    }
    column_formatters = _user_formatters
    column_formatters_detail = _user_formatters

class AdmissionServiceAdmin(ModelView, model=AdmissionService):
    """Admission Kit sahifasidagi pullik xizmatlar.

    Mini App shu jadvaldan o'qiydi: xizmat qo'shish, matnini tahrirlash,
    narxini o'zgartirish yoki vaqtincha o'chirish uchun deploy kerak emas.

    `code` — barqaror kalit, Mini App ikonkani shu bo'yicha tanlaydi.
    Uni o'zgartirmang: nom tahrirlanaveradi, kod esa o'zgarmasligi kerak.

    Narx BO'SH qoldirilsa, Mini App "Narx kelishiladi" deb yozadi. 0 yozib
    qo'yish "bepul" degan boshqa ma'no beradi.

    DIQQAT: to'lov tizimi ulanmagan. Narx faqat ko'rsatish uchun, pul
    ilovada undirilmaydi — foydalanuvchi "Buyurtma berish"ni bosadi va
    "Xizmat so'rovlari" bo'limida paydo bo'ladi.
    """

    name = "Xizmat"
    category = "Admission Kit"
    name_plural = "Admission Kit xizmatlari"
    icon = "fa-solid fa-briefcase"

    column_list = [
        AdmissionService.id,
        AdmissionService.title_uz,
        AdmissionService.code,
        AdmissionService.price_amount,
        AdmissionService.price_currency,
        AdmissionService.sort_order,
        AdmissionService.is_active,
    ]
    column_searchable_list = [AdmissionService.title_uz, AdmissionService.code]
    column_sortable_list = [AdmissionService.sort_order, AdmissionService.price_amount]
    column_default_sort = [(AdmissionService.sort_order, False)]
    column_filters = [BooleanFilter(AdmissionService.is_active, title="Faol")]
    form_columns = [
        AdmissionService.code,
        AdmissionService.title_uz,
        AdmissionService.title_ru,
        AdmissionService.title_en,
        AdmissionService.description_uz,
        AdmissionService.description_ru,
        AdmissionService.description_en,
        AdmissionService.price_amount,
        AdmissionService.price_currency,
        AdmissionService.price_note_uz,
        AdmissionService.price_note_ru,
        AdmissionService.price_note_en,
        AdmissionService.sort_order,
        AdmissionService.is_active,
    ]
    column_labels = _labels(
        code="Kod",
        title_uz="Nomi (uz)",
        title_ru="Nomi (ru)",
        title_en="Nomi (en)",
        description_uz="Tavsifi (uz)",
        description_ru="Tavsifi (ru)",
        description_en="Tavsifi (en)",
        price_amount="Narxi",
        price_currency="Valyuta",
        price_note_uz="Narx izohi (uz)",
        price_note_ru="Narx izohi (ru)",
        price_note_en="Narx izohi (en)",
        sort_order="Tartib",
        is_active="Faol",
    )
    form_args = {
        "code": {
            "description": (
                "Lotin kichik harflar va _ (masalan cv_guide). Mini App ikonkani shu "
                "kod bo'yicha tanlaydi — keyin o'zgartirmang."
            )
        },
        "price_amount": {
            "description": "Bo'sh qoldirsangiz, ilovada «Narx kelishiladi» deb chiqadi."
        },
        "price_currency": {"description": "UZS, USD, EUR..."},
        "price_note_uz": {"description": "Narx yonidagi qisqa izoh: «bir marta», «1 soat»."},
        "sort_order": {"description": "Ro'yxatdagi o'rni: kichigi yuqorida."},
        "is_active": {"description": "O'chirilsa, xizmat ilovada ko'rinmaydi."},
    }
    column_formatters = {AdmissionService.is_active: format_bool}
    column_formatters_detail = {AdmissionService.is_active: format_bool}


class ServiceRequestAdmin(ModelView, model=ServiceRequest):
    """Foydalanuvchilarning Admission Kit xizmatlariga so'rovlari.

    Bu to'lov emas, qiziqish: foydalanuvchi ilovada "Buyurtma berish"ni
    bosgan, siz u bilan bog'lanib holatni yangilab borasiz. Yangi yozuv
    faqat shu yerdan yaratilmaydi — u ilovadan keladi.
    """

    name = "Xizmat so'rovi"
    category = "Admission Kit"
    name_plural = "Xizmat so'rovlari"
    icon = "fa-solid fa-handshake"
    can_create = False

    column_list = [
        ServiceRequest.id,
        ServiceRequest.service,
        ServiceRequest.user,
        ServiceRequest.status,
        ServiceRequest.created_at,
    ]
    column_default_sort = [(ServiceRequest.created_at, True)]
    column_filters = [
        StaticValuesFilter(
            ServiceRequest.status, values=_choices(_SERVICE_REQUEST_LABELS), title="Holat"
        )
    ]
    form_columns = [ServiceRequest.status, ServiceRequest.admin_note]
    column_labels = _labels(
        service="Xizmat",
        user="Kim so'ragan",
        status="Holat",
        admin_note="Ishchi izoh",
    )
    column_formatters = {ServiceRequest.status: enum_label(_SERVICE_REQUEST_LABELS)}
    column_formatters_detail = {ServiceRequest.status: enum_label(_SERVICE_REQUEST_LABELS)}


class PaymentSettingsAdmin(ModelView, model=PaymentSettings):
    """Karta rekvizitlari — botdagi /topup javobida aynan shular chiqadi.

    Jadval BITTA qatorli: yaratish va o'chirish o'chirilgan, faqat mavjud
    yozuv tahrirlanadi. Bir nechta qator bo'lsa, qaysi biri amal qilishi
    chalkash bo'lardi.
    """

    name = "To'lov sozlamasi"
    category = "To'lovlar"
    name_plural = "To'lov sozlamalari"
    icon = "fa-solid fa-credit-card"
    can_create = False
    can_delete = False

    column_list = [
        PaymentSettings.card_number,
        PaymentSettings.card_holder,
        PaymentSettings.min_amount,
        PaymentSettings.currency,
        PaymentSettings.updated_at,
    ]
    form_columns = [
        PaymentSettings.card_number,
        PaymentSettings.card_holder,
        PaymentSettings.min_amount,
        PaymentSettings.currency,
    ]
    column_labels = _labels(
        card_number="Karta raqami",
        card_holder="Karta egasi",
        min_amount="Eng kam summa",
        currency="Valyuta",
    )
    form_args = {
        "card_number": {
            "description": "Bot xabarida shundayligicha ko'rsatiladi: 9860 0201 0994 3405"
        },
        "card_holder": {"description": "Kartadagi ism-familiya."},
        "min_amount": {"description": "Bundan kam summa botda qabul qilinmaydi."},
    }


class BotAdminAdmin(ModelView, model=BotAdmin):
    """Botda /approve, /reject va /blockuser yoza oladigan odamlar.

    Adminka logini bilan bog'liq EMAS — bu Telegram tomonidagi ruxsat.
    Chek kelganda xabar aynan shu ro'yxatdagilarga yuboriladi, shuning
    uchun ro'yxat bo'sh bo'lsa hech kim xabar olmaydi.

    Telegram ID ni bilish uchun: @userinfobot ga yozing.
    """

    name = "Bot admini"
    name_plural = "Bot adminlari"
    icon = "fa-solid fa-user-shield"

    column_list = [BotAdmin.id, BotAdmin.telegram_id, BotAdmin.title, BotAdmin.is_active]
    column_searchable_list = [BotAdmin.title]
    form_columns = [BotAdmin.telegram_id, BotAdmin.title, BotAdmin.is_active]
    column_labels = _labels(
        telegram_id="Telegram ID",
        title="Izoh (kim)",
        is_active="Faol",
    )
    form_args = {
        "telegram_id": {"description": "Raqamli ID. Bilmasangiz @userinfobot ga yozing."},
        "title": {"description": "Eslatma uchun: ism yoki lavozim."},
        "is_active": {"description": "O'chirilsa, chek xabarlari kelmaydi va buyruqlar ishlamaydi."},
    }
    column_formatters = {BotAdmin.is_active: format_bool}
    column_formatters_detail = {BotAdmin.is_active: format_bool}


class PaymentAdmin(ModelView, model=Payment):
    """Balans to'ldirish urinishlari.

    Yozuvlar botdan keladi, shuning uchun bu yerda yaratilmaydi. Odatda
    tasdiqlash ham botda (/approve) bo'ladi — bu sahifa ko'rib chiqish va
    tarixni tekshirish uchun.

    DIQQAT: bu yerda holatni qo'lda o'zgartirish BALANSGA TEGMAYDI. Balans
    faqat botdagi /approve orqali to'ldiriladi, aks holda qoldiq va
    tranzaksiyalar tarixi bir-biriga mos kelmay qolardi.
    """

    name = "To'lov"
    category = "To'lovlar"
    name_plural = "To'lovlar"
    icon = "fa-solid fa-receipt"
    can_create = False

    column_list = [
        Payment.id,
        Payment.user,
        Payment.amount,
        Payment.currency,
        Payment.status,
        Payment.created_at,
    ]
    column_default_sort = [(Payment.created_at, True)]
    column_filters = [
        StaticValuesFilter(
            Payment.status, values=_choices(_PAYMENT_STATUS_LABELS), title="Holat"
        )
    ]
    form_columns = [Payment.admin_note]
    column_labels = _labels(
        user="Kim",
        amount="Summa",
        currency="Valyuta",
        status="Holat",
        receipt_file_id="Chek fayli",
        receipt_kind="Fayl turi",
        reviewed_by="Kim ko'rdi",
        admin_note="Ishchi izoh",
    )
    column_formatters = {Payment.status: enum_label(_PAYMENT_STATUS_LABELS)}
    column_formatters_detail = {Payment.status: enum_label(_PAYMENT_STATUS_LABELS)}


class BalanceTransactionAdmin(ModelView, model=BalanceTransaction):
    """Balansdagi har bir o'zgarish — faqat o'qish uchun.

    Tahrirlash ATAYLAB yopiq: bu yozuvlar qoldiqning izohi, ularni qo'lda
    o'zgartirish balans bilan tarixni bir-biriga qarama-qarshi qilib
    qo'yardi.
    """

    name = "Tranzaksiya"
    category = "To'lovlar"
    name_plural = "Balans tarixi"
    icon = "fa-solid fa-arrow-right-arrow-left"
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        BalanceTransaction.id,
        BalanceTransaction.user,
        BalanceTransaction.kind,
        BalanceTransaction.amount,
        BalanceTransaction.balance_after,
        BalanceTransaction.created_at,
    ]
    column_default_sort = [(BalanceTransaction.created_at, True)]
    column_filters = [
        StaticValuesFilter(
            BalanceTransaction.kind, values=_choices(_TRANSACTION_KIND_LABELS), title="Turi"
        )
    ]
    column_labels = _labels(
        user="Kim",
        kind="Turi",
        amount="O'zgarish",
        balance_after="Keyingi qoldiq",
        note="Izoh",
    )
    column_formatters = {BalanceTransaction.kind: enum_label(_TRANSACTION_KIND_LABELS)}
    column_formatters_detail = {BalanceTransaction.kind: enum_label(_TRANSACTION_KIND_LABELS)}


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

        # Admin Chat ID maydoniga ko'pincha to'liq havola yoki "@"siz nom
        # yozib qo'yadi. Ilgari bunday qiymat o'zgartirilmasdan saqlanar,
        # Telegram esa uni tanimay "chat not found" qaytarardi — majburiy
        # obuna jimgina ishlamay qolardi.
        chat_id = normalize_chat_id(data.get("chat_id")) or derive_chat_id(url)
        if not chat_id:
            raise ValueError(
                "Kanal identifikatorini aniqlab bo'lmadi. Ochiq kanal uchun havolani "
                "(https://t.me/kanalnomi) kiriting, yopiq kanal uchun esa raqamli "
                "Chat ID ni (-1001234567890 ko'rinishida) yozing."
            )

        # Sozlama noto'g'ri bo'lsa admin shu yerda bilsin. Aks holda xato
        # faqat log'ga tushar, tekshiruv esa "fail-open" bo'lgani uchun
        # hamma bemalol o'tib ketaverardi.
        problem = await self._channel_access_problem(chat_id)
        if problem:
            raise ValueError(problem)

        data["invite_url"] = url
        data["chat_id"] = chat_id

    @staticmethod
    async def _channel_access_problem(chat_id: str) -> str | None:
        """Bot kanalda a'zolikni o'qiy oladimi. Muammo matnini qaytaradi."""
        if not settings.bot_token:
            return None
        bot = Bot(token=settings.bot_token)
        try:
            return await verify_channel_access(bot, chat_id)
        finally:
            await bot.session.close()

    async def after_model_change(
        self, data: dict, model: RequiredChannel, is_created: bool, request: Request
    ) -> None:
        # Kanallar ro'yxati o'zgardi — eski "obuna bo'lgan" keshi bekor qilinadi.
        await clear_all_cache(redis_client)

    async def after_model_delete(self, model: RequiredChannel, request: Request) -> None:
        await clear_all_cache(redis_client)
