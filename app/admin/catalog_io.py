"""Katalogni CSV orqali import/eksport qilish (davlatlar, universitetlar, dasturlar).

Bu modul HTTP'ga bog'liq emas — faylni o'qish, tekshirish va saqlash shu yerda,
admin sahifasi (app/admin/csv_views.py) faqat uni chaqiradi. Shu tufayli
mantiq to'g'ridan-to'g'ri testlanadi.

Asosiy qoidalar:
  * Upsert kalitlari: davlat — iso_code; universitet — (name, country_iso);
    dastur — (universitet, name, degree_level). Nomlar registrga sezgir emas.
  * BO'SH KATAK MAVJUD QIYMATNI O'ZGARTIRMAYDI. Import hech qachon admin
    kiritgan ma'lumotni o'chirmaydi — qiymatni tozalash faqat adminkada.
  * Ikki bosqich: `build_plan` bazaga hech narsa yozmaydi (oldindan ko'rish),
    `apply_plan` esa rejani bitta tranzaksiyada saqlaydi. Bitta xato qator
    bo'lsa ham reja saqlanmaydi.
  * Bir importda uchala fayl birga berilishi mumkin: ular davlatlar ->
    universitetlar -> dasturlar tartibida ishlanadi va keyingisi oldingisida
    yaratilayotgan yozuvga tayana oladi (bo'sh bazani eksportdan tiklash
    bitta qadam bo'lishi uchun).
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    INSTRUCTION_LANGUAGES,
    REQUIRED_DOCUMENTS,
    Country,
    CoverageType,
    Deadline,
    DeadlineType,
    DegreeLevel,
    Field,
    Program,
    ProgramCost,
    ProgramRequirement,
    Scholarship,
    ScholarshipDeadline,
    University,
    UniversityChoiceType,
)

KINDS = ("countries", "universities", "programs", "scholarships")

COLUMNS: dict[str, list[str]] = {
    "countries": ["iso_code", "name_uz", "name_ru", "name_en"],
    "universities": ["country_iso", "name", "city", "website", "timezone", "logo_url", "ranking"],
    "programs": [
        "country_iso",
        "university_name",
        "name",
        "abbreviation",
        "degree_level",
        "field_code",
        "language_of_instruction",
        "duration_years",
        "intake_term",
        "source_url",
        "notes",
        "notes_ru",
        "notes_en",
        # Tafsilotlar (bo'sh katak — o'zgarmaydi)
        "ielts_min",
        "toefl_min",
        "tuition_amount",
        "tuition_currency",
        "deadline_close",
        "has_application_fee",
        "application_fee_amount",
        "application_fee_currency",
        "has_scholarship",
        "scholarship_url",
        "required_documents",
        "requirements_text",
    ],
    "scholarships": [
        "name",
        "country_isos",
        "description",
        "description_ru",
        "description_en",
        "logo_url",
        "coverage_type",
        "coverage_percent",
        "stipend_amount",
        "stipend_max",
        "stipend_period",
        "currency",
        "ielts_min",
        "toefl_min",
        "work_experience_years",
        "degree_levels",
        "study_language",
        "duration_min_years",
        "duration_max_years",
        "selection_stages",
        "extras_flight",
        "extras_insurance",
        "extras_dormitory",
        "extras_language_course",
        "age_limit",
        "citizenship_eligible",
        "university_choice",
        "application_linked_to_program",
        "universities_text",
        "selected_by",
        "requirements_text",
        "source_url",
        "deadline_close",
        "intake_term",
    ],
}

# Bir katakda bir nechta qiymat (hujjatlar, talab qatorlari) shu belgi bilan ajratiladi.
LIST_SEPARATOR = "|"

# Kalit ustunlar sarlavhada bo'lishi SHART; qolganlari ixtiyoriy
# (yo'q ustun = bo'sh katak = qiymat o'zgarmaydi).
KEY_COLUMNS: dict[str, list[str]] = {
    "countries": ["iso_code"],
    "universities": ["country_iso", "name"],
    "programs": ["country_iso", "university_name", "name", "degree_level"],
    "scholarships": ["name"],
}

# Yangi yozuv yaratish uchun majburiy ustunlar (mavjudini yangilashda emas).
REQUIRED_FOR_NEW: dict[str, list[str]] = {
    "countries": ["name_uz", "name_ru", "name_en"],
    "universities": ["city", "timezone"],
    "programs": [
        "field_code",
        "language_of_instruction",
        "duration_years",
        "intake_term",
        "source_url",
    ],
    "scholarships": ["coverage_type", "university_choice", "source_url"],
}

SAMPLE_ROWS: dict[str, dict[str, str]] = {
    "countries": {
        "iso_code": "DE",
        "name_uz": "Germaniya",
        "name_ru": "Германия",
        "name_en": "Germany",
    },
    "universities": {
        "country_iso": "DE",
        "name": "Technical University of Munich",
        "city": "Munich",
        "website": "https://www.tum.de",
        "timezone": "Europe/Berlin",
        "logo_url": "",
        "ranking": "28",
    },
    "programs": {
        "country_iso": "DE",
        "university_name": "Technical University of Munich",
        "name": "Informatics",
        "abbreviation": "M.Sc.",
        "degree_level": "master",
        "field_code": "cs_it",
        "language_of_instruction": "English",
        "duration_years": "2",
        "intake_term": "2027 Winter",
        "source_url": "https://www.tum.de/en/studies/degree-programs/detail/informatics-master",
        "notes": "",
        "notes_ru": "",
        "notes_en": "",
        "ielts_min": "6.5",
        "toefl_min": "88",
        "tuition_amount": "54000",
        "tuition_currency": "EUR",
        "deadline_close": "2027-05-31",
        "has_application_fee": "no",
        "application_fee_amount": "",
        "application_fee_currency": "",
        "has_scholarship": "",
        "scholarship_url": "",
        "required_documents": "transcript|degree_certificate|cv|english_test",
        "requirements_text": "Bachelor's in computer science or related field",
    },
    "scholarships": {
        "name": "Chevening Scholarship",
        "country_isos": "GB",
        "description": "Buyuk Britaniya hukumatining bir yillik magistratura stipendiyasi.",
        "description_ru": "",
        "description_en": "UK government scholarship for a one-year master's degree.",
        "logo_url": "",
        "coverage_type": "full",
        "coverage_percent": "",
        "stipend_amount": "1500",
        "stipend_max": "",
        "stipend_period": "month",
        "currency": "GBP",
        "ielts_min": "6.5",
        "toefl_min": "",
        "work_experience_years": "2",
        "degree_levels": "master",
        "study_language": "English",
        "duration_min_years": "1",
        "duration_max_years": "1",
        "selection_stages": "3",
        "extras_flight": "yes",
        "extras_insurance": "no",
        "extras_dormitory": "no",
        "extras_language_course": "no",
        "age_limit": "",
        "citizenship_eligible": "yes",
        "university_choice": "user_chooses",
        "application_linked_to_program": "yes",
        "universities_text": "Buyuk Britaniyadagi istalgan universitet",
        "selected_by": "Chevening kotibiyati va Toshkentdagi elchixona",
        "requirements_text": "Bakalavr diplomi|Kamida 2 yil ish tajribasi",
        "source_url": "https://www.chevening.org/scholarship/uzbekistan/",
        "deadline_close": "2027-11-02",
        "intake_term": "2027 Autumn",
    },
}

KIND_LABELS = {
    "countries": "Davlatlar",
    "universities": "Universitetlar",
    "programs": "Dasturlar",
    "scholarships": "Grantlar",
}

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000

STATUS_NEW = "new"
STATUS_UPDATE = "update"
STATUS_UNCHANGED = "unchanged"
STATUS_ERROR = "error"

_ISO_RE = re.compile(r"^[A-Z]{2}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_URL_RE = re.compile(r"^https?://\S+$")


class CsvFileError(Exception):
    """Fayl umuman o'qib bo'lmaydigan holatda (kodirovka, sarlavha, hajm)."""


# ------------------------------ o'qish ------------------------------


def parse_csv(data: bytes, kind: str) -> list[tuple[int, dict[str, str]]]:
    """CSV faylni `(qator raqami, {ustun: qiymat})` ro'yxatiga aylantiradi.

    UTF-8 (BOM bilan ham), ajratuvchi `,` yoki `;` (Excel'ning ba'zi
    lokallari `;` ishlatadi) — sarlavhadan aniqlanadi. Bo'sh qatorlar
    o'tkazib yuboriladi, qiymatlar chetdagi bo'shliqlardan tozalanadi.
    """
    if kind not in COLUMNS:
        raise CsvFileError(f"Noma'lum tur: {kind}")
    if len(data) > MAX_BYTES:
        raise CsvFileError(f"Fayl juda katta: {len(data) // 1024} KB (chegara 5 MB)")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFileError(
            "Fayl UTF-8 emas. Excel'da \"CSV UTF-8\" formatida saqlang."
        ) from exc

    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    try:
        header = next(reader)
    except StopIteration as exc:
        raise CsvFileError("Fayl bo'sh") from exc
    header = [h.strip().lower() for h in header]

    unknown = [h for h in header if h and h not in COLUMNS[kind]]
    if unknown:
        raise CsvFileError(
            f"Noma'lum ustun(lar): {', '.join(unknown)}. "
            f"Kutilgan: {', '.join(COLUMNS[kind])}"
        )
    missing = [c for c in KEY_COLUMNS[kind] if c not in header]
    if missing:
        raise CsvFileError(f"Majburiy ustun(lar) yo'q: {', '.join(missing)}")
    if len(set(header)) != len(header):
        raise CsvFileError("Sarlavhada takrorlangan ustun bor")

    rows: list[tuple[int, dict[str, str]]] = []
    for line_no, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        if len(rows) >= MAX_ROWS:
            raise CsvFileError(f"Qatorlar soni {MAX_ROWS} dan oshdi")
        row = {column: "" for column in COLUMNS[kind]}
        for column, value in zip(header, values, strict=False):
            if column:
                row[column] = value.strip()
        rows.append((line_no, row))
    return rows


# ------------------------------ reja ------------------------------


@dataclass
class RowPlan:
    kind: str
    line: int
    key: str  # foydalanuvchiga ko'rinadigan kalit, masalan "DE / TUM"
    status: str
    errors: list[str] = field(default_factory=list)
    # Yangilanadigan maydonlar: {maydon: (eski, yangi)}
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    # Saqlash uchun tayyor qiymatlar (bo'sh kataklar kirmaydi)
    values: dict[str, Any] = field(default_factory=dict)
    target_id: int | None = None  # yangilanadigan yozuv ID'si
    # Bog'lanishlar (yangi yozuvlarga ham): davlat ISO / universitet kaliti
    ref: dict[str, Any] = field(default_factory=dict)
    # Dasturning bog'liq jadvallari uchun qiymatlar:
    # {"requirement": {...}, "cost": {...}, "deadline": {"date_utc": ...}}
    related: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class ImportPlan:
    rows: list[RowPlan] = field(default_factory=list)
    file_errors: dict[str, str] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return bool(self.file_errors) or any(r.status == STATUS_ERROR for r in self.rows)

    def counts(self) -> dict[str, int]:
        result = {STATUS_NEW: 0, STATUS_UPDATE: 0, STATUS_UNCHANGED: 0, STATUS_ERROR: 0}
        for row in self.rows:
            result[row.status] += 1
        return result

    def fingerprint(self) -> list[list[Any]]:
        """Oldindan ko'rish va tasdiqlash orasida baza o'zgarganini aniqlash uchun."""
        return [
            [r.kind, r.line, r.status, sorted(r.changes)] for r in self.rows
        ]


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).normalize()


def _diff(record: Any, values: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    """Faqat berilgan (bo'sh bo'lmagan) qiymatlar bo'yicha farq."""
    changes = {}
    for name, new in values.items():
        old = getattr(record, name)
        if isinstance(new, Decimal):
            same = _decimal(old) == new
        elif hasattr(old, "value"):  # Enum
            same = old == new
        else:
            same = old == new
        if not same:
            changes[name] = (old.value if hasattr(old, "value") else old,
                             new.value if hasattr(new, "value") else new)
    return changes


def _check_url(value: str, column: str, errors: list[str]) -> None:
    if value and not _URL_RE.match(value):
        errors.append(f"{column}: http(s):// bilan boshlanadigan havola bo'lishi kerak")


async def build_plan(
    session: AsyncSession, files: dict[str, list[tuple[int, dict[str, str]]]]
) -> ImportPlan:
    """Fayllarni tekshirib, har qator uchun holatni hisoblaydi. BAZAGA YOZMAYDI."""
    plan = ImportPlan()

    countries = {
        c.iso_code.upper(): c for c in (await session.execute(select(Country))).scalars()
    }
    new_country_isos: set[str] = set()
    seen_isos: set[str] = set()
    for line, row in files.get("countries", []):
        plan.rows.append(_plan_country(line, row, countries, new_country_isos, seen_isos))

    universities: dict[tuple[str, str], list[University]] = {}
    for uni in (
        await session.execute(select(University).options(selectinload(University.country)))
    ).scalars():
        universities.setdefault((_norm(uni.name), uni.country.iso_code.upper()), []).append(uni)
    new_university_keys: set[tuple[str, str]] = set()
    seen_universities: set[tuple[str, str]] = set()
    known_isos = set(countries) | new_country_isos
    for line, row in files.get("universities", []):
        plan.rows.append(
            _plan_university(
                line, row, known_isos, universities, new_university_keys, seen_universities
            )
        )

    if files.get("programs"):
        fields = {f.code: f for f in (await session.execute(select(Field))).scalars()}
        programs: dict[tuple[int, str, DegreeLevel], Program] = {
            (p.university_id, _norm(p.name), p.degree_level): p
            for p in (
                await session.execute(
                    select(Program).options(
                        selectinload(Program.requirement),
                        selectinload(Program.cost),
                        selectinload(Program.deadlines),
                    )
                )
            ).scalars()
        }
        seen: set[tuple[str, str, str, DegreeLevel]] = set()
        for line, row in files["programs"]:
            plan.rows.append(
                _plan_program(
                    line, row, fields, universities, new_university_keys, programs, seen
                )
            )

    if files.get("scholarships"):
        scholarships = {
            _norm(item.name): item
            for item in (
                await session.execute(
                    select(Scholarship).options(
                        selectinload(Scholarship.countries),
                        selectinload(Scholarship.deadlines),
                    )
                )
            ).scalars()
        }
        seen_scholarships: set[str] = set()
        for line, row in files["scholarships"]:
            plan.rows.append(
                _plan_scholarship(line, row, known_isos, scholarships, seen_scholarships)
            )
    return plan


def _plan_scholarship(
    line: int,
    row: dict[str, str],
    known_isos: set[str],
    scholarships: dict[str, Scholarship],
    seen: set[str],
) -> RowPlan:
    name = row["name"]
    result = RowPlan("scholarships", line, name or "—", STATUS_ERROR)
    errors = result.errors

    if not name:
        errors.append("name: grant nomi bo'sh")

    values: dict[str, Any] = {}
    related: dict[str, Any] = {}

    isos = [code.upper() for code in _split_list(row["country_isos"])]
    unknown = [code for code in isos if code not in known_isos]
    if unknown:
        errors.append(
            f"country_isos: {', '.join(unknown)} davlat(lar)i bazada ham, faylda ham yo'q"
        )
    if isos:
        related["country_isos"] = isos

    for column in (
        "description", "description_ru", "description_en", "logo_url",
        "study_language", "selected_by", "currency",
    ):
        if row[column]:
            values[column] = row[column]
    if row["currency"]:
        code = _currency(row["currency"], "currency", errors)
        if code:
            values["currency"] = code
    for column in ("universities_text", "requirements_text"):
        if row[column]:
            values[column] = "\n".join(_split_list(row[column]))
    _check_url(row["logo_url"], "logo_url", errors)
    _check_url(row["source_url"], "source_url", errors)
    if row["source_url"]:
        values["source_url"] = row["source_url"]

    if row["coverage_type"]:
        try:
            values["coverage_type"] = CoverageType(row["coverage_type"].lower())
        except ValueError:
            errors.append(
                f"coverage_type: {row['coverage_type']!r} noto'g'ri "
                f"(ruxsat: {', '.join(c.value for c in CoverageType)})"
            )
    if row["university_choice"]:
        try:
            values["university_choice"] = UniversityChoiceType(row["university_choice"].lower())
        except ValueError:
            errors.append(
                f"university_choice: {row['university_choice']!r} noto'g'ri "
                f"(ruxsat: {', '.join(u.value for u in UniversityChoiceType)})"
            )

    if row["study_language"] and row["study_language"] not in INSTRUCTION_LANGUAGES:
        errors.append(
            f"study_language: {row['study_language']!r} ro'yxatda yo'q "
            f"(ruxsat: {', '.join(INSTRUCTION_LANGUAGES)})"
        )
        values.pop("study_language", None)

    if row["degree_levels"]:
        levels = [level.lower() for level in _split_list(row["degree_levels"])]
        allowed = {d.value for d in DegreeLevel}
        wrong = [level for level in levels if level not in allowed]
        if wrong:
            errors.append(
                f"degree_levels: {', '.join(wrong)} noto'g'ri "
                f"(ruxsat: {', '.join(sorted(allowed))})"
            )
        else:
            values["degree_levels"] = [d.value for d in DegreeLevel if d.value in levels]

    if row["stipend_period"]:
        if row["stipend_period"] in ("month", "year"):
            values["stipend_period"] = row["stipend_period"]
        else:
            errors.append("stipend_period: faqat 'month' yoki 'year'")

    for column, upper in (
        # KRW/HUF/JPY kabi valyutalarda oylik stipendiya millionlarda bo'ladi.
        ("stipend_amount", 100_000_000),
        ("stipend_max", 100_000_000),
        ("duration_min_years", 15),
        ("duration_max_years", 15),
    ):
        if row[column]:
            number = _positive_decimal(row[column], column, errors, upper)
            if number is not None:
                values[column] = number

    if row["ielts_min"]:
        ielts = _positive_decimal(row["ielts_min"], "ielts_min", errors, 9)
        if ielts is not None:
            if (ielts * 2) % 1:
                errors.append("ielts_min: 0.5 qadam bilan bo'lishi kerak (6, 6.5, 7...)")
            else:
                values["ielts_min"] = ielts
    for column, low, high in (
        ("toefl_min", 1, 120),
        ("coverage_percent", 1, 100),
        ("selection_stages", 1, 10),
        ("age_limit", 11, 99),
        ("work_experience_years", 0, 50),
    ):
        if row[column]:
            if row[column].isdigit() and low <= int(row[column]) <= high:
                values[column] = int(row[column])
            else:
                errors.append(f"{column}: {low} dan {high} gacha butun son bo'lishi kerak")

    for column in (
        "extras_flight", "extras_insurance", "extras_dormitory", "extras_language_course",
        "citizenship_eligible", "application_linked_to_program",
    ):
        if row[column]:
            flag = _yes_no(row[column], column, errors)
            if flag is not None:
                values[column] = flag

    if row["deadline_close"]:
        try:
            day = date.fromisoformat(row["deadline_close"])
            related["deadline"] = {
                "date_utc": datetime(day.year, day.month, day.day, tzinfo=UTC),
                "intake_term": row["intake_term"] or "—",
            }
        except ValueError:
            errors.append("deadline_close: sana YYYY-MM-DD ko'rinishida bo'lishi kerak")

    if errors:
        return result

    key = _norm(name)
    if key in seen:
        errors.append("Faylda bu grant ikki marta uchraydi")
        return result
    seen.add(key)

    result.related = related
    existing = scholarships.get(key)
    if existing is None:
        missing = [c for c in REQUIRED_FOR_NEW["scholarships"] if not row[c]]
        if missing:
            errors.append(f"Yangi grant uchun majburiy: {', '.join(missing)}")
            return result
        result.status = STATUS_NEW
        result.values = {"name": name, **values}
        return result

    result.target_id = existing.id
    result.values = values
    result.changes = _diff(existing, values)
    if related.get("country_isos") and sorted(
        c.iso_code.upper() for c in existing.countries
    ) != sorted(set(related["country_isos"])):
        result.changes["countries"] = (
            ", ".join(sorted(c.iso_code for c in existing.countries)),
            ", ".join(sorted(set(related["country_isos"]))),
        )
    if related.get("deadline"):
        close = next(
            (d for d in existing.deadlines if d.type == DeadlineType.APPLICATION_CLOSE), None
        )
        if close is None or close.date_utc.date() != related["deadline"]["date_utc"].date():
            result.changes["deadline_close"] = (
                close.date_utc.date().isoformat() if close else None,
                related["deadline"]["date_utc"].date().isoformat(),
            )
    result.status = STATUS_UPDATE if result.changes else STATUS_UNCHANGED
    return result


def _plan_country(
    line: int,
    row: dict[str, str],
    countries: dict[str, Country],
    new_isos: set[str],
    seen: set[str],
) -> RowPlan:
    iso = row["iso_code"].upper()
    result = RowPlan("countries", line, iso or "—", STATUS_ERROR)
    if not _ISO_RE.match(iso):
        result.errors.append("iso_code: ikki lotin harfi bo'lishi kerak (masalan DE)")
        return result
    if iso in seen:
        result.errors.append("Faylda bu davlat ikki marta uchraydi")
        return result
    seen.add(iso)

    values = {k: row[k] for k in ("name_uz", "name_ru", "name_en") if row[k]}
    existing = countries.get(iso)
    if existing is None:
        missing = [c for c in REQUIRED_FOR_NEW["countries"] if not row[c]]
        if missing:
            result.errors.append(f"Yangi davlat uchun majburiy: {', '.join(missing)}")
            return result
        new_isos.add(iso)
        result.status = STATUS_NEW
        result.values = {"iso_code": iso, **values}
        return result

    result.target_id = existing.id
    result.values = values
    result.changes = _diff(existing, values)
    result.status = STATUS_UPDATE if result.changes else STATUS_UNCHANGED
    return result


def _plan_university(
    line: int,
    row: dict[str, str],
    known_isos: set[str],
    universities: dict[tuple[str, str], list[University]],
    new_keys: set[tuple[str, str]],
    seen: set[tuple[str, str]],
) -> RowPlan:
    iso = row["country_iso"].upper()
    name = row["name"]
    key = (_norm(name), iso)
    result = RowPlan("universities", line, f"{iso or '—'} / {name or '—'}", STATUS_ERROR)
    errors = result.errors

    if not name:
        errors.append("name: universitet nomi bo'sh")
    if iso not in known_isos:
        shown = iso or "(bo'sh)"
        errors.append(f"country_iso: {shown} davlati bazada ham, faylda ham yo'q")

    values: dict[str, Any] = {}
    for column in ("city", "website", "logo_url"):
        if row[column]:
            values[column] = row[column]
    _check_url(row["website"], "website", errors)
    _check_url(row["logo_url"], "logo_url", errors)
    if row["timezone"]:
        try:
            ZoneInfo(row["timezone"])
            values["timezone"] = row["timezone"]
        except (ZoneInfoNotFoundError, ValueError):
            errors.append(f"timezone: {row['timezone']!r} haqiqiy IANA zonasi emas")
    if row["ranking"]:
        if row["ranking"].isdigit() and int(row["ranking"]) >= 1:
            values["ranking"] = int(row["ranking"])
        else:
            errors.append("ranking: musbat butun son bo'lishi kerak")
    if errors:
        return result

    if key in seen:
        errors.append("Faylda bu universitet ikki marta uchraydi")
        return result
    seen.add(key)

    matches = universities.get(key, [])
    if len(matches) > 1:
        errors.append("Bazada bu nom va davlat bilan bir nechta universitet bor — adminkada tozalang")
        return result

    result.ref = {"country_iso": iso}
    if not matches:
        missing = [c for c in REQUIRED_FOR_NEW["universities"] if not row[c]]
        if missing:
            errors.append(f"Yangi universitet uchun majburiy: {', '.join(missing)}")
            return result
        new_keys.add(key)
        result.status = STATUS_NEW
        result.values = {"name": name, **values}
        return result

    existing = matches[0]
    result.target_id = existing.id
    result.values = values
    result.changes = _diff(existing, values)
    result.status = STATUS_UPDATE if result.changes else STATUS_UNCHANGED
    return result


def _yes_no(value: str, column: str, errors: list[str]) -> bool | None:
    text = value.strip().lower()
    if text in ("yes", "ha", "true", "1"):
        return True
    if text in ("no", "yo'q", "yoq", "false", "0"):
        return False
    errors.append(f"{column}: 'yes' yoki 'no' bo'lishi kerak")
    return None


def _positive_decimal(value: str, column: str, errors: list[str], upper: int) -> Decimal | None:
    try:
        number = Decimal(value.replace(",", "."))
        if number <= 0 or number > upper:
            raise InvalidOperation
        return number.normalize()
    except InvalidOperation:
        errors.append(f"{column}: 0 dan katta, {upper} dan oshmaydigan son bo'lishi kerak")
        return None


def _currency(value: str, column: str, errors: list[str]) -> str | None:
    code = value.strip().upper()
    if not _CURRENCY_RE.match(code):
        errors.append(f"{column}: uch harfli valyuta kodi bo'lishi kerak (GBP, USD, EUR)")
        return None
    return code


def _split_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(LIST_SEPARATOR) if part.strip()]


def _parse_program_details(
    row: dict[str, str], values: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    """Tafsilot ustunlarini o'qiydi. Dastur maydonlari `values`ga yoziladi,
    bog'liq jadvallar (talab, xarajat, muddat) qiymatlari qaytariladi.

    Bo'sh katak — hech narsa qo'shilmaydi (mavjud qiymat o'zgarmaydi).
    """
    related: dict[str, dict[str, Any]] = {"requirement": {}, "cost": {}, "deadline": {}}

    if row["ielts_min"]:
        ielts = _positive_decimal(row["ielts_min"], "ielts_min", errors, 9)
        if ielts is not None:
            if (ielts * 2) % 1:
                errors.append("ielts_min: 0.5 qadam bilan bo'lishi kerak (6, 6.5, 7...)")
            else:
                related["requirement"]["ielts_min"] = ielts
    if row["toefl_min"]:
        if row["toefl_min"].isdigit() and 0 < int(row["toefl_min"]) <= 120:
            related["requirement"]["toefl_min"] = int(row["toefl_min"])
        else:
            errors.append("toefl_min: 1 dan 120 gacha butun son bo'lishi kerak")

    if row["tuition_amount"]:
        amount = _positive_decimal(row["tuition_amount"], "tuition_amount", errors, 10_000_000)
        if amount is not None:
            related["cost"]["tuition_amount"] = amount
    if row["tuition_currency"]:
        code = _currency(row["tuition_currency"], "tuition_currency", errors)
        if code:
            related["cost"]["currency"] = code

    if row["deadline_close"]:
        try:
            day = date.fromisoformat(row["deadline_close"])
            related["deadline"]["date_utc"] = datetime(day.year, day.month, day.day, tzinfo=UTC)
        except ValueError:
            errors.append("deadline_close: sana YYYY-MM-DD ko'rinishida bo'lishi kerak")

    if row["has_application_fee"]:
        flag = _yes_no(row["has_application_fee"], "has_application_fee", errors)
        if flag is not None:
            values["has_application_fee"] = flag
    if row["application_fee_amount"]:
        fee = _positive_decimal(
            row["application_fee_amount"], "application_fee_amount", errors, 100_000
        )
        if fee is not None:
            values["application_fee_amount"] = fee
    if row["application_fee_currency"]:
        code = _currency(row["application_fee_currency"], "application_fee_currency", errors)
        if code:
            values["application_fee_currency"] = code

    if row["has_scholarship"]:
        flag = _yes_no(row["has_scholarship"], "has_scholarship", errors)
        if flag is not None:
            values["has_scholarship"] = flag
    if row["scholarship_url"]:
        _check_url(row["scholarship_url"], "scholarship_url", errors)
        values["scholarship_url"] = row["scholarship_url"]

    if row["required_documents"]:
        documents = _split_list(row["required_documents"])
        unknown = [d for d in documents if d not in REQUIRED_DOCUMENTS]
        if unknown:
            errors.append(
                f"required_documents: noma'lum kalit(lar) {', '.join(unknown)} "
                f"(ruxsat: {', '.join(REQUIRED_DOCUMENTS)})"
            )
        else:
            values["required_documents"] = [d for d in REQUIRED_DOCUMENTS if d in documents]
    if row["requirements_text"]:
        values["requirements_text"] = "\n".join(_split_list(row["requirements_text"]))
    return related


def _close_deadline(program: Program) -> Deadline | None:
    return next(
        (d for d in program.deadlines if d.type == DeadlineType.APPLICATION_CLOSE), None
    )


def _related_diff(
    program: Program, related: dict[str, dict[str, Any]]
) -> dict[str, tuple[Any, Any]]:
    """Bog'liq jadvallar bo'yicha farq (oldindan ko'rishda ko'rsatish uchun)."""
    changes: dict[str, tuple[Any, Any]] = {}
    requirement, cost = program.requirement, program.cost
    for name, new in related["requirement"].items():
        old = getattr(requirement, name) if requirement else None
        if (_decimal(old) if old is not None else None) != _decimal(new):
            changes[name] = (old, new)
    for name, new in related["cost"].items():
        old = getattr(cost, name) if cost else None
        same = _decimal(old) == new if isinstance(new, Decimal) else old == new
        if not same:
            changes["tuition_amount" if name == "tuition_amount" else "tuition_currency"] = (
                old, new
            )
    if "date_utc" in related["deadline"]:
        current = _close_deadline(program)
        old_day = current.date_utc.date() if current else None
        new_day = related["deadline"]["date_utc"].date()
        if old_day != new_day:
            changes["deadline_close"] = (old_day, new_day)
    return changes


async def _apply_related(
    session: AsyncSession,
    program: Program,
    related: dict[str, dict[str, Any]],
    today: date,
    existing: Program | None,
) -> None:
    """Talab, xarajat va ariza muddatini yozadi (bo'sh qiymatlar tegilmaydi).

    `existing` — bog'liq yozuvlari oldindan yuklangan mavjud dastur; yangi
    dasturda None (async'da relationship'ni lazy yuklab bo'lmaydi).
    """
    if related.get("requirement"):
        requirement = existing.requirement if existing else None
        if requirement is None:
            requirement = ProgramRequirement(program_id=program.id, gre_required=False)
            session.add(requirement)
        for name, value in related["requirement"].items():
            setattr(requirement, name, value)

    if related.get("cost"):
        cost = existing.cost if existing else None
        if cost is None:
            cost = ProgramCost(program_id=program.id, last_checked=today)
            session.add(cost)
        for name, value in related["cost"].items():
            setattr(cost, name, value)
        cost.last_checked = today

    if related.get("deadline"):
        deadline = _close_deadline(existing) if existing else None
        if deadline is None:
            session.add(Deadline(
                program_id=program.id,
                type=DeadlineType.APPLICATION_CLOSE,
                date_utc=related["deadline"]["date_utc"],
                intake_term=program.intake_term,
            ))
        else:
            deadline.date_utc = related["deadline"]["date_utc"]


def _plan_program(
    line: int,
    row: dict[str, str],
    fields: dict[str, Field],
    universities: dict[tuple[str, str], list[University]],
    new_university_keys: set[tuple[str, str]],
    programs: dict[tuple[int, str, DegreeLevel], Program],
    seen: set[tuple[str, str, str, DegreeLevel]],
) -> RowPlan:
    iso = row["country_iso"].upper()
    uni_name = row["university_name"]
    name = row["name"]
    result = RowPlan(
        "programs", line, f"{uni_name or '—'} / {name or '—'} ({row['degree_level'] or '—'})",
        STATUS_ERROR,
    )
    errors = result.errors

    if not name:
        errors.append("name: dastur nomi bo'sh")
    try:
        degree = DegreeLevel(row["degree_level"].lower())
    except ValueError:
        degree = None
        errors.append(
            f"degree_level: {row['degree_level']!r} noto'g'ri "
            f"(ruxsat: {', '.join(d.value for d in DegreeLevel)})"
        )

    uni_key = (_norm(uni_name), iso)
    matches = universities.get(uni_key, [])
    university = matches[0] if len(matches) == 1 else None
    if len(matches) > 1:
        errors.append("Bazada bu nom va davlat bilan bir nechta universitet bor")
    elif university is None and uni_key not in new_university_keys:
        errors.append(
            f"university_name: {uni_name!r} ({iso or '—'}) bazada ham, faylda ham yo'q"
        )

    values: dict[str, Any] = {}
    if row["field_code"]:
        found = fields.get(row["field_code"].lower())
        if found is None:
            errors.append(f"field_code: {row['field_code']!r} yo'nalishlar ro'yxatida yo'q")
        else:
            values["field_id"] = found.id
    if row["language_of_instruction"]:
        if row["language_of_instruction"] in INSTRUCTION_LANGUAGES:
            values["language_of_instruction"] = row["language_of_instruction"]
        else:
            errors.append(
                f"language_of_instruction: {row['language_of_instruction']!r} ro'yxatda yo'q "
                f"(ruxsat: {', '.join(INSTRUCTION_LANGUAGES)})"
            )
    if row["duration_years"]:
        try:
            duration = Decimal(row["duration_years"].replace(",", "."))
            if duration <= 0 or duration >= 100:
                raise InvalidOperation
            values["duration_years"] = duration.normalize()
        except InvalidOperation:
            errors.append("duration_years: musbat son bo'lishi kerak (masalan 2 yoki 1.5)")
    _check_url(row["source_url"], "source_url", errors)
    for column in (
        "abbreviation", "intake_term", "source_url", "notes", "notes_ru", "notes_en",
    ):
        if row[column]:
            values[column] = row[column]
    if len(row["abbreviation"]) > 30:
        errors.append("abbreviation: 30 belgidan oshmasin")
    related = _parse_program_details(row, values, errors)
    if errors:
        return result

    file_key = (iso, _norm(uni_name), _norm(name), degree)
    if file_key in seen:
        errors.append("Faylda bu dastur ikki marta uchraydi")
        return result
    seen.add(file_key)

    result.ref = {"country_iso": iso, "university_name": uni_name}
    existing = (
        programs.get((university.id, _norm(name), degree)) if university is not None else None
    )
    if existing is None:
        missing = [c for c in REQUIRED_FOR_NEW["programs"] if not row[c]]
        if missing:
            errors.append(f"Yangi dastur uchun majburiy: {', '.join(missing)}")
            return result
        if related["cost"] and "tuition_amount" not in related["cost"]:
            errors.append("tuition_currency berilgan, lekin tuition_amount yo'q")
            return result
        if "tuition_amount" in related["cost"] and "currency" not in related["cost"]:
            errors.append("tuition_amount uchun tuition_currency ham kerak (masalan GBP)")
            return result
        result.status = STATUS_NEW
        result.values = {"name": name, "degree_level": degree, **values}
        result.related = related
        return result

    if related["cost"] and existing.cost is None:
        missing_cost = [
            column for column, key in (("tuition_amount", "tuition_amount"),
                                       ("tuition_currency", "currency"))
            if key not in related["cost"]
        ]
        if missing_cost:
            errors.append(
                f"Dasturda hali xarajat yo'q — {', '.join(missing_cost)} ham kerak"
            )
            return result

    result.target_id = existing.id
    result.values = values
    result.related = related
    result.changes = _diff(existing, values)
    result.changes.update(_related_diff(existing, related))
    if "field_id" in result.changes:
        # Oldindan ko'rishda ID emas, yo'nalish kodi ko'rinsin.
        codes = {f.id: f.code for f in fields.values()}
        old_id, new_id = result.changes.pop("field_id")
        result.changes["field_code"] = (codes.get(old_id), codes.get(new_id))
    result.status = STATUS_UPDATE if result.changes else STATUS_UNCHANGED
    return result


# ------------------------------ saqlash ------------------------------


async def apply_plan(session: AsyncSession, plan: ImportPlan, admin: str) -> dict[str, int]:
    """Rejani saqlaydi. Tranzaksiyani CHAQIRUVCHI boshqaradi (commit/rollback).

    Dasturlarda verified_by = admin login'i, verified_at = hozirgi vaqt
    (faqat yangi yoki o'zgargan dasturlarga).
    """
    if plan.has_errors:
        raise ValueError("Rejada xato bor — saqlanmaydi")

    now = datetime.now(UTC)
    saved = {STATUS_NEW: 0, STATUS_UPDATE: 0}

    by_kind: dict[str, list[RowPlan]] = {kind: [] for kind in KINDS}
    for row in plan.rows:
        if row.status in (STATUS_NEW, STATUS_UPDATE):
            by_kind[row.kind].append(row)

    for row in by_kind["countries"]:
        if row.status == STATUS_NEW:
            session.add(Country(**row.values))
        else:
            country = await session.get(Country, row.target_id)
            for name, value in row.values.items():
                setattr(country, name, value)
        saved[row.status] += 1
    await session.flush()

    country_ids = {
        c.iso_code.upper(): c.id for c in (await session.execute(select(Country))).scalars()
    }
    for row in by_kind["universities"]:
        if row.status == STATUS_NEW:
            session.add(University(country_id=country_ids[row.ref["country_iso"]], **row.values))
        else:
            university = await session.get(University, row.target_id)
            for name, value in row.values.items():
                setattr(university, name, value)
        saved[row.status] += 1
    await session.flush()

    if by_kind["programs"]:
        university_ids: dict[tuple[str, str], int] = {}
        for uni in (
            await session.execute(select(University).options(selectinload(University.country)))
        ).scalars():
            university_ids[(_norm(uni.name), uni.country.iso_code.upper())] = uni.id
        for row in by_kind["programs"]:
            if row.status == STATUS_NEW:
                uni_id = university_ids[(_norm(row.ref["university_name"]), row.ref["country_iso"])]
                program = Program(university_id=uni_id, **row.values)
                session.add(program)
                program.verified_at = now
                program.verified_by = admin
                await session.flush()
                existing = None
            else:
                program = (
                    await session.execute(
                        select(Program)
                        .options(
                            selectinload(Program.requirement),
                            selectinload(Program.cost),
                            selectinload(Program.deadlines),
                        )
                        .where(Program.id == row.target_id)
                    )
                ).scalar_one()
                for name, value in row.values.items():
                    setattr(program, name, value)
                program.verified_at = now
                program.verified_by = admin
                existing = program
            await _apply_related(session, program, row.related, now.date(), existing)
            saved[row.status] += 1
    await session.flush()

    if by_kind["scholarships"]:
        country_by_iso = {
            c.iso_code.upper(): c for c in (await session.execute(select(Country))).scalars()
        }
        for row in by_kind["scholarships"]:
            if row.status == STATUS_NEW:
                scholarship = Scholarship(**row.values)
                session.add(scholarship)
            else:
                scholarship = (
                    await session.execute(
                        select(Scholarship)
                        .options(
                            selectinload(Scholarship.countries),
                            selectinload(Scholarship.deadlines),
                        )
                        .where(Scholarship.id == row.target_id)
                    )
                ).scalar_one()
                for name, value in row.values.items():
                    setattr(scholarship, name, value)
            scholarship.verified_at = now
            scholarship.verified_by = admin

            isos = row.related.get("country_isos")
            if isos:
                scholarship.countries = [
                    country_by_iso[iso] for iso in dict.fromkeys(isos) if iso in country_by_iso
                ]
            await session.flush()

            deadline = row.related.get("deadline")
            if deadline:
                close = next(
                    (
                        d
                        for d in (scholarship.deadlines if row.status == STATUS_UPDATE else [])
                        if d.type == DeadlineType.APPLICATION_CLOSE
                    ),
                    None,
                )
                if close is None:
                    session.add(
                        ScholarshipDeadline(
                            scholarship_id=scholarship.id,
                            type=DeadlineType.APPLICATION_CLOSE,
                            date_utc=deadline["date_utc"],
                            intake_term=deadline["intake_term"],
                        )
                    )
                else:
                    close.date_utc = deadline["date_utc"]
                    close.intake_term = deadline["intake_term"]
            saved[row.status] += 1
    await session.flush()
    return saved


# ------------------------------ eksport ------------------------------


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal | float):
        text = f"{Decimal(str(value)).normalize():f}"
        return text
    return str(value)


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "yes" if value else "no"


def template_csv(kind: str) -> str:
    """Shablon: sarlavha + bitta namuna qator (Excel uchun BOM bilan)."""
    return _write(kind, [SAMPLE_ROWS[kind]])


async def export_csv(session: AsyncSession, kind: str) -> str:
    """Katalogni import bilan AYNAN bir xil formatda yozadi (zaxira va tiklash uchun)."""
    rows: list[dict[str, str]] = []
    if kind == "countries":
        for c in (await session.execute(select(Country).order_by(Country.iso_code))).scalars():
            rows.append({
                "iso_code": c.iso_code, "name_uz": c.name_uz,
                "name_ru": c.name_ru, "name_en": c.name_en,
            })
    elif kind == "universities":
        stmt = (
            select(University)
            .options(selectinload(University.country))
            .order_by(University.name)
        )
        for u in (await session.execute(stmt)).scalars():
            rows.append({
                "country_iso": u.country.iso_code, "name": u.name, "city": u.city,
                "website": u.website or "", "timezone": u.timezone,
                "logo_url": u.logo_url or "", "ranking": _fmt(u.ranking),
            })
    elif kind == "programs":
        stmt = (
            select(Program)
            .options(
                selectinload(Program.university).selectinload(University.country),
                selectinload(Program.field),
                selectinload(Program.requirement),
                selectinload(Program.cost),
                selectinload(Program.deadlines),
            )
            .order_by(Program.university_id, Program.name, Program.degree_level)
        )
        for p in (await session.execute(stmt)).scalars():
            req, cost, close = p.requirement, p.cost, _close_deadline(p)
            rows.append({
                "country_iso": p.university.country.iso_code,
                "university_name": p.university.name,
                "name": p.name,
                "abbreviation": p.abbreviation or "",
                "degree_level": p.degree_level.value,
                "field_code": p.field.code if p.field else "",
                "language_of_instruction": p.language_of_instruction,
                "duration_years": _fmt(p.duration_years),
                "intake_term": p.intake_term,
                "source_url": p.source_url,
                "notes": p.notes or "",
                "notes_ru": p.notes_ru or "",
                "notes_en": p.notes_en or "",
                "ielts_min": _fmt(req.ielts_min) if req else "",
                "toefl_min": _fmt(req.toefl_min) if req else "",
                "tuition_amount": _fmt(cost.tuition_amount) if cost else "",
                "tuition_currency": cost.currency if cost else "",
                "deadline_close": close.date_utc.date().isoformat() if close else "",
                "has_application_fee": _fmt_bool(p.has_application_fee),
                "application_fee_amount": _fmt(p.application_fee_amount),
                "application_fee_currency": p.application_fee_currency or "",
                "has_scholarship": _fmt_bool(p.has_scholarship),
                "scholarship_url": p.scholarship_url or "",
                "required_documents": LIST_SEPARATOR.join(p.required_documents or []),
                "requirements_text": LIST_SEPARATOR.join(
                    (p.requirements_text or "").splitlines()
                ),
            })
    elif kind == "scholarships":
        stmt = (
            select(Scholarship)
            .options(
                selectinload(Scholarship.countries), selectinload(Scholarship.deadlines)
            )
            .order_by(Scholarship.name)
        )
        for item in (await session.execute(stmt)).scalars():
            close = next(
                (d for d in item.deadlines if d.type == DeadlineType.APPLICATION_CLOSE), None
            )
            rows.append({
                "name": item.name,
                "country_isos": LIST_SEPARATOR.join(
                    sorted(c.iso_code for c in item.countries)
                ),
                "description": item.description or "",
                "description_ru": item.description_ru or "",
                "description_en": item.description_en or "",
                "logo_url": item.logo_url or "",
                "coverage_type": item.coverage_type.value,
                "coverage_percent": _fmt(item.coverage_percent),
                "stipend_amount": _fmt(item.stipend_amount),
                "stipend_max": _fmt(item.stipend_max),
                "stipend_period": item.stipend_period or "",
                "currency": item.currency,
                "ielts_min": _fmt(item.ielts_min),
                "toefl_min": _fmt(item.toefl_min),
                "work_experience_years": _fmt(item.work_experience_years),
                "degree_levels": LIST_SEPARATOR.join(item.degree_levels or []),
                "study_language": item.study_language or "",
                "duration_min_years": _fmt(item.duration_min_years),
                "duration_max_years": _fmt(item.duration_max_years),
                "selection_stages": _fmt(item.selection_stages),
                "extras_flight": _fmt_bool(item.extras_flight),
                "extras_insurance": _fmt_bool(item.extras_insurance),
                "extras_dormitory": _fmt_bool(item.extras_dormitory),
                "extras_language_course": _fmt_bool(item.extras_language_course),
                "age_limit": _fmt(item.age_limit),
                "citizenship_eligible": _fmt_bool(item.citizenship_eligible),
                "university_choice": item.university_choice.value,
                "application_linked_to_program": _fmt_bool(item.application_linked_to_program),
                "universities_text": LIST_SEPARATOR.join(
                    (item.universities_text or "").splitlines()
                ),
                "selected_by": item.selected_by or "",
                "requirements_text": LIST_SEPARATOR.join(
                    (item.requirements_text or "").splitlines()
                ),
                "source_url": item.source_url or "",
                "deadline_close": close.date_utc.date().isoformat() if close else "",
                "intake_term": close.intake_term if close else "",
            })
    else:
        raise ValueError(f"Noma'lum tur: {kind}")
    return _write(kind, rows)


def _write(kind: str, rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    buffer.write("﻿")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS[kind], lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


# ------------------------- Redis uchun seriyalash -------------------------


def dump_files(files: dict[str, list[tuple[int, dict[str, str]]]]) -> dict[str, Any]:
    return {kind: [[line, row] for line, row in rows] for kind, rows in files.items()}


def load_files(data: dict[str, Any]) -> dict[str, list[tuple[int, dict[str, str]]]]:
    return {kind: [(line, row) for line, row in rows] for kind, rows in data.items()}
