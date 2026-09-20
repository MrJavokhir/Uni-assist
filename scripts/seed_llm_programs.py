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
        notes="Ariza qabul qilish uzluksiz (rolling admissions) — qat'iy yopilish sanasi yo'q.",
        notes_ru="Приём заявок идёт непрерывно (rolling admissions) — жёсткого дедлайна нет.",
        notes_en="Applications are accepted on a rolling basis — there is no fixed deadline.",
        missing=("language_score",),
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
        notes="Xalqaro talabalar uchun 2 000 GBP depozit, u kontrakt hisobiga o'tadi.",
        notes_ru="Для международных студентов депозит 2 000 GBP, он засчитывается в стоимость обучения.",
        notes_en="International students pay a GBP 2,000 deposit, credited towards tuition.",
        missing=("tuition", "deadline"),
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
        intake_term="2026 Fall",
        tuition_amount=31000,
        tuition_currency="GBP",
        ielts_min=7.0,
        toefl_min=100,
        notes="Narx 2026-yil sentyabrda boshlanadigan o'quv yili uchun (xalqaro talabalar).",
        notes_ru="Стоимость за учебный год, начинающийся в сентябре 2026 (международные студенты).",
        notes_en="Fee for the academic year starting September 2026 (international students).",
        missing=("deadline",),
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
