"""Bitta sahifadan to'liq yozuv kiritish uchun "sehrgar" sahifalar.

Muammo: SQLAdmin har bir model uchun alohida CRUD beradi, shuning uchun bitta
universitetni dasturlari, talablari, xarajatlari va muddatlari bilan kiritish
uchun 5-6 ta bo'limga kirib, har birini qo'lda bog'lash kerak bo'lardi.

Bu yerda ikkita sahifa bor:
  * UniversityWizard  — davlat tanlanadi, universitet va uning dasturlari
    (talab + xarajat + ariza muddati bilan birga) bitta formada kiritiladi.
  * ScholarshipWizard — davlat stipendiyasi barcha tafsilotlari va muddatlari
    bilan bitta formada kiritiladi.

Mavjud CRUD bo'limlari saqlanadi — ular tahrirlash va nozik tuzatishlar uchun.
"""

from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from starlette.datastructures import FormData
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.db.models import (
    INSTRUCTION_LANGUAGES,
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
from app.db.session import async_session_factory

# Tahrirlashda forma universitetning TO'LIQ holati: bu chegaradan oshgan
# dasturlar formaga sig'masa, saqlashda o'chib ketadi — shuning uchun katta.
MAX_PROGRAMS = 60
MAX_DEADLINES = 6


# --------------------------- forma yordamchilari ---------------------------


def _text(form: FormData, key: str) -> str | None:
    value = (form.get(key) or "").strip()
    return value or None


def _number(form: FormData, key: str) -> float | None:
    value = _text(form, key)
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _integer(form: FormData, key: str) -> int | None:
    value = _number(form, key)
    return int(value) if value is not None else None


def _date(form: FormData, key: str) -> date | None:
    value = _text(form, key)
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _datetime_utc(form: FormData, key: str) -> datetime | None:
    """`<input type="date">` qiymatini UTC yarim tuniga aylantiradi."""
    parsed = _date(form, key)
    if parsed is None:
        return None
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)


def _checked(form: FormData, key: str) -> bool:
    return form.get(key) is not None


def _as_str(value: Any) -> str:
    """Decimal/int/None ni forma maydoniga tushadigan matnga aylantiradi.

    Decimal("4.00") -> "4", Decimal("6.50") -> "6.5" — ortiqcha nollar
    <input type="number"> da chalkash ko'rinadi.
    """
    if value is None:
        return ""
    text = f"{value}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _multiline(form: FormData, key: str) -> str | None:
    """Textarea: bo'sh qatorlar va chetdagi bo'shliqlar olib tashlanadi."""
    lines = [line.strip() for line in (form.get(key) or "").splitlines()]
    text = "\n".join(line for line in lines if line)
    return text or None


def _tristate(form: FormData, key: str) -> bool | None:
    """Tanlov "yes" / "no" / "" -> True / False / None."""
    value = _text(form, key)
    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def _tristate_out(value: bool | None) -> str:
    if value is None:
        return ""
    return "yes" if value else "no"


def _enum(form: FormData, key: str, enum_cls: Any) -> Any | None:
    value = _text(form, key)
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


# --------------------------- Universitet sehrgari ---------------------------


class UniversityWizard(BaseView):
    name = "Universitet qo'shish"
    identity = "university-wizard"
    icon = "fa-solid fa-wand-magic-sparkles"

    @expose("/university-wizard", methods=["GET", "POST"])
    async def wizard(self, request: Request):
        # `?university_id=` bo'lsa forma mavjud universitet bilan to'ldiriladi —
        # tahrirlash va yangi dastur qo'shish shu yerdan bajariladi.
        university_id = request.query_params.get("university_id")
        university_id = int(university_id) if (university_id or "").isdigit() else None
        # "Dasturlar" bo'limidan kelinganda (`?program_id=`) o'sha dastur bloki
        # ajratib ko'rsatiladi va unga aylantiriladi.
        focus_program_id = request.query_params.get("program_id")
        focus_program_id = int(focus_program_id) if (focus_program_id or "").isdigit() else None

        errors: list[str] = []
        university_errors: dict[str, str] = {}
        prefill: dict[str, Any] | None = None

        async with async_session_factory() as session:
            if request.method == "POST":
                form = await request.form()
                university_errors, program_errors = await self._validate(session, form)
                if not university_errors and not program_errors:
                    try:
                        created = await self._save(session, form)
                        await session.commit()
                    except Exception as exc:  # noqa: BLE001 — xabarni foydalanuvchiga ko'rsatamiz
                        await session.rollback()
                        errors = [f"Saqlashda xatolik: {exc}"]
                    else:
                        Flash.success(request, self._success_message(created))
                        # Saqlagandan keyin ham tahrirlash rejimida qolamiz, shunda
                        # admin darhol yana dastur qo'sha oladi.
                        return RedirectResponse(
                            f"{request.url.path}?university_id={created['id']}", status_code=303
                        )

                # Hech narsa saqlanmadi — forma admin kiritgan qiymatlar bilan
                # qayta ochiladi (bazadagi eski holat bilan emas).
                prefill = self._prefill_from_form(form, program_errors)
                errors = errors or list(university_errors.values()) + [
                    f"Dastur #{position} ({program['name']}): {message}"
                    for position, program in enumerate(prefill["programs"], start=1)
                    for message in program["_errors"].values()
                ]

            countries = (
                (await session.execute(select(Country).order_by(Country.name_uz))).scalars().all()
            )
            fields = (
                (await session.execute(select(Field).order_by(Field.sort_order, Field.name_uz)))
                .scalars()
                .all()
            )
            if prefill is None and university_id:
                prefill = await self._load(session, university_id)

        editing = bool(prefill and prefill.get("id"))
        return await self.templates.TemplateResponse(
            request,
            "wizard_university.html",
            {
                "title": (
                    f"{prefill['university_name']} — tahrirlash"
                    if editing
                    else "Universitet qo'shish"
                ),
                "subtitle": (
                    "Mavjud dasturlarni o'zgartiring yoki yangisini qo'shing"
                    if editing
                    else "Davlat, universitet va uning dasturlari — bitta formada"
                ),
                "countries": countries,
                "fields": fields,
                "degree_levels": list(DegreeLevel),
                "max_programs": MAX_PROGRAMS,
                "prefill": prefill,
                "focus_program_id": focus_program_id,
                "editing": editing,
                "languages": INSTRUCTION_LANGUAGES,
                "errors": errors,
                "university_errors": university_errors,
                # "Yangi universitet qo'shish" havolasi uchun — sehrgarning
                # o'z manzili, query'siz.
                "wizard_path": request.url.path,
            },
        )

    async def _validate(
        self, session: Any, form: FormData
    ) -> tuple[dict[str, str], dict[int, dict[str, str]]]:
        """Formani saqlashdan OLDIN tekshiradi.

        Ilgari bo'sh maydon jimgina to'ldirilardi (yo'nalishga dastur nomi,
        tilga "Ingliz tili", shaharga "—") — natijada katalog buzilardi.
        Endi bo'sh majburiy maydon xato beradi va hech narsa saqlanmaydi.

        Qaytaradi: (universitet xatolari {maydon: xabar},
                    dastur xatolari {forma indeksi: {kalit: xabar}}).
        """
        university_errors: dict[str, str] = {}

        country_id = _integer(form, "country_id")
        if country_id is None or await session.get(Country, country_id) is None:
            university_errors["country_id"] = "Davlat tanlanmagan"
        if _text(form, "university_name") is None:
            university_errors["university_name"] = "Universitet nomi kiritilmagan"
        if _text(form, "city") is None:
            university_errors["city"] = "Shahar kiritilmagan"

        timezone = _text(form, "timezone")
        if timezone is None:
            university_errors["timezone"] = "Vaqt zonasi kiritilmagan"
        else:
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, ValueError):
                university_errors["timezone"] = (
                    f"Vaqt zonasi noto'g'ri: {timezone!r} (masalan Europe/Berlin)"
                )

        ranking = _text(form, "ranking")
        if ranking is not None and (not ranking.isdigit() or int(ranking) < 1):
            university_errors["ranking"] = "Reyting musbat butun son bo'lishi kerak"

        valid_field_ids = set((await session.execute(select(Field.id))).scalars().all())
        program_errors: dict[int, dict[str, str]] = {}
        programs = 0
        for index in range(MAX_PROGRAMS):
            if _text(form, f"p{index}_name") is None:
                continue
            programs += 1
            problems: dict[str, str] = {}
            if _integer(form, f"p{index}_field") not in valid_field_ids:
                problems["field"] = "yo'nalish tanlanmagan"
            if _text(form, f"p{index}_language") not in INSTRUCTION_LANGUAGES:
                problems["language"] = "o'qitish tili tanlanmagan"
            if _enum(form, f"p{index}_degree", DegreeLevel) is None:
                problems["degree"] = "daraja tanlanmagan"
            duration = _number(form, f"p{index}_duration")
            if duration is None or duration <= 0:
                problems["duration"] = "davomiylik kiritilmagan"
            if _text(form, f"p{index}_intake") is None:
                problems["intake"] = "qabul davri kiritilmagan"
            if _text(form, f"p{index}_source_url") is None:
                problems["source_url"] = "manba havolasi kiritilmagan"
            if problems:
                program_errors[index] = problems

        if programs == 0:
            university_errors["programs"] = "Kamida bitta dastur kiritilishi kerak"
        return university_errors, program_errors

    def _prefill_from_form(
        self, form: FormData, program_errors: dict[int, dict[str, str]]
    ) -> dict[str, Any]:
        """Yuborilgan formani `_load` bilan bir xil ko'rinishga keltiradi.

        Xato bo'lganda forma shu bilan qayta chiziladi — admin kiritgan hech
        narsa yo'qolmaydi. Bloklar ketma-ket qayta raqamlanadi, xatolar esa
        har bir blokka `_errors` sifatida biriktiriladi.
        """
        keys = (
            "name", "abbr", "degree", "field", "language", "duration", "intake", "source_url",
            "ielts", "toefl", "requirements", "tuition", "currency", "fee", "fee_amount",
            "fee_currency", "scholarship", "scholarship_url", "notes", "notes_ru", "notes_en",
            "deadline_close", "legacy_field", "legacy_language",
        )
        programs = []
        for index in range(MAX_PROGRAMS):
            if _text(form, f"p{index}_name") is None:
                continue
            program: dict[str, Any] = {key: form.get(f"p{index}_{key}") or "" for key in keys}
            program["gre_required"] = _checked(form, f"p{index}_gre_required")
            program["_errors"] = program_errors.get(index, {})
            programs.append(program)

        return {
            "id": _integer(form, "university_id"),
            "country_id": _integer(form, "country_id"),
            "university_name": form.get("university_name") or "",
            "city": form.get("city") or "",
            "website": form.get("website") or "",
            "logo_url": form.get("logo_url") or "",
            "timezone": form.get("timezone") or "",
            "ranking": form.get("ranking") or "",
            "verified_by": form.get("verified_by") or "",
            "programs": programs,
        }

    @staticmethod
    def _success_message(created: dict[str, Any]) -> str:
        message = (
            f"'{created['university']}' saqlandi — {created['programs']} ta dastur "
            f"({created['new_programs']} tasi yangi), {created['requirements']} ta talab, "
            f"{created['costs']} ta xarajat, {created['deadlines']} ta muddat."
        )
        if created.get("removed_programs"):
            message += f" {created['removed_programs']} ta dastur o'chirildi."
        return message

    async def _load(self, session: Any, university_id: int) -> dict[str, Any] | None:
        """Universitetni dasturlari bilan formaga tushadigan ko'rinishda o'qiydi."""
        university = (
            await session.execute(
                select(University)
                .options(
                    selectinload(University.programs).selectinload(Program.requirement),
                    selectinload(University.programs).selectinload(Program.cost),
                    selectinload(University.programs).selectinload(Program.deadlines),
                )
                .where(University.id == university_id)
            )
        ).scalar_one_or_none()
        if university is None:
            return None

        programs = []
        for program in sorted(university.programs, key=lambda p: (p.degree_level.value, p.name)):
            requirement = program.requirement
            cost = program.cost
            close = next(
                (
                    d
                    for d in program.deadlines
                    if d.type == DeadlineType.APPLICATION_CLOSE
                ),
                None,
            )
            programs.append(
                {
                    # Kalitlar forma maydoni suffikslariga (p<i>_<kalit>) mos
                    # bo'lishi shart — shablondagi JS shu bo'yicha to'ldiradi.
                    "name": program.name,
                    "abbr": program.abbreviation or "",
                    "degree": program.degree_level.value,
                    "field": program.field_id or "",
                    # Kanonik bo'lmagan eski qiymat tanlovga tushmaydi — admin
                    # uni ro'yxatdan qayta tanlaydi, eski qiymat esa maslahat
                    # sifatida ko'rinadi (`legacy_*`).
                    "language": (
                        program.language_of_instruction
                        if program.language_of_instruction in INSTRUCTION_LANGUAGES
                        else ""
                    ),
                    "legacy_field": (
                        (program.field_of_study_legacy or "") if program.field_id is None else ""
                    ),
                    "legacy_language": (
                        ""
                        if program.language_of_instruction in INSTRUCTION_LANGUAGES
                        else program.language_of_instruction
                    ),
                    "duration": _as_str(program.duration_years),
                    "intake": program.intake_term,
                    "source_url": program.source_url or "",
                    "ielts": _as_str(requirement.ielts_min) if requirement else "",
                    "toefl": _as_str(requirement.toefl_min) if requirement else "",
                    "gre_required": bool(requirement and requirement.gre_required),
                    "requirements": program.requirements_text or "",
                    "tuition": _as_str(cost.tuition_amount) if cost else "",
                    "currency": cost.currency if cost else "USD",
                    "fee": _tristate_out(program.has_application_fee),
                    "fee_amount": _as_str(program.application_fee_amount),
                    "fee_currency": program.application_fee_currency or "",
                    "scholarship": _tristate_out(program.has_scholarship),
                    "scholarship_url": program.scholarship_url or "",
                    "notes": program.notes or "",
                    "notes_ru": program.notes_ru or "",
                    "notes_en": program.notes_en or "",
                    "deadline_close": close.date_utc.strftime("%Y-%m-%d") if close else "",
                    # "_" bilan boshlangan kalitlar forma maydoni emas —
                    # JS ularni to'ldirishda o'tkazib yuboradi.
                    "_pid": program.id,
                }
            )

        return {
            "id": university.id,
            "country_id": university.country_id,
            "university_name": university.name,
            "city": university.city,
            "website": university.website or "",
            "logo_url": university.logo_url or "",
            "timezone": university.timezone,
            "ranking": _as_str(university.ranking),
            "programs": programs,
        }

    async def _save(self, session: Any, form: FormData) -> dict[str, Any]:
        # Forma `_validate`dan o'tgan — majburiy maydonlar shu yerda bor.
        country_id = _integer(form, "country_id")
        university_name = _text(form, "university_name")

        verified_by = _text(form, "verified_by") or "admin"
        now = datetime.now(UTC)

        # Tahrirlash rejimida universitet ID bo'yicha topiladi, shunda nomini
        # o'zgartirish yangi yozuv yaratmaydi. Yangi kiritishda esa nom bo'yicha
        # qidiriladi — bir xil universitet ikki marta kiritilmasin.
        university_id = _integer(form, "university_id")
        if university_id is not None:
            existing = (
                await session.execute(select(University).where(University.id == university_id))
            ).scalar_one_or_none()
        else:
            existing = (
                await session.execute(select(University).where(University.name == university_name))
            ).scalar_one_or_none()

        university = existing or University(name=university_name)
        university.name = university_name
        university.country_id = country_id
        university.city = _text(form, "city")
        university.website = _text(form, "website")
        university.logo_url = _text(form, "logo_url")
        university.timezone = _text(form, "timezone")
        university.ranking = _integer(form, "ranking")
        if existing is None:
            session.add(university)
        await session.flush()

        counters = {
            "id": university.id,
            "university": university_name,
            "programs": 0,  # formada kiritilgan dasturlar (yangi + yangilangan)
            "new_programs": 0,
            "requirements": 0,
            "costs": 0,
            "deadlines": 0,
        }

        # Mavjud dasturlar (nom + daraja bo'yicha) — forma qayta yuborilsa
        # dublikat yaratmasdan yangilanadi.
        existing_programs = {
            (p.name, p.degree_level): p
            for p in (
                await session.execute(
                    select(Program).where(Program.university_id == university.id)
                )
            )
            .scalars()
            .all()
        }
        submitted_keys: set[tuple[str, DegreeLevel]] = set()

        for index in range(MAX_PROGRAMS):
            name = _text(form, f"p{index}_name")
            if name is None:
                continue

            degree = _enum(form, f"p{index}_degree", DegreeLevel)
            program = existing_programs.get((name, degree))
            submitted_keys.add((name, degree))
            counters["programs"] += 1
            if program is None:
                program = Program(university_id=university.id, name=name, degree_level=degree)
                session.add(program)
                counters["new_programs"] += 1
            else:
                # Eski talab/xarajat/muddat qayta yozilishi uchun tozalanadi.
                await session.execute(
                    delete(ProgramRequirement).where(ProgramRequirement.program_id == program.id)
                )
                await session.execute(
                    delete(ProgramCost).where(ProgramCost.program_id == program.id)
                )
                await session.execute(delete(Deadline).where(Deadline.program_id == program.id))

            program.abbreviation = _text(form, f"p{index}_abbr")
            program.field_id = _integer(form, f"p{index}_field")
            program.language_of_instruction = _text(form, f"p{index}_language")
            program.duration_years = _number(form, f"p{index}_duration")
            program.intake_term = _text(form, f"p{index}_intake")
            program.notes = _text(form, f"p{index}_notes")
            program.notes_ru = _text(form, f"p{index}_notes_ru")
            program.notes_en = _text(form, f"p{index}_notes_en")
            program.requirements_text = _multiline(form, f"p{index}_requirements")
            program.has_application_fee = _tristate(form, f"p{index}_fee")
            # Summa faqat "Bor" tanlanganda ma'noli — "Yo'q"da eski raqam
            # qolib ketib, Mini App'da chalkashlik bermasin.
            if program.has_application_fee:
                program.application_fee_amount = _number(form, f"p{index}_fee_amount")
                program.application_fee_currency = (
                    _text(form, f"p{index}_fee_currency")
                    or _text(form, f"p{index}_currency")
                    or "USD"
                ).upper()
            else:
                program.application_fee_amount = None
                program.application_fee_currency = None
            program.has_scholarship = _tristate(form, f"p{index}_scholarship")
            program.scholarship_url = (
                _text(form, f"p{index}_scholarship_url") if program.has_scholarship else None
            )
            program.source_url = _text(form, f"p{index}_source_url")
            program.verified_at = now
            program.verified_by = verified_by
            await session.flush()

            # GPA, yosh chegarasi, viza isboti va yashash xarajati endi
            # yuritilmaydi — talab/xarajat yozuvi qayta yaratilganda ular bo'sh
            # qoladi.
            ielts = _number(form, f"p{index}_ielts")
            toefl = _integer(form, f"p{index}_toefl")
            gre_required = _checked(form, f"p{index}_gre_required")

            if ielts is not None or toefl is not None or gre_required:
                session.add(
                    ProgramRequirement(
                        program_id=program.id,
                        ielts_min=ielts,
                        toefl_min=toefl,
                        gre_required=gre_required,
                    )
                )
                counters["requirements"] += 1

            tuition = _number(form, f"p{index}_tuition")
            if tuition is not None:
                session.add(
                    ProgramCost(
                        program_id=program.id,
                        tuition_amount=tuition,
                        currency=(_text(form, f"p{index}_currency") or "USD").upper(),
                        last_checked=_date(form, f"p{index}_last_checked") or now.date(),
                    )
                )
                counters["costs"] += 1

            close_date = _datetime_utc(form, f"p{index}_deadline_close")
            if close_date is not None:
                session.add(
                    Deadline(
                        program_id=program.id,
                        type=DeadlineType.APPLICATION_CLOSE,
                        date_utc=close_date,
                        intake_term=program.intake_term,
                    )
                )
                counters["deadlines"] += 1

        # Tahrirlash rejimida forma universitetning to'liq holati: admin
        # blokni o'chirsa, dastur bazadan ham o'chadi. Yangi kiritishda bu
        # qilinmaydi — aks holda bir xil nomli universitetni qayta kiritish
        # eski dasturlarni sezdirmay yo'q qilib yuborardi.
        if university_id is not None:
            removed = [
                program
                for key, program in existing_programs.items()
                if key not in submitted_keys
            ]
            for program in removed:
                await session.delete(program)
            counters["removed_programs"] = len(removed)

        counters["id"] = university.id
        return counters


# ------------------------------ Grant sehrgari ------------------------------


class ScholarshipWizard(BaseView):
    name = "Grant qo'shish"
    identity = "scholarship-wizard"
    icon = "fa-solid fa-wand-magic-sparkles"

    @expose("/scholarship-wizard", methods=["GET", "POST"])
    async def wizard(self, request: Request):
        async with async_session_factory() as session:
            if request.method == "POST":
                form = await request.form()
                try:
                    created = await self._save(session, form)
                    await session.commit()
                except Exception as exc:  # noqa: BLE001
                    await session.rollback()
                    Flash.error(request, f"Saqlashda xatolik: {exc}")
                else:
                    Flash.success(
                        request,
                        f"'{created['name']}' saqlandi — {created['countries']} ta davlat, "
                        f"{created['deadlines']} ta muddat.",
                    )
                    return RedirectResponse(request.url.path, status_code=303)

            countries = (
                (await session.execute(select(Country).order_by(Country.name_uz))).scalars().all()
            )

        return await self.templates.TemplateResponse(
            request,
            "wizard_scholarship.html",
            {
                "title": "Grant qo'shish",
                "subtitle": "Davlat stipendiyasi — barcha tafsilotlari bitta formada",
                "countries": countries,
                "coverage_types": list(CoverageType),
                "university_choices": list(UniversityChoiceType),
                "deadline_types": list(DeadlineType),
                "max_deadlines": MAX_DEADLINES,
            },
        )

    async def _save(self, session: Any, form: FormData) -> dict[str, Any]:
        name = _text(form, "name")
        if name is None:
            raise ValueError("Grant nomi kiritilmagan")

        source_url = _text(form, "source_url")
        if source_url is None:
            raise ValueError("Rasmiy manba havolasi kiritilmagan")

        now = datetime.now(UTC)
        # `countries` darhol yuklanadi: aks holda quyida unga qiymat berishda
        # SQLAlchemy lazy-load qilmoqchi bo'lib, async kontekstda
        # "greenlet_spawn has not been called" xatosini beradi.
        existing = (
            await session.execute(
                select(Scholarship)
                .options(selectinload(Scholarship.countries))
                .where(Scholarship.name == name)
            )
        ).scalar_one_or_none()

        scholarship = existing or Scholarship(name=name)
        scholarship.description = _text(form, "description")
        scholarship.coverage_type = _enum(form, "coverage_type", CoverageType) or CoverageType.FULL
        scholarship.coverage_percent = _integer(form, "coverage_percent")
        scholarship.stipend_amount = _number(form, "stipend_amount")
        scholarship.currency = _text(form, "currency") or "USD"
        scholarship.extras_flight = _checked(form, "extras_flight")
        scholarship.extras_insurance = _checked(form, "extras_insurance")
        scholarship.extras_dormitory = _checked(form, "extras_dormitory")
        scholarship.extras_language_course = _checked(form, "extras_language_course")
        scholarship.age_limit = _integer(form, "age_limit")
        scholarship.citizenship_eligible = _checked(form, "citizenship_eligible")
        scholarship.university_choice = (
            _enum(form, "university_choice", UniversityChoiceType)
            or UniversityChoiceType.USER_CHOOSES
        )
        scholarship.application_linked_to_program = _checked(form, "application_linked_to_program")
        scholarship.source_url = source_url
        scholarship.verified_at = now
        scholarship.verified_by = _text(form, "verified_by") or "admin"

        # Davlatlar flush'dan OLDIN biriktiriladi: flush'dan keyin obyekt
        # "persistent" bo'lib qoladi va yuklanmagan to'plamga qiymat berish
        # lazy-load'ni chaqiradi (async'da "greenlet_spawn" xatosi).
        country_ids = [int(v) for v in form.getlist("country_ids") if str(v).isdigit()]
        countries = (
            (await session.execute(select(Country).where(Country.id.in_(country_ids))))
            .scalars()
            .all()
        )
        scholarship.countries = list(countries)

        if existing is None:
            session.add(scholarship)
        await session.flush()

        # Forma yozuvning to'liq holatini ifodalaydi — eski muddatlar
        # o'chirilib, formadagilar bilan almashtiriladi (dublikat bo'lmasin).
        await session.execute(
            delete(ScholarshipDeadline).where(
                ScholarshipDeadline.scholarship_id == scholarship.id
            )
        )

        deadlines_added = 0
        for index in range(MAX_DEADLINES):
            when = _datetime_utc(form, f"d{index}_date")
            if when is None:
                continue
            session.add(
                ScholarshipDeadline(
                    scholarship_id=scholarship.id,
                    type=_enum(form, f"d{index}_type", DeadlineType)
                    or DeadlineType.APPLICATION_CLOSE,
                    date_utc=when,
                    intake_term=_text(form, f"d{index}_intake") or "—",
                )
            )
            deadlines_added += 1

        return {"name": name, "countries": len(countries), "deadlines": deadlines_added}
