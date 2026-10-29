const RULES_KEY = "voice_command_rules";
const ENABLED_KEY = "enable_voice_command_sensor";
const AUDIO_KEYS = {
  source: "voice_success_audio_source", timing: "voice_success_audio_timing",
  url: "voice_success_audio_url", player: "voice_success_media_player_entity_id",
  path: "voice_success_audio_path",
};
const RESPONSE_TTS_KEY = "voice_response_tts_entity_id";
const DOMAIN_NAMES = {
  light: "Đèn", switch: "Công tắc", fan: "Quạt", cover: "Rèm / cửa",
  climate: "Điều hòa", sensor: "Cảm biến", binary_sensor: "Cảm biến nhị phân", media_player: "Loa / TV", automation: "Automation",
  script: "Kịch bản", scene: "Cảnh", vacuum: "Robot hút bụi", button: "Nút bấm",
  input_button: "Nút ảo", input_boolean: "Công tắc ảo", humidifier: "Máy tạo ẩm",
  water_heater: "Bình nóng lạnh", number: "Giá trị số", input_number: "Số tùy chỉnh",
  select: "Lựa chọn", input_select: "Lựa chọn tùy chỉnh", counter: "Bộ đếm",
  timer: "Hẹn giờ", text: "Văn bản", input_text: "Văn bản tùy chỉnh",
  siren: "Còi báo", valve: "Van", lawn_mower: "Máy cắt cỏ", lock: "Khóa cửa",
  camera: "Camera", remote: "Điều khiển từ xa",
};
const ACTION_NAMES = {
  read: "Đọc trạng thái và trả lời", turn_on: "Bật", turn_off: "Tắt", toggle: "Đảo trạng thái bật / tắt", trigger: "Kích hoạt automation",
  press: "Bấm nút", open_cover: "Mở rèm / cửa", close_cover: "Đóng rèm / cửa", stop_cover: "Dừng rèm / cửa",
  set_cover_position: "Đặt độ mở (%)", open_cover_tilt: "Mở lá rèm", close_cover_tilt: "Đóng lá rèm",
  stop_cover_tilt: "Dừng lá rèm", toggle_cover_tilt: "Đảo trạng thái lá rèm", set_cover_tilt_position: "Đặt góc lá rèm (%)",
  set_percentage: "Đặt tốc độ (%)", increase_speed: "Tăng tốc độ", decrease_speed: "Giảm tốc độ",
  oscillate: "Bật / tắt đảo gió", set_direction: "Chọn chiều quay", set_preset_mode: "Chọn chế độ có sẵn",
  set_temperature: "Đặt nhiệt độ", set_hvac_mode: "Chọn chế độ điều hòa", set_humidity: "Đặt độ ẩm",
  set_fan_mode: "Chọn chế độ quạt", set_swing_mode: "Chọn đảo gió", set_swing_horizontal_mode: "Chọn đảo gió ngang",
  media_play_pause: "Phát / tạm dừng", media_play: "Phát", media_pause: "Tạm dừng", media_stop: "Dừng phát",
  media_next_track: "Bài tiếp theo", media_previous_track: "Bài trước", clear_playlist: "Xóa danh sách phát",
  volume_up: "Tăng âm lượng", volume_down: "Giảm âm lượng", volume_set: "Đặt âm lượng (%)", volume_mute: "Tắt / bật âm thanh",
  media_seek: "Tua đến vị trí", select_source: "Chọn nguồn phát", select_sound_mode: "Chọn chế độ âm thanh",
  shuffle_set: "Phát ngẫu nhiên", repeat_set: "Chọn chế độ lặp", start: "Bắt đầu", pause: "Tạm dừng",
  stop: "Dừng", return_to_base: "Về đế sạc", clean_spot: "Dọn tại chỗ", locate: "Tìm robot", set_fan_speed: "Chọn lực hút",
  set_mode: "Chọn chế độ", set_away_mode: "Chế độ vắng nhà", set_operation_mode: "Chọn chế độ hoạt động",
  set_value: "Đặt giá trị", increment: "Tăng một bước", decrement: "Giảm một bước", reset: "Đặt lại",
  select_first: "Chọn mục đầu", select_last: "Chọn mục cuối", select_next: "Chọn mục tiếp theo",
  select_previous: "Chọn mục trước", select_option: "Chọn giá trị", cancel: "Hủy", finish: "Kết thúc", change: "Đổi thời gian",
  open_valve: "Mở van", close_valve: "Đóng van", stop_valve: "Dừng van", set_valve_position: "Đặt độ mở van (%)",
  start_mowing: "Bắt đầu cắt cỏ", dock: "Về trạm", lock: "Khóa cửa",
  enable_motion_detection: "Bật phát hiện chuyển động", disable_motion_detection: "Tắt phát hiện chuyển động",
};
const FIELD_NAMES = {
  brightness: "Độ sáng (0–255)", brightness_pct: "Độ sáng (%)", brightness_step: "Bước sáng (−255–255)",
  brightness_step_pct: "Bước sáng (%)", color_temp_kelvin: "Nhiệt độ màu (K)", rgb_color: "Màu RGB",
  rgbw_color: "Màu RGBW", rgbww_color: "Màu RGBWW", hs_color: "Màu HS", xy_color: "Màu XY",
  color_name: "Tên màu", profile: "Hồ sơ màu", flash: "Nháy đèn", effect: "Hiệu ứng", transition: "Thời gian chuyển (giây)",
  activity: "Hoạt động", percentage: "Tốc độ (%)", percentage_step: "Bước tốc độ (%)", preset_mode: "Chế độ",
  oscillating: "Đảo gió", direction: "Chiều quay", position: "Độ mở (%)", tilt_position: "Góc lá rèm (%)",
  hvac_mode: "Chế độ điều hòa", temperature: "Nhiệt độ", humidity: "Độ ẩm (%)", fan_mode: "Chế độ quạt",
  swing_mode: "Đảo gió", swing_horizontal_mode: "Đảo gió ngang", volume_level: "Âm lượng (%)",
  is_volume_muted: "Tắt âm thanh", seek_position: "Vị trí (giây)", source: "Nguồn phát", sound_mode: "Chế độ âm thanh",
  shuffle: "Phát ngẫu nhiên", repeat: "Lặp", fan_speed: "Lực hút", mode: "Chế độ", away_mode: "Vắng nhà",
  operation_mode: "Chế độ hoạt động", value: "Giá trị", cycle: "Quay về đầu khi hết danh sách", option: "Giá trị lựa chọn",
  duration: "Thời gian", tone: "Âm còi", skip_condition: "Bỏ qua điều kiện automation",
};
const VALUE_NAMES = {
  off: "Tắt", heat: "Sưởi", cool: "Làm lạnh", heat_cool: "Sưởi / lạnh", auto: "Tự động", dry: "Hút ẩm",
  fan_only: "Chỉ quạt", forward: "Thuận", reverse: "Ngược", all: "Tất cả", one: "Một bài", short: "Ngắn", long: "Dài",
};
const OPTION_ATTRIBUTES = {
  preset_mode: "preset_modes", hvac_mode: "hvac_modes", fan_mode: "fan_modes", swing_mode: "swing_modes",
  swing_horizontal_mode: "swing_horizontal_modes", source: "source_list", sound_mode: "sound_mode_list",
  option: "options", effect: "effect_list", fan_speed: "fan_speed_list", mode: "available_modes",
  operation_mode: "operation_list", tone: "available_tones",
};
const COMMON_FIELDS = new Set(["brightness_pct", "color_temp_kelvin", "percentage", "preset_mode", "skip_condition", "transition", "duration"]);

function element(tag, attributes = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "text") node.textContent = value;
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  node.append(...children);
  return node;
}

function normalizedPhrase(value) {
  return value.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "").replaceAll("đ", "d")
    .replaceAll("ß", "ss").replace(/[\p{P}\p{S}]/gu, " ").trim().replace(/\s+/gu, " ");
}

function phraseList(value) {
  return String(value || "").split(",").map((phrase) => phrase.trim()).filter(Boolean);
}

function parseLines(text) {
  return String(text || "").split(/\r?\n/u).map((raw) => {
    const trimmed = raw.trim();
    if (!trimmed || trimmed.startsWith("#")) return {raw};
    const parts = trimmed.split("|");
    try {
      if (parts.length < 3) throw new Error("Thiếu thông tin");
      const entity = parts[1].trim().toLowerCase();
      const action = parts[2].trim().toLowerCase().replace(`${entity.split(".")[0]}.`, "");
      const data = parts.length > 3 ? JSON.parse(parts.slice(3).join("|")) : {};
      if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("Thông số không hợp lệ");
      return {raw, rule: {phrase: parts[0].trim(), entity, action, data}};
    } catch {
      return {raw, invalid: true};
    }
  });
}

class MaikaVoiceEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._entry = null;
    this._lines = [];
    this._editing = -1;
    this._dirty = false;
    this._formDirty = false;
    this._saving = false;
    this._testing = false;
    this._schema = null;
    this._serverSignature = "";
    this._entitySignature = "";
  }

  connectedCallback() {
    if (!this.shadowRoot.hasChildNodes()) this._build();
  }

  get isBusy() { return this._saving || this._testing; }

  get hasUnsavedChanges() {
    return this._dirty || this._formDirty || this.isBusy;
  }

  _optionsSignature(options) {
    return JSON.stringify([options?.[RULES_KEY], options?.[ENABLED_KEY], ...Object.values(AUDIO_KEYS).map((key) => options?.[key])]);
  }

  configure({hass, entry, catalog, limits}) {
    this._hass = hass;
    this._catalog = catalog || {};
    this._limits = limits || {rules: 200, phrase: 200};
    if (!entry) return;
    const changedEntry = entry.entry_id !== this._entry?.entry_id;
    this._entry = entry;
    const signature = this._optionsSignature(entry.options);
    if (changedEntry) {
      this._query("command-form").reset();
      this._query("target").value = "";
      this._query("list-search").value = "";
      this._query("message").hidden = true;
      this._query("reload-rules").hidden = true;
      this._entitySignature = "";
    }
    if (changedEntry || (!this.hasUnsavedChanges && signature !== this._serverSignature)) {
      this._serverSignature = signature;
      this._loadOptions(entry.options || {});
      if (changedEntry) this._resetEditor();
    }
    this._query("phrase").maxLength = this._limits.phrase;
    this._query("feature-form").hidden = !Object.keys(this._catalog).length;
    this._query("catalog-error").hidden = Boolean(Object.keys(this._catalog).length);
    this._refreshEntities();
    this._audioVisibility();
    this._status();
  }

  _query(id) { return this.shadowRoot.getElementById(id); }

  _build() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; min-width:0; color:var(--text); container-type:inline-size; }
        * { box-sizing:border-box; } [hidden] { display:none!important; }
        h2,h3,p { margin:0; } h2 { font-size:1.3rem; letter-spacing:-.02em; } h3 { font-size:1rem; }
        .intro { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:20px; }
        .intro-copy { flex:1; min-width:160px; } .intro p,.muted { font-size:.84rem; color:var(--muted); }
        .emblem { width:50px; height:50px; border-radius:18px; display:grid; place-items:center; background:linear-gradient(145deg,var(--brand-start),var(--brand-end)); color:var(--brand-ink); font-size:1.5rem; box-shadow:inset 0 1px 0 rgba(255,255,255,.6),0 6px 18px rgba(239,116,24,.12); }
        .eyebrow { color:var(--accent); font-size:.7rem; font-weight:750; letter-spacing:.1em; margin-bottom:4px; }
        .layout { display:grid; grid-template-columns:minmax(0,1.05fr) minmax(0,1fr); gap:20px; align-items:start; }
        .box { padding:18px; border-radius:20px; border:1px solid var(--line); background:var(--surface-2); min-width:0; }
        .stack { display:grid; gap:14px; } label,.field { display:grid; gap:6px; min-width:0; font-size:.83rem; font-weight:600; }
        .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; } .row>* { min-width:0; }
        .steps { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin:0 0 18px; }
        .step { display:flex; gap:7px; align-items:center; color:var(--muted); font-size:.78rem; }
        .step b { background:var(--surface-3); color:var(--accent); border-radius:50%; width:24px; height:24px; display:grid; place-items:center; flex:none; }
        input,select,button,textarea { font:inherit; font-size:16px; color:inherit; min-width:0; }
        input,select,textarea { width:100%; min-height:46px; border:1px solid var(--line); border-radius:13px; padding:10px 12px; background:var(--surface); }
        input::placeholder { color:var(--muted); opacity:.8; } select option { background:var(--surface); }
        button { min-height:44px; cursor:pointer; border:1px solid var(--line); border-radius:13px; padding:9px 13px; background:var(--surface); font-size:.85rem; font-weight:650; transition:transform .15s, background .15s; touch-action:manipulation; }
        button { position:relative; isolation:isolate; -webkit-tap-highlight-color:transparent; }
        button::after { content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none; background:currentColor; opacity:0; transform:scale(.7); transition:opacity .32s,transform .4s var(--ease,ease); }
        button:active:not(:disabled)::after { opacity:.12; transform:scale(1); transition-duration:.08s; }
        button:hover { background:var(--surface-3); } button:active:not(:disabled) { transform:scale(.97); }
        button:disabled { opacity:.55; cursor:wait; } .primary { background:var(--accent); border-color:transparent; color:var(--accent-ink); }
        .primary:hover { background:var(--accent); filter:brightness(1.08); } .danger { color:var(--bad); }
        button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible { outline:3px solid var(--accent); outline-offset:3px; }
        .filters { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .params { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        .params>.wide { grid-column:1/-1; } .vector { display:flex; flex-wrap:wrap; gap:6px; } .vector input { flex:1 1 60px; width:60px; }
        .note { color:var(--muted); font-size:.78rem; font-weight:400; line-height:1.5; overflow-wrap:anywhere; }
        details { border:1px solid var(--line); border-radius:14px; padding:0 12px; } summary { cursor:pointer; padding:12px 0; font-size:.83rem; min-height:46px; }
        details>.params { padding-bottom:12px; } .commands { display:grid; gap:10px; max-height:520px; overflow:auto; padding:3px; }
        .command { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:14px; display:grid; gap:8px; overflow-wrap:anywhere; transition:border-color .2s,box-shadow .2s; }
        @media(hover:hover) { .command:hover { border-color:var(--accent); box-shadow:var(--shadow); } }
        .command-title { font-weight:700; font-size:.96rem; } .command .note { line-height:1.6; }
        .command-actions { display:flex; flex-wrap:wrap; gap:8px; } .command-actions button { font-size:.8rem; }
        .count { padding:5px 10px; border-radius:999px; background:var(--surface-3); color:var(--accent); font-size:.8rem; font-weight:700; }
        .toggle { display:flex; align-items:center; justify-content:space-between; gap:12px; background:var(--surface-2); padding:12px; border-radius:15px; }
        input[type=checkbox] { width:24px; height:24px; min-height:24px; accent-color:var(--accent); flex:none; }
        .notice { padding:12px; border-radius:14px; background:var(--surface-3); font-size:.85rem; overflow-wrap:anywhere; animation:notice-in .24s var(--ease,ease); }
        .notice[data-kind=error] { color:var(--bad); } .notice[data-kind=success] { color:var(--ok); }
        .preview { padding:12px; border:1px dashed var(--line); border-radius:14px; font-size:.9rem; overflow-wrap:anywhere; }
        .preview strong { color:var(--accent); } .empty { text-align:center; padding:25px 10px; }
        .status { font-size:.8rem; color:var(--accent); } .audio { margin-top:18px; } .audio .filters { margin-top:12px; }
        .buttons { display:flex; gap:8px; flex-wrap:wrap; } .buttons button { flex:1 1 130px; }
        .invalid { border-color:var(--bad); } pre { white-space:pre-wrap; font-size:.76rem; overflow-wrap:anywhere; margin:0; }
        fieldset { border:0; margin:0; padding:0; min-width:0; } legend { font-weight:700; margin-bottom:12px; }
        @container (max-width:850px) { .layout { grid-template-columns:1fr; } .commands { max-height:420px; } }
        @container (max-width:440px) {
          .box { padding:13px; } .filters,.params { grid-template-columns:1fr; } .steps { gap:4px; } .step { font-size:.71rem; }
          .intro { display:grid; grid-template-columns:38px minmax(0,1fr); gap:10px; }
          .intro-copy { min-width:0; } .intro h2 { font-size:1.15rem; } .intro p { font-size:.78rem; }
          .intro .eyebrow { font-size:.64rem; } .emblem { width:38px; height:38px; border-radius:14px; }
          .count { grid-column:2; justify-self:start; }
        }
        @keyframes notice-in { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:none; } }
        *,*::before,*::after { animation-play-state:var(--maika-motion-state,running)!important; }
        :host([data-reduced-motion]) *,:host([data-reduced-motion]) *::before,:host([data-reduced-motion]) *::after { animation:none!important; transition:none!important; }
        @media(prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none!important; transition:none!important; } }
      </style>
      <header class="intro">
        <span class="emblem" aria-hidden="true">✦</span>
        <div class="intro-copy"><p class="eyebrow">MAIKA × HOME ASSISTANT</p><h2>Điều khiển nhà bằng giọng nói</h2><p>Chọn thiết bị, chọn thao tác, nhập câu bạn muốn nói.</p></div>
        <span id="summary" class="count">0 câu lệnh</span>
      </header>
      <p id="catalog-error" class="notice" hidden>Chưa tải được danh sách thao tác. Hãy cập nhật integration rồi làm mới panel.</p>
      <p id="message" class="notice" role="status" aria-live="polite" hidden></p>
      <div id="feature-form" class="layout">
        <section class="box stack">
          <h3 id="editor-title">Tạo câu lệnh mới</h3>
          <div class="steps" aria-label="Ba bước tạo câu lệnh"><span class="step"><b>1</b>Chọn thiết bị</span><span class="step"><b>2</b>Chọn thao tác</span><span class="step"><b>3</b>Nhập câu nói</span></div>
          <form id="command-form" class="stack">
            <div class="filters">
              <label for="target-type">Bạn muốn điều khiển<select id="target-type"><option value="device">Thiết bị</option><option value="automation">Automation</option><option value="script">Kịch bản (script)</option><option value="scene">Cảnh (scene)</option></select></label>
              <label for="device-type" id="device-type-field">Loại thiết bị<select id="device-type"><option value="">Tất cả thiết bị</option></select></label>
            </div>
            <label for="target-search">Tìm trong Home Assistant<input id="target-search" type="search" placeholder="Tên thiết bị, automation hoặc entity…" autocomplete="off"></label>
            <label for="target">Thiết bị / automation<select id="target" required><option value="">Chọn thiết bị…</option></select></label>
            <p id="target-note" class="note"></p>
            <label for="action">Thao tác<select id="action" required><option value="">Chọn thiết bị trước</option></select></label>
            <p id="action-note" class="note" hidden></p>
            <div id="parameters" class="stack"></div>
            <label for="phrase">Khi tôi nói<input id="phrase" required maxlength="200" placeholder="Ví dụ: bật đèn phòng khách" autocomplete="off"></label>
            <p class="note">Cùng một thao tác có thể dùng nhiều câu, cách nhau bằng dấu phẩy. Ví dụ: bật điện, bật quạt.</p>
            <div id="preview" class="preview" aria-live="polite">Câu lệnh của bạn sẽ hiện ở đây.</div>
            <div class="buttons"><button id="save-command" class="primary" type="submit">Lưu câu lệnh</button><button id="test-command" type="button">Chạy thử thao tác</button><button id="cancel-edit" type="button" hidden>Hủy sửa</button></div>
          </form>
        </section>
        <div class="stack">
          <section class="box stack">
            <div class="row"><h3>Câu lệnh của bạn</h3><span id="saved-state" class="status">Đã lưu</span></div>
            <label for="list-search">Tìm câu lệnh<input id="list-search" type="search" placeholder="Tìm câu nói hoặc tên thiết bị…"></label>
            <div id="commands" class="commands"></div>
            <button id="retry-save" class="primary" type="button" hidden>Lưu lại thay đổi</button>
            <button id="reload-rules" type="button" hidden>Tải lại cấu hình đã lưu</button>
          </section>
          <section class="box stack">
            <h3>Giọng nói & âm phản hồi</h3>
            <form id="voice-settings" class="stack">
              <label class="toggle" for="voice-enabled"><span>Bật điều khiển thiết bị HASS<br><small class="note">Lắng nghe câu nói từ loa MAIKA</small></span><input id="voice-enabled" type="checkbox"></label>
              <label for="audio-source">Âm báo khi thành công<select id="audio-source"><option value="disabled">Không phát âm báo</option><option value="bundled">Âm MAIKA có sẵn</option><option value="library">Thư viện MP3 trên Home Assistant</option><option value="custom">File MP3 của bạn (URL)</option></select></label>
              <label for="audio-url" id="audio-url-field" hidden>URL file MP3<input id="audio-url" type="url" placeholder="https://…/thanh-cong.mp3"></label>
              <label for="audio-library" id="audio-library-field" hidden>Chọn file trong thư viện<select id="audio-library"><option value="">Đang tải danh sách…</option></select></label>
              <button id="audio-library-refresh" type="button" hidden>Tải lại danh sách MP3</button>
              <p id="audio-library-note" class="note" hidden>Đặt file vào /config/www, /config/mp3 hoặc /config/media (mp3, m4a, aac, wav, ogg, flac). Home Assistant phải truy cập được từ Internet để loa tải file.</p>
              <label for="audio-player">Phát âm phản hồi qua<select id="audio-player"><option value="">Tự chọn khi tài khoản chỉ có một loa</option></select></label>
              <label for="response-tts">Giọng đọc câu trả lời trạng thái<select id="response-tts"><option value="">Tự chọn khi Home Assistant chỉ có một TTS</option></select></label>
              <p id="response-tts-note" class="note" hidden>Thêm TTS trong Home Assistant để nghe câu trả lời như “Nhiệt độ phòng khách là 28,5 độ C”.</p>
              <p id="audio-note" class="note"></p>
              <label for="audio-timing">Thời điểm phản hồi<select id="audio-timing"><option value="priority">Ưu tiên che giọng mặc định của loa</option><option value="after_success">Sau khi điều khiển thành công</option></select></label>
              <p class="note">Chế độ ưu tiên cố gắng che câu trả lời mặc định, không đảm bảo tắt hoàn toàn giọng cloud của loa. Các cài đặt này áp dụng cho mọi loa cùng tài khoản MAIKA.</p>
              <button class="primary" type="submit">Lưu cài đặt giọng nói</button>
            </form>
          </section>
        </div>
      </div>`;
    this._query("target-type").addEventListener("change", () => { this._query("target").value = ""; this._refreshTargets(); this._targetChanged(); });
    this._query("device-type").addEventListener("change", () => { this._query("target").value = ""; this._refreshTargets(); this._targetChanged(); });
    this._query("target-search").addEventListener("input", () => this._refreshTargets());
    this._query("target").addEventListener("change", () => this._targetChanged());
    this._query("action").addEventListener("change", () => this._renderParameters());
    this._query("phrase").addEventListener("input", () => this._preview());
    for (const name of ["input", "change"]) this._query("command-form").addEventListener(name, () => { this._formDirty = true; this._status(); });
    this._query("command-form").addEventListener("submit", (event) => { event.preventDefault(); this._saveCommand(); });
    this._query("test-command").addEventListener("click", () => this._test());
    this._query("cancel-edit").addEventListener("click", () => {
      if (!this._formDirty || window.confirm("Bỏ phần đang nhập ở trình soạn?")) this._resetEditor();
    });
    this._query("list-search").addEventListener("input", () => this._renderList());
    this._query("commands").addEventListener("click", (event) => this._listAction(event));
    this._query("voice-settings").addEventListener("change", () => { this._dirty = true; this._audioVisibility(); this._status(); });
    this._query("voice-settings").addEventListener("input", () => { this._dirty = true; this._status(); });
    this._query("voice-settings").addEventListener("submit", (event) => { event.preventDefault(); this._persist(); });
    this._query("audio-library-refresh").addEventListener("click", () => { this._libraryLoaded = false; this._loadAudioLibrary(); });
    this._query("retry-save").addEventListener("click", () => this._persist());
    this._query("reload-rules").addEventListener("click", () => this._reload());
  }

  _name(entityId) { return this._hass?.states?.[entityId]?.attributes?.friendly_name || entityId; }
  _actionName(domain, action) {
    if (action === "turn_on" && domain === "scene") return "Kích hoạt cảnh";
    if (action === "turn_on" && domain === "script") return "Chạy kịch bản";
    if (domain === "automation" && action === "turn_on") return "Bật automation (không chạy ngay)";
    if (domain === "automation" && action === "turn_off") return "Tắt automation";
    return ACTION_NAMES[action] || action;
  }

  _refreshEntities() {
    const states = this._hass?.states || {};
    const ids = Object.keys(states).filter((entityId) => this._catalog[entityId.split(".")[0]]).sort((first, second) => this._name(first).localeCompare(this._name(second), "vi") || first.localeCompare(second));
    const ttsIds = Object.keys(states).filter((entityId) => entityId.startsWith("tts.")).sort((first, second) => this._name(first).localeCompare(this._name(second), "vi") || first.localeCompare(second));
    const signature = JSON.stringify([ids.map((entityId) => [entityId, this._name(entityId), ["unknown", "unavailable"].includes(states[entityId].state)]), ttsIds.map((entityId) => [entityId, this._name(entityId)])]);
    if (signature === this._entitySignature) return;
    this._entitySignature = signature;
    this._entityIds = ids;
    const domainSelect = this._query("device-type");
    const selectedDomain = domainSelect.value;
    domainSelect.replaceChildren(element("option", {value: "", text: "Tất cả thiết bị"}));
    for (const domain of [...new Set(ids.map((entityId) => entityId.split(".")[0]))].filter((domain) => !["automation", "script", "scene"].includes(domain))) {
      domainSelect.append(element("option", {value: domain, text: DOMAIN_NAMES[domain] || domain}));
    }
    domainSelect.value = selectedDomain;
    const playerSelect = this._query("audio-player");
    const selectedPlayer = playerSelect.value;
    playerSelect.replaceChildren(element("option", {value: "", text: "Tự chọn khi tài khoản chỉ có một loa"}));
    for (const entityId of this._entry.entities?.media_player || []) playerSelect.append(element("option", {value: entityId, text: `${this._name(entityId)} · ${entityId}`}));
    this._retainOption(playerSelect, selectedPlayer);
    const ttsSelect = this._query("response-tts");
    const selectedTts = ttsSelect.value;
    ttsSelect.replaceChildren(element("option", {value: "", text: "Tự chọn khi Home Assistant chỉ có một TTS"}));
    for (const entityId of ttsIds) ttsSelect.append(element("option", {value: entityId, text: `${this._name(entityId)} · ${entityId}`}));
    this._retainOption(ttsSelect, selectedTts);
    this._refreshTargets();
    this._renderList();
  }

  _retainOption(select, value) {
    if (value && ![...select.options].some((option) => option.value === String(value))) select.append(element("option", {value, text: `${this._name(value)} (đã lưu / không tìm thấy)`}));
    select.value = value || "";
  }

  _refreshTargets() {
    const target = this._query("target");
    const selected = target.value;
    const type = this._query("target-type").value;
    const domainFilter = this._query("device-type").value;
    const search = normalizedPhrase(this._query("target-search").value);
    this._query("device-type-field").hidden = type !== "device";
    const matches = (this._entityIds || []).filter((entityId) => {
      const domain = entityId.split(".")[0];
      const typeMatch = type === "device" ? !["automation", "script", "scene"].includes(domain) && (!domainFilter || domain === domainFilter) : domain === type;
      return typeMatch && (!search || normalizedPhrase(`${this._name(entityId)} ${entityId}`).includes(search));
    });
    target.replaceChildren(element("option", {value: "", text: matches.length ? `Chọn trong ${matches.length} mục…` : "Không tìm thấy — thử từ khóa khác"}));
    for (const entityId of matches) {
      const offline = this._hass.states[entityId].state === "unavailable" ? " · mất kết nối" : "";
      target.append(element("option", {value: entityId, text: `${this._name(entityId)} · ${entityId}${offline}`}));
    }
    if (selected && !matches.includes(selected) && this._hass.states[selected]) target.append(element("option", {value: selected, text: `${this._name(selected)} · ${selected} (đang chọn)`}));
    this._retainOption(target, selected);
    this._targetNote();
  }

  _targetNote() {
    const entityId = this._query("target").value;
    this._query("target-note").textContent = entityId ? `${this._name(entityId)} · ${entityId}` : "Danh sách lấy trực tiếp từ Home Assistant của bạn.";
  }

  _targetChanged(action, data = {}, editing = false) {
    const domain = this._query("target").value.split(".")[0];
    const select = this._query("action");
    const available = Object.keys(this._catalog[domain] || {}).filter((name) => name === "read" || !this._hass?.services?.[domain] || this._hass.services[domain][name] || name === action);
    select.replaceChildren();
    if (!available.length) select.append(element("option", {value: "", text: "Chọn thiết bị có thể điều khiển"}));
    for (const name of available) select.append(element("option", {value: name, text: this._actionName(domain, name)}));
    if (action) select.value = action;
    else if (domain === "automation") select.value = "trigger";
    else if (["script", "scene"].includes(domain)) select.value = "turn_on";
    this._targetNote();
    this._renderParameters(data, editing);
  }

  _renderParameters(data = {}, editing = false) {
    const entityId = this._query("target").value;
    const domain = entityId.split(".")[0];
    const action = this._query("action").value;
    this._schema = this._catalog[domain]?.[action];
    const params = this._query("parameters");
    params.replaceChildren();
    const note = this._query("action-note");
    note.hidden = action !== "read" && (domain !== "automation" || action !== "trigger");
    note.textContent = action === "read" ? "Khi nói câu này, loa đọc trạng thái hiện tại bằng giọng TTS. Không điều khiển thiết bị và không dùng được nút chạy thử." : "Kích hoạt automation ngay, không đợi trigger. Lệnh mới kiểm tra điều kiện; ‘Giữ mặc định’ giữ hành vi HA (bỏ qua điều kiện). Automation cần dữ liệu trigger có thể không chạy được theo cách này.";
    this._query("test-command").hidden = action === "read";
    this._unknownData = {};
    this._originalData = data;
    if (!this._schema) { this._preview(); return; }
    const values = {...data};
    if (!editing && domain === "automation" && action === "trigger") values.skip_condition = false;
    const primary = element("div", {class: "params"});
    const additional = element("div", {class: "params"});
    for (const [name, schema] of Object.entries(this._schema.fields)) {
      const required = this._schema.required.includes(name);
      const field = this._field(name, schema, required, values[name]);
      (required || COMMON_FIELDS.has(name) || name in values ? primary : additional).append(field);
    }
    params.append(primary);
    if (additional.children.length) params.append(element("details", {}, [element("summary", {text: "Thêm thông số (không bắt buộc)"}), additional]));
    const unknown = Object.keys(data).filter((name) => !this._schema.fields[name]);
    this._unknownData = Object.fromEntries(unknown.map((name) => [name, data[name]]));
    if (unknown.length) params.append(element("p", {class: "note", text: `Giữ nguyên thông số cũ: ${unknown.join(", ")}. Máy chủ sẽ kiểm tra khi lưu.`}));
    this._preview();
  }

  _field(name, schema, required, value) {
    const field = element("div", {class: "field", "data-param": name});
    const id = `param-${name}`;
    field.append(element("label", {for: id, text: `${FIELD_NAMES[name] || name}${required ? " *" : ""}`}));
    const attrs = this._hass?.states?.[this._query("target").value]?.attributes || {};
    const choices = attrs[OPTION_ATTRIBUTES[name]];
    let input;
    if (schema.type === "sequence") {
      const row = element("div", {class: "vector"});
      schema.items.forEach((item, index) => row.append(element("input", {id: index === 0 ? id : `${id}-${index}`, type: "number", min: item.min, max: item.max, step: item.type === "integer" ? "1" : "any", required, "aria-label": `${FIELD_NAMES[name]} ${index + 1}`, value: value?.[index] ?? ""})));
      field.append(row);
      return field;
    }
    if (schema.type === "boolean" || schema.type === "enum" || Array.isArray(choices) && choices.length) {
      input = element("select", {id, required});
      input.append(element("option", {value: "", text: required ? "Chọn giá trị…" : "Giữ mặc định"}));
      let options = schema.type === "boolean" ? [true, false] : schema.options || choices;
      if (schema.type === "enum" && Array.isArray(choices) && choices.length) options = options.filter((item) => choices.includes(item));
      for (const option of options) input.append(element("option", {value: String(option), text: typeof option === "boolean" ? (name === "skip_condition" ? (option ? "Có — chạy trực tiếp" : "Không — kiểm tra điều kiện") : option ? "Có / Bật" : "Không / Tắt") : VALUE_NAMES[option] || String(option)}));
      this._retainOption(input, value === undefined ? "" : String(value));
    } else {
      const numeric = ["number", "integer"].includes(schema.type);
      const scale = name === "volume_level" ? 100 : 1;
      let minimum = schema.min;
      let maximum = schema.max;
      if (name === "temperature") { minimum = Math.max(minimum, attrs.min_temp ?? minimum); maximum = Math.min(maximum, attrs.max_temp ?? maximum); }
      if (name === "value" && numeric) { minimum = Math.max(minimum, attrs.min ?? minimum); maximum = Math.min(maximum, attrs.max ?? maximum); }
      input = element("input", {id, type: numeric ? "number" : "text", required, min: numeric ? minimum * scale : null, max: numeric ? maximum * scale : null, step: numeric ? schema.type === "integer" || scale === 100 ? 1 : "any" : null, maxlength: schema.max_length, value: value === undefined ? "" : numeric ? value * scale : value, placeholder: schema.type === "duration" ? "00:05:00" : required ? "Nhập giá trị" : "Không bắt buộc"});
    }
    field.append(input);
    return field;
  }

  _collect(requirePhrase = true) {
    const entityId = this._query("target").value;
    const action = this._query("action").value;
    const phrase = this._query("phrase").value.trim().replace(/\s+/gu, " ");
    if (!this._schema || !entityId || !action) throw new Error("Hãy chọn thiết bị và thao tác.");
    if (requirePhrase && (!normalizedPhrase(phrase) || phrase.includes("|") || phrase.startsWith("#") || phrase.length > this._limits.phrase)) throw new Error("Nhập câu nói hợp lệ, không dùng dấu | hoặc bắt đầu bằng #.");
    const data = {...this._unknownData};
    for (const [name, schema] of Object.entries(this._schema.fields)) {
      const field = this._query(`param-${name}`).closest("[data-param]");
      const controls = [...field.querySelectorAll("input, select")];
      const values = controls.map((input) => input.value.trim());
      if (values.every((value) => value === "")) {
        if (this._schema.required.includes(name)) throw new Error(`Chưa nhập ${FIELD_NAMES[name] || name}.`);
        continue;
      }
      for (const input of controls) if (!input.checkValidity() || schema.type === "sequence" && input.value === "") throw new Error(`Kiểm tra ${FIELD_NAMES[name] || name}.`);
      if (schema.type === "sequence") data[name] = values.map(Number);
      else if (["number", "integer"].includes(schema.type)) data[name] = Number(values[0]) / (name === "volume_level" ? 100 : 1);
      else if (schema.type === "boolean") data[name] = values[0] === "true";
      else if (schema.type === "tone" && typeof this._originalData[name] === "number" && /^\d+$/u.test(values[0])) data[name] = Number(values[0]);
      else data[name] = values[0];
    }
    for (const group of this._schema.exclusive || []) {
      const used = group.filter((name) => name in data);
      if (used.length > 1) throw new Error(`Chỉ chọn một trong: ${used.map((name) => FIELD_NAMES[name] || name).join(", ")}.`);
    }
    const rule = {phrase, entity: entityId, action, data};
    this._validateRule(rule);
    return rule;
  }

  _validateRule(rule) {
    const schema = this._catalog[rule.entity.split(".")[0]]?.[rule.action];
    if (!schema || !/^[a-z_][a-z0-9_]*\.[a-z0-9_]+$/u.test(rule.entity)) throw new Error("Thiết bị hoặc thao tác không hợp lệ.");
    if (Object.keys(rule.data).length > 12) throw new Error("Một thao tác tối đa 12 thông số.");
    const valid = (value, field) => {
      if (["number", "integer"].includes(field.type)) return typeof value === "number" && Number.isFinite(value) && value >= field.min && value <= field.max && (field.type !== "integer" || Number.isInteger(value));
      if (field.type === "boolean") return typeof value === "boolean";
      if (field.type === "enum") return typeof value === "string" && field.options.includes(value.toLowerCase());
      if (field.type === "sequence") return Array.isArray(value) && value.length === field.items.length && value.every((item, index) => valid(item, field.items[index]));
      if (field.type === "tone" && typeof value === "number") return Number.isInteger(value) && value >= 0 && value <= 1000000;
      if (typeof value !== "string" || !value.trim() || value.length > (field.max_length || 255) || /\p{Cc}/u.test(value)) return false;
      if (field.type === "duration") return /^(?:\d{1,3}:)?\d{1,3}:\d{2}$/u.test(value) && value.split(":").slice(-2).every((part) => Number(part) <= 59);
      return true;
    };
    for (const [name, value] of Object.entries(rule.data)) {
      if (!Object.hasOwn(schema.fields, name) || !valid(value, schema.fields[name])) throw new Error(`Kiểm tra thông số: ${FIELD_NAMES[name] || name}.`);
    }
    for (const name of schema.required) if (!Object.hasOwn(rule.data, name)) throw new Error(`Chưa nhập ${FIELD_NAMES[name] || name}.`);
    for (const group of schema.exclusive || []) if (group.filter((name) => Object.hasOwn(rule.data, name)).length > 1) throw new Error("Các thông số đã chọn không thể dùng cùng nhau.");
  }

  _preview() {
    const phrase = this._query("phrase").value.trim();
    const target = this._query("target").value;
    const action = this._query("action").value;
    this._query("preview").replaceChildren(element("strong", {text: phrase ? `“${phrase}”` : "Câu nói của bạn"}), document.createTextNode(target && action ? ` → ${this._actionName(target.split(".")[0], action)} · ${this._name(target)}` : " → chọn thiết bị và thao tác"));
  }

  _loadOptions(options) {
    this._expectedOptions = this._voiceOptions(options);
    this._baselineRules = String(options[RULES_KEY] || "");
    this._lines = parseLines(this._baselineRules);
    this._query("voice-enabled").checked = Boolean(options[ENABLED_KEY]);
    this._query("audio-source").value = options[AUDIO_KEYS.source] || "disabled";
    this._query("audio-timing").value = options[AUDIO_KEYS.timing] || "priority";
    this._query("audio-url").value = options[AUDIO_KEYS.url] || "";
    this._retainedPath = options[AUDIO_KEYS.path] || "";
    this._libraryLoaded = false;
    this._retainOption(this._query("audio-player"), options[AUDIO_KEYS.player] || "");
    this._retainOption(this._query("response-tts"), options[RESPONSE_TTS_KEY] || "");
    this._retainAudioPath();
    this._dirty = false;
    this._audioVisibility();
    this._renderList();
    this._status();
  }

  _retainAudioPath() {
    const select = this._query("audio-library");
    const value = this._retainedPath || "";
    if (value && ![...select.options].some((option) => option.value === value)) select.append(element("option", {value, text: `${value} (đã lưu / không tìm thấy)`}));
    select.value = value;
  }

  async _loadAudioLibrary() {
    if (this._libraryLoading) return;
    this._libraryLoading = true;
    const select = this._query("audio-library");
    const previous = select.value || this._retainedPath || "";
    select.disabled = true;
    try {
      const response = await this._hass.callApi("GET", "maika/panel/audio");
      const files = Array.isArray(response?.files) ? response.files : [];
      select.replaceChildren(element("option", {value: "", text: files.length ? "Chọn file MP3…" : "Không tìm thấy MP3 trong /config/www, /config/mp3 hoặc /config/media"}));
      for (const file of files) select.append(element("option", {value: file.path, text: file.path}));
    } catch (error) {
      select.replaceChildren(element("option", {value: "", text: "Không tải được danh sách MP3"}));
    } finally {
      this._libraryLoaded = true;
      this._libraryLoading = false;
      this._retainedPath = previous;
      this._retainAudioPath();
      this._audioVisibility();
    }
  }

  _audioVisibility() {
    const source = this._query("audio-source").value;
    this._query("audio-url-field").hidden = source !== "custom";
    this._query("audio-url").required = source === "custom";
    this._query("audio-url").disabled = this.isBusy || source !== "custom";
    const libraryField = this._query("audio-library-field");
    const librarySelect = this._query("audio-library");
    libraryField.hidden = source !== "library";
    this._query("audio-library-refresh").hidden = source !== "library";
    this._query("audio-library-note").hidden = source !== "library";
    librarySelect.required = source === "library";
    librarySelect.disabled = this.isBusy || source !== "library";
    if (source === "library" && !this._libraryLoaded && !this._libraryLoading && !this.isBusy) this._loadAudioLibrary();
    const notes = [];
    const ttsEntities = Object.keys(this._hass?.states || {}).filter((entityId) => entityId.startsWith("tts."));
    const hasReadRule = this._lines.some((line) => line.rule?.action === "read");
    const ttsNote = this._query("response-tts-note");
    ttsNote.hidden = !hasReadRule;
    if (hasReadRule) {
      if (!this._entry?.options?.enable_experimental_cloud_cast) notes.push("Bật ‘Cast âm thanh cloud’ để loa đọc câu trả lời.");
      if (!ttsEntities.length) notes.push("Chưa có TTS trong Home Assistant: chưa thể đọc câu trả lời.");
      else if (ttsEntities.length > 1 && !this._query("response-tts").value) notes.push("Có nhiều TTS: chọn giọng đọc câu trả lời.");
      if ((this._entry?.entities?.media_player || []).length > 1 && !this._query("audio-player").value) notes.push("Có nhiều loa: chọn loa trả lời trạng thái.");
    }
    if (source !== "disabled") {
      if (!this._entry?.options?.enable_experimental_cloud_cast) notes.push("Bật ‘Cast âm thanh cloud’ trong Cấu hình loa để phát âm báo.");
      if (source === "library" && !this._query("audio-library").value) notes.push("Chọn một file MP3 trong thư viện.");
      if ((this._entry?.entities?.media_player || []).length > 1 && !this._query("audio-player").value) notes.push("Tài khoản có nhiều loa: chọn loa phát âm phản hồi.");
    }
    this._query("audio-note").textContent = notes.join(" ");
    this._query("audio-note").hidden = !notes.length;
  }

  _renderList() {
    const list = this._query("commands");
    const query = normalizedPhrase(this._query("list-search").value);
    list.replaceChildren();
    let count = 0;
    this._lines.forEach((line, index) => {
      if (!line.rule && !line.invalid) return;
      count += line.rule ? phraseList(line.rule.phrase).length : 1;
      const rule = line.rule;
      if (query && !normalizedPhrase(`${rule?.phrase || line.raw} ${rule ? this._name(rule.entity) : ""} ${rule?.entity || ""}`).includes(query)) return;
      const card = element("article", {class: `command${line.invalid ? " invalid" : ""}`});
      card.append(element("div", {class: "command-title", text: rule ? `“${rule.phrase}”` : "Lệnh cũ cần kiểm tra"}));
      if (rule) {
        card.append(element("p", {class: "note", text: `${this._actionName(rule.entity.split(".")[0], rule.action)} · ${this._name(rule.entity)}`}), element("p", {class: "note", text: rule.entity}));
        const params = Object.entries(rule.data).map(([name, value]) => `${FIELD_NAMES[name] || name}: ${name === "volume_level" ? Math.round(Number(value) * 100) : typeof value === "boolean" ? value ? "Có" : "Không" : Array.isArray(value) ? value.join(", ") : value}`);
        if (params.length) card.append(element("p", {class: "note", text: params.join(" · ")}));
      } else card.append(element("pre", {text: line.raw}));
      const buttons = element("div", {class: "command-actions"});
      if (rule) for (const [action, label] of [["edit", "Sửa"], ["copy", "Thêm cách nói"], ["test", "Chạy thử"]]) buttons.append(element("button", {type: "button", "data-action": action, "data-index": index, text: label}));
      buttons.append(element("button", {type: "button", class: "danger", "data-action": "delete", "data-index": index, text: "Xóa"}));
      card.append(buttons);
      list.append(card);
    });
    this._query("summary").textContent = `${count} câu lệnh`;
    if (!list.children.length) list.append(element("p", {class: "muted empty", text: count ? "Không tìm thấy câu lệnh phù hợp." : "Chưa có câu lệnh. Tạo câu đầu tiên bằng 3 bước bên cạnh."}));
  }

  _resetEditor() {
    this._editing = -1;
    this._unknownData = {};
    this._query("phrase").value = "";
    this._query("editor-title").textContent = "Tạo câu lệnh mới";
    this._query("save-command").textContent = "Lưu câu lệnh";
    this._query("cancel-edit").hidden = true;
    this._targetChanged();
    this._formDirty = false;
    this._status();
  }

  async _saveCommand() {
    if (this._saving || this._testing) return;
    try {
      const rule = this._collect();
      if (!this._hass.states[rule.entity]) throw new Error("Thiết bị không còn trong Home Assistant. Hãy chọn lại.");
      const phrases = phraseList(rule.phrase);
      if (!phrases.length) throw new Error("Nhập ít nhất một câu nói.");
      const used = new Set(this._lines.flatMap((line, index) => index === this._editing || !line.rule ? [] : phraseList(line.rule.phrase).map(normalizedPhrase)));
      if (phrases.some((phrase) => used.has(normalizedPhrase(phrase)))) throw new Error("Câu nói này đã được dùng. Hãy sửa câu cũ hoặc chọn cách nói khác.");
      const otherRules = this._lines.reduce((count, line, index) => index === this._editing ? count : count + (line.rule ? phraseList(line.rule.phrase).length : line.invalid ? 1 : 0), 0);
      if (otherRules + phrases.length > this._limits.rules) throw new Error(`Tối đa ${this._limits.rules} câu lệnh.`);
      const raw = `${rule.phrase} | ${rule.entity} | ${rule.action}${Object.keys(rule.data).length ? ` | ${JSON.stringify(rule.data)}` : ""}`;
      const line = {raw, rule};
      if (this._editing >= 0) this._lines[this._editing] = line;
      else { this._editing = this._lines.length; this._lines.push(line); }
      this._query("voice-enabled").checked = true;
      this._dirty = true;
      this._renderList();
      if (await this._persist()) this._resetEditor();
    } catch (error) { this._message(error.message, "error"); }
  }

  async _persist() {
    if (this._saving || this._testing) return false;
    this._status();
    if (!this._query("voice-settings").reportValidity()) {
      this._message("Kiểm tra cài đặt âm phản hồi rồi lưu lại. Thay đổi vẫn là bản nháp.", "error");
      return false;
    }
    const options = {
      [RULES_KEY]: this._lines.map((line) => line.raw).join("\n"),
      [ENABLED_KEY]: this._query("voice-enabled").checked,
      [AUDIO_KEYS.source]: this._query("audio-source").value,
      [AUDIO_KEYS.timing]: this._query("audio-timing").value,
      [AUDIO_KEYS.url]: this._query("audio-url").value.trim(),
      [AUDIO_KEYS.path]: this._query("audio-library").value,
      [AUDIO_KEYS.player]: this._query("audio-player").value,
      [RESPONSE_TTS_KEY]: this._query("response-tts").value,
    };
    this._saving = true;
    this._status();
    try {
      await this._hass.callApi("POST", "maika/panel/options", {entry_id: this._entry.entry_id, options, expected_voice_rules: this._baselineRules, expected_voice_options: this._expectedOptions});
      this._baselineRules = options[RULES_KEY];
      this._dirty = false;
      this._query("reload-rules").hidden = true;
      this._message("Đã lưu. Loa sẽ dùng câu lệnh và âm phản hồi mới sau khi tích hợp tải lại.", "success");
      this._notifySaved(options);
      return true;
    } catch (error) {
      const code = error?.body?.message || error?.body?.error || error?.message || "";
      const errors = Object.values(error?.body?.errors || {});
      const hint = errors.includes("voice_success_audio_media_player_invalid") ? "Chọn lại loa phát âm phản hồi." : errors.includes("voice_response_tts_invalid") ? "Chọn lại giọng TTS đang có trong Home Assistant." : errors.includes("invalid_voice_success_audio_url") ? "Kiểm tra URL MP3." : errors.includes("invalid_voice_success_audio_path") ? "File MP3 không còn trong thư viện, hãy chọn lại." : "Kiểm tra kết nối, câu nói trùng hoặc thông số của thiết bị rồi thử lại.";
      this._message(code === "voice_rules_changed" ? "Cấu hình đã đổi ở nơi khác. Tải lại cấu hình đã lưu trước khi sửa tiếp; bản nháp hiện tại vẫn được giữ." : `Chưa lưu được. ${hint} Bản nháp vẫn được giữ.`, "error");
      this._query("reload-rules").hidden = false;
      return false;
    } finally {
      this._saving = false;
      this._status();
    }
  }

  _notifySaved(options) {
    this._entry = {...this._entry, options: {...this._entry.options, ...options}};
    this._expectedOptions = this._voiceOptions(this._entry.options);
    this._serverSignature = this._optionsSignature(this._entry.options);
    this.dispatchEvent(new CustomEvent("maika-voice-saved", {bubbles: true, composed: true, detail: {entry_id: this._entry.entry_id, options}}));
  }

  _voiceOptions(options) {
    return Object.fromEntries([RULES_KEY, ENABLED_KEY, RESPONSE_TTS_KEY, ...Object.values(AUDIO_KEYS)].filter((key) => key in options).map((key) => [key, options[key]]));
  }

  _status() {
    this._query("saved-state").textContent = this._saving ? "Đang lưu…" : this._dirty ? "Có thay đổi chưa lưu" : "Đã lưu";
    this._query("retry-save").hidden = !this._dirty;
    this._query("cancel-edit").hidden = !this._formDirty && this._editing < 0;
    for (const control of this.shadowRoot.querySelectorAll("button,input,select,textarea")) control.disabled = this._saving || this._testing;
    this._query("save-command").textContent = !this._query("voice-enabled").checked ? "Lưu & bật điều khiển" : this._editing >= 0 ? "Lưu thay đổi" : "Lưu câu lệnh";
    this._audioVisibility();
    this.setAttribute("aria-busy", String(this._saving || this._testing));
  }

  _message(text, kind) {
    const message = this._query("message");
    message.textContent = text;
    message.dataset.kind = kind;
    message.hidden = false;
  }

  async _reload() {
    if (this.isBusy || !window.confirm("Tải cấu hình từ Home Assistant và bỏ bản nháp chưa lưu?")) return;
    this._saving = true;
    this._status();
    try {
      const snapshot = await this._hass.callApi("GET", "maika/panel");
      const entry = snapshot.entries.find((item) => item.entry_id === this._entry.entry_id);
      if (!entry) throw new Error("Không tìm thấy tài khoản");
      this._loadOptions(entry.options || {});
      this._resetEditor();
      this._notifySaved(entry.options || {});
      this._query("reload-rules").hidden = true;
      this._message("Đã tải lại cấu hình đã lưu.", "success");
    } catch { this._message("Không tải được cấu hình. Bản nháp vẫn được giữ.", "error"); }
    finally { this._saving = false; this._status(); }
  }

  _listAction(event) {
    const button = event.target.closest("button[data-action]");
    if (!button || this._saving || this._testing) return;
    const index = Number(button.dataset.index);
    const line = this._lines[index];
    if (!line) return;
    if (button.dataset.action === "delete") {
      if (!window.confirm(`Xóa câu lệnh “${line.rule?.phrase || line.raw}”?`)) return;
      this._lines.splice(index, 1);
      if (this._editing === index) this._resetEditor();
      else if (this._editing > index) this._editing -= 1;
      this._dirty = true;
      this._renderList();
      this._persist();
      return;
    }
    if (button.dataset.action === "test") { this._test(line.rule); return; }
    if (this._formDirty && !window.confirm("Mở câu lệnh này và bỏ phần đang nhập ở trình soạn?")) return;
    const rule = line.rule;
    const domain = rule.entity.split(".")[0];
    this._query("target-type").value = ["automation", "script", "scene"].includes(domain) ? domain : "device";
    this._query("device-type").value = "";
    this._query("target-search").value = "";
    this._query("target").value = "";
    this._refreshTargets();
    this._retainOption(this._query("target"), rule.entity);
    this._editing = button.dataset.action === "copy" ? -1 : index;
    this._query("phrase").value = this._editing < 0 ? "" : rule.phrase;
    this._query("editor-title").textContent = this._editing < 0 ? "Thêm cách nói khác" : "Sửa câu lệnh";
    this._query("save-command").textContent = this._editing < 0 ? "Lưu câu lệnh" : "Lưu thay đổi";
    this._query("cancel-edit").hidden = false;
    this._targetChanged(rule.action, rule.data, true);
    this._formDirty = true;
    this._status();
    this._query("phrase").focus();
  }

  async _test(existing) {
    if (this._saving || this._testing) return;
    try {
      const rule = existing || this._collect(false);
      const domain = rule.entity.split(".")[0];
      this._validateRule(rule);
      if (!this._catalog[domain]?.[rule.action] || !this._hass.states[rule.entity]) throw new Error("Thiết bị hoặc thao tác không khả dụng.");
      if (rule.action === "read") throw new Error("Câu đọc trạng thái chỉ chạy khi nói với loa, không dùng nút chạy thử.");
      if (!window.confirm(`Chạy thử sẽ điều khiển thật: ${this._actionName(domain, rule.action)} — ${this._name(rule.entity)}. Tiếp tục?`)) return;
      this._testing = true;
      this._status();
      await this._hass.callService(domain, rule.action, {...rule.data, entity_id: rule.entity});
      this._message("Đã gửi thao tác chạy thử. Chạy thử không kiểm tra nhận diện giọng nói hoặc âm báo.", "success");
    } catch (error) { this._message(error?.message || "Không thực hiện được thao tác. Kiểm tra thiết bị và quyền tài khoản HA.", "error"); }
    finally { this._testing = false; this._status(); }
  }
}

customElements.define("maika-voice-editor", MaikaVoiceEditor);
