const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try {
    tg.setHeaderColor("secondary_bg_color");
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
const TAPPABLE = "button, a, label, .chip, .country-row, [role='button']";

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
const ASSET_V = 61;
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

function flag(isoCode) {
  // ISO alpha-2 kodini bayroq emojisiga aylantiradi: har bir harf o'zining
  // "regional indicator" belgisiga ko'chiriladi (A -> 🇦).
  const code = String(isoCode || "").trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return "🏳️";
  return String.fromCodePoint(...[...code].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
}

function countryName(country) {
  return country["name_" + lang] || country.name_uz;
}

// Yo'nalish (`fields` ma'lumotnomasi) nomi foydalanuvchi tilida.
function fieldName(field) {
  return field ? field["name_" + lang] || field.name_uz : "";
}

// Profildagi yo'nalish tanlovi: qiymat — yo'nalish ID'si.
function majorOptions(selectedId) {
  return (
    `<option value="">${escapeHtml(t("profile.major_placeholder"))}</option>` +
    majors
      .map(
        (m) =>
          `<option value="${m.id}" ${String(selectedId) === String(m.id) ? "selected" : ""}>${escapeHtml(
            fieldName(m)
          )}</option>`
      )
      .join("")
  );
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
    "home.alert_title": "Yaqinlashayotgan muddat",
    "home.alert_body": "{program} · {days} kun qoldi",
    "home.section_shortcuts": "Tezkor amallar",
    "nav.kit": "Admission Kit",
    "kit.title": "Admission Kit",
    "kit.back": "Bosh sahifa",
    "profile.no_name": "Foydalanuvchi",
    "account.balance": "Hisobim",
    "account.topup_hint": "To'ldirish botda: /topup buyrug'ini yozing",
    "account.filter": "Qidiruv filtri",
    "account.filter_sub": "Daraja, yo'nalish, baho, davlatlar",
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
    "faq.a2": "Bosh sahifadagi «Qidiruvni sozlash» tugmasi orqali. Daraja, yo'nalish, baho va davlatlarni belgilasangiz, faqat sizga mos dasturlar qoladi.",
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
    "kit.pick_time": "Vaqtni tanlang",
    "kit.pick_time_text": "Uchrashuv uchun qulay vaqtni tanlang. Tanlaganingizdan keyin narx hisobingizdan yechiladi.",
    "kit.no_slots": "Hozircha bo'sh vaqt yo'q",
    "kit.no_slots_text": "Yangi vaqtlar qo'shilishi bilan bu yerda paydo bo'ladi.",
    "kit.slots_left": "{count} ta bo'sh vaqt",
    "kit.slot_taken": "Bu vaqtni boshqa birov band qildi. Boshqasini tanlang.",
    "kit.booked_title": "Yozildingiz",
    "kit.booked_text": "Uchrashuv vaqti: {slot}. Tez orada siz bilan bog'lanamiz.",
    "kit.minutes": "{count} daqiqa",
    "home.recap_title": "Mos dasturlar",
    "home.full_match": "To'liq mos",
    "home.recap_text": "Profilingizga mos keladigan barcha dasturlar — bir joyda.",
    "home.recap_cta": "Ko'rish",
    "home.unit_program": "dastur",
    "home.near_short": "{n} yaqin",
    "home.deadline_short": "{n} kun qoldi",
    "home.deadline_none": "Muddat yo'q",
    "home.fact_country": "Davlat",
    "home.fact_ielts": "IELTS",
    "home.fact_tuition": "Kontrakt",
    "home.fact_rank": "Reyting",
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
    "home.profile_progress": "Profil to'ldirilgan",
    "home.section_top": "Eng mos dastur",
    "home.setup_filter": "Qidiruvni sozlash",
    "home.empty_text": "Yo'nalish, daraja va davlatni tanlang — ro'yxat shunga qarab toraytiriladi.",
    "home.refine_filter": "Filtrni to'ldirish",

    "profile.section_academic": "Ta'lim",
    "profile.section_language": "Til sertifikati",
    "profile.section_preferences": "Afzalliklar",
    "profile.degree_level": "Daraja",
    "profile.degree_level.bachelor": "Bakalavr",
    "profile.degree_level.master": "Magistratura",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Yo'nalish",
    "profile.major_placeholder": "— yo'nalishni tanlang —",
    "profile.major_empty": "Katalogda hali yo'nalish yo'q.",
    "profile.gpa_scale": "Baholash tizimi",
    "profile.gpa_scale.5": "5 balli",
    "profile.gpa_scale.100": "100 balli",
    "profile.gpa_scale.4": "4.0 GPA",
    "profile.gpa_value": "Bahoingiz",
    "profile.gpa_us4": "US GPA",
    "profile.gpa_ects": "ECTS",
    "profile.gpa_bavarian": "Germaniya",
    "profile.study_language": "O'qish tili",
    "profile.study_language_any": "Farqi yo'q",
    "profile.study_language_hint": "Dastur qaysi tilda o'qitiladi. Sertifikat balidan alohida.",
    "profile.lang_cert_type": "Sertifikat turi",
    "profile.lang_cert_none": "Yo'q",
    "profile.lang_cert_score": "Ball",
    "profile.countries": "Maqsad davlatlar",
    "profile.countries_all": "Barchasi",
    "profile.countries_none": "Tanlanmagan",
    "profile.countries_count": "{n} ta davlat",
    "profile.rank": "Universitet reytingi",
    "profile.rank_hint": "Jahon reytingidagi o'rin",
    "profile.rank_any": "Farqi yo'q",
    "profile.app_fee": "Ariza to'lovi",
    "profile.app_fee_hint": "Ariza to'lovi bo'lgan dasturlar ham mos keladimi?",
    "profile.yes": "Ha",
    "profile.no": "Yo'q",
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
    "onboard.title": "Keling, sizga mos dasturlarni topamiz",
    "onboard.text": "Bir daqiqa vaqt oling. Bir necha savolga javob bersangiz, katalogdan aynan sizga to'g'ri keladigan dasturlar ajratiladi.",
    "onboard.step1": "Daraja va yo'nalishni tanlaysiz",
    "onboard.step2": "Bahoingiz va til sertifikatingizni kiritasiz",
    "onboard.step3": "Qaysi davlatlarda o'qimoqchi ekaningizni belgilaysiz",
    "onboard.cta": "Filtrni sozlash",
    "onboard.skip": "Keyinroq",
    "match.save": "Saqlash",
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
    "saved.removed_toast": "O'chirildi",
    "saved.status.planning": "Rejada",
    "saved.status.applied": "Topshirdim",
    "saved.status.rejected": "Rad etildi",
    "saved.status.accepted": "Qabul",
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
    "home.alert_title": "Приближается дедлайн",
    "home.alert_body": "{program} · осталось {days} дн.",
    "home.section_shortcuts": "Быстрые действия",
    "nav.kit": "Admission Kit",
    "kit.title": "Admission Kit",
    "kit.back": "На главную",
    "profile.no_name": "Пользователь",
    "account.balance": "Мой счёт",
    "account.topup_hint": "Пополнение в боте: отправьте команду /topup",
    "account.filter": "Фильтр поиска",
    "account.filter_sub": "Ступень, направление, балл, страны",
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
    "faq.a2": "Через кнопку «Настроить поиск» на главной. Укажите ступень, направление, балл и страны — останутся только подходящие программы.",
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
    "kit.pick_time": "Выберите время",
    "kit.pick_time_text": "Выберите удобное время встречи. После выбора стоимость спишется с баланса.",
    "kit.no_slots": "Свободного времени пока нет",
    "kit.no_slots_text": "Как только появятся новые слоты, они будут здесь.",
    "kit.slots_left": "свободных слотов: {count}",
    "kit.slot_taken": "Это время успели занять. Выберите другое.",
    "kit.booked_title": "Вы записаны",
    "kit.booked_text": "Время встречи: {slot}. Скоро свяжемся с вами.",
    "kit.minutes": "{count} мин",
    "home.recap_title": "Подходящие программы",
    "home.full_match": "Полное совпадение",
    "home.recap_text": "Все программы, подходящие вашему профилю, — в одном месте.",
    "home.recap_cta": "Смотреть",
    "home.unit_program": "программ",
    "home.near_short": "{n} близких",
    "home.deadline_short": "осталось {n} дн.",
    "home.deadline_none": "Без дедлайна",
    "home.fact_country": "Страна",
    "home.fact_ielts": "IELTS",
    "home.fact_tuition": "Контракт",
    "home.fact_rank": "Рейтинг",
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
    "home.profile_progress": "Профиль заполнен",
    "home.section_top": "Лучшее совпадение",
    "home.setup_filter": "Настроить поиск",
    "home.empty_text": "Выберите направление, уровень и страну — список сузится под вас.",
    "home.refine_filter": "Дополнить фильтр",

    "profile.section_academic": "Образование",
    "profile.section_language": "Языковой сертификат",
    "profile.section_preferences": "Предпочтения",
    "profile.degree_level": "Степень",
    "profile.degree_level.bachelor": "Бакалавриат",
    "profile.degree_level.master": "Магистратура",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Направление",
    "profile.major_placeholder": "— выберите направление —",
    "profile.major_empty": "В каталоге пока нет направлений.",
    "profile.gpa_scale": "Система оценок",
    "profile.gpa_scale.5": "5-балльная",
    "profile.gpa_scale.100": "100-балльная",
    "profile.gpa_scale.4": "4.0 GPA",
    "profile.gpa_value": "Ваш балл",
    "profile.gpa_us4": "US GPA",
    "profile.gpa_ects": "ECTS",
    "profile.gpa_bavarian": "Германия",
    "profile.study_language": "Язык обучения",
    "profile.study_language_any": "Не важно",
    "profile.study_language_hint": "На каком языке ведётся программа. Это не балл сертификата.",
    "profile.lang_cert_type": "Тип сертификата",
    "profile.lang_cert_none": "Нет",
    "profile.lang_cert_score": "Балл",
    "profile.countries": "Целевые страны",
    "profile.countries_none": "Не выбрано",
    "profile.countries_count": "Стран: {n}",
    "profile.rank": "Рейтинг университета",
    "profile.rank_hint": "Место в мировом рейтинге",
    "profile.rank_any": "Не важно",
    "profile.app_fee": "Плата за подачу заявки",
    "profile.app_fee_hint": "Подходят ли программы с платной подачей заявки?",
    "profile.yes": "Да",
    "profile.no": "Нет",
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
    "onboard.title": "Давайте подберём подходящие программы",
    "onboard.text": "Это займёт минуту. Ответьте на несколько вопросов, и из каталога останутся только те программы, которые вам подходят.",
    "onboard.step1": "Выберете ступень и направление",
    "onboard.step2": "Укажете свой балл и языковой сертификат",
    "onboard.step3": "Отметите страны, где хотите учиться",
    "onboard.cta": "Настроить фильтр",
    "onboard.skip": "Позже",
    "match.save": "Сохранить",
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
    "saved.removed_toast": "Удалено",
    "saved.status.planning": "В планах",
    "saved.status.applied": "Подал",
    "saved.status.rejected": "Отказ",
    "saved.status.accepted": "Принят",
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
    "home.alert_title": "Deadline approaching",
    "home.alert_body": "{program} · {days} day(s) left",
    "home.section_shortcuts": "Quick actions",
    "nav.kit": "Admission Kit",
    "kit.title": "Admission Kit",
    "kit.back": "Back to home",
    "profile.no_name": "User",
    "account.balance": "My balance",
    "account.topup_hint": "Top up in the bot: send the /topup command",
    "account.filter": "Search filter",
    "account.filter_sub": "Degree, field, grade, countries",
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
    "faq.a2": "Use «Set up your search» on the home screen. Once you set degree, field, grade and countries, only matching programmes remain.",
    "faq.q3": "How do I top up my balance?",
    "faq.a3": "Send /topup to the bot, enter the amount and transfer to the card. Then send the receipt photo via /chekyubor — the balance is credited after review.",
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
    "kit.pick_time": "Pick a time",
    "kit.pick_time_text": "Choose a time that works for you. The price is taken from your balance once you pick.",
    "kit.no_slots": "No free times yet",
    "kit.no_slots_text": "New slots will show up here as soon as they are added.",
    "kit.slots_left": "{count} slots free",
    "kit.slot_taken": "Someone just took that time. Please pick another.",
    "kit.booked_title": "You are booked",
    "kit.booked_text": "Meeting time: {slot}. We will contact you shortly.",
    "kit.minutes": "{count} min",
    "home.recap_title": "Your matches",
    "home.full_match": "Full match",
    "home.recap_text": "Every programme that fits your profile, in one place.",
    "home.recap_cta": "Explore",
    "home.unit_program": "programmes",
    "home.near_short": "{n} close",
    "home.deadline_short": "{n} days left",
    "home.deadline_none": "No deadline",
    "home.fact_country": "Country",
    "home.fact_ielts": "IELTS",
    "home.fact_tuition": "Tuition",
    "home.fact_rank": "Ranking",
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
    "home.profile_progress": "Profile complete",
    "home.section_top": "Best match",
    "home.setup_filter": "Set up your search",
    "home.empty_text": "Pick a field, level and country — the list narrows down to fit you.",
    "home.refine_filter": "Refine your filter",

    "profile.section_academic": "Academic",
    "profile.section_language": "Language certificate",
    "profile.section_preferences": "Preferences",
    "profile.degree_level": "Degree",
    "profile.degree_level.bachelor": "Bachelor's",
    "profile.degree_level.master": "Master's",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Major",
    "profile.major_placeholder": "— select a field —",
    "profile.major_empty": "No fields in the catalog yet.",
    "profile.gpa_scale": "Grading system",
    "profile.gpa_scale.5": "5-point",
    "profile.gpa_scale.100": "100-point",
    "profile.gpa_scale.4": "4.0 GPA",
    "profile.gpa_value": "Your grade",
    "profile.gpa_us4": "US GPA",
    "profile.gpa_ects": "ECTS",
    "profile.gpa_bavarian": "Germany",
    "profile.study_language": "Language of study",
    "profile.study_language_any": "Any",
    "profile.study_language_hint": "The language the programme is taught in. Separate from your test score.",
    "profile.lang_cert_type": "Certificate type",
    "profile.lang_cert_none": "None",
    "profile.lang_cert_score": "Score",
    "profile.countries": "Target countries",
    "profile.countries_none": "None selected",
    "profile.countries_count": "{n} countries",
    "profile.rank": "University ranking",
    "profile.rank_hint": "Position in world rankings",
    "profile.rank_any": "Any",
    "profile.app_fee": "Application fee",
    "profile.app_fee_hint": "Are programs with an application fee acceptable?",
    "profile.yes": "Yes",
    "profile.no": "No",
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
    "onboard.title": "Let's find programmes that fit you",
    "onboard.text": "It takes a minute. Answer a few questions and the catalogue narrows down to the programmes that actually fit you.",
    "onboard.step1": "Pick your degree level and field",
    "onboard.step2": "Add your grade and language certificate",
    "onboard.step3": "Choose the countries you want to study in",
    "onboard.cta": "Set up filter",
    "onboard.skip": "Later",
    "match.save": "Save",
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
    "saved.removed_toast": "Removed",
    "saved.status.planning": "Planning",
    "saved.status.applied": "Applied",
    "saved.status.rejected": "Rejected",
    "saved.status.accepted": "Accepted",
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
  el.innerHTML = `${icon("check")}<span>${escapeHtml(message)}</span>`;
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 1900);
}

function skeletons(count, short) {
  return Array.from({ length: count }, () => `<div class="skeleton${short ? " short" : ""}"></div>`).join("");
}

let profile = null;
let countries = [];
let majors = [];
// Katalogda haqiqatan uchraydigan o'qish tillari (kanonik inglizcha
// nomlar). Nomlarni `instructionLanguage()` foydalanuvchi tiliga o'giradi.
let studyLanguages = [];

async function loadProfile() {
  profile = await api("/me");
  lang = profile.ui_language || lang;
}

async function loadCountries() {
  countries = await api("/countries");
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
    profile.gpa_raw !== null && profile.gpa_scale !== null,
    profile.language_certificates.length > 0,
    // "Farqi yo'q" ham javob: ariza to'lovi bo'yicha tanlov qilingani yetarli.
    // Reyting oralig'i ixtiyoriy afzallik — foizga qo'shilmaydi.
    profile.application_fee_ok !== null,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

// Bosh sahifadagi katta halqa: ichida raqam, atrofida to'liq mos dasturlar ulushi.
function bigRing(pct) {
  // 106px: ichki doiraga "dastur / программ / programmes" so'zi ham bemalol
  // sig'sin. 98px'da uzunroq so'z chetga tegib, siqilib ko'rinardi.
  const r = 42;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - Math.max(0, Math.min(100, pct)) / 100);
  return `
    <svg class="ring-svg" width="106" height="106" viewBox="0 0 106 106">
      <circle class="ring-bg" cx="53" cy="53" r="${r}" fill="none" stroke-width="10"/>
      <circle class="ring-fg" cx="53" cy="53" r="${r}" fill="none" stroke-width="10"
              stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}"/>
    </svg>`;
}

// Katta summani qisqartiradi: 9250 -> "9.3k". Faktlar ustuni tor, to'liq raqam sig'maydi.
function compactNumber(value) {
  const n = Number(value);
  if (!isFinite(n)) return "—";
  if (n >= 10000) return Math.round(n / 1000) + "k";
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "k";
  return String(Math.round(n));
}

// ============ Home ============

async function renderHome() {
  const el = document.getElementById("view-home");
  const pct = profileCompleteness();
  const ready = hasFilter();

  // Salomlashish qatori (avatar, qidiruv va "saqlangan" tugmalari) olib
  // tashlandi: ikkala tugma ham pastdagi tab panelida bor edi, ism esa
  // Profil sahifasida ko'rinadi. Sahifa darhol asosiy kartadan boshlanadi.
  el.innerHTML = `
    ${
      // Filtr hali sozlanmagan bo'lsa halqa ham, foiz ham ko'rsatilmaydi.
      // Ilgari bu yerda bo'sh oq halqa ichida chiziqcha turardi — u xuddi
      // yuklanmay qolgan yoki buzilgan elementdek ko'rinardi. Hisoblab
      // ko'rsatadigan narsa yo'q ekan, o'rniga aniq taklif turadi.
      ready
        ? `<div class="hero home-hero">
             <div class="hero-main">
               <div class="hero-chip">${icon("spark")}<span>${t(
                 "home.profile_progress"
               )}</span></div>
               <div class="hero-big">${pct}<span>%</span></div>
               <button type="button" class="hero-pill" id="home-cta">
                 <span>${t("home.refine_filter")}</span>${icon("chevron")}
               </button>
             </div>
             <div class="ring-lg" id="hero-ring">
               ${bigRing(0)}
               <div class="ring-core"><b>—</b><span>${t("home.unit_program")}</span></div>
             </div>
           </div>`
        : `<div class="hero home-hero hero-invite">
             <div class="hero-lead">${t("onboard.title")}</div>
             <div class="hero-note">${t("home.empty_text")}</div>
             <button type="button" class="hero-pill hero-pill-solid" id="home-cta">
               <span>${t("home.setup_filter")}</span>${icon("chevron")}
             </button>
           </div>`
    }

    <div id="home-alert"></div>

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
        <div class="hx-mini" data-goto="match" role="button" tabindex="0">
          <div class="hx-mini-head">
            <span class="hx-mini-label">${t("home.full_match")}</span>
            <span class="hx-mini-ico">${icon("check")}</span>
          </div>
          <div class="hx-mini-value" id="mini-green-value">—</div>
          <div class="hx-mini-foot" id="mini-green-foot"></div>
          <div class="split" id="mini-green-bar">
            <span class="split-green" style="width:0"></span>
            <span class="split-amber" style="width:0"></span>
          </div>
        </div>
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
        </div>
      </div>
    </div>

    <div id="home-top"></div>

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
      <button type="button" class="quick rose" data-action="gpa">
        <img class="quick-ico" src="icon-gpa.png?v=${ASSET_V}" alt="" aria-hidden="true">
        <span class="quick-label">${t("home.shortcut_gpa")}</span>
      </button>
    </div>
  `;

  document.getElementById("home-cta").addEventListener("click", () => switchTab("filter"));

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
      if (card.dataset.action === "gpa") openGpaSheet();
      else switchTab(card.dataset.goto);
    });
  });

  const [matches, saved] = await Promise.all([api("/match"), api("/saved")]);
  const green = matches.filter((m) => m.level === "green").length;
  const yellow = matches.filter((m) => m.level === "yellow").length;
  const total = green + yellow;
  const greenShare = total ? (green / total) * 100 : 0;

  const upcoming = saved
    .filter((s) => s.nearest_deadline_days_left !== null && s.nearest_deadline_days_left >= 0)
    .sort((a, b) => a.nearest_deadline_days_left - b.nearest_deadline_days_left);

  // Halqa faqat filtr sozlangan holatda chiziladi — aks holda bu element
  // umuman yo'q (hero o'rniga taklif ko'rsatiladi).
  const ringEl = document.getElementById("hero-ring");
  if (ringEl) {
    ringEl.innerHTML =
      bigRing(greenShare) +
      `<div class="ring-core"><b>${compactNumber(total)}</b><span>${t(
        "home.unit_program"
      )}</span></div>`;
  }

  document.getElementById("mini-green-value").textContent = ready ? green : "—";
  document.getElementById("mini-green-foot").innerHTML = `<span class="hx-tag">${
    ready ? t("home.near_short", { n: yellow }) : t("home.setup_filter")
  }</span>`;
  const greenBar = document.getElementById("mini-green-bar");
  greenBar.children[0].style.width = ready ? `${greenShare}%` : "0";
  greenBar.children[1].style.width = ready ? `${100 - greenShare}%` : "0";

  document.getElementById("mini-saved-value").textContent = saved.length;
  document.getElementById("mini-saved-foot").innerHTML = `<span class="hx-tag">${
    upcoming.length
      ? t("home.deadline_short", { n: upcoming[0].nearest_deadline_days_left })
      : t("home.deadline_none")
  }</span>`;
  document.getElementById("mini-saved-bar").children[0].style.width = saved.length
    ? `${(upcoming.length / saved.length) * 100}%`
    : "0";

  // Eng mos bitta dastur — bosh sahifada haqiqiy natija ko'rinsin, faqat
  // raqamlar emas. Filtr yo'q bo'lsa "eng mos" degan gap ma'nosiz.
  const best = ready ? matches.find((m) => m.level === "green") || matches[0] : null;
  if (best) {
    const facts = [
      {
        label: t("home.fact_country"),
        value: `<span class="fx-flag">${flag(best.country.iso_code)}</span>`,
      },
      { label: t("home.fact_ielts"), value: best.ielts_min ? escapeHtml(String(best.ielts_min)) : "—" },
      {
        label: t("home.fact_tuition"),
        value:
          best.tuition_amount !== null && best.tuition_amount !== undefined
            ? `${compactNumber(best.tuition_amount)}<i>${escapeHtml(best.tuition_currency || "")}</i>`
            : "—",
      },
      {
        label: t("home.fact_rank"),
        value: best.university_ranking ? "#" + best.university_ranking : "—",
      },
    ];

    document.getElementById("home-top").innerHTML = `
      <div class="section-head"><span class="section-title">${t("home.section_top")}</span></div>
      <div class="top-card">
        <div class="top-head">
          <div class="top-open program-open" data-id="${best.id}" role="button" tabindex="0">
            ${avatar(best.university, best.university_logo)}
            <div class="top-head-text">
              <div class="top-title">${escapeHtml(best.name)}</div>
              <div class="top-sub">${escapeHtml(best.university)}</div>
            </div>
          </div>
          <button type="button" class="top-btn top-save" data-id="${best.id}" ${
            best.saved ? "disabled" : ""
          } aria-label="${escapeHtml(t("match.save"))}">
            ${best.saved ? icon("check") : icon("plus")}
          </button>
          <button type="button" class="top-btn program-open" data-id="${best.id}"
                  aria-label="${escapeHtml(t("match.details"))}">${icon("chevron")}</button>
        </div>
        <div class="top-facts">
          ${facts
            .map(
              (f) => `<div class="top-fact">
                <div class="top-fact-label">${escapeHtml(f.label)}</div>
                <div class="top-fact-value">${f.value}</div>
              </div>`
            )
            .join("")}
        </div>
      </div>`;

    const topSave = document.querySelector(".top-save");
    topSave.addEventListener("click", async () => {
      haptic("light");
      await api(`/saved/${topSave.dataset.id}`, { method: "POST" });
      topSave.disabled = true;
      topSave.innerHTML = icon("check");
      haptic("success");
      showToast(t("match.saved_toast"));
    });
    bindProgramOpeners(document.getElementById("home-top"));
  }

  if (upcoming.length) {
    const n = upcoming[0];
    const urgent = n.nearest_deadline_days_left <= 7;
    document.getElementById("home-alert").innerHTML = `
      <div class="alert ${urgent ? "urgent" : ""}">
        <div class="alert-ico">${icon("clock")}</div>
        <div>
          <div class="alert-title">${t("home.alert_title")}</div>
          <div class="alert-body">${t("home.alert_body", {
            program: escapeHtml(n.program_name),
            days: n.nearest_deadline_days_left,
          })}</div>
        </div>
      </div>`;
  }
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
      // Davlatlar va "Hammasi" — to'liq filtr sahifasida.
      if (key === "all" || key === "countries") {
        switchTab("filter");
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

  el.innerHTML = noFilterNote(matches.length) + miniFilterBar() + matches
    .map((m) => {
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
          ? `${Number(m.tuition_amount).toLocaleString()} ${escapeHtml(m.tuition_currency || "")}`
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
    })
    .join("");

  el.querySelectorAll(".save-btn").forEach((btn) => {
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

  bindFilterCta(el);
  bindMiniFilter(el);
  bindProgramOpeners(el);
}

function bindProgramOpeners(root) {
  root.querySelectorAll(".program-open").forEach((node) => {
    node.addEventListener("click", () => openProgramSheet(node.dataset.id));
    node.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openProgramSheet(node.dataset.id);
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
      ${countries
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
    btn.addEventListener("click", () => openScholarshipSheet(byId.get(btn.dataset.id)));
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

  const deadline = s.nearest_deadline
    ? `<span class="pill ${
        s.nearest_deadline_days_left !== null && s.nearest_deadline_days_left <= 30 ? "red" : ""
      }">${icon("clock")}${t("scholarships.deadline", { date: escapeHtml(s.nearest_deadline) })}</span>`
    : "";

  // Bir qarashda eng kerakli raqam: oylik stipendiya.
  const stipend = stipendText(s);

  return `
    <div class="card gr-card details-btn" data-id="${s.id}" role="button" tabindex="0">
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

function closeSheet() {
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
let onboardingShown = false;

function openOnboardingSheet() {
  onboardingShown = true;
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  const steps = [1, 2, 3]
    .map(
      (n) => `
      <li class="onb-step"><span class="onb-num">${n}</span><span>${t("onboard.step" + n)}</span></li>`
    )
    .join("");

  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="onb">
      <img class="onb-ico" src="icon-bell.png?v=${ASSET_V}" alt="" aria-hidden="true">
      <div class="onb-title">${t("onboard.title")}</div>
      <div class="onb-text">${t("onboard.text")}</div>
      <ol class="onb-steps">${steps}</ol>
      <button type="button" class="btn btn-accent btn-block" id="onb-cta">${t("onboard.cta")}</button>
      <button type="button" class="btn btn-quiet btn-block" id="onb-skip">${t("onboard.skip")}</button>
    </div>
  `,
    sheet
  );

  document.getElementById("onb-cta").addEventListener("click", () => {
    haptic("light");
    closeSheet();
    switchTab("filter");
  });
  document.getElementById("onb-skip").addEventListener("click", () => {
    haptic("light");
    closeSheet();
  });
}

// ============ GPA konvertor ============

// Har bir O'zbekiston shkalasi uchun ruxsat etilgan oraliq va namuna qiymat.
const GPA_SCALES = {
  5: { min: 2, max: 5, step: "0.01", example: "4.5" },
  100: { min: 0, max: 100, step: "0.1", example: "85" },
  4: { min: 0, max: 4, step: "0.01", example: "3.5" },
};

function openGpaSheet() {
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  // Profilda baho bo'lsa, konvertor shu bilan ochiladi.
  let scale = profile && profile.gpa_scale ? String(profile.gpa_scale) : "100";
  const initial = profile && profile.gpa_raw !== null && profile.gpa_scale ? profile.gpa_raw : "";

  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-head gpa-head">
      <img class="gpa-head-ico" src="icon-gpa.png?v=${ASSET_V}" alt="" aria-hidden="true">
      <div>
        <div class="sheet-title">${t("gpa.title")}</div>
        <div class="sheet-sub">${t("gpa.subtitle")}</div>
      </div>
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("gpa.scale")}</div>
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
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("gpa.value")}</div>
      <input type="number" inputmode="decimal" id="gpa-sheet-input" class="gpa-input"
             value="${escapeHtml(initial)}" />
      <div class="gpa-range" id="gpa-sheet-range"></div>
    </div>

    <div id="gpa-sheet-result"></div>
  `,
    sheet,
    { tall: true }
  );

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
      <div class="sheet-section">
        <div class="sheet-section-title">${t("gpa.results")}</div>
        <div class="gpa-results">
          ${card("US", t("gpa.us"), `${r.us4.toFixed(2)}`, t("gpa.us_sub"))}
          ${card("GB", t("gpa.uk"), escapeHtml(t("gpa.uk_short." + r.uk)), t("gpa.uk_class." + r.uk))}
          ${card("EU", t("gpa.eu"), escapeHtml(r.ects), t("gpa.eu_sub"))}
          ${card("DE", t("gpa.de"), `${r.bavarian.toFixed(1)}`, t("gpa.de_sub"))}
        </div>
      </div>
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

async function openProgramSheet(programId) {
  haptic("light");
  ensureSheet();
  const sheet = document.querySelector(".sheet");

  showSheet(
    `<div class="sheet-handle"></div>${skeletons(4)}`,
    sheet
  );

  const p = await api(`/programs/${programId}`);

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
  const certRows =
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
      ? (cost ? row(t("program.tuition"), money(cost.tuition_amount, cost.currency)) : "") +
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
    : `<div class="sheet-empty">${t("program.no_deadlines")}</div>`;

  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-head">
      ${avatar(p.university, p.university_logo)}
      <div>
        <div class="sheet-title">${escapeHtml(p.name)}${
          p.abbreviation ? `<span class="abbr">${escapeHtml(p.abbreviation)}</span>` : ""
        }</div>
        <div class="sheet-sub">${escapeHtml(p.university)} · ${escapeHtml(p.city)}</div>
      </div>
    </div>
    <div class="meta-row">
      <span class="pill"><span class="chip-flag">${flag(p.country.iso_code)}</span>${escapeHtml(
        countryName(p.country)
      )}</span>
      <span class="pill">${icon("cap")}${t("profile.degree_level." + p.degree_level)}</span>
      <span class="pill">${icon("clock")}${p.duration_years} ${t("program.years")}</span>
      ${
        p.university_ranking
          ? `<span class="pill rank-pill" title="${escapeHtml(t("program.ranking_label"))}">${icon(
              "award"
            )}${t("program.ranking", { n: p.university_ranking })}</span>`
          : ""
      }
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("program.about")}</div>
      ${row(t("program.field"), p.field ? escapeHtml(fieldName(p.field)) : dash)}
      ${row(t("program.language"), escapeHtml(instructionLanguage(p.language_of_instruction)))}
      ${row(t("program.intake"), escapeHtml(p.intake_term))}
      ${p.notes ? `<div class="sheet-note">${escapeHtml(p.notes)}</div>` : ""}
      ${missingNote(p.missing_fields)}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("program.language_certs")}</div>
      ${languageCerts}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("program.costs")}</div>
      ${costs}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("program.requirements_docs")}</div>
      ${requirements}
    </div>

    ${
      p.has_scholarship === null || p.has_scholarship === undefined
        ? ""
        : `<div class="sheet-section">
             <div class="sheet-section-title">${t("program.own_scholarship")}</div>
             ${
               // Bitta karta: holat + izoh; havola bo'lsa kartaning o'zi bosiladi.
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
             }
           </div>`
    }

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.deadlines")}</div>
      ${deadlines}
    </div>

    <div class="sheet-verified">${t("program.verified_at", {
      date: escapeHtml(p.verified_at),
    })}</div>

    <div class="sheet-actions">
      <button type="button" class="btn ${
        p.saved ? "btn-done" : "btn-accent"
      } btn-block" id="sheet-save" ${p.saved ? "disabled" : ""}>
        ${p.saved ? icon("check") + t("match.saved") : icon("plus") + t("match.save")}
      </button>
      <button type="button" class="btn btn-soft btn-block" id="sheet-open-site">
        ${t("program.official_page")}
      </button>
    </div>
  `,
    sheet
  );

  // Dasturning o'z stipendiyasi yo'q — davlat grantlariga yo'naltiramiz.
  const toGrants = document.getElementById("sheet-to-grants");
  if (toGrants) {
    toGrants.addEventListener("click", () => {
      haptic("light");
      closeSheet();
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
      saveBtn.className = "btn btn-done btn-block";
      saveBtn.innerHTML = icon("check") + t("match.saved");
      haptic("success");
      showToast(t("match.saved_toast"));
    });
  }
}

function openScholarshipSheet(s) {
  haptic("light");
  ensureSheet();
  const sheet = document.querySelector(".sheet");

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
            `${escapeHtml(d.date.split(" ")[0])}<br><span class="card-sub">${left}</span>`
          );
        })
        .join("")
    : `<div class="card-sub">${t("scholarships.not_specified")}</div>`;

  const extras = [
    [s.extras_flight, "plane", "scholarships.extra_flight"],
    [s.extras_insurance, "shield", "scholarships.extra_insurance"],
    [s.extras_dormitory, "bed", "scholarships.extra_dormitory"],
    [s.extras_language_course, "lang", "scholarships.extra_language"],
  ]
    .filter(([on]) => on)
    .map(([, ic, key]) => `<span class="pill">${icon(ic)}${t(key)}</span>`)
    .join("");

  sheet.innerHTML = `
    <div class="sheet-handle"></div>
    <div class="sheet-head">
      ${avatar(s.name, s.logo)}
      <div><div class="sheet-title">${escapeHtml(s.name)}</div></div>
    </div>
    <div class="meta-row">
      <span class="pill ${s.coverage_type === "full" ? "green" : "amber"}">${icon("award")}${t(
        "scholarships.coverage." + s.coverage_type
      )}</span>
      ${s.countries
        .map(
          (c) =>
            `<span class="pill"><span class="chip-flag">${flag(c.iso_code)}</span>${escapeHtml(
              countryName(c)
            )}</span>`
        )
        .join("")}
    </div>
    ${
      s.description
        ? `<div class="sheet-section">
             <div class="sheet-section-title">${t("scholarships.about")}</div>
             <div class="sheet-text">${escapeHtml(s.description)}</div>
           </div>`
        : ""
    }

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.money")}</div>
      ${row(t("scholarships.stipend"), escapeHtml(stipend))}
      ${extras ? `<div class="meta-row sheet-extras">${extras}</div>` : ""}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.study")}</div>
      ${row(t("scholarships.degree_levels"), degrees || dash)}
      ${row(t("scholarships.duration"), duration)}
      ${row(
        t("program.language"),
        s.study_language ? escapeHtml(instructionLanguage(s.study_language)) : dash
      )}
      ${row(t("scholarships.uni_choice"), t("scholarships.uni_choice." + s.university_choice))}
      ${
        s.universities_text
          ? row(t("scholarships.universities"), multiline(s.universities_text))
          : ""
      }
      ${s.selected_by ? row(t("scholarships.selected_by"), escapeHtml(s.selected_by)) : ""}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.requirements")}</div>
      ${requirements}
      <div class="sheet-note">${t("scholarships.verify_hint")}</div>
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.deadlines")}</div>
      ${deadlines}
    </div>

    <div class="sheet-actions">
      <button type="button" class="btn btn-accent btn-block" id="sheet-open-site">
        ${t("scholarships.official_site")}
      </button>
    </div>
  `;

  document.getElementById("sheet-open-site").addEventListener("click", () => {
    haptic("light");
    // Telegram ichida tashqi havolani to'g'ri ochish usuli.
    if (tg && typeof tg.openLink === "function") tg.openLink(s.source_url);
    else window.open(s.source_url, "_blank", "noopener");
  });

  document.querySelector(".sheet-backdrop").classList.add("open");
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

// ============ Saved ============

const SAVED_STATUSES = ["planning", "applied", "rejected", "accepted"];

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

  el.innerHTML = items
    .map((s) => {
      const days = s.nearest_deadline_days_left;
      const hasDays = days !== null && days >= 0;
      const deadlinePill = s.nearest_deadline
        ? `<span class="pill ${hasDays && days <= 7 ? "red" : ""}">${icon("clock")}${
            hasDays ? t("saved.days_left", { days }) : escapeHtml(s.nearest_deadline)
          }</span>`
        : `<span class="pill">${icon("clock")}${t("saved.deadline")}: ${t("saved.no_deadline")}</span>`;

      return `
        <div class="card" data-saved-id="${s.id}">
          <div class="card-top program-open" data-id="${s.program_id}" role="button" tabindex="0">
            ${avatar(s.university, s.university_logo)}
            <div class="card-body">
              <div class="card-title">${escapeHtml(s.program_name)}</div>
              <div class="card-sub">${escapeHtml(s.university)}, ${flag(
                s.country.iso_code
              )} ${escapeHtml(countryName(s.country))}</div>
              <div class="meta-row">${deadlinePill}</div>
            </div>
            <span class="card-chevron">${icon("chevron")}</span>
          </div>
          <div class="seg" data-id="${s.id}">
            ${SAVED_STATUSES.map(
              (st) => `<div class="seg-item ${st === s.status ? "active" : ""}" data-status="${st}">${t(
                "saved.status." + st
              )}</div>`
            ).join("")}
          </div>
          <div class="card-actions">
            <button type="button" class="btn btn-quiet remove-btn" data-id="${s.id}">${icon("trash")}${t("saved.remove")}</button>
          </div>
        </div>`;
    })
    .join("");

  bindProgramOpeners(el);

  el.querySelectorAll(".seg").forEach((seg) => {
    seg.querySelectorAll(".seg-item").forEach((item) => {
      item.addEventListener("click", async () => {
        if (item.classList.contains("active")) return;
        haptic("light");
        seg.querySelectorAll(".seg-item").forEach((i) => i.classList.remove("active"));
        item.classList.add("active");
        await api(`/saved/${seg.dataset.id}`, {
          method: "PATCH",
          body: JSON.stringify({ status: item.dataset.status }),
        });
      });
    });
  });

  el.querySelectorAll(".remove-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      haptic("medium");
      await api(`/saved/${btn.dataset.id}`, { method: "DELETE" });
      btn.closest(".card").remove();
      showToast(t("saved.removed_toast"));
      if (!el.querySelector(".card")) await renderSaved();
    });
  });
}

// ============ Profile ============

// Bo'lim sarlavhasi + ikonka (faqat profil ekranida ishlatiladi).
function profileSection(iconName, title) {
  return `<div class="section-head">
      <span class="section-title sec-ico">${icon(iconName)}<span>${title}</span></span>
    </div>`;
}

const RANK_RANGES = ["1-100", "101-300", "301-500", "500+"];

// Filtr endi ALOHIDA sahifa: pastki panelda yo'q, unga faqat bosh
// sahifadan va Dasturlar ro'yxatidagi ogohlantirishdan kiriladi. Profil
// tabi esa akkaunt menyusi bo'lib qoldi (renderProfile).
// O'qish tili variantlari. Ro'yxat katalogdan keladi, nomlar esa
// foydalanuvchi tiliga o'giriladi (LANGUAGE_NAMES).
function studyLanguageOptions(selected) {
  const any = `<option value="" ${selected ? "" : "selected"}>${escapeHtml(
    t("profile.study_language_any")
  )}</option>`;
  return (
    any +
    studyLanguages
      .map(
        (value) =>
          `<option value="${escapeHtml(value)}" ${
            String(selected) === String(value) ? "selected" : ""
          }>${escapeHtml(instructionLanguage(value))}</option>`
      )
      .join("")
  );
}

function renderFilter() {
  const el = document.getElementById("view-filter");
  const cert = profile.language_certificates[0] || {};
  const certType = cert.type || "";
  const certScore = cert.score ?? "";
  const feeValue =
    profile.application_fee_ok === null || profile.application_fee_ok === undefined
      ? ""
      : profile.application_fee_ok
        ? "yes"
        : "no";

  const chips = (id, options, activeValue, multi) => `
    <div class="chip-group" id="${id}">
      ${options
        .map((o) => {
          const active = multi ? activeValue.includes(o.value) : String(activeValue) === String(o.value);
          return `<div class="chip ${active ? "active" : ""}" data-value="${escapeHtml(o.value)}">${escapeHtml(
            o.label
          )}</div>`;
        })
        .join("")}
    </div>`;

  el.innerHTML = `
    <button type="button" class="kit-back" id="filter-back">
      ${icon("chevron")}<span>${t("kit.back")}</span>
    </button>
    ${profileSection("cap", t("profile.section_academic"))}
    <div class="group">
      <div class="field">
        <label>${t("profile.degree_level")}</label>
        ${chips(
          "degree-chips",
          ["bachelor", "master", "phd"].map((d) => ({ value: d, label: t("profile.degree_level." + d) })),
          profile.degree_level || ""
        )}
      </div>
      <div class="field">
        <label>${t("profile.major")}</label>
        <select id="major-input" class="select-input">
          ${majorOptions(profile.field_id)}
        </select>
        ${
          majors.length
            ? ""
            : `<small class="field-hint">${escapeHtml(t("profile.major_empty"))}</small>`
        }
      </div>
      <div class="field">
        <label>${t("profile.gpa_scale")}</label>
        ${chips(
          "gpa-scale-chips",
          ["5", "100", "4"].map((s) => ({ value: s, label: t("profile.gpa_scale." + s) })),
          profile.gpa_scale || ""
        )}
      </div>
      <div class="field">
        <label>${t("profile.gpa_value")}</label>
        <!-- cert-score-input bilan bir xil sabab: type="number" da
             vergulli lokalda nuqta yo'qolib, "3.5" -> "35" bo'lardi. -->
        <input type="text" inputmode="decimal" autocomplete="off"
               id="gpa-value-input" placeholder="—" value="${
          profile.gpa_raw ?? ""
        }" />
        <div id="gpa-preview"></div>
      </div>
    </div>

    ${profileSection("lang", t("profile.section_language"))}
    <div class="group">
      <div class="field">
        <label>${t("profile.study_language")}</label>
        <select id="study-language-input" class="select-input">
          ${studyLanguageOptions(profile.study_language)}
        </select>
        <small class="field-hint">${escapeHtml(t("profile.study_language_hint"))}</small>
      </div>
      <div class="field">
        <label>${t("profile.lang_cert_type")}</label>
        ${chips(
          "cert-type-chips",
          [
            { value: "IELTS", label: "IELTS" },
            { value: "TOEFL", label: "TOEFL" },
            { value: "", label: t("profile.lang_cert_none") },
          ],
          certType
        )}
      </div>
      <div class="field" id="cert-score-field" ${certType ? "" : "hidden"}>
        <label>${t("profile.lang_cert_score")}</label>
        <!-- ATAYLAB type="text": type="number" da qurilma lokali vergul
             ishlatsa, iOS "." bosilishini shunchaki yutib yuborardi va
             "7.5" o'rniga "75" qolardi. Endi vergul ham, nuqta ham
             qabul qilinadi va o'qishda nuqtaga keltiriladi. -->
        <input type="text" inputmode="decimal" autocomplete="off"
               id="cert-score-input" placeholder="—" value="${certScore}" />
      </div>
    </div>

    ${profileSection("globe", t("profile.section_preferences"))}
    <div class="group">
      <div class="field field-collapse">
        <button type="button" class="collapse-head" id="country-toggle" aria-expanded="false" aria-controls="country-collapse">
          <span class="collapse-label">${t("profile.countries")}</span>
          <span class="collapse-value" id="country-summary"></span>
          <span class="collapse-chevron">${icon("chevron")}</span>
        </button>
        <div class="collapse-body" id="country-collapse" hidden>
          <div class="country-list" id="country-list">
            <button type="button" class="country-row country-all" id="country-all">
              <span class="country-flag">${icon("globe")}</span>
              <span class="country-name">${escapeHtml(t("profile.countries_all"))}</span>
              <span class="country-check">${icon("check")}</span>
            </button>
            ${countries
              .map((c) => {
                const active = profile.target_country_ids.map(String).includes(String(c.id));
                return `
                  <button type="button" class="country-row ${active ? "active" : ""}" data-value="${c.id}">
                    <span class="country-flag">${flag(c.iso_code)}</span>
                    <span class="country-name">${escapeHtml(countryName(c))}</span>
                    <span class="country-check">${icon("check")}</span>
                  </button>`;
              })
              .join("")}
          </div>
        </div>
      </div>
      <div class="field">
        <label>${t("profile.rank")}</label>
        ${chips(
          "rank-chips",
          [{ value: "", label: t("profile.rank_any") }].concat(
            RANK_RANGES.map((r) => ({ value: r, label: r }))
          ),
          profile.university_rank_range || ""
        )}
        <small class="field-hint">${escapeHtml(t("profile.rank_hint"))}</small>
      </div>
      <div class="field">
        <label>${t("profile.app_fee")}</label>
        ${chips(
          "fee-chips",
          [
            { value: "yes", label: t("profile.yes") },
            { value: "no", label: t("profile.no") },
          ],
          feeValue
        )}
        <small class="field-hint">${escapeHtml(t("profile.app_fee_hint"))}</small>
      </div>
    </div>

    <button type="button" class="btn btn-accent btn-block" id="find-programs-btn">
      ${icon("spark")}${t("profile.find")}
    </button>
    <button type="button" class="btn btn-danger-soft btn-block" id="reset-profile-btn">
      ${icon("trash")}${t("profile.reset")}
    </button>
  `;

  bindChips("gpa-scale-chips", updateGpaPreview);
  bindChips("rank-chips");
  bindChips("fee-chips");
  bindChips("cert-type-chips", (value) => {
    document.getElementById("cert-score-field").hidden = !value;
  });

  // Diqqat: "Barchasi" qatorida `data-value` yo'q — tanlangan davlatlarni
  // yig'ishda u chetlab o'tilishi uchun hamma joyda `[data-value]` ishlatiladi.
  const countryRows = () =>
    Array.from(document.querySelectorAll("#country-list .country-row[data-value]"));
  const allRow = document.getElementById("country-all");
  const summary = document.getElementById("country-summary");

  // Ro'yxat yopiq turganda ham nima tanlangani ko'rinib tursin: bayroqlar
  // (ko'pi bilan 4 ta) va davlatlar soni sarlavha qatorida ko'rsatiladi.
  const syncSummary = () => {
    const rows = countryRows();
    const selected = rows.filter((r) => r.classList.contains("active"));
    if (!selected.length) {
      summary.innerHTML = `<span class="collapse-empty">${escapeHtml(t("profile.countries_none"))}</span>`;
      return;
    }
    if (selected.length === rows.length) {
      summary.textContent = t("profile.countries_all");
      return;
    }
    const flags = selected
      .slice(0, 4)
      .map((r) => `<span class="summary-flag">${escapeHtml(r.querySelector(".country-flag").textContent)}</span>`)
      .join("");
    const label =
      selected.length === 1
        ? selected[0].querySelector(".country-name").textContent
        : t("profile.countries_count", { n: selected.length });
    summary.innerHTML = `${flags}<span>${escapeHtml(label)}</span>`;
  };

  const syncAllRow = () => {
    const rows = countryRows();
    allRow.classList.toggle("active", rows.length > 0 && rows.every((r) => r.classList.contains("active")));
    syncSummary();
  };

  countryRows().forEach((row) => {
    row.addEventListener("click", () => {
      haptic("light");
      row.classList.toggle("active");
      syncAllRow();
    });
  });

  allRow.addEventListener("click", () => {
    haptic("light");
    const turnOn = !allRow.classList.contains("active");
    countryRows().forEach((r) => r.classList.toggle("active", turnOn));
    allRow.classList.toggle("active", turnOn);
    syncSummary();
  });

  // Davlatlar ro'yxati uzun — sukut bo'yicha yig'ilgan holda turadi.
  const countryToggle = document.getElementById("country-toggle");
  const countryCollapse = document.getElementById("country-collapse");
  countryToggle.addEventListener("click", () => {
    haptic("light");
    const open = countryToggle.getAttribute("aria-expanded") === "true";
    countryToggle.setAttribute("aria-expanded", String(!open));
    countryCollapse.hidden = open;
  });

  syncAllRow();

  // Daraja o'zgarsa, yo'nalishlar ro'yxati ham o'sha darajadagilarga
  // qisqaradi — aks holda bakalavrga faqat PhD'da bor yo'nalish ko'rinardi.
  bindChips("degree-chips", async (value) => {
    const selected = document.getElementById("major-input").value;
    await loadMajors(value);
    document.getElementById("major-input").innerHTML = majorOptions(selected);
  });

  document.getElementById("gpa-value-input").addEventListener("input", updateGpaPreview);
  document.getElementById("find-programs-btn").addEventListener("click", findPrograms);
  document.getElementById("reset-profile-btn").addEventListener("click", resetProfile);
  document.getElementById("filter-back").addEventListener("click", () => {
    haptic("light");
    switchTab("home");
  });

  updateGpaPreview();
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

async function updateGpaPreview() {
  const scale = activeChip("gpa-scale-chips");
  const value = decimalValue(document.getElementById("gpa-value-input"));
  const box = document.getElementById("gpa-preview");
  if (!scale || !value) {
    box.innerHTML = "";
    return;
  }
  try {
    const r = await api(`/gpa/convert?value=${encodeURIComponent(value)}&scale=${encodeURIComponent(scale)}`);
    box.innerHTML = `
      <div class="gpa-preview">
        <div class="gpa-cell"><div class="gpa-cell-value">${r.us4}</div><div class="gpa-cell-label">${t(
          "profile.gpa_us4"
        )}</div></div>
        <div class="gpa-cell"><div class="gpa-cell-value">${r.ects}</div><div class="gpa-cell-label">${t(
          "profile.gpa_ects"
        )}</div></div>
        <div class="gpa-cell"><div class="gpa-cell-value">${r.bavarian}</div><div class="gpa-cell-label">${t(
          "profile.gpa_bavarian"
        )}</div></div>
      </div>
      <div class="disclaimer">${icon("clock")}<span>${escapeHtml(r.disclaimer)}</span></div>`;
  } catch (e) {
    box.innerHTML = "";
  }
}

async function saveProfile() {
  const selectedCountries = Array.from(
    document.querySelectorAll("#country-list .country-row[data-value].active")
  ).map((row) => Number(row.dataset.value));
  const payload = { ui_language: lang, target_country_ids: selectedCountries };

  const degree = activeChip("degree-chips");
  const fieldValue = document.getElementById("major-input").value;
  const gpaScale = activeChip("gpa-scale-chips");
  const gpaValue = document.getElementById("gpa-value-input").value;
  const certType = activeChip("cert-type-chips");
  const certScoreEl = document.getElementById("cert-score-input");
  const certScore = decimalValue(certScoreEl);
  const fee = activeChip("fee-chips");

  if (degree) payload.degree_level = degree;
  // Har doim yuboriladi: bo'sh tanlov (null) yo'nalishni tozalaydi.
  payload.field_id = fieldValue ? Number(fieldValue) : null;
  if (gpaScale && gpaValue) {
    payload.gpa_scale = gpaScale;
    payload.gpa_raw = parseFloat(gpaValue);
  }
  if (certType && certScore) {
    payload.language_cert_type = certType;
    payload.language_cert_score = parseFloat(certScore);
  }
  // Har doim yuboriladi: "Farqi yo'q" tanlansa bo'sh satr saqlangan
  // tanlovni tozalaydi.
  payload.university_rank_range = activeChip("rank-chips") || "";
  const studyLanguageEl = document.getElementById("study-language-input");
  if (studyLanguageEl) payload.study_language = studyLanguageEl.value || "";
  if (fee) payload.application_fee_ok = fee === "yes";

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
  showFindingOverlay();
  const startedAt = Date.now();
  try {
    await saveProfile();
    await switchTab("match");
    // Oyna eng kamida shuncha turadi. Javob tez kelsa ham u "chaqnab"
    // o'tib ketmasligi kerak — aks holda nima bo'lgani ko'rinmay qoladi.
    const left = FINDING_MS - (Date.now() - startedAt);
    if (left > 0) await new Promise((resolve) => setTimeout(resolve, left));
    haptic("success");
  } catch (err) {
    haptic("error");
    showToast(err.message);
  } finally {
    hideFindingOverlay();
    if (btn) btn.disabled = false;
  }
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
  if (service.price_amount === null || service.price_amount === undefined) {
    return escapeHtml(t("kit.price_ask"));
  }
  const amount = `${Number(service.price_amount).toLocaleString()} ${escapeHtml(
    service.price_currency
  )}`;
  return service.price_note ? `${amount} · ${escapeHtml(service.price_note)}` : amount;
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

// Vaqt tanlanadigan xizmat (1:1 mentor). Bo'sh vaqt qolmagan bo'lsa
// buyurtma qabul qilinmaydi: vaqtsiz pul olib bo'lmaydi.
function needsBooking(service) {
  return !isGuide(service) && service.requires_booking;
}

function isFullyBooked(service) {
  return needsBooking(service) && !service.requested && !service.free_slots;
}

function serviceBtnInner(service) {
  if (isGuide(service)) {
    if (isSoon(service)) return icon("clock") + t("kit.soon");
    return service.requested
      ? icon("download") + t("kit.download")
      : icon("lock") + t("kit.buy");
  }
  if (service.requested) return icon("check") + t("kit.requested");
  if (isFullyBooked(service)) return icon("clock") + t("kit.no_slots");
  if (needsBooking(service)) return icon("clock") + t("kit.pick_time");
  return t("kit.request") + icon("chevron");
}

function serviceBtnClass(service) {
  if (isGuide(service)) {
    if (isSoon(service)) return " is-done";
    return service.requested ? " is-get" : " is-buy";
  }
  if (service.requested || isFullyBooked(service)) return " is-done";
  return "";
}

// Tugma bosilmaydigan holatlar: qo'llanma hali tayyor emas, so'rov
// allaqachon yuborilgan yoki bo'sh vaqt qolmagan.
function serviceBtnDisabled(service) {
  return (
    isSoon(service) || (!isGuide(service) && service.requested) || isFullyBooked(service)
  );
}

// Vaqt tanlanadigan xizmatda qancha joy qolganini kartada ko'rsatamiz —
// "hoziroq tanlash kerak" degan signal.
function serviceSlotRow(service) {
  if (!needsBooking(service) || service.requested) return "";
  return `
    <div class="svc-file">
      ${icon("clock")}
      <span class="svc-file-text">
        <span class="svc-file-name">${
          service.free_slots
            ? t("kit.slots_left", { count: service.free_slots })
            : t("kit.no_slots")
        }</span>
        <span class="svc-file-hint">${
          service.free_slots ? t("kit.pick_time_text") : t("kit.no_slots_text")
        }</span>
      </span>
    </div>`;
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

// Vaqt tanlash oynasi. Vaqtlar ro'yxat bilan birga emas, AYNAN shu
// paytda o'qiladi: ular tez o'zgaradi (boshqa birov band qilishi mumkin)
// va eskirgan ro'yxatdan tanlash xatoga olib borardi.
async function openSlotSheet(serviceId, btn) {
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("kit.pick_time")}</div>
    <div class="sheet-text">${t("kit.pick_time_text")}</div>
    <div id="slot-list">${skeletons(3)}</div>`,
    sheet,
    { tall: true }
  );

  let slots = [];
  try {
    slots = await api(`/services/${serviceId}/slots`);
  } catch (err) {
    document.getElementById("slot-list").innerHTML =
      `<div class="sheet-text">${escapeHtml(err.message)}</div>`;
    return;
  }

  const list = document.getElementById("slot-list");
  if (!list) return;

  if (!slots.length) {
    list.innerHTML = `
      <div class="empty">
        <div class="empty-ico">${icon("clock")}</div>
        <div class="empty-title">${t("kit.no_slots")}</div>
        <div class="empty-text">${t("kit.no_slots_text")}</div>
      </div>`;
    return;
  }

  // Bir kunning vaqtlari birga tursin — ro'yxat sana bo'yicha guruhlanadi.
  const byDate = [];
  slots.forEach((slot) => {
    const last = byDate[byDate.length - 1];
    if (last && last.date === slot.date_label) last.items.push(slot);
    else byDate.push({ date: slot.date_label, items: [slot] });
  });

  list.innerHTML = byDate
    .map(
      (group) => `
      <div class="slot-day">
        <div class="slot-day-title">${escapeHtml(group.date)}</div>
        <div class="slot-row">
          ${group.items
            .map(
              (slot) => `
            <button type="button" class="slot-btn" data-slot="${slot.id}">
              <span class="slot-time">${escapeHtml(slot.time_label)}</span>
              <span class="slot-meta">${t("kit.minutes", {
                count: slot.duration_minutes,
              })}${slot.note ? ` · ${escapeHtml(slot.note)}` : ""}</span>
            </button>`
            )
            .join("")}
        </div>
      </div>`
    )
    .join("");

  list.querySelectorAll(".slot-btn").forEach((slotBtn) => {
    slotBtn.addEventListener("click", async () => {
      haptic("light");
      list.querySelectorAll(".slot-btn").forEach((b) => (b.disabled = true));
      await bookService(serviceId, slotBtn.dataset.slot, btn, list);
    });
  });
}

// Band qilish va to'lov BITTA so'rovda: server ikkalasini bir tranzaksiyada
// bajaradi, shuning uchun vaqt band bo'lib ulgursa pul ham yechilmaydi.
async function bookService(serviceId, slotId, btn, list) {
  try {
    const result = await api(`/services/${serviceId}/request`, {
      method: "POST",
      body: JSON.stringify({ slot_id: Number(slotId) }),
    });
    if (profile && typeof result.balance === "number") profile.balance = result.balance;
    closeSheet();
    unlockServiceCard(btn, false);
    haptic("success");
    openBookedSheet(result.slot_label);
  } catch (err) {
    haptic("error");
    const short = insufficientBalance(err);
    if (short) {
      closeSheet();
      openNeedBalanceSheet(short);
      return;
    }
    if (String(err.message).startsWith("API 409")) {
      // Oxirgi soniyada band bo'ldi — ro'yxatni yangilab, qaytadan
      // tanlashga imkon beramiz.
      showToast(t("kit.slot_taken"));
      await openSlotSheet(serviceId, btn);
      return;
    }
    list.querySelectorAll(".slot-btn").forEach((b) => (b.disabled = false));
    showToast(err.message);
  }
}

function openBookedSheet(slotLabel) {
  ensureSheet();
  const sheet = document.querySelector(".sheet");
  showSheet(
    `
    <div class="sheet-handle"></div>
    <div class="sheet-title">${t("kit.booked_title")}</div>
    <div class="sheet-text">${t("kit.booked_text", {
      slot: escapeHtml(slotLabel || ""),
    })}</div>
    <button type="button" class="btn btn-quiet btn-block" id="booked-close">
      ${t("onboard.skip")}
    </button>`,
    sheet
  );
  document.getElementById("booked-close").addEventListener("click", closeSheet);
}

async function renderKit() {
  const el = document.getElementById("view-kit");
  el.innerHTML = skeletons(3);

  const services = await api("/services");

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
        ${serviceSlotRow(service)}
        <div class="svc-foot">
          <span class="svc-price">${servicePriceText(service)}</span>
          <button type="button" class="svc-btn kit-btn${serviceBtnClass(service)}"
            data-id="${service.id}"
            data-guide="${isGuide(service) ? "1" : "0"}"
            data-booking="${needsBooking(service) ? "1" : "0"}"
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

      // Vaqt tanlanadigan xizmat: avval oyna tanlanadi, pul esa
      // tanlangandan keyin yechiladi.
      if (btn.dataset.booking === "1") {
        await openSlotSheet(btn.dataset.id, btn);
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
          await deliverPdf(btn.dataset.id, btn);
        } else {
          showToast(t("kit.requested_toast"));
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

function profileRow(id, iconName, title, value, extraClass) {
  return `
    <button type="button" class="acc-row ${extraClass || ""}" id="${id}">
      <span class="acc-ico">${icon(iconName)}</span>
      <span class="acc-text">
        <span class="acc-title">${title}</span>
        ${value ? `<span class="acc-value">${value}</span>` : ""}
      </span>
      ${icon("chevron", "acc-chevron")}
    </button>`;
}

function renderProfile() {
  const el = document.getElementById("view-profile");
  const name = (TG_USER && TG_USER.first_name) || "";
  const username = TG_USER && TG_USER.username;
  const balance = `${Number(profile.balance || 0).toLocaleString()} ${escapeHtml(
    profile.balance_currency || ""
  )}`;

  el.innerHTML = `
    <div class="acc-head">
      <div class="acc-avatar">${escapeHtml(initials(name)) || icon("user")}</div>
      <div class="acc-head-text">
        <div class="acc-name">${escapeHtml(name) || t("profile.no_name")}</div>
        <div class="acc-sub">${username ? "@" + escapeHtml(username) : ""}</div>
      </div>
    </div>

    <div class="acc-balance">
      <div class="acc-balance-label">${t("account.balance")}</div>
      <div class="acc-balance-value">${balance}</div>
      <div class="acc-balance-hint">${t("account.topup_hint")}</div>
    </div>

    <div class="acc-group">
      ${profileRow("acc-filter", "search", t("account.filter"), t("account.filter_sub"))}
      ${profileRow("acc-lang", "lang", t("account.language"), LANG_LABELS[lang] || lang)}
      ${profileRow("acc-invite", "spark", t("account.invite"), inviteSubtitle())}
      ${profileRow("acc-help", "shield", t("account.help"), "")}
      ${profileRow("acc-feedback", "plane", t("account.feedback"), "")}
    </div>`;

  document.getElementById("acc-filter").addEventListener("click", () => {
    haptic("light");
    switchTab("filter");
  });
  document.getElementById("acc-lang").addEventListener("click", openLanguageSheet);
  document.getElementById("acc-invite").addEventListener("click", shareBot);
  document.getElementById("acc-help").addEventListener("click", openHelpSheet);
  document.getElementById("acc-feedback").addEventListener("click", openFeedbackSheet);
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

// ============ Navigation ============

const RENDERERS = {
  filter: renderFilter,
  home: renderHome,
  match: renderMatch,
  kit: renderKit,
  scholarships: renderScholarships,
  saved: renderSaved,
  profile: renderProfile,
};

function updateNavLabels() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
    const btn = el.closest(".tab");
    if (btn) btn.setAttribute("aria-label", el.textContent);
  });
}

async function switchTab(tabName) {
  haptic("light");
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
  await loadCountries();
  await loadMajors();
  await loadStudyLanguages();

  updateNavLabels();
  bindTabs();

  // Filtr bo'sh bo'lsa — birinchi qadam sifatida yo'naltirish oynasi.
  // ATAYLAB `renderHome()` dan OLDIN: bosh sahifa /match va /saved
  // so'rovlarini kutadi, oyna esa ularsiz ham chiqaverishi mumkin.
  // Ilgari oyna shu ikki so'rov tugashini kutib, sezilarli kechikardi.
  // Bu yerda profil, davlatlar va yo'nalishlar allaqachon yuklangan,
  // ya'ni "Filtrni sozlash" bosilsa Profil sahifasi darhol chiziladi.
  // Filtr qo'yilgach oyna boshqa chiqmaydi, shuning uchun alohida
  // "ko'rsatilgan" belgisini saqlash shart emas.
  if (!hasFilter() && !onboardingShown) openOnboardingSheet();

  await renderHome();

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
