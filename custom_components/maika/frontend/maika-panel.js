/* MAIKA Speaker management panel for Home Assistant. */
const API = "maika/panel";

const PLAN_LABELS = {
  trial_1d: "Trải nghiệm 1 ngày",
  month_1: "Gói 1 tháng",
  month_6: "Gói 6 tháng",
  lifetime: "Vĩnh viễn",
};

const AUDIO_SOURCE_LABELS = {
  disabled: "Tắt",
  bundled: "MAIKA mặc định",
  custom: "URL tuỳ chọn",
};

const AUDIO_TIMING_LABELS = {
  priority: "Ưu tiên (che giọng loa)",
  after_success: "Sau khi điều khiển thành công",
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

function fmtTime(value) {
  if (!value) return "—";
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("vi-VN", {dateStyle: "short", timeStyle: "short"});
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

class MaikaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._hass = null;
    this._snapshot = null;
    this._selected = {};
    this._busy = false;
    this._message = null;
    this._lastSignature = "";
    this._loaded = false;
    this._onClick = this._onClick.bind(this);
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
  }

  _root() {
    this.shadowRoot.innerHTML = "";
    this.shadowRoot.append(this._style());
    this._stage = h("div", {class: "stage"});
    this.shadowRoot.append(this._stage);
    this.shadowRoot.addEventListener("click", this._onClick);
    this.shadowRoot.addEventListener("change", this._onChange);
    this.shadowRoot.addEventListener("submit", this._onSubmit);
  }

  _style() {
    const style = document.createElement("style");
    style.textContent = `
      :host { display: block; min-height: 100vh; background: var(--primary-background-color, #06101c); color: var(--primary-text-color, #edf8ff); }
      * { box-sizing: border-box; }
      .stage { max-width: 1180px; margin: 0 auto; padding: 20px 16px 60px; display: grid; gap: 18px; }
      .hero { position: relative; overflow: hidden; border-radius: 22px; padding: 22px; border: 1px solid rgba(132,204,255,.18);
        background: radial-gradient(120% 120% at 12% 0%, rgba(47,228,208,.18), transparent 55%),
                    radial-gradient(120% 120% at 92% 4%, rgba(157,139,255,.16), transparent 52%),
                    linear-gradient(160deg, #0b1f33, #071523 70%);
        display: flex; flex-wrap: wrap; gap: 18px; align-items: center; justify-content: space-between; }
      .hero h1 { margin: 2px 0 4px; font-size: 1.5rem; letter-spacing: -.01em; }
      .hero p { margin: 0; color: #9fb3c6; font-size: .9rem; }
      .brand { display: flex; align-items: center; gap: 12px; }
      .brand-mark { width: 46px; height: 46px; border-radius: 14px; display: grid; place-items: center; font-weight: 900; color: #04121a;
        background: linear-gradient(135deg, #2fe4d0, #6ff0a8); box-shadow: 0 0 34px rgba(47,228,208,.3); }
      .hero-actions { display: flex; gap: 10px; flex-wrap: wrap; }
      .grid { display: grid; gap: 18px; grid-template-columns: minmax(0, 1.15fr) minmax(0, .85fr); align-items: start; }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
      .card { border: 1px solid rgba(132,204,255,.16); border-radius: 20px; padding: 18px; background: linear-gradient(150deg, rgba(13,32,49,.92), rgba(7,21,35,.94)); }
      .card h2 { margin: 0 0 4px; font-size: 1.02rem; }
      .card .sub { margin: 0 0 14px; color: #93a8bb; font-size: .82rem; }
      .pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; font-size: .74rem; font-weight: 700;
        border: 1px solid rgba(47,228,208,.4); background: rgba(47,228,208,.12); color: #b6fff2; }
      .pill.warn { border-color: rgba(255,210,122,.4); background: rgba(255,210,122,.12); color: #ffe6b4; }
      .pill.bad { border-color: rgba(255,113,137,.42); background: rgba(255,113,137,.12); color: #ffc3cf; }
      .pill.off { border-color: rgba(148,177,211,.3); background: rgba(148,177,211,.12); color: #c6d4e2; }
      .info { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin: 0; }
      .info div { background: rgba(4,14,24,.5); border: 1px solid rgba(132,204,255,.12); border-radius: 12px; padding: 10px 12px; }
      .info dt { color: #8ba0b4; font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; margin: 0 0 4px; }
      .info dd { margin: 0; font-size: .92rem; overflow-wrap: anywhere; }
      .speaker { display: grid; place-items: center; gap: 12px; }
      .speaker svg { width: 132px; height: 132px; }
      .ring { animation: pulse 2.6s ease-in-out infinite; }
      @keyframes pulse { 0%,100% { opacity: .35; } 50% { opacity: .9; } }
      .row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
      button, select, input, textarea { font: inherit; color: #eaf6ff; }
      button { cursor: pointer; border-radius: 11px; border: 1px solid rgba(148,177,211,.28); background: rgba(255,255,255,.04); padding: 9px 13px; }
      button:hover { border-color: #2fe4d0; }
      button:disabled { opacity: .5; cursor: not-allowed; }
      button.primary { border: 0; color: #04121a; font-weight: 800; background: linear-gradient(120deg, #2fe4d0, #6ff0a8); }
      button.ghost { background: transparent; }
      select, input[type="text"], input[type="url"], input[type="number"], input[type="password"], textarea {
        width: 100%; min-height: 42px; padding: 9px 12px; border-radius: 11px; border: 1px solid rgba(148,177,211,.24); background: rgba(2,10,18,.55); }
      textarea { min-height: 110px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .82rem; }
      input[type="range"] { width: 100%; min-height: auto; padding: 0; }
      label.field { display: grid; gap: 6px; font-size: .84rem; color: #c6d7e6; }
      .form-grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
      .check { display: flex; align-items: center; gap: 10px; }
      .check input { width: auto; min-height: auto; }
      .sensors { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
      .sensor { background: rgba(4,14,24,.5); border: 1px solid rgba(132,204,255,.12); border-radius: 12px; padding: 10px 12px; }
      .sensor small { display: block; color: #8ba0b4; font-size: .72rem; margin-bottom: 4px; }
      .sensor strong { font-size: 1.05rem; }
      .muted { color: #8ba0b4; font-size: .82rem; }
      .notice { border-radius: 12px; padding: 10px 13px; font-size: .85rem; border: 1px solid rgba(47,228,208,.3); background: rgba(47,228,208,.1); color: #bdfff3; }
      .notice.error { border-color: rgba(255,113,137,.35); background: rgba(255,113,137,.12); color: #ffc6d1; }
      code { overflow-wrap: anywhere; color: #84ebff; }
      .chip-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
      .chip { border-radius: 999px; padding: 7px 13px; font-size: .84rem; border: 1px solid rgba(148,177,211,.28); background: rgba(255,255,255,.04); }
      .chip.active { border-color: #2fe4d0; background: rgba(47,228,208,.14); color: #cbfff6; }
      .kv { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px dashed rgba(148,177,211,.16); font-size: .86rem; }
      .kv:last-child { border-bottom: 0; }
      .divider { height: 1px; background: rgba(148,177,211,.16); margin: 14px 0; }
    `;
    return style;
  }

  _signature() {
    if (!this._snapshot) return "";
    const parts = [];
    for (const entry of this._snapshot.entries) {
      for (const ids of Object.values(entry.entities)) {
        for (const id of ids) {
          const state = this._hass.states[id];
          parts.push(id + "=" + (state ? state.state : "?"));
        }
      }
    }
    return parts.join("|");
  }

  _maybeUpdate() {
    const signature = this._signature();
    if (signature === this._lastSignature) return;
    this._lastSignature = signature;
    this._render();
  }

  async _load() {
    try {
      this._snapshot = await this._hass.callApi("GET", API);
      this._message = null;
    } catch (error) {
      this._message = {text: "Không tải được dữ liệu MAIKA: " + (error?.message || error), error: true};
    }
    this._lastSignature = "";
    this._render();
  }

  _post(path, payload) {
    return this._hass.callApi("POST", path, payload);
  }

  _flash(text, error = false) {
    this._message = {text, error};
    this._render();
    if (!error) window.setTimeout(() => { this._message = null; this._render(); }, 4000);
  }

  _selectedSerial(entry) {
    const serials = Object.keys(entry.devices);
    if (!serials.length) return null;
    const current = this._selected[entry.entry_id];
    if (current && serials.includes(current)) return current;
    this._selected[entry.entry_id] = serials[0];
    return serials[0];
  }

  _render() {
    if (!this._stage) return;
    this._stage.innerHTML = "";
    const snapshot = this._snapshot;
    this._stage.append(this._hero(snapshot));
    if (this._message) {
      this._stage.append(h("div", {class: "notice" + (this._message.error ? " error" : ""), text: this._message.text}));
    }
    if (!snapshot) {
      this._stage.append(h("p", {class: "muted", text: "Đang tải…"}));
      return;
    }
    if (!snapshot.entries.length) {
      this._stage.append(h("p", {class: "muted", text: "Chưa có cấu hình MAIKA nào. Hãy thêm tích hợp MAIKA trước."}));
      return;
    }
    for (const entry of snapshot.entries) this._stage.append(this._entry(entry, snapshot));
  }

  _hero(snapshot) {
    const hero = h("div", {class: "hero"}, [
      h("div", {class: "brand"}, [
        h("span", {class: "brand-mark", text: "M"}),
        h("div", {}, [
          h("h1", {text: "MAIKA Speaker"}),
          h("p", {text: "Quản lý loa, key bản quyền và cấu hình ngay trong Home Assistant."}),
        ]),
      ]),
      h("div", {class: "hero-actions"}, [
        h("button", {
          class: "ghost",
          text: "Tải lại dữ liệu",
          onClick: () => this._load(),
        }),
        snapshot && snapshot.portal_url
          ? h("a", {href: snapshot.portal_url, target: "_blank", rel: "noopener noreferrer"}, [
              h("button", {class: "primary", text: "Mua / gia hạn key"}),
            ])
          : null,
      ]),
    ]);
    return hero;
  }

  _entry(entry, snapshot) {
    const wrap = h("div", {class: "grid"});
    const left = h("div", {class: "card"});
    const right = h("div", {class: "card"});
    wrap.append(left, right);

    left.append(this._speakerCard(entry, snapshot));
    left.append(h("div", {class: "divider"}));
    left.append(h("h2", {text: "Cảm biến & thông số"}));
    left.append(h("p", {class: "sub", text: "Giá trị hiện tại do tích hợp MAIKA cung cấp."}));
    left.append(this._sensors(entry));

    right.append(this._licenseCard(entry, snapshot));
    right.append(h("div", {class: "divider"}));
    right.append(this._controls(entry));
    right.append(h("div", {class: "divider"}));
    right.append(this._settings(entry, snapshot));
    return wrap;
  }

  _speakerCard(entry, snapshot) {
    const card = h("div", {});
    const serials = Object.keys(entry.devices);
    if (serials.length > 1) {
      const chips = h("div", {class: "chip-row"});
      const selected = this._selectedSerial(entry);
      for (const serial of serials) {
        const device = entry.devices[serial];
        chips.append(h("button", {
          class: "chip" + (serial === selected ? " active" : ""),
          text: device.calling_name || device.name || serial.slice(-4),
          dataset: {serial},
          onClick: () => { this._selected[entry.entry_id] = serial; this._render(); },
        }));
      }
      card.append(chips);
    }
    const serial = this._selectedSerial(entry);
    if (!serial) {
      card.append(h("h2", {text: "Loa MAIKA"}));
      card.append(h("p", {class: "muted", text: "Chưa phát hiện loa nào."}));
      return card;
    }
    const device = entry.devices[serial];
    const online = Boolean(device.online);
    const name = device.calling_name || device.name || "MAIKA " + serial.slice(-4);

    const header = h("div", {class: "speaker"}, [
      this._speakerArt(online),
      h("span", {class: "pill " + (online ? "" : "off"), text: online ? "● Online" : "○ Offline"}),
    ]);

    const info = h("dl", {class: "info"}, [
      ["Tên loa", name],
      ["Model", device.model || "—"],
      ["Hãng", device.manufacturer || "—"],
      ["Số serial", serial],
      ["Firmware", device.firmware_version || "—"],
      ["Trạng thái", device.status || (online ? "online" : "offline")],
      ["Âm lượng", device.volume != null ? device.volume + "%" : "—"],
      ["Mic", device.mute ? "Đang tắt" : "Đang bật"],
      ["Wifi", this._wifi(device) || "—"],
      ["Địa chỉ", device.address || "—"],
      ["Gọi được", device.available_to_call ? "Có" : "Không"],
      ["Yêu thích", device.is_favorite ? "Có" : "Không"],
    ].map(([label, value]) => h("div", {}, [h("dt", {text: label}), h("dd", {text: String(value)})])));

    card.append(h("h2", {text: name}));
    card.append(h("p", {class: "sub", text: "Thông tin loa, kết nối và trạng thái phát."}));
    card.append(header);
    card.append(info);
    const playback = this._playback(device);
    if (playback) {
      card.append(h("div", {class: "divider"}));
      card.append(playback);
    }
    return card;
  }

  _wifi(device) {
    const list = device.wifi;
    if (!Array.isArray(list)) return "";
    const connected = list.find((item) => item && item.connected) || list[0];
    return connected && connected.ssid ? String(connected.ssid) : "";
  }

  _playback(device) {
    const current = device.current_playback;
    if (!current || typeof current !== "object") return null;
    const title = current.title || current.name || current.song_name || current.media_title;
    const artist = current.artist || current.singer || current.author;
    const status = current.status || current.state;
    if (!title && !artist && !status) return null;
    const rows = h("div", {});
    rows.append(h("h2", {text: "Đang phát"}));
    const kv = h("div", {});
    if (status) kv.append(h("div", {class: "kv"}, [h("span", {text: "Trạng thái"}), h("strong", {text: String(status)})]));
    if (title) kv.append(h("div", {class: "kv"}, [h("span", {text: "Bài / nội dung"}), h("strong", {text: String(title)})]));
    if (artist) kv.append(h("div", {class: "kv"}, [h("span", {text: "Nghệ sĩ"}), h("strong", {text: String(artist)})]));
    rows.append(kv);
    return rows;
  }

  _speakerArt(online) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 120 120");
    const ring = document.createElementNS(ns, "circle");
    ring.setAttribute("cx", "60");
    ring.setAttribute("cy", "60");
    ring.setAttribute("r", "52");
    ring.setAttribute("fill", "none");
    ring.setAttribute("stroke", online ? "#2fe4d0" : "#5b7180");
    ring.setAttribute("stroke-width", "2");
    ring.setAttribute("opacity", "0.5");
    if (online) ring.setAttribute("class", "ring");
    const body = document.createElementNS(ns, "rect");
    body.setAttribute("x", "38");
    body.setAttribute("y", "26");
    body.setAttribute("width", "44");
    body.setAttribute("height", "68");
    body.setAttribute("rx", "18");
    body.setAttribute("fill", "url(#maikaGrad)");
    const defs = document.createElementNS(ns, "defs");
    const grad = document.createElementNS(ns, "linearGradient");
    grad.setAttribute("id", "maikaGrad");
    grad.setAttribute("x1", "0");
    grad.setAttribute("y1", "0");
    grad.setAttribute("x2", "1");
    grad.setAttribute("y2", "1");
    for (const [offset, color] of [["0%", "#2fe4d0"], ["100%", "#6ff0a8"]]) {
      const stop = document.createElementNS(ns, "stop");
      stop.setAttribute("offset", offset);
      stop.setAttribute("stop-color", color);
      grad.append(stop);
    }
    defs.append(grad);
    const hole = document.createElementNS(ns, "circle");
    hole.setAttribute("cx", "60");
    hole.setAttribute("cy", "48");
    hole.setAttribute("r", "12");
    hole.setAttribute("fill", "#04121a");
    hole.setAttribute("opacity", "0.85");
    svg.append(defs, ring, body, hole);
    return svg;
  }

  _sensors(entry) {
    const ids = entry.entities.sensor || [];
    if (!ids.length) return h("p", {class: "muted", text: "Không có cảm biến."});
    const grid = h("div", {class: "sensors"});
    for (const id of ids) {
      const state = this._hass.states[id];
      const attrs = (state && state.attributes) || {};
      const unit = attrs.unit_of_measurement || "";
      const value = state ? state.state : "không khả dụng";
      grid.append(h("div", {class: "sensor"}, [
        h("small", {text: attrs.friendly_name || id}),
        h("strong", {text: unit ? value + " " + unit : value}),
      ]));
    }
    return grid;
  }

  _licenseCard(entry, snapshot) {
    const license = entry.license || {};
    const card = h("div", {});
    const status = license.status || "unavailable";
    const badgeClass = status === "active" ? "" : status === "grace" ? "warn" : status === "unavailable" ? "off" : "bad";
    card.append(h("div", {class: "row", style: "justify-content:space-between;align-items:center"}, [
      h("h2", {text: "Bản quyền MAIKA"}),
      h("span", {class: "pill " + badgeClass, text: STATUS_LABELS[status] || status}),
    ]));
    card.append(h("p", {class: "sub", text: "Key đang dùng, gói và hạn sử dụng."}));
    card.append(h("div", {class: "kv"}, [h("span", {text: "Key đang dùng"}), h("strong", {text: license.key_hint ? "MAIKA-…-" + license.key_hint : "—"})]));
    card.append(h("div", {class: "kv"}, [h("span", {text: "Gói"}), h("strong", {text: planLabel(license.plan)})]));
    card.append(h("div", {class: "kv"}, [h("span", {text: "Hết hạn"}), h("strong", {text: license.expires_at ? fmtTime(license.expires_at) : "Vĩnh viễn"})]));
    card.append(h("div", {class: "kv"}, [h("span", {text: "Mã cài đặt"}), h("strong", {}, [h("code", {text: license.activation_code || "—"})])]));

    const form = h("form", {class: "form-grid", style: "margin-top:14px"});
    form.dataset.role = "license";
    form.dataset.entry = entry.entry_id;
    form.append(h("label", {class: "field"}, [
      "Nhập key mới (để trống nếu không đổi)",
      h("input", {type: "text", name: "license_key", placeholder: "MAIKA-XXXX-XXXX-XXXX-XXXX", autocomplete: "off"}),
    ]));
    form.append(h("label", {class: "field"}, [
      "Máy chủ kích hoạt",
      h("input", {type: "text", name: "server_url", value: license.server_url || snapshot.default_server_url || ""}),
    ]));
    form.append(h("div", {class: "row", style: "align-items:end"}, [
      h("button", {class: "primary", type: "submit", text: "Kích hoạt key"}),
    ]));
    card.append(form);
    card.append(h("p", {class: "muted", text: "Nhập key xong, loa sẽ dùng gói mới ngay; không cần xoá máy hay thao tác trong phần Cấu hình."}));
    return card;
  }

  _controls(entry) {
    const card = h("div", {});
    card.append(h("h2", {text: "Điều khiển & cài đặt loa"}));
    card.append(h("p", {class: "sub", text: "Nút, công tắc và lựa chọn do tích hợp MAIKA tạo."}));
    const container = h("div", {class: "form-grid"});

    const mediaIds = entry.entities.media_player || [];
    for (const id of mediaIds) container.append(this._mediaControl(id));

    for (const id of entry.entities.select || []) container.append(this._selectControl(id));
    for (const id of entry.entities.switch || []) container.append(this._switchControl(id));
    for (const id of entry.entities.text || []) container.append(this._textControl(id));
    for (const id of entry.entities.button || []) container.append(this._buttonControl(id));

    if (!container.childElementCount) {
      card.append(h("p", {class: "muted", text: "Chưa có thực thể điều khiển."}));
    } else {
      card.append(container);
    }
    return card;
  }

  _label(id) {
    const state = this._hass.states[id];
    return (state && state.attributes && state.attributes.friendly_name) || id;
  }

  _call(domain, service, data) {
    return this._hass.callService(domain, service, data);
  }

  _mediaControl(id) {
    const state = this._hass.states[id];
    const attrs = (state && state.attributes) || {};
    const volume = attrs.volume_level != null ? Math.round(attrs.volume_level * 100) : 0;
    const box = h("div", {class: "card", style: "padding:14px"});
    box.append(h("h3", {style: "margin:0 0 8px;font-size:.92rem", text: this._label(id)}));
    box.append(h("div", {class: "row"}, [
      h("button", {text: "▶", title: "Phát", onClick: () => this._call("media_player", "media_play", {entity_id: id})}),
      h("button", {text: "⏸", title: "Tạm dừng", onClick: () => this._call("media_player", "media_pause", {entity_id: id})}),
      h("button", {text: "⏮", title: "Bài trước", onClick: () => this._call("media_player", "media_previous_track", {entity_id: id})}),
      h("button", {text: "⏭", title: "Bài sau", onClick: () => this._call("media_player", "media_next_track", {entity_id: id})}),
      h("button", {text: attrs.is_volume_muted ? "Bật tiếng" : "Tắt tiếng", onClick: () => this._call("media_player", "volume_mute", {entity_id: id, is_volume_muted: !attrs.is_volume_muted})}),
    ]));
    box.append(h("label", {class: "field", style: "margin-top:10px"}, [
      "Âm lượng: " + volume + "%",
      h("input", {
        type: "range", min: "0", max: "100", value: String(volume),
        onChange: (event) => this._call("media_player", "volume_set", {entity_id: id, volume_level: Number(event.target.value) / 100}),
      }),
    ]));
    const cast = h("form", {class: "row", style: "margin-top:8px"});
    cast.dataset.role = "cast";
    cast.dataset.entity = id;
    cast.append(h("input", {type: "url", name: "media_url", placeholder: "https://.../audio.mp3"}));
    cast.append(h("button", {class: "ghost", type: "submit", text: "Cast"}));
    box.append(cast);
    return box;
  }

  _selectControl(id) {
    const state = this._hass.states[id];
    const attrs = (state && state.attributes) || {};
    const options = Array.isArray(attrs.options) ? attrs.options : [];
    const select = h("select", {
      onChange: (event) => this._call("select", "select_option", {entity_id: id, option: event.target.value}),
    });
    for (const option of options) {
      select.append(h("option", {value: option, text: option, selected: state && state.state === option}));
    }
    return h("label", {class: "field"}, [this._label(id), select]);
  }

  _switchControl(id) {
    const state = this._hass.states[id];
    const on = state && state.state === "on";
    return h("label", {class: "field check"}, [
      h("input", {type: "checkbox", checked: on, onChange: (event) => this._call("switch", on ? "turn_off" : "turn_on", {entity_id: id})}),
      h("span", {text: this._label(id)}),
    ]);
  }

  _textControl(id) {
    const state = this._hass.states[id];
    const form = h("form", {class: "field"});
    form.dataset.role = "text";
    form.dataset.entity = id;
    form.append(h("span", {text: this._label(id)}));
    form.append(h("div", {class: "row"}, [
      h("input", {type: "text", name: "value", value: state ? state.state : ""}),
      h("button", {class: "ghost", type: "submit", text: "Lưu"}),
    ]));
    return form;
  }

  _buttonControl(id) {
    return h("div", {class: "field"}, [
      h("span", {text: this._label(id)}),
      h("button", {onClick: () => this._call("button", "press", {entity_id: id})}, [
        h("span", {text: "Nhấn"}),
      ]),
    ]);
  }

  _settings(entry, snapshot) {
    const options = entry.options || {};
    const card = h("div", {});
    card.append(h("h2", {text: "Cấu hình tích hợp"}));
    card.append(h("p", {class: "sub", text: "Thay đổi ngay tại đây, không cần mở phần Cấu hình của tích hợp."}));
    const form = h("form", {class: "form-grid"});
    form.dataset.role = "options";
    form.dataset.entry = entry.entry_id;

    const [minScan, maxScan] = snapshot.scan_interval_bounds || [15, 3600];
    form.append(h("label", {class: "field"}, [
      "Chu kỳ cập nhật (giây)",
      h("input", {type: "number", name: "scan_interval", min: String(minScan), max: String(maxScan), value: String(options.scan_interval ?? 60)}),
    ]));
    form.append(h("label", {class: "field check"}, [
      h("input", {type: "checkbox", name: "enable_experimental_cloud_cast", checked: Boolean(options.enable_experimental_cloud_cast)}),
      h("span", {text: "Bật cast âm thanh qua cloud"}),
    ]));
    form.append(h("label", {class: "field check"}, [
      h("input", {type: "checkbox", name: "enable_voice_command_sensor", checked: Boolean(options.enable_voice_command_sensor)}),
      h("span", {text: "Bật cảm biến khẩu lệnh"}),
    ]));

    const sourceSelect = h("select", {name: "voice_success_audio_source"});
    for (const [value, label] of Object.entries(AUDIO_SOURCE_LABELS)) {
      sourceSelect.append(h("option", {value, text: label, selected: options.voice_success_audio_source === value}));
    }
    form.append(h("label", {class: "field"}, ["Nguồn âm báo thành công", sourceSelect]));

    const timingSelect = h("select", {name: "voice_success_audio_timing"});
    for (const [value, label] of Object.entries(AUDIO_TIMING_LABELS)) {
      timingSelect.append(h("option", {value, text: label, selected: options.voice_success_audio_timing === value}));
    }
    form.append(h("label", {class: "field"}, ["Kiểu phát âm báo (che giọng loa)", timingSelect]));

    form.append(h("label", {class: "field"}, [
      "URL âm báo (khi chọn URL tuỳ chọn)",
      h("input", {type: "url", name: "voice_success_audio_url", value: options.voice_success_audio_url || "", placeholder: "https://.../maika.mp3"}),
    ]));

    const mediaSelect = h("select", {name: "voice_success_media_player_entity_id"});
    mediaSelect.append(h("option", {value: "", text: "Tự động", selected: !options.voice_success_media_player_entity_id}));
    for (const id of entry.entities.media_player || []) {
      mediaSelect.append(h("option", {value: id, text: this._label(id), selected: options.voice_success_media_player_entity_id === id}));
    }
    form.append(h("label", {class: "field"}, ["Loa phát âm báo", mediaSelect]));

    form.append(h("label", {class: "field", style: "grid-column:1/-1"}, [
      "Điều khiển thiết bị HASS bằng khẩu lệnh",
      h("textarea", {name: "voice_command_rules", placeholder: "bật đèn | light.den | turn_on", text: options.voice_command_rules || ""}),
      h("span", {class: "muted", text: "Mỗi dòng: câu nói | entity_id | service | {dữ liệu tuỳ chọn}"}),
    ]));

    form.append(h("div", {class: "row", style: "grid-column:1/-1"}, [
      h("button", {class: "primary", type: "submit", text: "Lưu cấu hình"}),
      h("button", {class: "ghost", type: "button", text: "Tải lại tích hợp", onClick: () => this._action(entry.entry_id, "reload")}),
    ]));

    card.append(form);
    return card;
  }

  async _action(entryId, action) {
    if (this._busy) return;
    this._busy = true;
    try {
      await this._post("maika/panel/action", {entry_id: entryId, action});
      this._flash("Đã gửi yêu cầu tải lại tích hợp.");
    } catch (error) {
      this._flash("Không thực hiện được: " + (error?.message || error), true);
    } finally {
      this._busy = false;
    }
  }

  async _onSubmit(event) {
    const form = event.target.closest("form");
    if (!form || !form.dataset.role) return;
    event.preventDefault();
    if (this._busy) return;
    const role = form.dataset.role;
    const data = new FormData(form);
    this._busy = true;
    try {
      if (role === "license") {
        const key = String(data.get("license_key") || "").trim();
        if (!key) {
          this._flash("Hãy nhập key mới trước khi kích hoạt.", true);
          return;
        }
        const result = await this._post("maika/panel/license", {
          entry_id: form.dataset.entry,
          license_key: key,
          server_url: String(data.get("server_url") || "").trim(),
        });
        this._flash("Kích hoạt thành công. Trạng thái: " + (STATUS_LABELS[result.status] || result.status));
        await this._load();
      } else if (role === "options") {
        const payload = {
          entry_id: form.dataset.entry,
          options: {
            scan_interval: Number(data.get("scan_interval")),
            enable_experimental_cloud_cast: data.get("enable_experimental_cloud_cast") === "on",
            enable_voice_command_sensor: data.get("enable_voice_command_sensor") === "on",
            voice_success_audio_source: String(data.get("voice_success_audio_source") || ""),
            voice_success_audio_timing: String(data.get("voice_success_audio_timing") || ""),
            voice_success_audio_url: String(data.get("voice_success_audio_url") || "").trim(),
            voice_success_media_player_entity_id: String(data.get("voice_success_media_player_entity_id") || ""),
            voice_command_rules: String(data.get("voice_command_rules") || ""),
          },
        };
        await this._post("maika/panel/options", payload);
        this._flash("Đã lưu cấu hình. Tích hợp sẽ tải lại để áp dụng.");
      } else if (role === "cast") {
        const url = String(data.get("media_url") || "").trim();
        if (!url) {
          this._flash("Hãy nhập URL âm thanh để cast.", true);
          return;
        }
        await this._call("media_player", "play_media", {
          entity_id: form.dataset.entity,
          media_content_id: url,
          media_content_type: "music",
        });
        this._flash("Đã gửi lệnh cast âm thanh.");
        form.reset();
      } else if (role === "text") {
        await this._call("text", "set_value", {
          entity_id: form.dataset.entity,
          value: String(data.get("value") || ""),
        });
        this._flash("Đã lưu giá trị.");
      }
    } catch (error) {
      const message = error?.body?.errors ? JSON.stringify(error.body.errors) : error?.message || error;
      this._flash("Thao tác thất bại: " + message, true);
    } finally {
      this._busy = false;
    }
  }

  _onClick(event) {
    const copyTarget = event.target.closest("[data-copy]");
    if (copyTarget) {
      navigator.clipboard?.writeText(copyTarget.dataset.copy || "");
    }
  }

  _onChange() {
    /* change events are handled inline per control */
  }
}

customElements.define("maika-panel", MaikaPanel);
