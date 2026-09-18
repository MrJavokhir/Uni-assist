#!/bin/bash
# Railway'da bitta servis ichida admin panel (+ Mini App) va botni birga
# ishga tushiradi. Bunga sabab: joriy Railway loyiha tokeni yangi servis
# yaratishga ruxsat bermaydi, lekin mavjud servisni to'liq boshqarish
# mumkin. docker-compose.yml (masalan Contabo VPS) da esa bular alohida
# servis sifatida ishlayveradi — bu fayl faqat shu bitta-servis holati uchun.
set -e

alembic upgrade head

uvicorn app.admin.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
ADMIN_PID=$!

python -m app.bot.main &
BOT_PID=$!

wait -n "$ADMIN_PID" "$BOT_PID"
exit $?
