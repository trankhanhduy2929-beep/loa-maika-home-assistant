/* MAIKA Speaker management panel for Home Assistant. */
import "./maika-voice-editor.js";

const API = "maika/panel";
const HERO_IMAGE = "https://smarthomekit.vn/wp-content/uploads/2021/12/olli-maika-2.jpg";

const PLAN_LABELS = {
  trial_1d: "Trải nghiệm 1 ngày",
  month_1: "Gói 1 tháng",
  month_6: "Gói 6 tháng",
  lifetime: "Vĩnh viễn",
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
  castBaseUrl: "cloud_cast_base_url",
};

const UNKNOWN = new Set(["unknown", "unavailable", "none", "", "None", "null"]);
const LICENSE_REMINDER_DAYS = 7;
const HISTORY_RESULT_LABELS = {executed: "Đã thực hiện", failed: "Lỗi", pending: "Đang chạy", not_matched: "Chưa có rule"};
const THEME_STORE_KEY = "maika.panel.theme";
const THEME_MODES = ["auto", "light", "dark"];
const THEME_MODE_LABELS = {auto: "Tự động", light: "Sáng", dark: "Tối"};
const SECTIONS = [
  {id: "overview", label: "Tổng quan"},
  {id: "voice", label: "Giọng nói"},
  {id: "history", label: "Lịch sử"},
  {id: "status", label: "Trạng thái"},
  {id: "assistant", label: "Trợ lý"},
  {id: "identity", label: "Tên & vị trí"},
  {id: "info", label: "Thiết bị"},
  {id: "license", label: "Bản quyền"},
  {id: "settings", label: "Cấu hình"},
  {id: "tools", label: "Công cụ"},
];

function fmtTime(value) {
  if (!value) return "—";
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("vi-VN", {dateStyle: "short", timeStyle: "short"});
}

function fmtClock(value) {
  const total = Math.max(0, Math.round(Number(value) || 0));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
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
  stop: "M6 6h12v12H6z",
  list: "M3 5h2v2H3zm4 0h14v2H7zM3 11h2v2H3zm4 0h14v2H7zM3 17h2v2H3zm4 0h14v2H7z",
  music: "M12 3v10.55A4 4 0 1 0 14 17V7h4V3zM10 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0",
  restart: "M12 5V2L8 6l4 4V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z",
  refresh: "M17.7 6.3A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.8-4.3L13 11h7V4z",
  chip: "M9 2v2H7a3 3 0 0 0-3 3v2H2v2h2v2H2v2h2v2a3 3 0 0 0 3 3h2v2h2v-2h2v2h2v-2h2a3 3 0 0 0 3-3v-2h2v-2h-2v-2h2V9h-2V7a3 3 0 0 0-3-3h-2V2h-2v2h-2V2zm0 6h6v8H9z",
  shield: "M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5zm0 5 1.6 3.3 3.4.5-2.5 2.4.6 3.5-3.1-1.7-3.1 1.7.6-3.5L7 10.8l3.4-.5z",
  key: "M7 14a5 5 0 1 1 5-5c0 .7-.2 1.3-.4 1.9l7.5 7.5-1.6 1.6-1.5-1.5-1.5 1.5-1.5-1.5-1.5 1.5-2.6-2.6A5 5 0 0 1 7 14m0-2a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3",
  tune: "M3 17v2h6v-2zm0-6v2h10v-2zm0-6v2h14V5zm12 12h6v-2h-4v-8h4V5h-6zm-2-8h2v-2h-2z",
  speaker: "M12 3a6 6 0 0 0-6 6v5a6 6 0 0 0 12 0V9a6 6 0 0 0-6-6m0 15a9 9 0 0 1-9-9H1a11 11 0 0 0 10 10.9V22h2v-2.1A11 11 0 0 0 23 9h-2a9 9 0 0 1-9 9",
  home: "M12 3 2 12h3v8h6v-5h2v5h6v-8h3z",
  clock: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20m1 5h-2v6l5 3 1-1.7-4-2.3z",
  check: "M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z",
  alert: "M12 2 1 21h22zm1 14h-2v2h2zm0-6h-2v4h2z",
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
  sun: "M11 1h2v3h-2zm0 19h2v3h-2zM1 11h3v2H1zm19 0h3v2h-3zM4.2 2.8l2.1 2.1-1.4 1.4L2.8 4.2zm14.9 14.9 2.1 2.1-1.4 1.4-2.1-2.1zM2.8 19.8l2.1-2.1 1.4 1.4-2.1 2.1zM17.7 4.9l2.1-2.1 1.4 1.4-2.1 2.1zM12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12",
  moon: "M20.9 13.2A8 8 0 0 1 10.8 3.1 9 9 0 1 0 20.9 13.2",
  menu: "M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z",
  left: "M15.4 5 8.4 12l7 7 1.4-1.4-5.6-5.6 5.6-5.6z",
  right: "m8.6 5-1.4 1.4 5.6 5.6-5.6 5.6L8.6 19l7-7z",
};

class MaikaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._hass = null;
    this._snapshot = null;
    this._activeIndex = 0;
    this._deviceSerial = "";
    this._themeMode = "auto";
    this._activeSection = "overview";
    this._busy = false;
    this._message = null;
    this._draft = {};
    this._loaded = false;
    this._loading = false;
    this._renderFrame = null;
    this._lastSignature = "";
    this._playlist = null;
    this._playlistDialog = null;
    this._playlistToken = 0;
    this._playlistBusy = false;
    this._playlistReturnFocus = false;
    this._onClick = this._onClick.bind(this);
    this._onInput = this._onInput.bind(this);
    this._onChange = this._onChange.bind(this);
    this._onSubmit = this._onSubmit.bind(this);
    this._gesture = null;
    this._gestureFrame = null;
    this._deviceAnimation = null;
    this._onPointerDown = this._onPointerDown.bind(this);
    this._onPointerMove = this._onPointerMove.bind(this);
    this._onPointerEnd = this._onPointerEnd.bind(this);
    this._onSpeakerKey = this._onSpeakerKey.bind(this);
    this._onMotionChange = () => {
      this._cancelGesture();
      this._deviceAnimation?.cancel();
      this._applyMotion();
    };
    this._onThemeChange = () => this._applyTheme();
    this._onStorage = (event) => {
      if (event.key === THEME_STORE_KEY || event.key === null) {
        this._themeMode = this._storedThemeMode();
        this._applyTheme();
      }
    };
    this._onVisibility = () => {
      this.toggleAttribute("data-paused", document.hidden);
      if (document.hidden) this._onMotionChange();
    };
  }

  connectedCallback() {
    this._colorQuery = window.matchMedia?.("(prefers-color-scheme: dark)");
    this._colorQuery?.addEventListener("change", this._onThemeChange);
    this._motionQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    this._motionQuery?.addEventListener("change", this._onMotionChange);
    this._applyMotion();
    window.addEventListener("storage", this._onStorage);
    document.addEventListener("visibilitychange", this._onVisibility);
    this._onVisibility();
    if (this._stage) {
      this._themeMode = this._storedThemeMode();
      this._applyTheme();
      this._observeSections();
      this._maybeUpdate();
    }
  }

  disconnectedCallback() {
    this._colorQuery?.removeEventListener("change", this._onThemeChange);
    this._motionQuery?.removeEventListener("change", this._onMotionChange);
    this._onMotionChange();
    this._motionObserver?.disconnect();
    window.removeEventListener("storage", this._onStorage);
    document.removeEventListener("visibilitychange", this._onVisibility);
    this._sectionObserver?.disconnect();
    this._toolbarObserver?.disconnect();
    if (this._renderFrame !== null) cancelAnimationFrame(this._renderFrame);
    this._renderFrame = null;
  }

  set hass(value) {
    this._hass = value;
    if (!this._loaded) {
      this._loaded = true;
      this._themeMode = this._storedThemeMode();
      this._root();
      this._applyTheme();
      this._load();
    } else {
      this._applyTheme();
      if (this._snapshot && this.isConnected && this._renderFrame === null) {
        this._renderFrame = requestAnimationFrame(() => {
          this._renderFrame = null;
          this._maybeUpdate();
        });
      }
    }
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    if (this._narrow === value) return;
    this._narrow = value;
    if (this._snapshot) this._maybeUpdate();
  }

  set panel(value) {
    this._panel = value;
    if (value && value.config && Number.isInteger(value.config.entry_index)) {
      this._activeIndex = value.config.entry_index;
    }
  }

  _storedThemeMode() {
    try {
      const stored = window.localStorage.getItem(THEME_STORE_KEY);
      return THEME_MODES.includes(stored) ? stored : "auto";
    } catch (err) {
      return "auto";
    }
  }

  _persistThemeMode() {
    try {
      window.localStorage.setItem(THEME_STORE_KEY, this._themeMode);
    } catch {}
  }

  _applyMotion() {
    const reduced = this._reducedMotion();
    this.toggleAttribute("data-reduced-motion", reduced);
    this.shadowRoot.querySelector("maika-voice-editor")?.toggleAttribute("data-reduced-motion", reduced);
  }

  _themeLuminance(value) {
    const color = String(value || "").trim().toLowerCase();
    if (!color) return null;
    const hex = color.match(/^#([0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/);
    if (hex) {
      let digits = hex[1];
      if (digits.length === 3 || digits.length === 4) digits = digits.split("").map((digit) => digit + digit).join("");
      const channels = [0, 2, 4].map((index) => parseInt(digits.slice(index, index + 2), 16));
      return (0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]) / 255;
    }
    const hsl = color.match(/hsla?\(([^)]*)\)/);
    if (hsl) {
      const numbers = hsl[1].match(/[-\d.]+(?:%|deg)?/g) || [];
      const lightness = numbers[2];
      return lightness ? Number(lightness.slice(0, -1)) / 100 : null;
    }
    const numbers = color.match(/[\d.]+/g);
    if (numbers && numbers.length >= 3) {
      return (0.2126 * Number(numbers[0]) + 0.7152 * Number(numbers[1]) + 0.0722 * Number(numbers[2])) / 255;
    }
    return null;
  }

  _resolveTheme() {
    if (this._themeMode !== "auto") return this._themeMode;
    if (typeof this._hass?.themes?.darkMode === "boolean") {
      return this._hass.themes.darkMode ? "dark" : "light";
    }
    const styles = getComputedStyle(this);
    const candidates = [
      styles.getPropertyValue("--card-background-color"),
      styles.getPropertyValue("--primary-background-color"),
      styles.getPropertyValue("--paper-card-background-color"),
    ];
    for (const candidate of candidates) {
      const luminance = this._themeLuminance(candidate);
      if (luminance !== null) return luminance > 0.6 ? "light" : "dark";
    }
    return this._colorQuery?.matches === false ? "light" : "dark";
  }

  _applyTheme() {
    const resolved = this._resolveTheme();
    if (this.dataset.theme !== resolved) this.dataset.theme = resolved;
    this.dataset.themeMode = this._themeMode;
    const select = this.shadowRoot.querySelector('[data-action="theme"]');
    if (select) select.value = this._themeMode;
  }

  _setTheme(mode) {
    if (!THEME_MODES.includes(mode)) return;
    this._themeMode = mode;
    this._persistThemeMode();
    this._applyTheme();
  }

  _style() {
    const style = document.createElement("style");
    style.textContent = `
      :host {
        --bg: #17110f;
        --surface: #2a201b;
        --surface-2: rgba(255, 201, 160, .055);
        --surface-3: rgba(255, 201, 160, .11);
        --line: rgba(255, 215, 184, .19);
        --text: #fff4ec;
        --muted: #c9b3a4;
        --accent: #ffaf70;
        --accent-2: #ffc981;
        --accent-ink: #381a08;
        --brand-start: #ffce8a;
        --brand-end: #ff7a23;
        --brand-ink: #3c1c08;
        --glass-surface: rgba(42, 32, 27, .78);
        --glass-toolbar: rgba(42, 32, 27, .9);
        --glass-sheen: rgba(255, 239, 222, .11);
        --ease: cubic-bezier(.22, 1, .36, 1);
        --product-surface: #fff6e9;
        --product-tint: #ffe0bf;
        --maika-motion-state: running;
        --ok: #3ee39b;
        --bad: #ff7c8a;
        --blue: #5cc0ff;
        --purple: #8f7dff;
        --amber: #ffc775;
        --pink: #ff9ec4;
        --cyan: #6fe6f0;
        --shadow: 0 8px 28px rgba(18, 7, 0, .2), inset 0 1px 0 rgba(255, 241, 223, .15), inset 0 -1px 0 rgba(255, 179, 113, .035);
        --shadow-hover: 0 14px 32px rgba(18, 7, 0, .28), inset 0 1px 0 rgba(255, 241, 223, .22);
        --radius: 26px;
        --radius-sm: 16px;
        --gap: 14px;
        --pad: 18px;
        --toolbar-offset: 150px;

        display: block;
        height: 100%;
        max-height: 100vh;
        max-height: 100dvh;
        min-height: 0;
        min-width: 0;
        overflow: auto;
        container-type: inline-size;
        overscroll-behavior-y: contain;
        scrollbar-width: thin;
        scrollbar-color: color-mix(in srgb, var(--accent) 60%, transparent) transparent;
        font-family: var(--ha-font-family-body, system-ui, -apple-system, "Segoe UI", sans-serif);
        line-height: 1.5;
        color: var(--text);
        color-scheme: dark;
        background: var(--bg);
        background-image: radial-gradient(ellipse at 4% 4%, rgba(255, 119, 32, .2), transparent 45%), radial-gradient(ellipse at 96% 35%, rgba(255, 183, 87, .12), transparent 40%);
        transition: background-color .35s ease, color .25s ease;
      }
      :host([data-theme="light"]) {
        --bg: #fff5ed;
        --surface: #fffdfa;
        --surface-2: rgba(143, 65, 17, .04);
        --surface-3: rgba(143, 65, 17, .085);
        --line: rgba(134, 67, 27, .18);
        --text: #392316;
        --muted: #775b49;
        --accent: #b74708;
        --accent-2: #a45108;
        --accent-ink: #ffffff;
        --glass-surface: rgba(255, 253, 250, .78);
        --glass-toolbar: rgba(255, 253, 250, .92);
        --glass-sheen: rgba(255, 255, 255, .85);
        --ok: #06734f;
        --bad: #b82642;
        --blue: #1466ac;
        --purple: #6b57e6;
        --amber: #805009;
        --pink: #a12d68;
        --cyan: #08687a;
        --shadow: 0 8px 28px rgba(125, 59, 13, .065), inset 0 1px 0 #fff, inset 0 -1px 0 rgba(255, 255, 255, .65);
        --shadow-hover: 0 14px 32px rgba(125, 59, 13, .12), inset 0 1px 0 #fff;
        color-scheme: light;
      }
      * { box-sizing: border-box; }
      [hidden] { display: none !important; }
      button, input, select, textarea { -webkit-tap-highlight-color: transparent; }
      button, a, select { touch-action: manipulation; }
      button { position: relative; isolation: isolate; }
      button::after {
        content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
        background: currentColor; opacity: 0; transform: scale(.7);
        transition: opacity .32s ease, transform .4s var(--ease);
      }
      button:active:not(:disabled)::after { opacity: .12; transform: scale(1); transition-duration: .08s; }
      button:focus-visible, a:focus-visible, summary:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
        outline: 3px solid var(--accent); outline-offset: 3px;
      }
      button:disabled { opacity: .55; cursor: wait; }
      [data-sec] { scroll-margin-top: var(--toolbar-offset); }

      .stage {
        max-width: 1560px;
        min-width: 0;
        min-height: 100%;
        background: transparent;
        margin: 0 auto;
        padding: calc(14px + env(safe-area-inset-top, 0px)) max(12px, env(safe-area-inset-left, 0px))
          calc(40px + env(safe-area-inset-bottom, 0px));
        padding-right: max(12px, env(safe-area-inset-right, 0px));
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        grid-auto-rows: min-content;
        gap: var(--gap);
        align-content: start;
      }
      .span1 { grid-column: span 1; }
      .span2 { grid-column: span 2; }
      .span3 { grid-column: span 3; }
      .span4 { grid-column: 1 / -1; }
      @container (max-width: 1100px) { .stage { grid-template-columns: repeat(2, minmax(0, 1fr)); } .span3 { grid-column: span 2; } }
      @container (max-width: 620px) {
        .stage { grid-template-columns: 1fr; --gap: 11px; --pad: 15px; --radius: 22px; --radius-sm: 14px; }
        .span1, .span2, .span3 { grid-column: span 1; }
      }
      @container (max-width: 380px) { .stage { --pad: 12px; } }

      .card {
        min-width: 0;
        overflow-wrap: anywhere;
        position: relative;
        background: var(--surface);
        background-image: linear-gradient(145deg, var(--surface-2), transparent 65%);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        padding: var(--pad);
        box-shadow: var(--shadow);
        animation: rise .42s cubic-bezier(.22, .9, .3, 1) both;
        animation-delay: var(--d, 0ms);
        transition: box-shadow .25s ease, border-color .25s ease, background-color .3s ease, transform .28s var(--ease);
      }
      .card:hover { box-shadow: var(--shadow-hover); border-color: color-mix(in srgb, var(--accent) 30%, var(--line)); transform: translateY(-2px); }
      .card:has(:focus-visible) { border-color: var(--accent); }

      .toolbar {
        position: sticky;
        top: env(safe-area-inset-top, 0px);
        z-index: 5;
        padding: 10px 12px;
        border-radius: 20px;
        background: var(--surface);
        animation: none;
      }
      @supports ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
        .card {
          background: linear-gradient(145deg, var(--glass-sheen), transparent 42%), var(--glass-surface);
        }
        .toolbar, .hero, [data-card="media"] {
          backdrop-filter: blur(14px) saturate(125%);
          -webkit-backdrop-filter: blur(14px) saturate(125%);
        }
        .toolbar { background: linear-gradient(145deg, var(--glass-sheen), transparent 42%), var(--glass-toolbar); }
      }
      :host::-webkit-scrollbar { width: 10px; height: 10px; }
      :host::-webkit-scrollbar-track { background: transparent; }
      :host::-webkit-scrollbar-thumb {
        background: linear-gradient(var(--brand-start), var(--brand-end)); border-radius: 999px;
        border: 3px solid transparent; background-clip: padding-box;
      }
      :host::-webkit-scrollbar-thumb:hover { border-width: 2px; }
      .toolbar-main { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
      .brand { display: flex; align-items: center; gap: 9px; margin-right: auto; min-width: 0; flex: 1; }
      .brand .mark {
        width: 34px; height: 34px; border-radius: 12px; display: grid; place-items: center; flex: none;
        background: linear-gradient(145deg, var(--brand-start), var(--brand-end)); color: var(--brand-ink);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, .5);
      }
      .brand .mark svg { width: 18px; height: 18px; fill: currentColor; }
      .brand-wave { display: flex; align-items: center; gap: 3px; }
      .brand-wave i { width: 3px; height: 15px; border-radius: 4px; background: currentColor; transform-origin: center; animation: brand-wave 1.6s ease-in-out infinite; }
      .brand-wave i:nth-child(2) { animation-delay: .2s; }
      .brand-wave i:nth-child(3) { animation-delay: .4s; }
      .brand-wave i:nth-child(4) { animation-delay: .6s; }
      .brand-wave i:first-child, .brand-wave i:last-child { height: 8px; }
      .brand .txt { min-width: 0; }
      .brand b { display: block; font-size: .86rem; letter-spacing: .12em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .brand small { display: block; font-size: .72rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .iconbtn {
        width: 44px; height: 44px; border-radius: 14px; border: 1px solid var(--line); flex: none;
        background: var(--surface-2); color: var(--text); display: grid; place-items: center; cursor: pointer;
        transition: transform .16s ease, background .2s ease, border-color .2s ease;
      }
      .iconbtn:hover {
        background: linear-gradient(145deg, color-mix(in srgb, var(--accent) 16%, transparent), var(--surface-3));
        border-color: color-mix(in srgb, var(--accent) 32%, var(--line)); transform: translateY(-1px);
      }
      .iconbtn:active { transform: scale(.94); }
      .iconbtn svg { width: 19px; height: 19px; fill: currentColor; }
      .theme-picker { display: flex; align-items: center; gap: 6px; font-size: .75rem; color: var(--muted); }
      .theme-picker select { width: 118px; min-height: 44px; padding: 8px; font-size: 16px; }
      .theme-picker svg { width: 18px; height: 18px; fill: var(--accent); }
      .theme-moon { display: none; }
      :host([data-theme="dark"]) .theme-moon { display: block; }
      :host([data-theme="dark"]) .theme-sun { display: none; }
      .toolbar-groups { display: flex; flex-wrap: wrap; gap: 8px 24px; margin-top: 10px; min-width: 0; }
      .toolbar-group { display: flex; align-items: center; gap: 8px; min-width: 0; max-width: 100%; }
      .group-label { font-size: .72rem; color: var(--muted); flex: none; width: 60px; }
      .nav {
        display: flex; gap: 8px; margin-top: 10px; padding-bottom: 2px;
        overflow-x: auto; scrollbar-width: none; scroll-padding-inline: 4px;
        scroll-snap-type: x proximity; overscroll-behavior-x: contain;
      }
      .nav::-webkit-scrollbar { display: none; }
      .pill {
        flex: none; border: 1px solid var(--line); background: var(--surface-2); color: var(--muted);
        font: inherit; font-size: .78rem; font-weight: 620; padding: 7px 13px; border-radius: 999px; cursor: pointer; min-height: 44px;
        transition: background .24s ease, color .24s ease, transform .22s var(--ease), box-shadow .24s ease;
        scroll-snap-align: start;
      }
      .pill:hover { color: var(--text); transform: translateY(-1px); }
      .pill--on, .pill--on:hover {
        background: linear-gradient(145deg, var(--brand-start), var(--brand-end));
        border-color: transparent; color: var(--brand-ink);
        animation: pill-glow 3.6s ease-in-out infinite;
      }

      .titlecard { background: none; border: none; box-shadow: none; padding: 2px 4px 0; animation: none; }
      .titlecard:hover { box-shadow: none; }
      .titlecard h2 { margin: 0; font-size: 1.02rem; font-weight: 700; letter-spacing: -.01em; }
      .titlecard p { margin: 3px 0 0; font-size: .8rem; color: var(--muted); }
      .sec-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
      .sec-head .ico {
        width: 34px; height: 34px; border-radius: 12px; display: grid; place-items: center; flex: none;
        background: linear-gradient(145deg, color-mix(in srgb, var(--accent) 20%, transparent), var(--surface-3));
        color: var(--accent); box-shadow: inset 0 1px 0 var(--glass-sheen);
      }
      .sec-head .ico svg { width: 18px; height: 18px; fill: currentColor; }
      .sec-head h3 { margin: 0; font-size: clamp(.9rem, .84rem + .3vw, .98rem); font-weight: 660; }
      .sec-head span { display: block; font-size: .76rem; color: var(--muted); }

      .hero { padding: var(--pad); overflow: hidden; display: grid; gap: 16px; align-content: center; }
      .hero-heading { display: flex; align-items: center; gap: 12px; justify-content: space-between; min-width: 0; }
      .eyebrow { color: var(--accent); font-size: .67rem; font-weight: 750; letter-spacing: .14em; }
      .hero-account { color: var(--muted); font-size: .75rem; max-width: 48%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .hero-showcase {
        display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 16px; min-width: 0;
        transform: translate3d(var(--swipe-offset, 0px), 0, 0); transition: transform .32s var(--ease);
      }
      .hero-showcase[data-swipe] { touch-action: pan-y pinch-zoom; cursor: grab; user-select: none; -webkit-user-select: none; border-radius: 20px; }
      .hero-showcase:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
      :host([data-swiping]) .hero-showcase { transition: none; cursor: grabbing; will-change: transform; }
      .hero-media {
        position: relative; width: clamp(114px, 21cqw, 180px); aspect-ratio: 1 / 1.08; overflow: hidden; isolation: isolate;
        background: var(--product-surface); border-radius: 30px; flex: none;
        box-shadow: 0 12px 30px rgba(73, 34, 8, .12);
        transition: box-shadow .45s ease, transform .3s var(--ease);
      }
      .hero:hover .hero-media { transform: translateY(-2px); }
      .hero[data-playing] .hero-media { box-shadow: 0 16px 38px rgba(232, 118, 30, .28); }
      .hero-media::before {
        content: ""; position: absolute; inset: -35%; pointer-events: none;
        background: conic-gradient(from 20deg, transparent 15%, #ff8d36 40%, #ffd9a2 55%, transparent 80%);
        opacity: .55;
      }
      .hero[data-connected] .hero-media::before { animation: orbit 12s linear infinite; }
      .hero-media::after { content: ""; position: absolute; inset: 2px; z-index: 0; background: linear-gradient(140deg, var(--product-surface), var(--product-tint)); border-radius: 28px; }
      .hero-media img {
        position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; object-fit: cover; display: block;
        mix-blend-mode: multiply; opacity: 0; transition: opacity .4s ease; pointer-events: none;
      }
      .hero-media img.is-ready { opacity: 1; }
      .hero-art { position: absolute; inset: 0; display: grid; place-items: center; z-index: 1; color: #a36a3d; }
      .hero-aura { position: absolute; inset: 8%; z-index: 2; pointer-events: none; }
      .hero-aura i { position: absolute; inset: 15% 0; border: 1px solid #e77525; border-radius: 50%; opacity: 0; }
      .hero[data-playing] .hero-aura i { animation: sound-ripple 3.6s ease-out infinite; }
      .hero[data-playing] .hero-aura i:nth-child(2) { animation-delay: 1.2s; }
      .hero[data-playing] .hero-aura i:nth-child(3) { animation-delay: 2.4s; }
      .hero[data-playing] .hero-media img.is-ready { animation: speaker-float 4.8s ease-in-out infinite; }
      .sound-wave { display: flex; align-items: center; gap: 3px; height: 24px; color: var(--accent); pointer-events: none; }
      .sound-wave i { width: 3px; height: var(--bar-height); border-radius: 3px; background: currentColor; transform: scaleY(.22); opacity: .35; }
      .hero[data-playing] .sound-wave i { opacity: .85; animation: sound-wave 1.2s ease-in-out infinite; animation-delay: var(--bar-delay); }
      .hero[data-activity="offline"] .sound-wave { color: var(--muted); }
      .hero-media:has(img.is-ready:not([hidden])) .hero-art { visibility: hidden; }
      .hero-media--art { display: grid; place-items: center; width: 100%; }
      .hero-art svg { width: 42%; max-width: 80px; fill: currentColor; }
      .hero-copy { display: grid; gap: 10px; min-width: 0; }
      .hero-copy h1 { margin: 0; font-size: clamp(1.18rem, 1rem + .9vw, 1.7rem); line-height: 1.2; letter-spacing: -.035em; color: var(--text); }
      .hero-copy p { margin: 0; font-size: .8rem; color: var(--muted); display: flex; align-items: center; gap: 9px; }
      .hero-link { align-self: start; justify-self: start; display: inline-flex; align-items: center; gap: 6px; min-height: 44px; padding: 6px 9px; margin-left: -9px; border: 0; border-radius: 12px; background: transparent; color: var(--accent); font: inherit; font-size: .78rem; font-weight: 650; cursor: pointer; }
      .hero-link svg { width: 17px; height: 17px; fill: currentColor; flex: none; }
      .dot { width: 8px; height: 8px; flex: none; border-radius: 50%; background: var(--ok); position: relative; }
      .dot::after { content: ""; position: absolute; inset: -4px; border: 1px solid var(--ok); border-radius: 50%; animation: pulse 2.8s infinite; }
      .dot--off { background: var(--bad); }
      .dot--off::after { display: none; }
      .speaker-pager { display: flex; align-items: center; gap: 10px; padding-top: 10px; border-top: 1px solid var(--line); }
      .swipe-hint { color: var(--muted); font-size: .73rem; flex: 1; min-width: 0; }
      .speaker-count { color: var(--text); font-size: .75rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
      .speaker-pager .iconbtn { width: 44px; height: 44px; border-radius: 50%; }
      .speaker-pager .iconbtn:disabled { cursor: default; opacity: .3; }
      @container (max-width: 380px) {
        .hero-showcase { gap: 10px; }
        .hero-media { width: 100px; border-radius: 25px; }
        .hero-media::after { border-radius: 23px; }
        .hero-copy h1 { font-size: 1.15rem; }
        .hero-link { font-size: .72rem; }
        .hero { gap: 12px; }
        .swipe-hint { font-size: .68rem; }
      }

      .chips { display: flex; flex-wrap: wrap; gap: 8px; }
      .chips--scroll { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; padding-bottom: 2px; scroll-snap-type: x proximity; overscroll-behavior-x: contain; }
      .chips--scroll > .chip { scroll-snap-align: start; }
      .chips--scroll::-webkit-scrollbar { display: none; }
      .chip {
        display: inline-flex; align-items: center; gap: 7px; padding: 7px 12px; border-radius: 999px;
        min-height: 36px; background: var(--surface-2); border: 1px solid var(--line); max-width: 100%;
        font-size: .8rem; font-weight: 600; white-space: nowrap;
      }
      .chip svg { width: 15px; height: 15px; fill: currentColor; flex: none; }
      .chip--ok { color: var(--ok); background: rgba(62, 227, 155, .14); }
      .chip--bad { color: var(--bad); background: rgba(255, 124, 138, .14); }
      .chip--blue { color: var(--blue); background: rgba(92, 192, 255, .14); }
      .chip--muted { color: var(--muted); }
      button.chip { cursor: pointer; font: inherit; font-size: .84rem; min-height: 44px; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; display: block; transition: transform .16s ease, background .2s ease, color .2s ease; }
      button.chip:hover { transform: translateY(-1px); }
      button.chip:active { transform: scale(.96); }
      button.chip[aria-pressed="true"] {
        background: linear-gradient(145deg, var(--brand-start), var(--brand-end));
        border-color: transparent; color: var(--brand-ink);
      }

      .tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
      [data-sec="status"] .tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      @container (max-width: 440px) { [data-sec="status"] .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
      .tile {
        position: relative; overflow: hidden; display: flex; flex-direction: column; gap: 7px; padding: 12px 12px 12px 15px;
        border-radius: var(--radius-sm); background: var(--surface-2); border: 1px solid transparent;
        transition: transform .18s ease, background .18s ease, border-color .18s ease;
      }
      .tile::before {
        content: ""; position: absolute; inset: 10px auto 10px 0; width: 3px; border-radius: 999px;
        background: linear-gradient(var(--brand-start), var(--brand-end)); opacity: .25;
        transition: opacity .2s ease, inset .2s ease;
      }
      .tile:hover { transform: translateY(-2px); background: var(--surface-3); border-color: color-mix(in srgb, var(--accent) 26%, var(--line)); }
      .tile:hover::before { opacity: 1; inset: 6px auto 6px 0; }
      .tile .ico { width: 32px; height: 32px; border-radius: 11px; display: grid; place-items: center; background: var(--surface-3); color: var(--muted); }
      .tile .ico svg { width: 17px; height: 17px; fill: currentColor; }
      .tile .k { font-size: .7rem; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); }
      .tile .v { font-size: .96rem; font-weight: 650; line-height: 1.25; word-break: break-word; }

      .c-ok { color: var(--ok); } .c-bad { color: var(--bad); } .c-blue { color: var(--blue); }
      .c-purple { color: var(--purple); } .c-amber { color: var(--amber); } .c-pink { color: var(--pink); } .c-cyan { color: var(--cyan); }
      .sec-head .ico.c-ok, .tile .ico.c-ok { background: rgba(62, 227, 155, .16); color: var(--ok); }
      .sec-head .ico.c-bad, .tile .ico.c-bad { background: rgba(255, 124, 138, .16); color: var(--bad); }
      .sec-head .ico.c-blue, .tile .ico.c-blue { background: rgba(92, 192, 255, .16); color: var(--blue); }
      .sec-head .ico.c-purple, .tile .ico.c-purple { background: rgba(143, 125, 255, .16); color: var(--purple); }
      .sec-head .ico.c-amber, .tile .ico.c-amber { background: rgba(255, 199, 117, .16); color: var(--amber); }
      .sec-head .ico.c-pink, .tile .ico.c-pink { background: rgba(255, 158, 196, .16); color: var(--pink); }
      .sec-head .ico.c-cyan, .tile .ico.c-cyan { background: rgba(111, 230, 240, .16); color: var(--cyan); }

      .reminder {
        display: flex; align-items: center; gap: 10px; padding: 11px 13px; border-radius: var(--radius-sm);
        background: rgba(255, 199, 117, .14); border: 1px solid rgba(255, 199, 117, .32);
        color: var(--text); font-size: .86rem; margin-bottom: 10px;
      }
      .reminder--bad { background: rgba(255, 124, 138, .16); border-color: rgba(255, 124, 138, .36); }
      .reminder .ico { flex: none; }
      .history { display: grid; gap: 8px; }
      .history-row {
        display: flex; align-items: center; gap: 11px; padding: 10px 13px; border-radius: var(--radius-sm);
        background: var(--surface-2); border: 1px solid transparent;
        transition: background .2s ease, border-color .2s ease, transform .2s ease;
      }
      .history-row:hover { background: var(--surface-3); border-color: color-mix(in srgb, var(--accent) 26%, var(--line)); transform: translateY(-1px); }
      .history-row .history-icon { flex: none; width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center; background: rgba(143, 125, 255, .16); color: var(--purple); }
      .history-row--executed .history-icon { background: rgba(62, 227, 155, .18); color: var(--ok); }
      .history-row--failed .history-icon { background: rgba(255, 124, 138, .18); color: var(--bad); }
      .history-row--pending .history-icon { background: rgba(255, 199, 117, .18); color: var(--amber); }
      .history-row .history-icon svg { width: 17px; height: 17px; fill: currentColor; }
      .history-row .history-body { flex: 1; min-width: 0; display: grid; gap: 2px; }
      .history-row .history-text { font-weight: 620; font-size: .93rem; overflow-wrap: anywhere; }
      .history-row .history-meta { font-size: .76rem; color: var(--muted); overflow-wrap: anywhere; }

      .rows { display: grid; gap: 8px; }
      .row {
        display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 13px;
        border-radius: var(--radius-sm); background: var(--surface-2); border: 1px solid transparent;
        transition: background .2s ease, border-color .2s ease;
      }
      .row:hover { background: var(--surface-3); border-color: var(--line); }
      .row > * { min-width: 0; overflow-wrap: anywhere; }
      .row .lbl { font-size: .84rem; color: var(--muted); }
      .row .val { font-weight: 620; font-size: .92rem; text-align: right; max-width: 66%; }
      .row--field { display: grid; gap: 6px; }
      .row--field input, .row--field select { min-width: 0; }

      .media { display: grid; gap: 14px; }
      .media-now {
        display: flex; align-items: center; gap: 12px; padding: 13px; border-radius: 20px; position: relative; overflow: hidden;
        background: linear-gradient(135deg, rgba(255, 136, 47, .16), rgba(255, 200, 117, .1));
        border: 1px solid var(--line); box-shadow: inset 0 1px 0 var(--glass-sheen);
      }
      .media-now::before { content: ""; position: absolute; inset: 0; width: 55%; pointer-events: none; opacity: 0; background: linear-gradient(110deg, transparent, var(--glass-sheen), transparent); }
      .media-now[data-playing]::before { animation: glass-sweep 6s ease-in-out infinite; }
      .media-now > * { position: relative; }
      .media-now .ico { width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; background: var(--surface-3); color: var(--accent); flex: none; }
      .media-now .ico svg { width: 22px; height: 22px; fill: currentColor; }
      .media-now .t { font-weight: 680; }
      .media-now .s { font-size: .8rem; color: var(--muted); }
      .media-now__body { min-width: 0; display: grid; gap: 2px; }
      .media-title {
        display: inline-flex; align-items: center; gap: 6px; max-width: 100%; min-width: 0;
        margin: 0; padding: 0; background: none; border: 0; color: inherit; font: inherit; text-align: left; cursor: pointer;
      }
      .media-title .t { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .media-title svg { width: 16px; height: 16px; fill: var(--muted); flex: none; transition: fill .2s ease; }
      .media-title:hover:not(:disabled) svg { fill: var(--accent); }
      .media-title:disabled { cursor: default; }
      .media-title:disabled svg { display: none; }
      .media-title:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 7px; }

      dialog.playlist { width: min(560px, 92vw); max-width: 100%; margin: auto; padding: 0; border: 0; background: transparent; color: var(--text); }
      dialog.playlist::backdrop { background: rgba(12, 6, 2, .58); }
      dialog.playlist:not([open]) { display: none; }
      .sheet {
        display: grid; grid-template-rows: auto minmax(0, 1fr); max-height: min(78vh, 720px); overflow: hidden;
        background: var(--glass-toolbar); border: 1px solid var(--line); border-radius: var(--radius);
        box-shadow: var(--shadow); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
      }
      .sheet:focus { outline: none; }
      .sheet__head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 15px var(--pad); border-bottom: 1px solid var(--line); }
      .sheet__head h2 { margin: 0; font-size: 1rem; font-weight: 700; }
      .sheet__close { min-height: 34px; padding: 0 14px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface-2); color: var(--text); font: inherit; font-weight: 600; font-size: .84rem; cursor: pointer; }
      .sheet__close:hover { background: var(--surface-3); }
      .sheet__close:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
      .pl-list { overflow: auto; overscroll-behavior: contain; padding: 9px; display: grid; gap: 6px; }
      .pl-item { display: flex; align-items: center; gap: 11px; width: 100%; padding: 10px 12px; border-radius: var(--radius-sm); border: 1px solid transparent; background: var(--surface-2); color: var(--text); font: inherit; text-align: left; cursor: pointer; transition: background .2s ease, border-color .2s ease; }
      .pl-item:hover:not(:disabled) { background: var(--surface-3); border-color: color-mix(in srgb, var(--accent) 26%, var(--line)); }
      .pl-item:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
      .pl-item:disabled { cursor: progress; opacity: .72; }
      .pl-item--on { background: color-mix(in srgb, var(--accent) 16%, transparent); border-color: color-mix(in srgb, var(--accent) 42%, var(--line)); }
      .pl-item__ico { flex: none; width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center; background: var(--surface-3); color: var(--accent); }
      .pl-item__ico svg { width: 16px; height: 16px; fill: currentColor; }
      .pl-item__body { min-width: 0; flex: 1; display: grid; gap: 2px; }
      .pl-item__t { font-weight: 620; font-size: .92rem; overflow-wrap: anywhere; }
      .pl-item__s { font-size: .78rem; color: var(--muted); overflow-wrap: anywhere; }
      .pl-item__badge { flex: none; font-size: .72rem; font-weight: 600; color: var(--accent); }
      .pl-state { padding: 26px 18px; text-align: center; color: var(--muted); font-size: .9rem; overflow-wrap: anywhere; }
      .pl-state--bad { color: var(--bad); }
      .pl-retry { justify-self: center; }
      .eq { display: flex; align-items: flex-end; gap: 3px; height: 16px; margin-left: auto; flex: none; }
      .eq i { width: 3px; border-radius: 2px; background: var(--accent); height: 100%; transform-origin: bottom; animation: eq .9s ease-in-out infinite; }
      .eq i:nth-child(2) { animation-delay: .12s; }
      .eq i:nth-child(3) { animation-delay: .26s; }
      .eq i:nth-child(4) { animation-delay: .38s; }
      .eq--idle i { animation: none; transform: scaleY(.3); opacity: .45; }
      .transport { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; align-items: center; }
      .tbtn {
        width: 46px; height: 46px; border-radius: var(--radius-sm); border: 1px solid var(--line);
        background: var(--surface-2); color: inherit; display: grid; place-items: center; cursor: pointer;
        transition: transform .15s ease, background .15s ease, color .15s ease;
      }
      .tbtn:hover { transform: translateY(-2px); background: var(--surface-3); }
      .tbtn:active { transform: scale(.93); }
      .tbtn svg { width: 20px; height: 20px; fill: currentColor; }
      .tbtn--main { width: 60px; height: 60px; border-radius: 22px; background: linear-gradient(145deg, var(--brand-start), var(--brand-end)); color: var(--brand-ink); border: none; box-shadow: 0 6px 18px rgba(239, 116, 24, .2), inset 0 1px 0 rgba(255, 255, 255, .6); }
      .tbtn--main svg { width: 26px; height: 26px; }
      .tbtn--on { background: rgba(255, 124, 138, .18); color: var(--bad); }
      .tbtn--stop { border-color: color-mix(in srgb, var(--bad) 30%, var(--line)); }
      .tbtn--stop:hover { background: rgba(255, 124, 138, .16); color: var(--bad); border-color: color-mix(in srgb, var(--bad) 46%, var(--line)); }
      @media (prefers-reduced-motion: no-preference) { .tbtn--stop:active { transform: scale(.86) rotate(-2deg); } }

      .slider { display: flex; align-items: center; gap: 12px; }
      .slider .ico svg { width: 18px; height: 18px; fill: var(--blue); }
      .slider .val { min-width: 44px; text-align: right; font-size: .84rem; font-weight: 650; color: var(--muted); }
      .slider--seek { flex-wrap: wrap; row-gap: 8px; }
      .slider--seek input[type="range"] { flex: 1 1 130px; }
      .slider--seek .sbtn {
        flex: none; min-width: 50px; height: 40px; padding: 0 10px; border-radius: 999px; border: 1px solid var(--line);
        background: var(--surface-2); color: var(--text); font-size: .78rem; font-weight: 680; cursor: pointer;
        transition: transform .14s var(--ease), background .16s var(--ease), border-color .16s var(--ease);
      }
      .slider--seek .sbtn:hover { background: var(--surface-3); border-color: color-mix(in srgb, var(--accent) 34%, var(--line)); transform: translateY(-1px); }
      .slider--seek .sbtn:active { transform: scale(.93); }
      .slider--seek .sbtn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
      input[type="range"] {
        -webkit-appearance: none; appearance: none; width: 100%; min-width: 0; height: 44px; border-radius: 999px;
        background: linear-gradient(90deg, var(--accent) var(--p, 0%), var(--surface-3) var(--p, 0%)) center / 100% 8px no-repeat;
        outline: none; padding: 0; border: none; cursor: pointer;
      }
      input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none; width: 22px; height: 22px; border-radius: 50%;
        background: var(--surface); border: 3px solid var(--accent); cursor: pointer;
        box-shadow: 0 2px 8px rgba(0, 0, 0, .25); transition: transform .12s ease;
      }
      input[type="range"]:active::-webkit-slider-thumb { transform: scale(1.15); }
      input[type="range"]::-moz-range-thumb {
        width: 18px; height: 18px; border-radius: 50%; background: var(--surface); border: 3px solid var(--accent); cursor: pointer;
      }

      .field { display: grid; gap: 6px; min-width: 0; }
      .field > label { font-size: .78rem; font-weight: 600; color: var(--muted); }
      input, select, textarea {
        font: inherit; font-size: 16px; color: var(--text); width: 100%; min-width: 0; min-height: 44px;
        background: var(--surface-2); border: 1px solid var(--line); border-radius: 14px; padding: 10px 12px; outline: none;
        transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
      }
      textarea { min-height: 140px; resize: vertical; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
      input:focus, select:focus, textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(239, 116, 24, .16); }
      select option { background: var(--surface); color: var(--text); }

      .sw { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 13px; border-radius: var(--radius-sm); background: var(--surface-2); }
      .sw .txt { display: block; font-size: .88rem; font-weight: 600; }
      .sw .sub { display: block; font-size: .76rem; color: var(--muted); }
      input[type="checkbox"] {
        -webkit-appearance: none; appearance: none; width: 48px; min-height: 27px; height: 27px; border-radius: 999px;
        background: var(--surface-3); position: relative; cursor: pointer; flex: none; transition: background .2s; border: none; padding: 0;
      }
      input[type="checkbox"]::after {
        content: ""; position: absolute; top: 3px; left: 3px; width: 21px; height: 21px; border-radius: 50%;
        background: #fff; transition: transform .2s cubic-bezier(.3, .8, .3, 1);
      }
      input[type="checkbox"]:checked { background: linear-gradient(135deg, var(--accent), var(--ok)); }
      input[type="checkbox"]:checked::after { transform: translateX(21px); }

      .btn {
        border: 1px solid transparent; border-radius: var(--radius-sm); padding: 11px 16px; font: inherit; font-size: .88rem;
        font-weight: 650; cursor: pointer; background: var(--surface-3); color: inherit;
        display: inline-flex; align-items: center; gap: 8px; justify-content: center; min-height: 44px;
        transition: transform .15s ease, filter .15s ease, background .15s ease;
      }
      .btn:hover:not(:disabled) { transform: translateY(-1px); }
      .btn:active:not(:disabled) { transform: scale(.97); }
      .btn:disabled { opacity: .55; cursor: not-allowed; }
      .btn svg { width: 17px; height: 17px; fill: currentColor; }
      .btn--primary {
        background: linear-gradient(145deg, var(--brand-start), var(--brand-end)); color: var(--brand-ink);
        box-shadow: 0 8px 20px rgba(232, 118, 30, .22), inset 0 1px 0 rgba(255, 255, 255, .5);
      }
      .btn--primary:hover { box-shadow: 0 10px 26px rgba(232, 118, 30, .3), inset 0 1px 0 rgba(255, 255, 255, .55); }
      .btn--ghost { background: var(--surface-2); border-color: var(--line); }
      .btn--danger { background: rgba(255, 124, 138, .16); color: var(--bad); border-color: transparent; }
      .btn-row { display: flex; flex-wrap: wrap; gap: 10px; }
      .btn-row .btn { flex: 1 1 150px; }
      .cast-fields { display: grid; grid-template-columns: minmax(0, 1fr) 90px; gap: 8px; }
      .cast-fields > input { grid-column: 1 / -1; }
      .cast-fields > .btn { grid-column: 1; grid-row: 2; }
      .cast-fields > select { grid-column: 2; grid-row: 2; }
      .advanced { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 0 12px; }
      .advanced > summary { cursor: pointer; min-height: 48px; padding: 12px 0; color: var(--text); font-size: .85rem; font-weight: 650; }
      .advanced > .field { padding-bottom: 14px; gap: 14px; }

      .badge {
        display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; font-size: .74rem;
        font-weight: 700; letter-spacing: .03em; background: var(--surface-3);
        border: 1px solid var(--line); box-shadow: inset 0 1px 0 var(--glass-sheen);
      }
      .badge--ok { background: rgba(62, 227, 155, .18); color: var(--ok); }
      .badge--warn { background: rgba(255, 199, 117, .18); color: var(--amber); }
      .badge--bad { background: rgba(255, 124, 138, .18); color: var(--bad); }
      .badge--info { background: rgba(143, 125, 255, .2); color: var(--purple); }

      .msg { padding: 12px 14px; border-radius: 18px; font-size: .86rem; font-weight: 600; animation: slidein .3s ease both; }
      .msg--ok { background: rgba(62, 227, 155, .14); color: var(--ok); }
      .msg--err { background: rgba(255, 124, 138, .14); color: var(--bad); }
      .hint { font-size: .78rem; color: var(--muted); margin: 0; }

      .loading { display: grid; gap: 12px; padding: 8px 0; }
      .skel { height: 74px; border-radius: 20px; background: var(--surface-2); position: relative; overflow: hidden; }
      .skel::after {
        content: ""; position: absolute; inset: 0; transform: translateX(-100%);
        background: linear-gradient(90deg, transparent, var(--surface-3), transparent);
        animation: shimmer 1.4s infinite;
      }
      .skel--tall { height: 190px; }
      .spinner { width: 30px; height: 30px; border-radius: 50%; border: 3px solid var(--surface-3); border-top-color: var(--accent); animation: spin .9s linear infinite; }

      .cast-drawer { border-top: 1px solid var(--line); }
      .cast-drawer summary { display: flex; align-items: center; gap: 9px; list-style: none; min-height: 48px; font-size: .8rem; font-weight: 600; color: var(--muted); cursor: pointer; }
      .cast-drawer summary::-webkit-details-marker { display: none; }
      .cast-drawer summary svg { width: 18px; height: 18px; fill: var(--accent); flex: none; }
      .cast-drawer summary::after { content: "+"; margin-left: auto; font-size: 1.15rem; color: var(--accent); transition: transform .25s var(--ease); }
      .cast-drawer[open] summary::after { transform: rotate(45deg); }
      .cast-drawer[open] > form { padding-top: 2px; animation: slidein .25s var(--ease); }
      @keyframes orbit { to { transform: rotate(360deg); } }
      @keyframes sound-ripple { 0% { transform: scale(.48); opacity: 0; } 25% { opacity: .3; } 100% { transform: scale(1.22); opacity: 0; } }
      @keyframes speaker-float { 0%, 100% { transform: translateY(1px); } 50% { transform: translateY(-3px); } }
      @keyframes sound-wave { 0%, 100% { transform: scaleY(.28); } 50% { transform: scaleY(1); } }
      @keyframes glass-sweep { 0%, 15% { transform: translateX(-120%); opacity: 0; } 30% { opacity: .65; } 60%, 100% { transform: translateX(300%); opacity: 0; } }
      @keyframes rise { from { opacity: 0; transform: translateY(12px) scale(.99); } to { opacity: 1; transform: none; } }
      @keyframes slidein { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
      @keyframes pulse { from { transform: scale(.6); opacity: .7; } to { transform: scale(1.6); opacity: 0; } }
      @keyframes breathe { 0%, 100% { transform: scale(1); opacity: .8; } 50% { transform: scale(1.05); opacity: 1; } }
      @keyframes spin { to { transform: rotate(360deg); } }
      @keyframes shimmer { to { transform: translateX(100%); } }
      @keyframes eq { 0%, 100% { transform: scaleY(.25); } 50% { transform: scaleY(1); } }
      @keyframes brand-wave { 0%, 100% { transform: scaleY(.5); } 50% { transform: scaleY(1); } }
      @keyframes pill-glow {
        0%, 100% { box-shadow: 0 3px 12px rgba(232, 118, 30, .24); }
        50% { box-shadow: 0 7px 22px rgba(232, 118, 30, .42); }
      }
      .is-loading svg { animation: spin .9s linear infinite; }
      :host([data-paused]) *, :host([data-paused]) *::before, :host([data-paused]) *::after,
      [data-motion-paused] *, [data-motion-paused] *::before, [data-motion-paused] *::after { animation-play-state: paused !important; }
      :host([data-paused]), [data-motion-paused] { --maika-motion-state: paused; }
      :host([data-reduced-motion]), :host([data-reduced-motion]) *, :host([data-reduced-motion]) *::before, :host([data-reduced-motion]) *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
      @container (max-width: 440px) {
        .toolbar-main { gap: 7px; }
        .toolbar .brand .mark { width: 30px; height: 32px; border-radius: 11px; }
        .brand { gap: 7px; }
        .theme-picker svg { display: none !important; }
        .theme-picker select { width: 103px; }
        .brand small { font-size: .67rem; }
      }

      @container (max-width: 380px) { .toolbar .brand .mark { display: none; } }
      @media (hover: none) {
        .card:hover { box-shadow: var(--shadow); transform: none; border-color: var(--line); }
        .tile:hover, .chip:hover, .tbtn:hover, .btn:hover, .iconbtn:hover, .pill:hover { transform: none; }
      }
      @media (max-height: 560px) {
        .toolbar { position: relative; top: auto; }
        [data-sec] { scroll-margin-top: 12px; }
      }
      @media (pointer: coarse) {
        .toolbar, .hero, [data-card="media"] { backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
        button.chip, .pill { min-height: 44px; }
        .tbtn { width: 52px; height: 52px; }
        .tbtn--main { width: 62px; height: 62px; }
        input[type="range"]::-webkit-slider-thumb { width: 28px; height: 28px; }
        input[type="range"]::-moz-range-thumb { width: 28px; height: 28px; }
      }
      button:active:not(:disabled) { transform: scale(.96); }
      @media (prefers-reduced-motion: reduce) {
        :host, *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
        .eq i { transform: scaleY(.5); }
      }
      @media (prefers-reduced-transparency: reduce), (prefers-contrast: more), (forced-colors: active) {
        :host { background-image: none; }
        .card, .toolbar, .sheet { background: var(--surface); backdrop-filter: none; -webkit-backdrop-filter: none; }
        .hero-aura, .media-now::before { display: none; }
        dialog.playlist::backdrop { background: rgba(12, 6, 2, .82); }
      }
    `;
    return style;
  }

  _root() {
    this.dataset.theme = "dark";
    this.shadowRoot.innerHTML = "";
    this.shadowRoot.append(this._style());
    this._stage = h("div", {class: "stage"});
    this.shadowRoot.append(this._stage);
    this.shadowRoot.addEventListener("click", this._onClick);
    this.shadowRoot.addEventListener("input", this._onInput);
    this.shadowRoot.addEventListener("change", this._onChange);
    this.shadowRoot.addEventListener("submit", this._onSubmit);
    this.shadowRoot.addEventListener("pointerdown", this._onPointerDown, {passive: true});
    this.shadowRoot.addEventListener("pointermove", this._onPointerMove, {passive: true});
    this.shadowRoot.addEventListener("pointerup", this._onPointerEnd, {passive: true});
    this.shadowRoot.addEventListener("pointercancel", this._onPointerEnd, {passive: true});
    this.shadowRoot.addEventListener("lostpointercapture", this._onPointerEnd, {passive: true});
    this.shadowRoot.addEventListener("keydown", this._onSpeakerKey);
    this.shadowRoot.addEventListener("maika-voice-saved", (event) => {
      const entry = this._snapshot?.entries?.find((item) => item.entry_id === event.detail.entry_id);
      if (entry) entry.options = {...entry.options, ...event.detail.options};
      this._maybeUpdate();
    });
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
    const serials = this._serials();
    const index = serials.indexOf(this._activeSerial());
    const canSwipe = serials.length > 1;
    const activity = this._speakerActivity();
    const online = this._isOn(this._entity("binary_sensor", "online")) && !["offline", "unknown"].includes(activity);
    const image = h("img", {src: HERO_IMAGE, alt: "Loa MAIKA", decoding: "async", referrerpolicy: "no-referrer", draggable: "false", width: "180", height: "180"});
    const mediaBox = h("div", {class: "hero-media"}, [
      h("div", {class: "hero-art", "aria-hidden": "true"}, [this._speakerArt()]), image,
      h("div", {class: "hero-aura", "aria-hidden": "true"}, [h("i"), h("i"), h("i")]),
    ]);
    image.addEventListener("load", () => image.classList.add("is-ready"));
    image.addEventListener("error", () => { image.hidden = true; });
    if (image.complete && image.naturalWidth) image.classList.add("is-ready");
    const copy = h("div", {class: "hero-copy"}, [
      h("h1", {text: this._speakerName()}),
      h("p", {class: "playback-label"}, [
        h("span", {class: online ? "dot" : "dot dot--off", "aria-hidden": "true"}),
        document.createTextNode(this._activityLabel(activity)),
      ]),
      h("div", {class: "sound-wave", "aria-hidden": "true"}, [10, 17, 12, 23, 16, 24, 13, 20, 11, 18, 14, 9].map((height, index) => h("i", {style: `--bar-height:${height}px;--bar-delay:${-index * .13}s` }))),
      h("button", {class: "hero-link", type: "button", dataset: {action: "open-voice"}}, [svgIcon(ICONS.mic), "Tạo câu lệnh", svgIcon(ICONS.right)]),
    ]);
    const showcase = h("div", {
      class: "hero-showcase", role: "group", "aria-label": `Loa đang chọn: ${this._speakerName()}`,
      tabindex: canSwipe ? "0" : null, "aria-describedby": canSwipe ? "speaker-swipe-hint" : null, "aria-keyshortcuts": canSwipe ? "ArrowLeft ArrowRight" : null,
      dataset: canSwipe ? {swipe: "speakers"} : {},
    }, [copy, mediaBox]);
    const pager = canSwipe ? h("div", {class: "speaker-pager"}, [
      h("span", {class: "swipe-hint", id: "speaker-swipe-hint", text: "Vuốt để đổi loa"}),
      h("span", {class: "speaker-count", "aria-live": "polite", "aria-atomic": "true", "aria-label": `Loa ${index + 1} trên ${serials.length}`, text: `${index + 1} / ${serials.length}`}),
      h("button", {class: "iconbtn", type: "button", "aria-label": "Loa trước", disabled: this._busy || index <= 0, dataset: {action: "speaker-step", direction: "-1"}}, [svgIcon(ICONS.left)]),
      h("button", {class: "iconbtn", type: "button", "aria-label": "Loa tiếp theo", disabled: this._busy || index >= serials.length - 1, dataset: {action: "speaker-step", direction: "1"}}, [svgIcon(ICONS.right)]),
    ]) : null;
    const card = this._card("hero span2", [
      h("div", {class: "hero-heading"}, [h("span", {class: "eyebrow", text: "MAIKA SPEAKER"}), h("span", {class: "hero-account", text: entry?.title || "MAIKA", title: entry?.title || "MAIKA"})]),
      showcase, this._chips(), pager,
    ], delay);
    card.toggleAttribute("data-connected", online);
    card.toggleAttribute("data-playing", activity === "playing");
    card.dataset.activity = activity;
    return card;
  }

  _speakerActivity() {
    const state = this._state(this._entity("media_player"));
    const onlineEntity = this._entity("binary_sensor", "online");
    const online = this._state(onlineEntity)?.state;
    if (online === "off" || state?.state === "unavailable") return "offline";
    if ((onlineEntity && online !== "on") || !state || UNKNOWN.has(state.state)) return "unknown";
    if (state.state === "playing") return state.attributes?.is_volume_muted ? "muted" : "playing";
    return ["idle", "paused", "off", "on", "standby", "buffering"].includes(state.state) ? state.state : "unknown";
  }

  _activityLabel(activity) {
    return {playing: "Đang phát nhạc", muted: "Đang phát · tắt tiếng", paused: "Đã tạm dừng", off: "Đã tắt", on: "Đang bật", standby: "Chế độ chờ", buffering: "Đang tải âm thanh", idle: "Sẵn sàng", offline: "Mất kết nối", unknown: "Chưa rõ trạng thái"}[activity];
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
      ["online", "c-ok", "Trực tuyến", this._entity("binary_sensor", "online"), "online"],
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
    const volume = this._draft.volume ?? Math.round((Number(attrs.volume_level) || 0) * 100);
    const muted = Boolean(attrs.is_volume_muted);
    const playing = state?.state === "playing";
    const activity = this._speakerActivity();

    const bars = h("div", {class: activity === "playing" ? "eq" : ["eq", "eq--idle"].join(" "), "aria-hidden": "true"});
    for (let index = 0; index < 4; index += 1) bars.append(h("i"));

    const online = Boolean(state) && !UNKNOWN.has(state.state);
    const title = attrs.media_title || this._speakerName();
    const now = h("div", {class: "media-now", "data-playing": activity === "playing"}, [
      h("div", {class: "ico"}, [svgIcon(playing ? ICONS.pause : ICONS.play)]),
      h("div", {class: "media-now__body"}, [
        h("button", {
          class: "media-title",
          type: "button",
          dataset: {action: "playlist"},
          "aria-haspopup": "dialog",
          "aria-label": `Chọn bài trên ${this._speakerName()}`,
          title: online ? "Chọn bài trong danh sách trên loa" : "Loa đang mất kết nối",
          disabled: !online,
        }, [
          h("span", {class: "t", text: title}),
          svgIcon(ICONS.list),
        ]),
        h("div", {class: "s", text: this._activityLabel(activity)}),
      ]),
      bars,
    ]);

    const transport = h("div", {class: "transport"}, [
      this._tbtn("prev", "prev", media),
      this._tbtn(playing ? "pause" : "play", "playpause", media, "tbtn--main"),
      this._tbtn("stop", "stop", media, "tbtn--stop"),
      this._tbtn("next", "next", media),
      this._tbtn(muted ? "micOff" : "volume", "mute", media, muted ? "tbtn--on" : ""),
    ]);

    const range = h("input", {type: "range", min: "0", max: "100", step: "1", value: String(volume), "aria-label": "Âm lượng loa", "aria-valuetext": `${volume}%`, dataset: {field: "volume", entity: media}});
    const slider = h("div", {class: "slider"}, [
      h("span", {class: "ico"}, [svgIcon(ICONS.volume)]),
      range,
      h("span", {class: "val", text: `${volume}%`}),
    ]);

    const seek = this._seekRow(attrs, media, playing);

    const form = h("form", {class: "field", dataset: {form: "cast"}}, [
      h("label", {text: "Phát âm thanh qua cloud (URL MP3/AAC)"}),
      h("div", {class: "cast-fields"}, [
        h("input", {type: "url", name: "cast_url", placeholder: "https://.../maika.mp3", value: this._draft.cast_url || "", required: true, dataset: {field: "cast_url"}}),
        h("select", {name: "cast_type", "aria-label": "Định dạng âm thanh", dataset: {field: "cast_type"}}, [
          h("option", {value: "music", text: "Nhạc", selected: !this._draft.cast_type || this._draft.cast_type === "music"}),
          h("option", {value: "audio/mpeg", text: "MP3", selected: this._draft.cast_type === "audio/mpeg"}),
          h("option", {value: "audio/aac", text: "AAC", selected: this._draft.cast_type === "audio/aac"}),
        ]),
        h("button", {class: "btn btn--ghost", type: "submit", text: "Phát"}),
      ]),
      h("p", {class: "hint", text: "Cần bật “Cast âm thanh cloud” trong phần Cấu hình bên dưới."}),
    ]);

    return this._card("span2", [
      this._sectionHead("cast", "Điều khiển MAIKA", "Phát nhạc, âm lượng và mute", "c-purple"),
      h("div", {class: "media"}, [now, transport, slider,
        seek,
        h("details", {class: "cast-drawer"}, [
          h("summary", {}, [svgIcon(ICONS.cast), "Phát âm thanh từ đường dẫn"]), form,
        ]),
      ]),
    ], delay);
  }

  _ensurePlaylistDialog() {
    let dialog = this.shadowRoot.querySelector("dialog.playlist");
    if (dialog) {
      this._playlistDialog = dialog;
      return dialog;
    }
    dialog = h("dialog", {class: "playlist", "aria-labelledby": "playlist-heading"});
    dialog.addEventListener("close", () => this._resetPlaylist());
    dialog.addEventListener("cancel", () => { this._playlistToken += 1; });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    this.shadowRoot.append(dialog);
    this._playlistDialog = dialog;
    return dialog;
  }

  _openPlaylist() {
    const media = this._entity("media_player");
    if (!media) return;
    const state = this._state(media);
    if (!state || UNKNOWN.has(state.state)) {
      this._notify("error", "Loa đang mất kết nối, chưa xem được danh sách bài.");
      return;
    }
    if (this._playlistDialog?.open) return;
    this._playlistToken += 1;
    this._playlistReturnFocus = true;
    this._playlist = {status: "loading", items: [], entity: media, serial: this._activeSerial()};
    const dialog = this._ensurePlaylistDialog();
    this._renderPlaylist();
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    this._loadPlaylist(this._playlistToken);
  }

  _closePlaylist() {
    const dialog = this._playlistDialog;
    if (dialog?.open) dialog.close();
    else this._resetPlaylist();
  }

  _resetPlaylist() {
    this._playlistToken += 1;
    this._playlist = null;
    this._playlistBusy = false;
    if (!this._playlistReturnFocus) return;
    this._playlistReturnFocus = false;
    const opener = this.shadowRoot.querySelector('[data-action="playlist"]');
    if (opener?.isConnected) opener.focus();
  }

  async _loadPlaylist(token) {
    const media = this._playlist?.entity;
    if (!media || typeof this._hass?.callWS !== "function") {
      if (token === this._playlistToken) this._setPlaylistState("error", "Không tải được danh sách bài.");
      return;
    }
    try {
      const result = await this._hass.callWS({
        type: "media_player/browse_media",
        entity_id: media,
        media_content_type: "maika_playlist",
        media_content_id: "maika_playlist",
      });
      if (token !== this._playlistToken || !this._playlist) return;
      if (this._activeSerial() !== this._playlist.serial || this._entity("media_player") !== media) return;
      const children = Array.isArray(result?.children) ? result.children : [];
      const current = this._state(media)?.attributes?.maika_queue_item_id || "";
      const items = children
        .filter((child) => child?.media_content_type === "maika_song" && child.media_content_id)
        .map((child) => ({id: child.media_content_id, title: child.title || "Bài hát MAIKA", busy: false, current: child.media_content_id === current}));
      this._playlist = {...this._playlist, status: items.length ? "ready" : "empty", items, title: result?.title || ""};
      this._renderPlaylist();
      const focusTarget = this.shadowRoot.querySelector(".pl-item--on") || this.shadowRoot.querySelector(".pl-item") || this.shadowRoot.querySelector(".sheet__close");
      focusTarget?.focus();
    } catch (err) {
      if (token !== this._playlistToken) return;
      this._setPlaylistState("error", this._playlistError(err));
    }
  }

  _setPlaylistState(status, message) {
    if (!this._playlist) return;
    this._playlist = {...this._playlist, status, message};
    this._renderPlaylist();
  }

  _playlistError(err) {
    const key = err?.body?.message || err?.body?.error || err?.translation_key || err?.message || "";
    const labels = {
      maika_queue_unavailable: "Loa đang mất kết nối.",
      maika_queue_refresh_failed: "Không đọc được danh sách bài từ loa.",
      maika_queue_invalid_selection: "Bài này không còn trong danh sách.",
    };
    return labels[key] || "Không tải được danh sách bài.";
  }

  async _playPlaylistItem(id) {
    const playlist = this._playlist;
    if (!playlist || playlist.status !== "ready" || this._playlistBusy) return;
    const item = playlist.items.find((entry) => entry.id === id);
    if (!item || item.busy) return;
    this._playlistBusy = true;
    item.busy = true;
    this._renderPlaylist();
    try {
      await this._hass.callService("media_player", "play_media", {
        entity_id: playlist.entity,
        media_content_type: "maika_song",
        media_content_id: id,
      });
      if (this._playlist !== playlist) return;
      this._playlistBusy = false;
      this._notify("ok", "Đã chọn bài trên loa.");
      this._closePlaylist();
    } catch (err) {
      if (this._playlist !== playlist) return;
      item.busy = false;
      this._playlistBusy = false;
      playlist.status = "error";
      playlist.message = this._playlistError(err);
      this._renderPlaylist();
    }
  }

  _renderPlaylist() {
    const dialog = this._ensurePlaylistDialog();
    const playlist = this._playlist || {status: "loading", items: []};
    const rows = h("div", {class: "pl-list"});
    if (playlist.status === "loading") {
      rows.append(h("div", {class: "pl-state", role: "status", text: "Đang tải danh sách bài..."}));
    } else if (playlist.status === "empty") {
      rows.append(h("div", {class: "pl-state", text: "Loa chưa có danh sách bài. Hãy mở nhạc trên loa rồi thử lại."}));
    } else if (playlist.status === "offline") {
      rows.append(h("div", {class: "pl-state pl-state--bad", role: "alert", text: "Loa đang mất kết nối."}));
    } else if (playlist.status === "error") {
      rows.append(h("div", {class: "pl-state pl-state--bad", role: "alert", text: playlist.message || "Không tải được danh sách bài."}));
      rows.append(h("button", {class: "btn pl-retry", type: "button", dataset: {action: "playlist-retry"}, text: "Thử lại"}));
    } else {
      for (const item of playlist.items) {
        const [name, ...rest] = String(item.title).split(" — ");
        rows.append(h("button", {
          class: ["pl-item", item.current ? "pl-item--on" : ""].filter(Boolean).join(" "),
          type: "button",
          "aria-current": item.current ? "true" : null,
          dataset: {action: "playlist-item", id: item.id},
          disabled: item.busy,
        }, [
          h("span", {class: "pl-item__ico"}, [svgIcon(item.current ? ICONS.music : ICONS.play)]),
          h("span", {class: "pl-item__body"}, [
            h("span", {class: "pl-item__t", text: name}),
            rest.length ? h("span", {class: "pl-item__s", text: rest.join(" — ")}) : null,
          ]),
          item.current ? h("span", {class: "pl-item__badge", text: "Đang phát"}) : null,
          item.busy ? h("span", {class: "pl-item__badge", text: "Đang chọn..."}) : null,
        ]));
      }
    }
    const sheet = h("div", {class: "sheet", tabindex: "-1"}, [
      h("header", {class: "sheet__head"}, [
        h("h2", {id: "playlist-heading", text: playlist.title || "Danh sách bài trên loa"}),
        h("button", {class: "sheet__close", type: "button", dataset: {action: "playlist-close"}, text: "Đóng"}),
      ]),
      rows,
    ]);
    dialog.replaceChildren(sheet);
    return dialog;
  }

  _syncPlaylistCurrent() {
    if (!this._playlist || this._playlist.status !== "ready") return;
    const current = this._state(this._playlist.entity)?.attributes?.maika_queue_item_id || "";
    let changed = false;
    for (const item of this._playlist.items) {
      const isCurrent = item.id === current;
      if (item.current !== isCurrent) {
        item.current = isCurrent;
        changed = true;
      }
    }
    if (changed) this._renderPlaylist();
  }

  _tbtn(icon, action, entity, extra) {
    const labels = {prev: "Bài trước", next: "Bài tiếp theo", playpause: icon === "pause" ? "Tạm dừng" : "Phát nhạc", stop: "Dừng phát", mute: extra === "tbtn--on" ? "Bật âm lượng" : "Tắt âm lượng"};
    const state = this._state(entity);
    const features = Number(state?.attributes?.supported_features) || 0;
    const disabled = !state || UNKNOWN.has(state.state) || (action === "stop" && (features & 4096) !== 4096);
    const btn = h("button", {class: ["tbtn", extra].filter(Boolean).join(" "), type: "button", title: action === "stop" ? "Dừng âm thanh bằng tạm dừng; loa giữ vị trí phát" : labels[action], "aria-label": labels[action], "aria-pressed": action === "mute" ? String(extra === "tbtn--on") : null, disabled, dataset: {action, entity}});
    btn.append(svgIcon(ICONS[icon]));
    return btn;
  }

  _playbackPosition(attrs, playing) {
    let current = Number(attrs.media_position);
    if (!Number.isFinite(current)) current = 0;
    const updatedAt = attrs.media_position_updated_at ? Date.parse(attrs.media_position_updated_at) : NaN;
    if (playing && Number.isFinite(updatedAt)) current += Math.max(0, (Date.now() - updatedAt) / 1000);
    return Math.max(0, current);
  }

  _seekRow(attrs, entity, playing) {
    const features = Number(attrs.supported_features) || 0;
    if ((features & 2) !== 2 || !entity) return null;
    const duration = Number(attrs.media_duration);
    const hasDuration = Number.isFinite(duration) && duration > 0;
    const current = hasDuration ? Math.min(this._playbackPosition(attrs, playing), duration) : this._playbackPosition(attrs, playing);
    const items = [this._seekButton(-30, current, duration, entity, "Tua lại 30 giây")];
    if (hasDuration) {
      const max = Math.max(1, Math.round(duration));
      const range = h("input", {type: "range", min: "0", max: String(max), step: "1", value: String(Math.round(current)), "aria-label": "Vị trí phát", "aria-valuetext": `${fmtClock(current)} / ${fmtClock(duration)}`, dataset: {field: "seek", entity, duration: String(duration)}});
      range.style.setProperty("--p", `${(current / duration) * 100}%`);
      items.push(range);
      items.push(h("span", {class: "val", text: `${fmtClock(current)} / ${fmtClock(duration)}`}));
    }
    items.push(this._seekButton(30, current, duration, entity, "Tua tới 30 giây"));
    return h("div", {class: "slider slider--seek"}, items);
  }

  _seekButton(delta, position, duration, entity, label) {
    const text = `${delta > 0 ? "+" : "−"}${Math.abs(delta)}s`;
    return h("button", {class: "sbtn", type: "button", title: label, "aria-label": label, dataset: {action: "seek-step", entity, delta: String(delta), position: String(position), duration: Number.isFinite(duration) && duration > 0 ? String(duration) : ""}}, text);
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
    const select = h("select", {id: `control-${entityId}`, dataset: {action: "select", entity: entityId}});
    for (const option of options) {
      select.append(h("option", {value: option, text: option, selected: option === state?.state}));
    }
    return h("div", {class: "row row--field"}, [
      h("label", {class: "lbl", text: label, for: `control-${entityId}`}),
      select,
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
        id: `control-${entityId}`,
        value: this._draft[`text:${entityId}`] ?? (UNKNOWN.has(String(state?.state)) ? "" : String(state?.state || "")),
        dataset: {action: "text", entity: entityId, field: `text:${entityId}`},
        placeholder: label,
      });
      return h("div", {class: "row row--field"}, [
        h("label", {class: "lbl", text: label, for: `control-${entityId}`}),
        input,
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

  _historySection(delay) {
    const entry = this._entry();
    const live = this._state(this._entity("sensor", "last_voice_command"))?.attributes?.recent_commands;
    const commands = Array.isArray(live) && live.length ? live : (entry?.command_history || []);
    const body = h("div", {class: "history"});
    if (!commands.length) {
      body.append(h("p", {class: "hint", text: "Chưa có câu lệnh nào. Hãy gọi “Maika” rồi ra một câu lệnh đã cấu hình trong mục Giọng nói."}));
    } else {
      commands.forEach((command) => body.append(this._historyRow(command)));
    }
    return this._card("span4", [
      this._sectionHead("clock", "Lịch sử câu lệnh", "Câu lệnh gần đây MAIKA đã nghe và thực hiện", "c-purple"),
      body,
    ], delay);
  }

  _historyRow(command) {
    const result = command?.error ? "failed" : command?.executed ? "executed" : command?.matched_phrase ? "pending" : "not_matched";
    const icon = {executed: "check", failed: "alert", pending: "clock", not_matched: "info"}[result];
    const meta = [];
    if (command?.action && command?.target_entity_id) meta.push(`${command.action} · ${command.target_entity_id}`);
    if (command?.received_at) meta.push(fmtTime(Date.parse(command.received_at) / 1000));
    if (!meta.length) meta.push("Không tìm thấy câu lệnh phù hợp");
    return h("div", {class: `history-row history-row--${result}`}, [
      h("span", {class: "history-icon"}, [svgIcon(ICONS[icon])]),
      h("div", {class: "history-body"}, [
        h("span", {class: "history-text", text: command?.text || command?.matched_phrase || "—"}),
        h("span", {class: "history-meta", text: meta.join(" · ")}),
      ]),
      h("span", {class: `badge badge--${result === "executed" ? "ok" : result === "failed" ? "bad" : "warn"}`, text: HISTORY_RESULT_LABELS[result]}),
    ]);
  }

  _licenseReminder(license) {
    if (!license || license.plan === "lifetime") return null;
    const expiresAt = Number(license.license_expires_at ?? 0);
    if (!Number.isFinite(expiresAt) || expiresAt <= 0) return null;
    const days = Math.ceil((expiresAt * 1000 - Date.now()) / 86400000);
    if (days > LICENSE_REMINDER_DAYS) return null;
    const late = days <= 0;
    return h("div", {class: ["reminder", late ? "reminder--bad" : ""].filter(Boolean).join(" ")}, [
      this._icon(late ? "alert" : "clock", late ? "c-bad" : "c-amber"),
      h("span", {text: late
        ? "Key MAIKA đã hết hạn. Mua key mới rồi dán vào ô bên dưới để tiếp tục sử dụng."
        : `Key MAIKA còn ${days} ngày. Dán key mới vào ô bên dưới để gia hạn.`}),
    ]);
  }

  _licenseSection(delay) {
    const entry = this._entry();
    const license = entry?.license || {};
    const plan = license.plan ? planLabel(license.plan) : "Chưa kích hoạt";
    const lifetime = license.plan === "lifetime";
    const licenseExpiresAt = license.license_expires_at ?? license.expires_at ?? null;
    const expires = licenseExpiresAt ? fmtTime(licenseExpiresAt) : "Không giới hạn";
    const draftKey = this._draft["license_key"] ?? "";

    const rows = [
      this._row("Gói hiện tại", plan, "c-cyan"),
      lifetime ? null : this._row("Hạn dùng", expires, licenseExpiresAt ? "c-amber" : "c-ok"),
      this._row("Key đang dùng", license.key_hint || "—"),
      this._row("Mã cài đặt", license.activation_code || "—"),
    ];

    const form = h("form", {class: "field", dataset: {form: "license"}}, [
      h("label", {text: "License key"}),
      h("input", {type: "text", name: "license_key", placeholder: "MAIKA-XXXX-XXXX-XXXX-XXXX", value: draftKey, dataset: {field: "license_key"}, autocomplete: "off"}),
      h("div", {class: "btn-row"}, [
        h("button", {class: "btn btn--primary", type: "submit", text: "Kích hoạt / thay key", disabled: this._busy}),
        this._snapshot?.portal_url
          ? h("a", {class: "btn btn--ghost", href: this._snapshot.portal_url, target: "_blank", rel: "noreferrer", text: "Mua key / xem lịch sử"})
          : null,
      ]),
      h("p", {class: "hint", text: "Nhập key mới để nâng gói hoặc gia hạn. Hệ thống tự thay máy sang key mới, không cần admin xoá máy."}),
    ]);

    return this._card("span2", [
      this._sectionHead("key", "Bản quyền", lifetime ? "Key vĩnh viễn, không giới hạn thời gian" : "Key, gói và hạn sử dụng", "c-amber"),
      this._licenseReminder(license),
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
    const draft = this._draft;

    const value = (key, fallback) => (key in draft ? draft[key] : fallback);

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
      h("div", {class: "field"}, [
        h("label", {text: "Địa chỉ Home Assistant cho loa tải nhạc (tuỳ chọn)"}),
        h("input", {type: "url", name: "cloud_cast_base_url", placeholder: "http://192.168.1.10:8123", value: String(value("cloud_cast_base_url", options[OPTION_KEYS.castBaseUrl] || "")), dataset: {field: "cloud_cast_base_url"}}),
        h("p", {class: "hint", text: "Để trống để tự dò địa chỉ LAN. Chỉ nhập khi cast nhạc local từ Home Assistant bị lỗi."}),
      ]),
      h("div", {class: "btn-row"}, [
        h("button", {class: "btn btn--primary", type: "submit", text: "Lưu cấu hình", disabled: this._busy}),
        h("button", {class: "btn btn--ghost", type: "button", dataset: {action: "reload"}, text: "Tải lại integration"}),
      ]),
    ]);

    return this._card("span2", [
      this._sectionHead("tune", "Cấu hình loa", "Áp dụng cho mọi loa cùng tài khoản", "c-purple"),
      form,
    ], delay);
  }

  _toolbar() {
    const entries = this._snapshot?.entries || [];
    const serials = this._serials();
    const active = this._activeSerial();
    const entry = this._entry();

    const accountChips = entries.map((item, index) =>
      h("button", {
        class: ["chip", index === this._activeIndex ? "" : "chip--muted"].join(" "),
        type: "button",
        "aria-pressed": index === this._activeIndex ? "true" : "false",
        disabled: this._busy,
        title: item.title || `Tài khoản ${index + 1}`,
        dataset: {action: "entry", index: String(index)},
        text: item.title || `Tài khoản ${index + 1}`,
      })
    );

    const deviceChips = serials.map((serial) =>
      h("button", {
        class: ["chip", serial === active ? "" : "chip--muted"].join(" "),
        type: "button",
        "aria-pressed": serial === active ? "true" : "false",
        disabled: this._busy,
        title: this._deviceLabel(serial),
        dataset: {action: "device", serial},
        text: this._deviceLabel(serial),
      })
    );

    const groups = [];
    if (accountChips.length > 1) {
      groups.push(h("div", {class: "toolbar-group"}, [h("span", {class: "group-label", text: "Tài khoản"}), h("div", {class: "chips chips--scroll", role: "group", "aria-label": "Chọn tài khoản MAIKA"}, accountChips)]));
    }
    if (deviceChips.length > 1) {
      groups.push(h("div", {class: "toolbar-group"}, [h("span", {class: "group-label", text: "Chọn loa"}), h("div", {class: "chips chips--scroll", role: "group", "aria-label": "Chọn loa"}, deviceChips)]));
    }

    const nav = h("nav", {class: "nav", "aria-label": "Các mục quản lý loa"}, SECTIONS.map((section) =>
      h("button", {
        class: ["pill", section.id === this._activeSection ? "pill--on" : ""].filter(Boolean).join(" "),
        type: "button",
        "aria-current": section.id === this._activeSection ? "location" : null,
        dataset: {action: "jump", section: section.id},
        text: section.label,
      })
    ));

    return this._card("toolbar span4", [
      h("div", {class: "toolbar-main"}, [
        this._narrow ? h("button", {class: "iconbtn", type: "button", "aria-label": "Mở menu Home Assistant", dataset: {action: "menu"}}, [svgIcon(ICONS.menu)]) : null,
        h("div", {class: "brand"}, [
          h("span", {class: "mark", "aria-hidden": "true"}, [h("span", {class: "brand-wave"}, [h("i"), h("i"), h("i"), h("i")])]),
          h("span", {class: "txt"}, [
            h("b", {text: "MAIKA"}),
            h("small", {text: this._speakerName(), title: this._speakerName()}),
          ]),
        ]),
        h("label", {class: "theme-picker"}, [
          h("span", {class: "theme-sun", "aria-hidden": "true"}, [svgIcon(ICONS.sun)]),
          h("span", {class: "theme-moon", "aria-hidden": "true"}, [svgIcon(ICONS.moon)]),
          h("select", {"aria-label": "Giao diện sáng, tối hoặc tự động", title: "Tự động theo giao diện Home Assistant", dataset: {action: "theme"}}, THEME_MODES.map((mode) => h("option", {value: mode, selected: mode === this._themeMode, text: THEME_MODE_LABELS[mode]}))),
        ]),
        h("button", {
          class: `iconbtn${this._loading ? " is-loading" : ""}`,
          type: "button",
          title: "Làm mới dữ liệu loa",
          "aria-label": "Làm mới dữ liệu loa",
          disabled: this._loading,
          dataset: {action: "refreshdata"},
        }, [svgIcon(ICONS.refresh)]),
      ]),
      groups.length ? h("div", {class: "toolbar-groups"}, groups) : null,
      entry ? nav : null,
    ]);
  }

  _reducedMotion() {
    if (this._motionQuery) return this._motionQuery.matches;
    return typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;
  }

  _syncRangeFills() {
    for (const range of this.shadowRoot.querySelectorAll('input[type="range"]')) {
      const min = Number(range.min) || 0;
      const max = Number(range.max) || 100;
      const value = Number(range.value) || 0;
      const percent = max > min ? ((value - min) / (max - min)) * 100 : 0;
      range.style.setProperty("--p", `${percent.toFixed(1)}%`);
    }
  }

  _setActiveSection(section, scroll) {
    if (section) this._activeSection = section;
    for (const pill of this.shadowRoot.querySelectorAll('[data-action="jump"]')) {
      const active = pill.dataset.section === this._activeSection;
      pill.classList.toggle("pill--on", active);
      if (active) pill.setAttribute("aria-current", "location");
      else pill.removeAttribute("aria-current");
    }
    const activePill = this.shadowRoot.querySelector('.nav [aria-current="location"]');
    const nav = activePill?.parentElement;
    if (nav) {
      const pillRect = activePill.getBoundingClientRect();
      const navRect = nav.getBoundingClientRect();
      if (pillRect.left < navRect.left || pillRect.right > navRect.right) {
        nav.scrollTo({left: nav.scrollLeft + pillRect.left - navRect.left - (nav.clientWidth - pillRect.width) / 2, behavior: this._reducedMotion() ? "instant" : "smooth"});
      }
    }
    if (!scroll) return;
    const target = this._stage.querySelector(`[data-sec="${this._activeSection}"]`);
    if (target) {
      target.scrollIntoView({behavior: this._reducedMotion() ? "instant" : "smooth", block: "start"});
    }
  }

  _observeSections() {
    this._toolbarObserver?.disconnect();
    const toolbar = this._stage.querySelector(".toolbar");
    if (toolbar) {
      const resize = () => this.style.setProperty("--toolbar-offset", `${toolbar.offsetHeight + 24}px`);
      resize();
      if (typeof ResizeObserver === "function") {
        this._toolbarObserver = new ResizeObserver(resize);
        this._toolbarObserver.observe(toolbar);
      }
    }
    this._sectionObserver?.disconnect();
    this._motionObserver?.disconnect();
    if (typeof IntersectionObserver !== "function") return;
    this._motionObserver = new IntersectionObserver((records) => {
      for (const record of records) {
        record.target.toggleAttribute("data-motion-paused", !record.isIntersecting);
        if (!record.isIntersecting && record.target.dataset.card === "overview") this._onMotionChange();
      }
    }, {root: this, rootMargin: "40px"});
    for (const card of this._stage.querySelectorAll(".card:not(.toolbar)")) this._motionObserver.observe(card);
    const targets = [...this._stage.querySelectorAll("[data-sec]")];
    if (!targets.length) return;
    const intersections = new Map();
    this._sectionObserver = new IntersectionObserver((records) => {
      for (const record of records) intersections.set(record.target, record);
      const visible = [...intersections.values()]
        .filter((record) => record.isIntersecting)
        .sort((first, second) => first.target.getBoundingClientRect().top - second.target.getBoundingClientRect().top)[0];
      if (!visible) return;
      const section = visible.target.dataset.sec;
      if (section !== this._activeSection) this._setActiveSection(section, false);
    }, {root: this, rootMargin: `-${(toolbar?.offsetHeight || 0) + 24}px 0px -35% 0px`, threshold: 0});
    for (const target of targets) this._sectionObserver.observe(target);
  }

  _render() {
    if (!this._stage) return;
    const cards = [["toolbar", this._toolbar()]];
    const message = h("div", {
      class: `msg msg--${this._message?.type === "ok" ? "ok" : "err"} span4`,
      hidden: !this._message,
      role: "status",
      "aria-live": "polite",
      text: this._message?.text || "",
    });
    cards.push(["message", message]);
    if (!this._snapshot) {
      if (this._loading) cards.push(["loading", this._card("span4", [h("div", {class: "loading", role: "status", "aria-label": "Đang tải dữ liệu loa"}, [
          h("div", {class: ["skel", "skel--tall"].join(" ")}),
          h("div", {class: "skel"}),
          h("div", {class: "skel"}),
          h("span", {class: "hint", text: "Đang tải dữ liệu loa..."}),
        ])])]);
    } else if (!this._entry()) {
      cards.push(["empty",
        this._card("span2", [
          this._sectionHead("speaker", "Chưa có loa MAIKA", "Hãy thêm integration MAIKA Speaker trước", "c-bad"),
          h("p", {class: "hint", text: "Vào Settings → Devices & services → Add integration → MAIKA Speaker."}),
        ]),
      ]);
    } else {
      cards.push(
        ["overview", this._heroCard(30)],
        ["media", this._mediaSection(60)],
        ["voice", this._card("span4", [h("maika-voice-editor")], 90)],
        ["history", this._historySection(105)],
        ["status", this._statusSection(90)],
        ["assistant", this._assistantSection(120)],
        ["identity", this._identitySection(150)],
        ["info", this._deviceSection(180)],
        ["firmware", this._firmwareSection(210)],
        ["warranty", this._warrantySection(240)],
        ["tools", this._toolsSection(270)],
        ["license", this._licenseSection(300)],
        ["settings", this._settingsSection(330)],
      );
    }
    const previous = new Map([...this._stage.children].map((card) => [card.dataset.card, card]));
    let cursor = this._stage.firstElementChild;
    let structureChanged = false;
    for (const [section, card] of cards) {
      if (!card) continue;
      card.dataset.card = section;
      if (SECTIONS.some((item) => item.id === section)) card.dataset.sec = section;
      this._labelFields(card);
      const current = previous.get(section);
      const node = current ? this._patchNode(current, card) : card;
      if (node !== cursor) {
        this._stage.insertBefore(node, cursor);
        structureChanged = true;
      }
      cursor = node.nextElementSibling;
      previous.delete(section);
    }
    for (const card of previous.values()) { card.remove(); structureChanged = true; }
    this._stage.setAttribute("aria-busy", String(this._loading || this._busy));
    this._syncRangeFills();
    this._syncVoiceEditor();
    this._applyMotion();
    if (structureChanged) this._observeSections();
  }

  _labelFields(card) {
    for (const label of card.querySelectorAll(".field > label:not(.sw)")) {
      const sibling = label.nextElementSibling;
      const controls = "input:not([type=checkbox]), select, textarea";
      const input = sibling?.matches(controls) ? sibling : sibling?.querySelector(controls);
      if (!input || label.htmlFor) continue;
      input.id = input.id || `field-${input.dataset.field || input.name}`;
      label.htmlFor = input.id;
    }
  }

  _patchNode(current, next) {
    if (current.nodeType !== next.nodeType || current.nodeName !== next.nodeName) {
      current.replaceWith(next);
      return next;
    }
    if (current.nodeType === Node.TEXT_NODE) {
      if (current.textContent !== next.textContent) current.textContent = next.textContent;
      return current;
    }
    const focused = current === this.shadowRoot.activeElement;
    if (current.tagName === "IMG" && current.getAttribute("src") === next.getAttribute("src")) return current;
    const preserveAttribute = (name) => name === "data-motion-paused" || (current.tagName === "DETAILS" && name === "open") || (focused && name === "value");
    for (const {name} of [...current.attributes]) {
      if (!next.hasAttribute(name) && !preserveAttribute(name)) current.removeAttribute(name);
    }
    for (const {name, value} of next.attributes) {
      if (!preserveAttribute(name) && current.getAttribute(name) !== value) current.setAttribute(name, value);
    }
    const nextValue = next.value;
    if (focused && current.tagName === "SELECT") return current;
    if (current.tagName !== "TEXTAREA") {
      const children = [...current.childNodes];
      const nextChildren = [...next.childNodes];
      nextChildren.forEach((child, index) => {
        if (children[index]) this._patchNode(children[index], child);
        else current.append(child);
      });
      for (const child of children.slice(nextChildren.length)) child.remove();
    }
    if (["INPUT", "SELECT", "TEXTAREA"].includes(current.tagName) && !focused) {
      if (current.value !== nextValue) current.value = nextValue;
      if (current.tagName === "INPUT") current.checked = next.checked;
    }
    return current;
  }

  _signature() {
    const entry = this._entry();
    const states = {};
    const entities = entry?.device_entities?.[this._activeSerial()] || entry?.entities || {};
    for (const ids of Object.values(entities)) {
      for (const id of ids) {
        const state = this._hass?.states?.[id];
        if (state) {
          const attrs = state.attributes || {};
          states[id] = [state.state, attrs.options, attrs.volume_level, attrs.is_volume_muted, attrs.media_title, attrs.supported_features, attrs.media_position, attrs.media_duration, attrs.media_position_updated_at, attrs.maika_song_key, attrs.maika_queue_item_id];
        }
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
      loading: this._loading,
      message: this._message,
      narrow: this._narrow,
    });
  }

  _maybeUpdate() {
    const signature = this._signature();
    if (signature === this._lastSignature) { this._syncVoiceEditor(); this._syncPlaylistCurrent(); return; }
    this._lastSignature = signature;
    this._render();
    this._syncPlaylistCurrent();
  }

  _syncVoiceEditor() {
    this.shadowRoot.querySelector("maika-voice-editor")?.configure({
      hass: this._hass,
      entry: this._entry(),
      catalog: this._snapshot?.voice_actions,
      limits: this._snapshot?.voice_limits,
    });
  }

  async _load() {
    if (this._loading) return;
    this._loading = true;
    this._maybeUpdate();
    try {
      const snapshot = await this._hass.callApi("GET", API);
      this._snapshot = snapshot;
      if (this._activeIndex >= (snapshot.entries || []).length) this._activeIndex = 0;
    } catch (err) {
      this._message = {type: "error", text: `Không tải được dữ liệu panel: ${this._errorText(err)}`};
    }
    this._loading = false;
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
      invalid_cloud_cast_base_url: "Địa chỉ Home Assistant không hợp lệ",
      invalid_voice_command_rules: "Rule câu lệnh không hợp lệ",
      voice_success_audio_media_player_invalid: "Media player không tồn tại",
      voice_success_audio_url_invalid: "URL MP3 không hợp lệ",
      invalid_voice_success_audio_path: "File MP3 không còn trong thư viện",
      audio_library_unavailable: "Không tạo được liên kết tới file MP3. Kiểm tra địa chỉ truy cập Home Assistant (Settings → System → Network) và Cast âm thanh cloud.",
      unknown_entry: "Không tìm thấy loa",
    };
    return labels[code] || code || "Lỗi không xác định";
  }

  _notify(type, text) {
    this._message = {type, text};
    this._lastSignature = "";
    this._maybeUpdate();
  }

  _selectDevice(serial) {
    const serials = this._serials();
    const current = this._activeSerial();
    if (this._busy || this.shadowRoot.querySelector("maika-voice-editor")?.isBusy || !serials.includes(serial) || serial === current) return false;
    const direction = serials.indexOf(serial) > serials.indexOf(current) ? 1 : -1;
    this._closePlaylist();
    this._cancelGesture();
    this._deviceAnimation?.cancel();
    this._deviceSerial = serial;
    for (const field of Object.keys(this._draft)) {
      if (["volume", "cast_url", "cast_type"].includes(field) || field.startsWith("text:")) delete this._draft[field];
    }
    this._lastSignature = "";
    this._maybeUpdate();
    this._setActiveSection("overview", false);
    const showcase = this.shadowRoot.querySelector(".hero-showcase");
    if (!this._reducedMotion() && !document.hidden && !showcase?.closest("[data-motion-paused]") && showcase?.animate) {
      const animation = showcase.animate([
        {opacity: .65, transform: `translate3d(${direction * 22}px,0,0)`},
        {opacity: 1, transform: "translate3d(0,0,0)"},
      ], {duration: 280, easing: "cubic-bezier(.22,1,.36,1)"});
      this._deviceAnimation = animation;
      animation.finished.catch(() => {}).then(() => { if (this._deviceAnimation === animation) this._deviceAnimation = null; });
    }
    return true;
  }

  _stepSpeaker(direction) {
    if (![1, -1].includes(direction)) return false;
    const serials = this._serials();
    return this._selectDevice(serials[serials.indexOf(this._activeSerial()) + direction]);
  }

  _onSpeakerKey(event) {
    if (!event.target.matches?.("[data-swipe]") || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    this._stepSpeaker(event.key === "ArrowRight" ? 1 : -1);
  }

  _onPointerDown(event) {
    if (!event.isPrimary) { this._cancelGesture(); return; }
    const surface = event.target.closest?.("[data-swipe]");
    if (!surface || event.button !== 0 || this._busy || this.shadowRoot.querySelector("maika-voice-editor")?.isBusy || event.target.closest("button,input,select,textarea,a,summary")) return;
    this._cancelGesture();
    this._deviceAnimation?.cancel();
    this._gesture = {
      pointerId: event.pointerId, surface, startX: event.clientX, startY: event.clientY,
      deltaX: 0, deltaY: 0, horizontal: false, startedAt: event.timeStamp,
      entryId: this._entry()?.entry_id, serial: this._activeSerial(),
    };
  }

  _onPointerMove(event) {
    const gesture = this._gesture;
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    gesture.deltaX = event.clientX - gesture.startX;
    gesture.deltaY = event.clientY - gesture.startY;
    if (!gesture.horizontal) {
      if (Math.max(Math.abs(gesture.deltaX), Math.abs(gesture.deltaY)) < 10) return;
      if (Math.abs(gesture.deltaY) >= Math.abs(gesture.deltaX) / 1.4) { this._cancelGesture(); return; }
      gesture.horizontal = true;
      try { gesture.surface.setPointerCapture(event.pointerId); } catch {}
    }
    if (this._reducedMotion() || this._gestureFrame !== null) return;
    this._gestureFrame = requestAnimationFrame(() => {
      this._gestureFrame = null;
      if (this._gesture !== gesture) return;
      const serials = this._serials();
      const nextIndex = serials.indexOf(gesture.serial) + (gesture.deltaX < 0 ? 1 : -1);
      const resistance = serials[nextIndex] ? .28 : .08;
      const offset = Math.max(-65, Math.min(65, gesture.deltaX * resistance));
      this.style.setProperty("--swipe-offset", `${offset}px`);
      this.setAttribute("data-swiping", "");
    });
  }

  _onPointerEnd(event) {
    const gesture = this._gesture;
    if (!gesture || event.pointerId !== gesture.pointerId) return;
    if (event.type === "lostpointercapture" && (event.target !== gesture.surface || gesture.surface.hasPointerCapture?.(event.pointerId))) return;
    this._cancelGesture();
    if (event.type !== "pointerup" || !gesture.horizontal || gesture.entryId !== this._entry()?.entry_id || gesture.serial !== this._activeSerial()) return;
    const deltaX = event.clientX - gesture.startX;
    const deltaY = event.clientY - gesture.startY;
    const threshold = Math.min(80, Math.max(48, gesture.surface.clientWidth * .16));
    if (Math.abs(deltaX) < threshold || Math.abs(deltaX) < Math.abs(deltaY) * 1.4 || event.timeStamp - gesture.startedAt > 1200) return;
    this._stepSpeaker(deltaX < 0 ? 1 : -1);
  }

  _cancelGesture() {
    const gesture = this._gesture;
    this._gesture = null;
    if (this._gestureFrame !== null) cancelAnimationFrame(this._gestureFrame);
    this._gestureFrame = null;
    this.removeAttribute("data-swiping");
    this.style.removeProperty("--swipe-offset");
    if (gesture?.surface.hasPointerCapture?.(gesture.pointerId)) gesture.surface.releasePointerCapture(gesture.pointerId);
  }

  _onInput(event) {
    const el = event.target;
    const field = el?.dataset?.field;
    if (!field) return;
    if (el.type === "checkbox") return;
    this._draft[field] = el.value;
    if (field === "volume") {
      el.setAttribute("aria-valuetext", `${el.value}%`);
      const label = el.parentElement?.querySelector(".val");
      if (label) label.textContent = `${el.value}%`;
      const min = Number(el.min) || 0;
      const max = Number(el.max) || 100;
      const percent = max > min ? ((Number(el.value) - min) / (max - min)) * 100 : 0;
      el.style.setProperty("--p", `${percent.toFixed(1)}%`);
    } else if (field === "seek") {
      const total = Number(el.dataset.duration) || 0;
      const label = el.parentElement?.querySelector(".val");
      if (label && total > 0) label.textContent = `${fmtClock(Number(el.value))} / ${fmtClock(total)}`;
      const percent = total > 0 ? (Number(el.value) / total) * 100 : 0;
      el.style.setProperty("--p", `${percent.toFixed(1)}%`);
    }
  }

  _onChange(event) {
    const el = event.target;
    if (!el?.dataset) return;
    if (el.dataset.field) {
      this._draft[el.dataset.field] = el.type === "checkbox" ? el.checked : el.value;
    }
    const action = el.dataset.action;
    if (action === "theme") {
      this._setTheme(el.value);
      return;
    }
    if (!action) {
      if (el.dataset.field === "seek" && el.dataset.entity) {
        const position = Math.max(0, Number(el.value) || 0);
        delete this._draft.seek;
        this._callService("media_player", "media_seek", {entity_id: el.dataset.entity, seek_position: position}, "Đã tua tới vị trí mới.");
        return;
      }
      if (el.dataset.field === "volume" && el.dataset.entity) {
        const level = Math.min(1, Math.max(0, Number(el.value) / 100));
        delete this._draft.volume;
        this._callService("media_player", "volume_set", {entity_id: el.dataset.entity, volume_level: level});
      }
      return;
    }
    if (action === "select") {
      this._callService("select", "select_option", {entity_id: el.dataset.entity, option: el.value});
    } else if (action === "switch") {
      this._callService("switch", el.checked ? "turn_on" : "turn_off", {entity_id: el.dataset.entity});
    } else if (action === "text") {
      delete this._draft[el.dataset.field];
      this._callService("text", "set_value", {entity_id: el.dataset.entity, value: el.value});
    }
  }

  _onClick(event) {
    const target = event.target.closest?.("[data-action]");
    if (!target || target.tagName === "A") return;
    const action = target.dataset.action;
    const entity = target.dataset.entity;

    if (action === "playlist") {
      this._openPlaylist();
      return;
    }

    if (action === "playlist-close") {
      this._closePlaylist();
      return;
    }

    if (action === "playlist-retry") {
      if (!this._playlist) return;
      this._playlistToken += 1;
      this._playlistBusy = false;
      this._playlist = {...this._playlist, status: "loading", message: null};
      this._renderPlaylist();
      this._loadPlaylist(this._playlistToken);
      return;
    }

    if (action === "playlist-item") {
      this._playPlaylistItem(target.dataset.id);
      return;
    }

    if (action === "entry") {
      if (this._busy) return;
      if (Number(target.dataset.index) === this._activeIndex) return;
      const editor = this.shadowRoot.querySelector("maika-voice-editor");
      if (editor?.isBusy) return;
      if (editor?.hasUnsavedChanges && !window.confirm("Đổi tài khoản và bỏ bản nháp giọng nói chưa lưu?")) return;
      this._closePlaylist();
      this._onMotionChange();
      this._activeIndex = Number(target.dataset.index) || 0;
      this._deviceSerial = "";
      this._draft = {};
      this._message = null;
      this._activeSection = "overview";
      this._lastSignature = "";
      this._maybeUpdate();
      return;
    }

    if (action === "device") {
      this._selectDevice(target.dataset.serial);
      return;
    }

    if (action === "seek-step") {
      if (!entity) return;
      const state = this._state(entity);
      if (!state || UNKNOWN.has(state.state)) return;
      const attrs = state.attributes || {};
      const position = this._playbackPosition(attrs, state.state === "playing");
      const duration = Number(attrs.media_duration) || 0;
      const delta = Number(target.dataset.delta) || 0;
      let next = position + delta;
      if (next < 0) next = 0;
      if (duration > 0 && next > duration) next = duration;
      this._callService("media_player", "media_seek", {entity_id: entity, seek_position: next}, "Đã tua tới vị trí mới.");
      return;
    }

    if (action === "speaker-step") {
      this._stepSpeaker(Number(target.dataset.direction));
      return;
    }

    if (action === "open-voice") {
      this._setActiveSection("voice", true);
      return;
    }

    if (action === "menu") {
      this.dispatchEvent(new CustomEvent("hass-toggle-menu", {bubbles: true, composed: true}));
      return;
    }

    if (action === "jump") {
      this._setActiveSection(target.dataset.section, true);
      return;
    }

    if (action === "refreshdata") {
      this._message = null;
      this._lastSignature = "";
      this._load();
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
      stop: ["media_player", "media_stop", {}],
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
    if (this._busy || this.shadowRoot.querySelector("maika-voice-editor")?.isBusy) return;

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
      if (!licenseKey) {
        this._notify("error", "Nhập license key trước khi kích hoạt.");
        return;
      }
      this._busy = true;
      this._maybeUpdate();
      const result = await this._post(`${API}/license`, {
        entry_id: entry.entry_id,
        license_key: licenseKey,
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
        [OPTION_KEYS.castBaseUrl]: String(form.elements.namedItem("cloud_cast_base_url")?.value || "").trim(),
      };
      this._busy = true;
      this._maybeUpdate();
      const result = await this._post(`${API}/options`, {entry_id: entry.entry_id, options});
      this._busy = false;
      if (result.ok) {
        delete this._draft.scan_interval;
        delete this._draft.cloud_cast;
        delete this._draft.cloud_cast_base_url;
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
