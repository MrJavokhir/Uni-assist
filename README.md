# Uni Assist

Telegram bot (@assistuni_bot) va Mini App: chet eldagi universitet dasturlari va grantlarini
topishga yordam beradi. Stack: aiogram 3, FastAPI + SQLAdmin, PostgreSQL (SQLAlchemy 2, Alembic),
Redis. Deploy tafsilotlari — [DEPLOY.md](DEPLOY.md).

## Deep link qoidalari

Har bir reklama, post yoki hamkor havolasi o'z **parametriga** ega. Parametr foydalanuvchi qayerdan
kelganini (atributsiya) va Mini App qaysi ekranda ochilishini belgilaydi.

### Ikki format

| Havola | Nima qiladi | Parametr qayerga keladi |
|---|---|---|
| `https://t.me/assistuni_bot?start=PARAM` | Bot chatini ochadi | `/start PARAM` |
| `https://t.me/assistuni_bot/<SHORT_NAME>?startapp=PARAM` | Mini App'ni darhol ochadi | imzolangan `initData` → `start_param` |

`<SHORT_NAME>` — BotFather `/newapp` da berilgan Mini App qisqa nomi, `MINIAPP_SHORT_NAME` env
o'zgaruvchisida saqlanadi. U bo'sh bo'lsa, generator faqat `?start=` havolasini beradi.

### Parametr qoidasi

`^[A-Za-z0-9_-]{1,64}$` — ko'pi bilan 64 belgi: lotin harflari, raqamlar, `_` va `-`. Qoidaga mos
kelmagan qiymat oqimni to'xtatmaydi: manba `invalid` bo'ladi va bosh sahifa ochiladi.

### Nomlash tizimi

| Prefiks | Misol | Ma'nosi | `first_source` |
|---|---|---|---|
| `ads_` | `ads_de_law_a` | Telegram Ads: kampaniya `de_law`, variant `a` | `ads` |
| `ch_` | `ch_post_1105` | o'zimizning kanal posti | `channel` |
| `tt_` / `ig_` / `yt_` | `tt_video_12` | TikTok / Instagram / YouTube | `tiktok` / `instagram` / `youtube` |
| `pt_` | `pt_ielts_samarqand` | hamkor (IELTS markazi, talaba klubi) | `partner` |
| `ref_` | `ref_84512` | Telegram ID'si 84512 bo'lgan user taklif qilgan | `referral` |
| `p_` | `p_123` | 123-dastur sahifasi | `share` |
| `g_` | `g_45` | 45-grant sahifasi | `share` |
| birikma | `p_123_r_84512` | 123-dastur, 84512 ulashgan | `share` |
| bo'sh | — | to'g'ridan-to'g'ri kirgan | `organic` |
| boshqa | `xyz` | noma'lum, xom qiymat saqlanadi | `unknown` |

Qo'shimcha ma'lumot:
- **Variant** — oxirgi segment, faqat bitta harf yoki raqam bo'lsa:
  - `ads_de_law_a` → kampaniya `de_law`, variant `a`;
  - `ads_de_law` va `ads_de_uk` — variantsiz kampaniyalar.

  Shuning uchun kampaniya nomining oxirgi qismi bitta belgidan iborat bo'lmasligi kerak: `post_1`
  `post` + variant `1` deb o'qiladi. Generator buni o'zi tekshiradi.
- **Referal ID'lari** Telegram ID bo'yicha. Eski `ref84512` formati (pastki chiziqsiz) ham ishlaydi.
- **`topup`** — ilova ichidagi xizmat payload'i (balans to'ldirish). Atributsiyaga kirmaydi.
- **Parser** — [app/services/deeplink.py](app/services/deeplink.py) (`parse_start_param`).

### Qaysi ekran ochiladi

- **Kampaniyalar** (`ads_`, `ch_`, `tt_`, `ig_`, `yt_`, `pt_`):
  - ekran `campaign_links` jadvalidan, havola generatori orqali o'rnatiladi;
  - bitta kampaniyaning barcha variantlari bir xil ekranni ochadi;
  - mapping topilmasa — bosh sahifa.
- **`p_<id>` / `g_<id>`:** dastur yoki grant sahifasi. U mavjud bo'lmasa — bosh sahifa.
- **`ref_`, bo'sh va noma'lum:** bosh sahifa (oddiy onboarding).
- **"Dasturlar ro'yxati" ekrani:** "Find my programs" kabi, avval majburiy kanal so'raladi.
- **Kanal tekshiruvi maqsadni yo'qotmaydi:**
  - maqsad 24 soatga saqlanadi (`users.pending_target`);
  - kanaldan o'tilgach ochiladi va o'chiriladi.
- **Reklamadagi filtr** (masalan, Germaniya + Huquq):
  - faqat vaqtinchalik ko'rinish, profildagi filtrni o'zgartirmaydi;
  - ekranda chip bo'lib turadi, ✕ bilan olib tashlanadi.

### Atributsiya

| Maydon | Qachon yoziladi |
|---|---|
| `first_source`, `first_param_raw`, `first_seen_at` | faqat birinchi kirishda, keyin o'zgarmaydi |
| `last_source` | har bir `/start` va `startapp` havolasi bilan kirishda |
| `referred_by_id` | faqat yangi userga, bir marta |

`referred_by_id` uchun mavjud referal tizimi ishlatiladi: mukofot kanalga a'zo bo'lgandan keyin
beriladi. O'zini o'zi taklif qilish va mavjud bo'lmagan referrer e'tiborga olinmaydi.

Bu tizimdan oldingi userlar `first_source = legacy` oladi va hisobotga kirmaydi.

### Yangi kampaniya uchun havola yaratish

1. **Admin → Manbalar → Havola generatori.**
2. **Formani to'ldiring:**
   - manba turi, masalan Telegram Ads;
   - kampaniya nomi, masalan `de_law`;
   - kerak bo'lsa variant (`a`, `b`);
   - ochiladigan ekran, masalan "Dasturlar ro'yxati" + Germaniya + Huquq.
3. **"Havola yaratish"ni bosing** va tayyor `?start=` yoki `?startapp=` havolasini nusxalang.
4. **Xarajatni kiriting:** Admin → Manbalar → Kampaniya xarajatlari. Kalit sifatida `ads_de_law`
   (kampaniya), `ads_de_law_a` (variant) yoki `ads` (butun manba) yoziladi. Valyuta USD/UZS/EUR,
   kurs (1 birlik = ? USD) qo'lda kiritiladi.
5. **Natijani kuzating:** Admin → Manbalar → Hisobot. Unda manba yoki kampaniya kesimida:
   - yangi userlar;
   - kanal, Mini App, filtr va saqlash foizlari;
   - D1, D7;
   - xarajat va 1 faol user narxi.

### Hodisalar (`events`)

| Hodisa | Qachon | Kim yozadi |
|---|---|---|
| `start` | har bir `/start` (yoki `startapp` bilan kirish) | server |
| `gate_shown` / `gate_passed` | kanal oynasi ko'rsatildi / o'tildi (bir marta) | server |
| `app_opened` | Mini App ochildi (kuniga ko'pi bilan bir marta) | server (`POST /api/webapp/entry`) |
| `filter_completed` | profilda daraja + yo'nalish + kamida 1 davlat birinchi marta (bir marta) | server |
| `save` / `first_save` | dastur saqlandi / birinchi saqlash (bir marta) | server |
| `program_viewed` / `grant_viewed` / `share_clicked` | sahifa ochildi / "Do'stga yuborish" bosildi | Mini App (`POST /api/webapp/events`) |

`POST /api/webapp/events` quyidagicha himoyalangan:
- initData imzosi tekshiriladi: noto'g'ri bo'lsa 401;
- `user_id` faqat initData'dan olinadi;
- faqat oq ro'yxatdagi nomlar qabul qilinadi;
- rate limit: 60 hodisa/daqiqa.

Shaxsiy ma'lumot (ism, telefon, xabar matni) saqlanmaydi.
