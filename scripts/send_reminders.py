"""Deadline eslatmalarini qo'lda ishga tushirish.

Odatda bot o'zi, Toshkent vaqti bilan 10:00 da yuboradi. Bu skript ikki
holatda kerak: scheduler o'tkazib yuborgan kunni qo'lda yopish va yangi
qoidani jonli ma'lumotda xavfsiz tekshirish.

    uv run python scripts/send_reminders.py --dry-run
    uv run python scripts/send_reminders.py --dry-run --date 2027-01-01
    uv run python scripts/send_reminders.py            # haqiqatan yuboradi

`--dry-run` hech narsa yubormaydi va bazaga yozmaydi — faqat kimga nima
ketishini chiqaradi.
"""

import argparse
import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.session import async_session_factory
from app.services.reminder_service import run_reminder_scan
from app.services.timezone_utils import TASHKENT_TZ


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hech narsa yuborilmaydi, faqat ro'yxat chiqadi.",
    )
    parser.add_argument(
        "--date",
        help="Qaysi kun nomidan ishlash (YYYY-MM-DD). Odatda bugun.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    today = date.fromisoformat(args.date) if args.date else datetime.now(TASHKENT_TZ).date()

    bot = None
    if not args.dry_run:
        if not settings.bot_token:
            print("BOT_TOKEN o'rnatilmagan — faqat --dry-run ishlaydi.")
            return 1
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    try:
        async with async_session_factory() as session:
            result = await run_reminder_scan(
                bot, session, today=today, dry_run=args.dry_run
            )
    finally:
        if bot is not None:
            await bot.session.close()

    rejim = "SINOV (hech narsa yuborilmadi)" if args.dry_run else "HAQIQIY"
    print(f"Sana: {today}  |  rejim: {rejim}")
    print(f"Foydalanuvchi: {result.sent_users}  |  dastur: {result.sent_messages}")
    if result.blocked_users:
        print(f"Botni bloklaganlar: {result.blocked_users}")

    if result.planned:
        print("\nKimga nima ketadi:")
        for plan in result.planned:
            user = plan.saved.user
            who = user.username or user.telegram_id
            print(
                f"  {who:<20} {plan.notif_type.value:<16} "
                f"{plan.saved.program.name[:40]:<40} (muddati: {plan.due_on})"
            )
    else:
        print("\nYuboriladigan eslatma yo'q.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
