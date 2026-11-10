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

from sqladmin import BaseView, ModelView, expose
from sqladmin.flash import Flash
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse
from wtforms.validators import InputRequired, NumberRange

from app.db.models import (
    AdmissionService,
    Gift,
    ServiceKind,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceSlot,
    UserGift,
)
from app.db.session import async_session_factory
from app.services import booking_service, kit_service
from app.services.timezone_utils import from_tashkent, to_tashkent

logger = logging.getLogger(__name__)

_OBTAINED_LABELS = {
    kit_service.OBTAINED_PAID: ("Sotib olgan", "bg-blue-lt"),
    kit_service.OBTAINED_INVITES: ("Do'st taklifi", "bg-green-lt"),
    kit_service.OBTAINED_GIFT: ("Sovg'a", "bg-pink-lt"),
    kit_service.OBTAINED_FREE: ("Bepul", "bg-secondary-lt"),
}

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


def _obtained_item(row: kit_service.ObtainedRow) -> dict:
    """Olingan xizmat qatori: "So'rovlar" va "Olingan xizmatlar" uchun umumiy."""
    purchase = row.request
    service = purchase.service
    return {
        "id": purchase.id,
        "created_at": purchase.created_at,
        "service": service.title_uz,
        "kind": "Qo'llanma" if service.kind == ServiceKind.FILE else "Yordam",
        "user": str(purchase.user) if purchase.user else "—",
        "user_id": purchase.user_id,
        "how": _OBTAINED_LABELS[row.how],
        "paid": f"{row.paid:,.0f} {service.price_currency}" if row.paid is not None else None,
        "status": _STATUS_LABELS.get(
            purchase.status.value, (purchase.status.value, "bg-secondary-lt")
        ),
        "status_value": purchase.status.value,
        "slot": (
            to_tashkent(purchase.slot.starts_at).strftime("%d.%m.%Y %H:%M")
            if purchase.slot
            else None
        ),
    }


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
        got = request.query_params.get("got")
        if got not in _OBTAINED_LABELS:
            got = None
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

            # Xizmat necha marta va qanday olingani — qator boshiga bitta
            # so'rov yubormaslik uchun hammasi birdan sanaladi.
            obtained = await kit_service.obtained_counts(session)
            bought = {service_id: sum(ways.values()) for service_id, ways in obtained.items()}
            obtained_totals = {
                how: sum(ways.get(how, 0) for ways in obtained.values()) for how in _OBTAINED_LABELS
            }

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
                    "obtained": obtained.get(service.id, {}),
                    "icon_url": kit_service.icon_url(service),
                    "has_icon": bool(service.icon_version),
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

            # Sovg'alar: necha marta tushgan va ishlatilgan.
            gift_rows = (
                (
                    await session.execute(
                        select(Gift).options(selectinload(Gift.service)).order_by(Gift.id)
                    )
                )
                .scalars()
                .all()
            )
            gift_stats = {
                gift_id: (opened, used)
                for gift_id, opened, used in (
                    await session.execute(
                        select(
                            UserGift.gift_id,
                            func.count(),
                            func.count(UserGift.used_at),
                        ).group_by(UserGift.gift_id)
                    )
                ).all()
            }
            active_weight = sum(g.weight for g in gift_rows if g.is_active and g.service.is_active)
            gifts = [
                {
                    "id": g.id,
                    "title": g.service.title_uz,
                    "discount": g.discount_percent,
                    "weight": g.weight,
                    "is_active": g.is_active,
                    "service_active": g.service.is_active,
                    "share": (
                        round(g.weight * 100 / active_weight)
                        if g.is_active and g.service.is_active and active_weight
                        else None
                    ),
                    "opened": gift_stats.get(g.id, (0, 0))[0],
                    "used": gift_stats.get(g.id, (0, 0))[1],
                }
                for g in gift_rows
            ]

            limit = None if show_all else RECENT_REQUESTS
            # Hamma olingan xizmatlar: pulga, do'st taklifi bilan yoki bepul.
            obtained_list = [
                _obtained_item(row)
                for row in await kit_service.obtained_rows(session, how=got, limit=limit)
            ]

            # So'rovlar ro'yxatida FAQAT qo'lda bajariladigan xizmatlar:
            # qo'llanma olinganda admin hech narsa qilmaydi.
            request_filter = AdmissionService.kind == ServiceKind.REQUEST
            purchases = [
                _obtained_item(row)
                for row in await kit_service.obtained_rows(
                    session, kind=ServiceKind.REQUEST, limit=limit
                )
            ]

            total_requests = (
                await session.execute(
                    select(func.count())
                    .select_from(ServiceRequest)
                    .join(ServiceRequest.service)
                    .where(request_filter)
                )
            ).scalar_one()

        return await self.templates.TemplateResponse(
            request,
            "admission_kit.html",
            {
                "title": "Admission Kit",
                "subtitle": "Qo'llanmalar, xizmatlar va so'rovlar",
                "guides": guides,
                "manual": manual,
                "purchases": purchases,
                "obtained_list": obtained_list,
                "obtained_totals": obtained_totals,
                "obtained_labels": _OBTAINED_LABELS,
                "obtained_filter": got,
                "slot_groups": slot_groups,
                "requests_total": total_requests,
                "recent_limit": RECENT_REQUESTS,
                "show_all": show_all,
                "statuses": [(s.value, _STATUS_LABELS[s.value][0]) for s in ServiceRequestStatus],
                "max_mb": kit_service.MAX_PDF_BYTES // (1024 * 1024),
                "gifts": gifts,
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

    @expose("/admission-kit/upload-icon", methods=["POST"], identity="admission-kit-upload-icon")
    async def upload_icon(self, request: Request):
        form = await request.form()
        back = self._back(request, form)
        service_id = _int(form.get("service_id"))
        upload = form.get("file")
        if service_id is None or upload is None or not getattr(upload, "filename", ""):
            Flash.error(request, "Fayl tanlanmadi.")
            return back

        data = await upload.read(kit_service.MAX_ICON_BYTES + 1)
        async with async_session_factory() as session:
            service = await session.get(AdmissionService, service_id)
            if service is None:
                Flash.error(request, "Xizmat topilmadi.")
                return back
            try:
                kit_service.save_icon(service, upload.content_type, data)
            except kit_service.FileRejected as exc:
                Flash.error(request, str(exc))
                return back
            await session.commit()
            Flash.success(request, f"«{service.title_uz}» ikonkasi yuklandi.")
        return back

    @expose("/admission-kit/delete-icon", methods=["POST"], identity="admission-kit-delete-icon")
    async def delete_icon(self, request: Request):
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
            kit_service.delete_icon(service)
            await session.commit()
            Flash.success(request, f"«{service.title_uz}» ikonkasi o'chirildi.")
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


class GiftAdmin(ModelView, model=Gift):
    """Sovg'a qutisidagi sovg'alar (Admission Kit sahifasidan ochiladi).

    Har bir sovg'a — Kit xizmatiga chegirma. User qutini bir marta ochadi va
    faol sovg'alardan biri «Ehtimol» bo'yicha tasodifan tushadi.
    """

    name = "Sovg'a"
    name_plural = "Sovg'alar"
    icon = "fa-solid fa-gift"

    def is_visible(self, request: Request) -> bool:
        return False

    column_list = [Gift.id, Gift.service, Gift.discount_percent, Gift.weight, Gift.is_active]
    form_columns = [Gift.service, Gift.discount_percent, Gift.weight, Gift.is_active]
    column_labels = {
        "service": "Kit xizmati",
        "discount_percent": "Chegirma (%)",
        "weight": "Ehtimol",
        "is_active": "Faol",
    }
    form_args = {
        "service": {"validators": [InputRequired()]},
        "discount_percent": {
            "validators": [InputRequired(), NumberRange(min=1, max=100)],
            "description": "1–100. 100 — xizmat bepul beriladi.",
            "default": 100,
        },
        "weight": {
            "validators": [InputRequired(), NumberRange(min=1, max=1000)],
            "description": (
                "Boshqa faol sovg'alarga nisbatan tushish ehtimoli. Masalan, 3 va 1 bo'lsa, "
                "birinchisi 3 marta ko'proq tushadi. Hammasi 1 bo'lsa — teng."
            ),
            "default": 1,
        },
        "is_active": {
            "description": "O'chirilsa, yangi ochilgan qutilarga tushmaydi (olganlarda qoladi).",
            "default": True,
        },
    }
