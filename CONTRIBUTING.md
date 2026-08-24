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
python3 scripts/build_release.py --tag v1.2.0
```

Không commit `dist/`, `__pycache__`, `.pyc`, diagnostic hoặc Home Assistant backup.

## Báo lỗi

Dùng bug report form và cung cấp:

- Home Assistant version.
- Integration version.
- Model/firmware loa nếu an toàn để chia sẻ.
- Bước tái hiện.
- Log đã redact.

Vấn đề bảo mật phải theo `SECURITY.md`, không mở issue công khai.
