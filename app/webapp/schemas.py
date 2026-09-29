from pydantic import BaseModel


class LanguageCertOut(BaseModel):
    type: str
    score: float


class ProfileOut(BaseModel):
    ui_language: str
    degree_level: str | None
    field_id: int | None
    gpa_raw: float | None
    gpa_scale: str | None
    # Mo'ljaldagi universitet reytingi oralig'i ("1-100", "101-300", ...)
    university_rank_range: str | None
    # Ariza to'lovi bor dasturlar mos keladimi (None = tanlanmagan)
    application_fee_ok: bool | None
    # O'qish tili — kanonik inglizcha nom ("English"). None = farqi yo'q.
    study_language: str | None = None
    target_country_ids: list[int]
    language_certificates: list[LanguageCertOut]
    # Hisob: balans faqat BOTDA to'ldiriladi (/topup), Mini App uni
    # ko'rsatadi va xizmatlarga sarflaydi.
    balance: float
    balance_currency: str
    is_blocked: bool
    # Do'stlarni taklif qilish havolasi uchun. Telegram buni
    # `initDataUnsafe` da bermaydi, shuning uchun server aniqlaydi.
    bot_username: str | None = None
    # Taklif dasturi. Havola SERVER tomonida yig'iladi: unda foydalanuvchi
    # o'zgartira olmaydigan taklif kodi bor.
    referral_link: str | None = None
    referral_bonus: float = 0
    referral_count: int = 0


class ProfileIn(BaseModel):
    ui_language: str | None = None
    degree_level: str | None = None
    # null yuborilsa yo'nalish tozalanadi; umuman yuborilmasa o'zgarmaydi
    # (farqi `model_fields_set` orqali aniqlanadi).
    field_id: int | None = None
    gpa_raw: float | None = None
    gpa_scale: str | None = None
    university_rank_range: str | None = None
    application_fee_ok: bool | None = None
    # Bo'sh satr = "farqi yo'q" (tanlov tozalanadi); yuborilmasa o'zgarmaydi.
    study_language: str | None = None
    target_country_ids: list[int] | None = None
    language_cert_type: str | None = None
    language_cert_score: float | None = None


class GpaConvertOut(BaseModel):
    us4: float
    ects: str
    bavarian: float
    # Buyuk Britaniya diplom darajasi kaliti (first, upper_second, ...)
    uk: str
    disclaimer: str


class CountryOut(BaseModel):
    id: int
    name_uz: str
    name_ru: str
    name_en: str
    iso_code: str


class FieldOut(BaseModel):
    """Yo'nalish — Mini App nomini foydalanuvchi tilida o'zi tanlaydi."""

    id: int
    code: str
    name_uz: str
    name_ru: str
    name_en: str


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
    # Ro'yxatda darhol ko'rinadigan asosiy raqamlar — har birini ochib
    # ko'rmasdan taqqoslash uchun.
    tuition_amount: float | None = None
    tuition_currency: str | None = None
    ielts_min: float | None = None
    toefl_min: int | None = None
    # Universitetning jahon reytingidagi o'rni (QS)
    university_ranking: int | None = None


class ProgramRequirementOut(BaseModel):
    ielts_min: float | None
    toefl_min: int | None
    gre_required: bool
    gre_min: int | None
    prereq_major: str | None


class ProgramCostOut(BaseModel):
    tuition_amount: float
    currency: str
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
    university_ranking: int | None = None
    city: str
    country: CountryOut
    degree_level: str
    # None = yo'nalish hali biriktirilmagan
    field: FieldOut | None
    language_of_instruction: str
    duration_years: float
    intake_term: str
    # Foydalanuvchi tilidagi erkin izoh (yo'q bo'lsa o'zbekchasi)
    notes: str | None
    # Rasmiy sahifada ko'rsatilmagan maydon kalitlari — jumlani Mini App
    # foydalanuvchi tilida o'zi yasaydi.
    missing_fields: list[str]
    # Ariza uchun hujjat KALITLARI (Mini App ularni tarjima qiladi)
    required_documents: list[str] = []
    # Shu dasturning o'z stipendiyasi bormi (None = tekshirilmagan)
    has_scholarship: bool | None = None
    scholarship_url: str | None = None
    # Ariza to'lovi (None = tekshirilmagan, False = bepul)
    has_application_fee: bool | None = None
    application_fee_amount: float | None = None
    application_fee_currency: str | None = None
    # Qo'shimcha talablar — admin har qatorga bittadan yozadi
    requirements: list[str] = []
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
    logo: str | None = None
    # Rasmiy sahifadan olingan tafsilotlar (None = ko'rsatilmagan)
    stipend_max: float | None = None
    stipend_period: str | None = None
    ielts_min: float | None = None
    toefl_min: int | None = None
    work_experience_years: int | None = None
    degree_levels: list[str] = []
    study_language: str | None = None
    duration_min_years: float | None = None
    duration_max_years: float | None = None
    selection_stages: int | None = None
    # Qaysi universitetda o'qiladi / kim tanlaydi / erkin matnli talablar
    universities_text: str | None = None
    selected_by: str | None = None
    requirements_text: str | None = None
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


class ServiceOut(BaseModel):
    """Admission Kit sahifasidagi bitta xizmat.

    Matnlar server tomonida foydalanuvchi tiliga o'girilgan holda keladi —
    katalog bazada turgani uchun Mini App ularni tarjima qila olmaydi.
    """

    id: int
    code: str
    title: str
    description: str | None = None
    # Narx ko'rsatilmagan bo'lsa null — Mini App "Narx kelishiladi" deb yozadi.
    price_amount: float | None = None
    price_currency: str
    price_note: str | None = None
    # "file" — yuklab olinadigan qo'llanma: qulflangan turadi, sotib
    # olingach PDF botda yuboriladi. "request" — qo'lda bajariladigan
    # xizmat: buyurtma bergach admin bog'lanadi.
    kind: str = "request"
    # Foydalanuvchi bu xizmatni allaqachon sotib olganmi (yoki so'rov
    # yuborganmi). Fayl xizmatlar uchun bu "qulf ochilgan" degani.
    requested: bool = False
    # PDF haqiqatan biriktirilganmi. `kind == "file"` bo'lsa-yu fayl hali
    # yuklanmagan bo'lsa, ilova "tez orada" deb ko'rsatadi va sotib
    # olishga yo'l qo'ymaydi — pul olib, berishga narsa bo'lmasligi kerak.
    has_file: bool = False
    file_name: str | None = None
    file_size: int | None = None
    # Buyurtma berishdan oldin uchrashuv vaqti tanlanadimi (1:1 mentor).
    requires_booking: bool = False
    # Nechta bo'sh vaqt qolgan. 0 bo'lsa ilova buyurtmaga yo'l qo'ymaydi —
    # vaqtsiz pul olib bo'lmaydi.
    free_slots: int = 0


class SlotOut(BaseModel):
    """Bo'sh uchrashuv oynasi.

    Sana va vaqt SERVER tomonida Toshkent vaqtiga o'girilib, foydalanuvchi
    tilida tayyorlanadi: ilova qurilma vaqt mintaqasiga tayansa, chet elda
    turgan foydalanuvchi boshqa vaqtni ko'rardi.
    """

    id: int
    date_label: str
    time_label: str
    duration_minutes: int
    note: str | None = None


class ServiceRequestIn(BaseModel):
    """Buyurtma tafsiloti. Vaqt tanlanadigan xizmatlarda `slot_id` shart."""

    slot_id: int | None = None


class ServiceRequestResult(BaseModel):
    """Xizmat sotib olingandan keyingi javob."""

    requested: bool
    # Balansdan yechilgan bo'lsa yangi qoldiq, aks holda o'zgarmagan qoldiq.
    balance: float
    charged: float | None = None
    # PDF xizmat bo'lsa, ilova darhol yetkazishni so'raydi.
    has_file: bool = False
    # Band qilingan vaqt — tasdiq oynasida ko'rsatiladi.
    slot_label: str | None = None


class ServiceDeliveryResult(BaseModel):
    """PDF botga yuborilgandan keyingi javob."""

    sent: bool
    file_name: str | None = None


class FeedbackIn(BaseModel):
    text: str
