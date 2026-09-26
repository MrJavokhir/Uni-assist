"""Balansni to'ldirish — botda, qo'lda tasdiqlash bilan.

Oqim:
    /topup           -> summa so'raladi
    <summa>          -> karta rekvizitlari va ko'rsatma
    /chekyubor       -> chek rasmi so'raladi
    <rasm>           -> adminlarga xabar ketadi
    /approve <id> <summa> | /reject <id> | /blockuser <id>

To'lov tizimi ULANMAGAN: pul kartaga o'tkaziladi, chek qo'lda tekshiriladi.
Shuning uchun balans faqat admin /approve yozgandan keyin to'ldiriladi.

Holat (FSM) Redis'da saqlanadi — konteyner har deployda qayta ishga
tushadi, xotiradagi holat esa yo'qolib, foydalanuvchi oqim o'rtasida
"osilib" qolardi.
"""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentStatus, User
from app.services import payment_service
from app.services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

router = Router(name="payment")


class TopUp(StatesGroup):
    amount = State()
    receipt = State()


def _money(value: Decimal | float, currency: str) -> str:
    """10000 -> "10,000 so'm". Uch xonali guruhlash o'qishni yengillashtiradi."""
    amount = Decimal(str(value)).quantize(Decimal(1))
    return f"{amount:,} {currency}"


# ============ Foydalanuvchi tomoni ============


@router.message(Command("topup"))
async def cmd_topup(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    if user.is_blocked:
        await message.answer("Hisobingiz bloklangan. Sabab bo'yicha admin bilan bog'laning.")
        return

    settings_row = await payment_service.get_settings(session)
    await session.commit()

    await state.set_state(TopUp.amount)
    await message.answer(
        "💰 <b>Balans to'ldirish</b>\n\n"
        "To'ldirmoqchi bo'lgan summani yozing (so'mda).\n"
        f"Eng kam miqdor: {_money(settings_row.min_amount, settings_row.currency)}\n\n"
        "Misol: 10000, 20000, 50000"
    )


@router.message(TopUp.amount, F.text)
async def enter_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    # Foydalanuvchi "10 000" yoki "10.000" deb yozishi mumkin — bo'shliq va
    # ajratgichlarni tashlab yuboramiz, aks holda har safar xato beraverardi.
    raw = (message.text or "").strip().replace(" ", "").replace(",", "").replace(".", "")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        await message.answer("Summani faqat raqam bilan yozing. Masalan: 10000")
        return

    settings_row = await payment_service.get_settings(session)
    minimum = Decimal(str(settings_row.min_amount))
    if amount < minimum:
        await message.answer(
            f"Eng kam miqdor — {_money(minimum, settings_row.currency)}. "
            "Iltimos, kattaroq summa yozing."
        )
        return

    if not settings_row.card_number:
        # Adminka to'ldirilmagan bo'lsa, foydalanuvchiga bo'sh karta
        # ko'rsatib qo'ymaymiz.
        await state.clear()
        await message.answer(
            "To'lov rekvizitlari hali sozlanmagan. Birozdan keyin urinib ko'ring."
        )
        logger.warning("payment_settings.card_number bo'sh — /topup yakunlanmadi")
        return

    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    payment = await payment_service.start_topup(session, user, amount)
    await session.commit()

    await state.set_state(TopUp.receipt)
    await message.answer(
        "💳 <b>Balansni plastik kartaga pul o'tkazish orqali to'ldirish:</b>\n\n"
        f"1. Quyidagi karta raqamiga {_money(amount, settings_row.currency)} o'tkazing\n"
        "2. Botga /chekyubor yozing\n"
        "3. To'lov chekining rasmini yuboring\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Karta raqami (bosib nusxalang):\n"
        f"<code>{settings_row.card_number}</code>\n"
        f"Karta egasi: {settings_row.card_holder}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"To'lov miqdori: {_money(amount, settings_row.currency)}\n\n"
        "<b>Eslatmalar:</b>\n"
        "— Chekni yubormasangiz, balans to'ldirilmaydi\n"
        "— Cheklar qo'lda tekshiriladi\n"
        "— To'lov aniq bo'lmasa, qabul qilinmaydi\n\n"
        "/chekyubor"
    )
    logger.info("To'lov #%s yaratildi: %s", payment.id, amount)


@router.message(Command("chekyubor"))
async def cmd_receipt(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    payment = await payment_service.latest_open_payment(session, user)
    await session.commit()

    if payment is None:
        await message.answer("Avval /topup orqali summani kiriting.")
        return

    await state.set_state(TopUp.receipt)
    await message.answer(
        "To'lov chekining rasmini yuboring.\n\n"
        "Rasm aniq bo'lsin: summa, sana va karta raqami ko'rinib tursin."
    )


@router.message(TopUp.receipt, F.photo | F.document)
async def receive_receipt(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    payment = await payment_service.latest_open_payment(session, user)
    if payment is None:
        await state.clear()
        await message.answer("Avval /topup orqali summani kiriting.")
        return

    if message.photo:
        # Oxirgi element — eng katta o'lcham.
        file_id, kind = message.photo[-1].file_id, "photo"
    else:
        file_id, kind = message.document.file_id, "document"

    await payment_service.attach_receipt(session, payment, file_id, kind)
    admin_ids = await payment_service.active_admin_ids(session)
    await session.commit()

    await state.clear()
    await message.answer(
        "✅ Chek qabul qilindi.\n\n"
        "Admin tekshirgach, balansingiz to'ldiriladi va sizga xabar keladi."
    )

    if not admin_ids:
        logger.warning("Bot adminlari ro'yxati bo'sh — chek haqida hech kimga xabar ketmadi")
        return

    caption = (
        "🧾 <b>Yangi to'lov cheki!</b>\n\n"
        f"👤 User: {message.from_user.full_name}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"💰 Miqdor: {_money(payment.amount, payment.currency)}\n"
        f"🧾 Payment ID: {payment.id}\n"
        f"📎 Fayl turi: {kind}\n\n"
        f"Tasdiqlash: <code>/approve {message.from_user.id} "
        f"{Decimal(str(payment.amount)).quantize(Decimal(1))}</code>\n"
        f"Rad etish: <code>/reject {message.from_user.id}</code>\n"
        f"Blokash: <code>/blockuser {message.from_user.id}</code>"
    )
    for admin_id in admin_ids:
        try:
            if kind == "photo":
                await bot.send_photo(admin_id, file_id, caption=caption)
            else:
                await bot.send_document(admin_id, file_id, caption=caption)
        except Exception:
            # Bitta admin botni bloklagan bo'lsa, qolganlari xabarsiz
            # qolmasligi kerak.
            logger.exception("Adminga chek yuborilmadi: %s", admin_id)


@router.message(TopUp.receipt)
async def receipt_wrong_type(message: Message) -> None:
    await message.answer("Chekni RASM yoki fayl sifatida yuboring.")


# ============ Admin tomoni ============


async def _target_user(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    return (await session.execute(stmt)).scalar_one_or_none()


def _parse_args(message: Message, count: int) -> list[str] | None:
    parts = (message.text or "").split()
    return parts[1 : count + 1] if len(parts) >= count + 1 else None


@router.message(Command("approve"))
async def cmd_approve(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not await payment_service.is_admin(session, message.from_user.id):
        return

    args = _parse_args(message, 2)
    if args is None:
        await message.answer("Format: /approve &lt;telegram_id&gt; &lt;summa&gt;")
        return

    try:
        target_id = int(args[0])
        amount = Decimal(args[1])
    except (ValueError, InvalidOperation):
        await message.answer("Telegram ID va summa raqam bo'lishi kerak.")
        return

    user = await _target_user(session, target_id)
    if user is None:
        await message.answer("Bunday foydalanuvchi topilmadi.")
        return

    payment = await payment_service.latest_open_payment(session, user)
    if payment is None:
        await message.answer("Bu foydalanuvchida ochiq to'lov yo'q.")
        return

    # Admin summani o'zgartirib yuborishi mumkin (chekda boshqa raqam
    # bo'lsa) — balansga aynan admin tasdiqlagan summa qo'shiladi.
    payment.amount = amount
    new_balance = await payment_service.approve_payment(session, payment, message.from_user.id)
    await session.commit()

    await message.answer(
        f"✅ Tasdiqlandi. {_money(amount, payment.currency)} qo'shildi.\n"
        f"Yangi balans: {_money(new_balance, payment.currency)}"
    )
    try:
        await bot.send_message(
            target_id,
            f"✅ To'lovingiz tasdiqlandi!\n\n"
            f"Qo'shildi: {_money(amount, payment.currency)}\n"
            f"Joriy balans: {_money(new_balance, payment.currency)}",
        )
    except Exception:
        logger.exception("Foydalanuvchiga tasdiq xabari yetmadi: %s", target_id)


@router.message(Command("reject"))
async def cmd_reject(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not await payment_service.is_admin(session, message.from_user.id):
        return

    args = _parse_args(message, 1)
    if args is None:
        await message.answer("Format: /reject &lt;telegram_id&gt;")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("Telegram ID raqam bo'lishi kerak.")
        return

    user = await _target_user(session, target_id)
    if user is None:
        await message.answer("Bunday foydalanuvchi topilmadi.")
        return

    payment = await payment_service.latest_open_payment(session, user)
    if payment is None:
        await message.answer("Bu foydalanuvchida ochiq to'lov yo'q.")
        return

    await payment_service.reject_payment(session, payment, message.from_user.id)
    await session.commit()

    await message.answer("❌ Rad etildi.")
    try:
        await bot.send_message(
            target_id,
            "❌ To'lovingiz qabul qilinmadi.\n\n"
            "Chek noaniq yoki summa mos kelmagan bo'lishi mumkin. "
            "Qayta urinish uchun /topup yozing.",
        )
    except Exception:
        logger.exception("Foydalanuvchiga rad xabari yetmadi: %s", target_id)


@router.message(Command("blockuser"))
async def cmd_block(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not await payment_service.is_admin(session, message.from_user.id):
        return

    args = _parse_args(message, 1)
    if args is None:
        await message.answer("Format: /blockuser &lt;telegram_id&gt;")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("Telegram ID raqam bo'lishi kerak.")
        return

    user = await _target_user(session, target_id)
    if user is None:
        await message.answer("Bunday foydalanuvchi topilmadi.")
        return

    user.is_blocked = True
    # Ochiq to'lovi bo'lsa, u ham yopiladi — aks holda "tekshiruvda" holatida
    # abadiy osilib qolardi.
    payment = await payment_service.latest_open_payment(session, user)
    if payment is not None:
        payment.status = PaymentStatus.REJECTED
        payment.reviewed_by = message.from_user.id
        payment.admin_note = "Foydalanuvchi bloklandi"
    await session.commit()

    await message.answer(f"🚫 {target_id} bloklandi.")
    try:
        await bot.send_message(target_id, "Hisobingiz bloklandi. Admin bilan bog'laning.")
    except Exception:
        logger.exception("Foydalanuvchiga blok xabari yetmadi: %s", target_id)


@router.message(Command("balans"))
async def cmd_balance(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    settings_row = await payment_service.get_settings(session)
    await session.commit()
    await message.answer(
        f"💰 Joriy balansingiz: <b>{_money(user.balance or 0, settings_row.currency)}</b>\n\n"
        "To'ldirish: /topup"
    )


__all__ = ["router"]
