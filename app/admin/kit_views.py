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

Uchinchi bo'lim — uchrashuv vaqtlari. U faqat «Vaqt tanlansin» yoqilgan
xizmatlar uchun ko'rinadi: qolganlariga vaqt tushunchasi yo'q va bo'sh
jadval faqat chalkashtirardi.

Pastdagi so'rovlar ro'yxatida FAQAT REQUEST turidagilar bo'ladi.
Qo'llanma sotib olinganda adminning qiladigan ishi yo'q (fayl avtomatik
yuboriladi), shuning uchun u ro'yxatni to'ldirib yubormasligi kerak —
o'rniga qo'llanma qatorida "sotib olganlar" soni ko'rinadi.

Sahifadan CHIQIB ketiladigan yagona joy — xizmat matnlarini (uch tilda
nom, tavsif, narx izohi) tahrirlaydigan forma. O'nlab maydonni jadval
ichiga tiqishtirib bo'lmaydi, sqladmin formasi esa allaqachon bor va
ishlaydi. Undan tashqari hamma amal shu yerda bajariladi: holat, faollik,
o'chirish. Sqladmin ro'yxat sahifalariga havola ATAYLAB qo'yilmagan —
ular alohida bo'lim taassurotini berardi (saqlangandan keyin ham o'sha
yerga qaytarardi, qarang: `app/admin/main.py`).

Fayl qayerda saqlanadi va nega — `app/db/models/service.py`.
"""

import logging
from datetime import UTC, datetime

from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.db.models import (
    AdmissionService,
    ServiceKind,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceSlot,
)
from app.db.session import async_session_factory
from app.services import booking_service, kit_service
from app.services.timezone_utils import from_tashkent, to_tashkent

logger = logging.getLogger(__name__)

# So'rovlar vaqt o'tib yuzlab bo'lib ketadi. Sahifada oxirgilari ko'rinadi,
# "hammasini ko'rsatish" esa ?all=1 bilan SHU sahifani ochadi.
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
        show_all = request.query_params.get("all") == "1"
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
                    # Sotib olingan xizmatni o'chirish xarid tarixini ham
                    # olib ketadi (FK CASCADE). Shuning uchun o'chirish
                    # faqat hech kim sotib olmagan xizmatda taklif qilinadi
                    # — qolganini "faol emas" qilish kifoya.
                    "can_delete": bought.get(service.id, 0) == 0,
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

            # Uchrashuv vaqtlari — faqat "Vaqt tanlansin" yoqilgan
            # xizmatlar uchun. Qolganlarida bo'sh jadval chalkashtirardi.
            booking_services = [s for s in services if s.requires_booking]
            slot_groups = []
            for service in booking_services:
                rows_for_service = (
                    (
                        await session.execute(
                            select(ServiceSlot)
                            .where(ServiceSlot.service_id == service.id)
                            .options(
                                selectinload(ServiceSlot.request).selectinload(ServiceRequest.user)
                            )
                            .order_by(ServiceSlot.starts_at)
                        )
                    )
                    .scalars()
                    .all()
                )
                slot_groups.append(
                    {
                        "service_id": service.id,
                        "title": service.title_uz,
                        "slots": [
                            {
                                "id": slot.id,
                                "local": to_tashkent(slot.starts_at),
                                "duration": slot.duration_minutes,
                                "note": slot.note,
                                "taken_by": (
                                    str(slot.request.user)
                                    if slot.request and slot.request.user
                                    else None
                                ),
                                "is_past": slot.starts_at <= datetime.now(UTC),
                            }
                            for slot in rows_for_service
                        ],
                    }
                )

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
                        .limit(None if show_all else RECENT_REQUESTS)
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
                    "status_value": row.status.value,
                    "slot": (
                        to_tashkent(row.slot.starts_at).strftime("%d.%m.%Y %H:%M")
                        if row.slot
                        else None
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
                "slot_groups": slot_groups,
                "requests_total": total_requests,
                "recent_limit": RECENT_REQUESTS,
                "show_all": show_all,
                "statuses": [(s.value, _STATUS_LABELS[s.value][0]) for s in ServiceRequestStatus],
                "max_mb": kit_service.MAX_PDF_BYTES // (1024 * 1024),
            },
        )

    def _back(self, request: Request, form=None) -> RedirectResponse:
        """Har bir amal SHU sahifaga qaytadi.

        "Hammasini ko'rsatish" holati yo'qolmasligi kerak: uzun ro'yxatda
        holatni o'zgartirgan odam yana qisqartirilgan ko'rinishga tushib
        qolsa, qayerda ishlayotganini yo'qotadi.
        """
        url = request.url_for("admin:view-admission-kit")
        if form is not None and form.get("all") == "1":
            url = url.include_query_params(all="1")
        return RedirectResponse(url, status_code=303)

    @expose("/admission-kit/upload", methods=["POST"], identity="admission-kit-upload")
    async def upload(self, request: Request):
        form = await request.form()
        back = self._back(request, form)
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
        form = await request.form()
        back = self._back(request, form)
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

    @expose("/admission-kit/toggle-active", methods=["POST"], identity="admission-kit-toggle")
    async def toggle_active(self, request: Request):
        """Xizmatni ilovada ko'rsatish / yashirish.

        Sotib olingan xizmatni o'chirish o'rniga shu ishlatiladi: ilovada
        ko'rinmaydi, xarid tarixi esa joyida qoladi.
        """
        form = await request.form()
        back = self._back(request, form)
        service_id = _int(form.get("service_id"))
        if service_id is None:
            return back

        async with async_session_factory() as session:
            service = await session.get(AdmissionService, service_id)
            if service is None:
                Flash.error(request, "Xizmat topilmadi.")
                return back
            service.is_active = not service.is_active
            state = "faol" if service.is_active else "faol emas"
            await session.commit()
            Flash.success(request, f"«{service.title_uz}» endi {state}.")
        return back

    @expose(
        "/admission-kit/delete-service", methods=["POST"], identity="admission-kit-delete-service"
    )
    async def delete_service(self, request: Request):
        """Xizmatni butunlay o'chirish.

        Faqat hech kim sotib olmagan xizmat o'chiriladi. Aks holda FK
        CASCADE xarid yozuvlarini ham olib ketardi va "kim nima uchun
        to'lagan" degan savolga javob qolmasdi — sahifadagi tugma ham
        shunday xizmatda ko'rsatilmaydi, bu esa o'sha qoidaning server
        tomondagi nusxasi.
        """
        form = await request.form()
        back = self._back(request, form)
        service_id = _int(form.get("service_id"))
        if service_id is None:
            return back

        async with async_session_factory() as session:
            service = await session.get(AdmissionService, service_id)
            if service is None:
                Flash.error(request, "Xizmat topilmadi.")
                return back

            bought = (
                await session.execute(
                    select(func.count())
                    .select_from(ServiceRequest)
                    .where(ServiceRequest.service_id == service_id)
                )
            ).scalar_one()
            if bought:
                Flash.error(
                    request,
                    f"«{service.title_uz}» {bought} marta sotib olingan — o'chirib bo'lmaydi. "
                    "Ilovadan yashirish uchun «Faol emas» qiling.",
                )
                return back

            title = service.title_uz
            await session.delete(service)
            await session.commit()
            Flash.success(request, f"«{title}» o'chirildi.")
        return back

    @expose("/admission-kit/set-status", methods=["POST"], identity="admission-kit-set-status")
    async def set_status(self, request: Request):
        """So'rov holatini SHU sahifada o'zgartirish.

        Ilgari buning uchun sqladmin formasiga o'tilardi va saqlagandan
        keyin odam boshqa ro'yxat sahifasida qolib ketardi.
        """
        form = await request.form()
        back = self._back(request, form)
        request_id = _int(form.get("request_id"))
        raw_status = str(form.get("status") or "")
        try:
            status = ServiceRequestStatus(raw_status)
        except ValueError:
            Flash.error(request, "Noma'lum holat.")
            return back
        if request_id is None:
            return back

        async with async_session_factory() as session:
            row = await session.get(ServiceRequest, request_id)
            if row is None:
                Flash.error(request, "So'rov topilmadi.")
                return back
            row.status = status
            await session.commit()
        return back

    @expose("/admission-kit/add-slot", methods=["POST"], identity="admission-kit-add-slot")
    async def add_slot(self, request: Request):
        """Yangi uchrashuv oynasi.

        Vaqt formadan mintaqasiz keladi ("2026-10-05T14:00") va Toshkent
        vaqti deb qabul qilinadi — qarang: `timezone_utils.from_tashkent`.
        """
        form = await request.form()
        back = self._back(request, form)
        service_id = _int(form.get("service_id"))
        raw = str(form.get("starts_at") or "").strip()
        duration = _int(form.get("duration")) or 60
        note = str(form.get("note") or "").strip() or None

        if service_id is None or not raw:
            Flash.error(request, "Sana va vaqtni kiriting.")
            return back
        try:
            local = datetime.fromisoformat(raw)
        except ValueError:
            Flash.error(request, "Sana formati noto'g'ri.")
            return back

        starts_at = from_tashkent(local)
        if starts_at <= datetime.now(UTC):
            # O'tib ketgan vaqt ilovada baribir ko'rinmaydi — uni qo'shib
            # qo'yish adminga "qo'shildi" deb yolg'on aytardi.
            Flash.error(request, "O'tib ketgan vaqtni qo'shib bo'lmaydi.")
            return back

        async with async_session_factory() as session:
            service = await session.get(AdmissionService, service_id)
            if service is None:
                Flash.error(request, "Xizmat topilmadi.")
                return back
            await booking_service.add_slot(session, service_id, starts_at, duration, note)
            await session.commit()
            Flash.success(request, f"«{service.title_uz}» uchun {local:%d.%m.%Y %H:%M} qo'shildi.")
        return back

    @expose("/admission-kit/delete-slot", methods=["POST"], identity="admission-kit-delete-slot")
    async def delete_slot(self, request: Request):
        form = await request.form()
        back = self._back(request, form)
        slot_id = _int(form.get("slot_id"))
        if slot_id is None:
            return back

        async with async_session_factory() as session:
            removed = await booking_service.delete_slot(session, slot_id)
            await session.commit()
        if not removed:
            # Band qilingan oyna o'chirilmaydi: odam pul to'lagan va o'sha
            # vaqtga yozilgan.
            Flash.error(
                request,
                "Band qilingan vaqtni o'chirib bo'lmaydi. Uchrashuvni bekor qilish kerak "
                "bo'lsa, so'rov holatini o'zgartiring va odam bilan gaplashing.",
            )
        return back
