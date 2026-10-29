import assert from "node:assert/strict";
import {readFile, writeFile, mkdir} from "node:fs/promises";
import {createServer} from "node:http";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {join} from "node:path";
const {chromium} = await import(process.env.MAIKA_PLAYWRIGHT_MODULE || "playwright-core");

const root = fileURLToPath(new URL("../", import.meta.url));
const output = process.env.MAIKA_TEST_OUTPUT || "/tmp/maika-panel-browser";
await mkdir(output, {recursive: true});
const catalog = execFileSync(process.env.PYTHON || "python3", ["-c", 'import json, runpy, sys; print(json.dumps(runpy.run_path(sys.argv[1])["voice_action_catalog"]()))', join(root, "custom_components/maika/voice_rules.py")]);
const server = createServer(async (request, response) => {
  const path = new URL(request.url, "http://localhost").pathname;
  if (path === "/voice-actions.json") { response.setHeader("Content-Type", "application/json"); response.end(catalog); return; }
  const isScript = ["/maika-panel.js", "/maika-voice-editor.js"].includes(path);
  response.setHeader("Content-Type", isScript ? "application/javascript" : "text/html");
  response.end(await readFile(isScript ? join(root, "custom_components/maika/frontend", path.slice(1)) : join(root, "scripts/fixtures/panel.html")));
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({executablePath: process.env.MAIKA_BROWSER_EXECUTABLE, headless: true, args: ["--no-sandbox"]});
const context = await browser.newContext();
const image = process.env.MAIKA_TEST_HERO_IMAGE ? await readFile(process.env.MAIKA_TEST_HERO_IMAGE) : Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZlSAAAAAASUVORK5CYII=", "base64");
await context.route("**/olli-maika-2.jpg", (route) => route.fulfill({contentType: process.env.MAIKA_TEST_HERO_IMAGE ? "image/jpeg" : "image/png", body: image}));
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error)));
const waitRender = async () => {
  await page.waitForTimeout(100);
  await page.waitForFunction(() => document.querySelector("maika-panel")._renderFrame === null);
};
const load = async () => {
  await page.goto(base);
  await page.locator('[data-sec="settings"]').waitFor();
  await page.evaluate(() => document.querySelector("maika-panel")?.scrollTo({top: 0, behavior: "instant"}));
  await page.waitForTimeout(500);
};
const openSectionFold = async (section, targetPage = page) => {
  const fold = targetPage.locator(`[data-card="${section}"] .section-fold`).first();
  if (!await fold.count()) return;
  await fold.waitFor();
  if (await fold.getAttribute("open") === null) await fold.locator(":scope > summary").click();
};
const openSetup = async (key, targetPage = page) => {
  await openSectionFold("settings", targetPage);
  const section = targetPage.locator('[data-sec="settings"]');
  const accordion = section.locator(`.panel-accordion--${key}`);
  await accordion.waitFor();
  if (await accordion.getAttribute("open") === null) await accordion.locator("summary").click();
};
const metrics = [];

async function verifyVoiceEditor() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  await openSectionFold("voice");
  const editor = page.locator("maika-voice-editor");
  const input = (id) => editor.locator(`#${id}`);
  const rules = () => page.evaluate(() => snapshot.entries[0].options.voice_command_rules);
  const serverOptions = () => page.evaluate(() => structuredClone(snapshot.entries[0].options));
  const callsCount = () => page.evaluate(() => calls.filter((call) => call.service).length);
  const confirm = async (action, accept = true) => {
    await Promise.all([page.waitForEvent("dialog").then((dialog) => accept ? dialog.accept() : dialog.dismiss()), action()]);
  };
  const waitSaved = async () => {
    await page.waitForFunction(() => !document.querySelector("maika-panel").shadowRoot.querySelector("maika-voice-editor").isBusy);
    assert.match(await input("message").innerText(), /Đã lưu/);
  };
  const choose = async (entityId, action) => {
    const domain = entityId.split(".")[0];
    await input("target-type").selectOption(["automation", "script", "scene"].includes(domain) ? domain : "device");
    if (!["automation", "script", "scene"].includes(domain)) await input("device-type").selectOption("");
    await input("target-search").fill("");
    await input("target").selectOption(entityId);
    if (action) await input("action").selectOption(action);
  };
  const save = async (phrase) => { await input("phrase").fill(phrase); await input("save-command").click(); await waitSaved(); };
  const initial = await rules();
  assert.equal(await input("summary").innerText(), "2 câu lệnh");
  await choose("light.phong_khach", "turn_on");
  await save("bật đèn phòng khách, mở đèn phòng khách");
  assert.equal(await input("summary").innerText(), "4 câu lệnh");
  assert.match(await rules(), /bật đèn phòng khách, mở đèn phòng khách \| light\.phong_khach \| turn_on/);
  await input("phrase").fill("mở đèn phòng khách");
  await input("save-command").click();
  assert.match(await input("message").innerText(), /đã được dùng/);
  assert.doesNotMatch(await rules(), /\nmở đèn phòng khách \|/);
  await input("target-search").fill("den phong");
  assert.match(await input("target").innerText(), /Đèn phòng khách/);
  assert.doesNotMatch(await input("target").innerText(), /Điều hòa/);
  await choose("light.phong_khach", "turn_on");
  await input("param-brightness_pct").fill("70");
  await save("Đèn khách bảy mươi");
  assert((await rules()).startsWith(initial));
  assert.match(await rules(), /Đèn khách bảy mươi \| light.phong_khach \| turn_on \| \{"brightness_pct":70\}/);
  assert.equal(await callsCount(), 0);
  assert.equal(await input("phrase").inputValue(), "");
  const beforeDuplicate = await rules();
  await input("phrase").fill("den khach bay muoi!!!");
  await input("save-command").click();
  assert.match(await input("message").innerText(), /đã được dùng/);
  assert.equal(await rules(), beforeDuplicate);
  await choose("automation.di_ngu");
  assert.equal(await input("action").inputValue(), "trigger");
  assert.equal(await input("param-skip_condition").inputValue(), "false");
  await save("Bắt đầu đi ngủ");
  assert.match(await rules(), /\{"skip_condition":false\}/);
  await editor.locator(".command").filter({hasText: "chạy lệnh cũ"}).getByRole("button", {name: "Sửa", exact: true}).click();
  assert.equal(await input("param-skip_condition").inputValue(), "");
  await input("save-command").click(); await waitSaved();
  assert.match(await rules(), /chạy lệnh cũ \| automation.di_ngu \| trigger\n/);
  console.log("PASS visual create/search, exact legacy preservation, duplicate normalization, automation conditions and no actions on save");

  await choose("fan.phong_khach", "set_percentage");
  await input("param-percentage").fill("101");
  assert.equal(await input("param-percentage").evaluate((node) => node.checkValidity()), false);
  await input("param-percentage").fill("60"); await save("Quạt sáu mươi");
  await choose("climate.may_lanh", "set_hvac_mode");
  assert.deepEqual(await input("param-hvac_mode").locator("option").evaluateAll((nodes) => nodes.map((node) => node.value)), ["", "off", "cool"]);
  await input("action").selectOption("set_temperature");
  assert.equal(await input("param-temperature").getAttribute("min"), "16");
  assert.equal(await input("param-temperature").getAttribute("max"), "30");
  await input("param-temperature").fill("26"); await save("Điều hòa hai sáu");
  await choose("cover.rem", "set_cover_position"); await input("param-position").fill("50"); await save("Rèm một nửa");
  await choose("media_player.tv", "volume_set"); await input("param-volume_level").fill("35"); await save("TV âm lượng nhỏ");
  assert.match(await rules(), /\{"volume_level":0.35\}/);
  await choose("input_select.che_do", "select_option"); await input("param-option").selectOption("Đi vắng"); await save("Nhà đi vắng");
  for (const [entityId, action, phrase] of [["script.chao_mung", "turn_on", "Chào mừng"], ["scene.xem_phim", "turn_on", "Xem phim"], ["button.chuong", "press", "Bấm chuông"]]) {
    await choose(entityId, action); await save(phrase);
  }
  await choose("lock.cua", "lock");
  assert.equal(await input("action").locator('option[value="unlock"]').count(), 0);
  await choose("timer.bep", "start");
  await input("param-duration").fill("00:99:00");
  await input("phrase").fill("Hẹn giờ lỗi"); await input("save-command").click();
  assert.match(await input("message").innerText(), /Kiểm tra/);
  await input("param-duration").fill("00:05:00"); await save("Hẹn giờ bếp");
  console.log("PASS fan, climate dynamic modes/bounds, cover, volume scaling, helpers, scripts/scenes/buttons and safe action allow-list");

  await choose("light.phong_khach", "turn_on");
  await input("param-brightness_pct").fill("45");
  await input("phrase").fill("Bản nháp được giữ");
  await input("phrase").evaluate((node) => node.setSelectionRange(3, 6));
  await page.evaluate(() => {
    window.previousEditor = panel.shadowRoot.querySelector("maika-voice-editor");
    window.previousPhrase = previousEditor.shadowRoot.getElementById("phrase");
    states[panel._entity("media_player")].attributes.media_title = "Tên bài vừa đổi";
    states["light.den_moi"] = {state: "on", attributes: {friendly_name: "Đèn mới vừa thêm"}};
    tick();
  });
  await waitRender();
  assert.equal(await input("phrase").inputValue(), "Bản nháp được giữ");
  assert.equal(await input("param-brightness_pct").inputValue(), "45");
  assert(await page.evaluate(() => panel.shadowRoot.querySelector("maika-voice-editor") === previousEditor && previousEditor.shadowRoot.activeElement === previousPhrase));
  assert.deepEqual(await input("phrase").evaluate((node) => [node.selectionStart, node.selectionEnd]), [3, 6]);
  assert.match(await input("target").innerText(), /Đèn mới vừa thêm/);
  await page.locator('[data-action="device"][data-serial="SERIAL-0-1"]').click();
  assert.equal(await input("phrase").inputValue(), "Bản nháp được giữ");
  await confirm(() => page.locator('[data-action="entry"][data-index="1"]').click(), false);
  assert.equal(await input("phrase").inputValue(), "Bản nháp được giữ");
  const beforeActions = await callsCount();
  await confirm(() => input("test-command").click(), false);
  assert.equal(await callsCount(), beforeActions);
  await confirm(() => input("test-command").click());
  await waitRender();
  assert.equal(await callsCount(), beforeActions + 1);
  assert.deepEqual(await page.evaluate(() => calls.filter((call) => call.service).at(-1)), {domain: "light", service: "turn_on", data: {entity_id: "light.phong_khach", brightness_pct: 45}});
  console.log("PASS HA live updates, external entities, cursor/device/account draft preservation and explicit test confirmation");

  await page.evaluate(() => { failSave = true; });
  await input("save-command").click(); await waitRender();
  assert.match(await input("message").innerText(), /Chưa lưu được/);
  assert.equal(await input("phrase").inputValue(), "Bản nháp được giữ");
  assert.doesNotMatch(await rules(), /Bản nháp được giữ/);
  await page.evaluate(() => { failSave = false; });
  await openSetup("config");
  await page.locator('[name="scan_interval"]').fill("85");
  await page.locator('[data-form="options"] button[type="submit"]').click(); await waitRender();
  assert.equal(await input("phrase").inputValue(), "Bản nháp được giữ");
  await input("retry-save").click(); await waitSaved();
  assert.match(await rules(), /Bản nháp được giữ/);
  await confirm(() => input("cancel-edit").click());
  await editor.locator(".command").filter({hasText: "Đèn khách bảy mươi"}).getByRole("button", {name: "Sửa", exact: true}).click();
  await input("phrase").fill("Đèn sửa từ tab này");
  await page.evaluate(() => { snapshot.entries[0].options.voice_command_rules += "\n# Thay đổi từ tab khác"; });
  await page.locator('[data-action="refreshdata"]').click(); await waitRender();
  assert.equal(await input("phrase").inputValue(), "Đèn sửa từ tab này");
  await input("save-command").click(); await waitRender();
  assert.match(await input("message").innerText(), /đã đổi ở nơi khác/);
  assert.doesNotMatch(await rules(), /Đèn sửa từ tab này/);
  assert.equal(await input("phrase").inputValue(), "Đèn sửa từ tab này");
  await confirm(() => input("reload-rules").click()); await waitRender();
  assert.equal(await input("phrase").inputValue(), "");
  assert.match(await rules(), /# Thay đổi từ tab khác/);
  await input("audio-source").selectOption("disabled");
  await page.evaluate(() => { snapshot.entries[0].options.voice_success_audio_timing = "after_success"; });
  await input("voice-settings").locator('button[type="submit"]').click(); await waitRender();
  assert.match(await input("message").innerText(), /đã đổi ở nơi khác/);
  await confirm(() => input("reload-rules").click()); await waitRender();
  console.log("PASS failed save retry, partial general settings, optimistic concurrency for rules/audio and conflict reload");

  const original = editor.locator(".command").filter({hasText: "Đèn khách bảy mươi"});
  await original.getByRole("button", {name: "Thêm cách nói", exact: true}).click();
  assert.equal(await input("phrase").inputValue(), "");
  assert.equal(await input("param-brightness_pct").inputValue(), "70");
  await save("Cách nói khác cho đèn");
  const copied = editor.locator(".command").filter({hasText: "Cách nói khác cho đèn"});
  await confirm(() => copied.getByRole("button", {name: "Xóa", exact: true}).click(), false);
  assert.match(await rules(), /Cách nói khác cho đèn/);
  await confirm(() => copied.getByRole("button", {name: "Xóa", exact: true}).click()); await waitSaved();
  assert.doesNotMatch(await rules(), /Cách nói khác cho đèn/);
  assert.match(await rules(), /# Cấu hình cũ được giữ nguyên/);
  assert.match(await rules(), /# Thay đổi từ tab khác/);
  await input("list-search").fill("quat sau");
  assert.equal(await editor.locator(".command").count(), 1);
  await input("list-search").fill("");
  console.log("PASS copy/edit/delete, cancellation, accent-insensitive list search and preserved legacy comments/parameters");

  const players = await input("audio-player").locator("option").evaluateAll((nodes) => nodes.map((node) => node.value));
  assert.equal(players.length, 3);
  assert(!players.includes("media_player.tv"));
  await input("audio-player").selectOption(players[2]);
  await input("audio-source").selectOption("custom");
  await input("audio-url").fill("https://example.test/thanh-cong.mp3");
  await page.evaluate(() => { states["light.den_moi"].attributes.friendly_name = "Đèn mới đổi tên"; tick(); }); await waitRender();
  assert.equal(await input("audio-player").inputValue(), players[2]);
  await input("voice-settings").locator('button[type="submit"]').click(); await waitSaved();
  assert.equal((await serverOptions()).voice_success_audio_url, "https://example.test/thanh-cong.mp3");
  await input("audio-url").fill("invalid-url");
  await input("audio-source").selectOption("disabled");
  assert(await input("audio-url").isDisabled());
  await input("audio-source").selectOption("library");
  await page.waitForFunction(() => panel.shadowRoot.querySelector("maika-voice-editor").shadowRoot.querySelectorAll("#audio-library option").length === 3);
  const libraryOptions = await input("audio-library").locator("option").evaluateAll((nodes) => nodes.map((node) => node.value));
  assert.deepEqual(libraryOptions, ["", "mp3/maika.mp3", "www/thanh-cong.mp3"]);
  assert(await input("audio-url").isDisabled());
  await input("audio-library").selectOption("mp3/maika.mp3");
  await input("voice-settings").locator('button[type="submit"]').click(); await waitSaved();
  assert.equal((await serverOptions()).voice_success_audio_source, "library");
  assert.equal((await serverOptions()).voice_success_audio_path, "mp3/maika.mp3");
  await input("audio-source").selectOption("disabled");
  await input("voice-settings").locator('button[type="submit"]').click(); await waitSaved();
  await input("voice-enabled").uncheck();
  await input("voice-settings").locator('button[type="submit"]').click(); await waitSaved();
  await choose("light.phong_khach", "turn_off");
  assert.equal(await input("save-command").innerText(), "Lưu & bật điều khiển");
  await save("Tắt đèn phòng khách");
  assert.equal((await serverOptions()).enable_voice_command_sensor, true);
  const unlabeled = await editor.evaluate((node) => [...node.shadowRoot.querySelectorAll("input,select")].filter((control) => !control.getAttribute("aria-label") && !control.labels?.length).map((control) => control.id));
  assert.deepEqual(unlabeled, []);
  await choose("sensor.nhiet_do", "read");
  assert(await input("test-command").isHidden(), "Reading a state cannot be run as a control service");
  assert.match(await input("action-note").innerText(), /đọc trạng thái/i);
  await input("response-tts").selectOption("tts.piper");
  await save("nhiệt độ phòng khách");
  assert.match(await rules(), /nhiệt độ phòng khách \| sensor\.nhiet_do \| read(?:\n|$)/);
  assert.equal((await serverOptions()).voice_response_tts_entity_id, "tts.piper");
  await choose("light.phong_khach", "turn_on");
  await confirm(() => page.locator('[data-action="entry"][data-index="1"]').click());
  assert.equal(await input("phrase").inputValue(), "");
  assert.equal(await input("summary").innerText(), "2 câu lệnh");
  console.log("PASS per-account speaker selection, custom/disabled audio validity, explicit enable and accessible labels");

  await page.locator('[data-action="entry"][data-index="0"]').click();
  const storedRules = await rules();
  execFileSync(process.env.PYTHON || "python3", ["-c", 'import runpy, sys; parse = runpy.run_path(sys.argv[1])["parse_voice_command_rules"]; rules = parse(sys.stdin.read()); assert len(rules) >= 10', join(root, "custom_components/maika/voice_rules.py")], {input: storedRules});
  await writeFile(join(output, "voice-options.json"), JSON.stringify(await serverOptions(), null, 2));
  console.log("PASS generated browser rules round-trip through the actual Python backend validator");
}

async function verifyGlassAndMotion() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  const wave = page.locator(".sound-wave i").first();
  const aura = page.locator(".hero-aura i").first();
  const animation = (locator) => locator.evaluate((element) => getComputedStyle(element).animationName);
  const updatePlayback = async (state, online = "on", muted = false) => {
    await page.evaluate(({state, online, muted}) => {
      const media = states[panel._entity("media_player")];
      media.state = state;
      media.attributes.is_volume_muted = muted;
      states[panel._entity("binary_sensor", "online")].state = online;
      tick();
    }, {state, online, muted});
    await waitRender();
  };
  const contrast = (foreground, background) => {
    const luminance = (hex) => {
      const channels = [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255).map((value) => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
      return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
    };
    const values = [luminance(foreground), luminance(background)].sort((first, second) => second - first);
    return (values[0] + .05) / (values[1] + .05);
  };
  for (const theme of ["light", "dark"]) {
    await page.locator('[data-action="theme"]').selectOption(theme);
    const palette = await page.evaluate(() => {
      const style = getComputedStyle(panel);
      return Object.fromEntries(["accent", "text", "muted", "surface", "brand-start", "brand-end", "brand-ink"].map((key) => [key, style.getPropertyValue(`--${key}`).trim()]));
    });
    const accentChannels = [1, 3, 5].map((offset) => parseInt(palette.accent.slice(offset, offset + 2), 16));
    assert(accentChannels[0] > accentChannels[1] && accentChannels[1] > accentChannels[2], "The accent stays orange in both themes");
    for (const token of ["accent", "text", "muted"]) assert(contrast(palette[token], palette.surface) >= 4.5, `${theme} ${token} contrast on solid card fallback`);
    for (const token of ["brand-start", "brand-end"]) assert(contrast(palette["brand-ink"], palette[token]) >= 4.5, `${theme} ${token} button contrast`);
    await page.locator(".pill--on").hover();
    await page.waitForTimeout(300);
    const buttonInk = [1, 3, 5].map((offset) => parseInt(palette["brand-ink"].slice(offset, offset + 2), 16));
    assert.equal(await page.locator(".pill--on").evaluate((element) => getComputedStyle(element).color), `rgb(${buttonInk.join(", ")})`, "Active navigation keeps legible dark text on hover");
    assert.match(await page.locator(".hero").evaluate((element) => getComputedStyle(element).backdropFilter), /blur/);
  }
  assert.equal(await animation(wave), "sound-wave");
  assert.equal(await animation(aura), "sound-ripple");
  const movingTransform = await wave.evaluate((element) => getComputedStyle(element).transform);
  await page.waitForTimeout(250);
  assert.notEqual(await wave.evaluate((element) => getComputedStyle(element).transform), movingTransform, "The waveform really animates over time");
  await page.evaluate(() => { window.savedHeroImage = panel.shadowRoot.querySelector(".hero-media img"); });
  for (const [state, online, muted, expected] of [["paused", "on", false, "paused"], ["idle", "on", false, "idle"], ["off", "on", false, "off"], ["buffering", "on", false, "buffering"], ["standby", "on", false, "standby"], ["playing", "on", true, "muted"], ["playing", "off", false, "offline"], ["unavailable", "on", false, "offline"], ["playing", "unavailable", false, "unknown"]]) {
    await updatePlayback(state, online, muted);
    assert.equal(await page.locator(".hero").getAttribute("data-activity"), expected);
    assert.equal(await animation(wave), "none");
    assert.equal(await animation(aura), "none");
    assert.equal(await page.locator(".media-now").evaluate((element) => getComputedStyle(element, "::before").animationName), "none");
    assert.equal(await animation(page.locator(".eq i").first()), "none");
    if (["offline", "unknown"].includes(expected)) assert.equal(await page.locator(".hero").getAttribute("data-connected"), null);
  }
  await updatePlayback("playing");
  assert.equal(await animation(wave), "sound-wave");
  assert(await page.evaluate(() => savedHeroImage === panel.shadowRoot.querySelector(".hero-media img")));
  console.log("PASS orange glass themes, text/button palette contrast and live playback/muted/offline/unknown animations without reloading the image");

  assert.equal(await page.locator('[data-action="effects"]').count(), 0, "Motion stays automatic, there is no animation toggle button");
  await openSetup("license");
  await page.locator('[name="license_key"]').fill("MAIKA-MOTION-DRAFT");
  await openSectionFold("voice");
  await page.locator("maika-voice-editor").locator("#phrase").fill("bản nháp không mất khi đổi giao diện");
  await page.locator('[data-action="theme"]').selectOption("light");
  assert.equal(await page.locator('[name="license_key"]').inputValue(), "MAIKA-MOTION-DRAFT");
  assert.equal(await page.locator("maika-voice-editor").locator("#phrase").inputValue(), "bản nháp không mất khi đổi giao diện");
  await load();
  await page.emulateMedia({reducedMotion: "reduce"});
  await page.waitForFunction(() => panel.hasAttribute("data-reduced-motion"));
  assert.equal(await animation(wave), "none");
  assert.equal(await animation(aura), "none");
  assert.equal(await page.locator("maika-voice-editor").getAttribute("data-reduced-motion"), "");
  await page.emulateMedia({reducedMotion: "no-preference"});
  await page.waitForFunction(() => !panel.hasAttribute("data-reduced-motion"));
  assert.equal(await animation(wave), "sound-wave");
  await page.waitForFunction(() => !panel.shadowRoot.querySelector("maika-voice-editor").hasAttribute("data-reduced-motion"));
  await page.setViewportSize({width: 1440, height: 900});
  await page.locator('[data-action="jump"][data-section="settings"]').click();
  await page.evaluate(() => { panel.scrollTop = panel.scrollHeight; });
  await page.waitForFunction(() => panel.shadowRoot.querySelector(".hero").hasAttribute("data-motion-paused"));
  assert.equal(await wave.evaluate((element) => getComputedStyle(element).animationPlayState), "paused");
  await page.locator('[data-action="jump"][data-section="overview"]').click();
  await page.waitForFunction(() => !panel.shadowRoot.querySelector(".hero").hasAttribute("data-motion-paused"));
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", {configurable: true, value: true});
    document.dispatchEvent(new Event("visibilitychange"));
  });
  assert.equal(await wave.evaluate((element) => getComputedStyle(element).animationPlayState), "paused");
  await page.evaluate(() => { delete document.hidden; document.dispatchEvent(new Event("visibilitychange")); });
  assert.equal(await wave.evaluate((element) => getComputedStyle(element).animationPlayState), "running");
  console.log("PASS automatic motion, draft preservation across theme change, system reduced motion and offscreen/background pause");

  const session = await context.newCDPSession(page);
  for (const feature of [{name: "prefers-reduced-transparency", value: "reduce"}, {name: "prefers-contrast", value: "more"}]) {
    await session.send("Emulation.setEmulatedMedia", {features: [feature]});
    assert.equal(await page.locator(".hero").evaluate((element) => getComputedStyle(element).backdropFilter), "none");
    assert.equal(await page.locator(".toolbar").evaluate((element) => getComputedStyle(element).backdropFilter), "none");
  }
  await session.send("Emulation.setEmulatedMedia", {features: []});
  await session.detach();
  assert.equal(await page.evaluate(() => calls.filter((call) => call.service || call.method === "POST").length), 0);
  console.log("PASS solid readable fallback for reduced transparency/high contrast; no settings or device actions from visual effects");
}

async function verifySectionFolds() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  assert.equal(await page.locator('[data-sec="overview"] .section-fold').count(), 0);
  for (const section of ["media", "chat", "voice", "device", "settings"]) {
    const fold = page.locator(`[data-card="${section}"] .section-fold`).first();
    assert.equal(await fold.count(), 1, `${section} is folded`);
    assert.equal(await fold.getAttribute("open"), null, `${section} starts closed`);
    assert.equal(await fold.locator(":scope > summary").getAttribute("aria-expanded"), null);
  }
  await page.locator('[data-card="media"] .section-fold > summary').click();
  assert.equal(await page.locator('[data-card="media"] .section-fold').getAttribute("open"), "");
  assert(await page.locator('[data-card="media"] .media-now').isVisible(), "Media content expands on demand");
  await page.locator('[data-action="jump"][data-section="voice"]').click();
  await page.waitForFunction(() => panel.shadowRoot.querySelector('[data-card="voice"] .section-fold').open);
  assert.equal(await page.evaluate(() => panel.shadowRoot.querySelector('[data-card="voice"] .section-fold').open), true);
  console.log("PASS overview stays open, other sections fold, and navigation expands the selected section");
}

async function verifyDeviceAccordion() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  assert.deepEqual(await page.locator(".nav .pill").allTextContents(), ["Tổng quan", "Trò chuyện", "Giọng nói", "Nhắc hẹn", "Thiết bị", "Thiết lập"]);
  for (const section of ["status", "identity", "info", "firmware", "warranty"]) {
    assert.equal(await page.locator(`[data-action="jump"][data-section="${section}"]`).count(), 0);
  }
  await page.locator('[data-action="jump"][data-section="device"]').click();
  assert.equal(await page.locator('[data-action="jump"][data-section="device"]').getAttribute("aria-current"), "location");
  const card = page.locator('[data-sec="device"]');
  await card.waitFor();
  const status = card.locator(".panel-accordion--status");
  const identity = card.locator(".panel-accordion--identity");
  const firmware = card.locator(".panel-accordion--firmware");
  assert.equal(await card.locator(".panel-accordion").count(), 5);
  assert.deepEqual(await card.locator(".panel-accordion__copy b").allTextContents(), ["Trạng thái loa", "Tên & vị trí", "Thông tin thiết bị", "Firmware & hệ thống", "Bảo hành"]);
  assert.equal(await status.getAttribute("open"), "");
  assert.equal(await identity.getAttribute("open"), null);
  assert.equal(await firmware.getAttribute("open"), null);
  assert.equal(await status.locator(".tile").count(), 6);
  assert.equal(await card.locator(".panel-accordion--info .row").count(), 7);
  assert.equal(await firmware.locator(".row").count(), 3);
  assert.equal(await card.locator(".panel-accordion--warranty .tile").count(), 2);
  assert.equal(await identity.locator("input").count(), 3);
  assert.equal(await firmware.locator(".rows").isVisible(), false);

  await identity.locator("summary").click();
  assert.equal(await identity.getAttribute("open"), "");
  assert.notEqual(await identity.locator(".panel-accordion__arrow").evaluate((node) => getComputedStyle(node).transform), "none");
  await page.evaluate(() => { states[panel._entity("binary_sensor", "online")].state = "off"; tick(); });
  await waitRender();
  assert.equal(await identity.getAttribute("open"), "", "Open accordion survives live data re-render");
  assert.equal(await status.locator(".tile .v").first().innerText(), "Mất kết nối");
  await identity.locator("summary").press("Enter");
  assert.equal(await identity.getAttribute("open"), null);
  await identity.locator("summary").press("Enter");
  assert.equal(await identity.getAttribute("open"), "");
  await page.evaluate(() => { states[panel._entity("binary_sensor", "online")].state = "on"; tick(); });
  await waitRender();
  console.log("PASS one device tab, five accessible accordions, live data and keyboard/open-state preservation");
}

async function verifySetupAccordion() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  for (const section of ["assistant", "license", "tools"]) {
    assert.equal(await page.locator(`[data-action="jump"][data-section="${section}"]`).count(), 0);
  }
  await page.locator('[data-action="jump"][data-section="settings"]').click();
  const card = page.locator('[data-sec="settings"]');
  await card.waitFor();
  const assistant = card.locator(".panel-accordion--assistant");
  const license = card.locator(".panel-accordion--license");
  const config = card.locator(".panel-accordion--config");
  const tools = card.locator(".panel-accordion--tools");
  assert.equal(await card.locator(".panel-accordion").count(), 4);
  assert.deepEqual(await card.locator(".panel-accordion__copy b").allTextContents(), ["Trợ lý Maika", "Bản quyền", "Cấu hình loa", "Công cụ"]);
  assert.equal(await assistant.getAttribute("open"), "");
  assert.equal(await license.getAttribute("open"), null);
  assert.equal(await config.getAttribute("open"), null);
  assert.equal(await tools.getAttribute("open"), null);
  assert.equal(await license.getByRole("textbox", {name: "License key"}).isVisible(), false);
  assert.equal(await config.locator('[name="scan_interval"]').isVisible(), false);

  await openSetup("license");
  assert.equal(await license.getAttribute("open"), "");
  assert.equal(await license.getByRole("textbox", {name: "License key"}).isVisible(), true);
  await openSetup("config");
  assert.equal(await config.locator('[name="scan_interval"]').isVisible(), true);
  await openSetup("tools");
  assert.equal(await tools.getByRole("button", {name: "Làm mới"}).isVisible(), true);
  await page.evaluate(() => {
    const licenseExpiresAt = Math.floor(Date.now() / 1000) + 40 * 86400;
    snapshot.entries[0].license = {...snapshot.entries[0].license, plan: "month_1", expires_at: licenseExpiresAt, license_expires_at: licenseExpiresAt};
    tick();
  });
  await waitRender();
  assert.equal(await license.getAttribute("open"), "", "Open settings accordion survives live data re-render");
  await license.locator("summary").press("Enter");
  assert.equal(await license.getAttribute("open"), null);
  await license.locator("summary").press("Enter");
  assert.equal(await license.getAttribute("open"), "");
  console.log("PASS one settings tab, four accessible accordions and preserved open state");
}

async function verifyDesktopScrolling() {
  await page.setViewportSize({width: 1440, height: 900});
  await load();
  for (const section of ["media", "chat", "voice", "device", "settings"]) await openSectionFold(section);
  await page.waitForTimeout(200);
  const geometry = await page.evaluate(() => ({height: panel.clientHeight, content: panel.scrollHeight, viewport: innerHeight}));
  assert(geometry.height <= geometry.viewport, "The panel stays within the viewport when HA wrappers have auto height");
  assert(geometry.content > geometry.height, "The panel owns the vertical scroll area instead of expanding to its content");
  const activeSpeaker = await page.evaluate(() => panel._activeSerial());
  const pointAt = async (locator) => {
    const rect = await locator.boundingBox();
    await page.mouse.move(rect.x + Math.min(rect.width / 2, 100), rect.y + Math.min(rect.height / 2, 40));
  };
  const top = async () => {
    await page.evaluate(() => panel.scrollTo({top: 0, behavior: "instant"}));
    await page.waitForTimeout(150);
  };
  for (const selector of [".hero-media", ".hero-showcase", ".nav", ".chips--scroll", '[data-card="media"]']) {
    await top();
    await pointAt(page.locator(selector).first());
    await page.mouse.wheel(0, 360);
    await page.waitForFunction(() => panel.scrollTop > 200);
    await page.waitForTimeout(150);
    await pointAt(page.locator(".nav"));
    await page.mouse.wheel(0, -360);
    await page.waitForFunction(() => panel.scrollTop < 5);
  }
  await openSetup("config");
  await pointAt(page.locator(".nav"));
  await page.mouse.wheel(0, 20000);
  await page.waitForFunction(() => Math.abs(panel.scrollHeight - panel.clientHeight - panel.scrollTop) < 2);
  assert(await page.locator('[name="scan_interval"]').isVisible());
  await page.waitForTimeout(150);
  await page.mouse.wheel(0, -20000);
  await page.waitForFunction(() => panel.scrollTop < 5);
  assert.equal(await page.evaluate(() => document.documentElement.scrollTop), 0);
  assert.equal(await page.evaluate(() => panel._activeSerial()), activeSpeaker);
  console.log("PASS desktop wheel over image, swipe surface, navigation, speaker rails and cards; reach bottom and return to top in HA wrappers");

  await page.evaluate(() => { document.querySelector("#sidebar").style.display = "block"; });
  await page.setViewportSize({width: 1024, height: 720});
  await top();
  assert.equal(await page.evaluate(() => panel.clientHeight), 720);
  const nav = page.locator(".nav");
  if (!await nav.evaluate((element) => element.scrollWidth > element.clientWidth)) {
    await page.evaluate(() => { panel.shadowRoot.querySelector(".nav").style.maxWidth = "360px"; });
  }
  assert(await nav.evaluate((element) => element.scrollWidth > element.clientWidth));
  await pointAt(nav);
  await page.mouse.wheel(240, 0);
  await page.waitForFunction(() => panel.shadowRoot.querySelector(".nav").scrollLeft > 50);
  assert.equal(await page.evaluate(() => panel.scrollTop), 0, "Horizontal trackpad scrolling stays in the navigation rail");
  await page.waitForTimeout(150);
  await page.mouse.wheel(0, 360);
  await page.waitForFunction(() => panel.scrollTop > 200);
  await page.evaluate(() => { panel.shadowRoot.querySelector(".nav").style.maxWidth = ""; document.querySelector("ha-panel-custom").style.height = "540px"; });
  assert.equal(await page.evaluate(() => panel.clientHeight), 540, "A shorter explicit HA container still constrains the panel");
  await page.evaluate(() => { document.querySelector("ha-panel-custom").style.height = ""; });
  console.log("PASS resized desktop, HA sidebar, horizontal trackpad and vertical wheel over overflowing navigation");

  await page.setViewportSize({width: 1440, height: 900});
  await load();
  await page.evaluate(async () => {
    snapshot.entries[0].options.voice_command_rules += Array.from({length: 40}, (_, index) => `bật đèn thử ${index} | light.phong_khach | turn_on`).join("\n");
    await panel._load();
  });
  await openSectionFold("voice");
  const commands = page.locator("maika-voice-editor").locator("#commands");
  await commands.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await pointAt(commands);
  const outerTop = await page.evaluate(() => panel.scrollTop);
  await page.mouse.wheel(0, 200);
  await page.waitForFunction(() => panel.shadowRoot.querySelector("maika-voice-editor").shadowRoot.querySelector("#commands").scrollTop > 100);
  assert.equal(await page.evaluate(() => panel.scrollTop), outerTop, "Nested command list scrolls before the outer panel");
  await commands.evaluate((element) => { element.scrollTop = element.scrollHeight; });
  await page.waitForTimeout(200);
  await page.mouse.wheel(0, 240);
  await page.waitForFunction((previous) => panel.scrollTop > previous + 100, outerTop);
  assert.equal(await page.evaluate(() => calls.filter((call) => call.service || call.method === "POST").length), 0);
  console.log("PASS native nested command scrolling and scroll chaining at the list edge without device actions or saves");
}

async function verifySpeakerGestures() {
  const touchContext = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
  await touchContext.route("**/olli-maika-2.jpg", (route) => route.fulfill({contentType: process.env.MAIKA_TEST_HERO_IMAGE ? "image/jpeg" : "image/png", body: image}));
  const touchPage = await touchContext.newPage();
  touchPage.on("pageerror", (error) => errors.push(String(error)));
  const touchSession = await touchContext.newCDPSession(touchPage);
  const activeSpeaker = () => touchPage.evaluate(() => panel._activeSerial());
  const overview = async () => {
    await touchPage.locator('[data-action="jump"][data-section="overview"]').click();
    await touchPage.waitForTimeout(600);
  };
  const swipe = async (deltaX, deltaY = 0, selector = ".hero-showcase") => {
    const rect = await touchPage.locator(selector).boundingBox();
    const startX = rect.x + rect.width * (deltaX < 0 ? .8 : .2);
    const startY = rect.y + (selector === ".hero-showcase" ? Math.min(rect.height * .25, 32) : rect.height / 2);
    await touchSession.send("Input.dispatchTouchEvent", {type: "touchStart", touchPoints: [{x: startX, y: startY}]});
    for (let step = 1; step <= 3; step += 1) {
      await touchSession.send("Input.dispatchTouchEvent", {type: "touchMove", touchPoints: [{x: startX + deltaX * step / 3, y: startY + deltaY * step / 3}]});
      await touchPage.waitForTimeout(10);
    }
    await touchSession.send("Input.dispatchTouchEvent", {type: "touchEnd", touchPoints: []});
    await touchPage.waitForTimeout(400);
  };
  try {
    await touchPage.goto(base);
    await touchPage.locator(".speaker-pager").waitFor();
    await touchPage.waitForFunction(() => document.querySelector("maika-panel")._busy === false);
    await openSetup("license", touchPage);
    await openSetup("config", touchPage);
    await touchPage.locator('[name="license_key"]').fill("MAIKA-UNSAVED-KEY");
    await touchPage.locator('[name="scan_interval"]').fill("91");
    await openSectionFold("voice", touchPage);
    await touchPage.locator("maika-voice-editor").locator("#phrase").fill("bản nháp giọng nói");
    await overview();
    await touchPage.evaluate(() => { document.querySelector("maika-panel").scrollTop = 0; });
    const initial = await activeSpeaker();
    const initialImage = await touchPage.locator(".hero-media").boundingBox();
    assert(initialImage.width <= 180 && initialImage.height <= 200);
    assert.match(await touchPage.locator(".hero-showcase").evaluate((element) => getComputedStyle(element).touchAction), /pan-y/);
    await swipe(-150);
    const second = await activeSpeaker();
    assert.notEqual(second, initial, "A horizontal touch swipe selects the next speaker");
    assert.equal(await touchPage.locator('[name="license_key"]').inputValue(), "MAIKA-UNSAVED-KEY");
    assert.equal(await touchPage.locator('[name="scan_interval"]').inputValue(), "91");
    assert.equal(await touchPage.locator("maika-voice-editor").locator("#phrase").inputValue(), "bản nháp giọng nói");
    await swipe(-150);
    assert.equal(await activeSpeaker(), second, "The last speaker does not wrap unexpectedly");
    await swipe(20);
    assert.equal(await activeSpeaker(), second, "A short movement is not a swipe");
    await swipe(150);
    assert.equal(await activeSpeaker(), initial);
    assert.equal(await touchPage.locator('[data-action="speaker-step"][data-direction="-1"]').isDisabled(), true);
    await touchPage.locator(".hero-showcase").focus();
    await touchPage.keyboard.press("ArrowRight");
    assert.equal(await activeSpeaker(), second);
    await touchPage.keyboard.press("ArrowLeft");
    assert.equal(await activeSpeaker(), initial);
    await touchPage.locator('[data-action="speaker-step"][data-direction="1"]').click();
    assert.equal(await activeSpeaker(), second);
    await touchPage.locator('[data-action="speaker-step"][data-direction="-1"]').click();
    assert.equal(await activeSpeaker(), initial);
    console.log("PASS real touch swipe, edge limits, small-movement rejection, arrow keys/buttons and key/settings/voice drafts");

    const scrollBefore = await touchPage.evaluate(() => panel.scrollTop);
    await swipe(2, -120);
    assert.equal(await activeSpeaker(), initial, "Vertical gestures do not switch speakers");
    assert(await touchPage.evaluate(() => panel.scrollTop) > scrollBefore + 20, "Native vertical scrolling remains available");
    await overview();
    await swipe(-150, 0, ".nav");
    assert(await touchPage.locator(".nav").evaluate((element) => element.scrollLeft) > 0, "Navigation chips scroll with touch");
    assert.equal(await activeSpeaker(), initial);
    await overview();
    await touchPage.evaluate(() => {
      const surface = panel.shadowRoot.querySelector(".hero-showcase");
      const send = (type, values = {}) => surface.dispatchEvent(new PointerEvent(type, {bubbles: true, pointerId: 77, pointerType: "touch", isPrimary: true, button: 0, clientX: 200, clientY: 360, ...values}));
      send("pointerdown"); send("pointermove", {clientX: 80}); send("pointercancel");
      send("pointerdown"); send("pointermove", {clientX: 80}); send("pointerdown", {pointerId: 78, isPrimary: false}); send("pointerup", {clientX: 80});
    });
    assert.equal(await activeSpeaker(), initial);
    assert(await touchPage.evaluate(() => panel._gesture === null && panel._gestureFrame === null && !panel.hasAttribute("data-swiping")));
    await touchPage.evaluate(() => { panel._busy = true; });
    await swipe(-150);
    assert.equal(await activeSpeaker(), initial);
    await touchPage.evaluate(() => { panel._busy = false; panel.shadowRoot.querySelector("maika-voice-editor")._saving = true; });
    await swipe(-150);
    assert.equal(await activeSpeaker(), initial);
    await touchPage.evaluate(() => { panel.shadowRoot.querySelector("maika-voice-editor")._saving = false; });
    assert.equal(await touchPage.evaluate(() => calls.filter((call) => call.service || call.method === "POST").length), 0);
    console.log("PASS native vertical/nav scrolling, pointer cancellation, multitouch, busy guards and no device actions from gestures");

    await touchPage.emulateMedia({reducedMotion: "reduce"});
    await swipe(-150);
    assert.equal(await activeSpeaker(), second);
    assert.equal(await touchPage.locator(".hero-media").evaluate((element) => getComputedStyle(element, "::before").animationName), "none");
    assert(await touchPage.evaluate(() => panel._deviceAnimation === null));
    await touchPage.emulateMedia({reducedMotion: "no-preference"});
    await touchPage.waitForTimeout(100);
    await touchPage.locator('[data-action="open-voice"]').click();
    await touchPage.waitForFunction(() => panel.shadowRoot.querySelector('[data-action="jump"][data-section="voice"]')?.getAttribute("aria-current") === "location");
    await touchPage.locator('[data-action="jump"][data-section="settings"]').click();
    await touchPage.waitForFunction(() => panel.shadowRoot.querySelector('[data-action="jump"][data-section="settings"]')?.getAttribute("aria-current") === "location");
    await touchPage.waitForFunction(() => panel.shadowRoot.querySelector(".hero")?.hasAttribute("data-motion-paused"));
    assert.equal(await touchPage.locator(".hero-media").evaluate((element) => getComputedStyle(element, "::before").animationPlayState), "paused");
    await overview();
    await touchPage.waitForFunction(() => getComputedStyle(panel.shadowRoot.querySelector(".hero-media"), "::before").animationPlayState === "running");
    assert.equal(await touchPage.locator(".hero-media").evaluate((element) => getComputedStyle(element, "::before").animationPlayState), "running");
    await touchPage.evaluate(() => {
      Object.defineProperty(document, "hidden", {configurable: true, value: true});
      document.dispatchEvent(new Event("visibilitychange"));
    });
    assert.equal(await touchPage.locator(".hero-media").evaluate((element) => getComputedStyle(element, "::before").animationPlayState), "paused");
    await touchPage.evaluate(() => {
      delete document.hidden;
      document.dispatchEvent(new Event("visibilitychange"));
      const root = panel.parentElement;
      panel.remove();
      if (panel._gestureFrame !== null || panel._gesture !== null) throw new Error("Gesture resources not cleaned up");
      root.append(panel); tick();
    });
    await touchPage.waitForTimeout(150);
    await swipe(150);
    assert.equal(await activeSpeaker(), initial);
    await touchPage.evaluate(() => {
      const entry = snapshot.entries[0];
      const serial = panel._activeSerial();
      entry.devices = {[serial]: entry.devices[serial]};
      entry.device_entities = {[serial]: entry.device_entities[serial]};
    });
    await touchPage.locator('[data-action="refreshdata"]').click();
    await touchPage.waitForTimeout(150);
    assert.equal(await touchPage.locator(".speaker-pager").count(), 0);
    assert.equal(await touchPage.locator("[data-swipe]").count(), 0);
    assert.equal(await touchPage.evaluate(() => calls.filter((call) => call.service || call.method === "POST").length), 0);
    console.log("PASS reduced motion, offscreen/background pause, reconnection cleanup and single-speaker layout");
  } finally {
    await touchContext.close();
  }
}

async function verifyLifetimeLicense() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  await page.locator('[data-action="jump"][data-section="settings"]').click();
  await openSetup("license");
  const license = page.locator('[data-sec="settings"] .panel-accordion--license');
  const labels = () => license.locator(".row .lbl").allTextContents();
  assert.equal(await page.evaluate(() => snapshot.entries[0].license.plan), "lifetime");
  assert.deepEqual(await labels(), ["Gói hiện tại", "Key đang dùng", "Mã cài đặt"]);
  assert.match(await license.locator(".panel-accordion__copy small").innerText(), /vĩnh viễn/);
  assert.equal(await license.locator(".reminder").count(), 0);
  const soon = await page.evaluate(() => {
    const licenseExpiresAt = Math.floor(Date.now() / 1000) + 3 * 86400;
    snapshot.entries[0].license = {...snapshot.entries[0].license, plan: "month_1", expires_at: licenseExpiresAt, license_expires_at: licenseExpiresAt};
    tick();
    return licenseExpiresAt;
  });
  assert.ok(soon);
  await page.locator('[data-action="refreshdata"]').click();
  await waitRender();
  await openSetup("license");
  assert.deepEqual(await labels(), ["Gói hiện tại", "Hạn dùng", "Key đang dùng", "Mã cài đặt"]);
  assert.match(await license.locator(".reminder").innerText(), /còn 3 ngày/);
  await page.evaluate(() => {
    const licenseExpiresAt = Math.floor(Date.now() / 1000) + 40 * 86400;
    snapshot.entries[0].license = {...snapshot.entries[0].license, license_expires_at: licenseExpiresAt, expires_at: licenseExpiresAt};
    tick();
  });
  await page.locator('[data-action="refreshdata"]').click();
  await waitRender();
  await openSetup("license");
  assert.equal(await license.locator(".reminder").count(), 0);
  console.log("PASS lifetime key hides the expiry row; paid plans show it with a near-expiry reminder");
}

async function verifyCommandHistory() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  await page.locator('[data-action="jump"][data-section="chat"]').click();
  await page.waitForFunction(() => document.querySelector("maika-panel").shadowRoot.querySelectorAll('[data-card="chat"] .history-row').length === 3);
  const rows = page.locator('[data-card="chat"] .history-row');
  assert.equal(await rows.first().locator(".history-text").innerText(), "tắt quạt");
  assert.equal(await rows.first().locator(".badge").innerText(), "Lỗi");
  assert.equal(await rows.nth(1).locator(".badge").innerText(), "Chưa có rule");
  assert.equal(await rows.last().locator(".history-text").innerText(), "bật đèn phòng khách");
  assert.equal(await rows.last().locator(".badge").innerText(), "Đã thực hiện");
  await page.evaluate(() => { delete states["sensor.loa_last_voice_command"]; tick(); });
  await page.waitForFunction(() => document.querySelector("maika-panel").shadowRoot.querySelector('[data-card="chat"] .history-text')?.textContent === "từ snapshot");
  assert.equal(await rows.count(), 1);
  assert.equal(await rows.first().locator(".badge").innerText(), "Đã thực hiện");
  console.log("PASS command history merged into the chat section with live sensor attributes and snapshot fallback");
}

async function verifyPlaylistPicker() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  await openSectionFold("media");
  const context = () => page.evaluate(() => ({
    media: panel._entity("media_player"),
    serial: panel._activeSerial(),
    items: window.browseItems.map((item) => ({id: item.media_content_id, title: item.title})),
  }));
  const {media, items} = await context();
  const [first, second] = items;
  const dialog = page.locator("dialog.playlist");
  const rows = dialog.locator(".pl-item");
  const playCalls = () => page.evaluate((entity) => calls.filter((call) => call.service === "play_media" && call.data.entity_id === entity), media);
  const open = async () => {
    await page.evaluate(() => { window.browseCalls.length = 0; });
    await page.locator(".media-now .media-title").click();
  };

  assert.equal(await page.locator(".media-now .media-title").count(), 1);
  assert.equal(await page.locator(".media-now .media-title").getAttribute("aria-haspopup"), "dialog");
  await open();
  await rows.first().waitFor();
  assert.equal(await rows.count(), 2);
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).type), "media_player/browse_media");
  assert.deepEqual(await page.evaluate(() => { const call = window.browseCalls.at(-1); return {ct: call.media_content_type, ci: call.media_content_id}; }), {ct: "maika_playlist", ci: "maika_playlist"});
  const currentRow = dialog.locator('.pl-item[aria-current="true"]');
  assert.equal(await currentRow.count(), 1);
  assert.equal(await currentRow.getAttribute("data-id"), second.id);
  assert.equal(await currentRow.locator(".pl-item__badge").innerText(), "Đang phát");
  assert.equal(await rows.first().locator(".pl-item__s").innerText(), "Ca sĩ A");
  console.log("PASS playlist browse maps native queue, marks the current song and keeps `maika_song` ids verbatim");

  await page.evaluate((entity) => { states[entity].attributes.maika_queue_item_id = window.browseItems[0].media_content_id; tick(); }, media);
  await page.waitForFunction(() => document.querySelector("maika-panel").shadowRoot.querySelector('.pl-item[data-id="' + window.browseItems[0].media_content_id + '"]')?.getAttribute("aria-current") === "true");
  assert.equal(await currentRow.getAttribute("data-id"), first.id);
  console.log("PASS playlist current-song highlight follows live media_player attributes");

  await rows.first().click();
  await page.waitForFunction(() => { const current = document.querySelector("maika-panel"); return !current.shadowRoot.querySelector("dialog.playlist")?.open && current._playlist === null; });
  const played = await playCalls();
  assert.equal(played.length, 1);
  assert.deepEqual(played[0].data, {entity_id: media, media_content_type: "maika_song", media_content_id: first.id});
  assert.equal(await page.evaluate(() => panel._playlistBusy), false);
  assert(await page.evaluate(() => panel.shadowRoot.activeElement === panel.shadowRoot.querySelector(".media-now .media-title")), "Focus returns to the title button");
  console.log("PASS choosing a song dispatches one media_player.play_media with the exact queue id and restores focus");

  await page.evaluate(() => { window.failBrowse = true; });
  await open();
  await dialog.locator(".pl-state--bad").waitFor();
  assert.match(await dialog.locator(".pl-state--bad").innerText(), /Không đọc được danh sách bài/);
  await page.evaluate(() => { window.failBrowse = false; });
  await dialog.locator('[data-action="playlist-retry"]').click();
  await rows.first().waitFor();
  assert.equal(await rows.count(), 2);
  console.log("PASS playlist browse failure shows a retry and recovers");

  await page.keyboard.press("Escape");
  await page.waitForFunction(() => { const current = document.querySelector("maika-panel"); return !current.shadowRoot.querySelector("dialog.playlist")?.open && current._playlist === null; });
  assert(await page.evaluate(() => panel._playlistBusy === false));
  console.log("PASS Escape closes the picker and clears its state");

  const playCountBefore = (await playCalls()).length;
  await open();
  await page.keyboard.press("Escape");
  await page.waitForTimeout(160);
  assert(await page.evaluate(() => panel._playlist === null), "A response arriving after close is discarded");
  assert.equal(await dialog.getAttribute("open"), null);
  assert.equal((await playCalls()).length, playCountBefore);
  console.log("PASS an in-flight browse that resolves after close is ignored");
}

async function verifyChat() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  await openSectionFold("chat");
  const card = () => page.locator('[data-card="chat"]');
  const rows = () => card().locator(".chat-row");
  assert.equal(await card().count(), 1);
  assert.equal(await card().locator(".chat-input").count(), 1);

  await page.evaluate(() => {
    window.snapshot.entries[0].chat = [
      {role: "user", text: "bật đèn", serial_number: panel._activeSerial(), at: "2026-10-12T10:00:00+00:00"},
      {role: "assistant", text: "Đã bật đèn phòng khách", serial_number: panel._activeSerial(), at: "2026-10-12T10:00:02+00:00"},
    ];
  });
  await page.evaluate(() => panel._load());
  await card().locator(".chat-row--assistant .chat-text").first().waitFor();
  assert.equal(await rows().count(), 2);
  assert.equal(await card().locator(".chat-row--user .chat-text").first().innerText(), "bật đèn");
  assert.equal(await card().locator(".chat-row--assistant .chat-text").first().innerText(), "Đã bật đèn phòng khách");
  console.log("PASS chat renders user and assistant turns for the active speaker");

  await page.evaluate(() => { window.calls.length = 0; });
  const input = card().locator(".chat-input");
  await input.fill("mở nhạc");
  await card().locator('.chat-form button[type="submit"]').click();
  await page.waitForFunction(() => (document.querySelector("maika-panel")._entry()?.chat || []).some((turn) => turn.text === "mở nhạc"));
  const sent = await page.evaluate(() => window.calls.find((call) => call.path === "maika/panel/chat"));
  assert.equal(sent.method, "POST");
  assert.equal(sent.data.entry_id, "account-0");
  assert.equal(sent.data.text, "mở nhạc");
  assert.equal(typeof sent.data.serial_number, "string");
  assert.equal(await input.inputValue(), "");
  assert.equal(await card().locator(".chat-row--user .chat-text").last().innerText(), "mở nhạc");
  await page.evaluate(() => { if (panel._chatTimer) { clearTimeout(panel._chatTimer); panel._chatTimer = null; } });
  console.log("PASS chat submit posts to the panel chat API and clears the input");
}

async function verifyReminders() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  await page.locator('[data-action="jump"][data-section="reminders"]').click();
  const card = page.locator('[data-sec="reminders"]');
  const input = (name) => card.locator(`[data-field="${name}"]`);
  await card.locator(".reminder-item").first().waitFor();
  assert.equal(await page.locator(".nav .pill").filter({hasText: "Nhắc hẹn"}).getAttribute("aria-current"), "location");
  assert.match(await page.evaluate(() => document.querySelector("maika-panel")._lastSignature), /"status":"ready"/);
  assert.equal(await card.locator(".reminder-item").count(), 1);
  assert.match(await input("reminder_start").inputValue(), /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  const listed = await page.evaluate(() => window.calls.find((call) => call.method === "GET" && call.path.startsWith("maika/panel/reminders")));
  const activeSerial = await page.evaluate(() => document.querySelector("maika-panel")._activeSerial());
  assert.ok(listed.path.includes(`serial_number=${activeSerial}`));
  console.log("PASS reminders load lazily for the selected speaker with a default future time");

  await page.evaluate(() => { window.calls.length = 0; });
  await input("reminder_event").fill("Họp nhóm");
  await input("reminder_start").fill("2030-01-03T09:30");
  await input("reminder_frequency").selectOption("weekly");
  await input("reminder_alert").selectOption("15");
  await input("reminder_tts").fill("Sắp đến giờ họp nhóm");
  await card.locator('form[data-form="reminders"] button[type="submit"]').click();
  await card.locator(".reminder-item").filter({hasText: "Họp nhóm"}).waitFor();
  const created = await page.evaluate(() => window.calls.find((call) => call.method === "POST" && call.path === "maika/panel/reminders"));
  assert.equal(created.data.action, "create");
  assert.equal(created.data.event, "Họp nhóm");
  assert.equal(created.data.frequency, "weekly");
  assert.equal(created.data.alert_prior, 15);
  assert.equal(created.data.custom_tts, "Sắp đến giờ họp nhóm");
  assert.equal(new Date(created.data.start_at).toISOString(), new Date("2030-01-03T09:30").toISOString());
  assert.equal(await card.locator(".reminder-item").count(), 2);
  assert.equal(await input("reminder_event").inputValue(), "");
  await page.locator(".msg").filter({hasText: "Đã tạo nhắc hẹn"}).waitFor();
  console.log("PASS creating a reminder posts the validated payload and updates the list");

  const row = card.locator(".reminder-item").filter({hasText: "Họp nhóm"});
  await page.evaluate(() => { window.calls.length = 0; });
  await row.locator('[data-action="reminders-edit"]').click();
  assert.equal(await input("reminder_event").inputValue(), "Họp nhóm");
  assert.equal(await input("reminder_frequency").inputValue(), "weekly");
  assert.equal(await input("reminder_alert").inputValue(), "15");
  assert.match(await card.locator(".reminder-editbar").innerText(), /Đang sửa: Họp nhóm/);
  await input("reminder_event").fill("Họp nhóm tuần");
  await input("reminder_alert").selectOption("30");
  await card.locator('form[data-form="reminders"] button[type="submit"]').click();
  await card.locator(".reminder-item").filter({hasText: "Họp nhóm tuần"}).waitFor();
  const updated = await page.evaluate(() => window.calls.find((call) => call.method === "POST" && call.path === "maika/panel/reminders"));
  assert.equal(updated.data.action, "update");
  assert.equal(updated.data.reminder_id, 2);
  assert.equal(updated.data.alert_prior, 30);
  assert.equal(await card.locator(".reminder-editbar").count(), 0);
  assert.equal(await input("reminder_event").inputValue(), "");
  await page.locator(".msg").filter({hasText: "Đã cập nhật nhắc hẹn"}).waitFor();
  console.log("PASS editing a reminder pre-fills the form and sends a partial update");

  await page.evaluate(() => { window.calls.length = 0; });
  await card.locator(".reminder-item").filter({hasText: "Họp nhóm tuần"}).locator('[data-action="reminders-toggle"]').click();
  await page.waitForFunction(() => [...document.querySelector("maika-panel").shadowRoot.querySelectorAll(".reminder-item")].some((item) => item.textContent.includes("Họp nhóm tuần") && item.textContent.includes("Đã tắt")));
  const toggled = await page.evaluate(() => window.calls.find((call) => call.method === "POST" && call.path === "maika/panel/reminders"));
  assert.equal(toggled.data.action, "toggle");
  assert.equal(toggled.data.reminder_id, 2);
  assert.equal(toggled.data.enabled, false);
  console.log("PASS toggling a reminder sends the requested enabled state");

  await page.evaluate(() => { window.calls.length = 0; });
  let checks = card.locator('.reminder-check input[type="checkbox"]');
  await checks.nth(1).check();
  await input("reminder_mute_date").fill("2030-01-04");
  await card.locator('[data-action="reminders-mute"]').click();
  await page.locator(".msg").filter({hasText: "Đã tạm tắt 1 nhắc hẹn"}).waitFor();
  const muted = await page.evaluate(() => window.calls.find((call) => call.method === "POST" && call.path === "maika/panel/reminders"));
  assert.equal(muted.data.action, "mute");
  assert.deepEqual(muted.data.reminder_ids, [2]);
  assert.deepEqual(muted.data.mute_days, ["2030-01-04"]);
  await card.locator('[data-action="reminders-select-clear"]').click();
  console.log("PASS muting selected reminders sends the chosen date");

  await page.evaluate(() => { window.calls.length = 0; });
  checks = card.locator('.reminder-check input[type="checkbox"]');
  await checks.nth(0).check();
  await checks.nth(1).check();
  assert.match(await card.locator(".reminder-editbar").filter({hasText: "đã chọn"}).innerText(), /2 nhắc hẹn đã chọn/);
  page.once("dialog", (dialog) => dialog.accept());
  await card.locator('[data-action="reminders-delete-selected"]').click();
  await page.waitForFunction(() => document.querySelector("maika-panel").shadowRoot.querySelectorAll(".reminder-item").length === 0);
  const deleted = await page.evaluate(() => window.calls.find((call) => call.method === "POST" && call.path === "maika/panel/reminders"));
  assert.equal(deleted.data.action, "delete");
  assert.deepEqual(deleted.data.reminder_ids, [1, 2]);
  console.log("PASS multi-select deletes the scoped reminder IDs and clears the list");
}

async function verifyContentStore() {
  await page.setViewportSize({width: 1440, height: 1000});
  await load();
  await openSectionFold("media");
  const media = await page.evaluate(() => panel._entity("media_player"));
  const opener = page.locator('[data-action="library"]');
  const dialog = page.locator("dialog.library");
  assert.equal(await opener.count(), 1);

  await page.evaluate(() => { window.browseCalls.length = 0; });
  await opener.click();
  await dialog.locator(".pl-item").first().waitFor();
  assert.equal(await dialog.locator(".pl-item").count(), 4);
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).media_content_id), "maika_cs_root");
  console.log("PASS content store opens at the MAIKA library root");

  await dialog.getByRole("button", {name: "Kênh"}).click();
  await dialog.getByRole("button", {name: "Kênh thiếu nhi"}).waitFor();
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).media_content_id), "maika_cs_channels");
  assert.equal(await dialog.locator(".pl-item").count(), 1);
  await dialog.getByRole("button", {name: "Kênh thiếu nhi"}).click();
  await dialog.getByRole("button", {name: "Album bé"}).waitFor();
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).media_content_id), "maika_cs_channel:7");
  await dialog.getByRole("button", {name: "Album bé"}).click();
  await dialog.getByRole("button", {name: "Bài thiếu nhi"}).waitFor();
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).media_content_id), "maika_cs_media:42");
  assert.equal(await dialog.locator(".pl-item__t").first().innerText(), "Bài thiếu nhi");
  console.log("PASS content store drills down channels, media folders and tracks");

  await dialog.locator('[data-action="library-up"]').click();
  await dialog.getByRole("button", {name: "Album bé"}).waitFor();
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).media_content_id), "maika_cs_channel:7");
  assert.equal(await dialog.locator(".pl-item__t").first().innerText(), "Album bé");
  console.log("PASS content store breadcrumb returns to the parent folder");

  await page.evaluate(() => { window.calls.length = 0; });
  await dialog.getByRole("button", {name: "Album bé"}).click();
  await dialog.getByRole("button", {name: "Bài thiếu nhi"}).waitFor();
  await dialog.getByRole("button", {name: "Bài thiếu nhi"}).click();
  await page.waitForFunction(() => { const current = document.querySelector("maika-panel"); return !current.shadowRoot.querySelector("dialog.library")?.open && current._cs === null; });
  const played = await page.evaluate((entity) => calls.filter((call) => call.service === "play_media" && call.data.entity_id === entity), media);
  assert.equal(played.length, 1);
  assert.deepEqual(played[0].data, {entity_id: media, media_content_type: "maika_cs_track", media_content_id: "https://cdn.example.test/be.mp3"});
  assert(await page.evaluate(() => panel.shadowRoot.activeElement === panel.shadowRoot.querySelector('[data-action="library"]')), "Focus returns to the library button");
  console.log("PASS content store track dispatches one media_player.play_media with the maika_cs_track id");

  await opener.click();
  await dialog.getByRole("button", {name: "Bài hát yêu thích"}).click();
  await dialog.getByRole("button", {name: "Yêu thích — Ca sĩ"}).waitFor();
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).media_content_id), "maika_favorite");
  await page.evaluate(() => { window.calls.length = 0; });
  await dialog.getByRole("button", {name: "Yêu thích — Ca sĩ"}).click();
  await page.waitForFunction(() => !document.querySelector("maika-panel").shadowRoot.querySelector("dialog.library")?.open);
  const favorite = await page.evaluate((entity) => calls.find((call) => call.service === "play_media" && call.data.entity_id === entity), media);
  assert.deepEqual(favorite.data, {entity_id: media, media_content_type: "maika_favorite_track", media_content_id: "https://cdn.example.test/yeu-thich.mp3"});
  console.log("PASS favorite track is playable instead of being treated as a folder");
}

async function verifyNhacCuaTui() {
  await load();
  await openSectionFold("media");
  const media = await page.evaluate(() => panel._entity("media_player"));
  const dialog = page.locator("dialog.library");
  await page.locator('[data-action="library"]').click();
  await dialog.getByRole("button", {name: "NhạcCủaTui"}).click();
  await dialog.getByRole("button", {name: "Bài hát mới"}).waitFor();
  assert.equal(await page.evaluate(() => window.browseCalls.at(-1).media_content_id), "maika_nct_root");
  await dialog.getByRole("button", {name: "Bài hát mới"}).click();
  await dialog.getByRole("button", {name: "Bài NCT — Ca sĩ NCT"}).click();
  await page.waitForFunction(() => { const current = document.querySelector("maika-panel"); return !current.shadowRoot.querySelector("dialog.library")?.open && current._cs === null; });
  const played = await page.evaluate((entity) => calls.filter((call) => call.service === "play_media" && call.data.entity_id === entity), media);
  assert.equal(played.length, 1);
  assert.deepEqual(played[0].data, {entity_id: media, media_content_type: "maika_nct_track", media_content_id: "Track0001"});
  console.log("PASS NhacCuaTui track dispatches media_player.play_media with maika_nct_track");
}

async function verifyNhacCuaTuiSearch() {
  await load();
  await openSectionFold("media");
  const media = await page.evaluate(() => panel._entity("media_player"));
  const dialog = page.locator("dialog.library");
  await page.locator('[data-action="library"]').click();
  const input = dialog.getByRole("searchbox", {name: "Tìm bài hát trên NhạcCủaTui"});
  await dialog.getByRole("button", {name: "NhạcCủaTui"}).waitFor();
  await input.fill("sơn tùng");
  await input.press("Enter");
  const result = dialog.getByRole("button", {name: "Tìm thấy — Sơn Tùng"});
  await result.waitFor();
  const searchCall = await page.evaluate(() => window.browseCalls.at(-1));
  assert.equal(searchCall.type, "media_player/search_media");
  assert.equal(searchCall.search_query, "sơn tùng");
  assert.equal(searchCall.entity_id, media);
  assert(await page.evaluate(() => panel.shadowRoot.activeElement === panel.shadowRoot.querySelector(".pl-item")), "Focus moves to first search result");
  await result.click();
  await page.waitForFunction(() => { const current = document.querySelector("maika-panel"); return !current.shadowRoot.querySelector("dialog.library")?.open && current._cs === null; });
  const played = await page.evaluate((entity) => calls.filter((call) => call.service === "play_media" && call.data.entity_id === entity), media);
  assert.equal(played.length, 1);
  assert.deepEqual(played[0].data, {entity_id: media, media_content_type: "maika_nct_track", media_content_id: "Track0009"});
  console.log("PASS NhacCuaTui search dispatches media_player/search_media and plays the selected track");
}

try {
  await verifyGlassAndMotion();
  await verifySectionFolds();
  await verifyDeviceAccordion();
  await verifySetupAccordion();
  await verifyDesktopScrolling();
  await verifySpeakerGestures();
  await verifyVoiceEditor();
  await verifyLifetimeLicense();
  await verifyCommandHistory();
  await verifyPlaylistPicker();
  await verifyChat();
  await verifyReminders();
  await verifyContentStore();
  await verifyNhacCuaTui();
  await verifyNhacCuaTuiSearch();
  for (const width of [320, 360, 390, 620, 768, 1024, 1280, 1440, 1920]) {
    await page.setViewportSize({width, height: width < 621 ? 844 : 1000});
    await load();
    for (const theme of ["light", "dark"]) {
      await page.locator('[data-action="theme"]').selectOption(theme);
      await page.waitForTimeout(350);
      const result = await page.evaluate(() => ({
        width: panel.clientWidth, scroll: panel.scrollWidth, theme: panel.dataset.theme,
        color: getComputedStyle(panel).backgroundColor,
        imageWidth: panel.shadowRoot.querySelector(".hero-media").clientWidth,
        imageHeight: panel.shadowRoot.querySelector(".hero-media").clientHeight,
        columns: getComputedStyle(panel.shadowRoot.querySelector(".stage")).gridTemplateColumns.split(" ").length,
        overflow: [...panel.shadowRoot.querySelectorAll(".card, .row, .panel-accordion, .panel-accordion__copy, input, select, textarea"), ...panel.shadowRoot.querySelector("maika-voice-editor").shadowRoot.querySelectorAll(".box, input, select, button")].filter((node) => {
          const rect = node.getBoundingClientRect();
          return rect.width && (rect.right > panel.getBoundingClientRect().right + 1 || rect.left < -1);
        }).map((node) => node.className || node.tagName),
      }));
      assert.equal(result.scroll, result.width, `Horizontal scroll ${width} ${theme}`);
      assert.equal(result.theme, theme);
      assert.deepEqual(result.overflow, [], `Overflow ${width}`);
      assert.equal(result.columns, width > 1100 ? 4 : width > 620 ? 2 : 1);
      assert(result.imageWidth <= 180 && result.imageHeight <= 200, `Compact speaker image ${width} ${theme}`);
      metrics.push({viewport: width, ...result});
      if ([390, 1440].includes(width)) {
        await page.waitForTimeout(1000);
        await page.screenshot({path: join(output, `${theme}-${width}.png`)});
        await page.locator('[data-action="jump"][data-section="voice"]').click();
        await page.waitForTimeout(600);
        assert.equal(await page.locator('[data-action="jump"][data-section="voice"]').getAttribute("aria-current"), "location");
        await page.screenshot({path: join(output, `voice-${theme}-${width}.png`)});
        await page.locator('[data-action="jump"][data-section="overview"]').click();
      }
    }
  }
  console.log("PASS 18 width/theme combinations (320–1920px), no horizontal overflow");
  await page.setViewportSize({width: 1300, height: 900});
  await page.evaluate(() => { document.querySelector("#sidebar").style.display = "block"; });
  assert.equal(await page.evaluate(() => getComputedStyle(panel.shadowRoot.querySelector(".stage")).gridTemplateColumns.split(" ").length), 2);
  console.log("PASS responsive layout follows actual panel width with HA sidebar");

  await page.locator('[data-action="theme"]').selectOption("auto");
  await page.evaluate(() => { hass.themes.darkMode = false; tick(); });
  await waitRender();
  assert.equal(await page.locator("maika-panel").getAttribute("data-theme"), "light");
  await page.locator('[data-action="theme"]').selectOption("dark");
  await page.waitForTimeout(450);
  assert.equal(await page.evaluate(() => getComputedStyle(panel).backgroundColor), "rgb(23, 17, 15)");
  await load();
  assert.equal(await page.locator("maika-panel").getAttribute("data-theme"), "dark");
  console.log("PASS automatic HA theme, manual override, persistence after reload");

  await page.locator('[data-action="theme"]').selectOption("light");
  await openSectionFold("media");
  await page.locator(".cast-drawer summary").click();
  const cast = page.locator('[name="cast_url"]');
  await cast.fill("https://example.test/nhac.mp3");
  const before = await page.evaluate(() => {
    window.oldImage = panel.shadowRoot.querySelector(".hero-media img");
    window.oldCast = panel.shadowRoot.querySelector('[name="cast_url"]');
    const media = panel._entity("media_player");
    states[media].attributes = {...states[media].attributes, volume_level: .75, media_title: "Bài tiếp theo", is_volume_muted: true};
    tick();
    return true;
  });
  await waitRender();
  assert(before);
  assert.equal(await cast.inputValue(), "https://example.test/nhac.mp3");
  assert(await page.evaluate(() => panel.shadowRoot.activeElement === oldCast && panel.shadowRoot.querySelector(".hero-media img") === oldImage));
  assert.equal(await page.locator('[data-field="volume"]').inputValue(), "75");
  assert.equal(await page.locator(".media-now .t").innerText(), "Bài tiếp theo");
  assert.equal(await page.locator('[data-action="mute"]').getAttribute("aria-pressed"), "true");
  console.log("PASS live attributes update without replacing focused input or hero image");

  await page.locator('[data-action="theme"]').selectOption("dark");
  assert.equal(await cast.inputValue(), "https://example.test/nhac.mp3");
  await page.locator('[data-form="cast"] button[type="submit"]').click();
  assert(await page.evaluate(() => calls.some((call) => call.service === "play_media" && call.data.media_content_id === "https://example.test/nhac.mp3")));
  await page.locator('[data-action="device"][data-serial="SERIAL-0-0"]').click();
  assert.equal(await page.locator(".hero-copy h1").innerText(), "Loa phòng ngủ");
  assert.equal(await cast.inputValue(), "");
  await page.locator('[data-action="playpause"]').click();
  assert(await page.evaluate(() => calls.some((call) => call.service === "media_play_pause" && call.data.entity_id === snapshot.entries[0].device_entities["SERIAL-0-0"].media_player[0])));
  console.log("PASS cast service payload and correct device despite unrelated entity names");

  const seek = page.locator('[data-field="seek"]');
  assert.equal(await seek.count(), 1);
  await seek.fill("120");
  assert(await page.evaluate(() => calls.some((call) => call.service === "media_seek" && Math.round(call.data.seek_position) === 120 && call.data.entity_id === snapshot.entries[0].device_entities["SERIAL-0-0"].media_player[0])));
  console.log("PASS seek slider dispatches media_seek for the active speaker");

  const seekBack = page.locator('[data-action="seek-step"][data-delta="-30"]');
  const seekFwd = page.locator('[data-action="seek-step"][data-delta="30"]');
  assert.equal(await seekBack.count(), 1);
  assert.equal(await seekFwd.count(), 1);
  const lastSeek = () => page.evaluate(() => { const target = snapshot.entries[0].device_entities["SERIAL-0-0"].media_player[0]; return calls.filter((call) => call.service === "media_seek" && call.data.entity_id === target).at(-1)?.data.seek_position; });
  await seekFwd.click();
  const forwardSeek = await lastSeek();
  assert(Number.isFinite(forwardSeek) && forwardSeek >= 72 && forwardSeek <= 215, String(forwardSeek));
  await seekBack.click();
  const backSeek = await lastSeek();
  assert(Number.isFinite(backSeek) && backSeek >= 0 && backSeek < forwardSeek, `${backSeek} < ${forwardSeek}`);
  console.log("PASS seek step buttons clamp and dispatch media_seek offsets");

  const expectedSeek = await page.evaluate(() => {
    window.originalSeekClock = Date.now;
    Date.now = () => window.originalSeekClock() + 45000;
    const attrs = states[panel._entity("media_player")].attributes;
    return Math.min(panel._playbackPosition(attrs, true) + 30, attrs.media_duration);
  });
  try {
    await seekFwd.click();
    assert(Math.abs(await lastSeek() - expectedSeek) < 2, "Seek uses elapsed time at click, not the old rendered position");
  } finally {
    await page.evaluate(() => { Date.now = window.originalSeekClock; delete window.originalSeekClock; });
  }
  await page.evaluate(() => {
    const state = states[panel._entity("media_player")];
    state.state = "paused";
    state.attributes.media_position = 10;
    state.attributes.media_position_updated_at = new Date(Date.now() - 600000).toISOString();
    tick();
  });
  await waitRender();
  await seekFwd.click();
  assert.equal(await lastSeek(), 40, "Paused time is not added to seek position");
  await seekBack.click();
  assert.equal(await lastSeek(), 0, "Backward seek clamps at zero");
  console.log("PASS seek uses the click-time position and ignores paused time");

  const stopButton = page.locator('[data-action="stop"]');
  assert.equal(await stopButton.count(), 1);
  assert.equal(await stopButton.getAttribute("aria-label"), "Dừng phát");
  await stopButton.click();
  assert(await page.evaluate(() => calls.some((call) => call.service === "media_stop" && call.data.entity_id === snapshot.entries[0].device_entities["SERIAL-0-0"].media_player[0])));
  console.log("PASS stop button dispatches media_stop for the active speaker");

  await page.evaluate(() => {
    states[panel._entity("media_player")].attributes.supported_features &= ~4096;
    tick();
  });
  await waitRender();
  assert(await stopButton.isDisabled(), "Old integrations without STOP cannot send unsupported commands");
  await page.evaluate(() => {
    const state = states[panel._entity("media_player")];
    state.attributes.supported_features |= 4096;
    state.state = "unavailable";
    tick();
  });
  await waitRender();
  assert(await stopButton.isDisabled(), "Offline transport is disabled");
  await page.evaluate(() => { states[panel._entity("media_player")].state = "playing"; tick(); });
  await waitRender();
  assert(await stopButton.isEnabled());
  console.log("PASS stop respects firmware feature flags and speaker availability");

  await page.evaluate(() => { states[panel._entity("media_player")].state = "paused"; tick(); });
  await waitRender();
  await page.evaluate(() => {
    const attrs = states[panel._entity("media_player")].attributes;
    attrs.media_position = 88;
    attrs.media_duration = 300;
    attrs.media_position_updated_at = new Date().toISOString();
    tick();
  });
  await waitRender();
  assert.equal(await seek.inputValue(), "88");
  assert.equal(await seek.getAttribute("max"), "300");
  console.log("PASS live position/duration changes refresh the timeline without a title or state change");

  await page.locator('[data-action="jump"][data-section="settings"]').click();
  await page.waitForTimeout(600);
  const positions = await page.evaluate(() => ({toolbar: panel.shadowRoot.querySelector(".toolbar").getBoundingClientRect().bottom, target: panel.shadowRoot.querySelector('[data-sec="settings"]').getBoundingClientRect().top}));
  assert(positions.target >= positions.toolbar, JSON.stringify(positions));
  const beforeOptions = await page.evaluate(() => ({...snapshot.entries[0].options}));
  await openSetup("config");
  await page.locator('[name="scan_interval"]').fill("90");
  await page.locator('[name="cloud_cast_base_url"]').fill("http://192.168.1.42:8123");
  await page.locator('[data-form="options"] button[type="submit"]').click();
  await waitRender();
  const savedOptions = await page.evaluate(() => calls.filter((call) => call.path === "maika/panel/options").at(-1).data.options);
  assert.deepEqual(Object.keys(savedOptions).sort(), ["cloud_cast_base_url", "enable_experimental_cloud_cast", "scan_interval"]);
  assert.equal(savedOptions.cloud_cast_base_url, "http://192.168.1.42:8123");
  assert.equal(await page.evaluate(() => snapshot.entries[0].options.cloud_cast_base_url), "http://192.168.1.42:8123");
  assert.equal(await page.evaluate(() => snapshot.entries[0].options.voice_command_rules), beforeOptions.voice_command_rules);
  assert.equal(await page.locator('[name="license_server_url"]').count(), 0);
  assert.equal(await page.locator('[name="rules"]').count(), 0);
  console.log("PASS section navigation, hidden activation URL, partial settings preserve voice rules/audio");

  await page.evaluate(() => { failApi = true; });
  await page.locator('[data-action="refreshdata"]').click();
  await waitRender();
  assert.match(await page.locator('[data-card="message"]').innerText(), /Không tải được/);
  assert(await page.locator('[data-sec="overview"]').isVisible());
  await page.evaluate(() => { failApi = false; });
  await page.locator('[data-action="refreshdata"]').click();
  await waitRender();
  assert(await page.locator('[data-card="message"]').isHidden());
  console.log("PASS refresh failure keeps previous data and allows retry");

  await page.emulateMedia({reducedMotion: "reduce"});
  assert.equal(await page.evaluate(() => getComputedStyle(panel.shadowRoot.querySelector(".card")).animationName), "none");
  assert.equal(await page.evaluate(() => getComputedStyle(panel.shadowRoot.querySelector(".dot"), "::after").animationName), "none");
  await page.evaluate(() => {
    const root = panel.parentElement;
    panel.remove();
    if (panel._renderFrame !== null) throw new Error("Frame not cleaned up");
    root.append(panel);
    tick();
  });
  await waitRender();
  console.log("PASS reduced motion and disconnect/reconnect lifecycle");
  await page.setViewportSize({width: 390, height: 844});
  await load();
  await page.locator('[data-action="jump"][data-section="device"]').click();
  await page.locator('[data-sec="device"] .panel-accordion--identity summary').click();
  const textId = await page.evaluate(() => panel._entity("text", "speaker_name"));
  const nameInput = page.locator(`input[data-entity="${textId}"]`);
  await nameInput.fill("Tên loa đang viết");
  await nameInput.evaluate((element) => element.setSelectionRange(4, 7));
  await page.evaluate(() => { states[panel._entity("sensor", "volume")].state = "63"; tick(); });
  await waitRender();
  assert.equal(await nameInput.inputValue(), "Tên loa đang viết");
  assert.deepEqual(await nameInput.evaluate((element) => [element.selectionStart, element.selectionEnd]), [4, 7]);
  await page.locator('[data-action="jump"][data-section="settings"]').click();
  await openSetup("license");
  await page.locator('[name="license_key"]').fill("MAIKA-TEST-TEST-TEST-TEST");
  await page.locator('[data-form="license"] button[type="submit"]').click();
  await waitRender();
  assert.deepEqual(await page.evaluate(() => calls.find((call) => call.path === "maika/panel/license").data), {entry_id: "account-0", license_key: "MAIKA-TEST-TEST-TEST-TEST"});
  assert.equal(await page.locator('[name="license_key"]').inputValue(), "");
  console.log("PASS text caret, selection and license replacement API");

  await page.evaluate(() => {
    for (const entry of snapshot.entries) {
      entry.title = "Tài khoản có tên rất dài ".repeat(8);
      for (const device of Object.values(entry.devices)) device.name = "Loa có tên rất dài ".repeat(10);
      entry.license.key_hint = "MAIKA-" + "x".repeat(150);
    }
    states[panel._entity("media_player")].attributes.media_title = "Bài hát không có khoảng cách".replaceAll(" ", "").repeat(30);
    tick();
  });
  await waitRender();
  assert.equal(await page.evaluate(() => panel.scrollWidth - panel.clientWidth), 0);
  await page.setViewportSize({width: 844, height: 390});
  assert.equal(await page.locator(".toolbar").evaluate((element) => getComputedStyle(element).position), "relative");
  console.log("PASS long content, landscape phone layout");

  const blockedContext = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
  await blockedContext.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {get() { throw new Error("Storage blocked"); }});
  });
  await blockedContext.route("**/olli-maika-2.jpg", (route) => route.abort());
  const blockedPage = await blockedContext.newPage();
  blockedPage.on("pageerror", (error) => errors.push(String(error)));
  await blockedPage.goto(base);
  await blockedPage.locator('[data-sec="overview"]').waitFor();
  await blockedPage.locator('[data-action="theme"]').selectOption("light");
  assert.equal(await blockedPage.locator("maika-panel").getAttribute("data-theme"), "light");
  assert.equal(await blockedPage.locator('[data-action="effects"]').count(), 0);
  await blockedPage.evaluate(() => { const root = panel.parentElement; panel.remove(); root.append(panel); tick(); });
  await blockedPage.locator('[data-action="theme"]').selectOption("light");
  assert.equal(await blockedPage.locator("maika-panel").getAttribute("data-theme"), "light");
  await blockedPage.waitForTimeout(300);
  assert(await blockedPage.locator(".hero-media img").evaluate((element) => element.hidden));
  const unlabeled = await blockedPage.evaluate(() => [...panel.shadowRoot.querySelectorAll("input, select, textarea")].filter((element) => !element.getAttribute("aria-label") && !element.labels?.length).map((element) => element.outerHTML));
  assert.deepEqual(unlabeled, []);
  console.log("PASS touch browser, blocked storage, failed image fallback and form labels");

  await blockedPage.evaluate(async () => {
    const root = panel.parentElement;
    panel.remove();
    window.failedPanel = document.createElement("maika-panel");
    root.append(failedPanel);
    failedPanel.hass = {...hass, callApi: async () => { throw new Error("Offline at startup"); }};
  });
  await blockedPage.locator('[data-card="message"]').waitFor();
  assert.match(await blockedPage.locator('[data-card="message"]').innerText(), /Offline at startup/);
  await blockedPage.evaluate(() => { failedPanel.hass = hass; });
  await blockedPage.locator('[data-action="refreshdata"]').click();
  await blockedPage.locator('[data-sec="overview"]').waitFor();
  console.log("PASS first-load failure, visible error and working retry");
  await blockedContext.close();
  await page.setViewportSize({width: 390, height: 844});
  await load();
  const recoveryOptions = await page.evaluate(() => {
    const entry = snapshot.entries[0];
    snapshot.entries = [entry];
    entry.devices = {};
    entry.entities = {};
    entry.device_entities = {};
    entry.entity_keys = {};
    entry.license = {status: "unavailable", key_hint: "", activation_code: ""};
    window.states = {};
    hass.states = states;
    tick();
    return structuredClone(entry.options);
  });
  await page.locator('[data-action="refreshdata"]').click();
  await waitRender();
  await page.locator('[data-action="jump"][data-section="settings"]').click();
  await openSetup("license");
  const recoveryKey = page.locator('[name="license_key"]');
  assert.ok(await recoveryKey.isVisible());
  await recoveryKey.fill("MAIKA-RECOVERY-TEST-ONLY");
  await page.locator('[data-form="license"] button[type="submit"]').click();
  await page.waitForFunction(() => document.querySelector("maika-panel").shadowRoot.querySelector('[name="license_key"]').value === "");
  assert.deepEqual(await page.evaluate(() => calls.findLast((call) => call.path === "maika/panel/license").data), {entry_id: "account-0", license_key: "MAIKA-RECOVERY-TEST-ONLY"});
  assert.deepEqual(await page.evaluate(() => snapshot.entries[0].options), recoveryOptions);
  assert.equal(await page.evaluate(() => calls.filter((call) => call.service).length), 0);
  assert.equal(await page.evaluate(() => panel.scrollWidth - panel.clientWidth), 0);
  await page.screenshot({path: join(output, "license-recovery-mobile.png"), fullPage: true});
  console.log("PASS license replacement without loaded speaker runtime or entities");
  assert.deepEqual(errors, []);
  await writeFile(join(output, "metrics.json"), JSON.stringify(metrics, null, 2));
} finally {
  await browser.close();
  server.close();
}
