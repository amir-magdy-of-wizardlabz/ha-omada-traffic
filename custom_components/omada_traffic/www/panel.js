/* Omada Traffic panel for Home Assistant. Vanilla web component, no build step. */

const CSS = `
:host { display:block; --bg:#0f1113; --card:#17191d; --card2:#1d2025; --line:#26292e; --text:#e8e9eb; --muted:#8b8f96; --dim:#5c6068;
  --green:#22c55e; --green-dim:#15803d; --orange:#f0781e; --orange-dim:#9a4a12; --accent:#e8e9eb; --ghost:#3a3d43;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; font-size:14px; color:var(--text); background:var(--bg); min-height:100vh; }
* { box-sizing:border-box; }
.page { padding:16px 20px 40px; max-width:1800px; margin:0 auto; }
h1 { font-size:22px; font-weight:600; margin:4px 0 14px; display:flex; align-items:center; gap:14px; }
h1 .status { font-size:12px; color:var(--muted); font-weight:400; }
h2 { font-size:16px; font-weight:600; margin:0; display:flex; align-items:center; gap:8px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
.strip { display:grid; grid-template-columns: 300px 280px 1fr; gap:12px; margin-bottom:14px; max-width:1000px; }
.strip .card { display:flex; flex-direction:column; gap:6px; }
.strip .title { font-size:12px; color:var(--muted); display:flex; justify-content:space-between; align-items:center; }
.big { font-size:22px; font-weight:600; }
.rate { display:grid; grid-template-columns:auto auto 1fr auto; gap:6px 10px; align-items:baseline; }
.rate .dir { font-size:12px; color:var(--muted); }
.rate .val { font-size:20px; font-weight:600; }
.rate .sec { font-size:11px; color:var(--muted); text-align:right; }
.green { color:var(--green); } .orange { color:var(--orange); }
.bar { height:6px; background:#2a2d33; border-radius:3px; position:relative; overflow:hidden; margin:4px 0; }
.bar > i { position:absolute; left:0; top:0; bottom:0; background:var(--accent); border-radius:3px; }
.bar > b { position:absolute; top:0; bottom:0; width:2px; background:#fff; opacity:.9; }
.bar > s { position:absolute; left:0; top:0; bottom:0; background:repeating-linear-gradient(90deg,#3a3d43 0 3px,transparent 3px 6px); }
.small { font-size:11px; color:var(--muted); }
.section { margin-top:14px; }
.section-head { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:10px; }
.seg { display:inline-flex; background:#121417; border:1px solid var(--line); border-radius:8px; padding:2px; }
.seg button { background:transparent; border:0; color:var(--muted); padding:4px 10px; border-radius:6px; cursor:pointer; font:inherit; font-size:12px; }
.seg button.on { background:#2a2d33; color:var(--text); font-weight:600; }
.seg button:hover { color:var(--text); }
.filters { display:flex; gap:18px; align-items:flex-end; flex-wrap:wrap; margin-bottom:10px; }
.filters .grp { display:flex; flex-direction:column; gap:4px; }
.filters label { font-size:11px; color:var(--muted); }
.chips { display:flex; gap:6px; align-items:center; }
.chip { height:32px; min-width:32px; padding:0 10px; border:1px solid var(--line); border-radius:8px; background:#121417; color:var(--muted); cursor:pointer; display:inline-flex; align-items:center; gap:6px; font:inherit; font-size:12px; }
.chip.on { border-color:#9aa0a8; color:var(--text); background:#23262b; box-shadow:0 0 0 1px #9aa0a8 inset; }
.chip:hover { color:var(--text); }
.chip svg { width:16px; height:16px; fill:none; stroke:currentColor; stroke-width:1.6; }
.avatar { width:32px; height:32px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-weight:600; font-size:12px; color:#fff; border:2px solid transparent; cursor:pointer; }
.avatar.on { border-color:#fff; box-shadow:0 0 0 2px #0f1113 inset; }
select { background:#121417; color:var(--text); border:1px solid var(--line); border-radius:8px; height:32px; padding:0 8px; font:inherit; font-size:12px; max-width:220px; }
.sub { color:var(--muted); font-size:12px; margin:0 0 10px; } .sub b { color:var(--text); font-weight:600; }
.grid3 { display:grid; grid-template-columns: 1.3fr 1fr 1fr; gap:12px; }
.stat { display:grid; grid-template-columns: repeat(3, 1fr); gap:8px; }
.stat .lbl { font-size:11px; color:var(--muted); }
.stat .v { font-size:20px; font-weight:600; }
.stat .s { font-size:11px; color:var(--muted); }
.dircard { padding:10px 12px; border:1px solid var(--line); border-radius:8px; background:var(--card2); margin-bottom:8px; }
.dircard .t { font-size:12px; font-weight:600; margin-bottom:6px; }
.rank { display:flex; flex-direction:column; gap:8px; max-height:300px; overflow-y:auto; scrollbar-width:thin; }
.rank .unit { position:sticky; bottom:0; background:var(--card); padding-top:4px; }
.rank .hd { display:flex; justify-content:space-between; font-size:12px; color:var(--muted); }
.rank .hd b { color:var(--text); font-weight:600; }
.row { display:grid; grid-template-columns: 120px 1fr 54px; gap:10px; align-items:center; font-size:12px; }
.row .nm { display:flex; align-items:center; gap:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.row .bars { display:flex; flex-direction:column; gap:3px; }
.row .bars i { display:block; height:5px; border-radius:3px; }
.row .bars .d { background:var(--green); } .row .bars .u { background:var(--orange); }
.row .nums { text-align:right; font-size:11px; line-height:1.2; }
.unit { text-align:right; font-size:10px; color:var(--dim); margin-top:auto; }
.chart { position:relative; margin-top:10px; }
.chart svg { width:100%; display:block; }
.chart .lbl { position:absolute; left:0; top:0; font-size:11px; font-weight:600; }
.tip { position:absolute; pointer-events:none; background:#0b0c0e; border:1px solid #3a3d43; border-radius:6px; padding:6px 8px; font-size:11px; white-space:nowrap; z-index:5; transform:translate(-50%, -110%); color:var(--text); }
.tip b { font-weight:600; }
.livebar { display:flex; justify-content:flex-end; gap:10px; font-size:11px; color:var(--muted); align-items:center; }
.conn { width:8px; height:8px; border-radius:50%; background:var(--dim); display:inline-block; flex:none; margin-right:6px; }
.conn.on { background:var(--green); box-shadow:0 0 0 3px rgba(34,197,94,.15); }
.livebar .dot { width:7px; height:7px; border-radius:50%; background:var(--green); display:inline-block; }
.livebar button { font:inherit; font-size:11px; background:#23262b; border:1px solid var(--line); color:var(--text); border-radius:6px; padding:2px 8px; cursor:pointer; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; font-size:11px; color:var(--muted); font-weight:600; padding:6px 8px; border-bottom:1px solid var(--line); cursor:pointer; white-space:nowrap; user-select:none; }
th.r, td.r { text-align:right; }
td { padding:7px 8px; border-bottom:1px solid #1e2126; vertical-align:middle; }
tr.child td { background:#141619; }
tr.child td:first-child { padding-left:34px; }
td .nm { font-weight:600; } td .sb { font-size:11px; color:var(--muted); }
td .tw { display:flex; align-items:center; gap:8px; }
.caret { width:16px; display:inline-block; color:var(--muted); cursor:pointer; }
.spark svg { display:block; }
.muted { color:var(--muted); }
.nowcell { font-size:11px; line-height:1.25; text-align:right; }
.err { background:#3b1113; border:1px solid #7f1d1d; color:#fecaca; padding:8px 12px; border-radius:8px; margin-bottom:10px; font-size:12px; }
.rank .row[data-f] { cursor:pointer; border-radius:6px; padding:2px 4px; margin:-2px -4px; }
.rank .row[data-f]:hover { background:#23262b; }
.avatar.photo { background-size:cover; background-position:center; color:transparent; }
.menu { position:fixed; z-index:50; min-width:240px; background:#121417; border:1px solid #3a3d43; border-radius:10px; box-shadow:0 10px 30px rgba(0,0,0,.6); padding:6px; font-size:13px; }
.menu .mh { padding:6px 10px 8px; border-bottom:1px solid var(--line); margin-bottom:4px; }
.menu .mh b { display:block; } .menu .mh span { font-size:11px; color:var(--muted); }
.menu .ms { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; padding:8px 10px 2px; }
.menu .mi { display:flex; align-items:center; gap:8px; padding:6px 10px; border-radius:6px; cursor:pointer; }
.menu .mi:hover { background:#23262b; } .menu .mi.on { color:var(--green); }
.menu .mi .avatar { width:22px; height:22px; font-size:10px; }
.menu form { display:flex; gap:6px; padding:4px 10px 6px; }
.menu input, .menu select { flex:1; background:#0f1113; border:1px solid var(--line); color:var(--text); border-radius:6px; padding:5px 8px; font:inherit; font-size:12px; min-width:0; }
.menu button { background:#23262b; border:1px solid var(--line); color:var(--text); border-radius:6px; padding:4px 10px; font:inherit; font-size:12px; cursor:pointer; }
.menu .ask { background:#2a2110; border:1px solid #6b4e12; color:#fcd34d; border-radius:6px; padding:6px 10px; margin-bottom:4px; font-size:12px; }
.unk { display:flex; flex-wrap:wrap; gap:8px; align-items:center; background:#2a2110; border:1px solid #6b4e12; color:#fcd34d; border-radius:10px; padding:8px 12px; margin-bottom:12px; font-size:12px; }
.unk .chip { height:28px; color:var(--text); }
.menu .note { font-size:11px; color:var(--muted); padding:4px 10px 6px; }
.more { background:transparent; border:0; color:var(--muted); font-size:16px; cursor:pointer; padding:0 6px; border-radius:6px; }
.more:hover { background:#23262b; color:var(--text); }
tr[data-mac] { cursor:pointer; }
@media (max-width: 1100px) { .strip { grid-template-columns:1fr; max-width:none; } .grid3 { grid-template-columns:1fr; } }
`;

const AVATAR_COLORS = ["#6366f1", "#ec4899", "#14b8a6", "#f59e0b", "#8b5cf6", "#0ea5e9", "#84cc16"];
const TYPE_ICON = {
  "Phone": '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
  "PC": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  "Laptop": '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/>',
  "Tablet": '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M11 18h2"/>',
  "TV": '<rect x="2" y="5" width="20" height="13" rx="2"/><path d="M8 22h8"/>',
  "Streaming": '<path d="M3 18l4-4M5 8l10 10M9 4l10 10M12 2l2 2M2 12l2 2"/><rect x="12" y="12" width="9" height="9" rx="1"/>',
  "Speaker": '<rect x="6" y="2" width="12" height="20" rx="2"/><circle cx="12" cy="15" r="3"/><circle cx="12" cy="7" r="1"/>',
  "Game console": '<path d="M6 11h4M8 9v4M15 11h.01M18 12h.01"/><path d="M4 16a4 4 0 0 1 4-8h8a4 4 0 0 1 4 8l-1 4h-2l-2-3H9l-2 3H5z"/>',
  "Camera": '<rect x="2" y="7" width="15" height="10" rx="2"/><path d="M17 10l5-2v8l-5-2z"/>',
  "Smart home": '<path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  "Printer": '<path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  "Network": '<circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M12 7v5M12 12l-6 5M12 12l6 5"/>',
  "Other": '<circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 2"/>',
};

const fmtBytes = (b, d) => {
  b = Math.max(0, b || 0);
  if (b >= 1e12) return (b / 1e12).toFixed(d ?? (b >= 1e13 ? 0 : 1)) + " TB";
  if (b >= 1e9) return (b / 1e9).toFixed(d ?? (b >= 1e10 ? 0 : 1)) + " GB";
  if (b >= 1e6) return (b / 1e6).toFixed(d ?? (b >= 1e7 ? 0 : 1)) + " MB";
  if (b >= 1e3) return (b / 1e3).toFixed(0) + " KB";
  return Math.round(b) + " B";
};
const fmtMbit = (bps) => { const m = (bps || 0) * 8 / 1e6; return (m >= 100 ? m.toFixed(0) : m >= 10 ? m.toFixed(1) : m.toFixed(2)) + " Mbit/s"; };
const fmtBps = (bps) => { bps = bps || 0; if (bps >= 1e6) return (bps / 1e6).toFixed(1) + " MB/s"; if (bps >= 1e3) return (bps / 1e3).toFixed(0) + " KB/s"; return Math.round(bps) + " B/s"; };
const fmtMbitShort = (bps) => { const m = (bps || 0) * 8 / 1e6; return m >= 10 ? m.toFixed(0) : m >= 1 ? m.toFixed(1) : m.toFixed(2); };
const fmtGB = (b, d = 0) => (Math.max(0, b || 0) / 1e9).toFixed(d);
const ago = (s) => s == null ? "–" : s < 60 ? `${s} s ago` : s < 3600 ? `${Math.round(s / 60)} min ago` : `${Math.round(s / 3600)} h ago`;

class OmadaTrafficPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.state = {
      filter: "house", dayStart: null, bwWindow: "1h", bwEnd: null, usWindow: "24h",
      tbWindow: "24h", tbBy: "device", tbSort: ["window", -1], expanded: new Set(), expandAll: false,
    };
    this.data = {};
    this._timers = [];
  }
  set hass(h) { this._hass = h; if (!this._init) { this._init = true; this.boot(); } }
  get tz() { return this.data.meta?.settings?.timezone; }

  async api(path) { return this._hass.callApi("GET", "omada_traffic/" + path); }

  async boot() {
    this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="page"><h1>Traffic <span class="status">loading…</span></h1></div>`;
    try {
      this.data.meta = await this.api("meta");
      if (this.state.dayStart == null) this.state.dayStart = this.data.meta.settings.day_start_hour;
      this.renderSkeleton();
      await this.refreshAll();
      this.renderUnknown(); this.checkDeepLink();
      this._onLoc = () => this.checkDeepLink();
      window.addEventListener("location-changed", this._onLoc); window.addEventListener("popstate", this._onLoc);
      this._timers.push(setInterval(() => this.refreshLive(), 30000));
      this._timers.push(setInterval(() => this.refreshSlow(), 60000));
      this._timers.push(setInterval(() => this.tickAge(), 5000));
    } catch (e) {
      this.shadowRoot.querySelector(".status").textContent = "error: " + (e.message || e);
    }
  }
  disconnectedCallback() { this._timers.forEach(clearInterval); if (this._onLoc) { window.removeEventListener("location-changed", this._onLoc); window.removeEventListener("popstate", this._onLoc); } }

  q(sel) { return this.shadowRoot.querySelector(sel); }
  get ds() { return `day_start=${this.state.dayStart}`; }

  async refreshAll() { await Promise.all([this.loadSummary(), this.loadBandwidth(), this.loadUsage(), this.loadTable()]); }
  async refreshLive() { await Promise.all([this.loadSummary(), this.state.bwEnd == null ? this.loadBandwidth() : null]); }
  async refreshSlow() { this.data.meta = await this.api("meta"); this.renderUnknown(); await Promise.all([this.loadUsage(), this.loadTable()]); }

  async loadSummary() { this.data.summary = await this.api(`summary?${this.ds}`); this.renderStrip(); }
  async loadBandwidth() {
    const s = this.state; const end = s.bwEnd ? `&end=${s.bwEnd}` : "";
    const d = await this.api(`bandwidth?window=${s.bwWindow}&filter=${encodeURIComponent(s.filter)}${end}`);
    this.data.bw = d; this.renderBandwidth();
  }
  async loadUsage() {
    const s = this.state;
    this.data.usage = await this.api(`usage?window=${s.usWindow}&filter=${encodeURIComponent(s.filter)}&${this.ds}`);
    this.renderUsage();
  }
  async loadTable() {
    const s = this.state;
    this.data.table = await this.api(`table?by=${s.tbBy}&window=${s.tbWindow}&${this.ds}`);
    this.renderTable();
  }

  // ----------------------------------------------------------------- time helpers
  fmtTime(ts, opts) { return new Date(ts * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", timeZone: this.tz, ...opts }); }
  connText(c) {
    if (c.online) return "Connected";
    if (!c.last_seen) return "Disconnected";
    const s = Math.max(0, Date.now() / 1000 - c.last_seen);
    const ago = s < 90 ? "just now" : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`;
    return `Disconnected · last seen ${ago}`;
  }
  fmtDate(ts, opts) { return new Date(ts * 1000).toLocaleDateString([], { month: "short", day: "numeric", timeZone: this.tz, ...opts }); }
  fmtDayTime(ts) {
    const now = this.data.summary?.now || Date.now() / 1000;
    const dayOf = (t) => new Date(t * 1000).toLocaleDateString([], { timeZone: this.tz });
    const today = dayOf(now), yday = dayOf(now - 86400), d = dayOf(ts);
    const day = d === today ? "Today" : d === yday ? "Yesterday" : new Date(ts * 1000).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric", timeZone: this.tz });
    return `${day}, ${this.fmtTime(ts)}`;
  }
  fmtDayName(ts) {
    const now = this.data.summary?.now || Date.now() / 1000;
    const dayOf = (t) => new Date(t * 1000).toLocaleDateString([], { timeZone: this.tz });
    if (dayOf(ts) === dayOf(now)) return "Today";
    if (dayOf(ts) === dayOf(now - 86400)) return "Yesterday";
    return new Date(ts * 1000).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric", timeZone: this.tz });
  }

  // ----------------------------------------------------------------- skeleton
  renderSkeleton() {
    this.shadowRoot.innerHTML = `<style>${CSS}</style>
    <div class="page">
      <h1>Traffic <span class="status" id="status"></span></h1>
      <div id="err"></div>
      <div id="unknown"></div>
      <div class="strip" id="strip"></div>
      <div class="card section" id="bw">
        <div class="section-head"><h2>Bandwidth</h2><div class="seg" id="bw-win"></div></div>
        <div class="filters" id="bw-filters"></div>
        <p class="sub" id="bw-sub"></p>
        <div class="grid3">
          <div><div class="dircard" id="bw-down"></div><div class="dircard" id="bw-up"></div></div>
          <div class="card rank" id="bw-people"></div>
          <div class="card rank" id="bw-types"></div>
        </div>
        <div class="livebar" id="bw-live"></div>
        <div class="chart" id="bw-chart-down"></div>
        <div class="chart" id="bw-chart-up"></div>
      </div>
      <div class="card section" id="us">
        <div class="section-head"><h2>Usage</h2>
          <div style="display:flex;gap:10px;align-items:center">
            <span class="small">Day starts</span><div class="seg" id="us-daystart"></div>
            <div class="seg" id="us-win"></div></div></div>
        <div class="filters" id="us-filters"></div>
        <p class="sub" id="us-sub"></p>
        <div class="grid3">
          <div><div class="dircard" id="us-down"></div><div class="dircard" id="us-up"></div></div>
          <div class="card rank" id="us-people"></div>
          <div class="card rank" id="us-types"></div>
        </div>
        <div class="livebar" id="us-live"></div>
        <div class="chart" id="us-chart"></div>
      </div>
      <div class="card section" id="tb">
        <div class="section-head">
          <div style="display:flex;gap:12px;align-items:center"><h2>Usage by</h2><div class="seg" id="tb-by"></div><span class="small">click a device for options</span></div>
          <div style="display:flex;gap:10px;align-items:center"><button class="chip" id="tb-expand">Expand all</button><div class="seg" id="tb-win"></div></div></div>
        <div id="tb-table"></div>
      </div>
    </div>`;
    this.renderSeg("#bw-win", [["1h", "1 h"], ["6h", "6 h"], ["24h", "24 h"], ["7d", "7 days"]], this.state.bwWindow, (v) => { this.state.bwWindow = v; this.state.bwEnd = null; this.loadBandwidth(); });
    this.renderSeg("#us-win", [["6h", "6 h"], ["24h", "24 h"], ["7d", "7 days"], ["14d", "14 days"], ["30d", "30 days"], ["plan", "Plan"]], this.state.usWindow, (v) => { this.state.usWindow = v; this.loadUsage(); });
    this.renderSeg("#us-daystart", [["0", "Midnight"], ["6", "6 AM"]], String(this.state.dayStart), (v) => { this.state.dayStart = Number(v); this.refreshAll(); });
    this.renderSeg("#tb-by", [["device", "Device"], ["person", "Person"], ["type", "Type"]], this.state.tbBy, (v) => { this.state.tbBy = v; this.state.expanded.clear(); this.loadTable(); });
    this.renderSeg("#tb-win", [["6h", "6 h"], ["24h", "24 h"], ["7d", "7 days"], ["14d", "14 days"], ["30d", "30 days"], ["plan", "Plan"]], this.state.tbWindow, (v) => { this.state.tbWindow = v; this.loadTable(); });
    this.q("#tb-expand").onclick = () => { this.state.expandAll = !this.state.expandAll; this.state.expanded.clear(); this.renderTable(); };
    this.renderFilters("#bw-filters"); this.renderFilters("#us-filters");
    // Clicking a person or type in a ranking list filters the page to it.
    this.shadowRoot.addEventListener("click", (e) => {
      const row = e.composedPath().find((n) => n.classList && n.classList.contains("row") && n.dataset.f);
      if (row && row.closest(".rank")) this.setFilter(row.dataset.f);
    });
    this.shadowRoot.addEventListener("keydown", (e) => { if (e.key === "Escape") this.closeMenu(); });
    this.shadowRoot.addEventListener("click", (e) => { if (this._menu && !e.composedPath().includes(this._menu)) this.closeMenu(); });
  }

  // ----------------------------------------------------------------- unidentified devices
  renderUnknown() {
    const el = this.q("#unknown"); if (!el) return;
    const list = (this.data.meta?.clients || []).filter((c) => c.needs_id);
    if (!list.length) { el.innerHTML = ""; return; }
    el.innerHTML = `<div class="unk"><span>${list.length === 1 ? "1 device needs" : list.length + " devices need"} identifying:</span>${list.map((c) => `<button class="chip" data-unk="${c.mac}"><span class="conn ${c.online ? "on" : ""}"></span>${c.label}</button>`).join("")}</div>`;
    el.querySelectorAll("[data-unk]").forEach((b) => b.onclick = (e) => { e.stopPropagation(); const r = b.getBoundingClientRect(); this.openMenu(r.left, r.bottom + 4, b.dataset.unk); });
  }
  // A notification links to /traffic?device=<MAC>: open that device's menu.
  checkDeepLink() {
    const mac = new URLSearchParams(window.location.search).get("device");
    if (!mac || mac === this._linked || !this.data.meta) return;
    this._linked = mac;
    setTimeout(() => this.openMenu(window.innerWidth / 2 - 130, 90, mac.toUpperCase()), 50);
  }

  // ----------------------------------------------------------------- device menu
  closeMenu() { if (this._menu) { this._menu.remove(); this._menu = null; } }
  openMenu(x, y, mac) {
    this.closeMenu();
    const c = this.data.meta.clients.find((k) => k.mac === mac); if (!c) return;
    const admin = !!this._hass.user?.is_admin; const m = this.data.meta;
    const types = ["Phone", "PC", "Laptop", "Tablet", "TV", "Streaming", "Speaker", "Game console", "Camera", "Smart home", "Printer", "Network", "Other"];
    const el = document.createElement("div"); el.className = "menu";
    el.innerHTML = `${c.needs_id ? `<div class="ask">What device is this?${c.calls_itself ? ` It calls itself <b>${c.calls_itself}</b>.` : ""}</div>` : ""}<div class="mh"><b><span class="conn ${c.online ? "on" : ""}"></span> ${c.label}</b><span><span class="${c.online ? "green" : ""}">${this.connText(c)}</span> · ${c.mac} · ${c.ip || "no IP"} · ${c.vendor || "unknown vendor"}${c.via ? " · " + c.via : ""}</span></div>
      <div class="mi" data-act="show">📈&nbsp; Show only this device in the charts</div>
      ${admin ? `
      <div class="ms">Assign to</div>
      ${[...m.people].map((p) => `<div class="mi ${c.owner === p && !c.needs_id ? "on" : ""}" data-owner="${p}">${this.avatar(p)}<span>${p}</span>${c.owner === p && !c.needs_id ? "<span style='margin-left:auto'>✓</span>" : ""}</div>`).join("")}
      <form data-form="person"><input name="name" placeholder="Add a person…" maxlength="40"><button>Add</button></form>
      <div class="ms">Name</div>
      <form data-form="rename"><input name="name" value="${c.label.replace(/"/g, "&quot;")}" maxlength="60"><button>Save</button></form>
      <div class="ms">Type</div>
      <form data-form="type"><select name="type">${types.map((t) => `<option ${t === c.type ? "selected" : ""}>${t}</option>`).join("")}</select><button>Save</button></form>
      ${c.needs_id ? `<div class="mi" data-act="known">✓&nbsp; It's fine as it is, stop asking</div>` : ""}`
      : `<div class="note">Sign in as an administrator to assign or rename devices.</div>`}`;
    this.shadowRoot.appendChild(el); this._menu = el;
    const vw = window.innerWidth, vh = window.innerHeight; const r = el.getBoundingClientRect();
    el.style.left = `${Math.min(x, vw - r.width - 10)}px`; el.style.top = `${Math.min(y, vh - r.height - 10)}px`;
    el.querySelector('[data-act="show"]').onclick = () => { this.closeMenu(); this.setFilter("device:" + mac); this.q("#bw").scrollIntoView({ behavior: "smooth", block: "start" }); };
    const known = el.querySelector('[data-act="known"]'); if (known) known.onclick = () => this.assign(mac, {});
    el.querySelectorAll("[data-owner]").forEach((it) => it.onclick = () => this.assign(mac, { owner: it.dataset.owner === c.owner && !c.needs_id ? "" : it.dataset.owner }));
    el.querySelectorAll("form").forEach((f) => f.onsubmit = async (e) => {
      e.preventDefault(); const kind = f.dataset.form; const v = f.elements[kind === "type" ? "type" : "name"].value.trim();
      if (kind === "person") { if (!v) return; await this._hass.callApi("POST", "omada_traffic/person", { name: v }); await this.assign(mac, { owner: v }); }
      else if (kind === "rename") await this.assign(mac, { name: v === c.label ? undefined : v });
      else await this.assign(mac, { type: v });
    });
  }
  async assign(mac, fields) {
    try {
      await this._hass.callApi("POST", "omada_traffic/assign", { mac, ...fields });
      this.closeMenu();
      this.data.meta = await this.api("meta");
      this.renderFilters("#bw-filters"); this.renderFilters("#us-filters"); this.renderUnknown();
      await this.refreshAll();
    } catch (e) { this.q("#err").innerHTML = `<div class="err">Could not save: ${e.message || e}</div>`; setTimeout(() => this.q("#err").innerHTML = "", 6000); }
  }

  renderSeg(sel, items, current, onPick) {
    const el = this.q(sel);
    el.innerHTML = items.map(([v, l]) => `<button data-v="${v}" class="${v === current ? "on" : ""}">${l}</button>`).join("");
    el.querySelectorAll("button").forEach((b) => b.onclick = () => { el.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b)); onPick(b.dataset.v); });
  }

  setFilter(f) {
    this.state.filter = f; this.state.bwEnd = null;
    this.renderFilters("#bw-filters"); this.renderFilters("#us-filters");
    this.loadBandwidth(); this.loadUsage();
  }

  personColor(name) { const i = this.data.meta.people.indexOf(name); return name === "Home/Shared" ? "#3f4650" : AVATAR_COLORS[(i < 0 ? 0 : i) % AVATAR_COLORS.length]; }
  personPhoto(name) {
    const st = this._hass?.states || {}; const want = name.trim().toLowerCase();
    for (const id in st) {
      if (!id.startsWith("person.")) continue;
      const a = st[id].attributes || {};
      if (a.entity_picture && String(a.friendly_name || "").trim().toLowerCase() === want) return a.entity_picture;
    }
    return null;
  }
  avatar(name, extra = "") {
    const photo = this.personPhoto(name);
    const initials = name === "Home/Shared" ? "⌂" : name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
    if (photo) return `<span class="avatar photo ${extra}" style="background-image:url('${photo}')" title="${name}">${initials}</span>`;
    return `<span class="avatar ${extra}" style="background:${this.personColor(name)}" title="${name}">${initials}</span>`;
  }
  typeIcon(t) { return `<svg viewBox="0 0 24 24">${TYPE_ICON[t] || TYPE_ICON.Other}</svg>`; }

  renderFilters(sel) {
    const m = this.data.meta, f = this.state.filter, el = this.q(sel);
    const house = `<button class="chip ${f === "house" ? "on" : ""}" data-f="house"><svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg>Whole house</button>`;
    const types = m.types.map((t) => `<button class="chip ${f === "type:" + t ? "on" : ""}" data-f="type:${t}" title="${t}">${this.typeIcon(t)}</button>`).join("");
    const people = m.people.map((p) => `<span data-f="person:${p}">${this.avatar(p, f === "person:" + p ? "on" : "")}</span>`).join("");
    const devSel = f.startsWith("device:") ? f.slice(7) : "";
    const devices = `<select id="dev"><option value="">A device…</option>${m.clients.map((c) => `<option value="${c.mac}" ${c.mac === devSel ? "selected" : ""}>${c.label}${c.online ? "" : " (offline)"}</option>`).join("")}</select>`;
    el.innerHTML = `<div class="grp"><label>Show</label><div class="chips">${house}</div></div>
      <div class="grp"><label>Types</label><div class="chips">${types}</div></div>
      <div class="grp"><label>People</label><div class="chips">${people}</div></div>
      <div class="grp"><label>Device</label><div class="chips">${devices}${devSel ? '<button class="chip" data-f="house" title="Clear">✕</button>' : ""}</div></div>`;
    el.querySelectorAll("[data-f]").forEach((b) => b.onclick = () => this.setFilter(b.dataset.f));
    el.querySelector("#dev").onchange = (e) => this.setFilter(e.target.value ? "device:" + e.target.value : "house");
  }

  // ----------------------------------------------------------------- summary strip
  tickAge() {
    const s = this.data.summary; if (!s) return;
    const age = Math.round(Date.now() / 1000 - (s.last_poll || 0));
    this.shadowRoot.querySelectorAll(".read-age").forEach((e) => e.textContent = `read ${ago(age)}`);
    const st = this.q("#status"); const m = this.data.meta;
    st.textContent = m?.last_error ? `controller read failed: ${m.last_error}` : `${m?.clients?.filter((c) => c.online).length ?? "?"} devices online`;
  }
  renderStrip() {
    const s = this.data.summary; if (!s) return;
    const t = s.today, p = s.plan; const sum = t.down + t.up;
    const endLbl = this.fmtTime(t.end, { hour: "numeric", minute: undefined }).replace(":00", "");
    const projPct = t.projected ? Math.min(100, sum / t.projected * 100) : 0;
    const avgPct = t.projected && t.avg_day ? Math.min(100, t.avg_day / Math.max(t.projected, t.avg_day) * 100) : 0;
    const planCard = (p) => {
      const used = p.used, quota = p.quota || 0;
      const usedPct = quota ? Math.min(100, used / quota * 100) : 0, projPlanPct = quota ? Math.min(100, p.projected / quota * 100) : 0;
      const dayPct = p.days ? Math.min(100, (s.now - p.start) / (p.end - p.start) * 100) : 0;
      const spare = p.spare;
      const note = p.partial ? `counted since ${this.fmtDate(p.observed_from)} only` : (p.source === "wan" ? "measured at the gateway" : "sum of devices");
      return `<div class="card"><div class="title"><span><b style="color:var(--text)">${p.name}</b> · ${this.fmtDate(p.start)} – ${this.fmtDate(p.end - 1)}</span><span title="${note}">${p.partial ? "⚠ partial" : ""}</span></div>
        <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">
          <span class="big">${fmtGB(used, used < 1e10 ? 1 : 0)} GB <span class="muted" style="font-size:16px">/ ${quota ? fmtGB(quota) : "—"} GB</span></span>
          <span style="text-align:right"><div class="${spare != null && spare < 0 ? "orange" : "green"}" style="font-weight:600;font-size:12px">${spare == null ? "no quota set" : spare >= 0 ? `${fmtGB(spare)} GB to spare` : `${fmtGB(-spare)} GB over`}</div><div class="small">≈ ${fmtGB(p.projected)} GB by ${this.fmtDate(p.end - 1)}</div></span></div>
        <div class="bar"><s style="width:${projPlanPct}%"></s><i style="width:${usedPct}%"></i><b style="left:${dayPct}%"></b></div>
        <div class="small">▲ day ${p.day} of ${p.days} · ${note}</div></div>`;
    };
    const plans = s.plans || [s.plan];
    this.q("#strip").style.gridTemplateColumns = window.innerWidth > 1100 ? `300px 280px ${plans.map(() => "minmax(300px, 1fr)").join(" ")}` : "";
    this.q("#strip").style.maxWidth = `${640 + plans.length * 420}px`;
    this.q("#strip").innerHTML = `
      <div class="card"><div class="title"><span>Right now</span><span class="read-age">read ${ago(s.read_age)}</span></div>
        <div class="rate"><span class="dir green">↓ down</span><span class="val green">${fmtMbit(s.rates[0])}</span><span></span><span class="sec">${fmtBps(s.rates[0])}</span>
        <span class="dir orange">↑ up</span><span class="val orange">${fmtMbit(s.rates[1])}</span><span></span><span class="sec">${fmtBps(s.rates[1])}</span></div></div>
      <div class="card"><div class="title"><span>Today so far</span><span class="seg" style="padding:1px"><button class="${s.day_start_hour === 0 ? "on" : ""}" data-ds="0">Midnight</button><button class="${s.day_start_hour === 6 ? "on" : ""}" data-ds="6">6 AM</button></span></div>
        <div style="display:flex;justify-content:space-between;align-items:baseline"><span class="big">${fmtGB(sum, sum < 1e10 ? 1 : 0)} GB</span><span class="small">≈ ${fmtGB(t.projected, 0)} GB by ${endLbl}</span></div>
        <div class="bar"><i style="width:${projPct}%"></i>${t.avg_day ? `<b style="left:${avgPct}%"></b>` : ""}</div>
        <div class="small">${t.avg_day ? `average ${fmtGB(t.avg_day, 0)} GB a day` : "collecting first day of data"}</div></div>
      ${plans.map(planCard).join("")}`;
    this.q("#strip").querySelectorAll("[data-ds]").forEach((b) => b.onclick = () => { this.state.dayStart = Number(b.dataset.ds); this.renderSeg("#us-daystart", [["0", "Midnight"], ["6", "6 AM"]], String(this.state.dayStart), (v) => { this.state.dayStart = Number(v); this.refreshAll(); }); this.refreshAll(); });
    this.tickAge();
  }

  // ----------------------------------------------------------------- ranking lists
  rankHtml(title, rows, kind, unitLabel, fmt, maxOverride) {
    const max = maxOverride ?? Math.max(1e-9, ...rows.map((r) => Math.max(r.down, r.up)));
    rows = rows.filter((r) => (r.down + r.up) >= max * 0.005);
    const body = rows.length ? rows.map((r) => `
      <div class="row" data-f="${kind === "people" ? "person:" : "type:"}${r.key}" title="Show only ${r.key}"><span class="nm">${kind === "people" ? this.avatar(r.key) : `<span class="chip" style="height:24px;min-width:24px;padding:0 4px;cursor:default">${this.typeIcon(r.key)}</span>`}<span>${r.key}</span></span>
        <span class="bars"><i class="d" style="width:${Math.max(1, r.down / max * 100)}%"></i><i class="u" style="width:${Math.max(1, r.up / max * 100)}%"></i></span>
        <span class="nums"><span class="green">${fmt(r.down)}</span><br><span class="orange">${fmt(r.up)}</span></span></div>`).join("") : `<div class="small">Nothing used then.</div>`;
    return `<div class="hd"><b>${title}</b><span class="rank-when"></span></div>${body}<div class="unit">${unitLabel}</div>`;
  }

  // ----------------------------------------------------------------- bandwidth section
  renderBandwidth() {
    const d = this.data.bw; if (!d) return;
    const st = d.stats;
    this.q("#bw-sub").innerHTML = `<b>${d.label}</b> &nbsp; ${this.fmtDayTime(d.start)} – ${this.fmtDayTime(d.end)}`;
    const card = (title, cls, now, avg, peak) => `<div class="t ${cls}">${title}</div><div class="stat">
      <div><div class="lbl">Now</div><div class="v ${cls}">${fmtMbit(now)}</div><div class="s">${fmtBps(now)}</div></div>
      <div><div class="lbl">Average</div><div class="v">${fmtMbit(avg)}</div><div class="s">${fmtBps(avg)}</div></div>
      <div><div class="lbl">Peak</div><div class="v">${fmtMbit(peak[0])}</div><div class="s">${peak[1] ? this.fmtTime(peak[1]) : ""}</div></div></div>`;
    this.q("#bw-down").innerHTML = card("↓ Download", "green", st.now[0], st.avg[0], st.peak_down);
    this.q("#bw-up").innerHTML = card("↑ Upload", "orange", st.now[1], st.avg[1], st.peak_up);
    this.q("#bw-people").innerHTML = this.rankHtml("People", d.people_rank, "people", "Mbit/s", fmtMbitShort);
    this.q("#bw-types").innerHTML = this.rankHtml("Types", d.types_rank, "types", "Mbit/s", fmtMbitShort);
    this.setRankWhen("#bw", "average over the window");
    const age = this.data.summary ? Math.round(Date.now() / 1000 - this.data.summary.last_poll) : null;
    this.q("#bw-live").innerHTML = d.live ? `<span class="read-age">read ${ago(age)}</span><span class="dot"></span> Live` : `<span>Showing ${this.fmtDayTime(d.end)}</span><button id="bw-now">Now</button>`;
    if (!d.live) this.q("#bw-now").onclick = () => { this.state.bwEnd = null; this.loadBandwidth(); };
    this.drawArea("#bw-chart-down", d, 0, "Download", "var(--green)", "#16a34a");
    this.drawArea("#bw-chart-up", d, 1, "Upload", "var(--orange)", "#c2410c");
  }

  setRankWhen(section, text) { this.shadowRoot.querySelectorAll(`${section} .rank-when`).forEach((e) => e.textContent = text); }

  drawArea(sel, d, di, title, color, fill) {
    const el = this.q(sel); const W = Math.max(600, el.clientWidth || 1200), H = 150, L = 72, R = 72, T = 18, B = 22;
    const n = d.t.length; const sel_ = d.selected.map((p) => p[di]); const house = d.house.map((p) => p[di]);
    const filtered = this.state.filter !== "house";
    const max = Math.max(1e5, ...sel_, ...(filtered ? house : [])) * 1.08;
    const x = (i) => L + (i / Math.max(1, n - 1)) * (W - L - R);
    const y = (v) => T + (1 - v / max) * (H - T - B);
    const path = (arr) => arr.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const area = `${path(sel_)} L${x(n - 1).toFixed(1)},${y(0)} L${x(0)},${y(0)} Z`;
    const gridVals = [max / 1.08 / 2, max / 1.08]; const yl = (v) => { const m = v * 8 / 1e6; return (m >= 10 ? m.toFixed(0) : m >= 1 ? m.toFixed(1) : m.toFixed(2)) + " Mbit/s"; };
    const ticks = []; const span = d.end - d.start; const stepT = span <= 3600 ? 600 : span <= 6 * 3600 ? 3600 : span <= 86400 ? 3 * 3600 : 86400;
    for (let t = Math.ceil(d.start / stepT) * stepT; t < d.end; t += stepT) ticks.push(t);
    const tickLbl = (t) => span > 86400 ? this.fmtDate(t, { weekday: "short", month: undefined, day: undefined }) : this.fmtTime(t);
    const nowX = d.live ? null : null;
    const todayMark = (() => { const ds = this.data.summary?.today?.start; return ds && ds > d.start && ds < d.end ? x((ds - d.start) / d.step) : null; })();
    el.innerHTML = `<span class="lbl" style="color:${color}">${di === 0 ? "↓" : "↑"} ${title}</span>
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${H}px">
        ${gridVals.map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#23262b"/><text x="${L - 6}" y="${y(v) + 4}" font-size="10" fill="#8b8f96" text-anchor="end">${yl(v)}</text><text x="${W - R + 6}" y="${y(v) + 4}" font-size="10" fill="#8b8f96">${yl(v)}</text>`).join("")}
        ${filtered ? `<path d="${path(house)}" fill="none" stroke="#8b8f96" stroke-width="1" stroke-dasharray="3 3" opacity=".7"/>` : ""}
        <path d="${area}" fill="${fill}" opacity=".45"/><path d="${path(sel_)}" fill="none" stroke="${color}" stroke-width="1.5"/>
        ${todayMark != null ? `<line x1="${todayMark}" x2="${todayMark}" y1="${T}" y2="${H - B}" stroke="#555a62"/><rect x="${todayMark - 20}" y="${H - B + 4}" width="40" height="14" rx="7" fill="#2a2d33"/><text x="${todayMark}" y="${H - B + 14}" font-size="10" fill="#e8e9eb" text-anchor="middle">Today</text>` : ""}
        ${ticks.map((t) => `<text x="${x((t - d.start) / d.step)}" y="${H - 6}" font-size="10" fill="#8b8f96" text-anchor="middle">${tickLbl(t)}</text>`).join("")}
        <line id="cursor" x1="0" x2="0" y1="${T}" y2="${H - B}" stroke="#9aa0a8" opacity="0"/>
        <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" style="cursor:${d.live ? "crosshair" : "grab"}"/>
      </svg><div class="tip" style="display:none"></div>`;
    const svg = el.querySelector("svg"), tip = el.querySelector(".tip"), cursor = el.querySelector("#cursor");
    const idxAt = (ev) => { const r = svg.getBoundingClientRect(); const px = (ev.clientX - r.left) / r.width * W; return Math.max(0, Math.min(n - 1, Math.round((px - L) / (W - L - R) * (n - 1)))); };
    let dragStart = null;
    svg.onmousemove = (ev) => {
      if (dragStart != null) return;
      const i = idxAt(ev); const r = svg.getBoundingClientRect();
      cursor.setAttribute("x1", x(i)); cursor.setAttribute("x2", x(i)); cursor.setAttribute("opacity", "1");
      const t0 = d.t[i], t1 = t0 + d.step;
      tip.style.display = "block"; tip.style.left = `${(ev.clientX - r.left)}px`; tip.style.top = `${T - 2}px`;
      tip.innerHTML = `<b>${this.fmtDayTime(t0)} – ${this.fmtTime(t1)}</b> &nbsp; <span class="green">↓ ${fmtMbit(d.selected[i][0])} · ${fmtBps(d.selected[i][0])}</span> &nbsp; <span class="orange">↑ ${fmtMbit(d.selected[i][1])} · ${fmtBps(d.selected[i][1])}</span>${filtered ? `<br><span class="muted">whole house ↓ ${fmtMbit(d.house[i][0])} ↑ ${fmtMbit(d.house[i][1])}</span>` : ""}`;
      this.rerankBandwidth(i);
    };
    svg.onmouseleave = () => { tip.style.display = "none"; cursor.setAttribute("opacity", "0"); this.rerankBandwidth(null); dragStart = null; };
    svg.onmousedown = (ev) => { dragStart = { x: ev.clientX, end: d.end }; tip.style.display = "none"; };
    svg.onmouseup = (ev) => {
      if (dragStart == null) return;
      const r = svg.getBoundingClientRect(); const dx = (ev.clientX - dragStart.x) / r.width * (d.end - d.start);
      dragStart = null;
      if (Math.abs(dx) > d.step * 2) { const now = Math.floor(Date.now() / 1000); const newEnd = Math.min(now, Math.round(d.end - dx)); this.state.bwEnd = newEnd >= now - 60 ? null : newEnd; this.loadBandwidth(); }
    };
  }
  rerankBandwidth(i) {
    const d = this.data.bw; if (!d) return;
    const at = (groups, order) => i == null ? null : Object.entries(groups).map(([key, arr]) => ({ key, down: arr[i][0], up: arr[i][1] })).filter((r) => r.down || r.up).sort((a, b) => (b.down + b.up) - (a.down + a.up));
    const people = i == null ? d.people_rank : at(d.people), types = i == null ? d.types_rank : at(d.types);
    this.q("#bw-people").innerHTML = this.rankHtml("People", people, "people", "Mbit/s", fmtMbitShort);
    this.q("#bw-types").innerHTML = this.rankHtml("Types", types, "types", "Mbit/s", fmtMbitShort);
    this.setRankWhen("#bw", i == null ? "average over the window" : `at ${this.fmtDayTime(d.t[i])}`);
  }

  // ----------------------------------------------------------------- usage section
  renderUsage() {
    const d = this.data.usage; if (!d) return;
    const st = d.stats; const unit = d.unit === "day" ? "day" : "hour";
    this.q("#us-sub").innerHTML = `<b>${d.label}</b> &nbsp; ${this.fmtDayTime(d.start)} – ${d.cycle_end ? this.fmtDate(d.cycle_end - 1) : this.fmtDayTime(d.end)}`;
    const when = (ts) => ts == null ? "" : d.unit === "day" ? this.fmtDayName(ts) : `${this.fmtDayName(ts)}, ${this.fmtTime(ts)}`;
    const card = (title, cls, tot, avg, busy) => `<div class="t ${cls}">${title}</div><div class="stat">
      <div><div class="lbl">Total</div><div class="v ${cls}">${fmtBytes(tot)}</div></div>
      <div><div class="lbl">Average ${unit}</div><div class="v">${fmtBytes(avg)}</div></div>
      <div><div class="lbl">Busiest ${unit}</div><div class="v">${fmtBytes(busy[0])}</div><div class="s">${when(busy[1])}</div></div></div>`;
    this.q("#us-down").innerHTML = card("↓ Download", "green", st.total[0], st.avg[0], st.busiest_down);
    this.q("#us-up").innerHTML = card("↑ Upload", "orange", st.total[1], st.avg[1], st.busiest_up);
    this.rerankUsage(null);
    this.q("#us-live").innerHTML = `<span>${d.window === "plan" ? "The plan period" : "Up to now"}</span>`;
    this.drawBars("#us-chart", d);
  }
  rerankUsage(i) {
    const d = this.data.usage; if (!d) return;
    const at = (groups) => i == null ? null : Object.entries(groups).map(([key, arr]) => ({ key, down: arr[i][0], up: arr[i][1] })).filter((r) => r.down || r.up).sort((a, b) => (b.down + b.up) - (a.down + a.up));
    const people = i == null ? d.people_rank : at(d.people), types = i == null ? d.types_rank : at(d.types);
    this.q("#us-people").innerHTML = this.rankHtml("People", people, "people", "", fmtBytes);
    this.q("#us-types").innerHTML = this.rankHtml("Types", types, "types", "", fmtBytes);
    const lbl = i == null ? "in the window" : d.unit === "day" ? `on ${this.fmtDayName(d.t[i])}` : `in ${this.fmtDayName(d.t[i])}, ${this.fmtTime(d.t[i])} – ${this.fmtTime(d.t[i] + 3600)}`;
    this.setRankWhen("#us", lbl);
  }
  drawBars(sel, d) {
    const el = this.q(sel); const W = Math.max(600, el.clientWidth || 1200), H = 190, L = 72, R = 72, T = 14, B = 24;
    const n = d.t.length; const filtered = this.state.filter !== "house";
    const tot = (p) => p[0] + p[1];
    const max = Math.max(1e6, ...d.selected.map(tot), ...(filtered ? d.house.map(tot) : [])) * 1.05;
    const slot = (W - L - R) / Math.max(1, n); const bw = Math.max(2, slot * 0.72);
    const x = (i) => L + i * slot + (slot - bw) / 2; const y = (v) => T + (1 - v / max) * (H - T - B);
    const grid = [max / 1.05 / 3, max / 1.05 * 2 / 3, max / 1.05];
    const now = this.data.summary?.now || Date.now() / 1000;
    const lblEvery = d.unit === "day" ? (n > 16 ? 5 : 1) : (n > 12 ? 3 : 1);
    const tickLbl = (i) => d.unit === "day" ? this.fmtDate(d.t[i]) : this.fmtTime(d.t[i], { minute: undefined });
    const bars = d.t.map((t, i) => {
      const s = d.selected[i], h = d.house[i]; const future = t > now;
      const ghost = filtered ? `<rect x="${x(i)}" y="${y(tot(h))}" width="${bw}" height="${Math.max(0, y(0) - y(tot(h)))}" fill="#2b2e34"/>` : "";
      const dn = `<rect x="${x(i)}" y="${y(s[0])}" width="${bw}" height="${Math.max(0, y(0) - y(s[0]))}" fill="#22c55e"/>`;
      const up = `<rect x="${x(i)}" y="${y(s[0] + s[1])}" width="${bw}" height="${Math.max(0, y(s[0]) - y(s[0] + s[1]))}" fill="#f0781e"/>`;
      const isNow = (d.unit === "day" ? (t <= now && (i === n - 1 || d.t[i + 1] > now)) : (t <= now && t + 3600 > now));
      return `<g data-i="${i}">${ghost}${future ? "" : dn + up}${isNow ? `<rect x="${x(i) - 2}" y="${H - B + 3}" width="${bw + 4}" height="13" rx="6" fill="#2a2d33"/><text x="${x(i) + bw / 2}" y="${H - B + 13}" font-size="9" fill="#e8e9eb" text-anchor="middle">${d.unit === "day" ? "Today" : "Now"}</text>` : ""}</g>`;
    }).join("");
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${H}px">
      ${grid.map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#23262b"/><text x="${L - 6}" y="${y(v) + 4}" font-size="10" fill="#8b8f96" text-anchor="end">${fmtBytes(v, 0)}</text><text x="${W - R + 6}" y="${y(v) + 4}" font-size="10" fill="#8b8f96">${fmtBytes(v, 0)}</text>`).join("")}
      ${bars}
      ${d.t.map((t, i) => i % lblEvery === 0 && !(d.unit === "day" ? (t <= now && (i === n - 1 || d.t[i + 1] > now)) : (t <= now && t + 3600 > now)) ? `<text x="${x(i) + bw / 2}" y="${H - 6}" font-size="10" fill="#8b8f96" text-anchor="middle">${tickLbl(i)}</text>` : "").join("")}
      <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/>
    </svg><div class="tip" style="display:none"></div>`;
    const svg = el.querySelector("svg"), tip = el.querySelector(".tip");
    svg.onmousemove = (ev) => {
      const r = svg.getBoundingClientRect(); const px = (ev.clientX - r.left) / r.width * W; const i = Math.max(0, Math.min(n - 1, Math.floor((px - L) / slot)));
      if (d.t[i] > now) { tip.style.display = "none"; return; }
      const s = d.selected[i], h = d.house[i];
      const range = d.unit === "day" ? this.fmtDayName(d.t[i]) : `${this.fmtDayName(d.t[i])}, ${this.fmtTime(d.t[i])} – ${this.fmtTime(d.t[i] + 3600)}`;
      tip.style.display = "block"; tip.style.left = `${ev.clientX - r.left}px`; tip.style.top = `${T + 8}px`;
      tip.innerHTML = `<b>${range}</b> &nbsp; <span class="green">↓ ${fmtBytes(s[0])}</span> &nbsp; <span class="orange">↑ ${fmtBytes(s[1])}</span>${filtered ? ` &nbsp; <span class="muted">whole house ↓ ${fmtBytes(h[0])} ↑ ${fmtBytes(h[1])}</span>` : ""}`;
      this.rerankUsage(i);
    };
    svg.onmouseleave = () => { tip.style.display = "none"; this.rerankUsage(null); };
  }

  // ----------------------------------------------------------------- table
  renderTable() {
    const d = this.data.table; if (!d) return;
    const s = this.state; const [sortKey, dir] = s.tbSort;
    const val = (r) => sortKey === "label" ? r.label.toLowerCase() : sortKey === "now" ? r.now[0] + r.now[1] : sortKey === "today" ? r.today[0] + r.today[1] : sortKey === "share" ? r.share : r.window[0] + r.window[1];
    const rows = [...d.rows].sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * dir);
    const maxSpark = Math.max(1, ...d.rows.flatMap((r) => r.spark.map((p) => p[0] + p[1])));
    const unit = d.unit === "day" ? "Daily" : "Hourly";
    const rangeLbl = d.t.length ? `${this.fmtDayName(d.t[0])}${d.unit === "day" ? "" : ", " + this.fmtTime(d.t[0])} – ${d.unit === "day" ? "today" : "now"}` : "";
    const th = (k, l, cls = "") => `<th class="${cls}" data-k="${k}">${l} ${sortKey === k ? (dir < 0 ? "↓" : "↑") : '<span class="muted">⇅</span>'}</th>`;
    const winLbl = { "6h": "6 h", "24h": "24 h", "7d": "7 days", "14d": "14 days", "30d": "30 days", "plan": "Plan" }[s.tbWindow];
    const spark = (arr, m) => { const w = 150, h = 22, sw = Math.max(1.5, w / arr.length - 1); return `<svg width="${w}" height="${h}">${arr.map((p, i) => { const tot = p[0] + p[1]; if (!tot) return `<rect x="${i * w / arr.length}" y="${h - 1}" width="${sw}" height="1" fill="#2b2e34"/>`; const hd = p[0] / m * h, hu = p[1] / m * h; return `<rect x="${i * w / arr.length}" y="${h - hd}" width="${sw}" height="${hd}" fill="#22c55e"/><rect x="${i * w / arr.length}" y="${h - hd - hu}" width="${sw}" height="${hu}" fill="#f0781e"/>`; }).join("")}</svg>`; };
    const rowHtml = (r, child) => {
      const canExpand = !!r.children; const open = s.expandAll || s.expanded.has(r.key);
      const icon = r.kind === "owner" ? this.avatar(r.label) : r.kind === "type" ? `<span class="chip" style="height:26px;min-width:26px;padding:0 5px;cursor:default">${this.typeIcon(r.label)}</span>` : `<span class="chip" style="height:26px;min-width:26px;padding:0 5px;cursor:default;opacity:${r.online ? 1 : .5}">${this.typeIcon(r.type)}</span>`;
      return `<tr class="${child ? "child" : ""}" data-key="${r.key}" ${r.kind === "device" ? `data-mac="${r.key}"` : ""} style="${canExpand ? "cursor:pointer" : ""}">
        <td><div class="tw">${canExpand ? `<span class="caret">${open ? "⌄" : "›"}</span>` : ""}${icon}<div><div class="nm">${r.kind === "device" ? `<span class="conn ${r.online ? "on" : ""}" title="${r.online ? "Connected" : "Disconnected"}"></span>` : ""}${r.label}</div><div class="sb">${r.kind === "device" ? `<span class="${r.online ? "green" : ""}">${this.connText(r)}</span> · ` : ""}${r.sub || ""}</div></div></div></td>
        <td class="r nowcell"><span class="green">${fmtBps(r.now[0])}</span><br><span class="orange">${fmtBps(r.now[1])}</span></td>
        <td class="r">${fmtBytes(r.today[0] + r.today[1])}</td>
        <td class="r"><b>${fmtBytes(r.window[0] + r.window[1])}</b></td>
        <td class="spark">${spark(r.spark, maxSpark)}</td>
        <td class="r muted">${Math.round(r.share * 100)}%</td>
        <td class="r" style="width:30px">${r.kind === "device" ? `<button class="more" title="Assign, rename, type…" data-more="${r.key}">⋯</button>` : ""}</td></tr>` + (canExpand && open ? r.children.map((c) => rowHtml(c, true)).join("") : "");
    };
    this.q("#tb-table").innerHTML = `<table><thead><tr>${th("label", s.tbBy === "person" ? "Person" : s.tbBy === "type" ? "Type" : "Device")}${th("now", "Now ↓ down / ↑ up", "r")}${th("today", "Today", "r")}${th("window", winLbl, "r")}<th>${unit} <span class="muted" style="font-weight:400">· ${rangeLbl}</span></th>${th("share", "Share", "r")}<th></th></tr></thead><tbody>${rows.map((r) => rowHtml(r, false)).join("")}</tbody></table>`;
    this.q("#tb-table").querySelectorAll("th[data-k]").forEach((h) => h.onclick = () => { const k = h.dataset.k; s.tbSort = s.tbSort[0] === k ? [k, -s.tbSort[1]] : [k, k === "label" ? 1 : -1]; this.renderTable(); });
    this.q("#tb-table").querySelectorAll("tr[data-key]:not([data-mac])").forEach((tr) => tr.onclick = () => { const k = tr.dataset.key; const r = d.rows.find((x) => x.key === k); if (!r || !r.children) return; if (s.expanded.has(k)) s.expanded.delete(k); else s.expanded.add(k); if (s.expandAll) { s.expandAll = false; d.rows.forEach((x) => x.key !== k && s.expanded.add(x.key)); } this.renderTable(); });
    this.q("#tb-table").querySelectorAll("tr[data-mac]").forEach((tr) => {
      tr.oncontextmenu = (e) => { e.preventDefault(); this.openMenu(e.clientX, e.clientY, tr.dataset.mac); };
      tr.onclick = (e) => { if (e.target.closest("[data-more]")) return; this.openMenu(e.clientX, e.clientY, tr.dataset.mac); };
    });
    this.q("#tb-table").querySelectorAll("[data-more]").forEach((b) => b.onclick = (e) => { e.stopPropagation(); const r = b.getBoundingClientRect(); this.openMenu(r.left - 220, r.bottom + 4, b.dataset.more); });
    this.q("#tb-expand").textContent = s.expandAll ? "Collapse all" : "Expand all";
    this.q("#tb-expand").style.display = s.tbBy === "device" ? "none" : "";
  }
}

if (!customElements.get("omada-traffic-panel")) customElements.define("omada-traffic-panel", OmadaTrafficPanel);
