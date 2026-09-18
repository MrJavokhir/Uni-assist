from sqladmin import ModelView
from sqladmin.filters import BooleanFilter, StaticValuesFilter

from app.admin.filters import RelationshipFilter
from app.admin.formatters import enum_label, format_bool, format_verified_at
from app.db.models import (
    Country,
    CoverageType,
    Deadline,
    DeadlineType,
    DegreeLevel,
    LanguageCertType,
    Program,
    ProgramCost,
    ProgramRequirement,
    Report,
    ReportStatus,
    SavedProgram,
    SavedProgramStatus,
    Scholarship,
    ScholarshipDeadline,
    UiLanguage,
    University,
    User,
    UserLanguageCertificate,
    UserOtherTest,
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

CATALOG = "Katalog"
GRANTS = "Grantlar"
USERS = "Foydalanuvchilar"
QUALITY = "Ma'lumot sifati"


class CountryAdmin(ModelView, model=Country):
    name = "Davlat"
    name_plural = "Davlatlar"
    icon = "fa-solid fa-flag"
    category = CATALOG

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
    category = CATALOG

    column_list = [University.id, University.name, University.country, University.city, University.timezone]
    column_searchable_list = [University.name, University.city]
    column_sortable_list = [University.name, University.city]
    form_columns = [
        University.country,
        University.name,
        University.city,
        University.website,
        University.timezone,
    ]
    column_labels = _labels(
        name="Nomi", country="Davlat", city="Shahar", website="Veb-sayt", timezone="Vaqt zonasi"
    )


class ProgramAdmin(ModelView, model=Program):
    name = "Dastur"
    name_plural = "Dasturlar"
    icon = "fa-solid fa-graduation-cap"
    category = CATALOG

    column_list = [
        Program.id,
        Program.university,
        Program.name,
        Program.degree_level,
        Program.field_of_study,
        Program.intake_term,
        Program.verified_at,
    ]
    column_details_list = [
        Program.id,
        Program.university,
        Program.name,
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
    column_searchable_list = [Program.name, Program.field_of_study]
    column_sortable_list = [Program.name, Program.verified_at]
    column_filters = [
        StaticValuesFilter(Program.degree_level, values=_choices(_DEGREE_LABELS), title="Daraja")
    ]
    form_columns = [
        Program.university,
        Program.name,
        Program.degree_level,
        Program.field_of_study,
        Program.language_of_instruction,
        Program.duration_years,
        Program.intake_term,
        Program.notes,
        Program.source_url,
        Program.verified_at,
        Program.verified_by,
    ]
    column_labels = _labels(
        name="Dastur nomi",
        university="Universitet",
        degree_level="Daraja",
        field_of_study="Yo'nalish",
        language_of_instruction="O'qitish tili",
        duration_years="Davomiyligi (yil)",
        intake_term="Qabul davri",
        notes="Izoh",
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


class ProgramRequirementAdmin(ModelView, model=ProgramRequirement):
    name = "Talab"
    name_plural = "Dastur talablari"
    icon = "fa-solid fa-list-check"
    category = CATALOG

    column_list = [
        ProgramRequirement.id,
        ProgramRequirement.program,
        ProgramRequirement.gpa_min,
        ProgramRequirement.ielts_min,
        ProgramRequirement.toefl_min,
        ProgramRequirement.gre_required,
    ]
    form_columns = [
        ProgramRequirement.program,
        ProgramRequirement.gpa_min,
        ProgramRequirement.gpa_scale,
        ProgramRequirement.ielts_min,
        ProgramRequirement.toefl_min,
        ProgramRequirement.gre_required,
        ProgramRequirement.gre_min,
        ProgramRequirement.prereq_major,
        ProgramRequirement.age_limit,
    ]
    column_labels = _labels(
        program="Dastur",
        gpa_min="Minimal GPA",
        gpa_scale="GPA tizimi",
        ielts_min="Minimal IELTS",
        toefl_min="Minimal TOEFL",
        gre_required="GRE talab qilinadi",
        gre_min="Minimal GRE",
        prereq_major="Kerakli yo'nalish",
        age_limit="Yosh chegarasi",
    )
    column_formatters = {ProgramRequirement.gre_required: format_bool}


class ProgramCostAdmin(ModelView, model=ProgramCost):
    name = "Xarajat"
    name_plural = "Dastur xarajatlari"
    icon = "fa-solid fa-money-bill-wave"
    category = CATALOG

    column_list = [
        ProgramCost.id,
        ProgramCost.program,
        ProgramCost.tuition_amount,
        ProgramCost.currency,
        ProgramCost.visa_proof_amount,
        ProgramCost.living_cost_monthly,
        ProgramCost.last_checked,
    ]
    form_columns = [
        ProgramCost.program,
        ProgramCost.tuition_amount,
        ProgramCost.currency,
        ProgramCost.visa_proof_amount,
        ProgramCost.living_cost_monthly,
        ProgramCost.last_checked,
    ]
    column_labels = _labels(
        program="Dastur",
        tuition_amount="Kontrakt",
        currency="Valyuta",
        visa_proof_amount="Viza uchun isbot summasi",
        living_cost_monthly="Yashash (oyiga)",
        last_checked="Oxirgi tekshiruv",
    )


class DeadlineAdmin(ModelView, model=Deadline):
    name = "Muddat"
    name_plural = "Dastur muddatlari"
    icon = "fa-solid fa-calendar-days"
    category = CATALOG

    column_list = [Deadline.id, Deadline.program, Deadline.type, Deadline.date_utc, Deadline.intake_term]
    column_sortable_list = [Deadline.date_utc]
    form_columns = [Deadline.program, Deadline.type, Deadline.date_utc, Deadline.intake_term]
    column_labels = _labels(
        program="Dastur", type="Muddat turi", date_utc="Sana (UTC)", intake_term="Qabul davri"
    )
    column_formatters = {Deadline.type: enum_label(_DEADLINE_LABELS)}
    column_formatters_detail = {Deadline.type: enum_label(_DEADLINE_LABELS)}


class ScholarshipAdmin(ModelView, model=Scholarship):
    name = "Grant"
    name_plural = "Grantlar"
    icon = "fa-solid fa-hand-holding-dollar"
    category = GRANTS

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
    category = GRANTS

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
    category = USERS
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


class UserLanguageCertificateAdmin(ModelView, model=UserLanguageCertificate):
    name = "Til sertifikati"
    name_plural = "Til sertifikatlari"
    icon = "fa-solid fa-certificate"
    category = USERS
    can_create = False

    column_list = [
        UserLanguageCertificate.id,
        UserLanguageCertificate.user,
        UserLanguageCertificate.type,
        UserLanguageCertificate.score,
        UserLanguageCertificate.exam_date,
    ]
    form_columns = [
        UserLanguageCertificate.user,
        UserLanguageCertificate.type,
        UserLanguageCertificate.score,
        UserLanguageCertificate.exam_date,
    ]
    column_labels = _labels(
        user="Foydalanuvchi", type="Sertifikat turi", score="Ball", exam_date="Imtihon sanasi"
    )
    column_formatters = {UserLanguageCertificate.type: enum_label(_CERT_LABELS)}


class UserOtherTestAdmin(ModelView, model=UserOtherTest):
    name = "Boshqa test"
    name_plural = "Boshqa testlar (GRE/GMAT)"
    icon = "fa-solid fa-pen"
    category = USERS
    can_create = False

    column_list = [UserOtherTest.id, UserOtherTest.user, UserOtherTest.type, UserOtherTest.score]
    form_columns = [UserOtherTest.user, UserOtherTest.type, UserOtherTest.score, UserOtherTest.exam_date]
    column_labels = _labels(
        user="Foydalanuvchi", type="Test turi", score="Ball", exam_date="Imtihon sanasi"
    )


class SavedProgramAdmin(ModelView, model=SavedProgram):
    name = "Saqlangan dastur"
    name_plural = "Saqlangan dasturlar"
    icon = "fa-solid fa-bookmark"
    category = USERS
    can_create = False

    column_list = [
        SavedProgram.id,
        SavedProgram.user,
        SavedProgram.program,
        SavedProgram.status,
        SavedProgram.reminders_active,
        SavedProgram.created_at,
    ]
    column_filters = [
        StaticValuesFilter(
            SavedProgram.status, values=_choices(_SAVED_STATUS_LABELS), title="Holat"
        ),
        BooleanFilter(SavedProgram.reminders_active, title="Eslatmalar yoqilgan"),
    ]
    form_columns = [SavedProgram.status, SavedProgram.reminders_active]
    column_labels = _labels(
        user="Foydalanuvchi",
        program="Dastur",
        status="Ariza holati",
        reminders_active="Eslatmalar yoqilgan",
    )
    _saved_formatters = {
        SavedProgram.status: enum_label(_SAVED_STATUS_LABELS),
        SavedProgram.reminders_active: format_bool,
    }
    column_formatters = _saved_formatters
    column_formatters_detail = _saved_formatters


class ReportAdmin(ModelView, model=Report):
    """Foydalanuvchidan kelgan 'ma'lumot noto'g'ri' signallari."""

    name = "Signal"
    name_plural = "Ma'lumot noto'g'ri signallari"
    icon = "fa-solid fa-triangle-exclamation"
    category = QUALITY
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
