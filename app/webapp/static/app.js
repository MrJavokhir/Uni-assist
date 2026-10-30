const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try {
    // Sarlavha brend ko'k rangda; matn rangini Telegram fonga qarab o'zi tanlaydi.
    tg.setHeaderColor("#315cdf");
    tg.setBackgroundColor("secondary_bg_color");
  } catch (e) {
    /* older Telegram clients */
  }
  // Telegram'da pastga svayp ilovani yig'ib yuboradi. iOS'ning `<select>`
  // tanlagichida g'ildirakni aylantirish ham shunday svayp deb qabul
  // qilinardi: profil filtrida yo'nalish tanlamoqchi bo'lgan odam ilovadan
  // chiqib ketar, qayta ochilganda esa hammasi boshidan yuklanardi.
  // Bot API 7.7 dan oldingi klientlarda bu metod yo'q.
  try {
    tg.disableVerticalSwipes();
  } catch (e) {
    /* Bot API < 7.7 */
  }
}
const INIT_DATA = (tg && tg.initData) || "";

// iOS raqamli klaviaturasida "Done" tugmasi yo'q — foydalanuvchi uni yopa
// olmay, natija klaviatura ostida qolib ketardi. Shuning uchun maydondan
// tashqariga bosilganda yoki sahifa surilganda klaviatura yopiladi, Enter
// ham uni yopadi (Android klaviaturasida "Done" ko'rsatiladi).
const TEXT_FIELD = "input, textarea, select, [contenteditable='true']";

function isFieldFocused() {
  const active = document.activeElement;
  return !!(active && active.matches && active.matches("input, textarea"));
}

// Klaviatura qachon yopilgani. Varaq foni shu vaqtga qaraydi: agar bosish
// klaviaturani yopgan bo'lsa, o'sha bosish varaqni yopmasligi kerak.
let lastKeyboardDismissAt = 0;

function dismissKeyboard() {
  if (!isFieldFocused()) return;
  document.activeElement.blur();
  lastKeyboardDismissAt = Date.now();
}

function keyboardJustDismissed() {
  return Date.now() - lastKeyboardDismissAt < 400;
}

// Tugma/chip bosilganda klaviatura touchstart'da yopilsa, ekran siljib bosish
// boshqa joyga tushib qolishi mumkin — ular uchun bosish bajarilgach yopiladi.
const TAPPABLE = "button, a, label, .chip, .wz-opt, [role='button']";

document.addEventListener(
  "touchstart",
  (event) => {
    if (!event.target.closest(TEXT_FIELD) && !event.target.closest(TAPPABLE)) dismissKeyboard();
  },
  { passive: true }
);
document.addEventListener(
  "click",
  (event) => {
    if (event.target.closest(TAPPABLE) && !event.target.closest(TEXT_FIELD)) {
      setTimeout(dismissKeyboard, 0);
    }
  },
  true
);
document.addEventListener(
  "touchmove",
  (event) => {
    if (!event.target.closest(TEXT_FIELD)) dismissKeyboard();
  },
  { passive: true }
);
document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.matches && event.target.matches("input")) {
    event.preventDefault();
    event.target.blur();
  }
});
document.addEventListener("focusin", (event) => {
  const field = event.target;
  if (field.matches && field.matches("input") && !field.hasAttribute("enterkeyhint")) {
    field.setAttribute("enterkeyhint", "done");
  }
});
// Telegram statik fayllarni qattiq keshlaydi. Rasm/CSS/JS o'zgarganda bu raqam
// oshiriladi (index.html'dagi `?v=` bilan bir xil bo'lishi kerak).
const ASSET_V = 98;
const TG_USER = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || null;

function haptic(style) {
  try {
    if (!tg || !tg.HapticFeedback) return;
    if (style === "success" || style === "error" || style === "warning") {
      tg.HapticFeedback.notificationOccurred(style);
    } else {
      tg.HapticFeedback.impactOccurred(style || "light");
    }
  } catch (e) {
    /* haptics unsupported */
  }
}

function icon(name, cls) {
  return `<svg class="${cls || "ico"}"><use href="#i-${name}"/></svg>`;
}

function initials(text) {
  // Qavs/tinish belgilari bilan boshlanadigan so'zlar ("(Buyuk") initsialga
  // tushmasligi uchun faqat harf/raqamdan boshlanadigan so'zlarni olamiz.
  return (text || "")
    .split(/[\s(),.—-]+/)
    .filter((w) => /^[\p{L}\p{N}]/u.test(w))
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

// Bayroq — SVG rasm. Emoji bayroqlar Windows'da (Telegram Desktop) chizilmaydi
// va "UZ", "DE" kabi ikki harf bo'lib ko'rinardi.
const FLAG_BASE = "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/";

function flag(isoCode) {
  const code = String(isoCode || "").trim().toLowerCase();
  if (!/^[a-z]{2}$/.test(code)) return "";
  return `<img class="flag-img" src="${FLAG_BASE}${code}.svg" alt="${code.toUpperCase()}" loading="lazy">`;
}

function countryName(country) {
  return country["name_" + lang] || country.name_uz;
}

// Yo'nalish (`fields` ma'lumotnomasi) nomi foydalanuvchi tilida.
function fieldName(field) {
  return field ? field["name_" + lang] || field.name_uz : "";
}

// Bazada o'qitish tili KANONIK INGLIZCHA nom bilan saqlanadi ("English") —
// ro'yxat Python'dagi INSTRUCTION_LANGUAGES bilan bir xil bo'lishi kerak.
// Eski o'zbekcha qiymatlar (LANGUAGE_ALIASES) ham shu yerda o'giriladi.
// Ro'yxatda yo'q qiymat bo'lsa, o'zi qanday bo'lsa shunday ko'rsatiladi.
const LANGUAGE_NAMES = {
  English: { uz: "Ingliz tili", ru: "Английский", en: "English" },
  Russian: { uz: "Rus tili", ru: "Русский", en: "Russian" },
  German: { uz: "Nemis tili", ru: "Немецкий", en: "German" },
  French: { uz: "Fransuz tili", ru: "Французский", en: "French" },
  Korean: { uz: "Koreys tili", ru: "Корейский", en: "Korean" },
  Chinese: { uz: "Xitoy tili", ru: "Китайский", en: "Chinese" },
  Japanese: { uz: "Yapon tili", ru: "Японский", en: "Japanese" },
  Turkish: { uz: "Turk tili", ru: "Турецкий", en: "Turkish" },
  Italian: { uz: "Italyan tili", ru: "Итальянский", en: "Italian" },
  Polish: { uz: "Polyak tili", ru: "Польский", en: "Polish" },
  Czech: { uz: "Chex tili", ru: "Чешский", en: "Czech" },
  Hungarian: { uz: "Venger tili", ru: "Венгерский", en: "Hungarian" },
  Malay: { uz: "Malay tili", ru: "Малайский", en: "Malay" },
  Romanian: { uz: "Rumin tili", ru: "Румынский", en: "Romanian" },
  Dutch: { uz: "Golland tili", ru: "Нидерландский", en: "Dutch" },
  Norwegian: { uz: "Norveg tili", ru: "Норвежский", en: "Norwegian" },
};
const LANGUAGE_ALIASES = {
  "ingliz tili": "English",
  "rus tili": "Russian",
  "nemis tili": "German",
  "italyan tili": "Italian",
};

function instructionLanguage(value) {
  const raw = String(value || "").trim();
  const key = LANGUAGE_ALIASES[raw.toLowerCase()] || raw;
  const entry = LANGUAGE_NAMES[key];
  return entry ? entry[lang] || entry.uz : raw;
}

const DATE_LOCALES = { uz: "uz-Latn-UZ", ru: "ru-RU", en: "en-US" };

function shortDate(iso) {
  const d = new Date(`${iso}T00:00:00`);
  if (isNaN(d)) return escapeHtml(iso);
  // Brauzerlar o'zbekcha oy nomlarini bilmaydi ("M11 10" chiqardi) — o'zimiznikidan.
  if (lang === "uz") return `${d.getDate()}-${t("month." + (d.getMonth() + 1))}`;
  try {
    return d.toLocaleDateString(DATE_LOCALES[lang] || "en-US", { day: "numeric", month: "short" });
  } catch (e) {
    return escapeHtml(iso);
  }
}

function missingNote(fields) {
  if (!fields || !fields.length) return "";
  const names = fields.map((f) => t("program.missing." + f)).join(", ");
  return `<div class="sheet-note">${escapeHtml(t("program.missing_intro", { fields: names }))}</div>`;
}

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

const I18N = {
  uz: {
    "nav.home": "Bosh sahifa",
    "nav.match": "Dasturlar",
    "nav.scholarships": "Grantlar",
    "nav.saved": "Saqlangan",
    "nav.profile": "Profil",

    "home.stat_green": "Mos dasturlar",
    "home.stat_yellow": "Yaqin dasturlar",
    "home.stat_saved": "Saqlangan",
    "home.grants_title": "Muddati yaqin grantlar",
    "home.see_all": "Barchasi",
    "home.gs_left": "{n} kun qoldi",
    "home.gs_left_one": "1 kun qoldi",
    "home.gs_today": "Bugun oxirgi kun",
    "home.section_shortcuts": "Tezkor amallar",
    "nav.kit": "Admission Kit",
    "kit.title": "Admission Kit",
    "kit.back": "Bosh sahifa",
    "common.back": "Orqaga",
    "profile.no_name": "Foydalanuvchi",
    "account.balance": "Hisobim",
    "account.topup_hint": "To'ldirish botda: /topup buyrug'ini yozing",
    "profile.completeness": "profil {n}%",
    "account.topup_btn": "To'ldirish",
    "account.filter": "Qidiruv filtri",
    "account.filter_sub": "Daraja, yo'nalish, davlatlar, til",
    "account.language": "Til",
    "account.invite": "Do'stlarni taklif qilish",
    "account.invite_sub": "Har bir do'st uchun {bonus}",
    "account.invite_sub_plain": "Botni ulashing",
    "account.invite_count": "{count} ta do'st qo'shilgan · {bonus} har biri uchun",
    "account.invite_text": "Chet elda o'qish uchun dastur va grant qidiryapsizmi? Uni Assist yordam beradi.",
    "account.invite_unavailable": "Havolani olishning imkoni bo'lmadi",
    "account.help": "Yordam va FAQ",
    "account.feedback": "Fikr bildirish",
    "account.feedback_hint": "Taklif yoki muammo bo'lsa yozing — xabaringiz to'g'ridan-to'g'ri jamoaga boradi.",
    "account.feedback_placeholder": "Fikringizni yozing...",
    "account.feedback_send": "Yuborish",
    "account.feedback_sent": "Rahmat! Fikringiz yuborildi",
    "kit.need_balance": "Balans yetmaydi",
    "kit.need_balance_text": "Bu xizmat uchun {needed} kerak, hisobingizda {available} bor. Botda /topup yozib to'ldiring.",
    "faq.q1": "Dasturlar qayerdan olingan?",
    "faq.a1": "Har bir dastur universitetning rasmiy sahifasidan kiritilgan. Ko'rsatilmagan ma'lumot to'qilmaydi — bo'sh qoldiriladi.",
    "faq.q2": "Filtrni qanday sozlayman?",
    "faq.a2": "Bosh sahifadagi «Qidiruvni sozlash» (yoki «Filtrni to'ldirish») tugmasi yoki Profil → «Qidiruv filtri» orqali. Daraja, yo'nalish, baho va davlatlarni belgilasangiz, faqat sizga mos dasturlar qoladi.",
    "faq.q3": "Balansni qanday to'ldiraman?",
    "faq.a3": "Botga /topup yozing, summani kiriting va kartaga o'tkazing. So'ng /chekyubor orqali chek rasmini yuboring — admin tekshirgach balans to'ldiriladi.",
    "faq.q4": "Admission Kit nima?",
    "faq.a4": "Ariza topshirishda yordam beradigan qo'llanmalar va xizmatlar: motivatsion xat, CV, mentor bilan maslahat va to'liq yordam.",
    "error.title": "Ma'lumotni yuklab bo'lmadi",
    "kit.subtitle": "Ariza topshirishda yordam beradigan qo'llanmalar va xizmatlar.",
    "kit.price_ask": "Narx kelishiladi",
    "kit.request": "Buyurtma berish",
    "kit.requested": "So'rov yuborilgan",
    "kit.requested_toast": "So'rovingiz qabul qilindi — tez orada bog'lanamiz",
    "kit.empty_title": "Xizmatlar hali qo'shilmagan",
    "kit.empty_text": "Tez orada bu yerda qo'llanmalar va yordam xizmatlari paydo bo'ladi.",
    "kit.note": "Narx balansdan yechiladi. Balansni botda /topup buyrug'i bilan to'ldirasiz.",
    "kit.unlock_invites": "yoki {n} ta do'st taklif qiling",
    "kit.unlock_progress": "{have} / {need} ta do'st",
    "kit.unlock_free": "Bepul ochish",
    "kit.unlocked_free_toast": "Do'stlaringiz uchun bepul ochildi",
    "kit.locked": "Qulflangan",
    "kit.unlocked": "Ochilgan",
    "kit.buy": "Sotib olish",
    "kit.download": "PDF ni olish",
    "kit.sending": "Yuborilmoqda...",
    "kit.pdf_label": "PDF qo'llanma",
    "kit.pdf_locked_hint": "Sotib olingach, PDF shu zahoti botga yuboriladi.",
    "kit.pdf_open_hint": "Qo'llanma sizniki. Istagan vaqtda botga qayta yuborishingiz mumkin.",
    "kit.sent_title": "PDF yuborildi",
    "kit.sent_text": "Qo'llanma bot suhbatiga yuborildi — u yerda ochib, telefoningizga saqlashingiz mumkin.",
    "kit.sent_toast": "PDF botga yuborildi",
    "kit.open_bot": "Botni ochish",
    "kit.soon": "Tez orada",
    "kit.pdf_soon_hint": "Qo'llanma tayyorlanmoqda — tez orada ochiladi.",
    "kit.booked_title": "Yozildingiz",
    "kit.booked_text": "Uchrashuv vaqti: {slot}. Tez orada siz bilan bog'lanamiz.",
    "kit.minutes": "{count} daqiqa",
    "home.recap_title": "Mos dasturlar",
    "home.full_match": "To'liq mos",
    "home.recap_text": "Profilingizga mos keladigan barcha dasturlar — bir joyda.",
    "home.recap_cta": "Ko'rish",
    "home.gpa_tag": "4.0 · ECTS · UK",
    "home.shortcut_gpa": "GPA konvertor",
    "gpa.title": "GPA konvertor",
    "gpa.subtitle": "O'zbekiston bahosini AQSH, Buyuk Britaniya va Yevropa tizimlariga o'giradi",
    "gpa.scale": "Baholash tizimi",
    "gpa.value": "O'rtacha bahoingiz",
    "gpa.range": "{min} dan {max} gacha kiriting",
    "gpa.empty": "Bahoingizni kiriting — natija shu yerda chiqadi.",
    "gpa.results": "Natija",
    "gpa.us": "AQSH",
    "gpa.us_sub": "GPA, 4.0 shkala",
    "gpa.uk": "Buyuk Britaniya",
    "gpa.eu": "Yevropa",
    "gpa.eu_sub": "ECTS baho (A — eng yuqori)",
    "gpa.de": "Germaniya",
    "gpa.de_sub": "1.0 — eng yuqori, 4.0 — o'tish chegarasi",
    "gpa.uk_short.first": "First",
    "gpa.uk_short.upper_second": "2:1",
    "gpa.uk_short.lower_second": "2:2",
    "gpa.uk_short.third": "Third",
    "gpa.uk_short.below": "—",
    "gpa.uk_class.first": "Birinchi daraja (First Class)",
    "gpa.uk_class.upper_second": "Yuqori ikkinchi daraja (Upper Second)",
    "gpa.uk_class.lower_second": "Quyi ikkinchi daraja (Lower Second)",
    "gpa.uk_class.third": "Uchinchi daraja (Third Class)",
    "gpa.uk_class.below": "Diplom darajasidan past",
    "gpa.disclaimer": "Bu taxminiy hisob. Yakuniy bahoni universitet yoki tan olish idorasi (WES, UK ENIC, uni-assist) belgilaydi.",
    "profile.degree_level": "Daraja",
    "profile.degree_level.bachelor": "Bakalavr",
    "profile.degree_level.master": "Magistratura",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Yo'nalish",
    "profile.major_placeholder": "— yo'nalishni tanlang —",
    "profile.major_empty": "Katalogda hali yo'nalish yo'q.",
    "profile.gpa_scale.5": "5 balli",
    "profile.gpa_scale.100": "100 balli",
    "profile.gpa_scale.4": "4.0 GPA",
    "profile.study_language": "O'qish tili",
    "profile.study_language_any": "Farqi yo'q",
    "profile.countries": "Maqsad davlatlar",
    "profile.countries_all": "Barchasi",
    "profile.countries_count": "{n} ta davlat",
    "profile.rank": "Universitet reytingi",
    "profile.rank_any": "Farqi yo'q",
    "profile.app_fee": "Ariza to'lovi",
    "profile.reset": "Hammasini tozalash",
    "profile.reset_confirm": "Profildagi barcha tanlovlar o'chiriladi. Saqlangan dasturlarga tegilmaydi. Davom etamizmi?",
    "profile.reset_toast": "Profil tozalandi",
    "profile.find": "Mos dasturlarni topish",
    "finding.title": "Siz uchun mos dasturlar jamlanmoqda",
    "finding.step1": "Profil ma'lumotlari o'qilmoqda",
    "finding.step2": "Dasturlar talablaringiz bo'yicha solishtirilmoqda",
    "finding.step3": "Eng mos natijalar saralanmoqda",

    "match.filter_all": "Filtr",
    "match.empty_title": "Mos dastur topilmadi",
    "match.empty_text": "Profilingizni to'ldiring — shunda sizga mos dasturlarni topa olaman.",
    "match.no_filter_title": "Filtr hali qo'yilmagan",
    "match.no_filter_count": "Butun katalog: {n} ta dastur, sizga moslanmagan",
    "match.no_filter_cta": "Sozlash",
    "onboard.skip": "Keyinroq",
    "inquiry.country": "Qaysi davlat bo'yicha?",
    "inquiry.country_unsure": "Hali aniq emas",
    "inquiry.topics": "Nimada yordam kerak?",
    "inquiry.topic_placeholder": "Tanlang",
    "inquiry.contact": "Bog'lanish uchun raqam yoki Telegram username",
    "inquiry.need_contact": "Bog'lanish uchun raqam yoki username qoldiring",
    "inquiry.topic.university": "Universitet tanlash",
    "inquiry.topic.documents": "Hujjatlar",
    "inquiry.topic.essay": "Motivatsion xat / esse",
    "inquiry.topic.scholarship": "Grantlar",
    "inquiry.topic.visa": "Viza",
    "inquiry.topic.interview": "Suhbatga tayyorlov",
    "inquiry.topic.full": "To'liq ariza jarayoni",
    "inquiry.topic.other": "Boshqa",
    "inquiry.text": "Qo'shimcha izoh",
    "inquiry.text_placeholder": "Vaziyatingizni qisqacha yozing (ixtiyoriy)",
    "inquiry.send": "Yuborish",
    "inquiry.need_topic": "Nimada yordam kerakligini tanlang",
    "inquiry.sent": "So'rovingiz yuborildi — tez orada bog'lanamiz",
    "sub.step": "Oxirgi qadam",
    "sub.join": "Qo'shilish",
    "first.title": "Sizga eng mos dasturlar",
    "first.closes": "Muddat: {date}",
    "first.tba": "Muddat e'lon qilinmagan",
    "first.cta": "Barchasini ko'rish",
    "program.ask_mentor": "{country}dagi mentorga savol bering",
    "sub.title": "Natijalarni ko'rish uchun kanalga a'zo bo'ling",
    "sub.text": "Javoblaringiz saqlandi. Quyidagi kanal(lar)ga a'zo bo'lib, «A'zo bo'ldim» tugmasini bosing — mos dasturlar darhol chiqadi.",
    "sub.check": "A'zo bo'ldim",
    "sub.still_missing": "Hali hamma kanalga a'zo bo'lmadingiz",
    "program.opens": "Ochiladi",
    "program.closes": "Yopiladi",
    "program.left": "Qoldi",
    "program.days_n": "{n} kun",
    "wizard.tagline": "Grantlar, qabul va muddatlar — bir joyda.",
    "wizard.start": "Boshlash",
    "wizard.skip": "O'tkazish",
    "wizard.next": "Davom etish",
    "wizard.q.degree": "Qaysi darajada o'qimoqchisiz?",
    "wizard.q.field": "Qaysi yo'nalishda?",
    "wizard.q.countries": "Qayerda?",
    "wizard.hint.countries": "Bir nechtasini tanlashingiz mumkin",
    "wizard.q.language": "Qaysi tilda o'qimoqchisiz?",
    "wizard.q.english": "Ingliz tili darajangiz?",
    "wizard.cert_none": "Sertifikat yo'q",
    "wizard.score_ielts": "IELTS balingiz",
    "wizard.score_toefl": "TOEFL iBT balingiz (0–120)",
    "wizard.q.prefs": "Universitet reytingi muhimmi?",
    "match.save": "Saqlash",
    "match.search_placeholder": "Dastur, universitet yoki davlat",
    "match.search_empty": "Bu so'z bo'yicha dastur topilmadi",
    "match.sort.relevance": "Moslik",
    "match.sort.price": "Arzonroq",
    "match.sort.ranking": "Reyting",
    "match.sort.deadline": "Muddat yaqin",
    "match.saved": "Saqlangan",
    "match.missing": "Yetishmayapti: {list}",
    "match.green": "Mos",
    "match.yellow": "Yaqin",
    "match.saved_toast": "Dastur saqlandi",
    "match.details": "Batafsil",

    "program.about": "Dastur haqida",
    "program.field": "Yo'nalish",
    "program.language": "O'qitish tili",
    "program.intake": "Qabul davri",
    "program.years": "yil",
    "program.requirements": "Talablar",
    "program.requirements_docs": "Talablar va hujjatlar",
    "program.req_gre": "GRE talab qilinadi",
    "program.req_gre_score": "GRE: kamida {score}",
    "program.req_prereq": "Tayyorgarlik yo'nalishi: {major}",
    "program.ranking": "QS #{n}",
    "program.ranking_label": "Jahon reytingi (QS)",
    "program.language_certs": "Til sertifikati",
    "program.certs_either": "Ulardan biri yetarli.",
    "program.no_language_req": "Til sertifikati talab qilinmaydi.",
    "program.app_fee": "Ariza to'lovi",
    "program.app_fee_free": "Bepul",
    "program.app_fee_paid": "Bor (summasi ko'rsatilmagan)",
    "match.missing_key.ielts": "IELTS",
    "match.missing_key.toefl": "TOEFL",
    "match.missing_key.ielts_toefl": "IELTS yoki TOEFL",
    "program.gpa_min": "Min. GPA",
    "program.ielts_min": "Min. IELTS",
    "program.toefl_min": "Min. TOEFL",
    "program.no_requirements": "Talablar kiritilmagan.",
    "program.costs": "Xarajatlar",
    "program.tuition": "Kontrakt (yiliga)",
    "program.no_costs": "Xarajatlar kiritilmagan.",
    "program.cost_disclaimer": "Taxminiy raqamlar, oxirgi tekshiruv: {date}. Aniq summani universitet saytidan tasdiqlang.",
    "program.no_deadlines": "Muddatlar kiritilmagan.",
    "program.official_page": "Dastur sahifasiga o'tish",
    "program.verified_at": "Ma'lumot {date} sanasida tekshirilgan.",
    "program.own_scholarship": "Dastur stipendiyasi",
    "program.scholarship_title_yes": "Stipendiya mavjud",
    "program.scholarship_sub_link": "Shartlari va ariza tartibi — rasmiy sahifada",
    "program.scholarship_sub_nolink": "Shartlarini universitet sahifasidan aniqlang",
    "program.scholarship_title_no": "Alohida stipendiya yo'q",
    "program.scholarship_sub_no": "Davlat grantlarini ko'ring",
    "document.degree_certificate": "Diplom nusxasi",
    "document.transcript": "Baholar varaqasi (transcript)",
    "document.translation": "Hujjatlarning rasmiy tarjimasi",
    "document.reference": "Tavsiyanoma",
    "document.english_test": "Ingliz tili sertifikati",
    "document.passport": "Pasport nusxasi",
    "document.personal_statement": "Motivatsion xat",
    "document.cv": "CV",
    "document.research_proposal": "Tadqiqot rejasi",
    "document.portfolio": "Portfolio (ishlar to'plami)",
    "program.missing_intro": "Rasmiy sahifada ko'rsatilmagani uchun bo'sh: {fields}.",
    "program.missing.tuition": "kontrakt narxi",
    "program.missing.language_score": "IELTS/TOEFL bali",
    "program.missing.deadline": "ariza muddati",
    "program.missing.living_cost": "yashash xarajati",

    "scholarships.empty_title": "Grant topilmadi",
    "scholarships.empty_text": "Hozircha bazada davlat stipendiyalari yo'q yoki tanlangan davlat bo'yicha topilmadi.",
    "scholarships.all_countries": "Barcha davlatlar",
    "scholarships.coverage.full": "To'liq qoplaydi",
    "scholarships.coverage.partial": "Qisman qoplaydi",
    "scholarships.coverage.contract_only": "Faqat kontrakt",
    "scholarships.extra_flight": "Aviachipta",
    "scholarships.extra_insurance": "Sug'urta",
    "scholarships.extra_dormitory": "Yotoqxona",
    "scholarships.extra_language": "Til kursi",
    "scholarships.deadline": "Muddat: {date}",
    "scholarships.closed_badge": "Qabul yopilgan",
    "scholarships.details": "Batafsil",
    "scholarships.official_site": "Rasmiy saytga o'tish",
    "scholarships.about": "Grant haqida",
    "scholarships.money": "Moliyaviy qo'llab-quvvatlash",
    "scholarships.study": "O'qish",
    "scholarships.requirements": "Talablar",
    "scholarships.req_language": "Til sertifikati: {score}",
    "scholarships.req_work": "Kamida {years} yil ish tajribasi",
    "scholarships.req_no_work": "Ish tajribasi talab qilinmaydi",
    "scholarships.req_age": "Yosh chegarasi: {age} yosh",
    "scholarships.req_stages": "Tanlov {n} bosqichdan iborat",
    "scholarships.req_separate": "Universitetga alohida ariza topshiriladi",
    "scholarships.req_one_application": "Bitta ariza — universitet ham, grant ham",
    "scholarships.req_citizenship_ok": "O'zbekiston fuqarolari ariza bera oladi",
    "scholarships.req_citizenship_no": "O'zbekiston fuqarolari uchun ochiq emas",
    "scholarships.no_requirements": "Talablar kiritilmagan.",
    "scholarships.degree_levels": "Qaysi darajaga",
    "scholarships.duration": "Muddati",
    "scholarships.per_month": "oyiga",
    "scholarships.per_year": "yiliga",
    "scholarships.verify_hint": "Talablar har yili o'zgarishi mumkin — ariza berishdan oldin rasmiy saytdan tasdiqlang.",
    "scholarships.conditions": "Shartlar",
    "scholarships.deadlines": "Muddatlar",
    "scholarships.covers": "Qamrov",
    "scholarships.stipend": "Stipendiya",
    "scholarships.uni_choice": "Universitetni kim tanlaydi",
    "scholarships.universities": "Qaysi universitetda",
    "scholarships.selected_by": "Kim tanlaydi",
    "scholarships.uni_choice.user_chooses": "Talabaning o'zi",
    "scholarships.uni_choice.assigned_by_scholarship": "Grant tayinlaydi",
    "scholarships.yes": "Ha",
    "scholarships.no": "Yo'q",
    "scholarships.not_specified": "Ko'rsatilmagan",
    "scholarships.days_left": "{days} kun qoldi",
    "scholarships.deadline_passed": "Muddat o'tgan",
    "deadline.application_open": "Ariza ochilishi",
    "deadline.application_close": "Ariza yopilishi",
    "deadline.document": "Hujjat topshirish",
    "deadline.visa": "Viza",

    "saved.empty_title": "Hozircha bo'sh",
    "saved.empty_text": "Dasturlar bo'limidan yoqqanini saqlang — men muddatlarini kuzatib boraman.",
    "saved.deadline": "Muddat",
    "saved.no_deadline": "ko'rsatilmagan",
    "saved.days_left": "{days} kun qoldi",
    "saved.remove": "Olib tashlash",
    "saved.month_hint": "Odatda {month}da yopiladi",
    "saved.unknown_hint": "Deadline noma'lum — rasmiy saytni tekshiring",
    "saved.urgent": "{n} ta shoshilinch",
    "saved.closed_section": "Yopilgan",
    "saved.tag_applied": "Ariza berilgan",
    "saved.tag_muted": "Eslatma o'chiq",
    "saved.btn_site": "Rasmiy sayt",
    "saved.btn_mute": "Eslatmani o'chirish",
    "saved.btn_unmute": "Eslatmani yoqish",
    "saved.unmuted_toast": "Eslatma qayta yoqildi",
    "saved.btn_suggest": "Sanani bilaman",
    "saved.btn_suggested": "Taklif yuborilgan",
    "saved.muted_toast": "Bu dastur bo'yicha eslatmalar o'chirildi",
    "saved.notif_off_title": "Eslatmalar o'chirilgan",
    "saved.notif_off_text": "Deadline yaqinlashganda bot sizga xabar yubormaydi.",
    "saved.notif_on_btn": "Yoqish",
    "profile.notifications": "Eslatmalar",
    "profile.notif_hint": "Saqlangan dasturlar deadline'i yaqinlashganda bot sizga xabar yuboradi.",
    "profile.notif_on_toast": "Eslatmalar yoqildi",
    "profile.notif_off_toast": "Eslatmalar o'chirildi",
    "suggest.title": "Deadline sanasini bilasizmi?",
    "suggest.text": "Sanani yuboring — tekshirgandan keyin uni katalogga qo'shamiz va boshqa talabalar ham ko'radi.",
    "suggest.date_label": "Ariza yopilish sanasi",
    "suggest.send": "Yuborish",
    "suggest.thanks": "Rahmat! Taklifingiz tekshiruvga yuborildi.",
    "month.1": "yanvar",
    "month.2": "fevral",
    "month.3": "mart",
    "month.4": "aprel",
    "month.5": "may",
    "month.6": "iyun",
    "month.7": "iyul",
    "month.8": "avgust",
    "month.9": "sentyabr",
    "month.10": "oktyabr",
    "month.11": "noyabr",
    "month.12": "dekabr",
    "saved.removed_toast": "O'chirildi",
    "common.undo": "Bekor qilish",
    "saved.status.planning": "Rejada",
    "saved.status.applied": "Topshirdim",
    "saved.status.rejected": "Rad etildi",
    "saved.status.accepted": "Qabul",
    "mentor.my_questions": "Mening savollarim",
    "buddy.home_quota": "Bu oy: {left} / {n}",
    "buddy.tagline": "Xorijda o'qiyotgan o'zbek talabalar savolingizga javob beradi.",
    "mentor.new_question": "Yangi savol",
    "mentor.empty_title": "Hali savol bermagansiz",
    "mentor.empty_text": "Tanlagan davlatingizda o'qiyotgan talabalardan kirish, viza, yashash va boshqa mavzularda so'rang.",
    "mentor.choose_country": "Davlatni tanlang",
    "mentor.choose_country_sub": "Savolingiz shu davlatda o'qiyotgan mentorlarga boradi.",
    "mentor.quota": "Bu oy yana {left} ta savol bera olasiz ({n} tadan).",
    "mentor.limit_title": "Bu oy uchun savollar limiti tugadi",
    "mentor.limit_text": "Har oy {n} ta savol berish mumkin. Keyingi oy yana so'rashingiz mumkin.",
    "mentor.level": "Daraja",
    "mentor.level.bachelor": "Bakalavr",
    "mentor.level.master": "Magistratura",
    "mentor.level.phd": "PhD",
    "mentor.topic": "Mavzu",
    "mentor.topic.admission": "Kirish",
    "mentor.topic.documents": "Hujjatlar",
    "mentor.topic.visa": "Viza",
    "mentor.topic.living": "Yashash va xarajatlar",
    "mentor.topic.work": "Ish",
    "mentor.topic.studies": "O'qish jarayoni",
    "mentor.topic.other": "Boshqa",
    "mentor.text": "Savolingiz",
    "mentor.text_placeholder": "Savolingizni batafsil yozing: nimani bilmoqchisiz, qaysi bosqichdasiz...",
    "mentor.count_min": "{len} / kamida {min} belgi",
    "mentor.count": "{len} / {max}",
    "mentor.privacy_warning": "Shaxsiy ma'lumot (telefon, username, hujjat) yozmang.",
    "mentor.send": "Savolni yuborish",
    "mentor.sent_notice": "Savolingiz {country}dagi mentorlarga yuborildi. Odatda 24 soat ichida javob beriladi.",
    "mentor.waiting": "Mentor javobi kutilmoqda. Javob kelganda bot xabar beradi.",
    "mentor.mentor_label": "{country}dagi mentor",
    "mentor.status.open": "Kutilmoqda",
    "mentor.status.claimed": "Javob yozilmoqda",
    "mentor.status.answered": "Javob berildi",
    "mentor.status.closed": "Yopildi",
    "mentor.followup_label": "Qo'shimcha savol (yana {left} ta)",
    "mentor.followup_placeholder": "Aniqlashtirmoqchi bo'lgan narsangizni yozing",
    "mentor.followup_send": "Yuborish",
    "mentor.followup_sent": "Qo'shimcha savol yuborildi",
    "mentor.followup_limit": "Bu savol bo'yicha qo'shimcha savollar limiti tugadi.",
    "mentor.close_btn": "✅ Javob oldim",
    "mentor.complain_btn": "⚠️ Shikoyat",
    "mentor.report_short": "Shikoyat",
    "mentor.rate_title": "Mentor javobini baholang",
    "mentor.rate_thanks": "Rahmat! Bahoyingiz qabul qilindi",
    "mentor.rated": "Bahoyingiz: {stars}",
    "mentor.complain_title": "Shikoyat",
    "mentor.complain_sub": "Sababni tanlang. Shikoyat faqat adminga ko'rinadi.",
    "mentor.complain_comment": "Izoh (ixtiyoriy)",
    "mentor.complain_send": "Yuborish",
    "mentor.complain_sent": "Shikoyatingiz adminga yuborildi",
    "mentor.reason.wrong_info": "Noto'g'ri ma'lumot",
    "mentor.reason.disrespect": "Hurmatsiz muomala",
    "mentor.reason.paid_or_ad": "Pullik xizmat yoki reklama",
    "mentor.reason.other": "Boshqa",
    "mentor.become_row": "Mentor bo'lish",
    "mentor.apply_text": "Uni Assistda Mentor bo'lmoqchiman",
    "mentor.become_row_sub": "Xorijda o'qiyotgan bo'lsangiz",
    "mentor.err.generic": "Xatolik yuz berdi, qayta urinib ko'ring",
    "mentor.err.disabled": "Bu imkoniyat hozircha mavjud emas",
    "mentor.err.monthly_limit": "Bu oy uchun savollar limiti tugadi",
    "mentor.err.text_too_short": "Savol juda qisqa — biroz batafsilroq yozing",
    "mentor.err.text_too_long": "Savol juda uzun",
    "mentor.err.country_inactive": "Bu davlat bo'yicha hozircha savol qabul qilinmaydi",
    "mentor.err.followup_limit": "Qo'shimcha savollar limiti tugadi",
    "mentor.err.followup_not_allowed": "Hozir qo'shimcha savol yuborib bo'lmaydi",
    "mentor.err.send_failed": "Savol yuborilmadi, birozdan keyin qayta urinib ko'ring",
    "mentor.err.choose_all": "Daraja va mavzuni tanlang",
    "mentor.err.choose_reason": "Sababni tanlang",
    "mentor.err.not_found": "Savol topilmadi",
  },
  ru: {
    "nav.home": "Главная",
    "nav.match": "Программы",
    "nav.scholarships": "Гранты",
    "nav.saved": "Сохранённые",
    "nav.profile": "Профиль",

    "home.stat_green": "Подходящие",
    "home.stat_yellow": "Почти подходят",
    "home.stat_saved": "Сохранённые",
    "home.grants_title": "Скоро закрываются",
    "home.see_all": "Все",
    "home.gs_left": "осталось {n} дн.",
    "home.gs_left_one": "остался 1 день",
    "home.gs_today": "Последний день",
    "home.section_shortcuts": "Быстрые действия",
    "nav.kit": "Admission Kit",
    "kit.title": "Admission Kit",
    "kit.back": "На главную",
    "common.back": "Назад",
    "profile.no_name": "Пользователь",
    "account.balance": "Мой счёт",
    "account.topup_hint": "Пополнение в боте: отправьте команду /topup",
    "profile.completeness": "профиль {n}%",
    "account.topup_btn": "Пополнить",
    "account.filter": "Фильтр поиска",
    "account.filter_sub": "Ступень, направление, страны, язык",
    "account.language": "Язык",
    "account.invite": "Пригласить друзей",
    "account.invite_sub": "{bonus} за каждого друга",
    "account.invite_sub_plain": "Поделитесь ботом",
    "account.invite_count": "друзей: {count} · {bonus} за каждого",
    "account.invite_text": "Ищете программу или грант для учёбы за рубежом? Uni Assist поможет.",
    "account.invite_unavailable": "Не удалось получить ссылку",
    "account.help": "Помощь и FAQ",
    "account.feedback": "Оставить отзыв",
    "account.feedback_hint": "Напишите предложение или проблему — сообщение придёт напрямую команде.",
    "account.feedback_placeholder": "Напишите ваше мнение...",
    "account.feedback_send": "Отправить",
    "account.feedback_sent": "Спасибо! Отзыв отправлен",
    "kit.need_balance": "Недостаточно средств",
    "kit.need_balance_text": "Для этой услуги нужно {needed}, на счету {available}. Пополните через /topup в боте.",
    "faq.q1": "Откуда взяты программы?",
    "faq.a1": "Каждая программа внесена с официальной страницы университета. Неуказанные данные не выдумываются — поле остаётся пустым.",
    "faq.q2": "Как настроить фильтр?",
    "faq.a2": "Через кнопку «Настроить поиск» (или «Дополнить фильтр») на главной либо Профиль → «Фильтр поиска». Укажите ступень, направление, балл и страны — останутся только подходящие программы.",
    "faq.q3": "Как пополнить счёт?",
    "faq.a3": "Отправьте боту /topup, укажите сумму и переведите на карту. Затем через /chekyubor отправьте фото чека — после проверки баланс пополнится.",
    "faq.q4": "Что такое Admission Kit?",
    "faq.a4": "Руководства и услуги для подачи заявки: мотивационное письмо, CV, консультация с ментором и полное сопровождение.",
    "error.title": "Не удалось загрузить данные",
    "kit.subtitle": "Руководства и услуги, которые помогут с подачей заявки.",
    "kit.price_ask": "Цена по договорённости",
    "kit.request": "Оставить заявку",
    "kit.requested": "Заявка отправлена",
    "kit.requested_toast": "Заявка принята — скоро свяжемся с вами",
    "kit.empty_title": "Услуги пока не добавлены",
    "kit.empty_text": "Скоро здесь появятся руководства и услуги поддержки.",
    "kit.note": "Стоимость списывается с баланса. Пополнить — командой /topup в боте.",
    "kit.unlock_invites": "или пригласите {n} друзей",
    "kit.unlock_progress": "{have} / {need} друзей",
    "kit.unlock_free": "Открыть бесплатно",
    "kit.unlocked_free_toast": "Открыто бесплатно — за приглашённых друзей",
    "kit.locked": "Закрыто",
    "kit.unlocked": "Открыто",
    "kit.buy": "Купить",
    "kit.download": "Получить PDF",
    "kit.sending": "Отправляем...",
    "kit.pdf_label": "PDF-руководство",
    "kit.pdf_locked_hint": "После покупки PDF сразу придёт в бот.",
    "kit.pdf_open_hint": "Руководство ваше. Можно отправить в бот ещё раз в любой момент.",
    "kit.sent_title": "PDF отправлен",
    "kit.sent_text": "Руководство отправлено в чат с ботом — там его можно открыть и сохранить на телефон.",
    "kit.sent_toast": "PDF отправлен в бот",
    "kit.open_bot": "Открыть бот",
    "kit.soon": "Скоро",
    "kit.pdf_soon_hint": "Руководство готовится — скоро будет доступно.",
    "kit.booked_title": "Вы записаны",
    "kit.booked_text": "Время встречи: {slot}. Скоро свяжемся с вами.",
    "kit.minutes": "{count} мин",
    "home.recap_title": "Подходящие программы",
    "home.full_match": "Полное совпадение",
    "home.recap_text": "Все программы, подходящие вашему профилю, — в одном месте.",
    "home.recap_cta": "Смотреть",
    "home.gpa_tag": "4.0 · ECTS · UK",
    "home.shortcut_gpa": "Конвертер GPA",
    "gpa.title": "Конвертер GPA",
    "gpa.subtitle": "Переводит узбекскую оценку в системы США, Великобритании и Европы",
    "gpa.scale": "Система оценок",
    "gpa.value": "Ваш средний балл",
    "gpa.range": "Введите значение от {min} до {max}",
    "gpa.empty": "Введите средний балл — результат появится здесь.",
    "gpa.results": "Результат",
    "gpa.us": "США",
    "gpa.us_sub": "GPA, шкала 4.0",
    "gpa.uk": "Великобритания",
    "gpa.eu": "Европа",
    "gpa.eu_sub": "Оценка ECTS (A — высшая)",
    "gpa.de": "Германия",
    "gpa.de_sub": "1.0 — высшая, 4.0 — проходной порог",
    "gpa.uk_short.first": "First",
    "gpa.uk_short.upper_second": "2:1",
    "gpa.uk_short.lower_second": "2:2",
    "gpa.uk_short.third": "Third",
    "gpa.uk_short.below": "—",
    "gpa.uk_class.first": "Диплом первой степени (First Class)",
    "gpa.uk_class.upper_second": "Высшая вторая степень (Upper Second)",
    "gpa.uk_class.lower_second": "Низшая вторая степень (Lower Second)",
    "gpa.uk_class.third": "Третья степень (Third Class)",
    "gpa.uk_class.below": "Ниже уровня диплома",
    "gpa.disclaimer": "Это приблизительный расчёт. Итоговую оценку определяет университет или служба признания (WES, UK ENIC, uni-assist).",
    "profile.degree_level": "Степень",
    "profile.degree_level.bachelor": "Бакалавриат",
    "profile.degree_level.master": "Магистратура",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Направление",
    "profile.major_placeholder": "— выберите направление —",
    "profile.major_empty": "В каталоге пока нет направлений.",
    "profile.gpa_scale.5": "5-балльная",
    "profile.gpa_scale.100": "100-балльная",
    "profile.gpa_scale.4": "4.0 GPA",
    "profile.study_language": "Язык обучения",
    "profile.study_language_any": "Не важно",
    "profile.countries": "Целевые страны",
    "profile.countries_count": "Стран: {n}",
    "profile.rank": "Рейтинг университета",
    "profile.rank_any": "Не важно",
    "profile.app_fee": "Плата за подачу заявки",
    "profile.countries_all": "Все страны",
    "profile.reset": "Очистить всё",
    "profile.reset_confirm": "Все данные профиля будут удалены. Сохранённые программы не тронем. Продолжить?",
    "profile.reset_toast": "Профиль очищен",
    "profile.find": "Подобрать программы",
    "finding.title": "Подбираем подходящие вам программы",
    "finding.step1": "Читаем данные профиля",
    "finding.step2": "Сравниваем программы с вашими параметрами",
    "finding.step3": "Отбираем самые подходящие результаты",

    "match.filter_all": "Фильтр",
    "match.empty_title": "Программы не найдены",
    "match.empty_text": "Заполните профиль — и я подберу подходящие программы.",
    "match.no_filter_title": "Фильтр ещё не настроен",
    "match.no_filter_count": "Весь каталог: {n} программ, без подбора под вас",
    "match.no_filter_cta": "Настроить",
    "onboard.skip": "Позже",
    "inquiry.country": "По какой стране?",
    "inquiry.country_unsure": "Пока не знаю",
    "inquiry.topics": "С чем нужна помощь?",
    "inquiry.topic_placeholder": "Выберите",
    "inquiry.contact": "Телефон или Telegram username для связи",
    "inquiry.need_contact": "Оставьте телефон или username для связи",
    "inquiry.topic.university": "Выбор университета",
    "inquiry.topic.documents": "Документы",
    "inquiry.topic.essay": "Мотивационное письмо / эссе",
    "inquiry.topic.scholarship": "Гранты",
    "inquiry.topic.visa": "Виза",
    "inquiry.topic.interview": "Подготовка к интервью",
    "inquiry.topic.full": "Весь процесс поступления",
    "inquiry.topic.other": "Другое",
    "inquiry.text": "Комментарий",
    "inquiry.text_placeholder": "Кратко опишите ситуацию (необязательно)",
    "inquiry.send": "Отправить",
    "inquiry.need_topic": "Выберите, с чем нужна помощь",
    "inquiry.sent": "Заявка отправлена — скоро свяжемся",
    "sub.step": "Последний шаг",
    "sub.join": "Подписаться",
    "first.title": "Ваши первые совпадения",
    "first.closes": "До {date}",
    "first.tba": "Срок не объявлен",
    "first.cta": "Смотреть все",
    "program.ask_mentor": "Спросите ментора: {country}",
    "sub.title": "Подпишитесь на канал, чтобы увидеть результаты",
    "sub.text": "Ответы сохранены. Подпишитесь на канал(ы) ниже и нажмите «Я подписался» — подходящие программы появятся сразу.",
    "sub.check": "Я подписался",
    "sub.still_missing": "Вы подписались ещё не на все каналы",
    "program.opens": "Открытие",
    "program.closes": "Закрытие",
    "program.left": "Осталось",
    "program.days_n": "{n} дн.",
    "wizard.tagline": "Гранты, поступление и дедлайны — в одном месте.",
    "wizard.start": "Начать",
    "wizard.skip": "Пропустить",
    "wizard.next": "Продолжить",
    "wizard.q.degree": "Куда хотите поступить?",
    "wizard.q.field": "Какое направление?",
    "wizard.q.countries": "Где?",
    "wizard.hint.countries": "Можно выбрать несколько",
    "wizard.q.language": "На каком языке учиться?",
    "wizard.q.english": "Ваш уровень английского?",
    "wizard.cert_none": "Нет сертификата",
    "wizard.score_ielts": "Ваш балл IELTS",
    "wizard.score_toefl": "Ваш балл TOEFL iBT (0–120)",
    "wizard.q.prefs": "Важен ли рейтинг университета?",
    "match.save": "Сохранить",
    "match.search_placeholder": "Программа, университет или страна",
    "match.search_empty": "По этому запросу программ нет",
    "match.sort.relevance": "Соответствие",
    "match.sort.price": "Дешевле",
    "match.sort.ranking": "Рейтинг",
    "match.sort.deadline": "Ближайший дедлайн",
    "match.saved": "Сохранено",
    "match.missing": "Не хватает: {list}",
    "match.green": "Подходит",
    "match.yellow": "Почти",
    "match.saved_toast": "Программа сохранена",
    "match.details": "Подробнее",

    "program.about": "О программе",
    "program.field": "Направление",
    "program.language": "Язык обучения",
    "program.intake": "Период набора",
    "program.years": "г.",
    "program.requirements": "Требования",
    "program.requirements_docs": "Требования и документы",
    "program.req_gre": "Требуется GRE",
    "program.req_gre_score": "GRE: не менее {score}",
    "program.req_prereq": "Профильное направление: {major}",
    "program.ranking": "QS #{n}",
    "program.ranking_label": "Мировой рейтинг (QS)",
    "program.language_certs": "Языковой сертификат",
    "program.certs_either": "Достаточно одного из них.",
    "program.no_language_req": "Языковой сертификат не требуется.",
    "program.app_fee": "Плата за подачу заявки",
    "program.app_fee_free": "Бесплатно",
    "program.app_fee_paid": "Есть (сумма не указана)",
    "match.missing_key.ielts": "IELTS",
    "match.missing_key.toefl": "TOEFL",
    "match.missing_key.ielts_toefl": "IELTS или TOEFL",
    "program.gpa_min": "Мин. GPA",
    "program.ielts_min": "Мин. IELTS",
    "program.toefl_min": "Мин. TOEFL",
    "program.no_requirements": "Требования не указаны.",
    "program.costs": "Расходы",
    "program.tuition": "Контракт (в год)",
    "program.no_costs": "Расходы не указаны.",
    "program.cost_disclaimer": "Приблизительные суммы, последняя проверка: {date}. Уточните на сайте университета.",
    "program.no_deadlines": "Сроки не указаны.",
    "program.official_page": "Открыть страницу программы",
    "program.verified_at": "Данные проверены {date}.",
    "program.own_scholarship": "Стипендия программы",
    "program.scholarship_title_yes": "Есть стипендия",
    "program.scholarship_sub_link": "Условия и порядок подачи — на официальной странице",
    "program.scholarship_sub_nolink": "Условия уточните на сайте университета",
    "program.scholarship_title_no": "Отдельной стипендии нет",
    "program.scholarship_sub_no": "Посмотрите государственные гранты",
    "document.degree_certificate": "Копия диплома",
    "document.transcript": "Транскрипт оценок",
    "document.translation": "Официальный перевод документов",
    "document.reference": "Рекомендательное письмо",
    "document.english_test": "Сертификат по английскому",
    "document.passport": "Копия паспорта",
    "document.personal_statement": "Мотивационное письмо",
    "document.cv": "Резюме (CV)",
    "document.research_proposal": "Исследовательское предложение",
    "document.portfolio": "Портфолио работ",
    "program.missing_intro": "Не указано на официальной странице: {fields}.",
    "program.missing.tuition": "стоимость обучения",
    "program.missing.language_score": "балл IELTS/TOEFL",
    "program.missing.deadline": "срок подачи",
    "program.missing.living_cost": "расходы на проживание",

    "scholarships.empty_title": "Гранты не найдены",
    "scholarships.empty_text": "Пока в базе нет государственных стипендий или по выбранной стране ничего не найдено.",
    "scholarships.all_countries": "Все страны",
    "scholarships.coverage.full": "Полное покрытие",
    "scholarships.coverage.partial": "Частичное покрытие",
    "scholarships.coverage.contract_only": "Только контракт",
    "scholarships.extra_flight": "Авиабилет",
    "scholarships.extra_insurance": "Страховка",
    "scholarships.extra_dormitory": "Общежитие",
    "scholarships.extra_language": "Языковой курс",
    "scholarships.deadline": "Дедлайн: {date}",
    "scholarships.closed_badge": "Приём закрыт",
    "scholarships.details": "Подробнее",
    "scholarships.official_site": "Перейти на официальный сайт",
    "scholarships.about": "О гранте",
    "scholarships.money": "Финансирование",
    "scholarships.study": "Обучение",
    "scholarships.requirements": "Требования",
    "scholarships.req_language": "Языковой сертификат: {score}",
    "scholarships.req_work": "Не менее {years} лет опыта работы",
    "scholarships.req_no_work": "Опыт работы не требуется",
    "scholarships.req_age": "Возрастное ограничение: {age} лет",
    "scholarships.req_stages": "Отбор состоит из {n} этапов",
    "scholarships.req_separate": "В университет подаётся отдельная заявка",
    "scholarships.req_one_application": "Одна заявка — и на университет, и на грант",
    "scholarships.req_citizenship_ok": "Граждане Узбекистана могут подавать заявку",
    "scholarships.req_citizenship_no": "Для граждан Узбекистана недоступна",
    "scholarships.no_requirements": "Требования не указаны.",
    "scholarships.degree_levels": "Для каких степеней",
    "scholarships.duration": "Длительность",
    "scholarships.per_month": "в месяц",
    "scholarships.per_year": "в год",
    "scholarships.verify_hint": "Требования могут меняться каждый год — перед подачей уточните на официальном сайте.",
    "scholarships.conditions": "Условия",
    "scholarships.deadlines": "Дедлайны",
    "scholarships.covers": "Покрытие",
    "scholarships.stipend": "Стипендия",
    "scholarships.uni_choice": "Кто выбирает университет",
    "scholarships.universities": "В каком университете",
    "scholarships.selected_by": "Кто отбирает",
    "scholarships.uni_choice.user_chooses": "Сам студент",
    "scholarships.uni_choice.assigned_by_scholarship": "Назначает грант",
    "scholarships.yes": "Да",
    "scholarships.no": "Нет",
    "scholarships.not_specified": "Не указано",
    "scholarships.days_left": "осталось {days} дн.",
    "scholarships.deadline_passed": "Срок прошёл",
    "deadline.application_open": "Открытие приёма",
    "deadline.application_close": "Закрытие приёма",
    "deadline.document": "Подача документов",
    "deadline.visa": "Виза",

    "saved.empty_title": "Пока пусто",
    "saved.empty_text": "Сохраните программы из раздела «Программы» — я буду следить за дедлайнами.",
    "saved.deadline": "Дедлайн",
    "saved.no_deadline": "не указан",
    "saved.days_left": "осталось {days} дн.",
    "saved.remove": "Убрать",
    "saved.month_hint": "Обычно закрывается в {month}",
    "saved.unknown_hint": "Дедлайн неизвестен — проверьте сайт",
    "saved.urgent": "Срочных: {n}",
    "saved.closed_section": "Закрытые",
    "saved.tag_applied": "Заявка подана",
    "saved.tag_muted": "Напоминания выкл.",
    "saved.btn_site": "Официальный сайт",
    "saved.btn_mute": "Отключить напоминание",
    "saved.btn_unmute": "Включить напоминание",
    "saved.unmuted_toast": "Напоминание включено",
    "saved.btn_suggest": "Я знаю дату",
    "saved.btn_suggested": "Предложение отправлено",
    "saved.muted_toast": "Напоминания по этой программе отключены",
    "saved.notif_off_title": "Напоминания отключены",
    "saved.notif_off_text": "Бот не напомнит о близком дедлайне.",
    "saved.notif_on_btn": "Включить",
    "profile.notifications": "Напоминания",
    "profile.notif_hint": "Бот напомнит, когда приблизится дедлайн сохранённых программ.",
    "profile.notif_on_toast": "Напоминания включены",
    "profile.notif_off_toast": "Напоминания отключены",
    "suggest.title": "Знаете дату дедлайна?",
    "suggest.text": "Отправьте дату — после проверки мы добавим её в каталог.",
    "suggest.date_label": "Дата закрытия приёма",
    "suggest.send": "Отправить",
    "suggest.thanks": "Спасибо! Предложение отправлено на проверку.",
    "month.1": "январе",
    "month.2": "феврале",
    "month.3": "марте",
    "month.4": "апреле",
    "month.5": "мае",
    "month.6": "июне",
    "month.7": "июле",
    "month.8": "августе",
    "month.9": "сентябре",
    "month.10": "октябре",
    "month.11": "ноябре",
    "month.12": "декабре",
    "saved.removed_toast": "Удалено",
    "common.undo": "Отменить",
    "saved.status.planning": "В планах",
    "saved.status.applied": "Подал",
    "saved.status.rejected": "Отказ",
    "saved.status.accepted": "Принят",
    "mentor.my_questions": "Мои вопросы",
    "buddy.home_quota": "В этом месяце: {left} / {n}",
    "buddy.tagline": "На ваши вопросы отвечают узбекские студенты, которые учатся за рубежом.",
    "mentor.new_question": "Новый вопрос",
    "mentor.empty_title": "Вы ещё не задавали вопросов",
    "mentor.empty_text": "Спросите студентов из выбранной страны о поступлении, визе, жизни и не только.",
    "mentor.choose_country": "Выберите страну",
    "mentor.choose_country_sub": "Вопрос получат менторы, которые учатся в этой стране.",
    "mentor.quota": "В этом месяце осталось вопросов: {left} из {n}.",
    "mentor.limit_title": "Лимит вопросов на этот месяц исчерпан",
    "mentor.limit_text": "В месяц можно задать {n} вопроса. В следующем месяце лимит обновится.",
    "mentor.level": "Уровень",
    "mentor.level.bachelor": "Бакалавриат",
    "mentor.level.master": "Магистратура",
    "mentor.level.phd": "Аспирантура (PhD)",
    "mentor.topic": "Тема",
    "mentor.topic.admission": "Поступление",
    "mentor.topic.documents": "Документы",
    "mentor.topic.visa": "Виза",
    "mentor.topic.living": "Жизнь и расходы",
    "mentor.topic.work": "Работа",
    "mentor.topic.studies": "Учёба",
    "mentor.topic.other": "Другое",
    "mentor.text": "Ваш вопрос",
    "mentor.text_placeholder": "Опишите подробно: что хотите узнать, на каком вы этапе...",
    "mentor.count_min": "{len} / минимум {min} символов",
    "mentor.count": "{len} / {max}",
    "mentor.privacy_warning": "Не пишите личные данные (телефон, username, документы).",
    "mentor.send": "Отправить вопрос",
    "mentor.sent_notice": "Вопрос отправлен менторам ({country}). Обычно отвечают в течение 24 часов.",
    "mentor.waiting": "Ждём ответа ментора. Бот сообщит, когда он придёт.",
    "mentor.mentor_label": "Ментор · {country}",
    "mentor.status.open": "Ожидает",
    "mentor.status.claimed": "Пишут ответ",
    "mentor.status.answered": "Есть ответ",
    "mentor.status.closed": "Закрыт",
    "mentor.followup_label": "Уточняющий вопрос (осталось {left})",
    "mentor.followup_placeholder": "Что хотите уточнить?",
    "mentor.followup_send": "Отправить",
    "mentor.followup_sent": "Уточнение отправлено",
    "mentor.followup_limit": "Лимит уточняющих вопросов по этому вопросу исчерпан.",
    "mentor.close_btn": "✅ Ответ получен",
    "mentor.complain_btn": "⚠️ Пожаловаться",
    "mentor.report_short": "Пожаловаться",
    "mentor.rate_title": "Оцените ответ ментора",
    "mentor.rate_thanks": "Спасибо за оценку!",
    "mentor.rated": "Ваша оценка: {stars}",
    "mentor.complain_title": "Жалоба",
    "mentor.complain_sub": "Выберите причину. Жалобу увидит только администратор.",
    "mentor.complain_comment": "Комментарий (необязательно)",
    "mentor.complain_send": "Отправить",
    "mentor.complain_sent": "Жалоба отправлена администратору",
    "mentor.reason.wrong_info": "Неверная информация",
    "mentor.reason.disrespect": "Неуважительное общение",
    "mentor.reason.paid_or_ad": "Платные услуги или реклама",
    "mentor.reason.other": "Другое",
    "mentor.become_row": "Стать ментором",
    "mentor.apply_text": "Хочу стать ментором в Uni Assist",
    "mentor.become_row_sub": "Если вы учитесь за рубежом",
    "mentor.err.generic": "Произошла ошибка, попробуйте ещё раз",
    "mentor.err.disabled": "Эта функция пока недоступна",
    "mentor.err.monthly_limit": "Лимит вопросов на этот месяц исчерпан",
    "mentor.err.text_too_short": "Вопрос слишком короткий — опишите подробнее",
    "mentor.err.text_too_long": "Вопрос слишком длинный",
    "mentor.err.country_inactive": "По этой стране вопросы пока не принимаются",
    "mentor.err.followup_limit": "Лимит уточняющих вопросов исчерпан",
    "mentor.err.followup_not_allowed": "Сейчас нельзя отправить уточнение",
    "mentor.err.send_failed": "Не удалось отправить, попробуйте чуть позже",
    "mentor.err.choose_all": "Выберите уровень и тему",
    "mentor.err.choose_reason": "Выберите причину",
    "mentor.err.not_found": "Вопрос не найден",
  },
  en: {
    "nav.home": "Home",
    "nav.match": "Programs",
    "nav.scholarships": "Grants",
    "nav.saved": "Saved",
    "nav.profile": "Profile",

    "home.stat_green": "Matching",
    "home.stat_yellow": "Close matches",
    "home.stat_saved": "Saved",
    "home.grants_title": "Closing soon",
    "home.see_all": "See all",
    "home.gs_left": "{n} days left",
    "home.gs_left_one": "1 day left",
    "home.gs_today": "Last day",
    "home.section_shortcuts": "Quick actions",
    "nav.kit": "Admission Kit",
    "kit.title": "Admission Kit",
    "kit.back": "Back to home",
    "common.back": "Back",
    "profile.no_name": "User",
    "account.balance": "My balance",
    "account.topup_hint": "Top up in the bot: send the /topup command",
    "profile.completeness": "profile {n}%",
    "account.topup_btn": "Top up",
    "account.filter": "Search filter",
    "account.filter_sub": "Degree, field, countries, language",
    "account.language": "Language",
    "account.invite": "Invite friends",
    "account.invite_sub": "{bonus} for every friend",
    "account.invite_sub_plain": "Share the bot",
    "account.invite_count": "{count} friends joined · {bonus} each",
    "account.invite_text": "Looking for a programme or scholarship to study abroad? Uni Assist helps.",
    "account.invite_unavailable": "Could not get the link",
    "account.help": "Help & FAQ",
    "account.feedback": "Send feedback",
    "account.feedback_hint": "Tell us a suggestion or a problem — it goes straight to the team.",
    "account.feedback_placeholder": "Write your feedback...",
    "account.feedback_send": "Send",
    "account.feedback_sent": "Thank you! Your feedback was sent",
    "kit.need_balance": "Not enough balance",
    "kit.need_balance_text": "This service costs {needed}, your balance is {available}. Top up with /topup in the bot.",
    "faq.q1": "Where does the programme data come from?",
    "faq.a1": "Every programme is entered from the university's official page. Anything not stated there is left empty rather than guessed.",
    "faq.q2": "How do I set up the filter?",
    "faq.a2": "Tap «Set up your search» (or «Refine your filter») on the home screen, or open Profile → «Search filter». Once you set degree, field, grade and countries, only matching programmes remain.",
    "faq.q3": "How do I top up my balance?",
    "faq.a3": "Send /topup to the bot, enter the amount and transfer to the card. Then send the receipt photo via the /chekyubor (“send receipt”) command — the balance is credited after review.",
    "faq.q4": "What is the Admission Kit?",
    "faq.a4": "Guides and services for your application: motivation letter, CV, mentor sessions and full support.",
    "error.title": "Could not load the data",
    "kit.subtitle": "Guides and services that help you through the application.",
    "kit.price_ask": "Price on request",
    "kit.request": "Request",
    "kit.requested": "Request sent",
    "kit.requested_toast": "Request received — we will contact you shortly",
    "kit.empty_title": "No services yet",
    "kit.empty_text": "Guides and support services will appear here soon.",
    "kit.note": "The price comes from your balance. Top it up with /topup in the bot.",
    "kit.unlock_invites": "or invite {n} friends",
    "kit.unlock_progress": "{have} / {need} friends",
    "kit.unlock_free": "Unlock for free",
    "kit.unlocked_free_toast": "Unlocked for free — thanks to your invites",
    "kit.locked": "Locked",
    "kit.unlocked": "Unlocked",
    "kit.buy": "Buy",
    "kit.download": "Get the PDF",
    "kit.sending": "Sending...",
    "kit.pdf_label": "PDF guide",
    "kit.pdf_locked_hint": "Once bought, the PDF is sent to the bot right away.",
    "kit.pdf_open_hint": "The guide is yours. You can have it sent to the bot again any time.",
    "kit.sent_title": "PDF sent",
    "kit.sent_text": "The guide was sent to your chat with the bot — open it there and save it to your phone.",
    "kit.sent_toast": "PDF sent to the bot",
    "kit.open_bot": "Open the bot",
    "kit.soon": "Coming soon",
    "kit.pdf_soon_hint": "The guide is being prepared — it will open soon.",
    "kit.booked_title": "You are booked",
    "kit.booked_text": "Meeting time: {slot}. We will contact you shortly.",
    "kit.minutes": "{count} min",
    "home.recap_title": "Your matches",
    "home.full_match": "Full match",
    "home.recap_text": "Every programme that fits your profile, in one place.",
    "home.recap_cta": "Explore",
    "home.gpa_tag": "4.0 · ECTS · UK",
    "home.shortcut_gpa": "GPA converter",
    "gpa.title": "GPA converter",
    "gpa.subtitle": "Converts an Uzbek grade to the US, UK and European systems",
    "gpa.scale": "Grading system",
    "gpa.value": "Your average grade",
    "gpa.range": "Enter a value from {min} to {max}",
    "gpa.empty": "Enter your grade — the result will appear here.",
    "gpa.results": "Result",
    "gpa.us": "United States",
    "gpa.us_sub": "GPA, 4.0 scale",
    "gpa.uk": "United Kingdom",
    "gpa.eu": "Europe",
    "gpa.eu_sub": "ECTS grade (A is highest)",
    "gpa.de": "Germany",
    "gpa.de_sub": "1.0 is highest, 4.0 is the pass mark",
    "gpa.uk_short.first": "First",
    "gpa.uk_short.upper_second": "2:1",
    "gpa.uk_short.lower_second": "2:2",
    "gpa.uk_short.third": "Third",
    "gpa.uk_short.below": "—",
    "gpa.uk_class.first": "First Class Honours",
    "gpa.uk_class.upper_second": "Upper Second Class (2:1)",
    "gpa.uk_class.lower_second": "Lower Second Class (2:2)",
    "gpa.uk_class.third": "Third Class Honours",
    "gpa.uk_class.below": "Below honours level",
    "gpa.disclaimer": "This is an estimate. The final grade is set by the university or a recognition body (WES, UK ENIC, uni-assist).",
    "profile.degree_level": "Degree",
    "profile.degree_level.bachelor": "Bachelor's",
    "profile.degree_level.master": "Master's",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Major",
    "profile.major_placeholder": "— select a field —",
    "profile.major_empty": "No fields in the catalog yet.",
    "profile.gpa_scale.5": "5-point",
    "profile.gpa_scale.100": "100-point",
    "profile.gpa_scale.4": "4.0 GPA",
    "profile.study_language": "Language of study",
    "profile.study_language_any": "Any",
    "profile.countries": "Target countries",
    "profile.countries_count": "{n} countries",
    "profile.rank": "University ranking",
    "profile.rank_any": "Any",
    "profile.app_fee": "Application fee",
    "profile.countries_all": "All countries",
    "profile.reset": "Reset everything",
    "profile.reset_confirm": "All profile choices will be cleared. Saved programs stay untouched. Continue?",
    "profile.reset_toast": "Profile cleared",
    "profile.find": "Find my programs",
    "finding.title": "Finding programs that fit you",
    "finding.step1": "Reading your profile",
    "finding.step2": "Comparing programs against your requirements",
    "finding.step3": "Ranking the closest matches",

    "match.filter_all": "Filter",
    "match.empty_title": "No programs found",
    "match.empty_text": "Fill in your profile and I'll find programs that fit you.",
    "match.no_filter_title": "No filter set yet",
    "match.no_filter_count": "Whole catalogue: {n} programmes, not matched to you",
    "match.no_filter_cta": "Set up",
    "onboard.skip": "Later",
    "inquiry.country": "Which country?",
    "inquiry.country_unsure": "Not sure yet",
    "inquiry.topics": "What do you need help with?",
    "inquiry.topic_placeholder": "Choose one",
    "inquiry.contact": "Phone number or Telegram username",
    "inquiry.need_contact": "Leave a phone number or username so we can reach you",
    "inquiry.topic.university": "Choosing a university",
    "inquiry.topic.documents": "Documents",
    "inquiry.topic.essay": "Motivation letter / essay",
    "inquiry.topic.scholarship": "Scholarships",
    "inquiry.topic.visa": "Visa",
    "inquiry.topic.interview": "Interview prep",
    "inquiry.topic.full": "The whole application",
    "inquiry.topic.other": "Something else",
    "inquiry.text": "Anything to add?",
    "inquiry.text_placeholder": "Briefly describe your situation (optional)",
    "inquiry.send": "Send",
    "inquiry.need_topic": "Choose what you need help with",
    "inquiry.sent": "Request sent — we'll be in touch soon",
    "sub.step": "One last step",
    "sub.join": "Join",
    "first.title": "Your first matches",
    "first.closes": "Closes {date}",
    "first.tba": "Not announced",
    "first.cta": "Start exploring",
    "program.ask_mentor": "Ask a mentor in {country}",
    "sub.title": "Join the channel to see your results",
    "sub.text": "Your answers are saved. Join the channel(s) below and tap “I've joined” — matching programmes will show up right away.",
    "sub.check": "I've joined",
    "sub.still_missing": "You haven't joined all the channels yet",
    "program.opens": "Opens",
    "program.closes": "Closes",
    "program.left": "Left",
    "program.days_n": "{n} days",
    "wizard.tagline": "Scholarships, admissions and deadlines — in one place.",
    "wizard.start": "Get started",
    "wizard.skip": "Skip",
    "wizard.next": "Continue",
    "wizard.q.degree": "What do you want to study?",
    "wizard.q.field": "Which field?",
    "wizard.q.countries": "Where?",
    "wizard.hint.countries": "You can pick several",
    "wizard.q.language": "Language of instruction?",
    "wizard.q.english": "Your English level?",
    "wizard.cert_none": "No certificate",
    "wizard.score_ielts": "Your IELTS score",
    "wizard.score_toefl": "Your TOEFL iBT score (0–120)",
    "wizard.q.prefs": "Does university ranking matter?",
    "match.save": "Save",
    "match.search_placeholder": "Programme, university or country",
    "match.search_empty": "No programmes match this search",
    "match.sort.relevance": "Best match",
    "match.sort.price": "Cheapest",
    "match.sort.ranking": "Ranking",
    "match.sort.deadline": "Deadline soon",
    "match.saved": "Saved",
    "match.missing": "Missing: {list}",
    "match.green": "Match",
    "match.yellow": "Close",
    "match.saved_toast": "Program saved",
    "match.details": "Details",

    "program.about": "About the program",
    "program.field": "Field",
    "program.language": "Language of instruction",
    "program.intake": "Intake",
    "program.years": "yr",
    "program.requirements": "Requirements",
    "program.requirements_docs": "Requirements & documents",
    "program.req_gre": "GRE is required",
    "program.req_gre_score": "GRE: at least {score}",
    "program.req_prereq": "Prior field of study: {major}",
    "program.ranking": "QS #{n}",
    "program.ranking_label": "World ranking (QS)",
    "program.language_certs": "Language certificate",
    "program.certs_either": "Either one is accepted.",
    "program.no_language_req": "No language certificate required.",
    "program.app_fee": "Application fee",
    "program.app_fee_free": "Free",
    "program.app_fee_paid": "Required (amount not listed)",
    "match.missing_key.ielts": "IELTS",
    "match.missing_key.toefl": "TOEFL",
    "match.missing_key.ielts_toefl": "IELTS or TOEFL",
    "program.gpa_min": "Min. GPA",
    "program.ielts_min": "Min. IELTS",
    "program.toefl_min": "Min. TOEFL",
    "program.no_requirements": "No requirements recorded.",
    "program.costs": "Costs",
    "program.tuition": "Tuition (per year)",
    "program.no_costs": "No costs recorded.",
    "program.cost_disclaimer": "Approximate figures, last checked {date}. Confirm on the university site.",
    "program.no_deadlines": "No deadlines recorded.",
    "program.official_page": "Open program page",
    "program.verified_at": "Data verified on {date}.",
    "program.own_scholarship": "Programme scholarship",
    "program.scholarship_title_yes": "Scholarship available",
    "program.scholarship_sub_link": "Terms and how to apply — on the official page",
    "program.scholarship_sub_nolink": "Check the terms on the university website",
    "program.scholarship_title_no": "No dedicated scholarship",
    "program.scholarship_sub_no": "Browse government grants",
    "document.degree_certificate": "Degree certificate",
    "document.transcript": "Academic transcript",
    "document.translation": "Certified translations",
    "document.reference": "Reference letter",
    "document.english_test": "English language certificate",
    "document.passport": "Passport copy",
    "document.personal_statement": "Personal statement",
    "document.cv": "CV",
    "document.research_proposal": "Research proposal",
    "document.portfolio": "Portfolio of work",
    "program.missing_intro": "Not stated on the official page: {fields}.",
    "program.missing.tuition": "tuition fee",
    "program.missing.language_score": "IELTS/TOEFL score",
    "program.missing.deadline": "application deadline",
    "program.missing.living_cost": "living costs",

    "scholarships.empty_title": "No grants found",
    "scholarships.empty_text": "There are no government scholarships in the database yet, or none for the selected country.",
    "scholarships.all_countries": "All countries",
    "scholarships.coverage.full": "Full coverage",
    "scholarships.coverage.partial": "Partial coverage",
    "scholarships.coverage.contract_only": "Tuition only",
    "scholarships.extra_flight": "Flight",
    "scholarships.extra_insurance": "Insurance",
    "scholarships.extra_dormitory": "Dormitory",
    "scholarships.extra_language": "Language course",
    "scholarships.deadline": "Deadline: {date}",
    "scholarships.closed_badge": "Applications closed",
    "scholarships.details": "Details",
    "scholarships.official_site": "Open official website",
    "scholarships.about": "About this grant",
    "scholarships.money": "Funding",
    "scholarships.study": "Study",
    "scholarships.requirements": "Requirements",
    "scholarships.req_language": "Language certificate: {score}",
    "scholarships.req_work": "At least {years} years of work experience",
    "scholarships.req_no_work": "No work experience required",
    "scholarships.req_age": "Age limit: {age}",
    "scholarships.req_stages": "Selection has {n} stages",
    "scholarships.req_separate": "A separate university application is required",
    "scholarships.req_one_application": "One application covers both the place and the grant",
    "scholarships.req_citizenship_ok": "Open to citizens of Uzbekistan",
    "scholarships.req_citizenship_no": "Not open to citizens of Uzbekistan",
    "scholarships.no_requirements": "No requirements listed.",
    "scholarships.degree_levels": "Degree levels",
    "scholarships.duration": "Duration",
    "scholarships.per_month": "per month",
    "scholarships.per_year": "per year",
    "scholarships.verify_hint": "Requirements can change each year — confirm on the official site before applying.",
    "scholarships.conditions": "Conditions",
    "scholarships.deadlines": "Deadlines",
    "scholarships.covers": "Coverage",
    "scholarships.stipend": "Stipend",
    "scholarships.uni_choice": "Who picks the university",
    "scholarships.universities": "Where you study",
    "scholarships.selected_by": "Who selects",
    "scholarships.uni_choice.user_chooses": "The student",
    "scholarships.uni_choice.assigned_by_scholarship": "The scholarship",
    "scholarships.yes": "Yes",
    "scholarships.no": "No",
    "scholarships.not_specified": "Not specified",
    "scholarships.days_left": "{days} day(s) left",
    "scholarships.deadline_passed": "Deadline passed",
    "deadline.application_open": "Applications open",
    "deadline.application_close": "Applications close",
    "deadline.document": "Document submission",
    "deadline.visa": "Visa",

    "saved.empty_title": "Nothing here yet",
    "saved.empty_text": "Save programs from the Programs tab — I'll track their deadlines for you.",
    "saved.deadline": "Deadline",
    "saved.no_deadline": "not set",
    "saved.days_left": "{days} day(s) left",
    "saved.remove": "Remove",
    "saved.month_hint": "Usually closes in {month}",
    "saved.unknown_hint": "Deadline unknown — check the official site",
    "saved.urgent": "{n} urgent",
    "saved.closed_section": "Closed",
    "saved.tag_applied": "Applied",
    "saved.tag_muted": "Reminders off",
    "saved.btn_site": "Official site",
    "saved.btn_mute": "Mute reminders",
    "saved.btn_unmute": "Turn reminders on",
    "saved.unmuted_toast": "Reminders are back on",
    "saved.btn_suggest": "I know the date",
    "saved.btn_suggested": "Suggestion sent",
    "saved.muted_toast": "Reminders for this programme are off",
    "saved.notif_off_title": "Reminders are off",
    "saved.notif_off_text": "The bot will not message you when a deadline approaches.",
    "saved.notif_on_btn": "Turn on",
    "profile.notifications": "Reminders",
    "profile.notif_hint": "The bot messages you when a saved programme's deadline approaches.",
    "profile.notif_on_toast": "Reminders on",
    "profile.notif_off_toast": "Reminders off",
    "suggest.title": "Do you know the deadline?",
    "suggest.text": "Send the date — we add it to the catalogue after checking.",
    "suggest.date_label": "Application closing date",
    "suggest.send": "Send",
    "suggest.thanks": "Thank you! Your suggestion is queued for review.",
    "month.1": "January",
    "month.2": "February",
    "month.3": "March",
    "month.4": "April",
    "month.5": "May",
    "month.6": "June",
    "month.7": "July",
    "month.8": "August",
    "month.9": "September",
    "month.10": "October",
    "month.11": "November",
    "month.12": "December",
    "saved.removed_toast": "Removed",
    "common.undo": "Undo",
    "saved.status.planning": "Planning",
    "saved.status.applied": "Applied",
    "saved.status.rejected": "Rejected",
    "saved.status.accepted": "Accepted",
    "mentor.my_questions": "My questions",
    "buddy.home_quota": "This month: {left} / {n}",
    "buddy.tagline": "Uzbek students studying abroad answer your questions.",
    "mentor.new_question": "New question",
    "mentor.empty_title": "No questions yet",
    "mentor.empty_text": "Ask students in your chosen country about admission, visas, living costs and more.",
    "mentor.choose_country": "Choose a country",
    "mentor.choose_country_sub": "Your question goes to mentors studying in that country.",
    "mentor.quota": "You can ask {left} more question(s) this month (out of {n}).",
    "mentor.limit_title": "You've used this month's questions",
    "mentor.limit_text": "You can ask {n} questions per month. The limit resets next month.",
    "mentor.level": "Level",
    "mentor.level.bachelor": "Bachelor's",
    "mentor.level.master": "Master's",
    "mentor.level.phd": "PhD",
    "mentor.topic": "Topic",
    "mentor.topic.admission": "Admission",
    "mentor.topic.documents": "Documents",
    "mentor.topic.visa": "Visa",
    "mentor.topic.living": "Living & costs",
    "mentor.topic.work": "Work",
    "mentor.topic.studies": "Studies",
    "mentor.topic.other": "Other",
    "mentor.text": "Your question",
    "mentor.text_placeholder": "Describe it in detail: what you want to know, where you are in the process...",
    "mentor.count_min": "{len} / at least {min} characters",
    "mentor.count": "{len} / {max}",
    "mentor.privacy_warning": "Don't include personal details (phone, username, documents).",
    "mentor.send": "Send question",
    "mentor.sent_notice": "Your question was sent to mentors in {country}. Answers usually arrive within 24 hours.",
    "mentor.waiting": "Waiting for a mentor. The bot will notify you when the answer arrives.",
    "mentor.mentor_label": "Mentor in {country}",
    "mentor.status.open": "Waiting",
    "mentor.status.claimed": "Being answered",
    "mentor.status.answered": "Answered",
    "mentor.status.closed": "Closed",
    "mentor.followup_label": "Follow-up question ({left} left)",
    "mentor.followup_placeholder": "What would you like to clarify?",
    "mentor.followup_send": "Send",
    "mentor.followup_sent": "Follow-up sent",
    "mentor.followup_limit": "You've used all follow-up questions for this question.",
    "mentor.close_btn": "✅ Got my answer",
    "mentor.complain_btn": "⚠️ Report",
    "mentor.report_short": "Report",
    "mentor.rate_title": "Rate the mentor's answer",
    "mentor.rate_thanks": "Thanks for your rating!",
    "mentor.rated": "Your rating: {stars}",
    "mentor.complain_title": "Report",
    "mentor.complain_sub": "Choose a reason. Only the admin will see your report.",
    "mentor.complain_comment": "Comment (optional)",
    "mentor.complain_send": "Send",
    "mentor.complain_sent": "Your report was sent to the admin",
    "mentor.reason.wrong_info": "Wrong information",
    "mentor.reason.disrespect": "Disrespectful",
    "mentor.reason.paid_or_ad": "Paid services or advertising",
    "mentor.reason.other": "Other",
    "mentor.become_row": "Become a mentor",
    "mentor.apply_text": "I'd like to become a mentor on Uni Assist",
    "mentor.become_row_sub": "If you study abroad",
    "mentor.err.generic": "Something went wrong, please try again",
    "mentor.err.disabled": "This feature isn't available yet",
    "mentor.err.monthly_limit": "You've used this month's questions",
    "mentor.err.text_too_short": "Your question is too short — please add more detail",
    "mentor.err.text_too_long": "Your question is too long",
    "mentor.err.country_inactive": "Questions for this country aren't accepted yet",
    "mentor.err.followup_limit": "No follow-up questions left",
    "mentor.err.followup_not_allowed": "You can't send a follow-up right now",
    "mentor.err.send_failed": "Couldn't send, please try again shortly",
    "mentor.err.choose_all": "Choose a level and topic",
    "mentor.err.choose_reason": "Choose a reason",
    "mentor.err.not_found": "Question not found",
  },
};

let lang = (TG_USER && TG_USER.language_code) || "uz";
if (!I18N[lang]) lang = "uz";

function t(key, vars) {
  const s = (I18N[lang] && I18N[lang][key]) || I18N.uz[key] || key;
  if (!vars) return s;
  return Object.entries(vars).reduce((acc, [k, v]) => acc.replaceAll(`{${k}}`, v), s);
}

async function api(path, opts) {
  opts = opts || {};
  const res = await fetch(`/api/webapp${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": INIT_DATA,
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function showToast(message) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  if (el._commit) el._commit();
  el.innerHTML = `${icon("check")}<span>${escapeHtml(message)}</span>`;
  el.classList.remove("has-action");
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 1900);
}

/** Bekor qilish tugmali toast. `onUndo` bosilsa chaqiriladi, `onCommit` —
 *  vaqt tugaganda (ya'ni amal haqiqatan bajariladi). */
function showUndoToast(message, onUndo, onCommit, ms = 5000) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  // Oldingi kutilayotgan amal darhol bajariladi — ikkita toast ustma-ust
  // turmasin va birinchisi "yo'qolib" qolmasin.
  if (el._commit) el._commit();
  clearTimeout(el._timer);

  let done = false;
  const commit = () => {
    if (done) return;
    done = true;
    el._commit = null;
    onCommit();
  };
  el._commit = commit;
  el.innerHTML = `<span>${escapeHtml(message)}</span><button type="button" class="toast-undo">${t(
    "common.undo"
  )}</button>`;
  el.classList.add("show", "has-action");
  el.querySelector(".toast-undo").addEventListener("click", () => {
    if (done) return;
    done = true;
    el._commit = null;
    clearTimeout(el._timer);
    el.classList.remove("show", "has-action");
    haptic("light");
    onUndo();
  });
  el._timer = setTimeout(() => {
    el.classList.remove("show", "has-action");
    commit();
  }, ms);
}

function skeletons(count, short) {
  return Array.from({ length: count }, () => `<div class="skeleton${short ? " short" : ""}"></div>`).join("");
}

let profile = null;
let countries = [];
// Yashirinlari ham — faqat grantlar filtri uchun (hukumat grantlari).
let allCountries = [];
let majors = [];
// Katalogda haqiqatan uchraydigan o'qish tillari (kanonik inglizcha
// nomlar). Nomlarni `instructionLanguage()` foydalanuvchi tiliga o'giradi.
let studyLanguages = [];

async function loadProfile() {
  profile = await api("/me");
  lang = profile.ui_language || lang;
}

async function loadCountries() {
  allCountries = await api("/countries");
  countries = allCountries.filter((c) => !c.hidden);
}

async function loadStudyLanguages() {
  // Ro'yxat bo'sh qolsa filtrda faqat "Farqi yo'q" ko'rinadi — bu
  // bo'sh tanlovlar ko'rsatishdan yaxshiroq.
  try {
    studyLanguages = await api("/languages");
  } catch (e) {
    studyLanguages = [];
  }
}

async function loadMajors(degreeLevel) {
  const level = degreeLevel === undefined ? profile && profile.degree_level : degreeLevel;
  majors = await api("/majors" + (level ? `?degree_level=${encodeURIComponent(level)}` : ""));
}

// Qidiruvni chegaralaydigan maydonlar. `hasFilter()` ham, to'ldirilganlik
// foizi ham AYNAN shu ro'yxatdan hisoblanadi.
//
// Ilgari ikkisi alohida yozilgan edi va o'qish tili faqat `hasFilter()` ga
// qo'shilgandi. Natijada faqat tilni tanlagan odam "0% to'ldirilgan" degan
// yozuvni ko'rardi, ilova esa filtr qo'yilgan holatda ishlardi: na foiz
// to'g'ri edi, na "filtrni sozlang" taklifi chiqardi.
function filterFields() {
  if (!profile) return [];
  return [
    !!profile.degree_level,
    !!profile.field_id,
    !!profile.study_language,
    (profile.target_country_ids || []).length > 0,
  ];
}

// Hech biri tanlanmagan bo'lsa `find_matches` hamma dasturni qaytaradi —
// ularni "sizga mos" deb ko'rsatish yangi foydalanuvchini chalg'itadi.
function hasFilter() {
  return filterFields().some(Boolean);
}

function profileCompleteness() {
  const checks = [
    ...filterFields(),
    profile.language_certificates.length > 0,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

// ============ Home ============

async function renderHome() {
  const el = document.getElementById("view-home");
  const ready = hasFilter();

  // Tepada filtr kartasi (profil foizi + halqa) turardi. Filtr endi
  // onboarding'da majburiy sozlanadi, shuning uchun uning o'rnida muddati
  // yaqin hukumat grantlari aylanib turadi.
  el.innerHTML = `
    <div id="home-grants">
      <div class="section-head">
        <span class="section-title">${t("home.grants_title")}</span>
      </div>
      <div class="gs-track"><div class="gs-card gs-skeleton"></div><div class="gs-card gs-skeleton"></div></div>
    </div>

    <div class="hx-grid">
      <div class="hx-recap" data-goto="kit" role="button" tabindex="0">
        <div class="hx-recap-title">${t("kit.title")}</div>
        <div class="hx-recap-text">${t("kit.subtitle")}</div>
        <div class="hx-recap-art">
          <img src="icon-kit.png?v=${ASSET_V}" alt="" aria-hidden="true">
        </div>
        <span class="hx-recap-cta">${t("home.recap_cta")}</span>
      </div>

      <div class="hx-side">
        <div class="hx-mini hx-buddy" id="home-gpa" role="button" tabindex="0">
          <div class="hx-mini-head">
            <span class="hx-mini-label">${t("home.shortcut_gpa")}</span>
          </div>
          <div class="hx-buddy-art">
            <img src="icon-gpa.png?v=${ASSET_V}" alt="" aria-hidden="true">
          </div>
          <div class="hx-mini-foot"><span class="hx-tag">${t("home.gpa_tag")}</span></div>
        </div>
        ${buddyHomeCard()}
      </div>
    </div>

    <div class="section-head"><span class="section-title">${t("home.section_shortcuts")}</span></div>
    <div class="quick-grid">
      <button type="button" class="quick accent" data-goto="match">
        <img class="quick-ico" src="icon-programs.png?v=${ASSET_V}" alt="" aria-hidden="true">
        <span class="quick-label">${t("nav.match")}</span>
      </button>
      <button type="button" class="quick amber" data-goto="scholarships">
        <img class="quick-ico" src="icon-grants.png?v=${ASSET_V}" alt="" aria-hidden="true">
        <span class="quick-label">${t("nav.scholarships")}</span>
      </button>
      <button type="button" class="quick green" data-goto="match">
        <span class="quick-num" id="home-green-value">—</span>
        <span class="quick-label">${t("home.full_match")}</span>
      </button>
    </div>
  `;

  renderHomeGrants();
  document.getElementById("home-buddy")?.addEventListener("click", openBuddy);
  document.getElementById("home-gpa").addEventListener("click", openGpaPage);

  // Tezkor amallar o'z ishlov beruvchisiga ega — ular bu yerga tushmaydi.
  el.querySelectorAll("[data-goto]:not(.quick)").forEach((node) => {
    node.addEventListener("click", () => {
      haptic("light");
      switchTab(node.dataset.goto);
    });
  });

  el.querySelectorAll(".quick").forEach((card) => {
    card.addEventListener("click", () => {
      haptic("light");
      switchTab(card.dataset.goto);
    });
  });

  const matches = await api("/match");
  const green = matches.filter((m) => m.level === "green").length;
  document.getElementById("home-green-value").textContent = ready ? green : "—";
}

// ---- Home: muddati yaqin grantlar karuseli ----
//
// Ochiq (muddati o'tmagan) grantlar eng yaqin muddat bo'yicha. Kartalar
// o'zi chapga aylanib turadi; foydalanuvchi barmog'i bilan sursa, bir
// muddat to'xtab turadi.

const HOME_GRANTS_LIMIT = 8;
const GRANT_ROTATE_MS = 4500;
let homeGrantsTimer = null;

function grantDaysLeft(days) {
  if (days === 0) return t("home.gs_today");
  if (days === 1) return t("home.gs_left_one");
  return t("home.gs_left", { n: days });
}

function grantSlide(s) {
  const days = s.nearest_deadline_days_left;
  const tone = days <= 7 ? "red" : days <= 30 ? "amber" : "blue";
  const first = s.countries[0];
  const place = !first
    ? ""
    : s.countries.length > 1
    ? t("profile.countries_count", { n: s.countries.length })
    : countryName(first);
  // Rasm yuklanmagan grant: davlat bayrog'idan xira fon, o'rtada logotip.
  const flagCode = first ? String(first.iso_code).toLowerCase() : "";
  const cover = s.cover_url
    ? `<img class="gs-img" src="${escapeHtml(s.cover_url)}" alt="" loading="lazy">`
    : `<div class="gs-fallback">
         ${/^[a-z]{2}$/.test(flagCode) ? `<img class="gs-flag-bg" src="${FLAG_BASE}${flagCode}.svg" alt="">` : ""}
         <div class="gs-logo">${avatar(s.name, s.logo)}</div>
       </div>`;
  const sub = [
    (s.degree_levels || []).map((d) => t("profile.degree_level." + d)).join(" / "),
    t("scholarships.coverage." + s.coverage_type),
  ]
    .filter(Boolean)
    .join(" · ");
  return `
    <div class="gs-card" data-id="${s.id}" role="button" tabindex="0">
      <div class="gs-cover">
        ${cover}
        ${
          place
            ? `<span class="gs-pill">${first && s.countries.length === 1 ? `<span class="chip-flag">${flag(
                first.iso_code
              )}</span>` : ""}${escapeHtml(place)}</span>`
            : ""
        }
      </div>
      <div class="gs-body">
        <div class="gs-title">${escapeHtml(s.name)}</div>
        <div class="gs-meta">
          <span class="gs-left ${tone}">${grantDaysLeft(days)}</span>
          <span class="gs-sub">${escapeHtml(sub)}</span>
        </div>
      </div>
    </div>`;
}

async function renderHomeGrants() {
  clearInterval(homeGrantsTimer);
  const box = document.getElementById("home-grants");
  let items = [];
  try {
    items = await api("/scholarships");
  } catch (e) {
    items = [];
  }
  if (!box.isConnected) return;
  const soon = items
    .filter((s) => !s.closed && s.nearest_deadline_days_left !== null && s.nearest_deadline_days_left >= 0)
    .sort((a, b) => a.nearest_deadline_days_left - b.nearest_deadline_days_left)
    .slice(0, HOME_GRANTS_LIMIT);
  if (!soon.length) {
    box.remove();
    return;
  }

  box.innerHTML = `
    <div class="section-head">
      <span class="section-title">${t("home.grants_title")}</span>
      <button type="button" class="section-action" id="home-grants-all">${t("home.see_all")}</button>
    </div>
    <div class="gs-track">${soon.map(grantSlide).join("")}</div>
    ${
      soon.length > 1
        ? `<div class="gs-dots">${soon.map((_, i) => `<span class="${i ? "" : "on"}"></span>`).join("")}</div>`
        : ""
    }`;

  document.getElementById("home-grants-all").addEventListener("click", () => {
    haptic("light");
    switchTab("scholarships");
  });
  const byId = new Map(soon.map((s) => [String(s.id), s]));
  box.querySelectorAll(".gs-card").forEach((card) => {
    card.addEventListener("click", () => openScholarshipPage(byId.get(card.dataset.id)));
  });
  startGrantCarousel(box);
}

function startGrantCarousel(box) {
  const track = box.querySelector(".gs-track");
  const cards = [...track.children];
  const dots = [...box.querySelectorAll(".gs-dots span")];
  if (cards.length < 2) return;

  const step = () => cards[1].offsetLeft - cards[0].offsetLeft;
  const current = () => Math.min(cards.length - 1, Math.round(track.scrollLeft / step()));
  track.addEventListener(
    "scroll",
    () => {
      const i = current();
      dots.forEach((d, k) => d.classList.toggle("on", k === i));
    },
    { passive: true }
  );

  // Foydalanuvchi o'zi surayotganda avtomatik aylantirish xalaqit bermasin.
  let pausedUntil = 0;
  const pause = () => (pausedUntil = Date.now() + 7000);
  ["touchstart", "pointerdown", "wheel"].forEach((type) =>
    track.addEventListener(type, pause, { passive: true })
  );

  homeGrantsTimer = setInterval(() => {
    if (!track.isConnected || currentTab !== "home") {
      clearInterval(homeGrantsTimer);
      return;
    }
    if (document.hidden || Date.now() < pausedUntil) return;
    const next = (current() + 1) % cards.length;
    track.scrollTo({ left: next * step(), behavior: "smooth" });
  }, GRANT_ROTATE_MS);
}

// ============ Match ============

// Filtr qo'yilmaganda `/match` butun katalogni qaytaradi — ro'yxat to'la
// ko'rinadi va foydalanuvchi buni "menga moslashtirilgan" deb o'ylaydi.
// Shuning uchun ro'yxat tepasida nima bo'layotgani ochiq aytiladi.
function noFilterNote(total) {
  if (hasFilter()) return "";
  // Katta karta + keng tugma ko'rinishi har qanday ilovaga yopishtirsa
  // bo'ladigan umumiy blokka o'xshardi. Bu esa natijalar sahifasining o'z
  // elementi: joriy filtr holatini va nechta dastur ko'rinayotganini
  // ko'rsatadigan ixcham chiziq. Butun chiziq bosiladi.
  return `
    <div class="fx-bar" id="match-filter-cta" role="button" tabindex="0">
      <span class="fx-bar-mark">${icon("search")}</span>
      <span class="fx-bar-text">
        <span class="fx-bar-title">${t("match.no_filter_title")}</span>
        <span class="fx-bar-sub">${t("match.no_filter_count", { n: total })}</span>
      </span>
      <span class="fx-bar-go">${t("match.no_filter_cta")}${icon("chevron")}</span>
    </div>`;
}

// ---- Ixcham filtr (Dasturlar sahifasi tepasida) ----
//
// Filtr qo'yilgandan keyin uni o'zgartirish uchun alohida sahifaga o'tib,
// qaytadan "Topish" bosish kerak edi. Ko'p hollarda esa bitta narsa
// almashtiriladi: daraja, yo'nalish, til yoki reyting. Shuning uchun
// ro'yxat tepasida joriy tanlovlar ko'rinib turadi va har biri bir
// bosishda almashadi.
//
// Davlatlar bu yerda YO'Q: ular ko'p tanlovli va ixcham qatorga
// sig'maydi — o'sha chip to'liq filtr sahifasini ochadi.

function degreeLabel() {
  return profile.degree_level ? t("profile.degree_level." + profile.degree_level) : "";
}

function majorLabel() {
  const found = majors.find((m) => String(m.id) === String(profile.field_id));
  return found ? fieldName(found) : "";
}

function countriesLabel() {
  const ids = profile.target_country_ids || [];
  if (!ids.length) return "";
  if (ids.length === 1) {
    const found = countries.find((c) => String(c.id) === String(ids[0]));
    if (found) return countryName(found);
  }
  return t("profile.countries_count", { n: ids.length });
}

function miniChip(key, label, value) {
  return `
    <button type="button" class="mf-chip${value ? " is-set" : ""}" data-mf="${key}">
      <span class="mf-chip-label">${escapeHtml(label)}</span>
      <span class="mf-chip-value">${escapeHtml(value || t("profile.study_language_any"))}</span>
    </button>`;
}

function miniFilterBar() {
  if (!hasFilter()) return "";
  return `
    <div class="mf-bar">
      ${miniChip("degree", t("profile.degree_level"), degreeLabel())}
      ${miniChip("major", t("profile.major"), majorLabel())}
      ${miniChip("language", t("profile.study_language"), instructionLanguage(profile.study_language))}
      ${miniChip("rank", t("profile.rank"), profile.university_rank_range || "")}
      ${miniChip("countries", t("profile.countries"), countriesLabel())}
      <button type="button" class="mf-chip mf-all" data-mf="all">
        ${icon("search")}<span>${t("match.filter_all")}</span>
      </button>
    </div>`;
}

// Har bir tugma uchun: sarlavha, variantlar va tanlanganda yuboriladigan
// payload. `null` qaytsa — bu yerda hal qilib bo'lmaydi, to'liq filtr
// sahifasi ochiladi.
function quickFilterOptions(key) {
  const mark = (value, current) => String(value) === String(current || "");
  if (key === "degree") {
    return {
      title: t("profile.degree_level"),
      // "Farqi yo'q" yo'q: server darajani tozalashni qo'llab-quvvatlamaydi,
      // shuning uchun bu yerda ham va'da qilinmaydi.
      items: ["bachelor", "master", "phd"].map((d) => ({
        value: d,
        label: t("profile.degree_level." + d),
        active: mark(d, profile.degree_level),
      })),
      payload: (value) => ({ degree_level: value }),
    };
  }
  if (key === "major") {
    return {
      title: t("profile.major"),
      items: [
        { value: "", label: t("profile.major_placeholder"), active: !profile.field_id },
      ].concat(
        majors.map((m) => ({
          value: String(m.id),
          label: fieldName(m),
          active: mark(m.id, profile.field_id),
        }))
      ),
      payload: (value) => ({ field_id: value ? Number(value) : null }),
    };
  }
  if (key === "language") {
    return {
      title: t("profile.study_language"),
      items: [
        {
          value: "",
          label: t("profile.study_language_any"),
          active: !profile.study_language,
        },
      ].concat(
        studyLanguages.map((value) => ({
          value: value,
          label: instructionLanguage(value),
          active: mark(value, profile.study_language),
        }))
      ),
      payload: (value) => ({ study_language: value }),
    };
  }
  if (key === "rank") {
    return {
      title: t("profile.rank"),
      items: [
        {
          value: "",
          label: t("profile.rank_any"),
          active: !profile.university_rank_range,
        },
      ].concat(
        RANK_RANGES.map((r) => ({
          value: r,
          label: r,
          active: mark(r, profile.university_rank_range),
        }))
      ),
      payload: (value) => ({ university_rank_range: value }),
    };
  }
  return null;
}

async function applyQuickFilter(payload) {
  try {
    profile = await api("/me", { method: "PATCH", body: JSON.stringify(payload) });
    closeSheet();
    haptic("success");
    // Daraja almashsa yo'nalishlar ro'yxati ham boshqacha bo'ladi.
    if ("degree_level" in payload) await loadMajors();
    await renderMatch();
  } catch (err) {
    haptic("error");
    showToast(err.message);
  }
}

function openQuickFilterSheet(key) {
  const options = quickFilterOptions(key);
  if (!options) {
    switchTab("filter");
    return;
  }
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${options.title}</div>
    <div class="mf-options">
      ${options.items
        .map(
          (o) => `
        <button type="button" class="mf-option${o.active ? " active" : ""}"
                data-value="${escapeHtml(o.value)}">
          <span>${escapeHtml(o.label)}</span>
          ${o.active ? icon("check") : ""}
        </button>`
        )
        .join("")}
    </div>`,
    sheet,
    { tall: options.items.length > 7 }
  );
  sheet.querySelectorAll(".mf-option").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      applyQuickFilter(options.payload(btn.dataset.value));
    });
  });
}

function bindMiniFilter(root) {
  root.querySelectorAll(".mf-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      haptic("light");
      const key = chip.dataset.mf;
      // Davlatlar — onboarding'ning o'sha savolida, "Hammasi" — boshidan.
      if (key === "all" || key === "countries") {
        openFilter(key === "countries" ? "countries" : null);
        return;
      }
      openQuickFilterSheet(key);
    });
  });
}

function bindFilterCta(root) {
  const bar = root.querySelector("#match-filter-cta");
  if (!bar) return;
  const open = () => {
    haptic("light");
    switchTab("filter");
  };
  bar.addEventListener("click", open);
  bar.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      open();
    }
  });
}

async function renderMatch() {
  const el = document.getElementById("view-match");
  el.innerHTML = skeletons(4);

  const matches = await api("/match");
  if (!matches.length) {
    // Ixcham filtr bu yerda AYNIQSA kerak: ro'yxat bo'sh bo'lsa, demak
    // tanlov juda tor va uni o'zgartirish kerak. Ilgari buning uchun
    // alohida sahifaga o'tishga to'g'ri kelardi.
    el.innerHTML =
      miniFilterBar() +
      `
      <div class="empty">
        <div class="empty-ico">${icon("search")}</div>
        <div class="empty-title">${t("match.empty_title")}</div>
        <div class="empty-text">${t("match.empty_text")}</div>
      </div>`;
    bindMiniFilter(el);
    return;
  }

  el.innerHTML =
    noFilterNote(matches.length) +
    miniFilterBar() +
    `<div class="pr-tools">
       <div class="pr-search">${icon("search")}<input type="search" id="match-search" placeholder="${t(
         "match.search_placeholder"
       )}" value="${escapeHtml(matchQuery)}" autocomplete="off"></div>
       <div class="filter-scroll" id="match-sort">
         ${MATCH_SORTS.map(
           (key) =>
             `<div class="chip ${matchSort === key ? "active" : ""}" data-value="${key}">${t(
               "match.sort." + key
             )}</div>`
         ).join("")}
       </div>
     </div>
     <div id="match-list"></div>`;

  const listEl = document.getElementById("match-list");
  const drawList = () => {
    const shown = sortMatches(filterMatches(matches, matchQuery), matchSort);
    listEl.innerHTML = shown.length
      ? shown.map(matchCard).join("")
      : `<div class="empty"><div class="empty-text">${t("match.search_empty")}</div></div>`;
    bindMatchCards(listEl);
  };

  document.getElementById("match-search").addEventListener("input", (event) => {
    matchQuery = event.target.value;
    drawList();
  });
  el.querySelectorAll("#match-sort .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      haptic("light");
      matchSort = chip.dataset.value;
      el.querySelectorAll("#match-sort .chip").forEach((c) => c.classList.toggle("active", c === chip));
      drawList();
    });
  });
  drawList();

  bindFilterCta(el);
  bindMiniFilter(el);
}

// Qidiruv va saralash tab almashganda saqlanib qoladi.
let matchQuery = "";
let matchSort = "relevance";
const MATCH_SORTS = ["relevance", "price", "ranking", "deadline"];

function filterMatches(items, query) {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return items;
  return items.filter((m) => {
    const hay = [m.name, m.abbreviation, m.university, countryName(m.country)]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return words.every((w) => hay.includes(w));
  });
}

/** Qiymati yo'q dasturlar har doim oxirida. "relevance" — server tartibi. */
function sortMatches(items, sort) {
  const keyOf = {
    price: (m) => approxUsd(m.tuition_amount, m.tuition_currency),
    ranking: (m) => m.university_ranking,
    deadline: (m) => m.nearest_deadline,
  }[sort];
  if (!keyOf) return items;
  const missing = (v) => v === null || v === undefined;
  return [...items].sort((a, b) => {
    const ka = keyOf(a);
    const kb = keyOf(b);
    if (missing(ka)) return missing(kb) ? 0 : 1;
    if (missing(kb)) return -1;
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
}

function bindMatchCards(root) {
  root.querySelectorAll(".save-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      haptic("light");
      await api(`/saved/${btn.dataset.id}`, { method: "POST" });
      btn.disabled = true;
      btn.className = "btn btn-done save-btn";
      btn.innerHTML = icon("check") + t("match.saved");
      haptic("success");
      showToast(t("match.saved_toast"));
    });
  });
  bindProgramOpeners(root);
}

function matchCard(m) {
  const isGreen = m.level === "green";
  // Kalitlar ("ielts", "toefl", "ielts_toefl") foydalanuvchi tiliga o'giriladi.
  const missing = m.missing.length
    ? `<span class="pill amber">${t("match.missing", {
        list: m.missing.map((k) => t("match.missing_key." + k)).join(", "),
      })}</span>`
    : "";
  // Tuzilishi grant kartasi bilan bir xil: sarlavha -> faktlar -> amal.
  const fee =
    m.tuition_amount !== null && m.tuition_amount !== undefined
      ? feeWithUsd(m.tuition_amount, m.tuition_currency)
      : "";

  return `
    <div class="card pr-card">
      <div class="pr-head program-open" data-id="${m.id}" role="button" tabindex="0">
        ${avatar(m.university, m.university_logo)}
        <div class="pr-head-text">
          <div class="card-title">${escapeHtml(m.name)}${
            m.abbreviation ? `<span class="abbr">${escapeHtml(m.abbreviation)}</span>` : ""
          }</div>
          <div class="card-sub">${escapeHtml(m.university)}</div>
          <div class="pr-countries">
            <span class="pill"><span class="chip-flag">${flag(
              m.country.iso_code
            )}</span>${escapeHtml(countryName(m.country))}</span>
            ${
              m.university_ranking
                ? `<span class="pill rank-pill">${icon("award")}${t("program.ranking", {
                    n: m.university_ranking,
                  })}</span>`
                : ""
            }
          </div>
        </div>
        <span class="card-chevron">${icon("chevron")}</span>
      </div>

      <div class="pr-facts">
        <span class="pill ${isGreen ? "green" : "amber"}">${isGreen ? icon("check") : icon("spark")}${
          isGreen ? t("match.green") : t("match.yellow")
        }</span>
        ${fee ? `<span class="pill">${icon("spark")}${fee}</span>` : ""}
        ${m.ielts_min ? `<span class="pill">IELTS ${m.ielts_min}</span>` : ""}
        ${m.toefl_min ? `<span class="pill">TOEFL ${m.toefl_min}</span>` : ""}
        ${missing}
      </div>

      <div class="pr-actions">
        <button type="button" class="btn ${m.saved ? "btn-done" : "btn-soft"} save-btn" data-id="${m.id}" ${
          m.saved ? "disabled" : ""
        }>
          ${m.saved ? icon("check") + t("match.saved") : icon("plus") + t("match.save")}
        </button>
      </div>
    </div>`;
}

function bindProgramOpeners(root) {
  root.querySelectorAll(".program-open").forEach((node) => {
    node.addEventListener("click", () => openProgramPage(node.dataset.id));
    node.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openProgramPage(node.dataset.id);
      }
    });
  });
}

function avatar(name, logoUrl) {
  // Logotip yuklanmasa (domen favicon bermasa) `onerror` uni olib tashlaydi
  // va ostidagi bosh harflar ko'rinadi.
  const fallback = escapeHtml(initials(name));
  if (!logoUrl) return `<div class="avatar">${fallback}</div>`;
  return `<div class="avatar">${fallback}<img src="${escapeHtml(
    logoUrl
  )}" alt="" loading="lazy" onerror="this.remove()"></div>`;
}

// ============ Narxlar: taxminiy USD ============

// 1 birlik = N USD, taxminiy (2026-yil oktabr). Faqat "≈" yozuvi va narx
// bo'yicha saralash uchun: katalogda GBP, EUR, MYR, KRW va boshqalar aralash,
// ularni ko'z bilan solishtirib bo'lmaydi. Aniq summa — universitet saytida.
const APPROX_USD = {
  USD: 1,
  EUR: 1.15,
  GBP: 1.33,
  MYR: 0.235,
  KRW: 0.00072,
  CZK: 0.047,
  PLN: 0.27,
  NOK: 0.098,
  HUF: 0.0029,
};

function approxUsd(amount, currency) {
  const rate = APPROX_USD[String(currency || "").toUpperCase()];
  return rate && amount !== null && amount !== undefined ? Number(amount) * rate : null;
}

/** "18,500 GBP · ≈ $24,600" — USD bo'lmagan narx yoniga taxminiy dollar. */
function feeWithUsd(amount, currency) {
  const base = `${Number(amount).toLocaleString()} ${escapeHtml(currency || "")}`;
  const usd = approxUsd(amount, currency);
  if (usd === null || String(currency).toUpperCase() === "USD") return base;
  return `${base} · ≈ $${(Math.round(usd / 100) * 100).toLocaleString()}`;
}

// ============ Scholarships (davlat stipendiyalari) ============

let scholarshipCountryId = null; // null — barcha davlatlar

async function renderScholarships() {
  const el = document.getElementById("view-scholarships");
  el.innerHTML = skeletons(4);

  const query = scholarshipCountryId ? `?country_id=${scholarshipCountryId}` : "";
  const items = await api(`/scholarships${query}`);

  // Bir qatorli gorizontal lenta: chiplar bir necha qatorga yoyilib
  // grant kartalarini pastga surib yubormasligi uchun.
  const chips = `
    <div class="filter-scroll" id="scholarship-country-chips">
      <div class="chip ${scholarshipCountryId === null ? "active" : ""}" data-value="">${t(
        "scholarships.all_countries"
      )}</div>
      ${allCountries
        .map(
          (c) =>
            `<div class="chip ${String(scholarshipCountryId) === String(c.id) ? "active" : ""}" data-value="${
              c.id
            }"><span class="chip-flag">${flag(c.iso_code)}</span>${escapeHtml(countryName(c))}</div>`
        )
        .join("")}
    </div>`;

  const cards = items.length
    ? items.map(scholarshipCard).join("")
    : `<div class="empty">
         <div class="empty-ico">${icon("award")}</div>
         <div class="empty-title">${t("scholarships.empty_title")}</div>
         <div class="empty-text">${t("scholarships.empty_text")}</div>
       </div>`;

  el.innerHTML = chips + cards;

  el.querySelectorAll("#scholarship-country-chips .chip").forEach((chip) => {
    chip.addEventListener("click", async () => {
      haptic("light");
      scholarshipCountryId = chip.dataset.value ? Number(chip.dataset.value) : null;
      await renderScholarships();
    });
  });

  const byId = new Map(items.map((s) => [String(s.id), s]));
  el.querySelectorAll(".details-btn").forEach((btn) => {
    btn.addEventListener("click", () => openScholarshipPage(byId.get(btn.dataset.id)));
  });
}

function scholarshipCard(s) {
  const coverageTone = s.coverage_type === "full" ? "green" : "amber";
  const extras = [
    [s.extras_flight, "plane", "scholarships.extra_flight"],
    [s.extras_insurance, "shield", "scholarships.extra_insurance"],
    [s.extras_dormitory, "bed", "scholarships.extra_dormitory"],
    [s.extras_language_course, "lang", "scholarships.extra_language"],
  ]
    .filter(([enabled]) => enabled)
    .map(([, iconName, key]) => `<span class="pill">${icon(iconName)}${t(key)}</span>`)
    .join("");

  const countryPills = s.countries
    .map(
      (c) =>
        `<span class="pill"><span class="chip-flag">${flag(c.iso_code)}</span>${escapeHtml(
          countryName(c)
        )}</span>`
    )
    .join("");

  // Muddati o'tgan grant — kartaning o'zida aniq belgi. Ilgari "Deadline
  // passed" faqat ichida yozilardi va karta ochiq grantdek ko'rinardi.
  const deadline = s.closed
    ? `<span class="pill">${icon("clock")}${t("scholarships.closed_badge")}</span>`
    : s.nearest_deadline
    ? `<span class="pill ${
        s.nearest_deadline_days_left !== null && s.nearest_deadline_days_left <= 30 ? "red" : ""
      }">${icon("clock")}${t("scholarships.deadline", { date: escapeHtml(s.nearest_deadline) })}</span>`
    : "";

  // Bir qarashda eng kerakli raqam: oylik stipendiya.
  const stipend = stipendText(s);

  return `
    <div class="card gr-card details-btn${s.closed ? " is-closed" : ""}" data-id="${s.id}" role="button" tabindex="0">
      <div class="gr-head">
        ${avatar(s.name, s.logo)}
        <div class="gr-head-text">
          <div class="card-title">${escapeHtml(s.name)}</div>
          <div class="gr-countries">${countryPills}</div>
        </div>
        <span class="card-chevron">${icon("chevron")}</span>
      </div>

      <div class="gr-facts">
        <span class="pill ${coverageTone}">${icon("award")}${t(
          "scholarships.coverage." + s.coverage_type
        )}</span>
        ${stipend ? `<span class="pill">${icon("spark")}${escapeHtml(stipend)}</span>` : ""}
        ${deadline}
      </div>

      ${extras ? `<div class="gr-extras">${extras}</div>` : ""}
    </div>`;
}

// Ko'p qatorli matn: har bir qator alohida satrda chiqadi.
function multiline(text) {
  return String(text)
    .split("\n")
    .filter(Boolean)
    .map((line) => escapeHtml(line))
    .join("<br>");
}

function stipendText(s) {
  if (s.stipend_amount === null || s.stipend_amount === undefined) return "";
  const fmt = (n) => Number(n).toLocaleString();
  const amount =
    s.stipend_max && s.stipend_max !== s.stipend_amount
      ? `${fmt(s.stipend_amount)}–${fmt(s.stipend_max)}`
      : fmt(s.stipend_amount);
  const period = s.stipend_period ? " / " + t("scholarships.per_" + s.stipend_period) : "";
  return `${amount} ${s.currency}${period}`;
}

// ---- Tafsilot oynasi: avval ilova ichida ko'rsatiladi, rasmiy saytga
// ---- o'tish esa alohida tugma orqali (ilgari darhol tashqariga chiqib ketardi).

function ensureSheet() {
  let backdrop = document.querySelector(".sheet-backdrop");
  if (backdrop) return backdrop;

  backdrop = document.createElement("div");
  backdrop.className = "sheet-backdrop";
  const sheet = document.createElement("div");
  sheet.className = "sheet";
  document.body.append(backdrop, sheet);

  // Klaviatura ochiq turganda fonga bosish AVVAL faqat klaviaturani yopadi,
  // varaq ochiqligicha qoladi; ikkinchi bosishda varaq yopiladi.
  // Ilgari bitta bosish ikki ishni birdan qilardi: hujjat darajasidagi
  // `touchstart` klaviaturani yopar, o'sha bosishning `click`i esa varaqni
  // ham yopib yuborardi. GPA konvertorda raqam yozib chetga bosilganda
  // kalkulyator butunlay yopilib ketishi shundan edi.
  // `touchstart` va `pointerdown` tartibi brauzerlarda bir xil emas, shuning
  // uchun bayroqqa emas, klaviatura yopilgan vaqtga qaraymiz — bu tartibdan
  // qat'i nazar ishlaydi.
  backdrop.addEventListener("click", () => {
    if (isFieldFocused() || keyboardJustDismissed()) {
      dismissKeyboard();
      return;
    }
    closeSheet();
  });

  // Tepadagi "tutqich" yopish belgisiga o'xshaydi — uni bosganda ham yopilsin.
  sheet.addEventListener("click", (event) => {
    if (event.target.classList.contains("sheet-handle")) closeSheet();
  });
  // Varaq ichidagi bo'sh joyga bosilganda ham klaviatura yopilsin. Hujjat
  // darajasidagi qoida `touchstart`ga bog'langan, ya'ni sichqonchada
  // ishlamaydi; `pointerdown` esa barmoqni ham, sichqonchani ham qamraydi.
  sheet.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(TEXT_FIELD) && !event.target.closest(TAPPABLE)) dismissKeyboard();
  });
  return backdrop;
}

// Varaq qanday yopilmasin (fon, "Orqaga", boshqa varaq ochilishi) —
// uni kutayotgan kod bundan xabar topishi kerak. Aks holda obuna
// varag'i yopilganda "Mos dasturlarni topish" o'chiq tugma bilan qolardi.
let onSheetClose = null;

function fireSheetClose() {
  const callback = onSheetClose;
  onSheetClose = null;
  if (callback) callback();
}

function closeSheet() {
  fireSheetClose();
  document.querySelector(".sheet-backdrop")?.classList.remove("open");
  const sheet = document.querySelector(".sheet");
  sheet?.classList.remove("open");
  // Balandlik faqat o'sha varaqqa tegishli — yopilganda olib tashlanadi,
  // aks holda keyingi kichik varaq ham balandligicha ochilardi.
  sheet?.classList.remove("sheet-tall");
  document.body.style.overflow = "";
  try {
    tg?.BackButton?.hide();
  } catch (e) {
    /* eski klientlar */
  }
}

// `options.tall` — varaqni kontent bo'yicha emas, to'liq sahifa balandligida
// ochadi (GPA konvertor uchun: natija chiqqanda varaq sakrab kattaymaydi).
function showSheet(html, sheet, options) {
  fireSheetClose();
  sheet.innerHTML = html;
  document.querySelector(".sheet-backdrop").classList.add("open");
  sheet.classList.toggle("sheet-tall", !!(options && options.tall));
  sheet.classList.add("open");
  document.body.style.overflow = "hidden";
  try {
    if (tg?.BackButton) {
      tg.BackButton.show();
      tg.BackButton.onClick(closeSheet);
    }
  } catch (e) {
    /* eski klientlar */
  }
}

// ============ Birinchi kirishda yo'naltirish ============

// Filtrsiz ilova "hamma dasturlar ro'yxati" bo'lib qoladi va yangi
// foydalanuvchi uning nima uchun kerakligini tushunmaydi. Shuning uchun
// ilova ochilganda filtr bo'sh bo'lsa, birinchi bo'lib shu oyna chiqadi.
// Sessiyada bir marta: sahifalar orasida yurganda qayta ochilmasin.
// ============ GPA konvertor ============

// Har bir O'zbekiston shkalasi uchun ruxsat etilgan oraliq va namuna qiymat.
const GPA_SCALES = {
  5: { min: 2, max: 5, step: "0.01", example: "4.5" },
  100: { min: 0, max: 100, step: "0.1", example: "85" },
  4: { min: 0, max: 4, step: "0.01", example: "3.5" },
};

function openGpaPage() {
  haptic("light");
  enterPage("gpa");
  closeSheet();
  return switchTab("gpa");
}

function renderGpaPage() {
  const el = document.getElementById("view-gpa");
  document.body.classList.add("page-mode");
  const leave = () => leavePage("gpa", "home");
  showPageBack(leave);
  // Profilda baho bo'lsa, konvertor shu bilan ochiladi.
  let scale = profile && profile.gpa_scale ? String(profile.gpa_scale) : "100";
  const initial = profile && profile.gpa_raw !== null && profile.gpa_scale ? profile.gpa_raw : "";

  el.innerHTML = `
    <div class="pg">
    <div class="pg-top">
      <button type="button" class="pg-back" id="pg-back" aria-label="${t("common.back")}">${icon(
        "chevron"
      )}</button>
      <span></span>
    </div>
    <div class="pg-hero pg-hero-row">
      <img class="pg-hero-ico" src="icon-gpa.png?v=${ASSET_V}" alt="" aria-hidden="true">
      <div>
        <h2 class="pg-title">${t("gpa.title")}</h2>
        <div class="pg-sub">${t("gpa.subtitle")}</div>
      </div>
    </div>

    <section class="pg-card">
      <h3>${t("gpa.scale")}</h3>
      <div class="chip-group" id="gpa-sheet-scale">
        ${["5", "100", "4"]
          .map(
            (value) =>
              `<div class="chip ${value === scale ? "active" : ""}" data-value="${value}">${t(
                "profile.gpa_scale." + value
              )}</div>`
          )
          .join("")}
      </div>
    </section>

    <section class="pg-card">
      <h3>${t("gpa.value")}</h3>
      <input type="number" inputmode="decimal" id="gpa-sheet-input" class="gpa-input"
             value="${escapeHtml(initial)}" />
      <div class="gpa-range" id="gpa-sheet-range"></div>
    </section>

    <div id="gpa-sheet-result"></div>
    </div>
  `;
  document.getElementById("pg-back").addEventListener("click", leave);

  const input = document.getElementById("gpa-sheet-input");
  const range = document.getElementById("gpa-sheet-range");
  const result = document.getElementById("gpa-sheet-result");
  let timer = null;
  let requestId = 0;

  const applyScale = () => {
    const cfg = GPA_SCALES[scale];
    input.step = cfg.step;
    input.min = cfg.min;
    input.max = cfg.max;
    input.placeholder = cfg.example;
    range.textContent = t("gpa.range", { min: cfg.min, max: cfg.max });
  };

  const render = async () => {
    const cfg = GPA_SCALES[scale];
    const value = parseFloat(String(input.value).replace(",", "."));
    if (Number.isNaN(value)) {
      result.innerHTML = `<div class="sheet-empty">${t("gpa.empty")}</div>`;
      return;
    }
    if (value < cfg.min || value > cfg.max) {
      result.innerHTML = `<div class="gpa-error">${t("gpa.range", { min: cfg.min, max: cfg.max })}</div>`;
      return;
    }
    const current = ++requestId;
    let r;
    try {
      r = await api(`/gpa/convert?value=${encodeURIComponent(value)}&scale=${encodeURIComponent(scale)}`);
    } catch (e) {
      return;
    }
    // Tez yozilganda eski javob yangisining ustidan chizilmasin.
    if (current !== requestId) return;

    const card = (code, label, main, sub) => `
      <div class="gpa-result">
        <span class="gpa-result-flag">${flag(code)}</span>
        <div class="gpa-result-text">
          <div class="gpa-result-label">${label}</div>
          ${sub ? `<div class="gpa-result-sub">${sub}</div>` : ""}
        </div>
        <div class="gpa-result-value">${main}</div>
      </div>`;

    result.innerHTML = `
      <section class="pg-card">
        <h3>${t("gpa.results")}</h3>
        <div class="gpa-results">
          ${card("US", t("gpa.us"), `${r.us4.toFixed(2)}`, t("gpa.us_sub"))}
          ${card("GB", t("gpa.uk"), escapeHtml(t("gpa.uk_short." + r.uk)), t("gpa.uk_class." + r.uk))}
          ${card("EU", t("gpa.eu"), escapeHtml(r.ects), t("gpa.eu_sub"))}
          ${card("DE", t("gpa.de"), `${r.bavarian.toFixed(1)}`, t("gpa.de_sub"))}
        </div>
      </section>
      <div class="disclaimer">${icon("clock")}<span>${t("gpa.disclaimer")}</span></div>`;
  };

  document.querySelectorAll("#gpa-sheet-scale .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      haptic("light");
      document
        .querySelectorAll("#gpa-sheet-scale .chip")
        .forEach((c) => c.classList.toggle("active", c === chip));
      scale = chip.dataset.value;
      applyScale();
      render();
    });
  });
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(render, 250);
  });

  applyScale();
  render();
}

// ---- Dastur sahifasi ----
// Ilgari pastdan chiqadigan yarim oyna edi — endi alohida to'liq sahifa
// (Scout'dagidek). Orqaga — Telegram'ning tugmasi yoki sahifadagi tugma;
// dastur qayerdan ochilgan bo'lsa (ro'yxat, saqlanganlar, ...) o'sha yerga.
let programPageId = null;
let programReturnTab = "match";

function openProgramPage(programId) {
  haptic("light");
  // Mentor formasidan qaytilganda qaytish manzili o'zgarmaydi.
  if (currentTab !== "program" && currentTab !== "mentor") programReturnTab = currentTab;
  programPageId = Number(programId);
  closeSheet();
  return switchTab("program");
}

function leaveProgramPage() {
  haptic("light");
  switchTab(programReturnTab && programReturnTab !== "program" ? programReturnTab : "match");
}

// To'liq sahifalar (pastki menyusiz, Telegram "orqaga" tugmasi bilan).
const PAGE_TABS = new Set(["program", "grant", "service", "gpa"]);
// Har sahifa qayerdan ochilgan bo'lsa — "orqaga" o'sha yerga.
const pageReturn = {};

function enterPage(name) {
  if (currentTab !== name && currentTab !== "mentor") pageReturn[name] = currentTab;
}

function leavePage(name, fallback) {
  haptic("light");
  const back = pageReturn[name];
  switchTab(back && back !== name ? back : fallback);
}

// Telegram'ning sarlavhadagi "orqaga" tugmasi — faqat to'liq sahifalarda.
let pageBackHandler = null;

// Telegram'ning o'z "orqaga" tugmasi (6.1+) bo'lsa, sahifa ichidagi tugma
// yashiriladi — ikkita bir xil tugma turmasin. Eski klientlarda ichkisi qoladi.
if (tg && tg.BackButton && typeof tg.isVersionAtLeast === "function" && tg.isVersionAtLeast("6.1")) {
  document.body.classList.add("tg-back");
}

function showPageBack(handler) {
  hidePageBack();
  pageBackHandler = handler;
  try {
    tg?.BackButton?.onClick(handler);
    tg?.BackButton?.show();
  } catch (e) {
    /* eski klientlar */
  }
}

function hidePageBack() {
  if (!pageBackHandler) return;
  try {
    tg?.BackButton?.offClick(pageBackHandler);
    tg?.BackButton?.hide();
  } catch (e) {
    /* eski klientlar */
  }
  pageBackHandler = null;
}

async function renderProgramPage() {
  const el = document.getElementById("view-program");
  document.body.classList.add("page-mode");
  showPageBack(leaveProgramPage);
  el.innerHTML = skeletons(4);

  const p = await api(`/programs/${programPageId}`);

  const row = (label, value) =>
    `<div class="sheet-row"><span class="sheet-row-label">${label}</span><span class="sheet-row-value">${value}</span></div>`;
  const dash = t("scholarships.not_specified");
  const money = (amount, currency) =>
    amount === null || amount === undefined
      ? dash
      : `${Number(amount).toLocaleString()} ${escapeHtml(currency)}`;

  const req = p.requirement || {};

  // Til sertifikati: faqat dastur qabul qiladiganlari. Ikkalasi bo'lsa —
  // ulardan biri yetarli ekani alohida aytiladi.
  // Minimal GPA talablar matnidan hisoblanadi (faqat magistr/PhD).
  const gpaRow =
    p.gpa_min !== null && p.gpa_min !== undefined
      ? row(t("program.gpa_min"), `${p.gpa_min} / ${p.gpa_scale === "100" ? "100" : "4.0"}`)
      : "";
  const certRows =
    gpaRow +
    (req.ielts_min !== null && req.ielts_min !== undefined
      ? row(t("program.ielts_min"), req.ielts_min)
      : "") +
    (req.toefl_min !== null && req.toefl_min !== undefined
      ? row(t("program.toefl_min"), req.toefl_min)
      : "");
  const bothCerts =
    req.ielts_min !== null && req.ielts_min !== undefined &&
    req.toefl_min !== null && req.toefl_min !== undefined;
  const languageCerts = certRows
    ? certRows + (bothCerts ? `<div class="sheet-note">${t("program.certs_either")}</div>` : "")
    : `<div class="sheet-empty">${t("program.no_language_req")}</div>`;

  // Talab ham, hujjat ham bitta savolga javob beradi — "arizaga nima kerak".
  // Shuning uchun tizimli maydonlar ham, admin yozgan matn ham bitta ro'yxatga
  // qo'shiladi; qiymati yo'q maydon umuman ko'rsatilmaydi.
  const checklist = [];
  if (req.gre_required) {
    checklist.push(
      req.gre_min !== null && req.gre_min !== undefined
        ? t("program.req_gre_score", { score: req.gre_min })
        : t("program.req_gre")
    );
  }
  if (req.prereq_major) {
    checklist.push(t("program.req_prereq", { major: req.prereq_major }));
  }
  checklist.push(
    ...(p.required_documents || []).map((d) => t("document." + d)),
    ...(p.requirements || [])
  );
  const requirements = checklist.length
    ? `<ul class="doc-list">${checklist
        .map((r) => `<li>${icon("check")}${escapeHtml(r)}</li>`)
        .join("")}</ul>`
    : `<div class="sheet-empty">${t("program.no_requirements")}</div>`;

  const cost = p.cost;
  const feeRow =
    p.has_application_fee === null || p.has_application_fee === undefined
      ? ""
      : row(
          t("program.app_fee"),
          p.has_application_fee
            ? p.application_fee_amount !== null && p.application_fee_amount !== undefined
              ? money(p.application_fee_amount, p.application_fee_currency || "")
              : t("program.app_fee_paid")
            : t("program.app_fee_free")
        );
  const costs =
    cost || feeRow
      ? (cost
          ? row(
              t("program.tuition"),
              cost.tuition_amount === null || cost.tuition_amount === undefined
                ? dash
                : feeWithUsd(cost.tuition_amount, cost.currency)
            )
          : "") +
        feeRow +
        (cost
          ? `<div class="sheet-note">${t("program.cost_disclaimer", {
              date: escapeHtml(cost.last_checked),
            })}</div>`
          : "")
      : `<div class="sheet-empty">${t("program.no_costs")}</div>`;

  const deadlines = p.deadlines.length
    ? p.deadlines
        .map((d) => {
          const left =
            d.days_left >= 0
              ? t("scholarships.days_left", { days: d.days_left })
              : t("scholarships.deadline_passed");
          return row(
            t("deadline." + d.type),
            `${escapeHtml(d.date)} <span class="sheet-muted">· ${left}</span>`
          );
        })
        .join("")
    : p.deadline_month
      // Aniq sana yo'q, lekin odatdagi oy ma'lum — bu ham foydali
      // ma'lumot: "hech narsa yo'q" degandan ko'ra aniqroq.
      ? `<div class="sheet-note">${t("saved.month_hint", {
          month: t("month." + p.deadline_month),
        })}</div>`
      : `<div class="sheet-empty">${t("saved.unknown_hint")}</div>`;

  // Scout uslubidagi sahifa: tepada kalit faktlar, bo'limlar oq kartalarda,
  // pastda doimiy panel (saqlash + rasmiy sahifa).
  const openDl = p.deadlines.find((d) => d.type === "application_open");
  const closes = p.deadlines.filter((d) => d.type === "application_close");
  const closeDl = closes.find((d) => d.days_left >= 0) || closes[closes.length - 1];
  const daysLeft = closeDl && closeDl.days_left >= 0 ? closeDl.days_left : null;
  const dlChip = closeDl
    ? daysLeft !== null
      ? `<span class="pg-chip ${daysLeft <= 7 ? "is-urgent" : "is-soon"}"><i></i>${t(
          "scholarships.days_left",
          { days: daysLeft }
        )}</span>`
      : `<span class="pg-chip is-closed">${t("scholarships.deadline_passed")}</span>`
    : "";
  const fact = (label, value) =>
    `<div class="pg-fact"><span>${label}</span><b>${value || "—"}</b></div>`;
  const section = (title, body) =>
    `<section class="pg-card"><h3>${title}</h3>${body}</section>`;

  const scholarship =
    p.has_scholarship === null || p.has_scholarship === undefined
      ? ""
      : section(
          t("program.own_scholarship"),
          p.has_scholarship
            ? p.scholarship_url
              ? `<button type="button" class="sch-card sheet-scholarship" data-url="${escapeHtml(
                  p.scholarship_url
                )}">
                   <span class="sch-ico">${icon("award")}</span>
                   <span class="sch-text">
                     <span class="sch-title">${t("program.scholarship_title_yes")}</span>
                     <span class="sch-sub">${t("program.scholarship_sub_link")}</span>
                   </span>
                   <span class="sch-go">${icon("chevron")}</span>
                 </button>`
              : `<div class="sch-card">
                   <span class="sch-ico">${icon("award")}</span>
                   <span class="sch-text">
                     <span class="sch-title">${t("program.scholarship_title_yes")}</span>
                     <span class="sch-sub">${t("program.scholarship_sub_nolink")}</span>
                   </span>
                 </div>`
            : `<button type="button" class="sch-card sch-none" id="sheet-to-grants">
                 <span class="sch-ico">${icon("award")}</span>
                 <span class="sch-text">
                   <span class="sch-title">${t("program.scholarship_title_no")}</span>
                   <span class="sch-sub">${t("program.scholarship_sub_no")}</span>
                 </span>
                 <span class="sch-go">${icon("chevron")}</span>
               </button>`
        );

  // Shu davlatdagi mentor (Uni Buddy) — savol guruhga ketadi.
  const mentorOn = mentorConfig && mentorConfig.enabled;
  const mentorCountry = mentorOn
    ? mentorConfig.countries.find((c) => c.code === String(p.country.iso_code).toUpperCase())
    : null;
  const mentorCard = mentorOn
    ? `<button type="button" class="pg-mentor" id="pg-mentor">
         <img src="icon-buddy.png?v=${ASSET_V}" alt="" aria-hidden="true">
         <span class="pg-mentor-text">
           <span class="pg-mentor-title">${t("program.ask_mentor", {
             country: escapeHtml(countryName(p.country)),
           })}</span>
           <span class="pg-mentor-sub">${t("buddy.tagline")}</span>
         </span>
         <span class="pg-mentor-go">${icon("arrow")}</span>
       </button>`
    : "";

  el.innerHTML = `
    <div class="pg">
      <div class="pg-top">
        <button type="button" class="pg-back" id="pg-back" aria-label="${t("common.back")}">${icon(
          "chevron"
        )}</button>
        ${
          // Rasm bo'lsa davlat yorlig'i rasm ustida turadi.
          p.cover_url
            ? ""
            : `<span class="pg-country"><span class="chip-flag">${flag(p.country.iso_code)}</span>${escapeHtml(
                countryName(p.country)
              )}</span>`
        }
      </div>
      ${
        p.cover_url
          ? `<div class="pg-cover">
               <img src="${escapeHtml(p.cover_url)}" alt="" loading="eager" onerror="this.style.visibility='hidden'">
               <span class="pg-country pg-cover-pill"><span class="chip-flag">${flag(p.country.iso_code)}</span>${escapeHtml(countryName(p.country))}</span>
             </div>`
          : ""
      }
      <div class="pg-hero${p.cover_url ? " has-cover" : ""}">${avatar(p.university, p.university_logo)}</div>
      <h2 class="pg-title">${escapeHtml(p.name)}${
        p.abbreviation ? `<span class="abbr">${escapeHtml(p.abbreviation)}</span>` : ""
      }</h2>
      <div class="pg-sub">${escapeHtml(p.university)}${p.city ? " · " + escapeHtml(p.city) : ""}</div>
      <div class="pg-chips">
        ${dlChip}
        <span class="pg-chip">${t("profile.degree_level." + p.degree_level)}</span>
        <span class="pg-chip">${p.duration_years} ${t("program.years")}</span>
        ${
          p.university_ranking
            ? `<span class="pg-chip">${t("program.ranking", { n: p.university_ranking })}</span>`
            : ""
        }
      </div>

      <div class="pg-facts">
        ${fact(t("program.opens"), openDl ? shortDate(openDl.date) : "")}
        ${fact(t("program.closes"), closeDl ? shortDate(closeDl.date) : "")}
        ${fact(t("program.left"), daysLeft !== null ? t("program.days_n", { n: daysLeft }) : "")}
      </div>
      <div class="pg-source">${t("program.verified_at", { date: escapeHtml(p.verified_at) })}</div>

      ${section(
        t("program.about"),
        row(t("program.field"), p.field ? escapeHtml(fieldName(p.field)) : dash) +
          row(t("program.language"), escapeHtml(instructionLanguage(p.language_of_instruction))) +
          row(t("program.intake"), escapeHtml(p.intake_term)) +
          (p.notes ? `<div class="sheet-note">${escapeHtml(p.notes)}</div>` : "") +
          missingNote(p.missing_fields)
      )}
      ${section(t("program.language_certs"), languageCerts)}
      ${section(t("program.costs"), costs)}
      ${section(t("program.requirements_docs"), requirements)}
      ${scholarship}
      ${section(t("scholarships.deadlines"), deadlines)}
      ${mentorCard}
    </div>

    <div class="pg-bar">
      <button type="button" class="pg-save${p.saved ? " is-saved" : ""}" id="sheet-save" ${
        p.saved ? "disabled" : ""
      } aria-label="${escapeHtml(t(p.saved ? "match.saved" : "match.save"))}">${icon("bookmark")}</button>
      <button type="button" class="btn btn-accent pg-open" id="sheet-open-site">
        ${t("program.official_page")}
      </button>
    </div>
  `;

  document.getElementById("pg-back").addEventListener("click", leaveProgramPage);
  document.getElementById("pg-mentor")?.addEventListener("click", () => {
    haptic("light");
    openMentor(mentorCountry ? "form" : "countries", {
      country: mentorCountry ? mentorCountry.code : undefined,
      from: "program",
      returnProgram: p.id,
    });
  });

  // Dasturning o'z stipendiyasi yo'q — davlat grantlariga yo'naltiramiz.
  const toGrants = document.getElementById("sheet-to-grants");
  if (toGrants) {
    toGrants.addEventListener("click", () => {
      haptic("light");
      // Ilgari barcha davlatlar ochilardi — Malayziya dasturidan kelgan odam
      // AQSH va Buyuk Britaniya grantlarini ko'rardi.
      scholarshipCountryId = p.country ? p.country.id : null;
      switchTab("scholarships");
    });
  }

  const grantBtn = document.querySelector(".sheet-scholarship");
  if (grantBtn) {
    grantBtn.addEventListener("click", () => {
      haptic("light");
      const url = grantBtn.dataset.url;
      if (tg && typeof tg.openLink === "function") tg.openLink(url);
      else window.open(url, "_blank", "noopener");
    });
  }

  document.getElementById("sheet-open-site").addEventListener("click", () => {
    haptic("light");
    const url = p.source_url || p.university_website;
    if (tg && typeof tg.openLink === "function") tg.openLink(url);
    else window.open(url, "_blank", "noopener");
  });

  const saveBtn = document.getElementById("sheet-save");
  if (!p.saved) {
    saveBtn.addEventListener("click", async () => {
      haptic("light");
      await api(`/saved/${p.id}`, { method: "POST" });
      saveBtn.disabled = true;
      saveBtn.classList.add("is-saved");
      haptic("success");
      showToast(t("match.saved_toast"));
    });
  }
}

// ---- Grant sahifasi ----
// Dastur sahifasi bilan bir xil: to'liq sahifa, kalit faktlar kartasi, oq
// bo'lim kartalari, pastda rasmiy sayt tugmasi. Ma'lumot ro'yxatdan keladi —
// alohida so'rov kerak emas.
let grantPageData = null;
let grantReturnTab = "scholarships";

function openScholarshipPage(s) {
  haptic("light");
  if (currentTab !== "grant" && currentTab !== "mentor") grantReturnTab = currentTab;
  grantPageData = s;
  closeSheet();
  return switchTab("grant");
}

function leaveGrantPage() {
  haptic("light");
  switchTab(grantReturnTab && grantReturnTab !== "grant" ? grantReturnTab : "scholarships");
}

function renderGrantPage() {
  const el = document.getElementById("view-grant");
  const s = grantPageData;
  if (!s) return switchTab("scholarships");
  document.body.classList.add("page-mode");
  showPageBack(leaveGrantPage);

  const row = (label, value) =>
    `<div class="sheet-row"><span class="sheet-row-label">${label}</span><span class="sheet-row-value">${value}</span></div>`;

  const dash = t("scholarships.not_specified");
  const stipend = stipendText(s) || dash;

  // Daraja/muddat/til/bosqich — hammasi raqam yoki kalit sifatida saqlanadi,
  // shuning uchun jumla foydalanuvchi tilida shu yerda yig'iladi.
  const degrees = (s.degree_levels || [])
    .map((d) => t("profile.degree_level." + d))
    .join(", ");
  const duration =
    s.duration_min_years
      ? s.duration_max_years && s.duration_max_years !== s.duration_min_years
        ? `${s.duration_min_years}–${s.duration_max_years} ${t("program.years")}`
        : `${s.duration_min_years} ${t("program.years")}`
      : dash;
  const langScore = [
    s.ielts_min ? `IELTS ${s.ielts_min}` : "",
    s.toefl_min ? `TOEFL ${s.toefl_min}` : "",
  ]
    .filter(Boolean)
    .join(" / ");
  // Talablar: tizimli maydonlar ham, admin yozgan matn ham bitta savolga
  // javob beradi — "nima talab qilinadi". Shuning uchun ular bitta ro'yxatga
  // qo'shiladi; qiymati yo'q maydon umuman ko'rsatilmaydi.
  const requirementLines = [];
  if (!s.citizenship_eligible) {
    requirementLines.push(t("scholarships.req_citizenship_no"));
  }
  if (langScore) requirementLines.push(t("scholarships.req_language", { score: langScore }));
  if (s.work_experience_years !== null && s.work_experience_years !== undefined) {
    requirementLines.push(
      s.work_experience_years === 0
        ? t("scholarships.req_no_work")
        : t("scholarships.req_work", { years: s.work_experience_years })
    );
  }
  if (s.age_limit !== null && s.age_limit !== undefined) {
    requirementLines.push(t("scholarships.req_age", { age: s.age_limit }));
  }
  if (s.selection_stages) {
    requirementLines.push(t("scholarships.req_stages", { n: s.selection_stages }));
  }
  requirementLines.push(
    t(
      s.application_linked_to_program
        ? "scholarships.req_separate"
        : "scholarships.req_one_application"
    )
  );
  requirementLines.push(...(s.requirements_text || "").split("\n").filter(Boolean));

  const requirements = requirementLines.length
    ? `<ul class="doc-list">${requirementLines
        .map((line) => `<li>${icon("check")}${escapeHtml(line)}</li>`)
        .join("")}</ul>`
    : `<div class="sheet-empty">${t("scholarships.no_requirements")}</div>`;

  const deadlines = s.deadlines.length
    ? s.deadlines
        .map((d) => {
          const left =
            d.days_left !== null && d.days_left >= 0
              ? t("scholarships.days_left", { days: d.days_left })
              : t("scholarships.deadline_passed");
          return row(
            t("deadline." + d.type),
            `${escapeHtml(d.date.split(" ")[0])} <span class="sheet-muted">· ${left}</span>`
          );
        })
        .join("")
    : `<div class="card-sub">${t("scholarships.not_specified")}</div>`;

  const extraChips = [
    [s.extras_flight, "plane", "scholarships.extra_flight"],
    [s.extras_insurance, "shield", "scholarships.extra_insurance"],
    [s.extras_dormitory, "bed", "scholarships.extra_dormitory"],
    [s.extras_language_course, "lang", "scholarships.extra_language"],
  ]
    .filter(([on]) => on)
    .map(([, ic, key]) => `<span class="pg-extra">${icon(ic)}${t(key)}</span>`)
    .join("");

  const openDl = s.deadlines.find((d) => d.type === "application_open");
  const closeDate = s.nearest_deadline ? s.nearest_deadline.split(" ")[0] : "";
  const daysLeft =
    s.nearest_deadline_days_left !== null && s.nearest_deadline_days_left !== undefined && s.nearest_deadline_days_left >= 0
      ? s.nearest_deadline_days_left
      : null;
  const dlChip = s.closed
    ? `<span class="pg-chip is-closed">${t("scholarships.closed_badge")}</span>`
    : daysLeft !== null
      ? `<span class="pg-chip ${daysLeft <= 7 ? "is-urgent" : "is-soon"}"><i></i>${t(
          "scholarships.days_left",
          { days: daysLeft }
        )}</span>`
      : "";
  const fact = (label, value) =>
    `<div class="pg-fact"><span>${label}</span><b>${value || "—"}</b></div>`;
  const section = (title, body) => `<section class="pg-card"><h3>${title}</h3>${body}</section>`;

  const first = s.countries[0];
  const countryPill = first
    ? `<span class="pg-country"><span class="chip-flag">${flag(first.iso_code)}</span>${escapeHtml(
        s.countries.length > 1 ? t("profile.countries_count", { n: s.countries.length }) : countryName(first)
      )}</span>`
    : "<span></span>";

  // Shu davlatdagi mentor (Uni Buddy) — savol guruhga ketadi.
  const mentorOn = mentorConfig && mentorConfig.enabled && first;
  const mentorCountry = mentorOn
    ? mentorConfig.countries.find((c) => c.code === String(first.iso_code).toUpperCase())
    : null;
  const mentorCard = mentorOn
    ? `<button type="button" class="pg-mentor" id="pg-mentor">
         <img src="icon-buddy.png?v=${ASSET_V}" alt="" aria-hidden="true">
         <span class="pg-mentor-text">
           <span class="pg-mentor-title">${t("program.ask_mentor", {
             country: escapeHtml(countryName(first)),
           })}</span>
           <span class="pg-mentor-sub">${t("buddy.tagline")}</span>
         </span>
         <span class="pg-mentor-go">${icon("arrow")}</span>
       </button>`
    : "";

  el.innerHTML = `
    <div class="pg">
      <div class="pg-top">
        <button type="button" class="pg-back" id="pg-back" aria-label="${t("common.back")}">${icon(
          "chevron"
        )}</button>
        ${s.cover_url ? "" : countryPill}
      </div>
      ${
        s.cover_url
          ? `<div class="pg-cover">
               <img src="${escapeHtml(s.cover_url)}" alt="" loading="eager" onerror="this.style.visibility='hidden'">
               ${countryPill.replace('class="pg-country"', 'class="pg-country pg-cover-pill"')}
             </div>`
          : ""
      }
      <div class="pg-hero${s.cover_url ? " has-cover" : ""}">${avatar(s.name, s.logo)}</div>
      <h2 class="pg-title">${escapeHtml(s.name)}</h2>
      ${
        s.countries.length > 1
          ? `<div class="pg-sub">${s.countries.map((c) => escapeHtml(countryName(c))).join(" · ")}</div>`
          : ""
      }
      <div class="pg-chips">
        ${dlChip}
        <span class="pg-chip ${s.coverage_type === "full" ? "is-full" : ""}">${t(
          "scholarships.coverage." + s.coverage_type
        )}</span>
        ${degrees ? `<span class="pg-chip">${escapeHtml(degrees)}</span>` : ""}
      </div>

      <div class="pg-facts">
        ${fact(
          t("scholarships.stipend"),
          // Ustun tor — faqat summa; davri ("oyiga") pastdagi bo'limda.
          s.stipend_amount ? `${Number(s.stipend_amount).toLocaleString()} ${escapeHtml(s.currency)}` : ""
        )}
        ${fact(t("program.closes"), closeDate ? shortDate(closeDate) : "")}
        ${fact(t("program.left"), daysLeft !== null ? t("program.days_n", { n: daysLeft }) : "")}
      </div>
      <div class="pg-source">${t("scholarships.verify_hint")}</div>

      ${s.description ? section(t("scholarships.about"), `<div class="sheet-text">${escapeHtml(s.description)}</div>`) : ""}
      ${section(
        t("scholarships.money"),
        row(t("scholarships.stipend"), escapeHtml(stipend)) +
          (extraChips ? `<div class="pg-extras">${extraChips}</div>` : "")
      )}
      ${section(
        t("scholarships.study"),
        row(t("scholarships.degree_levels"), degrees || dash) +
          row(t("scholarships.duration"), duration) +
          row(
            t("program.language"),
            s.study_language ? escapeHtml(instructionLanguage(s.study_language)) : dash
          ) +
          row(t("scholarships.uni_choice"), t("scholarships.uni_choice." + s.university_choice)) +
          (s.universities_text ? row(t("scholarships.universities"), multiline(s.universities_text)) : "") +
          (s.selected_by ? row(t("scholarships.selected_by"), escapeHtml(s.selected_by)) : "")
      )}
      ${section(t("scholarships.requirements"), requirements)}
      ${section(t("scholarships.deadlines"), deadlines)}
      ${mentorCard}
    </div>

    <div class="pg-bar">
      <button type="button" class="btn btn-accent pg-open" id="grant-open-site">
        ${t("scholarships.official_site")}
      </button>
    </div>
  `;

  document.getElementById("pg-back").addEventListener("click", leaveGrantPage);
  document.getElementById("grant-open-site").addEventListener("click", () => {
    haptic("light");
    // Telegram ichida tashqi havolani to'g'ri ochish usuli.
    if (tg && typeof tg.openLink === "function") tg.openLink(s.source_url);
    else window.open(s.source_url, "_blank", "noopener");
  });
  document.getElementById("pg-mentor")?.addEventListener("click", () => {
    haptic("light");
    openMentor(mentorCountry ? "form" : "countries", {
      country: mentorCountry ? mentorCountry.code : undefined,
      from: "grant",
      returnGrant: true,
    });
  });
}

// ============ Saved ============

const SAVED_STATUSES = ["planning", "applied", "rejected", "accepted"];

// Deadline badge rangi: 14 kundan kam — qizil, 60 kundan kam — sariq,
// qolgani — kulrang. `month` turi uchun oyning 1-sanasi asos qilinadi.
function deadlineTone(days) {
  if (days === null || days === undefined) return "";
  if (days < 14) return "red";
  if (days < 60) return "amber";
  return "";
}

// `month` turidagi dastur uchun keyingi kelish sanasi (o'sha oyning 1-kuni).
// Serverdagi `next_month_occurrence` bilan bir xil qoida: oy bu yil tugagan
// bo'lsa, keyingi yil olinadi.
function nextMonthStart(month) {
  const today = new Date();
  const year = today.getFullYear();
  const thisYear = new Date(year, month - 1, 1);
  const monthEnd = new Date(year, month, 0);
  return monthEnd < today ? new Date(year + 1, month - 1, 1) : thisYear;
}

function daysUntil(when) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((when - today) / 86400000);
}

/** Kartani saralash va badge uchun kerakli raqam.
 *  exact -> deadline'gacha kun; month -> oy boshigacha kun; unknown -> null. */
function savedDaysLeft(s) {
  if (s.deadline_precision === "exact") return s.nearest_deadline_days_left;
  if (s.deadline_precision === "month" && s.deadline_month) {
    return daysUntil(nextMonthStart(s.deadline_month));
  }
  return null;
}

// Tartib: avval exact (eng yaqini tepada), keyin month, oxirida unknown.
const PRECISION_ORDER = { exact: 0, month: 1, unknown: 2 };

function compareSaved(a, b) {
  const byPrecision =
    (PRECISION_ORDER[a.deadline_precision] ?? 9) - (PRECISION_ORDER[b.deadline_precision] ?? 9);
  if (byPrecision !== 0) return byPrecision;
  const left = savedDaysLeft(a);
  const right = savedDaysLeft(b);
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  return left - right;
}

function deadlineLabel(s) {
  if (s.deadline_precision === "exact") {
    const days = s.nearest_deadline_days_left;
    const date = (s.nearest_deadline || "").split(" ")[0];
    return days !== null && days >= 0
      ? `${date} · ${t("saved.days_left", { days })}`
      : date || t("saved.no_deadline");
  }
  if (s.deadline_precision === "month" && s.deadline_month) {
    return t("saved.month_hint", { month: t("month." + s.deadline_month) });
  }
  return t("saved.unknown_hint");
}

function savedCard(s) {
  const days = savedDaysLeft(s);
  const tone = s.closed ? "" : deadlineTone(days);
  const stateTags = [];
  if (s.status === "applied") {
    stateTags.push(`<span class="pill green">${icon("check")}${t("saved.tag_applied")}</span>`);
  }
  if (!s.reminders_active) {
    stateTags.push(`<span class="pill">${t("saved.tag_muted")}</span>`);
  }

  // Tugmalar faqat shu BITTA dasturga ta'sir qiladi.
  const actions = [];
  if (s.official_url) {
    actions.push(
      `<button type="button" class="btn btn-quiet site-btn" data-url="${escapeHtml(
        s.official_url
      )}">${t("saved.btn_site")}</button>`
    );
  }
  // Eslatma o'chiq bo'lsa ham qayta yoqish imkoni doim bor.
  actions.push(
    s.reminders_active
      ? `<button type="button" class="btn btn-quiet mute-btn" data-id="${s.id}">${t(
          "saved.btn_mute"
        )}</button>`
      : `<button type="button" class="btn btn-quiet unmute-btn" data-id="${s.id}">${t(
          "saved.btn_unmute"
        )}</button>`
  );
  if (s.deadline_precision === "unknown") {
    actions.push(
      `<button type="button" class="btn btn-quiet suggest-btn" data-program="${s.program_id}">${t(
        s.has_pending_suggestion ? "saved.btn_suggested" : "saved.btn_suggest"
      )}</button>`
    );
  }
  actions.push(
    `<button type="button" class="btn btn-quiet remove-btn" data-id="${s.id}">${icon("trash")}${t(
      "saved.remove"
    )}</button>`
  );

  return `
    <div class="card" data-saved-id="${s.id}" data-program-id="${s.program_id}">
      <div class="card-top program-open" data-id="${s.program_id}" role="button" tabindex="0">
        ${avatar(s.university, s.university_logo)}
        <div class="card-body">
          <div class="card-title">${escapeHtml(s.program_name)}</div>
          <div class="card-sub">${escapeHtml(s.university)}, ${flag(
            s.country.iso_code
          )} ${escapeHtml(countryName(s.country))}</div>
          <div class="meta-row">
            <span class="pill ${tone}">${icon("clock")}${escapeHtml(deadlineLabel(s))}</span>
            ${stateTags.join("")}
          </div>
        </div>
        <span class="card-chevron">${icon("chevron")}</span>
      </div>
      <div class="seg" data-id="${s.id}">
        ${SAVED_STATUSES.map(
          (st) =>
            `<div class="seg-item ${st === s.status ? "active" : ""}" data-status="${st}">${t(
              "saved.status." + st
            )}</div>`
        ).join("")}
      </div>
      <div class="card-actions saved-actions">${actions.join("")}</div>
    </div>`;
}

async function renderSaved() {
  const el = document.getElementById("view-saved");
  el.innerHTML = skeletons(3);

  const items = await api("/saved");
  if (!items.length) {
    el.innerHTML = `
      <div class="empty">
        <div class="empty-ico">${icon("bookmark")}</div>
        <div class="empty-title">${t("saved.empty_title")}</div>
        <div class="empty-text">${t("saved.empty_text")}</div>
      </div>`;
    return;
  }

  const open = items.filter((s) => !s.closed).sort(compareSaved);
  const closed = items.filter((s) => s.closed).sort(compareSaved);
  const urgent = open.filter((s) => {
    const days = savedDaysLeft(s);
    return days !== null && days >= 0 && days < 14;
  }).length;

  // Eslatmalar butunlay o'chirilgan bo'lsa, buni shu yerda aytamiz: odam
  // deadline'ni kuzatish uchun aynan shu sahifaga keladi.
  const banner =
    profile && profile.notifications_enabled === false
      ? `<div class="alert">
           <div class="alert-ico">${icon("clock")}</div>
           <div class="card-body">
             <div class="alert-title">${t("saved.notif_off_title")}</div>
             <div class="alert-body">${t("saved.notif_off_text")}</div>
           </div>
           <button type="button" class="btn btn-accent" id="notif-on-btn">${t(
             "saved.notif_on_btn"
           )}</button>
         </div>`
      : "";

  el.innerHTML = `
    ${banner}
    ${
      urgent
        ? `<div class="section-head"><span class="section-title">${t("saved.urgent", {
            n: urgent,
          })}</span></div>`
        : ""
    }
    ${open.map(savedCard).join("")}
    ${
      closed.length
        ? `<div class="section-head"><span class="section-title">${t(
            "saved.closed_section"
          )}</span></div>${closed.map(savedCard).join("")}`
        : ""
    }`;

  bindProgramOpeners(el);
  bindSavedActions(el);
}

function bindSavedActions(el) {
  const onBtn = el.querySelector("#notif-on-btn");
  if (onBtn) {
    onBtn.addEventListener("click", async () => {
      haptic("light");
      await api("/me", {
        method: "PATCH",
        body: JSON.stringify({ notifications_enabled: true }),
      });
      if (profile) profile.notifications_enabled = true;
      showToast(t("profile.notif_on_toast"));
      await renderSaved();
    });
  }

  el.querySelectorAll(".site-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("light");
      const url = btn.dataset.url;
      if (tg && typeof tg.openLink === "function") tg.openLink(url);
      else window.open(url, "_blank", "noopener");
    });
  });

  // Ariza natijasi — segment tugma orqali. "Ariza berilgan" tanlansa shu
  // dastur bo'yicha eslatmalar ham to'xtaydi (serverda).
  el.querySelectorAll(".seg").forEach((seg) => {
    seg.querySelectorAll(".seg-item").forEach((item) => {
      item.addEventListener("click", async () => {
        if (item.classList.contains("active")) return;
        haptic("light");
        await api(`/saved/${seg.dataset.id}`, {
          method: "PATCH",
          body: JSON.stringify({ status: item.dataset.status }),
        });
        await renderSaved();
      });
    });
  });

  el.querySelectorAll(".mute-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      haptic("light");
      await api(`/saved/${btn.dataset.id}`, {
        method: "PATCH",
        body: JSON.stringify({ reminders_active: false }),
      });
      showToast(t("saved.muted_toast"));
      await renderSaved();
    });
  });

  el.querySelectorAll(".unmute-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      haptic("light");
      await api(`/saved/${btn.dataset.id}`, {
        method: "PATCH",
        body: JSON.stringify({ reminders_active: true }),
      });
      showToast(t("saved.unmuted_toast"));
      await renderSaved();
    });
  });

  el.querySelectorAll(".suggest-btn").forEach((btn) => {
    btn.addEventListener("click", () => openSuggestSheet(Number(btn.dataset.program)));
  });

  // Olib tashlash darhol bajarilmaydi: karta yashiriladi va 5 soniya
  // "Bekor qilish" imkoni beriladi. Ilgari na tasdiq, na qaytarish bor edi —
  // tasodifiy bosish dasturni butunlay o'chirib yuborardi.
  el.querySelectorAll(".remove-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      haptic("medium");
      const card = btn.closest(".card");
      card.hidden = true;
      showUndoToast(
        t("saved.removed_toast"),
        () => {
          card.hidden = false;
        },
        async () => {
          try {
            await api(`/saved/${btn.dataset.id}`, { method: "DELETE" });
          } catch (err) {
            card.hidden = false;
            showToast(err.message);
            return;
          }
          card.remove();
          if (!el.querySelector(".card")) await renderSaved();
        }
      );
    });
  });
}

/** "Sanani bilaman" — deadline'i noma'lum dasturlar uchun.
 *  Taklif to'g'ridan-to'g'ri katalogga tushmaydi: admin tasdiqlaydi. */
function openSuggestSheet(programId) {
  haptic("light");
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  const today = new Date().toISOString().slice(0, 10);
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("suggest.title")}</div>
    <p class="sheet-text">${t("suggest.text")}</p>
    <div class="field">
      <label>${t("suggest.date_label")}</label>
      <input type="date" id="suggest-date" min="${today}" value="">
    </div>
    <button type="button" class="btn btn-accent btn-block" id="suggest-send">${t(
      "suggest.send"
    )}</button>`,
    sheet
  );

  sheet.querySelector("#suggest-send").addEventListener("click", async () => {
    const value = sheet.querySelector("#suggest-date").value;
    if (!value) return;
    haptic("light");
    try {
      await api("/deadline-suggestions", {
        method: "POST",
        body: JSON.stringify({ program_id: programId, suggested_date: value }),
      });
      closeSheet();
      showToast(t("suggest.thanks"));
      await renderSaved();
    } catch (err) {
      showToast(err.message);
    }
  });
}

// ============ Profile ============

const RANK_RANGES = ["1-100", "101-300", "301-500", "500+"];

// ============ Filtr: qadamli onboarding ============
//
// Ilgari filtr bitta uzun sahifa edi (daraja, yo'nalish, GPA, til, davlatlar,
// reyting, ariza to'lovi) — yangi foydalanuvchi uni ko'rib cho'chib qolardi.
// Endi har bir savol alohida ekranda, tepada qadamlar chizig'i, pastda
// "Davom etish". GPA so'ralmaydi — moslik unga qaramaydi
// (app/services/matching_service.py).
//
// Javoblar `wiz.draft` da yig'iladi va faqat oxirgi qadamda saqlanadi:
// yarim yo'lda chiqib ketgan odamning eski filtri buzilmaydi.

const WIZ_STEPS = ["degree", "field", "countries", "language", "english", "prefs"];
const IELTS_SCORES = ["4.0", "4.5", "5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0", "8.5", "9.0"];

let wiz = null;
// init() da to'ldiriladi; onboarding savollari katalog yuklanishini kutadi.
let catalogReady = Promise.resolve();
// Filtrni ma'lum bir savoldan ochish uchun (masalan "Davlatlar" tugmasi).
let wizEntryStep = null;

// Filtri bo'sh odamga har safar, filtri bor-u onboarding'ni hali ko'rmaganga
// (eski filtr sahifasida to'ldirgan) — bir marta.
function needsOnboarding() {
  return !hasFilter() || !profile.onboarding_done;
}

// Onboarding tugatildi yoki o'tkazib yuborildi — 3 kun davomida qayta chiqmaydi
// (muddatni server hisoblaydi: `profile.onboarding_done`).
function markOnboardingDone() {
  if (profile.onboarding_done) return;
  profile.onboarding_done = true;
  api("/me", { method: "PATCH", body: JSON.stringify({ onboarding_done: true }) }).catch(() => {});
}

function openFilter(step) {
  wizEntryStep = step || null;
  switchTab("filter");
}

function wizDraftFromProfile() {
  const cert = profile.language_certificates[0];
  return {
    degree_level: profile.degree_level || "",
    field_id: profile.field_id || null,
    target_country_ids: (profile.target_country_ids || []).map(Number),
    study_language: profile.study_language || "",
    // null — savolga javob berilmagan (saqlanganiga tegilmaydi), "none" — sertifikat yo'q
    cert_type: cert ? cert.type : null,
    cert_score: cert ? String(cert.score) : "",
    university_rank_range: profile.university_rank_range || "",
  };
}

function renderFilter() {
  const entry = WIZ_STEPS.indexOf(wizEntryStep);
  wizEntryStep = null;
  // Yangi foydalanuvchiga avval kutib olish ekrani; filtri borga — darhol savollar.
  const step = entry >= 0 ? entry : needsOnboarding() ? -1 : 0;
  wiz = { step, firstStep: step, draft: wizDraftFromProfile() };
  document.body.classList.add("no-tabbar", "wizard-mode");
  drawWizard();
}

function leaveWizard() {
  switchTab(previousTab && previousTab !== "filter" ? previousTab : "home");
}

async function wizGo(step) {
  haptic("light");
  if (step < -1 || (step === -1 && wiz.firstStep !== -1)) {
    leaveWizard();
    return;
  }
  if (step >= WIZ_STEPS.length) {
    await findPrograms();
    return;
  }
  wiz.step = step;
  await drawWizard();
  window.scrollTo({ top: 0 });
}

async function drawWizard() {
  const el = document.getElementById("view-filter");
  if (wiz.step === -1) {
    el.innerHTML = `
      <div class="wz wz-welcome">
        <div class="wz-top"><span></span><button type="button" class="wz-skip" id="wz-skip">${t(
          "wizard.skip"
        )}</button></div>
        <div class="wz-hero">
          <div class="wz-logo"><img src="logo-mark.png?v=${ASSET_V}" alt="" aria-hidden="true"></div>
          <h1 class="wz-brand">Uni Assist</h1>
          <p class="wz-tagline">${t("wizard.tagline")}</p>
        </div>
        <div class="wz-foot">
          <button type="button" class="btn btn-accent btn-block" id="wz-next">${t("wizard.start")}</button>
        </div>
      </div>`;
    document.getElementById("wz-skip").addEventListener("click", () => {
      haptic("light");
      markOnboardingDone();
      leaveWizard();
    });
    document.getElementById("wz-next").addEventListener("click", () => wizGo(0));
    return;
  }

  await catalogReady;
  const key = WIZ_STEPS[wiz.step];
  if (key === "field") {
    // Yo'nalishlar darajaga bog'liq: bakalavrga faqat PhD'da bor yo'nalish chiqmasin.
    await loadMajors(wiz.draft.degree_level || null);
    if (wiz.draft.field_id && !majors.some((m) => m.id === wiz.draft.field_id)) wiz.draft.field_id = null;
  }
  const last = wiz.step === WIZ_STEPS.length - 1;
  const progress = WIZ_STEPS.map((_, i) => `<span class="${i <= wiz.step ? "on" : ""}"></span>`).join("");
  const hint = key === "countries" ? `<p class="wz-hint">${t("wizard.hint.countries")}</p>` : "";

  el.innerHTML = `
    <div class="wz">
      <div class="wz-top">
        <button type="button" class="wz-back" id="wz-back" aria-label="${t("common.back")}">${icon("chevron")}</button>
        <div class="wz-progress">${progress}</div>
        <button type="button" class="wz-skip" id="wz-skip">${t("wizard.skip")}</button>
      </div>
      <h1 class="wz-title">${t("wizard.q." + key)}</h1>
      ${hint}
      <div class="wz-body" id="wz-body">${wizStepBody(key)}</div>
      <div class="wz-foot">
        <button type="button" class="btn btn-accent btn-block" id="${last ? "find-programs-btn" : "wz-next"}">
          ${last ? icon("spark") + t("profile.find") : t("wizard.next")}
        </button>
        ${
          last && hasFilter()
            ? `<button type="button" class="btn btn-quiet btn-block" id="reset-profile-btn">${t(
                "profile.reset"
              )}</button>`
            : ""
        }
      </div>
    </div>`;

  document.getElementById("wz-back").addEventListener("click", () => wizGo(wiz.step - 1));
  document.getElementById("wz-skip").addEventListener("click", () => wizGo(wiz.step + 1));
  document
    .getElementById(last ? "find-programs-btn" : "wz-next")
    .addEventListener("click", () => wizGo(wiz.step + 1));
  document.getElementById("reset-profile-btn")?.addEventListener("click", resetProfile);
  bindWizStep(key);
  syncWizNext();
}

function wizOption(value, label, active, opts = {}) {
  return `
    <button type="button" class="wz-opt${active ? " active" : ""}${opts.multi ? " is-multi" : ""}" data-value="${escapeHtml(
      String(value)
    )}">
      ${opts.flag ? `<span class="wz-flag">${opts.flag}</span>` : ""}
      <span class="wz-opt-label">${escapeHtml(label)}</span>
      <span class="wz-mark">${icon("check")}</span>
    </button>`;
}

function wizStepBody(key) {
  const d = wiz.draft;
  if (key === "degree") {
    return ["bachelor", "master", "phd"]
      .map((v) => wizOption(v, t("profile.degree_level." + v), d.degree_level === v))
      .join("");
  }
  if (key === "field") {
    if (!majors.length) return `<p class="wz-hint">${escapeHtml(t("profile.major_empty"))}</p>`;
    return (
      wizOption("", t("profile.study_language_any"), !d.field_id) +
      majors.map((m) => wizOption(m.id, fieldName(m), d.field_id === m.id)).join("")
    );
  }
  if (key === "countries") {
    const all = countries.length > 0 && countries.every((c) => d.target_country_ids.includes(c.id));
    return (
      wizOption("all", t("profile.countries_all"), all, { multi: true, flag: icon("globe") }) +
      countries
        .map((c) =>
          wizOption(c.id, countryName(c), d.target_country_ids.includes(c.id), {
            multi: true,
            flag: flag(c.iso_code),
          })
        )
        .join("")
    );
  }
  if (key === "language") {
    return (
      wizOption("", t("profile.study_language_any"), !d.study_language) +
      studyLanguages.map((v) => wizOption(v, instructionLanguage(v), d.study_language === v)).join("")
    );
  }
  if (key === "english") {
    const score =
      d.cert_type === "IELTS"
        ? `<div class="wz-sub">${t("wizard.score_ielts")}</div>
           <div class="wz-scores" id="wz-ielts">${IELTS_SCORES.map(
             (v) =>
               `<button type="button" class="wz-score${Number(d.cert_score) === Number(v) ? " active" : ""}" data-value="${v}">${v}</button>`
           ).join("")}</div>`
        : d.cert_type === "TOEFL"
          ? `<div class="wz-sub">${t("wizard.score_toefl")}</div>
             <input type="text" inputmode="numeric" autocomplete="off" class="wz-input" id="wz-toefl"
                    placeholder="90" value="${escapeHtml(d.cert_score)}">`
          : "";
    return (
      wizOption("none", t("wizard.cert_none"), d.cert_type === "none") +
      wizOption("IELTS", "IELTS", d.cert_type === "IELTS") +
      wizOption("TOEFL", "TOEFL iBT", d.cert_type === "TOEFL") +
      score
    );
  }
  // prefs: universitet reytingi
  return `
    <div class="wz-group" data-group="rank">
      ${[{ v: "", l: t("profile.rank_any") }]
        .concat(RANK_RANGES.map((r) => ({ v: r, l: r })))
        .map((o) => wizOption(o.v, o.l, d.university_rank_range === o.v))
        .join("")}
    </div>`;
}

function bindWizStep(key) {
  const body = document.getElementById("wz-body");
  const d = wiz.draft;
  const single = (container, onPick) => {
    container.querySelectorAll(":scope > .wz-opt").forEach((btn) => {
      btn.addEventListener("click", () => {
        haptic("light");
        container.querySelectorAll(":scope > .wz-opt").forEach((b) => b.classList.toggle("active", b === btn));
        onPick(btn.dataset.value);
      });
    });
  };

  if (key === "degree") single(body, (v) => (d.degree_level = v));
  if (key === "field") single(body, (v) => (d.field_id = v ? Number(v) : null));
  if (key === "language") single(body, (v) => (d.study_language = v));
  if (key === "prefs") {
    single(body.querySelector('[data-group="rank"]'), (v) => (d.university_rank_range = v));
  }
  if (key === "countries") {
    const rows = () => Array.from(body.querySelectorAll('.wz-opt:not([data-value="all"])'));
    const allRow = body.querySelector('[data-value="all"]');
    const sync = () => {
      d.target_country_ids = rows()
        .filter((r) => r.classList.contains("active"))
        .map((r) => Number(r.dataset.value));
      allRow.classList.toggle("active", rows().every((r) => r.classList.contains("active")));
    };
    rows().forEach((row) =>
      row.addEventListener("click", () => {
        haptic("light");
        row.classList.toggle("active");
        sync();
      })
    );
    allRow.addEventListener("click", () => {
      haptic("light");
      const on = !allRow.classList.contains("active");
      rows().forEach((r) => r.classList.toggle("active", on));
      sync();
    });
  }
  if (key === "english") {
    body.querySelectorAll(":scope > .wz-opt").forEach((btn) => {
      btn.addEventListener("click", async () => {
        haptic("light");
        if (d.cert_type !== btn.dataset.value) d.cert_score = "";
        d.cert_type = btn.dataset.value;
        // Ball maydoni turga qarab almashadi — qadam qayta chiziladi.
        body.innerHTML = wizStepBody("english");
        bindWizStep("english");
        syncWizNext();
      });
    });
    body.querySelectorAll(".wz-score").forEach((btn) => {
      btn.addEventListener("click", () => {
        haptic("light");
        body.querySelectorAll(".wz-score").forEach((b) => b.classList.toggle("active", b === btn));
        d.cert_score = btn.dataset.value;
        syncWizNext();
      });
    });
    document.getElementById("wz-toefl")?.addEventListener("input", (event) => {
      d.cert_score = decimalValue(event.target);
      syncWizNext();
    });
  }
}

// IELTS/TOEFL tanlangan-u, ball kiritilmagan bo'lsa davom etib bo'lmaydi:
// aks holda sertifikat jimgina saqlanmay qolardi.
function syncWizNext() {
  const d = wiz.draft;
  const btn = document.getElementById("wz-next") || document.getElementById("find-programs-btn");
  if (!btn || WIZ_STEPS[wiz.step] !== "english") return;
  const toefl = Number(d.cert_score);
  btn.disabled =
    (d.cert_type === "IELTS" && !d.cert_score) ||
    (d.cert_type === "TOEFL" && !(d.cert_score && toefl >= 0 && toefl <= 120));
}

function bindChips(containerId, onChange, multi) {
  const container = document.getElementById(containerId);
  container.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      haptic("light");
      if (multi) {
        chip.classList.toggle("active");
      } else {
        container.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
      }
      if (onChange) onChange(chip.dataset.value);
    });
  });
}

function activeChip(containerId) {
  const el = document.querySelector(`#${containerId} .chip.active`);
  return el ? el.dataset.value : null;
}

function activeChips(containerId) {
  return Array.from(document.querySelectorAll(`#${containerId} .chip.active`)).map((c) => c.dataset.value);
}

/** Matn maydonidan o'nlik sonni o'qiydi.
 *
 * Maydonlar `type="text"`: vergulli lokalda `type="number"` nuqtani yutib
 * yuborardi. Shuning uchun vergul ham qabul qilinadi va bu yerda nuqtaga
 * keltiriladi. Raqam, nuqta va verguldan boshqa hamma narsa tashlanadi.
 */
function decimalValue(el) {
  if (!el) return "";
  const raw = String(el.value || "")
    .replace(/,/g, ".")
    .replace(/[^0-9.]/g, "");
  // Bir nechta nuqta yozilsa — birinchisidan keyingilari tashlanadi.
  const first = raw.indexOf(".");
  return first === -1
    ? raw
    : raw.slice(0, first + 1) + raw.slice(first + 1).replace(/\./g, "");
}

async function saveProfile() {
  const d = wiz.draft;
  const payload = {
    ui_language: lang,
    onboarding_done: true,
    target_country_ids: d.target_country_ids,
    // Har doim yuboriladi: bo'sh qiymat = "farqi yo'q" (tanlov tozalanadi).
    field_id: d.field_id,
    study_language: d.study_language,
    university_rank_range: d.university_rank_range,
  };
  if (d.degree_level) payload.degree_level = d.degree_level;
  if (d.cert_type === "none") {
    payload.language_cert_type = "";
  } else if (d.cert_type && d.cert_score) {
    payload.language_cert_type = d.cert_type;
    payload.language_cert_score = parseFloat(d.cert_score);
  }
  profile = await api("/me", { method: "PATCH", body: JSON.stringify(payload) });
}

// ---- "Mos dasturlarni topish" ----
// Oyna faqat vizual: tanlov mantiqi — serverdagi o'sha eski filtrning o'zi.
// Hech qanday tashqi xizmat yoki model chaqirilmaydi, shuning uchun matnlarda
// ham "AI" deyilmaydi — faqat nima qilinayotgani aytiladi.

const FINDING_MS = 2200;

function showFindingOverlay() {
  let el = document.getElementById("finding-overlay");
  if (!el) {
    el = document.createElement("div");
    el.id = "finding-overlay";
    el.className = "finding";
    document.body.append(el);
  }
  // Yopilish animatsiyasi (260 ms) tugamasdan tugma qayta bosilsa, eski
  // o'chirish taymeri yangi oynani ham olib tashlab yuborardi.
  clearTimeout(el._hideTimer);
  el.innerHTML = `
    <div class="finding-card" role="status" aria-live="polite">
      <div class="finding-orb">
        <span class="finding-ring"></span>
        <span class="finding-ring finding-ring-2"></span>
        <span class="finding-ring finding-ring-3"></span>
        <span class="finding-core">${icon("spark")}</span>
      </div>
      <div class="finding-title">${t("finding.title")}</div>
      <div class="finding-steps">
        ${[1, 2, 3]
          .map(
            (n, i) => `
        <div class="finding-step" style="--d:${i * 620}ms">
          <span class="finding-step-dot"></span><span>${t("finding.step" + n)}</span>
        </div>`
          )
          .join("")}
      </div>
      <div class="finding-bar"><span style="--dur:${FINDING_MS}ms"></span></div>
    </div>`;
  document.body.style.overflow = "hidden";
  // Ochilish animatsiyasi ishga tushishi uchun klass keyingi kadrda qo'shiladi.
  requestAnimationFrame(() => el.classList.add("open"));
  return el;
}

function hideFindingOverlay() {
  const el = document.getElementById("finding-overlay");
  if (!el) return;
  el.classList.remove("open");
  document.body.style.overflow = "";
  el._hideTimer = setTimeout(() => el.remove(), 260);
}

async function findPrograms() {
  const btn = document.getElementById("find-programs-btn");
  if (btn) btn.disabled = true;
  haptic("light");
  try {
    // Filtr obuna tekshiruvidan OLDIN saqlanadi: kanalga o'tganda Telegram
    // ilovani yopib yuborishi mumkin va javoblar yo'qolmasligi kerak.
    await saveProfile();
    if (!(await ensureSubscribed())) return;
    await showResults();
  } catch (err) {
    haptic("error");
    showToast(err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ---- Majburiy kanal obunasi ----
// Bot /start'da to'smaydi: obuna onboarding oxirida, "Find my programs"
// bosilganda so'raladi. Haqiqiy tekshiruv serverda (`/subscription`); u
// adminkadagi ozod qilinganlar ro'yxatini ham hisobga oladi.

async function checkSubscription(fresh) {
  try {
    return await api(`/subscription${fresh ? "?fresh=1" : ""}`);
  } catch (e) {
    // Tekshiruvning o'zi ishlamasa qidiruvni TO'SMAYMIZ — server tomoni
    // ham shunday (fail-open): noto'g'ri sozlama hammani to'xtatmasin.
    console.error(e);
    return { subscribed: true, channels: [] };
  }
}

async function ensureSubscribed() {
  const status = await checkSubscription(false);
  if (status.subscribed) return true;
  return openSubscriptionSheet(status.channels);
}

function openChannelLink(url) {
  try {
    tg.openTelegramLink(url);
  } catch (e) {
    window.open(url, "_blank");
  }
}

// Kanalga o'tganda Telegram Mini App'ni yopib yuborishi mumkin. Belgi
// qolsa, keyingi ochilishda odam o'sha joyga — obuna dialogiga qaytadi.
const PENDING_RESULTS_KEY = "ua_pending_results";

function setPendingResults(on) {
  try {
    if (on) localStorage.setItem(PENDING_RESULTS_KEY, "1");
    else localStorage.removeItem(PENDING_RESULTS_KEY);
  } catch (e) {
    /* xususiy rejim — belgisiz ham ishlaydi */
  }
}

function hasPendingResults() {
  try {
    return localStorage.getItem(PENDING_RESULTS_KEY) === "1";
  } catch (e) {
    return false;
  }
}

/** O'rtadagi obuna dialogi. A'zo bo'lingach `true`, yopib ketilsa `false`.
 *  Kanaldan qaytganda (ilova yana ko'rinsa) a'zolik o'zi tekshiriladi. */
function openSubscriptionSheet(channels) {
  return new Promise((resolve) => {
    setPendingResults(true);
    document.getElementById("sub-gate")?.remove();
    const el = document.createElement("div");
    el.id = "sub-gate";
    el.className = "sg";

    const rows = (list) =>
      list
        .map(
          (c) => `
        <button type="button" class="sg-channel" data-url="${escapeHtml(c.invite_url)}">
          <span class="sg-channel-ava">${escapeHtml(initials(c.title))}</span>
          <span class="sg-channel-name">${escapeHtml(c.title)}</span>
          <span class="sg-channel-join">${t("sub.join")}</span>
        </button>`
        )
        .join("");

    el.innerHTML = `
      <div class="sg-card" role="dialog" aria-modal="true" aria-labelledby="sg-title">
        <button type="button" class="sg-close" id="sg-close" aria-label="${t("onboard.skip")}">${icon(
          "close"
        )}</button>
        <div class="sg-art">
          <span class="sg-halo"></span><span class="sg-halo sg-halo-2"></span>
          <img src="icon-bell.png?v=${ASSET_V}" alt="" aria-hidden="true">
        </div>
        <div class="sg-step">${t("sub.step")}</div>
        <div class="sg-title" id="sg-title">${t("sub.title")}</div>
        <div class="sg-text">${t("sub.text")}</div>
        <div class="sg-channels" id="sg-channels">${rows(channels)}</div>
        <button type="button" class="btn btn-accent btn-block" id="sg-check">
          ${icon("check")}${t("sub.check")}
        </button>
      </div>`;
    document.body.append(el);
    document.body.style.overflow = "hidden";
    requestAnimationFrame(() => el.classList.add("open"));

    const bindRows = () => {
      el.querySelectorAll(".sg-channel").forEach((row) => {
        row.addEventListener("click", () => {
          haptic("light");
          openChannelLink(row.dataset.url);
        });
      });
    };
    bindRows();

    let done = false;
    let checking = false;
    const finish = (ok) => {
      if (done) return;
      done = true;
      document.removeEventListener("visibilitychange", onReturn);
      try {
        tg?.offEvent?.("activated", onReturn);
      } catch (e) {
        /* eski klientlar */
      }
      // Yopib ketsa — keyingi ochilishda qayta chiqmasin.
      if (!ok) setPendingResults(false);
      el.classList.remove("open");
      document.body.style.overflow = "";
      setTimeout(() => el.remove(), 280);
      resolve(ok);
    };

    const recheck = async (silent) => {
      if (checking || done) return;
      checking = true;
      const btn = document.getElementById("sg-check");
      btn.disabled = true;
      try {
        const status = await checkSubscription(true);
        if (status.subscribed) {
          haptic("success");
          finish(true);
          return;
        }
        if (!silent) {
          haptic("warning");
          showToast(t("sub.still_missing"));
        }
        // A'zo bo'lingan kanallar ro'yxatdan tushadi.
        document.getElementById("sg-channels").innerHTML = rows(status.channels);
        bindRows();
      } finally {
        checking = false;
        btn.disabled = false;
      }
    };

    // Kanaldan qaytildi — Mini App yana ko'rinadi: tugma bosilishini kutmasdan tekshiramiz.
    const onReturn = () => {
      if (document.visibilityState !== "hidden") recheck(true);
    };
    document.addEventListener("visibilitychange", onReturn);
    try {
      tg?.onEvent?.("activated", onReturn);
    } catch (e) {
      /* eski klientlar */
    }

    document.getElementById("sg-check").addEventListener("click", () => {
      haptic("light");
      recheck(false);
    });
    document.getElementById("sg-close").addEventListener("click", () => {
      haptic("light");
      finish(false);
    });
  });
}

// ---- Natijalar: qidirish animatsiyasi -> "Sizga eng mos 3 ta dastur" ----

async function showResults() {
  setPendingResults(false);
  showFindingOverlay();
  const startedAt = Date.now();
  let matches = [];
  try {
    matches = await api("/match");
  } finally {
    // Oyna eng kamida shuncha turadi — javob tez kelsa ham "chaqnab" o'tmasin.
    const left = FINDING_MS - (Date.now() - startedAt);
    if (left > 0) await new Promise((resolve) => setTimeout(resolve, left));
    hideFindingOverlay();
  }
  haptic("success");
  if (!matches.length) {
    await switchTab("match");
    return;
  }
  showFirstMatches(matches);
}

/** Eng mos 3 ta: avval to'liq moslar, so'ng "yaqin"lar — server tartibida. */
function bestThree(matches) {
  return [...matches.filter((m) => m.level === "green"), ...matches.filter((m) => m.level !== "green")].slice(
    0,
    3
  );
}

function showFirstMatches(matches) {
  document.getElementById("first-matches")?.remove();
  const el = document.createElement("div");
  el.id = "first-matches";
  el.className = "fmx";
  el.innerHTML = `
    <div class="fmx-body">
      <img class="fmx-art" src="icon-programs.png?v=${ASSET_V}" alt="" aria-hidden="true">
      <h2 class="fmx-title">${t("first.title")}</h2>
      ${bestThree(matches)
        .map(
          (m, i) => `
        <button type="button" class="fmx-card" data-id="${m.id}" style="--i:${i}">
          <span class="fmx-card-title">${escapeHtml(m.name)}</span>
          <span class="fmx-card-sub">${escapeHtml(m.university)}</span>
          <span class="fmx-meta">
            <span class="fmx-chip${m.nearest_deadline ? " is-open" : ""}">${
              m.nearest_deadline
                ? t("first.closes", { date: shortDate(m.nearest_deadline) })
                : t("first.tba")
            }</span>
            <span class="chip-flag">${flag(m.country.iso_code)}</span>${escapeHtml(countryName(m.country))}
          </span>
        </button>`
        )
        .join("")}
    </div>
    <div class="fmx-bar">
      <button type="button" class="btn btn-accent btn-block" id="fmx-go">${t("first.cta")}</button>
    </div>`;
  document.body.append(el);
  requestAnimationFrame(() => el.classList.add("open"));

  const close = () => {
    el.classList.remove("open");
    setTimeout(() => el.remove(), 280);
  };
  document.getElementById("fmx-go").addEventListener("click", async () => {
    haptic("light");
    await switchTab("match");
    close();
  });
  el.querySelectorAll(".fmx-card").forEach((card) => {
    card.addEventListener("click", async () => {
      haptic("light");
      // Dasturdan "orqaga" bosilganda butun ro'yxat ochiladi.
      await switchTab("match");
      close();
      openProgramPage(card.dataset.id);
    });
  });
}

async function resetProfile() {
  haptic("warning");
  // Telegram'ning o'z tasdiq oynasi; eski klientlarda `confirm` ishlaydi.
  const confirmed = await new Promise((resolve) => {
    if (tg && typeof tg.showConfirm === "function") tg.showConfirm(t("profile.reset_confirm"), resolve);
    else resolve(window.confirm(t("profile.reset_confirm")));
  });
  if (!confirmed) return;

  profile = await api("/me/reset", { method: "POST" });
  // Yo'nalishlar ro'yxati darajaga bog'liq edi — daraja tozalangach uni
  // to'liq ro'yxatga qaytaramiz.
  await loadMajors(null);
  renderFilter();
  haptic("success");
  showToast(t("profile.reset_toast"));
}

// ============ Admission Kit ============
//
// Xizmatlar katalogi BAZADA va adminkadan boshqariladi, shuning uchun
// matnlar serverdan foydalanuvchi tilida tayyor keladi — bu yerdagi lug'at
// faqat interfeys elementlariga tegishli.
//
// Ikki xil xizmat bor, turini PDF biriktirilgani hal qiladi:
//   PDF bor  -> qulflangan mahsulot. Sotib olinadi (narx balansdan
//               yechiladi) va fayl BOTGA yuboriladi, ilovaga emas.
//   PDF yo'q -> qo'lda bajariladigan xizmat: pul yechiladi, keyin admin
//               "Xizmat so'rovlari" bo'limidan ko'rib bog'lanadi.
//
// Bu yerdagi qulf faqat KO'RINISH. Haqiqiy tekshiruv serverda: fayl
// berishdan oldin egalik qaytadan so'raladi.

function bindKitBack(root) {
  const back = root.querySelector("#kit-back");
  if (back) {
    back.addEventListener("click", () => {
      haptic("light");
      switchTab("home");
    });
  }
}

// Narx bitta satr matn: gradientli kartada u sarlavha ustidagi "ko'z qoshi"
// (eyebrow) bo'lib turadi, shuning uchun alohida teglar kerak emas.
function servicePriceText(service) {
  const unlock = inviteUnlock(service);
  if (service.price_amount === null || service.price_amount === undefined) {
    return escapeHtml(t("kit.price_ask"));
  }
  const amount = `${Number(service.price_amount).toLocaleString()} ${escapeHtml(
    service.price_currency
  )}`;
  const base = service.price_note ? `${amount} · ${escapeHtml(service.price_note)}` : amount;
  if (!unlock) return base;
  // Pulsiz yo'l narx bilan BIR QATORDA turganda jumla uzun bo'lib,
  // tugmaga tiqilib qolardi. Endi u narx ostida, mayda qatorda —
  // va faqat shu yerda: ilgari karta ichida ham takrorlanardi.
  return `${base}<span class="svc-price-alt">${t("kit.unlock_progress", {
    have: unlock.have,
    need: unlock.need,
  })} · ${t("kit.unlock_invites", { n: unlock.need })}</span>`;
}

// `api()` xatoni "API 402: {...}" ko'rinishida beradi — tafsilotni
// shundan ajratib olamiz. Boshqa xatolarda null qaytadi.
function insufficientBalance(err) {
  const message = String(err && err.message ? err.message : "");
  if (!message.startsWith("API 402")) return null;
  try {
    const body = JSON.parse(message.slice(message.indexOf("{")));
    const detail = body.detail || body;
    if (detail.error !== "insufficient_balance") return null;
    return { needed: detail.needed, available: detail.available };
  } catch (e) {
    return null;
  }
}

function openNeedBalanceSheet(short) {
  const currency = (profile && profile.balance_currency) || "";
  const money = (value) => `${Number(value).toLocaleString()} ${escapeHtml(currency)}`;
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("kit.need_balance")}</div>
    <div class="sheet-text">${t("kit.need_balance_text", {
      needed: money(short.needed),
      available: money(short.available),
    })}</div>
    <button type="button" class="btn btn-quiet btn-block" id="need-close">
      ${t("onboard.skip")}
    </button>`,
    sheet
  );
  document.getElementById("need-close").addEventListener("click", closeSheet);
}

// PDF o'lchami odam o'qiydigan ko'rinishda: "2.3 MB" yoki "740 KB".
function fileSizeLabel(bytes) {
  if (!bytes) return "";
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(Math.round(bytes / 1024), 1)} KB`;
}

// Xizmatning turi serverdan keladi (`kind`). Qulf FAYL turidagilarda
// doim ko'rinadi — hatto PDF hali yuklanmagan bo'lsa ham. Ilgari qulf
// "fayl biriktirilganmi" ga bog'liq edi va PDF yuklanmagan qo'llanma
// oddiy buyurtmaga o'xshab, qulfsiz turardi.
function isGuide(service) {
  return service.kind === "file";
}

// Fayl turidagi xizmat, lekin PDF hali yo'q — sotib olishga yo'l
// qo'yilmaydi: pul olib, berishga narsa bo'lmasligi kerak.
function isSoon(service) {
  return isGuide(service) && !service.has_file;
}

function serviceTag(service) {
  if (!isGuide(service)) return "";
  return service.requested
    ? `<span class="svc-tag is-open">${icon("check")}${t("kit.unlocked")}</span>`
    : `<span class="svc-tag is-locked">${icon("lock")}${t("kit.locked")}</span>`;
}

function serviceFileRow(service) {
  if (!isGuide(service)) return "";
  const size = fileSizeLabel(service.file_size);
  // Fayl nomi ataylab ko'rsatilmaydi: u adminka uchun ish nomi
  // ("cv_guide_v3_final.pdf") va foydalanuvchiga hech narsa aytmaydi.
  let hint = t("kit.pdf_locked_hint");
  if (isSoon(service)) hint = t("kit.pdf_soon_hint");
  else if (service.requested) hint = t("kit.pdf_open_hint");
  return `
    <div class="svc-file">
      ${icon("file")}
      <span class="svc-file-text">
        <span class="svc-file-name">${t("kit.pdf_label")}${
          size && !isSoon(service) ? ` · ${size}` : ""
        }</span>
        <span class="svc-file-hint">${hint}</span>
      </span>
    </div>`;
}

// Do'st taklif qilib ochiladigan xizmat. Hisoblagich profildan keladi
// (`referral_count`) — u faqat TASDIQLANGAN takliflarni sanaydi.
//
// Bu yerdagi hisob faqat KO'RSATISH uchun: haqiqiy tekshiruv serverda,
// xizmat berishdan oldin qaytadan bajariladi.
function inviteUnlock(service) {
  const need = Number(service.unlock_invites || 0);
  if (!need || service.requested) return null;
  const have = Number((profile && profile.referral_count) || 0);
  return { need: need, have: have, ready: have >= need };
}

function serviceBtnInner(service) {
  if (isGuide(service)) {
    if (isSoon(service)) return icon("clock") + t("kit.soon");
    if (service.requested) return icon("download") + t("kit.download");
    const guideUnlock = inviteUnlock(service);
    if (guideUnlock && guideUnlock.ready) return icon("spark") + t("kit.unlock_free");
    return icon("lock") + t("kit.buy");
  }
  // Qo'lda bajariladigan xizmat — forma sahifasi ochiladi, har doim bosiladi.
  return t("kit.request") + icon("chevron");
}

function serviceBtnClass(service) {
  if (isGuide(service)) {
    if (isSoon(service)) return " is-done";
    return service.requested ? " is-get" : " is-buy";
  }
  return "";
}

// Tugma faqat PDF'i hali yuklanmagan qo'llanmada bosilmaydi. Qo'lda
// bajariladigan xizmat formasi istalgancha yuborilishi mumkin.
function serviceBtnDisabled(service) {
  return isSoon(service);
}

// Sotib olingandan keyin kartani JOYIDA yangilaymiz. Butun sahifani qayta
// chizsak, foydalanuvchi bosgan joyidan uzilib, ro'yxat yuqorisiga
// qaytib qolardi.
function unlockServiceCard(btn, hasFile) {
  btn.dataset.owned = "1";
  btn.disabled = !hasFile;
  btn.classList.remove("is-buy");
  btn.classList.add(hasFile ? "is-get" : "is-done");
  btn.innerHTML = hasFile
    ? icon("download") + t("kit.download")
    : icon("check") + t("kit.requested");

  const card = btn.closest(".svc-card");
  if (!card) return;
  card.classList.remove("is-locked");
  const tag = card.querySelector(".svc-tag");
  if (tag) {
    tag.className = "svc-tag is-open";
    tag.innerHTML = icon("check") + t("kit.unlocked");
  }
  const hint = card.querySelector(".svc-file-hint");
  if (hint) hint.textContent = t("kit.pdf_open_hint");
}

// Fayl ILOVAGA emas, BOTGA yuboriladi: Mini App Telegram ichidagi
// brauzerda ochiladi va u yerda PDF saqlash (ayniqsa iOS'da) ishonchsiz.
// Bot suhbatiga tushgan fayl esa o'sha yerda qolib, istalgan vaqtda
// ochiladi.
async function deliverPdf(serviceId, btn) {
  const label = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = t("kit.sending");
  try {
    await api(`/services/${serviceId}/deliver`, { method: "POST" });
    haptic("success");
    openPdfSentSheet();
  } catch (err) {
    haptic("error");
    // Xarid kuchda qoladi — tugmani qayta bosish yetarli.
    showToast(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = label;
  }
}

function openPdfSentSheet() {
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("kit.sent_title")}</div>
    <div class="sheet-text">${t("kit.sent_text")}</div>
    <button type="button" class="btn btn-accent btn-block" id="pdf-open">
      ${t("kit.open_bot")}
    </button>
    <button type="button" class="btn btn-quiet btn-block" id="pdf-close">
      ${t("onboard.skip")}
    </button>`,
    sheet
  );
  document.getElementById("pdf-open").addEventListener("click", () => {
    // Ilovani yopsak, foydalanuvchi aynan bot suhbatiga qaytadi — fayl
    // o'sha yerda turadi.
    if (tg && tg.close) tg.close();
  });
  document.getElementById("pdf-close").addEventListener("click", closeSheet);
}

// ---- Xizmat so'rovi sahifasi (1-on-1 mentor sessiya, to'liq yordam) ----
// Davlat va nimada yordam kerakligi tanlanadi — so'rov bot orqali adminlarga
// boradi. Pul yechilmaydi va vaqt tanlanmaydi: admin o'zi bog'lanadi.
let kitServices = [];
let servicePageId = null;
const INQUIRY_TOPICS = ["university", "documents", "essay", "scholarship", "visa", "interview", "full", "other"];

function openServicePage(serviceId) {
  haptic("light");
  enterPage("service");
  servicePageId = serviceId;
  return switchTab("service");
}

function renderServicePage() {
  const el = document.getElementById("view-service");
  const service = kitServices.find((s) => s.id === servicePageId);
  if (!service) return switchTab("kit");
  document.body.classList.add("page-mode");
  const leave = () => leavePage("service", "kit");
  showPageBack(leave);

  // Ixcham: davlat va mavzu — ochiladigan ro'yxat. Ilgari har biri uzun
  // variantlar ro'yxati edi va sahifa haddan tashqari cho'zilib ketardi.
  const select = (id, placeholder, options) => `
    <div class="inq-select-wrap">
      <select id="${id}" class="inq-field inq-select">
        <option value="">${escapeHtml(placeholder)}</option>
        ${options.map((o) => `<option value="${escapeHtml(String(o.value))}">${escapeHtml(o.label)}</option>`).join("")}
      </select>
      ${icon("chevron", "ico inq-caret")}
    </div>`;
  const username = TG_USER && TG_USER.username ? "@" + TG_USER.username : "";

  el.innerHTML = `
    <div class="pg">
      <div class="pg-top">
        <button type="button" class="pg-back" id="pg-back" aria-label="${t("common.back")}">${icon(
          "chevron"
        )}</button>
        <span class="pg-country">${servicePriceText(service)}</span>
      </div>
      <h2 class="pg-title svc-page-title">${escapeHtml(service.title)}</h2>
      ${service.description ? `<div class="pg-sub">${escapeHtml(service.description)}</div>` : ""}

      <section class="pg-card inq-card">
        <label class="inq-label" for="inq-country">${t("inquiry.country")}</label>
        ${select(
          "inq-country",
          t("inquiry.country_unsure"),
          countries.map((c) => ({ value: c.id, label: countryName(c) }))
        )}

        <label class="inq-label" for="inq-topic">${t("inquiry.topics")}</label>
        ${select(
          "inq-topic",
          t("inquiry.topic_placeholder"),
          INQUIRY_TOPICS.map((k) => ({ value: k, label: t("inquiry.topic." + k) }))
        )}

        <label class="inq-label" for="inq-contact">${t("inquiry.contact")}</label>
        <input id="inq-contact" class="inq-field" type="text" autocomplete="tel" maxlength="100"
               value="${escapeHtml(username)}" placeholder="+998 90 123 45 67 / @username">

        <label class="inq-label" for="inq-text">${t("inquiry.text")}</label>
        <textarea id="inq-text" class="inq-field inq-text" rows="3" maxlength="1500"
                  placeholder="${escapeHtml(t("inquiry.text_placeholder"))}"></textarea>
      </section>
    </div>

    <div class="pg-bar">
      <button type="button" class="btn btn-accent pg-open" id="inq-send">${t("inquiry.send")}</button>
    </div>`;

  document.getElementById("pg-back").addEventListener("click", leave);

  const sendBtn = document.getElementById("inq-send");
  sendBtn.addEventListener("click", async () => {
    const topic = document.getElementById("inq-topic").value;
    const country = document.getElementById("inq-country").value;
    const contact = document.getElementById("inq-contact").value.trim();
    if (!topic) {
      haptic("warning");
      showToast(t("inquiry.need_topic"));
      return;
    }
    if (!contact) {
      haptic("warning");
      showToast(t("inquiry.need_contact"));
      document.getElementById("inq-contact").focus();
      return;
    }
    sendBtn.disabled = true;
    try {
      await api(`/services/${service.id}/inquiry`, {
        method: "POST",
        body: JSON.stringify({
          country_id: country ? Number(country) : null,
          topics: [topic],
          contact,
          text: document.getElementById("inq-text").value.trim(),
        }),
      });
    } catch (err) {
      sendBtn.disabled = false;
      haptic("error");
      showToast(err.message);
      return;
    }
    haptic("success");
    showToast(t("inquiry.sent"));
    leavePage("service", "kit");
  });
}

async function renderKit() {
  const el = document.getElementById("view-kit");
  el.innerHTML = skeletons(3);

  const services = await api("/services");
  kitServices = services;

  if (!services.length) {
    el.innerHTML = `
      <div class="empty">
        <div class="empty-ico">${icon("kit")}</div>
        <div class="empty-title">${t("kit.empty_title")}</div>
        <div class="empty-text">${t("kit.empty_text")}</div>
      </div>`;
    bindKitBack(el);
    return;
  }

  // Sarlavha bandi (orqaga + nom + balans) OLIB TASHLANGAN: sahifaga bosh
  // sahifadagi "Admission Kit" kartasi orqali kelinadi, ya'ni nom takror
  // edi; orqaga qaytish pastdagi panelda bor; balans esa Profil sahifasida
  // ko'rsatiladi. Mablag' yetmasa server 402 qaytaradi va ilova qancha
  // kerakligini alohida oynada aytadi — shuning uchun uni bu yerda doim
  // ko'rsatib turish shart emas.
  el.innerHTML = `
    ${services
      .map(
        (service, index) => `
      <article class="svc-card svc-card-${(index % 4) + 1}${
        isGuide(service) && !service.requested ? " is-locked" : ""
      }">
        <div class="svc-top">
          <span class="svc-num">${String(index + 1).padStart(2, "0")}</span>
          <h3 class="svc-title">${escapeHtml(service.title)}</h3>
          ${serviceTag(service)}
        </div>
        ${
          service.description
            ? `<p class="svc-text">${escapeHtml(service.description)}</p>`
            : ""
        }
        ${serviceFileRow(service)}
        <div class="svc-foot">
          <span class="svc-price">${servicePriceText(service)}</span>
          <button type="button" class="svc-btn kit-btn${serviceBtnClass(service)}"
            data-id="${service.id}"
            data-guide="${isGuide(service) ? "1" : "0"}"
            data-file="${service.has_file ? "1" : "0"}"
            data-owned="${service.requested ? "1" : "0"}"
            ${serviceBtnDisabled(service) ? "disabled" : ""}>
            ${serviceBtnInner(service)}
          </button>
        </div>
      </article>`
      )
      .join("")}
    <div class="disclaimer">${icon("shield")}<span>${t("kit.note")}</span></div>`;

  bindKitBack(el);

  el.querySelectorAll(".kit-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      haptic("light");

      // Allaqachon sotib olingan qo'llanma — pul qayta yechilmaydi,
      // faqat fayl botga qayta yuboriladi.
      if (btn.dataset.owned === "1" && btn.dataset.guide === "1") {
        await deliverPdf(btn.dataset.id, btn);
        return;
      }

      // Qo'lda bajariladigan xizmat (1-on-1 mentor, to'liq yordam) — forma sahifasi.
      if (btn.dataset.guide !== "1") {
        openServicePage(Number(btn.dataset.id));
        return;
      }

      btn.disabled = true;
      try {
        const result = await api(`/services/${btn.dataset.id}/request`, { method: "POST" });
        // Narxi bor xizmat balansdan yechiladi. Qoldiq Admission Kit
        // sahifasida ko'rsatilmaydi, lekin Profil sahifasi shu qiymatni
        // o'qiydi — shuning uchun uni darhol yangilab qo'yamiz.
        if (profile && typeof result.balance === "number") profile.balance = result.balance;
        haptic("success");
        unlockServiceCard(btn, Boolean(result.has_file));
        if (result.has_file) {
          // Sotib olgan odam yana bir tugma qidirmasligi kerak — fayl
          // shu zahoti yuboriladi.
          if (result.unlocked_by_invites) showToast(t("kit.unlocked_free_toast"));
          await deliverPdf(btn.dataset.id, btn);
        } else {
          showToast(
            result.unlocked_by_invites
              ? t("kit.unlocked_free_toast")
              : t("kit.requested_toast")
          );
        }
      } catch (err) {
        btn.disabled = false;
        haptic("error");
        // Server 402 va tafsilot qaytaradi: qancha kerak, qancha bor.
        const short = insufficientBalance(err);
        if (short) openNeedBalanceSheet(short);
        else showToast(err.message);
      }
    });
  });
}

// ============ Profil: akkaunt menyusi ============
//
// Bu sahifada QIDIRUV SOZLAMALARI YO'Q — ular alohida "filter" sahifasida
// (renderFilter). Bu yerda faqat hisob bilan bog'liq narsalar: balans,
// til, do'stlarni taklif qilish, yordam va fikr bildirish.
//
// Balans BOTDA to'ldiriladi (/topup). Mini App ichida to'lov qabul
// qilinmaydi: chek qo'lda tekshiriladi va bu bot suhbatida qulayroq.

// Profil qatori (Scout uslubi): chapda fonsiz ko'k ikonka, o'ngda qisqa qiymat.
// `sub` — sarlavha ostidagi izoh (masalan taklif mukofoti).
function profileRow(id, iconName, title, opts = {}) {
  // `valueId` — qiymat keyin to'ldiriladi (masalan saqlanganlar soni).
  const hasValue = (opts.value !== undefined && opts.value !== "") || opts.valueId;
  return `
    <button type="button" class="pf-row${hasValue ? " has-value" : ""}" id="${id}">
      <span class="pf-ico">${icon(iconName)}</span>
      <span class="pf-text">
        <span class="pf-title">${title}</span>
        ${opts.sub ? `<span class="pf-sub">${opts.sub}</span>` : ""}
      </span>
      ${hasValue ? `<span class="pf-value"${opts.valueId ? ` id="${opts.valueId}"` : ""}>${opts.value || ""}</span>` : ""}
      ${icon("chevron", "pf-chevron")}
    </button>`;
}

/** Eslatmalar toggle'i. Boshqa qatorlardan farqi: sahifa ochmaydi, qiymatni
 *  joyida o'zgartiradi va darhol saqlaydi. */
function notificationsRow() {
  const on = profile.notifications_enabled !== false;
  return `
    <div class="pf-row pf-row-static" id="acc-notif">
      <span class="pf-ico">${icon("bell")}</span>
      <span class="pf-text"><span class="pf-title">${t("profile.notifications")}</span></span>
      <span class="switch ${on ? "is-on" : ""}" role="switch" aria-checked="${on}" aria-label="${t(
        "profile.notif_hint"
      )}">
        <span class="switch-knob"></span>
      </span>
    </div>`;
}

// "Magistratura · 2 ta davlat" — filtr qatorining o'ngidagi qisqa xulosa.
function filterSummary() {
  return [degreeLabel(), countriesLabel()].filter(Boolean).map(escapeHtml).join(" · ");
}

function renderProfile() {
  const el = document.getElementById("view-profile");
  const name = (TG_USER && TG_USER.first_name) || "";
  const username = TG_USER && TG_USER.username;
  const balance = `${Number(profile.balance || 0).toLocaleString()} ${escapeHtml(
    profile.balance_currency || ""
  )}`;
  const userSub = [username ? "@" + escapeHtml(username) : "", t("profile.completeness", { n: profileCompleteness() })]
    .filter(Boolean)
    .join(" · ");

  el.innerHTML = `
    <h1 class="pf-heading">${t("nav.profile")}</h1>
    <button type="button" class="pf-card pf-user" id="acc-user">
      <span class="pf-avatar">${escapeHtml(initials(name)) || icon("user")}</span>
      <span class="pf-text">
        <span class="pf-name">${escapeHtml(name) || t("profile.no_name")}</span>
        <span class="pf-sub">${userSub}</span>
      </span>
      ${icon("chevron", "pf-chevron")}
    </button>

    <div class="pf-balance">
      <span class="pf-balance-ico">${icon("wallet")}</span>
      <span class="pf-text">
        <span class="pf-balance-label">${t("account.balance")}</span>
        <span class="pf-balance-value">${balance}</span>
        <span class="pf-balance-hint">${t("account.topup_hint")}</span>
      </span>
      ${
        profile.bot_username
          ? `<button type="button" class="pf-balance-btn" id="acc-topup">${t("account.topup_btn")}${icon(
              "chevron"
            )}</button>`
          : ""
      }
    </div>

    <div class="pf-group">
      ${profileRow("acc-filter", "target", t("account.filter"), { value: filterSummary() || "—" })}
      ${profileRow("acc-saved", "bookmark", t("nav.saved"), { value: "", valueId: "acc-saved-count" })}
      ${notificationsRow()}
    </div>

    <div class="pf-group">
      ${profileRow("acc-lang", "globe", t("account.language"), { value: LANG_LABELS[lang] || lang })}
      ${profileRow("acc-invite", "gift", t("account.invite"), { sub: inviteSubtitle() })}
      ${
        mentorConfig && mentorConfig.admin_username
          ? profileRow("acc-mentor", "cap", t("mentor.become_row"), { sub: t("mentor.become_row_sub") })
          : ""
      }
      ${profileRow("acc-help", "shield", t("account.help"))}
      ${profileRow("acc-feedback", "chat", t("account.feedback"))}
    </div>`;

  const openFilterTab = () => {
    haptic("light");
    switchTab("filter");
  };
  document.getElementById("acc-user").addEventListener("click", openFilterTab);
  document.getElementById("acc-filter").addEventListener("click", openFilterTab);
  document.getElementById("acc-saved").addEventListener("click", () => switchTab("saved"));
  document.getElementById("acc-topup")?.addEventListener("click", () => {
    haptic("light");
    // To'ldirish botda (/topup) — bot suhbati ochiladi.
    const url = `https://t.me/${encodeURIComponent(profile.bot_username)}`;
    try {
      tg.openTelegramLink(url);
    } catch (e) {
      window.open(url, "_blank");
    }
  });
  document.getElementById("acc-lang").addEventListener("click", openLanguageSheet);
  document.getElementById("acc-notif").addEventListener("click", async () => {
    haptic("light");
    const enabled = profile.notifications_enabled === false;
    // Darhol saqlanadi: "saqlash" tugmasi yo'q, odam toggle'ni bosdi-yu
    // ketib qolsa ham tanlovi yo'qolmasligi kerak.
    await api("/me", {
      method: "PATCH",
      body: JSON.stringify({ notifications_enabled: enabled }),
    });
    profile.notifications_enabled = enabled;
    showToast(t(enabled ? "profile.notif_on_toast" : "profile.notif_off_toast"));
    renderProfile();
  });
  document.getElementById("acc-invite").addEventListener("click", shareBot);
  document.getElementById("acc-help").addEventListener("click", openHelpSheet);
  document.getElementById("acc-feedback").addEventListener("click", openFeedbackSheet);
  document.getElementById("acc-mentor")?.addEventListener("click", applyAsMentor);

  // Saqlanganlar soni sahifani kutdirmasdan keyin to'ldiriladi.
  api("/saved")
    .then((items) => {
      const count = document.getElementById("acc-saved-count");
      if (count) count.textContent = items.length;
    })
    .catch(() => {});
}

const LANG_LABELS = { uz: "O'zbekcha", ru: "Русский", en: "English" };

function openLanguageSheet() {
  haptic("light");
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("account.language")}</div>
    <div class="acc-group">
      ${["uz", "ru", "en"]
        .map(
          (code) => `
        <button type="button" class="acc-row lang-pick${code === lang ? " is-active" : ""}"
                data-lang="${code}">
          <span class="acc-text"><span class="acc-title">${LANG_LABELS[code]}</span></span>
          ${code === lang ? icon("check", "acc-chevron") : ""}
        </button>`
        )
        .join("")}
    </div>`,
    sheet
  );

  sheet.querySelectorAll(".lang-pick").forEach((btn) => {
    btn.addEventListener("click", async () => {
      haptic("light");
      lang = btn.dataset.lang;
      await api("/me", { method: "PATCH", body: JSON.stringify({ ui_language: lang }) });
      closeSheet();
      updateNavLabels();
      await switchTab("profile");
    });
  });
}

// Bot foydalanuvchi nomi Telegram'ning `initDataUnsafe` da YO'Q — u
// serverdan `/me` javobi bilan keladi (api.py `_get_bot_username`).
// Taklif havolasi — oddiy bot havolasidan farqli o'laroq, unda taklif
// kodi bor va shu bo'yicha mukofot hisoblanadi. Kod SERVERDA yig'iladi,
// shuning uchun uni o'zgartirib bo'lmaydi.
function botLink() {
  if (profile && profile.referral_link) return profile.referral_link;
  const username = profile && profile.bot_username;
  return username ? `https://t.me/${username}` : null;
}

// Taklif qatorining izohi: mukofot summasi, taklif qilinganlar bo'lsa —
// ularning soni ham. Mukofot 0 bo'lsa (dastur to'xtatilgan) pul haqida
// umuman gapirilmaydi.
function inviteSubtitle() {
  const bonus = Number((profile && profile.referral_bonus) || 0);
  if (!bonus) return t("account.invite_sub_plain");
  const money = `${bonus.toLocaleString()} ${escapeHtml(
    (profile && profile.balance_currency) || ""
  )}`;
  const count = Number((profile && profile.referral_count) || 0);
  return count
    ? t("account.invite_count", { count: count, bonus: money })
    : t("account.invite_sub", { bonus: money });
}

function shareBot() {
  haptic("light");
  const link = botLink();
  if (!link) {
    showToast(t("account.invite_unavailable"));
    return;
  }
  const url = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(
    t("account.invite_text")
  )}`;
  try {
    tg.openTelegramLink(url);
  } catch (e) {
    window.open(url, "_blank");
  }
}

function openHelpSheet() {
  haptic("light");
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  const items = [1, 2, 3, 4]
    .map(
      (n) => `
    <div class="faq-item">
      <div class="faq-q">${t("faq.q" + n)}</div>
      <div class="faq-a">${t("faq.a" + n)}</div>
    </div>`
    )
    .join("");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("account.help")}</div>
    ${items}`,
    sheet,
    { tall: true }
  );
}

function openFeedbackSheet() {
  haptic("light");
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("account.feedback")}</div>
    <div class="sheet-sub">${t("account.feedback_hint")}</div>
    <textarea id="fb-text" class="fb-text" rows="5"
              placeholder="${escapeHtml(t("account.feedback_placeholder"))}"></textarea>
    <button type="button" class="btn btn-accent btn-block" id="fb-send">
      ${t("account.feedback_send")}
    </button>`,
    sheet
  );

  document.getElementById("fb-send").addEventListener("click", async () => {
    const text = document.getElementById("fb-text").value.trim();
    if (!text) return;
    const btn = document.getElementById("fb-send");
    btn.disabled = true;
    try {
      await api("/feedback", { method: "POST", body: JSON.stringify({ text }) });
      closeSheet();
      haptic("success");
      showToast(t("account.feedback_sent"));
    } catch (err) {
      btn.disabled = false;
      haptic("error");
      showToast(err.message);
    }
  });
}

// ============ Mentordan so'rash ============
//
// Foydalanuvchi tanlagan davlatda o'qiyotgan o'zbek talabadan (mentordan)
// savol so'raydi. Savol mentorlar guruhiga tushadi, javob bot orqali
// ANONIM keladi. Bu yerda mentorning ismi HECH QAYERDA ko'rsatilmaydi —
// server uni umuman bermaydi, ko'rinadigani faqat "{davlat}dagi mentor".
//
// Bitta sahifa (`view-mentor`), ichida to'rt holat:
//   list      — "Mening savollarim"
//   countries — davlat tanlash
//   form      — savol formasi
//   chat      — bitta savolning yozishmasi

let mentorConfig = null;
let mentorState = { screen: "list" };

const MENTOR_TOPICS = ["admission", "documents", "visa", "living", "work", "studies", "other"];
const MENTOR_COMPLAINT_REASONS = ["wrong_info", "disrespect", "paid_or_ad", "other"];

async function loadMentorConfig(force) {
  if (mentorConfig && !force) return mentorConfig;
  try {
    mentorConfig = await api("/mentor/config");
  } catch (e) {
    // Funksiya ishlamasa ilovaning qolgan qismi buzilmasin — tugmalar
    // shunchaki ko'rinmaydi.
    console.error(e);
    mentorConfig = { enabled: false, countries: [], admin_username: null };
  }
  return mentorConfig;
}

/** Server rad etganda kelgan kod ("monthly_limit") -> tushunarli matn. */
function mentorErrorText(err) {
  const match = /"code"\s*:\s*"([a-z_]+)"/.exec(String(err && err.message));
  const key = match ? `mentor.err.${match[1]}` : "";
  const text = key ? t(key) : "";
  return text && text !== key ? text : t("mentor.err.generic");
}

function mentorLimitLeft() {
  if (!mentorConfig) return 0;
  return Math.max(mentorConfig.monthly_limit - mentorConfig.monthly_used, 0);
}

function openMentor(screen, extra) {
  mentorState = { screen, ...(extra || {}) };
  return switchTab("mentor");
}

function mentorDate(iso) {
  try {
    return new Date(iso).toLocaleDateString(lang === "en" ? "en-GB" : lang === "ru" ? "ru-RU" : "uz-UZ", {
      day: "numeric",
      month: "short",
    });
  } catch (e) {
    return "";
  }
}

function mentorTime(iso) {
  try {
    const d = new Date(iso);
    return `${mentorDate(iso)}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch (e) {
    return "";
  }
}

function mentorStatusPill(status) {
  const tone = { open: "amber", claimed: "accent", answered: "green", closed: "" }[status] || "";
  return `<span class="pill ${tone}">${t("mentor.status." + status)}</span>`;
}

function mentorChips(id, options, active) {
  return `
    <div class="chip-group" id="${id}">
      ${options
        .map(
          (o) =>
            `<div class="chip ${o.value === active ? "active" : ""}" data-value="${escapeHtml(o.value)}">${escapeHtml(
              o.label
            )}</div>`
        )
        .join("")}
    </div>`;
}

function mentorBack(label) {
  return `
    <button type="button" class="kit-back" id="mentor-back">
      ${icon("chevron")}<span>${escapeHtml(label)}</span>
    </button>`;
}

// Uni Buddy dastur yoki grant sahifasidan ochilgan bo'lsa — "orqaga" o'sha sahifaga.
function mentorReturn() {
  if (mentorState.returnProgram) return () => openProgramPage(mentorState.returnProgram);
  if (mentorState.returnGrant) return () => switchTab("grant");
  return null;
}

function bindMentorBack(target) {
  const btn = document.getElementById("mentor-back");
  if (!btn) return;
  btn.addEventListener("click", () => {
    haptic("light");
    if (typeof target === "function") target();
    else if (typeof target === "string") switchTab(target);
    else openMentor(target.screen, target);
  });
}

async function renderMentor() {
  const el = document.getElementById("view-mentor");
  el.innerHTML = skeletons(3);
  await loadMentorConfig(true);
  const screen = mentorState.screen;
  // Savol yoziladigan ekranlarda pastki menyu umuman ko'rinmaydi: iPhone'da
  // klaviatura ochilganda u yuqoriga ko'tarilib, yozish maydonini yopardi.
  // Bu ekranlardan qaytish o'zining "orqaga" tugmasi orqali.
  document.body.classList.toggle("no-tabbar", screen === "form" || screen === "chat");
  if (screen === "countries") return renderMentorCountries(el);
  if (screen === "form") return renderMentorForm(el);
  if (screen === "chat") return renderMentorChat(el);
  return renderMentorList(el);
}

// ---- "Mening savollarim" ----

async function renderMentorList(el) {
  const items = await api("/mentor/questions");
  const canAsk = mentorConfig.enabled;
  el.innerHTML = `
    <div class="mnt-head">
      <div class="mnt-title">Uni Buddy</div>
      ${
        canAsk
          ? `<button type="button" class="btn btn-accent mnt-new" id="mentor-new">${icon("plus")}${t(
              "mentor.new_question"
            )}</button>`
          : ""
      }
    </div>
    <div class="mnt-sub">${t("buddy.tagline")}</div>
    ${
      items.length
        ? `<div class="section-head"><span class="section-title">${t("mentor.my_questions")}</span></div>` + items
            .map(
              (q) => `
      <button type="button" class="mnt-item" data-id="${q.id}">
        <span class="mnt-flag">${flag(q.country_code)}</span>
        <span class="mnt-item-body">
          <span class="mnt-item-title">${escapeHtml(q.country_name)} · #${q.number}</span>
          <span class="mnt-item-sub">${mentorDate(q.created_at)}</span>
        </span>
        ${mentorStatusPill(q.status)}
      </button>`
            )
            .join("")
        : `<div class="empty">
             <div class="empty-ico">${icon("cap")}</div>
             <div class="empty-title">${t("mentor.empty_title")}</div>
             <div class="empty-text">${t("mentor.empty_text")}</div>
           </div>`
    }`;

  document.getElementById("mentor-new")?.addEventListener("click", () => {
    haptic("light");
    openMentor("countries", { from: "list" });
  });
  el.querySelectorAll(".mnt-item").forEach((row) => {
    row.addEventListener("click", () => {
      haptic("light");
      openMentor("chat", { id: Number(row.dataset.id) });
    });
  });
}

// ---- Davlat tanlash ----

function mentorLimitBlock() {
  return `
    <div class="empty">
      <div class="empty-ico">${icon("clock")}</div>
      <div class="empty-title">${t("mentor.limit_title")}</div>
      <div class="empty-text">${t("mentor.limit_text", { n: mentorConfig.monthly_limit })}</div>
    </div>`;
}

async function renderMentorCountries(el) {
  // Ro'yxatdan kelinganda unga qaytish tugmasi bor. Bosh sahifadan
  // kelinganda yo'q — pastdagi menyu shu vazifani bajaradi.
  const fromList = mentorState.from === "list";
  const fromProgram = mentorReturn();
  const backBtn = fromProgram
    ? mentorBack(t("common.back"))
    : fromList
      ? mentorBack("Uni Buddy")
      : "";
  if (!mentorConfig.enabled) {
    el.innerHTML = `${backBtn}<div class="empty"><div class="empty-title">${t(
      "mentor.err.disabled"
    )}</div></div>`;
    if (fromList) bindMentorBack({ screen: "list" });
    return;
  }
  el.innerHTML = `
    ${backBtn}
    <div class="mnt-title">${t("mentor.choose_country")}</div>
    <div class="mnt-sub">${t("mentor.choose_country_sub")}</div>
    ${
      mentorLimitLeft() <= 0
        ? mentorLimitBlock()
        : `<div class="mnt-countries">
            ${mentorConfig.countries
              .map(
                (c) => `
            <button type="button" class="mnt-country" data-code="${c.code}">
              <span class="mnt-flag">${flag(c.code)}</span>
              <span class="mnt-country-name">${escapeHtml(c.name)}</span>
              ${icon("chevron", "ico mnt-go")}
            </button>`
              )
              .join("")}
          </div>
          <div class="mnt-quota">${t("mentor.quota", {
            left: mentorLimitLeft(),
            n: mentorConfig.monthly_limit,
          })}</div>`
    }`;

  if (fromProgram) bindMentorBack(fromProgram);
  else if (fromList) bindMentorBack({ screen: "list" });
  el.querySelectorAll(".mnt-country").forEach((row) => {
    row.addEventListener("click", () => {
      haptic("light");
      openMentor("form", {
        country: row.dataset.code,
        from: mentorState.from,
        returnProgram: mentorState.returnProgram,
        returnGrant: mentorState.returnGrant,
      });
    });
  });
}

// ---- Savol formasi ----

async function renderMentorForm(el) {
  const country = mentorConfig.countries.find((c) => c.code === mentorState.country);
  // Dastur/grant sahifasidan kelinganda "orqaga" o'sha sahifaga qaytaradi.
  const fromProgram = mentorReturn();
  const back = fromProgram || { screen: "countries", from: mentorState.from };
  if (!country) return openMentor("countries", { from: mentorState.from });

  const min = mentorConfig.question_min_chars;
  const max = mentorConfig.question_max_chars;
  el.innerHTML = `
    ${mentorBack(fromProgram ? t("common.back") : t("mentor.choose_country"))}
    <div class="mnt-title">${flag(country.code)} ${escapeHtml(country.name)}</div>
    ${
      mentorLimitLeft() <= 0
        ? mentorLimitBlock()
        : `
    <div class="group">
      <div class="field">
        <label>${t("mentor.level")}</label>
        ${mentorChips(
          "mentor-level",
          ["bachelor", "master", "phd"].map((v) => ({ value: v, label: t("mentor.level." + v) })),
          // Profilda daraja tanlangan bo'lsa, oldindan belgilanadi.
          mentorState.level || (profile && profile.degree_level) || ""
        )}
      </div>
      <div class="field">
        <label>${t("mentor.topic")}</label>
        ${mentorChips(
          "mentor-topic",
          MENTOR_TOPICS.map((v) => ({ value: v, label: t("mentor.topic." + v) })),
          mentorState.topic || ""
        )}
      </div>
      <div class="field">
        <label>${t("mentor.text")}</label>
        <textarea id="mentor-text" class="fb-text mnt-textarea" rows="6" maxlength="${max}"
                  placeholder="${escapeHtml(t("mentor.text_placeholder"))}">${escapeHtml(
            mentorState.text || ""
          )}</textarea>
        <small class="field-hint" id="mentor-count"></small>
      </div>
    </div>
    <div class="mnt-warn">${icon("shield")}<span>${t("mentor.privacy_warning")}</span></div>
    <button type="button" class="btn btn-accent btn-block" id="mentor-send">${t("mentor.send")}</button>`
    }`;

  bindMentorBack(back);
  if (mentorLimitLeft() <= 0) return;

  bindChips("mentor-level");
  bindChips("mentor-topic");
  const textEl = document.getElementById("mentor-text");
  const countEl = document.getElementById("mentor-count");
  const updateCount = () => {
    const len = textEl.value.trim().length;
    countEl.textContent =
      len < min ? t("mentor.count_min", { len, min }) : t("mentor.count", { len, max });
    countEl.classList.toggle("mnt-count-bad", len > 0 && len < min);
  };
  textEl.addEventListener("input", updateCount);
  updateCount();

  const sendBtn = document.getElementById("mentor-send");
  sendBtn.addEventListener("click", async () => {
    const level = activeChip("mentor-level");
    const topic = activeChip("mentor-topic");
    const text = textEl.value.trim();
    // Kiritilgan narsa qayta chizishda yo'qolmasin (masalan xatodan keyin).
    Object.assign(mentorState, { level, topic, text });
    if (!level || !topic) {
      haptic("error");
      showToast(t("mentor.err.choose_all"));
      return;
    }
    if (text.length < min) {
      haptic("error");
      showToast(t("mentor.err.text_too_short"));
      return;
    }
    sendBtn.disabled = true;
    try {
      const question = await api("/mentor/questions", {
        method: "POST",
        body: JSON.stringify({ country_code: country.code, level, topic, text }),
      });
      haptic("success");
      await openMentor("chat", { id: question.id, justSent: true });
    } catch (err) {
      sendBtn.disabled = false;
      haptic("error");
      showToast(mentorErrorText(err));
    }
  });
}

// ---- Chat ----

async function renderMentorChat(el) {
  const q = await api(`/mentor/questions/${mentorState.id}`);
  const mentorLabel = t("mentor.mentor_label", { country: q.country_name });

  const bubbles = q.messages
    .map((m) => {
      if (m.sender === "user") {
        return `<div class="mnt-msg mine"><div class="mnt-bubble">${escapeHtml(m.text)}</div>
          <div class="mnt-meta">${mentorTime(m.created_at)}</div></div>`;
      }
      return `<div class="mnt-msg theirs">
          <div class="mnt-from">🎓 ${escapeHtml(mentorLabel)}</div>
          <div class="mnt-bubble">${escapeHtml(m.text)}</div>
          <div class="mnt-meta">${mentorTime(m.created_at)}
            <button type="button" class="mnt-report" data-msg="${m.id}">${t("mentor.report_short")}</button>
          </div></div>`;
    })
    .join("");

  const waiting =
    q.status === "open" || q.status === "claimed"
      ? `<div class="mnt-note">${icon("clock")}<span>${
          mentorState.justSent
            ? t("mentor.sent_notice", { country: q.country_name })
            : t("mentor.waiting")
        }</span></div>`
      : "";

  const followup = q.can_followup
    ? `<div class="group mnt-followup">
        <div class="field">
          <label>${t("mentor.followup_label", { left: q.followups_left })}</label>
          <textarea id="mentor-followup" class="fb-text mnt-textarea" rows="3" maxlength="${
            mentorConfig.question_max_chars
          }" placeholder="${escapeHtml(t("mentor.followup_placeholder"))}"></textarea>
          <button type="button" class="btn btn-accent btn-block" id="mentor-followup-send">${t(
            "mentor.followup_send"
          )}</button>
        </div>
      </div>`
    : q.status === "answered"
    ? `<div class="mnt-note">${t("mentor.followup_limit")}</div>`
    : "";

  const rating = q.can_rate
    ? `<div class="group mnt-rate">
        <div class="mnt-rate-title">${t("mentor.rate_title")}</div>
        <div class="mnt-stars">${[1, 2, 3, 4, 5]
          .map((n) => `<button type="button" class="mnt-star" data-n="${n}" aria-label="${n}">★</button>`)
          .join("")}</div>
      </div>`
    : q.rating
    ? `<div class="mnt-note">${t("mentor.rated", { stars: "⭐".repeat(q.rating) })}</div>`
    : "";

  el.innerHTML = `
    ${mentorBack("Uni Buddy")}
    <div class="mnt-chat-head">
      <span class="mnt-flag">${flag(q.country_code)}</span>
      <div class="mnt-chat-head-text">
        <div class="mnt-item-title">${escapeHtml(q.country_name)} · #${q.number}</div>
        <div class="mnt-item-sub">${t("mentor.level." + q.level)} · ${t("mentor.topic." + q.topic)}</div>
      </div>
      ${mentorStatusPill(q.status)}
    </div>
    <div class="mnt-chat">${bubbles}</div>
    ${waiting}
    ${followup}
    ${rating}
    <div class="mnt-actions">
      ${
        q.can_close
          ? `<button type="button" class="btn btn-accent btn-block" id="mentor-close">${t(
              "mentor.close_btn"
            )}</button>`
          : ""
      }
      ${
        q.can_complain
          ? `<button type="button" class="btn btn-quiet btn-block" id="mentor-complain">${t(
              "mentor.complain_btn"
            )}</button>`
          : ""
      }
    </div>`;

  bindMentorBack({ screen: "list" });
  // "Yuborildi" xabari faqat birinchi ochilishda.
  mentorState.justSent = false;

  el.querySelectorAll(".mnt-report").forEach((btn) => {
    btn.addEventListener("click", () => openComplaintSheet(q, Number(btn.dataset.msg)));
  });
  document.getElementById("mentor-complain")?.addEventListener("click", () => openComplaintSheet(q, null));

  document.getElementById("mentor-close")?.addEventListener("click", async (event) => {
    const btn = event.currentTarget;
    btn.disabled = true;
    try {
      await api(`/mentor/questions/${q.id}/close`, { method: "POST" });
      haptic("success");
      await renderMentorChat(el);
    } catch (err) {
      btn.disabled = false;
      haptic("error");
      showToast(mentorErrorText(err));
    }
  });

  el.querySelectorAll(".mnt-star").forEach((star) => {
    star.addEventListener("click", async () => {
      const n = Number(star.dataset.n);
      el.querySelectorAll(".mnt-star").forEach((s) => s.classList.toggle("on", Number(s.dataset.n) <= n));
      try {
        await api(`/mentor/questions/${q.id}/rate`, { method: "POST", body: JSON.stringify({ rating: n }) });
        haptic("success");
        showToast(t("mentor.rate_thanks"));
        await renderMentorChat(el);
      } catch (err) {
        haptic("error");
        showToast(mentorErrorText(err));
      }
    });
  });

  const sendFollowup = document.getElementById("mentor-followup-send");
  sendFollowup?.addEventListener("click", async () => {
    const text = document.getElementById("mentor-followup").value.trim();
    if (!text) return;
    sendFollowup.disabled = true;
    try {
      await api(`/mentor/questions/${q.id}/followup`, { method: "POST", body: JSON.stringify({ text }) });
      haptic("success");
      showToast(t("mentor.followup_sent"));
      await renderMentorChat(el);
    } catch (err) {
      sendFollowup.disabled = false;
      haptic("error");
      showToast(mentorErrorText(err));
    }
  });
}

function openComplaintSheet(question, messageId) {
  haptic("light");
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("mentor.complain_title")}</div>
    <div class="sheet-sub">${t("mentor.complain_sub")}</div>
    <div class="sheet-section">
      ${mentorChips(
        "complaint-reason",
        MENTOR_COMPLAINT_REASONS.map((v) => ({ value: v, label: t("mentor.reason." + v) })),
        ""
      )}
    </div>
    <textarea id="complaint-comment" class="fb-text" rows="3" maxlength="1000"
              placeholder="${escapeHtml(t("mentor.complain_comment"))}"></textarea>
    <button type="button" class="btn btn-accent btn-block" id="complaint-send">${t("mentor.complain_send")}</button>`,
    sheet
  );
  bindChips("complaint-reason");

  document.getElementById("complaint-send").addEventListener("click", async (event) => {
    const reason = activeChip("complaint-reason");
    if (!reason) {
      haptic("error");
      showToast(t("mentor.err.choose_reason"));
      return;
    }
    const btn = event.currentTarget;
    btn.disabled = true;
    try {
      await api(`/mentor/questions/${question.id}/complaints`, {
        method: "POST",
        body: JSON.stringify({
          reason,
          comment: document.getElementById("complaint-comment").value.trim() || null,
          message_id: messageId,
        }),
      });
      closeSheet();
      haptic("success");
      showToast(t("mentor.complain_sent"));
    } catch (err) {
      btn.disabled = false;
      haptic("error");
      showToast(mentorErrorText(err));
    }
  });
}

// ---- Bosh sahifadagi kirish nuqtasi: Uni Buddy ----
// "Saqlangan" kartasi turgan joyda. Funksiya o'chiq bo'lsa (env sozlanmagan)
// o'rniga eski "Saqlangan" kartasi qaytadi — bosh sahifada bo'sh joy qolmasin.

function buddyHomeCard() {
  if (!mentorConfig || !mentorConfig.enabled) {
    return `
        <div class="hx-mini" data-goto="saved" role="button" tabindex="0">
          <div class="hx-mini-head">
            <span class="hx-mini-label">${t("home.stat_saved")}</span>
            <span class="hx-mini-ico">${icon("bookmark")}</span>
          </div>
          <div class="hx-mini-value" id="mini-saved-value">—</div>
          <div class="hx-mini-foot" id="mini-saved-foot"></div>
          <div class="split" id="mini-saved-bar">
            <span class="split-accent" style="width:0"></span>
          </div>
        </div>`;
  }
  const limit = mentorConfig.monthly_limit;
  const left = mentorLimitLeft();
  return `
        <div class="hx-mini hx-buddy" id="home-buddy" role="button" tabindex="0">
          <div class="hx-mini-head">
            <span class="hx-mini-label">Uni Buddy</span>
          </div>
          <div class="hx-buddy-art">
            <img src="icon-buddy.png?v=${ASSET_V}" alt="" aria-hidden="true">
          </div>
          <div class="hx-mini-foot"><span class="hx-tag">${t("buddy.home_quota", { left, n: limit })}</span></div>
        </div>`;
}

/** Savollari bor odam — ro'yxatga, birinchi marta kelgan — darhol davlat tanlashga. */
async function openBuddy() {
  haptic("light");
  let items = [];
  try {
    items = await api("/mentor/questions");
  } catch (e) {
    console.error(e);
  }
  await openMentor(items.length ? "list" : "countries", { from: "home" });
}

// ---- Profil: "Mentor bo'lish" ----
// Oraliq oyna yo'q: bosilganda darhol admin bilan Telegram suhbati tayyor
// matn bilan ochiladi.


function applyAsMentor() {
  haptic("light");
  const username = mentorConfig && mentorConfig.admin_username;
  if (!username) return;
  const url = `https://t.me/${encodeURIComponent(username)}?text=${encodeURIComponent(t("mentor.apply_text"))}`;
  try {
    tg.openTelegramLink(url);
  } catch (e) {
    window.open(url, "_blank");
  }
}

// ============ Navigation ============

const RENDERERS = {
  filter: renderFilter,
  home: renderHome,
  match: renderMatch,
  kit: renderKit,
  scholarships: renderScholarships,
  saved: renderSaved,
  profile: renderProfile,
  mentor: renderMentor,
  program: renderProgramPage,
  grant: renderGrantPage,
  service: renderServicePage,
  gpa: renderGpaPage,
};

function updateNavLabels() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
    const btn = el.closest(".tab");
    if (btn) btn.setAttribute("aria-label", el.textContent);
  });
}

// Filtr bir necha joydan ochiladi (bosh sahifa, profil, dasturlar) —
// "Orqaga" foydalanuvchini qayerdan kelgan bo'lsa, o'sha yerga qaytaradi.
let currentTab = "home";
let previousTab = "home";

async function switchTab(tabName) {
  haptic("light");
  if (tabName !== currentTab) {
    previousTab = currentTab;
    currentTab = tabName;
  }
  // Pastki menyu har bir o'tishda qaytadi; uni yashiradigan ekran
  // (Uni Buddy formasi va chati) o'zi qayta yashiradi.
  document.body.classList.remove("no-tabbar", "wizard-mode", "page-mode");
  if (!PAGE_TABS.has(tabName)) hidePageBack();
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabName));
  document.querySelectorAll(".view").forEach((v) => {
    v.hidden = v.id !== `view-${tabName}`;
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
  const render = RENDERERS[tabName];
  if (!render) return;
  try {
    await render();
  } catch (err) {
    // Xato ushlanmasa sahifa skeletonlarda qotib qolardi va foydalanuvchi
    // nima bo'lganini bilmasdi — Admission Kit aynan shunday "ishlamay"
    // turgandi (serverdagi AttributeError 500 qaytargan).
    console.error(err);
    document.getElementById(`view-${tabName}`).innerHTML = `
      <div class="empty">
        <div class="empty-ico">${icon("clock")}</div>
        <div class="empty-title">${t("error.title")}</div>
        <div class="empty-text">${escapeHtml(err.message)}</div>
      </div>`;
  }
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

/** Bot xabaridagi tugmalardan kelgan yo'nalish.
 *
 * `WebAppInfo` tugmasi `startapp` ni qo'llamaydi (u faqat t.me havolasida
 * ishlaydi), shuning uchun parametr URL hash'ida keladi: `#program_12`.
 * Telegram `start_param` bersa, u ham tekshiriladi.
 */
//
// Faqat TANILGAN yo'nalish qaytariladi. Telegram Mini App'ni ochganda hash'ga
// o'zining `tgWebAppData=...` parametrlarini yozadi — ilgari u ham "havola"
// deb olinib, yangi foydalanuvchiga onboarding umuman ko'rsatilmasdi.
const DEEP_LINK = /^(profile|program_\d+|question_\d+|suggest_\d+)$/;

function deepLinkTarget() {
  const fromHash = (location.hash || "").replace(/^#/, "");
  const fromStart =
    (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || "";
  return [fromHash, fromStart].find((value) => DEEP_LINK.test(value)) || "";
}

async function applyDeepLink() {
  const target = deepLinkTarget();
  if (!target) return false;
  // Bir marta ishlasin: sahifa ichida yurganda qayta ochilib qolmasin.
  try {
    history.replaceState(null, "", location.pathname + location.search);
  } catch (e) {
    /* eski WebView */
  }

  if (target === "profile") {
    await switchTab("profile");
    return true;
  }
  const program = target.match(/^program_(\d+)$/);
  if (program) {
    await switchTab("saved");
    openProgramPage(Number(program[1]));
    return true;
  }
  const question = target.match(/^question_(\d+)$/);
  if (question) {
    await openMentor("chat", { id: Number(question[1]) });
    return true;
  }
  const suggest = target.match(/^suggest_(\d+)$/);
  if (suggest) {
    await switchTab("saved");
    openSuggestSheet(Number(suggest[1]));
    return true;
  }
  return false;
}

async function init() {
  if (!INIT_DATA) {
    document.getElementById("app").innerHTML = `
      <div class="empty">
        <div class="empty-ico">${icon("cap")}</div>
        <div class="empty-title">Uni Assist</div>
        <div class="empty-text">Bu ilova faqat Telegram ichida ishlaydi.<br>This app only works inside Telegram.</div>
      </div>`;
    return;
  }

  // Tab paneli statik HTML'da, ya'ni ma'lumot yuklanguncha ham bosiladi.
  // Tayyor bo'lmaguncha bosishni to'xtatamiz — aks holda tez bosilgan tab
  // hech narsa qilmay, foydalanuvchiga "ishlamadi" bo'lib ko'rinardi.
  const tabbar = document.querySelector(".tabbar");
  tabbar.setAttribute("aria-busy", "true");

  await loadProfile();
  // Katalog so'rovlari bir-biriga bog'liq emas — parallel yuklanadi.
  // Ilgari beshta so'rov ketma-ket kutilardi.
  catalogReady = Promise.all([loadCountries(), loadMajors(), loadStudyLanguages(), loadMentorConfig()]);

  // Filtr bo'sh bo'lsa — darhol onboarding'ning kutib olish ekrani. U katalogni
  // kutmaydi va bosh sahifa umuman chizilmaydi: ilgari avval bosh sahifa
  // chiqib, 2-3 soniyadan keyin onboarding'ga "sakrab" o'tardi.
  // Bot xabaridan kelingan bo'lsa — darhol o'sha joyga: odam aniq maqsad bilan kelgan.
  // Kanalga o'tib ilova yopilgan bo'lsa — o'sha joyga: oxirgi savol + obuna dialogi.
  const resume = !deepLinkTarget() && hasPendingResults() && hasFilter();
  const onboarding = !deepLinkTarget() && (resume || needsOnboarding());
  if (resume) wizEntryStep = "prefs";
  if (onboarding) await switchTab("filter");
  document.body.classList.remove("booting");

  await catalogReady;
  updateNavLabels();
  bindTabs();

  if (!onboarding) {
    const routed = await applyDeepLink();
    if (!routed) await renderHome();
  }
  if (resume) {
    ensureSubscribed()
      .then((ok) => ok && showResults())
      .catch((err) => showToast(err.message));
  }

  tabbar.removeAttribute("aria-busy");
}

init().catch((err) => {
  console.error(err);
  document.getElementById("app").innerHTML = `
    <div class="empty">
      <div class="empty-ico">${icon("clock")}</div>
      <div class="empty-title">Xatolik</div>
      <div class="empty-text">${escapeHtml(err.message)}</div>
    </div>`;
});
