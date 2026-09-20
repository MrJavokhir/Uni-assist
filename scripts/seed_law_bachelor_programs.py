"""Germaniyadagi huquq bo'yicha BAKALAVR dasturlari — rasmiy sahifalardan.

NIMA UCHUN ALOHIDA SKRIPT:
`seed_llm_programs.py` faqat magistratura (LL.M.) yozadi — u yerda daraja
`DegreeLevel.MASTER` deb qotirilgan. Bakalavr dasturlari boshqa auditoriya
uchun: Mini App foydalanuvchining profildagi darajasiga qarab filtrlaydi,
shuning uchun "Law" yo'nalishi bakalavr tanlaganlarga ham ko'rinishi kerak.

GERMANIYA HUQUQ TA'LIMI HAQIDA (muhim):
Germaniyada advokat/sudya bo'lish uchun klassik yo'l — bakalavr emas, balki
davlat imtihoni (Staatsexamen). LL.B. dasturlari ham bor, lekin ularning
deyarli barchasi NEMIS TILIDA o'qitiladi va DSH-2 yoki C1 talab qiladi.
Shuning uchun har bir yozuvda `language` maydoni aniq to'ldirilgan — bu
foydalanuvchi uchun kontrakt narxidan kam ahamiyatli emas.

MANBA HAQIDA:
Har bir qiymatning `source_url`i universitetning o'z sahifasi. Rasmiy
sahifada ko'rsatilmagan maydon BO'SH qoldiriladi va `missing` ga yoziladi —
taxmin qilinmaydi.

Idempotent: universitet (nomi) va dastur (universitet + nomi + daraja)
bo'yicha upsert qilinadi.

Ishlatish:
    uv run python scripts/seed_law_bachelor_programs.py
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

VERIFIED_BY = "seed-law-bachelor-official"
FIELD_OF_STUDY = "Law"
DEGREE_LEVEL = DegreeLevel.BACHELOR


@dataclass(frozen=True)
class LawBachelorSeed:
    """Bitta huquq bakalavri dasturi va uning universiteti.

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
    duration_years: float
    # Germaniyada aksariyat LL.B. nemis tilida — shuning uchun bu maydonning
    # standart qiymati yo'q, har bir yozuvda ataylab yoziladi.
    language: str
    abbreviation: str = "LLB"

    tuition_amount: float | None = None
    tuition_currency: str = "EUR"
    ielts_min: float | None = None
    toefl_min: int | None = None
    deadline_close: date | None = None
    notes: str | None = None
    notes_ru: str | None = None
    notes_en: str | None = None

    # Ariza uchun hujjatlar — KALITLAR (Mini App ularni tarjima qiladi):
    # degree_certificate, transcript, translation, reference, english_test,
    # passport, personal_statement, cv, research_proposal
    documents: tuple[str, ...] = ()
    has_scholarship: bool | None = None
    scholarship_url: str | None = None
    missing: tuple[str, ...] = field(default_factory=tuple)


# Har bir qiymat 2026-yil sentyabr holatiga ko'ra rasmiy sahifadan olingan.
SEEDS: list[LawBachelorSeed] = [
    # --------------------- Xususiy oliy ta'lim muassasalari ---------------------
    LawBachelorSeed(
        country_iso="DE",
        university="Bucerius Law School",
        city="Gamburg",
        website="https://www.law-school.de",
        timezone="Europe/Berlin",
        program="Law (LL.B.)",
        source_url="https://www.law-school.de/studium/jurastudium",
        intake_term="2027 Fall",
        duration_years=3.5,
        language="German",
        tuition_amount=16800,
        tuition_currency="EUR",
        deadline_close=date(2027, 5, 15),
        has_scholarship=True,
        scholarship_url="https://www.law-school.de/studium/jurastudium/kosten-finanzierung-stipendien",
        notes=(
            "Germaniyadagi birinchi xususiy yuridik oliygoh. O'qish semestrlarga emas, "
            "trimestrlarga bo'lingan: bir o'quv yilida uchta trimestr, har biri 12 hafta. "
            "Kontrakt trimestriga 5 600 EUR, ya'ni yiliga 16 800 EUR; «Umgekehrter "
            "Generationenvertrag» sahifasida jami 14 trimestr hisoblab chiqilgan. Eng muhimi: "
            "o'qish davomida hech narsa to'lanmaydi — kontrakt ishga kirgandan keyin, yillik "
            "daromad 35 000 EUR dan oshganda, oylik brutto daromadning 9% miqdorida "
            "qaytariladi. LL.B. o'n trimestrdan keyin beriladi, yana uch trimestrdan so'ng "
            "davlat imtihoniga (Staatsexamen) ro'yxatdan o'tish mumkin. Ariza portali "
            "15-mayda soat 15:00 da yopiladi; ariza yig'imi 1-martgacha 40 EUR, keyin 80 EUR. "
            "Qabul baholar bo'yicha emas, yozma va og'zaki imtihon orqali. Darslar nemis "
            "tilida."
        ),
        notes_ru=(
            "Первая частная юридическая школа Германии. Учебный год делится не на семестры, а "
            "на три триместра по 12 недель. Стоимость — 5 600 EUR за триместр, то есть "
            "16 800 EUR в год; на странице «Umgekehrter Generationenvertrag» расчёт ведётся "
            "на 14 триместров. Главное: во время учёбы платить не нужно — оплата начинается "
            "после выхода на работу, при годовом доходе выше 35 000 EUR, в размере 9% "
            "месячного брутто-дохода. Степень LL.B. присваивается после десяти триместров, "
            "ещё через три можно регистрироваться на государственный экзамен (Staatsexamen). "
            "Портал заявок закрывается 15 мая в 15:00; сбор за заявку — 40 EUR до 1 марта и "
            "80 EUR после. Отбор идёт не по оценкам, а через письменный и устный экзамен. "
            "Занятия на немецком."
        ),
        notes_en=(
            "Germany's first private law school. The academic year is divided into three "
            "twelve-week trimesters rather than semesters. Tuition is EUR 5,600 per trimester, "
            "i.e. EUR 16,800 a year; the «Umgekehrter Generationenvertrag» page bases its "
            "calculation on 14 trimesters. Crucially, nothing is paid during the studies: "
            "repayment starts after entering working life, once annual income exceeds "
            "EUR 35,000, at 9% of monthly gross income. The LL.B. is awarded after ten "
            "trimesters, and after three more students may register for the State Examination. "
            "The application portal closes on 15 May at 15:00; the application fee is EUR 40 "
            "until 1 March and EUR 80 afterwards. Selection is by written and oral examination, "
            "not by grades. Teaching is in German."
        ),
        missing=("language_score",),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="EBS Universität für Wirtschaft und Recht",
        city="Visbaden",
        website="https://www.ebs.edu",
        timezone="Europe/Berlin",
        program="Law, Politics and Economics (B.A.)",
        source_url="https://www.ebs.edu/en/ebs-law-school/programmes/study-law/bachelor-in-law-politics-and-economics",
        intake_term="2027 Fall",
        duration_years=3.0,
        language="English",
        abbreviation="BA",
        tuition_amount=18160,
        tuition_currency="EUR",
        documents=("cv", "degree_certificate", "english_test"),
        notes=(
            "EBS yuridik fakultetining TO'LIQ INGLIZ TILIDAGI bakalavr dasturi — Germaniyada "
            "bunday dastur juda kam. Diqqat: daraja LL.B. emas, Bachelor of Arts (B.A.). "
            "Kontrakt 6 semestr uchun jami 54 480 EUR (barcha yig'imlar bilan), ya'ni yiliga "
            "18 160 EUR. EBS'da qat'iy ariza muddati yo'q, lekin tavsiya etiladi: kuzgi semestr "
            "uchun 30-iyungacha, bahorgi semestr uchun 30-noyabrgacha; viza kerak bo'lganlarga "
            "mos ravishda 30-may va 15-oktyabr. Ingliz tili IELTS, TOEFL, Cambridge, Pearson "
            "yoki Duolingo bilan tasdiqlanadi, lekin minimal ball sahifada ko'rsatilmagan. "
            "Hujjatlar: jadval ko'rinishidagi CV, maktab attestati va til sertifikati."
        ),
        notes_ru=(
            "Полностью АНГЛОЯЗЫЧНАЯ бакалаврская программа юридического факультета EBS — "
            "большая редкость для Германии. Важно: степень не LL.B., а Bachelor of Arts (B.A.). "
            "Стоимость — 54 480 EUR за 6 семестров (со всеми сборами), то есть 18 160 EUR в "
            "год. Жёстких дедлайнов у EBS нет, но рекомендуют подавать до 30 июня (осенний "
            "семестр) и до 30 ноября (весенний); тем, кому нужна виза, — до 30 мая и "
            "15 октября соответственно. Английский подтверждается IELTS, TOEFL, Cambridge, "
            "Pearson или Duolingo, но минимальный балл на странице не указан. Документы: "
            "резюме в табличной форме, аттестат и языковой сертификат."
        ),
        notes_en=(
            "A fully ENGLISH-TAUGHT bachelor's programme at the EBS Law School, which is rare "
            "in Germany. Note that the degree is a Bachelor of Arts (B.A.), not an LL.B. "
            "Tuition is EUR 54,480 for six semesters including all fees, i.e. EUR 18,160 a "
            "year. EBS has no fixed application deadlines but recommends applying before "
            "30 June for the fall term and 30 November for the spring term; visa applicants "
            "should apply before 30 May and 15 October respectively. English is evidenced by "
            "IELTS, TOEFL, Cambridge, Pearson or Duolingo, but no minimum score is stated on "
            "the page. Documents: a tabular CV, the school leaving qualification and the "
            "language certificate."
        ),
        missing=("language_score", "deadline"),
    ),
    # ------------------------- Davlat universitetlari -------------------------
    LawBachelorSeed(
        country_iso="DE",
        university="Carl von Ossietzky University of Oldenburg",
        city="Oldenburg",
        website="https://uol.de",
        timezone="Europe/Berlin",
        program="Comparative and European Law (LL.B.) - Hanse Law School",
        source_url="https://uol.de/en/course-of-study/comparative-european-law-fach-bachelor-331",
        intake_term="2027 Fall",
        duration_years=4.0,
        language="German, English",
        deadline_close=date(2027, 7, 15),
        notes=(
            "Hanse Law School — Oldenburg, Bremen va Groningen (Niderlandiya) universitetlari "
            "hamkorligidagi dastur; nemis huquqi bilan bir qatorda ingliz, golland, fransuz "
            "huquqi va Yevropa Ittifoqi huquqi qiyosiy tarzda o'qitiladi. Darslar nemis va "
            "ingliz tillarida. Til talabi ikki tomonlama: nemis tilidan DSH-2 yoki TestDaF "
            "(to'rt bo'limda ham 4), ingliz tilidan B2 (TOEFL, IELTS yoki Cambridge qabul "
            "qilinadi, lekin minimal ball yozilmagan). O'qish 8 semestr, qishki semestrda "
            "boshlanadi, joylar soni cheklangan. Ariza muddati — 15-iyul; chet elda ta'lim "
            "olganlar uni-assist orqali topshiradi. Kontrakt summasi sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "Hanse Law School — совместная программа университетов Ольденбурга, Бремена и "
            "Гронингена (Нидерланды); наряду с немецким правом сравнительно изучаются "
            "английское, голландское, французское право и право ЕС. Занятия идут на немецком и "
            "английском. Языковые требования двойные: немецкий — DSH-2 или TestDaF (4 по всем "
            "четырём разделам), английский — B2 (принимаются TOEFL, IELTS или Cambridge, но "
            "минимальный балл не указан). Обучение — 8 семестров, начало в зимнем семестре, "
            "число мест ограничено. Дедлайн — 15 июля; получившие образование за рубежом "
            "подают через uni-assist. Сумма контракта на странице не указана."
        ),
        notes_en=(
            "The Hanse Law School is run jointly by Oldenburg, Bremen and Groningen (the "
            "Netherlands); alongside German law it teaches English, Dutch and French law and EU "
            "law comparatively. Teaching is in German and English. The language requirement is "
            "twofold: German at DSH-2 or TestDaF with 4 in all four sections, and English at B2 "
            "(TOEFL, IELTS or Cambridge are accepted but no minimum score is given). The "
            "programme runs for eight semesters, starts in the winter semester and has a "
            "limited number of places. The deadline is 15 July; applicants educated abroad "
            "apply through uni-assist. No tuition figure is stated on the page."
        ),
        missing=("tuition", "language_score"),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="University of Mannheim",
        city="Mannheim",
        website="https://www.uni-mannheim.de",
        timezone="Europe/Berlin",
        program="Integrated LL.B. and State Examination Program in Law",
        source_url="https://www.uni-mannheim.de/en/academics/before-your-studies/programs/law/",
        intake_term="2027 Fall",
        duration_years=3.0,
        language="German",
        tuition_amount=3000,
        tuition_currency="EUR",
        deadline_close=date(2027, 7, 15),
        notes=(
            "Baden-Vyurtemberg yerida EI/EIH tashqarisidagi talabalar kontrakt to'laydi: "
            "semestriga 1 500 EUR, ya'ni yiliga 3 000 EUR (mahalliylar uchun semestr yig'imi "
            "194 EUR, ikkinchi oliy ta'lim uchun 650 EUR). Dastur ikki bosqichli: birinchi "
            "bosqich — 6 semestr, 180 ECTS, LL.B. darajasi; ikkinchi bosqich — yana 4 semestr "
            "va davlat imtihoni. Darslar nemis tilida, nemis diplomi bo'lmaganlardan C1 "
            "darajasi talab qilinadi. Ariza 1-iyundan 15-iyulgacha; tanlov attestat o'rtacha "
            "bahosi va huquq sohasidagi darsdan tashqari faoliyat bo'yicha o'tkaziladi. O'qish "
            "kuzgi semestrda (sentyabr) boshlanadi."
        ),
        notes_ru=(
            "В земле Баден-Вюртемберг студенты из стран вне ЕС/ЕЭП платят за обучение: "
            "1 500 EUR за семестр, то есть 3 000 EUR в год (для остальных семестровый взнос — "
            "194 EUR, для второго высшего — 650 EUR). Программа состоит из двух этапов: первый "
            "— 6 семестров, 180 ECTS, степень LL.B.; второй — ещё 4 семестра и государственный "
            "экзамен. Занятия на немецком, от абитуриентов без немецкого диплома требуется "
            "уровень C1. Заявки с 1 июня по 15 июля; отбор по среднему баллу аттестата и "
            "внеучебной деятельности, связанной с правом. Обучение начинается в осеннем "
            "семестре (сентябрь)."
        ),
        notes_en=(
            "In Baden-Württemberg students from outside the EU/EEA pay tuition: EUR 1,500 per "
            "semester, i.e. EUR 3,000 a year (others pay a semester fee of EUR 194, and EUR 650 "
            "for a second degree). The programme has two phases: the first is six semesters and "
            "180 ECTS leading to the LL.B., the second adds four semesters and the state "
            "examination. Teaching is in German and applicants without a German qualification "
            "need C1. Applications run 1 June to 15 July; selection is based on the university "
            "entrance qualification grade and extracurricular activities relating to law. "
            "Studies begin in the fall semester (September)."
        ),
        missing=("language_score",),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="Leibniz University Hannover",
        city="Gannover",
        # seed_llm_programs.py ham shu universitetni yozadi — sayt manzili bir
        # xil bo'lishi kerak, aks holda ikki skript har ishga tushganda
        # bir-birining qiymatini almashtirib turadi.
        website="https://www.jura.uni-hannover.de",
        timezone="Europe/Berlin",
        program="Information Technology Law and Intellectual Property Law (LL.B.)",
        source_url="https://www.uni-hannover.de/studium/studienangebot/info/studiengang/detail/informationstechnologierecht-und-recht-des-geistigen-eigentums-llb",
        intake_term="2027 Fall",
        duration_years=4.0,
        language="German, English",
        tuition_amount=0,
        tuition_currency="EUR",
        deadline_close=date(2027, 7, 15),
        notes=(
            "Germaniyada shu ko'rinishda yagona dastur: klassik huquqiy ta'lim IT va "
            "intellektual mulk huquqi bo'yicha ixtisoslashuv bilan birlashtirilgan. O'qish "
            "8 semestr (240 ECTS), qishki semestrda boshlanadi va joylar cheklangan "
            "(zulassungsbeschränkt). Darslar nemis va ingliz tillarida. Xalqaro arizachilar "
            "uchun til talabi: nemis tilidan C1 VA ingliz tilidan B2 — aniq IELTS/TOEFL bali "
            "ko'rsatilmagan. Ariza birinchi kursga 1-iyundan 15-iyulgacha. Kontrakt yo'q: "
            "yuridik fakultetning o'z sahifasiga ko'ra Gannoverda o'qish uchun kontrakt "
            "olinmaydi, faqat semestr yig'imi (~433 EUR, jamoat transporti chiptasi bilan)."
        ),
        notes_ru=(
            "Единственная в Германии программа такого рода: классическое юридическое "
            "образование объединено со специализацией по IT-праву и праву интеллектуальной "
            "собственности. Обучение — 8 семестров (240 ECTS), начало в зимнем семестре, число "
            "мест ограничено (zulassungsbeschränkt). Занятия на немецком и английском. Для "
            "иностранных абитуриентов: немецкий C1 И английский B2 — конкретный балл "
            "IELTS/TOEFL не указан. Заявки на первый курс с 1 июня по 15 июля. Платы за "
            "обучение нет: по данным страницы юридического факультета в Ганновере контракт не "
            "взимается, только семестровый взнос (~433 EUR, включая проездной)."
        ),
        notes_en=(
            "The only programme of its kind in Germany: classical legal training combined with "
            "a specialisation in IT and intellectual property law. It runs for eight semesters "
            "(240 ECTS), starts in the winter semester and has restricted admission "
            "(zulassungsbeschränkt). Teaching is in German and English. For international "
            "applicants the requirement is German at C1 AND English at B2; no IELTS or TOEFL "
            "score is specified. First-semester applications run 1 June to 15 July. There are "
            "no tuition fees: according to the law faculty's own page, studying in Hannover "
            "carries no tuition, only a semester fee of about EUR 433 including a transport "
            "ticket."
        ),
        missing=("language_score",),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="University of Münster",
        city="Myunster",
        website="https://www.uni-muenster.de",
        timezone="Europe/Berlin",
        program="International and Comparative Law (LL.B.)",
        source_url="https://www.uni-muenster.de/Jura/studium/weitere_studieng_nge/bachelor_international_and_comparative_law/voraussetzung_bewerbung.html",
        intake_term="2027 Fall",
        duration_years=3.0,
        language="German, English",
        notes=(
            "2023/24 o'quv yilidan ochilgan dastur: nemis huquqi, Common Law tizimlari hamda "
            "xalqaro va Yevropa huquqi birga o'qitiladi, o'quv rejaga chet eldagi amaliyot "
            "kiradi. Til talabi ikki tomonlama: nemis tili DSH imtihon qoidalariga muvofiq "
            "(chet el attestati bilan kelganlar uchun) va ingliz tili CEFR bo'yicha C1 — aniq "
            "IELTS/TOEFL bali ko'rsatilmagan. Birinchi semestrga qabul cheklangan "
            "(zulassungsbeschränkt); 2025/26 qishki semestridan boshlab ikkinchi semestrdan "
            "yuqorisiga qabul cheklovsiz. Kontrakt summasi ham, aniq ariza muddati ham shu "
            "sahifada yozilmagan."
        ),
        notes_ru=(
            "Программа открыта с 2023/24 учебного года: вместе изучаются немецкое право, "
            "системы общего права (Common Law), а также международное и европейское право; в "
            "учебный план входит стажировка за рубежом. Языковые требования двойные: немецкий "
            "по правилам экзамена DSH (для тех, кто поступает с зарубежным аттестатом) и "
            "английский на уровне C1 по CEFR — конкретный балл IELTS/TOEFL не указан. Приём на "
            "первый семестр ограничен (zulassungsbeschränkt); начиная с зимнего семестра "
            "2025/26 со второго семестра и выше приём свободный. Ни сумма контракта, ни точный "
            "дедлайн на этой странице не указаны."
        ),
        notes_en=(
            "Open since the 2023/24 academic year, the programme covers German law, common law "
            "systems and international and European law together, and an internship abroad is "
            "part of the curriculum. The language requirement is twofold: German in line with "
            "the DSH examination rules for applicants with a foreign school qualification, and "
            "English at CEFR C1; no IELTS or TOEFL score is specified. Admission to the first "
            "semester is restricted (zulassungsbeschränkt); from the 2025/26 winter semester "
            "entry to the second semester and above is unrestricted. Neither a tuition figure "
            "nor a precise deadline is stated on this page."
        ),
        missing=("tuition", "language_score", "deadline"),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="Leuphana University Lüneburg",
        city="Lyuneburg",
        website="https://www.leuphana.de",
        timezone="Europe/Berlin",
        program="Law (LL.B.)",
        source_url="https://www.leuphana.de/en/college/bachelor/law.html",
        intake_term="2027 Fall",
        duration_years=3.0,
        language="German",
        tuition_amount=0,
        tuition_currency="EUR",
        deadline_close=date(2027, 7, 15),
        notes=(
            "Leuphana kollejining «Law» yo'nalishi: kontrakt yo'q, faqat semestr yig'imi "
            "452,92 EUR. O'qish 3 yil (6 semestr), oktyabr boshida — qishki semestrda "
            "boshlanadi. Onlayn ariza may o'rtasidan 15-iyulgacha. Darslar nemis tilida, "
            "sahifada nemis tilini yaxshi bilish va ingliz tili ko'nikmalari talab qilinishi "
            "aytilgan, lekin aniq sertifikat darajasi yoki bali ko'rsatilmagan."
        ),
        notes_ru=(
            "Направление «Law» в колледже Leuphana: платы за обучение нет, только семестровый "
            "взнос 452,92 EUR. Обучение длится 3 года (6 семестров) и начинается в начале "
            "октября, в зимнем семестре. Онлайн-заявки с середины мая по 15 июля. Занятия на "
            "немецком; на странице указано требование хорошего немецкого и навыков английского, "
            "но конкретный уровень сертификата или балл не назван."
        ),
        notes_en=(
            "The Law major at Leuphana College: no tuition fees, only a semester fee of "
            "EUR 452.92. The programme lasts three years (six semesters) and starts at the "
            "beginning of October in the winter semester. Online applications run from mid-May "
            "to 15 July. Teaching is in German; the page states that a good command of German "
            "and English skills are required but names no certificate level or score."
        ),
        missing=("language_score",),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="University of Bayreuth",
        city="Bayroyt",
        website="https://www.uni-bayreuth.de",
        timezone="Europe/Berlin",
        program="Law and Business (LL.B.)",
        source_url="https://www.uni-bayreuth.de/en/bachelor/law-and-business",
        intake_term="2027 Fall",
        duration_years=3.0,
        language="German",
        notes=(
            "Huquq va iqtisodiyotni birlashtirgan fanlararo bakalavr dasturi — Bayroyt "
            "universitetining tanilgan yo'nalishlaridan biri. Darslar to'liq nemis tilida; "
            "qabul uchun nemis tilidan DSH-2 yoki unga teng sertifikat talab qilinadi. "
            "Bitirgandan so'ng davlat imtihoniga tayyorgarlikni davom ettirish yoki "
            "magistraturaga o'tish mumkin. Kontrakt summasi, ariza muddati va ingliz tili "
            "talabi bu sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "Междисциплинарная бакалаврская программа на стыке права и экономики — одно из "
            "известных направлений Байройтского университета. Занятия полностью на немецком; "
            "для поступления требуется сертификат DSH-2 или равноценный. После выпуска можно "
            "продолжить подготовку к государственному экзамену или пойти в магистратуру. Сумма "
            "контракта, дедлайн подачи и требования по английскому на этой странице не указаны."
        ),
        notes_en=(
            "An interdisciplinary bachelor's programme combining law and business, one of "
            "Bayreuth's better-known offerings. Teaching is entirely in German and admission "
            "requires a DSH-2 German certificate or an equivalent. Graduates can go on to "
            "prepare for the state examination or move to a master's programme. No tuition "
            "figure, application deadline or English requirement is stated on this page."
        ),
        missing=("tuition", "language_score", "deadline"),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="University of Siegen",
        city="Zigen",
        website="https://www.uni-siegen.de",
        timezone="Europe/Berlin",
        program="German and European Business Law (LL.B.)",
        source_url="https://www.uni-siegen.de/studium/bachelor/deutsches-und-europaeisches-wirtschaftsrecht",
        intake_term="2027 Fall",
        duration_years=3.0,
        language="German, English",
        notes=(
            "Zigen universiteti 1999-yilda Germaniyada birinchi bo'lib iqtisodiy huquq "
            "(Wirtschaftsrecht) yo'nalishini ochgan va shu soha bo'yicha yetakchi markaz "
            "hisoblanadi. O'qish 6 semestr, qishki semestrda boshlanadi; darslar nemis tilida, "
            "qisman ingliz tilida. Kontrakt summasi, ariza muddati va til sertifikati talabi "
            "dastur sahifasida ko'rsatilmagan."
        ),
        notes_ru=(
            "Университет Зигена в 1999 году первым в Германии открыл направление "
            "хозяйственного права (Wirtschaftsrecht) и считается ведущим центром в этой "
            "области. Обучение — 6 семестров, начало в зимнем семестре; занятия на немецком, "
            "частично на английском. Сумма контракта, дедлайн и требования к языковому "
            "сертификату на странице программы не указаны."
        ),
        notes_en=(
            "In 1999 Siegen became the first German university to offer business law "
            "(Wirtschaftsrecht) as a degree and it remains a leading centre for the subject. "
            "The programme runs for six semesters and starts in the winter semester; teaching "
            "is in German and partly in English. No tuition figure, deadline or language "
            "certificate requirement is stated on the programme page."
        ),
        missing=("tuition", "language_score", "deadline"),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="University of Kassel",
        city="Kassel",
        website="https://www.uni-kassel.de",
        timezone="Europe/Berlin",
        program="Business Law (LL.B.)",
        source_url="https://www.uni-kassel.de/uni/studium/wirtschaftsrecht-bachelor/studienaufbau.html",
        intake_term="2027 Fall",
        duration_years=3.5,
        language="German",
        notes=(
            "Iqtisodiy huquq bo'yicha bakalavr: dastlabki uch semestrda fuqarolik huquqi, "
            "mehnat va ijtimoiy huquq, savdo va korporativ huquq asoslari hamda iqtisodiyot va "
            "buxgalteriya o'qitiladi. Uchinchi semestrdan keyin 20 haftalik majburiy amaliyot "
            "moduli bor. O'qish 7 semestr. Darslar nemis tilida, lekin o'quv rejaga «Legal and "
            "Business English» moduli kiradi. Kontrakt summasi, ariza muddati va til talabi bu "
            "sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "Бакалавриат по хозяйственному праву: в первых трёх семестрах изучаются основы "
            "гражданского, трудового и социального, торгового и корпоративного права, а также "
            "экономика и бухгалтерский учёт. После третьего семестра предусмотрен обязательный "
            "20-недельный практический модуль. Срок обучения — 7 семестров. Занятия на "
            "немецком, но в программу входит модуль «Legal and Business English». Сумма "
            "контракта, дедлайн и языковые требования на этой странице не указаны."
        ),
        notes_en=(
            "A business law bachelor's degree: the first three semesters cover the foundations "
            "of civil law, labour and social law, commercial and corporate law, plus economics "
            "and accounting. A compulsory 20-week practical module follows the third semester. "
            "The programme lasts seven semesters. Teaching is in German, but the curriculum "
            "includes a «Legal and Business English» module. No tuition figure, deadline or "
            "language requirement is stated on this page."
        ),
        missing=("tuition", "language_score", "deadline"),
    ),
    # --------------------- Amaliy fanlar oliygohlari (UAS) ---------------------
    LawBachelorSeed(
        country_iso="DE",
        university="Frankfurt University of Applied Sciences",
        city="Frankfurt",
        website="https://www.frankfurt-university.de",
        timezone="Europe/Berlin",
        program="Business Law (LL.B.)",
        source_url="https://www.frankfurt-university.de/de/studium/bachelor-studiengange/wirtschaftsrecht-business-law-bachelor-of-laws-llb/fuer-studieninteressierte/",
        intake_term="2027 Fall",
        duration_years=3.5,
        language="German",
        deadline_close=date(2027, 7, 15),
        notes=(
            "Amaliyotga yo'naltirilgan iqtisodiy huquq bakalavri: 7 semestr, 210 ECTS, ZEvA "
            "akkreditatsiyasi. Oltinchi semestr — korxonada majburiy amaliyot semestri. Qabul "
            "yiliga ikki marta: qishki va yozgi semestrga. Ariza muddati qishki semestr uchun "
            "15-iyul, yozgi semestr uchun 15-yanvar (Ausschlussfrist — qat'iy muddat). Joylar "
            "cheklangan, tanlov mahalliy NC tartibida. Darslar nemis tilida; sahifada ingliz "
            "tili va matematikani yaxshi bilish tavsiya etilgan, lekin sertifikat talab "
            "qilinmagan. Bitiruvchilar Frankfurt UAS'ning magistratura dasturini davom ettirishi "
            "mumkin. Kontrakt summasi sahifada ko'rsatilmagan."
        ),
        notes_ru=(
            "Практико-ориентированный бакалавриат по хозяйственному праву: 7 семестров, "
            "210 ECTS, аккредитация ZEvA. Шестой семестр — обязательная практика на "
            "предприятии. Приём дважды в год: на зимний и летний семестр. Дедлайн — 15 июля для "
            "зимнего и 15 января для летнего семестра (Ausschlussfrist, жёсткий срок). Число "
            "мест ограничено, отбор по местному NC. Занятия на немецком; на странице "
            "рекомендованы хорошие знания английского и математики, но сертификат не требуется. "
            "Выпускники могут продолжить обучение в магистратуре Frankfurt UAS. Сумма контракта "
            "на странице не указана."
        ),
        notes_en=(
            "A practice-oriented business law bachelor's degree: seven semesters, 210 ECTS, "
            "accredited by ZEvA. The sixth semester is a compulsory placement in a company. "
            "There are two intakes a year, winter and summer. The deadline is 15 July for the "
            "winter semester and 15 January for the summer semester (Ausschlussfrist, a strict "
            "cut-off). Places are limited and allocated through a local numerus clausus "
            "procedure. Teaching is in German; the page recommends good English and mathematics "
            "but requires no certificate. Graduates can continue into Frankfurt UAS's master's "
            "programme. No tuition figure is stated on the page."
        ),
        missing=("tuition", "language_score"),
    ),
    LawBachelorSeed(
        country_iso="DE",
        university="Osnabrück University of Applied Sciences",
        city="Osnabryuk",
        website="https://www.hs-osnabrueck.de",
        timezone="Europe/Berlin",
        program="Business Law (LL.B.)",
        source_url="https://www.hs-osnabrueck.de/studium/studienangebot/bachelor/wirtschaftsrecht-llb/kurzportraet/",
        intake_term="2027 Fall",
        duration_years=3.5,
        language="German",
        tuition_amount=0,
        tuition_currency="EUR",
        deadline_close=date(2027, 7, 15),
        notes=(
            "Iqtisodiy huquq bakalavri: 7 semestr, 180 ECTS. Kontrakt yo'q, faqat semestr "
            "badali ~443 EUR. Yiliga 109 ta o'quv o'rni ajratiladi, ya'ni qabul cheklangan. "
            "Qabul ham qishki, ham yozgi semestrga: ariza qishki semestr uchun maydan "
            "15-iyulgacha, yozgi semestr uchun noyabrdan 15-yanvargacha (Ausschlussfrist). "
            "Chet el attestati bilan kelganlar uchun muddatlar boshqacha — uni-assist orqali "
            "topshiriladi. Darslar nemis tilida; til sertifikati darajasi ariza sahifasida "
            "ko'rsatilmagan."
        ),
        notes_ru=(
            "Бакалавриат по хозяйственному праву: 7 семестров, 180 ECTS. Платы за обучение нет, "
            "только семестровый взнос около 443 EUR. Выделяется 109 мест в год, то есть приём "
            "ограничен. Набор и на зимний, и на летний семестр: заявки с мая по 15 июля "
            "(зимний) и с ноября по 15 января (летний), это Ausschlussfrist. Для поступающих с "
            "зарубежным аттестатом сроки другие — подача через uni-assist. Занятия на немецком; "
            "уровень языкового сертификата на странице подачи не указан."
        ),
        notes_en=(
            "A business law bachelor's degree: seven semesters, 180 ECTS. There are no tuition "
            "fees, only a semester contribution of about EUR 443. With 109 places a year, "
            "admission is restricted. There are both winter and summer intakes: applications "
            "run from May to 15 July for the winter semester and from November to 15 January "
            "for the summer semester (Ausschlussfrist). Applicants with a foreign school "
            "qualification have different dates and apply through uni-assist. Teaching is in "
            "German; the application page names no language certificate level."
        ),
        missing=("language_score",),
    ),
]

# DIQQAT: "rasmiy sahifadan tekshirilgan" va "quyidagi maydonlar bo'sh" degan
# jumlalar BAZAGA YOZILMAYDI — Mini App ularni `verified_at` va
# `missing_fields` dan foydalanuvchi tilida o'zi yasaydi.


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
        key = (university.id, seed.program, DEGREE_LEVEL)

        program = existing.get(key)
        if program is None:
            program = Program(
                university_id=university.id,
                name=seed.program,
                degree_level=DEGREE_LEVEL,
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
    session: AsyncSession, program: Program, seed: LawBachelorSeed, now: datetime
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
    with_deadline = sum(1 for s in SEEDS if s.deadline_close is not None)
    in_english = sum(1 for s in SEEDS if "English" in s.language)

    print(f"Universitetlar: {uni_created} ta yangi, {uni_updated} ta yangilandi")
    print(f"Huquq bakalavri dasturlari: {prog_created} ta yangi, {prog_updated} ta yangilandi")
    print(
        f"Tasdiqlangan qiymatlar: {with_tuition}/{len(SEEDS)} kontrakt, "
        f"{with_deadline}/{len(SEEDS)} muddat; {in_english}/{len(SEEDS)} tasida "
        "ingliz tili o'qitish tilida bor"
    )


if __name__ == "__main__":
    asyncio.run(main())
