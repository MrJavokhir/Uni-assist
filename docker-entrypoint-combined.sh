#!/bin/bash
# Railway'da bitta servis ichida admin panel (+ Mini App) va botni birga
# ishga tushiradi. Bunga sabab: joriy Railway loyiha tokeni yangi servis
# yaratishga ruxsat bermaydi, lekin mavjud servisni to'liq boshqarish
# mumkin. docker-compose.yml (masalan Contabo VPS) da esa bular alohida
# servis sifatida ishlayveradi — bu fayl faqat shu bitta-servis holati uchun.
set -e

alembic upgrade head

# Katalog (davlatlar, universitetlar, dasturlar, stipendiyalar) kodda emas —
# faqat admin panel orqali boshqariladi. Deploy faqat sxemani yangilaydi.

# --proxy-headers + --forwarded-allow-ips: Railway TLS'ni o'z proxy'sida tugatib,
# konteynerga oddiy HTTP bilan uzatadi. Busiz url_for() "http://" havolalar
# yasaydi va brauzer ularni "mixed content" deb bloklaydi (admin panel CSS'siz
# qoladi). Konteyner faqat Railway proxy orqali ochiq, shuning uchun "*" xavfsiz.
uvicorn app.admin.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips="*" &
ADMIN_PID=$!

python -m app.bot.main &
BOT_PID=$!

wait -n "$ADMIN_PID" "$BOT_PID"
exit $?
