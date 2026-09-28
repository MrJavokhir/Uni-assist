"""Sehrgardagi "Ariza uchun hujjatlar" katakchalari <-> Program.required_documents."""

from starlette.datastructures import FormData

from app.admin.wizards import _documents_in, _documents_out
from app.db.models import REQUIRED_DOCUMENTS


def test_saved_documents_are_prechecked():
    fields = _documents_out(["transcript", "cv"])

    assert fields["doc_transcript"] is True
    assert fields["doc_cv"] is True
    assert fields["doc_passport"] is False
    assert fields["docs_extra"] == ""


def test_checked_boxes_become_document_keys_in_canonical_order():
    form = FormData([("p0_doc_cv", "on"), ("p0_doc_transcript", "on")])

    assert _documents_in(form, 0) == ["transcript", "cv"]


def test_no_checked_boxes_clears_documents():
    assert _documents_in(FormData([]), 0) is None


def test_unknown_legacy_keys_survive_a_round_trip():
    """Ro'yxatda yo'q eski kalit sehrgar orqali saqlaganda jimgina o'chmaydi.

    Namuna kalit ataylab hech qachon haqiqiy bo'lmaydigan qilib olingan: ilgari
    bu yerda "portfolio" turgan edi, keyin u REQUIRED_DOCUMENTS ga qo'shilib,
    test o'z ma'nosini yo'qotgan.
    """
    legacy = "legacy_unknown_key"
    assert legacy not in REQUIRED_DOCUMENTS
    fields = _documents_out(["transcript", legacy])
    assert fields["docs_extra"] == legacy

    form = FormData([
        (f"p3_{key}", "on") for key, checked in fields.items() if key.startswith("doc_") and checked
    ] + [("p3_docs_extra", fields["docs_extra"])])

    assert _documents_in(form, 3) == ["transcript", legacy]


def test_every_document_key_is_translated_in_mini_app():
    """Yangi hujjat kaliti qo'shilsa, app.js'da uch tildagi tarjimasi ham bo'lishi shart."""
    from pathlib import Path

    app_js = (
        Path(__file__).resolve().parent.parent / "app" / "webapp" / "static" / "app.js"
    ).read_text(encoding="utf-8")
    for key in REQUIRED_DOCUMENTS:
        assert app_js.count(f'"document.{key}":') == 3, key
