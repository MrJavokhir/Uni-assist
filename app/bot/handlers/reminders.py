"""Deadline eslatmasidagi tugmalar.

Tugmalar `program_id` bilan ishlaydi (saqlangan yozuv `id` si bilan emas):
jamlangan xabarda bir nechta dastur bo'ladi va foydalanuvchiga ko'rinadigan
narsa — dastur. Har bir bosishda tegishli `notification_logs` qatori
"bosilgan" deb belgilanadi — adminkadagi statistika shundan o'qiladi.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NotificationLog, SavedProgram, SavedProgramStatus
from app.i18n import t
from app.services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

router = Router(name="reminders")


async def _saved_for(
    session: AsyncSession, user_id: int, program_id: int
) -> SavedProgram | None:
    """Shu dastur AYNAN shu foydalanuvchining ro'yxatidami.

    Callback ma'lumotini istalgan odam yuborishi mumkin, shuning uchun
    egalik har safar qaytadan tekshiriladi.
    """
    stmt = select(SavedProgram).where(
        SavedProgram.user_id == user_id, SavedProgram.program_id == program_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _mark_clicked(session: AsyncSession, user_id: int, program_id: int) -> None:
    await session.execute(
        update(NotificationLog)
        .where(
            NotificationLog.user_id == user_id,
            NotificationLog.program_id == program_id,
        )
        .values(clicked=True)
    )


async def _handle(callback: CallbackQuery, session: AsyncSession, action: str) -> None:
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = user.ui_language.value

    try:
        program_id = int((callback.data or "").split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    saved = await _saved_for(session, user.id, program_id)
    if saved is None:
        await callback.answer(t("notif.not_yours", lang), show_alert=True)
        return

    if action == "applied":
        saved.status = SavedProgramStatus.APPLIED
        # "Ariza berdim" — bu dastur bo'yicha eslatmalar ham to'xtaydi.
        saved.reminders_active = False
        reply = t("notif.applied_done", lang)
    else:
        saved.reminders_active = False
        reply = t("notif.mute_done", lang)

    await _mark_clicked(session, user.id, program_id)
    await session.commit()

    await callback.answer()
    # Xabarni tahrirlaymiz: jamlangan xabarda bir nechta dastur bo'lishi
    # mumkin, shuning uchun butun matnni almashtirmasdan, tasdiqni qo'shamiz.
    try:
        await callback.message.edit_text(reply)
    except Exception:
        # Matn o'zgarmagan yoki xabar juda eski bo'lsa Telegram xato beradi —
        # foydalanuvchi uchun bu muhim emas, amal baribir bajarildi.
        logger.debug("Xabarni tahrirlab bo'lmadi", exc_info=True)


@router.callback_query(F.data.startswith("applied:"))
async def mark_applied(callback: CallbackQuery, session: AsyncSession) -> None:
    await _handle(callback, session, "applied")


@router.callback_query(F.data.startswith("mute:"))
async def mute_program(callback: CallbackQuery, session: AsyncSession) -> None:
    await _handle(callback, session, "mute")
