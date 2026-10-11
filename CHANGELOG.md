# Changelog

Các thay đổi đáng chú ý của dự án được ghi tại đây.

## [1.12.0] - 2026-10-11

### Added

- Phong cách Liquid Glass tông cam: thẻ kính mờ, viền phản sáng, nút cam
  chuyển sắc, nền sáng kem/tối nâu than. Ô nhập giữ nền rõ để dễ đọc.
- Vòng sóng quanh loa, ảnh loa chuyển động nhẹ, dải sóng và vệt sáng trên
  thanh phát nhạc khi trạng thái HA đang phát và không tắt tiếng. Dừng
  hiệu ứng phát nhạc khi tạm dừng, tắt tiếng, mất kết nối hoặc chưa rõ
  trạng thái. Sóng chỉ mang tính minh hoạ, không thu/phân tích âm thanh.
- Nút **Hoạt ảnh** cạnh thanh chọn mục để bật/tắt chuyển động, nhớ theo
  trình duyệt và đồng bộ lựa chọn giữa các tab, không lưu lên HA/server.

### Accessibility

- Tôn trọng **Giảm chuyển động** của hệ thống, kể cả khi đã bật hoạt ảnh;
  dừng animation khi ra khỏi vùng nhìn hoặc chuyển tab, gồm cả thông báo
  bên trong trình tạo câu lệnh. Không thêm vòng lặp animation JavaScript.
- Nền đặc khi giảm trong suốt/tăng tương phản; fallback nền đặc nếu trình
  duyệt không hỗ trợ kính mờ. Giảm mức blur trên thiết bị cảm ứng.
- Giữ độ tương phản chữ/nút và chữ trên mục được chọn cả khi rê chuột.

### Preserved

- Giữ sửa lỗi cuộn chuột v1.11.1, vuốt đổi loa, cuộn lồng nhau, sáng/tối,
  bản nháp key/câu lệnh và mọi cấu hình. Không đổi API hay dữ liệu license.

### Tests

- Kiểm tra trực tiếp chuyển trạng thái, hoạt ảnh chuyển động theo thời
  gian, bật/tắt/lưu lựa chọn, giảm chuyển động/trong suốt và tương phản;
  chạy lại bộ trình duyệt ở 320–1920px, con lăn và cử chỉ cảm ứng với HA
  giả lập. Chưa kiểm thử trên loa và máy Home Assistant thực tế.

## [1.11.1] - 2026-10-11

### Fixed

- Sửa panel không cuộn được bằng con lăn chuột khi khung custom panel của
  Home Assistant không có chiều cao cố định. Giới hạn chiều cao panel theo
  viewport để nội dung cuộn bên trong, thay vì kéo dài khỏi màn hình.
- Giữ cuộn tự nhiên trên ảnh loa, thanh chọn mục/loa và các thẻ; không chặn
  wheel bằng JavaScript, không ảnh hưởng cuộn ngang trackpad, danh sách câu
  lệnh, vuốt chạm đổi loa hay điều hướng tới từng mục.
- Không thay đổi key, tài khoản, câu lệnh và cấu hình đã lưu.

### Tests

- Mô phỏng lớp khung `partial-panel-resolver` / `ha-panel-custom` không đặt
  chiều cao như khi nhúng trong HA; kiểm thử con lăn thật qua Chromium ở
  đầu/cuối trang, khi đổi kích thước và mở sidebar, cùng cuộn lồng nhau.
- Kiểm tra lại thao tác vuốt trên điện thoại, sáng/tối, bản nháp và đổi key
  trên HA giả lập; chưa kiểm thử trên thiết bị Home Assistant/loa thực tế.

## [1.11.0] - 2026-10-11

### Added

- Vuốt ngang trên thẻ loa để chuyển loa trong cùng tài khoản; có nút trước/sau,
  số thứ tự và hỗ trợ phím trái/phải. Không chuyển vòng bất ngờ ở hai đầu.
- Hiệu ứng kéo nhẹ, chuyển loa, phản hồi khi nhấn và viền sáng chuyển động;
  thanh chọn mục/loa cuộn ngang có điểm dừng. Vuốt dọc vẫn cuộn trang bình thường.
- Nút **Tạo câu lệnh** ngay trên thẻ loa để mở nhanh mục Giọng nói.

### Changed

- Giao diện xanh ngọc, nền tối xanh than / nền sáng trắng bạc hà, điểm nhấn tím
  nhẹ; thẻ và nút đồng bộ giữa panel và trình tạo câu lệnh.
- Thu gọn ảnh loa sang bên cạnh tên/trạng thái, bỏ khung ảnh lớn chiếm màn hình.
- Phần phát URL MP3/AAC thu gọn trong **Phát âm thanh từ đường dẫn**; chạm để mở.
  Ô nhập và trạng thái mở vẫn giữ khi loa cập nhật.
- Dừng hoạt cảnh khi ra ngoài vùng nhìn hoặc tab bị ẩn; tôn trọng chế độ
  giảm chuyển động của thiết bị, không chạy vòng lặp JavaScript khi đứng yên.

### Safety

- Vuốt chỉ đổi loa đang xem, không gọi service, không đổi tài khoản và không
  lưu cấu hình. Giữ bản nháp key, cấu hình chung và giọng nói trong cùng tài khoản.
- Bỏ qua vuốt ngắn, cuộn dọc, cử chỉ nhiều ngón hoặc bị hủy; không đổi loa
  khi đang thực hiện thao tác/lưu câu lệnh. Một loa thì ẩn bộ chuyển loa.
- Không đổi license, entity, câu lệnh, âm báo, API kích hoạt hoặc thanh toán.

## [1.10.1] - 2026-10-11

### Changed

- Bỏ nút **Configure / Tùy chọn MAIKA** bên trang tích hợp Home Assistant.
  Nhập/thay key trong **MAIKA → Bản quyền**; chỉnh chu kỳ cập nhật, cast,
  câu lệnh và âm phản hồi tại **Cấu hình loa** / **Giọng nói**.
- Giữ nguyên key, tài khoản, thiết bị, rule và mọi tuỳ chọn đã lưu. Luồng cài
  mới, kích hoạt lần đầu và đăng nhập lại tài khoản MAIKA không thay đổi.
- Hướng dẫn và thông báo lỗi dẫn tới panel thay vì màn hình tuỳ chọn cũ.

### Fixed

- Đăng ký panel trước khi kiểm tra license/kết nối cloud, để vẫn thay key
  được khi license hết hạn ngay lúc Home Assistant khởi động.
- Không gỡ panel khi tải lại tích hợp; chỉ gỡ khi xoá tài khoản MAIKA cuối
  cùng. Kiểm tra license vẫn bắt buộc trước khi loa được kết nối.

## [1.10.0] - 2026-10-11

### Added

- Mục **Giọng nói** riêng, nổi bật ngay dưới điều khiển loa: tạo câu lệnh bằng
  cách chọn thiết bị → chọn thao tác → nhập câu nói, không cần viết rule/JSON.
- Tìm theo tên trong Home Assistant, lọc loại thiết bị và chọn riêng automation,
  script, scene. Chọn trực quan độ sáng, tốc độ quạt, vị trí rèm, nhiệt độ,
  âm lượng và các thông số được hỗ trợ.
- Danh sách câu lệnh có tìm kiếm, sửa, thêm cách nói, xóa và chạy thử có xác
  nhận. Lưu/chọn thiết bị không tự thực hiện thao tác.
- Automation có lựa chọn kiểm tra hoặc bỏ qua điều kiện. Lệnh mới mặc định
  kiểm tra điều kiện; lệnh cũ giữ nguyên hành vi.
- Cài đặt giọng nói và âm phản hồi nằm trong cùng mục, có chọn loa MAIKA theo
  tên, MP3 có sẵn hoặc URL riêng và chế độ ưu tiên che giọng mặc định.

### Changed

- Bỏ ô URL máy chủ kích hoạt khỏi panel: chỉ nhập key. Máy chủ đang lưu hoặc
  máy chủ mặc định vẫn được dùng tự động; không đổi key, gói hay mã máy.
- Cấu hình chung chỉ còn chu kỳ cập nhật và cast cloud; lưu tại đây không ghi
  đè câu lệnh hoặc âm phản hồi.

### Fixed

- Giữ nguyên câu lệnh cũ, comment và thông số chưa sửa; không phải tạo lại.
- Giữ bản nháp khi cập nhật trạng thái/chuyển loa cùng tài khoản, cảnh báo khi
  đổi tài khoản và phát hiện cấu hình bị sửa từ tab khác để tránh ghi đè.
- Từ chối câu nói trùng, thông số sai và thao tác ngoài danh sách an toàn.
  Chọn loa phát phản hồi chỉ liệt kê loa MAIKA thuộc tài khoản đang mở.

Kiểm tra bằng Python và Chromium với Home Assistant giả lập; chưa kiểm thử
nhận dạng giọng nói/cast trên loa thật trong lần phát hành này. Portal Vercel,
thanh toán và các license hiện có không thay đổi.

## [1.9.4] - 2026-10-11

### Changed

- Panel MAIKA tự chia 1 / 2 / 4 cột theo chiều rộng thực tế của panel, kể cả
  khi mở sidebar Home Assistant, dùng tablet, điện thoại ngang hoặc màn hình nhỏ.
- Chọn **Tự động / Sáng / Tối** ngay trên thanh công cụ. Tự động theo Home
  Assistant; chế độ chọn tay có bảng màu riêng và được nhớ trên trình duyệt.
- Thanh chuyển nhanh đến từng mục, nút mở menu HA trên điện thoại, vùng bấm
  lớn hơn, hỗ trợ bàn phím và nhãn cho các nút điều khiển/ô nhập.
- Ảnh loa không bị cắt; nhóm thông tin rõ hơn, phần cấu hình nâng cao có thể
  thu gọn. Ô URL MP3 chỉ hiện khi chọn âm báo tuỳ chỉnh.
- Hiệu ứng xuất hiện, trạng thái đang phát và phản hồi nút nhẹ hơn; giảm chuyển
  động theo thiết lập thiết bị và dừng animation khi tab bị ẩn.

### Fixed

- Không dựng lại toàn bộ dashboard mỗi lần trạng thái loa thay đổi: giữ vị trí
  cuộn, ô đang nhập, con trỏ, nội dung cast, key và rule chưa lưu.
- Cập nhật tên bài, âm lượng và mute khi chỉ thuộc tính media player thay đổi.
- Giữ cấu hình/key chưa lưu khi chuyển giữa các loa cùng tài khoản.
- Lỗi tải dữ liệu có thông báo và nút thử lại, không còn chỉ hiện màn hình chờ.
- Đổi màu vẫn dùng được khi trình duyệt chặn lưu trữ; ảnh lỗi có hình thay thế.

License, gói, hạn dùng, API kích hoạt và ghép entity theo `unique_id` giữ nguyên.

## [1.9.3] - 2026-10-11

### Fixed

- Panel ghép thực thể theo `unique_id` (key dịch của integration) thay vì khớp chuỗi
  trong `entity_id`. Trước đây tên loa đặt trùng keyword (vd `wifi_relay`,
  `a_volume`) làm chip Wi-Fi, âm lượng, trạng thái đọc nhầm thực thể khác.
- Snapshot panel bổ sung `entity_keys` (entity_id -> key thực thể) cho mọi entry.

### Changed

- Cách khớp vẫn tương thích ngược: nếu snapshot không có `entity_keys`, panel quay
  về khớp theo tên thực thể như cũ.

## [1.9.2] - 2026-10-11

### Added

- Panel tự nhận diện **nhiều loa trong cùng một tài khoản MAIKA**: thêm hàng chip
  chọn loa, mọi mục (ảnh, media, trạng thái, trợ lý, tên/vị trí, thông tin thiết
  bị, firmware, bảo hành, công cụ) chỉ hiển thị entity của loa đang chọn.
- Snapshot panel có thêm `device_entities` (entity theo serial từng loa) để giao
  diện scoped theo thiết bị thay vì gộp toàn bộ entry.

### Fixed

- Thêm tài khoản MAIKA thứ hai dùng chung license key trên cùng Home Assistant
  không còn bị cắt hạn dùng thử: khi máy chủ xoay refresh token cho entry khác,
  entry đang chạy tự nạp lại lease vừa xoay thay vì báo lỗi rồi reload.
- Chip và tile Wi-Fi luôn báo "Mất Wi-Fi" dù loa đang kết nối, do panel tìm
  chuỗi `wifi` trong khi entity_id thật là `..._wi_fi_connected`. Cách khớp tên
  giờ bỏ dấu gạch dưới nên vẫn khớp các entity có tên viết tắt.

### Changed

- Nhãn mục Cấu hình ghi rõ cấu hình áp dụng cho mọi loa cùng tài khoản.

## [1.9.1] - 2026-10-10

### Changed

- Làm lại giao diện panel theo phong cách dashboard sections (4 cột, tự co giãn
  trên điện thoại): ảnh loa lớn, chip trạng thái, thẻ điều khiển media, lưới
  tile trạng thái, thẻ trợ lý, tên/vị trí, thông tin thiết bị, firmware, bảo
  hành, bản quyền, cấu hình và công cụ.
- Thêm ảnh loa MAIKA thật, hiệu ứng chuyển động nhẹ, màu nhấn xanh ngọc/tím và
  theme sáng/tối theo Home Assistant.
- Ô nhập trong panel giữ nguyên nội dung đang gõ khi dữ liệu loa cập nhật.
- Sửa tên trường khớp entity thực tế (Wi-Fi SSID, ngày kích hoạt, ngày hết hạn
  bảo hành) và ẩn thẻ Bảo hành khi loa không có dữ liệu.

## [1.9.0] - 2026-10-10

### Added

- Thêm panel quản lý loa MAIKA riêng trong sidebar Home Assistant: hiển thị thông
  tin loa (tên, model, hãng, serial, firmware, wifi, trạng thái, bài đang phát)
  cùng toàn bộ cảm biến, nút, công tắc và lựa chọn của tích hợp.
- Panel hiển thị bản quyền đang dùng: key (dạng rút gọn), gói, hạn sử dụng, mã
  cài đặt và liên kết mua/gia hạn.
- Cho phép nhập/đổi key và chỉnh cấu hình tích hợp ngay trong panel: chu kỳ cập
  nhật, cast âm thanh cloud, cảm biến khẩu lệnh, nguồn/kiểu phát âm báo thành
  công, loa phát âm báo, khẩu lệnh điều khiển thiết bị HASS.
- Thêm API nội bộ `/api/maika/panel` cho panel (yêu cầu đăng nhập Home Assistant).

### Changed

- Lease ký gửi kèm `key_hint` để panel hiển thị key đang dùng mà không lộ key đầy
  đủ.
- Panel được đăng ký tự động khi tích hợp khởi động và gỡ khi gỡ cấu hình cuối;
  mọi lỗi đăng ký panel đều được bắt để không ảnh hưởng tích hợp.

## [1.8.1] - 2026-08-26

### Fixed

- Sửa lỗi tài khoản MAIKA đăng nhập thành công nhưng integration báo không tìm
  thấy loa khi REST `/v1/user-device` của cloud trả HTTP 5xx hoặc response sai
  cấu trúc.
- Thêm fallback tìm loa mặc định qua `/connect` và
  `ClientInformation/GetDeviceInfo`; chuẩn hóa cả field camelCase/snake_case,
  tự đánh dấu online khi loa đã phản hồi và giữ cache cho các lần poll sau.
- Bước thêm tài khoản chỉ xác thực đăng nhập, không còn thất bại vì API danh
  sách loa tạm lỗi trước khi listener cloud được khởi động.
- Hủy sạch waiter discovery khi unload để không còn task chờ treo.

### Changed

- Gửi thêm `organization_code=MAIKA` theo request chính thức của ứng dụng và
  giữ nguyên license, activation server, PayOS, key cùng thiết bị HASS hiện có.

## [1.8.0] - 2026-08-25

### Added

- Mở rộng voice rule từ bật/tắt/toggle sang đèn có độ sáng/màu, quạt, rèm,
  điều hòa, media player, scene, script, automation, button, robot hút bụi,
  máy tạo ẩm, bình nước nóng, camera, valve, máy cắt cỏ và các helper phổ biến.
- Thêm cột JSON tùy chọn: `câu lệnh | entity_id | action | {"field":value}`;
  toàn bộ rule ba cột cũ vẫn hoạt động.
- Sensor câu lệnh hiển thị service data đã lọc để kiểm tra lệnh có tham số.

### Security

- Chỉ cho phép domain, action và field nằm trong allowlist cố định; kiểm tra kiểu,
  khoảng giá trị, số rule, kích thước dòng và kích thước JSON trước khi lưu.
- Chặn JSON ghi đè entity/target, credential, token, context, variables, object
  lồng nhau và service hệ thống/raw command.
- Không expose mở khóa hoặc alarm control panel; coordinator luôn ép target từ
  entity ID trong rule sau khi ghép service data.

### Changed

- Giữ nguyên chế độ âm MP3 ưu tiên của `1.7.2`, license signing key, activation
  server, PayOS và dữ liệu/key khách hàng hiện có.

## [1.7.2] - 2026-08-25

### Added

- Thêm chế độ **Ưu tiên: che giọng mặc định** cho âm phản hồi rule HASS.
- Thêm lựa chọn **Sau khi HASS thành công** để giữ hành vi cũ.

### Fixed

- Gửi clip custom sớm hơn khi rule hợp lệ để giảm câu “không thể điều khiển”
  phát trước.
- Tái sử dụng `dialogRequestId`, `messageId` và `serverMessageId` của hội thoại
  khi gửi `AudioPlayer/Play`, giúp cloud/loa ưu tiên thay nội dung đang phát.
- Không thay đổi license key, activation server, PayOS hoặc dữ liệu người dùng.

### Limitations

- APK MAIKA 3.2.3 không có command hủy TTS/conversation riêng; chế độ ưu tiên
  chỉ che/cắt phản hồi mặc định theo best-effort.

## [1.7.1] - 2026-08-24

### Changed

- Rút gọn màn hình kích hoạt thành mã máy, link chọn gói/xem key và ô nhập key.
- Rút gọn portal thành ba bước: chọn gói, quét QR PayOS và sao chép key.
- Viết lại phần cài đặt HACS cho người dùng và thêm ZIP có tên kèm version.

### Fixed

- Khi máy bị từ chối, hướng dẫn người dùng nhờ admin xóa máy rồi nhập lại cùng key.
- Giữ nguyên activation server nhúng sẵn, public signing key và mọi key hiện có.

## [1.7.0] - 2026-08-23

### Added

- Thêm lựa chọn nguồn âm báo sau khi rule Home Assistant chạy thành công:
  tắt, dùng file MAIKA MP3 có sẵn trên portal Vercel hoặc dùng URL MP3 tùy chỉnh.
- Giữ tương thích với cấu hình cũ chỉ có `voice_success_audio_url`; người dùng
  đang dùng URL MP3 riêng không bị thay đổi hành vi sau khi nâng cấp.
- Hiển thị URL portal license trong bước kích hoạt, phần quản lý license và
  thông báo license chưa hợp lệ để người dùng mua, dùng thử hoặc xem lại key.
- Cho phép script phát hành nhúng đồng thời URL Worker và URL portal; URL portal
  cũng tạo đường dẫn cố định `/mp3/maika.mp3` cho âm báo bundled.

### Changed

- Nâng phiên bản integration lên `1.7.0`; không rotate/revoke license key,
  installation hoặc dữ liệu khách hàng hiện có.

## [1.6.3] - 2026-08-17

### Fixed

- Đồng bộ lại Ed25519 public key nhúng trong integration với cặp khóa production
  đang được Worker dùng để ký lease.
- Sửa lỗi mọi license key đều báo `invalid_license_response` sau khi Worker đã
  dùng cặp khóa mới nhưng source GitHub vẫn giữ public key cũ.
- Không thay đổi dữ liệu khách hàng, license key, installation hoặc web Vercel;
  người dùng chỉ cần cập nhật custom integration lên bản này.

## [1.6.2] - 2026-08-17

### Fixed

- Thêm đăng nhập bằng email/Gmail và mật khẩu tài khoản MAIKA qua endpoint
  `/v1/auth/login` đúng như APK; form tự nhận biết email khi giá trị có dấu `@`.
- Giữ nguyên đăng nhập số điện thoại qua `/v1/auth/otp/login`, không làm thay đổi
  config entry hoặc quy trình reauthentication hiện có.
- Chấp nhận số điện thoại Việt Nam ở dạng nội địa `084...` và tự chuyển sang
  dạng MAIKA cloud yêu cầu là `+8484...` khi đăng nhập.
- Chuẩn hóa thêm các dạng phổ biến như `84...`, `0084...` và số có khoảng
  trắng, dấu chấm, dấu gạch ngang hoặc dấu ngoặc.
- Tự chuyển số điện thoại trong config entry cũ sang dạng quốc tế khi nâng cấp,
  nên người dùng không cần xóa rồi thêm lại integration.

## [1.6.1] - 2026-08-17

### Fixed

- Ghi `license_config.py` bằng UTF-8 với xuống dòng LF cố định trên Windows để
  `ruff format --check .` không còn báo file cần format sau Easy Mode.
- Validator chặn Python source dùng CRLF trước khi tạo source ZIP hoặc release.
- Trình cấu hình repository chuẩn hóa file đã chỉnh sửa về LF.

## [1.6.0] - 2026-08-17

### Added

- Thêm kích hoạt theo hash của Home Assistant instance ID, không phụ thuộc MAC address.
- Thêm config flow nhập activation server/license key, trạng thái chờ người bán duyệt và mã cài đặt rút gọn.
- Thêm Ed25519 signed lease, refresh định kỳ 12 giờ, lease 48 giờ và offline grace bảy ngày.
- Thêm options riêng để kích hoạt entry cũ, thay license hoặc kiểm tra lại yêu cầu pending.
- Thêm private storage `maika.license` cho refresh token và lease; dữ liệu này không nằm trong config entry hoặc diagnostics.
- Bổ sung server mẫu Cloudflare Worker + D1 riêng trong thư mục bàn giao private, kèm admin CLI tạo khách hàng, license, duyệt, từ chối và thu hồi installation.

### Security

- Activation server không nhận credential/token MAIKA, MAC, raw Home Assistant instance ID, serial loa, entity hoặc câu nói.
- License key và refresh token chỉ được lưu dạng HMAC hash trên server; private signing key, pepper và admin token không nằm trong GitHub public.
- Redact license key, lease token, refresh token, license ID, installation hash và activation code khỏi diagnostics.
- Entry ngừng tải khi license bị thu hồi, hết hạn hoặc offline grace kết thúc.

### Changed

- Nâng config entry flow lên version `2`; entry cũ phải kích hoạt trong Configure trước khi tải lại.
- Giữ MIT/HACS cho client public; activation service chỉ ngăn chia sẻ thông thường và không tuyên bố chống sửa mã tuyệt đối.

## [1.5.1] - 2026-08-16

### Performance

- Sau khi service HASS hoàn tất thành công, coordinator gửi `CommandHandOver/AudioPlayer/Play` trực tiếp qua MAIKA client thay vì gọi vòng qua service `media_player.play_media` của Home Assistant.
- Bỏ bước refresh playback đồng bộ khỏi đường phản hồi tự động; state được cập nhật optimistic và stream cloud tiếp tục đồng bộ trạng thái thật.
- Dùng chung bộ kiểm tra URL giữa config flow, media player và phản hồi rule để đường cast trực tiếp vẫn giữ nguyên safeguard.

### Safety

- Vẫn chờ service HASS với `blocking=true`; action lỗi hoặc câu không khớp tuyệt đối không gửi cast.
- Không thêm `Pause`, không phát suy đoán trước kết quả và không thay đổi luồng thiết bị native MAIKA.

## [1.5.0] - 2026-08-16

### Added

- Thêm URL MP3 phản hồi thành công: chỉ cần nhập một địa chỉ HTTP(S), integration sẽ gọi `media_player.play_media` với payload `media` và MIME `audio/mpeg` sau khi rule HASS hoàn tất thành công.
- Tự chọn và ẩn trường loa đích khi config entry chỉ có một media player MAIKA; khi có nhiều loa, cho phép chọn đúng loa phát âm báo.
- Sensor câu lệnh hiển thị `success_audio_status` (`pending`, `played`, `failed`) và `success_audio_error` an toàn.

### Changed

- Để trống URL là tắt hoàn toàn âm báo; không còn công tắc enable riêng, entity TTS hay nội dung câu TTS.
- Gọi service entity HASS với `blocking=true`, sau đó mới phát MP3. Câu không khớp, entity unavailable và service thất bại không gửi `Pause`, `Play` hoặc command audio nào tới MAIKA.
- Redact URL MP3 khỏi diagnostics và không ghi URL vào log lỗi.

### Removed

- Gỡ phản hồi TTS tự động, cache prewarm và dependency `tts`; khả năng gọi `tts.speak` thủ công qua media player MAIKA vẫn giữ nguyên.
- Gỡ bridge thử nghiệm MAIKA → Home Assistant Assist, toàn bộ tùy chọn prefix/language/agent, event liên quan và dependency `conversation`.

## [1.4.0] - 2026-08-16

### Added

- Thêm TTS xác nhận chọn lọc cho rule giọng nói: chỉ gọi `tts.speak` sau khi service Home Assistant khớp rule và hoàn tất thành công.
- Cho phép chọn entity `tts.*`, đúng media player MAIKA trong config entry và câu xác nhận tùy chỉnh; câu mặc định là `Đã điều khiển thiết bị thành công`.
- Làm nóng cache TTS best-effort sau khi integration load để giảm độ trễ lần phát đầu.
- Sensor câu lệnh hiển thị `success_tts_status` (`pending`, `played`, `failed`) và `success_tts_error` an toàn.

### Safety

- Không gửi `Pause` hoặc lệnh audio nào cho câu không khớp rule, entity không tồn tại/unavailable, service không hỗ trợ hoặc service Home Assistant ném lỗi.
- Lệnh điều khiển thiết bị native của MAIKA tiếp tục theo luồng gốc nếu không khớp rule HASS; chỉ rule HASS đã chạy thành công mới cast clip xác nhận để thay thế phản hồi MAIKA theo best-effort.
- Xác minh loa TTS đích thuộc đúng config entry MAIKA, đang available và cloud cast đã bật trước khi gọi TTS.
- Redact câu xác nhận tùy chỉnh khỏi diagnostics và không log nội dung TTS, URL media hoặc raw cloud payload.

## [1.3.2] - 2026-08-16

### Fixed

- Gửi `Conversation/StartListening` cho từng loa khi sensor giọng nói hoặc Assist bridge được bật, đúng bước đăng ký mà APK MAIKA thực hiện trước khi nhận hội thoại của loa.
- Tự đăng ký lại sau mỗi lần `/connect` reconnect và gửi `StopListening` best-effort khi unload integration.
- Nhận thêm frame nằm trong các wrapper `directive`, `event`, `message`, `response` hoặc `data`, bên cạnh envelope phẳng hiện có.
- Xóa trạng thái kết nối ngay cả khi stream kết thúc bình thường thay vì chỉ khi có exception.

### Added

- Sensor câu lệnh hiển thị bộ đếm frame/directive, loại frame cuối, header type/name/namespace, thời điểm frame cuối và trạng thái đăng ký nghe của từng thế hệ kết nối.
- Telemetry không lưu raw payload, token, credential hoặc serial loa.

## [1.3.1] - 2026-08-16

### Fixed

- Không còn báo `executed` giả khi entity ID không tồn tại, domain viết sai hoặc entity không hỗ trợ action đã chọn.
- Gọi trực tiếp service của domain entity, ví dụ `switch.turn_on`, sau khi xác minh entity tồn tại, available và service được đăng ký.
- Sensor hiển thị thêm service thực tế, state trước/sau và mã lỗi `entity_not_found`, `entity_unavailable` hoặc `service_not_supported`.
- Sensor luôn hiển thị trạng thái kết nối stream và số rule đã nạp để phân biệt lỗi cloud stream với lỗi cấu hình rule.

## [1.3.0] - 2026-08-16

### Added

- Thêm sensor cấp tài khoản chứa câu lệnh giọng nói mới nhất nhận từ frame `speakerConversationResponse.rawSpeech`.
- Thêm rule khớp toàn câu theo cú pháp `câu lệnh | entity_id | turn_on/turn_off/toggle` để điều khiển entity Home Assistant trực tiếp.
- Chuẩn hóa câu lệnh không phân biệt hoa/thường, dấu tiếng Việt, khoảng trắng và dấu câu.
- Hiển thị thời điểm, rule khớp, entity đích, action và kết quả chạy trong thuộc tính sensor.

### Security

- Sensor/rule mặc định tắt và giao diện cảnh báo câu nói có thể được Recorder lưu vào lịch sử.
- Chỉ cho phép ba generic service `turn_on`, `turn_off`, `toggle`; không cho cấu hình domain/service tùy ý.
- Redact toàn bộ câu lệnh gần nhất và nội dung rule khỏi diagnostics.
- Dùng chung dedupe message ID trong 5 phút để frame cloud lặp không chạy `toggle` hai lần.

## [1.2.0] - 2026-08-16

### Added

- Hỗ trợ TTS và media source trả `audio/mp4`, AAC hoặc M4A bên cạnh MP3/MPEG.
- Thêm `BROWSE_MEDIA` để duyệt các nguồn audio của Home Assistant ngay từ entity loa.
- Thêm mute âm lượng đầu ra, khôi phục mức âm lượng trước đó và bước âm lượng 5%.
- Bổ sung content ID, playlist, MIME snake/camel case và artwork URL vào metadata media player.

### Fixed

- Không còn ném `ServiceValidationError` khi `tts.speak` resolve thành `audio/mp4`.

### Notes

- APK chỉ xác nhận fallback `AUDIO_MPEG`; MP4/AAC được gửi bằng fallback này để firmware tự nhận dạng nội dung URL.
- Không quảng bá stop, seek theo giây, power, queue hoặc native announcement vì APK không có command tương ứng đủ an toàn.

## [1.1.1] - 2026-08-16

### Fixed

- Cho phép cờ `announce=true` mà service `tts.speak` của Home Assistant luôn gửi tới media player, sửa lỗi TTS bị chặn trước khi resolve media source.

### Changed

- TTS announcement được cast theo chế độ thay thế nội dung đang phát vì protocol MAIKA chưa có cơ chế native để tạm dừng rồi tự khôi phục nội dung trước đó.
- Tiếp tục từ chối queue `enqueue=add` và `enqueue=next`.

## [1.1.0] - 2026-08-15

### Added

- Cloud cast thử nghiệm từ `media_player.play_media` tới loa MAIKA vật lý bằng protocol `CommandHandOver` tìm thấy trong APK 3.2.3.
- Hỗ trợ URL HTTP(S), đường dẫn Home Assistant và `media-source://` cho audio MPEG.
- Tùy chọn `enable_experimental_cloud_cast`, mặc định tắt.

### Security

- Chỉ gửi payload cast cố định tới đúng serial của entity; không expose raw command.
- Từ chối URL không phải HTTP(S), URL quá dài, ký tự trắng, username/password và IP literal loopback/link-local/reserved.
- Không hỗ trợ queue hoặc announcement trong giai đoạn thử nghiệm.

## [1.0.0] - 2026-08-15

### Added

- Local brand icon để vượt qua HACS brands validation.
- MIT license và hướng dẫn cấu hình repository GitHub cho HACS.

### Changed

- Nâng version integration lên `1.0.0` để khớp release tag `v1.0.0`.
- Bổ sung kiểm tra license và brand asset trong repository validator.

## [0.1.0] - 2026-08-15

### Added

- Config flow và reauthentication cho tài khoản MAIKA.
- 27 entity cho mỗi loa: media player, sensor, binary sensor, select, text, switch và button.
- REST polling kết hợp cloud `/connect` stream.
- Volume, playback, microphone mute, restart và các setting an toàn.
- Diagnostics có redact dữ liệu nhạy cảm.
- Bridge MAIKA → Home Assistant Assist thử nghiệm với prefix và dedupe.
- HACS metadata, hassfest/HACS validation và release workflow.

### Security

- Không expose factory reset, SIP credential, arbitrary command, write `status` hoặc avatar.
- Access token chỉ giữ trong memory; refresh token không được dùng hoặc persist.
