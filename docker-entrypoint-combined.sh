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
#
# Bot ALOHIDA jarayon emas — admin panel bilan bitta jarayonda, FastAPI
# lifespan'i ichida ishlaydi (app/admin/main.py). Ilgari ikkita Python
# jarayoni bor edi va har biri butun ilovani qaytadan yuklardi: o'lchovda
# ikkalasi 424 MB, bitta jarayon esa 224 MB. Railway RAM uchun pul oladi,
# shuning uchun bu eng katta tejam. Bot yiqilsa jarayon yopiladi va
# Railway uni qayta ishga tushiradi — avvalgi `wait -n` xatti-harakati.
export RUN_BOT_IN_PROCESS=1
exec uvicorn app.admin.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips="*"
