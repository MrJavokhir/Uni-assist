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
    university: str
    country: str
    degree_level: str
    level: str
    missing: list[str]
    saved: bool


class SavedOut(BaseModel):
    id: int
    program_id: int
    program_name: str
    university: str
    country: str
    status: str
    reminders_active: bool
    nearest_deadline: str | None
    nearest_deadline_days_left: int | None


class SavedStatusIn(BaseModel):
    status: str
