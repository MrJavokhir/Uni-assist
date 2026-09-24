"""Mini App matnlari foydalanuvchi tilida chiqishini tekshiradi.

Qoida `description` dan olingan: asosiy ustun o'zbekcha, `_ru`/`_en` bo'sh
bo'lsa interfeys o'zbekchasiga qaytadi — bo'sh joy ko'rsatgandan ko'ra
tushunarli matn yaxshiroq.
"""

from app.db.models import CoverageType, Scholarship, UniversityChoiceType
from app.webapp.api import _localized


def _scholarship(**kwargs) -> Scholarship:
    return Scholarship(
        name="Test",
        coverage_type=CoverageType.FULL,
        university_choice=UniversityChoiceType.USER_CHOOSES,
        **kwargs,
    )


def test_translation_is_used_when_present() -> None:
    item = _scholarship(
        selected_by="Komissiya",
        selected_by_ru="Комиссия",
        selected_by_en="Committee",
    )
    assert _localized(item, "selected_by", "uz") == "Komissiya"
    assert _localized(item, "selected_by", "ru") == "Комиссия"
    assert _localized(item, "selected_by", "en") == "Committee"


def test_missing_translation_falls_back_to_uzbek() -> None:
    item = _scholarship(selected_by="Komissiya")
    assert _localized(item, "selected_by", "ru") == "Komissiya"
    assert _localized(item, "selected_by", "en") == "Komissiya"


def test_empty_translation_is_treated_as_missing() -> None:
    # Bo'sh satr ham "tarjima yo'q" degani — aks holda foydalanuvchi bo'sh
    # joy ko'rardi.
    item = _scholarship(selected_by="Komissiya", selected_by_ru="")
    assert _localized(item, "selected_by", "ru") == "Komissiya"


def test_all_three_text_fields_are_localized() -> None:
    item = _scholarship(
        universities_text="Oksford",
        universities_text_ru="Оксфорд",
        requirements_text="Bakalavr diplomi",
        requirements_text_en="Bachelor degree",
        selected_by="Komissiya",
    )
    assert _localized(item, "universities_text", "ru") == "Оксфорд"
    # Inglizchasi yo'q — o'zbekchasiga qaytadi.
    assert _localized(item, "universities_text", "en") == "Oksford"
    assert _localized(item, "requirements_text", "en") == "Bachelor degree"
    assert _localized(item, "requirements_text", "ru") == "Bakalavr diplomi"
    assert _localized(item, "selected_by", "en") == "Komissiya"


def test_none_stays_none() -> None:
    item = _scholarship()
    assert _localized(item, "universities_text", "ru") is None
    assert _localized(item, "universities_text", "uz") is None
