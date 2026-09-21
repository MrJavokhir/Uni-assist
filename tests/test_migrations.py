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
