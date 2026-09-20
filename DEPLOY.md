# Deploy (Railway)

Loyiha Railway'da **bitta servis** ichida ishlaydi: admin panel (+ Mini App) va
Telegram bot birga. Sabab `docker-entrypoint-combined.sh` boshida yozilgan.

| | |
|---|---|
| Servis | `Uni-assist` |
| URL | https://uni-assist-production-8bc4.up.railway.app |
| Manba | GitHub `MrJavokhir/Uni-assist`, `master` |
| Build | `Dockerfile.combined` |
| Bazalar | Postgres, Redis (o'sha loyihada) |

Har `master`ga push GitHub orqali avtomatik build va deploy'ni boshlaydi.
Migratsiyalar (`alembic upgrade head`) konteyner ishga tushganda o'zi bajariladi.

## Katalogni to'ldirish (seed)

Seed skriptlari **avtomatik ishlamaydi** — kodni push qilish yetarli emas.
Railway Postgres'i tashqaridan ochiq bo'lmagani uchun yo'l shunday:

1. Railway → Variables → `RUN_SEEDS=1`
2. Deploy tugashini kuting, log'da tekshiring:
   `✓ seed_scholarships`, `✓ seed_top_destinations`, `✓ seed_llm_programs`
3. `RUN_SEEDS=0` ga qaytaring

Skriptlar idempotent — tasodifan yoqilgan holda qolsa ham dublikat yaratmaydi.
Bittasi yiqilsa ham servis baribir ishga tushadi (faqat log'da `✗` yoziladi).

## ⚠️ CLI'dan `railway redeploy` QILMANG

`railway redeploy` / `railway up` lokal papkani yuklab, Railpack bilan build
qilmoqchi bo'ladi va **yiqiladi** (`railpack prepare exited with an error`).
Servis GitHub'dan deploy bo'ladi, lokal papkadan emas.

Qayta deploy kerak bo'lsa: Railway UI'dagi **Redeploy** tugmasi, yoki yangi
commit push qiling. Yiqilgan CLI deploy'i ishlab turgan servisga ta'sir
qilmaydi — eski muvaffaqiyatli deploy ishlayveradi.

## Servis sozlamalari qayerda

Muhim sozlamalar `railway.json`da emas, **servisning o'zida** saqlanadi
(Railway UI → Settings). Shunda ular config faylga bog'liq bo'lmaydi:

- Dockerfile Path: `Dockerfile.combined`
- Healthcheck Path: `/health`
- Restart Policy: `ON_FAILURE`, 5 marta

## ⚠️ 2026-12-01: `railway.json` o'chadi

Railway `railway.json` / `railway.toml` (Config as Code) ni eskirgan deb
e'lon qildi. Mavjud servislar uni **2026-12-01 gacha** o'qiydi, keyin yo'q.

Yuqoridagi sozlamalar servisning o'ziga yozib qo'yilgani uchun o'sha sanada
deploy buzilmaydi. Lekin o'shangacha yangi formatga (`.railway/railway.ts`,
Infrastructure as Code) o'tish kerak:

```
railway config migrate --apply    # CLI 4.57.5 da hali yo'q, yangilash kerak
```

Hujjat: https://docs.railway.com/infrastructure-as-code

## Bot haqida

Deploy paytida log'da `TelegramConflictError: terminated by other getUpdates`
chiqishi **normal** — eski va yangi konteyner bir necha soniya birga ishlaydi.
Eski konteyner to'xtagach o'zi tinadi. Agar u davom etsa, bot boshqa joyda
(masalan lokal mashinada) ham ishlayotgan bo'lishi mumkin.

## Majburiy kanal obunasi

Admin panel → Majburiy kanallar → havola kiriting. **Bot o'sha kanalda
administrator bo'lishi shart** — busiz Telegram a'zolikni tekshirishga ruxsat
bermaydi va tekshiruv o'tkazib yuboriladi (foydalanuvchi bloklanmaydi).
