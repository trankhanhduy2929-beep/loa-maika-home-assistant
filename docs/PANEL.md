# Panel quản lý loa MAIKA

Từ bản `1.9.0`, tích hợp MAIKA tự đăng ký một mục **MAIKA** trong sidebar Home
Assistant. Đây là nơi quản lý loa, bản quyền và cấu hình thay cho việc mở phần
**Cấu hình** của tích hợp.

## Panel hiển thị gì

- **Loa**: tên, model, hãng, serial, firmware, wifi, địa chỉ, trạng thái online,
  âm lượng, mic và bài đang phát. Nếu có nhiều loa, chọn loa bằng các chip ở đầu
  thẻ.
- **Cảm biến**: toàn bộ sensor mà tích hợp tạo (âm lượng, firmware, trạng thái
  phát, cảm biến khẩu lệnh…).
- **Điều khiển**: media player (phát/dừng, chuyển bài, âm lượng, tắt tiếng, cast
  URL), các `select` (kiểu phản hồi wakeword, độ nhạy, giọng TTS), `switch`,
  `text` và các nút như khởi động lại loa / làm mới trạng thái.
- **Bản quyền**: trạng thái, gói, hạn sử dụng, key dạng rút gọn, mã cài đặt và
  liên kết mua/gia hạn.
- **Cấu hình**: chu kỳ cập nhật, cast âm thanh cloud, cảm biến khẩu lệnh, nguồn
  âm báo thành công, kiểu phát âm báo, loa phát âm báo và khẩu lệnh điều khiển
  thiết bị HASS.

## Thao tác

- **Kích hoạt key**: dán key mới vào ô *Nhập key mới* rồi bấm **Kích hoạt key**.
  Không cần xoá máy hay xoá key cũ; loa dùng gói mới ngay.
- **Lưu cấu hình**: chỉnh các trường rồi bấm **Lưu cấu hình**; tích hợp tự tải
  lại để áp dụng.
- **Tải lại tích hợp**: bấm nút trong mục Cấu hình nếu cần nạp lại thủ công.

## Bảo mật

- Các API của panel đều yêu cầu phiên đăng nhập Home Assistant.
- Key đầy đủ không bao giờ được gửi tới trình duyệt; panel chỉ nhận `key_hint`
  (dạng rút gọn) từ lease đã ký.
- Mọi lỗi khi đăng ký panel đều được bắt và ghi log, không làm hỏng tích hợp.
