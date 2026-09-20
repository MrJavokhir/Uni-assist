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

// Bazada o'qitish tili matn sifatida saqlanadi. Yangi yozuvlar kanonik
// inglizcha nom bilan keladi ("English"), eskilarida esa o'zbekcha nom
// qolgan — ikkalasi ham shu yerda foydalanuvchi tiliga o'giriladi.
// Ro'yxatda yo'q qiymat bo'lsa, o'zi qanday bo'lsa shunday ko'rsatiladi.
const LANGUAGE_NAMES = {
  English: { uz: "Ingliz tili", ru: "Английский", en: "English" },
  Russian: { uz: "Rus tili", ru: "Русский", en: "Russian" },
  German: { uz: "Nemis tili", ru: "Немецкий", en: "German" },
  Italian: { uz: "Italyan tili", ru: "Итальянский", en: "Italian" },
  Czech: { uz: "Chex tili", ru: "Чешский", en: "Czech" },
  Polish: { uz: "Polyak tili", ru: "Польский", en: "Polish" },
  Turkish: { uz: "Turk tili", ru: "Турецкий", en: "Turkish" },
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
    "home.complete_profile": "Profilni to'ldirish",
    "home.section_overview": "Qisqacha",
    "home.stat_green": "Mos dasturlar",
    "home.stat_yellow": "Yaqin dasturlar",
    "home.stat_saved": "Saqlangan",
    "home.stat_profile": "Profil to'liqligi",
    "home.alert_title": "Yaqinlashayotgan muddat",
    "home.alert_body": "{program} · {days} kun qoldi",
    "home.section_shortcuts": "Tezkor amallar",
    "home.shortcut_match": "Mos dasturlarni ko'rish",
    "home.shortcut_saved": "Saqlangan dasturlarim",
    "home.profile_progress": "Profil to'ldirilgan",
    "home.profile_done": "Profil to'liq to'ldirilgan",
    "home.summary_total": "Sizga mos dasturlar",
    "home.summary_empty": "Profilni to'ldiring — sizga mos dasturlarni topaman",
    "home.section_top": "Eng mos dastur",
    "home.setup_filter": "Qidiruvni sozlash",
    "home.refine_filter": "Filtrni to'ldirish",
    "home.summary_no_filter": "Qidiruvni sozlang",
    "home.summary_no_filter_hint": "Yo'nalish, daraja va davlatni tanlang — shundan keyin sizga mos dasturlarni ko'rsataman",

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
    "profile.reset": "Hammasini tozalash",
    "profile.reset_confirm": "Profildagi barcha tanlovlar o'chiriladi. Saqlangan dasturlarga tegilmaydi. Davom etamizmi?",
    "profile.reset_toast": "Profil tozalandi",
    "profile.budget": "Yillik byudjet (USD)",
    "profile.age": "Yosh",
    "profile.save": "Saqlash",
    "profile.saved_toast": "Profil saqlandi",

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
    "program.gpa_min": "Min. GPA",
    "program.ielts_min": "Min. IELTS",
    "program.toefl_min": "Min. TOEFL",
    "program.gre": "GRE",
    "program.age_limit": "Yosh chegarasi",
    "program.prereq": "Oldingi ta'lim",
    "program.no_requirements": "Talablar kiritilmagan.",
    "program.costs": "Xarajatlar",
    "program.tuition": "Kontrakt (yiliga)",
    "program.visa_proof": "Viza uchun isbot",
    "program.living": "Yashash (oyiga)",
    "program.no_costs": "Xarajatlar kiritilmagan.",
    "program.cost_disclaimer": "Taxminiy raqamlar, oxirgi tekshiruv: {date}. Aniq summani universitet saytidan tasdiqlang.",
    "program.no_deadlines": "Muddatlar kiritilmagan.",
    "program.official_page": "Dastur sahifasiga o'tish",
    "program.verified_at": "Ma'lumot {date} sanasida tekshirilgan.",
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
    "home.complete_profile": "Заполнить профиль",
    "home.section_overview": "Обзор",
    "home.stat_green": "Подходящие",
    "home.stat_yellow": "Почти подходят",
    "home.stat_saved": "Сохранённые",
    "home.stat_profile": "Профиль заполнен",
    "home.alert_title": "Приближается дедлайн",
    "home.alert_body": "{program} · осталось {days} дн.",
    "home.section_shortcuts": "Быстрые действия",
    "home.shortcut_match": "Смотреть подходящие программы",
    "home.shortcut_saved": "Мои сохранённые",
    "home.profile_progress": "Профиль заполнен",
    "home.profile_done": "Профиль заполнен полностью",
    "home.summary_total": "Подходящих программ",
    "home.summary_empty": "Заполните профиль — и я подберу программы",
    "home.section_top": "Лучшее совпадение",
    "home.setup_filter": "Настроить поиск",
    "home.refine_filter": "Дополнить фильтр",
    "home.summary_no_filter": "Настройте поиск",
    "home.summary_no_filter_hint": "Выберите направление, степень и страну — и я покажу подходящие программы",

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
    "profile.countries_all": "Все страны",
    "profile.reset": "Очистить всё",
    "profile.reset_confirm": "Все данные профиля будут удалены. Сохранённые программы не тронем. Продолжить?",
    "profile.reset_toast": "Профиль очищен",
    "profile.budget": "Годовой бюджет (USD)",
    "profile.age": "Возраст",
    "profile.save": "Сохранить",
    "profile.saved_toast": "Профиль сохранён",

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
    "program.gpa_min": "Мин. GPA",
    "program.ielts_min": "Мин. IELTS",
    "program.toefl_min": "Мин. TOEFL",
    "program.gre": "GRE",
    "program.age_limit": "Возрастной предел",
    "program.prereq": "Предыдущее образование",
    "program.no_requirements": "Требования не указаны.",
    "program.costs": "Расходы",
    "program.tuition": "Контракт (в год)",
    "program.visa_proof": "Подтверждение для визы",
    "program.living": "Проживание (в месяц)",
    "program.no_costs": "Расходы не указаны.",
    "program.cost_disclaimer": "Приблизительные суммы, последняя проверка: {date}. Уточните на сайте университета.",
    "program.no_deadlines": "Сроки не указаны.",
    "program.official_page": "Открыть страницу программы",
    "program.verified_at": "Данные проверены {date}.",
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
    "home.complete_profile": "Complete your profile",
    "home.section_overview": "Overview",
    "home.stat_green": "Matching",
    "home.stat_yellow": "Close matches",
    "home.stat_saved": "Saved",
    "home.stat_profile": "Profile complete",
    "home.alert_title": "Deadline approaching",
    "home.alert_body": "{program} · {days} day(s) left",
    "home.section_shortcuts": "Quick actions",
    "home.shortcut_match": "See matching programs",
    "home.shortcut_saved": "My saved programs",
    "home.profile_progress": "Profile complete",
    "home.profile_done": "Your profile is complete",
    "home.summary_total": "Programs that fit you",
    "home.summary_empty": "Fill in your profile and I'll find programs for you",
    "home.section_top": "Best match",
    "home.setup_filter": "Set up your search",
    "home.refine_filter": "Refine your filter",
    "home.summary_no_filter": "Set up your search",
    "home.summary_no_filter_hint": "Pick a field, degree and country — then I'll show the programs that fit you",

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
    "profile.countries_all": "All countries",
    "profile.reset": "Reset everything",
    "profile.reset_confirm": "All profile choices will be cleared. Saved programs stay untouched. Continue?",
    "profile.reset_toast": "Profile cleared",
    "profile.budget": "Annual budget (USD)",
    "profile.age": "Age",
    "profile.save": "Save",
    "profile.saved_toast": "Profile saved",

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
    "program.gpa_min": "Min. GPA",
    "program.ielts_min": "Min. IELTS",
    "program.toefl_min": "Min. TOEFL",
    "program.gre": "GRE",
    "program.age_limit": "Age limit",
    "program.prereq": "Prior degree",
    "program.no_requirements": "No requirements recorded.",
    "program.costs": "Costs",
    "program.tuition": "Tuition (per year)",
    "program.visa_proof": "Visa proof of funds",
    "program.living": "Living (per month)",
    "program.no_costs": "No costs recorded.",
    "program.cost_disclaimer": "Approximate figures, last checked {date}. Confirm on the university site.",
    "program.no_deadlines": "No deadlines recorded.",
    "program.official_page": "Open program page",
    "program.verified_at": "Data verified on {date}.",
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
      (profile.degree_level || profile.major || (profile.target_country_ids || []).length)
  );
}

function profileCompleteness() {
  const checks = [
    !!profile.degree_level,
    !!profile.major,
    profile.gpa_raw !== null && profile.gpa_scale !== null,
    profile.language_certificates.length > 0,
    profile.target_country_ids.length > 0,
    profile.budget_max !== null,
    profile.age !== null,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

function progressRing(pct) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct / 100);
  return `
    <div class="ring">
      <svg width="64" height="64" viewBox="0 0 64 64">
        <circle class="ring-bg" cx="32" cy="32" r="${r}" fill="none" stroke-width="6"/>
        <circle class="ring-fg" cx="32" cy="32" r="${r}" fill="none" stroke-width="6"
                stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${offset.toFixed(1)}"/>
      </svg>
      <div class="ring-value">${pct}%</div>
    </div>`;
}

// ============ Home ============

async function renderHome() {
  const el = document.getElementById("view-home");
  const name = (TG_USER && TG_USER.first_name) || "";
  const pct = profileCompleteness();

  el.innerHTML = `
    <div class="hero">
      <img class="hero-logo" src="logo-mark.png?v=18" alt="" aria-hidden="true">
      <div class="hero-greeting">${t("home.greeting", { name: escapeHtml(name) })}</div>
      <div class="hero-sub">${t("home.tagline")}</div>
      ${
        !hasFilter()
          ? // Hali hech narsa tanlanmagan — foizni ko'rsatishdan ma'no yo'q,
            // darhol filtrga taklif qilamiz.
            `<div class="hero-progress">
               <button type="button" class="hero-cta" id="home-cta">
                 ${icon("search")}<span>${t("home.setup_filter")}</span>
               </button>
             </div>`
          : pct < 100
            ? `<div class="hero-progress">
                 <div class="hero-progress-head">
                   <span>${t("home.profile_progress")}</span>
                   <strong>${pct}%</strong>
                 </div>
                 <div class="bar"><span style="width:${pct}%"></span></div>
                 <button type="button" class="hero-cta" id="home-cta">
                   ${icon("spark")}<span>${t("home.refine_filter")}</span>
                 </button>
               </div>`
            : `<div class="hero-progress">
                 <div class="hero-done">${icon("check")}<span>${t("home.profile_done")}</span></div>
               </div>`
      }
    </div>

    <div id="home-alert"></div>

    <div class="section-head"><span class="section-title">${t("home.section_overview")}</span></div>
    <div id="home-summary">${skeletons(2)}</div>

    <div id="home-top"></div>

    <div class="section-head"><span class="section-title">${t("home.section_shortcuts")}</span></div>
    <div class="quick-grid">
      <button type="button" class="quick" data-goto="match">
        <span class="quick-ico accent">${icon("search")}</span>
        <span class="quick-label">${t("nav.match")}</span>
      </button>
      <button type="button" class="quick" data-goto="scholarships">
        <span class="quick-ico amber">${icon("award")}</span>
        <span class="quick-label">${t("nav.scholarships")}</span>
      </button>
      <button type="button" class="quick" data-goto="saved">
        <span class="quick-ico green">${icon("bookmark")}</span>
        <span class="quick-label">${t("nav.saved")}</span>
      </button>
    </div>
  `;

  const cta = document.getElementById("home-cta");
  if (cta) cta.addEventListener("click", () => switchTab("profile"));
  el.querySelectorAll(".quick").forEach((card) => {
    card.addEventListener("click", () => {
      haptic("light");
      switchTab(card.dataset.goto);
    });
  });

  const [matches, saved] = await Promise.all([api("/match"), api("/saved")]);
  const green = matches.filter((m) => m.level === "green").length;
  const yellow = matches.filter((m) => m.level === "yellow").length;
  const total = green + yellow;

  // Bitta ma'noli karta: to'rtta bir xil plitka o'rniga yashil/sariq
  // nisbatini ko'rsatadigan chiziq — bir qarashda holatni bildiradi.
  // Filtr qo'yilmagan bo'lsa qidiruv katalogdagi HAMMA dasturni qaytaradi.
  // Ularni "sizga mos" deb ko'rsatish noto'g'ri bo'lardi — buning o'rniga
  // filtrni sozlashga taklif qilamiz.
  document.getElementById("home-summary").innerHTML = !hasFilter()
    ? `<div class="summary empty-summary" data-goto="profile">
         <div class="summary-ico">${icon("search")}</div>
         <div class="summary-label">${t("home.summary_no_filter")}</div>
         <div class="summary-hint">${t("home.summary_no_filter_hint")}</div>
       </div>`
    : total
    ? `<div class="summary" data-goto="match">
         <div class="summary-top">
           <div>
             <div class="summary-value">${total}</div>
             <div class="summary-label">${t("home.summary_total")}</div>
           </div>
           <span class="summary-go">${icon("chevron")}</span>
         </div>
         <div class="split">
           <span class="split-green" style="width:${total ? (green / total) * 100 : 0}%"></span>
           <span class="split-amber" style="width:${total ? (yellow / total) * 100 : 0}%"></span>
         </div>
         <div class="summary-legend">
           <span><i class="dot green"></i>${green} ${t("home.stat_green")}</span>
           <span><i class="dot amber"></i>${yellow} ${t("home.stat_yellow")}</span>
           <span class="summary-saved"><i class="dot accent"></i>${saved.length} ${t("home.stat_saved")}</span>
         </div>
       </div>`
    : `<div class="summary empty-summary" data-goto="profile">
         <div class="summary-label">${t("home.summary_empty")}</div>
       </div>`;

  el.querySelectorAll("#home-summary .summary").forEach((s) => {
    s.addEventListener("click", () => {
      haptic("light");
      switchTab(s.dataset.goto);
    });
  });

  // Eng mos bitta dastur — bosh sahifada haqiqiy natija ko'rinsin,
  // faqat raqamlar emas. Filtr yo'q bo'lsa "eng mos" degan gap ma'nosiz:
  // ro'yxat katalogdagi tasodifiy birinchi yozuv bo'lib qoladi.
  const best = hasFilter() ? matches.find((m) => m.level === "green") || matches[0] : null;
  if (best) {
    document.getElementById("home-top").innerHTML = `
      <div class="section-head"><span class="section-title">${t("home.section_top")}</span></div>
      <div class="card">
        <div class="card-top program-open" data-id="${best.id}" role="button" tabindex="0">
          ${avatar(best.university, best.university_logo)}
          <div class="card-body">
            <div class="card-title">${escapeHtml(best.name)}${
              best.abbreviation ? `<span class="abbr">${escapeHtml(best.abbreviation)}</span>` : ""
            }</div>
            <div class="card-sub">${escapeHtml(best.university)}</div>
            <div class="meta-row">
              <span class="pill ${best.level === "green" ? "green" : "amber"}">${
                best.level === "green" ? icon("check") + t("match.green") : icon("spark") + t("match.yellow")
              }</span>
              <span class="pill"><span class="chip-flag">${flag(
                best.country.iso_code
              )}</span>${escapeHtml(countryName(best.country))}</span>
            </div>
          </div>
          <span class="card-chevron">${icon("chevron")}</span>
        </div>
      </div>`;
    bindProgramOpeners(document.getElementById("home-top"));
  }

  const upcoming = saved
    .filter((s) => s.nearest_deadline_days_left !== null && s.nearest_deadline_days_left >= 0)
    .sort((a, b) => a.nearest_deadline_days_left - b.nearest_deadline_days_left);

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
      const missing = m.missing.length
        ? `<span class="pill amber">${t("match.missing", { list: m.missing.join(", ") })}</span>`
        : "";
      return `
        <div class="card">
          <div class="card-top program-open" data-id="${m.id}" role="button" tabindex="0">
            ${avatar(m.university, m.university_logo)}
            <div class="card-body">
              <div class="card-title">${escapeHtml(m.name)}${
                m.abbreviation ? `<span class="abbr">${escapeHtml(m.abbreviation)}</span>` : ""
              }</div>
              <div class="card-sub">${escapeHtml(m.university)}</div>
              <div class="meta-row">
                <span class="pill ${isGreen ? "green" : "amber"}">${isGreen ? icon("check") : icon("spark")}${
                  isGreen ? t("match.green") : t("match.yellow")
                }</span>
                <span class="pill"><span class="chip-flag">${flag(
                  m.country.iso_code
                )}</span>${escapeHtml(countryName(m.country))}</span>
                ${missing}
              </div>
            </div>
            <span class="card-chevron">${icon("chevron")}</span>
          </div>
          <div class="card-actions">
            <button type="button" class="btn btn-soft program-open" data-id="${m.id}">
              ${icon("search")}${t("match.details")}
            </button>
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

  return `
    <div class="card">
      <div class="card-top">
        <div class="avatar">${escapeHtml(initials(s.name))}</div>
        <div class="card-body">
          <div class="card-title">${escapeHtml(s.name)}</div>
          <div class="meta-row">
            <span class="pill ${coverageTone}">${icon("award")}${t(
              "scholarships.coverage." + s.coverage_type
            )}</span>
            ${countryPills}
            ${deadline}
          </div>
          ${extras ? `<div class="meta-row">${extras}</div>` : ""}
        </div>
      </div>
      <div class="card-actions">
        <button type="button" class="btn btn-soft details-btn" data-id="${s.id}">
          ${icon("chevron")}${t("scholarships.details")}
        </button>
      </div>
    </div>`;
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
  document.querySelector(".sheet")?.classList.remove("open");
  document.body.style.overflow = "";
  try {
    tg?.BackButton?.hide();
  } catch (e) {
    /* eski klientlar */
  }
}

function showSheet(html, sheet) {
  sheet.innerHTML = html;
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

  const req = p.requirement;
  const requirements = req
    ? row(t("program.gpa_min"), req.gpa_min !== null ? `${req.gpa_min}${
        req.gpa_scale ? ` / ${req.gpa_scale}` : ""
      }` : dash) +
      row(t("program.ielts_min"), req.ielts_min !== null ? req.ielts_min : dash) +
      row(t("program.toefl_min"), req.toefl_min !== null ? req.toefl_min : dash) +
      row(
        t("program.gre"),
        req.gre_required
          ? (req.gre_min !== null ? `${t("scholarships.yes")} (${req.gre_min})` : t("scholarships.yes"))
          : t("scholarships.no")
      ) +
      row(t("program.age_limit"), req.age_limit !== null ? req.age_limit : dash) +
      (req.prereq_major ? row(t("program.prereq"), escapeHtml(req.prereq_major)) : "")
    : `<div class="sheet-empty">${t("program.no_requirements")}</div>`;

  const cost = p.cost;
  const costs = cost
    ? row(t("program.tuition"), money(cost.tuition_amount, cost.currency)) +
      row(t("program.visa_proof"), money(cost.visa_proof_amount, cost.currency)) +
      row(t("program.living"), money(cost.living_cost_monthly, cost.currency)) +
      `<div class="sheet-note">${t("program.cost_disclaimer", {
        date: escapeHtml(cost.last_checked),
      })}</div>`
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
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("program.about")}</div>
      ${row(t("program.field"), escapeHtml(p.field_of_study))}
      ${row(t("program.language"), escapeHtml(instructionLanguage(p.language_of_instruction)))}
      ${row(t("program.intake"), escapeHtml(p.intake_term))}
      ${p.notes ? `<div class="sheet-note">${escapeHtml(p.notes)}</div>` : ""}
      ${missingNote(p.missing_fields)}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("program.requirements")}</div>
      ${requirements}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("program.costs")}</div>
      ${costs}
    </div>

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.deadlines")}</div>
      ${deadlines}
    </div>

    <div class="sheet-actions">
      <button type="button" class="btn ${
        p.saved ? "btn-done" : "btn-accent"
      } btn-block" id="sheet-save" ${p.saved ? "disabled" : ""}>
        ${p.saved ? icon("check") + t("match.saved") : icon("plus") + t("match.save")}
      </button>
      <button type="button" class="btn btn-soft btn-block" id="sheet-open-site">
        ${t("program.official_page")}
      </button>
      <div class="sheet-note">${t("program.verified_at", { date: escapeHtml(p.verified_at) })}</div>
    </div>
  `,
    sheet
  );

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

  const stipend =
    s.stipend_amount !== null
      ? `${s.stipend_amount} ${escapeHtml(s.currency)}`
      : t("scholarships.not_specified");

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
    <div class="sheet-title">${escapeHtml(s.name)}</div>
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
    ${extras ? `<div class="meta-row">${extras}</div>` : ""}

    ${
      s.description
        ? `<div class="sheet-section">
             <div class="sheet-section-title">${t("scholarships.about")}</div>
             <div class="sheet-text">${escapeHtml(s.description)}</div>
           </div>`
        : ""
    }

    <div class="sheet-section">
      <div class="sheet-section-title">${t("scholarships.conditions")}</div>
      ${row(t("scholarships.stipend"), stipend)}
      ${row(
        t("scholarships.age_limit"),
        s.age_limit !== null ? s.age_limit : t("scholarships.not_specified")
      )}
      ${row(t("scholarships.uni_choice"), t("scholarships.uni_choice." + s.university_choice))}
      ${row(t("scholarships.separate_application"), yesNo(s.application_linked_to_program))}
      ${row(t("scholarships.for_uzbekistan"), yesNo(s.citizenship_eligible))}
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

function renderProfile() {
  const el = document.getElementById("view-profile");
  const cert = profile.language_certificates[0] || {};
  const certType = cert.type || "";
  const certScore = cert.score ?? "";

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
    <div class="section-head"><span class="section-title">${t("profile.section_academic")}</span></div>
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
          <option value="">${escapeHtml(t("profile.major_placeholder"))}</option>
          ${majors
            .map(
              (m) =>
                `<option value="${escapeHtml(m)}" ${
                  profile.major === m ? "selected" : ""
                }>${escapeHtml(m)}</option>`
            )
            .join("")}
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

    <div class="section-head"><span class="section-title">${t("profile.section_language")}</span></div>
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

    <div class="section-head"><span class="section-title">${t("profile.section_preferences")}</span></div>
    <div class="group">
      <div class="field">
        <label>${t("profile.countries")}</label>
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
      <div class="field">
        <label>${t("profile.budget")}</label>
        <input type="number" inputmode="numeric" id="budget-input" placeholder="—" value="${profile.budget_max ?? ""}" />
      </div>
      <div class="field">
        <label>${t("profile.age")}</label>
        <input type="number" inputmode="numeric" id="age-input" placeholder="—" value="${profile.age ?? ""}" />
      </div>
    </div>

    <button type="button" class="btn btn-accent btn-block" id="save-profile-btn">${t("profile.save")}</button>
    <button type="button" class="btn btn-danger-soft btn-block" id="reset-profile-btn">
      ${icon("trash")}${t("profile.reset")}
    </button>
  `;

  bindChips("gpa-scale-chips", updateGpaPreview);
  bindChips("cert-type-chips", (value) => {
    document.getElementById("cert-score-field").hidden = !value;
  });

  // Diqqat: "Barchasi" qatorida `data-value` yo'q — tanlangan davlatlarni
  // yig'ishda u chetlab o'tilishi uchun hamma joyda `[data-value]` ishlatiladi.
  const countryRows = () =>
    Array.from(document.querySelectorAll("#country-list .country-row[data-value]"));
  const allRow = document.getElementById("country-all");

  const syncAllRow = () => {
    const rows = countryRows();
    allRow.classList.toggle("active", rows.length > 0 && rows.every((r) => r.classList.contains("active")));
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
  });

  syncAllRow();

  // Daraja o'zgarsa, yo'nalishlar ro'yxati ham o'sha darajadagilarga
  // qisqaradi — aks holda bakalavrga faqat PhD'da bor yo'nalish ko'rinardi.
  bindChips("degree-chips", async (value) => {
    const selected = document.getElementById("major-input").value;
    await loadMajors(value);
    const select = document.getElementById("major-input");
    select.innerHTML =
      `<option value="">${escapeHtml(t("profile.major_placeholder"))}</option>` +
      majors
        .map(
          (m) =>
            `<option value="${escapeHtml(m)}" ${
              selected === m ? "selected" : ""
            }>${escapeHtml(m)}</option>`
        )
        .join("");
  });

  document.getElementById("gpa-value-input").addEventListener("input", updateGpaPreview);
  document.getElementById("save-profile-btn").addEventListener("click", saveProfile);
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
  const major = document.getElementById("major-input").value.trim();
  const gpaScale = activeChip("gpa-scale-chips");
  const gpaValue = document.getElementById("gpa-value-input").value;
  const certType = activeChip("cert-type-chips");
  const certScoreEl = document.getElementById("cert-score-input");
  const certScore = certScoreEl ? certScoreEl.value : "";
  const budget = document.getElementById("budget-input").value;
  const age = document.getElementById("age-input").value;

  if (degree) payload.degree_level = degree;
  // Har doim yuboriladi: bo'sh qiymat tanlansa yo'nalish tozalanishi kerak.
  payload.major = major;
  if (gpaScale && gpaValue) {
    payload.gpa_scale = gpaScale;
    payload.gpa_raw = parseFloat(gpaValue);
  }
  if (certType && certScore) {
    payload.language_cert_type = certType;
    payload.language_cert_score = parseFloat(certScore);
  }
  if (budget) payload.budget_max = parseFloat(budget);
  if (age) payload.age = parseInt(age, 10);

  profile = await api("/me", { method: "PATCH", body: JSON.stringify(payload) });
  haptic("success");
  showToast(t("profile.saved_toast"));
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
