# Panel quản lý loa MAIKA

Từ bản `1.9.0`, tích hợp MAIKA tự đăng ký một mục **MAIKA** trong sidebar Home
Assistant. Từ `1.9.1`, panel dùng giao diện dashboard dạng sections; từ `1.9.2`,
panel hỗ trợ nhiều loa trong cùng tài khoản. Layout: lưới 4 cột
trên máy tính, tự co về 2 cột trên tablet và 1 cột trên điện thoại.

## Bố cục

1. **Ảnh loa + trạng thái**: ảnh loa MAIKA, tên loa, chấm online, chip Trực
   tuyến / Wi-Fi / Micro / Âm lượng.
2. **Điều khiển MAIKA**: media player đang phát gì, nút trước – phát/dừng – sau,
   mute, thanh âm lượng, form cast URL MP3/AAC qua cloud.
3. **Trạng thái loa**: 6 tile — trực tuyến, Wi-Fi, âm lượng, đang phát, cuộc gọi,
   yêu thích.
4. **Trợ lý Maika**: chọn giọng đọc, độ nhạy đánh thức, phản hồi khi gọi, công
   tắc tắt microphone.
5. **Tên & vị trí**: sửa trực tiếp tên loa, tên khi gọi, địa chỉ (lưu bằng
   `text.set_value`).
6. **Thông tin thiết bị**: model, phòng, ngôn ngữ, Wi-Fi SSID, serial, ngày kích
   hoạt, trạng thái.
7. **Firmware & hệ thống**: phiên bản firmware, trạng thái cập nhật, nhà sản xuất.
8. **Bảo hành**: còn/hết bảo hành và ngày hết hạn — chỉ hiện khi loa có dữ liệu.
9. **Bản quyền**: trạng thái, gói, hạn dùng, key dạng rút gọn, mã cài đặt, form
   nhập key mới và liên kết mua/gia hạn.
10. **Cấu hình**: chu kỳ cập nhật, cast âm thanh cloud, sensor câu lệnh, nguồn
    âm báo thành công, thời điểm phát, URL MP3 tuỳ chỉnh, media player phát âm
    báo, rule câu lệnh, nút lưu và nút tải lại integration.
11. **Công cụ**: làm mới trạng thái và khởi động lại loa (có xác nhận).

Nếu có nhiều config entry, các chip chọn **tài khoản** xuất hiện ở đầu panel.
Nếu một tài khoản có nhiều loa, thêm hàng chip chọn **loa** ngay bên dưới: chạm
để đổi loa và mọi mục trong panel (media, trạng thái, trợ lý, tên/vị trí, thông
tin thiết bị, firmware, bảo hành, công cụ) chỉ hiển thị entity của loa đó.
Mục **Bản quyền** và **Cấu hình** là của cả tài khoản/Home Assistant nên dùng
chung cho mọi loa.

## Thao tác

- **Kích hoạt / thay key**: dán key mới vào ô *License key* rồi bấm
  **Kích hoạt / thay key**. Hệ thống tự thay máy sang key mới, không cần admin
  xoá máy và không cần xoá key cũ.
- **Lưu cấu hình**: chỉnh các trường rồi bấm **Lưu cấu hình**; tích hợp tự tải
  lại để áp dụng. Các trường đang gõ không bị mất khi dữ liệu loa cập nhật.
- **Tải lại integration**: bấm nút trong mục Cấu hình nếu cần nạp lại thủ công.

## Bảo mật

- Các API của panel đều yêu cầu phiên đăng nhập Home Assistant.
- Key đầy đủ không bao giờ được gửi tới trình duyệt; panel chỉ nhận `key_hint`
  (dạng rút gọn) từ lease đã ký.
- Mọi lỗi khi đăng ký panel đều được bắt và ghi log, không làm hỏng tích hợp.
