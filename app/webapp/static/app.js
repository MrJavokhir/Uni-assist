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
}
const INIT_DATA = (tg && tg.initData) || "";

// iOS raqamli klaviaturasida "Done" tugmasi yo'q — foydalanuvchi uni yopa
// olmay, natija klaviatura ostida qolib ketardi. Shuning uchun maydondan
// tashqariga bosilganda yoki sahifa surilganda klaviatura yopiladi, Enter
// ham uni yopadi (Android klaviaturasida "Done" ko'rsatiladi).
const TEXT_FIELD = "input, textarea, select, [contenteditable='true']";

function dismissKeyboard() {
  const active = document.activeElement;
  if (active && active.matches && active.matches("input, textarea")) active.blur();
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
const ASSET_V = 33;
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

    "home.greeting": "Salom, {name}!",
    "home.tagline": "Chet elda o'qish safaringiz shu yerdan boshlanadi.",
    "home.stat_green": "Mos dasturlar",
    "home.stat_yellow": "Yaqin dasturlar",
    "home.stat_saved": "Saqlangan",
    "home.alert_title": "Yaqinlashayotgan muddat",
    "home.alert_body": "{program} · {days} kun qoldi",
    "home.section_shortcuts": "Tezkor amallar",
    "home.greeting_plain": "Salom!",
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

    "match.empty_title": "Mos dastur topilmadi",
    "match.empty_text": "Profilingizni to'ldiring — shunda sizga mos dasturlarni topa olaman.",
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
    "program.gre": "GRE",
    "program.prereq": "Oldingi ta'lim",
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
    "scholarships.degree_levels": "Qaysi darajaga",
    "scholarships.duration": "Muddati",
    "scholarships.lang_score": "Til bali",
    "scholarships.work_exp": "Ish tajribasi",
    "scholarships.stages": "Tanlov bosqichlari",
    "scholarships.stages_count": "{n} bosqich",
    "scholarships.years_count": "{years} yil",
    "scholarships.per_month": "oyiga",
    "scholarships.per_year": "yiliga",
    "scholarships.verify_hint": "Talablar har yili o'zgarishi mumkin — ariza berishdan oldin rasmiy saytdan tasdiqlang.",
    "scholarships.conditions": "Shartlar",
    "scholarships.deadlines": "Muddatlar",
    "scholarships.covers": "Qamrov",
    "scholarships.stipend": "Stipendiya",
    "scholarships.age_limit": "Yosh chegarasi",
    "scholarships.uni_choice": "Universitetni kim tanlaydi",
    "scholarships.uni_choice.user_chooses": "Talabaning o'zi",
    "scholarships.uni_choice.assigned_by_scholarship": "Grant tayinlaydi",
    "scholarships.separate_application": "Alohida ariza kerak",
    "scholarships.for_uzbekistan": "O'zbekiston fuqarolari uchun",
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

    "home.greeting": "Привет, {name}!",
    "home.tagline": "Ваш путь к учёбе за рубежом начинается здесь.",
    "home.stat_green": "Подходящие",
    "home.stat_yellow": "Почти подходят",
    "home.stat_saved": "Сохранённые",
    "home.alert_title": "Приближается дедлайн",
    "home.alert_body": "{program} · осталось {days} дн.",
    "home.section_shortcuts": "Быстрые действия",
    "home.greeting_plain": "Привет!",
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

    "match.empty_title": "Программы не найдены",
    "match.empty_text": "Заполните профиль — и я подберу подходящие программы.",
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
    "program.gre": "GRE",
    "program.prereq": "Предыдущее образование",
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
    "scholarships.degree_levels": "Для каких степеней",
    "scholarships.duration": "Длительность",
    "scholarships.lang_score": "Языковой балл",
    "scholarships.work_exp": "Опыт работы",
    "scholarships.stages": "Этапы отбора",
    "scholarships.stages_count": "{n} этапа",
    "scholarships.years_count": "{years} г.",
    "scholarships.per_month": "в месяц",
    "scholarships.per_year": "в год",
    "scholarships.verify_hint": "Требования могут меняться каждый год — перед подачей уточните на официальном сайте.",
    "scholarships.conditions": "Условия",
    "scholarships.deadlines": "Дедлайны",
    "scholarships.covers": "Покрытие",
    "scholarships.stipend": "Стипендия",
    "scholarships.age_limit": "Возрастное ограничение",
    "scholarships.uni_choice": "Кто выбирает университет",
    "scholarships.uni_choice.user_chooses": "Сам студент",
    "scholarships.uni_choice.assigned_by_scholarship": "Назначает грант",
    "scholarships.separate_application": "Нужна отдельная заявка",
    "scholarships.for_uzbekistan": "Для граждан Узбекистана",
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

    "home.greeting": "Hi, {name}!",
    "home.tagline": "Your journey to studying abroad starts here.",
    "home.stat_green": "Matching",
    "home.stat_yellow": "Close matches",
    "home.stat_saved": "Saved",
    "home.alert_title": "Deadline approaching",
    "home.alert_body": "{program} · {days} day(s) left",
    "home.section_shortcuts": "Quick actions",
    "home.greeting_plain": "Hi there!",
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

    "match.empty_title": "No programs found",
    "match.empty_text": "Fill in your profile and I'll find programs that fit you.",
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
    "program.gre": "GRE",
    "program.prereq": "Prior degree",
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
    "scholarships.degree_levels": "Degree levels",
    "scholarships.duration": "Duration",
    "scholarships.lang_score": "Language score",
    "scholarships.work_exp": "Work experience",
    "scholarships.stages": "Selection stages",
    "scholarships.stages_count": "{n} stages",
    "scholarships.years_count": "{years} yr",
    "scholarships.per_month": "per month",
    "scholarships.per_year": "per year",
    "scholarships.verify_hint": "Requirements can change each year — confirm on the official site before applying.",
    "scholarships.conditions": "Conditions",
    "scholarships.deadlines": "Deadlines",
    "scholarships.covers": "Coverage",
    "scholarships.stipend": "Stipend",
    "scholarships.age_limit": "Age limit",
    "scholarships.uni_choice": "Who picks the university",
    "scholarships.uni_choice.user_chooses": "The student",
    "scholarships.uni_choice.assigned_by_scholarship": "The scholarship",
    "scholarships.separate_application": "Separate application required",
    "scholarships.for_uzbekistan": "Open to Uzbekistan citizens",
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

async function loadProfile() {
  profile = await api("/me");
  lang = profile.ui_language || lang;
}

async function loadCountries() {
  countries = await api("/countries");
}

async function loadMajors(degreeLevel) {
  const level = degreeLevel === undefined ? profile && profile.degree_level : degreeLevel;
  majors = await api("/majors" + (level ? `?degree_level=${encodeURIComponent(level)}` : ""));
}

// Qidiruvni chegaralaydigan maydonlardan birortasi tanlanganmi.
// Hech biri tanlanmagan bo'lsa `find_matches` hamma dasturni qaytaradi —
// ularni "sizga mos" deb ko'rsatish yangi foydalanuvchini chalg'itadi.
function hasFilter() {
  return Boolean(
    profile &&
      (profile.degree_level || profile.field_id || (profile.target_country_ids || []).length)
  );
}

function profileCompleteness() {
  const checks = [
    !!profile.degree_level,
    !!profile.field_id,
    profile.gpa_raw !== null && profile.gpa_scale !== null,
    profile.language_certificates.length > 0,
    profile.target_country_ids.length > 0,
    // "Farqi yo'q" ham javob: ariza to'lovi bo'yicha tanlov qilingani yetarli.
    // Reyting oralig'i ixtiyoriy afzallik — foizga qo'shilmaydi.
    profile.application_fee_ok !== null,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

// Bosh sahifadagi katta halqa: ichida raqam, atrofida to'liq mos dasturlar ulushi.
function bigRing(pct) {
  const r = 39;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - Math.max(0, Math.min(100, pct)) / 100);
  return `
    <svg class="ring-svg" width="98" height="98" viewBox="0 0 98 98">
      <circle class="ring-bg" cx="49" cy="49" r="${r}" fill="none" stroke-width="10"/>
      <circle class="ring-fg" cx="49" cy="49" r="${r}" fill="none" stroke-width="10"
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
  const name = (TG_USER && TG_USER.first_name) || "";
  const pct = profileCompleteness();
  const ready = hasFilter();
  const photo = TG_USER && TG_USER.photo_url;

  el.innerHTML = `
    <div class="hi-row">
      ${
        photo
          ? `<img class="hi-ava" src="${escapeHtml(photo)}" alt="">`
          : `<div class="hi-ava hi-ava-text">${escapeHtml(initials(name)) || icon("user")}</div>`
      }
      <div class="hi-text">
        <div class="hi-hello">${
          name ? t("home.greeting", { name: escapeHtml(name) }) : t("home.greeting_plain")
        }</div>
        <div class="hi-sub">${t("home.tagline")}</div>
      </div>
      <button type="button" class="hi-btn" data-goto="match" aria-label="${escapeHtml(t("nav.match"))}">
        ${icon("search")}
      </button>
      <button type="button" class="hi-btn" id="hi-saved" data-goto="saved"
              aria-label="${escapeHtml(t("nav.saved"))}">
        ${icon("bookmark")}
      </button>
    </div>

    <div class="hero home-hero">
      <div class="hero-main">
        <div class="hero-chip">${icon("spark")}<span>${t("home.profile_progress")}</span></div>
        <div class="hero-big">${pct}<span>%</span></div>
        <button type="button" class="hero-pill" id="home-cta">
          <span>${t(ready ? "home.refine_filter" : "home.setup_filter")}</span>${icon("chevron")}
        </button>
      </div>
      <div class="ring-lg" id="hero-ring">
        ${bigRing(0)}
        <div class="ring-core"><b>—</b><span>${t("home.unit_program")}</span></div>
      </div>
    </div>

    <div id="home-alert"></div>

    <div class="hx-grid">
      <div class="hx-recap" data-goto="match" role="button" tabindex="0">
        <div class="hx-recap-title">${t("home.recap_title")}</div>
        <div class="hx-recap-text">${t("home.recap_text")}</div>
        <div class="hx-recap-art">
          <img src="icon-programs.png?v=${ASSET_V}" alt="" aria-hidden="true">
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

  document.getElementById("home-cta").addEventListener("click", () => switchTab("profile"));

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

  // Filtr qo'yilmagan bo'lsa qidiruv katalogdagi HAMMA dasturni qaytaradi —
  // ularni "sizga mos" deb ko'rsatish noto'g'ri bo'lardi, shuning uchun chiziqcha.
  document.getElementById("hero-ring").innerHTML =
    bigRing(ready ? greenShare : 0) +
    `<div class="ring-core"><b>${ready ? compactNumber(total) : "—"}</b><span>${t(
      "home.unit_program"
    )}</span></div>`;

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

  if (upcoming.length) document.getElementById("hi-saved").classList.add("has-dot");

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

async function renderMatch() {
  const el = document.getElementById("view-match");
  el.innerHTML = skeletons(4);

  const matches = await api("/match");
  if (!matches.length) {
    el.innerHTML = `
      <div class="empty">
        <div class="empty-ico">${icon("search")}</div>
        <div class="empty-title">${t("match.empty_title")}</div>
        <div class="empty-text">${t("match.empty_text")}</div>
      </div>`;
    return;
  }

  el.innerHTML = matches
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
  backdrop.addEventListener("click", closeSheet);
  // Tepadagi "tutqich" yopish belgisiga o'xshaydi — uni bosganda ham yopilsin.
  sheet.addEventListener("click", (event) => {
    if (event.target.classList.contains("sheet-handle")) closeSheet();
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

  // Ariza hujjatlari (kalitlar, foydalanuvchi tilida) va admin yozgan
  // qo'shimcha talablar — bitta ro'yxat: ikkalasi ham "arizaga nima kerak".
  const checklist = [
    ...(p.required_documents || []).map((d) => t("document." + d)),
    ...(p.requirements || []),
  ];
  const extraRequirements = checklist.length
    ? `<ul class="doc-list">${checklist
        .map((r) => `<li>${icon("check")}${escapeHtml(r)}</li>`)
        .join("")}</ul>`
    : "";
  const requirementRows =
    (req.gre_required
      ? row(
          t("program.gre"),
          req.gre_min !== null && req.gre_min !== undefined
            ? `${t("scholarships.yes")} (${req.gre_min})`
            : t("scholarships.yes")
        )
      : "") +
    (req.prereq_major ? row(t("program.prereq"), escapeHtml(req.prereq_major)) : "");
  const requirements =
    requirementRows || extraRequirements
      ? requirementRows + extraRequirements
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

  const yesNo = (value) => (value ? t("scholarships.yes") : t("scholarships.no"));
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
  const workExp =
    s.work_experience_years === null || s.work_experience_years === undefined
      ? dash
      : s.work_experience_years === 0
        ? t("scholarships.no")
        : t("scholarships.years_count", { years: s.work_experience_years });

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
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.requirements")}</div>
      ${row(t("scholarships.lang_score"), langScore || dash)}
      ${row(t("scholarships.work_exp"), workExp)}
      ${row(
        t("scholarships.age_limit"),
        s.age_limit !== null && s.age_limit !== undefined ? s.age_limit : dash
      )}
      ${row(
        t("scholarships.stages"),
        s.selection_stages ? t("scholarships.stages_count", { n: s.selection_stages }) : dash
      )}
      ${row(t("scholarships.separate_application"), yesNo(s.application_linked_to_program))}
      ${row(t("scholarships.for_uzbekistan"), yesNo(s.citizenship_eligible))}
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

function renderProfile() {
  const el = document.getElementById("view-profile");
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
        <input type="number" inputmode="decimal" step="0.01" id="gpa-value-input" placeholder="—" value="${
          profile.gpa_raw ?? ""
        }" />
        <div id="gpa-preview"></div>
      </div>
    </div>

    ${profileSection("lang", t("profile.section_language"))}
    <div class="group">
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
        <input type="number" inputmode="decimal" step="0.1" id="cert-score-input" placeholder="—" value="${certScore}" />
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

async function updateGpaPreview() {
  const scale = activeChip("gpa-scale-chips");
  const value = document.getElementById("gpa-value-input").value;
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
  const certScore = certScoreEl ? certScoreEl.value : "";
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
  renderProfile();
  haptic("success");
  showToast(t("profile.reset_toast"));
}

// ============ Navigation ============

const RENDERERS = {
  home: renderHome,
  match: renderMatch,
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
  if (render) await render();
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function bindLangSwitch() {
  const select = document.getElementById("lang-switch");
  select.value = lang;
  select.addEventListener("change", async () => {
    lang = select.value;
    await api("/me", { method: "PATCH", body: JSON.stringify({ ui_language: lang }) });
    updateNavLabels();
    const active = document.querySelector(".tab.active");
    await switchTab(active ? active.dataset.tab : "home");
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

  updateNavLabels();
  bindTabs();
  bindLangSwitch();
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
