from sqladmin import ModelView

from app.admin.formatters import format_verified_at
from app.db.models import (
    Country,
    Deadline,
    Program,
    ProgramCost,
    ProgramRequirement,
    Report,
    SavedProgram,
    Scholarship,
    ScholarshipDeadline,
    University,
    User,
    UserLanguageCertificate,
    UserOtherTest,
)

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
    column_filters = [Program.degree_level]
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
    column_formatters = {Program.verified_at: format_verified_at}
    column_formatters_detail = {Program.verified_at: format_verified_at}


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


class DeadlineAdmin(ModelView, model=Deadline):
    name = "Muddat"
    name_plural = "Dastur muddatlari"
    icon = "fa-solid fa-calendar-days"
    category = CATALOG

    column_list = [Deadline.id, Deadline.program, Deadline.type, Deadline.date_utc, Deadline.intake_term]
    column_sortable_list = [Deadline.date_utc]
    form_columns = [Deadline.program, Deadline.type, Deadline.date_utc, Deadline.intake_term]


class ScholarshipAdmin(ModelView, model=Scholarship):
    name = "Grant"
    name_plural = "Grantlar"
    icon = "fa-solid fa-hand-holding-dollar"
    category = GRANTS

    column_list = [
        Scholarship.id,
        Scholarship.name,
        Scholarship.coverage_type,
        Scholarship.citizenship_eligible,
        Scholarship.verified_at,
    ]
    column_details_list = [
        Scholarship.id,
        Scholarship.name,
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
    column_filters = [Scholarship.coverage_type, Scholarship.citizenship_eligible]
    form_columns = [
        Scholarship.name,
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
    column_formatters = {Scholarship.verified_at: format_verified_at}
    column_formatters_detail = {Scholarship.verified_at: format_verified_at}


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


class UserOtherTestAdmin(ModelView, model=UserOtherTest):
    name = "Boshqa test"
    name_plural = "Boshqa testlar (GRE/GMAT)"
    icon = "fa-solid fa-pen"
    category = USERS
    can_create = False

    column_list = [UserOtherTest.id, UserOtherTest.user, UserOtherTest.type, UserOtherTest.score]
    form_columns = [UserOtherTest.user, UserOtherTest.type, UserOtherTest.score, UserOtherTest.exam_date]


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
    column_filters = [SavedProgram.status, SavedProgram.reminders_active]
    form_columns = [SavedProgram.status, SavedProgram.reminders_active]


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
    column_filters = [Report.status]
    form_columns = [Report.status]
