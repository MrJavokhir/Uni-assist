"""Admin paneldan bot orqali userlarga xabar yuborish (app/services/broadcast_service.py)."""

from sqladmin import BaseView, expose
from sqladmin.flash import Flash
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.admin.auth import current_admin
from app.db.models import Broadcast
from app.db.models.broadcast import BROADCAST_AUDIENCES, BUTTON_KINDS
from app.db.session import async_session_factory
from app.services import broadcast_service as bs
from app.services import payment_service

AUDIENCE_LABELS = {
    "all": "Hamma userlar",
    "uz": "O'zbek tilidagilar",
    "ru": "Rus tilidagilar",
    "en": "Ingliz tilidagilar",
}
STATUS_LABELS = {
    bs.STATUS_DRAFT: ("Qoralama", "bg-secondary-lt"),
    bs.STATUS_SENDING: ("Yuborilmoqda", "bg-blue-lt"),
    bs.STATUS_DONE: ("Yuborildi", "bg-green-lt"),
    bs.STATUS_INTERRUPTED: ("To'xtatilgan", "bg-warning-lt"),
    bs.STATUS_FAILED: ("Xato — to'xtatildi", "bg-red-lt"),
}
HISTORY_LIMIT = 20
ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")


class BroadcastView(BaseView):
    name = "Xabar yuborish"
    identity = "broadcast"
    icon = "fa-solid fa-paper-plane"

    def _back(self, request: Request, draft_id: int | None = None) -> RedirectResponse:
        url = str(request.url_for("admin:view-broadcast"))
        if draft_id:
            url += f"?draft={draft_id}"
        return RedirectResponse(url, status_code=303)

    @expose("/broadcast", methods=["GET"], identity="broadcast")
    async def page(self, request: Request):
        draft_id = request.query_params.get("draft")
        async with async_session_factory() as session:
            draft = None
            if draft_id and draft_id.isdigit():
                draft = await session.get(Broadcast, int(draft_id))
                if draft is not None and draft.status != bs.STATUS_DRAFT:
                    draft = None
            history = (
                (
                    await session.execute(
                        select(Broadcast)
                        .where(Broadcast.status != bs.STATUS_DRAFT)
                        .order_by(Broadcast.id.desc())
                        .limit(HISTORY_LIMIT)
                    )
                )
                .scalars()
                .all()
            )
            counts = {
                audience: await bs.count_recipients(session, audience)
                for audience in BROADCAST_AUDIENCES
            }
            admins = await payment_service.active_admin_ids(session)
        return await self.templates.TemplateResponse(
            request,
            "broadcast.html",
            {
                "title": "Xabar yuborish",
                "subtitle": "Bot orqali userlarga xabar",
                "draft": draft,
                "draft_has_image": bool(draft and draft.image_type),
                "history": history,
                "counts": counts,
                "audiences": AUDIENCE_LABELS,
                "statuses": STATUS_LABELS,
                "admins_count": len(admins),
                "sending": any(b.status == bs.STATUS_SENDING for b in history),
            },
        )

    @expose("/broadcast", methods=["POST"], identity="broadcast-create")
    async def create(self, request: Request):
        """Qoralama + bot adminlariga sinov."""
        form = await request.form()
        text = str(form.get("text") or "").strip()
        audience = str(form.get("audience") or "all")
        if audience not in BROADCAST_AUDIENCES:
            audience = "all"
        button_text = str(form.get("button_text") or "").strip()[:64]
        button_kind = str(form.get("button_kind") or "webapp")
        if button_kind not in BUTTON_KINDS:
            button_kind = "webapp"
        button_url = str(form.get("button_url") or "").strip()[:500]

        image = form.get("image")
        image_data = image_type = None
        if image is not None and getattr(image, "filename", ""):
            image_data = await image.read()
            image_type = image.content_type
            if image_type not in ALLOWED_IMAGE_TYPES:
                Flash.error(request, "Rasm JPG, PNG yoki WEBP bo'lishi kerak.")
                return self._back(request)
            if len(image_data) > bs.MAX_IMAGE_BYTES:
                Flash.error(request, "Rasm 5 MB dan katta.")
                return self._back(request)

        error = bs.validate(text, bool(image_data), button_text, button_kind, button_url)
        if error:
            Flash.error(request, error)
            return self._back(request)

        async with async_session_factory() as session:
            admins = await payment_service.active_admin_ids(session)
            broadcast = Broadcast(
                text=text,
                image_data=image_data,
                image_type=image_type,
                button_text=button_text or None,
                button_kind=button_kind if button_text else None,
                button_url=button_url or None,
                audience=audience,
                status=bs.STATUS_DRAFT,
                started_by=current_admin(request),
            )
            session.add(broadcast)
            await session.commit()
            draft_id = broadcast.id

        if not admins:
            test_error = (
                "Bot adminlari ro'yxati bo'sh — sinov yuborilmadi. «Bot adminlari» bo'limiga "
                "o'z Telegram ID'ingizni qo'shing."
            )
        else:
            errors = await bs.send_test(broadcast, admins)
            test_error = "; ".join(errors)[:1000] if errors else None
        # Sinov natijasi saqlanadi: yiqilgan bo'lsa, hammaga yuborib bo'lmaydi.
        async with async_session_factory() as session:
            row = await session.get(Broadcast, draft_id)
            row.test_error = test_error
            await session.commit()
        if test_error:
            Flash.error(request, "Sinov yuborilmadi — xabarni tuzating.")
        else:
            Flash.success(request, f"Sinov xabari {len(admins)} ta bot adminiga yuborildi.")
        return self._back(request, draft_id)

    @expose("/broadcast/{broadcast_id:int}/send", methods=["POST"], identity="broadcast-send")
    async def send(self, request: Request):
        broadcast_id = request.path_params["broadcast_id"]
        form = await request.form()
        if form.get("confirm") != "yes":
            Flash.error(request, "Yuborishni tasdiqlang.")
            return self._back(request, broadcast_id)
        async with async_session_factory() as session:
            broadcast = await session.get(Broadcast, broadcast_id)
            if broadcast is None or broadcast.status != bs.STATUS_DRAFT:
                Flash.error(request, "Qoralama topilmadi yoki allaqachon yuborilgan.")
                return self._back(request)
            if broadcast.test_error:
                Flash.error(request, "Sinov yiqilgan xabarni hammaga yuborib bo'lmaydi.")
                return self._back(request, broadcast_id)
            broadcast.status = bs.STATUS_SENDING
            broadcast.started_by = current_admin(request)
            await session.commit()
        bs.start(broadcast_id)
        Flash.success(request, "Yuborish boshlandi. Natija quyidagi ro'yxatda yangilanib boradi.")
        return self._back(request)

    @expose("/broadcast/{broadcast_id:int}/discard", methods=["POST"], identity="broadcast-discard")
    async def discard(self, request: Request):
        broadcast_id = request.path_params["broadcast_id"]
        async with async_session_factory() as session:
            broadcast = await session.get(Broadcast, broadcast_id)
            if broadcast is not None and broadcast.status == bs.STATUS_DRAFT:
                await session.delete(broadcast)
                await session.commit()
        return self._back(request)

    @expose("/broadcast/{broadcast_id:int}/image", methods=["GET"], identity="broadcast-image")
    async def image(self, request: Request):
        broadcast_id = request.path_params["broadcast_id"]
        async with async_session_factory() as session:
            row = (
                await session.execute(
                    select(Broadcast.image_data, Broadcast.image_type).where(
                        Broadcast.id == broadcast_id
                    )
                )
            ).one_or_none()
        if row is None or not row[0]:
            return Response(status_code=404)
        return Response(content=row[0], media_type=row[1] or "image/jpeg")
