"""Admission Kit qo'llanmalari uchun PDF yuklash sahifasi.

Nega alohida sahifa, xizmat formasi ichida emas: sqladmin xizmat formasini
saqlashda fayl maydonini fayl OMBORI obyekti deb kutadi. Oddiy baytlar
ustuniga fayl maydonini qo'yib bo'lsa ham, keyin o'sha xizmatni faylni
qayta yuklamasdan tahrirlaganda (masalan, narxni o'zgartirganda) forma
xato beradi. Bu yerda forma o'zimizniki, shuning uchun bunday tuzoq yo'q.

Fayl qayerda saqlanadi va nega — `app/db/models/service.py`.
"""

import logging

from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.db.models import AdmissionService
from app.db.session import async_session_factory
from app.services import kit_service

logger = logging.getLogger(__name__)


def _size_label(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    return f"{max(size_bytes // 1024, 1)} KB"


class ServiceFileView(BaseView):
    name = "Qo'llanma fayllari"
    # Xizmatlar va so'rovlar bilan bitta guruhda tursin — ular birga
    # ishlatiladi: xizmat yaratiladi, keyin unga PDF biriktiriladi.
    category = "Admission Kit"
    icon = "fa-solid fa-file-pdf"

    @expose("/kit-files", methods=["GET"], identity="kit-files")
    async def page(self, request: Request):
        async with async_session_factory() as session:
            stmt = select(AdmissionService).order_by(
                AdmissionService.sort_order, AdmissionService.id
            )
            services = (await session.execute(stmt)).scalars().all()
            rows = [
                {
                    "id": service.id,
                    "title": service.title_uz,
                    "code": service.code,
                    "is_active": service.is_active,
                    "price": service.price_amount,
                    "currency": service.price_currency,
                    "file": (
                        {
                            "filename": service.file.filename,
                            "size": _size_label(service.file.size_bytes),
                            "uploaded": service.file.updated_at,
                            "cached": bool(service.file.telegram_file_id),
                        }
                        if service.file is not None
                        else None
                    ),
                }
                for service in services
            ]

        return await self.templates.TemplateResponse(
            request,
            "service_files.html",
            {
                "title": "Qo'llanma fayllari",
                "subtitle": "Admission Kit xizmatlariga PDF biriktirish",
                "rows": rows,
                "max_mb": kit_service.MAX_PDF_BYTES // (1024 * 1024),
            },
        )

    @expose("/kit-files/upload", methods=["POST"], identity="kit-files-upload")
    async def upload(self, request: Request):
        back = RedirectResponse(request.url_for("admin:view-kit-files"), status_code=303)
        form = await request.form()
        service_id = _int(form.get("service_id"))
        upload = form.get("file")

        if service_id is None or upload is None or not getattr(upload, "filename", ""):
            Flash.error(request, "Fayl tanlanmadi.")
            return back

        # Chegaradan bitta bayt ko'p o'qiymiz: "juda katta" faylni butunlay
        # xotiraga olmasdan aniqlash uchun.
        data = await upload.read(kit_service.MAX_PDF_BYTES + 1)

        async with async_session_factory() as session:
            service = await session.get(AdmissionService, service_id)
            if service is None:
                Flash.error(request, "Xizmat topilmadi.")
                return back
            try:
                row = await kit_service.save_file(session, service, upload.filename, data)
            except kit_service.FileRejected as exc:
                Flash.error(request, str(exc))
                return back
            await session.commit()
            Flash.success(
                request,
                f"«{service.title_uz}» uchun {row.filename} ({_size_label(row.size_bytes)}) yuklandi.",
            )
        return back

    @expose("/kit-files/delete", methods=["POST"], identity="kit-files-delete")
    async def delete(self, request: Request):
        back = RedirectResponse(request.url_for("admin:view-kit-files"), status_code=303)
        form = await request.form()
        service_id = _int(form.get("service_id"))
        if service_id is None:
            return back

        async with async_session_factory() as session:
            service = await session.get(AdmissionService, service_id)
            if service is None:
                Flash.error(request, "Xizmat topilmadi.")
                return back
            removed = await kit_service.delete_file(session, service)
            await session.commit()
        if removed:
            Flash.success(request, f"«{service.title_uz}» fayli o'chirildi.")
        return back


def _int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
