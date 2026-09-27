"""Admission Kit — bitta sahifa: qo'llanmalar, xizmatlar va so'rovlar.

Ilgari bu uchta alohida bo'lim edi va yon menyuda uchta qator egallardi.
Amalda ular doim birga ishlatiladi: xizmat yaratiladi -> unga PDF
biriktiriladi -> kim sotib olgani ko'riladi. Shuning uchun hammasi shu
sahifada.

Sahifa xizmat TURI bo'yicha ikkiga bo'lingan:
  * qo'llanmalar (FILE)  — faqat ular yonida PDF yuklash turadi;
  * xizmatlar (REQUEST)  — ularga fayl biriktirilmaydi.
Ilgari ikkalasi bitta jadvalda edi va mentor yonida ham fayl yuklash
tugmasi turardi — nimaga nima kerakligi bilinmasdi.

Pastdagi so'rovlar ro'yxatida FAQAT REQUEST turidagilar bo'ladi.
Qo'llanma sotib olinganda adminning qiladigan ishi yo'q (fayl avtomatik
yuboriladi), shuning uchun u ro'yxatni to'ldirib yubormasligi kerak —
o'rniga qo'llanma qatorida "sotib olganlar" soni ko'rinadi.

Xizmat matnlari (uch tilda nom, tavsif, narx izohi) bu yerda tahrirlanmaydi
— ular uchun sqladmin'ning o'z formasi ochiladi. Sabab: o'nlab maydonni
jadval ichiga tiqishtirish sahifani o'qib bo'lmaydigan qiladi, forma esa
allaqachon bor va ishlaydi. `AdmissionServiceAdmin` va `ServiceRequestAdmin`
menyudan yashirilgan (`is_visible`), lekin marshrutlari joyida — wizard'lar
bilan bir xil yondashuv.

Fayl qayerda saqlanadi va nega — `app/db/models/service.py`.
"""

import logging

from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.db.models import AdmissionService, ServiceKind, ServiceRequest
from app.db.session import async_session_factory
from app.services import kit_service

logger = logging.getLogger(__name__)

# So'rovlar vaqt o'tib yuzlab bo'lib ketadi. Sahifada oxirgilari ko'rinadi,
# qolganiga to'liq ro'yxatdan kiriladi.
RECENT_REQUESTS = 30

_STATUS_LABELS = {
    "new": ("Yangi", "bg-yellow-lt"),
    "contacted": ("Bog'lanildi", "bg-blue-lt"),
    "done": ("Bajarildi", "bg-green-lt"),
    "cancelled": ("Bekor qilindi", "bg-secondary-lt"),
}


def _size_label(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    return f"{max(size_bytes // 1024, 1)} KB"


def _int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


class AdmissionKitView(BaseView):
    name = "Admission Kit"
    identity = "admission-kit"
    icon = "fa-solid fa-briefcase"

    @expose("/admission-kit", methods=["GET"], identity="admission-kit")
    async def page(self, request: Request):
        async with async_session_factory() as session:
            services = (
                (
                    await session.execute(
                        select(AdmissionService).order_by(
                            AdmissionService.sort_order, AdmissionService.id
                        )
                    )
                )
                .scalars()
                .all()
            )

            # Qo'llanma nechta marta sotib olingani — qator boshiga bitta
            # so'rov yubormaslik uchun hammasi birdan sanaladi.
            bought = dict(
                (
                    await session.execute(
                        select(ServiceRequest.service_id, func.count()).group_by(
                            ServiceRequest.service_id
                        )
                    )
                ).all()
            )

            guides, manual = [], []
            for service in services:
                row = {
                    "id": service.id,
                    "title": service.title_uz,
                    "code": service.code,
                    "is_active": service.is_active,
                    "price": service.price_amount,
                    "currency": service.price_currency,
                    "bought": bought.get(service.id, 0),
                    "file": (
                        {
                            "filename": service.file.filename,
                            "size": _size_label(service.file.size_bytes),
                            "uploaded": service.file.updated_at,
                        }
                        if service.file is not None
                        else None
                    ),
                }
                (guides if service.kind == ServiceKind.FILE else manual).append(row)

            # So'rovlar ro'yxatida FAQAT qo'lda bajariladigan xizmatlar:
            # qo'llanma sotib olinganda admin hech narsa qilmaydi.
            request_filter = AdmissionService.kind == ServiceKind.REQUEST
            purchase_rows = (
                (
                    await session.execute(
                        select(ServiceRequest)
                        .join(ServiceRequest.service)
                        .where(request_filter)
                        .options(
                            selectinload(ServiceRequest.service),
                            selectinload(ServiceRequest.user),
                        )
                        .order_by(ServiceRequest.id.desc())
                        .limit(RECENT_REQUESTS)
                    )
                )
                .scalars()
                .all()
            )

            total_requests = (
                await session.execute(
                    select(func.count())
                    .select_from(ServiceRequest)
                    .join(ServiceRequest.service)
                    .where(request_filter)
                )
            ).scalar_one()

            purchases = [
                {
                    "id": row.id,
                    "created_at": row.created_at,
                    "service": row.service.title_uz if row.service else "—",
                    "user": str(row.user) if row.user else "—",
                    "status": _STATUS_LABELS.get(
                        row.status.value, (row.status.value, "bg-secondary-lt")
                    ),
                }
                for row in purchase_rows
            ]

        return await self.templates.TemplateResponse(
            request,
            "admission_kit.html",
            {
                "title": "Admission Kit",
                "subtitle": "Qo'llanmalar, xizmatlar va so'rovlar",
                "guides": guides,
                "manual": manual,
                "purchases": purchases,
                "requests_total": total_requests,
                "recent_limit": RECENT_REQUESTS,
                "max_mb": kit_service.MAX_PDF_BYTES // (1024 * 1024),
            },
        )

    @expose("/admission-kit/upload", methods=["POST"], identity="admission-kit-upload")
    async def upload(self, request: Request):
        back = RedirectResponse(request.url_for("admin:view-admission-kit"), status_code=303)
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
                f"«{service.title_uz}» uchun {row.filename} "
                f"({_size_label(row.size_bytes)}) yuklandi.",
            )
        return back

    @expose("/admission-kit/delete-file", methods=["POST"], identity="admission-kit-delete-file")
    async def delete_file(self, request: Request):
        back = RedirectResponse(request.url_for("admin:view-admission-kit"), status_code=303)
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
