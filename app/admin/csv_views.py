"""CSV import / eksport sahifasi (sqladmin BaseView, wizards.py uslubida).

Mantiq (o'qish, tekshirish, saqlash) app/admin/catalog_io.py'da — bu yerda
faqat HTTP: fayl qabul qilish, oldindan ko'rish, tasdiqlash, yuklab berish.

Oldindan ko'rish va tasdiqlash orasida fayl qayerda turadi:
  Redis'da, 30 daqiqa TTL bilan; kaliti tasodifiy token, token esa admin
  sessiyasida. Sabablari:
    * sessiya cookie'ga sig'maydi (~4 KB, fayl esa 5 MB gacha);
    * Redis prod'da allaqachon bor (obuna keshi) — yangi infratuzilma yo'q;
    * bir nechta worker yoki qayta ishga tushishda ham ishlaydi (xotiradagi
      lug'atdan farqli o'laroq);
    * TTL tashlab ketilgan importlarni o'zi tozalaydi.
  Tasdiqlashda qatorlar QAYTA tekshiriladi: oraliqda bazada biror narsa
  o'zgargan bo'lsa (natija oldindan ko'rilganidan farq qilsa), saqlash
  o'rniga yangi oldindan ko'rish ko'rsatiladi.
"""

import json
import secrets
from typing import Any

from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.admin.auth import current_admin
from app.admin.catalog_io import (
    COLUMNS,
    KEY_COLUMNS,
    KIND_LABELS,
    KINDS,
    MAX_BYTES,
    MAX_ROWS,
    REQUIRED_FOR_NEW,
    CsvFileError,
    ImportPlan,
    apply_plan,
    build_plan,
    dump_files,
    export_csv,
    load_files,
    parse_csv,
    template_csv,
)
from app.db.session import async_session_factory
from app.services.redis_client import redis_client

TOKEN_SESSION_KEY = "catalog_import_token"
REDIS_PREFIX = "catalog_import:"
PREVIEW_TTL_SECONDS = 30 * 60


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _fingerprint(plan: ImportPlan) -> Any:
    # JSON orqali o'tkaziladi — Redis'dan qaytgan qiymat bilan solishtirish uchun.
    return json.loads(json.dumps(plan.fingerprint()))


class CatalogImportView(BaseView):
    name = "CSV import / eksport"
    icon = "fa-solid fa-file-csv"

    # Yon menyu birinchi e'lon qilingan route'ga bog'lanadi.
    @expose("/catalog-io", methods=["GET"], identity="catalog-io")
    async def catalog_page(self, request: Request):
        return await self._render(request)

    @expose("/catalog-io/template/{kind}", methods=["GET"], identity="catalog-io-template")
    async def download_template(self, request: Request):
        kind = request.path_params["kind"]
        if kind not in KINDS:
            return Response("Noma'lum tur", status_code=404)
        return _csv_response(template_csv(kind), f"{kind}_shablon.csv")

    @expose("/catalog-io/eksport/{kind}", methods=["GET"], identity="catalog-io-export")
    async def download_export(self, request: Request):
        kind = request.path_params["kind"]
        if kind not in KINDS:
            return Response("Noma'lum tur", status_code=404)
        async with async_session_factory() as session:
            content = await export_csv(session, kind)
        return _csv_response(content, f"{kind}.csv")

    @expose("/catalog-io/preview", methods=["POST"], identity="catalog-io-preview")
    async def upload_preview(self, request: Request):
        form = await request.form()
        files: dict[str, list[tuple[int, dict[str, str]]]] = {}
        file_errors: dict[str, str] = {}
        for kind in KINDS:
            upload = form.get(kind)
            if upload is None or not getattr(upload, "filename", ""):
                continue
            # Chegaradan bitta bayt ko'p o'qiymiz — katta faylni butunlay
            # xotiraga olmasdan "juda katta" deb aniqlash uchun.
            data = await upload.read(MAX_BYTES + 1)
            if not data:
                continue
            try:
                files[kind] = parse_csv(data, kind)
            except CsvFileError as exc:
                file_errors[kind] = str(exc)

        if not files and not file_errors:
            Flash.error(request, "Hech qanday CSV fayl tanlanmadi.")
            return RedirectResponse(request.url_for("admin:view-catalog-io"), status_code=303)

        async with async_session_factory() as session:
            plan = await build_plan(session, files)
        plan.file_errors = file_errors

        token = None
        if not plan.has_errors:
            token = await self._store(request, files, plan)
        return await self._render(request, plan=plan, token=token)

    @expose("/catalog-io/confirm", methods=["POST"], identity="catalog-io-confirm")
    async def import_confirm(self, request: Request):
        form = await request.form()
        token = form.get("token")
        page_url = request.url_for("admin:view-catalog-io")
        if not token or token != request.session.get(TOKEN_SESSION_KEY):
            Flash.error(request, "Oldindan ko'rish topilmadi — faylni qaytadan yuklang.")
            return RedirectResponse(page_url, status_code=303)

        raw = await redis_client.get(REDIS_PREFIX + token)
        if raw is None:
            Flash.error(
                request, "Oldindan ko'rish muddati o'tdi (30 daqiqa) — faylni qaytadan yuklang."
            )
            return RedirectResponse(page_url, status_code=303)
        stored = json.loads(raw)
        files = load_files(stored["files"])

        async with async_session_factory() as session:
            plan = await build_plan(session, files)
            if plan.has_errors or _fingerprint(plan) != stored["fingerprint"]:
                # Oraliqda baza o'zgargan — admin yangi holatni ko'rib chiqsin.
                new_token = None if plan.has_errors else await self._store(request, files, plan)
                return await self._render(
                    request,
                    plan=plan,
                    token=new_token,
                    notice=(
                        "Oldindan ko'rishdan keyin bazada o'zgarish bo'ldi — natija yangilandi, "
                        "qaytadan ko'rib chiqing."
                    ),
                )
            try:
                saved = await apply_plan(session, plan, admin=current_admin(request))
                await session.commit()
            except Exception as exc:  # noqa: BLE001 — xabarni adminga ko'rsatamiz
                await session.rollback()
                Flash.error(request, f"Saqlashda xatolik, hech narsa saqlanmadi: {exc}")
                return RedirectResponse(page_url, status_code=303)

        await redis_client.delete(REDIS_PREFIX + token)
        request.session.pop(TOKEN_SESSION_KEY, None)
        Flash.success(
            request,
            f"Import saqlandi: {saved['new']} ta yangi, {saved['update']} ta yangilandi.",
        )
        return RedirectResponse(page_url, status_code=303)

    async def _store(
        self,
        request: Request,
        files: dict[str, list[tuple[int, dict[str, str]]]],
        plan: ImportPlan,
    ) -> str:
        token = secrets.token_urlsafe(16)
        payload = {"files": dump_files(files), "fingerprint": _fingerprint(plan)}
        await redis_client.set(
            REDIS_PREFIX + token, json.dumps(payload, ensure_ascii=False), ex=PREVIEW_TTL_SECONDS
        )
        request.session[TOKEN_SESSION_KEY] = token
        return token

    async def _render(
        self,
        request: Request,
        plan: ImportPlan | None = None,
        token: str | None = None,
        notice: str | None = None,
    ):
        return await self.templates.TemplateResponse(
            request,
            "csv_import.html",
            {
                "title": "CSV import / eksport",
                "subtitle": "Katalogni ommaviy kiritish va zaxiralash",
                "kinds": KINDS,
                "labels": KIND_LABELS,
                "columns": COLUMNS,
                "key_columns": KEY_COLUMNS,
                "required_for_new": REQUIRED_FOR_NEW,
                "max_rows": MAX_ROWS,
                "plan": plan,
                "counts": plan.counts() if plan else None,
                "token": token,
                "notice": notice,
            },
        )
