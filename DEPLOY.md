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

## Katalogni to'ldirish

Katalog (davlatlar, universitetlar, dasturlar, stipendiyalar) **faqat admin
panel orqali** boshqariladi — kodda katalog ma'lumoti yo'q va deploy uni hech
qachon o'zgartirmaydi. Ilgari bu ish `RUN_SEEDS=1` seed skriptlari bilan
qilinardi; ular adminkada qilingan tahrirlarni ustidan yozib, admin o'chirgan
dasturlarni qaytarib keltirgani uchun olib tashlandi (git tarixida bor).

Yo'llar:

- **Bittalab:** "Universitet qo'shish" sehrgari (universitet + dasturlari),
  "Grant qo'shish" sehrgari, "Yo'nalishlar" bo'limi.
- **Ommaviy:** "CSV import" sahifasi — davlatlar, universitetlar, dasturlar.
  Shablon CSV shu sahifadan yuklab olinadi. Import avval oldindan ko'rish
  beradi (bazaga hech narsa yozilmaydi), "Tasdiqlash"dan keyin bitta
  tranzaksiyada saqlaydi. Bo'sh katak mavjud qiymatni **o'zgartirmaydi**.
- **Zaxira:** o'sha sahifadagi "Eksport CSV" — xuddi shu formatda, ya'ni
  eksport qilingan fayllarni bo'sh bazaga qayta import qilish mumkin.

Railway'da `RUN_SEEDS` o'zgaruvchisi qolgan bo'lsa, u endi hech narsa qilmaydi.

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

## Deadline eslatmalari

Bot saqlangan dasturlarning muddati yaqinlashganda xabar yuboradi. Jadval
bot jarayonining ichida (`app/bot/main.py` → `reminder_loop`), alohida
servis yoki cron KERAK EMAS.

**Qachon:** har kuni Toshkent vaqti bilan **10:00**. Sikl har 30 daqiqada
uyg'onadi, lekin kuniga bir marta ishlaydi — Redis'dagi kunlik qulf
(`reminder_daily:<sana>`) ikkita konteyner bir kunda ikki marta
yubormasligini kafolatlaydi.

**Nechta xabar:** bitta saqlangan dastur uchun ko'pi bilan ikkita
(+ istisno holatda bitta "darhol" xabar). Dublikat nazorati
`notification_logs` jadvalida, unique (user, program, tur) bilan — ya'ni
kafolat bazada, kodda emas.

| Dasturdagi ma'lumot | Xabarlar |
|---|---|
| `deadlines` da ariza yopilish sanasi bor | 14 va 3 kun qolganda |
| faqat `programs.deadline_month` | oldingi oy boshi va o'sha oy boshi |
| hech narsa yo'q | saqlangandan 3 kun keyin bir marta |

**Sozlamalar:** alohida env o'zgaruvchi yo'q. Mavjud `BOT_TOKEN`,
`DATABASE_URL`, `REDIS_URL` va `WEBAPP_URL` yetarli (oxirgisi xabardagi
"Ilovada ochish" tugmasi uchun).

**Qo'lda ishga tushirish va tekshirish:**

```bash
# Hech narsa yubormaydi — faqat kimga nima ketishini ko'rsatadi
uv run python scripts/send_reminders.py --dry-run

# Boshqa kun nomidan (oy chegarasi, yil o'tishi kabi holatlarni sinash)
uv run python scripts/send_reminders.py --dry-run --date 2027-01-01

# Haqiqatan yuboradi (scheduler kunni o'tkazib yuborgan bo'lsa)
uv run python scripts/send_reminders.py
```

Prodakshenda: `railway ssh --service Uni-assist` orqali konteyner ichida.

**Foydalanuvchi tomoni:** Mini App → Profil → "Eslatmalar" tugmachasi
hammasini o'chiradi; saqlangan dastur kartasidagi "Eslatmani o'chirish"
esa faqat o'sha bitta dasturga ta'sir qiladi.

**Admin tomoni:** "Taklif qilingan sanalar" — foydalanuvchilar yuborgan
deadline sanalari. Tasdiqlansa sana `deadlines` jadvaliga yoziladi.
Boshqaruv panelida yuborilgan/bosilgan xabarlar statistikasi bor.

## Mentordan so'rash

Foydalanuvchi Mini App'dan (Saqlangan → «Shu davlatda o'qiyotganlardan
so'rash») savol beradi. Savol mentorlar forum-guruhidagi davlat topic'iga
tushadi, javob esa userga bot orqali **anonim** keladi. Mentorlar jadvali
yo'q: **guruh a'zoligining o'zi mentorlik huquqi**. Mentorni qo'shish va
chiqarishni Telegram'da qo'lda qilasiz.

**Guruhni sozlash (bir marta):**

1. Telegram'da yopiq guruh yarating → Guruh sozlamalari → **Topics (Mavzular)** ni yoqing.
2. Botni guruhga qo'shing va **administrator** qiling. Kerakli huquqlar:
   - **Mavzularni boshqarish** (`can_manage_topics`) — davlat topic'larini bot o'zi ochadi;
   - **Xabarlarni o'chirish** — eskirgan «javobni shu yerga yozing» xabarlarini tozalash uchun.
   Admin bo'lgan bot guruhdagi barcha xabarlarni ko'radi (privacy mode unga ta'sir qilmaydi).
3. Guruh ID'sini oling: kompyuterda <https://web.telegram.org/k/> ni oching va guruhga
   kiring — manzil satri `...#-1001234567890` bilan tugaydi, `#` dan keyingisi ID.
   (Forward qilish usuli ishlamaydi: u guruhni emas, xabar egasini ko'rsatadi.
   `getUpdates` ham ishlamaydi — bot ishlab turganda yangilanishlarni o'zi oladi.)
4. Railway → Variables (bo'sh qolsa funksiya o'chiq, ilovada tugma chiqmaydi):

   | O'zgaruvchi | Misol | Nima |
   |---|---|---|
   | `MENTOR_GROUP_ID` | `-1001234567890` | mentorlar guruhi |
   | `ADMIN_TELEGRAM_USERNAME` | `uniassist_admin` | «Mentor bo'lish» murojaati shu yerga |
   | `ADMIN_TELEGRAM_ID` | `123456789` | javobsiz savol (24 soat) va shikoyat haqida xabar |
   | `ACTIVE_COUNTRIES` | `DE,HU,KR,PL` | ISO kodlar, katalogdagi «Davlatlar» bilan mos bo'lishi kerak |
   | `QUESTION_MONTHLY_LIMIT` | `3` | bitta userning oylik savollari |
   | `FOLLOWUP_LIMIT` | `3` | bitta savolga qo'shimcha savollar |
   | `ALLOWED_LINK_DOMAINS` | `.de,.edu,.ac.uk,daad.de` | javobda ruxsat etilgan havolalar; `.de` — butun zona |

   `ADMIN_TELEGRAM_ID` egasi botga kamida bir marta `/start` bosgan bo'lishi kerak —
   aks holda Telegram unga xabar yuborishga ruxsat bermaydi.

**Qanday ishlaydi:**

- Davlat topic'i birinchi savol kelganda yaratiladi («🇩🇪 Germaniya»). Topic o'chirib
  yuborilsa, bot keyingi savolda uni qayta yaratadi.
- Mentor «✋ Javob berish» ni bosadi → bot unga ForceReply yuboradi → mentor
  **aynan shu xabarga reply qilib** javob yozadi. Boshqa xabarlar e'tiborsiz —
  mentorlar o'zaro gaplashishi mumkin.
- Javob qabul qilinmaydi: matn bo'lmasa, 50 belgidan qisqa bo'lsa, telefon,
  @username, `t.me` havolasi yoki ruxsatsiz domen bo'lsa (bot mentorga sababini aytadi).
- Har 30 daqiqada tekshiruv: 12 soat javobsiz biriktirish bekor bo'ladi; 24 soat
  javobsiz savol topic'da va adminga eslatiladi; 48 soatda userga «mentorlar band»
  deyiladi (bu savol oylik limitga sanalmaydi); javobdan 72 soat o'tib savol
  avtomatik yopiladi.
- Mentor guruhdan chiqsa yoki chiqarilsa, unga biriktirilgan savollar boshqa
  mentorlarga qayta ochiladi.

**Adminka → Mentordan so'rash:** «Savollar» (statistika, filtrlar, to'liq yozishma,
mentor ismi va ID'si faqat shu yerda, «Savolni yopish») va «Shikoyatlar».

**Tekshirish:** test guruh oching, o'zingizni (boshqa akkaunt bilan) a'zo qiling,
Mini App'dan savol bering → topic paydo bo'ladi → «Javob berish» → ForceReply'ga
50+ belgili javob yozing → savol bergan akkauntga bot xabari keladi.
