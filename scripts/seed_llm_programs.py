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
        source_url="https://www.ilf-frankfurt.de/llm-international-finance-1",
        intake_term="2026 Fall",
        missing=("tuition", "language_score", "deadline"),
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
