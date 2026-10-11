# Panel quản lý loa MAIKA

Từ bản `1.9.0`, tích hợp MAIKA tự đăng ký một mục **MAIKA** trong sidebar Home
Assistant. Từ `1.9.1`, panel dùng giao diện dashboard dạng sections; từ `1.9.2`,
panel hỗ trợ nhiều loa trong cùng tài khoản; từ `1.9.3`, panel ghép thực thể theo
`unique_id` nên tên loa đặt kiểu nào (`wifi_relay`, `amply_ke_sach`,…) cũng không
đọc nhầm thực thể. Bản `1.9.4` dùng lưới 4 cột khi panel rộng hơn 1100px,
2 cột từ 621–1100px và 1 cột khi rộng tối đa 620px. Bố cục tính theo vùng
panel còn lại, không chỉ theo màn hình, nên vẫn phù hợp khi mở sidebar HA.
Từ `1.10.0`, mục **Giọng nói** có trình tạo câu lệnh trực quan và panel không
hiện ô URL máy chủ kích hoạt.

## Giao diện sáng / tối và điều hướng

- Chọn **Tự động / Sáng / Tối** trên thanh công cụ. **Tự động** theo chế độ
  sáng/tối của Home Assistant; lựa chọn được nhớ riêng trong trình duyệt.
  Nếu trình duyệt chặn lưu trữ, vẫn đổi được cho phiên đang mở.
- Chạm **Tổng quan / Giọng nói / Trạng thái / Trợ lý / Tên & vị trí / Thiết bị / Bản quyền /
  Cấu hình / Công cụ** để tới đúng mục. Vuốt ngang thanh mục trên điện thoại.
- Nút menu ở góc trên mở sidebar HA khi màn hình hẹp. Thanh công cụ bám trên
  đầu khi cuộn; trên màn hình thấp (điện thoại ngang) thanh này cuộn cùng nội dung.
- Animation nhẹ cho thẻ, trạng thái phát nhạc và nút; tự tắt theo cài đặt
  **Giảm chuyển động** của thiết bị và tạm dừng khi tab không hiển thị.
- Các nút/ô nhập có nhãn hỗ trợ trình đọc màn hình, focus bàn phím rõ và vùng
  chạm lớn. Không cần cài Mushroom hoặc card-mod.

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
10. **Cấu hình**: chu kỳ cập nhật, cast âm thanh cloud, nút lưu và nút tải lại
    integration. Lưu tại đây không ghi đè cấu hình giọng nói.
11. **Công cụ**: làm mới trạng thái và khởi động lại loa (có xác nhận).
12. **Giọng nói**, nằm ngay sau điều khiển MAIKA: trình tạo câu lệnh ba bước,
    danh sách tìm kiếm/sửa/thêm cách nói/xóa/chạy thử, cài đặt âm phản hồi.

Nếu có nhiều config entry, các chip chọn **tài khoản** xuất hiện ở đầu panel.
Nếu một tài khoản có nhiều loa, thêm hàng chip chọn **loa** ngay bên dưới: chạm
để đổi loa và mọi mục trong panel (media, trạng thái, trợ lý, tên/vị trí, thông
tin thiết bị, firmware, bảo hành, công cụ) chỉ hiển thị entity của loa đó.
Mục **Bản quyền**, **Giọng nói** và **Cấu hình** là của tài khoản/Home Assistant nên dùng
chung cho mọi loa.

## Thao tác

- **Kích hoạt / thay key**: dán key mới vào ô *License key* rồi bấm
  **Kích hoạt / thay key**. Hệ thống tự thay máy sang key mới, không cần admin
  xoá máy và không cần xoá key cũ. Không cần nhập URL: dùng máy chủ đã lưu,
  hoặc máy chủ mặc định nếu chưa từng kích hoạt.
- **Lưu cấu hình**: chỉnh các trường rồi bấm **Lưu cấu hình**; tích hợp tự tải
  lại để áp dụng. Các trường đang gõ không bị mất khi dữ liệu loa cập nhật.
- **Giọng nói**: chọn loại mục (thiết bị/automation/script/scene), tìm theo tên,
  chọn thao tác và thông số, nhập câu muốn nói rồi lưu. Không cần gõ mã rule.
  Nút **Lưu & bật điều khiển** cho biết tính năng sẽ được bật cùng lúc lưu lệnh.
- **Chạy thử**: chỉ thực hiện sau khi bạn xác nhận; không kiểm thử khả năng
  nhận dạng giọng nói hay phát MP3. Lưu câu lệnh không tự điều khiển thiết bị.
- **Âm phản hồi**: chọn MP3 có sẵn/URL riêng/tắt, thời điểm và loa MAIKA trong
  cùng tài khoản. Bật cast cloud ở Cấu hình; nếu nhiều loa cần chọn một loa
  phát, không tự suy ra loa nhận câu nói. Ưu tiên che giọng chỉ là best-effort.
- **Đổi loa**: cấu hình và key chưa lưu vẫn giữ khi chuyển loa cùng tài khoản;
  ô cast và tên/vị trí tách theo loa. Có xác nhận trước khi đổi tài khoản nếu
  đang có bản nháp giọng nói; không đổi tài khoản khi đang lưu/chạy thử.
- **Xung đột cấu hình**: nếu câu lệnh hoặc âm phản hồi đã bị sửa ở tab khác,
  máy chủ từ chối ghi đè. Bản nháp còn nguyên để bạn xem lại; nút **Tải lại
  cấu hình đã lưu** yêu cầu xác nhận bỏ bản nháp trước khi nạp dữ liệu mới.
- **Tải lại integration**: bấm nút trong mục Cấu hình nếu cần nạp lại thủ công.
- **Mất mạng**: thông báo lỗi hiển thị trên đầu panel; bấm nút làm mới để thử
  lại. Dữ liệu đã tải trước đó vẫn hiện để tham khảo.

## Cập nhật từ bản cũ

Cập nhật custom integration lên `1.10.0`, khởi động lại Home Assistant rồi tải
lại trang/mở lại ứng dụng. Không xoá integration, thiết bị hoặc license key.
Đây là nâng cấp panel Home Assistant; portal Vercel và hệ thống thanh toán
không thay đổi. Đã kiểm tra bằng trình duyệt Chromium với HA giả lập ở các
kích thước 320–1920px; cần kiểm tra thêm trên loa và ứng dụng HA thực tế.
Các câu lệnh đã lưu tự hiện trong mục Giọng nói. Những dòng chưa sửa (kể cả
comment và thông số nâng cao) được giữ lại; không cần tạo lại lệnh.

## Bảo mật

- Các API của panel đều yêu cầu phiên đăng nhập Home Assistant.
- Key đầy đủ không bao giờ được gửi tới trình duyệt; panel chỉ nhận `key_hint`
  (dạng rút gọn) từ lease đã ký.
- Mọi lỗi khi đăng ký panel đều được bắt và ghi log, không làm hỏng tích hợp.
