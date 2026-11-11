// Codeonto dashboard: a small hash-routed SPA over the /api endpoints.
// Pages and KPIs come from GET /api/brands/{id}/config, so every industry renders from the same code.

const API = "/api";

const ICONS = {
  overview: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  reviews: '<path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 17.8 5.8 21l1.2-6.9-5-4.9 6.9-1z"/>',
  ai_replies: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
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
  return fetch(url, { ...opts, headers, credentials: "same-origin" });
}

async function api(path, params = {}, opts = {}) {
  const url = new URL(API + path, location.origin);
  Object.entries(params).forEach(([k, v]) => { if (v !== "" && v != null) url.searchParams.set(k, v); });
  const res = await apiFetch(url, opts);
  if (res.status === 401 && path !== "/auth/me") { showLogin(); throw new Error("Please log in"); }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(typeof body.detail === "string" ? body.detail : `${res.status} ${res.statusText}`);
    err.status = res.status; err.body = body;
    throw err;
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
const plural = (n, w) => `${inr.format(n)} ${w}${n === 1 ? "" : "s"}`;
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
const PLATFORM_ICONS = ["google", "zomato", "swiggy"];

function platformPill(code) {
  const icon = PLATFORM_ICONS.includes(code);
  const name = { google: "Google", zomato: "Zomato", swiggy: "Swiggy" }[code] || code;
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
        fill: datasets.length === 1, tension: 0.35, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2, ...d,
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
    html += `<div class="nav-group">Reputation</div>${common.map(link).join("")}` +
      (industry.length ? `<div class="nav-group">Aggregator management</div>${industry.map(link).join("")}` : "");
  } else {
    html += navLink("overview", "Overview");
  }
  html += `<div class="nav-group">Setup</div>${state.me?.outlet_limited ? "" : navLink("setup", "Brands & Outlets")}` +
    (state.me?.can_manage && state.me?.client ? navLink("team", "Team") + navLink("alert-settings", "Alerts settings") + navLink("billing", "Billing") : "") + navLink("profile", "Profile");
  if (state.me?.is_staff) html += `<div class="nav-group">Client management</div>${navLink("clients", "Clients")}${navLink("sessions", "Sessions")}`;
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
  const [config, outlets] = await Promise.all([api(`/brands/${id}/config`), api(`/brands/${id}/outlets`)]);
  state.config = config;
  state.locations = outlets.outlets.map((o) => {
    const name = o.area || o.outlet_name;
    const label = o.area && o.area.toLowerCase() !== o.outlet_name.toLowerCase() ? `${o.outlet_name} · ${o.area}` : name;
    const resId = [o.zomato && `Zomato ${o.zomato}`, o.swiggy && `Swiggy ${o.swiggy}`].filter(Boolean).join(" · ");
    return { id: o.id, name, label, city: o.city, resId, zomato: o.zomato || "", swiggy: o.swiggy || "", google: o.google || "",
             search: [name, o.outlet_name, o.city, o.zomato, o.swiggy].filter(Boolean).join(" ").toLowerCase() };
  }).sort((a, b) => a.city.localeCompare(b.city) || a.name.localeCompare(b.name));
  $("#brandIndustry").textContent = config.brand.industry_name;
  renderFilters();
  const route = currentRoute();
  if (!["setup", "clients", "profile", "team", "billing"].includes(route) && !config.modules.some((m) => m.code === route)) location.hash = "#/overview";
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

async function render() {
  if (!state.me) return;
  ensureAssistant();
  renderSidebar();
  destroyCharts();
  closePicker();
  const route = currentRoute();
  const page = $("#page");
  showPageSkeleton(page);
  document.body.classList.remove("nav-open");

  // staff-only client management, independent of the selected brand
  if (route === "sessions") {
    if (!state.me.is_staff) { location.hash = "#/overview"; return; }
    $("#filters").style.display = "none";
    try { await renderSessions(page); }
    catch (e) { page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(e.message)}</p></div>`; }
    return;
  }
  if (route === "clients") {
    if (!state.me.is_staff) { location.hash = "#/overview"; return; }
    $("#filters").style.display = "none";
    try {
      if (routeParam()) await renderClient(page, Number(routeParam()));
      else await renderClients(page);
    } catch (e) {
      page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(e.message)}</p></div>`;
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
    catch (e) { page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(e.message)}</p></div>`; }
    return;
  }
  if (route === "team") {
    const clientId = Number(routeParam()) || state.me.client?.id;
    if (!state.me.can_manage || !clientId) { location.hash = state.me.is_staff ? "#/clients" : "#/overview"; return; }
    $("#filters").style.display = "none";
    try {
      await renderTeam(page, clientId);
    } catch (e) {
      page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(e.message)}</p></div>`;
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
      page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(e.message)}</p></div>`;
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
  $("#pageTitle").textContent = isSetup ? "Brands & Outlets" : moduleName(route);
  $("#pageSub").textContent = isSetup
    ? "Name your brand and map each outlet to its Google, Zomato and Swiggy listing"
    : `${state.config.brand.name} · ${outletsLabel().replace(/ \(\d+\)$/, "")} · ${periodLabel()}`;
  const lockedModule = state.config.modules.find((m) => m.code === route && m.locked);
  if (lockedModule) return renderLocked(page, lockedModule);
  try {
    if (isSetup) await renderSetup(page, { creating: Boolean(setup.newBrandClientId) });
    else if (route === "overview") await renderOverview(page);
    else if (route === "reviews") await renderReviews(page);
    else if (route === "stock_outs") await renderStockOuts(page);
    else if (route === "tickets") await renderComplaints(page);
    else if (route === "items") await renderItems(page);
    else if (route === "store_uptime") await renderUptime(page);
    else if (route === "reconciliation") await renderReconciliation(page);
    else if (route === "marketplace_ads") await renderAds(page);
    else if (route === "alerts") await renderAlerts(page);
    else if (route === "listings") await renderListings(page);
    else if (route === "competitors") await renderCompetition(page);
    else if (state.config.kpis.some((k) => k.module === route)) await renderModule(page, route);
    else renderComingSoon(page, route);
  } catch (e) {
    page.innerHTML = `<div class="card empty-state"><h3>Couldn't load this page</h3><p>${esc(e.message)}</p></div>`;
  }
}

function sparkline(points, tone = "#d9480f") {
  const v = points.map((p) => p.value).filter((x) => x != null);
  if (v.length < 2) return "";
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1, w = 100, h = 28;
  const xy = v.map((y, i) => [(i / (v.length - 1)) * w, h - 3 - ((y - lo) / span) * (h - 6)]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><path d="${line} L${w} ${h} L0 ${h} Z" fill="${tone}" opacity=".12"/><path d="${line}" fill="none" stroke="${tone}" stroke-width="1.8" vector-effect="non-scaling-stroke"/></svg>`;
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

// ---------- overview ----------
// the overview answers one question: what needs fixing right now across ratings, reviews, offline outlets and stock-outs
async function renderOverview(page) {
  const has = (code) => state.config.modules.some((m) => m.code === code);
  const opt = (p) => p.catch(() => null);
  const [kpiRes, summary, negPending, uptime, stock, stockActive, pay, payIssues] = await Promise.all([
    api(`/brands/${state.brandId}/kpis`, filterParams()),
    api(`/brands/${state.brandId}/reviews/summary`, filterParams()),
    api(`/brands/${state.brandId}/reviews`, { outlet_id: state.locationId, platform: state.platform, rating: "neg", reply_status: "pending", limit: 3 }),
    has("store_uptime") ? opt(api(`/brands/${state.brandId}/uptime/summary`, filterParams())) : null,
    has("stock_outs") ? opt(api(`/brands/${state.brandId}/stock-outs/summary`, filterParams())) : null,
    has("stock_outs") ? opt(api(`/brands/${state.brandId}/stock-outs`, filterParams({ status: "active", limit: 500 }))) : null,
    has("reconciliation") ? opt(api(`/brands/${state.brandId}/payouts/summary`, filterParams())) : null,
    has("reconciliation") ? opt(api(`/brands/${state.brandId}/payouts/cycles`, filterParams({ status: "issues", limit: 500 }))) : null,
  ]);
  if (!kpiRes.kpis.length && !summary.total && !uptime && !stock && !pay?.cycles) return renderNoData(page);
  const payByOutlet = new Map();
  (payIssues?.results || []).forEach((c) => payByOutlet.set(c.outlet_id, (payByOutlet.get(c.outlet_id) || 0) + 1));
  const platformRating = kpiRes.kpis.find((k) => k.code === "listing_rating" && k.value != null);
  const ratingCount = kpiRes.kpis.find((k) => k.code === "rating_count" && k.value);
  const weekRating = kpiRes.kpis.find((k) => k.code === "weekly_rating" && k.value != null);
  const rating = kpiRes.kpis.find((k) => k.code === "avg_rating");
  const offline = (uptime?.outlets || []).filter((o) => o.offline_since);

  // ---- 1. four status tiles ----
  const tile = (tone, href, label, value, sub, extra = "") => `<a class="ov-tile ${tone}" href="${href}">
      <span class="ov-tile-label">${label}</span><div class="ov-tile-value">${value}${extra}</div><span class="ov-tile-sub">${sub}</span></a>`;
  const tiles = [
    platformRating
      ? tile(platformRating.change_pct <= -2 ? "amber" : "ok", "#/reviews", "Platform rating", `${fmt(platformRating.value, "rating")}<small>★</small>`,
          [ratingCount ? `${compactCount(ratingCount.value)} ratings, weighted` : "weighted by number of ratings",
           weekRating ? `<span class="${weekRating.value < platformRating.value - 0.2 ? "ov-bad" : ""}">this week ${fmt(weekRating.value, "rating")}★</span>` : "",
           summary.avg_rating != null ? `reviews ${fmt(summary.avg_rating, "rating")}★` : ""].filter(Boolean).join(" · "), changeChip(platformRating))
      : tile(rating?.change_pct <= -2 ? "amber" : "ok", "#/reviews", "Rating",
          rating?.value != null ? `${fmt(rating.value, "rating")}<small>★</small>` : summary.avg_rating != null ? `${fmt(summary.avg_rating, "rating")}<small>★</small>` : "—",
          `${inr.format(summary.total)} reviews · ${periodLabel()}`, rating ? changeChip(rating) : ""),
    tile(summary.pending ? (negPending.length ? "red" : "amber") : "ok", "#/reviews", "Reviews to reply",
      inr.format(summary.pending), summary.pending ? `${inr.format(summary.negative)} negative in this period` : "All replied"),
  ];
  if (uptime) tiles.push(tile(offline.length ? "red" : "ok", "#/store_uptime", "Outlets offline", inr.format(offline.length),
    offline.length ? "Not taking orders right now" : `All online · ${uptime.uptime_pct != null ? fmt(uptime.uptime_pct, "percent") : "—"} uptime`));
  if (stock) tiles.push(tile(stock.active ? "red" : "ok", "#/stock_outs", "Items out of stock", inr.format(stock.active),
    stock.active ? `across ${plural(stock.outlets_affected, "outlet")}` : "Full menu live"));
  const PAY_SHORT = { payout_mismatch: "don't match orders", order_count_mismatch: "order count off", unsettled_orders: "orders unsettled",
    order_payout_math: "order payout off", order_fee_math: "order fee off", fee_rate_changed: "fee % changed", paid_without_utr: "no UTR", overdue: "overdue", deductions_carried: "deductions carried over" };
  const PAY_MONEY = new Set(["payout_mismatch", "overdue", "fee_rate_changed", "order_payout_math", "order_fee_math"]);
  if (pay?.cycles) tiles.push(tile(pay.with_issues ? "red" : "ok", "#/reconciliation", "Payouts to check", inr.format(pay.with_issues),
    pay.with_issues
      ? `<span class="ov-issues">${pay.issues.slice(0, 4).map((i) => `<span class="ov-issue ${PAY_MONEY.has(i.code) ? "money" : ""}" data-payissue="${i.code}" title="Show these payouts">${inr.format(i.count)} ${PAY_SHORT[i.code] || esc(i.label)}</span>`).join("")}</span>
         <span>${pay.discrepancy_total ? `${rupees(pay.discrepancy_total)} unexplained` : "money matches orders"}</span>`
      : `All ${inr.format(pay.reconciled)} checked payouts match`));

  // ---- 2. fix these now: the five most urgent things, offline outlets first ----
  const fixes = [];
  offline.forEach((o) => fixes.push({ tone: "red", tag: "Offline", title: `${o.name} is offline`,
    sub: `${o.city ? o.city + " · " : ""}since ${timeAgo(o.offline_since).replace(" ago", "")}`, href: "#/store_uptime", cta: "Check outlet" }));
  negPending.forEach((r) => fixes.push({ tone: "red", tag: `${Math.round(r.rating)}★ review`, title: r.body ? r.body.slice(0, 90) + (r.body.length > 90 ? "…" : "") : "Rating with no text",
    sub: `${r.outlet_name} · ${timeAgo(r.reviewed_at)}`, href: "#/reviews", set: { status: "pending", rating: "neg" }, cta: "Reply" }));
  if (pay?.new_lines?.length) fixes.push({ tone: "amber", tag: "New deduction",
    title: pay.new_lines.length === 1 ? `New ${pay.new_lines[0].platform === "swiggy" ? "Swiggy" : "Zomato"} statement line: ${pay.new_lines[0].label}` : `${pay.new_lines.length} new lines on payout statements`,
    sub: `${pay.new_lines.map((l) => `${l.label} ${rupees(l.total)}`).slice(0, 3).join(" · ")}`, href: "#/reconciliation", cta: "Review" });
  (pay?.issues || []).slice(0, 2).forEach((i) => fixes.push({ tone: i.code === "payout_mismatch" || i.code === "overdue" ? "red" : "amber",
    tag: "Payout", title: `${plural(i.count, "payout")}: ${i.label.toLowerCase()}`, sub: pay.discrepancy_total ? `${rupees(pay.discrepancy_total)} unexplained in total · ${periodLabel()}` : periodLabel(),
    href: "#/reconciliation", cta: "Check" }));
  // one line per outlet (its items listed), outlets with the longest-running stock-out first
  const outByOutlet = new Map();
  (stockActive || []).forEach((s) => outByOutlet.set(s.outlet_id, [...(outByOutlet.get(s.outlet_id) || []), s]));
  [...outByOutlet.values()]
    .map((list) => list.sort((x, y) => new Date(x.first_detected_at) - new Date(y.first_detected_at)))
    .sort((a, b) => new Date(a[0].first_detected_at) - new Date(b[0].first_detected_at)).slice(0, 3)
    .forEach((list) => fixes.push({ tone: "amber", tag: "Out of stock",
      title: list.length === 1 ? list[0].item_name : `${list.length} items: ${list.slice(0, 3).map((s) => s.item_name).join(", ")}${list.length > 3 ? ` +${list.length - 3} more` : ""}`,
      sub: `${list[0].outlet_name.split(" · ").pop()} · out for ${timeAgo(list[0].first_detected_at).replace(" ago", "")}`, href: "#/stock_outs", cta: "View" }));
  if (rating?.change_pct != null && rating.change_pct <= -2) fixes.push({ tone: "amber", tag: "Rating", title: `Average rating down ${Math.abs(rating.change_pct).toFixed(1)}%`,
    sub: `vs previous ${state.days === 1 ? "day" : state.days + " days"}`, href: "#/reviews", set: { status: "", rating: "neg" }, cta: "See why" });
  const shown = fixes.slice(0, 5);

  // ---- 3. one row per outlet, worst first ----
  const rev = new Map((summary.by_outlet || []).map((o) => [o.outlet_id, o]));
  const up = new Map((uptime?.outlets || []).map((o) => [o.id, o]));
  const so = new Map((stock?.by_outlet || []).map((o) => [o.outlet_id, o]));
  const rows = platformLocations().filter((l) => !selIds().length || selIds().includes(String(l.id))).map((l) => ({
    ...l, rating: rev.get(l.id)?.avg_rating ?? null, pending: rev.get(l.id)?.pending || 0,
    offline: !!up.get(l.id)?.offline_since, uptime: up.get(l.id)?.uptime_pct ?? null, out: so.get(l.id)?.active || 0, pay: payByOutlet.get(l.id) || 0,
  })).sort((a, b) => b.offline - a.offline || b.pay - a.pay || b.out - a.out || b.pending - a.pending || (a.rating ?? 9) - (b.rating ?? 9));
  const bad = (cond, html) => `<td class="num ${cond ? "ov-bad" : ""}">${html}</td>`;

  page.innerHTML = `
    <div class="ov-tiles">${tiles.join("")}</div>
    <div class="ov-two">
    <div class="card ov-fix">
      <div class="card-head"><h3>Fix these now</h3><span class="muted">${fixes.length > 5 ? `top 5 of ${fixes.length}` : ""}</span></div>
      ${shown.length ? shown.map((f, i) => `<a class="ov-fix-row ${f.tone}" href="${f.href}" data-fix="${i}">
          <span class="ov-fix-tag">${esc(f.tag)}</span>
          <span class="ov-fix-text"><strong>${esc(f.title)}</strong><small>${esc(f.sub)}</small></span>
          <span class="btn light">${f.cta}</span></a>`).join("")
        : `<div class="ov-fix-row ok"><span class="ov-fix-tag">✓</span><span class="ov-fix-text"><strong>All clear</strong><small>Nothing needs fixing right now</small></span></div>`}
    </div>
    ${pay?.cycles ? `<div class="card ov-pay-card">
      <div class="card-head"><h3>Payouts</h3><a class="muted" href="#/reconciliation">Open reconciliation →</a></div>
      <div class="ov-pay">
        <div><span class="ov-tile-label">Paid</span><b>${rupees(pay.paid_total)}</b><small class="muted">${periodLabel()}</small></div>
        <div><span class="ov-tile-label">To be paid</span><b>${rupees(pay.to_be_paid_total)}</b><small class="muted">${plural(pay.to_be_paid_cycles, "payout")}</small></div>
        <div><span class="ov-tile-label">Unexplained difference</span><b class="${pay.discrepancy_total ? "ov-bad" : ""}">${rupees(pay.discrepancy_total)}</b><small class="muted">${inr.format(pay.reconciled)} of ${inr.format(pay.cycles)} checked against orders</small></div>
        <div><span class="ov-tile-label">Commission take rate</span><b>${pay.take_rate == null ? "—" : `${pay.take_rate.toFixed(2)}%`}</b><small class="muted">service fee on checked orders</small></div>
      </div>
      ${pay.issues.length ? `<ul class="payout-issues">${pay.issues.slice(0, 4).map((i) => `<li><a href="#/reconciliation" data-payissue="${i.code}"><b>${inr.format(i.count)}</b> ${esc(i.label)} <span class="muted">show</span></a></li>`).join("")}</ul>` : ""}
    </div>` : ""}
    </div>
    <div class="card" style="margin-top:12px">
      <div class="card-head"><h3>Outlets at a glance</h3><span class="muted">worst first · click to focus</span></div>
      <div class="cp-scroll"><table class="ov-table"><thead><tr><th>Outlet</th><th class="num">Rating</th><th class="num">To reply</th>
        ${uptime ? '<th class="num">Status</th>' : ""}${stock ? '<th class="num">Items out</th>' : ""}${pay?.cycles ? '<th class="num">Payouts to check</th>' : ""}</tr></thead><tbody>
        ${rows.map((r) => `<tr class="cp-click" data-outlet="${r.id}">
          <td><strong>${esc(r.name)}</strong><small class="muted">${esc(r.city || "")}</small></td>
          ${bad(r.rating != null && r.rating < 3.5, r.rating != null ? `${fmt(r.rating, "rating")} ★` : '<span class="muted">—</span>')}
          ${bad(r.pending > 0, r.pending || '<span class="muted">0</span>')}
          ${uptime ? bad(r.offline, r.offline ? "Offline" : r.uptime != null ? `<span class="muted">${fmt(r.uptime, "percent")}</span>` : '<span class="muted">—</span>') : ""}
          ${stock ? bad(r.out > 0, r.out || '<span class="muted">0</span>') : ""}
          ${pay?.cycles ? bad(r.pay > 0, r.pay || '<span class="muted">0</span>') : ""}</tr>`).join("")}
      </tbody></table></div>
    </div>`;

  page.querySelectorAll("[data-payissue]").forEach((el) => el.addEventListener("click", (e) => {
    e.preventDefault(); e.stopPropagation();
    Object.assign(payoutFilters, { issue: el.dataset.payissue, status: "", q: "" });
    location.hash = "#/reconciliation";
  }));
  page.querySelectorAll("[data-fix]").forEach((a) => a.addEventListener("click", () => {
    const set = shown[Number(a.dataset.fix)].set;
    if (set) Object.assign(reviewFilters, set);
  }));
  page.querySelectorAll("[data-outlet]").forEach((r) => r.addEventListener("click", () => {
    state.locationId = r.dataset.outlet; showSelectedOutlet(); render();
  }));
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

  const [kpiRes, trend, board, ...perPlatform] = await Promise.all([
    api(`/brands/${state.brandId}/kpis`, filterParams({ module })),
    api(`/brands/${state.brandId}/kpis/${meta.code}/trend`, filterParams()),
    api(`/brands/${state.brandId}/leaderboard/${meta.code}`, range()),
    ...platforms.map((p) => api(`/brands/${state.brandId}/kpis/${meta.code}/trend`, filterParams({ platform: p.code }))),
  ]);
  if (!kpiRes.kpis.length) return renderNoData(page);
  const platformSeries = platforms
    .map((p, i) => ({ platform: p, points: perPlatform[i] }))
    .filter((s) => s.points.length);

  const funnel = module === "marketplace_funnel" ? funnelCard(kpiRes.kpis) : "";
  page.innerHTML = `
    ${kpiCards(kpiRes.kpis, module)}
    ${funnel}
    <div class="card">
      <div class="card-head">
        <h3>${esc(meta.name)} trend</h3>
        <div class="tabs">${modKpis.map((k) => `<button class="tab ${k.code === meta.code ? "active" : ""}" data-kpi="${k.code}">${esc(k.name)}</button>`).join("")}</div>
      </div>
      <div class="chart-box"><canvas id="cTrend"></canvas></div>
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
  lineChart($("#cTrend"), labels, datasets, meta.unit);

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

// ---------- reviews inbox ----------
const reviewFilters = { rating: "", status: "", q: "", contact: "", offset: 0 };

let reviewRows = new Map();
const RATING_BAND = { 1: "neg", 2: "neg", 3: "mid", 4: "pos", 5: "pos" };
const REPLY_LABELS = { pending: "Pending", drafted: "Drafted", replied: "Replied", ignored: "Ignored" };

async function renderReviews(page) {
  const s = await api(`/brands/${state.brandId}/reviews/summary`, filterParams());
  const names = new Map(state.locations.map((l) => [l.id, l.name]));
  const short = (n) => n.split(" · ").slice(1).join(" · ") || n;
  const pct = (n, of = s.total) => (of ? `${Math.round((n / of) * 100)}%` : "—");
  const meter = (n, max) => `<span class="cp-meter"><i style="width:${(n / Math.max(1, max)) * 100}%"></i></span>`;
  const stat = (label, value, tone = "") => `<div class="cp-stat ${tone}"><span>${label}</span><b>${value}</b></div>`;
  const avg = (v) => (v == null ? "—" : `<span class="rv-avg ${v < 3.5 ? "cp-bad" : v < 4 ? "cp-warn" : ""}">${v.toFixed(2)} ★</span>`);
  const maxStar = Math.max(1, ...s.by_rating.map((r) => r.count));
  const maxPlat = Math.max(1, ...s.by_platform.map((r) => r.count));
  const maxNeg = Math.max(1, ...s.by_outlet.map((r) => r.negative));
  page.innerHTML = `
    <div class="card cp-stats">
      ${stat("Reviews", inr.format(s.total))}${stat("Avg rating", s.avg_rating != null ? `${s.avg_rating} ★` : "—")}
      ${stat("Negative (1–2★)", inr.format(s.negative), s.negative ? "bad" : "")}${stat("Pending", inr.format(s.pending), s.pending ? "warn" : "")}
      ${stat("Replied", inr.format(s.replied), "ok")}${stat("Response rate", pct(s.replied))}
    </div>
    ${s.total ? `<div class="cp-grid rv-grid">
      <div class="card cp-card"><div class="cp-head"><h3>By rating</h3><span class="muted">click to filter</span></div>
        <table class="cp-table"><thead><tr><th>Stars</th><th class="num">#</th><th class="num">Share</th><th></th></tr></thead><tbody>
        ${s.by_rating.map((r) => `<tr class="cp-click ${reviewFilters.rating === RATING_BAND[r.stars] ? "on" : ""}" data-band="${RATING_BAND[r.stars] || ""}">
          <td>${stars(r.stars)}</td><td class="num"><b>${inr.format(r.count)}</b></td><td class="num muted">${pct(r.count)}</td>
          <td class="cp-mcell">${meter(r.count, maxStar)}</td></tr>`).join("")}
        </tbody></table></div>
      <div class="card cp-card"><div class="cp-head"><h3>By platform</h3></div>
        <table class="cp-table"><thead><tr><th>Platform</th><th class="num">#</th><th class="num">Avg</th><th></th></tr></thead><tbody>
        ${s.by_platform.map((r) => `<tr><td>${platformPill(r.platform)}</td><td class="num"><b>${inr.format(r.count)}</b></td>
          <td class="num">${avg(r.avg_rating)}</td><td class="cp-mcell">${meter(r.count, maxPlat)}</td></tr>`).join("")}
        </tbody></table></div>
      <div class="card cp-card rv-wide"><div class="cp-head"><h3>By outlet</h3><span class="muted">most negative first · click to filter</span></div>
        <div class="cp-scroll"><table class="cp-table"><thead><tr><th>Outlet</th><th class="num">#</th><th class="num">Avg</th>
          <th class="num">1–2★</th><th></th><th class="num">Pending</th></tr></thead><tbody>
        ${s.by_outlet.map((r) => `<tr class="cp-click" data-outlet="${r.outlet_id}">
          <td class="cp-ellip" title="${esc(names.get(r.outlet_id) || "")}">${esc(short(names.get(r.outlet_id) || `Outlet ${r.outlet_id}`))}</td>
          <td class="num">${inr.format(r.count)}</td><td class="num">${avg(r.avg_rating)}</td>
          <td class="num ${r.negative ? "cp-bad" : "muted"}">${inr.format(r.negative)}</td><td class="cp-mcell">${meter(r.negative, maxNeg)}</td>
          <td class="num ${r.pending ? "cp-warn" : "muted"}">${inr.format(r.pending)}</td></tr>`).join("")}
        </tbody></table></div></div>
    </div>` : ""}
    <div class="card cp-card">
      <div class="toolbar cp-toolbar">
        <input id="rq" type="search" placeholder="Search review text…" value="${esc(reviewFilters.q)}">
        <select id="rRating"><option value="">All ratings</option><option value="neg">1–2 ★</option><option value="mid">3 ★</option><option value="pos">4–5 ★</option></select>
        <select id="rStatus"><option value="">Any status</option>${Object.entries(REPLY_LABELS).map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>
        <label class="check nowrap" title="Customers who chose on Zomato to share their number with the restaurant"><input type="checkbox" id="rContact" ${reviewFilters.contact ? "checked" : ""}> Number shared</label>
        <span class="muted" style="margin-left:auto">click a row to read it and reply</span>
      </div>
      <div class="table-wrap"><table class="cp-table cp-list"><thead><tr>
        <th>When</th><th>Outlet</th><th></th><th>Rating</th><th>Review</th><th>Customer</th><th>Reply</th></tr></thead>
        <tbody id="reviewList"></tbody></table></div>
      <div style="text-align:center;margin-top:8px"><button class="btn light" id="moreBtn">Load more</button></div>
    </div>`;
  $("#rRating").value = reviewFilters.rating;
  $("#rStatus").value = reviewFilters.status;
  let timer;
  $("#rq").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { reviewFilters.q = e.target.value; loadReviews(true); }, 300); });
  $("#rRating").addEventListener("change", (e) => { reviewFilters.rating = e.target.value; render(); });
  $("#rStatus").addEventListener("change", (e) => { reviewFilters.status = e.target.value; loadReviews(true); });
  $("#rContact").addEventListener("change", (e) => { reviewFilters.contact = e.target.checked ? "shared" : ""; loadReviews(true); });
  page.querySelectorAll("[data-band]").forEach((r) => r.addEventListener("click", () => {
    reviewFilters.rating = reviewFilters.rating === r.dataset.band ? "" : r.dataset.band; render();
  }));
  page.querySelectorAll("[data-outlet]").forEach((r) => r.addEventListener("click", () => {
    state.locationId = r.dataset.outlet; showSelectedOutlet(); render();
  }));
  $("#moreBtn").addEventListener("click", () => loadReviews(false));
  bindReviewTable($("#reviewList"));
  await loadReviews(true);
}

async function loadReviews(reset) {
  if (reset) { reviewFilters.offset = 0; reviewRows = new Map(); }
  const rows = await api(`/brands/${state.brandId}/reviews`, {
    outlet_id: state.locationId, platform: state.platform, reply_status: reviewFilters.status, q: reviewFilters.q,
    rating: reviewFilters.rating, contact: reviewFilters.contact, limit: 50, offset: reviewFilters.offset,
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

function reviewDetail(r) {
  const canReply = r.reply_status !== "replied" && state.me?.can_edit !== false;
  return `<tr class="cp-detail" data-detail="${r.id}"><td colspan="7">
    <div class="review-body ${r.body ? "" : "empty"}">${r.body ? esc(r.body) : "Rating only, no text"}</div>
    ${r.latest_reply ? `<div class="latest-reply" style="margin-top:8px">${esc(r.latest_reply)}</div>` : ""}
    ${r.contact ? contactBox(r) : ""}
    ${canReply ? `<div class="reply-box" style="margin-top:8px"><textarea rows="1" placeholder="Write a reply…"></textarea>
      <button class="btn blue" data-reply>Save draft</button></div>` : ""}</td></tr>`;
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
  } catch (err) { toast(err.message); view.disabled = false; }
  return true;
}

function bindReviewTable(list) {
  list.addEventListener("click", async (e) => {
    if (await contactClick(e)) return;
    const btn = e.target.closest("[data-reply]");
    if (btn) {
      const detail = btn.closest(".cp-detail");
      const body = detail.querySelector("textarea").value.trim();
      if (!body) return toast("Write a reply first");
      btn.disabled = true;
      try {
        await apiJSON(`/reviews/${detail.dataset.detail}/replies`, "POST", { body });
        const r = { ...reviewRows.get(detail.dataset.detail), latest_reply: body };
        if (r.reply_status === "pending") r.reply_status = "drafted";
        reviewRows.set(String(r.id), r);
        list.querySelector(`.cp-row[data-id="${r.id}"]`).outerHTML = reviewTableRow(r);
        detail.outerHTML = reviewDetail(r);
        toast("Draft saved");
      } catch (err) { toast(err.message); btn.disabled = false; }
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
    } catch (e) { toast(e.message); }
    btn.disabled = false;
  }));
}

// ---------- complaints: order complaints from Zomato / Swiggy, tracked as tickets ----------
const complaintFilters = { status: "", issue: "", q: "", offset: 0 };
const ISSUE_LABELS = { missing_items: "Missing items", wrong_items: "Wrong items", quality: "Quality", quantity: "Quantity",
  packaging: "Packaging / spillage", other: "Other" };
const TICKET_STATUS = [["open", "Open"], ["in_progress", "In progress"], ["resolved", "Resolved"]];
let complaintRows = new Map();

async function renderComplaints(page) {
  const s = await api(`/brands/${state.brandId}/complaints/summary`, filterParams());
  const names = new Map(state.locations.map((l) => [l.id, l.name]));
  const short = (n) => n.split(" · ").slice(1).join(" · ") || n;
  const pct = (n) => (s.total ? `${Math.round((n / s.total) * 100)}%` : "—");
  const maxIssue = Math.max(1, ...s.by_issue.map((r) => r.count));
  const maxOutlet = Math.max(1, ...s.by_outlet.map((r) => r.count));
  const meter = (n, max) => `<span class="cp-meter"><i style="width:${(n / max) * 100}%"></i></span>`;
  const stat = (label, value, tone = "") => `<div class="cp-stat ${tone}"><span>${label}</span><b>${value}</b></div>`;
  page.innerHTML = `
    <div class="card cp-stats">
      ${stat("Complaints", inr.format(s.total))}${stat("Open", inr.format(s.open), s.open ? "warn" : "")}
      ${stat("In progress", inr.format(s.in_progress))}${stat("Resolved", inr.format(s.resolved), "ok")}
      ${stat("Refunds", rupees(s.refunds))}${stat("Avg / complaint", s.total ? rupees(s.refunds / s.total) : "—")}
      ${stat("Expiring ≤6h", inr.format(s.expiring), s.expiring ? "bad" : "")}
    </div>
    ${s.total ? `<div class="cp-grid">
      <div class="card cp-card"><div class="cp-head"><h3>By issue</h3><span class="muted">click to filter</span></div>
        <table class="cp-table"><thead><tr><th>Issue</th><th class="num">#</th><th class="num">Share</th><th></th><th class="num">Refunds</th></tr></thead><tbody>
        ${s.by_issue.map((r) => `<tr class="cp-click ${complaintFilters.issue === r.issue_type ? "on" : ""}" data-issue="${esc(r.issue_type)}">
          <td>${esc(ISSUE_LABELS[r.issue_type] || r.issue_type)}</td><td class="num"><b>${inr.format(r.count)}</b></td>
          <td class="num muted">${pct(r.count)}</td><td class="cp-mcell">${meter(r.count, maxIssue)}</td><td class="num">${rupees(r.refunds)}</td></tr>`).join("")}
        </tbody></table></div>
      <div class="card cp-card"><div class="cp-head"><h3>By outlet</h3><span class="muted">top ${s.by_outlet.length} · click to filter</span></div>
        <div class="cp-scroll"><table class="cp-table"><thead><tr><th>Outlet</th><th class="num">#</th><th class="num">Open</th><th></th><th class="num">Refunds</th></tr></thead><tbody>
        ${s.by_outlet.map((r) => `<tr class="cp-click" data-outlet="${r.outlet_id}">
          <td title="${esc(names.get(r.outlet_id) || "")}">${esc(short(names.get(r.outlet_id) || `Outlet ${r.outlet_id}`))}</td>
          <td class="num"><b>${inr.format(r.count)}</b></td><td class="num ${r.open ? "cp-warn" : "muted"}">${inr.format(r.open)}</td>
          <td class="cp-mcell">${meter(r.count, maxOutlet)}</td><td class="num">${rupees(r.refunds)}</td></tr>`).join("")}
        </tbody></table></div></div>
    </div>` : ""}
    <div class="card cp-card">
      <div class="toolbar cp-toolbar">
        <input id="cq" type="search" placeholder="Search order id, item, customer…" value="${esc(complaintFilters.q)}">
        <select id="cStatus"><option value="">Any status</option>${TICKET_STATUS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>
        ${complaintFilters.issue ? `<button class="btn light" id="cClear">${esc(ISSUE_LABELS[complaintFilters.issue] || complaintFilters.issue)} ✕</button>` : ""}
        <span class="muted" style="margin-left:auto">click a row for details and notes</span>
      </div>
      <div class="table-wrap"><table class="cp-table cp-list"><thead><tr>
        <th>Raised</th><th>Outlet</th><th></th><th>Issue</th><th>Items</th><th>Customer</th><th class="num">Refund</th>
        <th>Platform</th><th>Window</th><th>Ticket</th></tr></thead><tbody id="complaintList"></tbody></table></div>
      <div style="text-align:center;margin-top:8px"><button class="btn light" id="cMore">Load more</button></div>
    </div>`;
  $("#cStatus").value = complaintFilters.status;
  let timer;
  $("#cq").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { complaintFilters.q = e.target.value; loadComplaints(true); }, 300); });
  $("#cStatus").addEventListener("change", (e) => { complaintFilters.status = e.target.value; loadComplaints(true); });
  $("#cClear")?.addEventListener("click", () => { complaintFilters.issue = ""; render(); });
  page.querySelectorAll("[data-issue]").forEach((r) => r.addEventListener("click", () => {
    complaintFilters.issue = complaintFilters.issue === r.dataset.issue ? "" : r.dataset.issue; render();
  }));
  page.querySelectorAll("[data-outlet]").forEach((r) => r.addEventListener("click", () => {
    state.locationId = r.dataset.outlet; showSelectedOutlet(); render();
  }));
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
    } catch (e) { toast(e.message); }
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
  ...(SHOW_STOCK_LOSS ? [["stockout_loss", "Stock-out ₹", "num"]] : []), ["avg_item_rating", "Item ★", "num"], ["money_lost", "₹ lost", "num"],
];

async function renderItems(page) {
  itemData = await api(`/brands/${state.brandId}/items`, filterParams());
  const t = itemData.totals;
  const stat = (label, value, tone = "") => `<div class="cp-stat ${tone}"><span>${label}</span><b>${value}</b></div>`;
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
        <span class="muted" style="margin-left:auto">₹ lost = ${SHOW_STOCK_LOSS ? "refunds + sales missed on stock-outs" : "refunds"} · click a row for details</span>
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
      ${SHOW_STOCK_LOSS ? `<td class="num">${r.stockout_loss ? rupees(r.stockout_loss) : dash}</td>` : ""}
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
    } catch (err) { toast(err.message); e.target.disabled = false; }
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
    } catch (err) { toast(err.message); }
  });
}

// ---------- payout reconciliation ----------
const payoutFilters = { status: "", q: "", open: null, issue: "", view: "list" };
const stmtSel = new Map();  // statement view: "outletId:platform" -> Set of unticked cycle ids
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

async function renderReconciliation(page) {
  const listParams = filterParams({ status: payoutFilters.status, q: payoutFilters.q, issue: payoutFilters.issue });
  const [summary, cycles, combined] = await Promise.all([
    api(`/brands/${state.brandId}/payouts/summary`, filterParams()),
    api(`/brands/${state.brandId}/payouts/cycles`, { ...listParams, limit: 200 }),
    api(`/brands/${state.brandId}/payouts/combined`, listParams).catch(() => null),
  ]);
  const statements = payoutFilters.view === "statements" ? await api(`/brands/${state.brandId}/payouts/statements`, listParams) : null;
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
    ${summary.new_lines?.length ? `<div class="card new-lines" style="margin-bottom:20px"><div class="card-head"><h3>New statement lines</h3>
        <span class="muted">${state.me.is_staff ? "say what each one is, once" : "Codeonto is reviewing these"}</span></div>
      <p class="muted" style="margin-top:0">These appeared on Zomato or Swiggy payout statements for the first time. Until reviewed they count as deductions not tied to orders, and aren't counted as ad spend.</p>
      <table class="ov-table"><thead><tr><th>Platform</th><th>Line</th><th class="num">Payouts</th><th class="num">Total</th><th>Last seen</th><th></th></tr></thead><tbody>
      ${summary.new_lines.map((l) => `<tr><td>${l.platform === "swiggy" ? "Swiggy" : "Zomato"}</td><td><b>${esc(l.label)}</b><br><span class="muted">${esc(l.section)}</span></td>
        <td class="num">${inr.format(l.payouts)}</td><td class="num">${rupees(l.total)}</td><td class="muted">${shortDate(l.last_seen)}</td>
        <td>${state.me.is_staff ? `<span class="btn-row">${[["order", "Order charge"], ["ad", "Ad spend"], ["deduction", "Other deduction"]].map(([k, t]) =>
          `<button class="btn ${l.guess === k ? "blue" : "light"}" data-line="${l.id}" data-kind="${k}">${t}</button>`).join("")}</span>` : ""}</td></tr>`).join("")}
      </tbody></table></div>` : ""}
    ${summary.issues.length ? `<div class="card" style="margin-bottom:20px"><div class="card-head"><h3>What needs checking</h3></div>
      <ul class="payout-issues">${summary.issues.map((i) => `<li><button class="payout-issue-btn ${payoutFilters.issue === i.code ? "on" : ""}" data-payout-issue="${i.code}">
        <b>${inr.format(i.count)}</b> ${esc(i.label)}<span class="muted">${payoutFilters.issue === i.code ? "showing · clear" : "show"}</span></button></li>`).join("")}</ul></div>` : ""}
    ${combined?.platforms.length ? `<div class="card payout-combined" style="margin-bottom:20px">
      <div class="card-head"><h3>Combined statement <a class="btn light" style="margin-left:10px" href="${combinedXlsx}" download>Export Excel</a></h3>
        <span class="muted">${plural(combined.total.payouts, "payout")} matching these filters · ${inr.format(combined.total.orders)} orders · net ${rupees(combined.total.net_payout)}
          (paid ${rupees(combined.total.paid)} · to be paid ${rupees(combined.total.to_be_paid)})</span></div>
      <div class="payout-combined-grid">${combined.platforms.map((p) => `<div>
        <h4>${p.platform === "swiggy" ? "Swiggy" : "Zomato"} <span class="muted">· ${plural(p.payouts, "payout")} · ${plural(p.outlets, "outlet")} · ${inr.format(p.orders)} orders</span></h4>
        <table class="payout-statement"><tbody>${p.sections.map((sec) => `<tr class="section"><td>${esc(sec.label)}</td><td>${rupees(sec.value)}</td></tr>
          ${sec.items.map((i) => `<tr><td class="muted">${esc(i.label)}</td><td class="muted">${rupees(i.value)}</td></tr>`).join("")}`).join("")}
          <tr class="section total"><td>Net payout</td><td>${rupees(p.net_payout)}</td></tr></tbody></table></div>`).join("")}</div>
      <p class="muted" style="margin:8px 0 0">Adds up every payout matching the filters (dates, outlets, platform, status, search), the same ones the list and the CSV use. Zomato and Swiggy statements are laid out differently, so each is combined on its own.</p>
    </div>` : ""}
    <div class="card so-list">
      <div class="toolbar">
        <label class="payout-date">From <input id="payoutFrom" type="date" value="${range().start}" max="${isoDate(new Date())}"></label>
        <label class="payout-date">To <input id="payoutTo" type="date" value="${range().end}" max="${isoDate(new Date())}"></label>
        <input id="payoutSearch" type="search" placeholder="Search outlet or UTR…" value="${esc(payoutFilters.q)}">
        <div class="segmented" id="payoutView">${[["list", "List"], ["statements", "Statement view"]].map(([v, l]) => `<button data-view="${v}" class="${payoutFilters.view === v ? "active" : ""}">${l}</button>`).join("")}</div>
        ${payoutFilters.view === "statements" ? '<button class="btn blue" id="exportBook">Export Book</button>' : `<a class="btn light" href="${exportUrl}" download>Export CSV</a>`}
        ${payoutFilters.issue ? `<button class="btn light" id="payoutIssueClear">${esc((summary.issues.find((i) => i.code === payoutFilters.issue) || {}).label || payoutFilters.issue)} ✕</button>` : ""}
        <div class="segmented" id="payoutStatus">${[["", "All"], ["issues", "To check"], ["paid", "Paid"], ["to_be_paid", "To be paid"]]
          .map(([v, l]) => `<button data-v="${v}" class="${payoutFilters.status === v ? "active" : ""}">${l}</button>`).join("")}</div>
      </div>
      ${statements ? renderStatementBlocks(statements.groups) : cycles.results.length ? `<div class="table-wrap payout-table"><table>
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
    catch (e) { toast(e.message); b.disabled = false; }
  }));
  page.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => { payoutFilters.view = b.dataset.view; renderReconciliation(page); }));
  if (statements) wireStatementBlocks(page, statements.groups);
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
      catch (x) { err.textContent = x.message; e.target.disabled = false; }
    });
    el.querySelector("[data-test]")?.addEventListener("click", async (e) => {
      e.target.disabled = true;
      try { await apiJSON(`${base}/${id}/test`, "POST", {}); toast("Test queued: the collector sends it on its next check, within about 5 minutes."); }
      catch (x) { err.textContent = x.message; }
      e.target.disabled = false;
    });
    el.querySelector("[data-del]")?.addEventListener("click", async () => {
      if (!confirm("Remove this recipient? They stop getting alerts.")) return;
      try { await api(`${base}/${id}`, {}, { method: "DELETE" }); toast("Removed"); renderAlertSettings(page, clientId); } catch (x) { err.textContent = x.message; }
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

let sessionsPoll = null;
async function renderSessions(page) {
  clearTimeout(sessionsPoll);
  const d = await api("/staff/sessions");
  const when = (x) => (x ? `${timeAgo(x.updated_at)}<br><span class="muted">${esc(x.updated_by || "")}</span>` : '<span class="muted">not in database</span>');
  const btn = (platform, kind, id, label) => `<button class="btn light" data-sess="${platform}|${kind}|${id ?? ""}|${esc(label)}">Paste session</button>`;
  page.innerHTML = `<div class="page-head"><h2>Platform sessions</h2><p class="muted">Zomato and Swiggy logins, stored encrypted in the database. The Windows collector and this site read them from here, so a refresh here reaches every machine on its next run.</p></div>
    <div class="card"><div class="card-head"><h3>Collector accounts</h3></div>
      <div class="table-wrap"><table class="ov-table"><thead><tr><th>Account</th><th>Client</th><th>Status</th><th>Merchant dashboard</th><th>Automatic login</th><th></th><th>Merchant app (ratings)</th><th></th></tr></thead><tbody>
      ${d.accounts.map((a) => `<tr class="${a.is_active ? "" : "muted"}"><td><b>${a.platform === "swiggy" ? "Swiggy" : "Zomato"} · ${esc(a.label)}</b>${a.is_active ? "" : " (inactive)"}</td>
        <td>${esc(a.client)}</td><td>${sessionHealth(a)}<div class="sess-note">reads from ${esc(a.reads_from)}</div></td>
        <td>${when(a.merchant)}</td><td class="sess-login">${loginButton(a)}</td><td>${btn(a.platform, "merchant", a.id, `${a.platform} · ${a.label}`)}</td>
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
      toast(err.status === 409 ? "Someone already started a refresh for this login" : `Couldn't start: ${err.message}`);
    }
    renderSessions(page);
    checkSessionAlerts();
  }));
  // while a login is queued or running, keep the page current so everyone sees the same state
  if (d.accounts.some((a) => a.refresh && ["queued", "running"].includes(a.refresh.status))) {
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
      } catch (err) { m.querySelector("#sessErr").textContent = err.message; e.target.disabled = false; }
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
    row.innerHTML = `<td colspan="8" class="muted">${esc(e.message)}</td>`;
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
  const ORDER_SECTIONS = ["total_order_value", "total_customer_paid", "total_fees", "total_taxes", "order_level_deductions", "tax_deductions", "additions", "complaint_cancellation_charges"];
  const bigLines = d.breakdown.filter((sec) => !ORDER_SECTIONS.includes(sec.id)).flatMap((sec) => sec.items.filter((i) => i.value < 0).map((i) => ({ ...i, section: sec.label })))
    .sort((a, b) => a.value - b.value).slice(0, 3);
  const nGap = d.orders.filter((o) => reasons(o).some((x) => x.gap)).length;
  const nFlag = d.orders.filter(flagged).length;
  const explain = carried ? `The orders match the statement. ${d.platform === "swiggy" ? "Swiggy" : "Zomato"} paid ₹0 because deductions not tied to orders (${bigLines.map((l) => `${l.label} ${rupees(l.value)}`).join(", ") || "see the statement"}) were bigger than what the orders earned; ${rupees(-(d.expected_payout || 0))} carries into the next payout`
    : gap && !nGap && bigLines.length ? `No single order explains it. Biggest deductions not tied to orders: ${bigLines.map((l) => `${l.label} ${rupees(l.value)}`).join(", ")}`
    : gap ? (nGap ? `${plural(nGap, "order")} ${nGap === 1 ? "has" : "have"} a payout equal to the gap, so ${nGap === 1 ? "it was" : "they were"} likely left out of the payout`
      : nFlag ? `${plural(nFlag, "order")} flagged below may explain it` : "No single order explains it: likely a deduction or adjustment the order report doesn't show")
    : nFlag ? `${plural(nFlag, "order")} flagged` : "";
  row.innerHTML = `<td colspan="8">
    ${d.issues.length ? `<ul class="payout-issues warn">${d.issues.map((i) => `<li>${esc(label(i))}</li>`).join("")}</ul>` : ""}
    <div class="payout-columns">
      <div>
        <h4>${d.platform === "swiggy" ? "Swiggy" : "Zomato"}'s statement</h4>
        ${d.breakdown.length ? `<table class="payout-statement"><tbody>${d.breakdown.map((s) => `<tr class="section"><td>${esc(s.label)}</td><td>${rupees(s.value)}</td></tr>
          ${s.items.filter((i) => i.value).map((i) => `<tr class="${(carried || gap) && bigLines.some((l) => l.label === i.label && l.value === i.value) ? "payout-culprit" : ""}"><td class="muted">${esc(i.label)}</td><td class="muted">${rupees(i.value)}</td></tr>`).join("")}`).join("")}
          <tr class="section total"><td>Net payout</td><td>${rupees(d.net_payout)}</td></tr></tbody></table>` : '<p class="muted">No statement available.</p>'}
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
      <thead><tr><th>Order ID</th><th>Date</th><th>Status</th><th>Order value</th><th>Fee %</th><th>Fees</th><th>Taxes</th><th>Other</th><th>Payout</th><th>Settlement</th><th>Why flagged</th></tr></thead>
      <tbody>${orders.map((o) => `<tr class="${flagged(o) ? (reasons(o).some((x) => x.gap) ? "flagged gap" : "flagged") : ""}">
        <td>${esc(o.order_id)}</td>
        <td class="muted">${o.order_date ? new Date(o.order_date).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "—"}</td>
        <td>${esc(o.status)}</td><td>${rupees(o.net_order_value)}</td><td>${o.base_fee_pct}%${o.service_fee_pct !== o.base_fee_pct ? ` <span class="muted">+${(o.service_fee_pct - o.base_fee_pct).toFixed(1)}% distance</span>` : ""}</td><td>${rupees(o.fees_total)}</td>
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

function showOfflineNotice({ title, detail, when = "", open, online = false }) {
  const el = document.createElement("div");
  el.className = `offline-notice ${online ? "online" : ""}`;
  el.innerHTML = `<i class="offline-dot"></i>
    <div class="offline-text"><b>${esc(title)}</b><span>${esc(detail)}</span>${when ? `<small class="muted">${esc(when)}</small>` : ""}
      <button class="offline-view" type="button">View</button></div>
    <button class="offline-close" type="button" aria-label="Dismiss">×</button>`;
  let timer;
  const close = () => { clearTimeout(timer); el.remove(); };
  const arm = () => { clearTimeout(timer); timer = setTimeout(close, OFFLINE_NOTICE_MS); };
  el.querySelector(".offline-close").addEventListener("click", close);
  el.querySelector(".offline-view").addEventListener("click", () => { close(); open(); });
  el.addEventListener("mouseenter", () => clearTimeout(timer));  // stays while being read
  el.addEventListener("mouseleave", arm);
  offlineStack().prepend(el);
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

const noticeTime = (ts) => new Date(ts).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
const manyOutlets = (n) => `${n} outlet${n === 1 ? "" : "s"}`;

function showChanges(fresh, one, summary, online) {
  if (fresh.length > OFFLINE_MAX_NOTICES) {
    showOfflineNotice({ title: summary, detail: "Open Store Uptime to see which", open: () => openOfflineOutlet(), online });
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

  const offline = unseenChanges("offline", changes.offline);
  if (offline.firstVisit) {  // first visit on this browser: these aren't news, so one summary instead of a popup each
    if (changes.offline.length) showOfflineNotice({ title: `${manyOutlets(changes.offline.length)} offline right now`, detail: "Open Store Uptime to see which", open: () => openOfflineOutlet() });
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
async function renderUptime(page) {
  const params = () => filterParams({ limit: 500, status: uptimeFilters.status, outlet_id: uptimeFilters.outlet || state.locationId });
  const [summary, episodes] = await Promise.all([
    api(`/brands/${state.brandId}/uptime/summary`, filterParams()),
    api(`/brands/${state.brandId}/uptime/episodes`, params()),
  ]);
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
  const dayList = [...new Set(summary.outlets.flatMap((o) => Object.keys(o.days || {})))].sort();
  const upColor = (v) => (v == null ? "#e6e9ef" : v >= 95 ? "#12a150" : v >= 85 ? "#7ccf8e" : v >= 70 ? "#f5a524" : "#e5484d");
  page.innerHTML = `
    <div class="so-hero">
      <div><span class="so-live"><i></i> Live</span>
        <div class="so-big">${inr.format(summary.offline_now)}<small> outlet${summary.offline_now === 1 ? "" : "s"} offline right now</small></div>
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

    <div class="so-section"><h3>Outlets <small>${dayList.length > 1 ? "daily uptime, one square per day" : "uptime in this period"}, worst first · ${uptimeAll ? `all ${shown.length}` : `worst ${Math.min(UP_TOP, shown.length)} of ${shown.length}`}${uptimeCity ? ` in ${esc(uptimeCity)}` : ""} · click to filter</small></h3>
      <div class="up-heat">${(uptimeAll ? shown : shown.slice(0, UP_TOP)).map((o) => `
        <button class="up-row ${String(uptimeFilters.outlet) === String(o.id) ? "on" : ""}" data-outlet="${o.id}" title="${esc(o.name)}">
          <span class="up-name">${esc(o.name)} <small class="muted">${esc(o.city || "")}</small>${o.offline_since ? ' <em class="uptime-off">offline</em>' : ""}</span>
          ${dayList.length > 1 ? `<span class="up-cells">${dayList.map((d) => { const v = o.days[d]; return `<i style="background:${upColor(v)}" title="${shortDate(d)}: ${v == null ? "no checks" : `${v.toFixed(1)}%`}"></i>`; }).join("")}</span>` : ""}
          <b class="${o.offline_since ? "bad" : "ok"}">${o.uptime_pct == null ? "—" : `${o.uptime_pct.toFixed(1)}%`}</b></button>`).join("")}</div>
      ${shown.length > UP_TOP ? `<button class="btn light" id="uAll" style="margin-top:8px">${uptimeAll ? "Show fewer" : `Show all ${shown.length}`}</button>` : ""}</div>

    <div class="card so-list">
      <div class="toolbar">
        <div class="segmented" id="uStatus">${[["", "All"], ["active", "Offline now"], ["restored", "Back online"]]
          .map(([v, l]) => `<button data-v="${v}" class="${uptimeFilters.status === v ? "active" : ""}">${l}</button>`).join("")}</div>
        <button class="btn light" id="uClear" ${uptimeFilters.outlet ? "" : "hidden"}>Clear filter</button>
      </div>
      ${episodes.length ? `<table><thead><tr><th>Outlet</th><th>Status</th><th>Went offline</th><th>Back online</th><th>Downtime</th></tr></thead>
        <tbody>${episodes.map((e) => `<tr>
          <td>${esc(e.outlet_name.split(" · ").slice(1).join(" · ") || e.outlet_name)}${e.zomato_id ? ` <span class="muted">${esc(e.zomato_id)}</span>` : ""}</td>
          <td><span class="status ${e.is_active ? "pending" : "replied"}">${e.is_active ? "Offline" : "Back"}</span></td>
          <td class="muted">${new Date(e.first_detected_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}</td>
          <td class="muted">${e.restored_at ? new Date(e.restored_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "—"}</td>
          <td>${offlineFor(e)}</td></tr>`).join("")}</tbody></table>`
        : `<div class="empty-state"><h3>No offline events match</h3><p>Every checked outlet stayed online.</p></div>`}
    </div>`;
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

// ---------- stock-outs ----------
const MEALS = [
  { name: "Breakfast", hours: "5 am – 12 pm", from: 5, to: 12, tone: "#f5a524" },
  { name: "Lunch", hours: "12 – 4 pm", from: 12, to: 16, tone: "#e5484d" },
  { name: "Evening Snacks", hours: "4 – 7 pm", from: 16, to: 19, tone: "#a855f7" },
  { name: "Dinner", hours: "7 – 11 pm", from: 19, to: 23, tone: "#408fca" },
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
        <div class="so-big">${inr.format(summary.active)}<small> items out of stock right now</small></div>
        <p>across ${summary.outlets_affected} outlet${summary.outlets_affected === 1 ? "" : "s"} · ${inr.format(restored)} back in stock · avg downtime ${downtimeText(summary.avg_downtime) || "—"}${summary.long_off ? ` · ${inr.format(summary.long_off)} off for ${summary.long_off_days}+ days` : ""}</p>
        ${SHOW_STOCK_LOSS ? `<p class="so-lost" title="Estimate: each item's usual sales for the hours it was out, using the outlet's own hour-by-hour order pattern${summary.lost_unpriced ? `. ${summary.lost_unpriced} stock-outs have no sales history, so no ₹` : ""}">
          <b>${rupees(summary.lost_sales)}</b> of sales missed in this period <small>(estimate)</small></p>` : ""}</div>
      ${hasToday ? `<div class="so-now">Now serving<b>${now}</b></div>` : ""}
    </div>

    <div class="so-section"><h3>By mealtime <small>items out ${periodWord}, under the first meal each went out in · click to filter</small></h3>
      <div class="so-meals">${summary.by_meal.map((m) => {
        const meta = MEALS.find((x) => x.name === m.meal);
        return `<button class="so-meal ${stockFilters.meal === m.meal ? "on" : ""} ${hasToday && m.meal === now ? "now" : ""}" data-meal="${m.meal}" style="--tone:${meta.tone}">
          ${hasToday && m.meal === now ? '<em>NOW</em>' : ""}<span class="so-meal-name">${m.meal}</span><span class="so-meal-hours">${meta.hours}</span>
          <b>${inr.format(mealNum(m))}</b>
          <span class="so-bar"><i style="width:${(mealNum(m) / maxMeal) * 100}%"></i></span></button>`;
      }).join("")}</div>
      ${summary.long_off ? `<button class="so-earlier ${stockFilters.status === "long" ? "on" : ""}" id="sLong"><b>+${inr.format(summary.long_off)}</b> off for ${summary.long_off_days}+ days · probably taken off the menu · click to see</button>` : ""}</div>

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
        <button class="btn blue" id="sExport" style="margin-left:auto">Export to Excel</button>
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
  $("#sLong")?.addEventListener("click", () => { stockFilters.status = "long"; stockFilters.meal = ""; renderStockOuts(page); });
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
    if (!res.ok) throw new Error(`Export failed (${res.status})`);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(await res.blob());
    a.download = `stock-outs_${new Date().toISOString().slice(0, 10)}.xlsx`;
    a.click(); URL.revokeObjectURL(a.href);
  } catch (e) { toast(e.message); }
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
    (!stockFilters.meal || (r.mealtime === stockFilters.meal && (stockFilters.status === "active" || !r.earlier))) &&
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
const setup = { rows: [], deleted: [], filter: "", dirty: false, bulkPlatform: "zomato", bulkSelected: new Map() };

async function renderSetup(page, { creating = false } = {}) {
  const [industries, clients, data] = await Promise.all([
    api("/industries"), api("/clients"), creating ? null : api(`/brands/${state.brandId}/outlets`),
  ]);
  const brand = creating ? null : state.config.brand;
  const staff = state.me.is_staff;
  const first = creating && !state.brands.length;
  setup.rows = creating ? [] : data.outlets.map((o) => ({ ...o, labels: { ...o.labels } }));
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
    const pick = e.target.closest("[data-pick]");
    if (pick) openPicker(pick, Number(pick.dataset.idx), pick.dataset.pick);
  });

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
  if (!creating && brand) renderGoogleCard(page, brand.client_id);
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
    catch (err) { toast(err.message); e.currentTarget.disabled = false; }
  });
  card.querySelectorAll("[data-gsync]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true; b.textContent = "Syncing…";
    try {
      await api(`/google/connections/${b.dataset.gsync}/sync`, {}, { method: "POST" });
      toast("Fetching this account's Google locations. They'll appear in the Google list in a minute.");
      setTimeout(() => render(), 45000);
    } catch (err) { toast(err.message); b.disabled = false; b.textContent = "Sync locations"; }
  }));
  card.querySelectorAll("[data-disconnect]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("Disconnect this Google account? Reviews and numbers already saved stay, but new ones stop arriving.")) return;
    try { await api(`/google/connections/${b.dataset.disconnect}`, {}, { method: "DELETE" }); toast("Google disconnected"); render(); }
    catch (err) { toast(err.message); }
  }));
}

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
  try { d = await api(`/brands/${state.brandId}/outlets/link-suggestions`); } catch (e) { toast(e.message); return; }
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

function renderOutletRows() {
  const match = (r) => !setup.filter || [r.outlet_name, r.area, r.city, r.zomato, r.swiggy, r.google]
    .some((v) => (v || "").toLowerCase().includes(setup.filter));
  const visible = setup.rows.map((r, i) => [r, i]).filter(([r]) => match(r));
  $("#outletCount").textContent = `· ${setup.rows.length}${setup.deleted.length ? ` (${setup.deleted.length} to delete)` : ""}`;
  const cell = (r, i, p) => r[p]
    ? `<div class="id-chip" title="${esc(r.labels[p] || r[p])}"><button class="chip-pick" data-pick="${p}" data-idx="${i}">${esc(r[p])}</button><button class="chip-x" data-clear="${p}" data-idx="${i}" title="Unmap">×</button></div>`
    : `<button class="pick-btn" data-pick="${p}" data-idx="${i}">+ Pick</button>`;
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
  } catch (e) { toast(e.message); }
  btn.disabled = false;
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
    if (!res.ok) throw new Error(body.detail || res.statusText);
    toast(`Saved ${body.saved} outlet${body.saved === 1 ? "" : "s"}${body.deleted ? `, deleted ${body.deleted}` : ""}`);
    setup.dirty = false;
    await loadBrand(state.brandId);
  } catch (e) { toast(e.message); }
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
    tag.onerror = () => { mapsReady = null; reject(new Error("Couldn't load Google Maps")); };
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
      <form id="zSearch" class="comp-search comp-search-lg"><input name="q" placeholder="Search a restaurant, dish or cuisine on ${zName()}, e.g. Meghana, biryani, chinese" autofocus>
        <button class="btn blue">Search</button></form>
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

  const err = (e) => { $("#zError").textContent = e.message; };
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
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const name = /filename="?([^";]+)"?/.exec(res.headers.get("Content-Disposition") || "")?.[1] || `${state.compTab}-competition.xlsx`;
      const f = document.createElement("a");
      f.href = URL.createObjectURL(await res.blob()); f.download = name; f.click(); URL.revokeObjectURL(f.href);
      toast("Report downloaded");
    } catch (x) { toast(x.message); }
    delete a.dataset.busy; a.classList.remove("disabled"); a.textContent = label;
  });
  page.querySelectorAll("[data-zuntrack]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); track({ res_id: b.dataset.zuntrack }, false); }));
  page.querySelectorAll("[data-zview]").forEach((tr) => tr.addEventListener("click", () => showMarketRestaurant(outletId, tr.dataset.zview, track)));
  let results = [];
  $("#zSearch").addEventListener("submit", async (e) => {
    e.preventDefault(); $("#zError").textContent = "";
    const btn = e.target.querySelector("button"); btn.disabled = true;
    $("#zResults").innerHTML = `<p class="muted">Searching ${zName()}…</p>`;
    try {
      const r = await apiJSON(`${zBase(outletId)}/search`, "POST", { q: e.target.q.value, spot: zPeek(outletId)?.spot });
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
    } catch (x) { $("#zError").textContent = x.message; }
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
    catch (x) { $("#zError").textContent = x.message; b.disabled = false; }
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
    const fail = async (res) => { const b = await res.json().catch(() => ({})); throw new Error(b.detail || `${res.status} ${res.statusText}`); };
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
    } catch (x) { $("#phError").textContent = x.message; }
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
  catch (e) { box.innerHTML = `<div class="card" style="margin-top:16px"><p class="login-error">${esc(e.message)}</p></div>`; return; }
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
          <td class="num">₹${t.price}</td><td class="num">${t.reorder != null ? `<small class="muted">reordered</small> ${Math.round(t.reorder * 100)}%`
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
        <td class="num">₹${i.price ?? "—"}</td><td>${[...i.tags, i.in_stock ? "" : "Out of stock"].filter(Boolean).map((t) => `<span class="comp-svc">${esc(t)}</span>`).join("")}</td></tr>`).join("")}</tbody></table></details>
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

  const err = (e) => { $("#compError").textContent = e.message; };
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
    } catch (e) { cell.innerHTML = `<p class="login-error">${esc(e.message)}</p>`; }
  }));
  $("#relocate").addEventListener("click", () => renderLocate(page, o));
  if ($("#compMap")) {
    mapP = drawCompMap($("#compMap"), d.maps_key, me, comps, (pid) => trackBtn(pid, true))
      .catch((e) => { $("#compMap").innerHTML = `<p class="muted" style="padding:16px">${esc(e.message)}</p>`; return null; });
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
    } catch (e) { $("#compError").textContent = e.message; $("#compResults").innerHTML = ""; }
  };
  $("#locSearch").addEventListener("submit", (e) => { e.preventDefault(); run(e.target.q.value.trim()); });
  $("#compResults").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-pick]");
    if (!b) return;
    b.disabled = true;
    try { await apiJSON(`/brands/${state.brandId}/competition/${o.outlet_id}/locate`, "POST", { place_id: b.dataset.pick }); render(); }
    catch (x) { $("#compError").textContent = x.message; b.disabled = false; }
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
    } catch (err) { toast(err.message); }
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
    } catch (err) { toast(err.message); }
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
    s.list.addEventListener("change", (e) => { const cb = e.target; if (cb.type !== "checkbox") return; cb.checked ? s.state.sel.add(cb.value) : s.state.sel.delete(cb.value); updateBtn(s); });
    s.all.addEventListener("change", () => { s.list.querySelectorAll("input:not(:disabled)").forEach((cb) => { cb.checked = s.all.checked; cb.checked ? s.state.sel.add(cb.value) : s.state.sel.delete(cb.value); }); updateBtn(s); });
    s.pager.addEventListener("click", (e) => { const b = e.target.closest("[data-pg]"); if (!b) return; s.state.page += Number(b.dataset.pg); load(key); });
    s.btn.addEventListener("click", async () => {
      try {
        const res = await apiJSON(`/staff/clients/${clientId}/ids/${clientView.platform}`, "POST", { op: key === "avail" ? "assign" : "remove", ids: [...s.state.sel] });
        toast(res.message); s.state.sel.clear(); renderClient(page, clientId);
      } catch (err) { toast(err.message); }
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
    } catch (err) { $("#loginError").textContent = err.message; }
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
      catch (err) { $("#loginError").textContent = err.message; btn.disabled = false; }
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
    catch (err) { toast(err.message); }
    setTimeout(() => { e.target.disabled = false; }, 60000);
  });
  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('[type="submit"]'); btn.disabled = true;
    try {
      await api("/auth/me").catch(() => null);  // sets the CSRF cookie
      await apiJSON("/auth/otp/verify", "POST", { identifier, code: new FormData(e.target).get("code") });
      location.reload();
    } catch (err) { $("#loginError").textContent = err.message; btn.disabled = false; }
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
    } catch (err) { $("#loginError").textContent = err.message; btn.disabled = false; }
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
    } catch (err) { error.textContent = err.message; btn.disabled = false; }
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
    } catch (err) { error.textContent = err.message; }
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
    } catch (err) { $("#memberError").textContent = err.message; }
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
      } catch (err) { toast(err.message); }
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
      } catch (err) { error.textContent = err.message; save.disabled = false; }
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
      } catch (err) { toast(err.message); }
    });
  };

  page.querySelectorAll("[data-member]").forEach((tr) => {
    const u = team.users.find((x) => x.id === Number(tr.dataset.member));
    if (u.username === state.me.username) return;
    const url = `/clients/${clientId}/team/${u.id}`;
    tr.querySelector("[data-role]").addEventListener("change", async (e) => {
      if (e.target.value === "manager") return openPicker(tr, u, "manager");
      try { await apiJSON(url, "PATCH", { role: e.target.value }); toast("Role updated"); }
      catch (err) { toast(err.message); }
      renderTeam(page, clientId);
    });
    tr.querySelector("[data-outlets]")?.addEventListener("click", () => openPicker(tr, u, "manager"));
    tr.querySelector("[data-pass]").addEventListener("click", () => openPassword(tr, u));
    tr.querySelector("[data-delete]")?.addEventListener("click", () => openDelete(tr, u));
    tr.querySelector("[data-toggle]").addEventListener("click", async () => {
      try { await apiJSON(url, "PATCH", { is_active: !u.is_active }); renderTeam(page, clientId); } catch (err) { toast(err.message); }
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
  } catch (e) { $("#csvResult").innerHTML = `<p class="login-error">${esc(e.message)}</p>`; }
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
  } catch (e) { toast(e.message); $("#csvSave").disabled = false; }
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
  else document.body.classList.toggle("collapsed");
});
$("#scrim").addEventListener("click", () => document.body.classList.remove("nav-open"));
$("#fullscreenBtn").addEventListener("click", () => {
  if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen?.();
});
window.addEventListener("hashchange", render);

boot().catch((e) => { $("#page").innerHTML = `<div class="card empty-state"><h3>Something went wrong</h3><p>${esc(e.message)}</p></div>`; });


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
    $("#askThinking").outerHTML = e.message === "Not configured yet"
      ? `<div class="ask-msg bot muted">The assistant isn't configured yet.</div>`
      : `<div class="ask-msg bot err">${esc(e.message)}</div>`;
  }
  assistant.busy = false; $("#askSend").disabled = false;
  box.scrollTop = box.scrollHeight;
}
