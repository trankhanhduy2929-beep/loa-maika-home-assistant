# Contributing

Cảm ơn bạn muốn đóng góp cho MAIKA Speaker.

## Nguyên tắc

- Không đăng credential, access/refresh token, SIP credential, serial, địa chỉ hoặc SSID thật.
- Không thử `Reset` trên loa đang sử dụng.
- Command mới phải có bằng chứng từ APK/API và được thử bằng thao tác không phá hủy trước.
- Giữ thay đổi nhỏ, tập trung và tương thích với style hiện có.
- Cập nhật tài liệu/changelog khi thay đổi hành vi hoặc entity.

## Kiểm tra trước pull request

```bash
python3 -m pip install ruff==0.16.3
ruff check .
ruff format --check .
python3 scripts/validate_repository.py
python3 scripts/build_release.py
```

Không commit `dist/`, `__pycache__`, `.pyc`, diagnostic hoặc Home Assistant backup.

## Kiểm thử panel bằng trình duyệt

`scripts/test_panel_browser.mjs` chạy với Home Assistant giả lập, không đăng
nhập cloud MAIKA, không gửi lệnh tới thiết bị thật và không cần payment key.
Cần Node.js, Python 3.13+ và Playwright Core/Chromium có sẵn trên máy:

```bash
node --check custom_components/maika/frontend/maika-panel.js
node --check custom_components/maika/frontend/maika-voice-editor.js
MAIKA_PLAYWRIGHT_MODULE=file:///duong-dan/node_modules/playwright-core/index.mjs \
MAIKA_BROWSER_EXECUTABLE=/duong-dan/chromium \
node scripts/test_panel_browser.mjs
```

Nếu đã cài `playwright-core` trong môi trường Node có thể bỏ biến module;
nếu dùng Chromium do Playwright cài thì có thể bỏ biến executable. Ảnh chụp
và báo cáo giả lập nằm tại `/tmp/maika-panel-browser` (đổi bằng
`MAIKA_TEST_OUTPUT`). Bộ kiểm tra bao gồm CRUD câu lệnh, giữ thông số cũ,
automation, xung đột/lỗi lưu, payload kích hoạt không URL, điều khiển loa,
dark/light và 18 tổ hợp kích thước/chủ đề từ 320–1920px. Câu lệnh tạo ra được
đưa qua parser Python thật để kiểm tra tương thích.

## Báo lỗi

Dùng bug report form và cung cấp:

- Home Assistant version.
- Integration version.
- Model/firmware loa nếu an toàn để chia sẻ.
- Bước tái hiện.
- Log đã redact.

Vấn đề bảo mật phải theo `SECURITY.md`, không mở issue công khai.
