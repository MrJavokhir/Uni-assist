"""Mentor javobidagi kontakt va havola filtri."""

import pytest

from app.services.mentor_filter import Violation, find_violation

ALLOWED = [".de", ".edu", ".ac.uk", "daad.de", "uni-assist.de"]


@pytest.mark.parametrize(
    "text",
    [
        "Hujjatlarni uni-assist.de orqali yuborasiz.",
        "Batafsil: https://www.daad.de/de/stipendien/123456789",
        "tum.de saytida hammasi yozilgan",
        "Oxford: https://www.ox.ac.uk/admissions",
        "MIT: mit.edu/admissions",
        "admission@tum.de manziliga yozing",
        # Raqamlar telefon emas: narx, yillar, ballar.
        "Kontrakt 1 200 000 so'm, 2024-2025 o'quv yili, IELTS 6.5, GPA 3.5.",
        "Narxi 11.904 EUR atrofida",
        # Daraja nomlari havola emas.
        "M.Sc va B.Sc dasturlari, i.e. e.g. Ph.D.",
    ],
)
def test_clean_text_passes(text: str) -> None:
    assert find_violation(text, ALLOWED) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Menga +998 90 123 45 67 ga yozing", Violation.PHONE),
        ("90 123 45 67 ga qo'ng'iroq qiling", Violation.PHONE),
        ("Telegram: @javohir_mentor", Violation.USERNAME),
        ("Kanalim t.me/abroad_uz", Violation.TELEGRAM_LINK),
        ("https://t.me/+AbCdEf", Violation.TELEGRAM_LINK),
        ("tg://resolve?domain=x", Violation.TELEGRAM_LINK),
        ("Konsultatsiya: www.my-consulting.com", Violation.LINK),
        ("https://evil.com/de", Violation.LINK),
        ("bit.ly/abc ga kiring", Violation.LINK),
        ("Yozing: mentor@gmail.com", Violation.EMAIL),
    ],
)
def test_contacts_and_foreign_links_are_blocked(text: str, expected: Violation) -> None:
    assert find_violation(text, ALLOWED) == expected


def test_domain_zone_and_exact_domain() -> None:
    # ".de" — butun zona; "daad.de" — o'zi va subdomenlari, boshqasi emas.
    assert find_violation("www.uni-heidelberg.de", [".de"]) is None
    assert find_violation("www.daad.de", ["daad.de"]) is None
    assert find_violation("notdaad.com", ["daad.de"]) == Violation.LINK


def test_no_allowed_domains_blocks_every_link() -> None:
    assert find_violation("tum.de", []) == Violation.LINK
