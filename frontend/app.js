// Codeonto dashboard: a small hash-routed SPA over the /api endpoints.
// Pages and KPIs come from GET /api/brands/{id}/config, so every industry renders from the same code.

const API = "/api";

const ICONS = {
  overview: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  reviews: '<path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 17.8 5.8 21l1.2-6.9-5-4.9 6.9-1z"/>',
  ai_replies: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  reply_service: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.5-4.6A8 8 0 1 1 21 12z"/><path d="M8.5 11.5h7M8.5 14.5h4"/>',
  listings: '<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  reports: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  items: '<path d="M4 6h16M4 12h16M4 18h10"/><circle cx="19" cy="18" r="2"/>',
  tickets: '<path d="M3 8a2 2 0 0 0 0 4v4a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-4a2 2 0 0 1 0-4V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z"/><path d="M13 5v2M13 11v2M13 17v1"/>',
  competitors: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  surveys: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1M9 11h6M9 15h4"/>',
  social: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
  alerts: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
  marketplace_sales: '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
  marketplace_ops: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2M9 2h6"/>',
  marketplace_funnel: '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
  marketplace_ads: '<path d="M3 11v3a1 1 0 0 0 1 1h3l5 4V6L7 10H4a1 1 0 0 0-1 1z"/><path d="M16 8a5 5 0 0 1 0 8M19 5a9 9 0 0 1 0 14"/>',
  marketplace_discounts: '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
  store_uptime: '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>',
  stock_outs: '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
  reconciliation: '<rect x="2" y="6" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/><path d="M6 6V4h12v2"/>',
  setup: '<path d="M3 21h18M5 21V7l7-4 7 4v14"/><path d="M9 21v-6h6v6M9 10h.01M15 10h.01"/>',
  clients: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17" cy="9" r="2.5"/><path d="M16 14.2a5 5 0 0 1 5.5 4.8"/>',
  profile: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  team: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M19 8v6M16 11h6"/>',
  billing: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
};

const PLATFORM_COLORS = {
  google: "#d9480f", zomato: "#e23744", swiggy: "#fc8019", magicpin: "#e91e63",
  tripadvisor: "#00aa6c", booking: "#003580", makemytrip: "#d63b3b", facebook: "#1877f2",
  instagram: "#c13584", practo: "#28328c", justdial: "#ff6f00", survey: "#64748b",
};
const SERIES = ["#d9480f", "#0b1229", "#f5a524", "#12a150", "#8b5cf6", "#e5484d"];

// Modules that have a dedicated page; everything else with KPIs uses the generic module page.
const MODULE_PRIMARY = {
  marketplace_sales: "gross_revenue", marketplace_ops: "avg_prep_time", marketplace_funnel: "menu_views",
  marketplace_ads: "ad_roi", marketplace_discounts: "discount_pct_revenue", store_uptime: "online_pct",
  stock_outs: "stock_out_items", listings: "listing_rating", tickets: "open_tickets",
};

// The five marketplace pages are one "Performance" entry in the sidebar, with a tab for each (see addPerfTabs).
const PERF_TABS = [["marketplace_sales", "Sales"], ["marketplace_ops", "Delivery & ops"], ["marketplace_funnel", "Customer funnel"],
  ["marketplace_ads", "Ads"], ["marketplace_discounts", "Discounts & offers"]];
const PERF_CODES = PERF_TABS.map(([c]) => c);

const state = {
  brands: [], brandId: null, config: null, locations: [],
  locationId: "", platform: "", days: 30, custom: null, charts: [],
};

// ---------- helpers ----------
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const icon = (name) => `<svg viewBox="0 0 24 24">${ICONS[name] || ICONS.overview}</svg>`;
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
};

function csrfToken() {
  return (document.cookie.split("; ").find((c) => c.startsWith("csrftoken=")) || "").split("=")[1] || "";
}

// fetch with the session cookie and, on writes, the CSRF token Django expects
function apiFetch(url, opts = {}) {
  const method = (opts.method || "GET").toUpperCase();
  const headers = { ...(opts.headers || {}), ...(method === "GET" ? {} : { "X-CSRFToken": csrfToken() }) };
  return fetch(url, { cache: "no-store", ...opts, headers, credentials: "same-origin" });
}

// What a person may read when a request fails: a sentence the server wrote for people, else a plain one for the kind of failure.
// Status codes, "Internal Server Error" and exception text stay out of the page (they go to the browser console).
function friendlyStatus(status, body) {
  if (typeof body?.detail === "string" && body.detail.trim()) return body.detail;
  if (status === 403) return "You don't have access to this.";
  if (status === 404) return "We couldn't find that.";
  if (status === 409) return "That changed in the meantime. Please refresh and try again.";
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  if (status >= 500) return "Something went wrong on our side. Please try again in a moment.";
  return "That didn't work. Please try again.";
}
const userError = (message, extra = {}) => Object.assign(new Error(message), { friendly: true }, extra);
// Any error shown to a person goes through this: ours are worded for people; anything else (a bug, a library) is hidden.
function userMessage(e) {
  if (e && e.friendly) return e.message;
  console.error(e);
  return "Something went wrong. Please refresh the page and try again.";
}

async function api(path, params = {}, opts = {}) {
  const url = new URL(API + path, location.origin);
  Object.entries(params).forEach(([k, v]) => { if (v !== "" && v != null) url.searchParams.set(k, v); });
  let res;
  try { res = await apiFetch(url, opts); }
  catch (e) { console.error(e); throw userError("We couldn't reach Compass. Check your internet connection and try again.", { status: 0 }); }
  if (res.status === 401 && path !== "/auth/me") { showLogin(); throw userError("Please log in"); }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    console.error(`${res.status} ${res.statusText} from ${path}`);
    throw userError(friendlyStatus(res.status, body), { status: res.status, body });
  }
  return res.json();
}

// local calendar date (toISOString is UTC, which is still "yesterday" before 5:30 am IST)
function isoDate(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; }
function range() {
  if (state.custom) return { start: state.custom.start, end: state.custom.end };
  const end = new Date();
  const start = new Date(); start.setDate(end.getDate() - (state.days - 1));
  return { start: isoDate(start), end: isoDate(end) };
}
const dayLabel = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
function periodLabel() {
  if (!state.custom) return `last ${state.days} days`;
  if (state.custom.label) return state.custom.label;
  const { start, end } = state.custom;
  return start === end ? dayLabel(start) : `${dayLabel(start)} – ${dayLabel(end)}`;
}

function filterParams(extra = {}) {
  return { ...range(), outlet_id: state.locationId, platform: state.platform, ...extra };
}

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const plural = (n, w, many) => `${inr.format(n)} ${n === 1 ? w : many || `${w}s`}`;
function compactCount(v) {
  const a = Math.abs(v);
  return a >= 1e7 ? `${(v / 1e7).toFixed(1)} Cr` : a >= 1e5 ? `${(v / 1e5).toFixed(1)}L` : a >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : inr.format(v);
}
function compactINR(v) {
  const a = Math.abs(v);
  if (a >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (a >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  if (a >= 1e3) return `₹${(v / 1e3).toFixed(1)}K`;
  return `₹${inr.format(v)}`;
}
function fmt(value, unit, compact = true) {
  if (value == null) return "—";
  const v = Number(value);
  switch (unit) {
    case "currency": return compact ? compactINR(v) : `₹${inr.format(v)}`;
    case "percent": return `${v.toFixed(1)}%`;
    case "rating": return v.toFixed(2);
    case "ratio": return `${v.toFixed(2)}x`;
    case "seconds": { const m = Math.floor(v / 60), s = Math.round(v % 60); return `${m}m ${String(s).padStart(2, "0")}s`; }
    case "minutes": return `${v.toFixed(1)} min`;
    default: return compact && Math.abs(v) >= 1e5 ? `${(v / 1e5).toFixed(2)} L` : inr.format(Math.round(v));
  }
}
function changeChip(k) {
  if (k.change_pct == null) return `<span class="chip flat">—</span>`;
  const good = (k.change_pct >= 0) === k.higher_is_better;
  const cls = Math.abs(k.change_pct) < 0.05 ? "flat" : good ? "up" : "down";
  return `<span class="chip ${cls}">${k.change_pct >= 0 ? "▲" : "▼"} ${Math.abs(k.change_pct).toFixed(1)}%</span>`;
}
function stars(r) {
  const n = Math.round(Number(r) || 0);
  return `<span class="stars">${"★".repeat(n)}<span class="off">${"★".repeat(5 - n)}</span></span>`;
}
function timeAgo(ts) {
  const diff = (Date.now() - new Date(ts)) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.max(1, Math.round(diff / 60))}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  if (diff < 86400 * 30) return `${Math.round(diff / 86400)}d ago`;
  return new Date(ts).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
// the ₹ "sales missed on stock-outs" estimate stays hidden (stock-outs page, item scorecard) until it only counts
// checked hours and leaves out items switched off on purpose; apps/insights STOCKOUT_LOSS_SHOWN is the server side
const SHOW_STOCK_LOSS = false;
const PLATFORM_ICONS = ["google", "zomato", "swiggy", "district"];
const outletAvatar = (u) => (u ? `<img src="${esc(u)}" alt="" loading="lazy" referrerpolicy="no-referrer" style="width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:-8px;margin-right:8px;border:1px solid var(--border)">` : "");
const districtLogo = `<img class="pill-icon" src="assets/district.png" alt="District" title="District, Zomato's dining app" style="display:inline-block;vertical-align:-4px;margin-right:6px">`;

function platformPill(code) {
  const icon = PLATFORM_ICONS.includes(code);
  const name = { google: "Google", zomato: "Zomato", swiggy: "Swiggy", district: "District" }[code] || code;
  return `<span class="pill">${icon ? `<img class="pill-icon" src="assets/${code}.png" alt="">` : `<span class="dot" style="background:${PLATFORM_COLORS[code] || "#94a3b8"}"></span>`}${esc(name)}</span>`;
}
function toast(msg) {
  const t = document.createElement("div"); t.className = "toast"; t.textContent = msg;
  document.body.appendChild(t); setTimeout(() => t.remove(), 2200);
}
function kpiMeta(code) { return state.config.kpis.find((k) => k.code === code); }
function moduleName(code) { return state.config.modules.find((m) => m.code === code)?.name || code; }

// ---------- charts ----------
Chart.defaults.font.family = "Inter, sans-serif";
Chart.defaults.color = "#64748b";
Chart.defaults.plugins.legend.labels.boxWidth = 10;
Chart.defaults.plugins.legend.labels.usePointStyle = true;

function destroyCharts() { state.charts.forEach((c) => c.destroy()); state.charts = []; }
function chart(canvas, config) { const c = new Chart(canvas, config); state.charts.push(c); return c; }

function lineChart(canvas, labels, datasets, unit) {
  return chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: datasets.map((d, i) => ({
        borderColor: d.color || SERIES[i], backgroundColor: (d.color || SERIES[i]) + "1f",
        fill: datasets.length === 1, tension: 0.35, pointRadius: labels.length <= 2 ? 6 : 0, pointHoverRadius: 6, pointBackgroundColor: d.color || SERIES[i], borderWidth: 2, ...d,
      })),
    },
    options: {
      maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: datasets.length > 1, position: "top", align: "end" },
        tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmt(c.parsed.y, unit, false)}` } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
        y: { grid: { color: "#eef1f5" }, border: { display: false }, ticks: { callback: (v) => fmt(v, unit) } },
      },
    },
  });
}

function shortDate(d) { return new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" }); }

// ---------- shell ----------
function applyCustomRange(start, end, label = "") {
  state.custom = { start, end, label };
  state.days = Math.round((new Date(end) - new Date(start)) / 86400000) + 1;  // labels like "vs previous N days" stay right
  $("#rangeSeg .active")?.classList.remove("active"); $("#customBtn").classList.add("active");
  $("#customBtn").textContent = periodLabel();
  $("#rangePop").hidden = true; render();
}

function renderSidebar() {
  const route = currentRoute();
  const navLink = (code, name, extra = "") => `<a class="nav-item ${route === code ? "active" : ""}" href="#/${code}" title="${esc(name)}">
      ${icon(code)}<span>${esc(name)}</span>${extra}</a>`;
  let html = "";
  if (state.config) {
    const mods = state.config.modules;
    const link = (m) => {
      const hasData = m.code === "overview" || m.code === "reviews" || m.code === "stock_outs" || m.code === "tickets" || m.code === "items" || m.code === "store_uptime" || m.code === "reconciliation" || m.code === "alerts" || m.code === "listings" || m.code === "competitors" || state.config.kpis.some((k) => k.module === m.code);
      if (m.locked) return navLink(m.code, m.name, `<em class="soon locked-badge">${icon("lock")}Upgrade</em>`);
      return navLink(m.code, m.name, hasData ? "" : '<em class="soon">soon</em>');
    };
    const HIDDEN_NAV = ["ai_replies", "reports", "alerts"];  // taken off the sidebar for now
    const common = mods.filter((m) => m.scope === "common" && !HIDDEN_NAV.includes(m.code));
    const industry = mods.filter((m) => m.scope === "industry");
    // Reconciliation first (the most important), then one Performance entry for the five marketplace pages, then the rest
    const perf = industry.filter((m) => PERF_CODES.includes(m.code));
    const perfLink = perf.length ? `<a class="nav-item ${PERF_CODES.includes(route) ? "active" : ""}" href="#/${perf[0].code}" title="Performance">
      ${icon("marketplace_sales")}<span>Performance</span>${perf.every((m) => m.locked) ? `<em class="soon locked-badge">${icon("lock")}Upgrade</em>` : ""}</a>` : "";
    const diningLink = (state.hasDining ? navLink("dining", "Slots & offers") : "") + navLink("report", "Export reports");
    const aggregator = [...industry.filter((m) => m.code === "reconciliation").map(link), perfLink, diningLink,
      ...industry.filter((m) => m.code !== "reconciliation" && !PERF_CODES.includes(m.code)).map(link)].join("");
    html += `<div class="nav-group">Reputation</div>${common.map(link).join("")}` +
      (industry.length ? `<div class="nav-group">Aggregator management</div>${aggregator}` : "");
  } else {
    html += navLink("overview", "Overview");
  }
  html += `<div class="nav-group">Setup</div>${state.me?.outlet_limited ? "" : navLink("setup", "Brands & Outlets")}` +
    (state.me?.can_manage && state.me?.client ? navLink("team", "Team") + navLink("alert-settings", "Alerts settings") + navLink("billing", "Billing") : "") + navLink("profile", "Profile");
  if (state.me?.is_staff) html += `<div class="nav-group">Client management</div>${navLink("clients", "Clients")}${navLink("sessions", "Sessions")}${navLink("reply_service", "Reply service")}`;
  $("#sidebar").innerHTML = html;
}

// ---------- outlet filter: pick the platform first, then one or more of its outlets ----------
// state.locationId holds the chosen outlet ids as "12" or "12,15,40" ("" = all); every API takes it as outlet_id
const selIds = () => (state.locationId ? String(state.locationId).split(",").filter(Boolean) : []);
const singleId = () => (selIds().length === 1 ? selIds()[0] : "");
const PLATFORM_ID = { zomato: "zomato", swiggy: "swiggy", google: "google" };
const platformLocations = () => (state.platform && PLATFORM_ID[state.platform] ? state.locations.filter((l) => l[state.platform]) : state.locations);
const platformName = () => state.config?.connected_platforms.find((p) => p.code === state.platform)?.name || "";
const pickSel = new Set();

function outletsLabel() {
  const ids = selIds();
  if (!ids.length) return `All ${platformName() ? platformName() + " " : ""}outlets (${platformLocations().length})`;
  if (ids.length === 1) return state.locations.find((l) => String(l.id) === ids[0])?.label || "1 outlet";
  return `${ids.length} outlets`;
}

function showSelectedOutlet() {
  $("#locationBtn").textContent = outletsLabel();
  $("#locationBtn").title = selIds().map((id) => state.locations.find((l) => String(l.id) === id)?.label).filter(Boolean).join("\n");
}

function locationSub(l) {
  const ids = { zomato: l.zomato && `Zomato ${l.zomato}`, swiggy: l.swiggy && `Swiggy ${l.swiggy}`, google: l.google && "Google" };
  return [l.city, state.platform && PLATFORM_ID[state.platform] ? ids[state.platform] : l.resId].filter(Boolean).join(" · ");
}

function renderOutletList() {
  const q = $("#locationSearch").value.trim().toLowerCase();
  const words = q.split(/\s+/).filter(Boolean);
  const pool = platformLocations();
  const matches = pool.filter((l) => words.every((w) => l.search.includes(w)));
  $("#locationList").innerHTML = (q || !matches.length ? "" : `<label class="outlet-filter-item outlet-filter-all"><input type="checkbox" id="locationAll" ${matches.every((l) => pickSel.has(String(l.id))) ? "checked" : ""}>
      <span><b>Select all ${words.length ? "matching" : ""}</b><small>${plural(matches.length, "outlet")}</small></span></label>`) +
    (matches.map((l) => `<label class="outlet-filter-item ${pickSel.has(String(l.id)) ? "on" : ""}" role="option" aria-selected="${pickSel.has(String(l.id))}">
        <input type="checkbox" data-location="${esc(l.id)}" ${pickSel.has(String(l.id)) ? "checked" : ""}>
        <span><b>${esc(l.label)}</b><small>${esc(locationSub(l))}</small></span></label>`).join("") ||
      `<p class="muted outlet-filter-empty">${pool.length ? "No outlets match" : `No outlets on ${esc(platformName())}`}</p>`);
  $("#locationCount").textContent = pickSel.size ? `${pickSel.size} selected` : "none selected = all";
}

function setOutletPicker(open) {
  $("#locationPop").hidden = !open;
  $("#locationBtn").setAttribute("aria-expanded", String(open));
  if (!open) return;
  pickSel.clear(); selIds().forEach((id) => pickSel.add(id));
  $("#locationSearch").value = "";
  renderOutletList();
  $("#locationSearch").focus();
}

function applyOutlets(ids) {
  state.locationId = ids.join(",");
  showSelectedOutlet();
  setOutletPicker(false);
  render();
}

function renderFilters() {
  showSelectedOutlet();
  $("#platformSelect").innerHTML = `<option value="">All platforms</option>` +
    state.config.connected_platforms.map((p) => `<option value="${p.code}">${esc(p.name)}</option>`).join("");
  $("#platformSelect").value = state.platform;
}

async function loadBrand(id) {
  state.brandId = id; store.set("ss_brand", id);
  state.locationId = ""; state.platform = "";
  const [config, outlets, dining] = await Promise.all([api(`/brands/${id}/config`), api(`/brands/${id}/outlets`), api(`/brands/${id}/dining`, { summary: 1 }).catch(() => ({}))]);
  state.config = config;
  state.hasDining = Boolean(dining.has_dining);
  state.locations = outlets.outlets.map((o) => {
    const name = o.area || o.outlet_name;
    const label = o.area && o.area.toLowerCase() !== o.outlet_name.toLowerCase() ? `${o.outlet_name} · ${o.area}` : name;
    const resId = [o.zomato && `Zomato ${o.zomato}`, o.swiggy && `Swiggy ${o.swiggy}`].filter(Boolean).join(" · ");
    return { id: o.id, name, label, city: o.city, resId, zomato: o.zomato || "", swiggy: o.swiggy || "", google: o.google || "",
             search: [name, o.outlet_name, o.city, o.zomato, o.swiggy].filter(Boolean).join(" ").toLowerCase() };
  }).sort((a, b) => a.city.localeCompare(b.city) || a.name.localeCompare(b.name));
  $("#brandIndustry").textContent = config.brand.industry_name + (config.brand.is_demo ? " · SAMPLE DATA" : "");
  renderFilters();
  const route = currentRoute();
  if (!["setup", "clients", "profile", "team", "billing", "dining", "report"].includes(route) && !config.modules.some((m) => m.code === route)) location.hash = "#/overview";
  else render();
}

function currentRoute() { return (location.hash.replace(/^#\//, "") || "overview").split("?")[0].split("/")[0]; }
function routeParam() { return (location.hash.replace(/^#\//, "").split("?")[0].split("/")[1]) || ""; }

// While a page loads: blank for the first 300 ms (most pages are ready by then, so nothing flashes), then a grey
// shimmer in the rough shape of a page. Whatever the page renders replaces it.
let renderSeq = 0;
function showPageSkeleton(page) {
  const seq = ++renderSeq;
  page.innerHTML = `<div class="sk-wait"></div>`;
  setTimeout(() => {
    const wait = seq === renderSeq && page.querySelector(":scope > .sk-wait");
    if (!wait) return;
    wait.outerHTML = `<div class="sk" aria-busy="true" aria-label="Loading">
      <div class="sk-tiles">${'<div class="sk-box sk-tile"></div>'.repeat(4)}</div>
      <div class="sk-box sk-card">${'<div class="sk-line"></div>'.repeat(6)}</div></div>`;
  }, 300);
}

let pageSeq = 0;
async function render() {
  if (!state.me) return;
  ensureAssistant();
  renderSidebar();
  destroyCharts();
  STAT_PCT = {};  // each page sets its own tile bars
  closePicker();
  const route = currentRoute();
  // a slow page (Overview makes 8 requests) must not paint over the page opened after it: once a newer render starts,
  // this render's writes go to a throwaway element instead of the screen
  const mine = ++pageSeq, real = $("#page"), sink = document.createElement("div");
  const page = new Proxy(real, {
    get(t, k) { const o = pageSeq === mine ? t : sink, v = o[k]; return typeof v === "function" ? v.bind(o) : v; },
    set(t, k, v) { (pageSeq === mine ? t : sink)[k] = v; return true; },
  });
  showPageSkeleton(page);
  document.body.classList.remove("nav-open");

  // staff-only client management, independent of the selected brand
  if (route === "sessions") {
    if (!state.me.is_staff) { location.hash = "#/overview"; return; }
    $("#filters").style.display = "none";
    try { await renderSessions(page); }
    catch (e) { page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(userMessage(e))}</p></div>`; }
    return;
  }
  if (route === "reply_service") {
    if (!state.me.is_staff) { location.hash = "#/overview"; return; }
    $("#filters").style.display = "none";
    try { await renderReplyService(page); }
    catch (e) { page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(userMessage(e))}</p></div>`; }
    return;
  }
  if (route === "clients") {
    if (!state.me.is_staff) { location.hash = "#/overview"; return; }
    $("#filters").style.display = "none";
    try {
      if (routeParam()) await renderClient(page, Number(routeParam()));
      else await renderClients(page);
    } catch (e) {
      page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(userMessage(e))}</p></div>`;
    }
    return;
  }

  // the user's own account, independent of the selected brand
  if (route === "profile") {
    $("#filters").style.display = "none";
    return renderProfile(page);
  }

  // owners manage their own team; staff arrive from a client's page with its id in the address
  if (route === "alert-settings") {
    const clientId = Number(routeParam()) || state.me.client?.id;
    if (!state.me.can_manage || !clientId) { location.hash = state.me.is_staff ? "#/clients" : "#/overview"; return; }
    $("#filters").style.display = "none";
    try { await renderAlertSettings(page, clientId); }
    catch (e) { page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(userMessage(e))}</p></div>`; }
    return;
  }
  if (route === "team") {
    const clientId = Number(routeParam()) || state.me.client?.id;
    if (!state.me.can_manage || !clientId) { location.hash = state.me.is_staff ? "#/clients" : "#/overview"; return; }
    $("#filters").style.display = "none";
    try {
      await renderTeam(page, clientId);
    } catch (e) {
      page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(userMessage(e))}</p></div>`;
    }
    return;
  }

  // the client's plan; staff arrive from a client's page with its id in the address
  if (route === "billing") {
    const clientId = Number(routeParam()) || state.me.client?.id;
    if (!state.me.can_manage || !clientId) { location.hash = state.me.is_staff ? "#/clients" : "#/overview"; return; }
    $("#filters").style.display = "none";
    try {
      await renderBilling(page, clientId);
    } catch (e) {
      page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(userMessage(e))}</p></div>`;
    }
    return;
  }

  // managers don't see setup: it covers the whole client
  if (route === "setup" && state.me.outlet_limited) { location.hash = "#/overview"; return; }

  // no brand yet: keep the normal layout and point to the next step
  if (!state.config) {
    $("#filters").style.display = "none";
    if (state.me.outlet_limited) {
      $("#pageTitle").textContent = "Overview";
      $("#pageSub").textContent = state.me.client ? state.me.client.name : "Codeonto";
      page.innerHTML = `<div class="card empty-state">${icon("setup")}
        <h3>No outlets assigned yet</h3>
        <p>Ask your account owner to give your login access to your outlets.</p></div>`;
      return;
    }
    if (route === "setup") {
      $("#pageTitle").textContent = "Brands & Outlets";
      $("#pageSub").textContent = "Create a brand, then map its stores";
      return renderSetup(page, { creating: true });
    }
    $("#pageTitle").textContent = "Overview";
    $("#pageSub").textContent = state.me.client ? state.me.client.name : "Codeonto";
    page.innerHTML = `<div class="card empty-state">${icon("setup")}
      <h3>No brands yet</h3>
      <p>${state.me.is_staff
        ? "Add a client and assign its Zomato, Swiggy and Google IDs, then create its brands."
        : "Create your first brand and map its stores to their Zomato, Swiggy and Google IDs."}</p>
      <div class="btn-row" style="justify-content:center;margin-top:14px">
        ${state.me.is_staff ? `<a class="btn blue" href="#/clients">Manage clients</a>` : ""}
        <a class="btn ${state.me.is_staff ? "light" : "blue"}" href="#/setup">Create a brand</a>
      </div></div>`;
    return;
  }

  const isSetup = route === "setup";
  $("#filters").style.display = isSetup ? "none" : "";
  $("#pageTitle").textContent = isSetup ? "Brands & Outlets" : PERF_CODES.includes(route) ? "Performance" : route === "dining" ? "Slots & offers" : route === "report" ? "Export reports" : moduleName(route);
  $("#pageSub").textContent = isSetup
    ? "Name your brand and map each outlet to its Google, Zomato and Swiggy listing"
    : `${state.config.brand.name} · ${outletsLabel().replace(/ \(\d+\)$/, "")} · ${periodLabel()}`;
  const lockedModule = state.config.modules.find((m) => m.code === route && m.locked);
  if (lockedModule) return renderLocked(page, lockedModule);
  page.classList.toggle("ov-glass", !isSetup);
  try {
    if (isSetup) await renderSetup(page, { creating: Boolean(setup.newBrandClientId) });
    else if (route === "overview") await renderOverview(page);
    else if (route === "reviews") await renderReviews(page);
    else if (route === "stock_outs") await renderStockOuts(page);
    else if (route === "tickets") await renderComplaints(page);
    else if (route === "items") await renderItems(page);
    else if (route === "store_uptime") await renderUptime(page);
    else if (route === "reconciliation") {
      if (state.hasDining && state.reconView === "dining") await renderDiningPayouts(page);
      else { await renderReconciliation(page); addReconToggle(page); }
    }
    else if (route === "marketplace_ads") await renderAds(page);
    else if (route === "alerts") await renderAlerts(page);
    else if (route === "listings") await renderListings(page);
    else if (route === "competitors") await renderCompetition(page);
    else if (route === "dining") await renderDiningPage(page);
    else if (route === "report") await renderReport(page);
    else if (state.config.kpis.some((k) => k.module === route)) await renderModule(page, route);
    else renderComingSoon(page, route);
    if (PERF_CODES.includes(route)) addPerfTabs(page, route);
    if (!isSetup) animateOverview(page);
  } catch (e) {
    page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(userMessage(e))}</p></div>`;
  }
}

// Tabs across the top of the Performance pages: one per marketplace page the brand has.
function addPerfTabs(page, route) {
  const have = new Set(state.config.modules.filter((m) => !m.locked).map((m) => m.code));
  const tabs = PERF_TABS.filter(([code]) => have.has(code));
  if (tabs.length < 2) return;
  page.insertAdjacentHTML("afterbegin", `<div class="segmented perf-tabs" style="margin-bottom:16px;flex-wrap:wrap">${tabs.map(([code, label]) =>
    `<button data-go="${code}" class="${code === route ? "active" : ""}">${label}</button>`).join("")}</div>`);
  page.querySelectorAll(".perf-tabs [data-go]").forEach((b) => { b.onclick = () => { location.hash = `#/${b.dataset.go}`; }; });
}

// ---------- Export reports: pick the modules and the dates, check the data, download Excel or PDF ----------
const expState = { start: "", end: "", order: null, preset: "", tables: false, compact: false };
const exSvg = (d, c = "currentColor") => `<svg class="ex-ico" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="${c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const EX_ICON = {
  pdf: exSvg('<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>'),
  xlsx: exSvg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>'),
  wa: `<svg class="ex-ico" viewBox="0 0 24 24" width="17" height="17" fill="#25D366"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5.2 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.3-.7-2.8-1.2-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.8s.7-2 .9-2.3c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.9 2.1c.1.2.1.4 0 .5l-.4.6-.4.4c-.1.2-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.3 2.4 1.5.3.1.4.1.6-.1l.8-1c.2-.3.4-.2.6-.1l2 .9c.3.1.5.2.5.3.1.2.1.8-.1 1.4z"/></svg>`,
  more: exSvg('<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>'),
  mail: exSvg('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>', "#D9480F"),
};

async function renderReport(page) {
  const yest = new Date(); yest.setDate(yest.getDate() - 1);
  if (!expState.start) { const r = range(); expState.start = r.start; expState.end = r.end; }
  const meta = await api(`/brands/${state.brandId}/report`, { ...exportFilters(), check: 1 });
  const mods = new Map(meta.modules.map((m) => [m.key, m]));
  if (!expState.order) expState.order = meta.modules.map((m) => m.key);
  expState.order = expState.order.filter((k) => mods.has(k));
  const presets = [["7", "Last 7 days"], ["30", "Last 30 days"], ["month", "This month"], ["last", "Last month"]];
  const platName = state.platform ? platformName() : "All platforms";
  page.innerHTML = `<div class="ex-wrap"><div class="card ex">
    <h3>Export a report</h3>
    <p class="muted" style="margin:2px 0 14px">Pick the dates, drag what to include, and watch the preview. Download it as Excel or PDF, or send it.</p>
    <div class="ex-label">Dates</div>
    <div class="ex-row">${presets.map(([k, t]) => `<button type="button" class="chip-btn" data-preset="${k}">${t}</button>`).join("")}
      <span class="ex-dates"><label>From <input type="date" id="exStart" max="${isoDate(new Date())}"></label><label>To <input type="date" id="exEnd" max="${isoDate(new Date())}"></label></span></div>
    <div class="ex-label">What to include <small class="muted">drag between the lists, or drag to reorder</small> <button type="button" class="link-btn" id="exAll">all</button> · <button type="button" class="link-btn" id="exNone">none</button></div>
    <div class="ex-dnd">
      <div class="ex-col"><h4>In the report <small class="muted">in this order</small></h4><div class="ex-list" id="exIn" data-zone="in"></div></div>
      <div class="ex-col"><h4>Left out</h4><div class="ex-list" id="exOut" data-zone="out"></div></div>
    </div>
    <p class="muted" style="font-size:12.5px;margin:12px 0 10px">${esc(outletsLabel())} · ${esc(platName)}. Change these with the filters at the top of the page.</p>
    <div id="exCheck" class="rp-data">Checking the data…</div>
    <label class="ex-tables"><input type="checkbox" id="exCompact" ${expState.compact ? "checked" : ""}><span><b>Short report (3 pages)</b><small class="muted">Overview and next steps, Zomato and Swiggy side by side with weekdays against weekends, then payouts. Ignores the section list below.</small></span></label>
    <label class="ex-tables"><input type="checkbox" id="exTables" ${expState.tables ? "checked" : ""}><span><b>Include the detailed tables in the PDF</b><small class="muted">Off: the picture pages only. On: the picture pages plus every number, outlet by outlet.</small></span></label>
    <div class="ex-actions">
      <div class="ex-group"><span class="ex-glabel">Download</span><button class="btn light ex-btn" id="exPdf">${EX_ICON.pdf}PDF</button><button class="btn light ex-btn" id="exXlsx">${EX_ICON.xlsx}Excel</button></div>
      <div class="ex-group"><span class="ex-glabel">Share the PDF</span><button class="btn light ex-btn" id="exWa">${EX_ICON.wa}WhatsApp</button><button class="btn light ex-btn" id="exMail">${EX_ICON.mail}Email</button><button class="btn light ex-btn" id="exMore" title="AirDrop, Messages and other apps">${EX_ICON.more}More</button></div>
    </div></div>
    <aside class="ex-side"><div class="card ex-prev">
      <div class="ex-prev-head"><b>Preview</b><button class="ex-z ex-max-btn" id="exMax" title="Maximize the preview (Esc to close)" aria-label="Maximize">[ ]</button><span class="muted" id="exPrevState"></span></div>
      <div class="ex-frame-wrap"><iframe id="exFrame" title="Report preview"></iframe><div class="ex-busy" id="exBusy">Building the preview…</div></div>
      <div class="ex-send"><div class="ex-chip" id="exChip" draggable="true" title="Drag me onto WhatsApp or Email">${EX_ICON.pdf}<span><b id="exChipName">report.pdf</b><small class="muted">drag me to send</small></span></div>
        <div class="ex-drop" data-via="wa">${EX_ICON.wa}<span>WhatsApp</span></div><div class="ex-drop" data-via="mail">${EX_ICON.mail}<span>Email</span></div><div class="ex-drop" data-via="system" title="AirDrop, Messages and other apps">${EX_ICON.more}<span>More apps</span></div></div>
    </div></aside></div>`;
  const setMax = (on) => { const p = page.querySelector(".ex-prev"); p.classList.toggle("ex-max", on); document.body.classList.toggle("ex-noscroll", on); $("#exMax").textContent = on ? "✕" : "[ ]"; };
  $("#exMax").onclick = () => setMax(!page.querySelector(".ex-prev").classList.contains("ex-max"));
  if (!window._exEsc) { window._exEsc = true; document.addEventListener("keydown", (e) => { if (e.key === "Escape" && document.querySelector(".ex-prev.ex-max")) { document.querySelector(".ex-prev").classList.remove("ex-max"); document.body.classList.remove("ex-noscroll"); const b = document.getElementById("exMax"); if (b) b.textContent = "[ ]"; } }); }
  const wrap = page.querySelector(".ex-wrap");  // per-render handlers go on this, not on `page`, which outlives the render
  const $s = $("#exStart"), $e = $("#exEnd");
  $s.value = expState.start; $e.value = expState.end;
  let cov = null, timer = null, prevTimer = null, prevSeq = 0, prevUrl = null, prevBlob = null, prevSig = "";
  const nm = (g) => `${g.name} (${g.platform === "swiggy" ? "Swiggy" : "Zomato"})`;
  const dayLbl = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  const fileName = () => `report_${expState.start}_to_${expState.end}.pdf`;
  const sig = () => JSON.stringify([expState.start, expState.end, state.locationId, state.platform, expState.order, expState.tables, expState.compact]);
  const pdfUrl = () => {  // modules is always sent: an empty list means "none", not "all"
    const url = new URL(`${API}/brands/${state.brandId}/report/pdf`, location.origin);
    const f = exportFilters();
    ["start", "end", "outlet_id", "platform"].forEach((k) => { if (f[k] !== "" && f[k] != null) url.searchParams.set(k, f[k]); });
    url.searchParams.set("modules", expState.order.join(","));
    if (expState.tables) url.searchParams.set("tables", "1");
    if (expState.compact) { url.searchParams.set("layout", "compact"); url.searchParams.set("modules", "overview,recommendations"); }  // the short report brings its own pages: only the written part comes from the section list
    return url;
  };
  const okToExport = () => expState.start && expState.end && expState.end >= expState.start && expState.order.length > 0;
  const paint = () => {
    page.querySelectorAll("[data-preset]").forEach((b) => b.classList.toggle("on", b.dataset.preset === expState.preset));
    $("#exPdf").disabled = $("#exXlsx").disabled = $("#exWa").disabled = $("#exMail").disabled = $("#exMore").disabled = !okToExport();
    $("#exChip").classList.toggle("off", !okToExport());
    $("#exChipName").textContent = fileName();
  };
  // ---- the PDF, built once per set of choices and reused by the preview, Download and Share ----
  const getPdf = async () => {
    if (prevBlob && prevSig === sig()) return prevBlob;
    const res = await apiFetch(pdfUrl());
    if (!res.ok) throw userError("The file couldn't be made right now. Please try again in a moment.");
    return res.blob();
  };
  const refreshPreview = () => {
    clearTimeout(prevTimer);
    prevTimer = setTimeout(async () => {
      const seq = ++prevSeq, mine = sig(), busy = $("#exBusy"), st = $("#exPrevState");
      if (!busy) return;
      if (!okToExport()) { busy.textContent = expState.order.length ? "Pick a start date that is on or before the end date." : "Nothing is picked yet: drag a section into the report."; busy.classList.add("show"); st.textContent = ""; return; }
      busy.textContent = "Building the preview…"; busy.classList.add("show"); st.textContent = "updating";
      try {
        const res = await apiFetch(pdfUrl());
        if (!res.ok) throw new Error("preview failed");
        const blob = await res.blob();
        if (seq !== prevSeq || !$("#exFrame")) return;  // a newer choice has been made since
        if (prevUrl) URL.revokeObjectURL(prevUrl);
        prevBlob = blob; prevSig = mine; prevUrl = URL.createObjectURL(blob);
        $("#exFrame").src = `${prevUrl}#toolbar=0&navpanes=0&view=FitH`;
        busy.classList.remove("show"); st.textContent = "up to date";
      } catch (err) {
        if (seq !== prevSeq) return;
        busy.textContent = "The preview couldn't be built right now. The download still works."; busy.classList.add("show"); st.textContent = "";
      }
    }, 550);
  };
  // ---- the two lists: what is in the report, in order, and what is left out ----
  const item = (k, inList) => { const m = mods.get(k); return `<div class="ex-item" draggable="true" data-key="${k}"><span class="ex-grip" aria-hidden="true">⠿</span><span class="ex-item-text"><b>${esc(m.name)}</b><small class="muted">${esc(m.about)}</small></span><button type="button" class="ex-x" data-toggle="${k}" aria-label="${inList ? "Leave out" : "Add to the report"} ${esc(m.name)}" title="${inList ? "Leave out" : "Add to the report"}">${inList ? "×" : "+"}</button></div>`; };
  const drawLists = () => {
    const out = meta.modules.map((m) => m.key).filter((k) => !expState.order.includes(k));
    $("#exIn").innerHTML = expState.order.map((k) => item(k, true)).join("") || `<p class="ex-empty muted">Drag sections here to put them in the report.</p>`;
    $("#exOut").innerHTML = out.map((k) => item(k, false)).join("") || `<p class="ex-empty muted">Everything is in the report.</p>`;
    paint();
  };
  const changed = () => { drawLists(); refreshPreview(); };
  const move = (key, zone, index) => {
    expState.order = expState.order.filter((k) => k !== key);
    if (zone === "in") expState.order.splice(Math.min(index ?? expState.order.length, expState.order.length), 0, key);
    changed();
  };
  const dropIndex = (list, y) => {  // where among the items a pointer at height y would drop
    const items = [...list.querySelectorAll(".ex-item:not(.dragging)")];
    const i = items.findIndex((el) => { const r = el.getBoundingClientRect(); return y < r.top + r.height / 2; });
    return i < 0 ? items.length : i;
  };
  let dragKey = null;
  page.querySelectorAll(".ex-list").forEach((list) => {
    list.addEventListener("dragover", (e) => { if (!dragKey) return; e.preventDefault(); list.classList.add("over"); const i = dropIndex(list, e.clientY); list.querySelectorAll(".ex-item").forEach((el) => el.classList.remove("before", "after")); const its = [...list.querySelectorAll(".ex-item:not(.dragging)")]; if (its[i]) its[i].classList.add("before"); else if (its.length) its[its.length - 1].classList.add("after"); });
    list.addEventListener("dragleave", (e) => { if (!list.contains(e.relatedTarget)) { list.classList.remove("over"); list.querySelectorAll(".ex-item").forEach((el) => el.classList.remove("before", "after")); } });
    list.addEventListener("drop", (e) => { if (!dragKey) return; e.preventDefault(); const key = dragKey; dragKey = null; const zone = list.dataset.zone, idx = zone === "in" ? dropIndex(list, e.clientY) : null; list.classList.remove("over"); move(key, zone, idx); });
  });
  wrap.addEventListener("dragstart", (e) => { const it = e.target.closest?.(".ex-item"); if (!it) return; dragKey = it.dataset.key; it.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", dragKey); });
  wrap.addEventListener("dragend", (e) => { dragKey = null; wrap.querySelectorAll(".dragging, .over, .before, .after").forEach((el) => el.classList.remove("dragging", "over", "before", "after")); });
  wrap.addEventListener("click", (e) => { const t = e.target.closest?.("[data-toggle]"); if (!t) return; const k = t.dataset.toggle; move(k, expState.order.includes(k) ? "out" : "in", null); });
  $("#exAll").onclick = () => { expState.order = meta.modules.map((m) => m.key); changed(); };
  $("#exNone").onclick = () => { expState.order = []; changed(); };
  // ---- the data check ----
  const check = async () => {
    paint();
    const box = $("#exCheck");
    if (!expState.start || !expState.end || expState.end < expState.start) { box.className = "rp-data warn"; box.textContent = "Pick a start date that is on or before the end date."; cov = null; return; }
    box.className = "rp-data"; box.textContent = "Checking the data…";
    try {
      const d = await api(`/brands/${state.brandId}/report`, { ...exportFilters(), check: 1 });
      cov = d.coverage;
      if (!cov.days) { box.className = "rp-data"; box.textContent = cov.note || ""; return; }
      if (cov.complete) { box.className = "rp-data ok"; box.textContent = `✓ Sales data is complete for all ${cov.days} days (${dayLbl(cov.from)} – ${dayLbl(cov.to)}). Today is left out, its numbers are still filling in.`; return; }
      box.className = "rp-data warn";
      box.innerHTML = `<details><summary>⚠ ${cov.gaps.length} outlet${cov.gaps.length === 1 ? "" : "s"}/platform${cov.gaps.length === 1 ? "" : "s"} have days with no sales data in ${dayLbl(cov.from)} – ${dayLbl(cov.to)}. Totals leave these days out.</summary>
        <table class="tbl"><thead><tr><th>Outlet</th><th>Days missing</th><th>Which days</th></tr></thead><tbody>${cov.gaps.slice(0, 30).map((g) => `<tr><td>${esc(nm(g))}</td><td>${g.missing_days}${g.no_data ? " (all)" : ""}</td><td>${esc(g.ranges.join(", "))}</td></tr>`).join("")}</tbody></table>
        ${cov.gaps.length > 30 ? `<p class="muted">…and ${cov.gaps.length - 30} more, all listed in the file.</p>` : ""}</details>`;
    } catch (err) { cov = null; box.className = "rp-data warn"; box.textContent = userMessage(err); }
  };
  const later = () => { clearTimeout(timer); timer = setTimeout(check, 350); };
  const setDates = (a, b, preset = "") => { expState.start = a; expState.end = b; expState.preset = preset; $s.value = a; $e.value = b; later(); paint(); refreshPreview(); };
  page.querySelectorAll("[data-preset]").forEach((b) => b.onclick = () => {
    const end = new Date(yest), k = b.dataset.preset;
    if (k === "7" || k === "30") { const st = new Date(end); st.setDate(end.getDate() - (Number(k) - 1)); setDates(isoDate(st), isoDate(end), k); }
    else if (k === "month") setDates(isoDate(new Date(end.getFullYear(), end.getMonth(), 1)), isoDate(end), k);
    else setDates(isoDate(new Date(end.getFullYear(), end.getMonth() - 1, 1)), isoDate(new Date(end.getFullYear(), end.getMonth(), 0)), k);
  });
  $s.onchange = () => setDates($s.value, expState.end);
  $e.onchange = () => setDates(expState.start, $e.value);
  $("#exTables").onchange = (e) => { expState.tables = e.target.checked; refreshPreview(); };
  $("#exCompact").onchange = (e) => { expState.compact = e.target.checked; refreshPreview(); };
  // ---- Download ----
  const saveBlob = (blob, name) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); };
  const download = (kind) => async (e) => {
    const btn = e.currentTarget, label = btn.lastChild.textContent;
    if (cov && !cov.complete && cov.days) {  // tell them before the file is made, not after
      const lines = cov.gaps.slice(0, 6).map((g) => `• ${nm(g)}: ${g.no_data ? "no data at all" : g.ranges.join(", ")}`).join("\n");
      if (!confirm(`Some days have no sales data:\n\n${lines}${cov.gaps.length > 6 ? `\n…and ${cov.gaps.length - 6} more` : ""}\n\nThe file leaves these days out and lists them ${kind === "pdf" ? "on its last page" : 'on a "Data gaps" sheet'}. Download it anyway?`)) return;
    }
    btn.disabled = true; btn.lastChild.textContent = "Preparing…";
    try {
      if (kind === "pdf") saveBlob(await getPdf(), fileName());
      else {
        const url = new URL(`${API}/brands/${state.brandId}/report/xlsx`, location.origin);
        Object.entries(exportFilters()).forEach(([k, v]) => { if (v !== "" && v != null) url.searchParams.set(k, v); });
        const res = await apiFetch(url);
        if (!res.ok) throw userError("The file couldn't be made right now. Please try again in a moment.");
        saveBlob(await res.blob(), `report_${expState.start}_to_${expState.end}.xlsx`);
      }
    } catch (err) { toast(userMessage(err)); }
    btn.disabled = false; btn.lastChild.textContent = label; paint();
  };
  $("#exXlsx").onclick = download("xlsx");
  $("#exPdf").onclick = download("pdf");
  // ---- Share the PDF: the phone's share sheet when it can attach the file, else download it and open WhatsApp / mail with the message ready ----
  const sharePdf = async (via, btn) => {
    if (!okToExport()) { toast("Pick the dates and at least one section first."); return; }
    const label = btn?.lastChild?.textContent;
    if (btn) { btn.disabled = true; btn.lastChild.textContent = "Preparing…"; }
    try {
      const blob = await getPdf(), name = fileName();
      const file = new File([blob], name, { type: "application/pdf" });
      const title = `${dayLbl(expState.start)} – ${dayLbl(expState.end)} report`;
      // the system share sheet on a phone or tablet (WhatsApp is in it) or when asked for ("More"); on a computer, WhatsApp and Email do the direct thing
      const touch = matchMedia("(pointer: coarse)").matches;
      if (navigator.canShare?.({ files: [file] }) && (via === "system" || touch)) { try { await navigator.share({ files: [file], title, text: title }); } catch (err) { if (err.name !== "AbortError") throw err; } }
      else if (via === "system") { saveBlob(blob, name); toast(`PDF downloaded: ${name}`); }
      else {
        // a browser on a computer can't attach a file to WhatsApp or mail, so the PDF is kept on the server under a long random address and the message carries that link
        let link = "";
        try {
          const url = pdfUrl(); url.pathname = url.pathname.replace(/\/report\/pdf$/, "/report/share");
          const res = await apiFetch(url, { method: "POST" });
          if (res.ok) link = location.origin + (await res.json()).path;
        } catch (e) { /* falls back to downloading the file below */ }
        if (link) {
          const msg = `${title}\n${link}`;
          if (via === "wa") window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, "_blank", "noopener");
          else location.href = `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(msg)}`;
          toast("Link ready: it opens the PDF and works for 7 days");
        } else {
          saveBlob(blob, name);
          const msg = `${title}.`;
          if (via === "wa") window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, "_blank", "noopener");
          else location.href = `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(msg)}`;
          toast(`PDF downloaded: attach ${name} in ${via === "wa" ? "WhatsApp" : "your mail"}`);
        }
      }
    } catch (err) { toast(userMessage(err)); }
    if (btn) { btn.disabled = false; btn.lastChild.textContent = label; paint(); }
  };
  $("#exWa").onclick = (e) => sharePdf("wa", e.currentTarget);
  $("#exMail").onclick = (e) => sharePdf("mail", e.currentTarget);
  $("#exMore").onclick = (e) => sharePdf("system", e.currentTarget);
  // ---- drag the report chip onto WhatsApp or Email ----
  const chip = $("#exChip");
  chip.addEventListener("dragstart", (e) => { if (!okToExport()) { e.preventDefault(); return; } dragKey = null; e.dataTransfer.effectAllowed = "copy"; e.dataTransfer.setData("text/plain", fileName()); wrap.classList.add("sending"); });
  chip.addEventListener("dragend", () => wrap.classList.remove("sending"));
  page.querySelectorAll(".ex-drop").forEach((z) => {
    z.addEventListener("dragover", (e) => { if (wrap.classList.contains("sending")) { e.preventDefault(); z.classList.add("over"); } });
    z.addEventListener("dragleave", () => z.classList.remove("over"));
    z.addEventListener("drop", (e) => { e.preventDefault(); z.classList.remove("over"); wrap.classList.remove("sending"); sharePdf(z.dataset.via, null); });
    z.addEventListener("click", () => sharePdf(z.dataset.via, null));
  });
  drawLists();
  check();
  refreshPreview();
}

// the filters an export uses: the page's own dates and modules, plus the outlet and platform picked at the top
function exportFilters() {
  return { start: expState.start, end: expState.end, outlet_id: state.locationId, platform: state.platform, modules: (expState.order || []).join(",") };
}

// Sidebar page "Slots & offers": dining offers and bookable slots, for brands that have a dining outlet.
async function renderDiningPage(page) {
  const v = state.diningTab === "menu" ? "menu" : "offers";
  page.innerHTML = `<div class="segmented recon-toggle" style="margin-bottom:16px;width:fit-content"><button data-v="offers" class="${v === "offers" ? "active" : ""}">Offers</button><button data-v="menu" class="${v === "menu" ? "active" : ""}">Menu</button></div><div id="diningView"></div>`;
  page.querySelector(".recon-toggle").onclick = (e) => {
    const b = e.target.closest("[data-v]"); if (!b || b.dataset.v === v) return;
    state.diningTab = b.dataset.v; renderDiningPage(page);
  };
  if (v === "menu") { renderDiningMenu($("#diningView"), await api(`/brands/${state.brandId}/dining/menu`, { outlet_id: state.locationId })); return; }
  const d = await api(`/brands/${state.brandId}/dining`, { outlet_id: state.locationId, ...range() });
  renderDiningView($("#diningView"), d);
}

// Dining menu prices next to delivery prices: a summary strip, then one collapsed row per outlet.
function renderDiningMenu(box, d) {
  const outlets = d.outlets || [];
  if (!outlets.length) { box.innerHTML = `<div class="card empty-state"><h3>No dining outlets in this selection</h3></div>`; return; }
  const withData = outlets.filter((o) => o.compared);
  const all = withData.flatMap((o) => o.rows);
  const avg = all.length ? all.reduce((a, r) => a + r.diff_pct, 0) / all.length : null;
  const pill = (p) => p == null ? "" : `<span class="status ${Math.abs(p) < 1 ? "replied" : "pending"}">${p > 0 ? "+" : ""}${p.toFixed(1)}%</span>`;
  // the comparison numbers only appear once some dishes have been read and matched
  const strip = all.length ? `<div class="grid kpis" style="margin-bottom:16px">
    <div class="card kpi"><div class="kpi-top"><span class="kpi-label">Dishes compared</span></div><div class="kpi-value">${inr.format(all.length)}</div></div>
    <div class="card kpi"><div class="kpi-top"><span class="kpi-label">Dining vs delivery, average</span></div><div class="kpi-value">${(avg > 0 ? "+" : "") + avg.toFixed(1)}%</div></div>
    <div class="card kpi"><div class="kpi-top"><span class="kpi-label">Priced differently</span></div><div class="kpi-value">${inr.format(all.filter((r) => Math.abs(r.diff_pct) >= 1).length)}</div></div></div>` : "";
  const row = (r) => `<tr><td>${esc(r.name)}${r.note ? ` <small class="muted">${esc(r.note)}</small>` : ""}</td><td>₹${inr.format(r.delivery)}</td><td>₹${inr.format(r.dining)}</td><td>${pill(r.diff_pct)}</td></tr>`;
  const tbl = (rows) => `<table class="tbl"><thead><tr><th>Dish</th><th>Delivery</th><th>Dining</th><th>Difference</th></tr></thead><tbody>${rows.map(row).join("")}</tbody></table>`;
  const card = (o, i) => {
    const status = !o.pages ? "menu not collected yet" : !o.dishes ? `${o.pages} menu page${o.pages === 1 ? "" : "s"}` : !o.compared ? `${o.pages} pages · ${o.dishes} dishes read, none matched to delivery` : `${o.pages} pages · ${o.compared} dishes compared`;
    const top = o.rows.slice(0, 10), rest = o.rows.slice(10);
    const gallery = (o.images || []).length ? `<details class="dn-fold" ${o.dishes ? "" : "open"}><summary><b>Menu pages</b> <small class="muted">${o.images.length} · as shown on District</small></summary>
      <div class="menu-thumbs">${o.images.map((u, k) => `<button type="button" class="menu-thumb" data-lb="${i}" data-k="${k}" title="Open page ${k + 1}"><img loading="lazy" src="${esc(u)}" alt="Menu page ${k + 1}"></button>`).join("")}</div></details>` : "";
    return `<details class="card dining-card" style="margin-bottom:12px" ${i === 0 ? "open" : ""}>
      <summary class="card-head" style="cursor:pointer"><h3>${outletAvatar(o.logo)}${esc(o.name)}</h3><small class="muted">${esc(status)}</small>${pill(o.avg_diff_pct)}${districtLogo.replace("margin-right:6px","margin-left:10px;margin-right:0")}</summary>
      <p class="muted" style="margin:0 0 10px;font-size:12px">${o.menu_updated ? `District: ${esc(o.menu_updated.toLowerCase())}` : "District shows no update time"}${o.checked_at ? ` · checked ${timeAgo(o.checked_at)}` : ""}${o.synced_at ? ` · menu fetched ${timeAgo(o.synced_at)}` : ""}</p>
      ${top.length ? tbl(top) : ""}
      ${rest.length ? `<details class="dn-fold"><summary><b>All ${o.rows.length} compared dishes</b></summary>${tbl(rest)}</details>` : ""}
      ${o.unmatched.length ? `<details class="dn-fold"><summary><b>Not on the delivery menu</b> <small class="muted">${o.unmatched.length} dishes</small></summary>
        <table class="tbl"><tbody>${o.unmatched.map((r) => `<tr><td>${esc(r.name)}${r.note ? ` <small class="muted">${esc(r.note)}</small>` : ""}</td><td>₹${inr.format(r.dining)}</td></tr>`).join("")}</tbody></table></details>` : ""}
      ${gallery}</details>`;
  };
  box.innerHTML = strip + outlets.map(card).join("");
  box.onclick = (e) => {
    const t = e.target.closest("[data-lb]"); if (!t) return;
    const o = outlets[Number(t.dataset.lb)];
    openMenuViewer(o.name, o.images || [], Number(t.dataset.k) || 0);
  };
}

// Full-screen viewer for a menu's page images: arrows, keyboard, swipe, a strip of thumbnails, Esc or a click outside to close.
function openMenuViewer(title, images, start = 0) {
  if (!images.length) return;
  let i = Math.min(Math.max(start, 0), images.length - 1);
  const prevFocus = document.activeElement, prevOverflow = document.body.style.overflow;
  const el = document.createElement("div");
  el.className = "mv"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true"); el.setAttribute("aria-label", `${title} menu`);
  el.innerHTML = `<div class="mv-bar"><span class="mv-title">${esc(title)}</span><span class="mv-count"></span><button type="button" class="mv-x" aria-label="Close">✕</button></div>
    <button type="button" class="mv-nav mv-prev" aria-label="Previous page">‹</button>
    <div class="mv-stage"><img class="mv-img" alt=""></div>
    <button type="button" class="mv-nav mv-next" aria-label="Next page">›</button>
    <div class="mv-strip">${images.map((u, k) => `<button type="button" data-k="${k}" aria-label="Page ${k + 1}"><img src="${esc(u)}" alt="" loading="lazy"></button>`).join("")}</div>`;
  const img = el.querySelector(".mv-img"), count = el.querySelector(".mv-count"), strip = el.querySelector(".mv-strip");
  const show = (n) => {
    i = (n + images.length) % images.length;
    img.classList.add("mv-loading"); img.src = images[i];
    img.onload = () => img.classList.remove("mv-loading");
    count.textContent = `${i + 1} / ${images.length}`;
    strip.querySelectorAll("button").forEach((b, k) => b.classList.toggle("on", k === i));
    strip.querySelector("button.on")?.scrollIntoView({ block: "nearest", inline: "center" });
    [i - 1, i + 1].forEach((k) => { const u = images[(k + images.length) % images.length]; new Image().src = u; });  // the neighbours load ahead
  };
  const close = () => { document.removeEventListener("keydown", onKey); el.remove(); document.body.style.overflow = prevOverflow; prevFocus?.focus?.(); };
  const onKey = (e) => { if (e.key === "Escape") close(); else if (e.key === "ArrowRight") show(i + 1); else if (e.key === "ArrowLeft") show(i - 1); };
  el.querySelector(".mv-x").onclick = close;
  el.querySelector(".mv-prev").onclick = () => show(i - 1);
  el.querySelector(".mv-next").onclick = () => show(i + 1);
  strip.onclick = (e) => { const b = e.target.closest("[data-k]"); if (b) show(Number(b.dataset.k)); };
  el.querySelector(".mv-stage").onclick = (e) => { if (e.target === e.currentTarget) close(); };
  let x0 = null;
  el.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  el.addEventListener("touchend", (e) => { if (x0 == null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 50) show(i + (dx < 0 ? 1 : -1)); });
  document.addEventListener("keydown", onKey);
  document.body.style.overflow = "hidden";
  document.body.appendChild(el);
  show(i);
  el.querySelector(".mv-x").focus();
}

function renderDiningView(box, d) {
  if (!d.outlets.length) { box.innerHTML = `<div class="card empty-state"><h3>No dining outlets in this selection</h3></div>`; return; }
  box.innerHTML = d.outlets.map((o, i) => {
    if (!o.days.length) return `<div class="card" style="margin-bottom:16px"><h3>${esc(o.name)}</h3><p class="muted">No dining readings yet. The collector hasn't run for this outlet.</p></div>`;
    const day = o.days[0];
    return `<details class="card dining-card" data-i="${i}" style="margin-bottom:16px" ${i === 0 ? "open" : ""}>
      <summary class="card-head" style="cursor:pointer"><h3>${outletAvatar(o.logo)}${esc(o.name)}</h3><small class="muted">checked ${timeAgo(o.last_checked)} · ${esc(o.readings)} reading${o.readings === 1 ? "" : "s"}</small>${districtLogo.replace("margin-right:6px","margin-left:10px;margin-right:0")}</summary>
      <div class="segmented dining-days" style="margin:8px 0 12px;flex-wrap:wrap">${o.days.map((x, k) => `<button data-k="${k}" class="${k === 0 ? "active" : ""}">${new Date(x.date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}</button>`).join("")}</div>
      <div class="dining-day">${diningDay(day)}</div>${diningPast(o.past || [])}</details>`;
  }).join("");
  box.querySelectorAll(".dining-card").forEach((card) => {
    const o = d.outlets[Number(card.dataset.i)];
    card.querySelector(".dining-days").onclick = (e) => {
      const b = e.target.closest("[data-k]"); if (!b) return;
      card.querySelectorAll(".dining-days button").forEach((x) => x.classList.toggle("active", x === b));
      card.querySelector(".dining-day").innerHTML = diningDay(o.days[Number(b.dataset.k)]);
    };
  });
}

// Past dining dates in the chosen period: how much of each offer's capacity was taken (estimated from slots left).
function diningPast(rows) {
  const head = `<summary><b>Past days</b> <small class="muted">${esc(periodLabel())} · ${rows.length} rows</small></summary>`;
  if (!rows.length) return `<details class="dn-fold" style="margin-top:14px">${head}<p class="muted" style="margin:8px 0 0">No readings for past dates in this period. We keep the last 30 days.</p></details>`;
  const tone = (p) => (p == null ? "" : p >= 70 ? "color:#16a34a" : p < 30 ? "color:#dc2626" : "");
  return `<details class="dn-fold" style="margin-top:14px">${head}<p class="muted" style="margin:8px 0;font-size:12px">Booked = most slots we saw minus the last reading. An estimate: cancellations and manual changes also move the count.</p>
    <table class="tbl"><thead><tr><th>Date</th><th>Meal</th><th>Offer</th><th>Slots</th><th>Booked</th><th>Filled</th></tr></thead><tbody>${rows.map((r) => `<tr>
      <td>${new Date(r.date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}</td>
      <td>${esc(r.meal)}</td><td><b>${esc(r.offer)}</b></td><td>${esc(r.capacity)}</td><td>${esc(r.booked)}</td>
      <td style="${tone(r.fill_pct)}"><b>${r.fill_pct == null ? "—" : esc(r.fill_pct) + "%"}</b></td></tr>`).join("")}</tbody></table></details>`;
}

function diningDay(day) {
  const offers = day.offers.length ? `<table class="tbl"><thead><tr><th>Meal</th><th>Offer</th><th>Window</th><th>Slots left</th><th>Booked since first reading</th><th>Cover charge</th></tr></thead><tbody>${day.offers.map((o) => `<tr>
      <td>${esc(o.meal)}</td><td><b>${esc(o.offer)}</b></td><td><small>${esc(o.window)}</small></td>
      <td>${o.slots_left == null ? '<span class="muted">no limit shown</span>' : `<b>${esc(o.slots_left)}</b>`}</td>
      <td>${o.booked_since_first == null ? "—" : esc(o.booked_since_first)}</td><td>${o.cover_charge == null ? "—" : "₹" + esc(o.cover_charge)}</td></tr>`).join("")}</tbody></table>`
    : `<p class="muted">No offers on this day.</p>`;
  const byMeal = {};
  day.slots.forEach((s) => (byMeal[s.meal || "Slots"] = byMeal[s.meal || "Slots"] || []).push(s));
  const chip = (s, gone) => `<span class="comp-cuisine ${gone ? "" : "on"}" style="${gone ? "text-decoration:line-through;opacity:.5" : ""}" title="${gone ? "bookable earlier today, gone now" : "open"}">${esc(s.time || s)}${s.discount_pct ? ` · ${esc(s.discount_pct)}%` : ""}</span>`;
  const slots = Object.entries(byMeal).map(([m, list]) => `<details class="dn-fold"><summary><b>${esc(m)}</b> <small class="muted">${list.length} slots open · ${esc(list[0].time)} to ${esc(list[list.length - 1].time)}</small></summary><div class="comp-cuisine-row" style="margin-top:8px">${list.map((s) => chip(s, false)).join("")}</div></details>`).join("");
  const gone = day.gone.length ? `<details class="dn-fold"><summary><b>Gone since earlier readings</b> <small class="muted">${day.gone.length} full or closed</small></summary><div class="comp-cuisine-row" style="margin-top:8px">${day.gone.map((t) => chip({ time: t }, true)).join("")}</div></details>` : "";
  return offers + slots + gone;
}

function sparkline(points, tone = "#d9480f") {
  const v = points.map((p) => p.value).filter((x) => x != null);
  if (v.length < 2) return "";
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1, w = 100, h = 28;
  const xy = v.map((y, i) => [(i / (v.length - 1)) * w, h - 3 - ((y - lo) / span) * (h - 6)]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><path d="${line} L${w} ${h} L0 ${h} Z" fill="${tone}" opacity=".12"/><path d="${line}" pathLength="1" fill="none" stroke="${tone}" stroke-width="1.8" vector-effect="non-scaling-stroke"/></svg>`;
}

// The badge on a KPI card: the platform logo(s) that supply the number, else the module icon.
function kpiBadge(k, moduleIcon) {
  const known = (k.platforms || []).filter((p) => PLATFORM_ICONS.includes(p));
  if (!known.length) return `<span class="kpi-icon">${icon(moduleIcon || k.module)}</span>`;
  return `<span class="kpi-logos" title="${esc(known.join(" + "))}">${known.map((p) => `<img src="assets/${p}.png" alt="${esc(p)}">`).join("")}</span>`;
}

function kpiCards(kpis, moduleIcon, sparks = {}) {
  if (!kpis.length) return "";
  if (moduleIcon) {
    const order = state.config.kpis.map((k) => k.code);
    kpis = [...kpis].sort((a, b) => order.indexOf(a.code) - order.indexOf(b.code));
  }
  return `<div class="grid kpis">${kpis.map((k) => `
    <div class="card kpi">
      <div class="kpi-top"><span class="kpi-label">${esc(k.name)}</span>${kpiBadge(k, moduleIcon)}</div>
      <div class="kpi-value">${fmt(k.value, k.unit)}</div>
      ${sparks[k.code] ? sparkline(sparks[k.code]) : ""}
      <div class="kpi-foot">${changeChip(k)}<span>vs previous ${state.days === 1 ? "day" : state.days + " days"}</span></div>
    </div>`).join("")}</div>`;
}

// a menu price: the offer price first when a deal is running, with the list price struck through
const menuPrice = (i) => i.offer_price ? `<b title="${esc(i.offer_text || "Offer price")}">₹${i.offer_price}</b> <small class="muted"><s>₹${i.price}</s></small>` : `₹${i.price ?? "—"}`;

// ---------- overview ----------
// the overview answers one question: what needs fixing right now across ratings, reviews, offline outlets and stock-outs
// Overview motion: tiles rise in one after another, their numbers count up, sparklines draw, rating bars fill. Skipped for people who ask for less motion.
function animateOverview(page) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  page.querySelectorAll(".ov-t, .kpi").forEach((t, i) => t.style.setProperty("--i", i));
  page.querySelectorAll(".card:not(.kpi)").forEach((c, i) => { c.classList.add("ov-rise"); c.style.setProperty("--r", Math.min(i, 6)); });
  // table rows come in one after another (the first dozen only, so long tables don't drag)
  page.querySelectorAll("tbody tr").forEach((tr, i) => { if (i < 12) { tr.classList.add("ov-row"); tr.style.setProperty("--ri", i); } });
  // a value that moved since this page was last drawn gets a brief glow in the direction it moved
  const route = location.hash || "#/overview";
  state.lastVals ||= {};
  page.querySelectorAll(".ov-t, .kpi, .cp-stat").forEach((card) => {
    const label = card.querySelector(".ov-t-label, .kpi-label, span")?.textContent?.trim(), val = card.querySelector(".ov-t-value, .kpi-value, b");
    if (!label || !val) return;
    const key = `${route}|${label}`, txt = val.textContent.replace(/[^\d.\-]/g, ""), now = parseFloat(txt), before = state.lastVals[key];
    if (before != null && isFinite(now) && now !== before) card.classList.add(now > before ? "pulse-up" : "pulse-down");
    if (isFinite(now)) state.lastVals[key] = now;
  });
  page.querySelectorAll(".ov-t-value, .kpi-value, .cp-stat b").forEach((el) => {
    const node = [...el.childNodes].find((n) => n.nodeType === 3 && /\d/.test(n.textContent));
    const m = node && node.textContent.match(/^(\D*?)(\d[\d,]*(?:\.\d+)?)(.*)$/s);
    if (!m) return;
    const end = parseFloat(m[2].replace(/,/g, "")), dec = (m[2].split(".")[1] || "").length, [pre, , post] = [m[1], m[2], m[3]];
    if (!isFinite(end) || end === 0) return;
    const t0 = performance.now() + 120 + Number(el.closest(".ov-t, .kpi")?.style.getPropertyValue("--i") || 0) * 70;
    const step = (now) => {
      const p = Math.min(1, Math.max(0, (now - t0) / 800)), e = 1 - Math.pow(1 - p, 3);
      node.textContent = pre + (end * e).toLocaleString("en-IN", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + post;
      if (p < 1) requestAnimationFrame(step);
    };
    node.textContent = pre + (0).toLocaleString("en-IN", { minimumFractionDigits: dec }) + post;
    requestAnimationFrame(step);
  });
}

async function renderOverview(page) {
  const has = (code) => state.config.modules.some((m) => m.code === code);
  const opt = (p) => p.catch(() => null);
  const HEAD_KPIS = ["gross_revenue", "delivered_orders"].filter((c) => kpiMeta(c));  // the two tiles with a trend line
  const [kpiRes, summary, uptime, offLoss, stock, pay, payIssues, dropsRes, fresh, ...headTrends] = await Promise.all([
    api(`/brands/${state.brandId}/kpis`, filterParams()),
    api(`/brands/${state.brandId}/reviews/summary`, filterParams()),
    has("store_uptime") ? opt(api(`/brands/${state.brandId}/uptime/summary`, filterParams())) : null,
    has("store_uptime") ? opt(api(`/brands/${state.brandId}/uptime/loss`, filterParams())) : null,
    has("stock_outs") ? opt(api(`/brands/${state.brandId}/stock-outs/summary`, filterParams())) : null,
    has("reconciliation") ? opt(api(`/brands/${state.brandId}/payouts/summary`, filterParams())) : null,
    has("reconciliation") ? opt(api(`/brands/${state.brandId}/payouts/cycles`, filterParams({ status: "issues", limit: 500 }))) : null,
    opt(api(`/brands/${state.brandId}/kpi-drops`, filterParams())),
    opt(api(`/brands/${state.brandId}/freshness`)),
    ...HEAD_KPIS.map((c) => opt(api(`/brands/${state.brandId}/kpis/${c}/trend`, filterParams()))),
  ]);
  if (!kpiRes.kpis.length && !summary.total && !uptime && !stock && !pay?.cycles) return renderNoData(page);
  const payByOutlet = new Map();
  (payIssues?.results || []).forEach((c) => payByOutlet.set(c.outlet_id, (payByOutlet.get(c.outlet_id) || 0) + 1));
  const platformRating = kpiRes.kpis.find((k) => k.code === "listing_rating" && k.value != null);
  const ratingCount = kpiRes.kpis.find((k) => k.code === "rating_count" && k.value);
  const weekRating = kpiRes.kpis.find((k) => k.code === "weekly_rating" && k.value != null);
  const rating = kpiRes.kpis.find((k) => k.code === "avg_rating");
  const offline = (uptime?.outlets || []).filter((o) => o.offline_since);

  // ---- the eight tiles: the numbers that matter, each linking to its page ----
  const PAY_SHORT = { payout_mismatch: "don't match orders", order_count_mismatch: "order count off", unsettled_orders: "orders unsettled",
    order_payout_math: "order payout off", order_fee_math: "order fee off", fee_rate_changed: "fee % changed", paid_without_utr: "no UTR", unknown_statement_section: "new statement section", overdue: "overdue", deductions_carried: "deductions carried over" };
  const PAY_MONEY = new Set(["payout_mismatch", "overdue", "fee_rate_changed", "order_payout_math", "order_fee_math"]);
  const kpi = (code) => kpiRes.kpis.find((k) => k.code === code && k.value != null);
  const sparkOf = (code) => ((headTrends[HEAD_KPIS.indexOf(code)] || []).length > 1 ? sparkline(headTrends[HEAD_KPIS.indexOf(code)]) : "");
  const T = (tone, href, label, value, sub, chip = "", foot = "") => `<a class="ov-t ${tone}" href="${href}">
      <span class="ov-t-label">${label}</span><div class="ov-t-value">${value}${chip}</div><span class="ov-t-sub">${sub}</span>${foot ? `<div class="ov-t-foot">${foot}</div>` : ""}</a>`;
  const vs = `vs previous ${state.days === 1 ? "day" : state.days + " days"}`;
  const tiles = [];
  const shownRating = platformRating || rating;
  if (shownRating || summary.avg_rating != null) {
    tiles.push(T((shownRating?.change_pct ?? 0) <= -2 ? "amber" : "ok", "#/reviews", "Rating",
      `${shownRating?.value != null ? fmt(shownRating.value, "rating") : fmt(summary.avg_rating, "rating")}<small>★</small>`,
      [ratingCount ? `${compactCount(ratingCount.value)} ratings` : "", weekRating ? `this week ${fmt(weekRating.value, "rating")}★` : ""].filter(Boolean).join(" · ") || `${inr.format(summary.total)} reviews`,
      shownRating ? changeChip(shownRating) : ""));
  }
  const revK = kpi("gross_revenue"), ordK = kpi("delivered_orders");
  if (revK) tiles.push(T((revK.change_pct ?? 0) <= -10 ? "amber" : "ok", "#/marketplace_sales", "Revenue", fmt(revK.value, revK.unit), vs, changeChip(revK), sparkOf("gross_revenue")));
  if (ordK) tiles.push(T((ordK.change_pct ?? 0) <= -10 ? "amber" : "ok", "#/marketplace_sales", "Orders", fmt(ordK.value, ordK.unit), vs, changeChip(ordK), sparkOf("delivered_orders")));
  if (stock) {
    const loss = stock.period_loss;
    tiles.push(T(loss?.high ? "red" : stock.active ? "amber" : "ok", "#/stock_outs", "Sales lost to stock-outs",
      loss?.high ? `${rupeesShort(loss.low)}<small> – ${rupeesShort(loss.high)}</small>` : "—", loss?.high ? `estimated, best sellers, ${periodLabel()}` : "not enough order history to estimate"));
    const recentOut = stock.active - (stock.long_off || 0);  // items off for days are probably off the menu: counted apart, like on the Stock-outs page
    tiles.push(T(recentOut ? "amber" : "ok", "#/stock_outs", "Items out of stock", inr.format(recentOut), stock.active ? `across ${plural(stock.outlets_affected, "outlet")}${stock.long_off ? ` · +${inr.format(stock.long_off)} off ${stock.long_off_days}+ days` : ""}` : "Full menu live"));
  }
  if (uptime) tiles.push(T(offline.length ? "red" : "ok", "#/store_uptime", "Outlets offline", inr.format(offline.length),
    offline.length ? "Not taking orders right now" : `All online${uptime.uptime_pct != null ? ` · ${fmt(uptime.uptime_pct, "percent")} uptime` : ""}`, "",
    offLoss && offLoss.high > 0 ? `<span class="ov-loss lp-open" role="button" tabindex="0">Check estimated revenue loss ›</span>` : ""));
  tiles.push(T(summary.pending ? (summary.negative ? "red" : "amber") : "ok", "#/reviews", "Reviews to reply", inr.format(summary.pending),
    summary.pending ? `${inr.format(summary.negative)} negative in this period` : "All replied"));
  if (pay?.cycles) tiles.push(T(pay.with_issues ? "red" : "ok", "#/reconciliation", "Payouts to check", inr.format(pay.with_issues),
    pay.with_issues ? (pay.discrepancy_total ? `${rupees(pay.discrepancy_total)} unexplained` : "mismatches to review") : `All ${inr.format(pay.reconciled)} checked payouts match`));

  // ---- alerts: everything that got worse or needs action, worst first, in one list ----
  const nameOf = new Map(platformLocations().map((l) => [l.id, l.name]));
  const modName = new Map(state.config.modules.map((m) => [m.code, m.name]));
  const alerts = [];
  // data that used to arrive and has gone quiet: said plainly, so nobody trusts old numbers
  const ageWords = (h) => (h < 48 ? `${Math.round(h)} hours` : `${Math.round(h / 24)} days`);
  (fresh?.sources || []).filter((f) => f.status === "late")
    .forEach((f) => alerts.push({ sev: f.age_hours > f.limit_hours * 3 ? "critical" : "warning", cat: "Data", title: `${f.label} (${f.platform}) not updated for ${ageWords(f.age_hours)}`, sub: "numbers on this page may be out of date", href: "#/overview", rank: 0.5 }));
  offline.forEach((o) => alerts.push({ sev: "critical", cat: "Offline hours", title: `${o.name} is offline`, sub: `since ${timeAgo(o.offline_since).replace(" ago", "")}`, href: "#/store_uptime", rank: 0 }));
  const foodSafety = (summary.by_topic?.topics || []).find((t) => t.slug === "food_safety");
  if (foodSafety?.negative) alerts.push({ sev: "critical", cat: "Reviews", title: `${plural(foodSafety.negative, "negative review")} about food safety`, sub: "stomach issues, hair, insects, spoiled food", href: "#/reviews", set: { topic: "food_safety", rating: "neg", status: "" }, rank: 1 });
  if (summary.pending) alerts.push({ sev: summary.negative ? "critical" : "warning", cat: "Reviews", title: `${plural(summary.pending, "review")} waiting for a reply`, sub: `${inr.format(summary.negative)} negative in this period`, href: "#/reviews", set: { status: "pending", rating: "", topic: "" }, rank: 2 });
  (pay?.issues || []).slice(0, 3).forEach((i) => alerts.push({ sev: PAY_MONEY.has(i.code) ? "critical" : "warning", cat: "Payouts", title: `${plural(i.count, "payout")}: ${PAY_SHORT[i.code] || i.label}`, sub: pay.discrepancy_total && i.code === "payout_mismatch" ? `${rupees(pay.discrepancy_total)} unexplained` : "open reconciliation", href: "#/reconciliation", rank: 3 }));
  [...(stock?.by_outlet || [])].filter((o) => o.active >= 10).sort((a, b) => b.active - a.active).slice(0, 3)
    .forEach((o) => alerts.push({ sev: "warning", cat: "Out of stock", title: `${plural(o.active, "item")} out of stock`, sub: nameOf.get(o.outlet_id) || `Outlet ${o.outlet_id}`, href: "#/stock_outs", rank: 4 }));
  (dropsRes?.drops || []).slice(0, 60).forEach((d) => {
    const pct = d.change_pct == null ? "" : `${Math.abs(d.change_pct).toFixed(0)}%`;
    const title = d.unit === "percent" || d.unit === "rating" ? `${d.name} fell from ${fmt(d.previous, d.unit)} to ${fmt(d.value, d.unit)}`
      : `${d.name} ${d.higher_is_better === false ? "rose" : "fell"} ${pct} (${fmt(d.previous, d.unit)} → ${fmt(d.value, d.unit)})`;
    alerts.push({ sev: d.severity, cat: modName.get(d.module) || d.module, title, sub: `${d.outlet}${d.city ? ` · ${d.city}` : ""} · vs previous ${state.days === 1 ? "day" : state.days + " days"}`, href: `#/${d.module}`, rank: 5 });
  });
  alerts.sort((a, b) => (a.sev === "critical" ? 0 : 1) - (b.sev === "critical" ? 0 : 1) || a.rank - b.rank);
  const alertCats = [...new Set(alerts.map((a) => a.cat))];
  const critical = alerts.filter((a) => a.sev === "critical").length;

  // ---- 3. one row per outlet, worst first ----
  const rev = new Map((summary.by_outlet || []).map((o) => [o.outlet_id, o]));
  const up = new Map((uptime?.outlets || []).map((o) => [o.id, o]));
  const so = new Map((stock?.by_outlet || []).map((o) => [o.outlet_id, o]));
  const rows = platformLocations().filter((l) => !selIds().length || selIds().includes(String(l.id))).map((l) => ({
    ...l, rating: rev.get(l.id)?.avg_rating ?? null, pending: rev.get(l.id)?.pending || 0,
    offline: !!up.get(l.id)?.offline_since, uptime: up.get(l.id)?.uptime_pct ?? null, out: so.get(l.id)?.active || 0, pay: payByOutlet.get(l.id) || 0,
  })).sort((a, b) => b.offline - a.offline || b.pay - a.pay || b.out - a.out || b.pending - a.pending || (a.rating ?? 9) - (b.rating ?? 9));
  const bad = (cond, html) => `<td class="num ${cond ? "ov-bad" : ""}">${html}</td>`;

  // how much of the period's reviews have been answered: the one number on this page an owner can push to 100
  const healthyPct = summary.total ? Math.round((summary.replied / summary.total) * 100) : null;
  const healthRing = healthyPct == null ? "" : `<span class="ov-ring" title="${inr.format(summary.replied)} of ${inr.format(summary.total)} reviews in this period have a reply"><svg viewBox="0 0 36 36" width="30" height="30"><circle cx="18" cy="18" r="15" class="ov-ring-bg"/><circle cx="18" cy="18" r="15" class="ov-ring-fg ${healthyPct < 40 ? "low" : healthyPct < 75 ? "mid" : ""}" pathLength="100" stroke-dasharray="${healthyPct} 100"/></svg><b>${healthyPct}%</b><small class="muted">reviews replied</small></span>`;
  const ALERTS_SHOWN = 6, ROWS_SHOWN = 10;
  page.innerHTML = `
    <div class="ov-tgrid">${tiles.join("")}</div>
    <div class="card ov-alerts">
      <div class="card-head"><h3>${alerts.length ? "Needs attention" : "All clear"}</h3>${healthRing}${critical ? `<span class="ov-crit">${critical} critical</span>` : '<span class="muted">nothing needs fixing right now</span>'}</div>
      <div id="ovAlertList"></div>
    </div>
    <div class="card" style="margin-top:14px">
      <div class="card-head"><h3>Outlets at a glance</h3><span class="muted">worst first · click to focus</span></div>
      <div class="cp-scroll"><table class="ov-table"><thead><tr><th>Outlet</th><th class="num">Rating</th><th class="num">To reply</th>
        ${uptime ? '<th class="num">Status</th>' : ""}${stock ? '<th class="num">Items out</th>' : ""}${pay?.cycles ? '<th class="num">Payouts to check</th>' : ""}</tr></thead><tbody id="ovRows"></tbody></table></div>
      <div id="ovRowsMore"></div>
    </div>`;

  page.querySelectorAll(".lp-open").forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); openLossPanel(offLoss); }));
  let allAlerts = false, allRows = false;
  const drawAlerts = () => {
    const list = allAlerts ? alerts : alerts.slice(0, ALERTS_SHOWN);
    $("#ovAlertList").innerHTML = list.map((a) => `<a class="ov-alert ${a.sev}" href="${a.href}" data-ai="${alerts.indexOf(a)}">
        <i class="ov-dot"></i><span class="ov-alert-text"><strong>${esc(a.title)}</strong><small>${esc(a.sub)}</small></span><span class="ov-alert-cat">${esc(a.cat)}</span></a>`).join("")
      + (alerts.length > ALERTS_SHOWN ? `<button type="button" class="ov-more" id="ovAlertsMore">${allAlerts ? "Show fewer" : `Show all ${alerts.length}`}</button>` : "");
    $("#ovAlertsMore")?.addEventListener("click", () => { allAlerts = !allAlerts; drawAlerts(); });
  };
  const drawRows = () => {
    const list = allRows ? rows : rows.slice(0, ROWS_SHOWN);
    $("#ovRows").innerHTML = list.map((r) => `<tr class="cp-click" data-outlet="${r.id}">
          <td><strong>${esc(r.name)}</strong><small class="muted">${esc(r.city || "")}</small></td>
          <td class="num ${r.rating != null && r.rating < 3.5 ? "ov-bad" : ""}">${r.rating != null ? `<span class="ov-rbar"><i style="width:${Math.max(4, (r.rating / 5) * 100)}%" class="${r.rating < 3.5 ? "low" : r.rating < 4 ? "mid" : ""}"></i></span>${fmt(r.rating, "rating")} ★` : '<span class="muted">—</span>'}</td>
          ${bad(r.pending > 0, r.pending || '<span class="muted">0</span>')}
          ${uptime ? `<td class="num">${r.offline ? '<span class="ov-pill red">Offline</span>' : r.uptime != null ? `<span class="ov-pill ${r.uptime < 95 ? "amber" : "ok"}">${fmt(r.uptime, "percent")}</span>` : '<span class="muted">—</span>'}</td>` : ""}
          ${stock ? bad(r.out > 0, r.out || '<span class="muted">0</span>') : ""}
          ${pay?.cycles ? bad(r.pay > 0, r.pay || '<span class="muted">0</span>') : ""}</tr>`).join("");
    $("#ovRowsMore").innerHTML = rows.length > ROWS_SHOWN ? `<button type="button" class="ov-more" id="ovRowsBtn">${allRows ? "Show fewer" : `Show all ${rows.length} outlets`}</button>` : "";
    $("#ovRowsBtn")?.addEventListener("click", () => { allRows = !allRows; drawRows(); });
  };
  drawAlerts();
  drawRows();
  $("#ovAlertList").addEventListener("click", (e) => {
    const a = e.target.closest("[data-ai]");
    if (a && alerts[Number(a.dataset.ai)].set) Object.assign(reviewFilters, alerts[Number(a.dataset.ai)].set);
  });
  $("#ovRows").addEventListener("click", (e) => {
    const r = e.target.closest("[data-outlet]");
    if (r) { state.locationId = r.dataset.outlet; showSelectedOutlet(); render(); }
  });
}

function leaderboardTable(rows, unit) {
  const ranked = rows.filter((r) => r.value != null);
  if (!ranked.length) return `<p class="muted">No data for this period.</p>`;
  const max = Math.max(...ranked.map((r) => Math.abs(r.value)));
  return `<table><thead><tr><th>#</th><th>Outlet</th><th>City</th><th class="num">Value</th></tr></thead><tbody>
    ${ranked.map((r, i) => `<tr>
      <td><span class="rank ${i < 3 ? "top" : ""}">${i + 1}</span></td>
      <td>${esc(r.name)}</td><td class="muted">${esc(r.city || "")}</td>
      <td class="num"><div class="bar-cell"><div class="bar" style="width:${Math.round((Math.abs(r.value) / max) * 80)}px"></div>${fmt(r.value, unit)}</div></td>
    </tr>`).join("")}</tbody></table>`;
}

// ---------- generic module page ----------
async function renderModule(page, module) {
  const modKpis = state.config.kpis.filter((k) => k.module === module);
  const selected = new URLSearchParams(location.hash.split("?")[1] || "").get("kpi")
    || MODULE_PRIMARY[module] || modKpis[0].code;
  const meta = kpiMeta(selected) || modKpis[0];
  const platforms = state.platform ? [] : state.config.connected_platforms;

  const sparkKpis = modKpis.filter((k) => k.code !== meta.code).slice(0, 7);  // each card gets a small trend line, which also fills the width a few cards leave
  const [kpiRes, trend, board, sparkRes, ...perPlatform] = await Promise.all([
    api(`/brands/${state.brandId}/kpis`, filterParams({ module })),
    api(`/brands/${state.brandId}/kpis/${meta.code}/trend`, filterParams()),
    api(`/brands/${state.brandId}/leaderboard/${meta.code}`, range()),
    Promise.all(sparkKpis.map((k) => api(`/brands/${state.brandId}/kpis/${k.code}/trend`, filterParams()).catch(() => []))),
    ...platforms.map((p) => api(`/brands/${state.brandId}/kpis/${meta.code}/trend`, filterParams({ platform: p.code }))),
  ]);
  const sparks = { [meta.code]: trend };
  sparkKpis.forEach((k, i) => { sparks[k.code] = sparkRes[i]; });
  if (!kpiRes.kpis.length) return renderNoData(page);
  const platformSeries = platforms
    .map((p, i) => ({ platform: p, points: perPlatform[i] }))
    .filter((s) => s.points.length);

  const funnel = module === "marketplace_funnel" ? funnelCard(kpiRes.kpis) : "";
  // one day selected: a lone dot on a chart says nothing, so show the day's number (and each platform's share of it) instead
  const single = trend.length <= 1;
  const kpi = kpiRes.kpis.find((k) => k.code === meta.code);
  const cur = trend[0]?.value ?? kpi?.value ?? null;
  const prev = kpi && kpi.change_pct != null && kpi.change_pct > -100 && kpi.value != null ? kpi.value / (1 + kpi.change_pct / 100) : null;
  const addable = !["percent", "rating", "ratio", "seconds", "minutes"].includes(meta.unit);  // only totals split into a share per platform
  const split = platformSeries.map((s) => ({ name: s.platform.name, code: s.platform.code, v: s.points.at(-1)?.value })).filter((x) => x.v != null && x.v > 0);
  const dayLabel = trend[0] ? new Date(trend[0].date).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" }) : "";
  const bar = (label, v, max, color) => `<div style="display:grid;grid-template-columns:104px 1fr 96px;align-items:center;gap:10px;margin:9px 0">
    <span class="muted">${esc(label)}</span><div style="background:#eef1f5;border-radius:6px;height:12px"><div style="width:${max ? Math.max(2, Math.abs(v) / max * 100) : 0}%;height:12px;border-radius:6px;background:${color}"></div></div>
    <b style="text-align:right">${fmt(v, meta.unit, false)}</b></div>`;
  const donut = addable && split.length > 1;
  // one day selected: a lone dot on a chart says nothing, so show the day against the previous one and split by platform
  const singleDay = () => `<div class="single-day" style="display:flex;flex-wrap:wrap;gap:12px 28px;align-items:center;padding:4px 0">
    ${donut ? `<div style="position:relative;width:170px;height:170px"><canvas id="cSplit"></canvas>
      <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:none"><b style="font-size:20px">${fmt(cur, meta.unit)}</b><span class="muted" style="font-size:12px">${dayLabel}</span></div></div>`
      : `<div><div class="muted">${dayLabel}</div><b style="font-size:30px">${fmt(cur, meta.unit, false)}</b></div>`}
    <div style="flex:1;min-width:260px">
      ${prev != null && cur != null ? bar("This day", cur, Math.max(cur, prev), "#d9480f") + bar("Previous day", prev, Math.max(cur, prev), "#cbd5e1") : ""}
      ${split.length > 1 ? `<div style="border-top:1px solid #eef1f5;margin:10px 0 2px"></div>` + split.map((x) => bar(x.name, x.v, Math.max(...split.map((y) => y.v)), PLATFORM_COLORS[x.code] || "#94a3b8")).join("") : ""}
    </div></div>`;
  page.innerHTML = `
    ${kpiCards(kpiRes.kpis, module, sparks)}
    ${funnel}
    <div class="card">
      <div class="card-head">
        <h3>${esc(meta.name)}${single ? "" : " trend"}</h3>
        <div class="tabs">${modKpis.map((k) => `<button class="tab ${k.code === meta.code ? "active" : ""}" data-kpi="${k.code}">${esc(k.name)}</button>`).join("")}</div>
      </div>
      ${single ? singleDay() : `<div class="chart-box"><canvas id="cTrend"></canvas></div>`}
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-head"><h3>Outlets ranked by ${esc(meta.name)}</h3><span class="muted">${meta.higher_is_better ? "higher is better" : "lower is better"}</span></div>
      ${leaderboardTable(board, meta.unit)}
    </div>`;

  const labels = trend.map((p) => shortDate(p.date));
  const datasets = platformSeries.length > 1
    ? platformSeries.map((s) => {
        const byDate = Object.fromEntries(s.points.map((p) => [p.date, p.value]));
        return { label: s.platform.name, data: trend.map((p) => byDate[p.date] ?? null), color: PLATFORM_COLORS[s.platform.code], fill: false };
      })
    : [{ label: meta.name, data: trend.map((p) => p.value) }];
  if (!single) lineChart($("#cTrend"), labels, datasets, meta.unit);
  else if (donut) chart($("#cSplit"), { type: "doughnut",
    data: { labels: split.map((x) => x.name), datasets: [{ data: split.map((x) => x.v), backgroundColor: split.map((x) => PLATFORM_COLORS[x.code] || "#94a3b8"), borderWidth: 2 }] },
    options: { maintainAspectRatio: false, cutout: "68%", plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${c.label}: ${fmt(c.parsed, meta.unit, false)}` } } } } });

  page.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => {
    location.hash = `#/${module}?kpi=${b.dataset.kpi}`;
  }));
}

function funnelCard(kpis) {
  const by = Object.fromEntries(kpis.map((k) => [k.code, k.value]));
  const steps = [["Impressions", by.impressions], ["Menu views", by.menu_views], ["Add to cart", by.add_to_cart], ["Orders", by.funnel_orders]];
  if (!steps[0][1]) return "";
  return `<div class="card" style="margin-bottom:16px"><div class="card-head"><h3>Customer funnel</h3><span class="muted">step conversion</span></div>
    ${steps.map(([label, v], i) => `<div class="funnel-row">
      <span>${label}</span>
      <div><div class="funnel-bar" style="width:${Math.max(6, (v / steps[0][1]) * 100)}%">${fmt(v, "count")}</div></div>
      <span class="funnel-conv">${i ? `${((v / steps[i - 1][1]) * 100).toFixed(1)}%` : ""}</span>
    </div>`).join("")}</div>`;
}

// the outlets that need a look first: small cards (name, headline number, bar, badges); a click filters to that outlet, and the full table opens under them
function attentionCard({ hint, items, total, allKey, showAll, tableHtml }) {
  const card = (x) => `<button type="button" class="dn-ocard" data-outlet="${x.id}" title="${esc(x.full || "")}">
    <b class="dn-oname">${esc(x.name)}</b><small>${x.sub}</small>
    <i class="dn-obar"><u style="width:${Math.max(4, Math.round(x.pct))}%;background:${x.barColor}"></u></i>
    <span class="dn-oval ${x.tone || ""}">${x.value}</span>
    <span class="dn-pills">${(x.pills || []).map((t) => `<em class="${t.tone}">${t.text}</em>`).join("")}</span></button>`;
  return `<div class="card cp-card dn-attn"><div class="cp-head"><h3>Needs attention</h3><span class="muted">${hint}</span>
    ${total > items.length ? `<button type="button" class="dn-all" data-more="${allKey}">${showAll ? "Hide table" : `All ${total} outlets ›`}</button>` : ""}</div>
    <div class="dn-ocards">${items.map(card).join("")}</div>${showAll ? tableHtml : ""}</div>`;
}

// summary tiles (reviews, complaints, ...): an icon, the big number, a small note and, where it makes sense, a bar showing the share it stands for
const STAT_ICONS = [
  [/rating|avg/i, '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>'],
  [/negative|open|expir/i, '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17v.01"/>'],
  [/pending|progress|window/i, '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'],
  [/resolved|replied/i, '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>'],
  [/review|complaint/i, '<path d="M4 5h16v11H9l-5 4z"/>'],
  [/refund/i, '<path d="M7 5h10M7 9h10M7 5c5 0 5 7 0 7h-1l6 7"/>'],
];
let STAT_PCT = {};  // label -> 0..100, set by the page before it draws its tiles
function statTile(label, value, tone = "", sub = "") {
  const ico = (STAT_ICONS.find(([re]) => re.test(label)) || [0, '<path d="M5 19V9M12 19V5M19 19v-7"/>'])[1];
  const pct = STAT_PCT[label];
  return `<div class="cp-stat ${tone}"><span><i class="cs-ico"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ico}</svg></i>${label}</span>
    <b>${value}</b>${sub ? `<small>${sub}</small>` : ""}${pct != null && isFinite(pct) ? `<em class="cs-bar"><u style="--w:${Math.max(2, Math.min(100, pct)).toFixed(0)}%"></u></em>` : ""}</div>`;
}

// ---------- donut cards: a share of the whole, each slice a click-to-filter button (the legend holds the exact numbers) ----------
const shade = (hex, amt) => {  // mix a #rrggbb colour toward white (amt > 0) or black (amt < 0)
  const n = parseInt(hex.slice(1), 16), t = amt < 0 ? 0 : 255, k = Math.abs(amt);
  const mix = (c) => Math.round(c + (t - c) * k);
  return `rgb(${mix(n >> 16)}, ${mix((n >> 8) & 255)}, ${mix(n & 255)})`;
};
const DONUT_COLORS = ["#d9480f", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#64748b"];
function donutCard(id, title, hint, slices, centerLabel, cls = "", foot = "") {
  slices = slices.filter((x) => x.count > 0);
  if (!slices.length) return { html: "", mount() {} };
  const total = slices.reduce((t, x) => t + x.count, 0), anyOn = slices.some((x) => x.on);
  const html = `<div class="dn-ring ${cls}"><div class="dn-rh"><b>${title}</b>${hint ? `<small>${hint}</small>` : ""}</div>
    <div class="dn-body"><div class="dn-chart"><canvas id="dn_${id}"></canvas><div class="dn-center"><b data-count="${total}">${inr.format(total)}</b><span>${centerLabel}</span></div></div>
    <div class="dn-legend">${slices.map((x) => `<button type="button" class="dn-item ${x.on ? "on" : ""}" data-dn="${id}:${x.key}" ${x.attr || ""} title="${esc([x.tip, x.sub].filter(Boolean).join(" · "))}">
      <i style="background:${x.color}"></i><span class="dn-name">${esc(x.label)}</span><b>${inr.format(x.count)}</b><span class="muted">${Math.round((x.count / total) * 100)}%</span></button>`).join("")}${foot}</div></div></div>`;
  const mount = () => {
    const el = document.getElementById(`dn_${id}`);
    if (!el) return;
    const ring = chart(el, { type: "doughnut",
      data: { labels: slices.map((x) => x.label), datasets: [{ data: slices.map((x) => x.count), borderWidth: 2, borderColor: "#fff", hoverOffset: 12,
        backgroundColor: (c) => {  // light on top, darker below: the ring looks like it has volume
          const x = slices[c.dataIndex], a = c.chart.chartArea;
          if (!x || !a) return x ? x.color : "#ccc";
          const g = c.chart.ctx.createLinearGradient(0, a.top, 0, a.bottom);
          g.addColorStop(0, shade(x.color, 0.32)); g.addColorStop(0.55, x.color); g.addColorStop(1, shade(x.color, -0.28));
          return anyOn && !x.on ? shade(x.color, 0.6) : g;
        } }] },
      options: { maintainAspectRatio: false, devicePixelRatio: Math.max(2, window.devicePixelRatio || 1), cutout: "68%", layout: { padding: 8 }, animation: { animateRotate: true, animateScale: true, duration: 900, easing: "easeOutQuart" }, plugins: { legend: { display: false }, tooltip: { displayColors: false, padding: 6, bodyFont: { size: 12 }, callbacks: { title: () => "", label: (c) => `${c.label}: ${inr.format(c.parsed)}` } } },
        onClick: (e, els) => { if (els.length) document.querySelector(`[data-dn="${id}:${slices[els[0].index].key}"]`)?.click(); } } });
    document.querySelectorAll(`[data-dn^="${id}:"]`).forEach((b, i) => {  // hovering a legend row pops its slice out
      b.addEventListener("mouseenter", () => { ring.setActiveElements([{ datasetIndex: 0, index: i }]); ring.update(); });
      b.addEventListener("mouseleave", () => { ring.setActiveElements([]); ring.update(); });
    });
    const num = el.parentElement.querySelector("[data-count]");  // the centre number counts up as the ring draws
    if (num && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const end = Number(num.dataset.count), t0 = performance.now();
      const tick = (t) => { const k = Math.min(1, (t - t0) / 900); num.textContent = inr.format(Math.round(end * (1 - Math.pow(1 - k, 3)))); if (k < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    }
  };
  return { html, mount };
}

// ---------- reviews inbox ----------
const reviewFilters = { rating: "", status: "", q: "", contact: "", topic: "", offset: 0 };
const reviewUi = { topicsAll: false, outletsAll: false, listOpen: false };  // the topic and outlet lists show the top few until asked for all
const REVIEW_TOP_TOPICS = 5, REVIEW_TOP_OUTLETS = 5;

let reviewRows = new Map();
const RATING_BAND = { 1: "neg", 2: "neg", 3: "mid", 4: "pos", 5: "pos" };
const REPLY_LABELS = { pending: "Pending", drafted: "Drafted", replied: "Replied", ignored: "Ignored" };

async function renderReviews(page) {
  const [s, kp] = await Promise.all([api(`/brands/${state.brandId}/reviews/summary`, filterParams()),
    api(`/brands/${state.brandId}/kpis`, filterParams()).catch(() => null)]);
  const listing = (kp?.kpis || []).find((k) => k.code === "listing_rating" && k.value != null);
  const ratingTotal = (kp?.kpis || []).find((k) => k.code === "rating_count" && k.value);
  const reviewTotal = (kp?.kpis || []).find((k) => k.code === "total_reviews" && k.value);
  const vsText = state.days === 1 ? "yesterday" : `${state.days} days ago`;
  const dRating = listing && listing.previous_value != null ? Number(listing.value) - Number(listing.previous_value) : null;
  const ratingTrend = dRating == null ? "" : Math.abs(dRating) < 0.005 ? ` · no change vs ${vsText}`
    : ` · <b style="color:var(${dRating > 0 ? "--green" : "--red"})">${dRating > 0 ? "▲" : "▼"} ${Math.abs(dRating).toFixed(2)}</b> vs ${vsText}`;
  const dReviews = reviewTotal && reviewTotal.previous_value != null ? Number(reviewTotal.value) - Number(reviewTotal.previous_value) : null;
  const reviewTrend = dReviews > 0 ? `+${compactCount(dReviews)} new reviews this period · ` : "";  // the platform's own rating, which counts every rated order
  const names = new Map(state.locations.map((l) => [l.id, l.name]));
  const short = (n) => n.split(" · ").slice(1).join(" · ") || n;
  const pct = (n, of = s.total) => (of ? `${Math.round((n / of) * 100)}%` : "—");
  const meter = (n, max) => `<span class="cp-meter"><i style="width:${(n / Math.max(1, max)) * 100}%"></i></span>`;
  const stat = statTile;
  const avg = (v) => (v == null ? "—" : `<span class="rv-avg ${v < 3.5 ? "cp-bad" : v < 4 ? "cp-warn" : ""}">${v.toFixed(2)} ★</span>`);
  const maxStar = Math.max(1, ...s.by_rating.map((r) => r.count));
  const maxPlat = Math.max(1, ...s.by_platform.map((r) => r.count));
  const maxNeg = Math.max(1, ...s.by_outlet.map((r) => r.negative));
  const allTopics = (s.by_topic?.topics || []).filter((t) => t.count).sort((a, b) => (b.slug === "food_safety" && b.negative) - (a.slug === "food_safety" && a.negative) || b.negative - a.negative || b.count - a.count);
  const topicList = reviewUi.topicsAll ? allTopics : allTopics.filter((t, i) => i < REVIEW_TOP_TOPICS || t.slug === reviewFilters.topic);
  const outletList = s.by_outlet;  // the full table, shown under the cards on request
  const attentionItems = s.by_outlet.slice(0, 4).map((r) => ({ id: r.outlet_id, name: short(names.get(r.outlet_id) || `Outlet ${r.outlet_id}`), full: names.get(r.outlet_id) || "",
    sub: `${inr.format(r.count)} review${r.count === 1 ? "" : "s"}`, value: r.avg_rating == null ? "—" : `${r.avg_rating.toFixed(2)} ★`, tone: r.avg_rating == null ? "" : r.avg_rating < 3.5 ? "bad" : r.avg_rating < 4 ? "warn" : "",
    pct: (r.negative / maxNeg) * 100, barColor: r.negative ? "#dc2626" : "#cbd5e1",
    pills: [r.negative ? { text: `${inr.format(r.negative)} negative`, tone: "bad" } : null, r.pending ? { text: `${inr.format(r.pending)} pending`, tone: "warn" } : null].filter(Boolean) }));
  const ratingBands = [["neg", "1–2★", "#dc2626"], ["mid", "3★", "#f59e0b"], ["pos", "4–5★", "#16a34a"]];
  const bandCount = (b) => s.by_rating.filter((r) => RATING_BAND[r.stars] === b).reduce((t, r) => t + r.count, 0);
  const ratingDonut = donutCard("rating", "By rating", "click a slice to filter", ratingBands.map(([b, label, color]) => ({ key: b, label, color, count: bandCount(b), on: reviewFilters.rating === b, attr: `data-band="${b}"`, tip: b === "neg" ? "Negative reviews" : b === "pos" ? "Positive reviews" : "Neutral reviews" })), "reviews");
  const platformDonut = donutCard("platform", "By platform", "where the reviews came from", s.by_platform.map((r, i) => ({ key: r.platform, label: r.platform === "zomato" ? "Zomato" : r.platform === "swiggy" ? "Swiggy" : r.platform, color: PLATFORM_COLORS[r.platform] || DONUT_COLORS[i % DONUT_COLORS.length], count: r.count, attr: `data-platform="${r.platform}"`, sub: r.avg_rating != null ? `avg ${r.avg_rating.toFixed(2)} ★` : "" })), "reviews");
  const topicDonut = donutCard("topic", "What customers talk about", `${reviewFilters.topic ? "click again to clear" : "click a slice to filter"}${s.by_topic?.no_text ? ` · ${inr.format(s.by_topic.no_text)} rated with no text` : ""}`,
    [...topicList.map((t, i) => ({ key: t.slug, label: t.slug === "other" ? "No specific topic" : t.label, color: t.slug === "food_safety" ? "#dc2626" : DONUT_COLORS[i % DONUT_COLORS.length], count: t.count, on: reviewFilters.topic === t.slug,
        attr: `data-topic="${t.slug}"`, sub: t.negative ? `${inr.format(t.negative)} negative` : "", tip: `${t.count} review${t.count === 1 ? "" : "s"} mention this, ${t.negative} of them 1–2★` })),
     ...(!reviewUi.topicsAll && allTopics.length > topicList.length ? [{ key: "more", label: `${allTopics.length - topicList.length} more topics`, color: "#94a3b8", attr: 'data-more="topicsAll"',
        count: allTopics.filter((t) => !topicList.includes(t)).reduce((n, t) => n + t.count, 0) }] : [])], "mentions", "",
    reviewUi.topicsAll && allTopics.length > REVIEW_TOP_TOPICS ? '<button type="button" class="dn-item dn-more" data-more="topicsAll">Show fewer</button>' : "");
  const donuts = [ratingDonut, platformDonut, topicDonut];
  STAT_PCT = { "Platform rating": listing ? (Number(listing.value) / 5) * 100 : null, "Avg of reviews received": s.avg_rating != null ? (s.avg_rating / 5) * 100 : null,
    "Negative (1–2★)": s.total ? (s.negative / s.total) * 100 : null, "Pending reply": s.total ? (s.replied / s.total) * 100 : null };
  const showList = reviewUi.listOpen || reviewFilters.rating || reviewFilters.topic || reviewFilters.status || reviewFilters.q || reviewFilters.contact;  // the list stays out of the way until a slice is clicked
  page.innerHTML = `
    <i id="lkMarker" hidden></i>
    <div class="card cp-stats">
      ${listing ? stat("Platform rating", `${Number(listing.value).toFixed(2)} ★`, "", `${ratingTotal ? compactCount(ratingTotal.value) + " ratings" : ""}${ratingTrend}`.replace(/^ · /, "")) : stat("Avg of reviews received", s.avg_rating != null ? `${s.avg_rating} ★` : "—", "", "only orders where the customer left a review")}${reviewTotal ? stat("Total reviews", compactCount(reviewTotal.value), "", `${reviewTrend}${inr.format(s.total)} in the feed · avg ${s.avg_rating != null ? s.avg_rating + " ★" : "—"}`) : stat("Reviews", inr.format(s.total))}
      ${stat("Negative (1–2★)", inr.format(s.negative), s.negative ? "bad" : "")}${stat("Pending reply", inr.format(s.pending), s.pending ? "warn" : "", `${inr.format(s.replied)} replied · ${pct(s.replied)}`)}
    </div>
    ${s.total ? `<div class="dn-rings">${ratingDonut.html}${s.by_platform.length > 1 ? platformDonut.html : ""}${topicDonut.html}</div>
    ${attentionCard({ hint: "most negative first · click to filter", total: s.by_outlet.length, allKey: "outletsAll", showAll: reviewUi.outletsAll, items: attentionItems,
      tableHtml: `        <div class="cp-scroll"><table class="cp-table"><thead><tr><th>Outlet</th><th class="num">#</th><th class="num">Avg</th>
          <th class="num">1–2★</th><th></th><th class="num">Pending</th></tr></thead><tbody>
        ${outletList.map((r) => `<tr class="cp-click" data-outlet="${r.outlet_id}">
          <td class="cp-ellip" title="${esc(names.get(r.outlet_id) || "")}">${esc(short(names.get(r.outlet_id) || `Outlet ${r.outlet_id}`))}</td>
          <td class="num">${inr.format(r.count)}</td><td class="num">${avg(r.avg_rating)}</td>
          <td class="num ${r.negative ? "cp-bad" : "muted"}">${inr.format(r.negative)}</td><td class="cp-mcell">${meter(r.negative, maxNeg)}</td>
          <td class="num ${r.pending ? "cp-warn" : "muted"}">${inr.format(r.pending)}</td></tr>`).join("")}
        </tbody></table></div>` })}` : ""}
    ${showList ? `    <div class="card cp-card">
      <div class="toolbar cp-toolbar">
        <input id="rq" type="search" placeholder="Search review text…" value="${esc(reviewFilters.q)}">
        <select id="rRating"><option value="">All ratings</option><option value="neg">1–2 ★</option><option value="mid">3 ★</option><option value="pos">4–5 ★</option></select>
        <select id="rStatus"><option value="">Any status</option>${Object.entries(REPLY_LABELS).map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>
        <label class="check nowrap" title="Customers who chose on Zomato to share their number with the restaurant"><input type="checkbox" id="rContact" ${reviewFilters.contact ? "checked" : ""}> Number shared</label>
        <span class="muted">click a row to read it and reply</span>
        <button class="btn light" id="closeList" style="margin-left:auto">Hide list ✕</button>
      </div>
      <div class="table-wrap"><table class="cp-table cp-list"><thead><tr>
        <th>When</th><th>Outlet</th><th></th><th>Rating</th><th>Review</th><th>Customer</th><th>Reply</th></tr></thead>
        <tbody id="reviewList"></tbody></table></div>
      <div style="text-align:center;margin-top:8px"><button class="btn light" id="moreBtn">Load more</button></div>
    </div>`
      : `<div class="card cp-card dn-prompt"><span class="muted">Click a slice above to read those reviews.</span> <button class="btn light" id="showAll">Show all reviews</button></div>`}`;
  if (showList) { $("#rRating").value = reviewFilters.rating; $("#rStatus").value = reviewFilters.status; }
  donuts.forEach((d) => d.mount());
  let timer;
  $("#showAll")?.addEventListener("click", () => { reviewUi.listOpen = true; render(); });
  $("#closeList")?.addEventListener("click", () => { Object.assign(reviewFilters, { rating: "", status: "", q: "", contact: "", topic: "" }); reviewUi.listOpen = false; render(); });
  $("#rq")?.addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { reviewFilters.q = e.target.value; loadReviews(true); }, 300); });
  $("#rRating")?.addEventListener("change", (e) => { reviewFilters.rating = e.target.value; render(); });
  $("#rStatus")?.addEventListener("change", (e) => { reviewFilters.status = e.target.value; loadReviews(true); });
  $("#rContact")?.addEventListener("change", (e) => { reviewFilters.contact = e.target.checked ? "shared" : ""; loadReviews(true); });
  page.querySelectorAll("[data-more]").forEach((b) => b.addEventListener("click", () => { reviewUi[b.dataset.more] = !reviewUi[b.dataset.more]; render(); }));
  const cfg = { sel: reviewSel, types: ["band", "topic", "outlet", "platform"], noun: "review", noRead: ["platform"],
    labelOf: (t, k) => (t === "outlet" ? names.get(Number(k)) || `Outlet ${k}` : t === "band" ? { neg: "1–2★ reviews", mid: "3★ reviews", pos: "4–5★ reviews" }[k] : t === "platform" ? (k === "zomato" ? "Zomato" : k === "swiggy" ? "Swiggy" : k) : (allTopics.find((x) => x.slug === k)?.label || k)) };
  bindLinks(page, s, cfg, (type, key) => {  // "Read them": open the real reviews behind the highlight
    if (type === "band") reviewFilters.rating = key; else if (type === "topic") reviewFilters.topic = key; else if (type === "outlet") { state.locationId = key; showSelectedOutlet(); }
    reviewUi.listOpen = true; render();
  }, reviewLinks);
  if (!showList) return;
  $("#moreBtn").addEventListener("click", () => loadReviews(false));
  bindReviewTable($("#reviewList"));
  await loadReviews(true);
}

async function loadReviews(reset) {
  if (reset) { reviewFilters.offset = 0; reviewRows = new Map(); }
  const rows = await api(`/brands/${state.brandId}/reviews`, {
    ...range(), outlet_id: state.locationId, platform: state.platform, reply_status: reviewFilters.status, q: reviewFilters.q,
    rating: reviewFilters.rating, contact: reviewFilters.contact, topic: reviewFilters.topic, limit: 50, offset: reviewFilters.offset,
  });
  reviewFilters.offset += rows.length;
  rows.forEach((r) => reviewRows.set(String(r.id), r));
  const list = $("#reviewList");
  const html = rows.map(reviewTableRow).join("");
  if (reset) list.innerHTML = html || `<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">No reviews match these filters</td></tr>`;
  else list.insertAdjacentHTML("beforeend", html);
  $("#moreBtn").style.display = rows.length < 50 ? "none" : "";
}

function reviewTableRow(r) {
  const outlet = r.outlet_name.split(" · ").slice(1).join(" · ") || r.outlet_name;
  const tone = r.rating == null ? "" : r.rating <= 2 ? "neg" : r.rating < 4 ? "mid" : "pos";
  return `<tr class="cp-row" data-id="${r.id}">
    <td class="nowrap" title="${esc(new Date(r.reviewed_at).toLocaleString("en-IN"))}">${timeAgo(r.reviewed_at)}</td>
    <td class="cp-ellip" title="${esc(r.outlet_name)}">${esc(outlet)}</td>
    <td><img class="pill-icon" src="assets/${esc(r.platform)}.png" alt="${esc(r.platform)}" title="${esc(r.platform)}"></td>
    <td><span class="rv-chip ${tone}">${r.rating != null ? `${r.rating} ★` : "—"}</span></td>
    <td class="rv-text ${r.body ? "" : "muted"}" title="${esc(r.body)}">${r.body ? esc(r.body) : "Rating only"}</td>
    <td class="cp-ellip">${esc(r.author_name || "Anonymous")}${r.contact ? ` <span title="Shared their number">📞</span>` : ""}</td>
    <td><span class="status ${r.reply_status}">${esc(REPLY_LABELS[r.reply_status] || r.reply_status)}</span></td></tr>`;
}

// a good general reply to start from, for outlets that do not use automatic replies: matched to the stars and to what the
// customer complained about. Staff can edit it before sending. (Outlets on automatic replies get theirs from the collector.)
const SAFETY_WORDS = /stomach|vomit|food poison|poison|hair|insect|cockroach|worm|hospital|sick|\bill\b|infection|fungus|plastic|glass/i;
const REPLY_TOPICS = [
  [/salt/i, "the food being too salty"], [/spic(y|e)|\bhot\b.*chilli|mirchi/i, "the spice level"], [/bland|tasteless|no taste|not tasty|taste/i, "the taste"],
  [/cold|not hot|lukewarm|thanda/i, "the food arriving cold"], [/late|delay|slow|waited|took (too )?long/i, "the delay with your order"],
  [/packag|spill|leak|box|seal/i, "the packaging"], [/missing|not delivered|wrong item|forgot|without|didn.?t (get|receive)/i, "the missing or incorrect item"],
  [/quantity|portion|small|less|little/i, "the portion size"], [/price|expensive|costly|overpriced|value/i, "the pricing"],
  [/stale|old|smell|rotten|spoil/i, "the freshness"], [/oily|oil\b|greasy|undercook|raw|burn|dry|hard|chewy|soggy/i, "how the food was cooked"],
];
function suggestReply(r) {
  const first = (r.author_name || "").trim().split(/\s+/)[0];
  const hi = first && !/^(anonymous|zomato|swiggy|customer|guest)$/i.test(first) ? `Hi ${first}` : "Hi there";
  const brand = state.config?.brand?.name ? state.config.brand.name.replace(/\b\w/g, (c) => c.toUpperCase()) : "";
  const sign = brand ? `\n\nWarm regards,\nTeam ${brand}` : "\n\nWarm regards,\nThe team";
  const stars = r.rating != null ? Math.round(r.rating) : null;
  const text = `${r.title || ""} ${r.body || ""}`;
  if (SAFETY_WORDS.test(text)) {
    return `${hi}, we are very sorry to hear this and we take it seriously. Food safety is our first priority. Please contact us with your order details so our team can look into it right away.${sign}`;
  }
  const topic = (REPLY_TOPICS.find(([re]) => re.test(text)) || [])[1];
  if (stars == null || stars >= 4) {
    if (topic) return `${hi}, thank you for the ${stars || ""}${stars ? "-star " : ""}rating and for your honest feedback about ${topic}. We have shared it with our kitchen team so we get it right next time. We look forward to serving you again soon.${sign}`;
    return text.trim() ? `${hi}, thank you so much for the kind words${stars ? ` and the ${stars}-star rating` : ""}! We are delighted you enjoyed your order and look forward to serving you again soon.${sign}`
      : `${hi}, thank you so much${stars ? ` for the ${stars}-star rating` : ""}! We are glad you enjoyed your order and hope to serve you again soon.${sign}`;
  }
  if (stars === 3) {
    return `${hi}, thank you for your feedback. We are sorry your experience was not perfect${topic ? `, especially ${topic}` : ""}. We have shared your comments with our team so we can improve, and we would love another chance to serve you better.${sign}`;
  }
  if (topic) return `${hi}, we are sorry about ${topic} on your recent order. This is not the standard we aim for, and we have shared your feedback with our team so it is put right. Please reach out to us so we can make it up to you.${sign}`;
  return `${hi}, we are sorry your order did not meet your expectations. We would like to understand what went wrong and make it right, so please reach out to us. We would love another chance to serve you better.${sign}`;
}

function reviewDetail(r) {
  const canReply = r.reply_status !== "replied" && state.me?.can_edit !== false;
  return `<tr class="cp-detail" data-detail="${r.id}"><td colspan="7">
    <div class="review-body ${r.body ? "" : "empty"}">${r.body ? esc(r.body) : "Rating only, no text"}</div>
    ${r.latest_reply ? `<div class="latest-reply" style="margin-top:8px">${esc(r.latest_reply)}</div>` : ""}
    ${r.contact ? contactBox(r) : ""}
    ${r.queued ? '<div class="sess-note ok" style="margin-top:8px">✓ Queued: it goes to Zomato within a few hours, when the collector next runs.</div>' : ""}
    ${canReply && !r.queued && r.send_mode === "ai" ? '<div class="sess-note ok" style="margin-top:8px">Automatic replies are on for this outlet: a reply is written and posted within a few hours. You can still write your own below.</div>' : ""}
    ${canReply && !r.queued && r.send_mode !== "ai" ? '<div class="muted" style="margin:8px 0 2px;font-size:12px">Suggested reply: edit it before you send.</div>' : ""}
    ${canReply && !r.queued ? `<div class="reply-box" style="margin-top:8px"><textarea rows="${r.send_mode === "ai" ? 1 : 4}" placeholder="Write a reply…" data-suggested="${r.send_mode === "ai" ? "" : "1"}">${r.send_mode === "ai" ? "" : esc(suggestReply(r))}</textarea>
      <button class="btn light" data-reply>Save draft</button>${r.send_mode ? '<button class="btn blue" data-send title="Queue this reply to be posted on Zomato">Send to Zomato</button>' : ""}</div>` : ""}</td></tr>`;
}

// a reviewer's shared number (Zomato opt-in): masked until View, which the server logs; never kept after Hide
function contactBox(r, phone) {
  const shown = phone ? phone.replace(/(\d{5})(\d{5})/, "$1 $2") : r.contact.hint;
  return `<div class="rv-contact" data-contact="${r.id}" style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <span class="muted">Shared number</span><b class="nowrap">📞 ${esc(shown)}</b>
    ${phone ? `<a class="btn blue" target="_blank" rel="noopener" data-act="whatsapp"
         href="https://wa.me/91${esc(phone)}?text=${encodeURIComponent(contactMessage(r))}">WhatsApp</a>
      <button class="btn light" data-hide>Hide</button>` : `<button class="btn light" data-view>View</button>`}
    ${r.order_id ? `<span class="muted">Order ${esc(r.order_id)}</span>` : ""}</div>`;
}

function contactMessage(r) {
  const outlet = (r.outlet_name || "").split(" · ")[0];
  const name = (r.author_name || "").split(" ")[0];
  return r.rating != null && r.rating <= 2
    ? `Hi${name ? ` ${name}` : ""}, this is ${outlet}. We saw your review of your recent order${r.order_id ? ` (${r.order_id})` : ""} and we're sorry it wasn't right. Could you tell us what went wrong? We'd like to make it up to you.`
    : `Hi${name ? ` ${name}` : ""}, this is ${outlet}. Thank you for your review of your recent order! We'd love to hear what you'd like us to make for you next time.`;
}

async function contactClick(e) {
  const box = e.target.closest(".rv-contact");
  if (!box) return false;
  const r = reviewRows.get(box.dataset.contact);
  if (e.target.closest("[data-hide]")) { box.outerHTML = contactBox(r); return true; }
  const act = e.target.closest("[data-act]");
  if (act) { apiJSON(`/reviews/${r.id}/contact`, "POST", { action: act.dataset.act }).catch(() => {}); return true; }
  const view = e.target.closest("[data-view]");
  if (!view) return true;
  view.disabled = true;
  try {
    const { phone } = await apiJSON(`/reviews/${r.id}/contact`, "POST", { action: "view" });
    box.outerHTML = contactBox(r, phone);
  } catch (err) { toast(userMessage(err)); view.disabled = false; }
  return true;
}

function bindReviewTable(list) {
  list.addEventListener("click", async (e) => {
    if (await contactClick(e)) return;
    const sendBtn = e.target.closest("[data-send]");
    if (sendBtn) {
      const detail = sendBtn.closest(".cp-detail");
      const body = detail.querySelector("textarea").value.trim();
      if (!body) return toast("Write a reply first");
      if (!confirm("Send this reply to Zomato now? Once it is posted it can't be edited here.")) return;
      sendBtn.disabled = true;
      const label = sendBtn.textContent;
      sendBtn.textContent = "Sending…";
      try {
        const res = await apiJSON(`/reviews/${detail.dataset.detail}/replies`, "POST", { body, send: true, source: body === suggestReply(reviewRows.get(detail.dataset.detail)) ? "template" : "manual" });
        if (!res.sent && !res.queued) throw userError(res.error || "Zomato did not accept the reply");
        const r = { ...reviewRows.get(detail.dataset.detail), latest_reply: body, queued: !!res.queued };
        if (res.sent) r.reply_status = "replied"; else if (r.reply_status === "pending") r.reply_status = "drafted";
        reviewRows.set(String(r.id), r);
        list.querySelector(`.cp-row[data-id="${r.id}"]`).outerHTML = reviewTableRow(r);
        detail.outerHTML = reviewDetail(r);
        toast(res.sent ? "Posted to Zomato" : "Queued: it will be posted to Zomato shortly");
      } catch (err) { toast(userMessage(err)); sendBtn.disabled = false; sendBtn.textContent = label; }
      return;
    }
    const btn = e.target.closest("[data-reply]");
    if (btn) {
      const detail = btn.closest(".cp-detail");
      const body = detail.querySelector("textarea").value.trim();
      if (!body) return toast("Write a reply first");
      btn.disabled = true;
      try {
        await apiJSON(`/reviews/${detail.dataset.detail}/replies`, "POST", { body, source: body === suggestReply(reviewRows.get(detail.dataset.detail)) ? "template" : "manual" });
        const r = { ...reviewRows.get(detail.dataset.detail), latest_reply: body };
        if (r.reply_status === "pending") r.reply_status = "drafted";
        reviewRows.set(String(r.id), r);
        list.querySelector(`.cp-row[data-id="${r.id}"]`).outerHTML = reviewTableRow(r);
        detail.outerHTML = reviewDetail(r);
        toast("Draft saved");
      } catch (err) { toast(userMessage(err)); btn.disabled = false; }
      return;
    }
    const row = e.target.closest(".cp-row");
    if (!row) return;
    const open = list.querySelector(`[data-detail="${row.dataset.id}"]`);
    if (open) open.remove();
    else row.insertAdjacentHTML("afterend", reviewDetail(reviewRows.get(row.dataset.id)));
  });
}

function reviewRow(r) {
  return `<div class="review" data-id="${r.id}">
    <div class="review-head">
      <span class="review-author">${esc(r.author_name || "Anonymous")}</span>${stars(r.rating)}${platformPill(r.platform)}
      <span class="status ${r.reply_status}">${r.reply_status}</span>
      <span class="review-meta">${esc(r.outlet_name)} · ${timeAgo(r.reviewed_at)}</span>
    </div>
    <div class="review-body ${r.body ? "" : "empty"}">${r.body ? esc(r.body) : "Rating only, no text"}</div>
    ${r.latest_reply ? `<div class="latest-reply">${esc(r.latest_reply)}</div>` : ""}
    ${r.reply_status === "replied" ? "" : `<div class="reply-box"><textarea rows="1" placeholder="Write a reply…"></textarea><button class="btn blue" data-save>Save draft</button></div>`}
  </div>`;
}

function bindReplyBoxes(root) {
  root.querySelectorAll("[data-save]").forEach((btn) => btn.addEventListener("click", async () => {
    const card = btn.closest(".review");
    const body = card.querySelector("textarea").value.trim();
    if (!body) return toast("Write a reply first");
    btn.disabled = true;
    try {
      await api(`/reviews/${card.dataset.id}/replies`, {}, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ body }) });
      card.querySelector(".status").className = "status drafted";
      card.querySelector(".status").textContent = "drafted";
      card.querySelector(".reply-box").insertAdjacentHTML("beforebegin", `<div class="latest-reply">${esc(body)}</div>`);
      card.querySelector("textarea").value = "";
      toast("Draft saved");
    } catch (e) { toast(userMessage(e)); }
    btn.disabled = false;
  }));
}

// ---------- complaints: order complaints from Zomato / Swiggy, tracked as tickets ----------
const complaintFilters = { status: "", issue: "", q: "", offset: 0 };
const ISSUE_LABELS = { missing_items: "Missing items", wrong_items: "Wrong items", quality: "Quality", quantity: "Quantity",
  packaging: "Packaging / spillage", other: "Other" };
const TICKET_STATUS = [["open", "Open"], ["in_progress", "In progress"], ["resolved", "Resolved"]];
let complaintRows = new Map();
const complaintUi = { listOpen: false, outletsAll: false };
const EXPIRING_LABEL = "6 hours";

// ---------- connected highlight: click an item and everything linked to it lights up, with lines between the dots ----------
// cfg = { sel: {type, key}, types: [the kinds of clickable item, each marked data-<type>], labelOf(type, key), noRead: [types without a "Read them"] }
const complaintSel = { type: "", key: "" }, reviewSel = { type: "", key: "" };
function linkEls(page, type) { return [...page.querySelectorAll(`[data-${type}]`)].filter((el) => el.offsetParent !== null && el.tagName !== "TR"); }
function applySelection(page, s, cfg) {
  const sel = cfg.sel;
  page.querySelectorAll(".lk-n").forEach((n) => n.remove());
  page.querySelectorAll(".lk-rel, .lk-sel").forEach((el) => el.classList.remove("lk-rel", "lk-sel"));
  page.classList.toggle("lk-on", !!sel.type);
  page.querySelector("#lkSvg")?.remove(); page.querySelector("#lkBar")?.remove();
  cfg.types.forEach((t) => linkEls(page, t).forEach((el) => el.classList.add("lk")));
  if (!sel.type) return;
  const { type, key } = sel;
  const rows = (s.links || []).filter((l) => String(l[type]) === String(key));
  const total = rows.reduce((t, l) => t + l.n, 0);
  const weight = {};
  cfg.types.filter((t) => t !== type).forEach((t) => {
    weight[t] = new Map();
    rows.forEach((l) => { const k = String(l[t]); if (k !== "") weight[t].set(k, (weight[t].get(k) || 0) + l.n); });
  });
  const selEl = linkEls(page, type).find((el) => el.dataset[type] === String(key));
  if (selEl) selEl.classList.add("lk-sel");
  const targets = [];
  Object.keys(weight).forEach((t) => linkEls(page, t).forEach((el) => {
    const n = weight[t].get(el.dataset[t]);
    if (!n) return;
    el.classList.add("lk-rel");
    el.insertAdjacentHTML("beforeend", `<span class="lk-n">${inr.format(n)}</span>`);
    targets.push({ el, n });
  }));
  page.insertAdjacentHTML("afterbegin", `<div id="lkBar" class="lk-bar"><span><b>${esc(cfg.labelOf(type, key))}</b> · ${inr.format(total)} ${cfg.noun || "item"}${total === 1 ? "" : "s"} linked</span>
    ${(cfg.noRead || []).includes(type) ? "" : '<button type="button" class="btn blue" id="lkRead">Read them</button>'}<button type="button" class="btn light" id="lkClear">Clear</button></div>`);
  if (!selEl || !targets.length) return;
  requestAnimationFrame(() => drawLinks(page, selEl, targets));
}
// one click handler per page render: selects/clears the highlight, and "Read them" hands the selection to the page
function bindLinks(page, s, cfg, readThem, holder) {
  const marker = page.querySelector("#lkMarker");  // the handler lives only as long as this render, and never acts on another page
  const sel = cfg.sel;
  const onClick = (e) => {
    if (!marker || !marker.isConnected) return;
    if (e.target.closest("#lkClear")) { sel.type = ""; sel.key = ""; applySelection(page, s, cfg); return; }
    if (e.target.closest("#lkRead")) { const { type, key } = sel; sel.type = ""; sel.key = ""; readThem(type, key); return; }
    if (e.target.closest("#lkBar") || e.target.closest("#complaintList") || e.target.closest("#reviewList")) return;
    const el = e.target.closest(cfg.types.map((t) => `[data-${t}]`).join(", "));
    if (!el || !page.contains(el) || el.tagName === "TR") return;
    const type = cfg.types.find((t) => el.dataset[t] != null);
    sel.type = sel.key === String(el.dataset[type]) && sel.type === type ? "" : type;
    sel.key = sel.type ? String(el.dataset[type]) : "";
    applySelection(page, s, cfg);
  };
  if (holder.click) page.removeEventListener("click", holder.click);
  holder.click = onClick; page.addEventListener("click", onClick);
  if (holder.resize) window.removeEventListener("resize", holder.resize);
  holder.resize = () => { if (sel.type && marker.isConnected) applySelection(page, s, cfg); };
  window.addEventListener("resize", holder.resize);
  requestAnimationFrame(() => requestAnimationFrame(() => applySelection(page, s, cfg)));
}
const complaintLinks = {}, reviewLinks = {};
function drawLinks(page, selEl, targets) {
  page.querySelector("#lkSvg")?.remove();
  const base = page.getBoundingClientRect(), NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.id = "lkSvg"; svg.setAttribute("class", "lk-svg"); svg.setAttribute("width", page.scrollWidth); svg.setAttribute("height", page.scrollHeight);
  const box = (el) => { const r = el.getBoundingClientRect(); return { l: r.left - base.left, r: r.right - base.left, t: r.top - base.top, b: r.bottom - base.top, cx: (r.left + r.right) / 2 - base.left, cy: (r.top + r.bottom) / 2 - base.top }; };
  const a = box(selEl), max = Math.max(...targets.map((t) => t.n));
  targets.forEach(({ el, n }, i) => {
    const z = box(el); let d, p1, p2;
    if (z.t >= a.b - 4) { p1 = [a.cx, a.b]; p2 = [z.cx, z.t]; const m = (p1[1] + p2[1]) / 2; d = `M${p1[0]} ${p1[1]} C${p1[0]} ${m},${p2[0]} ${m},${p2[0]} ${p2[1]}`; }
    else if (z.b <= a.t + 4) { p1 = [a.cx, a.t]; p2 = [z.cx, z.b]; const m = (p1[1] + p2[1]) / 2; d = `M${p1[0]} ${p1[1]} C${p1[0]} ${m},${p2[0]} ${m},${p2[0]} ${p2[1]}`; }
    else { const right = z.cx > a.cx; p1 = [right ? a.r : a.l, a.cy]; p2 = [right ? z.l : z.r, z.cy]; const m = (p1[0] + p2[0]) / 2; d = `M${p1[0]} ${p1[1]} C${m} ${p1[1]},${m} ${p2[1] === p1[1] ? p2[1] : p2[1]},${p2[0]} ${p2[1]}`; }
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", d); path.setAttribute("class", "lk-path"); path.setAttribute("stroke-width", (1.5 + 3 * (n / max)).toFixed(1));
    svg.appendChild(path);
    const len = path.getTotalLength(); path.style.strokeDasharray = len; path.style.strokeDashoffset = len; path.style.animationDelay = `${i * 60}ms`;
    [p1, p2].forEach((pt, k) => { const c = document.createElementNS(NS, "circle"); c.setAttribute("cx", pt[0]); c.setAttribute("cy", pt[1]); c.setAttribute("r", 4.5); c.setAttribute("class", "lk-dot"); c.style.animationDelay = `${i * 60 + (k ? 450 : 0)}ms`; svg.appendChild(c); });
  });
  page.appendChild(svg);
}

async function renderComplaints(page) {
  const s = await api(`/brands/${state.brandId}/complaints/summary`, filterParams());
  const names = new Map(state.locations.map((l) => [l.id, l.name]));
  const short = (n) => n.split(" · ").slice(1).join(" · ") || n;
  const pct = (n) => (s.total ? `${Math.round((n / s.total) * 100)}%` : "—");
  const maxIssue = Math.max(1, ...s.by_issue.map((r) => r.count));
  const maxOutlet = Math.max(1, ...s.by_outlet.map((r) => r.count));
  const meter = (n, max) => `<span class="cp-meter"><i style="width:${(n / max) * 100}%"></i></span>`;
  const stat = statTile;
  const attentionItems = s.by_outlet.slice(0, 4).map((r) => ({ id: r.outlet_id, name: short(names.get(r.outlet_id) || `Outlet ${r.outlet_id}`), full: names.get(r.outlet_id) || "",
    sub: `${inr.format(r.count)} complaint${r.count === 1 ? "" : "s"}`, value: r.open ? `${inr.format(r.open)} open` : "none open", tone: r.open ? "bad" : "",
    pct: (r.count / maxOutlet) * 100, barColor: r.open ? "#dc2626" : "#cbd5e1", pills: r.refunds ? [{ text: `${rupees(r.refunds)} refunds`, tone: "warn" }] : [] }));
  const issueColor = new Map(s.by_issue.map((r, i) => [r.issue_type, DONUT_COLORS[i % DONUT_COLORS.length]]));
  const issueName = (t) => ISSUE_LABELS[t] || t;
  const topIssue = s.by_issue[0], topDish = s.by_item?.[0], span = Math.max(1, Math.round((new Date(range().end) - new Date(range().start)) / 864e5) + 1);
  const change = s.previous_total ? Math.round(((s.total - s.previous_total) / s.previous_total) * 100) : null;
  const rep = s.repeat || { repeat: 0, first: 0 }, repPct = rep.repeat + rep.first ? Math.round((rep.repeat / (rep.repeat + rep.first)) * 100) : null;
  const glance = s.total ? `<div class="card cp-card dn-glance">
    <div class="dn-gline"><b>${inr.format(s.total)} complaint${s.total === 1 ? "" : "s"}</b> in the last ${span} day${span === 1 ? "" : "s"}${change == null ? "" : `, <span class="${change > 0 ? "up" : "down"}">${change > 0 ? "up" : "down"} ${Math.abs(change)}%</span> on the period before`}.
      ${topIssue ? ` Mostly <b>${esc(issueName(topIssue.issue_type).toLowerCase())}</b> (${Math.round((topIssue.count / s.total) * 100)}%)` : ""}${topDish ? `, and <b>${esc(topDish.dish)}</b> is the dish people mention most (${inr.format(topDish.count)}).` : "."}</div>
    <div class="dn-gfacts">${s.expiring ? `<span class="bad">${inr.format(s.expiring)} must be answered within ${EXPIRING_LABEL}</span>` : ""}${s.open ? `<span class="warn">${inr.format(s.open)} still open</span>` : `<span class="ok">Nothing open</span>`}${s.refunds ? `<span>${rupees(s.refunds)} refunded</span>` : ""}${repPct != null ? `<span>${repPct}% from repeat customers</span>` : ""}</div></div>` : "";
  const maxDish = Math.max(1, ...(s.by_item || []).map((r) => r.count));
  const dishes = s.by_item?.length ? `<div class="card cp-card dn-dishes"><div class="cp-head"><h3>Dishes behind the complaints</h3><span class="muted">click a dish to read its complaints</span></div>
    ${s.by_item.map((r) => `<button type="button" class="dn-dish ${complaintFilters.q === r.dish ? "on" : ""}" data-dish="${esc(r.dish)}">
      <span class="dn-dname" title="${esc(r.dish)}">${esc(r.dish)}</span>
      <i class="dn-dbar"><u style="width:${Math.max(4, Math.round((r.count / maxDish) * 100))}%;background:${issueColor.get(r.issues[0]?.issue_type) || "#94a3b8"}"></u></i>
      <b>${inr.format(r.count)}</b><em>${esc(r.issues.slice(0, 2).map((x) => issueName(x.issue_type)).join(", "))}</em></button>`).join("")}</div>` : "";
  const reasons = s.by_reason?.length ? `<div class="card cp-card dn-reasons"><div class="cp-head"><h3>What exactly went wrong</h3><span class="muted">click to read them</span></div>
    <div class="dn-chips">${s.by_reason.map((r) => `<button type="button" class="dn-chip ${complaintFilters.q === r.reason ? "on" : ""}" data-reason="${esc(r.reason)}">${esc(r.reason)} <b>${inr.format(r.count)}</b></button>`).join("")}</div></div>` : "";
  const whoDonut = donutCard("who", "Who complains", "repeat customers are your regulars", [{ key: "repeat", label: "Repeat customers", color: "#f59e0b", count: rep.repeat }, { key: "first", label: "First-time customers", color: "#0a84ff", count: rep.first }], "customers");
  const issueDonut = donutCard("issue", "By issue", "click a slice to filter", s.by_issue.map((r, i) => ({ key: r.issue_type, label: ISSUE_LABELS[r.issue_type] || r.issue_type, color: DONUT_COLORS[i % DONUT_COLORS.length],
    count: r.count, on: complaintFilters.issue === r.issue_type, attr: `data-issue="${esc(r.issue_type)}"`, sub: r.refunds ? `${rupees(r.refunds)} refunds` : "" })), "complaints");
  const statusDonut = donutCard("status", "By ticket status", "click a slice to filter", [["open", "Open", "#dc2626", s.open], ["in_progress", "In progress", "#f59e0b", s.in_progress], ["resolved", "Resolved", "#16a34a", s.resolved]]
    .map(([key, label, color, count]) => ({ key, label, color, count, on: complaintFilters.status === key, attr: `data-status="${key}"` })), "complaints");
  STAT_PCT = s.total ? { "Open": (s.open / s.total) * 100, "In progress": (s.in_progress / s.total) * 100, "Resolved": (s.resolved / s.total) * 100 } : {};
  const showList = complaintUi.listOpen || complaintFilters.issue || complaintFilters.status || complaintFilters.q;  // the list stays out of the way until a slice is clicked
  page.innerHTML = `
    <i id="lkMarker" hidden></i>
    ${glance}
    <div class="card cp-stats">
      ${stat("Complaints", inr.format(s.total))}${stat("Open", inr.format(s.open), s.open ? "warn" : "")}
      ${stat("In progress", inr.format(s.in_progress))}${stat("Resolved", inr.format(s.resolved), "ok")}
      ${stat("Refunds", rupees(s.refunds))}
      ${stat("Expiring ≤6h", inr.format(s.expiring), s.expiring ? "bad" : "")}
    </div>
    ${s.total ? `<div class="dn-rings">${issueDonut.html}${statusDonut.html}${rep.repeat + rep.first ? whoDonut.html : ""}</div>
    <div class="dn-pair">${dishes}${reasons}</div>
    ${attentionCard({ hint: "most complaints first · click to filter", total: s.by_outlet.length, allKey: "outletsAll", showAll: complaintUi.outletsAll, items: attentionItems,
      tableHtml: `        <div class="cp-scroll"><table class="cp-table"><thead><tr><th>Outlet</th><th class="num">#</th><th class="num">Open</th><th></th><th class="num">Refunds</th></tr></thead><tbody>
        ${s.by_outlet.map((r) => `<tr class="cp-click" data-outlet="${r.outlet_id}">
          <td title="${esc(names.get(r.outlet_id) || "")}">${esc(short(names.get(r.outlet_id) || `Outlet ${r.outlet_id}`))}</td>
          <td class="num"><b>${inr.format(r.count)}</b></td><td class="num ${r.open ? "cp-warn" : "muted"}">${inr.format(r.open)}</td>
          <td class="cp-mcell">${meter(r.count, maxOutlet)}</td><td class="num">${rupees(r.refunds)}</td></tr>`).join("")}
        </tbody></table></div>` })}` : ""}
    ${showList ? `    <div class="card cp-card">
      <div class="toolbar cp-toolbar">
        <input id="cq" type="search" placeholder="Search order id, item, customer…" value="${esc(complaintFilters.q)}">
        <select id="cStatus"><option value="">Any status</option>${TICKET_STATUS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>
        ${complaintFilters.issue ? `<button class="btn light" id="cClear">${esc(ISSUE_LABELS[complaintFilters.issue] || complaintFilters.issue)} ✕</button>` : ""}
        <span class="muted">click a row for details and notes</span>
        <button class="btn light" id="closeList" style="margin-left:auto">Hide list ✕</button>
      </div>
      <div class="table-wrap"><table class="cp-table cp-list"><thead><tr>
        <th>Raised</th><th>Outlet</th><th></th><th>Issue</th><th>Items</th><th>Customer</th><th class="num">Refund</th>
        <th>Platform</th><th>Window</th><th>Ticket</th></tr></thead><tbody id="complaintList"></tbody></table></div>
      <div style="text-align:center;margin-top:8px"><button class="btn light" id="cMore">Load more</button></div>
    </div>`
      : `<div class="card cp-card dn-prompt"><span class="muted">Click a slice above to read those complaints.</span> <button class="btn light" id="showAll">Show all complaints</button></div>`}`;
  if (showList) $("#cStatus").value = complaintFilters.status;
  issueDonut.mount(); statusDonut.mount(); whoDonut.mount();
  $("#showAll")?.addEventListener("click", () => { complaintUi.listOpen = true; render(); });
  page.querySelectorAll("[data-more]").forEach((b) => b.addEventListener("click", () => { complaintUi[b.dataset.more] = !complaintUi[b.dataset.more]; render(); }));
  $("#closeList")?.addEventListener("click", () => { Object.assign(complaintFilters, { issue: "", status: "", q: "" }); complaintUi.listOpen = false; render(); });
  page.querySelectorAll("[data-status]").forEach((b) => b.addEventListener("click", () => {
    complaintFilters.status = complaintFilters.status === b.dataset.status ? "" : b.dataset.status; render();
  }));
  let timer;
  $("#cq")?.addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { complaintFilters.q = e.target.value; loadComplaints(true); }, 300); });
  $("#cStatus")?.addEventListener("change", (e) => { complaintFilters.status = e.target.value; loadComplaints(true); });
  $("#cClear")?.addEventListener("click", () => { complaintFilters.issue = ""; render(); });
  const cfg = { sel: complaintSel, types: ["dish", "issue", "outlet", "reason"], noun: "complaint",
    labelOf: (t, k) => (t === "outlet" ? names.get(Number(k)) || `Outlet ${k}` : t === "issue" ? ISSUE_LABELS[k] || k : k) };
  bindLinks(page, s, cfg, (type, key) => {  // "Read them": open the real complaints behind the highlight
    if (type === "issue") complaintFilters.issue = key; else if (type === "outlet") { state.locationId = key; showSelectedOutlet(); } else complaintFilters.q = key;
    complaintUi.listOpen = true; render();
  }, complaintLinks);
  if (!showList) return;
  $("#cMore").addEventListener("click", () => loadComplaints(false));
  bindComplaints($("#complaintList"));
  await loadComplaints(true);
}

async function loadComplaints(reset) {
  if (reset) { complaintFilters.offset = 0; complaintRows = new Map(); }
  const rows = await api(`/brands/${state.brandId}/complaints`, filterParams({
    status: complaintFilters.status, issue_type: complaintFilters.issue, q: complaintFilters.q, limit: 50, offset: complaintFilters.offset,
  }));
  complaintFilters.offset += rows.length;
  rows.forEach((c) => complaintRows.set(String(c.id), c));
  const list = $("#complaintList");
  const html = rows.map(complaintRow).join("");
  if (reset) list.innerHTML = html || `<tr><td colspan="10" class="muted" style="text-align:center;padding:24px">No complaints match these filters</td></tr>`;
  else list.insertAdjacentHTML("beforeend", html);
  $("#cMore").style.display = rows.length < 50 ? "none" : "";
}

function complaintWindow(c) {
  if (!c.expires_at || c.status === "resolved") return `<span class="muted">—</span>`;
  const left = (new Date(c.expires_at) - Date.now()) / 3600000;
  if (left <= 0) return `<span class="muted">closed</span>`;
  return `<span class="${left <= 6 ? "cp-bad" : "cp-warn"}">${left < 1 ? `${Math.round(left * 60)}m` : `${Math.round(left)}h`} left</span>`;
}

function complaintRow(c) {
  const canEdit = Boolean(state.me?.can_edit);
  const outlet = c.outlet_name.split(" · ").slice(1).join(" · ") || c.outlet_name;
  const ticket = canEdit
    ? `<select class="cp-status cp-${c.status}" data-status>${TICKET_STATUS.map(([v, l]) => `<option value="${v}" ${v === c.status ? "selected" : ""}>${l}</option>`).join("")}</select>`
    : `<span class="status cp-${c.status}">${esc(TICKET_STATUS.find(([v]) => v === c.status)?.[1] || c.status)}</span>`;
  return `<tr class="cp-row" data-id="${c.id}">
    <td class="nowrap" title="${esc(new Date(c.raised_at).toLocaleString("en-IN"))}">${timeAgo(c.raised_at)}</td>
    <td class="cp-ellip" title="${esc(c.outlet_name)}">${esc(outlet)}</td>
    <td><img class="pill-icon" src="assets/${esc(c.platform)}.png" alt="${esc(c.platform)}" title="${esc(c.platform)}"></td>
    <td class="nowrap">${esc(ISSUE_LABELS[c.issue_type] || c.issue_type || "—")}${c.note ? ' <span title="Has a note">📝</span>' : ""}</td>
    <td class="cp-ellip" title="${esc(c.items)}">${esc(c.items || "—")}</td>
    <td class="cp-ellip" title="${esc(c.customer_context)}">${esc(c.customer_name || "—")}</td>
    <td class="num">${c.refund_amount != null ? rupees(c.refund_amount) : "—"}</td>
    <td class="cp-ellip muted" title="${esc(c.resolution)}">${esc(c.platform_status || "—")}</td>
    <td class="nowrap">${complaintWindow(c)}</td>
    <td>${ticket}</td></tr>`;
}

function complaintDetail(c) {
  const canEdit = Boolean(state.me?.can_edit);
  const kv = (k, v) => (v ? `<div><span>${k}</span>${esc(v)}</div>` : "");
  return `<tr class="cp-detail" data-detail="${c.id}"><td colspan="10"><div class="cp-kv">
      ${kv("Order", c.order_id)}${kv("Complaint", c.issue_detail)}${kv("Items", c.items)}
      ${kv("Customer", [c.customer_name, c.customer_context].filter(Boolean).join(" · "))}
      ${kv("Platform", [c.platform_status, c.resolution].filter(Boolean).join(" · "))}${kv("Assigned to", c.assigned_to)}
      ${kv("Note", c.note)}</div>
    ${canEdit ? `<div class="reply-box"><textarea rows="1" placeholder="Note: what was done about it…"></textarea>
      <button class="btn blue" data-note>Save note</button></div>` : ""}</td></tr>`;
}

function bindComplaints(list) {
  const save = async (id, body) => {
    try {
      const c = await apiJSON(`/complaints/${id}`, "PATCH", body);
      complaintRows.set(String(c.id), c);
      const open = list.querySelector(`[data-detail="${c.id}"]`);
      list.querySelector(`.cp-row[data-id="${c.id}"]`).outerHTML = complaintRow(c);
      if (open) open.outerHTML = complaintDetail(c);
      toast("Saved");
    } catch (e) { toast(userMessage(e)); }
  };
  list.addEventListener("change", (e) => {
    const sel = e.target.closest("[data-status]");
    if (sel) save(sel.closest(".cp-row").dataset.id, { status: sel.value });
  });
  list.addEventListener("click", (e) => {
    if (e.target.closest("select")) return;
    const noteBtn = e.target.closest("[data-note]");
    if (noteBtn) {
      const note = noteBtn.closest(".cp-detail").querySelector("textarea").value.trim();
      if (!note) return toast("Write a note first");
      return save(noteBtn.closest(".cp-detail").dataset.detail, { note });
    }
    const row = e.target.closest(".cp-row");
    if (!row) return;
    const open = list.querySelector(`[data-detail="${row.dataset.id}"]`);
    if (open) open.remove();
    else row.insertAdjacentHTML("afterend", complaintDetail(complaintRows.get(row.dataset.id)));
  });
}

// ---------- item scorecard: every menu item's sales, stock-outs, complaints and ratings ----------
const itemView = { flagged: true, q: "", sort: "", dir: -1 };
let itemData = null;
const ITEM_COLS = [
  ["name", "Item", ""], ["revenue", "Sales", "num"], ["orders", "Orders", "num"], ["complaints", "Complaints", "num"],
  ["complaint_rate", "Per 100 orders", "num"], ["refunds", "Refunds", "num"], ["stockout_hours", "Hours out", "num"],
  ["stockout_loss", "Stock-out ₹", "num"], ["avg_item_rating", "Item ★", "num"], ["money_lost", "₹ lost", "num"],
];

async function renderItems(page) {
  itemData = await api(`/brands/${state.brandId}/items`, filterParams());
  const t = itemData.totals;
  const stat = statTile;
  page.innerHTML = `
    <div class="card cp-stats">
      ${stat("Items sold", inr.format(t.items))}${stat("Item sales", compactINR(t.revenue))}
      ${stat("Need action", inr.format(t.flagged), t.flagged ? "bad" : "")}${stat("₹ lost on items", rupees(t.money_lost), t.money_lost ? "warn" : "")}
      ${stat("Complaints / 100 orders", itemData.avg_complaint_rate.toFixed(2))}
    </div>
    <div class="card cp-card">
      <div class="toolbar cp-toolbar">
        <input id="iq" type="search" placeholder="Search item or category…" value="${esc(itemView.q)}">
        <div class="segmented" id="iFlag">${[[true, `Needs action (${t.flagged})`], [false, `All items (${itemData.items.length})`]]
          .map(([v, l]) => `<button data-v="${v}" class="${itemView.flagged === v ? "active" : ""}">${l}</button>`).join("")}</div>
        <span class="muted">₹ lost = refunds + the low end of sales missed on stock-outs · click a row for details</span>
      </div>
      <div class="table-wrap"><table class="cp-table cp-list"><thead><tr>
        ${ITEM_COLS.map(([k, l, cls]) => `<th class="${cls} it-sort" data-sort="${k}">${l}${itemView.sort === k ? (itemView.dir < 0 ? " ▾" : " ▴") : ""}</th>`).join("")}
      </tr></thead><tbody id="itemList"></tbody></table></div>
    </div>`;
  let timer;
  $("#iq").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { itemView.q = e.target.value; drawItems(); }, 200); });
  page.querySelectorAll("#iFlag button").forEach((b) => b.addEventListener("click", () => { itemView.flagged = b.dataset.v === "true"; renderItems(page); }));
  page.querySelectorAll(".it-sort").forEach((th) => th.addEventListener("click", () => {
    itemView.dir = itemView.sort === th.dataset.sort ? -itemView.dir : -1; itemView.sort = th.dataset.sort; renderItems(page);
  }));
  $("#itemList").addEventListener("click", (e) => {
    const row = e.target.closest(".cp-row");
    if (!row) return;
    const open = row.nextElementSibling?.classList.contains("cp-detail") ? row.nextElementSibling : null;
    if (open) open.remove();
    else row.insertAdjacentHTML("afterend", itemDetail(itemData.items[Number(row.dataset.i)]));
  });
  drawItems();
}

function drawItems() {
  const q = itemView.q.trim().toLowerCase();
  let rows = itemData.items.map((r, i) => ({ ...r, i }))
    .filter((r) => (!itemView.flagged || r.flags.length) && (!q || r.name.toLowerCase().includes(q) || (r.category || "").toLowerCase().includes(q)));
  if (itemView.sort) {
    const k = itemView.sort;
    rows.sort((a, b) => (k === "name" ? a.name.localeCompare(b.name) : (a[k] ?? -1) - (b[k] ?? -1)) * itemView.dir);
  }
  const avg = itemData.avg_complaint_rate;
  const dash = '<span class="muted">—</span>';
  $("#itemList").innerHTML = rows.map((r) => `<tr class="cp-row ${r.flags.length ? "it-flag" : ""}" data-i="${r.i}">
      <td class="it-name" title="${esc(r.flags.join(" · "))}"><b>${esc(r.name)}</b><small>${esc(r.category || "")}${r.outlets ? ` · ${r.outlets} outlets` : ""}</small></td>
      <td class="num">${r.revenue ? compactINR(r.revenue) : dash}</td><td class="num">${r.orders ? inr.format(r.orders) : dash}</td>
      <td class="num">${r.complaints || dash}</td>
      <td class="num ${r.complaints >= 5 && r.complaint_rate >= 2 * avg ? "cp-bad" : ""}">${r.orders && r.complaints ? r.complaint_rate.toFixed(1) : dash}</td>
      <td class="num">${r.refunds ? rupees(r.refunds) : dash}</td>
      <td class="num">${r.stockout_hours ? inr.format(Math.round(r.stockout_hours)) : dash}</td>
      <td class="num">${r.stockout_loss_high ? `${rupeesShort(r.stockout_loss)} – ${rupeesShort(r.stockout_loss_high)}` : dash}</td>
      <td class="num ${r.avg_item_rating != null && r.avg_item_rating < 3.5 ? "cp-bad" : ""}">${r.avg_item_rating != null ? `${r.avg_item_rating.toFixed(1)} <small class="muted">(${r.rated})</small>` : dash}</td>
      <td class="num"><b>${r.money_lost ? rupees(r.money_lost) : dash}</b></td></tr>`).join("")
    || `<tr><td colspan="${ITEM_COLS.length}" class="muted" style="text-align:center;padding:24px">${itemView.flagged ? "No item needs action in this period 🎉" : "No item data for this filter"}</td></tr>`;
}

function itemDetail(r) {
  const issues = Object.entries(r.issues || {}).sort((a, b) => b[1] - a[1])
    .map(([k, n]) => `${esc(ISSUE_LABELS[k] || k)} <b>${n}</b>`).join(" · ");
  return `<tr class="cp-detail"><td colspan="${ITEM_COLS.length}">
    ${r.flags.length ? `<ul class="it-flags">${r.flags.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : '<p class="muted" style="margin:0 0 6px">No problems flagged.</p>'}
    <div class="cp-kv">
      <div><span>Units sold</span>${inr.format(Math.round(r.units))}${r.units ? ` · avg ${rupees(r.revenue / r.units)} each` : ""}</div>
      ${issues ? `<div><span>Complaints by issue</span>${issues}</div>` : ""}
      <div><span>Stock-outs</span>${r.stockouts ? `${r.stockouts === 1 ? "once" : `${r.stockouts} times`} · ${inr.format(Math.round(r.stockout_hours))} h out in total${SHOW_STOCK_LOSS ? ` · ${rupees(r.stockout_loss)} missed` : ""}` : "none"}</div>
      <div><span>Item ratings</span>${r.rated ? `${r.rated} ratings · ${r.bad_review_pct}% are 1–2★` : "none in this period"}</div>
    </div></td></tr>`;
}

// ---------- listings: profile health + Google performance ----------
async function renderListings(page) {
  const rows = await api(`/brands/${state.brandId}/listings`, { outlet_id: state.locationId, platform: state.platform });
  const avg = rows.length ? Math.round(rows.reduce((n, r) => n + r.health_score, 0) / rows.length) : null;
  const tone = (n) => (n >= 80 ? "ok" : n >= 60 ? "mid" : "bad");
  page.innerHTML = `
    ${rows.length ? `<div class="card lp-card">
      <div class="card-head"><h3>Listing health</h3><span class="muted">${rows.length} listing${rows.length === 1 ? "" : "s"} · average <b>${avg}/100</b></span></div>
      <div class="lp-grid">${rows.map((r) => `<div class="lp">
        <div class="lp-ring ${tone(r.health_score)}" style="--p:${r.health_score}"><b>${r.health_score}</b></div>
        <div class="lp-body">
          <div class="lp-title">${platformPill(r.platform)} <b>${esc(r.outlet_name)}</b></div>
          <div class="lp-facts muted">${esc(r.category || "No category")} · ${r.photo_count} photo${r.photo_count === 1 ? "" : "s"} ·
            ${r.last_post_at ? `last post ${timeAgo(r.last_post_at)}` : "no posts"}${r.open_status && r.open_status !== "OPEN" ? ` · <span class="bad-text">${esc(r.open_status.replace(/_/g, " ").toLowerCase())}</span>` : ""}</div>
          ${r.issues.length ? `<ul class="lp-issues">${r.issues.map((i) => `<li>${esc(i.label)}</li>`).join("")}</ul>` : `<div class="lp-good">✓ Nothing to fix</div>`}
        </div></div>`).join("")}</div></div>` : ""}
    <div id="lpKpis"></div>`;
  await renderModule($("#lpKpis"), "listings");
}

// ---------- alerts ----------
const alertFilters = { status: "open" };
const ALERT_ICON = { critical: "!", warning: "!", info: "i" };

async function renderAlerts(page) {
  const rows = await api(`/brands/${state.brandId}/alerts`, { outlet_id: state.locationId, status: alertFilters.status === "all" ? "all" : alertFilters.status });
  const open = rows.filter((r) => r.is_open);
  const count = (sev) => open.filter((r) => r.severity === sev).length;
  page.innerHTML = `
    <div class="stat-strip">
      <div class="card kpi"><span class="kpi-label">Critical</span><div class="kpi-value bad-text">${count("critical")}</div></div>
      <div class="card kpi"><span class="kpi-label">Warnings</span><div class="kpi-value amber-text">${count("warning")}</div></div>
      <div class="card kpi"><span class="kpi-label">Open alerts</span><div class="kpi-value">${open.length}</div></div>
    </div>
    <div class="card">
      <div class="toolbar"><div class="segmented" id="alStatus">${[["open", "Open"], ["resolved", "Resolved"], ["all", "All"]]
        .map(([v, l]) => `<button data-v="${v}" class="${alertFilters.status === v ? "active" : ""}">${l}</button>`).join("")}</div>
        <span class="muted">Checked automatically against reviews, Google performance, listing health, stock-outs and store uptime</span></div>
      ${rows.length ? rows.map((a) => `<div class="alert-row ${a.is_open ? a.severity : "done"}">
        <span class="alert-dot">${a.is_open ? ALERT_ICON[a.severity] : "✓"}</span>
        <div class="alert-main"><b>${esc(a.title)}</b><small>${esc(a.outlet_name)} · ${esc(a.detail)}</small></div>
        <span class="muted alert-when">${a.is_open ? `since ${timeAgo(a.first_seen_at)}` : `resolved ${timeAgo(a.resolved_at)}`}</span>
      </div>`).join("") : `<div class="empty-state"><h3>${alertFilters.status === "open" ? "All clear" : "Nothing here"}</h3><p>${alertFilters.status === "open" ? "No open alerts right now." : ""}</p></div>`}
    </div>`;
  $("#alStatus").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    alertFilters.status = b.dataset.v; renderAlerts(page);
  });
}

// ---------- billing: plans, checkout, invoices ----------
const billingView = { cycle: "monthly", choosing: null, outlets: null };
const PLAN_STATUS = { trial: "Trial", active: "Active", past_due: "Payment overdue", cancelled: "Cancelled" };

function renderLocked(page, module) {
  page.innerHTML = `<div class="card empty-state">${icon("lock")}
    <h3>${esc(module.name)} isn't in your plan</h3>
    <p>${state.me.can_manage ? "Upgrade your plan to unlock it. Your data is kept and appears as soon as you do." : "Ask your account owner to upgrade the plan to unlock it."}</p>
    ${state.me.can_manage && state.me.client ? '<div class="btn-row" style="justify-content:center;margin-top:14px"><a class="btn blue" href="#/billing">See plans</a></div>' : ""}</div>`;
}

async function renderBilling(page, clientId) {
  const [plans, b] = await Promise.all([api("/billing/plans"), api(`/clients/${clientId}/billing`)]);
  const sub = b.subscription;
  $("#pageTitle").textContent = "Billing";
  $("#pageSub").textContent = state.me.is_staff ? `Plan and invoices for ${b.client.name}` : "Your plan, usage and invoices";
  if (billingView.outlets == null) billingView.outlets = Math.max(1, b.usage.outlets);
  const overLimit = sub?.outlet_limit != null && b.usage.outlets > sub.outlet_limit;
  const yearly = billingView.cycle === "annual";
  const priceLine = (p) => p.price_per_outlet == null ? "<b>Custom</b><small>talk to us</small>"
    : `<b>₹${inr.format(p.price_per_outlet)}</b><small>per outlet / month${yearly && p.annual_free_months ? `, billed yearly (${p.annual_free_months} months free)` : ""}</small>`;
  page.innerHTML = `
    <div class="card billing-current">
      <div class="card-head"><h3>Current plan</h3>${state.me.is_staff ? '<span class="muted">You are viewing this as Codeonto staff</span>' : ""}</div>
      ${sub ? `<div class="profile-details">
          <div class="profile-detail"><span class="muted">Plan</span><strong>${esc(sub.name)}</strong></div>
          <div class="profile-detail"><span class="muted">Status</span><strong class="${sub.status === "active" ? "payout-ok" : sub.status === "trial" && !sub.trial_expired ? "" : "payout-bad"}">${esc(sub.trial_expired ? "Trial ended" : PLAN_STATUS[sub.status])}</strong></div>
          <div class="profile-detail"><span class="muted">${sub.status === "trial" ? "Trial ends" : "Renews"}</span><strong>${(sub.status === "trial" ? sub.trial_ends_on : sub.current_period_end) ? dayLabel(sub.status === "trial" ? sub.trial_ends_on : sub.current_period_end) : "—"}</strong></div>
          <div class="profile-detail"><span class="muted">Billing</span><strong>${sub.cycle === "annual" ? "Yearly" : "Monthly"}</strong></div>
          <div class="profile-detail"><span class="muted">Outlets</span><strong class="${overLimit ? "payout-bad" : ""}">${inr.format(b.usage.outlets)}${sub.outlet_limit != null ? ` of ${inr.format(sub.outlet_limit)}` : ""}</strong></div>
          <div class="profile-detail"><span class="muted">Logins</span><strong>${inr.format(b.usage.logins)}${sub.max_logins ? ` of ${sub.max_logins}` : ""}</strong></div>
        </div>${overLimit ? '<p class="payout-bad" style="margin:12px 0 0">You have more outlets than your plan covers. Choose a plan with enough outlets below.</p>' : ""}`
      : `<p class="muted" style="margin:0">No plan yet: you have full access while your account is set up. ${inr.format(b.usage.outlets)} outlets, ${inr.format(b.usage.logins)} logins.</p>`}
      ${b.requests.length ? `<p class="billing-note">Requested: ${b.requests.map((r) => `${esc(r.plan)} (${r.cycle === "annual" ? "yearly" : "monthly"}, ${r.outlets} outlets)`).join(", ")}. Our team will contact you to activate it.</p>` : ""}
    </div>

    <div class="billing-plans-head">
      <h3>Plans</h3>
      <div class="segmented" id="billingCycle"><button data-c="monthly" class="${yearly ? "" : "active"}">Monthly</button><button data-c="annual" class="${yearly ? "active" : ""}">Yearly</button></div>
    </div>
    <div class="billing-plans">${plans.map((p) => `<div class="card billing-plan ${sub?.plan === p.code ? "current" : ""}">
        <h3>${esc(p.name)}</h3><p class="muted">${esc(p.description)}</p>
        <div class="billing-price">${priceLine(p)}</div>
        <ul>${p.features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
        <button class="btn ${sub?.plan === p.code ? "light" : "blue"}" data-choose="${p.code}">${p.price_per_outlet == null ? "Contact us" : sub?.plan === p.code ? "Renew or change outlets" : "Choose " + esc(p.name)}</button>
      </div>`).join("")}</div>

    <div id="checkout"></div>

    <div class="card" style="margin-top:20px">
      <div class="card-head"><h3>Invoices</h3></div>
      ${b.invoices.length ? `<div class="table-wrap"><table><thead><tr><th>Invoice</th><th>Period</th><th>Amount</th><th>GST</th><th>Total</th><th>Status</th></tr></thead><tbody>
        ${b.invoices.map((i) => `<tr><td>${esc(i.number)}</td><td>${dayLabel(i.period_start)} – ${dayLabel(i.period_end)}</td><td>${rupees(i.subtotal)}</td><td>${rupees(i.gst)}</td>
          <td><b>${rupees(i.total)}</b></td><td>${i.status === "paid" ? `<span class="status replied">Paid ${i.paid_on ? dayLabel(i.paid_on) : ""}</span>` : '<span class="status pending">Due</span>'}</td></tr>`).join("")}</tbody></table></div>`
        : '<p class="muted" style="margin:0">No invoices yet.</p>'}
    </div>
    ${state.me.is_staff ? staffBillingForm(plans, sub) : ""}`;

  $("#billingCycle").addEventListener("click", (e) => {
    const btn = e.target.closest("button"); if (!btn) return;
    billingView.cycle = btn.dataset.c; renderBilling(page, clientId);
  });
  page.querySelectorAll("[data-choose]").forEach((btn) => btn.addEventListener("click", () => {
    billingView.choosing = btn.dataset.choose;
    renderCheckout(plans.find((p) => p.code === btn.dataset.choose), clientId, page);
  }));
  if (billingView.choosing) renderCheckout(plans.find((p) => p.code === billingView.choosing), clientId, page);
  if (state.me.is_staff) wireStaffBilling(page, clientId);
}

async function renderCheckout(plan, clientId, page) {
  const box = $("#checkout");
  if (!plan) { box.innerHTML = ""; return; }
  const q = await api("/billing/quote", { plan: plan.code, cycle: billingView.cycle, outlets: billingView.outlets });
  box.innerHTML = `<div class="card billing-checkout">
    <div class="card-head"><h3>Checkout · ${esc(plan.name)}</h3><button class="btn light" id="checkoutClose">Cancel</button></div>
    <div class="form-row">
      <label>Outlets<input id="checkoutOutlets" type="number" min="1" max="10000" value="${billingView.outlets}"></label>
      <label>Billing<select id="checkoutCycle"><option value="monthly" ${billingView.cycle === "monthly" ? "selected" : ""}>Monthly</option><option value="annual" ${billingView.cycle === "annual" ? "selected" : ""}>Yearly</option></select></label>
    </div>
    ${q.total == null ? '<p class="muted">This plan is priced for you. Send a request and our team will get in touch.</p>' : `<table class="payout-statement billing-quote"><tbody>
      <tr><td>₹${inr.format(q.price_per_outlet)} × ${inr.format(q.outlets)} outlet${q.outlets === 1 ? "" : "s"} × ${q.months_billed} month${q.months_billed === 1 ? "" : "s"}${q.covers_months === 12 ? " (covers 12 months)" : ""}</td><td>${rupees(q.subtotal)}</td></tr>
      <tr><td>GST @ ${q.gst_percent}%</td><td>${rupees(q.gst)}</td></tr>
      <tr class="section total"><td>Total</td><td>${rupees(q.total)}</td></tr></tbody></table>`}
    <p class="billing-note">Online payment is coming soon. For now, this sends your request and our team will contact you to complete payment and activate the plan.</p>
    <button class="btn blue" id="checkoutPay">${q.total == null ? "Send request" : `Pay ${rupees(q.total)}`}</button>
  </div>`;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  $("#checkoutClose").addEventListener("click", () => { billingView.choosing = null; box.innerHTML = ""; });
  $("#checkoutOutlets").addEventListener("change", (e) => { billingView.outlets = Math.max(1, Number(e.target.value) || 1); renderCheckout(plan, clientId, page); });
  $("#checkoutCycle").addEventListener("change", (e) => { billingView.cycle = e.target.value; renderBilling(page, clientId); });
  $("#checkoutPay").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      await apiJSON(`/clients/${clientId}/billing/requests`, "POST", { plan: plan.code, cycle: billingView.cycle, outlets: billingView.outlets });
      billingView.choosing = null;
      toast("Request sent. Our team will contact you to complete payment.");
      renderBilling(page, clientId);
    } catch (err) { toast(userMessage(err)); e.target.disabled = false; }
  });
}

function staffBillingForm(plans, sub) {
  const opt = (v, l, cur) => `<option value="${v}" ${v === cur ? "selected" : ""}>${l}</option>`;
  return `<form class="card" id="staffBilling" style="margin-top:20px">
    <div class="card-head"><h3>Set plan (staff)</h3><span class="muted">Use this after payment is received. Invoices are added in admin.</span></div>
    <div class="form-row">
      <label>Plan<select name="plan">${plans.map((p) => opt(p.code, p.name, sub?.plan)).join("")}</select></label>
      <label>Status<select name="status">${Object.entries(PLAN_STATUS).map(([v, l]) => opt(v, l, sub?.status || "trial")).join("")}</select></label>
      <label>Billing<select name="cycle">${opt("monthly", "Monthly", sub?.cycle || "monthly")}${opt("annual", "Yearly", sub?.cycle)}</select></label>
      <label>Outlets paid for<input name="outlet_limit" type="number" min="0" value="${sub?.outlet_limit ?? ""}" placeholder="No limit"></label>
      <label>Trial ends<input name="trial_ends_on" type="date" value="${sub?.trial_ends_on || ""}"></label>
      <label>Renews on<input name="current_period_end" type="date" value="${sub?.current_period_end || ""}"></label>
    </div>
    <label class="billing-check"><input type="checkbox" name="close_requests" checked> Mark open requests as handled</label>
    <button class="btn blue" type="submit">Save plan</button>
  </form>`;
}

function wireStaffBilling(page, clientId) {
  $("#staffBilling").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    try {
      await apiJSON(`/clients/${clientId}/billing`, "PATCH", { ...f, close_requests: f.close_requests === "on" });
      toast("Plan saved");
      renderBilling(page, clientId);
    } catch (err) { toast(userMessage(err)); }
  });
}

// ---------- payout reconciliation ----------
const payoutFilters = { status: "", q: "", open: null, issue: "", view: "list", basis: "net", aPlatform: "", aLayout: "", detail: false, combinedOpen: false };
const analyticsOpen = new Set();  // statement sections opened in the analytics view
const stmtSel = new Map();  // statement view: "outletId:platform" -> Set of unticked cycle ids
const rupeesShort = (v) => {  // ₹12.6k, ₹3.13 L, ₹1.2 Cr: for tight spaces
  const n = Math.abs(v || 0);
  return `₹${n >= 1e7 ? `${(n / 1e7).toFixed(2)} Cr` : n >= 1e5 ? `${(n / 1e5).toFixed(2)} L` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : Math.round(n)}`;
};
const rupees = (v) => (v == null ? "—" : `${v < 0 && Math.round(Math.abs(v)) ? "-" : ""}₹${inr.format(Math.abs(v))}`);  // no "-₹0" for tiny negatives
const cycleDates = (c) => (c.start_date === c.end_date ? dayLabel(c.start_date) : `${dayLabel(c.start_date)} – ${dayLabel(c.end_date)}`);

function payoutStatusPill(c) {
  if (c.issues.includes("overdue")) return '<span class="status pending">Overdue</span>';
  if (c.status === "PAID") return '<span class="status replied">Paid</span>';
  return `<span class="status drafted">${esc(c.status ? c.status[0] + c.status.slice(1).toLowerCase() : "Unknown")}</span>`;
}

function payoutCheckCell(c) {
  if (c.issues.some((i) => i !== "overdue")) return `<span class="payout-bad">${c.discrepancy && c.issues.includes("payout_mismatch") ? `${rupees(c.discrepancy)} off` : `${c.issues.length} to check`}</span>`;
  if (c.reconciled) return '<span class="payout-ok">Matches</span>';
  return '<span class="muted">After payment</span>';
}

// Ads & discounts performance from the payout statements: what was spent, what it likely brought, where it works
const AD_VERDICT = {
  works: ["Paying off", "good"], ok: ["Break-even", "warn"], costly: ["Costly", "bad"], no_lift: ["No clear lift", "warn"],
  unclear: ["Unclear", "muted"], always_on: ["Same spend daily", "muted"], too_little: ["Not enough data", "muted"], no_ads: ["No ads", "muted"],
};
async function renderAds(page) {
  const d = await api(`/brands/${state.brandId}/ads/performance`, filterParams());
  const t = d.totals, p = d.previous;
  const change = (now, before, lowerIsBetter = false) => {
    if (now == null || !before) return "";
    const pct = Math.round(100 * (now - before) / before);
    if (!pct) return '<span class="ad-delta">same as before</span>';
    const good = lowerIsBetter ? pct < 0 : pct > 0;
    return `<span class="ad-delta ${good ? "good" : "bad"}">${pct > 0 ? "▲" : "▼"} ${Math.abs(pct)}% vs previous ${state.days === 1 ? "day" : state.days + " days"}</span>`;
  };
  const tile = (label, value, sub, delta = "") => `<div class="card kpi"><span class="kpi-label">${label}</span><div class="kpi-value">${value}</div><span class="muted">${sub}</span>${delta}</div>`;
  if (!t.ads && !t.discounts) {
    page.innerHTML = '<div class="card empty-state"><h3>No ad spend found in this period</h3><p>Ad spend comes from Zomato and Swiggy payout statements. Pick a longer date range, or check that payouts are being collected.</p></div>';
    return;
  }
  page.innerHTML = `
    <div class="so-hero">
      <div><div class="so-big">${compactINR(t.ads)}<small>spent on ads</small></div>
        <p>${t.ad_pct ?? "—"}% of sales · plus ${compactINR(t.discounts)} in discounts · ${inr.format(t.orders)} orders · Zomato and Swiggy payouts</p></div>
      <div class="so-now">Every ₹1 of ads came with<b>₹${t.roas ?? "—"} of sales</b></div>
    </div>
    <div class="grid ad-tiles" style="margin-bottom:20px">
      ${tile("Ad spend", compactINR(t.ads), `${t.ad_pct ?? "—"}% of order value`, change(t.ads, p.ads, true))}
      ${tile("Ads + discounts", `${t.growth_pct ?? "—"}%`, "of order value spent on growth", change(t.growth_pct, p.growth_pct, true))}
      ${tile("Ad cost per order", t.ad_per_order != null ? `₹${inr.format(t.ad_per_order)}` : "—", "ad spend ÷ delivered orders", change(t.ad_per_order, p.ad_per_order, true))}
      ${tile("Orders", inr.format(t.orders), `net payout ${compactINR(t.net_payout)}`, change(t.orders, p.orders))}
    </div>
    ${d.insights.length ? `<div class="ad-insights">${d.insights.map((i) => `<div class="ad-insight ${i.tone}"><b>${esc(i.title)}</b><p>${esc(i.text)}</p></div>`).join("")}</div>` : ""}
    <div class="card" style="margin-bottom:20px"><div class="card-head"><h3>Payout weeks</h3>
      <small class="muted">Monday to Sunday weeks that overlap your dates · change vs the week before</small></div>
      <div class="table-wrap"><table class="ov-table ad-table"><thead><tr><th>Week</th><th class="num">Ad spend</th><th class="num">Discounts</th>
        <th class="num">Orders</th><th class="num">Sales</th><th class="num">Ads % of sales</th><th class="num">Net payout</th><th>How it went</th></tr></thead><tbody>
      ${d.weekly.map((w) => { const ch = (v, lowerIsBetter) => v == null || !v ? "" : `<br><span class="ad-delta ${(lowerIsBetter ? v < 0 : v > 0) ? "good" : "bad"}">${v > 0 ? "▲" : "▼"} ${Math.abs(v)}%</span>`;
        return `<tr><td><b>${shortDate(w.week)} – ${shortDate(w.week_end)}</b>${w.partial ? '<br><span class="muted">week still running</span>' : ""}</td>
        <td class="num">${compactINR(w.ads)}${ch(w.ads_change, true)}</td><td class="num">${compactINR(w.discounts)}${ch(w.discounts_change, true)}</td>
        <td class="num">${inr.format(w.orders)}${ch(w.orders_change)}</td><td class="num">${compactINR(w.order_value)}</td>
        <td class="num ${(w.ad_pct || 0) >= 15 ? "ad-hot" : ""}">${w.ad_pct ?? "—"}%</td><td class="num">${compactINR(w.net_payout)}</td>
        <td>${esc(w.note)}</td></tr>`; }).join("")}</tbody></table></div></div>
    <div class="card" style="margin-bottom:20px"><div class="card-head"><h3>${d.trend.length >= 3 ? "Week by week" : "Day by day"}</h3><small class="muted">bars: ad spend and discounts · line: orders</small></div>
      <div style="height:220px"><canvas id="adTrend"></canvas></div></div>
    <div class="card"><div class="card-head"><h3>Outlets: is the ad money working?</h3>
      <small class="muted">ads' effect after allowing for discounts, season and trend · last 12 months</small></div>
      <div class="table-wrap"><table class="ov-table ad-table"><thead><tr><th>Outlet</th><th class="num">Ad spend</th><th class="num">% of sales</th>
        <th class="num">Orders/week<br>with · without ads</th><th class="num">Extra orders/week<br>from ads</th>
        <th class="num">Cost per extra order<br>ads · discounts</th><th>Confidence</th><th>Verdict</th></tr></thead><tbody>
      ${d.outlets.length ? "" : '<tr><td colspan="8" class="muted">No outlet has payouts in these dates yet.</td></tr>'}
      ${d.outlets.map((o) => { const m = o.model, l = o.lift, [label, tone] = AD_VERDICT[m.verdict] || ["—", "muted"];
        const money = (v) => (v != null ? `₹${inr.format(v)}` : "—");
        return `<tr>
        <td><b>${esc(o.outlet)}</b><br><span class="muted">${esc([o.city, o.platform === "swiggy" ? "Swiggy" : "Zomato"].filter(Boolean).join(" · "))}</span></td>
        <td class="num">${compactINR(o.ads)}</td><td class="num ${(o.ad_pct || 0) >= 15 ? "ad-hot" : ""}">${o.ad_pct ?? "—"}%</td>
        <td class="num">${l.with_ads ?? "—"} · ${l.without_ads ?? "—"}</td>
        <td class="num">${m.extra_orders != null ? (m.extra_orders > 0 ? `+${m.extra_orders}` : m.extra_orders) : "—"}</td>
        <td class="num">${money(m.cost_per_extra)} · ${money(m.disc_cost_per_extra)}<br><span class="muted">avg order ${money(m.avg_order)}</span></td>
        <td>${m.confidence ? `<span class="ad-conf ${m.confidence}">${m.confidence}</span>` : "—"}</td>
        <td><span class="ad-pill ${tone}">${label}</span></td></tr>`; }).join("")}</tbody></table></div>
      <p class="muted" style="margin:10px 0 0">For each outlet, orders a day are modelled on ad spend, discounts, season (how busy the brand's other outlets were the same day:
        festivals, weather, weekdays) and trend; store uptime and stock-outs join once they have 3 months of history. "Paying off" means an extra order from ads cost
        under about a third of the average order, "Costly" over two thirds. "Unclear" means the data can't separate ads from everything else yet; a two-week pause at
        one outlet is the surest test.</p></div>`;
  const series = d.trend.length >= 3 ? d.trend : d.daily;
  chart($("#adTrend"), {
    data: {
      labels: series.map((w) => shortDate(w.week || w.day)),
      datasets: [
        { type: "bar", label: "Ad spend", data: series.map((w) => w.ads), maxBarThickness: 48, backgroundColor: "#d9480f", stack: "s", yAxisID: "y" },
        { type: "bar", label: "Discounts", data: series.map((w) => w.discounts), maxBarThickness: 48, backgroundColor: "#f5a524", stack: "s", yAxisID: "y" },
        { type: "line", label: "Orders", data: series.map((w) => w.orders), borderColor: "#12a150", backgroundColor: "#12a150", tension: 0.35, pointRadius: 3, yAxisID: "y2" },
      ],
    },
    options: {
      maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "top", align: "end" },
        tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${c.dataset.yAxisID === "y2" ? inr.format(c.parsed.y) : compactINR(c.parsed.y)}` } } },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, grid: { color: "#eef1f5" }, border: { display: false }, ticks: { callback: (v) => compactINR(v) } },
        y2: { position: "right", grid: { display: false }, border: { display: false }, ticks: { callback: (v) => inr.format(v) } },
      },
    },
  });
}

// Delivery | Dining switch on Reconciliation, for brands with a dining outlet. Each side is its own page render.
function reconToggleHtml() {
  const v = state.reconView === "dining" ? "dining" : "delivery";
  return `<div class="segmented recon-toggle" style="margin-bottom:16px;width:fit-content"><button data-v="delivery" class="${v === "delivery" ? "active" : ""}">Delivery</button><button data-v="dining" class="${v === "dining" ? "active" : ""}">Dining</button></div>`;
}
function addReconToggle(page) {
  if (!state.hasDining) return;
  page.insertAdjacentHTML("afterbegin", reconToggleHtml());
  bindReconToggle(page);
}
function bindReconToggle(page) {
  page.querySelector(".recon-toggle")?.addEventListener("click", (e) => {
    const b = e.target.closest("[data-v]"); if (!b) return;
    state.reconView = b.dataset.v; render();
  });
}

async function renderDiningPayouts(page) {
  const d = await api(`/brands/${state.brandId}/dining/payouts`, filterParams());
  const s = d.summary, st = d.by_status;
  const label = { PENDING: "Pending settlement", CARRY_FORWARD: "Carried forward", SETTLED: "Settled", PAID: "Paid" };
  page.innerHTML = `${reconToggleHtml()}
    <div class="grid cols-3" style="margin-bottom:20px">
      <div class="card kpi"><span class="kpi-label">Billed (dining)</span><div class="kpi-value">${rupees(s.bill_amount)}</div><span class="muted">${inr.format(s.bills)} bills${s.first ? ` · ${shortDate(s.first)} to ${shortDate(s.last)}` : ""}</span></div>
      <div class="card kpi"><span class="kpi-label">Zomato commission</span><div class="kpi-value">${rupees(s.commission)}</div><span class="muted">plus ${rupees(s.tax)} tax on commission</span></div>
      <div class="card kpi"><span class="kpi-label">Deductions (ads & other)</span><div class="kpi-value">${rupees(d.ads.net)}</div><span class="muted">${rupees(d.ads.deducted)} deducted · ${rupees(d.ads.credited)} credited · ${inr.format(d.ads.lines)} lines</span></div>
      <div class="card kpi"><span class="kpi-label">Receivable after deductions</span><div class="kpi-value" style="${d.ads.after_ads < 0 ? "color:#e5484d" : ""}">${rupees(d.ads.after_ads)}</div><span class="muted">${d.ads.after_ads < 0 ? "deductions (ads and other charges on Zomato's statement) are larger than earnings: Zomato holds payouts until it clears" : "what is left after ads"}</span></div>
      <div class="card kpi"><span class="kpi-label">Receivable from Zomato</span><div class="kpi-value">${rupees(s.net_receivable)}</div><span class="muted">${Object.entries(st).map(([k, v]) => `${esc(label[k] || k)} ${rupees(v.net)}`).join(" · ") || "no bills yet"}</span></div>
    </div>
    ${Object.keys(st).length ? `<div class="card" style="margin-bottom:16px"><div class="card-head"><h3>By settlement status</h3><small class="muted">click a row to see its bills</small></div><table class="ov-table"><thead><tr><th>Status</th><th class="num">Bills</th><th class="num">Receivable</th></tr></thead><tbody>
      ${Object.entries(st).map(([k, v]) => `<tr class="dp-row" data-status="${esc(k)}" style="cursor:pointer"><td><b>${esc(label[k] || k)}</b></td><td class="num">${inr.format(v.bills)}</td><td class="num">${rupees(v.net)}</td></tr>`).join("")}</tbody></table></div>` : ""}
    <div class="card" style="margin-bottom:16px"><div class="card-head"><h3>By outlet</h3><small class="muted">click an outlet to see its bills</small></div>
      ${d.outlets.length ? `<table class="ov-table"><thead><tr><th>Outlet</th><th class="num">Bills</th><th class="num">Billed</th><th class="num">Commission</th><th class="num">Receivable</th><th class="num">Deductions</th><th class="num">After deductions</th></tr></thead><tbody>
      ${d.outlets.map((o) => `<tr class="dp-row" data-of="${esc(o.outlet_id)}" style="cursor:pointer" title="Click to see this outlet's bills"><td><b>${esc(o.name)}</b><br><small class="muted">${esc(o.res_id)}</small></td><td class="num">${inr.format(o.bills)}</td><td class="num">${rupees(o.bill_amount)}</td><td class="num">${rupees(o.commission)}</td><td class="num">${rupees(o.net_receivable)}</td><td class="num">${rupees(o.ads_net)}</td><td class="num" style="${o.after_ads < 0 ? "color:#e5484d" : ""}">${rupees(o.after_ads)}</td></tr>`).join("")}</tbody></table>` : `<p class="muted">No dining outlets here.</p>`}</div>
    ${d.ads.campaigns.length ? `<div class="card" style="margin-bottom:16px"><div class="card-head"><h3>Deductions by campaign <small class="muted">ads and other charges, as Zomato lists them</small></h3><small class="muted">click a campaign to see its lines</small></div><table class="ov-table"><thead><tr><th>Campaign</th><th class="num">Lines</th><th>From</th><th>To</th><th class="num">Amount</th></tr></thead><tbody>
      ${d.ads.campaigns.map((c) => `<tr class="dp-row" data-campaign="${esc(c.campaign_id)}" style="cursor:pointer"><td><code>${esc(c.campaign_id || "—")}</code></td><td class="num">${inr.format(c.lines)}</td><td class="muted">${c.first ? shortDate(c.first) : ""}</td><td class="muted">${c.last ? shortDate(c.last) : ""}</td><td class="num">${rupees(c.amount)}</td></tr>`).join("")}</tbody></table></div>` : ""}
    ${d.settlements.length ? `<div class="card" style="margin-bottom:16px"><div class="card-head"><h3>Settlements</h3><small class="muted">grouped by bank reference · click a row to see its bills</small></div><table class="ov-table"><thead><tr><th>Reference (UTR)</th><th>Date</th><th class="num">Bills</th><th class="num">Amount</th></tr></thead><tbody>
      ${d.settlements.map((x) => `<tr class="dp-row" data-utr="${esc(x.utr)}" style="cursor:pointer"><td><code>${esc(x.utr)}</code></td><td>${x.date ? shortDate(x.date) : ""}</td><td class="num">${inr.format(x.bills)}</td><td class="num">${rupees(x.amount)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="muted" style="margin:0 0 16px">No settled bills in this report yet: everything is pending or carried forward.</p>`}
    <div class="card"><div class="card-head"><h3>Latest bills</h3><small class="muted">newest 100</small></div><table class="ov-table"><thead><tr><th>When</th><th>Outlet</th><th>Type</th><th class="num">Bill</th><th class="num">Commission</th><th class="num">Receivable</th><th>Status</th></tr></thead><tbody>
      ${d.recent.map((t) => `<tr><td class="muted">${t.at ? shortDate(t.at) : ""}</td><td>${esc(t.outlet)}</td><td><small>${esc(t.discount_type || t.type || "")}</small></td><td class="num">${rupees(t.bill)}</td><td class="num">${rupees(t.commission)}</td><td class="num">${rupees(t.net)}</td><td><small>${esc(label[t.status] || t.status || "")}</small></td></tr>`).join("")}</tbody></table></div>`;
  bindReconToggle(page);
  page.onclick = async (e) => {  // click a settlement or a status to open the bills behind it (assigned, so renders never stack handlers)
    const row = e.target.closest(".dp-row"); if (!row) return;
    const open = row.nextElementSibling;
    if (open?.classList.contains("dp-open")) { open.remove(); return; }
    const cell = document.createElement("tr"); cell.className = "dp-open";
    cell.innerHTML = `<td colspan="9"><small class="muted">Loading bills…</small></td>`; row.after(cell);
    try {
      if (row.dataset.campaign != null) {
        const a = await api(`/brands/${state.brandId}/dining/payouts`, { ...filterParams(), campaign: row.dataset.campaign });
        cell.firstElementChild.innerHTML = `<div style="overflow:auto;max-height:420px"><table class="ov-table"><thead><tr><th>Order</th><th>Date</th><th>Outlet</th><th>Type</th><th>Status</th><th class="num">Amount</th></tr></thead><tbody>
          ${a.ad_lines.map((l) => `<tr><td><code>${esc(l.order)}</code></td><td class="muted">${l.date ? shortDate(l.date) : ""}</td><td>${esc(l.outlet)}</td><td><small>${l.kind === "ADDITION" ? "Credit" : "Deduction"}</small></td><td><small>${esc(label[l.status] || l.status || "")}</small></td><td class="num">${rupees(l.amount)}</td></tr>`).join("")}</tbody></table></div>${a.count > a.ad_lines.length ? `<small class="muted">showing ${a.ad_lines.length} of ${inr.format(a.count)}</small>` : ""}`;
        return;
      }
      const r = await api(`/brands/${state.brandId}/dining/payouts`, { ...filterParams(), ...(row.dataset.utr ? { utr: row.dataset.utr } : row.dataset.of ? { of: row.dataset.of } : { status: row.dataset.status }) });
      cell.firstElementChild.innerHTML = `<div style="overflow:auto;max-height:420px"><table class="ov-table"><thead><tr><th>Bill</th><th>When</th><th>Outlet</th><th>Offer</th><th class="num">Bill</th><th class="num">Commission</th><th class="num">Tax</th><th class="num">Adj.</th><th class="num">Receivable</th></tr></thead><tbody>
        ${r.bills.map((t) => `<tr><td><code>${esc(t.id)}</code></td><td class="muted">${t.at ? shortDate(t.at) : ""}</td><td>${esc(t.outlet)}</td><td><small>${esc(t.discount_type || t.type || "")}</small></td><td class="num">${rupees(t.bill)}</td><td class="num">${rupees(t.commission)}</td><td class="num">${rupees(t.tax)}</td><td class="num">${t.adjustment ? rupees(t.adjustment) : "—"}</td><td class="num">${rupees(t.net)}</td></tr>`).join("")}</tbody></table></div>${r.count > r.bills.length ? `<small class="muted">showing ${r.bills.length} of ${inr.format(r.count)}</small>` : ""}`;
    } catch (err) { cell.firstElementChild.innerHTML = `<small class="muted">${esc(userMessage(err))}</small>`; }
  };
}

async function renderReconciliation(page) {
  const listParams = filterParams({ status: payoutFilters.status, q: payoutFilters.q, issue: payoutFilters.issue });
  const [summary, cycles, combined] = await Promise.all([
    api(`/brands/${state.brandId}/payouts/summary`, filterParams()),
    api(`/brands/${state.brandId}/payouts/cycles`, { ...listParams, limit: 200 }),
    api(`/brands/${state.brandId}/payouts/combined`, listParams).catch(() => null),
  ]);
  const statements = payoutFilters.view === "statements" ? await api(`/brands/${state.brandId}/payouts/statements`, listParams) : null;
  const analytics = payoutFilters.view === "analytics" ? await api(`/brands/${state.brandId}/payouts/analytics`, { ...listParams, aplatform: payoutFilters.aPlatform, alayout: payoutFilters.aLayout }) : null;
  const analyticsXlsx = new URL(`${API}/brands/${state.brandId}/payouts/analytics/xlsx`, location.origin);
  Object.entries({ ...listParams, aplatform: analytics?.platform || "", alayout: analytics?.layout || "", basis: payoutFilters.basis }).forEach(([k, v]) => { if (v !== "" && v != null) analyticsXlsx.searchParams.set(k, v); });
  const exportUrl = new URL(`${API}/brands/${state.brandId}/payouts/export`, location.origin);
  Object.entries(listParams).forEach(([k, v]) => { if (v !== "" && v != null) exportUrl.searchParams.set(k, v); });
  const combinedXlsx = new URL(`${API}/brands/${state.brandId}/payouts/combined/xlsx`, location.origin);
  Object.entries(listParams).forEach(([k, v]) => { if (v !== "" && v != null) combinedXlsx.searchParams.set(k, v); });
  page.innerHTML = `
    <div class="so-hero">
      <div><div class="so-big">${inr.format(summary.with_issues)}<small> payout${summary.with_issues === 1 ? "" : "s"} to check</small></div>
        <p>${inr.format(summary.reconciled)} of ${inr.format(summary.cycles)} payouts checked against their orders · Zomato and Swiggy</p></div>
      <div class="so-now">Unexplained difference<b>${rupees(summary.discrepancy_total)}</b></div>
    </div>
    <div class="grid cols-3" style="margin-bottom:20px">
      <div class="card kpi"><span class="kpi-label">Paid</span><div class="kpi-value">${rupees(summary.paid_total)}</div>${summary.zero_payouts ? `<span class="muted">${inr.format(summary.zero_payouts)} payouts were ₹0 after ads and Hyperpure</span>` : ""}</div>
      <div class="card kpi"><span class="kpi-label">To be paid</span><div class="kpi-value">${rupees(summary.to_be_paid_total)}</div><span class="muted">${inr.format(summary.to_be_paid_cycles)} payouts${summary.carried_forward_cycles ? ` · ${inr.format(summary.carried_forward_cycles)} carried forward (${rupees(summary.carried_forward_total)})` : ""}</span></div>
      <div class="card kpi"><span class="kpi-label">Commission take rate</span><div class="kpi-value">${summary.take_rate == null ? "—" : `${summary.take_rate.toFixed(2)}%`}</div><span class="muted">service fee on checked orders</span></div>
    </div>
    ${summary.new_lines?.length && state.me.is_staff ? `<details class="card new-lines" style="margin-bottom:12px"><summary><b>${plural(summary.new_lines.length, "new statement line")}</b> to review <span class="muted">· lines we haven't seen on a Zomato or Swiggy statement before, click to open</span></summary>
      <p class="muted" style="margin-top:10px">These appeared on Zomato or Swiggy payout statements for the first time. Until reviewed they count as deductions not tied to orders, and aren't counted as ad spend.</p>
      <table class="ov-table"><thead><tr><th>Platform</th><th>Line</th><th class="num">Payouts</th><th class="num">Total</th><th>Last seen</th><th></th></tr></thead><tbody>
      ${summary.new_lines.map((l) => `<tr><td>${l.platform === "swiggy" ? "Swiggy" : "Zomato"}</td><td><b>${esc(l.label)}</b><br><span class="muted">${esc(l.section)}</span></td>
        <td class="num">${inr.format(l.payouts)}</td><td class="num">${rupees(l.total)}</td><td class="muted">${shortDate(l.last_seen)}</td>
        <td>${state.me.is_staff ? `<span class="btn-row">${[["order", "Order charge"], ["ad", "Ad spend"], ["deduction", "Other deduction"]].map(([k, t]) =>
          `<button class="btn ${l.guess === k ? "blue" : "light"}" data-line="${l.id}" data-kind="${k}">${t}</button>`).join("")}</span>` : ""}</td></tr>`).join("")}
      </tbody></table></details>` : ""}
    ${summary.issues.length ? `<div class="card" style="margin-bottom:20px"><div class="card-head"><h3>What needs checking</h3></div>
      <ul class="payout-issues">${summary.issues.map((i) => `<li><button class="payout-issue-btn ${payoutFilters.issue === i.code ? "on" : ""}" data-payout-issue="${i.code}">
        <b>${inr.format(i.count)}</b> ${esc(i.label)}<span class="muted">${payoutFilters.issue === i.code ? "showing · clear" : "show"}</span></button></li>`).join("")}</ul></div>` : ""}
    ${combined?.platforms.length ? `<details class="card payout-combined" id="combinedBox" style="margin-bottom:12px" ${payoutFilters.combinedOpen ? "open" : ""}>
      <summary><b>Combined statement</b> <span class="muted">· ${plural(combined.total.payouts, "payout")} matching these filters · ${inr.format(combined.total.orders)} orders · net ${rupees(combined.total.net_payout)}
          (paid ${rupees(combined.total.paid)} · to be paid ${rupees(combined.total.to_be_paid)}) · click to open</span></summary>
      <p style="margin:10px 0 6px"><a class="btn light" href="${combinedXlsx}" download>Export Excel</a></p>
      <div class="payout-combined-grid">${combined.platforms.map((p) => `<div>
        <h4>${p.platform === "swiggy" ? "Swiggy" : "Zomato"} <span class="muted">· ${plural(p.payouts, "payout")} · ${plural(p.outlets, "outlet")} · ${inr.format(p.orders)} orders</span></h4>
        <table class="payout-statement"><tbody>${(() => { const base = stmtBase(p.sections); return p.sections.map((sec) => `<tr class="section"><td>${esc(sec.label)}</td><td>${rupees(sec.value)}</td></tr>
          ${sec.items.map((i) => `<tr><td class="muted">${esc(i.label)}</td><td class="muted">${rupees(i.value)}</td></tr>`).join("")}`).join("") + `<tr class="section total"><td>Net payout</td><td>${rupees(p.net_payout)}</td></tr>`; })()}</tbody></table></div>`).join("")}</div>
      <p class="muted" style="margin:8px 0 0">Adds up every payout matching the filters (dates, outlets, platform, status, search), the same ones the list and the CSV use. Zomato and Swiggy statements are laid out differently, so each is combined on its own.</p>
    </details>` : ""}
    <div class="card so-list">
      <div class="toolbar">
        <label class="payout-date">From <input id="payoutFrom" type="date" value="${range().start}" max="${isoDate(new Date())}"></label>
        <label class="payout-date">To <input id="payoutTo" type="date" value="${range().end}" max="${isoDate(new Date())}"></label>
        <input id="payoutSearch" type="search" placeholder="Search outlet or UTR…" value="${esc(payoutFilters.q)}">
        <div class="segmented" id="payoutView">${[["list", "List"], ["statements", "Statement view"], ["analytics", "Analytics"]].map(([v, l]) => `<button data-view="${v}" class="${payoutFilters.view === v ? "active" : ""}">${l}</button>`).join("")}</div>
        ${payoutFilters.view === "statements" ? '<button class="btn blue" id="exportBook">Export Book</button>' : payoutFilters.view === "analytics" ? `<a class="btn blue" href="${analyticsXlsx}" download>Export Excel</a>` : `<a class="btn light" href="${exportUrl}" download>Export CSV</a>`}
        ${payoutFilters.issue ? `<button class="btn light" id="payoutIssueClear">${esc((summary.issues.find((i) => i.code === payoutFilters.issue) || {}).label || payoutFilters.issue)} ✕</button>` : ""}
        <div class="segmented" id="payoutStatus">${[["", "All"], ["issues", "To check"], ["paid", "Paid"], ["to_be_paid", "To be paid"]]
          .map(([v, l]) => `<button data-v="${v}" class="${payoutFilters.status === v ? "active" : ""}">${l}</button>`).join("")}</div>
      </div>
      ${analytics ? renderAnalytics(analytics) : statements ? renderStatementBlocks(statements.groups) : cycles.results.length ? `<div class="table-wrap payout-table"><table>
        <thead><tr><th>Outlet</th><th>Cycle</th><th>Payout date</th><th>Status</th><th>UTR</th><th>Orders</th><th>Net payout</th><th>Check</th></tr></thead>
        <tbody>${cycles.results.map((c) => `<tr data-cycle="${c.id}" class="${String(payoutFilters.open) === String(c.id) ? "open" : ""}">
          <td><b>${esc(c.outlet)}</b><br><span class="muted">${esc([c.city, c.platform === "swiggy" ? "Swiggy" : "Zomato", c.res_id].filter(Boolean).join(" · "))}</span></td>
          <td>${cycleDates(c)}</td>
          <td class="muted">${c.payout_date ? dayLabel(c.payout_date) : "—"}</td>
          <td>${payoutStatusPill(c)}</td>
          <td><button class="payout-utr" data-open="${c.id}">${esc(c.utr || "View")}</button></td>
          <td>${inr.format(c.order_count)}</td>
          <td>${rupees(c.net_payout)}</td>
          <td>${payoutCheckCell(c)}</td></tr>`).join("")}</tbody></table></div>
        ${cycles.total > cycles.results.length ? `<p class="muted" style="margin:10px 0 0">Showing ${inr.format(cycles.results.length)} of ${inr.format(cycles.total)}. Narrow the dates or search to see the rest.</p>` : ""}`
        : `<div class="empty-state"><h3>No payouts for these dates</h3><p>Pick other dates above. Payouts are collected once a day, for the recent dates the job covers.</p></div>`}
    </div>`;
  const pickDates = () => {
    const start = $("#payoutFrom").value, end = $("#payoutTo").value;
    if (!start || !end) return;
    if (start > end) return toast("The start date is after the end date");
    applyCustomRange(start, end);
  };
  $("#payoutFrom").addEventListener("change", pickDates);
  $("#payoutTo").addEventListener("change", pickDates);
  let timer;
  $("#payoutSearch").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { payoutFilters.q = e.target.value.trim(); renderReconciliation(page).then(() => { const s = $("#payoutSearch"); s.focus(); s.setSelectionRange(s.value.length, s.value.length); }); }, 300);
  });
  $("#payoutStatus").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    payoutFilters.status = b.dataset.v; renderReconciliation(page);
  });
  page.querySelectorAll("[data-line]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    try { await apiJSON(`/brands/${state.brandId}/payouts/line-types/${b.dataset.line}`, "POST", { kind: b.dataset.kind }); toast("Saved"); renderReconciliation(page); }
    catch (e) { toast(userMessage(e)); b.disabled = false; }
  }));
  page.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => { payoutFilters.view = b.dataset.view; renderReconciliation(page); }));
  if (statements) wireStatementBlocks(page, statements.groups);
  $("#combinedBox")?.addEventListener("toggle", (e) => { payoutFilters.combinedOpen = e.target.open; });
  page.querySelectorAll("[data-alayout]").forEach((b) => b.addEventListener("click", () => { payoutFilters.aLayout = b.dataset.alayout; analyticsOpen.clear(); renderReconciliation(page); }));
  page.querySelectorAll("[data-abasis]").forEach((b) => b.addEventListener("click", () => { payoutFilters.basis = b.dataset.abasis; renderReconciliation(page); }));
  page.querySelectorAll("[data-aplat]").forEach((b) => b.addEventListener("click", () => { payoutFilters.aPlatform = b.dataset.aplat; payoutFilters.aLayout = ""; analyticsOpen.clear(); renderReconciliation(page); }));
  page.querySelectorAll("[data-asec]").forEach((b) => b.addEventListener("click", () => { const k = b.dataset.asec; analyticsOpen.has(k) ? analyticsOpen.delete(k) : analyticsOpen.add(k); renderReconciliation(page); }));
  $("#aDetail")?.addEventListener("click", () => { payoutFilters.detail = !payoutFilters.detail; analyticsOpen.clear(); renderReconciliation(page); });
  $("#exportBook")?.addEventListener("click", () => {
    const url = new URL(`${API}/brands/${state.brandId}/payouts/book`, location.origin);
    Object.entries(listParams).forEach(([k, v]) => { if (v !== "" && v != null) url.searchParams.set(k, v); });
    const off = [...stmtSel.values()].reduce((n, set) => n + set.size, 0);
    if (off) url.searchParams.set("cycles", statements.groups.flatMap((g) => g.cycles.filter((c) => !stmtSel.get(stmtKey(g))?.has(c.id)).map((c) => c.id)).join(","));
    location.href = url;
  });
  page.querySelectorAll("[data-payout-issue]").forEach((b) => b.addEventListener("click", () => {
    payoutFilters.issue = payoutFilters.issue === b.dataset.payoutIssue ? "" : b.dataset.payoutIssue;
    if (payoutFilters.issue) payoutFilters.status = "";
    renderReconciliation(page).then(() => $(".payout-table, .so-list")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }));
  $("#payoutIssueClear")?.addEventListener("click", () => { payoutFilters.issue = ""; renderReconciliation(page); });
  page.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", () => togglePayoutDetail(b.closest("tr"), Number(b.dataset.open))));
}

// each statement line as a share of the net order value, like Zomato's own payout analytics (deductions shown as positive shares)
function stmtBase(sections) {
  const s = sections.find((x) => /^net order value/i.test(x.label || "")) || sections.find((x) => /^(total_order_value|total_customer_paid|gross_order_value)$/.test(x.id || ""));
  return s ? Math.abs(Number(s.value)) || null : null;
}
const pctOf = (v, base) => (base && v != null ? ` <span class="pct">${(100 * Math.abs(Number(v)) / base).toFixed(2)}%</span>` : "");

// ---------- alert settings: who gets WhatsApp / email alerts, for which outlets and alert types ----------
async function renderAlertSettings(page, clientId) {
  const d = await api(`/clients/${clientId}/alert-recipients`);
  const base = `/clients/${clientId}/alert-recipients`;
  const scopeText = (r) => r.outlet_ids.length ? plural(r.outlet_ids.length, "outlet") : r.brand_ids.length
    ? d.brands.filter((b) => r.brand_ids.includes(b.id)).map((b) => b.name).join(", ") : "All outlets";
  const card = (r) => `<div class="card al-card" data-r="${r.id ?? "new"}">
    <div class="al-row">
      <select name="channel"><option value="whatsapp" ${r.channel === "whatsapp" ? "selected" : ""}>WhatsApp</option><option value="email" ${r.channel === "email" ? "selected" : ""}>Email</option></select>
      <input name="address" placeholder="${r.channel === "email" ? "ops@brand.com" : "919876543210"}" value="${esc(r.address)}">
      <input name="name" placeholder="Name (e.g. Ops team)" value="${esc(r.name)}">
      <label class="al-active"><input type="checkbox" name="is_active" ${r.is_active ? "checked" : ""}> Active</label>
    </div>
    <div class="al-toggles">${d.toggles.map((t) => `<label><input type="checkbox" name="${t.key}" ${r[t.key] ? "checked" : ""}> ${esc(t.label)}</label>`).join("")}</div>
    <div class="al-row">
      <span class="muted">For:</span>
      <select name="scope"><option value="all" ${!r.brand_ids.length && !r.outlet_ids.length ? "selected" : ""}>All outlets</option>
        <option value="brands" ${r.brand_ids.length && !r.outlet_ids.length ? "selected" : ""}>Chosen brands</option>
        <option value="outlets" ${r.outlet_ids.length ? "selected" : ""}>Chosen outlets</option></select>
      <span class="muted al-scope-text">${esc(scopeText(r))}</span>
      <span class="muted" style="margin-left:auto">Quiet hours</span><input type="time" name="quiet_start" value="${r.quiet_start}"> to <input type="time" name="quiet_end" value="${r.quiet_end}">
    </div>
    <div class="al-pick" data-pick="brands" ${r.brand_ids.length && !r.outlet_ids.length ? "" : "hidden"}>${d.brands.map((b) => `<label><input type="checkbox" data-brand="${b.id}" ${r.brand_ids.includes(b.id) ? "checked" : ""}> ${esc(b.name)}</label>`).join("")}</div>
    <div class="al-pick" data-pick="outlets" ${r.outlet_ids.length ? "" : "hidden"}><input type="search" class="al-search" placeholder="Search outlets…">
      <div class="al-outlets">${d.outlets.map((o) => `<label data-q="${esc((o.name + " " + (o.city || "")).toLowerCase())}"><input type="checkbox" data-outlet="${o.id}" ${r.outlet_ids.includes(o.id) ? "checked" : ""}> ${esc(o.name)} <span class="muted">${esc(o.city || "")}</span></label>`).join("")}</div></div>
    <div class="btn-row"><button class="btn blue" data-save>${r.id ? "Save" : "Add recipient"}</button>
      ${r.id ? '<button class="btn light" data-test>Send test</button><button class="btn light" data-del>Remove</button>' : '<button class="btn light" data-cancel>Cancel</button>'}<span class="login-error" data-err></span></div>
  </div>`;
  const blank = { id: null, name: "", channel: "whatsapp", address: "", is_active: true, brand_ids: [], outlet_ids: [], quiet_start: "", quiet_end: "",
    ...Object.fromEntries(d.toggles.map((t) => [t.key, true])) };
  page.innerHTML = `<div class="page-head"><h2>Alerts settings</h2><p class="muted">Who gets WhatsApp or email alerts, for which outlets, and which alerts. Messages are grouped (one per alert type per check), and nothing is sent during a person's quiet hours.</p></div>
    <div id="alList">${d.recipients.map(card).join("") || '<div class="card empty-state"><h3>No one gets alerts yet</h3><p>Add a WhatsApp number or email below.</p></div>'}</div>
    <button class="btn blue" id="alAdd" style="margin:6px 0 18px">+ Add recipient</button>
    <div class="card"><div class="card-head"><h3>Recent alerts</h3></div>
      ${d.log.length ? `<div class="table-wrap"><table class="ov-table"><thead><tr><th>When</th><th>To</th><th>Alert</th><th>Message</th><th>Status</th></tr></thead><tbody>
        ${d.log.map((l) => `<tr><td class="muted">${timeAgo(l.at)}</td><td>${esc(l.to)}</td><td>${esc(l.kind)}</td><td>${esc(l.summary)}</td>
          <td>${l.status === "sent" ? '<span class="status replied">sent</span>' : `<span class="status pending" title="${esc(l.error)}">failed</span>`}</td></tr>`).join("")}</tbody></table></div>`
        : '<p class="muted">No alerts sent yet.</p>'}</div>`;
  const wire = (el) => {
    const pick = (name) => el.querySelector(`[data-pick="${name}"]`);
    el.querySelector('[name="scope"]').addEventListener("change", (e) => { pick("brands").hidden = e.target.value !== "brands"; pick("outlets").hidden = e.target.value !== "outlets"; });
    el.querySelector(".al-search")?.addEventListener("input", (e) => {
      const q = e.target.value.trim().toLowerCase();
      el.querySelectorAll(".al-outlets label").forEach((l) => { l.hidden = q && !l.dataset.q.includes(q); });
    });
    const id = el.dataset.r === "new" ? null : Number(el.dataset.r), err = el.querySelector("[data-err]");
    el.querySelector("[data-save]").addEventListener("click", async (e) => {
      const v = (n) => el.querySelector(`[name="${n}"]`), scope = v("scope").value;
      const body = { channel: v("channel").value, address: v("address").value, name: v("name").value, is_active: v("is_active").checked,
        quiet_start: v("quiet_start").value, quiet_end: v("quiet_end").value,
        brand_ids: scope === "brands" ? [...el.querySelectorAll("[data-brand]:checked")].map((c) => Number(c.dataset.brand)) : [],
        outlet_ids: scope === "outlets" ? [...el.querySelectorAll("[data-outlet]:checked")].map((c) => Number(c.dataset.outlet)) : [],
        ...Object.fromEntries(d.toggles.map((t) => [t.key, v(t.key).checked])) };
      if (scope !== "all" && !body.brand_ids.length && !body.outlet_ids.length) { err.textContent = `Tick at least one ${scope === "brands" ? "brand" : "outlet"}, or choose All outlets.`; return; }
      e.target.disabled = true;
      try { await apiJSON(id ? `${base}/${id}` : base, id ? "PUT" : "POST", body); toast("Saved"); renderAlertSettings(page, clientId); }
      catch (x) { err.textContent = userMessage(x); e.target.disabled = false; }
    });
    el.querySelector("[data-test]")?.addEventListener("click", async (e) => {
      e.target.disabled = true;
      try { await apiJSON(`${base}/${id}/test`, "POST", {}); toast("Test queued: the collector sends it on its next check, within about 5 minutes."); }
      catch (x) { err.textContent = userMessage(x); }
      e.target.disabled = false;
    });
    el.querySelector("[data-del]")?.addEventListener("click", async () => {
      if (!confirm("Remove this recipient? They stop getting alerts.")) return;
      try { await api(`${base}/${id}`, {}, { method: "DELETE" }); toast("Removed"); renderAlertSettings(page, clientId); } catch (x) { err.textContent = userMessage(x); }
    });
    el.querySelector("[data-cancel]")?.addEventListener("click", () => el.remove());
  };
  page.querySelectorAll(".al-card").forEach(wire);
  $("#alAdd").addEventListener("click", () => {
    if (page.querySelector('[data-r="new"]')) return;
    $("#alList").querySelector(".empty-state")?.remove();
    $("#alList").insertAdjacentHTML("beforeend", card(blank));
    wire(page.querySelector('[data-r="new"]'));
    page.querySelector('[data-r="new"] [name="address"]').focus();
  });
}

// ---------- staff: Zomato / Swiggy login sessions, stored encrypted in the database for every machine to use ----------
const SESSION_KINDS = {
  merchant: { zomato: "Paste a request to zomato.com copied as cURL from the logged-in merchant dashboard (it carries the cookies), or the cookie JSON.",
              swiggy: "Paste a request copied as cURL from the logged-in Swiggy partner app/dashboard (it carries access_token), or the session JSON." },
  merchant_app: { zomato: "Paste the merchant app's “Restaurant ratings” request copied as cURL (x-zomato-access-token)." },
  customer_app: { zomato: "Paste any request the Zomato customer app made to api.zomato.com, copied as cURL.",
                  swiggy: "Paste any request the Swiggy customer app made, copied as cURL." },
};

// the automatic "log in again" button: queued here, run by the collector worker on the Windows server
const fmtClock = (x) => new Date(x).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
function sessionHealth(a) {
  if (a.expired_at) return `<span class="status sess-bad" title="${esc(a.expired_reason || "")}">Expired ${timeAgo(a.expired_at)}</span>`;
  return a.reads_from === "database" ? '<span class="status replied">OK</span>' : '<span class="muted">—</span>';
}
function loginButton(a) {
  const r = a.refresh;
  if (r && (r.status === "queued" || r.status === "running")) {
    const what = r.status === "queued" ? "Waiting for the collector…" : "Logging in…";
    return `<button class="btn light" disabled title="${esc(what)}">⏳ Refreshing…</button>
      <div class="sess-note">${esc(what)} Started by ${esc(r.requested_by)} at ${fmtClock(r.requested_at)}</div>`;
  }
  const last = !r ? "" : r.status === "done"
    ? `<div class="sess-note ok">✓ Logged in again ${timeAgo(r.finished_at)} by ${esc(r.worker || "collector")}</div>`
    : `<div class="sess-note bad">✕ Last try failed ${timeAgo(r.finished_at)}: ${esc(r.error || "unknown error")}</div>`;
  return `<button class="btn blue" data-login="${a.id}" data-label="${esc(`${a.platform} · ${a.label}`)}">Log in again</button>${last}`;
}

// the outlets a login can see, and a staff button to ask the collector to re-read them from Zomato / Swiggy
function syncCell(a) {
  const isActive = (x) => x && ["queued", "running"].includes(x.status);
  const active = [a.outlet_sync, a.refresh].find(isActive);
  const r = a.outlet_sync;
  const head = `<b>${inr.format(a.outlets || 0)}</b> outlet${a.outlets === 1 ? "" : "s"}${a.last_synced_at ? ` <span class="muted">· synced ${timeAgo(a.last_synced_at)}</span>` : ""}`;
  if (active) {
    const what = active.kind === "outlets" ? (active.status === "queued" ? "Waiting for the collector…" : "Reading outlets…") : "A login is in progress…";
    return `${head}<div><button class="btn light" disabled title="${esc(what)}">⏳ ${active.kind === "outlets" ? "Syncing…" : "Busy"}</button></div><div class="sess-note">${esc(what)}</div>`;
  }
  const last = !r ? "" : r.status === "done"
    ? `<div class="sess-note ok">✓ ${esc(r.result || "synced")} · ${timeAgo(r.finished_at)}</div>`
    : `<div class="sess-note bad">✕ Last sync failed ${timeAgo(r.finished_at)}: ${esc(r.error || "unknown error")}</div>`;
  return `${head}<div><button class="btn light" data-sync="${a.id}" data-label="${esc(`${a.platform} · ${a.label}`)}" title="Ask the collector which outlets this login can see and add the new ones to the catalog">Sync outlets</button></div>${last}`;
}

// staff only: which Zomato outlets (by res ID) get review replies sent to Zomato. No row = no replies are ever sent.
async function renderReplyService(page) {
  const d = await api("/staff/reply-service");
  const MODE = { manual: "Manual only (no automatic replies)", ai: "Automatic AI replies" };
  page.innerHTML = `<div class="page-head"><h2>Reply service</h2>
      <p class="muted">The <b>Send to Zomato</b> button on the Reviews page works for everyone who can edit an outlet. This page controls the <b>automatic replies</b>: <b>an outlet is answered automatically only if its res ID is listed below and switched on.</b> The collector on the Windows server sends everything, every 3 hours.</p></div>
    <div class="card"><div class="card-head"><h3>Switch on automatic replies</h3></div>
      <label class="rs-wide">Zomato res IDs (one per line, or separated by commas)
        <textarea id="rsIds" rows="3" placeholder="12345678&#10;23456789"></textarea></label>
      <div class="rs-form">
        <label>Most automatic replies a day, per outlet<input id="rsMax" type="number" min="1" max="500" value="60"></label>
        <label class="check" style="align-self:end"><input id="rsHold" type="checkbox" checked> Leave food-safety, refund and legal reviews for a person</label>
      </div>
      <label class="rs-wide">Extra wording rules for the AI (optional), e.g. a contact number or signature
        <textarea id="rsNotes" rows="2" placeholder="Sign off as Team Carvel. For ratings below 3, ask the guest to call 9XXXXXXXXX."></textarea></label>
      <div class="btn-row"><button class="btn blue" id="rsSave">Switch on</button></div>
      <p class="muted" style="margin:8px 0 0">Every res ID must already be mapped to an outlet on Brands &amp; Outlets. The collector writes a reply with Gemini for each new unreplied review (up to 3 days old) at these outlets, and holds the risky ones for a person.</p></div>
    <div class="card" style="margin-top:14px"><div class="card-head"><h3>Who has it <span class="muted">${d.rows.length} outlet${d.rows.length === 1 ? "" : "s"}</span></h3><input id="rsFind" type="search" placeholder="Find a res ID or outlet…" style="max-width:240px"></div>
      <div id="rsTable"></div></div>`;
  const rows = new Map(d.rows.map((r) => [String(r.id), r]));
  const draw = () => {
    const q = ($("#rsFind").value || "").toLowerCase();
    const list = d.rows.filter((r) => !q || [r.res_id, r.outlet, r.client, r.city].some((v) => (v || "").toLowerCase().includes(q)));
    $("#rsTable").innerHTML = list.length ? `<div class="table-wrap"><table class="ov-table"><thead><tr><th>Res ID</th><th>Outlet</th><th>How</th><th class="num">Daily cap</th><th>Risky reviews</th><th>Status</th><th>Set by</th><th></th></tr></thead><tbody>
      ${list.map((r) => `<tr class="${r.is_active ? "" : "muted"}"><td class="nowrap"><b>${esc(r.res_id)}</b></td>
        <td>${r.mapped ? `${esc(r.outlet)}<br><span class="muted">${esc(r.client)}${r.city ? ` · ${esc(r.city)}` : ""}</span>` : '<span class="ov-bad">Not mapped to an outlet</span>'}</td>
        <td>${esc(MODE[r.mode] || r.mode)}</td><td class="num">${r.mode === "ai" ? r.max_per_day : "—"}</td>
        <td>${r.mode === "ai" ? (r.hold_risky ? "held for a person" : "answered") : "—"}</td>
        <td>${r.is_active ? '<span class="status replied">On</span>' : '<span class="status pending">Off</span>'}</td>
        <td class="muted">${esc(r.enabled_by || "")}<br>${timeAgo(r.updated_at)}</td>
        <td class="nowrap"><button class="btn light" data-rs-toggle="${r.id}">${r.is_active ? "Turn off" : "Turn on"}</button> <button class="btn light" data-rs-del="${r.id}">Remove</button></td></tr>`).join("")}
      </tbody></table></div>` : `<p class="muted">${d.rows.length ? "No match." : "No outlets yet, so no automatic replies are being sent for anyone."}</p>`;
    page.querySelectorAll("[data-rs-toggle]").forEach((b) => b.addEventListener("click", () => {
      const r = rows.get(b.dataset.rsToggle);
      save({ res_ids: [r.res_id], mode: r.mode, max_per_day: r.max_per_day, hold_risky: r.hold_risky, instructions: r.instructions, is_active: !r.is_active, allow_unmapped: true },
        r.is_active ? "Turned off: nothing more will be sent" : "Turned on");
    }));
    page.querySelectorAll("[data-rs-del]").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm("Remove this outlet? Nothing more will be sent for it.")) return;
      try { await apiJSON(`/staff/reply-service/${b.dataset.rsDel}`, "DELETE", {}); toast("Removed"); renderReplyService(page); } catch (err) { toast(userMessage(err)); }
    }));
  };
  const save = async (body, done) => {
    try { await apiJSON("/staff/reply-service", "POST", body); toast(done); renderReplyService(page); } catch (err) { toast(userMessage(err)); }
  };
  $("#rsFind").addEventListener("input", draw);
  $("#rsSave").addEventListener("click", () => {
    const ids = $("#rsIds").value.split(/[\s,;]+/).filter(Boolean);
    if (!ids.length) return toast("Enter at least one res ID");
    if (!confirm(`Switch on AUTOMATIC replies for ${ids.length} outlet${ids.length === 1 ? "" : "s"}? The collector will write and send replies on its own for their new reviews.`)) return;
    save({ res_ids: ids, mode: "ai", max_per_day: Number($("#rsMax").value) || 60, hold_risky: $("#rsHold").checked, instructions: $("#rsNotes").value, is_active: true },
      `Automatic replies on for ${ids.length} outlet${ids.length === 1 ? "" : "s"}`);
  });
  draw();
}

let sessionsPoll = null;
async function renderSessions(page) {
  clearTimeout(sessionsPoll);
  const d = await api("/staff/sessions");
  const when = (x) => (x ? `${timeAgo(x.updated_at)}<br><span class="muted">${esc(x.updated_by || "")}</span>` : '<span class="muted">not in database</span>');
  const btn = (platform, kind, id, label) => `<button class="btn light" data-sess="${platform}|${kind}|${id ?? ""}|${esc(label)}">Paste session</button>`;
  page.innerHTML = `<div class="page-head"><h2>Platform sessions</h2><p class="muted">Zomato and Swiggy logins, stored encrypted in the database. The Windows collector and this site read them from here, so a refresh here reaches every machine on its next run.</p></div>
    <div class="card"><div class="card-head"><h3>Collector accounts</h3></div>
      <div class="table-wrap"><table class="ov-table"><thead><tr><th>Account</th><th>Client</th><th>Status</th><th>Merchant dashboard</th><th>Automatic login</th><th>Outlets</th><th></th><th>Merchant app (ratings)</th><th></th></tr></thead><tbody>
      ${d.accounts.map((a) => `<tr class="${a.is_active ? "" : "muted"}"><td><b>${a.platform === "swiggy" ? "Swiggy" : "Zomato"} · ${esc(a.label)}</b>${a.is_active ? "" : " (inactive)"}</td>
        <td>${esc(a.client)}</td><td>${sessionHealth(a)}<div class="sess-note">reads from ${esc(a.reads_from)}</div></td>
        <td>${when(a.merchant)}</td><td class="sess-login">${loginButton(a)}</td><td class="sess-login">${syncCell(a)}</td><td>${btn(a.platform, "merchant", a.id, `${a.platform} · ${a.label}`)}</td>
        <td>${a.platform === "zomato" ? when(a.merchant_app) : '<span class="muted">—</span>'}</td><td>${a.platform === "zomato" ? btn(a.platform, "merchant_app", a.id, `${a.platform} · ${a.label} (merchant app)`) : ""}</td></tr>`).join("")}
      </tbody></table></div>
      <p class="muted" style="margin:10px 0 0">Saving a merchant session switches that account to read from the database. Collector logins (<code>run.py zomato session</code>) on any machine save here too once an account reads from the database.</p></div>
    <div class="card" style="margin-top:14px"><div class="card-head"><h3>Competitor search (customer app)</h3></div>
      <table class="ov-table"><tbody>${d.customer_app.map((c) => `<tr><td><b>${c.platform === "swiggy" ? "Swiggy" : "Zomato"}</b></td>
        <td>${c.session ? when(c.session) : c.file ? '<span class="muted">server file only</span>' : '<span class="muted">not set</span>'}</td>
        <td>${btn(c.platform, "customer_app", "", `${c.platform} customer app`)}</td></tr>`).join("")}</tbody></table></div>`;
  page.querySelectorAll("[data-login]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    b.textContent = "⏳ Queuing…";
    try {
      await apiJSON(`/staff/sessions/${b.dataset.login}/refresh`, "POST", {});
      toast(`Logging in to ${b.dataset.label} again. This takes a minute or two.`);
    } catch (err) {
      toast(err.status === 409 ? "Someone already started a refresh for this login" : `Couldn't start: ${userMessage(err)}`);
    }
    renderSessions(page);
    checkSessionAlerts();
  }));
  page.querySelectorAll("[data-sync]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    b.textContent = "⏳ Queuing…";
    try {
      await apiJSON(`/staff/sessions/${b.dataset.sync}/sync-outlets`, "POST", {});
      toast(`Reading the outlets of ${b.dataset.label}. This takes a minute or two.`);
    } catch (err) {
      toast(err.status === 409 ? "A request for this login is already in progress" : `Couldn't start: ${userMessage(err)}`);
    }
    renderSessions(page);
  }));
  // while a login or an outlet sync is queued or running, keep the page current so everyone sees the same state
  if (d.accounts.some((a) => [a.refresh, a.outlet_sync].some((x) => x && ["queued", "running"].includes(x.status)))) {
    sessionsPoll = setTimeout(() => { if (currentRoute() === "sessions" && page.isConnected) renderSessions(page).catch(() => {}); }, 5000);
  } else checkSessionAlerts();
  page.querySelectorAll("[data-sess]").forEach((b) => b.addEventListener("click", () => {
    const [platform, kind, id, label] = b.dataset.sess.split("|");
    document.querySelector(".link-modal")?.remove();
    const m = document.createElement("div");
    m.className = "link-modal";
    m.innerHTML = `<div class="card link-box"><div class="card-head"><h3>Refresh ${esc(label)}</h3><button class="btn light" data-close>Cancel</button></div>
      <p class="muted" style="margin-top:0">${SESSION_KINDS[kind][platform] || ""} It's stored encrypted; nobody sees it again after saving.</p>
      <textarea id="sessText" rows="10" style="width:100%;font-family:monospace;font-size:12px" placeholder="curl -H '...' ..."></textarea>
      <p class="login-error" id="sessErr"></p><div class="btn-row"><button class="btn blue" id="sessSave">Save session</button></div></div>`;
    document.body.appendChild(m);
    m.addEventListener("click", (e) => { if (e.target === m || e.target.closest("[data-close]")) m.remove(); });
    m.querySelector("#sessSave").addEventListener("click", async (e) => {
      e.target.disabled = true;
      try {
        await apiJSON("/staff/sessions", "POST", { platform, kind, account_id: id ? Number(id) : null, text: m.querySelector("#sessText").value });
        m.remove(); toast("Session saved"); renderSessions(page);
      } catch (err) { m.querySelector("#sessErr").textContent = userMessage(err); e.target.disabled = false; }
    });
  }));
}

// ---------- statement view: per outlet, its payout cycles as columns and the statement lines as rows ----------
const stmtKey = (g) => `${g.outlet_id}:${g.platform}`;
const paise = (v) => Math.round((v || 0) * 100);  // add money in whole paise so totals never drift

function stmtTotals(g) {
  const off = stmtSel.get(stmtKey(g)) || new Set();
  const on = g.cycles.filter((c) => !off.has(c.id));
  const net = on.reduce((n, c) => n + paise(c.net_payout), 0), paid = on.reduce((n, c) => n + paise(c.customer_paid), 0);
  return { n: on.length, net: net / 100, margin: paid ? Math.round((net / paid) * 10000) / 100 : null };
}


// Zomato-style payout analytics: an outlet per column, every statement line as an amount and its share of net (or gross) sales
function renderAnalytics(a) {
  if (!a.columns.length) return '<div class="empty-state"><h3>No payouts for these dates</h3><p>Pick other dates above.</p></div>';
  const key = payoutFilters.basis === "gross" ? "gross_base" : "net_base";
  const cols = [...a.columns, a.total];
  const cell = (c, v) => `${rupees(v)}${c[key] ? ` <span class="pct">${(100 * Math.abs(v) / c[key]).toFixed(c === a.total ? 1 : 0)}%</span>` : ""}`;
  const val = (c, sid) => (c.values[sid] || { value: 0, items: {} });
  const head = (c) => `<th class="an-col ${c === a.total ? "an-total" : ""}"><span>${esc(c.name)}</span><small>${esc(c.city || "")}</small>${c.res_id ? `<b class="an-id">${esc(c.res_id)}</b>` : ""}${c.start ? `<em>${dayLabel(c.start)} – ${dayLabel(c.end)}</em>` : ""}</th>`;
  const rows = a.sections.map((sec) => {
    const open = payoutFilters.detail || analyticsOpen.has(sec.id);
    const nonzero = sec.items.filter((lab) => cols.some((c) => val(c, sec.id).items[lab]));
    const main = `<tr class="an-sec"><td class="an-label">${nonzero.length ? `<button class="an-chev ${open ? "open" : ""}" data-asec="${esc(sec.id)}" aria-label="Show lines">›</button>` : '<span class="an-chev"></span>'}${esc(sec.label)}</td>
      ${cols.map((c) => `<td class="num ${c === a.total ? "an-total" : ""}">${cell(c, val(c, sec.id).value)}</td>`).join("")}</tr>`;
    const items = open ? nonzero.map((lab) => `<tr class="an-item"><td class="an-label muted">${esc(lab)}</td>${cols.map((c) => `<td class="num muted ${c === a.total ? "an-total" : ""}">${cell(c, val(c, sec.id).items[lab] || 0)}</td>`).join("")}</tr>`).join("") : "";
    return main + items;
  }).join("");
  return `<div class="an-bar">
      ${a.platforms.length > 1 ? `<div class="segmented">${a.platforms.map((p) => `<button data-aplat="${p}" class="${a.platform === p ? "active" : ""}">${p === "swiggy" ? "Swiggy" : "Zomato"}</button>`).join("")}</div>` : ""}
      ${(a.layouts || []).length > 1 ? `<div class="segmented" title="The platform changed its statement layout, and the lines of the two layouts are not the same lines. Each is shown on its own so every percentage is accurate.">${a.layouts.map((L) => `<button data-alayout="${esc(L.key)}" class="${a.layout === L.key ? "active" : ""}">${esc(L.name)} format · ${dayLabel(L.from)} – ${dayLabel(L.to)}</button>`).join("")}</div>` : ""}
      <div class="segmented">${[["net", "% of net sales"], ["gross", "% of gross sales"]].map(([v, l]) => `<button data-abasis="${v}" class="${payoutFilters.basis === v ? "active" : ""}">${l}</button>`).join("")}</div>
      <button class="btn light" id="aDetail">${payoutFilters.detail ? "Hide lines" : "Show all lines"}</button>
      <span class="muted">${plural(a.total.cycles, "payout")} · ${plural(a.columns.length, "outlet")} · ${inr.format(a.total.orders)} orders · all payouts matching the filters above</span></div>
    <div class="table-wrap an-wrap"><table class="an-table"><thead><tr><th class="an-label">Metrics</th>${cols.map(head).join("")}</tr></thead>
      <tbody><tr class="an-sec"><td class="an-label"><span class="an-chev"></span>Total orders</td>${cols.map((c) => `<td class="num ${c === a.total ? "an-total" : ""}">${inr.format(c.orders)}</td>`).join("")}</tr>
      ${rows}
      <tr class="an-sec an-net"><td class="an-label"><span class="an-chev"></span>Net payout</td>${cols.map((c) => `<td class="num ${c === a.total ? "an-total" : ""}">${cell(c, c.net_payout)}</td>`).join("")}</tr></tbody></table></div>
    <p class="muted" style="margin:8px 0 0">Percentages are each line's share of ${payoutFilters.basis === "gross" ? "gross sales (net order value plus the discounts)" : "net sales (the statement's net order value)"}. Zomato and Swiggy statements are laid out differently, so each is shown on its own${(a.layouts || []).length > 1 ? ", and so is each statement layout the platform has used in these dates (switch above)" : ""}.</p>`;
}

function renderStatementBlocks(groups) {
  if (!groups.length) return '<div class="empty-state"><h3>No payouts for these filters</h3><p>Pick other dates, outlets or status above.</p></div>';
  const cell = (g, c) => (stmtSel.get(stmtKey(g))?.has(c.id) ? "off" : "");
  return groups.map((g, gi) => {
    const t = stmtTotals(g);
    return `<div class="stmt-block" data-g="${gi}">
      <div class="stmt-head"><div><b>${esc(g.outlet)}</b> <span class="stmt-chip">${esc(g.res_id || "")}</span>
        <span class="stmt-chip ${g.platform}">${g.platform === "swiggy" ? "Swiggy" : "Zomato"}</span><br><span class="muted">${esc([g.brand_outlet, g.city].filter(Boolean).join(" · "))}</span></div>
        <div class="stmt-total"><span>Selected combined total · ${t.n} of ${g.cycles.length}</span><b>${rupees(t.net)}</b>${t.margin != null ? `<em>${t.margin.toFixed(2)}% margin</em>` : ""}</div></div>
      <div class="table-wrap stmt-wrap"><table class="stmt"><thead><tr><th class="stmt-first">Particulars</th>
        ${g.cycles.map((c) => `<th class="${cell(g, c)}"><label class="stmt-pick"><input type="checkbox" data-cycle="${c.id}" ${cell(g, c) ? "" : "checked"}>
          ${shortDate(c.start_date)}${c.end_date !== c.start_date ? ` – ${shortDate(c.end_date)}` : ""}</label>
          <div>${payoutStatusPill(c)} ${c.margin != null ? `<span class="stmt-margin">${c.margin.toFixed(2)}%</span>` : ""}</div>
          <small class="muted">${c.utr ? `UTR ${esc(c.utr)}` : "no UTR yet"}</small>${c.issues.length ? `<small class="stmt-issue">${esc(c.issues.join(", "))}</small>` : ""}</th>`).join("")}</tr></thead>
        <tbody><tr class="stmt-orders"><td class="stmt-first">Total orders</td>${g.cycles.map((c) => `<td class="num ${cell(g, c)}">${inr.format(c.orders)}</td>`).join("")}</tr>
        ${g.rows.map((r, ri) => `<tr class="stmt-sec" data-row="${gi}-${ri}"><td class="stmt-first">${r.items.length ? '<span class="stmt-caret">›</span>' : ""}${esc(r.label)}</td>
            ${g.cycles.map((c) => `<td class="num ${cell(g, c)}">${r.values[c.id] != null ? rupees(r.values[c.id]) : "—"}</td>`).join("")}</tr>
          ${r.items.map((it) => `<tr class="stmt-item" data-parent="${gi}-${ri}" hidden><td class="stmt-first muted">${esc(it.label)}</td>
            ${g.cycles.map((c) => `<td class="num muted ${cell(g, c)}">${it.values[c.id] != null ? rupees(it.values[c.id]) : "—"}</td>`).join("")}</tr>`).join("")}`).join("")}
        <tr class="stmt-net"><td class="stmt-first">Net payout</td>${g.cycles.map((c) => `<td class="num ${cell(g, c)}">${rupees(c.net_payout)}</td>`).join("")}</tr>
        </tbody></table></div></div>`;
  }).join("");
}

function wireStatementBlocks(page, groups) {
  page.querySelectorAll(".stmt-sec").forEach((tr) => tr.addEventListener("click", () => {
    const open = tr.classList.toggle("open");
    page.querySelectorAll(`[data-parent="${tr.dataset.row}"]`).forEach((r) => { r.hidden = !open; });
  }));
  page.querySelectorAll(".stmt-block").forEach((block) => {
    const g = groups[Number(block.dataset.g)];
    block.querySelectorAll("[data-cycle]").forEach((box) => box.addEventListener("change", () => {
      const key = stmtKey(g), off = stmtSel.get(key) || new Set(), id = Number(box.dataset.cycle);
      box.checked ? off.delete(id) : off.add(id);
      stmtSel.set(key, off);
      const col = [...box.closest("tr").children].indexOf(box.closest("th"));
      block.querySelectorAll("tr").forEach((tr) => tr.children[col]?.classList.toggle("off", !box.checked));
      const t = stmtTotals(g);
      block.querySelector(".stmt-total").innerHTML = `<span>Selected combined total · ${t.n} of ${g.cycles.length}</span><b>${rupees(t.net)}</b>${t.margin != null ? `<em>${t.margin.toFixed(2)}% margin</em>` : ""}`;
    }));
  });
}

async function togglePayoutDetail(tr, id) {
  const open = tr.nextElementSibling?.classList.contains("payout-detail");
  document.querySelector(".payout-detail")?.remove();
  document.querySelector("tr.open")?.classList.remove("open");
  if (open) return;
  tr.classList.add("open");
  const row = document.createElement("tr");
  row.className = "payout-detail";
  row.innerHTML = '<td colspan="8"><div class="loading">Loading…</div></td>';
  tr.after(row);
  let d;
  try {
    d = await api(`/brands/${state.brandId}/payouts/cycles/${id}`);
  } catch (e) {
    row.innerHTML = `<td colspan="8" class="muted">${esc(userMessage(e))}</td>`;
    return;
  }
  const label = (code) => d.issue_labels[code] || code;
  // why each order may explain a payout that doesn't match: its own failed checks, plus orders that could account for the gap
  const gap = d.issues.includes("payout_mismatch") ? Number(d.discrepancy || 0) : 0;
  const reasons = (o) => {
    const r = o.issues.map((c) => ({ text: label(c), money: true }));
    if (gap && Math.abs(Math.abs(o.payout || 0) - Math.abs(gap)) <= 1) r.unshift({ text: `payout equals the ₹${inr.format(Math.abs(gap))} gap`, money: true, gap: true });
    if (o.unsettled_amount) r.push({ text: `₹${inr.format(o.unsettled_amount)} not settled`, money: true });
    return r;
  };
  const flagged = (o) => reasons(o).length > 0;
  const orders = [...d.orders].sort((a, b) => (reasons(b).some((x) => x.gap) - reasons(a).some((x) => x.gap)) || (flagged(b) - flagged(a)));
  const carried = d.issues.includes("deductions_carried");
  const ORDER_SECTIONS = ["total_order_value", "total_customer_paid", "total_fees", "total_taxes", "order_level_deductions", "tax_deductions", "additions", "complaint_cancellation_charges",
    "gross_order_value", "discounts_and_promotions", "net_order_value_subtotal", "service_fee", "tax_deductions_v2", "refunds_and_additions", "penalties_and_other_deductions"];  // Zomato's newer statement layout too
  const bigLines = d.breakdown.filter((sec) => !ORDER_SECTIONS.includes(sec.id)).flatMap((sec) => sec.items.filter((i) => i.value < 0).map((i) => ({ ...i, section: sec.label })))
    .sort((a, b) => a.value - b.value).slice(0, 3);
  const nGap = d.orders.filter((o) => reasons(o).some((x) => x.gap)).length;
  // each order as a share of the payout's gross and net sales (Zomato's own statement totals; the orders' sum when the statement has none)
  const secBase = (re) => { const s = d.breakdown.find((x) => re.test(x.label || "") || re.test(x.id || "")); return s ? Math.abs(Number(s.value)) || null : null; };
  const grossBase = secBase(/^(gross order value|gross_order_value|total_order_value|total_customer_paid)/i) || d.orders.reduce((t, o) => t + Math.abs(Number(o.gross_value) || 0), 0) || null;
  const netBase = secBase(/^net order value/i) || d.orders.reduce((t, o) => t + Math.abs(Number(o.net_order_value) || 0), 0) || null;
  const nFlag = d.orders.filter(flagged).length;
  const explain = carried ? `The orders match the statement. ${d.platform === "swiggy" ? "Swiggy" : "Zomato"} paid ₹0 because deductions not tied to orders (${bigLines.map((l) => `${l.label} ${rupees(l.value)}`).join(", ") || "see the statement"}) were bigger than what the orders earned; ${rupees(-(d.expected_payout || 0))} carries into the next payout`
    : gap && !nGap && bigLines.length ? `No single order explains it. Biggest deductions not tied to orders: ${bigLines.map((l) => `${l.label} ${rupees(l.value)}`).join(", ")}`
    : gap ? (nGap ? `${plural(nGap, "order")} ${nGap === 1 ? "has" : "have"} a payout equal to the gap, so ${nGap === 1 ? "it was" : "they were"} likely left out of the payout`
      : nFlag ? `${plural(nFlag, "order")} flagged below may explain it` : "No single order explains it: likely a deduction or adjustment the order report doesn't show")
    : nFlag ? `${plural(nFlag, "order")} flagged` : "";
  // where the money went: what the orders earned, what ads and Hyperpure took off it, and what was paid. A payout of ₹0 is explained here, not flagged as an error.
  const sectionSum = (re) => d.breakdown.filter((x) => re.test(x.id || "")).reduce((t, x) => t + (Number(x.value) || 0), 0);
  const sectionTotal = (test) => d.breakdown.filter((x) => !ORDER_SECTIONS.includes(x.id) && test(`${x.id || ""} ${x.label || ""}`.toLowerCase())).reduce((t, x) => t + (Number(x.value) || 0), 0);
  const ads = sectionTotal((t) => /investments_in_growth|\bads\b/.test(t)), hyper = sectionTotal((t) => /hyperpure/.test(t));  // by id or title: "Ads deductions from previous weeks or other outlets" counts as ads
  const flow = (() => {
    if (!d.reconciled || d.orders_total == null) return "";
    const earned = Number(d.orders_total), paid = Number(d.net_payout || 0), other = Number(d.adjustments || 0) - ads - hyper;
    const part = (label, v, cls = "") => (Math.abs(v) >= 1 ? `<span class="pf-step ${cls}"><small>${label}</small><b>${rupees(v)}</b></span>` : "");
    const taken = -(ads + hyper + other);
    const eaten = earned > 0 ? taken / earned : 0;
    const bits = [ads && `ads ${rupees(-ads)}`, hyper && `Hyperpure ${rupees(-hyper)}`, Math.abs(other) >= 1 && `other ${rupees(-other)}`].filter(Boolean).join(", ");
    const note = !paid && earned > 0 && eaten >= 0.95 ? `Zomato paid ₹0 because deductions (${bits}) took the whole ₹${inr.format(Math.round(earned))} the orders earned.`
      : hyper < 0 && earned > 0 && -hyper / earned >= 0.4 ? `Hyperpure took ${Math.round((-hyper / earned) * 100)}% of what the orders earned.`
      : ads < 0 && earned > 0 && -ads / earned >= 0.2 ? `Ads took ${Math.round((-ads / earned) * 100)}% of what the orders earned.` : "";
    return `<div class="payout-flow">
      ${part("Orders earned", earned, "pf-earn")}${part("Ads", ads, ads < 0 && -ads / (earned || 1) >= 0.2 ? "pf-hot" : "")}${part("Hyperpure", hyper, hyper < 0 && -hyper / (earned || 1) >= 0.4 ? "pf-hot" : "")}${part("Other", other)}
      <span class="pf-step pf-paid"><small>${d.status === "PAID" ? "Paid" : "Payout"}</small><b>${rupees(paid)}</b></span>
      ${note ? `<span class="pf-note">${esc(note)}</span>` : ""}</div>`;
  })();
  row.innerHTML = `<td colspan="8">
    ${d.issues.length ? `<ul class="payout-issues warn">${d.issues.map((i) => `<li>${esc(label(i))}</li>`).join("")}</ul>` : ""}
    ${flow}
    <div class="payout-columns">
      <div>
        <h4>${d.platform === "swiggy" ? "Swiggy" : "Zomato"}'s statement</h4>
        ${d.breakdown.length ? `<table class="payout-statement"><tbody>${(() => { const base = stmtBase(d.breakdown); return d.breakdown.map((s) => `<tr class="section"><td>${esc(s.label)}</td><td>${rupees(s.value)}</td></tr>
          ${s.items.filter((i) => i.value).map((i) => `<tr class="${(carried || gap) && bigLines.some((l) => l.label === i.label && l.value === i.value) ? "payout-culprit" : ""}"><td class="muted">${esc(i.label)}</td><td class="muted">${rupees(i.value)}</td></tr>`).join("")}`).join("") + `<tr class="section total"><td>Net payout</td><td>${rupees(d.net_payout)}</td></tr>`; })()}</tbody></table>` : '<p class="muted">No statement available.</p>'}
      </div>
      <div>
        <h4>Our check</h4>
        ${d.reconciled ? `<table class="payout-statement"><tbody>
          <tr><td>Orders' payouts (${inr.format(d.orders.length)} orders)</td><td>${rupees(d.orders_total)}</td></tr>
          <tr><td>Not tied to an order (ads, Hyperpure)</td><td>${rupees(d.adjustments)}</td></tr>
          <tr class="section"><td>Expected payout</td><td>${rupees(d.expected_payout)}</td></tr>
          <tr><td>Net payout from ${d.platform === "swiggy" ? "Swiggy" : "Zomato"}</td><td>${rupees(d.net_payout)}</td></tr>
          <tr class="section total"><td>Difference</td><td class="${d.issues.includes("payout_mismatch") ? "payout-bad" : "payout-ok"}">${rupees(d.discrepancy)}</td></tr></tbody></table>`
          : '<p class="muted">Orders are checked once this payout is paid.</p>'}
      </div>
    </div>
    ${orders.length ? `<div class="payout-orders-head"><h4>Orders</h4>
      ${gap || nFlag || carried ? `<span class="payout-explain ${gap ? "bad" : carried ? "warn" : ""}">${gap ? `Difference ${rupees(gap)} · ` : ""}${esc(explain)}</span>` : ""}
      ${nFlag ? `<label class="muted"><input type="checkbox" class="payout-only-flagged"> Show only flagged orders</label>` : ""}</div>
      <div class="table-wrap payout-orders"><table>
      <thead><tr><th>Order ID</th><th>Date</th><th>Status</th><th>Gross value</th><th>Net value</th><th>Fee %</th><th>Fees</th><th>Taxes</th><th>Other</th><th>Payout</th><th>Settlement</th><th>Why flagged</th></tr></thead>
      <tbody>${orders.map((o) => `<tr class="${flagged(o) ? (reasons(o).some((x) => x.gap) ? "flagged gap" : "flagged") : ""}">
        <td>${esc(o.order_id)}</td>
        <td class="muted">${o.order_date ? new Date(o.order_date).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "—"}</td>
        <td>${esc(o.status)}</td><td>${rupees(o.gross_value)}${pctOf(o.gross_value, grossBase)}</td><td>${rupees(o.net_order_value)}${pctOf(o.net_order_value, netBase)}</td><td>${o.base_fee_pct}%${o.service_fee_pct !== o.base_fee_pct ? ` <span class="muted">+${(o.service_fee_pct - o.base_fee_pct).toFixed(1)}% distance</span>` : ""}</td><td>${rupees(o.fees_total)}</td>
        <td>${rupees(o.government_charges)}</td><td>${rupees(o.other_deductions)}</td><td><b>${rupees(o.payout)}</b></td>
        <td>${esc(o.settlement_status || "—")}${o.unsettled_amount ? ` <span class="muted">${rupees(o.unsettled_amount)} left</span>` : ""}</td>
        <td>${reasons(o).map((x) => `<span class="ov-issue ${x.money ? "money" : ""}">${esc(x.text)}</span>`).join(" ")}</td></tr>`).join("")}</tbody></table></div>` : ""}
  </td>`;
  row.querySelector(".payout-only-flagged")?.addEventListener("change", (e) => {
    row.querySelectorAll(".payout-orders tbody tr").forEach((r) => { r.hidden = e.target.checked && !r.classList.contains("flagged"); });
  });
}

// ---------- store uptime ----------
const OFFLINE_CHECK_MS = 60 * 1000;
const OFFLINE_NOTICE_MS = 30 * 1000;
const OFFLINE_MAX_NOTICES = 3;  // one bad minute shouldn't cover the screen; the rest become a single summary

function offlineStack() {
  let stack = $("#offlineStack");
  if (!stack) {
    document.body.insertAdjacentHTML("beforeend", '<div class="offline-stack" id="offlineStack" role="status" aria-live="polite"></div>');
    stack = $("#offlineStack");
  }
  return stack;
}

// with two or more popups open, a "Close all" button sits above them
function syncCloseAll() {
  const stack = offlineStack(), n = stack.querySelectorAll(".offline-notice").length;
  let btn = stack.querySelector(".offline-closeall");
  if (n < 2) { btn?.remove(); return; }
  if (!btn) {
    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "offline-closeall";
    btn.addEventListener("click", () => { stack.querySelectorAll(".offline-notice").forEach((x) => x.dispatchEvent(new Event("dismiss"))); stack.innerHTML = ""; });
  }
  stack.prepend(btn);  // always on top, above the newest popup
  btn.textContent = `Close all (${n})`;
}

function showOfflineNotice({ title, detail, when = "", open, online = false }) {
  const el = document.createElement("div");
  el.className = `offline-notice ${online ? "online" : ""}`;
  el.innerHTML = `<i class="offline-dot"></i>
    <div class="offline-text"><b>${esc(title)}</b><span>${esc(detail)}</span>${when ? `<small class="muted">${esc(when)}</small>` : ""}
      <button class="offline-view" type="button">View</button></div>
    <button class="offline-close" type="button" aria-label="Dismiss">×</button>`;
  let timer;
  const close = () => { clearTimeout(timer); el.remove(); syncCloseAll(); };
  el.addEventListener("dismiss", () => clearTimeout(timer));
  const arm = () => { clearTimeout(timer); timer = setTimeout(close, OFFLINE_NOTICE_MS); };
  el.querySelector(".offline-close").addEventListener("click", close);
  el.querySelector(".offline-view").addEventListener("click", () => { close(); open(); });
  el.addEventListener("mouseenter", () => clearTimeout(timer));  // stays while being read
  el.addEventListener("mouseleave", arm);
  offlineStack().prepend(el);
  syncCloseAll();
  arm();
}

async function openOfflineOutlet(row) {
  if (row) uptimeFilters.outlet = row.outlet_id;
  uptimeFilters.status = "";
  location.hash = "#/store_uptime";
  if (row && row.brand_id !== state.brandId) {
    $("#brandSelect").value = row.brand_id;
    await loadBrand(row.brand_id);
  }
}

// which changes this person has already been told about, kept per login so a shared browser doesn't mix them up
function unseenChanges(kind, rows) {
  const key = `ss_${kind}_seen_${state.me.username}`;
  const saved = store.get(key);
  const seen = new Set((saved || "").split(",").filter(Boolean).map(Number));
  store.set(key, rows.map((r) => r.id).join(","));
  return { firstVisit: saved == null, fresh: rows.filter((r) => !seen.has(r.id)) };
}

const noticeTime = (ts) => {
  const d = new Date(ts), t = d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
  const days = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 864e5);
  if (days <= 0) return t;
  return `${days === 1 ? "Yesterday" : d.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}, ${t}`;
};
const manyOutlets = (n) => `${n} outlet${n === 1 ? "" : "s"}`;

function showChanges(fresh, one, summary, online) {
  if (fresh.length > OFFLINE_MAX_NOTICES) {
    showOfflineNotice({ title: summary, detail: "Open Offline hours to see which", open: () => openOfflineOutlet(), online });
    return;
  }
  fresh.forEach((r) => showOfflineNotice({ ...one(r), open: () => openOfflineOutlet(r), online }));
}

async function checkOffline() {
  if (document.hidden || !state.me) return;
  let changes;
  try {
    changes = await api("/uptime/changes", state.me.is_staff && state.brandId ? { brand_id: state.brandId } : {});
  } catch { return; }  // try again next minute; a popup is never worth an error message

  // only stores that just went down are news: ones offline for days are on Offline hours, not a popup
  const offline = unseenChanges("offline", changes.offline.filter((r) => Date.now() - new Date(r.since) < 3 * 36e5));
  if (offline.firstVisit) {  // first visit on this browser: these aren't news, so one summary instead of a popup each
    if (changes.offline.length) showOfflineNotice({ title: `${manyOutlets(changes.offline.length)} offline right now`, detail: "Open Offline hours to see which", open: () => openOfflineOutlet() });
  } else {
    showChanges(offline.fresh, (r) => ({ title: `${r.outlet} went offline`, detail: `${r.brand} · ${r.platform}`, when: noticeTime(r.since) }),
      `${manyOutlets(offline.fresh.length)} went offline`, false);
  }

  const back = unseenChanges("online", changes.back);
  if (!back.firstVisit) {
    showChanges(back.fresh, (r) => ({ title: `${r.outlet} is back online`, detail: `${r.brand} · ${r.platform}`,
      when: `${noticeTime(r.restored_at)} · was offline ${downtimeText(r.downtime_minutes)}` }),
      `${manyOutlets(back.fresh.length)} came back online`, true);
  }
}

// staff: a banner while any Zomato / Swiggy login has expired, linking to the Sessions page to log in again
async function checkSessionAlerts() {
  const bar = $("#sessionBanner");
  if (!bar || !state.me?.is_staff) return;
  let d;
  try { d = await api("/staff/sessions/alerts"); } catch { return; }
  if (!d.expired.length) { bar.hidden = true; return; }
  const names = d.expired.map((a) => `${a.platform === "swiggy" ? "Swiggy" : "Zomato"} · ${esc(a.label)}${a.refreshing ? " (logging in…)" : ""}`).join(", ");
  bar.innerHTML = `<span>⚠ ${d.expired.length === 1 ? "A platform login has" : `${d.expired.length} platform logins have`} expired: <b>${names}</b>. Data from ${d.expired.length === 1 ? "it" : "them"} stops updating until it's logged in again.</span>
    <a class="btn light" href="#/sessions">Open Sessions</a>`;
  bar.hidden = false;
}

function startOfflineWatch() {
  checkSessionAlerts();
  setInterval(checkSessionAlerts, 120000);
  checkOffline();
  setInterval(checkOffline, OFFLINE_CHECK_MS);
  document.addEventListener("visibilitychange", checkOffline);  // catch up as soon as the tab is back
}

const uptimeFilters = { status: "", outlet: "" };

const offlineFor = (e) => downtimeText(e.downtime_minutes) || "under a minute";

let uptimeAll = false, uptimeCity = "";
const UP_TOP = 10;

// ---------- Estimated revenue loss: a slide-over panel (Offline hours page and the Overview tile) ----------
function openLossPanel(data, focusId) {
  if (!data || !(data.high > 0)) return;
  document.querySelector(".lp-root")?.remove();
  const root = document.createElement("div");
  root.className = "lp-root";
  const period = data.period ? `${shortDate(data.period.start)} – ${shortDate(data.period.end)}` : periodLabel();
  const rows = data.outlets || [];
  const maxHigh = Math.max(1, ...rows.map((o) => o.high));
  const nameCount = rows.reduce((m, o) => m.set(o.name, (m.get(o.name) || 0) + 1), new Map());
  const where = (o) => [o.city, nameCount.get(o.name) > 1 ? o.outlet_name : ""].filter(Boolean).join(" · ");  // the outlet's own name only where two share an area
  let focus = focusId != null ? rows.find((o) => String(o.outlet_id) === String(focusId)) : null;
  const close = () => { root.classList.remove("open"); document.removeEventListener("keydown", onKey); setTimeout(() => root.remove(), 380); };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  const countUp = (el, a, b, ms = 900) => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = `${rupeesShort(a)} – ${rupeesShort(b)}`; return; }
    const t0 = performance.now() + 250;
    const step = (now) => { const p = Math.min(1, Math.max(0, (now - t0) / ms)), e = 1 - Math.pow(1 - p, 3); el.textContent = `${rupeesShort(a * e)} – ${rupeesShort(b * e)}`; if (p < 1) requestAnimationFrame(step); };
    el.textContent = `${rupeesShort(0)} – ${rupeesShort(0)}`; requestAnimationFrame(step);
  };
  const draw = () => {
    const o = focus;
    root.innerHTML = `<div class="lp-scrim"></div>
      <aside class="lp-panel" role="dialog" aria-label="Estimated revenue loss">
        <header class="lp-head"><div>${o ? `<button class="lp-back" type="button">‹ All outlets</button>` : ""}<h3>${o ? esc(o.name) : "Estimated revenue loss"}</h3>
          <p>${o ? `${esc(where(o))} · ${esc(period)}` : `from being offline · ${esc(period)}`}</p></div><button class="lp-x" type="button" aria-label="Close">×</button></header>
        <section class="lp-hero"><span class="lp-label">${o ? "Sales we think were missed" : "Sales we think you missed"}</span>
          <b class="lp-big" id="lpBig">${rupeesShort(o ? o.low : data.low)} – ${rupeesShort(o ? o.high : data.high)}</b>
          <small>${o ? `${plural(o.offline_days, "day")} with offline time${o.avg_offline_pct != null ? `, offline about ${o.avg_offline_pct}% of opening hours on those days` : ""}` : `across ${plural(rows.length, "outlet")}`}</small></section>
        ${o ? dayView(o) : listView()}
        <footer class="lp-foot"><details><summary>How this is worked out</summary>
          <p>We take the share of each day an outlet was <b>offline</b>, from Zomato's and Swiggy's own online-time figure. Then we look at what that outlet <b>normally sells on that weekday</b>, using its last six weeks of normal days.</p>
          <p class="lp-formula">Usual sales for that weekday × share of the day offline</p>
          <p>Because not every missed order is lost, since some customers come back later or order elsewhere, we show a range. The bottom of the range is 60% of the full estimate.</p>
          <ul><li>It is an estimate, not a measurement: nobody can know which orders would have come.</li><li>It is the same idea as Zomato's own "Est. lost sales", and it covers Swiggy as well.</li><li>A day with no sales or online-time data is left out, not guessed.</li></ul></details>
          ${data.outlet_days_unestimated ? `<p class="muted">${plural(data.outlet_days_unestimated, "outlet-day")} left out: not enough sales data to estimate.</p>` : ""}</footer>
      </aside>`;
    root.querySelector(".lp-scrim").onclick = close;
    root.querySelector(".lp-x").onclick = close;
    root.querySelector(".lp-back")?.addEventListener("click", () => { focus = null; draw(); });
    root.querySelectorAll("[data-lp]").forEach((b) => b.addEventListener("click", () => { focus = rows.find((r) => String(r.outlet_id) === b.dataset.lp); draw(); root.querySelector(".lp-panel").scrollTop = 0; }));
    const big = root.querySelector("#lpBig"); countUp(big, o ? o.low : data.low, o ? o.high : data.high);
  };
  const listView = () => `<section class="lp-body"><h4>Outlets, biggest loss first</h4>
    ${rows.map((o, i) => `<button class="lp-row" type="button" data-lp="${o.outlet_id}" style="--i:${Math.min(i, 14)}">
      <span class="lp-name" title="${esc(o.outlet_name || "")}">${esc(o.name)} <small class="muted">${esc(where(o))}</small></span>
      <span class="lp-bar"><i style="width:${Math.max(3, (o.high / maxHigh) * 100)}%"></i></span>
      <b>${rupeesShort(o.low)} – ${rupeesShort(o.high)}</b></button>`).join("")}</section>`;
  const dayView = (o) => {
    const days = o.days || [], byDate = new Map(days.map((d) => [d.date, d]));
    const all = [], from = new Date(`${data.period.start}T00:00:00`), to = new Date(`${data.period.end}T00:00:00`);  // every day of the period, so quiet days show as gaps
    for (let t = new Date(from); t <= to && all.length < 120; t.setDate(t.getDate() + 1)) all.push(isoDate(t));
    const top = Math.max(1, ...days.map((d) => d.high)), peak = days.reduce((m, d) => (d.high > (m?.high || 0) ? d : m), null);
    const marks = new Set([0, Math.round((all.length - 1) * 0.25), Math.round((all.length - 1) * 0.5), Math.round((all.length - 1) * 0.75), all.length - 1]);  // five dates along the bottom, not one per bar
    const label = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
    return `<section class="lp-body"><h4>Day by day</h4>
      <div class="lp-days">${all.map((iso, i) => { const d = byDate.get(iso);
        return `<div class="lp-day ${d ? "" : "quiet"}" style="--i:${Math.min(i, 40)}" title="${esc(label(iso))}${d ? `: offline ${d.offline_pct}% · ${rupeesShort(d.low)} – ${rupeesShort(d.high)} · ${esc(d.source)}` : ": no offline time"}">
          <i style="height:${d ? Math.max(5, (d.high / top) * 100) : 0}%"></i>${d && peak && d.date === peak.date ? `<em>${rupeesShort(d.high)}</em>` : ""}${marks.has(i) ? `<span>${esc(label(iso))}</span>` : ""}</div>`; }).join("")}</div>
      <ul class="lp-list">${days.slice().sort((a, b) => b.high - a.high).slice(0, 6).map((d) => `<li><span>${esc(label(d.date))}</span><span class="muted">offline ${d.offline_pct}% · ${esc(d.source)}</span><b>${rupeesShort(d.low)} – ${rupeesShort(d.high)}</b></li>`).join("")}</ul></section>`;
  };
  document.body.appendChild(root);
  draw();
  document.addEventListener("keydown", onKey);
  requestAnimationFrame(() => requestAnimationFrame(() => root.classList.add("open")));
}

async function renderUptime(page) {
  const params = () => filterParams({ limit: 500, status: uptimeFilters.status, outlet_id: uptimeFilters.outlet || state.locationId });
  const [summary, episodes, offLoss] = await Promise.all([
    api(`/brands/${state.brandId}/uptime/summary`, filterParams()),
    api(`/brands/${state.brandId}/uptime/episodes`, params()),
    api(`/brands/${state.brandId}/uptime/loss`, filterParams()).catch(() => null),
  ]);
  const lossOf = new Map((offLoss?.outlets || []).map((o) => [o.outlet_id, o]));
  if (summary.uptime_pct == null && !episodes.length && !uptimeFilters.status && !uptimeFilters.outlet) {
    page.innerHTML = `<div class="card empty-state">${icon("store_uptime")}
      <h3>No uptime checks for this period</h3>
      <p>Store uptime is checked live on Zomato every 5 minutes during opening hours. Numbers appear here after the first checks of this period.</p></div>`;
    return;
  }
  const cityMap = new Map();
  summary.outlets.forEach((o) => {
    const c = cityMap.get(o.city || "Other") || { name: o.city || "Other", outlets: 0, off: 0, checks: 0, online: 0 };
    c.outlets++; c.off += o.offline_since ? 1 : 0; c.checks += o.checks || 0; c.online += o.online || 0; cityMap.set(c.name, c);
  });
  const cityList = [...cityMap.values()].map((c) => ({ ...c, pct: c.checks ? (100 * c.online) / c.checks : null }))
    .sort((a, b) => (a.pct ?? 101) - (b.pct ?? 101));
    const shown = uptimeCity ? summary.outlets.filter((o) => (o.city || "Other") === uptimeCity) : summary.outlets;
  // one square per day needs two or more days: for a one-day period (Today / Yesterday, which the other pages share), show the last 7 days instead
  let dayOf = (o) => o.days || {};
  let squaresNote = "";
  if (new Set(summary.outlets.flatMap((o) => Object.keys(o.days || {}))).size <= 1) {
    const end = new Date(), start = new Date(); start.setDate(end.getDate() - 6);
    try {
      const week = await api(`/brands/${state.brandId}/uptime/summary`, filterParams({ start: isoDate(start), end: isoDate(end) }));
      const byId = new Map(week.outlets.map((o) => [o.id, o.days || {}]));
      dayOf = (o) => byId.get(o.id) || {};
      squaresNote = "last 7 days, ";
    } catch { /* keep the one-day view */ }
  }
  const dayList = [...new Set(summary.outlets.flatMap((o) => Object.keys(dayOf(o))))].sort();
  const upColor = (v) => (v == null ? "#e6e9ef" : v >= 95 ? "#12a150" : v >= 85 ? "#7ccf8e" : v >= 70 ? "#f5a524" : "#e5484d");
  page.innerHTML = `
    <div class="so-hero">
      <div><span class="so-live"><i></i> Live</span>
        <div class="so-big">${inr.format(summary.offline_now)}<small> outlet${summary.offline_now === 1 ? "" : "s"} offline right now</small></div>
        ${offLoss && offLoss.high > 0 ? `<p><button class="lp-btn" id="lossBtn" type="button"><span>₹</span> Check estimated revenue loss <i>›</i></button></p>` : ""}
        <p>Zomato · during opening hours · ${summary.last_checked_at ? `last checked ${timeAgo(summary.last_checked_at)}` : "no checks yet"}</p>
        <p>${plural(summary.events, "offline event")} · avg downtime ${downtimeText(summary.avg_downtime) || (summary.offline_now ? "n/a, none back yet" : "—")} · total ${downtimeText(summary.total_downtime) || "0m"}</p></div>
      <div class="so-now">Uptime<b>${summary.uptime_pct == null ? "—" : `${summary.uptime_pct.toFixed(1)}%`}</b></div>
    </div>

    <div class="so-section"><h3>Cities <small>uptime in this period · click a city to filter its outlets</small></h3>
      <div class="so-rank">${cityList.map((c) => `
        <button class="so-rank-row ${uptimeCity === c.name ? "on" : ""}" data-ucity="${esc(c.name)}">
          <span>${esc(c.name)} <small class="muted">${plural(c.outlets, "outlet")}</small>${c.off ? ` <em class="uptime-off">${c.off} offline</em>` : ""}</span>
          <span class="so-bar"><i style="width:${c.pct == null ? 0 : 100 - c.pct}%;--tone:var(--red)"></i></span>
          <b class="${c.off ? "bad" : "ok"}">${c.pct == null ? "—" : `${c.pct.toFixed(1)}%`}</b></button>`).join("")}</div></div>

    <div class="so-section"><h3>Outlets <small>${dayList.length > 1 ? `${squaresNote}daily uptime, one square per day` : "uptime in this period"}, worst first · ${uptimeAll ? `all ${shown.length}` : `worst ${Math.min(UP_TOP, shown.length)} of ${shown.length}`}${uptimeCity ? ` in ${esc(uptimeCity)}` : ""} · click to filter</small></h3>
      <div class="up-heat">${(uptimeAll ? shown : shown.slice(0, UP_TOP)).map((o) => `
        <button class="up-row ${String(uptimeFilters.outlet) === String(o.id) ? "on" : ""}" data-outlet="${o.id}" title="${esc(o.name)}">
          <span class="up-name">${esc(o.name)} <small class="muted">${esc(o.city || "")}</small>${o.offline_since ? ' <em class="uptime-off">offline</em>' : ""}${lossOf.get(o.id) ? ` <small class="up-loss" data-loss="${o.id}" role="button" tabindex="0">Check estimated revenue loss ›</small>` : ""}${o.zomato_hours ? ` <small class="up-zh" title="Zomato's own count of hours this outlet was offline in this period">Zomato: ${o.zomato_hours.toFixed(1)} h offline</small>` : ""}</span>
          ${dayList.length > 1 ? `<span class="up-cells">${dayList.map((d) => { const v = dayOf(o)[d], zh = (o.zomato_days || {})[d]; const zc = zh == null ? null : zh >= 3 ? "#e5484d" : zh >= 0.5 ? "#f5a524" : "#cfe8d6";
          const day = new Date(d).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
          const what = v == null ? (zh != null ? "none of our checks that day" : "no checks recorded that day") : `${v.toFixed(1)}% uptime (${v >= 95 ? "online all day" : v >= 85 ? "a little downtime" : v >= 70 ? "some downtime" : "mostly offline"})`;
          return `<i style="background:${v == null && zc ? zc : upColor(v)}" title="${esc(o.name)}\n${day}\n${what}${zh != null ? `\nZomato's own count: ${zh.toFixed(1)} h offline` : ""}"></i>`; }).join("")}</span>` : ""}
          <b class="${o.offline_since ? "bad" : "ok"}">${o.uptime_pct == null ? "—" : `${o.uptime_pct.toFixed(1)}%`}</b></button>`).join("")}</div>
      ${shown.length > UP_TOP ? `<button class="btn light" id="uAll" style="margin-top:8px">${uptimeAll ? "Show fewer" : `Show all ${shown.length}`}</button>` : ""}</div>

    <div class="card so-list">
      <div class="toolbar">
        <div class="segmented" id="uStatus">${[["", "All"], ["active", "Offline now"], ["restored", "Back online"]]
          .map(([v, l]) => `<button data-v="${v}" class="${uptimeFilters.status === v ? "active" : ""}">${l}</button>`).join("")}</div>
        <button class="btn light" id="uClear" ${uptimeFilters.outlet ? "" : "hidden"}>Clear filter</button>
      </div>
      ${episodes.length ? `<table><thead><tr><th>Outlet</th><th>Status</th><th>Went offline</th><th>Back online</th><th title="Only the minutes the store was meant to be open are counted, so time offline while closed (for example overnight) is left out.">Downtime (open hours) ⓘ</th></tr></thead>
        <tbody>${episodes.map((e) => `<tr>
          <td>${esc(e.outlet_name.split(" · ").slice(1).join(" · ") || e.outlet_name)}${e.zomato_id ? ` <span class="muted">${esc(e.zomato_id)}</span>` : ""}</td>
          <td><span class="status ${e.is_active ? "pending" : "replied"}">${e.is_active ? "Offline" : "Back"}</span></td>
          <td class="muted">${new Date(e.first_detected_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}</td>
          <td class="muted">${e.restored_at ? new Date(e.restored_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "—"}</td>
          <td>${offlineFor(e)}</td></tr>`).join("")}</tbody></table>`
        : `<div class="empty-state"><h3>No offline events match</h3><p>Every checked outlet stayed online.</p></div>`}
    </div>`;
  // the revenue-loss panel: from the header button, or from an outlet's own link (which must not also filter the list)
  $("#lossBtn")?.addEventListener("click", () => openLossPanel(offLoss));
  page.querySelectorAll("[data-loss]").forEach((b) => {
    const open = (e) => { e.stopPropagation(); e.preventDefault(); openLossPanel(offLoss, b.dataset.loss); };
    b.addEventListener("click", open); b.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") open(e); });
  });
  page.querySelectorAll("[data-outlet]").forEach((b) => b.addEventListener("click", () => {
    uptimeFilters.outlet = String(uptimeFilters.outlet) === b.dataset.outlet ? "" : b.dataset.outlet;
    renderUptime(page);
  }));
  page.querySelectorAll("[data-ucity]").forEach((b) => b.addEventListener("click", () => {
    uptimeCity = uptimeCity === b.dataset.ucity ? "" : b.dataset.ucity; uptimeAll = false; renderUptime(page);
  }));
  $("#uStatus").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    uptimeFilters.status = b.dataset.v;
    renderUptime(page);
  });
  $("#uClear").addEventListener("click", () => { uptimeFilters.outlet = ""; renderUptime(page); });
  $("#uAll")?.addEventListener("click", () => { uptimeAll = !uptimeAll; renderUptime(page); });
}

// best sellers that are out now, valued from the outlet's own order history (a range: the low end assumes some customers pick another dish),
// and orders turned away because an item was out (a measured loss, not an estimate)
let lossItems = [];
function topSellerStrip(summary, periodWord = "in this period") {
  lossItems = summary.period_loss?.items || [];
  const t = summary.top_sellers_out, rej = summary.stock_rejections, per = summary.period_loss;
  const hasPer = !!(per && per.high);
  const items = hasPer ? per.items : (t?.items || []);
  if (!items.length && !(rej && rej.orders)) return `<div class="so-loss"><div class="so-loss-main"><span class="so-loss-label">Best sellers lost to stock-outs</span><small>none ${esc(periodWord)}, or not enough order history to value them</small></div></div>`;
  const range = (lo, hi) => (hi ? `${rupeesShort(lo)} – ${rupeesShort(hi)}` : "");
  const since = (ts) => new Date(ts).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hour12: true });
  return `<div class="so-loss">
    ${items.length ? `<div class="so-loss-main"><span class="so-loss-label">${hasPer ? "Sales lost on your best dishes" : "Best dishes out right now"}</span>
        ${(() => {
          const lo = hasPer ? per.low : t?.low, hi = hasPer ? per.high : t?.high;
          if (!hi) return `<p class="sl-sub">Not enough order history yet to put a value on them.</p>`;
          return `<div class="sl-head"><b class="sl-big">${rupeesShort(Math.round((lo + hi) / 2))}</b>
            <span class="sl-sub">about, ${hasPer ? esc(periodWord) : "so far today"} <span class="muted">(somewhere between ${rupeesShort(lo)} and ${rupeesShort(hi)})</span></span></div>`;
        })()}
        ${hasPer && t?.items?.length ? `<p class="sl-now"><b>${plural(t.items.length, "best dish", "best dishes")}</b> ${t.items.length === 1 ? "is" : "are"} out right now${t.high ? `, costing about <b>${rupeesShort(Math.round((t.low + t.high) / 2))}</b> so far today` : ""}.</p>` : ""}
        <div class="so-loss-items sl-list" id="lossItems">${(() => {
          const top = Math.max(...items.map((x) => x.high || 0), 1);
          return items.slice(0, 20).map((i) => {
            const priced = (hasPer || i.enough_history) && i.high;
            const click = hasPer && i.episodes?.length;
            return `<div class="sl-row ${click ? "clickable" : ""}" ${click ? `data-lossitem="${esc(i.item_name)}" role="button" tabindex="0"` : ""}>
              <div class="sl-name"><b>${esc(i.item_name)}</b><small>${plural(i.outlets, "outlet")}${i.price ? ` · ₹${inr.format(i.price)} each` : ""}</small></div>
              <div class="sl-bar"><i style="width:${priced ? Math.max(4, (100 * i.high) / top) : 0}%"></i></div>
              <b class="sl-amt">${priced ? rupeesShort(Math.round((i.low + i.high) / 2)) : "—"}</b></div>`;
          }).join("");
        })()}</div>
        ${items.length > 5 ? `<button type="button" class="sl-more" id="lossMore" data-n="${Math.min(items.length, 20) - 5}">Show ${Math.min(items.length, 20) - 5} more dishes</button>` : ""}
        <div class="so-loss-detail" id="lossDetail" hidden></div>
        ${rej && rej.orders ? `<div class="sl-rej"><span><b>${plural(rej.orders, "order")}</b> turned away because dishes were out of stock · <b>${rupeesShort(rej.value)}</b> <span class="muted">(measured)</span></span>
          <button type="button" class="sl-more" id="rejMore">Details</button></div>
          <div class="sl-rej-detail" id="rejDetail" hidden>
            ${(rej.by_platform && Object.keys(rej.by_platform).length) ? `<p class="muted" style="margin:0 0 4px">${Object.entries(rej.by_platform).map(([k, v]) => `${k === "swiggy" ? "Swiggy" : "Zomato"} ${plural(v, "order")}`).join(" · ")}</p>` : ""}
            ${(rej.by_outlet || []).map((o) => `<div class="sl-rej-row"><span>${esc(o.outlet)}</span><span><b>${plural(o.orders, "order")}</b> · ${rupeesShort(o.value)}</span></div>`).join("")}
            <p class="muted" style="margin:6px 0 0">Orders the platform rejected or cancelled because an item was out of stock, from your order history.</p>
          </div>` : ""}
        <p class="so-loss-note"><span class="so-how" tabindex="0">How is this estimated?
          <span class="so-how-body">
            <span class="so-how-title">How this is estimated</span>
            <span class="so-how-line">1. For each outlet we find its best sellers: the dishes that make up most of its sales in the last 30 days of orders.</span>
            <span class="so-how-line">2. For each dish we work out how many it normally sells in each mealtime, using only the days it was in stock.</span>
            <span class="so-how-line">3. For every hour the dish was out, we count the sales it would normally have made in that mealtime.</span>
            <span class="so-how-line">4. We multiply by the dish's latest price. That is the high end.</span>
            <span class="so-how-line">5. The low end is 40% of that, because some customers order something else instead.</span>
            <span class="so-how-note">Example: a burger that normally sells 6 at lunch, out for all of lunch at ₹200, shows ₹480 – ₹1,200.</span>
            <span class="so-how-note">Each platform (Zomato, Swiggy) is valued with its own orders. Dishes with under 7 in-stock days of history get no figure. Each stock-out counts for at most its first 3 days; any days after that are not counted, because the dish may have been taken off the menu.</span>
          </span></span></p></div>` : ""}
    ${rej && rej.orders && !items.length ? `<div class="so-loss-side"><b>${plural(rej.orders, "order")}</b><small>turned away for items out of stock in this period · ${rupees(rej.value)} in orders (measured, not estimated)</small></div>` : ""}
  </div>`;
}

// click a dish in the loss box: every stock-out of it in the period, when it went out and came back, hours out, and the sales it cost
function showLossDetail(name) {
  const box = $("#lossDetail"), it = lossItems.find((x) => x.item_name === name);
  if (!box || !it) return;
  if (!box.hidden && box.dataset.item === name) { box.hidden = true; return; }  // click again to close
  const at = (ts) => new Date(ts).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hour12: true });
  const hrs = (h) => (h >= 48 ? `${Math.round(h / 24)} days` : h >= 1 ? `${Math.round(h)} h` : `${Math.round(h * 60)} min`);
  const meals = (m) => Object.entries(m || {}).map(([k, [lo, hi]]) => `${esc(k)} ${rupees(lo)}–${rupees(hi)}`).join(" · ") || "—";
  box.dataset.item = name;
  box.innerHTML = `<div class="so-loss-detail-head"><b>${esc(name)}</b> <span class="muted">${plural(it.episode_count, "stock-out")} in this period · ${rupees(it.low)} – ${rupees(it.high)} estimated sales lost</span>
      <button class="btn light" data-closeloss>Close</button></div>
    <table class="cp-table"><thead><tr><th>Outlet</th><th>Went out</th><th>Back</th><th>Out for</th><th class="num">Sales lost</th><th>By mealtime</th></tr></thead><tbody>
      ${it.episodes.map((e) => `<tr><td>${esc(e.outlet)}</td><td>${esc(at(e.from))}</td><td>${e.back ? esc(at(e.back)) : '<b class="bad">still out</b>'}</td><td>${hrs(e.hours)}${e.counted_hours < e.hours - 0.5 ? `<small class="muted"> · counted ${hrs(e.counted_hours)}</small>` : ""}</td>
        <td class="num">${e.negligible ? `<span class="muted" title="Under 5% of a normal day's sales of this dish here (about ${e.daily_units} a day). Estimated ${rupees(e.low)} – ${rupees(e.high)}">Negligible</span>` : `<b>${rupees(e.low)} – ${rupees(e.high)}</b>`}</td><td class="muted">${meals(e.meals)}</td></tr>`).join("")}</tbody></table>
    ${it.episode_count > it.episodes.length ? `<p class="muted">Showing the ${it.episodes.length} biggest of ${it.episode_count} stock-outs.</p>` : ""}
    <p class="muted">Estimate: what this dish normally sells in each mealtime at that outlet, for the hours it was out, at its latest price. The low end assumes 6 in 10 of those customers order something else. Each stock-out counts for at most its first 3 days, and times before the period start are cut off.</p>`;
  box.hidden = false;
}
document.addEventListener("click", (e) => {
  const more = e.target.closest("#lossMore");
  if (more) {
    const open = $("#lossItems").classList.toggle("open");
    more.textContent = open ? "Show fewer dishes" : `Show ${more.dataset.n} more dishes`;
    return;
  }
  const rejBtn = e.target.closest("#rejMore");
  if (rejBtn) { const box = $("#rejDetail"); box.hidden = !box.hidden; rejBtn.textContent = box.hidden ? "Details" : "Hide details"; return; }
  const chip = e.target.closest("[data-lossitem]");
  if (chip) return showLossDetail(chip.dataset.lossitem);
  if (e.target.closest("[data-closeloss]")) $("#lossDetail").hidden = true;
});
document.addEventListener("keydown", (e) => {
  const chip = e.key === "Enter" && e.target.closest?.("[data-lossitem]");
  if (chip) showLossDetail(chip.dataset.lossitem);
});

// ---------- stock-outs ----------
const MEALS = [
  { name: "Breakfast", hours: "5 am – 12 pm", from: 5, to: 12, tone: "#f5a524" },
  { name: "Lunch", hours: "12 – 4 pm", from: 12, to: 16, tone: "#e5484d" },
  { name: "Evening Snacks", hours: "4 – 7 pm", from: 16, to: 19, tone: "#a855f7" },
  { name: "Dinner", hours: "7 – 11 pm", from: 19, to: 23, tone: "#d9480f" },
  { name: "Late Night Dinner", hours: "11 pm – 5 am", from: 23, to: 29, tone: "#0b1229" },
];
const stockFilters = { status: "active", q: "", meal: "", outlet: "", city: "" };
let stockRows = [];
let stockShowMinor = false;
let stockAllOutlets = false;
const TOP_OUTLETS = 10;
// a dish that is back, was never out long and cost next to nothing is noise in the list: folded away until asked for
const MINOR_MINUTES = 15, MINOR_RUPEES = 100;

function currentMeal() {
  let h = Number(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata", hour: "numeric", hour12: false })) % 24;
  if (h < 5) h += 24;
  return (MEALS.find((m) => h >= m.from && h < m.to) || MEALS[4]).name;
}
const downtimeText = (m) => (m == null ? "" : m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m}m`);

async function renderStockOuts(page) {
  const [summary, rows] = await Promise.all([
    api(`/brands/${state.brandId}/stock-outs/summary`, filterParams()),
    // active rows sort first, so ask for each kind separately or the restored ones fall off the end
    Promise.all([
      api(`/brands/${state.brandId}/stock-outs`, filterParams({ status: "out", limit: 5000 })),
      api(`/brands/${state.brandId}/stock-outs`, filterParams({ status: "restored", limit: 5000 })),
    ]).then(([a, r]) => [...a, ...r]),
  ]);
  stockRows = rows;
  stockShowMinor = false;
  const now = currentMeal();
  const restored = summary.restored;
  const { start, end } = range();
  const isToday = start === end;
  const hasToday = end === isoDate(new Date());  // "now" only means something when the period runs to today
  // cards: with today in the period, what is out right now by the meal it went out in (+ how many went out today);
  // for a past period, what went out in it
  const mealNum = (m) => m.count;
  const maxMeal = Math.max(1, ...summary.by_meal.map(mealNum));
  const periodWord = !isToday ? "in this period" : hasToday ? "today" : `on ${dayLabel(end)}`;
  const outlets = new Map();
  rows.forEach((r) => {
    const o = outlets.get(r.outlet_id) || { id: r.outlet_id, name: r.outlet_name, city: r.city || "Other", out: 0, total: 0 };
    o.total++; if (r.is_active) o.out++;
    outlets.set(r.outlet_id, o);
  });
  const outletList = [...outlets.values()].sort((a, b) => b.out - a.out || b.total - a.total);
  // cities first; a city's outlets on click (the worst few, the rest on request)
  const cities = new Map();
  outletList.forEach((o) => {
    const c = cities.get(o.city) || { name: o.city, out: 0, outlets: 0 };
    c.out += o.out; c.outlets++; cities.set(o.city, c);
  });
  const cityList = [...cities.values()].sort((a, b) => b.out - a.out || a.name.localeCompare(b.name));
  const maxCity = Math.max(1, ...cityList.map((c) => c.out));
  const cityOutlets = outletList.filter((o) => o.city === stockFilters.city);
  const maxOut = Math.max(1, ...cityOutlets.map((o) => o.out));
  const shownOutlets = stockAllOutlets ? cityOutlets
    : cityOutlets.filter((o, i) => (i < TOP_OUTLETS && o.out) || String(o.id) === String(stockFilters.outlet));

  page.innerHTML = `
    <div class="so-hero">
      <div><span class="so-live"><i></i> Live</span>
        <div class="so-big">${inr.format(summary.active - summary.long_off)}<small> items out of stock right now</small></div>
        <p>across ${summary.outlets_affected} outlet${summary.outlets_affected === 1 ? "" : "s"} · ${inr.format(restored)} back in stock · avg downtime ${downtimeText(summary.avg_downtime) || "—"}${summary.long_off ? ` · <b>${inr.format(summary.long_off)}</b> more off for ${summary.long_off_days}+ days (listed separately)` : ""}</p>
        ${SHOW_STOCK_LOSS ? `<p class="so-lost" title="Estimate: each item's usual sales for the hours it was out, using the outlet's own hour-by-hour order pattern${summary.lost_unpriced ? `. ${summary.lost_unpriced} stock-outs have no sales history, so no ₹` : ""}">
          <b>${rupees(summary.lost_sales)}</b> of sales missed in this period <small>(estimate)</small></p>` : ""}</div>
      ${hasToday ? `<div class="so-now">Now serving<b>${now}</b></div>` : ""}
    </div>

    ${topSellerStrip(summary, periodWord)}

    <div class="so-section"><h3>By mealtime <small data-tip="Items out ${periodWord}, counted under the first meal each went out in. Hover a tile for the sales lost in that meal; click it to filter.">items out ${periodWord}</small></h3>
      <div class="so-meals">${summary.by_meal.map((m) => {
        const meta = MEALS.find((x) => x.name === m.meal);
        const ml = summary.period_loss?.by_meal?.[m.meal];
        return `<button class="so-meal ${stockFilters.meal === m.meal ? "on" : ""} ${hasToday && m.meal === now ? "now" : ""}" data-meal="${m.meal}" style="--tone:${meta.tone}"${ml && ml.high ? ` data-tip="Best-seller sales lost in ${m.meal.toLowerCase()} hours: ${rupeesShort(ml.low)} – ${rupeesShort(ml.high)}"` : ""}>
          ${hasToday && m.meal === now ? '<em>NOW</em>' : ""}<span class="so-meal-name">${m.meal}</span><span class="so-meal-hours">${meta.hours}</span>
          <b>${inr.format(mealNum(m))}</b>
          <span class="so-bar"><i style="width:${(mealNum(m) / maxMeal) * 100}%"></i></span>
</button>`;
      }).join("")}</div>
      ${summary.long_off ? `<button class="so-earlier ${stockFilters.status === "long" ? "on" : ""}" id="sLong"><b>+${inr.format(summary.long_off)}</b> off for ${summary.long_off_days}+ days · may be removed from the menu${summary.long_off_top_sellers?.length ? ` · ${summary.long_off_top_sellers.length} top sellers ▾` : ""}</button>` : ""}
      ${summary.long_off_top_sellers?.length ? `<div class="so-long-top" id="longTop" hidden><b>Top sellers off ${summary.long_off_days}+ days:</b> ${summary.long_off_top_sellers.map((t) => `<span class="so-chip out" data-tip="out at ${plural(t.outlets, "outlet")}, longest ${t.days} days">${esc(t.item_name)} · ${t.days}d</span>`).join("")}<button class="so-link" id="sLongList">See all ${inr.format(summary.long_off)} items</button></div>` : ""}</div>

    ${outletList.length > 1 ? `<div class="so-section">${stockFilters.city
      ? `<h3><button class="so-back" id="sCities">‹ All cities</button> ${esc(stockFilters.city)} <small>items out of stock now · click an outlet to filter</small></h3>`
      : `<h3>Cities <small>items out of stock now · click a city for its outlets</small></h3>`}
      <div class="so-rank">${stockFilters.city ? shownOutlets.map((o) => `
        <button class="so-rank-row ${String(stockFilters.outlet) === String(o.id) ? "on" : ""}" data-outlet="${o.id}" title="${esc(o.name)}">
          <span>${esc(o.name.split(" · ").pop())}</span><span class="so-bar"><i style="width:${(o.out / maxOut) * 100}%"></i></span>
          <b class="${o.out ? "bad" : "ok"}">${o.out}</b></button>`).join("")
        : cityList.map((c) => `
        <button class="so-rank-row" data-city="${esc(c.name)}">
          <span>${esc(c.name)} <small class="muted">${plural(c.outlets, "outlet")}</small></span><span class="so-bar"><i style="width:${(c.out / maxCity) * 100}%"></i></span>
          <b class="${c.out ? "bad" : "ok"}">${inr.format(c.out)}</b></button>`).join("")}</div>
      ${!stockFilters.city ? "" : shownOutlets.length < cityOutlets.length ? `<button class="btn light so-more" id="sAllOutlets">Show all ${cityOutlets.length} outlets</button>`
        : stockAllOutlets && cityOutlets.length > TOP_OUTLETS ? `<button class="btn light so-more" id="sAllOutlets">Show top ${TOP_OUTLETS}</button>` : ""}</div>` : ""}

    <div class="card so-list">
      <div class="toolbar">
        <input id="sq" type="search" placeholder="Search item…" value="${esc(stockFilters.q)}">
        <div class="segmented" id="sStatus">${[["active", `Out now (${inr.format(summary.active - summary.long_off)})`],
          ["new", isToday ? `New ${periodWord}` : "New in period"], ["restored", "Back"], ["long", `Off ${summary.long_off_days}+ days${summary.long_off ? ` (${inr.format(summary.long_off)})` : ""}`]]
          .map(([v, l]) => `<button data-v="${v}" class="${stockFilters.status === v ? "active" : ""}">${l}</button>`).join("")}</div>
        <button class="btn light" id="sClear" ${stockFilters.meal || stockFilters.outlet || stockFilters.city ? "" : "hidden"}>Clear filters</button>
        <button class="btn blue" id="sExport">Export to Excel</button>
      </div>
      <div id="stockList"></div>
    </div>`;

  page.querySelectorAll("[data-meal]").forEach((b) => b.addEventListener("click", () => {
    stockFilters.meal = stockFilters.meal === b.dataset.meal ? "" : b.dataset.meal;
    if (stockFilters.meal) stockFilters.status = hasToday ? "active" : "new";
    renderStockOuts(page);
  }));
  page.querySelectorAll("[data-outlet]").forEach((b) => b.addEventListener("click", () => {
    stockFilters.outlet = String(stockFilters.outlet) === b.dataset.outlet ? "" : b.dataset.outlet; renderStockOuts(page);
  }));
  page.querySelectorAll("[data-city]").forEach((b) => b.addEventListener("click", () => {
    stockFilters.city = b.dataset.city; stockFilters.outlet = ""; stockAllOutlets = false; renderStockOuts(page);
  }));
  $("#sCities")?.addEventListener("click", () => { stockFilters.city = ""; stockFilters.outlet = ""; renderStockOuts(page); });
  $("#sAllOutlets")?.addEventListener("click", () => { stockAllOutlets = !stockAllOutlets; renderStockOuts(page); });
  $("#sExport").addEventListener("click", () => exportStockOuts($("#sExport")));
  $("#sClear").addEventListener("click", () => {
    stockFilters.meal = ""; stockFilters.outlet = ""; stockFilters.city = "";
    renderStockOuts(page);
  });
  const showLong = () => { stockFilters.status = "long"; stockFilters.meal = ""; renderStockOuts(page); };
  $("#sLongList")?.addEventListener("click", showLong);
  $("#sLong")?.addEventListener("click", () => { const top = $("#longTop"); if (top) top.hidden = !top.hidden; else showLong(); });
  $("#sStatus").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    stockFilters.status = b.dataset.v;
    $("#sStatus .active").classList.remove("active"); b.classList.add("active"); drawStockItems();
  });
  let timer;
  $("#sq").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { stockFilters.q = e.target.value; drawStockItems(); }, 200); });
  drawStockItems();
}

// Download what the page is showing (same filters) as an .xlsx
async function exportStockOuts(btn) {
  btn.disabled = true; const label = btn.textContent; btn.textContent = "Preparing…";
  try {
    const url = new URL(`${API}/brands/${state.brandId}/stock-outs/export`, location.origin);
    Object.entries(filterParams({ status: stockFilters.status, mealtime: stockFilters.meal, q: stockFilters.q,
      outlet_id: stockFilters.outlet || state.locationId })).forEach(([k, v]) => { if (v !== "" && v != null) url.searchParams.set(k, v); });
    const res = await apiFetch(url);
    if (!res.ok) throw userError("The file couldn't be made right now. Please try again in a moment.");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await res.blob());
    a.download = `stock-outs_${new Date().toISOString().slice(0, 10)}.xlsx`;
    a.click(); URL.revokeObjectURL(a.href);
  } catch (e) { toast(userMessage(e)); }
  btn.disabled = false; btn.textContent = label;
}

// Status tabs. Items off for days have their own tab so they don't drown out today's stock-outs.
function statusMatch(r) {
  switch (stockFilters.status) {
    case "restored": return !r.is_active;
    case "long": return r.long_off;
    case "active": return r.is_active && !r.long_off;
    case "new": return !r.earlier && !r.long_off;
    default: return true;
  }
}

// One line per dish: which outlets it is out at, in which meal, and for how long.
function drawStockItems() {
  const q = stockFilters.q.toLowerCase();
  const rows = stockRows.filter((r) =>
    statusMatch(r) &&
    (!stockFilters.meal || (r.range_meals || []).includes(stockFilters.meal)) &&
    (!stockFilters.outlet || String(r.outlet_id) === String(stockFilters.outlet)) &&
    (!stockFilters.city || r.city === stockFilters.city) &&
    (!q || r.item_name.toLowerCase().includes(q)));
  const byItem = new Map();
  rows.forEach((r) => { byItem.set(r.item_name, [...(byItem.get(r.item_name) || []), r]); });
  const all = [...byItem.entries()].map(([name, list]) => ({
    name, list, category: list[0].category, out: list.filter((r) => r.is_active).length,
    longest: Math.max(0, ...list.map((r) => r.downtime_minutes || 0)),
    lost: SHOW_STOCK_LOSS ? list.reduce((t, r) => t + (r.lost || 0), 0) : 0, priced: SHOW_STOCK_LOSS && list.some((r) => r.lost != null),
  })).sort((a, b) => b.out - a.out || b.lost - a.lost || b.list.length - a.list.length || a.name.localeCompare(b.name));
  const minor = (it) => !it.out && it.longest < MINOR_MINUTES && it.lost < MINOR_RUPEES;
  const hidden = stockFilters.q || stockShowMinor ? 0 : all.filter(minor).length;
  const items = hidden ? all.filter((it) => !minor(it)) : all;
  const short = (n) => esc(n.split(" · ").pop());
  const clock = (ts) => (ts ? new Date(ts).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hour12: true }) : "—");
  const { start: pStart, end: pEnd } = range();
  const inPeriod = pStart === pEnd ? (pEnd === isoDate(new Date()) ? "today" : `on ${dayLabel(pEnd)}`) : "in period";
  const comesBack = (t) => (t ? esc(t.replace(/^out of stock till\s*/i, "")) : "");
  // one expandable line per dish; the detail lists every episode with exact out / back times
  const detail = (it) => `<table class="so-detail"><thead><tr><th>Outlet</th><th>Meal</th><th>Went out</th><th>Back in</th><th class="num">Out ${inPeriod}</th>${SHOW_STOCK_LOSS ? '<th class="num">Sales missed</th>' : ""}<th>Platform says back</th></tr></thead><tbody>
    ${[...it.list].sort((x, y) => new Date(y.first_detected_at) - new Date(x.first_detected_at)).map((r) => `<tr>
      <td>${short(r.outlet_name)} <small class="muted">${r.platform === "swiggy" ? "Swiggy" : "Zomato"}</small></td><td>${esc(r.mealtime)}</td>
      <td title="${clock(r.first_detected_at)}">${r.earlier ? `<span class="muted">before ${pStart === pEnd ? dayLabel(pStart) : "period"}</span>` : clock(r.first_detected_at)}</td>
      <td>${r.is_active ? '<span class="status pending">still out</span>' : clock(r.restored_at)}</td>
      <td class="num">${r.period_minutes == null ? "—" : `${downtimeText(r.period_minutes) || "0m"}${r.is_active ? " so far" : ""}`}</td>
      ${!SHOW_STOCK_LOSS ? "" : `<td class="num">${r.lost == null ? '<span class="muted" title="No sales history for this item">—</span>' : rupees(r.lost)}</td>`}
      <td class="muted">${comesBack(r.back_at) || "—"}</td></tr>`).join("")}</tbody></table>`;
  const more = hidden ? `<button class="btn light so-minor" id="sMinor">Show ${hidden} minor stock-out${hidden === 1 ? "" : "s"} (back within ${MINOR_MINUTES} min, under ₹${MINOR_RUPEES})</button>` : "";
  $("#stockList").innerHTML = (items.length ? `<div class="so-count muted">${items.length} dish${items.length === 1 ? "" : "es"} · click a dish for exact times</div>` + items.map((it, i) => `
    <div class="so-item" data-i="${i}">
      <div class="so-item-main"><b>${esc(it.name)}</b>${it.category ? `<span class="so-cat">${esc(it.category)}</span>` : ""}</div>
      <div class="so-item-outlets">${it.list.slice(0, 4).map((r) => `<span class="so-chip ${r.is_active ? "out" : "back"}" title="${esc(r.mealtime)} · went out ${clock(r.first_detected_at)}${r.is_active ? "" : ` · back ${clock(r.restored_at)}`}${r.back_at ? ` · ${r.platform === "swiggy" ? "Swiggy" : "Zomato"} says back ${comesBack(r.back_at)}` : ""}">${short(r.outlet_name)}<small>${esc(r.mealtime)} · ${r.platform === "swiggy" ? "Swiggy" : "Zomato"}</small></span>`).join("")}
        ${it.list.length > 4 ? `<span class="so-chip more">+${it.list.length - 4} more</span>` : ""}</div>
      <div class="so-item-lost num">${!SHOW_STOCK_LOSS ? "" : it.priced ? `<b>${rupees(it.lost)}</b><small class="muted">missed</small>` : '<span class="muted" title="No sales history for this item">—</span>'}</div>
      <div class="so-item-state">${it.out ? `<span class="status pending">${it.out} out</span>` : `<span class="status replied">back</span>`}
        <small class="muted">${it.out ? `longest out ${timeAgo(it.list.filter((r) => r.is_active).reduce((a, r) => (new Date(r.first_detected_at) < new Date(a.first_detected_at) ? r : a)).first_detected_at).replace(" ago", "")}` : `down ${downtimeText(it.longest)}`}</small></div>
      <div class="so-item-more" hidden>${detail(it)}</div>
    </div>`).join("") : `<div class="empty-state"><h3>${stockFilters.q ? "No stock-outs match these filters" : stockFilters.status === "new" ? "No new stock-outs in this period" : stockFilters.status === "active" ? "Nothing is out of stock right now" : "No stock-outs match these filters"}</h3></div>`) + more;
  $("#sMinor")?.addEventListener("click", () => { stockShowMinor = true; drawStockItems(); });
  $("#stockList").querySelectorAll(".so-item").forEach((row) => row.addEventListener("click", (e) => {
    if (e.target.closest(".so-item-more")) return;  // clicks inside the detail table do not collapse it
    const more = row.querySelector(".so-item-more");
    more.hidden = !more.hidden;
    row.classList.toggle("open", !more.hidden);
  }));
}

// ---------- setup: clients, brands & outlet mapping ----------
// Platform ids are never typed: every Zomato / Swiggy / Google id is picked from the synced catalog.
const PICK_PLATFORMS = [
  { code: "zomato", label: "Zomato" },
  { code: "swiggy", label: "Swiggy" },
  { code: "google", label: "Google" },
];
const setup = { rows: [], deleted: [], filter: "", dirty: false, bulkPlatform: "zomato", bulkSelected: new Map(), pairs: [] };

async function renderSetup(page, { creating = false } = {}) {
  const [industries, clients, data] = await Promise.all([
    api("/industries"), api("/clients"), creating ? null : api(`/brands/${state.brandId}/outlets`),
  ]);
  const brand = creating ? null : state.config.brand;
  const staff = state.me.is_staff;
  const first = creating && !state.brands.length;
  setup.rows = creating ? [] : data.outlets.map((o) => ({ ...o, labels: { ...o.labels } }))
    .sort((a, b) => (a.area || "").toLowerCase().localeCompare((b.area || "").toLowerCase()) || (a.city || "").localeCompare(b.city || ""));  // same-area rows sit together
  setup.pairs = [];
  setup.deleted = []; setup.filter = ""; setup.dirty = false; setup.bulkSelected.clear();

  page.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div class="card-head">
        <h3>${creating ? "New brand" : "Brand"}</h3>
        ${creating ? (first ? "" : `<button class="btn light" id="cancelNew">Cancel</button>`) : `<button class="btn light" id="newBrand">${icon("plus")} New brand</button>`}
      </div>
      <div class="form-row">
        ${staff
          ? `<label>Client<select id="clientSelect">
              ${clients.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}
              <option value="__new">+ New client…</option></select></label>
            <label id="newClientWrap" hidden>New client name<input id="newClientName" placeholder="Company name"></label>`
          : `<label>Client<input value="${esc(state.me.client?.name || "")}" disabled></label>`}
        <label>Brand name<input id="brandName" value="${creating ? "" : esc(brand.name)}" placeholder="As the client wants it shown"></label>
        <label>Industry<select id="brandIndustryInput">${industries.map((i) => `<option value="${i.code}">${esc(i.name)}</option>`).join("")}</select></label>
        <button class="btn blue" id="saveBrand">${creating ? "Create brand" : "Save brand"}</button>
        ${creating ? "" : `<button class="btn light" id="archiveBrand" title="Hide this brand everywhere. Nothing is deleted.">Archive brand</button>`}
      </div>
    </div>
    ${creating ? "" : `
    <div class="card">
      <div class="card-head">
        <h3>Outlets &amp; platform IDs <span class="muted" id="outletCount"></span></h3>
        <div class="btn-row">
          <input id="outletSearch" type="search" placeholder="Search outlets…">
          <button class="btn light" id="toggleCsv">Bulk upload CSV</button>
          <button class="btn light" id="toggleBulk">${icon("plus")} Add from catalog</button>
          <button class="btn light" id="suggestLinks" title="Find Zomato-only and Swiggy-only rows that are probably the same kitchen">Suggested links</button>
          <button class="btn light" id="mergeRows" title="Combine Zomato-only and Swiggy-only rows that share an area">Merge same-area rows</button>
          <button class="btn light" id="addOutlet">${icon("plus")} Empty row</button>
          <button class="btn blue" id="saveOutlets">Save outlets</button>
        </div>
      </div>
      <div class="bulk-panel" id="bulkPanel" hidden>
        <div class="btn-row">
          <div class="segmented" id="bulkTabs">${PICK_PLATFORMS.map((p) => `<button data-p="${p.code}" class="${p.code === setup.bulkPlatform ? "active" : ""}">${p.label}</button>`).join("")}</div>
          <input id="bulkSearch" type="search" placeholder="Search unmapped outlets by name, area, city or ID…">
          <button class="btn" id="bulkAdd" disabled>Add selected</button>
        </div>
        <p class="muted" style="margin:0">${staff
          ? `All unassigned IDs from the master tables plus ${esc(brand?.client || "")}'s own are listed; saving assigns picked IDs to ${esc(brand?.client || "")}.`
          : `Only ${esc(brand?.client || "")}'s IDs that aren't used by a store yet are listed.`} Each one becomes a store row; then pick its other platform IDs.</p>
        <div class="bulk-results" id="bulkResults"></div>
      </div>
      <div class="bulk-panel" id="csvPanel" hidden>
        <div class="btn-row">
          <input type="file" id="csvFile" accept=".csv,text/csv">
          <button class="btn light" id="csvTemplate">Download template</button>
          <button class="btn blue" id="csvSave" disabled>Save</button>
        </div>
        <p class="muted" style="margin:0">Columns: <b>store_name, area, city, zomato_res_id, swiggy_id, google_location_id</b>.
          A store_name that already exists updates that store. Every row is checked first; nothing is saved unless all rows are valid.</p>
        <div id="csvResult"></div>
      </div>
      <div class="table-wrap"><table class="setup-table">
        <thead><tr><th>Outlet name</th><th>Area</th><th>City</th>${PICK_PLATFORMS.map((p) => `<th>${platformPill(p.code)}</th>`).join("")}<th></th></tr></thead>
        <tbody id="outletRows"></tbody>
      </table></div>
    </div>`}`;

  if (staff) $("#clientSelect").value = creating ? (setup.newBrandClientId ?? clients[0]?.id ?? "__new") : brand.client_id;
  if (creating) setup.newBrandClientId = null;
  if (staff) {
    const toggleNew = () => { $("#newClientWrap").hidden = $("#clientSelect").value !== "__new"; };
    $("#clientSelect").addEventListener("change", () => { toggleNew(); if (!$("#newClientWrap").hidden) $("#newClientName").focus(); });
    toggleNew();
  }
  $("#brandIndustryInput").value = creating ? "restaurant" : brand.industry_code;
  $("#saveBrand").addEventListener("click", () => saveBrand(creating));
  $("#archiveBrand")?.addEventListener("click", archiveBrand);
  lockIfViewer(page);
  if (creating) {
    $("#cancelNew")?.addEventListener("click", () => (state.config ? render() : (location.hash = "#/overview")));
    $("#brandName").focus();
    return;
  }
  $("#toggleCsv").addEventListener("click", () => { $("#csvPanel").hidden = !$("#csvPanel").hidden; });
  $("#csvTemplate").addEventListener("click", downloadTemplate);
  $("#csvFile").addEventListener("change", (e) => e.target.files[0] && previewCsv(e.target.files[0]));
  $("#csvSave").addEventListener("click", saveCsv);
  $("#newBrand").addEventListener("click", () => renderSetup(page, { creating: true }));
  $("#outletSearch").addEventListener("input", (e) => { setup.filter = e.target.value.toLowerCase(); renderOutletRows(); });
  $("#addOutlet").addEventListener("click", () => {
    setup.rows.unshift({ outlet_name: "", area: "", city: "", zomato: "", swiggy: "", google: "", labels: {} });
    setup.dirty = true; setup.filter = ""; $("#outletSearch").value = "";
    renderOutletRows(); $("#outletRows input")?.focus();
  });
  $("#saveOutlets").addEventListener("click", () => saveOutlets(false));
  $("#outletRows").addEventListener("input", (e) => {
    const input = e.target.closest("input[data-field]"); if (!input) return;
    setup.rows[Number(input.dataset.idx)][input.dataset.field] = input.value; setup.dirty = true;
  });
  $("#outletRows").addEventListener("click", (e) => {
    const rm = e.target.closest("[data-remove]");
    if (rm) {
      const [row] = setup.rows.splice(Number(rm.dataset.remove), 1);
      if (row.id) setup.deleted.push(row.id);
      setup.dirty = true; return renderOutletRows();
    }
    const clear = e.target.closest("[data-clear]");
    if (clear) {
      const row = setup.rows[Number(clear.dataset.idx)];
      row[clear.dataset.clear] = ""; delete row.labels[clear.dataset.clear];
      setup.dirty = true; return renderOutletRows();
    }
    const link = e.target.closest("[data-link]");
    if (link) return linkPair(Number(link.dataset.link));
    const pick = e.target.closest("[data-pick]");
    if (pick) openPicker(pick, Number(pick.dataset.idx), pick.dataset.pick);
  });
  if (!creating) loadLinkPairs();

  // bulk add from catalog
  $("#mergeRows").addEventListener("click", mergeSameArea);
  $("#suggestLinks").addEventListener("click", showLinkSuggestions);
  $("#toggleBulk").addEventListener("click", () => {
    $("#bulkPanel").hidden = !$("#bulkPanel").hidden;
    if (!$("#bulkPanel").hidden) { loadBulk(); $("#bulkSearch").focus(); }
  });
  $("#bulkTabs").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $("#bulkTabs .active").classList.remove("active"); b.classList.add("active");
    setup.bulkPlatform = b.dataset.p; setup.bulkSelected.clear(); loadBulk();
  });
  let t;
  $("#bulkSearch").addEventListener("input", () => { clearTimeout(t); t = setTimeout(loadBulk, 250); });
  $("#bulkResults").addEventListener("scroll", (e) => {
    const el = e.target;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80 && !bulkList.exhausted) loadBulk(false);
  });
  $("#bulkResults").addEventListener("change", async (e) => {
    const cb = e.target.closest("input[type=checkbox]"); if (!cb) return;
    if (cb.id === "bulkSelectAll") {
      const on = cb.checked;
      if (on) await loadAllBulk();
      bulkList.rows.forEach((r) => { if (on) setup.bulkSelected.set(r.id, r); else setup.bulkSelected.delete(r.id); });
      $("#bulkResults").querySelectorAll("input[data-item]").forEach((box) => { box.checked = on; });
      $("#bulkSelectAll").checked = on;
    } else {
      const item = JSON.parse(cb.dataset.item);
      if (cb.checked) setup.bulkSelected.set(item.id, item); else setup.bulkSelected.delete(item.id);
      const all = $("#bulkSelectAll");
      if (all) all.checked = [...$("#bulkResults").querySelectorAll("input[data-item]")].every((b) => b.checked);
    }
    $("#bulkAdd").disabled = !setup.bulkSelected.size;
    $("#bulkAdd").textContent = setup.bulkSelected.size ? `Add ${setup.bulkSelected.size} selected` : "Add selected";
  });
  $("#bulkAdd").addEventListener("click", () => {
    const p = setup.bulkPlatform;
    setup.bulkSelected.forEach((item) => {
      setup.rows.unshift({ outlet_name: item.name, area: item.area || "", city: item.city || "",
        zomato: "", swiggy: "", google: "", [p]: item.id, labels: { [p]: catalogLabel(item) } });
    });
    toast(`${setup.bulkSelected.size} outlet(s) added. Pick their other IDs, then Save outlets.`);
    setup.bulkSelected.clear(); setup.dirty = true; $("#bulkPanel").hidden = true; renderOutletRows();
  });
  renderOutletRows();
  if (!creating && brand) { renderGoogleCard(page, brand.client_id); renderInstagramCard(page, brand.client_id); }
}

// "Connect with Google": the client links their own Business Profile; no manager invite needed.
async function renderGoogleCard(page, clientId) {
  let info;
  try { info = await api(`/clients/${clientId}/google`); } catch { return; }
  const canEdit = Boolean(state.me.can_edit);
  const card = document.createElement("div");
  card.className = "card google-card";
  card.style.marginBottom = "16px";
  card.innerHTML = `
    <div class="card-head"><h3><img class="pill-icon" src="assets/google.png" alt=""> Google Business Profile</h3></div>
    <p class="muted" style="margin:0 0 12px">Connect the Google account that manages your listings. We then pull reviews, profile views, calls and listing health into this dashboard. We never post or change anything.</p>
    ${info.connections.length ? info.connections.map((c) => `<div class="g-conn">
        <span class="g-email"><b>${esc(c.email)}</b><small class="muted">connected ${timeAgo(c.connected_at)}</small></span>
        <span class="status ${c.status === "connected" ? "replied" : "pending"}">${c.status === "connected" ? "connected" : "needs reconnecting"}</span>
        ${canEdit && c.status === "connected" ? `<button class="btn light" data-gsync="${c.id}">Sync locations</button>` : ""}
        ${canEdit ? `<button class="btn light" data-disconnect="${c.id}">Disconnect</button>` : ""}</div>`).join("") : ""}
    ${canEdit ? `<button class="google-btn" id="googleConnect" ${info.configured ? "" : "disabled"}>
        <img src="assets/google.png" alt=""> ${info.connections.length ? "Connect another Google account" : "Connect with Google"}</button>
      ${info.configured ? "" : `<p class="muted" style="margin:8px 0 0">Not set up yet: ask Codeonto to add the Google keys.</p>`}` : ""}`;
  page.firstElementChild.insertAdjacentElement("afterend", card);
  $("#googleConnect")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    try { location.href = (await api("/google/connect", { client_id: clientId })).url; }
    catch (err) { toast(userMessage(err)); e.currentTarget.disabled = false; }
  });
  card.querySelectorAll("[data-gsync]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true; b.textContent = "Syncing…";
    try {
      await api(`/google/connections/${b.dataset.gsync}/sync`, {}, { method: "POST" });
      toast("Fetching this account's Google locations. They'll appear in the Google list in a minute.");
      setTimeout(() => render(), 45000);
    } catch (err) { toast(userMessage(err)); b.disabled = false; b.textContent = "Sync locations"; }
  }));
  card.querySelectorAll("[data-disconnect]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("Disconnect this Google account? Reviews and numbers already saved stay, but new ones stop arriving.")) return;
    try { await api(`/google/connections/${b.dataset.disconnect}`, {}, { method: "DELETE" }); toast("Google disconnected"); render(); }
    catch (err) { toast(userMessage(err)); }
  }));
}

// Instagram listening: connect the outlets' Business accounts, then see who tagged them and what people comment
async function renderInstagramCard(page, clientId) {
  let info;
  try { info = await api(`/clients/${clientId}/instagram`); } catch { return; }
  const canEdit = Boolean(state.me.can_edit);
  const card = document.createElement("div");
  card.className = "card";
  card.style.marginBottom = "16px";
  card.innerHTML = `
    <div class="card-head"><h3>Instagram</h3></div>
    <p class="muted" style="margin:0 0 12px">Connect your Instagram Business account (linked to a Facebook Page). We then show posts that tag you, your own posts and the comments on them. We never post or change anything.</p>
    ${info.connections.map((c) => `<div class="g-conn">
        <span class="g-email"><b>@${esc(c.username || "account")}</b><small class="muted">${c.followers != null ? `${esc(c.followers)} followers · ` : ""}${c.synced_at ? `synced ${timeAgo(c.synced_at)}` : "not synced yet"}</small></span>
        <span class="status ${c.status === "connected" ? "replied" : "pending"}" title="${esc(c.error || "")}">${c.status === "connected" ? "connected" : "needs attention"}</span>
        ${canEdit ? `<button class="btn light" data-igsync="${c.id}">Sync now</button><button class="btn light" data-igoff="${c.id}">Disconnect</button>` : ""}</div>`).join("")}
    ${canEdit ? `<button class="btn blue" id="igConnect" ${info.configured ? "" : "disabled"}>${info.connections.length ? "Connect another account" : "Connect Instagram"}</button>
      ${info.configured ? "" : `<p class="muted" style="margin:8px 0 0">Not set up yet: ask Codeonto to add the Meta keys.</p>`}` : ""}
    ${info.connections.length ? `<form id="igSearch" class="comp-search" style="margin-top:14px"><select name="type"><option value="hashtag">Hashtag</option><option value="username">Competitor username</option></select>
      <input name="q" placeholder="e.g. ramen, or a restaurant's Instagram name"><button class="btn blue">Search Instagram</button></form><div id="igResults"></div>` : ""}
    <div id="igFeed"></div>`;
  const after = $(".google-card") || page.firstElementChild;
  after.insertAdjacentElement("afterend", card);
  $("#igConnect")?.addEventListener("click", async (e) => {
    e.currentTarget.disabled = true;
    try { location.href = (await api("/instagram/connect", { client_id: clientId })).url; }
    catch (err) { toast(userMessage(err)); e.currentTarget.disabled = false; }
  });
  card.querySelectorAll("[data-igsync]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true; b.textContent = "Syncing…";
    try { const r = await api(`/instagram/connections/${b.dataset.igsync}/sync`, {}, { method: "POST" }); toast(`${r.new} new item${r.new === 1 ? "" : "s"}`); render(); }
    catch (err) { toast(userMessage(err)); b.disabled = false; b.textContent = "Sync now"; }
  }));
  card.querySelectorAll("[data-igoff]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("Disconnect this Instagram account? What we already saved stays.")) return;
    try { await api(`/instagram/connections/${b.dataset.igoff}`, {}, { method: "DELETE" }); toast("Instagram disconnected"); render(); }
    catch (err) { toast(userMessage(err)); }
  }));
  $("#igSearch")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget, out = $("#igResults");
    out.innerHTML = `<small class="muted">Searching…</small>`;
    try { out.innerHTML = igResults(await api(`/clients/${clientId}/instagram/search`, {}, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ type: f.type.value, q: f.q.value }) })); }
    catch (err) { out.innerHTML = `<small class="muted">${esc(userMessage(err))}</small>`; }
  });
  if (info.connections.length) loadInstagramFeed(clientId, "tag");
}

function igRows(list) {
  return list.length ? `<table class="tbl"><thead><tr><th>Who</th><th>What</th><th>Likes</th><th>Comments</th><th>When</th></tr></thead><tbody>${list.map((p) => `<tr>
    <td>${p.username ? `@${esc(p.username)}` : ""}</td><td><small>${esc((p.text || "").slice(0, 160))}</small> ${p.permalink ? `<a href="${esc(p.permalink)}" target="_blank" rel="noopener">open</a>` : ""}</td>
    <td>${esc(p.likes)}</td><td>${esc(p.comments)}</td><td><small class="muted">${p.posted_at ? timeAgo(p.posted_at) : ""}</small></td></tr>`).join("")}</tbody></table>` : `<p class="muted">No posts.</p>`;
}

function igResults(d) {
  if (d.type === "hashtag") return d.detail ? `<p class="muted">${esc(d.detail)}</p>` : `<h4 style="margin:14px 0 6px">Top posts for #${esc(d.q)}</h4>${igRows(d.top)}<h4 style="margin:14px 0 6px">Recent posts</h4>${igRows(d.recent)}`;
  const p = d.profile || {};
  return `<div style="margin:14px 0 6px"><b>@${esc(p.username)}</b> ${p.name ? `· ${esc(p.name)}` : ""}<br><small class="muted">${esc(p.followers_count ?? "?")} followers · ${esc(p.media_count ?? "?")} posts · avg ${esc(d.avg_likes)} likes and ${esc(d.avg_comments)} comments on the last ${d.posts.length}</small></div>${igRows(d.posts)}`;
}

async function loadInstagramFeed(clientId, kind) {
  const box = $("#igFeed");
  if (!box) return;
  const tabs = [["tag", "Tagged you"], ["comment", "Comments"], ["own", "Your posts"]];
  const d = await api(`/clients/${clientId}/instagram/feed`, { kind });
  box.innerHTML = `<div class="tabs" style="margin:14px 0 8px">${tabs.map(([k, l]) => `<button class="${k === kind ? "active" : ""}" data-igtab="${k}">${l}</button>`).join("")}</div>
    ${d.posts.length ? `<table class="tbl"><thead><tr><th>Who</th><th>What</th><th>Likes</th><th>When</th></tr></thead><tbody>${d.posts.map((p) => `<tr>
      <td>@${esc(p.username || p.account)}</td><td><small>${esc((p.text || "").slice(0, 160))}</small> ${p.permalink ? `<a href="${esc(p.permalink)}" target="_blank" rel="noopener">open</a>` : ""}</td>
      <td>${esc(p.likes)}</td><td><small class="muted">${p.posted_at ? timeAgo(p.posted_at) : ""}</small></td></tr>`).join("")}</tbody></table>`
      : `<p class="muted">Nothing yet. Press "Sync now" to read from Instagram.</p>`}`;
  box.querySelectorAll("[data-igtab]").forEach((b) => b.addEventListener("click", () => loadInstagramFeed(clientId, b.dataset.igtab)));
}

function instagramReturnNotice() {
  const q = new URLSearchParams(location.hash.split("?")[1] || "");
  if (!q.get("instagram")) return;
  toast(q.get("instagram") === "connected" ? "Instagram connected. Press Sync now to read it." : `Instagram connection failed: ${q.get("reason") || "try again"}`);
  history.replaceState(null, "", "#/setup");
}
setTimeout(instagramReturnNotice, 800);

function catalogLabel(item) {
  return `${item.name} · ${item.area || item.city || ""} (${item.id})`;
}

const pickerBoost = () => ($("#brandName")?.value || state.config?.brand?.name || "").trim();

// Move an id out of whichever other row holds it; a row left with no ids is removed.
function takeId(row, platform, id) {
  const other = setup.rows.find((r) => r !== row && r[platform] === id);
  if (!other) return;
  other[platform] = ""; delete other.labels[platform];
  if (!PICK_PLATFORMS.some((p) => other[p.code])) {
    setup.rows.splice(setup.rows.indexOf(other), 1);
    if (other.id) setup.deleted.push(other.id);
  }
}

const normArea = (r) => (r.area || r.outlet_name || "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

// Combine rows that hold different platforms' ids for the same area into one store.
// Zomato-only and Swiggy-only rows that are probably one kitchen (names differ between platforms): nothing links until
// someone ticks it and saves; saving moves the Swiggy row's whole history onto the kept row.
async function showLinkSuggestions() {
  if (setup.dirty && !confirm("Save or discard your unsaved outlet changes first? Suggestions are based on the saved outlets.")) return;
  let d;
  try { d = await api(`/brands/${state.brandId}/outlets/link-suggestions`); } catch (e) { toast(userMessage(e)); return; }
  document.querySelector(".link-modal")?.remove();
  const m = document.createElement("div");
  m.className = "link-modal";
  m.innerHTML = `<div class="card link-box">
    <div class="card-head"><h3>Suggested links · ${plural(d.pairs.length, "pair")}</h3><button class="btn light" data-close>Close</button></div>
    <p class="muted" style="margin-top:0">${inr.format(d.zomato_only)} Zomato-only and ${inr.format(d.swiggy_only)} Swiggy-only rows. Tick the pairs that are the same kitchen; confident ones are ticked for you.
      Linking puts both IDs on one row and moves the Swiggy row's reviews, payouts, uptime and the rest onto it. Nothing changes until you save outlets.</p>
    ${d.pairs.length ? `<div class="table-wrap"><table class="ov-table"><thead><tr><th><input type="checkbox" id="linkAll"></th><th>Zomato</th><th>Swiggy</th><th class="num">Match</th></tr></thead><tbody>
      ${d.pairs.map((p, i) => `<tr><td><input type="checkbox" data-pair="${i}" ${p.sure ? "checked" : ""}></td>
        <td><b>${esc(p.zomato.area || p.zomato.outlet_name)}</b><br><span class="muted">${esc(p.zomato.city || "")} · ${esc(p.zomato.zomato_id)}</span></td>
        <td><b>${esc(p.swiggy.area || p.swiggy.outlet_name)}</b><br><span class="muted">${esc(p.swiggy.city || "")} · ${esc(p.swiggy.swiggy_id)}</span></td>
        <td class="num">${Math.round(p.score * 100)}%${p.sure ? "" : '<br><span class="muted">check</span>'}</td></tr>`).join("")}</tbody></table></div>
      <div class="btn-row" style="margin-top:12px"><button class="btn blue" id="linkApply">Link selected</button></div>`
      : '<p class="muted">No likely pairs found. Link the rest by picking the other platform\'s ID on a row.</p>'}
  </div>`;
  document.body.appendChild(m);
  m.addEventListener("click", (e) => { if (e.target === m || e.target.closest("[data-close]")) m.remove(); });
  m.querySelector("#linkAll")?.addEventListener("change", (e) => m.querySelectorAll("[data-pair]").forEach((c) => { c.checked = e.target.checked; }));
  m.querySelector("#linkApply")?.addEventListener("click", () => {
    let linked = 0;
    m.querySelectorAll("[data-pair]:checked").forEach((c) => {
      const p = d.pairs[Number(c.dataset.pair)];
      const keep = setup.rows.find((r) => r.id === p.zomato.id), drop = setup.rows.find((r) => r.id === p.swiggy.id);
      if (!keep || !drop || keep.swiggy) return;
      keep.swiggy = drop.swiggy; keep.labels.swiggy = drop.labels.swiggy;
      setup.rows.splice(setup.rows.indexOf(drop), 1);
      setup.deleted.push(drop.id);
      linked++;
    });
    m.remove();
    if (linked) { setup.dirty = true; renderOutletRows(); toast(`${plural(linked, "pair")} linked. Click Save outlets to keep it.`); }
  });
}

function mergeSameArea() {
  let merged = 0, unsure = 0;
  const groups = new Map();
  setup.rows.forEach((r) => { const k = normArea(r); if (k) groups.set(k, [...(groups.get(k) || []), r]); });
  groups.forEach((rows) => {
    if (rows.length < 2) return;
    const base = rows[0];
    for (const r of rows.slice(1)) {
      const clash = PICK_PLATFORMS.some((p) => base[p.code] && r[p.code]);
      if (clash) { unsure++; continue; }
      PICK_PLATFORMS.forEach((p) => { if (r[p.code]) { base[p.code] = r[p.code]; base.labels[p.code] = r.labels[p.code]; } });
      setup.rows.splice(setup.rows.indexOf(r), 1);
      if (r.id) setup.deleted.push(r.id);
      merged++;
    }
  });
  if (merged) setup.dirty = true;
  renderOutletRows();
  toast(`${merged} row(s) merged${unsure ? `, ${unsure} left alone (same area but both already have the same platform)` : ""}`);
}

function pickedIds(platform) {
  return new Set(setup.rows.map((r) => r[platform]).filter(Boolean));
}

function syncBulkButton() {
  $("#bulkAdd").disabled = !setup.bulkSelected.size;
  $("#bulkAdd").textContent = setup.bulkSelected.size ? `Add ${setup.bulkSelected.size} selected` : "Add selected";
}

const bulkList = { rows: [], total: 0, loading: false, offset: 0, exhausted: false };

function bulkItemHtml(r) {
  return `<label class="bulk-item"><input type="checkbox" data-item='${esc(JSON.stringify(r))}' ${setup.bulkSelected.has(r.id) ? "checked" : ""}>
      <span><b>${esc(r.name)}</b> <span class="muted">${esc([r.area, r.city].filter(Boolean).join(", "))}</span></span>
      <code>${esc(r.id)}</code></label>`;
}

function bulkHeaderHtml() {
  const all = bulkList.rows.length && bulkList.rows.every((r) => setup.bulkSelected.has(r.id));
  return `<label class="bulk-item"><input type="checkbox" id="bulkSelectAll" ${all ? "checked" : ""}>
      <span><b>Select all ${bulkList.total}</b></span></label>`;
}

// Loads the next page of unmapped outlets (reset = start over); the list keeps loading as you scroll.
async function loadBulk(reset = true, pageSize = 100) {
  if (bulkList.loading) return;
  bulkList.loading = true;
  const p = setup.bulkPlatform;
  try {
    if (reset) { bulkList.rows = []; bulkList.offset = 0; }
    const taken = pickedIds(p);
    const res = await api(`/catalog/${p}`, { brand_id: state.brandId, q: $("#bulkSearch").value.trim(), unmapped: 1,
      limit: pageSize, offset: bulkList.offset });
    bulkList.offset += res.results.length;
    const fresh = res.results.filter((r) => !taken.has(r.id));
    bulkList.total = res.total;
    bulkList.rows.push(...fresh);
    bulkList.exhausted = res.results.length < pageSize;
    $("#bulkResults").innerHTML = bulkList.rows.length
      ? bulkHeaderHtml() + bulkList.rows.map(bulkItemHtml).join("")
      : `<p class="muted">No unmapped ${p} outlets match.</p>`;
  } finally { bulkList.loading = false; }
  syncBulkButton();
}

// Fetch everything that is still unloaded (used by Select all)
async function loadAllBulk() {
  while (!bulkList.exhausted && bulkList.offset < bulkList.total) await loadBulk(false, 500);
}

// the likeliest same-kitchen row on the other platform, offered right in the empty cell (one click links them)
function suggestionFor(r, platform) {
  if (!r.id || (platform !== "zomato" && platform !== "swiggy")) return "";
  const other = platform === "swiggy" ? "swiggy" : "zomato", mine = platform === "swiggy" ? "zomato" : "swiggy";
  const idx = setup.pairs.findIndex((p) => p[mine].id === r.id);
  if (idx < 0) return "";
  const o = setup.pairs[idx][other];
  return `<button class="pick-btn suggest-link" data-link="${idx}" title="${esc(`${o.outlet_name} · ${o.area || ""} · ${o.city || ""} (${o[other + "_id"]}). Click to link, then Save outlets.`)}">&#8596; ${esc(o.area || o.outlet_name)} · ${esc(o[other + "_id"])}<small>${Math.round(setup.pairs[idx].score * 100)}%${setup.pairs[idx].sure ? "" : " check"}</small></button>`;
}

async function loadLinkPairs() {
  try { setup.pairs = (await api(`/brands/${state.brandId}/outlets/link-suggestions`)).pairs || []; } catch { setup.pairs = []; }
  renderOutletRows();
}

function linkPair(idx) {
  const p = setup.pairs[idx];
  const keep = setup.rows.find((r) => r.id === p.zomato.id), drop = setup.rows.find((r) => r.id === p.swiggy.id);
  if (!keep || !drop || keep.swiggy) return;
  keep.swiggy = drop.swiggy; keep.labels.swiggy = drop.labels.swiggy;
  setup.rows.splice(setup.rows.indexOf(drop), 1);
  setup.deleted.push(drop.id);
  setup.pairs.splice(idx, 1);
  setup.dirty = true;
  renderOutletRows();
  toast("Linked. Click Save outlets to keep it.");
}

function renderOutletRows() {
  const match = (r) => !setup.filter || [r.outlet_name, r.area, r.city, r.zomato, r.swiggy, r.google]
    .some((v) => (v || "").toLowerCase().includes(setup.filter));
  const visible = setup.rows.map((r, i) => [r, i]).filter(([r]) => match(r));
  $("#outletCount").textContent = `· ${setup.rows.length}${setup.deleted.length ? ` (${setup.deleted.length} to delete)` : ""}`;
  const cell = (r, i, p) => r[p]
    ? `<div class="id-chip" title="${esc(r.labels[p] || r[p])}"><button class="chip-pick" data-pick="${p}" data-idx="${i}">${esc(r[p])}</button><button class="chip-x" data-clear="${p}" data-idx="${i}" title="Unmap">×</button></div>`
    : `${suggestionFor(r, p)}<button class="pick-btn" data-pick="${p}" data-idx="${i}">+ Pick</button>`;
  $("#outletRows").innerHTML = visible.length ? visible.map(([r, i]) => `<tr>
      <td><input data-idx="${i}" data-field="outlet_name" value="${esc(r.outlet_name)}" placeholder="e.g. Sector 29"></td>
      <td><input data-idx="${i}" data-field="area" value="${esc(r.area)}" placeholder="Area"></td>
      <td><input data-idx="${i}" data-field="city" value="${esc(r.city)}" placeholder="City"></td>
      ${PICK_PLATFORMS.map((p) => `<td>${cell(r, i, p.code)}</td>`).join("")}
      <td><button class="icon-del" data-remove="${i}" title="Remove outlet">${icon("trash")}</button></td>
    </tr>`).join("")
    : `<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">${setup.rows.length ? "No outlets match your search" : "No outlets yet. Use Add from catalog."}</td></tr>`;
}

// One floating picker for all platform cells
function openPicker(anchor, idx, platform) {
  closePicker();
  const row = setup.rows[idx];
  const pop = document.createElement("div");
  pop.className = "picker"; pop.id = "picker";
  pop.innerHTML = `
    <input type="search" placeholder="Search ${platform} by name, area, city or ID…" value="${esc(row.area || row.outlet_name || "")}">
    <label class="muted picker-opt"><input type="checkbox" id="pickAll"> include IDs already mapped (to move them)</label>
    <div class="picker-results"><p class="muted">Searching…</p></div>`;
  document.body.appendChild(pop);
  const r = anchor.getBoundingClientRect();
  pop.style.top = `${Math.min(window.innerHeight - 360, r.bottom + 4) + window.scrollY}px`;
  pop.style.left = `${Math.max(8, Math.min(window.innerWidth - 400, r.left)) + window.scrollX}px`;
  const input = pop.querySelector("input[type=search]");
  const load = async () => {
    const res = await api(`/catalog/${platform}`, { brand_id: state.brandId, q: input.value.trim(), unmapped: $("#pickAll").checked ? "" : 1, limit: 30, boost: pickerBoost() });
    const taken = pickedIds(platform);
    pop.querySelector(".picker-results").innerHTML = res.results.length ? res.results.map((it) => {
      const other = setup.rows.find((r) => r !== row && r[platform] === it.id);
      const usedHere = Boolean(other);
      return `<button class="picker-item" data-item='${esc(JSON.stringify(it))}'>
        <span><b>${esc(it.name)}</b> <span class="muted">${esc([it.area, it.city].filter(Boolean).join(", "))}</span>
        ${it.mapped_to ? `<br><small class="warn">mapped to ${esc(it.mapped_to)}</small>` : ""}${usedHere ? `<br><small class="warn">in your list as “${esc(other.outlet_name || "unnamed")}”; picking it merges that row into this one</small>` : ""}
        ${it.is_active ? "" : `<br><small class="warn">inactive</small>`}</span><code>${esc(it.id)}</code></button>`;
    }).join("") : `<p class="muted">No matches.</p>`;
  };
  let t;
  input.addEventListener("input", () => { clearTimeout(t); t = setTimeout(load, 250); });
  pop.querySelector("#pickAll").addEventListener("change", load);
  pop.addEventListener("click", (e) => {
    const b = e.target.closest(".picker-item"); if (!b) return;
    const it = JSON.parse(b.dataset.item);
    takeId(row, platform, it.id);
    row[platform] = it.id; row.labels[platform] = catalogLabel(it);
    if (!row.outlet_name) row.outlet_name = it.name;
    if (!row.area && it.area) row.area = it.area;
    if (!row.city && it.city) row.city = it.city;
    setup.dirty = true; closePicker(); renderOutletRows();
  });
  setTimeout(() => document.addEventListener("mousedown", outsidePicker), 0);
  input.focus(); input.select(); load();
}
function outsidePicker(e) { if (!e.target.closest("#picker")) closePicker(); }
function closePicker() { $("#picker")?.remove(); document.removeEventListener("mousedown", outsidePicker); }

async function saveBrand(creating) {
  const name = $("#brandName").value.trim();
  if (!name) return toast("Enter a brand name");
  let clientId = state.me.is_staff ? $("#clientSelect").value : state.me.client?.id;
  const btn = $("#saveBrand"); btn.disabled = true;
  try {
    if (clientId === "__new") {
      const clientName = $("#newClientName").value;
      if (!clientName.trim()) { btn.disabled = false; $("#newClientName").focus(); return toast("Enter the new client's name"); }
      clientId = (await apiJSON("/staff/clients", "POST", { name: clientName.trim() })).id;
    }
    const body = { name, industry_code: $("#brandIndustryInput").value, client_id: Number(clientId) };
    const id = creating
      ? (await apiJSON("/brands", "POST", body)).id
      : (await apiJSON(`/brands/${state.brandId}`, "PATCH", body), state.brandId);
    await loadBrandList();
    $("#brandSelect").value = id;
    toast(creating ? "Brand created. Now add its outlets." : "Brand saved");
    await loadBrand(id);
  } catch (e) { toast(userMessage(e)); }
  btn.disabled = false;
}

async function archiveBrand() {
  const b = state.brands.find((x) => x.id === state.brandId);
  if (!b || !confirm(`Archive "${b.name}"? It disappears from the dashboard for everyone. Nothing is deleted.`)) return;
  try {
    await apiJSON(`/brands/${b.id}`, "PATCH", { is_active: false });
    toast("Brand archived");
    await loadBrandList();
    if (!state.brands.length) { state.config = null; return render(); }
    $("#brandSelect").value = state.brands[0].id;
    await loadBrand(state.brands[0].id);
  } catch (e) { toast(userMessage(e)); }
}

async function saveOutlets(moveConflicts) {
  const btn = $("#saveOutlets"); btn.disabled = true;
  const payload = {
    outlets: setup.rows.map((r) => ({
      id: r.id, outlet_name: r.outlet_name, area: r.area, city: r.city,
      ...Object.fromEntries(PICK_PLATFORMS.map((p) => [p.code, r[p.code] || ""])),
    })),
    delete_ids: setup.deleted,
    move_conflicts: moveConflicts,
  };
  try {
    const res = await apiFetch(`${API}/brands/${state.brandId}/outlets`, {
      method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(payload),
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 409 && body.conflicts) {
      const list = body.conflicts.map((c) => `• ${c.platform} ${c.id} → currently on "${c.mapped_to}"`).join("\n");
      btn.disabled = false;
      if (confirm(`These IDs are already used in another store of this client:\n\n${list}\n\nMove them to this store? All their history (reviews, payouts, uptime, stock-outs, metrics) moves too.`)) return saveOutlets(true);
      return;
    }
    if (!res.ok) throw userError(friendlyStatus(res.status, body), { status: res.status, body });
    toast(`Saved ${body.saved} outlet${body.saved === 1 ? "" : "s"}${body.deleted ? `, deleted ${body.deleted}` : ""}`);
    setup.dirty = false;
    await loadBrand(state.brandId);
  } catch (e) { toast(userMessage(e)); }
  btn.disabled = false;
}

async function apiJSON(path, method, body) {
  return api(path, {}, { method, headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
}

window.addEventListener("beforeunload", (e) => {
  if (currentRoute() === "setup" && setup.dirty) { e.preventDefault(); e.returnValue = ""; }
});

function renderNoData(page) {
  const platforms = state.config.connected_platforms.map((p) => p.name).join(" + ") || "no platforms";
  page.innerHTML = `<div class="card empty-state">${icon("store_uptime")}
    <h3>No data synced yet</h3>
    <p>${esc(state.config.brand.name)} has ${state.locations.length} outlets linked on ${esc(platforms)}.<br>
    Numbers appear here once reviews, orders and metrics are synced for this period.</p></div>`;
}

// ---------- competition: each outlet's Google rating against the nearby places it chose to compare with ----------
const km = (m) => (m == null ? "—" : m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1)} km`);
const gRating = (p) => (p?.rating != null ? `${p.rating.toFixed(1)} ★` : '<span class="muted">—</span>');
const delta = (v, digits = 0, suffix = "") => (v == null || v === 0 ? '<span class="muted">—</span>'
  : `<span class="chip ${v > 0 ? "up" : "down"}">${v > 0 ? "▲" : "▼"} ${Math.abs(v).toFixed(digits)}${suffix}</span>`);

const SERVICE_LABELS = { delivery: "Delivery", dineIn: "Dine-in", takeout: "Takeaway", reservable: "Reservations", servesVegetarianFood: "Veg options" };
const clock = (m) => { if (m == null) return ""; const h = Math.floor(m / 60) % 24, mm = m % 60;
  return `${h % 12 || 12}${mm ? `:${String(mm).padStart(2, "0")}` : ""} ${h < 12 ? "AM" : "PM"}`; };
const todayHours = (t) => (!t ? '<span class="muted">—</span>' : t.open == null ? '<span class="muted">Closed today</span>'
  : t.open === 0 && t.close === 1440 ? "24 hours" : `${clock(t.open)} – ${clock(t.close)}`);
const services = (sv) => Object.entries(SERVICE_LABELS).filter(([k]) => sv?.[k]).map(([, l]) => `<span class="comp-svc">${l}</span>`).join("") || '<span class="muted">—</span>';

// Google Maps JavaScript API, loaded once on first use
let mapsReady;
function loadMaps(key) {
  mapsReady ||= new Promise((resolve, reject) => {
    window.__mapsInit = resolve;
    const tag = document.createElement("script");
    tag.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly&callback=__mapsInit`;
    tag.async = true;
    tag.onerror = () => { mapsReady = null; reject(userError("The map couldn't be loaded. Please try again in a moment.")); };
    document.head.appendChild(tag);
  });
  return mapsReady;
}

// your outlet in red, compared places in blue, suggestions in grey; a grey pin's popup can start comparing with it
async function drawCompMap(el, key, me, comps, onCompare) {
  await loadMaps(key);
  const g = google.maps, center = { lat: me.lat, lng: me.lng };
  const map = new g.Map(el, { center, zoom: 14, mapTypeControl: false, streetViewControl: false, clickableIcons: false });
  new g.Circle({ map, center, radius: 2000, clickable: false, strokeColor: "#d9480f", strokeOpacity: 0.4, strokeWeight: 1, fillColor: "#d9480f", fillOpacity: 0.05 });
  const info = new g.InfoWindow(), markers = new Map();
  const STYLE = { me: ["#e5484d", 10, 3], tracked: ["#d9480f", 8, 2], suggested: ["#94a3b8", 7, 1] };
  const add = (p, kind) => {
    if (p.lat == null || markers.has(p.place_id)) return;
    const [color, scale, zIndex] = STYLE[kind];
    const m = new g.Marker({ map, zIndex, title: p.name, position: { lat: p.lat, lng: p.lng },
      icon: { path: g.SymbolPath.CIRCLE, scale, fillColor: color, fillOpacity: 1, strokeColor: "#fff", strokeWeight: 2 } });
    m.addListener("click", () => {
      const box = document.createElement("div");
      box.className = "comp-info";
      box.innerHTML = `<strong>${esc(p.name)}</strong><span>${p.rating != null ? `${p.rating.toFixed(1)} ★ · ` : ""}${inr.format(p.rating_count || 0)} ratings${p.distance_m != null ? ` · ${km(p.distance_m)}` : ""}</span>`;
      if (kind === "suggested") {
        const b = document.createElement("button");
        b.className = "btn blue"; b.textContent = "Compare";
        b.addEventListener("click", () => onCompare(p.place_id));
        box.appendChild(b);
      }
      info.setContent(box);
      info.open({ map, anchor: m });
    });
    markers.set(p.place_id, m);
  };
  add(me, "me");
  comps.forEach((c) => add(c, "tracked"));
  return { addSuggestions: (list) => list.filter((p) => !p.tracked).forEach((p) => add(p, "suggested")) };
}

// Competition has three sources: Google Maps listings and the Zomato and Swiggy apps. The tab is remembered across reloads.
const MARKET_NAMES = { zomato: "Zomato", swiggy: "Swiggy" };
const zName = () => MARKET_NAMES[state.compTab] || "Zomato";
async function renderCompetition(page) {
  const tab = state.compTab || "google";
  page.innerHTML = `<div class="comp-tabs">
      <button class="${tab === "google" ? "active" : ""}" data-ctab="google">Google</button>
      <button class="${tab === "zomato" ? "active" : ""}" data-ctab="zomato">Zomato</button>
      <button class="${tab === "swiggy" ? "active" : ""}" data-ctab="swiggy">Swiggy</button></div>
    <div id="compBody"></div>`;
  page.querySelectorAll("[data-ctab]").forEach((b) => b.addEventListener("click", () => { state.compTab = b.dataset.ctab; render(); }));
  const body = $("#compBody");
  if (tab === "google") return renderGoogleComp(body);
  if (!singleId()) {
    body.innerHTML = `<div class="card empty-state">${icon("competitors")}<h3>Pick an outlet</h3>
      <p>${zName()} competition is set up per outlet. Choose one in the outlet filter above.</p></div>`;
    return;
  }
  return renderMarketComp(body, singleId());
}

const zBase = (outletId) => `/brands/${state.brandId}/competition/${outletId}/${state.compTab}`;
// a spot picked with "Look from another area": used by searches and menus until switched back, never saved
const zPeekKey = (outletId) => `${state.compTab}:${outletId}`;
const zPeek = (outletId) => (state.zPeek || {})[zPeekKey(outletId)];
const zOffer = (r) => (r.offers?.[0] ? `${esc(r.offers[0].text)}${r.offers.length > 1 ? ` <small class="muted">+${r.offers.length - 1} more</small>` : ""}` : '<span class="muted">—</span>');
// items missing a photo or description, as a count and share; a competitor shows green where it does better than you
const zGapPct = (n, of) => (n == null || !of ? null : Math.round((100 * n) / of));
function zGap(n, of, usN, usOf, isUs) {
  const pct = zGapPct(n, of);
  if (pct == null) return '<td class="num muted">—</td>';
  const worse = isUs ? false : zGapPct(usN, usOf) != null && pct < zGapPct(usN, usOf);
  return `<td class="num ${worse ? "comp-better" : ""}">${inr.format(n)} <small class="muted">(${pct}%)</small></td>`;
}
const zRating = (r) => (r.rating != null ? `${r.rating.toFixed(1)} ★${r.votes ? ` <small class="muted">(${esc(r.votes)})</small>` : ""}` : '<span class="muted">—</span>');

// the outlet's own cuisines on this app, as buttons: each runs the normal search for that cuisine around the outlet
async function loadMarketCuisines(outletId) {
  const box = $("#zCuisines"), form = $("#zSearch");
  if (!box || !form) return;
  box.innerHTML = `<small class="muted">Reading your ${zName()} cuisines…</small>`;
  try {
    const spot = zPeek(outletId)?.spot;
    const p = await api(`${zBase(outletId)}/cuisines`, spot ? { spot: JSON.stringify(spot) } : {});
    if (!$("#zCuisines")) return;  // the page changed while we waited
    if (!p.cuisines?.length) { box.innerHTML = p.detail ? `<small class="muted">${esc(p.detail)}</small>` : ""; return; }
    box.innerHTML = `<div class="comp-cuisine-head"><b>${esc(p.name || "This outlet")}</b> serves <small class="muted">click a cuisine to see who else serves it nearby</small></div>
      <div class="comp-cuisine-row">${p.cuisines.map((c) => `<button type="button" class="comp-cuisine" data-cuisine="${esc(c)}">${esc(c)}</button>`).join("")}</div>
      ${p.open_text || p.cost_text ? `<small class="muted">${[p.open_text, p.cost_text].filter(Boolean).map(esc).join(" · ")}</small>` : ""}`;
    loadSuggestedCompetitors(outletId, box, spot);
    loadCuisineRanking(outletId, box, spot);
    box.onclick = (e) => {
      const b = e.target.closest("[data-cuisine]");
      if (!b) return;
      box.querySelectorAll(".comp-cuisine").forEach((x) => x.classList.toggle("on", x === b));
      form.q.value = b.dataset.cuisine;
      if (form.kind) form.kind.value = "";  // a tag from the outlet's own list searches the way it always did
      form.requestSubmit();
    };
  } catch (x) { if ($("#zCuisines")) box.innerHTML = `<small class="muted">The cuisines couldn't be loaded right now. Please try again in a moment.</small>`; }
}

const SEARCH_KINDS = [["", "All", "a restaurant, dish or cuisine"], ["restaurant", "Restaurant", "a restaurant name"], ["dish", "Dish", "a dish"], ["cuisine", "Cuisine", "a cuisine"]];

// 3-4 nearby restaurants that serve the same food as the outlet, to compare against in one click
async function loadSuggestedCompetitors(outletId, box, spot) {
  const slot = document.createElement("div");
  slot.className = "comp-suggest";
  slot.innerHTML = `<small class="muted">Finding competitors near you with the same food…</small>`;
  box.appendChild(slot);
  try {
    const p = await api(`${zBase(outletId)}/suggested`, spot ? { spot: JSON.stringify(spot) } : {});
    if (!slot.isConnected) return;
    if (!p.suggestions?.length) { slot.innerHTML = p.detail ? `<small class="muted">${esc(p.detail)}</small>` : ""; return; }
    slot.innerHTML = `<div class="comp-cuisine-head"><b>Competitors near you serving the same food</b> <small class="muted">from ${zName()}'s own lists for ${esc((p.cuisines || []).join(", "))}</small></div>
      <div class="sg-grid">${p.suggestions.map((r, i) => `<div class="sg-card" style="--i:${i}">
        <div class="sg-top"><b class="sg-name" title="${esc(r.name)}">${esc(r.name)}</b>${r.rating != null ? `<span class="sg-rate">${Number(r.rating).toFixed(1)} ★</span>` : ""}</div>
        <div class="sg-meta">${[r.distance_km != null ? `${r.distance_km} km away` : "", r.delivery_time].filter(Boolean).map(esc).join(" · ")}</div>
        <div class="sg-tags">${r.cuisines.map((c) => `<span>${esc(c)}</span>`).join("")}</div>
        ${r.offer ? `<div class="sg-offer">${esc(r.offer)}</div>` : ""}
        <button class="btn light sg-track" type="button" data-sg="${esc(r.res_id)}">Compare with us</button></div>`).join("")}</div>`;
    slot.querySelectorAll("[data-sg]").forEach((b) => b.addEventListener("click", async () => {
      const r = p.suggestions.find((x) => x.res_id === b.dataset.sg);
      b.disabled = true; b.textContent = "Adding…";
      try { await apiJSON(`${zBase(outletId)}/track`, "POST", { res_id: r.res_id, tracked: true, name: r.name, distance_km: r.distance_km, delivery_time: r.delivery_time, spot }); render(); }
      catch (e) { b.disabled = false; b.textContent = "Compare with us"; toast(userMessage(e)); }
    }));
  } catch (x) { if (slot.isConnected) slot.innerHTML = `<small class="muted">Suggested competitors couldn't be loaded right now.</small>`; }
}

// where the outlet sits in the app's own list for each cuisine tag
async function loadCuisineRanking(outletId, box, spot) {
  const slot = document.createElement("div");
  slot.className = "comp-rank";
  slot.innerHTML = `<small class="muted">Checking your rank for each cuisine…</small>`;
  box.appendChild(slot);
  try {
    const p = await api(`${zBase(outletId)}/ranking`, spot ? { spot: JSON.stringify(spot) } : {});
    if (!slot.isConnected) return;
    if (!p.rows?.length) { slot.innerHTML = p.detail ? `<small class="muted">${esc(p.detail)}</small>` : ""; return; }
    slot.innerHTML = `<div class="comp-cuisine-head"><b>Your rank by cuisine</b> <small class="muted">in ${zName()}'s own list at this spot, first ~30 checked</small></div>
      <table class="tbl"><thead><tr><th>Cuisine</th><th>Your rank</th><th>Ahead of you</th></tr></thead><tbody>${p.rows.map((r) =>
        `<tr><td>${esc(r.cuisine)}</td><td>${r.rank ? `<b>#${r.rank}</b> <small class="muted">of ${esc(r.of)}</small>` : `<span class="muted">not in top ${esc(r.checked)}</span>`}</td><td><small>${r.top.map(esc).join(", ")}</small></td></tr>`).join("")}</tbody></table>`;
  } catch (x) { if (slot.isConnected) slot.innerHTML = `<small class="muted">The ranking couldn't be loaded right now.</small>`; }
}

async function renderMarketComp(page, outletId) {
  const d = await api(zBase(outletId));
  if (!d.configured) {
    page.innerHTML = `<div class="card empty-state">${icon("competitors")}<h3>${zName()} isn't connected yet</h3>
      <p>An admin needs to save a ${zName()} app session on the server (manage.py ${state.compTab}_app_session).</p></div>`;
    return;
  }
  if (!d.area) return renderMarketArea(page, outletId, null);
  const us = d.us;
  const rows = [...(us ? [{ ...us, is_us: true }] : []), ...d.competitors];
  page.innerHTML = `
    <div class="card">
      <form id="zSearch" class="comp-search comp-search-lg">${state.compTab === "zomato" ? `<select name="kind" id="zKind" aria-label="Search type" title="What to search for">${SEARCH_KINDS.map(([v, t]) => `<option value="${v}" ${(state.searchKind || "") === v ? "selected" : ""}>${t}</option>`).join("")}</select>` : ""}<input name="q" placeholder="Search a restaurant, dish or cuisine on ${zName()}, e.g. Meghana, biryani, chinese" autofocus>
        <button class="btn blue">Search</button></form>
      <div id="zCuisines" class="comp-cuisines"></div>
      ${zPeek(outletId) ? `<p class="comp-peek">Viewing from <strong>${esc(zPeek(outletId).title)}</strong>${zPeek(outletId).address ? `, ${esc(zPeek(outletId).address)}` : ""}
          <small>just for now, not saved</small> · <button class="login-link" id="zPeekOff">Back to the outlet's location</button></p>`
        : `<p class="comp-near">Showing what customers see around <strong>${esc(d.area.title)}</strong>${d.area.address ? `, ${esc(d.area.address)}` : ""}
          · <button class="login-link" id="zPeekOn">Look from another area</button> · <button class="login-link" id="zChangeArea">Change outlet's location</button></p>`}
      <p class="login-error" id="zError"></p><div id="zResults"></div>
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-head"><h3>${d.competitors.length ? `You vs ${plural(d.competitors.length, "competitor")}` : `Your ${zName()} competitors`}</h3>
        <span class="btn-row">${!d.us && d.our_res_id ? `<button class="btn light" id="zLoadUs">Add our own ${zName()} menu</button>` : ""}
          ${d.competitors.length ? `<a class="btn blue" id="zExport" href="${API}${zBase(outletId)}/export${d.us ? "" : "?us=0"}" download>Export analysis to Excel (${d.competitors.length + (d.us ? 1 : 0)})</a>` : `<span class="muted">up to ${d.max_tracked}</span>`}</span></div>
      ${!d.our_res_id ? `<p class="comp-note">We couldn't find this outlet's own ${zName()} listing, so there's no "You" row to compare with. Search for your restaurant above and click <b>This is us</b>.</p>`
        : d.our_how !== "linked" ? `<p class="comp-near" style="margin:0 0 12px">Your ${zName()} listing: <strong>${esc(d.our_name || d.our_res_id)}</strong> (res ID ${esc(d.our_res_id)}, ${d.our_how === "picked" ? "chosen by you" : "found by your brand name"}) · <button class="login-link" id="zNotUs">Not us?</button></p>` : ""}
      ${rows.length ? `<div class="cp-scroll"><table class="ov-table"><thead><tr><th class="comp-sel">${d.competitors.length ? '<input type="checkbox" id="zSelAll" checked title="Select all for the analysis">' : ""}</th><th>Restaurant</th><th class="num">Rating</th><th>Top offer</th>
        <th class="num">Items</th><th class="num">Avg price</th><th class="num">Out of stock</th><th class="num">No photo</th><th class="num">No description</th><th class="num">Veg</th><th>Best seller</th><th></th></tr></thead><tbody>
        ${rows.map((r) => `<tr class="cp-click ${r.is_us ? "comp-me" : ""}" data-zview="${esc(r.res_id)}">
          <td class="comp-sel">${r.is_us ? `<input type="checkbox" id="zSelUs" checked title="Include your own outlet in the analysis">`
            : `<input type="checkbox" data-zsel="${esc(r.res_id)}" checked title="Include in the analysis">`}</td>
          <td><strong>${esc(r.name)}${r.is_us ? ' <em class="comp-you">You</em>' : ""}</strong><small class="muted">${[r.distance_km != null ? `${r.distance_km} km` : "", r.delivery_time].filter(Boolean).join(" · ")}</small></td>
          <td class="num">${zRating(r)}</td><td class="comp-offer">${zOffer(r)}</td>
          <td class="num">${r.items ?? "—"}</td><td class="num">${r.avg_price ? `₹${inr.format(r.avg_price)}` : "—"}</td>
          <td class="num ${r.out_of_stock ? "ov-bad" : ""}">${r.out_of_stock ?? "—"}</td>
          ${zGap(r.no_photo, r.items, us?.no_photo, us?.items, r.is_us)}${zGap(r.no_desc, r.items, us?.no_desc, us?.items, r.is_us)}
          <td class="num">${r.veg_pct != null ? `${r.veg_pct}%` : "—"}</td>
          <td class="comp-offer">${r.top_sellers?.[0] ? `${esc(r.top_sellers[0].name)} <small class="muted">₹${r.top_sellers[0].price}</small>` : "—"}</td>
          <td class="num">${r.is_us ? "" : `<button class="btn light" data-zuntrack="${esc(r.res_id)}">Remove</button>`}</td></tr>`).join("")}
      </tbody></table></div>` : `<p class="muted" style="margin:0">Search above, then click <b>Compare</b> on the restaurants you want to keep an eye on.</p>`}
    </div>
    <div id="zDetail"></div>`;

  const err = (e) => { $("#zError").textContent = userMessage(e); };
  loadMarketCuisines(outletId);
  const track = async (r, on) => {
    try { await apiJSON(`${zBase(outletId)}/track`, "POST", { res_id: r.res_id, tracked: on, name: r.name, distance_km: r.distance_km, delivery_time: r.delivery_time, spot: zPeek(outletId)?.spot }); render(); return true; }
    catch (e) { err(e); return false; }
  };
  const setUs = async (resId) => {
    try { await apiJSON(`${zBase(outletId)}/us`, "POST", { res_id: resId }); render(); } catch (e) { err(e); }
  };
  $("#zNotUs")?.addEventListener("click", () => setUs(null));
  $("#zChangeArea")?.addEventListener("click", () => renderMarketArea(page, outletId, d.area));
  $("#zPeekOn")?.addEventListener("click", () => renderMarketArea(page, outletId, d.area, true));
  $("#zPeekOff")?.addEventListener("click", () => { delete state.zPeek[zPeekKey(outletId)]; render(); });
  $("#zLoadUs")?.addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "Loading…";
    try { await api(`${zBase(outletId)}/restaurants/${d.our_res_id}`); render(); } catch (x) { err(x); e.target.disabled = false; }
  });
  // pick which competitors go into the Excel analysis: all by default
  const sels = [...page.querySelectorAll("[data-zsel]")];
  const syncExport = () => {
    const picked = sels.filter((c) => c.checked).map((c) => c.dataset.zsel);
    const withUs = Boolean($("#zSelUs")?.checked);  // no "You" row at all means the analysis is competitors only
    const a = $("#zExport");
    if (!a) return;
    const q = new URLSearchParams();
    if (picked.length && picked.length < sels.length) q.set("res_ids", picked.join(","));
    if (!withUs) q.set("us", "0");
    a.href = `${API}${zBase(outletId)}/export${q.toString() ? `?${q}` : ""}`;
    a.textContent = `Export analysis to Excel (${picked.length + (withUs ? 1 : 0)})`;
    // needs something to compare: two restaurants, or you and one competitor
    a.classList.toggle("disabled", !picked.length || (!withUs && picked.length < 2));
    if ($("#zSelAll")) $("#zSelAll").checked = picked.length === sels.length;
  };
  sels.forEach((c) => { c.addEventListener("click", (e) => e.stopPropagation()); c.addEventListener("change", syncExport); });
  $("#zSelAll")?.addEventListener("change", (e) => { sels.forEach((c) => { c.checked = e.target.checked; }); syncExport(); });
  $("#zSelUs")?.addEventListener("click", (e) => e.stopPropagation());
  $("#zSelUs")?.addEventListener("change", syncExport);
  // download through fetch so the button can say the report is being built (it takes a while)
  $("#zExport")?.addEventListener("click", async (e) => {
    e.preventDefault();
    const a = e.currentTarget;
    if (a.classList.contains("disabled") || a.dataset.busy) return;
    a.dataset.busy = "1"; a.classList.add("disabled");
    const label = a.textContent;
    a.textContent = "Preparing your report… this can take a minute";
    try {
      const res = await apiFetch(new URL(a.href, location.origin));
      if (!res.ok) throw userError("The file couldn't be made right now. Please try again in a moment.");
      const name = /filename="?([^";]+)"?/.exec(res.headers.get("Content-Disposition") || "")?.[1] || `${state.compTab}-competition.xlsx`;
      const f = document.createElement("a");
      f.href = URL.createObjectURL(await res.blob()); f.download = name; f.click(); URL.revokeObjectURL(f.href);
      toast("Report downloaded");
    } catch (x) { toast(userMessage(x)); }
    delete a.dataset.busy; a.classList.remove("disabled"); a.textContent = label;
  });
  page.querySelectorAll("[data-zuntrack]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); track({ res_id: b.dataset.zuntrack }, false); }));
  page.querySelectorAll("[data-zview]").forEach((tr) => tr.addEventListener("click", () => showMarketRestaurant(outletId, tr.dataset.zview, track)));
  let results = [];
  const kindBox = $("#zKind"), qBox = $("#zSearch")?.q;
  const hint = () => { const k = SEARCH_KINDS.find(([v]) => v === (kindBox?.value || "")); if (qBox && k) qBox.placeholder = `Search ${k[2]} on ${zName()}${k[0] ? "" : ", e.g. Meghana, biryani, chinese"}`; };
  kindBox?.addEventListener("change", () => { state.searchKind = kindBox.value; hint(); qBox?.focus(); });
  hint();
  $("#zSearch").addEventListener("submit", async (e) => {
    e.preventDefault(); $("#zError").textContent = "";
    const btn = e.target.querySelector("button"); btn.disabled = true;
    $("#zResults").innerHTML = `<p class="muted">Searching ${zName()}…</p>`;
    try {
      const r = await apiJSON(`${zBase(outletId)}/search`, "POST", { q: e.target.q.value, kind: e.target.kind?.value || "", spot: zPeek(outletId)?.spot });
      results = r.results;
      $("#zResults").innerHTML = (r.total ? `<p class="muted" style="margin:0 0 4px">${inr.format(r.total)} restaurants for ${esc(r.query)} · showing the first ${results.length}</p>` : "") +
        (results.length ? results.map((x, i) => `<div class="comp-result">
          <span><strong>${esc(x.name)}${x.is_ad ? ' <em class="comp-ad">Ad</em>' : ""}${x.is_us ? ' <em class="comp-you">You</em>' : ""}</strong>
            <small class="muted">${[x.area, x.distance_km != null ? `${x.distance_km} km` : "", x.delivery_time, x.offers?.[0]?.text].filter(Boolean).map(esc).join(" · ")}</small></span>
          <span class="num">${x.rating != null ? `${x.rating.toFixed(1)} ★` : ""}</span>
          <span class="btn-row"><button class="btn light" data-zres="${i}" data-act="view">View</button>
            ${x.is_us ? "" : `${d.our_how === "linked" ? "" : `<button class="btn light" data-zres="${i}" data-act="us">This is us</button>`}
              <button class="btn ${x.tracked ? "light" : "blue"}" data-zres="${i}" data-act="track" ${x.tracked ? "disabled" : ""}>${x.tracked ? "Comparing" : "Compare"}</button>`}</span></div>`).join("")
          : '<p class="muted">Nothing found.</p>');
    } catch (x) { err(x); $("#zResults").innerHTML = ""; }
    btn.disabled = false;
  });
  $("#zResults").addEventListener("click", (e) => {
    const b = e.target.closest("[data-zres]");
    if (!b) return;
    const x = results[Number(b.dataset.zres)];
    if (b.dataset.act === "view") showMarketRestaurant(outletId, x.res_id, track);
    else if (b.dataset.act === "us") setUs(x.res_id);
    else { b.disabled = true; b.textContent = "Adding…"; track(x, true).then((ok) => { if (!ok) { b.disabled = false; b.textContent = "Compare"; } }); }
  });
}

// step one on a delivery app: where the outlet stands in the app, so searches and menus match what customers there see
function renderMarketArea(page, outletId, current, peek = false) {
  const outlet = state.locations.find((l) => String(l.id) === String(outletId));
  const title = peek ? "Look from another area" : current ? `Pick a different spot for ${esc(outlet?.name || "this outlet")}` : `Where is ${esc(outlet?.name || "this outlet")}?`;
  const help = peek ? "See which restaurants, offers and menus customers in another area get, for example a locality you deliver to or one you might open in. Nothing is saved: switch back any time."
    : current ? "Type the outlet's street or landmark and pick the closest match. This changes where all searches and comparisons for this outlet start from."
    : `We couldn't place this outlet on ${zName()} automatically. Type its street or landmark and pick the closest match.`;
  page.innerHTML = `<div class="card">
    <div class="card-head"><h3>${title}</h3>${current ? '<button class="btn light" id="zCancel">Cancel</button>' : ""}</div>
    <p class="muted" style="margin-top:0">${help}</p>
    <form id="zLoc" class="comp-search"><input name="q" value="${peek ? "" : esc([outlet?.name, outlet?.city].filter(Boolean).join(" "))}" placeholder="e.g. Koramangala Bengaluru" autofocus><button class="btn blue">Search</button></form>
    <p class="login-error" id="zError"></p><div id="zResults"></div></div>`;
  $("#zCancel")?.addEventListener("click", () => render());
  let found = [];
  $("#zLoc").addEventListener("submit", async (e) => {
    e.preventDefault(); $("#zError").textContent = "";
    try {
      found = await apiJSON(`${zBase(outletId)}/locations`, "POST", { q: e.target.q.value });
      $("#zResults").innerHTML = found.length ? found.map((f, i) => `<div class="comp-result">
          <span><strong>${esc(f.title)}</strong><small class="muted">${esc(f.address)}</small></span><span></span>
          <button class="btn blue" data-zpick="${i}">${peek ? "Look from here" : "Use this"}</button></div>`).join("") : '<p class="muted">No match. Try the area and city.</p>';
    } catch (x) { $("#zError").textContent = userMessage(x); }
  });
  $("#zResults").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-zpick]");
    if (!b) return;
    b.disabled = true;
    try {
      const pick = found[Number(b.dataset.zpick)];
      if (peek) { state.zPeek = { ...(state.zPeek || {}), [zPeekKey(outletId)]: await apiJSON(`${zBase(outletId)}/peek`, "POST", { pick }) }; }
      else await apiJSON(`${zBase(outletId)}/area`, "POST", { pick });
      render();
    }
    catch (x) { $("#zError").textContent = userMessage(x); b.disabled = false; }
  });
}

// pick menu photos, then cut out / re-background / add a logo on the server and download them as a zip
function photoEditor(outletId, r) {
  const form = $("#phForm");
  if (!form) return;
  const picks = () => [...document.querySelectorAll(".ph-pick:checked")].map((c) => c.value);
  const sync = () => { const n = picks().length; $("#phCount").textContent = `${n} selected`; $("#phOpen").disabled = !n; };
  document.querySelectorAll(".ph-pick").forEach((c) => c.addEventListener("change", sync));
  $("#phAll").addEventListener("change", (e) => { document.querySelectorAll(".ph-pick").forEach((c) => { c.checked = e.target.checked; }); sync(); });
  $("#phOpen").addEventListener("click", () => { form.hidden = false; });
  $("#phClose").addEventListener("click", () => { form.hidden = true; });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ids = picks(), go = $("#phGo");
    const base = `${API}${zBase(outletId)}/restaurants/${encodeURIComponent(r.res_id)}/images/edit`;
    const job = [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
    const opts = (batch) => {
      const fd = new FormData();
      fd.append("job", job);
      fd.append("item_ids", JSON.stringify(batch));
      if (form.remove_bg.checked) fd.append("remove_bg", "1");
      if (form.match_light.checked) fd.append("match_light", "1");
      if (form.use_color.checked) fd.append("bg_color", form.bg_color.value);
      if (form.bg_image.files[0]) fd.append("bg_image", form.bg_image.files[0]);
      if (form.logo.files[0]) fd.append("logo", form.logo.files[0]);
      ["logo_pos", "logo_size", "logo_opacity", "size", "dish_size", "pos_x", "pos_y", "tilt"].forEach((k) => fd.append(k, form[k].value));
      return fd;
    };
    const fail = async (res) => { const b = await res.json().catch(() => ({})); throw userError(friendlyStatus(res.status, b), { status: res.status, body: b }); };
    $("#phError").textContent = ""; go.disabled = true;
    try {
      let failed = 0;
      for (let i = 0; i < ids.length; i += 4) {
        go.textContent = `Editing ${Math.min(i + 4, ids.length)} of ${ids.length}…`;
        const res = await apiFetch(base, { method: "POST", body: opts(ids.slice(i, i + 4)) });
        if (!res.ok) await fail(res);
        failed += (await res.json()).failed.length;
      }
      go.textContent = "Preparing zip…";
      const res = await apiFetch(`${base}/${job}`);
      if (!res.ok) await fail(res);
      const url = URL.createObjectURL(await res.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: (res.headers.get("content-disposition") || "").match(/filename="(.+)"/)?.[1] || "photos.zip" });
      a.click(); setTimeout(() => URL.revokeObjectURL(url), 5000);
      if (failed) $("#phError").textContent = `${failed} photos couldn't be edited; their names are in could-not-edit.txt in the zip.`;
    } catch (x) { $("#phError").textContent = userMessage(x); }
    go.disabled = false; go.textContent = "Edit and download";
  });
}

// one restaurant's page on a delivery app: offers, combos, best sellers, categories and what is out of stock
async function showMarketRestaurant(outletId, resId, track, refresh = false) {
  const box = $("#zDetail");
  box.innerHTML = `<div class="card" style="margin-top:16px"><p class="muted">Loading the menu from ${zName()}… this can take a few seconds.</p></div>`;
  box.scrollIntoView({ behavior: "smooth", block: "start" });
  let r;
  const spot = zPeek(outletId)?.spot;
  try { r = await api(`${zBase(outletId)}/restaurants/${encodeURIComponent(resId)}`, spot ? { spot: JSON.stringify(spot) } : {}); }
  catch (e) { box.innerHTML = `<div class="card" style="margin-top:16px"><p class="login-error">${esc(userMessage(e))}</p></div>`; return; }
  const ins = r.insights || {};
  const cats = Object.entries(ins.by_category || {});
  box.innerHTML = `<div class="card" style="margin-top:16px">
    <div class="card-head"><h3>${esc(r.name)} ${r.is_us ? '<em class="comp-you">You</em>' : ""}</h3>
      <span class="btn-row"><small class="muted">menu read ${r.menu_refreshed_at ? timeAgo(r.menu_refreshed_at) : ""}</small>
        <button class="btn light" id="zRefresh">Refresh</button>
        ${r.is_us ? "" : `<a class="btn light" href="${API}${zBase(outletId)}/export?res_ids=${encodeURIComponent(r.res_id)}" download>${r.has_us ? "Export vs us" : "Export"}</a>`}
        ${(r.items || []).some((i) => i.image) ? `<a class="btn light" href="${API}${zBase(outletId)}/restaurants/${encodeURIComponent(r.res_id)}/images" download>Download photos</a>` : ""}
        ${r.is_us || r.tracked ? "" : '<button class="btn blue" id="zTrackThis">Compare</button>'}</span></div>
    <div class="ov-tiles">
      <div class="ov-tile"><span class="ov-tile-label">Rating</span><div class="ov-tile-value">${r.rating != null ? r.rating.toFixed(1) : "—"}<small>★</small></div><span class="ov-tile-sub">${[r.votes ? `${esc(r.votes)} ratings` : "", esc(r.cost_for_two || ""), esc((r.cuisines || []).join(", "))].filter(Boolean).join(" · ")}</span></div>
      <div class="ov-tile"><span class="ov-tile-label">Menu</span><div class="ov-tile-value">${ins.items ?? "—"}</div><span class="ov-tile-sub">items in ${ins.categories ?? "—"} categories · avg ₹${inr.format(ins.avg_price || 0)}</span></div>
      <div class="ov-tile ${(ins.out_of_stock || []).length ? "red" : ""}"><span class="ov-tile-label">Out of stock now</span><div class="ov-tile-value">${(ins.out_of_stock || []).length}</div><span class="ov-tile-sub">veg ${ins.veg_pct ?? "—"}% of the menu</span></div>
      <div class="ov-tile ${(ins.no_photo || []).length || (ins.no_desc || []).length ? "amber" : ""}"><span class="ov-tile-label">Menu content</span>
        <div class="ov-tile-value">${ins.photo_pct ?? "—"}<small class="muted">% photos</small></div>
        <span class="ov-tile-sub">${(ins.no_photo || []).length} items without a photo · ${(ins.no_desc || []).length} without a description (${ins.desc_pct ?? "—"}% described)</span></div>
    </div>
    <div class="grid cols-2-even">
      <div><h4 class="comp-h">Offers running now</h4>${(r.offers || []).length ? r.offers.map((o) => `<div class="comp-line">${esc(o.text)}${o.code ? ` <code>${esc(o.code)}</code>` : ""}</div>`).join("") : '<p class="muted">No offers.</p>'}
        ${(r.combos || []).length ? `<h4 class="comp-h">Combos customers order</h4>${r.combos.map((c) => `<div class="comp-line">${esc(c.name)} <b>${esc(c.price)}</b> <small class="muted">${esc(c.ordered_by)}</small></div>`).join("")}` : ""}</div>
      <div><h4 class="comp-h">Best sellers</h4><table class="ov-table"><tbody>${(ins.top_sellers || []).map((t, i) => `<tr><td><span class="rank ${i < 3 ? "top" : ""}">${i + 1}</span></td><td>${esc(t.name)}</td>
          <td class="num">${menuPrice(t)}</td><td class="num">${t.reorder != null ? `<small class="muted">reordered</small> ${Math.round(t.reorder * 100)}%`
            : state.compTab === "swiggy" && t.popularity ? `${inr.format(t.popularity)} <small class="muted">ratings</small>` : ""}</td></tr>`).join("")}</tbody></table></div>
    </div>
    <h4 class="comp-h">Categories</h4>
    <div class="cp-scroll"><table class="ov-table"><thead><tr><th>Category</th><th class="num">Items</th><th class="num">Avg price</th><th class="num">Range</th></tr></thead><tbody>
      ${cats.map(([c, v]) => `<tr><td>${esc(c)}</td><td class="num">${v.items}</td><td class="num">${v.avg_price ? `₹${inr.format(v.avg_price)}` : "—"}</td><td class="num muted">₹${v.min ?? "—"} – ₹${v.max ?? "—"}</td></tr>`).join("")}</tbody></table></div>
    ${(ins.out_of_stock || []).length ? `<h4 class="comp-h">Out of stock right now</h4><div class="comp-svcs">${ins.out_of_stock.map((n) => `<span class="comp-svc">${esc(n)}</span>`).join("")}</div>` : ""}
    ${(ins.no_photo || []).length ? `<details class="comp-menu"><summary>Without a photo · ${ins.no_photo.length} items</summary><div class="comp-svcs">${ins.no_photo.map((n) => `<span class="comp-svc">${esc(n)}</span>`).join("")}</div></details>` : ""}
    ${(ins.no_desc || []).length ? `<details class="comp-menu"><summary>Without a description · ${ins.no_desc.length} items</summary><div class="comp-svcs">${ins.no_desc.map((n) => `<span class="comp-svc">${esc(n)}</span>`).join("")}</div></details>` : ""}
    <details class="comp-menu"><summary>Full menu · ${(r.items || []).length} items</summary>
      ${(r.items || []).some((i) => i.image) ? `<div class="ph-bar"><label><input type="checkbox" id="phAll"> Select all photos</label>
        <span class="muted" id="phCount">0 selected</span><button class="btn blue" id="phOpen" disabled>Edit photos</button></div>
      <form id="phForm" class="ph-form" hidden>
        <label><input type="checkbox" name="remove_bg" checked> Remove background</label>
        <label>Background colour <input type="color" name="bg_color" value="#ffffff"> <span class="muted"><input type="checkbox" name="use_color" checked> use</span></label>
        <label>Background image <input type="file" name="bg_image" accept="image/*"></label>
        <label>Dish size <input type="range" name="dish_size" min="20" max="100" value="84"></label>
        <label>Dish left ↔ right <input type="range" name="pos_x" min="0" max="100" value="50"></label>
        <label>Dish up ↕ down <input type="range" name="pos_y" min="0" max="100" value="50"></label>
        <label>Table angle <input type="range" name="tilt" min="0" max="50" value="0"></label>
        <label><input type="checkbox" name="match_light" checked> Match background lighting</label>
        <label>Logo <input type="file" name="logo" accept="image/*"></label>
        <label>Logo position <select name="logo_pos"><option value="br">Bottom right</option><option value="bl">Bottom left</option><option value="tr">Top right</option><option value="tl">Top left</option><option value="c">Centre</option></select></label>
        <label>Logo size <input type="range" name="logo_size" min="5" max="60" value="20"></label>
        <label>Logo opacity <input type="range" name="logo_opacity" min="10" max="100" value="100"></label>
        <label>Output size <select name="size"><option value="1000">1000 × 1000</option><option value="800">800 × 800</option><option value="1200">1200 × 1200</option><option value="0">Keep original</option></select></label>
        <span class="btn-row"><button class="btn blue" id="phGo">Edit and download</button><button type="button" class="btn light" id="phClose">Close</button></span>
        <p class="login-error" id="phError"></p></form>` : ""}
      <table class="ov-table"><thead><tr><th></th><th>Item</th><th>Category</th><th class="num">Price</th><th>Tags</th></tr></thead><tbody>
      ${(r.items || []).map((i) => `<tr class="${i.in_stock ? "" : "comp-oos"}"><td>${i.image ? `<input type="checkbox" class="ph-pick" value="${esc(String(i.id))}">` : ""}</td><td>${i.image ? `<img class="comp-thumb" src="${esc(i.image)}" alt="" loading="lazy">` : '<span class="comp-thumb"></span>'}<span class="comp-diet ${i.veg ? "veg" : "nonveg"}"></span>${esc(i.name)}</td><td class="muted">${esc(i.category)}</td>
        <td class="num">${menuPrice(i)}</td><td>${[...i.tags, i.in_stock ? "" : "Out of stock"].filter(Boolean).map((t) => `<span class="comp-svc">${esc(t)}</span>`).join("")}</td></tr>`).join("")}</tbody></table></details>
  </div>`;
  $("#zRefresh").addEventListener("click", () => showMarketRestaurant(outletId, resId, track, true));
  photoEditor(outletId, r);
  $("#zTrackThis")?.addEventListener("click", (e) => { e.target.disabled = true; track(r, true); });
}

async function renderGoogleComp(page) {
  const d = await api(`/brands/${state.brandId}/competition`, { outlet_id: state.locationId });
  if (!d.configured) {
    page.innerHTML = `<div class="card empty-state">${icon("competitors")}<h3>Competition isn't switched on yet</h3>
      <p>It compares each outlet's Google rating with nearby restaurants. An admin needs to add a Google Places API key to the server.</p></div>`;
    return;
  }
  if (!singleId()) return renderCompetitionAll(page, d.outlets);
  const o = d.outlets[0];
  if (!o) { page.innerHTML = `<div class="card empty-state"><h3>Outlet not found</h3></div>`; return; }
  if (!o.place) return renderLocate(page, o);

  const me = o.place, comps = o.competitors;
  const gap = o.competitor_avg != null && me.rating != null ? me.rating - o.competitor_avg : null;
  const rows = [{ ...me, mine: true }, ...comps].sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
  page.innerHTML = `
    <div class="ov-tiles">
      <div class="ov-tile ${o.rank === 1 ? "" : o.rank ? "amber" : ""}"><span class="ov-tile-label">Rank nearby</span>
        <div class="ov-tile-value">${o.rank ? `#${o.rank}<small class="muted">of ${o.of}</small>` : "—"}</div>
        <span class="ov-tile-sub">${comps.length ? "by Google rating, among places you compare with" : "Add competitors to see your rank"}</span></div>
      <div class="ov-tile"><span class="ov-tile-label">Your Google rating</span>
        <div class="ov-tile-value">${me.rating != null ? me.rating.toFixed(1) : "—"}<small>★</small>${delta(me.rating_change, 1)}</div>
        <span class="ov-tile-sub">${inr.format(me.rating_count || 0)} ratings${me.new_ratings ? ` · +${inr.format(me.new_ratings)} this week` : ""}</span></div>
      <div class="ov-tile ${gap != null && gap < 0 ? "red" : ""}"><span class="ov-tile-label">vs competitors</span>
        <div class="ov-tile-value">${gap == null ? "—" : `${gap >= 0 ? "+" : "−"}${Math.abs(gap).toFixed(2)}`}</div>
        <span class="ov-tile-sub">${o.competitor_avg != null ? `their average is ${o.competitor_avg.toFixed(2)} ★` : "No competitors yet"}</span></div>
    </div>
    ${d.maps_key && me.lat != null ? `<div class="card comp-map-card">
      <div class="card-head"><h3>Around you</h3><span class="comp-legend"><i class="me"></i>You<i class="tracked"></i>Comparing<i class="suggested"></i>Suggested · 2 km</span></div>
      <div id="compMap" class="comp-map"></div></div>` : ""}
    <div class="card">
      <div class="card-head"><h3>You vs ${comps.length ? plural(comps.length, "competitor") : "nearby places"}</h3>
        <button class="btn light" id="relocate">Change our Google listing</button></div>
      <div class="cp-scroll"><table class="ov-table"><thead><tr><th>#</th><th>Place</th><th class="num">Rating</th><th class="num">Ratings</th>
        <th class="num">This week</th><th class="num">Price for two</th><th>Today</th><th>Services</th><th class="num">Distance</th><th></th></tr></thead><tbody>
        ${rows.map((p, i) => {
          const later = !p.mine && p.today?.close != null && me.today?.close != null && p.today.close > me.today.close;
          const closed = p.status && p.status !== "OPERATIONAL";
          return `<tr class="cp-click ${p.mine ? "comp-me" : ""}" data-place="${esc(p.place_id)}"><td><span class="rank ${i < 3 ? "top" : ""}">${i + 1}</span></td>
          <td><strong>${esc(p.name)}${p.mine ? ' <em class="comp-you">You</em>' : ""}${closed ? ` <em class="comp-closed">${p.status === "CLOSED_PERMANENTLY" ? "Closed" : "Temporarily closed"}</em>` : ""}</strong>
            <small class="muted">${esc(p.address || "")}</small></td>
          <td class="num">${gRating(p)} ${delta(p.rating_change, 1)}</td><td class="num">${inr.format(p.rating_count || 0)}</td>
          <td class="num">${p.new_ratings ? `+${inr.format(p.new_ratings)}` : '<span class="muted">—</span>'}</td>
          <td class="num">${p.price_range ? esc(p.price_range) : '<span class="muted">—</span>'}</td>
          <td class="comp-hours ${later ? "ov-bad" : ""}" title="${esc((p.week || []).join("\n"))}">${todayHours(p.today)}${later ? "<small>open later than you</small>" : ""}</td>
          <td><div class="comp-svcs">${services(p.services)}</div></td>
          <td class="num">${p.mine ? "" : km(p.distance_m)}</td>
          <td class="num">${p.mine ? "" : `<button class="btn light" data-untrack="${esc(p.place_id)}">Remove</button>`}</td></tr>`;
        }).join("")}
      </tbody></table></div>
      ${comps.length ? "" : `<p class="muted" style="margin:12px 0 0">No competitors yet. Use "Suggest nearby" below, or add one by name.</p>`}
    </div>
    <div class="card" style="margin-top:16px">
      <div class="card-head"><h3>Add competitors</h3><span class="muted">up to ${d.max_tracked} per outlet</span></div>
      <div class="comp-add">
        <button class="btn blue" id="suggest">Suggest nearby</button>
        <form id="compSearch" class="comp-search"><input name="q" placeholder="Or search by name, e.g. Behrouz Biryani"><button class="btn light">Search</button></form>
      </div>
      <p class="login-error" id="compError"></p>
      <div id="compResults"></div>
    </div>`;

  const err = (e) => { $("#compError").textContent = userMessage(e); };
  let mapP = Promise.resolve(null);
  const show = (list) => {
    mapP.then((m) => m?.addSuggestions(list));
    $("#compResults").innerHTML = list.length ? list.map((p) => `<div class="comp-result">
        <span><strong>${esc(p.name)}</strong><small class="muted">${esc(p.address || "")}</small></span>
        <span class="num">${gRating(p)}<small class="muted">${inr.format(p.rating_count || 0)} ratings · ${km(p.distance_m)}</small></span>
        <button class="btn ${p.tracked ? "light" : "blue"}" data-track="${esc(p.place_id)}" ${p.tracked ? "disabled" : ""}>${p.tracked ? "Comparing" : "Compare"}</button></div>`).join("")
      : `<p class="muted">Nothing found.</p>`;
  };
  const trackBtn = async (pid, on) => {
    try { await apiJSON(`/brands/${state.brandId}/competition/${o.outlet_id}/track`, "POST", { place_id: pid, tracked: on }); render(); }
    catch (e) { err(e); }
  };
  $("#suggest").addEventListener("click", async (e) => {
    e.target.disabled = true; $("#compError").textContent = "";
    try { show(await apiJSON(`/brands/${state.brandId}/competition/${o.outlet_id}/suggest`, "POST", {})); } catch (x) { err(x); }
    e.target.disabled = false;
  });
  $("#compSearch").addEventListener("submit", async (e) => {
    e.preventDefault(); $("#compError").textContent = "";
    try { show(await apiJSON(`/brands/${state.brandId}/competition/${o.outlet_id}/search`, "POST", { q: e.target.q.value })); } catch (x) { err(x); }
  });
  $("#compResults").addEventListener("click", (e) => { const b = e.target.closest("[data-track]"); if (b) trackBtn(b.dataset.track, true); });
  page.querySelectorAll("[data-untrack]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); trackBtn(b.dataset.untrack, false); }));
  // click a row: what Google's reviewers say about that place, read live
  page.querySelectorAll("[data-place]").forEach((tr) => tr.addEventListener("click", async () => {
    const open = tr.nextElementSibling?.classList.contains("comp-detail");
    page.querySelectorAll(".comp-detail").forEach((d) => d.remove());
    if (open) return;
    tr.insertAdjacentHTML("afterend", `<tr class="comp-detail"><td colspan="11"><p class="muted">Loading what reviewers say…</p></td></tr>`);
    const cell = tr.nextElementSibling.firstElementChild;
    try {
      const r = await api(`/brands/${state.brandId}/competition/${o.outlet_id}/places/${encodeURIComponent(tr.dataset.place)}/reviews`);
      cell.innerHTML = `${r.summary ? `<div class="comp-summary"><span class="ov-tile-label">What reviewers say · summarised by Google</span><p>${esc(r.summary)}</p></div>`
          : '<p class="muted">Google has no review summary for this place yet.</p>'}
        ${r.reviews.map((v) => `<div class="comp-review"><span>${v.rating != null ? `${v.rating} ★` : ""} <strong>${esc(v.author)}</strong> <small class="muted">${esc(v.when)}</small></span>
          <p>${esc(v.text)}</p></div>`).join("")}`;
    } catch (e) { cell.innerHTML = `<p class="login-error">${esc(userMessage(e))}</p>`; }
  }));
  $("#relocate").addEventListener("click", () => renderLocate(page, o));
  if ($("#compMap")) {
    mapP = drawCompMap($("#compMap"), d.maps_key, me, comps, (pid) => trackBtn(pid, true))
      .catch((e) => { $("#compMap").innerHTML = `<p class="muted" style="padding:16px">${esc(userMessage(e))}</p>`; return null; });
  }
}

function renderCompetitionAll(page, outlets) {
  page.innerHTML = `<div class="card">
    <div class="card-head"><h3>Where each outlet stands</h3><span class="muted">Google rating vs the places each outlet compares with · click an outlet to open it</span></div>
    <div class="cp-scroll"><table class="ov-table"><thead><tr><th>Outlet</th><th class="num">Your rating</th><th class="num">Competitors avg</th>
      <th class="num">Rank</th><th class="num">Comparing</th></tr></thead><tbody>
      ${outlets.map((o) => {
        const behind = o.place?.rating != null && o.competitor_avg != null && o.place.rating < o.competitor_avg;
        return `<tr class="cp-click" data-outlet="${o.outlet_id}"><td><strong>${esc(o.name)}</strong><small class="muted">${esc(o.city || "")}</small></td>
          <td class="num ${behind ? "ov-bad" : ""}">${o.place ? gRating(o.place) : '<span class="muted">Not set up</span>'}</td>
          <td class="num">${o.competitor_avg != null ? `${o.competitor_avg.toFixed(2)} ★` : '<span class="muted">—</span>'}</td>
          <td class="num">${o.rank ? `#${o.rank} of ${o.of}` : '<span class="muted">—</span>'}</td>
          <td class="num">${o.competitors.length || '<span class="muted">0</span>'}</td></tr>`;
      }).join("")}
    </tbody></table></div></div>`;
  page.querySelectorAll("[data-outlet]").forEach((r) => r.addEventListener("click", () => {
    state.locationId = r.dataset.outlet; showSelectedOutlet(); render();
  }));
}

// step one for an outlet: pick which Google Maps listing is its own
async function renderLocate(page, o) {
  page.innerHTML = `<div class="card">
    <div class="card-head"><h3>Find ${esc(o.name)} on Google</h3></div>
    <p class="muted" style="margin-top:0">Pick this outlet's own Google Maps listing. Competitors are found around it.</p>
    <form id="locSearch" class="comp-search"><input name="q" placeholder="Search a different name or address"><button class="btn light">Search</button></form>
    <p class="login-error" id="compError"></p><div id="compResults"><p class="muted">Searching…</p></div></div>`;
  const run = async (q) => {
    $("#compError").textContent = "";
    try {
      const r = await apiJSON(`/brands/${state.brandId}/competition/${o.outlet_id}/locate`, "POST", q ? { q } : {});
      if (!q) $("#locSearch").q.placeholder = r.query;
      $("#compResults").innerHTML = r.results.length ? r.results.map((p) => `<div class="comp-result">
          <span><strong>${esc(p.name)}</strong><small class="muted">${esc(p.address || "")}</small></span>
          <span class="num">${gRating(p)}<small class="muted">${inr.format(p.rating_count || 0)} ratings</small></span>
          <button class="btn blue" data-pick="${esc(p.place_id)}">This is us</button></div>`).join("")
        : `<p class="muted">No match. Try the outlet's name with its area or street.</p>`;
    } catch (e) { $("#compError").textContent = userMessage(e); $("#compResults").innerHTML = ""; }
  };
  $("#locSearch").addEventListener("submit", (e) => { e.preventDefault(); run(e.target.q.value.trim()); });
  $("#compResults").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-pick]");
    if (!b) return;
    b.disabled = true;
    try { await apiJSON(`/brands/${state.brandId}/competition/${o.outlet_id}/locate`, "POST", { place_id: b.dataset.pick }); render(); }
    catch (x) { $("#compError").textContent = userMessage(x); b.disabled = false; }
  });
  run("");
}

function renderComingSoon(page, module) {
  page.innerHTML = `<div class="card empty-state">${icon(module)}<h3>${esc(moduleName(module))} is coming soon</h3>
    <p>This module is enabled for ${esc(state.config.brand.name)} but has no data source connected yet.</p></div>`;
}

// ---------- client management (staff) ----------
const ID_TABS = [{ code: "zomato", label: "Zomato" }, { code: "swiggy", label: "Swiggy" }, { code: "google", label: "Google" }];

async function renderClients(page) {
  $("#pageTitle").textContent = "Clients";
  $("#pageSub").textContent = "Add clients, give them their Zomato / Swiggy / Google IDs and their logins";
  const data = await api("/staff/clients");
  const u = data.unassigned_ids;
  page.innerHTML = `
    <div class="stat-strip">
      <div class="card kpi"><span class="kpi-label">Clients</span><div class="kpi-value">${data.clients.length}</div></div>
      ${ID_TABS.map((t) => `<div class="card kpi"><span class="kpi-label">${t.label} IDs not assigned</span><div class="kpi-value">${inr.format(u[t.code])}</div></div>`).join("")}
    </div>
    <div class="card">
      <div class="card-head">
        <h3>All clients</h3>
        <div class="btn-row">
          <input id="clientSearch" type="search" placeholder="Search clients…">
          <button class="btn blue" id="addClientBtn">${icon("plus")} Add client</button>
        </div>
      </div>
      <form class="form-row add-client" id="addClientForm" hidden>
        <label>Client (company) name<input name="name" required placeholder="e.g. Massive Restaurants Pvt Ltd"></label>
        <label>Contact person<input name="contact_name"></label>
        <label>Email<input name="contact_email" type="email"></label>
        <label>Phone<input name="contact_phone"></label>
        <button class="btn blue" type="submit">Create client</button>
      </form>
      <div class="table-wrap"><table class="clients-table">
        <thead><tr><th>Client</th><th>Contact</th><th class="num">Brands</th><th class="num">Logins</th>
          ${ID_TABS.map((t) => `<th class="num">${platformPill(t.code)}</th>`).join("")}<th>Status</th></tr></thead>
        <tbody id="clientRows"></tbody>
      </table></div>
    </div>`;
  const draw = (q = "") => {
    const rows = data.clients.filter((c) => !q || `${c.name} ${c.contact_name} ${c.contact_email}`.toLowerCase().includes(q));
    $("#clientRows").innerHTML = rows.length ? rows.map((c) => `<tr class="click-row" data-id="${c.id}">
        <td><b>${esc(c.name)}</b></td><td class="muted">${esc([c.contact_name, c.contact_email].filter(Boolean).join(" · "))}</td>
        <td class="num">${c.brands}</td><td class="num">${c.users}</td>
        ${ID_TABS.map((t) => `<td class="num">${c.ids[t.code]}</td>`).join("")}
        <td>${c.is_active ? '<span class="status replied">active</span>' : '<span class="status pending">inactive</span>'}</td></tr>`).join("")
      : `<tr><td colspan="8" class="muted" style="text-align:center;padding:24px">${data.clients.length ? "No clients match" : "No clients yet. Click Add client."}</td></tr>`;
  };
  draw();
  $("#clientSearch").addEventListener("input", (e) => draw(e.target.value.toLowerCase()));
  $("#clientRows").addEventListener("click", (e) => { const tr = e.target.closest("[data-id]"); if (tr) location.hash = `#/clients/${tr.dataset.id}`; });
  $("#addClientBtn").addEventListener("click", () => { $("#addClientForm").hidden = !$("#addClientForm").hidden; $("#addClientForm [name=name]").focus(); });
  $("#addClientForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const c = await apiJSON("/staff/clients", "POST", Object.fromEntries(new FormData(e.target)));
      toast(`${c.name} created. Now assign its IDs.`);
      location.hash = `#/clients/${c.id}`;
    } catch (err) { toast(userMessage(err)); }
  });
}

const clientView = { platform: "zomato", avail: { q: "", page: 1, sel: new Set() }, owned: { q: "", page: 1, sel: new Set() } };

async function renderClient(page, clientId) {
  const c = await api(`/staff/clients/${clientId}`);
  $("#pageTitle").textContent = c.name;
  $("#pageSub").innerHTML = `<a href="#/clients">← All clients</a> · ${c.brands} brands · ${c.users} logins`;
  page.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div class="card-head"><h3>Client details</h3></div>
      <form class="form-row" id="clientForm">
        <label>Client name<input name="name" value="${esc(c.name)}" required></label>
        <label>Contact person<input name="contact_name" value="${esc(c.contact_name)}"></label>
        <label>Email<input name="contact_email" type="email" value="${esc(c.contact_email)}"></label>
        <label>Phone<input name="contact_phone" value="${esc(c.contact_phone)}"></label>
        <label class="check"><input type="checkbox" name="is_active" ${c.is_active ? "checked" : ""}> Active</label>
        <button class="btn blue" type="submit">Save</button>
      </form>
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="card-head">
        <h3>Platform IDs</h3>
        <div class="segmented" id="idTabs">${ID_TABS.map((t) => `<button data-p="${t.code}" class="${t.code === clientView.platform ? "active" : ""}">${t.label} · ${c.ids[t.code]}</button>`).join("")}</div>
      </div>
      <p class="muted" style="margin:0 0 12px">Only IDs assigned here can be mapped to ${esc(c.name)}'s stores. Left: IDs no client owns yet. Right: ${esc(c.name)}'s IDs.</p>
      <div class="ids-cols">
        <div class="ids-box">
          <div class="ids-head"><b>Available</b><span class="muted" id="availCount"></span></div>
          <div class="btn-row"><input type="search" id="availSearch" placeholder="Search name, area, city or ID…"></div>
          <div class="btn-row ids-actions"><label class="check"><input type="checkbox" id="availAll"> Select page</label>
            <button class="btn blue" id="assignBtn" disabled>Assign →</button></div>
          <div class="id-list" id="availList"></div>
          <div class="ids-pager" id="availPager"></div>
        </div>
        <div class="ids-box">
          <div class="ids-head"><b>${esc(c.name)}'s IDs</b><span class="muted" id="ownedCount"></span></div>
          <div class="btn-row"><input type="search" id="ownedSearch" placeholder="Search this client's IDs…"></div>
          <div class="btn-row ids-actions"><label class="check"><input type="checkbox" id="ownedAll"> Select page</label>
            <button class="btn light" id="removeBtn" disabled>← Remove</button></div>
          <div class="id-list" id="ownedList"></div>
          <div class="ids-pager" id="ownedPager"></div>
        </div>
      </div>
    </div>

    <div class="grid cols-2-even">
      <div class="card">
        <div class="card-head"><h3>Logins</h3><div class="btn-row"><a class="btn light" href="#/billing/${clientId}">Plan &amp; billing</a><a class="btn light" href="#/team/${clientId}">Manage team</a><a class="btn light" href="#/alert-settings/${clientId}">Alerts settings</a></div></div>
        <table><thead><tr><th>Login</th><th>Role</th><th>Last login</th></tr></thead>
          <tbody>${c.user_list.length ? c.user_list.map((u) => `<tr>
            <td><b>${esc(u.username)}</b><br><span class="muted">${esc([u.name, u.email].filter(Boolean).join(" · "))}</span>${u.is_active ? "" : ' <span class="status pending">disabled</span>'}</td>
            <td>${esc(TEAM_ROLES[u.role] || u.role)}</td>
            <td class="muted">${u.last_login ? timeAgo(u.last_login) : "never"}</td></tr>`).join("")
            : `<tr><td colspan="3" class="muted">No logins yet. Use Manage team to add one so ${esc(c.name)} can sign in.</td></tr>`}</tbody></table>
      </div>
      <div class="card">
        <div class="card-head"><h3>Brands</h3><a class="btn light" href="#/setup" id="newBrandForClient">${icon("plus")} New brand</a></div>
        <table><thead><tr><th>Brand</th><th>Industry</th><th class="num">Stores</th><th></th></tr></thead>
          <tbody>${c.brand_list.length ? c.brand_list.map((b) => `<tr><td><b>${esc(b.name)}</b></td><td class="muted">${esc(b.industry)}</td>
            <td class="num">${b.stores}</td><td><button class="btn light" data-open-brand="${b.id}">Map stores</button></td></tr>`).join("")
            : `<tr><td colspan="4" class="muted">No brands yet. ${esc(c.name)} can create them after logging in, or you can with New brand.</td></tr>`}</tbody></table>
      </div>
    </div>`;

  // details
  $("#clientForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      await apiJSON(`/staff/clients/${clientId}`, "PATCH", { ...Object.fromEntries(f), is_active: f.get("is_active") === "on" });
      toast("Client saved"); renderClient(page, clientId);
    } catch (err) { toast(userMessage(err)); }
  });

  // ids
  const side = (key) => ({
    list: $(`#${key}List`), count: $(`#${key}Count`), pager: $(`#${key}Pager`), all: $(`#${key}All`),
    btn: key === "avail" ? $("#assignBtn") : $("#removeBtn"), state: clientView[key],
    scope: key === "avail" ? "available" : "owned",
  });
  const sides = { avail: side("avail"), owned: side("owned") };
  const updateBtn = (s) => { s.btn.disabled = !s.state.sel.size; s.btn.textContent = s.btn.id === "assignBtn"
    ? (s.state.sel.size ? `Assign ${s.state.sel.size} →` : "Assign →") : (s.state.sel.size ? `← Remove ${s.state.sel.size}` : "← Remove"); };
  const load = async (key) => {
    const s = sides[key];
    const res = await api(`/staff/clients/${clientId}/ids/${clientView.platform}`, { scope: s.scope, q: s.state.q, page: s.state.page });
    s.count.textContent = ` · ${inr.format(res.total)}`;
    s.all.checked = false;
    s.list.innerHTML = res.results.length ? res.results.map((r) => {
      const locked = key === "owned" && r.store;
      return `<label class="id-row ${r.is_active ? "" : "inactive"}">
        <input type="checkbox" value="${esc(r.id)}" ${locked ? "disabled" : ""} ${s.state.sel.has(r.id) ? "checked" : ""}>
        <span><b>${esc(r.name)}</b> <span class="muted">${esc([r.extra, r.city].filter(Boolean).join(", "))}</span>
          ${r.store ? `<br><small class="muted">used by ${esc(r.store)}</small>` : ""}${r.is_active ? "" : '<br><small class="warn">inactive</small>'}</span>
        ${r.is_dining == null ? "" : `<button type="button" class="btn light" data-dining="${esc(r.id)}" data-on="${r.is_dining ? 1 : 0}" title="Mark this id as a dine-in listing">${r.is_dining ? "Dining ✓" : "Dining"}</button>`}
        <code>${esc(r.id)}</code></label>`;
    }).join("") : `<p class="muted" style="padding:10px">${s.state.q ? "Nothing matches." : key === "avail" ? "No unassigned IDs left." : "No IDs assigned yet. Pick from the left."}</p>`;
    s.pager.innerHTML = res.pages > 1 ? `<button class="btn light" data-pg="-1" ${res.page <= 1 ? "disabled" : ""}>‹</button>
      <span class="muted">page ${res.page} / ${res.pages}</span><button class="btn light" data-pg="1" ${res.page >= res.pages ? "disabled" : ""}>›</button>` : "";
    updateBtn(s);
  };
  for (const [key, s] of Object.entries(sides)) {
    let t;
    $(`#${key}Search`).value = s.state.q;
    $(`#${key}Search`).addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { s.state.q = e.target.value.trim(); s.state.page = 1; load(key); }, 250); });
    s.list.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-dining]"); if (!b) return;
      e.preventDefault();
      try { await apiJSON(`/staff/clients/${clientId}/ids/${clientView.platform}`, "POST", { op: "dining", ids: [b.dataset.dining], value: b.dataset.on !== "1" }); load(key); }
      catch (err) { toast(userMessage(err)); }
    });
    s.list.addEventListener("change", (e) => { const cb = e.target; if (cb.type !== "checkbox") return; cb.checked ? s.state.sel.add(cb.value) : s.state.sel.delete(cb.value); updateBtn(s); });
    s.all.addEventListener("change", () => { s.list.querySelectorAll("input:not(:disabled)").forEach((cb) => { cb.checked = s.all.checked; cb.checked ? s.state.sel.add(cb.value) : s.state.sel.delete(cb.value); }); updateBtn(s); });
    s.pager.addEventListener("click", (e) => { const b = e.target.closest("[data-pg]"); if (!b) return; s.state.page += Number(b.dataset.pg); load(key); });
    s.btn.addEventListener("click", async () => {
      try {
        const res = await apiJSON(`/staff/clients/${clientId}/ids/${clientView.platform}`, "POST", { op: key === "avail" ? "assign" : "remove", ids: [...s.state.sel] });
        toast(res.message); s.state.sel.clear(); renderClient(page, clientId);
      } catch (err) { toast(userMessage(err)); }
    });
  }
  $("#idTabs").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    clientView.platform = b.dataset.p;
    for (const key of ["avail", "owned"]) Object.assign(clientView[key], { q: "", page: 1, sel: new Set() });
    renderClient(page, clientId);
  });
  load("avail"); load("owned");

  // brands
  page.querySelectorAll("[data-open-brand]").forEach((b) => b.addEventListener("click", async () => {
    $("#brandSelect").value = b.dataset.openBrand;
    location.hash = "#/setup";
    await loadBrand(Number(b.dataset.openBrand));
  }));
  $("#newBrandForClient").addEventListener("click", (e) => {
    e.preventDefault(); setup.newBrandClientId = clientId; location.hash = "#/setup";
  });
}

// ---------- login, user menu, viewer lock ----------
// sign-in screens share one split layout: brand panel on the left, the form on the right
function loginShell(form) {
  return `
    <div class="login-screen" id="loginScreen">
      <aside class="login-brand">
        <span class="brand-logo login-logo"><img class="brand-mark" src="assets/logo-mark.svg" alt="">Compass<small>by codeonto</small></span>
        <div class="login-pitch">
          <span class="login-eyebrow"><i></i>Live monitoring for restaurant brands</span>
          <h1>Every outlet, every platform, <span>one dashboard.</span></h1>
          <p>Reviews, complaints, uptime, payouts and item sales from Zomato, Swiggy and Google, in one place.</p>
          <div class="login-feats">
            <div><b>⭐ Reviews &amp; complaints</b><span>Reply before they cost you ratings</span></div>
            <div><b>📡 Store uptime</b><span>Know the moment an outlet goes offline</span></div>
            <div><b>📦 Stock-outs</b><span>Catch items that run out mid-service</span></div>
            <div><b>💸 Payouts</b><span>Reconcile every cycle, no spreadsheets</span></div>
          </div>
          <div class="login-sample" aria-hidden="true">
            <span class="dot"></span>
            <div><b>Outlet offline on Zomato</b><small>Example alert · sent on WhatsApp and email</small></div>
            <em>Alert</em>
          </div>
        </div>
        <div class="login-platforms">
          <small>Works with</small>
          <img src="assets/zomato.png" alt="Zomato"><img src="assets/swiggy.png" alt="Swiggy"><img src="assets/google.png" alt="Google">
        </div>
      </aside>
      <main class="login-main">
        <form class="login-card" id="loginForm">
          <span class="brand-logo login-logo login-logo-sm"><img class="brand-mark" src="assets/logo-mark.svg" alt="">Compass<small>by codeonto</small></span>
          ${form}
        </form>
      </main>
    </div>`;
}

function showLogin() {
  if ($("#loginScreen")) return;
  document.body.insertAdjacentHTML("beforeend", loginShell(`
        <div class="login-head"><h2>Welcome back</h2><p class="login-note">Sign in to see how your outlets are doing today.</p></div>
        <label>Username<input name="username" autocomplete="username" placeholder="you@brand.com" required autofocus></label>
        <label>Password<input name="password" type="password" autocomplete="current-password" placeholder="Your password" required></label>
        <p class="login-error" id="loginError"></p>
        <button class="btn blue login-submit" type="submit">Sign in</button>
        <button class="login-link" type="button" id="otpLink">Email me a login code instead</button>
        <button class="login-link" type="button" id="forgotLink">Forgot password?</button>`));
  $("#forgotLink").addEventListener("click", showForgot);
  $("#otpLink").addEventListener("click", () => showOtp());
  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      await api("/auth/me").catch(() => null);  // sets the CSRF cookie
      await apiJSON("/auth/login", "POST", { username: f.get("username"), password: f.get("password") });
      location.reload();
    } catch (err) { $("#loginError").textContent = userMessage(err); }
  });
}

function showLoginCard(title, fields, submit) {
  $("#loginScreen")?.remove();
  document.body.insertAdjacentHTML("beforeend", loginShell(`
        <div class="login-head"><h2>${title}</h2></div>
        ${fields}
        <p class="login-error" id="loginError"></p>
        <button class="btn blue login-submit" type="submit">${submit}</button>
        <button class="login-link" type="button" id="backToLogin">Back to sign in</button>`));
  $("#backToLogin").addEventListener("click", () => {
    history.replaceState(null, "", location.pathname);  // drop any reset link so signing in doesn't return to it
    $("#loginScreen").remove();
    showLogin();
  });
}

// sign in with a 6-digit code emailed to the account: step 1 asks for the email, step 2 for the code
function showOtp(identifier = "") {
  if (!identifier) {
    showLoginCard("Sign in with a code", `
      <p class="login-note">Enter the email on your Codeonto login and we'll send you a 6-digit code.</p>
      <label>Email<input name="identifier" type="email" autocomplete="email" placeholder="you@brand.com" required autofocus></label>`, "Email me a code");
    $("#loginForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = e.target.querySelector('[type="submit"]'); btn.disabled = true;
      const who = new FormData(e.target).get("identifier").trim();
      try { await apiJSON("/auth/otp/request", "POST", { identifier: who }); showOtp(who); }
      catch (err) { $("#loginError").textContent = userMessage(err); btn.disabled = false; }
    });
    return;
  }
  showLoginCard("Enter your code", `
    <p class="login-note">If <b>${esc(identifier)}</b> has a Codeonto login, a 6-digit code is on its way. It expires in 10 minutes.</p>
    <label>Code<input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9 ]{6,7}" maxlength="7" placeholder="123456" required autofocus></label>
    <button class="login-link" type="button" id="otpResend">Send a new code</button>`, "Sign in");
  $("#otpResend").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try { await apiJSON("/auth/otp/request", "POST", { identifier }); toast("If you can ask for another one, a new code is on its way (one a minute)."); }
    catch (err) { toast(userMessage(err)); }
    setTimeout(() => { e.target.disabled = false; }, 60000);
  });
  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('[type="submit"]'); btn.disabled = true;
    try {
      await api("/auth/me").catch(() => null);  // sets the CSRF cookie
      await apiJSON("/auth/otp/verify", "POST", { identifier, code: new FormData(e.target).get("code") });
      location.reload();
    } catch (err) { $("#loginError").textContent = userMessage(err); btn.disabled = false; }
  });
}

function showForgot() {
  showLoginCard("Forgot password", `
    <p class="login-note">Enter your username or email and we'll send you a link to choose a new password.</p>
    <label>Username or email<input name="identifier" autocomplete="username" required autofocus></label>`, "Send reset link");
  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target, btn = form.querySelector('[type="submit"]');
    btn.disabled = true;
    try {
      await apiJSON("/auth/password/forgot", "POST", { identifier: new FormData(form).get("identifier") });
      form.querySelector("label").remove();
      btn.remove();
      form.querySelector(".login-note").textContent = "If that login has an email address, a reset link is on its way. It expires in 1 hour, so check your spam folder if you don't see it.";
    } catch (err) { $("#loginError").textContent = userMessage(err); btn.disabled = false; }
  });
}

function showReset(uid, token) {
  showLoginCard("Choose a new password", `
    <label>New password<input name="next" type="password" autocomplete="new-password" required autofocus></label>
    <label>Confirm new password<input name="confirm" type="password" autocomplete="new-password" required></label>`, "Save password");
  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target, f = new FormData(form), error = $("#loginError"), btn = form.querySelector('[type="submit"]');
    error.textContent = "";
    if (f.get("next") !== f.get("confirm")) { error.textContent = "The passwords don't match"; return; }
    btn.disabled = true;
    try {
      await apiJSON("/auth/password/reset", "POST", { uid, token, new_password: f.get("next") });
      history.replaceState(null, "", location.pathname);
      form.querySelectorAll("label").forEach((l) => l.remove());
      btn.remove();
      form.querySelector("h2").insertAdjacentHTML("afterend", '<p class="login-note">Your password has been changed. You can sign in with it now.</p>');
    } catch (err) { error.textContent = userMessage(err); btn.disabled = false; }
  });
}

function renderUser() {
  const btn = $("#userBtn"), menu = $("#userMenu"), me = state.me;
  btn.textContent = me.name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  btn.title = me.name;
  const org = me.client ? `${me.client.name} · ${TEAM_ROLES[me.role] || me.role || ""}` : "Codeonto staff";
  menu.innerHTML = `
    <div class="user-pop-head"><b>${esc(me.name)}</b><span class="muted">${esc(org)}</span></div>
    <a class="user-pop-item" href="#/profile">${icon("profile")}Profile</a>
    ${me.can_manage && me.client ? `<a class="user-pop-item" href="#/team">${icon("team")}Team</a>` : ""}
    <button class="user-pop-item" id="logoutBtn" type="button">${icon("logout")}Log out</button>`;
  const setOpen = (open) => { menu.hidden = !open; btn.setAttribute("aria-expanded", String(open)); };
  btn.addEventListener("click", () => setOpen(menu.hidden));
  menu.addEventListener("click", (e) => { if (e.target.closest("a")) setOpen(false); });
  document.addEventListener("click", (e) => { if (!e.target.closest(".user-menu")) setOpen(false); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !menu.hidden) { setOpen(false); btn.focus(); }
  });
  $("#logoutBtn").addEventListener("click", async () => {
    await apiJSON("/auth/logout", "POST", {}).catch(() => null);
    location.reload();
  });
}

function renderProfile(page) {
  const me = state.me;
  $("#pageTitle").textContent = "Profile";
  $("#pageSub").textContent = "Your login details and password";
  const roleLabel = me.role ? me.role[0].toUpperCase() + me.role.slice(1) : "—";
  const detail = (label, value) => `<div class="profile-detail"><span class="muted">${label}</span><strong>${esc(value || "—")}</strong></div>`;
  page.innerHTML = `
    <div class="card">
      <div class="card-head"><h3>Your details</h3></div>
      <div class="profile-details">
        ${detail("Name", me.name)}
        ${detail("Username", me.username)}
        ${detail("Email", me.email)}
        ${detail("Client", me.client ? me.client.name : "Codeonto staff")}
        ${detail("Role", roleLabel)}
      </div>
    </div>
    <form class="card profile-password" id="passwordForm">
      <div class="card-head"><h3>Change password</h3></div>
      <input type="text" autocomplete="username" value="${esc(me.username)}" hidden>
      <div class="form-row">
        <label>Current password<input name="current" type="password" autocomplete="current-password" required></label>
        <label>New password<input name="next" type="password" autocomplete="new-password" required></label>
        <label>Confirm new password<input name="confirm" type="password" autocomplete="new-password" required></label>
      </div>
      <p class="login-error" id="passwordError"></p>
      <button class="btn blue" type="submit">Update password</button>
    </form>`;
  $("#passwordForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target, f = new FormData(form), error = $("#passwordError");
    error.textContent = "";
    if (f.get("next") !== f.get("confirm")) { error.textContent = "The new passwords don't match"; return; }
    const btn = form.querySelector("button");
    btn.disabled = true;
    try {
      await apiJSON("/auth/password", "POST", { current_password: f.get("current"), new_password: f.get("next") });
      form.reset();
      toast("Password updated");
    } catch (err) { error.textContent = userMessage(err); }
    btn.disabled = false;
  });
}

// ---------- team: the owner's logins and which outlets each manager can see ----------
const TEAM_ROLES = { admin: "Owner", manager: "Outlet manager", viewer: "Viewer" };

function outletPicker(brands, selected = []) {
  const chosen = new Set(selected);
  const groups = brands.filter((b) => b.outlets.length).map((b) => `<div class="picker-brand">
      <label class="picker-all"><input type="checkbox" data-brand-all> <b>${esc(b.name)}</b> <span class="muted">· ${b.outlets.length}</span></label>
      ${b.outlets.map((o) => `<label class="id-row" data-search="${esc(`${b.name} ${o.name} ${o.city} ${o.zomato_id || ""}`.toLowerCase())}">
        <input type="checkbox" name="outlet" value="${o.id}" ${chosen.has(o.id) ? "checked" : ""}>
        <span><b>${esc(o.name)}</b> <span class="muted">${esc([o.city, o.zomato_id].filter(Boolean).join(" · "))}</span></span></label>`).join("")}
    </div>`).join("");
  return `<div class="outlet-picker">
    <input type="search" data-outlet-search placeholder="Search outlets" aria-label="Search outlets">
    <div class="id-list">${groups || '<p class="muted" style="padding:10px">No outlets yet. Add them under Brands &amp; Outlets first.</p>'}</div>
  </div>`;
}

function wireOutletPicker(root) {
  const syncAll = (group) => {
    const boxes = [...group.querySelectorAll('input[name="outlet"]')];
    group.querySelector("[data-brand-all]").checked = boxes.length > 0 && boxes.every((b) => b.checked);
  };
  root.querySelectorAll(".picker-brand").forEach((group) => {
    syncAll(group);
    group.addEventListener("change", (e) => {
      if (e.target.matches("[data-brand-all]")) {
        group.querySelectorAll('input[name="outlet"]').forEach((b) => { b.checked = e.target.checked; });
      } else syncAll(group);
    });
  });
  root.querySelector("[data-outlet-search]").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    root.querySelectorAll(".id-row[data-search]").forEach((row) => { row.hidden = !row.dataset.search.includes(q); });
  });
}

const pickedOutlets = (root) => [...root.querySelectorAll('input[name="outlet"]:checked')].map((b) => Number(b.value));

async function renderTeam(page, clientId) {
  const team = await api(`/clients/${clientId}/team`);
  $("#pageTitle").textContent = "Team";
  $("#pageSub").textContent = `Logins for ${team.client.name} and the outlets each manager can see`;
  const firstLogin = !team.users.length;  // a new client's first login is normally its owner
  const outletName = {};
  team.brands.forEach((b) => b.outlets.forEach((o) => { outletName[o.id] = o.name; }));
  const scopeText = (u) => {
    if (u.role !== "manager") return u.role === "viewer" ? "All outlets, read only" : "All outlets";
    const names = u.outlet_ids.map((id) => outletName[id]).filter(Boolean);
    return names.length ? (names.length > 2 ? `${names.slice(0, 2).join(", ")} +${names.length - 2} more` : names.join(", ")) : "No outlets";
  };
  page.innerHTML = `
    <div class="card">
      <div class="card-head"><h3>Logins</h3><div class="btn-row">
        ${state.me.is_staff ? `<a class="btn light" href="#/clients/${clientId}">Back to client</a>` : ""}
        <button class="btn blue" id="addMemberBtn">${icon("plus")} Add login</button></div></div>
      <form class="team-form" id="memberForm" hidden>
        <div class="form-row">
          <label>Username<input name="username" required autocomplete="off"></label>
          <label>Full name<input name="name" autocomplete="off"></label>
          <label>Email<input name="email" type="email" autocomplete="off"></label>
          <label>Password<input name="password" type="password" required autocomplete="new-password"></label>
          <label>Role<select name="role" id="memberRole">
            <option value="manager">Outlet manager: only their outlets, can draft replies</option>
            <option value="viewer">Viewer: all outlets, read only</option>
            <option value="admin" ${firstLogin ? "selected" : ""}>Owner: everything, including this page</option></select></label>
        </div>
        <div id="memberOutlets" ${firstLogin ? "hidden" : ""}><p class="team-hint">Outlets this manager can see</p>${outletPicker(team.brands)}</div>
        <p class="login-error" id="memberError"></p>
        <button class="btn blue" type="submit">Create login</button>
      </form>
      <div class="table-wrap team-table"><table>
        <thead><tr><th>Login</th><th>Role</th><th>Outlets</th><th>Last login</th><th></th></tr></thead>
        <tbody>${team.users.map((u) => {
          const self = u.username === state.me.username;
          return `<tr data-member="${u.id}">
            <td><b>${esc(u.username)}</b>${self ? ' <span class="muted">(you)</span>' : ""}<br><span class="muted">${esc([u.name, u.email].filter(Boolean).join(" · "))}</span>${u.is_active ? "" : ' <span class="status pending">disabled</span>'}</td>
            <td>${self ? esc(TEAM_ROLES[u.role]) : `<select data-role aria-label="Role for ${esc(u.username)}">${Object.entries(TEAM_ROLES).map(([v, l]) => `<option value="${v}" ${v === u.role ? "selected" : ""}>${l}</option>`).join("")}</select>`}</td>
            <td>${esc(scopeText(u))}</td>
            <td class="muted">${u.last_login ? timeAgo(u.last_login) : "never"}</td>
            <td>${self ? "" : `<div class="btn-row">
              ${u.role === "manager" ? '<button class="btn light" data-outlets>Outlets</button>' : ""}
              <button class="btn light" data-pass>Password</button>
              <button class="btn light" data-toggle>${u.is_active ? "Disable" : "Enable"}</button>
              ${state.me.is_staff ? `<button class="icon-del" data-delete title="Delete login" aria-label="Delete ${esc(u.username)}">${icon("trash")}</button>` : ""}</div>`}</td>
          </tr>`;
        }).join("")}</tbody>
      </table></div>
    </div>`;

  const form = $("#memberForm");
  $("#addMemberBtn").addEventListener("click", () => { form.hidden = !form.hidden; });
  wireOutletPicker(form);
  $("#memberRole").addEventListener("change", (e) => { $("#memberOutlets").hidden = e.target.value !== "manager"; });
  form.addEventListener("change", () => { $("#memberError").textContent = ""; });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    $("#memberError").textContent = "";
    const f = Object.fromEntries(new FormData(form));
    delete f.outlet;
    try {
      const u = await apiJSON(`/clients/${clientId}/team`, "POST", { ...f, outlet_ids: pickedOutlets(form) });
      toast(`Login ${u.username} created`);
      renderTeam(page, clientId);
    } catch (err) { $("#memberError").textContent = userMessage(err); }
  });

  // the outlet picker opens in a row under the login; a new manager must pick outlets before the role is saved
  const openPicker = (tr, u, role) => {
    page.querySelector(".team-edit")?.remove();
    const edit = document.createElement("tr");
    edit.className = "team-edit";
    edit.innerHTML = `<td colspan="5"><p class="team-hint">Outlets ${esc(u.username)} can see</p>${outletPicker(team.brands, u.outlet_ids)}
      <div class="btn-row"><button class="btn blue" data-save>Save</button><button class="btn light" data-cancel>Cancel</button></div></td>`;
    tr.after(edit);
    wireOutletPicker(edit);
    edit.querySelector("[data-cancel]").addEventListener("click", () => renderTeam(page, clientId));
    edit.querySelector("[data-save]").addEventListener("click", async () => {
      try {
        await apiJSON(`/clients/${clientId}/team/${u.id}`, "PATCH", { role, outlet_ids: pickedOutlets(edit) });
        toast("Outlets updated");
        renderTeam(page, clientId);
      } catch (err) { toast(userMessage(err)); }
    });
  };

  const openPassword = (tr, u) => {
    page.querySelector(".team-edit")?.remove();
    const edit = document.createElement("tr");
    edit.className = "team-edit";
    edit.innerHTML = `<td colspan="5"><form>
      <p class="team-hint">New password for ${esc(u.username)}. This signs them out everywhere.</p>
      <div class="form-row">
        <label>New password<input name="next" type="password" autocomplete="new-password" required></label>
        <label>Confirm new password<input name="confirm" type="password" autocomplete="new-password" required></label>
      </div>
      <p class="login-error"></p>
      <div class="btn-row"><button class="btn blue" type="submit">Save password</button><button class="btn light" type="button" data-cancel>Cancel</button></div>
    </form></td>`;
    tr.after(edit);
    const form = edit.querySelector("form"), error = edit.querySelector(".login-error");
    form.elements.next.focus();
    edit.querySelector("[data-cancel]").addEventListener("click", () => edit.remove());
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = new FormData(form);
      error.textContent = "";
      if (f.get("next") !== f.get("confirm")) { error.textContent = "The passwords don't match"; return; }
      const save = form.querySelector('[type="submit"]');
      save.disabled = true;
      try {
        await apiJSON(`/clients/${clientId}/team/${u.id}`, "PATCH", { password: f.get("next") });
        toast("Password changed");
        edit.remove();
      } catch (err) { error.textContent = userMessage(err); save.disabled = false; }
    });
  };

  const openDelete = (tr, u) => {
    page.querySelector(".team-edit")?.remove();
    const edit = document.createElement("tr");
    edit.className = "team-edit";
    edit.innerHTML = `<td colspan="5"><p class="team-hint">Delete ${esc(u.username)}? They won't be able to sign in any more. This can't be undone.</p>
      <div class="btn-row"><button class="btn danger" data-confirm>Delete login</button><button class="btn light" data-cancel>Cancel</button></div></td>`;
    tr.after(edit);
    edit.querySelector("[data-cancel]").addEventListener("click", () => edit.remove());
    edit.querySelector("[data-confirm]").addEventListener("click", async () => {
      try {
        await api(`/clients/${clientId}/team/${u.id}`, {}, { method: "DELETE" });
        toast("Login deleted");
        renderTeam(page, clientId);
      } catch (err) { toast(userMessage(err)); }
    });
  };

  page.querySelectorAll("[data-member]").forEach((tr) => {
    const u = team.users.find((x) => x.id === Number(tr.dataset.member));
    if (u.username === state.me.username) return;
    const url = `/clients/${clientId}/team/${u.id}`;
    tr.querySelector("[data-role]").addEventListener("change", async (e) => {
      if (e.target.value === "manager") return openPicker(tr, u, "manager");
      try { await apiJSON(url, "PATCH", { role: e.target.value }); toast("Role updated"); }
      catch (err) { toast(userMessage(err)); }
      renderTeam(page, clientId);
    });
    tr.querySelector("[data-outlets]")?.addEventListener("click", () => openPicker(tr, u, "manager"));
    tr.querySelector("[data-pass]").addEventListener("click", () => openPassword(tr, u));
    tr.querySelector("[data-delete]")?.addEventListener("click", () => openDelete(tr, u));
    tr.querySelector("[data-toggle]").addEventListener("click", async () => {
      try { await apiJSON(url, "PATCH", { is_active: !u.is_active }); renderTeam(page, clientId); } catch (err) { toast(userMessage(err)); }
    });
  });
}

function lockIfViewer(root) {
  if (state.me.can_edit) return;
  root.querySelectorAll("button, input, select").forEach((el) => {
    if (!["outletSearch"].includes(el.id)) el.disabled = true;
  });
}

// ---------- bulk CSV upload ----------
const csvState = { text: "" };

function downloadTemplate() {
  const csv = "store_name,area,city,zomato_res_id,swiggy_id,google_location_id\nSector 29,Sector 29,Gurugram,,,\n";
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = `${state.config.brand.name.replace(/[^a-z0-9]+/gi, "_")}_stores.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function previewCsv(file) {
  csvState.text = await file.text();
  $("#csvSave").disabled = true;
  $("#csvResult").innerHTML = `<p class="muted">Checking…</p>`;
  try {
    const res = await apiJSON(`/brands/${state.brandId}/outlets/import`, "POST", { csv: csvState.text, commit: false });
    renderCsvResult(res);
  } catch (e) { $("#csvResult").innerHTML = `<p class="login-error">${esc(userMessage(e))}</p>`; }
}

function renderCsvResult(res) {
  const s = res.summary;
  const blocking = res.file_errors.filter((e) => !e.startsWith("Ignored"));
  const ok = res.rows.length && !s.errors && !blocking.length;
  $("#csvSave").disabled = !ok || !state.me.can_edit;
  $("#csvSave").textContent = ok ? `Save ${s.rows} store${s.rows === 1 ? "" : "s"}` : "Save";
  const cell = (v) => v ? `<code>${esc(v)}</code>` : `<span class="muted">—</span>`;
  $("#csvResult").innerHTML = `
    ${res.file_errors.map((e) => `<p class="${e.startsWith("Ignored") ? "muted" : "login-error"}">${esc(e)}</p>`).join("")}
    ${res.rows.length ? `<p><b>${s.rows}</b> rows · ${s.create} new · ${s.update} updates · <b class="${s.errors ? "warn" : ""}">${s.errors} with errors</b></p>
    <div class="table-wrap" style="max-height:340px"><table class="setup-table">
      <thead><tr><th>Line</th><th>Store</th><th>City</th><th>Zomato</th><th>Swiggy</th><th>Google</th><th>Action</th><th>Problems</th></tr></thead>
      <tbody>${res.rows.map((r) => `<tr class="${r.errors.length ? "row-error" : ""}">
        <td>${r.line}</td><td>${esc(r.outlet_name)}</td><td>${esc(r.city || "")}</td>
        <td>${cell(r.zomato)}</td><td>${cell(r.swiggy)}</td><td>${cell(r.google)}</td>
        <td>${r.action}</td><td>${r.errors.length ? r.errors.map(esc).join("<br>") : "✓"}</td></tr>`).join("")}</tbody>
    </table></div>` : ""}`;
}

async function saveCsv() {
  $("#csvSave").disabled = true;
  try {
    const res = await apiJSON(`/brands/${state.brandId}/outlets/import`, "POST", { csv: csvState.text, commit: true });
    if (!res.committed) return renderCsvResult(res);
    toast(`Saved ${res.summary.rows} stores (${res.summary.create} new, ${res.summary.update} updated)`);
    await loadBrand(state.brandId);
  } catch (e) { toast(userMessage(e)); $("#csvSave").disabled = false; }
}

// ---------- boot ----------
async function loadBrandList() {
  // Brands grouped by client
  state.brands = await api("/brands");
  $(".brand-picker").style.display = state.brands.length ? "" : "none";
  const byClient = {};
  state.brands.forEach((b) => { (byClient[b.client] ||= []).push(b); });
  $("#brandSelect").innerHTML = Object.entries(byClient).map(([client, list]) =>
    `<optgroup label="${esc(client)} · ${list.length} brand${list.length === 1 ? "" : "s"}">${list.map((b) => `<option value="${b.id}">${esc(b.name)}</option>`).join("")}</optgroup>`).join("");
}

async function boot() {
  if (currentRoute() === "reset") {  // arrived from a password reset email
    const q = new URLSearchParams(location.hash.split("?")[1] || "");
    return showReset(q.get("uid") || "", q.get("token") || "");
  }
  try {
    state.me = await api("/auth/me");
  } catch (e) {
    if (e.status === 401) return showLogin();
    throw e;
  }
  renderUser();
  startOfflineWatch();
  await loadBrandList();
  if (!state.brands.length) {
    state.config = null;
    return render();
  }
  const saved = store.get("ss_brand");
  const initial = state.brands.find((b) => String(b.id) === saved)?.id || state.brands[0].id;
  $("#brandSelect").value = initial;
  await loadBrand(initial);
}

// back from Google's consent screen: tell the user how it went, then tidy the address bar
function googleReturnNotice() {
  const q = new URLSearchParams(location.hash.split("?")[1] || "");
  if (!q.get("google")) return;
  toast(q.get("google") === "connected" ? "Google connected. Locations appear after the first sync (a minute or two)." : `Google connection failed: ${q.get("reason") || "try again"}`);
  history.replaceState(null, "", "#/setup");
}
setTimeout(googleReturnNotice, 800);

$("#brandSelect").addEventListener("change", (e) => loadBrand(Number(e.target.value)));

// ---------- the brand picker: a search box over the brands, grouped by client ----------
// The hidden <select id="brandSelect"> stays the one place the chosen brand lives (other code reads and sets it); this is the face on it.
(() => {
  const sel = $("#brandSelect"), btn = $("#brandBtn"), pop = $("#brandPop"), box = $("#brandSearch"), list = $("#brandList");
  const nativeValue = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
  const labelNow = () => (state.brands || []).find((b) => String(b.id) === String(sel.value))?.name || sel.selectedOptions[0]?.textContent || "Brand";
  const sync = () => { $("#brandBtnText").textContent = labelNow(); };
  Object.defineProperty(sel, "value", { get() { return nativeValue.get.call(this); }, set(v) { nativeValue.set.call(this, v); sync(); }, configurable: true });
  new MutationObserver(sync).observe(sel, { childList: true, subtree: true });  // the list was just filled in
  let shown = [], at = -1;
  const draw = () => {
    const words = box.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const byClient = new Map();
    (state.brands || []).forEach((b) => {
      const hay = `${b.name} ${b.client}`.toLowerCase();
      if (words.every((w) => hay.includes(w))) (byClient.get(b.client) || byClient.set(b.client, []).get(b.client)).push(b);
    });
    shown = [...byClient.values()].flat();
    const cur = String(sel.value);
    at = Math.max(0, shown.findIndex((b) => String(b.id) === cur));
    list.innerHTML = shown.length ? [...byClient.entries()].map(([client, bs]) => `<div class="brand-group">${esc(client)} <small>· ${bs.length} brand${bs.length === 1 ? "" : "s"}</small></div>` +
      bs.map((b) => `<div class="brand-opt ${String(b.id) === cur ? "cur" : ""}" role="option" data-id="${b.id}" aria-selected="${String(b.id) === cur}"><span class="tick">${String(b.id) === cur ? "✓" : ""}</span>${esc(b.name)}</div>`).join("")).join("")
      : `<div class="brand-none">No brand matches “${esc(box.value.trim())}”</div>`;
    mark();
  };
  const mark = () => { list.querySelectorAll(".brand-opt").forEach((el, i) => el.classList.toggle("hot", i === at)); list.querySelectorAll(".brand-opt")[at]?.scrollIntoView({ block: "nearest" }); };
  const open = () => { pop.hidden = false; btn.setAttribute("aria-expanded", "true"); box.value = ""; draw(); box.focus(); };
  const close = (back = true) => { pop.hidden = true; btn.setAttribute("aria-expanded", "false"); if (back) btn.focus(); };
  const pick = (id) => { if (id == null) return; close(); if (String(sel.value) !== String(id)) { sel.value = id; sel.dispatchEvent(new Event("change", { bubbles: true })); } };
  btn.addEventListener("click", () => (pop.hidden ? open() : close(false)));
  box.addEventListener("input", draw);
  box.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); at = Math.min(shown.length - 1, at + 1); mark(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); at = Math.max(0, at - 1); mark(); }
    else if (e.key === "Enter") { e.preventDefault(); pick(shown[at]?.id); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
  });
  list.addEventListener("click", (e) => { const o = e.target.closest(".brand-opt"); if (o) pick(o.dataset.id); });
  list.addEventListener("mousemove", (e) => { const o = e.target.closest(".brand-opt"); if (!o) return; const i = [...list.querySelectorAll(".brand-opt")].indexOf(o); if (i !== at) { at = i; mark(); } });
  document.addEventListener("click", (e) => { if (!pop.hidden && !e.target.closest(".brand-picker")) close(false); });
  sync();
})();

$("#locationBtn").addEventListener("click", () => setOutletPicker($("#locationPop").hidden));
$("#locationSearch").addEventListener("input", renderOutletList);
$("#locationList").addEventListener("change", (e) => {
  const box = e.target;
  if (box.id === "locationAll") {
    const q = $("#locationSearch").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    platformLocations().filter((l) => q.every((w) => l.search.includes(w))).forEach((l) => (box.checked ? pickSel.add(String(l.id)) : pickSel.delete(String(l.id))));
  } else if (box.dataset.location) {
    box.checked ? pickSel.add(box.dataset.location) : pickSel.delete(box.dataset.location);
  }
  renderOutletList();
});
$("#locationApply").addEventListener("click", () => applyOutlets([...pickSel]));
$("#locationClear").addEventListener("click", () => applyOutlets([]));
$("#locationPop").addEventListener("keydown", (e) => {
  const items = [...$("#locationList").querySelectorAll("[data-location]")];
  const at = items.indexOf(document.activeElement);
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const next = e.key === "ArrowDown" ? at + 1 : at - 1;
    if (next < 0) $("#locationSearch").focus(); else items[Math.min(next, items.length - 1)]?.focus();
  } else if (e.key === "Enter" && document.activeElement === $("#locationSearch")) {
    e.preventDefault();
    items[0]?.click();
  }
});
document.addEventListener("click", (e) => { if (!e.target.closest("#outletFilter")) setOutletPicker(false); });
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#locationPop").hidden) { setOutletPicker(false); $("#locationBtn").focus(); }
});
$("#platformSelect").addEventListener("change", (e) => {
  state.platform = e.target.value;
  const onPlatform = new Set(platformLocations().map((l) => String(l.id)));
  state.locationId = selIds().filter((id) => onPlatform.has(id)).join(",");
  showSelectedOutlet();
  render();
});
$("#rangeSeg").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.custom) {  // open the date pickers, pre-filled with the range in use
    const r = range();
    $("#rangeFrom").value = r.start; $("#rangeTo").value = r.end;
    $("#rangeFrom").max = $("#rangeTo").max = isoDate(new Date());
    $("#rangePop").hidden = !$("#rangePop").hidden;
    return;
  }
  state.custom = null; $("#rangePop").hidden = true; $("#customBtn").textContent = "Custom";
  $("#rangeSeg .active").classList.remove("active"); b.classList.add("active");
  state.days = Number(b.dataset.days); render();
});
$("#rangeApply").addEventListener("click", () => {
  const start = $("#rangeFrom").value, end = $("#rangeTo").value;
  if (!start || !end) return toast("Pick both dates");
  if (start > end) return toast("The start date is after the end date");
  applyCustomRange(start, end);
});
// quick picks: Today, Yesterday, Last 7/30 days, This month, Last month
$("#rangeQuick").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-quick]"); if (!b) return;
  const q = b.dataset.quick, now = new Date(), day = (n) => { const d = new Date(now); d.setDate(d.getDate() - n); return isoDate(d); };
  let start, end = isoDate(now);
  if (q === "today") start = end;
  else if (q === "yesterday") start = end = day(1);
  else if (q === "month") start = isoDate(new Date(now.getFullYear(), now.getMonth(), 1));
  else if (q === "lastmonth") { start = isoDate(new Date(now.getFullYear(), now.getMonth() - 1, 1)); end = isoDate(new Date(now.getFullYear(), now.getMonth(), 0)); }
  else start = day(Number(q) - 1);
  applyCustomRange(start, end, b.textContent);
});
document.addEventListener("click", (e) => { if (!e.target.closest("#rangePop, #rangeSeg")) $("#rangePop").hidden = true; });
$("#menuToggle").addEventListener("click", () => {
  if (window.matchMedia("(max-width: 860px)").matches) document.body.classList.toggle("nav-open");
  else {
    document.body.classList.toggle("collapsed");
    try { localStorage.setItem("sidebar", document.body.classList.contains("collapsed") ? "icons" : "open"); } catch (e) { /* private window */ }
  }
});
// desktop starts with the icon rail (it opens on hover) unless the person pinned it open
try { if (localStorage.getItem("sidebar") !== "open") document.body.classList.add("collapsed"); } catch (e) { document.body.classList.add("collapsed"); }
$("#scrim").addEventListener("click", () => document.body.classList.remove("nav-open"));
$("#fullscreenBtn").addEventListener("click", () => {
  if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen?.();
});
window.addEventListener("hashchange", render);

boot().catch((e) => { $("#page").innerHTML = `<div class="card empty-state"><h3>Something went wrong</h3><p>${esc(userMessage(e))}</p></div>`; });


// ---------- AI assistant (read-only chat) ----------
const assistant = { open: false, busy: false, thread: null, started: false };
const ASK_EXAMPLES = [
  "Which outlets have the lowest rating this month?",
  "What is out of stock right now?",
  "Summarise this week's negative reviews",
  "How are Swiggy and Zomato orders trending vs last week?",
  "What should I fix first to improve my Google listing?",
];

function ensureAssistant() {
  if ($("#askBtn")) return;
  document.body.insertAdjacentHTML("beforeend", `
    <button id="askBtn" class="ask-fab" title="Ask Codeonto Assistant">${icon("ai_replies")}<span>Ask</span></button>
    <aside id="askPanel" class="ask-panel" hidden>
      <header><b>${icon("ai_replies")} Codeonto Assistant</b>
        <span><button id="askNew" title="New conversation">New chat</button><button id="askClose" title="Close">×</button></span></header>
      <div id="askMsgs" class="ask-msgs"></div>
      <form id="askForm" class="ask-form"><textarea id="askInput" rows="1" placeholder="Ask about your reviews, sales, stock-outs, listings…" maxlength="2000"></textarea>
        <button class="btn blue" id="askSend" type="submit">Send</button></form>
      <small class="ask-note">Read-only. It sees only your data and can make mistakes: check important numbers.</small>
    </aside>`);
  try { assistant.thread = sessionStorage.getItem("ss_ask_thread"); } catch { /* private window */ }
  $("#askBtn").addEventListener("click", () => toggleAsk(true));
  $("#askClose").addEventListener("click", () => toggleAsk(false));
  $("#askNew").addEventListener("click", () => { assistant.thread = null; try { sessionStorage.removeItem("ss_ask_thread"); } catch { /* */ } $("#askMsgs").innerHTML = ""; askWelcome(); });
  $("#askForm").addEventListener("submit", (e) => { e.preventDefault(); sendAsk($("#askInput").value); });
  $("#askInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#askForm").requestSubmit(); } });
  askWelcome();
}

function toggleAsk(open) {
  assistant.open = open;
  $("#askPanel").hidden = !open; $("#askBtn").hidden = open;
  if (open) $("#askInput").focus();
}

function askWelcome() {
  $("#askMsgs").innerHTML = `<div class="ask-welcome"><p><b>Hi! Ask me anything.</b> I can look up your reviews, ratings, sales, stock-outs and listing health, explain a number, or suggest what to do next.</p>
    ${ASK_EXAMPLES.map((q) => `<button class="ask-chip" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>`;
  $("#askMsgs").querySelectorAll(".ask-chip").forEach((b) => b.addEventListener("click", () => sendAsk(b.dataset.q)));
}

// small markdown subset: **bold**, `code`, lists, tables, headings, line breaks
function askMarkdown(text) {
  const inline = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
  const out = []; const lines = text.split("\n"); let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^\s*\|.*\|\s*$/.test(l) && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1] || "")) {
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const head = cells(l); i += 2; const body = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) body.push(cells(lines[i++]));
      out.push(`<div class="ask-table"><table><thead><tr>${head.map((h) => `<th>${inline(h)}</th>`).join("")}</tr></thead><tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
      const ordered = /^\s*\d+\./.test(l); const items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, ""));
      out.push(`<${ordered ? "ol" : "ul"}>${items.map((t) => `<li>${inline(t)}</li>`).join("")}</${ordered ? "ol" : "ul"}>`);
      continue;
    }
    if (/^#{1,4}\s/.test(l)) out.push(`<h4>${inline(l.replace(/^#{1,4}\s/, ""))}</h4>`);
    else if (l.trim()) out.push(`<p>${inline(l)}</p>`);
    i++;
  }
  return out.join("");
}

function askQueries(queries) {
  if (!queries?.length) return "";
  return `<details class="ask-how"><summary>How I got this (${queries.length} quer${queries.length === 1 ? "y" : "ies"})</summary>${queries.map((q) => `
    <div class="ask-q"><pre>${esc(q.sql)}</pre>${q.error ? `<div class="ask-err">${esc(q.error)}</div>`
      : q.columns ? `<div class="ask-table"><table><thead><tr>${q.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>
        ${q.rows.slice(0, 6).map((r) => `<tr>${q.columns.map((c) => `<td>${esc(r[c] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
        <small class="muted">${q.total_rows} row${q.total_rows === 1 ? "" : "s"}${q.truncated ? "+" : ""} · ${q.ms} ms</small>` : ""}</div>`).join("")}</details>`;
}

async function sendAsk(text) {
  text = (text || "").trim();
  if (!text || assistant.busy) return;
  assistant.busy = true;
  const box = $("#askMsgs");
  box.querySelector(".ask-welcome")?.remove();
  box.insertAdjacentHTML("beforeend", `<div class="ask-msg me">${esc(text)}</div><div class="ask-msg bot thinking" id="askThinking"><span class="dots"><i></i><i></i><i></i></span> Thinking…</div>`);
  box.scrollTop = box.scrollHeight;
  $("#askInput").value = ""; $("#askSend").disabled = true;
  try {
    const r = range();
    const res = await api("/assistant/chat", {}, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({
      message: text, thread_id: assistant.thread,
      context: { brand_id: state.brandId, outlet_id: state.locationId, start: r.start, end: r.end, page: currentRoute() } }) });
    assistant.thread = res.thread_id;
    try { sessionStorage.setItem("ss_ask_thread", res.thread_id); } catch { /* */ }
    $("#askThinking").outerHTML = `<div class="ask-msg bot">${askMarkdown(res.answer)}${askQueries(res.queries)}</div>`;
  } catch (e) {
    $("#askThinking").outerHTML = e.body?.code === "not_configured"
      ? `<div class="ask-msg bot muted">The assistant isn't configured yet.</div>`
      : `<div class="ask-msg bot err">${esc(userMessage(e))}</div>`;
  }
  assistant.busy = false; $("#askSend").disabled = false;
  box.scrollTop = box.scrollHeight;
}
