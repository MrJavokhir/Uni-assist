"""LL.M. (Master of Laws) dasturlari — universitetlarning RASMIY sahifalaridan.

MANBA HAQIDA (muhim):
Bu ro'yxat llm-guide.com kabi vositachi kataloglardan KO'CHIRILMAGAN. Har bir
yozuvning `source_url`i universitetning o'z sahifasi va har bir raqam (kontrakt,
IELTS/TOEFL, muddat) o'sha sahifada aynan shunday yozilgan.

TO'QILMAGAN MA'LUMOT:
Rasmiy sahifada ko'rsatilmagan maydon BO'SH qoldiriladi — taxmin qilinmaydi.
Masalan NYU faqat kredit narxini e'lon qiladi (yillik summa emas), shuning
uchun uning ProgramCost yozuvi yaratilmaydi. Bo'sh maydonlarni admin panelda
"Universitet qo'shish" sehrgari orqali to'ldirish mumkin.

Idempotent: universitet (nomi) va dastur (universitet + nomi + daraja) bo'yicha
upsert qilinadi — ikki marta ishga tushirilsa ham dublikat yaratmaydi.

Ishlatish:
    uv run python scripts/seed_llm_programs.py
"""

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Country,
    Deadline,
    DeadlineType,
    DegreeLevel,
    Program,
    ProgramCost,
    ProgramRequirement,
    University,
)
from app.db.session import async_session_factory

VERIFIED_BY = "seed-llm-official"
FIELD_OF_STUDY = "Law"


@dataclass(frozen=True)
class LlmSeed:
    """Bitta LL.M. dasturi va uning universiteti.

    `None` qiymat = rasmiy sahifada ko'rsatilmagan (to'qilmaydi).
    """

    country_iso: str
    university: str
    city: str
    website: str
    timezone: str

    program: str
    source_url: str
    intake_term: str
    duration_years: float = 1.0
    language: str = "English"
    abbreviation: str = "LLM"

    tuition_amount: float | None = None
    tuition_currency: str = "USD"
    ielts_min: float | None = None
    toefl_min: int | None = None
    deadline_close: date | None = None
    # Erkin izoh uch tilda. `notes` — o'zbekcha; ru/en bo'sh bo'lsa Mini App
    # o'zbekchasiga qaytadi.
    notes: str | None = None
    notes_ru: str | None = None
    notes_en: str | None = None

    # Ariza uchun hujjatlar — KALITLAR (Mini App ularni tarjima qiladi):
    # degree_certificate, transcript, translation, reference, english_test,
    # passport, personal_statement, cv, research_proposal
    documents: tuple[str, ...] = ()
    # Shu dasturga/fakultetga tegishli stipendiya bormi
    has_scholarship: bool | None = None
    scholarship_url: str | None = None
    # Universitet logotipi saytdan avtomatik olinadi, shuning uchun bu yerda
    # ataylab yo'q (app/webapp/api.py `_logo_url`).
    missing: tuple[str, ...] = field(default_factory=tuple)


# Har bir qiymat 2026-yil sentyabr holatiga ko'ra rasmiy sahifadan olingan.
SEEDS: list[LlmSeed] = [
    # ------------------------------- AQSH -------------------------------
    LlmSeed(
        country_iso="US",
        university="Harvard Law School",
        city="Cambridge, MA",
        website="https://hls.harvard.edu",
        timezone="America/New_York",
        program="Master of Laws (LL.M.)",
        source_url="https://hls.harvard.edu/graduate-program/graduate-program-admissions-and-financial-aid/apply-to-the-graduate-program/",
        intake_term="2027 Fall",
        deadline_close=date(2026, 12, 1),
        missing=("tuition", "language_score"),
    ),
    LlmSeed(
        country_iso="US",
        university="Columbia Law School",
        city="Nyu-York, NY",
        website="https://www.law.columbia.edu",
        timezone="America/New_York",
        program="Master of Laws (LL.M.)",
        source_url="https://www.law.columbia.edu/admissions/graduate-admissions/llm/llm-tuition-and-fees",
        intake_term="2027 Fall",
        tuition_amount=93757,
        tuition_currency="USD",
        # 2026-yil 21-yanvargacha bo'lgan TOEFL iBT shkalasi bo'yicha.
        # Yangi shkalada talab: umumiy 5.5, har bo'limda kamida 5.0.
        toefl_min=105,
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="US",
        university="Georgetown University Law Center",
        city="Vashington, DC",
        website="https://www.law.georgetown.edu",
        timezone="America/New_York",
        program="International Legal Studies LL.M.",
        source_url="https://www.law.georgetown.edu/academics/llm-degree-programs/international-legal-studies/",
        intake_term="2027 Fall",
        toefl_min=100,
        missing=("tuition", "language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="US",
        university="New York University School of Law",
        city="Nyu-York, NY",
        website="https://www.law.nyu.edu",
        timezone="America/New_York",
        program="Master of Laws (LL.M.)",
        source_url="https://www.law.nyu.edu/graduateadmissions/whentoapply",
        intake_term="2027 Fall",
        # NYU yillik summani e'lon qilmaydi — faqat kredit narxi. Kreditni
        # ko'paytirib "yillik" raqam chiqarish noto'g'ri bo'lardi.
        missing=("tuition", "language_score", "deadline"),
    ),
    # --------------------------- Buyuk Britaniya ---------------------------
    LlmSeed(
        country_iso="GB",
        university="London School of Economics and Political Science",
        city="London",
        website="https://www.lse.ac.uk",
        timezone="Europe/London",
        program="LLM, Master of Laws",
        source_url="https://www.lse.ac.uk/study-at-lse/graduate/llm",
        intake_term="2026 Fall",
        tuition_amount=39900,
        tuition_currency="GBP",
        missing=("language_score",),
        has_scholarship=True,
        documents=(
            "transcript",
            "personal_statement",
            "reference",
            "cv",
        ),
        notes=(
            "Ariza qabul qilish uzluksiz (rolling admissions) — qat'iy yopilish sanasi "
            "yo'q, joy to'lgach yopiladi. Ikkita akademik tavsiyanoma kerak. LSE'ning "
            "ehtiyojga asoslangan moliyaviy yordamiga ariza muddati — 23-aprel."
        ),
        notes_ru=(
            "Приём заявок непрерывный (rolling admissions) — жёсткого дедлайна нет, приём "
            "закрывается по заполнении мест. Нужны две академические рекомендации. Дедлайн "
            "заявки на финансовую помощь LSE по нуждаемости — 23 апреля."
        ),
        notes_en=(
            "Applications are considered on a rolling basis — there is no fixed deadline "
            "and applications close once the programme is full. Two academic references "
            "are required. The deadline for LSE needs-based funding is 23 April."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="Queen Mary University of London",
        city="London",
        website="https://www.qmul.ac.uk",
        timezone="Europe/London",
        program="Laws LLM",
        source_url="https://www.qmul.ac.uk/postgraduate/taught/coursefinder/courses/laws-llm/",
        intake_term="2026 Fall",
        # IELTS (Academic): umumiy 7.0, Writing 6.5, qolganlari 6.0.
        ielts_min=7.0,
        missing=("tuition", "deadline"),
        has_scholarship=True,
    ),
    # ------------------------------ Germaniya ------------------------------
    LlmSeed(
        country_iso="DE",
        university="Bucerius Law School",
        city="Gamburg",
        website="https://www.law-school.de",
        timezone="Europe/Berlin",
        program="Master of Law and Business (LL.M.)",
        source_url="https://www.law-school.de/international/education/master-of-law-and-business",
        intake_term="2027 Fall",
        tuition_amount=25000,
        tuition_currency="EUR",
        deadline_close=date(2027, 1, 15),
        notes=(
            "LL.M. darajasi faqat birinchi diplomi huquq bo'yicha bo'lganlarga beriladi; "
            "boshqalar MLB oladi. Dasturga 8 haftalik amaliyot kiradi. 15-yanvargacha "
            "ariza bergan va 1-aprelgacha to'lovni tasdiqlaganlarga 2 000 EUR chegirma."
        ),
        notes_ru=(
            "Степень LL.M. получают только те, чей первый диплом — юридический; остальные получают "
            "MLB. В программу входит 8-недельная стажировка. Подавшим заявку до 15 января и "
            "подтвердившим оплату до 1 апреля — скидка 2 000 EUR."
        ),
        notes_en=(
            "The LL.M. degree is awarded only to those whose first degree is in law; others receive "
            "the MLB. The programme includes an 8-week internship. Applicants who apply by 15 "
            "January and confirm payment by 1 April get a EUR 2,000 discount."
        ),
        missing=("language_score",),
    ),
    # ------------------------------- Italiya -------------------------------
    LlmSeed(
        country_iso="IT",
        university="Bocconi University",
        city="Milan",
        website="https://www.unibocconi.it",
        timezone="Europe/Rome",
        program="LLM in Law of Technology and Automated Systems",
        source_url="https://www.unibocconi.it/en/programs/specialized-masters-programs/llm-law-technology-and-automated-systems/fee-and-financial-aid",
        intake_term="2026 Fall",
        tuition_amount=16000,
        tuition_currency="EUR",
        notes="Narx 2026/27 nashri uchun; o'quv materiallari va kampus xizmatlari kiradi.",
        notes_ru="Стоимость за выпуск 2026/27; включает учебные материалы и доступ к кампусу.",
        notes_en="Fee for the 2026/27 edition; includes course materials and campus facilities.",
        missing=("language_score", "deadline"),
    ),
    # ------------------------------- Chexiya -------------------------------
    LlmSeed(
        country_iso="CZ",
        university="Charles University, Faculty of Law",
        city="Praga",
        website="https://www.prf.cuni.cz",
        timezone="Europe/Prague",
        program="LL.M. Programme",
        source_url="https://www.prf.cuni.cz/en/llm/apply-now",
        intake_term="2027 Fall",
        tuition_amount=6950,
        tuition_currency="USD",
        deadline_close=date(2027, 4, 30),
        notes=(
            "Muddat viza talab qilinadigan arizachilar uchun (O'zbekiston fuqarolari shunga "
            "kiradi); vizasizlar uchun 1-iyul. Ariza yig'imi 200 USD, qaytarilmaydi. "
            "Erta ariza bergan va 14 kun ichida to'laganlarga narx 6 200 USD."
        ),
        notes_ru=(
            "Дедлайн для заявителей, которым нужна виза (граждане Узбекистана входят сюда); для "
            "остальных — 1 июля. Невозвратный сбор за заявку 200 USD. При ранней подаче и оплате в "
            "течение 14 дней стоимость 6 200 USD."
        ),
        notes_en=(
            "Deadline for applicants who need a visa (Uzbek citizens are in this group); 1 July for "
            "the rest. Non-refundable application fee USD 200. Early applicants who pay within 14 "
            "days get the fee reduced to USD 6,200."
        ),
        missing=("language_score",),
    ),
    # --------------------- Buyuk Britaniya (davomi) ---------------------
    # Edinburgh: IELTS 7.0 (Writing 7.0, qolganlari 6.5). Kampus dasturining
    # kontrakt narxi sahifada yo'q — e'lon qilingan raqam ONLAYN dastur uchun
    # edi, uni bu yerga yozish noto'g'ri bo'lardi.
    LlmSeed(
        country_iso="GB",
        university="University of Edinburgh",
        city="Edinburg",
        website="https://www.ed.ac.uk",
        timezone="Europe/London",
        program="Law LLM",
        source_url="https://study.ed.ac.uk/programmes/postgraduate-taught/167-law",
        intake_term="2026 Fall",
        ielts_min=7.0,
        missing=("tuition", "deadline"),
        documents=(
            "personal_statement",
            "degree_certificate",
            "transcript",
            "translation",
            "english_test",
        ),
        has_scholarship=True,
        scholarship_url="https://www.law.ed.ac.uk/study/masters-degrees/scholarships-funding",
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Edinburgh",
        city="Edinburg",
        website="https://www.ed.ac.uk",
        timezone="Europe/London",
        program="International Law LLM",
        source_url="https://study.ed.ac.uk/programmes/postgraduate-taught/166-international-law",
        intake_term="2026 Fall",
        ielts_min=7.0,
        missing=("tuition", "deadline"),
        documents=(
            "personal_statement",
            "degree_certificate",
            "transcript",
            "translation",
            "english_test",
        ),
        has_scholarship=True,
        scholarship_url="https://www.law.ed.ac.uk/study/masters-degrees/scholarships-funding",
    ),
    LlmSeed(
        country_iso="GB",
        university="University College London",
        city="London",
        website="https://www.ucl.ac.uk",
        timezone="Europe/London",
        program="Master of Laws (LLM)",
        source_url="https://www.ucl.ac.uk/laws/study/master-laws-llm-courses/master-laws-llm",
        intake_term="2026 Fall",
        notes=(
            "Ariza yig'imi 90 GBP. Overseas talabalar birinchi yil kontraktining "
            "10% depozitini to'laydi."
        ),
        notes_ru=(
            "Сбор за заявку 90 GBP. Студенты категории Overseas вносят депозит 10% от стоимости "
            "первого года."
        ),
        notes_en="Application fee GBP 90. Overseas students pay a deposit of 10% of the first-year fee.",
        missing=("tuition", "language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="GB",
        university="King's College London",
        city="London",
        website="https://www.kcl.ac.uk",
        timezone="Europe/London",
        program="Master of Laws (LLM)",
        source_url="https://www.kcl.ac.uk/study/postgraduate-taught/courses/master-of-laws-llm",
        intake_term="2026 Fall",
        # King's "Band B": umumiy 7.0, har bo'limda kamida 6.5.
        ielts_min=7.0,
        missing=("tuition", "deadline"),
        tuition_amount=38300,
        tuition_currency="GBP",
        documents=(
            "personal_statement",
            "transcript",
            "degree_certificate",
            "translation",
        ),
        notes=(
            "Narx 2026/27 uchun. DIQQAT: King's LL.M.ga TAVSIYANOMA talab qilinmaydi "
            "(raqobat yuqoriligi sababli). Motivatsion xat 4 000 belgigacha yoki 2 "
            "sahifagacha. CV ixtiyoriy. Xalqaro talabalar 2 000 GBP depozit to'laydi, "
            "u kontrakt hisobiga o'tadi."
        ),
        notes_ru=(
            "Стоимость за 2026/27. ВНИМАНИЕ: для LL.M. в King's НЕ требуются "
            "рекомендательные письма (из-за высокого конкурса). Мотивационное письмо до "
            "4 000 знаков или 2 страниц. CV по желанию. Международные студенты вносят "
            "депозит 2 000 GBP, он засчитывается в стоимость."
        ),
        notes_en=(
            "Fee for 2026/27. NOTE: King's does NOT require references for the LL.M. "
            "(because of competition for places). Personal statement up to 4,000 "
            "characters or 2 pages. A CV is optional. International students pay a GBP "
            "2,000 deposit, credited towards tuition."
        ),
    ),
    # Manchester huquq fakulteti bir nechta LL.M. beradi. Ingliz tili talabi
    # fakultetning hammasiga bir xil e'lon qilingan, KONTRAKT esa kurs bo'yicha
    # belgilanadi — shuning uchun narx faqat u aniq yozilgan "LLM Law"da bor.
    LlmSeed(
        country_iso="GB",
        university="University of Manchester",
        city="Manchester",
        website="https://www.manchester.ac.uk",
        timezone="Europe/London",
        program="LLM Law",
        source_url="https://www.manchester.ac.uk/study/masters/courses/list/08446/llm-law/",
        intake_term="2027 Fall",
        tuition_amount=31000,
        tuition_currency="GBP",
        ielts_min=7.0,
        toefl_min=100,
        # Manchester arizalarni to'rt bosqichda ko'rib chiqadi; bu — oxirgisi.
        deadline_close=date(2027, 7, 4),
        notes=(
            "Narx 2026-yil sentyabrdan boshlangan o'quv yili uchun (xalqaro talabalar). "
            "Ariza to'rt bosqichda ko'rib chiqiladi: 6-dekabr, 1-mart, 4-may, 4-iyul. "
            "Erta bosqichda joy ko'proq bo'ladi."
        ),
        notes_ru=(
            "Стоимость за учебный год, начавшийся в сентябре 2026 (международные студенты). "
            "Заявки рассматриваются в четыре этапа: 6 декабря, 1 марта, 4 мая, 4 июля. "
            "На ранних этапах мест больше."
        ),
        notes_en=(
            "Fee for the academic year that started in September 2026 (international students). "
            "Applications are reviewed in four stages: 6 December, 1 March, 4 May, 4 July. "
            "Earlier stages have more places available."
        ),
        missing=(),
        has_scholarship=True,
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Manchester",
        city="Manchester",
        website="https://www.manchester.ac.uk",
        timezone="Europe/London",
        program="LLM Public International Law",
        source_url="https://www.manchester.ac.uk/study/masters/courses/list/09644/llm-public-international-law/",
        intake_term="2026 Fall",
        ielts_min=7.0,
        toefl_min=100,
        missing=("tuition", "deadline"),
        has_scholarship=True,
        tuition_amount=31000,
        tuition_currency="GBP",
        deadline_close=date(2027, 7, 4),
        notes=(
            "Narx 2026-yilda boshlangan o'quv yili uchun (xalqaro talabalar); 2027 uchun "
            "hali belgilanmagan. Ariza to'rt bosqichda ko'rib chiqiladi: 6-dekabr, 1-mart, "
            "4-may, 4-iyul. Erta bosqichda joy ko'proq bo'ladi."
        ),
        notes_ru=(
            "Стоимость за учебный год, начавшийся в 2026 (международные студенты); на 2027 "
            "ещё не установлена. Заявки рассматриваются в четыре этапа: 6 декабря, 1 марта, "
            "4 мая, 4 июля. На ранних этапах мест больше."
        ),
        notes_en=(
            "Fee for the academic year that started in 2026 (international students); the 2027 "
            "fee is not set yet. Applications are reviewed in four stages: 6 December, 1 March, "
            "4 May, 4 July. Earlier stages have more places."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Manchester",
        city="Manchester",
        website="https://www.manchester.ac.uk",
        timezone="Europe/London",
        program="LLM International Business and Commercial Law",
        source_url="https://www.manchester.ac.uk/study/masters/courses/list/07991/llm-international-business-and-commercial-law/",
        intake_term="2026 Fall",
        ielts_min=7.0,
        toefl_min=100,
        missing=("tuition", "deadline"),
        has_scholarship=True,
        tuition_amount=31000,
        tuition_currency="GBP",
        deadline_close=date(2027, 7, 4),
        notes=(
            "Narx 2026-yilda boshlangan o'quv yili uchun (xalqaro talabalar); 2027 uchun "
            "hali belgilanmagan. Ariza to'rt bosqichda ko'rib chiqiladi: 6-dekabr, 1-mart, "
            "4-may, 4-iyul. Erta bosqichda joy ko'proq bo'ladi."
        ),
        notes_ru=(
            "Стоимость за учебный год, начавшийся в 2026 (международные студенты); на 2027 "
            "ещё не установлена. Заявки рассматриваются в четыре этапа: 6 декабря, 1 марта, "
            "4 мая, 4 июля. На ранних этапах мест больше."
        ),
        notes_en=(
            "Fee for the academic year that started in 2026 (international students); the 2027 "
            "fee is not set yet. Applications are reviewed in four stages: 6 December, 1 March, "
            "4 May, 4 July. Earlier stages have more places."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Manchester",
        city="Manchester",
        website="https://www.manchester.ac.uk",
        timezone="Europe/London",
        program="LLM International Financial Law",
        source_url="https://www.manchester.ac.uk/study/masters/courses/list/01060/llm-international-financial-law/",
        intake_term="2026 Fall",
        ielts_min=7.0,
        toefl_min=100,
        missing=("tuition", "deadline"),
        has_scholarship=True,
        tuition_amount=31000,
        tuition_currency="GBP",
        deadline_close=date(2027, 7, 4),
        notes=(
            "Narx 2026-yilda boshlangan o'quv yili uchun (xalqaro talabalar); 2027 uchun "
            "hali belgilanmagan. Ariza to'rt bosqichda ko'rib chiqiladi: 6-dekabr, 1-mart, "
            "4-may, 4-iyul. Erta bosqichda joy ko'proq bo'ladi."
        ),
        notes_ru=(
            "Стоимость за учебный год, начавшийся в 2026 (международные студенты); на 2027 "
            "ещё не установлена. Заявки рассматриваются в четыре этапа: 6 декабря, 1 марта, "
            "4 мая, 4 июля. На ранних этапах мест больше."
        ),
        notes_en=(
            "Fee for the academic year that started in 2026 (international students); the 2027 "
            "fee is not set yet. Applications are reviewed in four stages: 6 December, 1 March, "
            "4 May, 4 July. Earlier stages have more places."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Manchester",
        city="Manchester",
        website="https://www.manchester.ac.uk",
        timezone="Europe/London",
        program="LLM International Economic Law",
        source_url="https://www.manchester.ac.uk/study/masters/courses/list/18222/llm-international-economic-law/",
        intake_term="2026 Fall",
        ielts_min=7.0,
        toefl_min=100,
        missing=("tuition", "deadline"),
        has_scholarship=True,
        tuition_amount=31000,
        tuition_currency="GBP",
        deadline_close=date(2027, 7, 4),
        notes=(
            "Narx 2026-yilda boshlangan o'quv yili uchun (xalqaro talabalar); 2027 uchun "
            "hali belgilanmagan. Ariza to'rt bosqichda ko'rib chiqiladi: 6-dekabr, 1-mart, "
            "4-may, 4-iyul. Erta bosqichda joy ko'proq bo'ladi."
        ),
        notes_ru=(
            "Стоимость за учебный год, начавшийся в 2026 (международные студенты); на 2027 "
            "ещё не установлена. Заявки рассматриваются в четыре этапа: 6 декабря, 1 марта, "
            "4 мая, 4 июля. На ранних этапах мест больше."
        ),
        notes_en=(
            "Fee for the academic year that started in 2026 (international students); the 2027 "
            "fee is not set yet. Applications are reviewed in four stages: 6 December, 1 March, "
            "4 May, 4 July. Earlier stages have more places."
        ),
    ),
    # ------------------- Buyuk Britaniya (to'rtinchi to'plam) -------------------
    # Leeds: uchala dastur ham bir xil narx/ball/muddatga ega — har biri
    # ALOHIDA kurs sahifasidan tasdiqlandi, bittasidan ko'chirilmadi.
    LlmSeed(
        country_iso="GB",
        university="University of Leeds",
        city="Lids",
        website="https://www.leeds.ac.uk",
        timezone="Europe/London",
        program="International Business Law LLM",
        source_url="https://courses.leeds.ac.uk/e461/international-business-law-llm",
        intake_term="2027 Fall",
        tuition_amount=29600,
        tuition_currency="GBP",
        ielts_min=6.5,
        deadline_close=date(2027, 7, 30),
        notes=(
            "Narx butun dastur uchun (12 oy). IELTS'da har bir bo'limda kamida 6.0 kerak. "
            "Muddat xalqaro talabalar uchun; Britaniya fuqarolariga 10-sentyabr."
        ),
        notes_ru=(
            "Стоимость за всю программу (12 месяцев). В IELTS нужно минимум 6.0 в каждом "
            "разделе. Дедлайн для международных студентов; для граждан Великобритании — "
            "10 сентября."
        ),
        notes_en=(
            "The fee covers the whole 12-month programme. IELTS requires at least 6.0 in "
            "each component. The deadline shown is for international applicants; UK "
            "applicants have until 10 September."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Leeds",
        city="Lids",
        website="https://www.leeds.ac.uk",
        timezone="Europe/London",
        program="International Human Rights Law LLM",
        source_url="https://courses.leeds.ac.uk/i325/international-human-rights-law-llm",
        intake_term="2027 Fall",
        tuition_amount=29600,
        tuition_currency="GBP",
        ielts_min=6.5,
        deadline_close=date(2027, 7, 30),
        notes="Narx butun dastur uchun (12 oy). IELTS'da har bo'limda kamida 6.0.",
        notes_ru="Стоимость за всю программу (12 месяцев). В IELTS минимум 6.0 в каждом разделе.",
        notes_en=(
            "The fee covers the whole 12-month programme. IELTS requires at least 6.0 in "
            "each component."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Leeds",
        city="Lids",
        website="https://www.leeds.ac.uk",
        timezone="Europe/London",
        program="International Banking and Finance Law LLM",
        source_url="https://courses.leeds.ac.uk/f712/international-banking-and-finance-law-llm",
        intake_term="2027 Fall",
        tuition_amount=29600,
        tuition_currency="GBP",
        ielts_min=6.5,
        deadline_close=date(2027, 7, 30),
        notes="Narx butun dastur uchun (12 oy). IELTS'da har bo'limda kamida 6.0.",
        notes_ru="Стоимость за всю программу (12 месяцев). В IELTS минимум 6.0 в каждом разделе.",
        notes_en=(
            "The fee covers the whole 12-month programme. IELTS requires at least 6.0 in "
            "each component."
        ),
    ),
    # Warwick: muddat va til talabi universitet bo'yicha umumiy, narx esa
    # kurs sahifasida ko'rsatilmagan.
    LlmSeed(
        country_iso="GB",
        university="University of Warwick",
        city="Koventri",
        website="https://warwick.ac.uk",
        timezone="Europe/London",
        program="Advanced Legal Studies LLM",
        source_url="https://warwick.ac.uk/study/postgraduate/courses/llm-advanced-legal-studies/",
        intake_term="2027 Fall",
        ielts_min=7.0,
        deadline_close=date(2027, 8, 2),
        notes=(
            "Dars 27-sentyabrda boshlanadi. IELTS: umumiy 7.0, ikkita bo'limda 6.0/6.5 "
            "bo'lishi mumkin, qolganlari 7.0 dan kam emas."
        ),
        notes_ru=(
            "Занятия начинаются 27 сентября. IELTS: общий 7.0, в двух разделах допускается "
            "6.0/6.5, остальные не ниже 7.0."
        ),
        notes_en=(
            "Teaching starts on 27 September. IELTS: 7.0 overall; two components may be "
            "6.0/6.5, the rest must be 7.0 or above."
        ),
        missing=("tuition",),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Warwick",
        city="Koventri",
        website="https://warwick.ac.uk",
        timezone="Europe/London",
        program="International Commercial Law LLM",
        source_url="https://warwick.ac.uk/study/postgraduate/courses/llm-international-commercial-law/",
        intake_term="2027 Fall",
        ielts_min=7.0,
        deadline_close=date(2027, 8, 2),
        notes="Dars 27-sentyabrda boshlanadi. IELTS'da ikkita bo'limda 6.0/6.5 bo'lishi mumkin.",
        notes_ru="Занятия начинаются 27 сентября. В IELTS два раздела могут быть 6.0/6.5.",
        notes_en=(
            "Teaching starts on 27 September. Two IELTS components may be 6.0/6.5."
        ),
        missing=("tuition",),
    ),
    # Cambridge: narx sahifada dinamik yuklanadi, olinmadi.
    LlmSeed(
        country_iso="GB",
        university="University of Cambridge",
        city="Kembrij",
        website="https://www.cam.ac.uk",
        timezone="Europe/London",
        program="Master of Law (LLM)",
        source_url="https://www.postgraduate.study.cam.ac.uk/courses/directory/lwlwllll",
        intake_term="2027 Fall",
        # 9 oy: oktyabrdan iyungacha
        duration_years=0.8,
        ielts_min=7.5,
        notes=(
            "Dastur 9 oy davom etadi: oktyabrda boshlanib iyunda tugaydi — boshqa UK "
            "LL.M.lari odatda 12 oy. IELTS talabi ro'yxatdagi eng yuqorisi: umumiy 7.5 va "
            "HAR BIR bo'limda kamida 7.0. Til testi ariza bilan BIRGA topshiriladi. "
            "2026-27 qabuli uchun muddat 2025-yil 2-dekabr edi — Cambridge har yili dekabr "
            "boshida yopadi, aniq sanani rasmiy saytdan tasdiqlang."
        ),
        notes_ru=(
            "Программа длится 9 месяцев: с октября по июнь — другие LL.M. в Великобритании "
            "обычно 12 месяцев. Требование по IELTS самое высокое в списке: общий 7.5 и "
            "минимум 7.0 в КАЖДОМ разделе. Языковой тест подаётся ВМЕСТЕ с заявкой. Для "
            "набора 2026-27 дедлайн был 2 декабря 2025 — Кембридж закрывает приём в начале "
            "декабря каждый год, уточните точную дату на официальном сайте."
        ),
        notes_en=(
            "The programme runs for 9 months, October to June — other UK LL.M.s are usually "
            "12 months. The IELTS requirement is the highest on this list: 7.5 overall and at "
            "least 7.0 in EVERY component. The language test must be submitted WITH the "
            "application. For 2026-27 entry the deadline was 2 December 2025 — Cambridge "
            "closes in early December each year; confirm the exact date on the official site."
        ),
        missing=("tuition", "deadline"),
    ),
    # ---------------------------- AQSH (davomi) ----------------------------
    LlmSeed(
        country_iso="US",
        university="UC Berkeley School of Law",
        city="Berkeley, CA",
        website="https://www.law.berkeley.edu",
        timezone="America/Los_Angeles",
        program="Master of Laws (LL.M.)",
        source_url="https://www.law.berkeley.edu/llm-jsd/tuition-costs/",
        intake_term="2027 Fall",
        notes=(
            "Qabul qilinganlar 1 000 USD qaytarilmaydigan depozit to'laydi, "
            "u kontrakt hisobiga o'tadi."
        ),
        notes_ru="Зачисленные вносят невозвратный депозит 1 000 USD, он засчитывается в стоимость.",
        notes_en="Admitted students pay a non-refundable USD 1,000 deposit, credited towards tuition.",
        missing=("tuition", "language_score", "deadline"),
    ),
    # -------------------------- Germaniya (davomi) --------------------------
    LlmSeed(
        country_iso="DE",
        university="Goethe University Frankfurt (ILF)",
        city="Frankfurt",
        website="https://www.ilf-frankfurt.de",
        timezone="Europe/Berlin",
        program="LL.M. Finance",
        source_url="https://www.ilf-frankfurt.de/llm-finance",
        intake_term="2026 Fall",
        tuition_amount=23000,
        tuition_currency="EUR",
        ielts_min=7.0,
        toefl_min=100,
        notes=(
            "Narx 2026/27 uchun, to'liq kunlik shakl (yarim kunlik 27 000 EUR). Bundan "
            "tashqari har semestr uchun universitetning ~380 EUR yig'imi bor. Ariza yig'imi "
            "yo'q, qabul uzluksiz (rolling) — navbat tartibida. TOEFL iBT'da har bo'limda "
            "kamida 22 ball kerak."
        ),
        notes_ru=(
            "Стоимость за 2026/27, очная форма (заочная — 27 000 EUR). Дополнительно "
            "университетский сбор ~380 EUR за семестр. Сбора за заявку нет, приём непрерывный в "
            "порядке очереди. В TOEFL iBT нужно минимум 22 балла в каждой секции."
        ),
        notes_en=(
            "Fee for 2026/27, full-time (part-time EUR 27,000). There is also a university semester "
            "contribution of about EUR 380. No application fee; admission is rolling, first come "
            "first served. TOEFL iBT requires at least 22 in each section."
        ),
    ),
    LlmSeed(
        country_iso="DE",
        university="Goethe University Frankfurt (ILF)",
        city="Frankfurt",
        website="https://www.ilf-frankfurt.de",
        timezone="Europe/Berlin",
        program="LL.M. International Finance",
        source_url="https://www.ilf-frankfurt.de/llm-programs/llm-international-finance/fees-and-application",
        intake_term="2027 Fall",
        tuition_amount=20000,
        tuition_currency="EUR",
        ielts_min=6.5,
        toefl_min=92,
        documents=(
            "cv",
            "personal_statement",
            "degree_certificate",
            "transcript",
            "english_test",
            "reference",
            "passport",
        ),
        has_scholarship=True,
        scholarship_url="https://www.ilf-frankfurt.de/llm-programs/llm-international-finance/fees-and-application",
        notes=(
            "Kontrakt 2026/27 o'quv yili uchun 20 000 EUR. Erta ariza chegirmasi: 15-yanvargacha "
            "bergan bo'lsangiz 3 000 EUR (15%), 28-fevralgacha bergan bo'lsangiz 2 000 EUR "
            "(10%). Til talabi: IELTS 6.5, TOEFL iBT 92 (qog'ozli 580, CBT 237) yoki Cambridge "
            "CAE «C» va undan yuqori. Hujjatlar orasida ikkita muhrlangan tavsiyanoma va kurs "
            "reytingi haqidagi ma'lumotnoma bor; Xitoy, Hindiston, Mo'g'uliston va Vetnam "
            "arizachilariga APS sertifikati kerak. 2026/27 uchun muddatlar: shu to'rt davlat "
            "uchun 15-may 2026, qolganlar uchun 1-iyul 2026 edi — keyingi yil sanalari sahifada "
            "hali e'lon qilinmagan."
        ),
        notes_ru=(
            "Стоимость на 2026/27 учебный год — 20 000 EUR. Скидка за раннюю подачу: 3 000 EUR "
            "(15%) при подаче до 15 января и 2 000 EUR (10%) при подаче до 28 февраля. Языковые "
            "требования: IELTS 6.5, TOEFL iBT 92 (бумажный 580, CBT 237) или Cambridge CAE "
            "уровня «C» и выше. Среди документов — два запечатанных рекомендательных письма и "
            "справка о месте в рейтинге курса; абитуриентам из Китая, Индии, Монголии и Вьетнама "
            "нужен сертификат APS. Дедлайны на 2026/27: 15 мая 2026 для этих четырёх стран и "
            "1 июля 2026 для остальных — даты на следующий год ещё не опубликованы."
        ),
        notes_en=(
            "Tuition for the 2026/27 academic year is EUR 20,000. Early-application discounts: "
            "EUR 3,000 (15%) for applying by 15 January and EUR 2,000 (10%) by 28 February. "
            "Language requirements: IELTS 6.5, TOEFL iBT 92 (paper-based 580, CBT 237) or "
            "Cambridge CAE at grade C or above. The documents include two sealed letters of "
            "recommendation and a confirmation of class rank; applicants from China, India, "
            "Mongolia and Vietnam need an APS certificate. The 2026/27 deadlines were 15 May "
            "2026 for those four countries and 1 July 2026 for everyone else; next year's dates "
            "are not yet published."
        ),
        missing=("deadline",),
    ),
    # ------------------------------- Polsha -------------------------------
    LlmSeed(
        country_iso="PL",
        university="Jagiellonian University",
        city="Krakov",
        website="https://www.uj.edu.pl",
        timezone="Europe/Warsaw",
        program="LL.M. in EU and EEA Law",
        source_url="https://okspo.wpia.uj.edu.pl/llm",
        intake_term="2026 Fall",
        notes=(
            "DIQQAT: bepul o'qish faqat EU/EEA/Shveytsariya rezidentlari uchun. "
            "O'zbekiston fuqarolari uchun narx sahifada ko'rsatilmagan — universitetdan "
            "aniqlashtiring."
        ),
        notes_ru=(
            "ВНИМАНИЕ: бесплатное обучение только для резидентов ЕС/ЕЭЗ/Швейцарии. Для граждан "
            "Узбекистана стоимость на сайте не указана — уточняйте в университете."
        ),
        notes_en=(
            "NOTE: tuition-free study applies only to EU/EEA/Swiss residents. The fee for Uzbek "
            "citizens is not stated on the page — check with the university."
        ),
        missing=("tuition", "language_score", "deadline"),
    ),
    # ------------------- Buyuk Britaniya (uchinchi to'plam) -------------------
    LlmSeed(
        country_iso="GB",
        university="University of Nottingham",
        city="Nottingem",
        website="https://www.nottingham.ac.uk",
        timezone="Europe/London",
        program="International Law LLM",
        source_url="https://www.nottingham.ac.uk/pgstudy/course/taught/international-law-llm",
        intake_term="2027 Fall",
        tuition_amount=26900,
        tuition_currency="GBP",
        # IELTS 6.5 (Writing va Reading 6.5 dan, Speaking va Listening 6.0 dan kam emas)
        ielts_min=6.5,
        missing=("deadline",),
        has_scholarship=True,
    ),
    # Glasgow: huquq LL.M.larining narxi va tili talabi bir xil e'lon qilingan
    # (har bir kurs sahifasida alohida yozilgan, taxmin qilinmadi).
    LlmSeed(
        country_iso="GB",
        university="University of Glasgow",
        city="Glazgo",
        website="https://www.gla.ac.uk",
        timezone="Europe/London",
        program="International Law LLM",
        source_url="https://www.gla.ac.uk/postgraduate/taught/internationallaw/",
        intake_term="2026 Fall",
        tuition_amount=29355,
        tuition_currency="GBP",
        ielts_min=7.0,
        missing=("deadline",),
        documents=(
            "degree_certificate",
            "transcript",
            "translation",
            "reference",
            "english_test",
            "passport",
        ),
        has_scholarship=True,
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Glasgow",
        city="Glazgo",
        website="https://www.gla.ac.uk",
        timezone="Europe/London",
        program="International Commercial Law LLM",
        source_url="https://www.gla.ac.uk/postgraduate/taught/internationalcommerciallaw/",
        intake_term="2026 Fall",
        tuition_amount=29355,
        tuition_currency="GBP",
        ielts_min=7.0,
        missing=("deadline",),
        documents=(
            "degree_certificate",
            "transcript",
            "translation",
            "reference",
            "english_test",
            "passport",
        ),
        has_scholarship=True,
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Glasgow",
        city="Glazgo",
        website="https://www.gla.ac.uk",
        timezone="Europe/London",
        program="Corporate & Financial Law LLM",
        source_url="https://www.gla.ac.uk/postgraduate/taught/corporateandfinanciallaw/",
        intake_term="2026 Fall",
        tuition_amount=29355,
        tuition_currency="GBP",
        ielts_min=7.0,
        missing=("deadline",),
        documents=(
            "degree_certificate",
            "transcript",
            "translation",
            "reference",
            "english_test",
            "passport",
        ),
        has_scholarship=True,
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Glasgow",
        city="Glazgo",
        website="https://www.gla.ac.uk",
        timezone="Europe/London",
        program="International Law & Security LLM",
        source_url="https://www.gla.ac.uk/postgraduate/taught/internationallawandsecurity/",
        intake_term="2026 Fall",
        tuition_amount=29355,
        tuition_currency="GBP",
        ielts_min=7.0,
        missing=("deadline",),
        documents=(
            "degree_certificate",
            "transcript",
            "translation",
            "reference",
            "english_test",
            "passport",
        ),
        has_scholarship=True,
    ),
    LlmSeed(
        country_iso="GB",
        university="Durham University",
        city="Daram",
        website="https://www.durham.ac.uk",
        timezone="Europe/London",
        program="Master of Laws (LLM)",
        source_url="https://www.durham.ac.uk/study/courses/master-of-laws-m1k116/",
        intake_term="2026 Fall",
        notes=(
            "Xalqaro talabalar uchun 'Inspiring Excellence' stipendiyasi bor: kontraktdan "
            "5 000 yoki 10 000 GBP chegirma, birinchi bosqich muddati 16-yanvar."
        ),
        notes_ru=(
            "Для международных студентов есть стипендия «Inspiring Excellence»: скидка 5 000 или 10 "
            "000 GBP, дедлайн первого раунда — 16 января."
        ),
        notes_en=(
            "International students can apply for the 'Inspiring Excellence' scholarship: a GBP "
            "5,000 or 10,000 fee discount, first-round deadline 16 January."
        ),
        missing=("tuition", "language_score", "deadline"),
        ielts_min=7.0,
    ),
    # --------------------------- Italiya (davomi) ---------------------------
    LlmSeed(
        country_iso="IT",
        university="Bocconi University",
        city="Milan",
        website="https://www.unibocconi.it",
        timezone="Europe/Rome",
        program="LLM in European Business and Social Law",
        source_url="https://www.unibocconi.it/en/programs/specialized-masters-programs/llm-european-business-and-social-law/fees-and-financial-aid",
        intake_term="2026 Fall",
        tuition_amount=16000,
        tuition_currency="EUR",
        notes="Narx 2025/26 nashri uchun e'lon qilingan.",
        notes_ru="Стоимость объявлена для выпуска 2025/26.",
        notes_en="Fee published for the 2025/26 edition.",
        missing=("language_score", "deadline"),
    ),
    # ------------------- Germaniya (uchinchi to'plam) -------------------
    LlmSeed(
        country_iso="DE",
        university="Humboldt University of Berlin",
        city="Berlin",
        website="https://www.rewi.hu-berlin.de",
        timezone="Europe/Berlin",
        program="International Dispute Resolution (IDR LL.M.)",
        source_url="https://www.rewi.hu-berlin.de/en/sp/angebote/master/idr/about-the-idr-master-program/tuition-fees",
        intake_term="2026 Fall",
        tuition_amount=12900,
        tuition_currency="EUR",
        notes=(
            "Jami 12 900 EUR (semestriga 6 450). Bundan tashqari har semestr uchun talabalar "
            "uyushmasi badali ~355 EUR. Qabul qilingach 2 hafta ichida 2 250 EUR oldindan "
            "to'lov kerak. Kontraktdan chegirma (to'liq yoki qisman) uchun ariza muddati "
            "31-mart. Arizalar uni-assist orqali topshiriladi."
        ),
        notes_ru=(
            "Всего 12 900 EUR (6 450 за семестр). Дополнительно взнос студенческого союза ~355 EUR "
            "за семестр. После зачисления в течение 2 недель нужно внести 2 250 EUR. Дедлайн заявки "
            "на скидку (полную или частичную) — 31 марта. Заявки подаются через uni-assist."
        ),
        notes_en=(
            "EUR 12,900 in total (EUR 6,450 per semester). There is also a student union "
            "contribution of about EUR 355 per semester. Admitted students must pay EUR 2,250 "
            "within two weeks. The deadline to apply for a full or partial fee waiver is 31 March. "
            "Applications go through uni-assist."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="Humboldt University of Berlin",
        city="Berlin",
        website="https://www.rewi.hu-berlin.de",
        timezone="Europe/Berlin",
        program="Humboldt Master of Laws (LL.M.)",
        source_url="https://humboldt-llm.hu-berlin.de/fees-and-schloarships",
        intake_term="2026 Fall",
        tuition_amount=15000,
        tuition_currency="EUR",
        notes="Jami 15 000 EUR (semestriga 7 500).",
        notes_ru="Всего 15 000 EUR (7 500 за семестр).",
        notes_en="EUR 15,000 in total (EUR 7,500 per semester).",
        missing=("language_score", "deadline"),
    ),
    # ------------------- Buyuk Britaniya (beshinchi to'plam) -------------------
    LlmSeed(
        country_iso="GB",
        university="University of Bristol",
        city="Bristol",
        website="https://www.bristol.ac.uk",
        timezone="Europe/London",
        program="Law - International Law LLM",
        source_url="https://www.bristol.ac.uk/study/postgraduate/taught/llm-law---international-law/",
        intake_term="2027 Fall",
        tuition_amount=29800,
        tuition_currency="GBP",
        ielts_min=7.0,
        deadline_close=date(2027, 8, 12),
        documents=(
            "transcript",
            "degree_certificate",
            "translation",
            "personal_statement",
            "reference",
            "english_test",
        ),
        has_scholarship=True,
        scholarship_url="https://www.bristol.ac.uk/law/courses/postgraduate/scholarships/",
        notes=(
            "Narx 2027/28 o'quv yili uchun (xalqaro talabalar). Xorijiy arizachilar uchun "
            "muddat — 12-avgust, lekin joylar undan oldin to'lishi mumkin. IELTS: umumiy "
            "7.0, har bir bo'limda kamida 6.5 (Profile B). Bristol yuridik fakulteti «Think "
            "Big about Law and Justice» stipendiyasini beradi; bitiruvchilarga 25% chegirma."
        ),
        notes_ru=(
            "Стоимость на 2027/28 "
            "учебный год "
            "(международны"
            "е студенты). "
            "Дедлайн для "
            "зарубежных "
            "абитуриентов "
            "— 12 августа, но "
            "места могут "
            "закончиться "
            "раньше. IELTS: 7.0 общи"
            "й, не менее 6.5 в "
            "каждом разде"
            "ле (Profile B). Юридиче"
            "ский факульт"
            "ет Бристоля "
            "даёт стипенд"
            "ию «Think Big about Law and Justice»; "
            "выпускникам "
            "— скидка 25%."
        ),
        notes_en=(
            "Fee for the 2027/28 academic year (international students). The deadline for "
            "overseas applicants is 12 August, but places may fill earlier. IELTS: 7.0 overall "
            "with at least 6.5 in each band (Profile B). Bristol Law School offers «Think "
            "Big about Law and Justice» scholarships; alumni get a 25% discount."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Bristol",
        city="Bristol",
        website="https://www.bristol.ac.uk",
        timezone="Europe/London",
        program="Law - International Commercial Law LLM",
        source_url="https://www.bristol.ac.uk/study/postgraduate/taught/llm-law---international-commercial-law/",
        intake_term="2027 Fall",
        tuition_amount=29800,
        tuition_currency="GBP",
        ielts_min=7.0,
        deadline_close=date(2027, 8, 12),
        documents=(
            "transcript",
            "degree_certificate",
            "translation",
            "personal_statement",
            "reference",
            "english_test",
        ),
        has_scholarship=True,
        scholarship_url="https://www.bristol.ac.uk/law/courses/postgraduate/scholarships/",
        notes=(
            "Narx 2027/28 o'quv yili uchun (xalqaro talabalar). Xorijiy arizachilar uchun "
            "muddat — 12-avgust, lekin joylar undan oldin to'lishi mumkin. IELTS: umumiy "
            "7.0, har bir bo'limda kamida 6.5 (Profile B). Bristol yuridik fakulteti «Think "
            "Big about Law and Justice» stipendiyasini beradi; bitiruvchilarga 25% chegirma."
        ),
        notes_ru=(
            "Стоимость на 2027/28 "
            "учебный год "
            "(международны"
            "е студенты). "
            "Дедлайн для "
            "зарубежных "
            "абитуриентов "
            "— 12 августа, но "
            "места могут "
            "закончиться "
            "раньше. IELTS: 7.0 общи"
            "й, не менее 6.5 в "
            "каждом разде"
            "ле (Profile B). Юридиче"
            "ский факульт"
            "ет Бристоля "
            "даёт стипенд"
            "ию «Think Big about Law and Justice»; "
            "выпускникам "
            "— скидка 25%."
        ),
        notes_en=(
            "Fee for the 2027/28 academic year (international students). The deadline for "
            "overseas applicants is 12 August, but places may fill earlier. IELTS: 7.0 overall "
            "with at least 6.5 in each band (Profile B). Bristol Law School offers «Think "
            "Big about Law and Justice» scholarships; alumni get a 25% discount."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Bristol",
        city="Bristol",
        website="https://www.bristol.ac.uk",
        timezone="Europe/London",
        program="Law - Human Rights Law LLM",
        source_url="https://www.bristol.ac.uk/study/postgraduate/taught/llm-law---human-rights-law/",
        intake_term="2027 Fall",
        tuition_amount=29800,
        tuition_currency="GBP",
        ielts_min=7.0,
        deadline_close=date(2027, 8, 12),
        documents=(
            "transcript",
            "degree_certificate",
            "translation",
            "personal_statement",
            "reference",
            "english_test",
        ),
        has_scholarship=True,
        scholarship_url="https://www.bristol.ac.uk/law/courses/postgraduate/scholarships/",
        notes=(
            "Narx 2027/28 o'quv yili uchun (xalqaro talabalar). Xorijiy arizachilar uchun "
            "muddat — 12-avgust, lekin joylar undan oldin to'lishi mumkin. IELTS: umumiy "
            "7.0, har bir bo'limda kamida 6.5 (Profile B). Bristol yuridik fakulteti «Think "
            "Big about Law and Justice» stipendiyasini beradi; bitiruvchilarga 25% chegirma."
        ),
        notes_ru=(
            "Стоимость на 2027/28 "
            "учебный год "
            "(международны"
            "е студенты). "
            "Дедлайн для "
            "зарубежных "
            "абитуриентов "
            "— 12 августа, но "
            "места могут "
            "закончиться "
            "раньше. IELTS: 7.0 общи"
            "й, не менее 6.5 в "
            "каждом разде"
            "ле (Profile B). Юридиче"
            "ский факульт"
            "ет Бристоля "
            "даёт стипенд"
            "ию «Think Big about Law and Justice»; "
            "выпускникам "
            "— скидка 25%."
        ),
        notes_en=(
            "Fee for the 2027/28 academic year (international students). The deadline for "
            "overseas applicants is 12 August, but places may fill earlier. IELTS: 7.0 overall "
            "with at least 6.5 in each band (Profile B). Bristol Law School offers «Think "
            "Big about Law and Justice» scholarships; alumni get a 25% discount."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Exeter",
        city="Ekseter",
        website="https://www.exeter.ac.uk",
        timezone="Europe/London",
        program="LLM Master of Laws",
        source_url="https://www.exeter.ac.uk/study/postgraduate/courses/law/masteroflaws/",
        intake_term="2026 Fall",
        tuition_amount=25550,
        tuition_currency="GBP",
        missing=("language_score", "deadline"),
        documents=(
            "transcript",
            "degree_certificate",
            "translation",
            "personal_statement",
            "reference",
            "english_test",
        ),
        has_scholarship=True,
        scholarship_url="https://www.exeter.ac.uk/study/funding/",
        notes=(
            "Narx 2026/27 uchun (xalqaro talabalar, to'liq kunduzgi). Kirish uchun 2:2 darajali "
            "diplom yetarli, huquq bo'yicha oldingi ta'lim talab qilinmaydi. Ingliz tili talabi "
            "sahifada «Profile B1» deb beriladi — aniq ball universitetning til "
            "talablari sahifasida. Stipendiyalar: Exeter Excellence Scholarships; "
            "bitiruvchilarga birinchi yil kontraktining 20% chegirmasi."
        ),
        notes_ru=(
            "Стоимость на "
            "2026/27 (международ"
            "ные студенты, "
            "очно). Для пост"
            "упления дост"
            "аточно дипло"
            "ма уровня 2:2, "
            "предыдущее "
            "юридическое "
            "образование "
            "не требуется. "
            "Требование п"
            "о английском"
            "у указано как "
            "«Profile B1» — точный "
            "балл на стран"
            "ице языковых "
            "требований. "
            "Стипендии: Exeter Excellence "
            "Scholarships; выпускник"
            "ам — скидка 20% на "
            "первый год."
        ),
        notes_en=(
            "Fee for 2026/27 (international students, full-time). A 2:2 honours degree is enough "
            "and no prior law study is required. The English requirement is given as "
            "«Profile B1» — the exact score is on the university's language "
            "requirements page. Funding: Exeter Excellence Scholarships; alumni receive a 20% "
            "first-year tuition discount."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Exeter",
        city="Ekseter",
        website="https://www.exeter.ac.uk",
        timezone="Europe/London",
        program="LLM International Commercial Law",
        source_url="https://www.exeter.ac.uk/study/postgraduate/courses/law/law-international-commercial/",
        intake_term="2026 Fall",
        tuition_amount=25550,
        tuition_currency="GBP",
        missing=("language_score", "deadline"),
        documents=(
            "transcript",
            "degree_certificate",
            "translation",
            "personal_statement",
            "reference",
            "english_test",
        ),
        has_scholarship=True,
        scholarship_url="https://www.exeter.ac.uk/study/funding/",
        notes=(
            "Narx 2026/27 uchun (xalqaro talabalar, to'liq kunduzgi). Kirish uchun 2:2 darajali "
            "diplom yetarli, huquq bo'yicha oldingi ta'lim talab qilinmaydi. Ingliz tili talabi "
            "sahifada «Profile B1» deb beriladi — aniq ball universitetning til "
            "talablari sahifasida. Stipendiyalar: Exeter Excellence Scholarships; "
            "bitiruvchilarga birinchi yil kontraktining 20% chegirmasi."
        ),
        notes_ru=(
            "Стоимость на "
            "2026/27 (международ"
            "ные студенты, "
            "очно). Для пост"
            "упления дост"
            "аточно дипло"
            "ма уровня 2:2, "
            "предыдущее "
            "юридическое "
            "образование "
            "не требуется. "
            "Требование п"
            "о английском"
            "у указано как "
            "«Profile B1» — точный "
            "балл на стран"
            "ице языковых "
            "требований. "
            "Стипендии: Exeter Excellence "
            "Scholarships; выпускник"
            "ам — скидка 20% на "
            "первый год."
        ),
        notes_en=(
            "Fee for 2026/27 (international students, full-time). A 2:2 honours degree is enough "
            "and no prior law study is required. The English requirement is given as "
            "«Profile B1» — the exact score is on the university's language "
            "requirements page. Funding: Exeter Excellence Scholarships; alumni receive a 20% "
            "first-year tuition discount."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="SOAS University of London",
        city="London",
        website="https://www.soas.ac.uk",
        timezone="Europe/London",
        program="LLM International Law",
        source_url="https://www.soas.ac.uk/study/find-course/llm-international-law",
        intake_term="2026 Fall",
        tuition_amount=27840,
        tuition_currency="GBP",
        missing=("language_score", "deadline"),
        notes=(
            "Narx xalqaro talabalar uchun, bir yillik to'liq kunduzgi o'qish. SOAS kurs "
            "sahifasida IELTS balli ham, ariza muddati ham ko'rsatilmagan — ularni qabul "
            "bo'limidan aniqlash kerak."
        ),
        notes_ru=(
            "Стоимость для "
            "международны"
            "х студентов, "
            "один год очно"
            "го обучения. Н"
            "а странице ку"
            "рса SOAS не указа"
            "ны ни балл IELTS, ни "
            "дедлайн — их "
            "нужно уточни"
            "ть в приёмной "
            "комиссии."
        ),
        notes_en=(
            "Fee for international students, one year full-time. The SOAS course page states "
            "neither an IELTS score nor an application deadline — check both with "
            "admissions."
        ),
    ),
    LlmSeed(
        country_iso="GB",
        university="University of Birmingham",
        city="Birmingem",
        website="https://www.birmingham.ac.uk",
        timezone="Europe/London",
        program="General Law LLM",
        source_url="https://www.birmingham.ac.uk/study/postgraduate/subjects/law-courses/general-law-llm",
        intake_term="2027 Fall",
        ielts_min=6.5,
        toefl_min=88,
        missing=("tuition", "deadline"),
        notes=(
            "IELTS 6.5, har bir bo'limda kamida 6.0 (TOEFL: umumiy 88). Kirish uchun 2:1 "
            "darajali huquq diplomi yoki unga teng ta'lim/ish tajribasi. Kontrakt summasi kurs "
            "sahifasida ko'rsatilmagan. Xalqaro talabalar CAS olishdan oldin depozit to'laydi."
        ),
        notes_ru=(
            "IELTS 6.5, не менее 6.0 в "
            "каждом разде"
            "ле (TOEFL: 88 общий). Дл"
            "я поступлени"
            "я нужен дипло"
            "м уровня 2:1 по "
            "праву либо "
            "равноценное "
            "образование "
            "или опыт рабо"
            "ты. Сумма конт"
            "ракта на стра"
            "нице курса не "
            "указана. Межд"
            "ународные ст"
            "уденты внося"
            "т депозит до "
            "получения CAS."
        ),
        notes_en=(
            "IELTS 6.5 with no less than 6.0 in any band (TOEFL: 88 overall). Entry requires a "
            "2:1 honours degree in law, or equivalent study or professional experience. The "
            "tuition figure is not stated on the course page. International students pay a "
            "deposit before a CAS is issued."
        ),
    ),
    # ------------------- Germaniya (to'rtinchi to'plam) -------------------
    LlmSeed(
        country_iso="DE",
        university="Ludwig Maximilian University of Munich",
        city="Myunxen",
        website="https://www.jura.lmu.de",
        timezone="Europe/Berlin",
        program="European and International Economic Law (LL.M.)",
        source_url="https://www.jura.lmu.de/en/study/aufbaustudium-ll.m/european-and-international-economic-law-ll.m/",
        intake_term="2027 Fall",
        tuition_amount=0,
        tuition_currency="EUR",
        documents=(
            "degree_certificate",
            "transcript",
            "cv",
            "personal_statement",
            "reference",
            "english_test",
        ),
        notes=(
            "Kontrakt yo'q: faqat semestr yig'imi (~98 EUR), shundan 85 EUR ma'muriy yig'im "
            "bo'lib, ariza bo'yicha bekor qilinishi mumkin. Dastur 2 semestr, oktyabrda "
            "boshlanadi va faqat qishki semestrga qabul qiladi. Ingliz tilidan C1 darajadagi "
            "sertifikat kerak, lekin aniq ball ko'rsatilmagan. Arizaga 3-5 daqiqalik video va "
            "2 sahifalik motivatsiya xati ham kiradi. 2026/27 uchun muddat 15.02.2026 edi; "
            "keyingi yil sanasi sahifada hali yo'q."
        ),
        notes_ru=(
            "Платы за обучение нет: только семестровый взнос (~98 EUR), из них 85 EUR — "
            "административный сбор, который по заявлению могут отменить. Программа длится "
            "2 семестра, начинается в октябре, набор только на зимний семестр. Нужен "
            "сертификат по английскому уровня C1, но конкретный балл не указан. В пакет "
            "документов входят видео на 3-5 минут и мотивационное письмо на 2 страницы. "
            "Дедлайн на 2026/27 был 15.02.2026; дата на следующий год на странице пока не "
            "опубликована."
        ),
        notes_en=(
            "There is no tuition fee: only a semester fee of about EUR 98, of which EUR 85 is an "
            "administrative charge that can be waived on request. The programme runs for two "
            "semesters, starts in October and admits only in the winter semester. An English "
            "certificate at C1 level is required, but no test score is stated. The application "
            "also asks for a 3-5 minute video and a two-page letter of motivation. The 2026/27 "
            "deadline was 15.02.2026; the next year's date is not yet on the page."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="Saarland University (Europa-Institut)",
        city="Saarbryukken",
        website="https://www.europainstitut.de",
        timezone="Europe/Berlin",
        program="European and International Law (LL.M.)",
        source_url="https://www.europainstitut.de/en/application",
        intake_term="2027 Fall",
        tuition_amount=6800,
        tuition_currency="EUR",
        deadline_close=date(2027, 7, 15),
        documents=(
            "cv",
            "personal_statement",
            "degree_certificate",
            "transcript",
            "english_test",
            "passport",
        ),
        has_scholarship=False,
        notes=(
            "Kontrakt semestriga 3 400 EUR, o'quv yiliga 6 800 EUR (institutning «Finances | "
            "Scholarships» sahifasi). Bunga kutubxona, kompyuter xonasi, nusxa olish va ayrim "
            "tadbirlar kiradi; universitetning semestr yig'imi alohida to'lanadi. Ariza muddati "
            "— har yili 15-iyul, viza kerak bo'lmaganlar uchun 30-sentyabrgacha kechikkan ariza "
            "qabul qilinadi. Til bali sahifada ko'rsatilmagan: TOEFL ham, IELTS ham qabul "
            "qilinadi, lekin minimal ball yozilmagan. Europa-Institut o'zi stipendiya bermaydi."
        ),
        notes_ru=(
            "Стоимость — 3 400 EUR за семестр, 6 800 EUR за учебный год (страница института "
            "«Finances | Scholarships»). В неё входят библиотека, компьютерный класс, копии и "
            "часть мероприятий; семестровый взнос университета оплачивается отдельно. Дедлайн — "
            "15 июля каждого года, для тех, кому не нужна виза, поздние заявки принимают до "
            "30 сентября. Балл по языку на странице не указан: TOEFL и IELTS принимаются, но "
            "минимум не назван. Сам Europa-Institut стипендий не даёт."
        ),
        notes_en=(
            "Tuition is EUR 3,400 per semester, EUR 6,800 for the academic year (the institute's "
            "«Finances | Scholarships» page). It covers the library, the computer workspace, "
            "photocopies and some activities; the university's semester fee is paid separately. "
            "The deadline is 15 July each year, with late applications accepted until "
            "30 September from applicants who do not need a visa. No language score is stated: "
            "TOEFL and IELTS are accepted but no minimum is given. The Europa-Institut itself "
            "awards no scholarships."
        ),
        missing=("language_score",),
    ),
    LlmSeed(
        country_iso="DE",
        university="Munich Intellectual Property Law Center (MIPLC)",
        city="Myunxen",
        website="https://www.miplc.de",
        timezone="Europe/Berlin",
        program="Intellectual Property Law (LL.M.)",
        source_url="https://www.miplc.de/admissions/tuition-and-financial-aid-law-and-ip-scholarships",
        intake_term="2027 Fall",
        tuition_amount=39500,
        tuition_currency="EUR",
        has_scholarship=True,
        scholarship_url="https://www.miplc.de/admissions/tuition-and-financial-aid-law-and-ip-scholarships",
        notes=(
            "Sahifada 39 500 EUR summasi 2025/2026 o'quv yili (qish + yoz) uchun ko'rsatilgan. "
            "Narxga MIPLC kurslari, IP va raqobat huquqi bo'yicha yirik kutubxona, LexisNexis "
            "va Westlaw bazalari, Myunxen markazidagi ish stoli hamda Augsburg universiteti va "
            "Myunxen texnika universitetiga ro'yxatdan o'tish kiradi. Qabul uzluksiz (rolling), "
            "aniq muddat e'lon qilinmagan. Cheklangan sonli qisman chegirma stipendiyalari bor "
            "— ariza bilan birga topshiriladi (1-dekabrdan 30-aprelgacha); DAAD stipendiyasiga "
            "1-iyun – 15-oktyabr oralig'ida ariza beriladi."
        ),
        notes_ru=(
            "На странице сумма 39 500 EUR указана для 2025/2026 учебного года (зима + лето). "
            "В неё входят все курсы MIPLC, крупнейшая библиотека по IP и конкурентному праву, "
            "базы LexisNexis и Westlaw, рабочее место в центре Мюнхена, а также зачисление в "
            "Университет Аугсбурга и Технический университет Мюнхена. Приём непрерывный, "
            "конкретный дедлайн не объявлен. Есть ограниченное число частичных стипендий-скидок "
            "— подаются вместе с заявкой (с 1 декабря по 30 апреля); на стипендию DAAD подают "
            "с 1 июня по 15 октября."
        ),
        notes_en=(
            "The page gives EUR 39,500 for the 2025/2026 academic year (winter and summer). The "
            "fee covers an unlimited number of MIPLC credit hours, the world's largest IP and "
            "competition library, LexisNexis and Westlaw, a desk in a downtown Munich office, "
            "and enrolment at the University of Augsburg and the Technical University of Munich. "
            "Admission is rolling and no fixed deadline is published. A limited number of partial "
            "fee-waiver scholarships is available and is applied for together with admission "
            "(1 December to 30 April); DAAD scholarship applications run 1 June to 15 October."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="University of Hamburg",
        city="Gamburg",
        website="https://www.jura.uni-hamburg.de",
        timezone="Europe/Berlin",
        program="European and International Law (MEIL) LL.M.",
        source_url="https://www.jura.uni-hamburg.de/en/studium/masterprogramme/meil.html",
        intake_term="2027 Fall",
        tuition_amount=7000,
        tuition_currency="EUR",
        ielts_min=6.5,
        toefl_min=90,
        deadline_close=date(2027, 4, 30),
        notes=(
            "Kontrakt 7 000 EUR, ustiga universitetning semestr yig'imi (~335 EUR). Arizalar "
            "1-noyabrdan qabul qilinadi: erta muddat — 31-yanvar 2027, oxirgi muddat — "
            "30-aprel 2027. TOEFL 90 yoki IELTS 6.5 kerak; ona tili ingliz bo'lganlar yoki "
            "diplomi ingliz tilida bo'lganlar bundan ozod. Dastur 2 semestr, sentyabr boshida "
            "boshlanadi. Hujjatlar bitta PDF fayl qilib yuklanadi, asl nusxalar ro'yxatdan "
            "o'tishda ko'rsatiladi."
        ),
        notes_ru=(
            "Стоимость 7 000 EUR плюс семестровый взнос университета (~335 EUR). Заявки "
            "принимают с 1 ноября: ранний срок — 31 января 2027, окончательный — 30 апреля 2027. "
            "Нужен TOEFL 90 или IELTS 6.5; носители языка и те, чей диплом на английском, "
            "освобождаются. Программа рассчитана на 2 семестра и начинается в начале сентября. "
            "Документы загружаются одним PDF-файлом, оригиналы предъявляются при зачислении."
        ),
        notes_en=(
            "Tuition is EUR 7,000, plus the university's semester fee of about EUR 335. "
            "Applications open on 1 November: the early-bird deadline is 31 January 2027 and the "
            "final deadline 30 April 2027. A TOEFL score of 90 or IELTS 6.5 is required; native "
            "speakers and holders of an English-taught degree are exempt. The programme runs for "
            "two semesters and starts at the beginning of September. Documents are uploaded as a "
            "single PDF and originals must be presented at registration."
        ),
    ),
    LlmSeed(
        country_iso="DE",
        university="TU Dresden",
        city="Drezden",
        website="https://tu-dresden.de",
        timezone="Europe/Berlin",
        program="International Studies in Intellectual Property Law and Data Law (LL.M.)",
        source_url="https://tu-dresden.de/gsw/phil/irget/ipllm/studium",
        intake_term="2027 Fall",
        tuition_amount=5000,
        tuition_currency="EUR",
        deadline_close=date(2027, 3, 15),
        notes=(
            "Kontrakt 2 semestr uchun 5 000 EUR, ustiga har semestr ~300 EUR ma'muriy yig'im "
            "(dasturning «Fees» sahifasi); qo'shimcha semestr 500 EUR. Yevropa Ittifoqidan "
            "tashqaridagilar uchun qishki semestrga muddat — 15-mart, EI fuqarolari uchun "
            "15-may. Bir semestrni hamkor universitetda (Ekseter, Krakov, London, Praga, "
            "Strasburg, Seged, Tallin, Tokio) o'tash mumkin — u holda TU Dresden ulushi "
            "3 000 EUR, hamkor esa o'z narxini oladi. O'qish 1-oktyabrda boshlanadi, til bali "
            "sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "Стоимость 5 000 EUR за 2 семестра плюс около 300 EUR административного сбора за "
            "семестр (страница программы «Fees»); дополнительный семестр — 500 EUR. Для "
            "неграждан ЕС дедлайн на зимний семестр — 15 марта, для граждан ЕС — 15 мая. Один "
            "семестр можно провести в вузе-партнёре (Эксетер, Краков, Лондон, Прага, Страсбург, "
            "Сегед, Таллин, Токио) — тогда доля TU Dresden составляет 3 000 EUR, а партнёр "
            "берёт свою плату. Занятия начинаются 1 октября, балл по языку на странице не указан."
        ),
        notes_en=(
            "Tuition is EUR 5,000 for two semesters, plus about EUR 300 per semester in "
            "administration fees (the programme's «Fees» page); an extra semester costs EUR 500. "
            "For non-EU applicants the winter-semester deadline is 15 March, for EU applicants "
            "15 May. One semester may be spent at a partner university (Exeter, Krakow, London, "
            "Prague, Strasbourg, Szeged, Tallinn, Tokyo), in which case TU Dresden's share is "
            "EUR 3,000 and the partner charges its own fee. Teaching starts on 1 October; no "
            "language score is stated on the page."
        ),
        missing=("language_score",),
    ),
    LlmSeed(
        country_iso="DE",
        university="Freie Universität Berlin",
        city="Berlin",
        website="https://www.jura.fu-berlin.de",
        timezone="Europe/Berlin",
        program="European and International Business, Competition and Regulatory Law (MBL-FU)",
        source_url="https://www.jura.fu-berlin.de/en/studium/masterstudiengaenge/mbl-fu/program/index.html",
        intake_term="2027 Fall",
        tuition_amount=9500,
        tuition_currency="EUR",
        deadline_close=date(2027, 3, 15),
        notes=(
            "Kontrakt jami 9 500 EUR (semestriga 4 750 EUR), ustiga semestr yig'imlari. Ariza "
            "muddati — har yili 15-mart; 2027/28 uchun qabul 1-dekabr 2026 dan boshlanadi. "
            "Talab: 240 ECTS li diplom (afzali huquq bo'yicha) va kamida bir yillik ish "
            "tajribasi. Ingliz tili CEFR bo'yicha C1 darajada bo'lishi kerak, aniq IELTS/TOEFL "
            "bali ko'rsatilmagan. O'qish bir o'quv yili, oktyabrda boshlanadi."
        ),
        notes_ru=(
            "Стоимость — 9 500 EUR всего (4 750 EUR за семестр) плюс семестровые взносы. Дедлайн "
            "— 15 марта каждого года; приём на 2027/28 открывается 1 декабря 2026. Требуется "
            "диплом на 240 ECTS (предпочтительно юридический) и минимум год опыта работы. "
            "Английский — уровень C1 по CEFR, конкретный балл IELTS/TOEFL не указан. Обучение "
            "длится один учебный год и начинается в октябре."
        ),
        notes_en=(
            "Tuition is EUR 9,500 in total (EUR 4,750 per term) plus semester fees and "
            "contributions. The deadline is 15 March each year; applications for 2027/28 open on "
            "1 December 2026. Entry requires a degree worth 240 ECTS, preferably in law, and at "
            "least one year of work experience. English must be at CEFR C1; no IELTS or TOEFL "
            "score is given. The programme lasts one academic year and starts in October."
        ),
        missing=("language_score",),
    ),
    LlmSeed(
        country_iso="DE",
        university="European University Viadrina Frankfurt (Oder)",
        city="Frankfurt (Oder)",
        website="https://www.europa-uni.de",
        timezone="Europe/Berlin",
        program="International Human Rights and Humanitarian Law (LL.M.)",
        source_url="https://www.europa-uni.de/en/studium/studienangebot/wb-ma-human-rights/index.html",
        intake_term="2026 Fall",
        duration_years=1.5,
        tuition_amount=7900,
        tuition_currency="EUR",
        ielts_min=7.0,
        toefl_min=93,
        deadline_close=date(2026, 9, 30),
        documents=("cv", "degree_certificate", "english_test"),
        has_scholarship=False,
        notes=(
            "Kontrakt 90 ECTS li to'liq LL.M. uchun 7 900 EUR. Muddatlar: erta qabul — "
            "1-avgust 2026, asosiy muddat — 30-sentyabr 2026 (23:59 CET). Til talabi: IELTS 7.0 "
            "(har bo'limda kamida 6.5), TOEFL iBT 93 yoki Cambridge C1 180. To'liq kunlik shakl "
            "3 semestr, yarim kunlik 6 semestrgacha cho'zilishi mumkin; qabul ham qishki, ham "
            "yozgi semestrga. CV ingliz tilida, ko'pi bilan 4 sahifa. Viadrina o'zi stipendiya "
            "bermaydi."
        ),
        notes_ru=(
            "Стоимость полной программы LL.M. на 90 ECTS — 7 900 EUR. Сроки: ранний приём — "
            "1 августа 2026, основной дедлайн — 30 сентября 2026 (23:59 CET). Языковые "
            "требования: IELTS 7.0 (не ниже 6.5 в каждом разделе), TOEFL iBT 93 или Cambridge C1 "
            "180. Очная форма — 3 семестра, заочная — до 6; набор и на зимний, и на летний "
            "семестр. Резюме на английском, максимум 4 страницы. Сам Viadrina стипендий не даёт."
        ),
        notes_en=(
            "Tuition is EUR 7,900 for the full 90-ECTS LL.M. Deadlines: early admission "
            "1 August 2026, regular admission 30 September 2026 (23:59 CET). Language "
            "requirements: IELTS 7.0 with no band below 6.5, TOEFL iBT 93, or Cambridge C1 at "
            "180. Full-time study takes three semesters, part-time up to six; there are both "
            "winter and summer intakes. The CV must be in English and at most four pages. "
            "Viadrina itself awards no scholarships."
        ),
    ),
    LlmSeed(
        country_iso="DE",
        university="University of Münster",
        city="Myunster",
        website="https://www.uni-muenster.de",
        timezone="Europe/Berlin",
        program="Comparative and Global Law (LL.M.)",
        source_url="https://www.uni-muenster.de/Jura/akademische_qualifizierung/ll_m_-_masterstudiengaenge/comparative_and_global_law_ll_m_/Application_admission_tuition.html",
        intake_term="2027 Fall",
        tuition_amount=0,
        tuition_currency="EUR",
        ielts_min=7.0,
        toefl_min=95,
        documents=(
            "degree_certificate",
            "transcript",
            "english_test",
            "cv",
            "reference",
        ),
        has_scholarship=False,
        notes=(
            "Kontrakt yo'q: faqat semestr badali ~350 EUR, unga ma'muriy xarajatlar, talabalar "
            "xizmati va jamoat transporti kiradi. Til talabi: IELTS kamida 7.0 yoki TOEFL iBT "
            "kamida 95 (speaking 25, writing 24), ya'ni C1. Yiliga atigi 20 talaba olinadi; "
            "arizaga o'qituvchidan bitta tavsiyanoma kerak. 2026/27 uchun ariza 4-may – "
            "15-iyul 2026 oralig'ida qabul qilingan (31-maygacha bergan kuchli nomzodlarga erta "
            "taklif), 2027 sanalari sahifada hali yo'q. Universitet o'z stipendiyasini bermaydi, "
            "DAAD va boshqa fondlarga murojaat qilish tavsiya etiladi."
        ),
        notes_ru=(
            "Платы за обучение нет: только семестровый взнос около 350 EUR, покрывающий "
            "административные расходы, студенческие сервисы и проезд. Языковые требования: IELTS "
            "не ниже 7.0 или TOEFL iBT не ниже 95 (speaking 25, writing 24), то есть уровень C1. "
            "В год берут всего 20 человек; нужна одна рекомендация от преподавателя. На 2026/27 "
            "заявки принимали с 4 мая по 15 июля 2026 (сильным кандидатам, подавшим до 31 мая, "
            "делали ранние предложения), даты на 2027 на странице пока не опубликованы. Своих "
            "стипендий университет не даёт и отсылает к DAAD и другим фондам."
        ),
        notes_en=(
            "There is no tuition fee: only a semester contribution of about EUR 350 covering "
            "administration, student services and public transport. Language requirements: IELTS "
            "at least 7.0 or TOEFL iBT at least 95 with 25 in speaking and 24 in writing, i.e. "
            "CEFR C1. Only 20 students are admitted each year and one academic reference letter "
            "is required. For 2026/27 the application period ran 4 May to 15 July 2026, with "
            "early offers to outstanding candidates who applied by 31 May; the 2027 dates are "
            "not yet on the page. The university awards no scholarships of its own and points "
            "applicants to the DAAD and other foundations."
        ),
        missing=("deadline",),
    ),
    LlmSeed(
        country_iso="DE",
        university="University of Göttingen",
        city="Gyottingen",
        website="https://www.uni-goettingen.de",
        timezone="Europe/Berlin",
        program="Göttingen Master of International Law (GOMIL) LL.M.",
        source_url="https://www.uni-goettingen.de/en/ll.m.+in+international+law+(gomil)/685263.html",
        intake_term="2027 Fall",
        tuition_amount=8500,
        tuition_currency="EUR",
        deadline_close=date(2027, 5, 31),
        has_scholarship=False,
        notes=(
            "Kontrakt 8 500 EUR (semestriga 4 250 EUR) — 2026/27 va 2027/28 qishki semestrlari "
            "uchun; 2028/29 dan 9 000 EUR, 2029/30 dan 9 500 EUR bo'ladi. Birinchi 25% taklif "
            "kelgandan keyin olti hafta ichida, qolgani oktyabr, yanvar va aprelda to'lanadi. "
            "Bundan tashqari semestriga ~500 EUR talabalar uyushmasi badali bor. Ariza muddati "
            "— 31-may; o'qish 1-oktyabrdan 30-sentyabrgacha. Fakultet o'z stipendiyasini "
            "bermaydi, DAAD kabi tashqi manbalarga yo'naltiradi. Til bali sahifada yo'q."
        ),
        notes_ru=(
            "Стоимость 8 500 EUR (4 250 EUR за семестр) — для зимних семестров 2026/27 и "
            "2027/28; с 2028/29 — 9 000 EUR, с 2029/30 — 9 500 EUR. Первые 25% вносят в течение "
            "шести недель после получения места, остальное — в октябре, январе и апреле. "
            "Дополнительно около 500 EUR взноса студенческого союза за семестр. Дедлайн — "
            "31 мая; обучение идёт с 1 октября по 30 сентября. Своих стипендий факультет не "
            "даёт и направляет к внешним источникам вроде DAAD. Балл по языку на странице "
            "не указан."
        ),
        notes_en=(
            "Tuition is EUR 8,500 (EUR 4,250 per semester) for the winter intakes of 2026/27 and "
            "2027/28; it rises to EUR 9,000 from 2028/29 and EUR 9,500 from 2029/30. The first "
            "instalment of 25% is due within six weeks of the offer, the rest in October, "
            "January and April. There is also a student union contribution of about EUR 500 per "
            "semester. The deadline is 31 May and the year runs 1 October to 30 September. The "
            "law faculty awards no scholarships of its own and points to external sources such "
            "as the DAAD. No language score is stated on the page."
        ),
        missing=("language_score",),
    ),
    LlmSeed(
        country_iso="DE",
        university="University of Göttingen",
        city="Gyottingen",
        website="https://www.uni-goettingen.de",
        timezone="Europe/Berlin",
        program=(
            "European and Transnational Law of Intellectual Property and Information "
            "Technology (LL.M.)"
        ),
        source_url="https://www.uni-goettingen.de/en/545891.html",
        intake_term="2027 Fall",
        tuition_amount=9000,
        tuition_currency="EUR",
        has_scholarship=True,
        scholarship_url="https://www.uni-goettingen.de/en/545891.html",
        notes=(
            "Kontrakt 9 000 EUR (semestriga 4 500 EUR). Dastur 1 yil, 60 ECTS: 27-oktyabrdan "
            "30-sentyabrgacha. To'liq va qisman kontrakt chegirmalari (tuition waiver) beriladi. "
            "Ingliz tili oliy ta'lim uchun yetarli bo'lishi talab qilinadi, lekin aniq "
            "IELTS/TOEFL bali sahifada yo'q; ariza muddati ham ko'rsatilmagan."
        ),
        notes_ru=(
            "Стоимость 9 000 EUR (4 500 EUR за семестр). Программа длится 1 год, 60 ECTS: с "
            "27 октября по 30 сентября. Предоставляются полные и частичные скидки на обучение "
            "(tuition waiver). Требуется английский, достаточный для обучения в вузе, но "
            "конкретный балл IELTS/TOEFL на странице не указан, дедлайн тоже не назван."
        ),
        notes_en=(
            "Tuition is EUR 9,000 (EUR 4,500 per semester). The programme lasts one year and is "
            "worth 60 ECTS, running from 27 October to 30 September. Full and partial tuition "
            "waivers are available. Applicants must show English sufficient for higher education, "
            "but no IELTS or TOEFL score is given on the page, and no deadline is stated either."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="Leibniz University Hannover",
        city="Gannover",
        website="https://www.jura.uni-hannover.de",
        timezone="Europe/Berlin",
        program="European Legal Practice (LL.M.) - Joint Degree",
        source_url="https://www.jura.uni-hannover.de/en/studies/studienangebot-der-fakultaet/ergaenzende-studiengaenge/european-legal-practice-llm-joint-degree-master-of-laws/costs-and-scholarship",
        intake_term="2027 Fall",
        duration_years=2.0,
        language="German, English",
        tuition_amount=0,
        tuition_currency="EUR",
        notes=(
            "Gannoverda kontrakt yo'q: faqat semestr yig'imi ~433,11 EUR, unga jamoat transporti "
            "chiptasi kiradi (sahifadagi holat — 2021/22 qishki semestri). Dastur 4 semestr va "
            "sakkizta hamkor universitetdan birida majburiy chet el semestrini o'z ichiga oladi "
            "— hamkor universitetlar o'z to'lovlarini oladi. Qabul cheklangan; darslar nemis va "
            "ingliz tillarida. Til bali ham, aniq ariza muddati ham fakultet sahifasida "
            "ko'rsatilmagan."
        ),
        notes_ru=(
            "В Ганновере платы за обучение нет: только семестровый взнос около 433,11 EUR, "
            "включающий проездной (по состоянию на зимний семестр 2021/22, как указано на "
            "странице). Программа рассчитана на 4 семестра и включает обязательный семестр в "
            "одном из восьми вузов-партнёров — они берут собственную плату. Приём ограничен; "
            "занятия идут на немецком и английском. Ни балл по языку, ни точный дедлайн на "
            "странице факультета не указаны."
        ),
        notes_en=(
            "There are no tuition fees in Hannover: only a semester fee of about EUR 433.11, "
            "which includes a public transport ticket (the page states winter semester 2021/22). "
            "The programme runs for four semesters and includes a compulsory period abroad at "
            "one of eight partner universities, which charge their own fees. Admission is "
            "restricted and teaching is in German and English. Neither a language score nor a "
            "precise deadline is stated on the faculty page."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="Kiel University",
        city="Kil",
        website="https://www.uni-kiel.de",
        timezone="Europe/Berlin",
        program="International and European Law (LL.M.Int.)",
        source_url="https://www.uni-kiel.de/en/law/study/international/llm",
        intake_term="2027 Fall",
        tuition_amount=0,
        tuition_currency="EUR",
        ielts_min=6.5,
        toefl_min=80,
        deadline_close=date(2027, 2, 15),
        documents=(
            "personal_statement",
            "degree_certificate",
            "transcript",
            "cv",
            "reference",
            "passport",
            "english_test",
        ),
        notes=(
            "Kontrakt yo'q: semestriga ~300 EUR yig'im, birinchi semestrda ro'yxatdan o'tish "
            "to'lovi ham qo'shiladi. Ingliz tilida to'liq o'qiladigan yagona yo'nalish — "
            "LL.M.Int.; qolgan ixtisosliklar faqat nemis tilida. Arizalar 1-dekabr 2026 dan "
            "15-fevral 2027 gacha qabul qilinadi. Til talabi: TOEFL iBT 80, IELTS 6.5 yoki PTE "
            "Academic 59. O'qish 2 semestr, oktyabrda boshlanadi. Hujjatlar orasida huquq "
            "professoridan tavsiyanoma bor; Xitoy, Hindiston va Vetnam arizachilariga APS "
            "sertifikati kerak."
        ),
        notes_ru=(
            "Платы за обучение нет: около 300 EUR взноса за семестр, в первом семестре "
            "добавляется плата за зачисление. Полностью на английском читается только "
            "LL.M.Int.; остальные специализации — на немецком. Заявки принимают с 1 декабря "
            "2026 по 15 февраля 2027. Языковые требования: TOEFL iBT 80, IELTS 6.5 или PTE "
            "Academic 59. Обучение длится 2 семестра и начинается в октябре. Среди документов — "
            "рекомендация от профессора права; абитуриентам из Китая, Индии и Вьетнама нужен "
            "сертификат APS."
        ),
        notes_en=(
            "There are no tuition fees: a semester contribution of about EUR 300, with an "
            "enrolment fee added in the first semester. Only the LL.M.Int. can be studied "
            "entirely in English; the other specialisations are taught in German only. "
            "Applications run from 1 December 2026 to 15 February 2027. Language requirements: "
            "TOEFL iBT 80, IELTS 6.5 or PTE Academic 59. The programme lasts two semesters and "
            "starts in October. The documents include a reference from a law professor, and "
            "applicants from China, India and Vietnam need an APS certificate."
        ),
    ),
    LlmSeed(
        country_iso="DE",
        university="University of Würzburg",
        city="Vyurtsburg",
        website="https://www.jura.uni-wuerzburg.de",
        timezone="Europe/Berlin",
        program="Digitalization & Law (LL.M.)",
        source_url="https://www.jura.uni-wuerzburg.de/en/studium/postgraduales-studium/aufbau-und-masterstudiengaenge/llm-digitalization-law/fees/",
        intake_term="2027 Fall",
        duration_years=1.5,
        tuition_amount=7500,
        tuition_currency="EUR",
        has_scholarship=False,
        notes=(
            "Kontrakt jami 7 500 EUR — dastlabki uch semestrda 2 500 EUR dan uch bo'lib "
            "to'lanadi; to'rtinchi semestr kerak bo'lsa, faqat semestr yig'imi to'lanadi. "
            "Universitet semestr yig'imi ~180 EUR. Dastur 3 semestr (1,5 yil), oktyabrda "
            "boshlanadi, yiliga 40-45 talaba olinadi va LL.M. bilan birga IT-huquq "
            "ixtisoslashuvining nazariy qismi tasdiqlanadi. Dasturning o'z stipendiyasi yo'q, "
            "lekin tashqi stipendiyalar qabul qilinadi. 2026/27 uchun ariza 22-yanvar – "
            "15-iyul 2026 oralig'ida ochiq edi."
        ),
        notes_ru=(
            "Стоимость — 7 500 EUR всего, тремя взносами по 2 500 EUR в первых трёх семестрах; "
            "если нужен четвёртый семестр, платится только семестровый взнос. Семестровый взнос "
            "университета — около 180 EUR. Программа длится 3 семестра (1,5 года), начинается в "
            "октябре, набирают 40-45 человек, и вместе с LL.M. подтверждается теоретическая "
            "часть специализации по IT-праву. Собственной стипендии у программы нет, но внешние "
            "принимаются. На 2026/27 приём шёл с 22 января по 15 июля 2026."
        ),
        notes_en=(
            "Tuition totals EUR 7,500, paid in three instalments of EUR 2,500 in the first three "
            "semesters; a fourth semester costs only the semester fee. The university's semester "
            "fee is about EUR 180. The programme runs for three semesters (1.5 years), starts in "
            "October, admits 40-45 students a year, and awards the LL.M. together with "
            "confirmation of the theoretical part of the IT law specialisation. It has no "
            "scholarship of its own but accepts external funding. The 2026/27 application window "
            "ran from 22 January to 15 July 2026."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="Osnabrück University",
        city="Osnabryuk",
        website="https://www.uni-osnabrueck.de",
        timezone="Europe/Berlin",
        program="European Technology Law (METL) LL.M.",
        source_url="https://www.uni-osnabrueck.de/fb10/en/studieninteressierte/studiengaenge/llm-master-of-european-technology-law-metl/admission-fees",
        intake_term="2027 Fall",
        duration_years=1.5,
        tuition_amount=4860,
        tuition_currency="EUR",
        has_scholarship=True,
        scholarship_url="https://www.uni-osnabrueck.de/fb10/en/studieninteressierte/studiengaenge/llm-master-of-european-technology-law-metl/admission-fees",
        notes=(
            "Kontrakt 4 860 EUR, ikki bo'lib to'lanadi — birinchisi taklif kelishi bilan. "
            "Bundan tashqari semestriga ~400 EUR talabalar uyushmasi badali. Ingliz tili B2 "
            "(CEFR) darajasida bo'lishi kerak, aniq IELTS/TOEFL bali ko'rsatilmagan. Qabul "
            "uchun huquq bo'yicha kamida 8 semestrlik diplom yoki texnika yo'nalishida 240 ECTS "
            "(formal metodlardan 15 ECTS va informatika/sun'iy intellekt sohasida 25 ECTS) "
            "kerak. O'qish 2 semestr dars va 1 semestr magistrlik ishi, qishki semestrda "
            "boshlanadi. Universitet va hamkorlari eng kuchli arizachilarga to'liq yoki qisman "
            "kontrakt chegirmasini berishi mumkin; muddat sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "Стоимость 4 860 EUR, оплачивается двумя частями — первая сразу после получения "
            "места. Дополнительно около 400 EUR взноса студенческого союза за семестр. "
            "Английский нужен на уровне B2 (CEFR), конкретный балл IELTS/TOEFL не указан. Для "
            "поступления нужен юридический диплом не менее 8 семестров либо техническое "
            "образование на 240 ECTS (15 ECTS по формальным методам и 25 ECTS по "
            "информатике/искусственному интеллекту). Программа: 2 семестра занятий плюс семестр "
            "на магистерскую работу, старт — зимний семестр. Университет и партнёры могут дать "
            "лучшим абитуриентам полную или частичную скидку; дедлайн на странице не указан."
        ),
        notes_en=(
            "Tuition is EUR 4,860, payable in two instalments, the first as soon as the offer "
            "arrives. There is also a student union contribution of about EUR 400 per semester. "
            "English at CEFR B2 is required, with no IELTS or TOEFL score specified. Entry needs "
            "a law degree of at least eight semesters or a technology degree worth 240 ECTS, "
            "including 15 ECTS in formal methods and 25 ECTS in informatics or artificial "
            "intelligence. The programme is two semesters of lectures plus one for the thesis, "
            "starting in the winter semester. The university and its partners may award full or "
            "partial tuition waivers to the best applicants; no deadline is stated on the page."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="Goethe University Frankfurt (European Academy of Legal Theory)",
        city="Frankfurt",
        website="https://www.legaltheory.eu",
        timezone="Europe/Berlin",
        program="Legal Theory (LL.M.)",
        source_url="https://www.legaltheory.eu/llm-in-legal-theory/application-admission-language/",
        intake_term="2027 Fall",
        tuition_amount=7200,
        tuition_currency="EUR",
        ielts_min=7.0,
        toefl_min=100,
        deadline_close=date(2027, 9, 15),
        documents=(
            "cv",
            "english_test",
            "transcript",
            "passport",
            "personal_statement",
            "reference",
        ),
        has_scholarship=True,
        scholarship_url="https://www.legaltheory.eu/llm-in-legal-theory/application-admission-language/",
        notes=(
            "Dasturni European Academy of Legal Theory olib boradi, o'qish Frankfurtdagi Gyote "
            "universitetida o'tadi. Kontrakt 7 200 EUR; a'lo natija yoki moddiy ehtiyoj asosida "
            "uni 6 000 EUR gacha kamaytirishga ariza berish mumkin. Muddat — har yili "
            "15-sentyabr. Til talabi: IELTS kamida 7.0 yoki TOEFL iBT 100 (har bo'limda kamida "
            "20). Qabul uchun huquq yoki unga yaqin sohada diplom va bir yillik kasbiy yoki "
            "ilmiy tajriba kerak; o'qish bir yil, oktyabrda boshlanadi."
        ),
        notes_ru=(
            "Программу ведёт European Academy of Legal Theory, занятия проходят в Университете "
            "Гёте во Франкфурте. Стоимость 7 200 EUR; при отличных результатах или финансовой "
            "необходимости можно подать на снижение до 6 000 EUR. Дедлайн — 15 сентября каждого "
            "года. Языковые требования: IELTS не ниже 7.0 или TOEFL iBT 100 (минимум 20 в "
            "каждом разделе). Нужны диплом по праву или смежной области и год "
            "профессионального либо исследовательского опыта; обучение длится год и начинается "
            "в октябре."
        ),
        notes_en=(
            "The programme is run by the European Academy of Legal Theory and hosted at Goethe "
            "University Frankfurt. Tuition is EUR 7,200, and a partial reduction to EUR 6,000 "
            "can be applied for on grounds of excellence or financial need. The deadline is "
            "15 September each year. Language requirements: IELTS at least 7.0 or TOEFL iBT 100 "
            "with at least 20 in each section. Entry requires a law degree or a degree in a "
            "related subject plus one year of professional or research experience; the course "
            "lasts one year and starts in October."
        ),
    ),
    LlmSeed(
        country_iso="DE",
        university="Heidelberg University",
        city="Geydelberg",
        website="https://www.uni-heidelberg.de",
        timezone="Europe/Berlin",
        program="Law - Legum Magister (LL.M.)",
        source_url="https://www.uni-heidelberg.de/en/study/all-subjects/law/law-legum-magister",
        intake_term="2027 Fall",
        language="German",
        tuition_amount=1000,
        tuition_currency="EUR",
        notes=(
            "Dastur chet el universitetida huquq bo'yicha bakalavr diplomini olganlar uchun va "
            "nemis tilida o'qitiladi. Sahifada narx semestriga 500 EUR deb berilgan; dastur "
            "2 semestr bo'lgani uchun yiliga 1 000 EUR chiqadi (bu summa EI/EIH tashqarisidagi "
            "talabalar uchun). Qabul faqat qishki semestrda. Ariza muddati va til bali sahifada "
            "ko'rsatilmagan — ular tanlangan dastur bo'yicha alohida e'lon qilinadi."
        ),
        notes_ru=(
            "Программа для тех, кто получил диплом бакалавра права в зарубежном вузе, и читается "
            "на немецком. На странице указана плата 500 EUR за семестр; поскольку программа "
            "длится 2 семестра, за год выходит 1 000 EUR (для студентов из стран вне ЕС/ЕЭП). "
            "Набор только на зимний семестр. Дедлайн и балл по языку на странице не указаны — "
            "их публикуют отдельно по выбранной программе."
        ),
        notes_en=(
            "The programme is for holders of a law bachelor's degree from a university outside "
            "Germany and is taught in German. The page states a fee of EUR 500 per semester; as "
            "the programme runs for two semesters that comes to EUR 1,000 for the year (the rate "
            "for students from outside the EU/EEA). Admission is for the winter semester only. "
            "Neither a deadline nor a language score is given on the page; these are published "
            "separately for the chosen programme."
        ),
        missing=("language_score", "deadline"),
    ),
    LlmSeed(
        country_iso="DE",
        university="University of Passau",
        city="Passau",
        website="https://www.uni-passau.de",
        timezone="Europe/Berlin",
        program="German Law for Foreign Graduates (LL.M.)",
        source_url="https://www.uni-passau.de/en/llm-germanlaw",
        intake_term="2027 Fall",
        language="German",
        deadline_close=date(2027, 7, 15),
        documents=(
            "cv",
            "degree_certificate",
            "transcript",
            "passport",
            "translation",
        ),
        notes=(
            "Dastur nemis tilida o'qitiladi va chet elda huquq diplomini olganlar uchun "
            "mo'ljallangan. Nemis tili CEFR bo'yicha B2 yoki undan yuqori bo'lishi kerak; agar "
            "oldingi ta'lim nemis tilida bo'lgan bo'lsa, diplomning o'zi yetarli. Ariza "
            "15-apreldan 15-iyulgacha, faqat qishki semestrga (oktyabr) qabul qilinadi. O'qish "
            "2 semestr, 60 ECTS. Hujjatlar boshqa tilda bo'lsa, tasdiqlangan nemis yoki ingliz "
            "tarjimasi talab qilinadi. Kontrakt summasi sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "Программа читается на немецком и предназначена для тех, кто получил юридический "
            "диплом за рубежом. Немецкий нужен на уровне B2 CEFR или выше; если предыдущее "
            "образование было на немецком, достаточно самого диплома. Заявки принимают с "
            "15 апреля по 15 июля, набор только на зимний семестр (октябрь). Обучение — "
            "2 семестра, 60 ECTS. Документы на других языках требуют заверенного перевода на "
            "немецкий или английский. Сумма контракта на странице не указана."
        ),
        notes_en=(
            "The programme is taught in German and is intended for people who earned a law "
            "degree abroad. German must be at CEFR B2 or higher; if the previous education was "
            "in German, the certificates themselves suffice. Applications run from 15 April to "
            "15 July and there is a winter-semester (October) intake only. The course lasts two "
            "semesters and is worth 60 ECTS. Documents in other languages need certified German "
            "or English translations. No tuition figure is stated on the page."
        ),
        missing=("tuition", "language_score"),
    ),
    LlmSeed(
        country_iso="DE",
        university="University of Bayreuth",
        city="Bayroyt",
        website="https://www.uni-bayreuth.de",
        timezone="Europe/Berlin",
        program="Law for International Students & Professionals (LL.M.)",
        source_url="https://www.international-office.uni-bayreuth.de/en/degree-programmes/master-EU/law-for-international-students-_-professionals-_magister-legum_/index.html",
        intake_term="2027 Fall",
        language="German",
        deadline_close=date(2027, 7, 15),
        documents=(
            "cv",
            "degree_certificate",
            "transcript",
            "translation",
        ),
        notes=(
            "Xalqaro talabalar va amaliyotchi yuristlar uchun LL.M. Nemis tilidan DSH-2 "
            "sertifikati talab qilinadi. Ariza muddatlari: qishki semestr uchun 15-apreldan "
            "15-iyulgacha, yozgi semestr uchun 15-oktyabrdan 15-yanvargacha. Bakalavr "
            "transkriptida kamida 150 ECTS bo'lishi kerak; maktab attestati va diplomlarning "
            "asl nusxasi hamda tasdiqlangan tarjimasi, baholar shkalasi ham topshiriladi. "
            "Kontrakt summasi sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "LL.M. для иностранных студентов и практикующих юристов. Требуется сертификат по "
            "немецкому DSH-2. Сроки подачи: на зимний семестр с 15 апреля по 15 июля, на летний "
            "— с 15 октября по 15 января. В транскрипте бакалавра должно быть не менее "
            "150 ECTS; также подаются аттестат и дипломы в оригинале с заверенным переводом и "
            "шкала оценок. Сумма контракта на странице не указана."
        ),
        notes_en=(
            "An LL.M. for international students and practising lawyers. A DSH-2 German "
            "certificate is required. Application periods: 15 April to 15 July for the winter "
            "semester and 15 October to 15 January for the summer semester. The bachelor's "
            "transcript must show at least 150 ECTS; the school leaving certificate and degrees "
            "must be submitted as originals with certified translations, along with the grading "
            "scale. No tuition figure is stated on the page."
        ),
        missing=("tuition", "language_score"),
    ),
]

# DIQQAT: "rasmiy sahifadan tekshirilgan" va "quyidagi maydonlar bo'sh" degan
# jumlalar endi BAZAGA YOZILMAYDI. Ilgari ular o'zbekcha matn sifatida
# `notes`ga qo'shilardi va ruscha/inglizcha interfeysda ham o'zbekcha chiqardi.
# Endi Mini App ularni `verified_at` va `missing_fields` dan o'zi yasaydi —
# foydalanuvchi tilida.


async def _countries_by_iso(session: AsyncSession) -> dict[str, Country]:
    rows = (await session.execute(select(Country))).scalars().all()
    return {c.iso_code: c for c in rows}


async def _upsert_universities(
    session: AsyncSession, countries: dict[str, Country]
) -> tuple[dict[str, University], int, int]:
    existing = {u.name: u for u in (await session.execute(select(University))).scalars().all()}

    created = updated = 0
    for seed in SEEDS:
        country = countries.get(seed.country_iso)
        if country is None:
            raise RuntimeError(
                f"'{seed.country_iso}' davlati bazada yo'q. Avval "
                "scripts/seed_top_destinations.py ni ishga tushiring."
            )

        university = existing.get(seed.university)
        if university is None:
            university = University(name=seed.university)
            session.add(university)
            existing[seed.university] = university
            created += 1
        else:
            updated += 1

        university.country_id = country.id
        university.city = seed.city
        university.website = seed.website
        university.timezone = seed.timezone

    await session.flush()
    return existing, created, updated


async def _upsert_programs(
    session: AsyncSession, universities: dict[str, University]
) -> tuple[int, int]:
    rows = (await session.execute(select(Program))).scalars().all()
    existing = {(p.university_id, p.name, p.degree_level): p for p in rows}

    now = datetime.now(UTC)
    created = updated = 0

    for seed in SEEDS:
        university = universities[seed.university]
        key = (university.id, seed.program, DegreeLevel.MASTER)

        program = existing.get(key)
        if program is None:
            program = Program(
                university_id=university.id,
                name=seed.program,
                degree_level=DegreeLevel.MASTER,
            )
            session.add(program)
            existing[key] = program
            created += 1
        else:
            updated += 1

        program.abbreviation = seed.abbreviation
        program.field_of_study = FIELD_OF_STUDY
        program.language_of_instruction = seed.language
        program.duration_years = seed.duration_years
        program.intake_term = seed.intake_term
        program.notes = seed.notes
        program.notes_ru = seed.notes_ru
        program.notes_en = seed.notes_en
        program.missing_fields = list(seed.missing) or None
        program.required_documents = list(seed.documents) or None
        program.has_scholarship = seed.has_scholarship
        program.scholarship_url = seed.scholarship_url
        program.source_url = seed.source_url
        program.verified_at = now
        program.verified_by = VERIFIED_BY
        await session.flush()

        await _replace_details(session, program, seed, now)

    return created, updated


async def _replace_details(
    session: AsyncSession, program: Program, seed: LlmSeed, now: datetime
) -> None:
    """Talab/xarajat/muddat yozuvlarini qayta yozadi.

    Skript ikkinchi marta ishga tushirilganda eskilari o'chirilib, seed'dagi
    qiymatlar bilan almashtiriladi — shunda dublikat ham, eskirgan raqam ham
    qolmaydi.
    """
    for model in (ProgramRequirement, ProgramCost, Deadline):
        for row in (
            (await session.execute(select(model).where(model.program_id == program.id)))
            .scalars()
            .all()
        ):
            await session.delete(row)
    await session.flush()

    if seed.ielts_min is not None or seed.toefl_min is not None:
        session.add(
            ProgramRequirement(
                program_id=program.id,
                ielts_min=seed.ielts_min,
                toefl_min=seed.toefl_min,
            )
        )

    if seed.tuition_amount is not None:
        session.add(
            ProgramCost(
                program_id=program.id,
                tuition_amount=seed.tuition_amount,
                currency=seed.tuition_currency,
                last_checked=now.date(),
            )
        )

    if seed.deadline_close is not None:
        session.add(
            Deadline(
                program_id=program.id,
                type=DeadlineType.APPLICATION_CLOSE,
                date_utc=datetime(
                    seed.deadline_close.year,
                    seed.deadline_close.month,
                    seed.deadline_close.day,
                    tzinfo=UTC,
                ),
                intake_term=seed.intake_term,
            )
        )


async def main() -> None:
    async with async_session_factory() as session:
        try:
            countries = await _countries_by_iso(session)
            universities, uni_created, uni_updated = await _upsert_universities(session, countries)
            prog_created, prog_updated = await _upsert_programs(session, universities)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    with_tuition = sum(1 for s in SEEDS if s.tuition_amount is not None)
    with_scores = sum(1 for s in SEEDS if s.ielts_min or s.toefl_min)
    with_deadline = sum(1 for s in SEEDS if s.deadline_close is not None)

    print(f"Universitetlar: {uni_created} ta yangi, {uni_updated} ta yangilandi")
    print(f"LL.M. dasturlari: {prog_created} ta yangi, {prog_updated} ta yangilandi")
    print(
        f"Tasdiqlangan qiymatlar: {with_tuition}/{len(SEEDS)} kontrakt, "
        f"{with_scores}/{len(SEEDS)} til bali, {with_deadline}/{len(SEEDS)} muddat"
    )


if __name__ == "__main__":
    asyncio.run(main())
