from pydantic import BaseModel


class LanguageCertOut(BaseModel):
    type: str
    score: float


class ProfileOut(BaseModel):
    ui_language: str
    degree_level: str | None
    major: str | None
    gpa_raw: float | None
    gpa_scale: str | None
    budget_max: float | None
    budget_currency: str | None
    age: int | None
    target_country_ids: list[int]
    language_certificates: list[LanguageCertOut]


class ProfileIn(BaseModel):
    ui_language: str | None = None
    degree_level: str | None = None
    major: str | None = None
    gpa_raw: float | None = None
    gpa_scale: str | None = None
    budget_max: float | None = None
    age: int | None = None
    target_country_ids: list[int] | None = None
    language_cert_type: str | None = None
    language_cert_score: float | None = None


class GpaConvertOut(BaseModel):
    us4: float
    ects: str
    bavarian: float
    disclaimer: str


class CountryOut(BaseModel):
    id: int
    name_uz: str
    name_ru: str
    name_en: str
    iso_code: str


class MatchProgramOut(BaseModel):
    id: int
    name: str
    # Diplom qisqartmasi (MBA, LLM, B.Sc.) — talabalar dasturni ko'pincha
    # shu bo'yicha taniydi.
    abbreviation: str | None = None
    university: str
    university_logo: str | None = None
    country: CountryOut
    degree_level: str
    level: str
    missing: list[str]
    saved: bool


class ProgramRequirementOut(BaseModel):
    gpa_min: float | None
    gpa_scale: str | None
    ielts_min: float | None
    toefl_min: int | None
    gre_required: bool
    gre_min: int | None
    prereq_major: str | None
    age_limit: int | None


class ProgramCostOut(BaseModel):
    tuition_amount: float
    currency: str
    visa_proof_amount: float | None
    living_cost_monthly: float | None
    last_checked: str


class ProgramDeadlineOut(BaseModel):
    type: str
    date: str
    days_left: int
    intake_term: str


class ProgramDetailOut(BaseModel):
    """Dastur kartasi bosilganda ochiladigan to'liq ma'lumot."""

    id: int
    name: str
    abbreviation: str | None
    university: str
    university_website: str | None
    university_logo: str | None
    city: str
    country: CountryOut
    degree_level: str
    field_of_study: str
    language_of_instruction: str
    duration_years: float
    intake_term: str
    # Foydalanuvchi tilidagi erkin izoh (yo'q bo'lsa o'zbekchasi)
    notes: str | None
    # Rasmiy sahifada ko'rsatilmagan maydon kalitlari — jumlani Mini App
    # foydalanuvchi tilida o'zi yasaydi.
    missing_fields: list[str]
    requirement: ProgramRequirementOut | None
    cost: ProgramCostOut | None
    deadlines: list[ProgramDeadlineOut]
    source_url: str
    verified_at: str
    saved: bool


class SavedOut(BaseModel):
    id: int
    program_id: int
    program_name: str
    university: str
    university_logo: str | None = None
    country: CountryOut
    status: str
    reminders_active: bool
    nearest_deadline: str | None
    nearest_deadline_days_left: int | None


class SavedStatusIn(BaseModel):
    status: str


class ScholarshipDeadlineOut(BaseModel):
    type: str
    date: str
    days_left: int | None
    intake_term: str


class ScholarshipOut(BaseModel):
    id: int
    name: str
    description: str | None
    coverage_type: str
    coverage_percent: int | None
    stipend_amount: float | None
    currency: str
    extras_flight: bool
    extras_insurance: bool
    extras_dormitory: bool
    extras_language_course: bool
    citizenship_eligible: bool
    # To'liq obyekt (faqat nom emas): Mini App bayroq chiqarishi uchun
    # iso_code, foydalanuvchi tilida ko'rsatishi uchun esa uchala nom kerak.
    countries: list[CountryOut]
    age_limit: int | None
    university_choice: str
    application_linked_to_program: bool
    source_url: str
    nearest_deadline: str | None
    nearest_deadline_days_left: int | None
    deadlines: list[ScholarshipDeadlineOut]
