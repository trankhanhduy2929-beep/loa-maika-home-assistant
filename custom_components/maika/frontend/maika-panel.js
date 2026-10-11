/* MAIKA Speaker management panel for Home Assistant. */
const API = "maika/panel";
const HERO_IMAGE = "https://smarthomekit.vn/wp-content/uploads/2021/12/olli-maika-2.jpg";

const PLAN_LABELS = {
  trial_1d: "Trải nghiệm 1 ngày",
  month_1: "Gói 1 tháng",
  month_6: "Gói 6 tháng",
  lifetime: "Vĩnh viễn",
};

const AUDIO_SOURCE_LABELS = {
  disabled: "Tắt",
  bundled: "MP3 MAIKA tích hợp",
  custom: "URL MP3 tuỳ chỉnh",
};

const AUDIO_TIMING_LABELS = {
  priority: "Ưu tiên: che giọng loa",
  after_success: "Chỉ phát sau khi thành công",
};

const STATUS_LABELS = {
  active: "Đang hoạt động",
  grace: "Trong thời gian gia hạn",
  expired: "Đã hết hạn",
  pending: "Chờ duyệt",
  rejected: "Bị từ chối",
  revoked: "Đã thu hồi",
  deactivated: "Đã tắt",
  unavailable: "Không đọc được",
};

const OPTION_KEYS = {
  scanInterval: "scan_interval",
  cloudCast: "enable_experimental_cloud_cast",
  voiceSensor: "enable_voice_command_sensor",
  rules: "voice_command_rules",
  audioSource: "voice_success_audio_source",
  audioTiming: "voice_success_audio_timing",
  audioUrl: "voice_success_audio_url",
  mediaPlayer: "voice_success_media_player_entity_id",
};

const UNKNOWN = new Set(["unknown", "unavailable", "none", "", "None", "null"]);

function fmtTime(value) {
  if (!value) return "—";
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("vi-VN", {dateStyle: "short", timeStyle: "short"});
}

function fmtDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString("vi-VN");
}

function planLabel(plan) {
  return PLAN_LABELS[plan] || plan || "Chưa rõ";
}

function h(tag, props, children) {
  const node = document.createElement(tag);
  if (props) {
    for (const [key, value] of Object.entries(props)) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "html") node.innerHTML = value;
      else if (key.startsWith("on") && typeof value === "function") {
        node.addEventListener(key.slice(2).toLowerCase(), value);
      } else if (key === "dataset") {
        Object.assign(node.dataset, value);
      } else if (value === true) node.setAttribute(key, "");
      else node.setAttribute(key, value);
    }
  }
  if (children) {
    for (const child of [].concat(children)) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
  }
  return node;
}

function svgIcon(path) {
  const wrap = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  wrap.setAttribute("viewBox", "0 0 24 24");
  wrap.setAttribute("aria-hidden", "true");
  const node = document.createElementNS("http://www.w3.org/2000/svg", "path");
  node.setAttribute("d", path);
  wrap.append(node);
  return wrap;
}

const ICONS = {
  online: "M12 21a9 9 0 0 0 9-9 9 9 0 0 0-9-9 9 9 0 0 0-9 9 9 9 0 0 0 9 9m0-3a6 6 0 0 1-6-6 6 6 0 0 1 6-6 6 6 0 0 1 6 6 6 6 0 0 1-6 6m0-3a3 3 0 0 0 3-3 3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3",
  wifi: "M12 21 8.5 16.5A5 5 0 0 1 12 15a5 5 0 0 1 3.5 1.5zM4.9 11.9 2 9a14 14 0 0 1 20 0l-2.9 2.9a10 10 0 0 0-14.2 0m3.5 3.5-2.2-2.2a7 7 0 0 1 7.8-1.5 7 7 0 0 1 2.4 1.5l-2.2 2.2a4 4 0 0 0-5.8 0",
  mic: "M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3m7 9a7 7 0 0 1-6 6.92V22h-2v-4.08A7 7 0 0 1 5 11h2a5 5 0 0 0 10 0z",
  micOff: "M19 11c0 1.19-.34 2.3-.93 3.24L16.4 12.57c.06-.18.1-.37.1-.57h2.5M12 2a3 3 0 0 1 3 3v5.18l-3-3V5a1 1 0 0 0-2 0v.18L8.07 3.25A3 3 0 0 1 12 2 M4.27 3 3 4.27l6.01 6.01V11a3 3 0 0 0 3 3h.73l1.24 1.24A5 5 0 0 1 7 11H5a7 7 0 0 0 6 6.92V22h2v-4.08a6.96 6.96 0 0 0 3.1-1.32L19.73 20 21 18.73z",
  volume: "M14 3.2v17.6l-5-4H4V7.2h5zM17 8.5a5 5 0 0 1 0 7l-1.4-1.4a3 3 0 0 0 0-4.2z",
  play: "M8 5.1v13.8L19 12z",
  pause: "M7 5h4v14H7zm6 0h4v14h-4z",
  prev: "M6 6h2v12H6zm12 0v12l-9-6z",
  next: "M16 6h2v12h-2zM6 18V6l9 6z",
  restart: "M12 5V2L8 6l4 4V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z",
  refresh: "M17.7 6.3A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.8-4.3L13 11h7V4z",
  chip: "M9 2v2H7a3 3 0 0 0-3 3v2H2v2h2v2H2v2h2v2a3 3 0 0 0 3 3h2v2h2v-2h2v2h2v-2h2a3 3 0 0 0 3-3v-2h2v-2h-2v-2h2V9h-2V7a3 3 0 0 0-3-3h-2V2h-2v2h-2V2zm0 6h6v8H9z",
  shield: "M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5zm0 5 1.6 3.3 3.4.5-2.5 2.4.6 3.5-3.1-1.7-3.1 1.7.6-3.5L7 10.8l3.4-.5z",
  key: "M7 14a5 5 0 1 1 5-5c0 .7-.2 1.3-.4 1.9l7.5 7.5-1.6 1.6-1.5-1.5-1.5 1.5-1.5-1.5-1.5 1.5-2.6-2.6A5 5 0 0 1 7 14m0-2a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3",
  tune: "M3 17v2h6v-2zm0-6v2h10v-2zm0-6v2h14V5zm12 12h6v-2h-4v-8h4V5h-6zm-2-8h2v-2h-2z",
  speaker: "M12 3a6 6 0 0 0-6 6v5a6 6 0 0 0 12 0V9a6 6 0 0 0-6-6m0 15a9 9 0 0 1-9-9H1a11 11 0 0 0 10 10.9V22h2v-2.1A11 11 0 0 0 23 9h-2a9 9 0 0 1-9 9",
  home: "M12 3 2 12h3v8h6v-5h2v5h6v-8h3z",
  clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20m1 5h-2v6l5 3 1-1.7-4-2.3z",
  cloud: "M6 18a4 4 0 0 1 0-8 6 6 0 0 1 11.6-1.5A4.5 4.5 0 0 1 18 18z",
  info: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20m1 15h-2v-6h2zm0-8h-2V7h2z",
  cast: "M2 17v3h3a3 3 0 0 0-3-3m0-4v2a5 5 0 0 1 5 5h2a7 7 0 0 0-7-7m0-4v2a9 9 0 0 1 9 9h2A11 11 0 0 0 2 9m19-6H9a2 2 0 0 0-2 2v3h2V5h12v14h-6v2h6a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2",
  phone: "M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.2 11 11 0 0 0 3.6.6 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11 11 0 0 0 .6 3.6 1 1 0 0 1-.3 1z",
  heart: "M12 21s-8-4.9-8-10.4A4.6 4.6 0 0 1 12 7a4.6 4.6 0 0 1 8 3.6C20 16.1 12 21 12 21",
  pencil: "M3 17.3V21h3.8L18 9.8 14.2 6zM20.7 7.1a1 1 0 0 0 0-1.4l-2.4-2.4a1 1 0 0 0-1.4 0L15.1 5 19 8.9z",
  power: "M13 3h-2v10h2zm4.5 2.1-1.4 1.4a7 7 0 1 1-8.2 0L6.5 5.1a9 9 0 1 0 11 0",
  lang: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20m6.9 6h-2.6a15 15 0 0 0-1.4-3.4A8 8 0 0 1 18.9 8M12 4c.8 1 1.5 2.4 1.9 4h-3.8C10.5 6.4 11.2 5 12 4M4.3 14a8 8 0 0 1 0-4h3a17 17 0 0 0 0 4zm.8 2h2.6a15 15 0 0 0 1.4 3.4A8 8 0 0 1 5.1 16m2.6-8H5.1a8 8 0 0 1 4-3.4A15 15 0 0 0 7.7 8M12 20c-.8-1-1.5-2.4-1.9-4h3.8c-.4 1.6-1.1 3-1.9 4m2.3-6H9.7a15 15 0 0 1 0-4h4.6a15 15 0 0 1 0 4m.6 5.4a15 15 0 0 0 1.4-3.4h2.6a8 8 0 0 1-4 3.4m1.8-5.4a17 17 0 0 0 0-4h3a8 8 0 0 1 0 4z",
  serial: "M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z",
  calendar: "M7 2v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2zm12 8v10H5V10z",
  update: "M12 4V1L8 5l4 4V6a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8",
};

class MaikaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._hass = null;
    this._snapshot = null;
    this._activeIndex = 0;
    this._deviceSerial = "";
    this._busy = false;
    this._message = null;
    this._draft = {};
    this._loaded = false;
    this._lastSignature = "";
    this._onClick = this._onClick.bind(this);
    this._onInput = this._onInput.bind(this);
    this._onChange = this._onChange.bind(this);
    this._onSubmit = this._onSubmit.bind(this);
  }

  set hass(value) {
    this._hass = value;
    if (!this._loaded) {
      this._loaded = true;
      this._root();
      this._load();
    } else if (this._snapshot) {
      this._maybeUpdate();
    }
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    this._narrow = value;
    if (this._snapshot) this._render();
  }

  set panel(value) {
    this._panel = value;
    if (value && value.config && Number.isInteger(value.config.entry_index)) {
      this._activeIndex = value.config.entry_index;
    }
  }

  _style() {
    const style = document.createElement("style");
    style.textContent = `
      :host { display: block; min-height: 100vh; background: var(--primary-background-color, #060d18); color: var(--primary-text-color, #eaf4ff); }
      * { box-sizing: border-box; }
      .stage {
        max-width: 1480px; margin: 0 auto; padding: 16px 14px 80px;
        display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
        grid-auto-flow: dense; grid-auto-rows: min-content;
        gap: 14px; align-content: start;
      }
      .span2 { grid-column: span 2; }
      .span3 { grid-column: span 3; }
      @media (max-width: 1240px) { .stage { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
      @media (max-width: 940px) { .stage { grid-template-columns: repeat(2, minmax(0, 1fr)); } .span3 { grid-column: span 2; } }
      @media (max-width: 640px) { .stage { grid-template-columns: 1fr; gap: 12px; padding: 12px 10px 90px; } .span2, .span3 { grid-column: span 1; } }

      .card {
        --accent: #31d8c4; --accent2: #8f7dff;
        position: relative; background: var(--card-background-color, #101a2b);
        border: 1px solid rgba(120, 190, 255, .14); border-radius: 26px; padding: 16px;
        box-shadow: 0 12px 32px rgba(3, 10, 20, .3);
        animation: rise .44s cubic-bezier(.22, .9, .3, 1) both; animation-delay: var(--d, 0ms);
      }
      .card:hover { box-shadow: 0 16px 40px rgba(3, 10, 20, .38); }
      .titlecard { background: none; border: none; box-shadow: none; padding: 2px 4px 0; }
      .titlecard h2 { margin: 0; font-size: 1.02rem; font-weight: 700; letter-spacing: -.01em; }
      .titlecard p { margin: 3px 0 0; font-size: .8rem; color: var(--secondary-text-color, #8fa8bf); }
      .sec-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
      .sec-head .ico { width: 34px; height: 34px; border-radius: 12px; display: grid; place-items: center; background: rgba(49, 216, 196, .14); color: #4ee8d4; flex: none; }
      .sec-head .ico svg { width: 18px; height: 18px; fill: currentColor; }
      .sec-head h3 { margin: 0; font-size: .95rem; font-weight: 650; }
      .sec-head span { display: block; font-size: .76rem; color: var(--secondary-text-color, #8fa8bf); }

      .hero { padding: 0; overflow: hidden; }
      .hero-media { position: relative; aspect-ratio: 16 / 9; min-height: 200px; background: linear-gradient(140deg, #0d2438, #071322); }
      .hero-media img { position: relative; z-index: 1; width: 100%; height: 100%; object-fit: cover; display: block; animation: slowzoom 14s ease-in-out infinite alternate; }
      .hero-art { position: absolute; inset: 0; display: grid; place-items: center; background: linear-gradient(140deg, #0d2438, #071322); }
      .hero-art svg { width: 40%; max-width: 200px; fill: rgba(120, 220, 255, .28); animation: pulse 4s ease-in-out infinite; }
      .hero-media::after { content: ""; position: absolute; inset: 0; z-index: 2; background: linear-gradient(180deg, rgba(4, 12, 22, .05) 20%, rgba(4, 12, 22, .86) 100%); }
      .hero-media--fallback { display: grid; place-items: center; }
      .hero-media--fallback svg { width: 42%; max-width: 220px; fill: rgba(120, 220, 255, .35); }
      .hero-copy { position: absolute; inset: auto 0 0 0; padding: 18px; z-index: 3; display: grid; gap: 4px; }
      .hero-copy h1 { margin: 0; font-size: 1.4rem; letter-spacing: -.02em; }
      .hero-copy p { margin: 0; font-size: .84rem; color: #b9cde0; display: flex; align-items: center; gap: 8px; }
      .hero-badges { position: absolute; top: 14px; right: 14px; z-index: 3; display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
      .dot { width: 9px; height: 9px; border-radius: 50%; background: #49e6a4; box-shadow: 0 0 0 0 rgba(73, 230, 164, .55); animation: pulse 2.2s infinite; }
      .dot--off { background: #ff7c8a; animation: none; }
      .hero-body { padding: 14px 16px 16px; display: grid; gap: 12px; }

      .chips { display: flex; flex-wrap: wrap; gap: 8px; }
      .chip { display: inline-flex; align-items: center; gap: 7px; padding: 7px 12px; border-radius: 999px;
        background: rgba(255, 255, 255, .06); border: 1px solid rgba(255, 255, 255, .05); font-size: .8rem; font-weight: 600; }
      .chip svg { width: 15px; height: 15px; fill: currentColor; }
      .chip--ok { color: #5ff0b4; background: rgba(73, 230, 164, .14); }
      .chip--bad { color: #ff98a6; background: rgba(255, 124, 138, .14); }
      .chip--blue { color: #74c8ff; background: rgba(92, 192, 255, .14); }
      .chip--muted { color: var(--secondary-text-color, #8fa8bf); }

      .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 10px; }
      .tile { display: flex; flex-direction: column; gap: 7px; padding: 12px; border-radius: 20px;
        background: rgba(255, 255, 255, .04); border: 1px solid rgba(255, 255, 255, .05);
        transition: transform .18s ease, background .18s ease; }
      .tile:hover { transform: translateY(-2px); background: rgba(255, 255, 255, .075); }
      .tile .ico { width: 32px; height: 32px; border-radius: 11px; display: grid; place-items: center; background: rgba(255, 255, 255, .07); }
      .tile .ico svg { width: 17px; height: 17px; fill: currentColor; }
      .tile .k { font-size: .72rem; letter-spacing: .05em; text-transform: uppercase; color: var(--secondary-text-color, #8fa8bf); }
      .tile .v { font-size: .98rem; font-weight: 650; line-height: 1.25; word-break: break-word; }
      .c-ok { color: #5ff0b4; } .c-bad { color: #ff98a6; } .c-blue { color: #74c8ff; }
      .c-purple { color: #b5a8ff; } .c-amber { color: #ffc775; } .c-pink { color: #ff9ec4; } .c-cyan { color: #6fe6f0; }
      .sec-head .ico.c-ok, .tile .ico.c-ok { background: rgba(73, 230, 164, .15); color: #5ff0b4; }
      .sec-head .ico.c-bad, .tile .ico.c-bad { background: rgba(255, 124, 138, .15); color: #ff98a6; }
      .sec-head .ico.c-blue, .tile .ico.c-blue { background: rgba(92, 192, 255, .15); color: #74c8ff; }
      .sec-head .ico.c-purple, .tile .ico.c-purple { background: rgba(143, 125, 255, .15); color: #b5a8ff; }
      .sec-head .ico.c-amber, .tile .ico.c-amber { background: rgba(255, 199, 117, .15); color: #ffc775; }
      .sec-head .ico.c-pink, .tile .ico.c-pink { background: rgba(255, 158, 196, .15); color: #ff9ec4; }
      .sec-head .ico.c-cyan, .tile .ico.c-cyan { background: rgba(111, 230, 240, .15); color: #6fe6f0; }

      .rows { display: grid; gap: 8px; }
      .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 13px; border-radius: 16px; background: rgba(255, 255, 255, .035); }
      .row .lbl { font-size: .84rem; color: var(--secondary-text-color, #8fa8bf); }
      .row .val { font-weight: 620; font-size: .92rem; text-align: right; }

      .media { display: grid; gap: 14px; }
      .media-now { display: flex; align-items: center; gap: 12px; padding: 13px; border-radius: 20px;
        background: linear-gradient(135deg, rgba(49, 216, 196, .14), rgba(143, 125, 255, .12)); }
      .media-now .ico { width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; background: rgba(255, 255, 255, .1); }
      .media-now .ico svg { width: 22px; height: 22px; fill: #6ff0e0; }
      .media-now .t { font-weight: 680; }
      .media-now .s { font-size: .8rem; color: var(--secondary-text-color, #8fa8bf); }
      .transport { display: flex; gap: 10px; justify-content: center; align-items: center; }
      .tbtn { width: 46px; height: 46px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, .08);
        background: rgba(255, 255, 255, .06); color: inherit; display: grid; place-items: center; cursor: pointer; transition: transform .15s, background .15s; }
      .tbtn:hover { transform: translateY(-2px); background: rgba(255, 255, 255, .12); }
      .tbtn svg { width: 20px; height: 20px; fill: currentColor; }
      .tbtn--main { width: 58px; height: 58px; border-radius: 20px; background: linear-gradient(135deg, #31d8c4, #6ff0a8); color: #04231f; border: none; }
      .tbtn--main svg { width: 26px; height: 26px; }
      .tbtn--on { background: rgba(255, 124, 138, .2); color: #ff9ead; }

      .slider { display: flex; align-items: center; gap: 12px; }
      .slider .ico svg { width: 18px; height: 18px; fill: #74c8ff; }
      input[type="range"] { -webkit-appearance: none; appearance: none; width: 100%; height: 6px; border-radius: 999px;
        background: linear-gradient(90deg, #31d8c4, #8f7dff); outline: none; padding: 0; border: none; }
      input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%;
        background: #eaf4ff; border: 3px solid #31d8c4; cursor: pointer; }
      input[type="range"]::-moz-range-thumb { width: 16px; height: 16px; border-radius: 50%; background: #eaf4ff; border: 3px solid #31d8c4; cursor: pointer; }

      .field { display: grid; gap: 6px; }
      .field > label { font-size: .78rem; font-weight: 600; color: var(--secondary-text-color, #8fa8bf); }
      input, select, textarea { font: inherit; font-size: .9rem; color: inherit; width: 100%;
        background: rgba(255, 255, 255, .05); border: 1px solid rgba(255, 255, 255, .09); border-radius: 14px; padding: 10px 12px; outline: none; }
      textarea { min-height: 120px; resize: vertical; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .82rem; }
      input:focus, select:focus, textarea:focus { border-color: rgba(49, 216, 196, .6); box-shadow: 0 0 0 3px rgba(49, 216, 196, .14); }
      select option { background: #0d1728; color: #eaf4ff; }

      .sw { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 13px; border-radius: 16px; background: rgba(255, 255, 255, .035); }
      .sw .txt { font-size: .88rem; font-weight: 600; }
      .sw .sub { font-size: .76rem; color: var(--secondary-text-color, #8fa8bf); }
      input[type="checkbox"] { -webkit-appearance: none; appearance: none; width: 48px; height: 27px; border-radius: 999px;
        background: rgba(255, 255, 255, .14); position: relative; cursor: pointer; flex: none; transition: background .2s; border: none; padding: 0; }
      input[type="checkbox"]::after { content: ""; position: absolute; top: 3px; left: 3px; width: 21px; height: 21px; border-radius: 50%;
        background: #eaf4ff; transition: transform .2s; }
      input[type="checkbox"]:checked { background: linear-gradient(135deg, #31d8c4, #6ff0a8); }
      input[type="checkbox"]:checked::after { transform: translateX(21px); }

      .btn { border: none; border-radius: 16px; padding: 11px 16px; font: inherit; font-size: .88rem; font-weight: 650; cursor: pointer;
        background: rgba(255, 255, 255, .08); color: inherit; display: inline-flex; align-items: center; gap: 8px; justify-content: center;
        transition: transform .15s, filter .15s, background .15s; }
      .btn:hover:not(:disabled) { transform: translateY(-1px); }
      .btn:disabled { opacity: .55; cursor: not-allowed; }
      .btn svg { width: 17px; height: 17px; fill: currentColor; }
      .btn--primary { background: linear-gradient(135deg, #31d8c4, #6ff0a8); color: #04231f; }
      .btn--ghost { background: rgba(255, 255, 255, .06); border: 1px solid rgba(255, 255, 255, .08); }
      .btn--danger { background: rgba(255, 124, 138, .16); color: #ff9ead; }
      .btn-row { display: flex; flex-wrap: wrap; gap: 10px; }
      .btn-row .btn { flex: 1 1 auto; }

      .badge { display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; font-size: .74rem;
        font-weight: 700; letter-spacing: .03em; background: rgba(255, 255, 255, .07); backdrop-filter: blur(6px); }
      .badge--ok { background: rgba(73, 230, 164, .18); color: #6df0b4; }
      .badge--warn { background: rgba(255, 199, 117, .18); color: #ffc775; }
      .badge--bad { background: rgba(255, 124, 138, .18); color: #ff9ead; }
      .badge--info { background: rgba(143, 125, 255, .2); color: #c3b8ff; }

      .msg { padding: 12px 14px; border-radius: 18px; font-size: .86rem; font-weight: 600; }
      .msg--ok { background: rgba(73, 230, 164, .14); color: #7df3bd; }
      .msg--err { background: rgba(255, 124, 138, .14); color: #ff9ead; }
      .hint { font-size: .78rem; color: var(--secondary-text-color, #8fa8bf); margin: 0; }
      .loading { display: grid; place-items: center; gap: 14px; padding: 80px 20px; color: var(--secondary-text-color, #8fa8bf); }
      .spinner { width: 34px; height: 34px; border-radius: 50%; border: 3px solid rgba(255, 255, 255, .12); border-top-color: #31d8c4; animation: spin .9s linear infinite; }

      @keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
      @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(73, 230, 164, .5); } 70% { box-shadow: 0 0 0 10px rgba(73, 230, 164, 0); } 100% { box-shadow: 0 0 0 0 rgba(73, 230, 164, 0); } }
      @keyframes slowzoom { from { transform: scale(1); } to { transform: scale(1.06); } }
      @keyframes spin { to { transform: rotate(360deg); } }
      @media (prefers-reduced-motion: reduce) {
        .card, .hero-media img, .dot, .spinner { animation: none !important; }
      }
    `;
    return style;
  }

  _root() {
    this.shadowRoot.innerHTML = "";
    this.shadowRoot.append(this._style());
    this._stage = h("div", {class: "stage"});
    this.shadowRoot.append(this._stage);
    this.shadowRoot.addEventListener("click", this._onClick);
    this.shadowRoot.addEventListener("input", this._onInput);
    this.shadowRoot.addEventListener("change", this._onChange);
    this.shadowRoot.addEventListener("submit", this._onSubmit);
    this._render();
  }

  _entry() {
    const entries = this._snapshot?.entries || [];
    if (!entries.length) return null;
    const index = Math.min(Math.max(this._activeIndex, 0), entries.length - 1);
    return entries[index];
  }

  _serials() {
    const entry = this._entry();
    const scoped = Object.keys(entry?.device_entities || {});
    if (scoped.length) {
      return scoped.sort((a, b) => this._deviceLabel(a).localeCompare(this._deviceLabel(b), "vi"));
    }
    return Object.keys(entry?.devices || {});
  }

  _activeSerial() {
    const serials = this._serials();
    if (!serials.length) return "";
    return serials.includes(this._deviceSerial) ? this._deviceSerial : serials[0];
  }

  _activeDevice() {
    return this._entry()?.devices?.[this._activeSerial()] || {};
  }

  _deviceLabel(serial) {
    const device = this._entry()?.devices?.[serial] || {};
    const name = String(device.name || device.calling_name || "").trim();
    return name || `Loa ${String(serial).slice(-4)}`;
  }

  _entities(domain) {
    const entry = this._entry();
    const scoped = entry?.device_entities?.[this._activeSerial()]?.[domain];
    if (scoped && scoped.length) return scoped;
    return entry?.entities?.[domain] || [];
  }

  _entity(domain, key) {
    const list = this._entities(domain);
    if (!key) return list[0] || "";
    const keys = this._entry()?.entity_keys || {};
    const serial = String(this._activeSerial() || "");
    const normalize = (value) => {
      const text = String(value || "");
      return serial && text.startsWith(`${serial}_`) ? text.slice(serial.length + 1) : text;
    };
    const exact = list.find((id) => normalize(keys[id]) === key);
    if (exact) return exact;
    const flat = String(key).replace(/_/g, "");
    return (
      list.find((id) => {
        const tail = id.slice(id.indexOf(".") + 1);
        return tail.includes(key) || tail.replace(/_/g, "").includes(flat);
      }) || ""
    );
  }

  _state(entityId) {
    if (!entityId) return null;
    return this._hass?.states?.[entityId] || null;
  }

  _value(entityId, fallback = "—") {
    const state = this._state(entityId);
    if (!state) return fallback;
    const raw = String(state.state);
    return UNKNOWN.has(raw) ? fallback : raw;
  }

  _isOn(entityId) {
    const state = this._state(entityId);
    return state ? state.state === "on" : false;
  }

  _icon(name, color) {
    const wrap = h("div", {class: "ico"});
    if (color) wrap.classList.add(color);
    wrap.append(svgIcon(ICONS[name] || ICONS.info));
    return wrap;
  }

  _tile({icon, color, label, value, tone}) {
    return h("div", {class: "tile"}, [
      this._icon(icon, color),
      h("div", {class: "k", text: label}),
      h("div", {class: ["v", tone].filter(Boolean).join(" "), text: value}),
    ]);
  }

  _row(label, value, tone) {
    return h("div", {class: "row"}, [
      h("span", {class: "lbl", text: label}),
      h("span", {class: ["val", tone].filter(Boolean).join(" "), text: value}),
    ]);
  }

  _card(cls, children, delay) {
    const node = h("div", {class: ["card", cls].filter(Boolean).join(" ")});
    if (delay) node.style.setProperty("--d", `${delay}ms`);
    for (const child of [].concat(children)) {
      if (child) node.append(child);
    }
    return node;
  }

  _sectionHead(icon, title, subtitle, color) {
    const head = h("div", {class: "sec-head"}, [
      h("div", {class: ["ico", color].filter(Boolean).join(" ")}, [svgIcon(ICONS[icon] || ICONS.info)]),
      h("div", {}, [h("h3", {text: title}), subtitle ? h("span", {text: subtitle}) : null]),
    ]);
    return head;
  }

  _licenseBadge(license) {
    const status = license?.status || "unavailable";
    const tone = ["active"].includes(status) ? "ok" : ["grace", "pending"].includes(status) ? "warn" : "bad";
    return h("span", {class: `badge badge--${tone}`, text: STATUS_LABELS[status] || status});
  }

  _speakerArt() {
    const wrap = h("div", {class: "hero-media--art"});
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", ICONS.speaker);
    svg.append(path);
    wrap.append(svg);
    return wrap;
  }

  _chips() {
    const online = this._entity("binary_sensor", "online");
    const wifi = this._entity("binary_sensor", "wifi_connected");
    const mic = this._entity("switch", "microphone_mute");
    const volume = this._entity("sensor", "volume");
    const chips = [];

    const onlineOn = this._isOn(online);
    chips.push(this._chip(ICONS.online, onlineOn ? "Trực tuyến" : "Ngoại tuyến", onlineOn ? "chip--ok" : "chip--bad"));

    const wifiOn = this._isOn(wifi);
    chips.push(this._chip(ICONS.wifi, wifiOn ? "Wi-Fi OK" : "Mất Wi-Fi", wifiOn ? "chip--blue" : "chip--bad"));

    const micMuted = this._isOn(mic);
    chips.push(this._chip(micMuted ? ICONS.micOff : ICONS.mic, micMuted ? "Mic tắt" : "Mic bật", micMuted ? "chip--bad" : "chip--ok"));

    const volumeState = this._state(volume);
    if (volumeState) {
      const level = Number(volumeState.state);
      chips.push(this._chip(ICONS.volume, `Âm lượng ${Number.isFinite(level) ? `${Math.round(level)}%` : this._value(volume)}`, "chip--muted"));
    }
    return h("div", {class: "chips"}, chips);
  }

  _chip(icon, text, tone) {
    const chip = h("span", {class: ["chip", tone].filter(Boolean).join(" ")});
    chip.append(svgIcon(icon));
    chip.append(document.createTextNode(text));
    return chip;
  }

  _heroCard(delay) {
    const entry = this._entry();
    const media = this._entity("media_player") || "";
    const mediaState = this._state(media);
    const online = this._entity("binary_sensor", "online");
    const image = h("img", {src: HERO_IMAGE, alt: "Loa MAIKA", loading: "lazy"});
    const mediaBox = h("div", {class: "hero-media"});
    const art = h("div", {class: "hero-art"});
    art.append(this._speakerArt());
    mediaBox.append(art);
    mediaBox.append(image);
    image.addEventListener("error", () => {
      image.remove();
      mediaBox.classList.add("hero-media--fallback");
    });

    const stateText = mediaState ? this._stateLabel(mediaState.state) : "Không tìm thấy loa";
    mediaBox.append(
      h("div", {class: "hero-badges"}, [
        h("span", {class: "badge badge--info", text: entry?.title || "MAIKA"}),
      ])
    );
    mediaBox.append(
      h("div", {class: "hero-copy"}, [
        h("h1", {text: this._speakerName()}),
        h("p", {}, [
          h("span", {class: ["dot", this._isOn(online) ? "" : "dot--off"].filter(Boolean).join(" ")}),
          document.createTextNode(stateText),
        ]),
      ])
    );

    const body = h("div", {class: "hero-body"}, [this._chips()]);
    return this._card("hero span2", [mediaBox, body], delay);
  }

  _speakerName() {
    const nameEntity = this._entity("text", "speaker_name");
    const name = this._value(nameEntity, "");
    if (name && name !== "—") return name;
    return this._activeDevice().name || this._entry()?.title || "Loa MAIKA";
  }

  _stateLabel(state) {
    const labels = {
      playing: "Đang phát",
      paused: "Tạm dừng",
      idle: "Đang chờ",
      off: "Đã tắt",
      on: "Đang bật",
      unavailable: "Không kết nối",
      unknown: "Chưa rõ trạng thái",
      standby: "Chế độ chờ",
    };
    return labels[state] || state;
  }

  _statusSection(delay) {
    const rows = [
      ["online", "c-ok", "Trực tuyến", this._entity("binary_sensor", "online"), "access-point"],
      ["wifi", "c-blue", "Wi-Fi", this._entity("binary_sensor", "wifi_connected"), "wifi"],
      ["volume", "c-blue", "Âm lượng", this._entity("sensor", "volume"), "volume"],
      ["playback", "c-purple", "Đang phát", this._entity("sensor", "playback_status"), "play"],
      ["calls", "c-cyan", "Cuộc gọi", this._entity("binary_sensor", "available_to_call"), "phone"],
      ["favorite", "c-pink", "Yêu thích", this._entity("binary_sensor", "favorite"), "heart"],
    ];
    const tiles = rows.map(([key, tone, label, entityId, icon]) => {
      let value = this._value(entityId);
      if (key === "online") value = this._isOn(entityId) ? "Đang kết nối" : "Mất kết nối";
      if (key === "wifi") value = this._isOn(entityId) ? "Đã kết nối" : "Mất Wi-Fi";
      if (key === "calls") value = this._isOn(entityId) ? "Sẵn sàng" : "Không khả dụng";
      if (key === "favorite") value = this._isOn(entityId) ? "Đã yêu thích" : "Bình thường";
      if (key === "playback") value = this._stateLabel(value);
      const ok = ["online", "wifi", "calls", "favorite"].includes(key) ? this._isOn(entityId) : true;
      return this._tile({icon, color: tone, label, value, tone: ok ? tone : "c-bad"});
    });
    return this._card("span2", [
      this._sectionHead("online", "Trạng thái loa", "Kết nối và hoạt động hiện tại", "c-ok"),
      h("div", {class: "tiles"}, tiles),
    ], delay);
  }

  _mediaSection(delay) {
    const media = this._entity("media_player");
    if (!media) {
      return this._card("span2", [
        this._sectionHead("cast", "Điều khiển MAIKA", "Chưa có media player", "c-purple"),
        h("p", {class: "hint", text: "Khởi động lại Home Assistant hoặc kiểm tra tài khoản MAIKA trong integration."}),
      ], delay);
    }
    const state = this._state(media);
    const attrs = state?.attributes || {};
    const volume = Math.round((Number(attrs.volume_level) || 0) * 100);
    const muted = Boolean(attrs.is_volume_muted);
    const playing = state?.state === "playing";

    const now = h("div", {class: "media-now"}, [
      h("div", {class: "ico"}, [svgIcon(playing ? ICONS.pause : ICONS.play)]),
      h("div", {}, [
        h("div", {class: "t", text: attrs.media_title || this._speakerName()}),
        h("div", {class: "s", text: this._stateLabel(state?.state || "unknown")}),
      ]),
    ]);

    const transport = h("div", {class: "transport"}, [
      this._tbtn("prev", "prev", media),
      this._tbtn(playing ? "pause" : "play", "playpause", media, "tbtn--main"),
      this._tbtn("next", "next", media),
      this._tbtn(muted ? "micOff" : "volume", "mute", media, muted ? "tbtn--on" : ""),
    ]);

    const range = h("input", {type: "range", min: "0", max: "100", step: "1", value: String(volume), dataset: {field: "volume", entity: media}});
    const slider = h("div", {class: "slider"}, [
      h("span", {class: "ico"}, [svgIcon(ICONS.volume)]),
      range,
      h("span", {class: "val", text: `${volume}%`}),
    ]);

    const form = h("form", {class: "field", dataset: {form: "cast"}}, [
      h("label", {text: "Phát âm thanh qua cloud (URL MP3/AAC)"}),
      h("div", {class: "btn-row"}, [
        h("input", {type: "url", name: "cast_url", placeholder: "https://.../maika.mp3", dataset: {field: "cast_url"}}),
        h("select", {name: "cast_type", dataset: {field: "cast_type"}}, [
          h("option", {value: "music", text: "Nhạc"}),
          h("option", {value: "audio/mpeg", text: "MP3"}),
          h("option", {value: "audio/aac", text: "AAC"}),
        ]),
        h("button", {class: "btn btn--ghost", type: "submit", text: "Phát"}),
      ]),
      h("p", {class: "hint", text: "Cần bật “Cast âm thanh cloud” trong phần Cấu hình bên dưới."}),
    ]);

    return this._card("span2", [
      this._sectionHead("cast", "Điều khiển MAIKA", "Phát nhạc, âm lượng và mute", "c-purple"),
      h("div", {class: "media"}, [now, transport, slider, form]),
    ], delay);
  }

  _tbtn(icon, action, entity, extra) {
    const btn = h("button", {class: ["tbtn", extra].filter(Boolean).join(" "), type: "button", dataset: {action, entity}});
    btn.append(svgIcon(ICONS[icon]));
    return btn;
  }

  _assistantSection(delay) {
    const rows = [];
    const voice = this._entity("select", "tts_voice");
    const sensitivity = this._entity("select", "wakeword_sensitivity");
    const response = this._entity("select", "wakeword_response");
    rows.push(this._selectRow("Giọng đọc Maika", voice, "mic"));
    rows.push(this._selectRow("Độ nhạy đánh thức", sensitivity, "tune"));
    rows.push(this._selectRow("Phản hồi khi gọi", response, "phone"));

    const mic = this._entity("switch", "microphone_mute");
    if (mic) {
      const muted = this._isOn(mic);
      const box = h("label", {class: "sw"}, [
        h("span", {}, [
          h("span", {class: "txt", text: "Tắt microphone"}),
          h("span", {class: "sub", text: muted ? "Micro đang tắt" : "Micro đang bật"}),
        ]),
        h("input", {type: "checkbox", checked: muted, dataset: {action: "switch", entity: mic}}),
      ]);
      rows.push(box);
    }

    return this._card("span1", [
      this._sectionHead("mic", "Trợ lý Maika", "Giọng nói và đánh thức", "c-purple"),
      h("div", {class: "rows"}, rows.filter(Boolean)),
    ], delay);
  }

  _selectRow(label, entityId, icon) {
    if (!entityId) return null;
    const state = this._state(entityId);
    const options = state?.attributes?.options || [];
    const select = h("select", {dataset: {action: "select", entity: entityId}});
    for (const option of options) {
      select.append(h("option", {value: option, text: option, selected: option === state?.state}));
    }
    return h("div", {class: "row"}, [
      h("span", {class: "lbl", text: label}),
      h("span", {style: "max-width:58%"}, [select]),
    ]);
  }

  _identitySection(delay) {
    const fields = [
      ["Tên loa", this._entity("text", "speaker_name"), "speaker"],
      ["Tên khi gọi", this._entity("text", "calling_name"), "phone"],
      ["Địa chỉ", this._entity("text", "address"), "home"],
    ];
    const rows = fields.map(([label, entityId, icon]) => {
      if (!entityId) return null;
      const state = this._state(entityId);
      const input = h("input", {
        type: "text",
        value: UNKNOWN.has(String(state?.state)) ? "" : String(state?.state || ""),
        dataset: {action: "text", entity: entityId, field: `text:${entityId}`},
        placeholder: label,
      });
      return h("div", {class: "row"}, [
        h("span", {class: "lbl", text: label}),
        h("span", {style: "max-width:62%"}, [input]),
      ]);
    });
    return this._card("span1", [
      this._sectionHead("speaker", "Tên & vị trí", "Thông tin nhận dạng loa", "c-blue"),
      h("div", {class: "rows"}, rows.filter(Boolean)),
    ], delay);
  }

  _deviceSection(delay) {
    const device = this._activeDevice();
    const rows = [
      ["Model", this._value(this._entity("sensor", "model"), device.model || "—")],
      ["Phòng", this._value(this._entity("sensor", "room"), "—")],
      ["Ngôn ngữ", this._value(this._entity("sensor", "default_language"), "—")],
      ["Wi-Fi SSID", this._value(this._entity("sensor", "wifi_ssid"), "—")],
      ["Serial", this._value(this._entity("sensor", "serial_number"), device.serial_number || "—")],
      ["Ngày kích hoạt", fmtDate(this._value(this._entity("sensor", "activated_at"), ""))],
      ["Trạng thái", device.status || "—"],
    ];
    return this._card("span1", [
      this._sectionHead("info", "Thông tin thiết bị", "Model, phòng và kết nối", "c-blue"),
      h("div", {class: "rows"}, rows.map(([label, value]) => this._row(label, String(value)))),
    ], delay);
  }

  _firmwareSection(delay) {
    const version = this._value(this._entity("sensor", "firmware_version"), "—");
    const status = this._value(this._entity("sensor", "firmware_update_status"), "—");
    const device = this._activeDevice();
    const rows = [
      this._row("Phiên bản firmware", version, "c-blue"),
      this._row("Trạng thái cập nhật", status, "c-cyan"),
      this._row("Nhà sản xuất", device.manufacturer || "MAIKA"),
    ];
    return this._card("span1", [
      this._sectionHead("chip", "Firmware & hệ thống", "Phiên bản phần mềm của loa", "c-cyan"),
      h("div", {class: "rows"}, rows),
    ], delay);
  }

  _warrantySection(delay) {
    const active = this._entity("binary_sensor", "warranty_active");
    const expires = this._entity("sensor", "warranty_expire_date");
    if (!active && !expires) return null;
    const on = this._isOn(active);
    return this._card("span1", [
      this._sectionHead("shield", "Bảo hành", "Theo dõi thời hạn thiết bị", on ? "c-ok" : "c-bad"),
      h("div", {class: "tiles"}, [
        this._tile({icon: "shield", color: on ? "c-ok" : "c-bad", label: "Bảo hành", value: on ? "Còn hiệu lực" : "Hết hiệu lực", tone: on ? "c-ok" : "c-bad"}),
        this._tile({icon: "calendar", color: "c-amber", label: "Ngày hết hạn", value: fmtDate(this._value(expires, "")), tone: "c-amber"}),
      ]),
    ], delay);
  }

  _toolsSection(delay) {
    const refresh = this._entity("button", "refresh_status");
    const restart = this._entity("button", "restart");
    const buttons = [];
    if (refresh) {
      buttons.push(this._actionButton("Làm mới", "refresh", refresh, "btn--ghost"));
    }
    if (restart) {
      buttons.push(this._actionButton("Khởi động lại", "restart", restart, "btn--danger"));
    }
    return this._card("span1", [
      this._sectionHead("tune", "Công cụ", "Quản lý và bảo trì loa", "c-amber"),
      h("div", {class: "btn-row"}, buttons),
    ], delay);
  }

  _actionButton(label, action, entity, cls) {
    const btn = h("button", {class: ["btn", cls].filter(Boolean).join(" "), type: "button", dataset: {action, entity}});
    btn.append(svgIcon(action === "restart" ? ICONS.restart : ICONS.refresh));
    btn.append(document.createTextNode(label));
    return btn;
  }

  _licenseSection(delay) {
    const entry = this._entry();
    const license = entry?.license || {};
    const plan = license.plan ? planLabel(license.plan) : "Chưa kích hoạt";
    const expires = license.expires_at ? fmtTime(license.expires_at) : "Không giới hạn";
    const serverUrl = license.server_url || this._snapshot?.default_server_url || "";
    const draftKey = this._draft["license_key"] ?? "";
    const draftServer = this._draft["license_server_url"] ?? serverUrl;

    const rows = [
      this._row("Gói hiện tại", plan, "c-cyan"),
      this._row("Hạn dùng", expires, license.expires_at ? "c-amber" : "c-ok"),
      this._row("Key đang dùng", license.key_hint || "—"),
      this._row("Mã cài đặt", license.activation_code || "—"),
    ];

    const form = h("form", {class: "field", dataset: {form: "license"}}, [
      h("label", {text: "License key"}),
      h("input", {type: "text", name: "license_key", placeholder: "MAIKA-XXXX-XXXX-XXXX-XXXX", value: draftKey, dataset: {field: "license_key"}, autocomplete: "off"}),
      h("label", {text: "URL máy chủ kích hoạt"}),
      h("input", {type: "url", name: "license_server_url", value: draftServer, dataset: {field: "license_server_url"}}),
      h("div", {class: "btn-row"}, [
        h("button", {class: "btn btn--primary", type: "submit", text: "Kích hoạt / thay key", disabled: this._busy}),
        this._snapshot?.portal_url
          ? h("a", {class: "btn btn--ghost", href: this._snapshot.portal_url, target: "_blank", rel: "noreferrer", text: "Mua key / xem lịch sử"})
          : null,
      ]),
      h("p", {class: "hint", text: "Nhập key mới để nâng gói hoặc gia hạn. Hệ thống tự thay máy sang key mới, không cần admin xoá máy."}),
    ]);

    return this._card("span2", [
      this._sectionHead("key", "Bản quyền", "Key, gói và hạn sử dụng", "c-amber"),
      h("div", {style: "display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap"}, [
        this._licenseBadge(license),
        h("span", {class: "badge", text: plan}),
      ]),
      h("div", {class: "rows", style: "margin-bottom:14px"}, rows),
      form,
    ], delay);
  }

  _settingsSection(delay) {
    const options = this._entry()?.options || {};
    const bounds = this._snapshot?.scan_interval_bounds || [15, 3600];
    const sourceOptions = this._snapshot?.audio_source_options || ["disabled", "bundled", "custom"];
    const timingOptions = this._snapshot?.audio_timing_options || ["priority", "after_success"];
    const draft = this._draft;

    const value = (key, fallback) => (key in draft ? draft[key] : fallback);

    const sourceSelect = h("select", {name: "audio_source", dataset: {field: "audio_source"}});
    for (const option of sourceOptions) {
      sourceSelect.append(h("option", {
        value: option,
        text: AUDIO_SOURCE_LABELS[option] || option,
        selected: option === value("audio_source", options[OPTION_KEYS.audioSource]),
      }));
    }

    const timingSelect = h("select", {name: "audio_timing", dataset: {field: "audio_timing"}});
    for (const option of timingOptions) {
      timingSelect.append(h("option", {
        value: option,
        text: AUDIO_TIMING_LABELS[option] || option,
        selected: option === value("audio_timing", options[OPTION_KEYS.audioTiming]),
      }));
    }

    const form = h("form", {class: "field", style: "gap:14px", dataset: {form: "options"}}, [
      h("div", {class: "field"}, [
        h("label", {text: `Chu kỳ cập nhật (${bounds[0]}–${bounds[1]} giây)`}),
        h("input", {type: "number", name: "scan_interval", min: String(bounds[0]), max: String(bounds[1]), value: String(value("scan_interval", options[OPTION_KEYS.scanInterval] ?? 60)), dataset: {field: "scan_interval"}}),
      ]),
      h("label", {class: "sw"}, [
        h("span", {}, [
          h("span", {class: "txt", text: "Cast âm thanh cloud"}),
          h("span", {class: "sub", text: "Phát MP3/TTS từ Home Assistant tới loa"}),
        ]),
        h("input", {type: "checkbox", name: "cloud_cast", checked: Boolean(value("cloud_cast", options[OPTION_KEYS.cloudCast])), dataset: {field: "cloud_cast"}}),
      ]),
      h("label", {class: "sw"}, [
        h("span", {}, [
          h("span", {class: "txt", text: "Sensor câu lệnh giọng nói"}),
          h("span", {class: "sub", text: "Bật rule điều khiển thiết bị HASS bằng giọng nói"}),
        ]),
        h("input", {type: "checkbox", name: "voice_sensor", checked: Boolean(value("voice_sensor", options[OPTION_KEYS.voiceSensor])), dataset: {field: "voice_sensor"}}),
      ]),
      h("div", {class: "field"}, [h("label", {text: "Nguồn âm báo thành công"}), sourceSelect]),
      h("div", {class: "field"}, [h("label", {text: "Thời điểm phát âm báo"}), timingSelect]),
      h("div", {class: "field"}, [
        h("label", {text: "URL MP3 thành công tuỳ chỉnh"}),
        h("input", {type: "url", name: "audio_url", placeholder: "https://.../thanh-cong.mp3", value: value("audio_url", options[OPTION_KEYS.audioUrl] || ""), dataset: {field: "audio_url"}}),
      ]),
      h("div", {class: "field"}, [
        h("label", {text: "Media player phát âm báo"}),
        h("input", {type: "text", name: "media_player", placeholder: "media_player.loa_phong_khach", value: value("media_player", options[OPTION_KEYS.mediaPlayer] || ""), dataset: {field: "media_player"}}),
      ]),
      h("div", {class: "field"}, [
        h("label", {text: "Rule câu lệnh (mỗi dòng: câu lệnh | entity_id | action)"}),
        h("textarea", {name: "rules", dataset: {field: "rules"}, text: value("rules", options[OPTION_KEYS.rules] || "")}),
      ]),
      h("div", {class: "btn-row"}, [
        h("button", {class: "btn btn--primary", type: "submit", text: "Lưu cấu hình", disabled: this._busy}),
        h("button", {class: "btn btn--ghost", type: "button", dataset: {action: "reload"}, text: "Tải lại integration"}),
      ]),
    ]);

    return this._card("span3", [
      this._sectionHead("tune", "Cấu hình loa", "Chu kỳ, cast, âm báo, rule giọng nói — áp dụng mọi loa cùng tài khoản", "c-purple"),
      form,
    ], delay);
  }

  _entrySwitch(delay) {
    const entries = this._snapshot?.entries || [];
    if (entries.length < 2) return null;
    const chips = entries.map((entry, index) =>
      h("button", {
        class: ["chip", index === this._activeIndex ? "chip--ok" : "chip--muted"].join(" "),
        type: "button",
        style: "cursor:pointer;border:none;font:inherit",
        dataset: {action: "entry", index: String(index)},
        text: entry.title || `Loa ${index + 1}`,
      })
    );
    return this._card("titlecard span2", [h("div", {class: "chips"}, chips)], delay);
  }

  _deviceSwitch(delay) {
    const serials = this._serials();
    if (serials.length < 2) return null;
    const active = this._activeSerial();
    const chips = serials.map((serial) =>
      h("button", {
        class: ["chip", serial === active ? "chip--ok" : "chip--muted"].join(" "),
        type: "button",
        style: "cursor:pointer;border:none;font:inherit",
        dataset: {action: "device", serial},
        text: this._deviceLabel(serial),
      })
    );
    return this._card("titlecard span2", [
      h("div", {class: "chips"}, chips),
      h("p", {
        class: "hint",
        text: `${serials.length} loa trong ${this._entry()?.title || "MAIKA"} — chạm để xem và cấu hình từng loa.`,
      }),
    ], delay);
  }

  _render() {
    if (!this._stage) return;
    const focusField = this.shadowRoot.activeElement?.dataset?.field || "";
    this._stage.innerHTML = "";

    if (!this._snapshot) {
      this._stage.append(
        this._card("span2", [h("div", {class: "loading"}, [h("div", {class: "spinner"}), h("span", {text: "Đang tải dữ liệu loa..."})])])
      );
      return;
    }

    if (!this._entry()) {
      this._stage.append(
        this._card("span2", [
          this._sectionHead("speaker", "Chưa có loa MAIKA", "Hãy thêm integration MAIKA Speaker trước", "c-bad"),
          h("p", {class: "hint", text: "Vào Settings → Devices & services → Add integration → MAIKA Speaker."}),
        ])
      );
      return;
    }

    if (this._message) {
      this._stage.append(
        this._card("span2", [h("div", {class: `msg msg--${this._message.type === "ok" ? "ok" : "err"}`, text: this._message.text})], 0)
      );
    }

    const cards = [
      this._entrySwitch(10),
      this._deviceSwitch(25),
      this._heroCard(30),
      this._mediaSection(60),
      this._statusSection(90),
      this._assistantSection(120),
      this._identitySection(150),
      this._deviceSection(180),
      this._firmwareSection(210),
      this._warrantySection(240),
      this._toolsSection(270),
      this._licenseSection(300),
      this._settingsSection(330),
    ];
    for (const card of cards) {
      if (card) this._stage.append(card);
    }

    if (focusField) {
      const target = this._stage.querySelector(`[data-field="${CSS.escape(focusField)}"]`);
      if (target) target.focus();
    }
  }

  _signature() {
    const entry = this._entry();
    const states = {};
    const entities = entry?.entities || {};
    for (const ids of Object.values(entities)) {
      for (const id of ids) {
        const state = this._hass?.states?.[id];
        if (state) states[id] = `${state.state}|${JSON.stringify(state.attributes?.options || "")}`;
      }
    }
    return JSON.stringify({
      entry: entry?.entry_id,
      index: this._activeIndex,
      device: this._activeSerial(),
      states,
      options: entry?.options,
      license: entry?.license,
      devices: entry?.devices,
      busy: this._busy,
      message: this._message,
      narrow: this._narrow,
    });
  }

  _maybeUpdate() {
    const signature = this._signature();
    if (signature === this._lastSignature) return;
    this._lastSignature = signature;
    this._render();
  }

  async _load() {
    try {
      const snapshot = await this._hass.callApi("GET", API);
      this._snapshot = snapshot;
      if (this._activeIndex >= (snapshot.entries || []).length) this._activeIndex = 0;
    } catch (err) {
      this._message = {type: "error", text: `Không tải được dữ liệu panel: ${this._errorText(err)}`};
    }
    this._lastSignature = "";
    this._maybeUpdate();
  }

  _errorText(err) {
    const code = err?.body?.message || err?.body?.error || err?.message;
    const labels = {
      invalid_license: "Key không hợp lệ",
      invalid_server_url: "URL máy chủ không hợp lệ",
      license_server_unavailable: "Không kết nối được máy chủ kích hoạt",
      invalid_license_response: "Máy chủ trả dữ liệu không hợp lệ",
      invalid_scan_interval: "Chu kỳ cập nhật không hợp lệ",
      invalid_voice_command_rules: "Rule câu lệnh không hợp lệ",
      voice_success_audio_media_player_invalid: "Media player không tồn tại",
      voice_success_audio_url_invalid: "URL MP3 không hợp lệ",
      unknown_entry: "Không tìm thấy loa",
    };
    return labels[code] || code || "Lỗi không xác định";
  }

  _notify(type, text) {
    this._message = {type, text};
    this._lastSignature = "";
    this._maybeUpdate();
  }

  _onInput(event) {
    const el = event.target;
    const field = el?.dataset?.field;
    if (!field) return;
    if (el.type === "checkbox") return;
    this._draft[field] = el.value;
    if (field === "volume") {
      const label = el.parentElement?.querySelector(".val");
      if (label) label.textContent = `${el.value}%`;
    }
  }

  _onChange(event) {
    const el = event.target;
    if (!el?.dataset) return;
    if (el.dataset.field) {
      this._draft[el.dataset.field] = el.type === "checkbox" ? el.checked : el.value;
    }
    const action = el.dataset.action;
    if (!action) {
      if (el.dataset.field === "volume" && el.dataset.entity) {
        const level = Math.min(1, Math.max(0, Number(el.value) / 100));
        this._callService("media_player", "volume_set", {entity_id: el.dataset.entity, volume_level: level});
      }
      return;
    }
    if (action === "select") {
      this._callService("select", "select_option", {entity_id: el.dataset.entity, option: el.value});
    } else if (action === "switch") {
      this._callService("switch", el.checked ? "turn_on" : "turn_off", {entity_id: el.dataset.entity});
    } else if (action === "text") {
      this._callService("text", "set_value", {entity_id: el.dataset.entity, value: el.value});
    }
  }

  _onClick(event) {
    const target = event.target.closest?.("[data-action]");
    if (!target || target.tagName === "A") return;
    const action = target.dataset.action;
    const entity = target.dataset.entity;

    if (action === "entry") {
      this._activeIndex = Number(target.dataset.index) || 0;
      this._deviceSerial = "";
      this._draft = {};
      this._message = null;
      this._lastSignature = "";
      this._maybeUpdate();
      return;
    }

    if (action === "device") {
      this._deviceSerial = target.dataset.serial || "";
      this._draft = {};
      this._lastSignature = "";
      this._maybeUpdate();
      return;
    }

    if (!entity) {
      if (action === "reload") this._reloadEntry();
      return;
    }

    const media = this._entity("media_player");
    const state = this._state(entity);
    const muted = Boolean(state?.attributes?.is_volume_muted);

    const services = {
      playpause: ["media_player", "media_play_pause", {}],
      prev: ["media_player", "media_previous_track", {}],
      next: ["media_player", "media_next_track", {}],
      mute: ["media_player", "volume_mute", {is_volume_muted: !muted}],
      refresh: ["button", "press", {}],
      restart: ["button", "press", {}],
    };
    const call = services[action];
    if (!call) return;
    if (action === "restart" && !window.confirm("Xác nhận khởi động lại loa MAIKA?")) return;
    if (action === "playpause" && !media) return;
    this._callService(call[0], call[1], {entity_id: entity, ...call[2]});
  }

  async _onSubmit(event) {
    const form = event.target;
    const kind = form?.dataset?.form;
    if (!kind) return;
    event.preventDefault();
    if (this._busy) return;

    if (kind === "cast") {
      const media = this._entity("media_player");
      const url = String(form.elements.namedItem("cast_url")?.value || "").trim();
      const type = String(form.elements.namedItem("cast_type")?.value || "music");
      if (!url || !media) {
        this._notify("error", "Nhập URL âm thanh hợp lệ trước khi phát.");
        return;
      }
      this._callService("media_player", "play_media", {
        entity_id: media,
        media_content_id: url,
        media_content_type: type,
      }, "Đã gửi lệnh phát tới loa.");
      return;
    }

    if (kind === "license") {
      const entry = this._entry();
      const licenseKey = String(form.elements.namedItem("license_key")?.value || "").trim();
      const serverUrl = String(form.elements.namedItem("license_server_url")?.value || "").trim();
      if (!licenseKey) {
        this._notify("error", "Nhập license key trước khi kích hoạt.");
        return;
      }
      this._busy = true;
      this._maybeUpdate();
      const result = await this._post(`${API}/license`, {
        entry_id: entry.entry_id,
        license_key: licenseKey,
        server_url: serverUrl,
      });
      this._busy = false;
      if (result.ok) {
        delete this._draft["license_key"];
        this._notify("ok", `Kích hoạt thành công. Trạng thái: ${result.data?.status || "active"}.`);
        await this._load();
      } else {
        this._notify("error", `Kích hoạt thất bại: ${this._errorText(result.error)}`);
      }
      return;
    }

    if (kind === "options") {
      const entry = this._entry();
      const num = (name, fallback) => {
        const value = Number(form.elements.namedItem(name)?.value);
        return Number.isFinite(value) ? value : fallback;
      };
      const options = {
        [OPTION_KEYS.scanInterval]: num("scan_interval", entry.options?.[OPTION_KEYS.scanInterval] ?? 60),
        [OPTION_KEYS.cloudCast]: Boolean(form.elements.namedItem("cloud_cast")?.checked),
        [OPTION_KEYS.voiceSensor]: Boolean(form.elements.namedItem("voice_sensor")?.checked),
        [OPTION_KEYS.audioSource]: String(form.elements.namedItem("audio_source")?.value || "disabled"),
        [OPTION_KEYS.audioTiming]: String(form.elements.namedItem("audio_timing")?.value || "priority"),
        [OPTION_KEYS.audioUrl]: String(form.elements.namedItem("audio_url")?.value || "").trim(),
        [OPTION_KEYS.mediaPlayer]: String(form.elements.namedItem("media_player")?.value || "").trim(),
        [OPTION_KEYS.rules]: String(form.elements.namedItem("rules")?.value || ""),
      };
      this._busy = true;
      this._maybeUpdate();
      const result = await this._post(`${API}/options`, {entry_id: entry.entry_id, options});
      this._busy = false;
      if (result.ok) {
        this._draft = {};
        this._notify("ok", "Đã lưu cấu hình. Integration đang tải lại.");
        await this._load();
      } else {
        this._notify("error", `Lưu cấu hình thất bại: ${this._errorText(result.error)}`);
      }
    }
  }

  async _reloadEntry() {
    const entry = this._entry();
    if (!entry) return;
    this._busy = true;
    this._maybeUpdate();
    const result = await this._post(`${API}/action`, {entry_id: entry.entry_id, action: "reload"});
    this._busy = false;
    this._notify(result.ok ? "ok" : "error", result.ok ? "Đã yêu cầu tải lại integration." : `Tải lại thất bại: ${this._errorText(result.error)}`);
  }

  _callService(domain, service, data, successText) {
    const promise = this._hass.callService(domain, service, data);
    if (!promise || typeof promise.then !== "function") {
      if (successText) this._notify("ok", successText);
      return;
    }
    promise.then(
      () => {
        if (successText) this._notify("ok", successText);
      },
      (err) => this._notify("error", `Không thực hiện được: ${this._errorText(err)}`)
    );
  }

  async _post(path, body) {
    try {
      const data = await this._hass.callApi("POST", path, body);
      return {ok: true, data};
    } catch (err) {
      return {ok: false, error: err};
    }
  }
}

customElements.define("maika-panel", MaikaPanel);
