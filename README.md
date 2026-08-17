# MAIKA Speaker cho Home Assistant

Custom integration không chính thức để kết nối loa MAIKA với Home Assistant
qua MAIKA cloud.

## Tính năng

- Tạo media player và các entity sensor, switch, button, select, text của loa.
- Điều khiển âm lượng, play/pause, bài kế/trước và micro.
- Phát URL âm thanh MPEG qua cloud cast.
- Nhận câu lệnh giọng nói từ loa và chạy rule bật/tắt/toggle entity Home Assistant.
- Hỗ trợ đăng nhập bằng số điện thoại Việt Nam hoặc email/Gmail có mật khẩu MAIKA.
- Kích hoạt license theo Home Assistant installation ID.

## Cài qua HACS

1. Vào **HACS → Integrations → Custom repositories**.
2. Thêm repository:
   `https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant`
3. Chọn loại **Integration**, sau đó tải **MAIKA Speaker**.
4. Khởi động lại Home Assistant.
5. Vào **Settings → Devices & services → Add integration** và tìm
   **MAIKA Speaker**.

## Cài thủ công

Tải `maika-manual.zip` trong GitHub Release, giải nén vào thư mục `/config` để
có đường dẫn:

```text
/config/custom_components/maika/manifest.json
```

Sau đó khởi động lại Home Assistant và thêm integration.

## Đăng nhập

- Số nội địa như `084...` được tự chuyển thành `+8484...`.
- Có thể nhập trực tiếp số dạng `+84...`, `84...` hoặc `0084...`.
- Email/Gmail phải có mật khẩu tài khoản MAIKA.
- Tài khoản chỉ dùng nút **Đăng nhập bằng Google** nhưng chưa đặt mật khẩu MAIKA
  chưa được hỗ trợ vì đây là luồng Google OAuth riêng.

## Cấu hình giọng nói

Sau khi thêm integration, mở **Configure** để bật sensor câu lệnh giọng nói,
cloud cast và khai báo rule theo dạng:

```text
bật đèn phòng khách | switch.turn_on | switch.den_phong_khach
tắt đèn phòng khách | switch.turn_off | switch.den_phong_khach
đổi trạng thái đèn | homeassistant.toggle | switch.den_phong_khach
```

## Release

Khi push tag trùng với version trong
`custom_components/maika/manifest.json`, GitHub Actions tự tạo:

- `maika.zip`: cài qua HACS.
- `maika-manual.zip`: cài thủ công.
- `SHA256SUMS.txt`: checksum SHA-256.

## Bảo mật

- Không đưa `maika-license-secrets`, private key, admin token, `.dev.vars`,
  database hoặc credential khách hàng lên repository này.
- Credential MAIKA được Home Assistant lưu trong config entry và chỉ gửi tới
  MAIKA cloud, không gửi tới activation server.

## Hỗ trợ

Báo lỗi tại GitHub Issues của repository. Khi gửi log, hãy xóa số điện thoại,
email, token, license key, URL riêng và thông tin thiết bị.

## License

MIT License. Xem file `LICENSE`.
