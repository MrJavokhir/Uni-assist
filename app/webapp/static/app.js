const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}
const INIT_DATA = (tg && tg.initData) || "";
const TG_USER = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || null;

const I18N = {
  uz: {
    "nav.home": "Bosh sahifa",
    "nav.profile": "Profil",
    "nav.match": "Dasturlar",
    "nav.saved": "Saqlangan",

    "home.greeting": "Salom, {name}! 👋",
    "home.tagline": "Chet elda o'qish safaringiz shu yerdan boshlanadi.",
    "home.profile_complete": "Profil to'ldirilgan",
    "home.complete_profile": "✏️ Profilni to'ldirish",
    "home.stat_green": "🟢 Mos dasturlar",
    "home.stat_yellow": "🟡 Yaqin dasturlar",
    "home.stat_saved": "💼 Saqlangan",
    "home.stat_profile": "✅ Profil",
    "home.section_overview": "Qisqacha",
    "home.alert_title": "⏰ Yaqinlashayotgan muddat",
    "home.alert_body": "{program} — {days} kun qoldi ({date})",
    "home.section_shortcuts": "Tezkor amallar",
    "home.shortcut_match": "Mos dasturlarni ko'rish",
    "home.shortcut_saved": "Saqlanganlarni ko'rish",

    "profile.degree_level": "Daraja",
    "profile.degree_level.bachelor": "Bakalavr",
    "profile.degree_level.master": "Magistratura",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Yo'nalish",
    "profile.major_placeholder": "masalan: Computer Science",
    "profile.gpa_scale": "GPA tizimi",
    "profile.gpa_scale.5": "5 balli",
    "profile.gpa_scale.100": "100 balli",
    "profile.gpa_scale.4": "4.0 (GPA)",
    "profile.gpa_value": "Bahoingiz",
    "profile.gpa_us4": "US GPA (4.0)",
    "profile.gpa_ects": "ECTS",
    "profile.gpa_bavarian": "Germaniya (Bavariya)",
    "profile.lang_cert_type": "Til sertifikati turi",
    "profile.lang_cert_none": "Yo'q",
    "profile.lang_cert_score": "Ball",
    "profile.countries": "Maqsad davlatlar",
    "profile.budget": "Yillik byudjet (USD)",
    "profile.age": "Yosh",
    "profile.save": "Saqlash",
    "profile.saved_toast": "Profil saqlandi ✅",
    "profile.section_academic": "Ta'lim",
    "profile.section_language": "Til",
    "profile.section_preferences": "Afzalliklar",

    "match.empty": "Hech qanday mos dastur topilmadi. Profilingizni to'ldiring.",
    "match.empty_icon": "🔍",
    "match.save": "💾 Saqlash",
    "match.saved": "✅ Saqlangan",
    "match.missing": "Yetishmayapti",
    "match.green": "Mos",
    "match.yellow": "Yaqin",

    "saved.empty": "Hozircha saqlangan dasturingiz yo'q.",
    "saved.empty_icon": "💼",
    "saved.status": "Holat",
    "saved.deadline": "Yaqin muddat",
    "saved.no_deadline": "ko'rsatilmagan",
    "saved.days_left": "{days} kun qoldi",
    "saved.remove": "🗑 Olib tashlash",
    "saved.status.planning": "rejalashtirilmoqda",
    "saved.status.applied": "ariza berildi",
    "saved.status.rejected": "rad etildi",
    "saved.status.accepted": "qabul qilindi",
  },
  ru: {
    "nav.home": "Главная",
    "nav.profile": "Профиль",
    "nav.match": "Программы",
    "nav.saved": "Сохранённые",

    "home.greeting": "Привет, {name}! 👋",
    "home.tagline": "Ваш путь к учёбе за рубежом начинается здесь.",
    "home.profile_complete": "Профиль заполнен",
    "home.complete_profile": "✏️ Заполнить профиль",
    "home.stat_green": "🟢 Подходящие",
    "home.stat_yellow": "🟡 Почти подходящие",
    "home.stat_saved": "💼 Сохранённые",
    "home.stat_profile": "✅ Профиль",
    "home.section_overview": "Обзор",
    "home.alert_title": "⏰ Приближающийся срок",
    "home.alert_body": "{program} — осталось {days} дн. ({date})",
    "home.section_shortcuts": "Быстрые действия",
    "home.shortcut_match": "Смотреть подходящие программы",
    "home.shortcut_saved": "Смотреть сохранённые",

    "profile.degree_level": "Степень",
    "profile.degree_level.bachelor": "Бакалавриат",
    "profile.degree_level.master": "Магистратура",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Направление",
    "profile.major_placeholder": "например: Computer Science",
    "profile.gpa_scale": "Система оценок",
    "profile.gpa_scale.5": "5-балльная",
    "profile.gpa_scale.100": "100-балльная",
    "profile.gpa_scale.4": "4.0 (GPA)",
    "profile.gpa_value": "Ваш балл",
    "profile.gpa_us4": "US GPA (4.0)",
    "profile.gpa_ects": "ECTS",
    "profile.gpa_bavarian": "Германия (Бавария)",
    "profile.lang_cert_type": "Тип языкового сертификата",
    "profile.lang_cert_none": "Нет",
    "profile.lang_cert_score": "Балл",
    "profile.countries": "Целевые страны",
    "profile.budget": "Годовой бюджет (USD)",
    "profile.age": "Возраст",
    "profile.save": "Сохранить",
    "profile.saved_toast": "Профиль сохранён ✅",
    "profile.section_academic": "Образование",
    "profile.section_language": "Язык",
    "profile.section_preferences": "Предпочтения",

    "match.empty": "Подходящих программ не найдено. Заполните профиль.",
    "match.empty_icon": "🔍",
    "match.save": "💾 Сохранить",
    "match.saved": "✅ Сохранено",
    "match.missing": "Не хватает",
    "match.green": "Подходит",
    "match.yellow": "Почти",

    "saved.empty": "Пока нет сохранённых программ.",
    "saved.empty_icon": "💼",
    "saved.status": "Статус",
    "saved.deadline": "Ближайший дедлайн",
    "saved.no_deadline": "не указан",
    "saved.days_left": "осталось {days} дн.",
    "saved.remove": "🗑 Убрать",
    "saved.status.planning": "в планах",
    "saved.status.applied": "подана заявка",
    "saved.status.rejected": "отказ",
    "saved.status.accepted": "принят(а)",
  },
  en: {
    "nav.home": "Home",
    "nav.profile": "Profile",
    "nav.match": "Programs",
    "nav.saved": "Saved",

    "home.greeting": "Hi, {name}! 👋",
    "home.tagline": "Your journey to studying abroad starts here.",
    "home.profile_complete": "Profile completed",
    "home.complete_profile": "✏️ Complete your profile",
    "home.stat_green": "🟢 Matching programs",
    "home.stat_yellow": "🟡 Close programs",
    "home.stat_saved": "💼 Saved",
    "home.stat_profile": "✅ Profile",
    "home.section_overview": "Overview",
    "home.alert_title": "⏰ Upcoming deadline",
    "home.alert_body": "{program} — {days} day(s) left ({date})",
    "home.section_shortcuts": "Quick actions",
    "home.shortcut_match": "See matching programs",
    "home.shortcut_saved": "See saved programs",

    "profile.degree_level": "Degree",
    "profile.degree_level.bachelor": "Bachelor's",
    "profile.degree_level.master": "Master's",
    "profile.degree_level.phd": "PhD",
    "profile.major": "Major",
    "profile.major_placeholder": "e.g. Computer Science",
    "profile.gpa_scale": "Grading system",
    "profile.gpa_scale.5": "5-point",
    "profile.gpa_scale.100": "100-point",
    "profile.gpa_scale.4": "4.0 (GPA)",
    "profile.gpa_value": "Your grade",
    "profile.gpa_us4": "US GPA (4.0)",
    "profile.gpa_ects": "ECTS",
    "profile.gpa_bavarian": "Germany (Bavarian)",
    "profile.lang_cert_type": "Language certificate type",
    "profile.lang_cert_none": "None",
    "profile.lang_cert_score": "Score",
    "profile.countries": "Target countries",
    "profile.budget": "Annual budget (USD)",
    "profile.age": "Age",
    "profile.save": "Save",
    "profile.saved_toast": "Profile saved ✅",
    "profile.section_academic": "Academic",
    "profile.section_language": "Language",
    "profile.section_preferences": "Preferences",

    "match.empty": "No matching programs found. Fill in your profile.",
    "match.empty_icon": "🔍",
    "match.save": "💾 Save",
    "match.saved": "✅ Saved",
    "match.missing": "Missing",
    "match.green": "Match",
    "match.yellow": "Close",

    "saved.empty": "No saved programs yet.",
    "saved.empty_icon": "💼",
    "saved.status": "Status",
    "saved.deadline": "Nearest deadline",
    "saved.no_deadline": "not set",
    "saved.days_left": "{days} day(s) left",
    "saved.remove": "🗑 Remove",
    "saved.status.planning": "planning",
    "saved.status.applied": "applied",
    "saved.status.rejected": "rejected",
    "saved.status.accepted": "accepted",
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
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1800);
}

function skeletonHtml(count) {
  return Array.from({ length: count }, () => `<div class="skeleton"></div>`).join("");
}

let profile = null;
let countries = [];

async function loadProfile() {
  profile = await api("/me");
  lang = profile.ui_language || lang;
}

async function loadCountries() {
  countries = await api("/countries");
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
  const done = checks.filter(Boolean).length;
  return Math.round((done / checks.length) * 100);
}

// ---------- Home view ----------

async function renderHome() {
  const el = document.getElementById("view-home");
  const firstName = (TG_USER && TG_USER.first_name) || "";
  const pct = profileCompleteness();

  el.innerHTML = `
    <div class="hero">
      <div class="hero-greeting">${t("home.greeting", { name: firstName || "👋" })}</div>
      <div class="hero-sub">${t("home.tagline")}</div>
      <div class="hero-progress-wrap">
        <div class="hero-progress-label"><span>${t("home.profile_complete")}</span><span>${pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
      </div>
      ${pct < 100 ? `<button class="hero-cta" id="home-complete-profile">${t("home.complete_profile")}</button>` : ""}
    </div>

    <div id="home-alert"></div>

    <div class="section-title">${t("home.section_overview")}</div>
    <div class="stat-grid" id="home-stats">${skeletonHtml(4)}</div>

    <div class="section-title">${t("home.section_shortcuts")}</div>
    <div class="card" id="home-shortcut-match" style="cursor:pointer;display:flex;align-items:center;gap:10px;">
      <span style="font-size:22px;">🔎</span>
      <div class="card-title" style="margin:0;">${t("home.shortcut_match")}</div>
    </div>
    <div class="card" id="home-shortcut-saved" style="cursor:pointer;display:flex;align-items:center;gap:10px;">
      <span style="font-size:22px;">💼</span>
      <div class="card-title" style="margin:0;">${t("home.shortcut_saved")}</div>
    </div>
  `;

  document.getElementById("home-complete-profile")?.addEventListener("click", () => switchTab("profile"));
  document.getElementById("home-shortcut-match").addEventListener("click", () => switchTab("match"));
  document.getElementById("home-shortcut-saved").addEventListener("click", () => switchTab("saved"));

  const [matches, saved] = await Promise.all([api("/match"), api("/saved")]);

  const green = matches.filter((m) => m.level === "green").length;
  const yellow = matches.filter((m) => m.level === "yellow").length;

  document.getElementById("home-stats").innerHTML = `
    <div class="stat-tile" data-tab="match">
      <div class="stat-tile-value" style="color:var(--green)">${green}</div>
      <div class="stat-tile-label">${t("home.stat_green")}</div>
    </div>
    <div class="stat-tile" data-tab="match">
      <div class="stat-tile-value" style="color:var(--yellow)">${yellow}</div>
      <div class="stat-tile-label">${t("home.stat_yellow")}</div>
    </div>
    <div class="stat-tile" data-tab="saved">
      <div class="stat-tile-value">${saved.length}</div>
      <div class="stat-tile-label">${t("home.stat_saved")}</div>
    </div>
    <div class="stat-tile" data-tab="profile">
      <div class="stat-tile-value">${pct}%</div>
      <div class="stat-tile-label">${t("home.stat_profile")}</div>
    </div>
  `;
  document.querySelectorAll("#home-stats .stat-tile").forEach((tile) => {
    tile.addEventListener("click", () => switchTab(tile.dataset.tab));
  });

  const withDeadline = saved
    .filter((s) => s.nearest_deadline_days_left !== null && s.nearest_deadline_days_left >= 0)
    .sort((a, b) => a.nearest_deadline_days_left - b.nearest_deadline_days_left);

  if (withDeadline.length > 0) {
    const nearest = withDeadline[0];
    const urgent = nearest.nearest_deadline_days_left <= 7;
    document.getElementById("home-alert").innerHTML = `
      <div class="alert ${urgent ? "urgent" : ""}">
        <span class="alert-icon">⏰</span>
        <div>
          <div class="alert-title">${t("home.alert_title")}</div>
          <div class="alert-body">${t("home.alert_body", {
            program: nearest.program_name,
            days: nearest.nearest_deadline_days_left,
            date: nearest.nearest_deadline,
          })}</div>
        </div>
      </div>
    `;
  }
}

// ---------- Profile view ----------

function renderProfile() {
  const el = document.getElementById("view-profile");
  const certType = (profile.language_certificates[0] || {}).type || "";
  const certScore = (profile.language_certificates[0] || {}).score || "";

  el.innerHTML = `
    <div class="section-title">${t("profile.section_academic")}</div>

    <div class="field">
      <label>${t("profile.degree_level")}</label>
      <div class="chip-group" id="degree-chips">
        ${["bachelor", "master", "phd"]
          .map(
            (d) =>
              `<div class="chip ${profile.degree_level === d ? "active" : ""}" data-value="${d}">${t(
                "profile.degree_level." + d
              )}</div>`
          )
          .join("")}
      </div>
    </div>

    <div class="field">
      <label>${t("profile.major")}</label>
      <input type="text" id="major-input" placeholder="${t("profile.major_placeholder")}" value="${profile.major || ""}" />
    </div>

    <div class="field">
      <label>${t("profile.gpa_scale")}</label>
      <div class="chip-group" id="gpa-scale-chips">
        ${["5", "100", "4"]
          .map(
            (s) =>
              `<div class="chip ${profile.gpa_scale === s ? "active" : ""}" data-value="${s}">${t(
                "profile.gpa_scale." + s
              )}</div>`
          )
          .join("")}
      </div>
    </div>

    <div class="field">
      <label>${t("profile.gpa_value")}</label>
      <input type="number" step="0.01" id="gpa-value-input" value="${profile.gpa_raw ?? ""}" />
      <div class="gpa-preview" id="gpa-preview" hidden></div>
    </div>

    <div class="section-title">${t("profile.section_language")}</div>

    <div class="field">
      <label>${t("profile.lang_cert_type")}</label>
      <div class="chip-group" id="cert-type-chips">
        ${["IELTS", "TOEFL", ""]
          .map(
            (c) =>
              `<div class="chip ${(certType || "") === c ? "active" : ""}" data-value="${c}">${
                c || t("profile.lang_cert_none")
              }</div>`
          )
          .join("")}
      </div>
    </div>

    <div class="field" id="cert-score-field" ${certType ? "" : "hidden"}>
      <label>${t("profile.lang_cert_score")}</label>
      <input type="number" step="0.1" id="cert-score-input" value="${certScore}" />
    </div>

    <div class="section-title">${t("profile.section_preferences")}</div>

    <div class="field">
      <label>${t("profile.countries")}</label>
      <div class="chip-group" id="country-chips">
        ${countries
          .map(
            (c) =>
              `<div class="chip ${profile.target_country_ids.includes(c.id) ? "active" : ""}" data-value="${c.id}">${c.name_uz}</div>`
          )
          .join("")}
      </div>
    </div>

    <div class="field">
      <label>${t("profile.budget")}</label>
      <input type="number" id="budget-input" value="${profile.budget_max ?? ""}" />
    </div>

    <div class="field">
      <label>${t("profile.age")}</label>
      <input type="number" id="age-input" value="${profile.age ?? ""}" />
    </div>

    <button class="btn-primary" id="save-profile-btn">${t("profile.save")}</button>
  `;

  bindChipGroup("degree-chips", { multi: false });
  bindChipGroup("gpa-scale-chips", { multi: false, onChange: updateGpaPreview });
  bindChipGroup("cert-type-chips", {
    multi: false,
    onChange: (value) => {
      document.getElementById("cert-score-field").hidden = !value;
    },
  });
  bindChipGroup("country-chips", { multi: true });

  document.getElementById("gpa-value-input").addEventListener("input", updateGpaPreview);
  document.getElementById("save-profile-btn").addEventListener("click", saveProfile);

  updateGpaPreview();
}

function bindChipGroup(containerId, { multi, onChange }) {
  const container = document.getElementById(containerId);
  container.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
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

function getActiveChipValue(containerId) {
  const active = document.querySelector(`#${containerId} .chip.active`);
  return active ? active.dataset.value : null;
}

function getActiveChipValues(containerId) {
  return Array.from(document.querySelectorAll(`#${containerId} .chip.active`)).map((c) => c.dataset.value);
}

async function updateGpaPreview() {
  const scale = getActiveChipValue("gpa-scale-chips");
  const valueRaw = document.getElementById("gpa-value-input").value;
  const preview = document.getElementById("gpa-preview");
  if (!scale || !valueRaw) {
    preview.hidden = true;
    return;
  }
  try {
    const result = await api(`/gpa/convert?value=${encodeURIComponent(valueRaw)}&scale=${encodeURIComponent(scale)}`);
    preview.hidden = false;
    preview.innerHTML = `
      ${t("profile.gpa_us4")}: <b>${result.us4}</b> &nbsp;·&nbsp;
      ${t("profile.gpa_ects")}: <b>${result.ects}</b> &nbsp;·&nbsp;
      ${t("profile.gpa_bavarian")}: <b>${result.bavarian}</b>
      <div class="disclaimer">⚠️ ${result.disclaimer}</div>
    `;
  } catch (e) {
    preview.hidden = true;
  }
}

async function saveProfile() {
  const degree = getActiveChipValue("degree-chips");
  const major = document.getElementById("major-input").value.trim();
  const gpaScale = getActiveChipValue("gpa-scale-chips");
  const gpaValueRaw = document.getElementById("gpa-value-input").value;
  const certType = getActiveChipValue("cert-type-chips");
  const certScoreRaw = document.getElementById("cert-score-input") ? document.getElementById("cert-score-input").value : "";
  const countryIds = getActiveChipValues("country-chips").map((v) => parseInt(v, 10));
  const budgetRaw = document.getElementById("budget-input").value;
  const ageRaw = document.getElementById("age-input").value;

  const payload = {
    ui_language: lang,
    target_country_ids: countryIds,
  };
  if (degree) payload.degree_level = degree;
  if (major) payload.major = major;
  if (gpaScale && gpaValueRaw) {
    payload.gpa_scale = gpaScale;
    payload.gpa_raw = parseFloat(gpaValueRaw);
  }
  if (certType && certScoreRaw) {
    payload.language_cert_type = certType;
    payload.language_cert_score = parseFloat(certScoreRaw);
  }
  if (budgetRaw) payload.budget_max = parseFloat(budgetRaw);
  if (ageRaw) payload.age = parseInt(ageRaw, 10);

  profile = await api("/me", { method: "PATCH", body: JSON.stringify(payload) });
  showToast(t("profile.saved_toast"));
}

// ---------- Match view ----------

async function renderMatch() {
  const el = document.getElementById("view-match");
  el.innerHTML = skeletonHtml(4);

  const matches = await api("/match");
  if (matches.length === 0) {
    el.innerHTML = `<div class="empty-state"><span class="empty-icon">${t("match.empty_icon")}</span>${t("match.empty")}</div>`;
    return;
  }

  el.innerHTML = matches
    .map((m) => {
      const badgeClass = m.level === "green" ? "badge-green" : "badge-yellow";
      const badgeLabel = m.level === "green" ? t("match.green") : t("match.yellow");
      const missing = m.missing.length ? `<div class="missing">${t("match.missing")}: ${m.missing.join(", ")}</div>` : "";
      return `
        <div class="card">
          <span class="badge ${badgeClass}">${badgeLabel}</span>
          <div class="card-title">${m.name}</div>
          <div class="card-sub">${m.university}, ${m.country}</div>
          ${missing}
          <div class="card-actions">
            <button class="btn-secondary save-match-btn" data-id="${m.id}" ${m.saved ? "disabled" : ""}>
              ${m.saved ? t("match.saved") : t("match.save")}
            </button>
          </div>
        </div>
      `;
    })
    .join("");

  el.querySelectorAll(".save-match-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/saved/${btn.dataset.id}`, { method: "POST" });
      btn.disabled = true;
      btn.textContent = t("match.saved");
    });
  });
}

// ---------- Saved view ----------

async function renderSaved() {
  const el = document.getElementById("view-saved");
  el.innerHTML = skeletonHtml(3);
  const items = await api("/saved");

  if (items.length === 0) {
    el.innerHTML = `<div class="empty-state"><span class="empty-icon">${t("saved.empty_icon")}</span>${t("saved.empty")}</div>`;
    return;
  }

  const statuses = ["planning", "applied", "rejected", "accepted"];

  el.innerHTML = items
    .map((s) => {
      const days = s.nearest_deadline_days_left;
      const deadlineText = s.nearest_deadline
        ? days !== null && days >= 0
          ? `${s.nearest_deadline} · ${t("saved.days_left", { days })}`
          : s.nearest_deadline
        : t("saved.no_deadline");
      const soonClass = days !== null && days >= 0 && days <= 7 ? "soon" : "";

      return `
        <div class="card" data-saved-id="${s.id}">
          <div class="card-title">${s.program_name}</div>
          <div class="card-sub">${s.university}, ${s.country}</div>
          <div class="deadline-pill ${soonClass}">📅 ${t("saved.deadline")}: ${deadlineText}</div>
          <div class="field" style="margin-top:12px;margin-bottom:6px;">
            <label>${t("saved.status")}</label>
            <select class="status-select" data-id="${s.id}">
              ${statuses
                .map((st) => `<option value="${st}" ${st === s.status ? "selected" : ""}>${t("saved.status." + st)}</option>`)
                .join("")}
            </select>
          </div>
          <div class="card-actions">
            <button class="btn-secondary remove-saved-btn" data-id="${s.id}">${t("saved.remove")}</button>
          </div>
        </div>
      `;
    })
    .join("");

  el.querySelectorAll(".status-select").forEach((select) => {
    select.addEventListener("change", async () => {
      await api(`/saved/${select.dataset.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: select.value }),
      });
    });
  });

  el.querySelectorAll(".remove-saved-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/saved/${btn.dataset.id}`, { method: "DELETE" });
      btn.closest(".card").remove();
      if (!el.querySelector(".card")) {
        el.innerHTML = `<div class="empty-state"><span class="empty-icon">${t("saved.empty_icon")}</span>${t("saved.empty")}</div>`;
      }
    });
  });
}

// ---------- Tabs & language ----------

function updateNavLabels() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
}

const TAB_RENDERERS = {
  home: renderHome,
  match: renderMatch,
  saved: renderSaved,
  profile: renderProfile,
};

async function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabName));
  document.querySelectorAll(".view").forEach((view) => {
    view.hidden = view.id !== `view-${tabName}`;
  });
  const renderer = TAB_RENDERERS[tabName];
  if (renderer) await renderer();
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
    const activeTab = document.querySelector(".tab.active")?.dataset.tab || "home";
    await switchTab(activeTab);
  });
}

async function init() {
  if (!INIT_DATA) {
    document.getElementById("app").innerHTML =
      '<div class="empty-state">Bu ilova faqat Telegram ichida ishlaydi.<br>This app only works inside Telegram.</div>';
    return;
  }

  await loadProfile();
  await loadCountries();

  updateNavLabels();
  bindTabs();
  bindLangSwitch();
  await renderHome();
}

init().catch((err) => {
  console.error(err);
  document.getElementById("app").innerHTML = `<div class="empty-state">Xatolik: ${err.message}</div>`;
});
