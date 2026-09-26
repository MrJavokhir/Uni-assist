"""Data-migratsiyalardagi mapping funksiyalari.

Mapping migratsiya faylining o'zida yozilgan (ilova kodidan import qilinmaydi) —
aks holda ilova kodi keyinchalik o'zgarsa, eski migratsiyaning xatti-harakati
ham jimgina o'zgarib qolardi. Shuning uchun test faylni to'g'ridan-to'g'ri yuklaydi.
"""

import importlib.util
from pathlib import Path

VERSIONS = Path(__file__).resolve().parent.parent / "migrations" / "versions"


def _load(filename: str):
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), VERSIONS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fields_migration = _load("d9e3a7c41b28_fields_reference.py")


def test_known_legacy_fields_map_to_codes():
    assert fields_migration.map_legacy_field("Computer Science") == "cs_it"
    assert fields_migration.map_legacy_field("Engineering") == "engineering"
    assert fields_migration.map_legacy_field("Business / Economics") == "business_mgmt"
    assert fields_migration.map_legacy_field("Law") == "law"


def test_legacy_field_mapping_ignores_case_and_outer_spaces():
    assert fields_migration.map_legacy_field("  computer SCIENCE ") == "cs_it"
    assert fields_migration.map_legacy_field("LAW\t") == "law"


def test_unknown_legacy_field_maps_to_none():
    # Noma'lum qiymatda migratsiya yiqilmaydi — field_id NULL qoladi.
    assert fields_migration.map_legacy_field("Business Administration") is None
    assert fields_migration.map_legacy_field("") is None
    assert fields_migration.map_legacy_field(None) is None


def test_mapping_targets_exist_among_seeded_fields():
    codes = {code for code, *_ in fields_migration.FIELDS}
    assert len(codes) == 18
    assert set(fields_migration.LEGACY_FIELD_MAP.values()) <= codes


language_migration = _load("e4b8c2d95f17_canonical_instruction_language.py")


def test_legacy_uzbek_english_maps_to_canonical():
    assert language_migration.map_legacy_language("Ingliz tili") == "English"
    assert language_migration.map_legacy_language("  ingliz TILI ") == "English"


def test_canonical_and_unknown_languages_are_left_alone():
    # Kanonik qiymat almashtirilmaydi; noma'lumi faqat log'ga chiqadi.
    assert language_migration.map_legacy_language("English") is None
    assert language_migration.map_legacy_language("Nemis tili") is None
    assert language_migration.map_legacy_language(None) is None


def test_migration_canonical_list_is_subset_of_app_constant():
    """Migratsiyadagi ro'yxat ataylab muzlatilgan (o'sha paytdagi holat).

    Ilova ro'yxatiga keyin yangi til qo'shilishi mumkin — bu migratsiyani
    o'zgartirmaydi. Ammo migratsiya bilgan til ilovadan olib tashlansa,
    bu xato: eski qatorlar kanonik ro'yxatdan tushib qolardi.
    """
    from app.db.models import INSTRUCTION_LANGUAGES

    assert language_migration.CANONICAL_LANGUAGES <= set(INSTRUCTION_LANGUAGES)


def test_every_canonical_language_is_translated_in_mini_app():
    """Yangi til qo'shilsa, app.js'da uch tildagi tarjimasi ham bo'lishi shart."""
    import re

    from app.db.models import INSTRUCTION_LANGUAGES

    app_js = (VERSIONS.parent.parent / "app" / "webapp" / "static" / "app.js").read_text(
        encoding="utf-8"
    )
    block = app_js[app_js.index("const LANGUAGE_NAMES = {") :]
    block = block[: block.index("};")]
    entry = re.compile(r"^\s+(\w+): \{ uz: .+, ru: .+, en: .+ \},$", re.MULTILINE)
    translated = set(entry.findall(block))
    assert set(INSTRUCTION_LANGUAGES) <= translated


def test_migration_chain_has_single_head():
    """Zanjir bitta uchga ega bo'lishi kerak.

    Ikki migratsiya bir xil `down_revision` ga ulansa, zanjir ikkiga
    bo'linadi va `alembic upgrade head` "Multiple heads" bilan yiqiladi.
    Bu xato deploy paytida chiqadi: entrypoint `set -e` bilan ishlagani
    uchun servis umuman ko'tarilmaydi.
    """
    import re

    revisions: dict[str, str] = {}
    downs: list[str] = []
    for path in VERSIONS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        rev = re.search(r"^revision: str = ['\"]([^'\"]+)", text, re.MULTILINE)
        down = re.search(r"^down_revision[^=]*=\s*['\"]([^'\"]+)", text, re.MULTILINE)
        if rev:
            revisions[rev.group(1)] = path.name
        if down:
            downs.append(down.group(1))

    heads = [rev for rev in revisions if rev not in downs]
    assert len(heads) == 1, f"Bir nechta head: {sorted(revisions[h] for h in heads)}"

    duplicates = {d for d in downs if downs.count(d) > 1}
    assert not duplicates, f"Bir xil down_revision'ga ulangan migratsiyalar: {duplicates}"
