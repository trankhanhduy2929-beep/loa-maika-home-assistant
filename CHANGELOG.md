# Changelog

Các thay đổi đáng chú ý của dự án được ghi tại đây.

## [1.29.4] - 2026-10-30

### Fixed

- Chọn bài trong danh sách trên loa tự phát ngay: integration gửi
  `JumpCommandIssued` rồi `ResumeCommandIssued`, không cần bấm phát thêm.
- Thanh thời gian tự chạy mỗi giây kể cả khi Home Assistant không trả
  `media_position_updated_at`; vị trí được neo lại khi đổi bài, tua hoặc
  chuyển trạng thái.
- Nút trái tim luôn bấm được khi loa trực tuyến. Integration tự tìm bài đang
  phát trong queue native qua `songKey`, tên bài hoặc queue chỉ có một bài để
  lấy ID, URL và metadata còn thiếu.
- Danh sách yêu thích trả mọi mã nhận diện của từng bài, tránh bỏ sót trạng
  thái đã lưu.

### Tests

- Thêm kiểm thử gửi jump + resume, fallback bài hiện tại từ queue, thời gian
  chạy khi thiếu timestamp và trái tim vẫn bấm được khi thiếu `maika_song_key`.

## [1.29.3] - 2026-10-30

### Added

- Panel **Điều khiển MAIKA** luôn hiển thị thanh tiến trình phát với thời gian
  đã phát và tổng thời lượng khi có metadata. Thời gian tự nhích mỗi giây;
  thanh kéo tua chỉ xuất hiện khi loa báo thời lượng và media player hỗ trợ
  seek.
- Tự lấy thời lượng bài đang phát từ `durationInMilliseconds` hoặc từ trường
  `time`/`duration` của bài tương ứng trong queue native.

### Fixed

- Nút trái tim nhận thêm `mediaId`/`media_id` và ID số, không còn bị vô hiệu
  khi bài đang phát thiếu `key` hoặc `songKey`.
- Panel tải danh sách bài yêu thích từ MAIKA để tô trạng thái trái tim và tự
  chuyển sang **đã lưu** sau khi thêm bài, tránh thêm trùng.
- Khi thêm bài yêu thích, integration luôn đối chiếu lại playlist theo tên và
  bỏ ID cache cũ nếu playlist đó không còn trong tài khoản.

### Tests

- Thêm kiểm thử fallback thời lượng từ queue, nhận diện `mediaId`/ID số, xóa
  ID yêu thích cache cũ và trạng thái trái tim trong browser test.

## [1.29.2] - 2026-10-30

### Changed

- Bỏ thanh mini-player cố định ở góc dưới panel theo yêu cầu. Điều khiển
  phát/tạm dừng, bài trước/sau, thời gian và thư viện vẫn nằm trong mục
  **Điều khiển MAIKA**.
- Khi login không trả `favorite_playlist_id`, integration tự tìm playlist
  **Bài hát yêu thích** qua `GET /v1/playlist` và dùng ID đó cho thư viện và
  service thêm bài yêu thích. Nếu danh sách tải về rỗng, integration thử lại
  bằng playlist yêu thích tìm theo tên.

### Fixed

- Gửi đúng payload thêm bài như app 3.2.3: bỏ `source` mặc định `nct` và dùng
  `status=0` thay vì `status=1`. Payload sai trước đây có thể làm playlist yêu
  thích trên app MAIKA không tải đúng.

### Tests

- Thêm kiểm thử tìm playlist yêu thích theo tên, fallback khi thiếu ID và
  payload thêm bài.
- Browser test xác nhận panel không còn render mini-player.

## [1.29.1] - 2026-10-30

### Fixed

- Chọn bài từ **Thư viện giải trí**, **NhạcCủaTui** hoặc **Bài hát yêu thích**
  cập nhật ngay bài đang phát, vị trí `0:00` và ảnh bìa thay vì giữ bài cũ tới
  khi loa báo lại. Nhờ đó nút phát/tạm dừng không còn gửi resume vào nội dung
  cũ và người dùng thấy bài mới tự phát ngay.
- Đổi bài không còn tái sử dụng thời gian `offsetInMilliseconds` của bài trước.
  Khi metadata bài đổi, khi chọn bài trong queue native hoặc khi bấm
  previous/next, panel reset vị trí về `0:00` và bỏ thời lượng cũ.
- Previous/next cập nhật ngay tên bài, ca sĩ và vị trí của bài liền kề trong
  queue native trước khi event live về, đồng thời xóa URL cast cũ để seek
  không phát lại bài trước.
- **Content Store** hiển thị thể loại của từng kênh thành thư mục con thay vì
  gộp toàn bộ media; query lọc thêm `media_channel_id` giống app 3.2.3.
- **Nhắc hẹn** tách các mục đã xong/đã qua vào khu **Lịch sử** nhưng vẫn cho
  phép sửa và xóa.

### Tests

- Thêm kiểm thử optimistic cast, reset offset, next/previous native, metadata
  bài đổi và cây kênh → thể loại → media.
- Browser test kiểm tra breadcrumb kênh/thể loại và khu lịch sử nhắc hẹn.
- Ruff, repository checks, unit test, browser test và HA compatibility pass.

## [1.29.0] - 2026-10-30

### Added

- Mini-player cố định trong panel, giữ nguyên khi cuộn hoặc chuyển giữa các
  mục. Có nút bài trước, phát/tạm dừng, bài tiếp theo và mở nhanh **Thư viện
  giải trí**.
- Mini-player hiển thị ảnh bìa, tên bài, ca sĩ và thời gian phát dạng
  `0:30 / 3:00`; thanh tua cập nhật mỗi giây và cho phép tua khi loa hỗ trợ.

### Tests

- Browser test kiểm tra mini-player cố định qua điều hướng, cập nhật thời gian,
  mở thư viện, trả focus và ẩn khi loa tắt.
- Ruff, repository checks, unit test, browser test và HA compatibility pass.

## [1.28.0] - 2026-10-30

### Added

- Nút trái tim cạnh bài đang phát trong panel gọi service
  `maika.add_current_to_favorites` để thêm bài MAIKA hiện tại vào playlist
  **Bài hát yêu thích** của tài khoản.
- Service `maika.add_current_to_favorites` dùng `POST
  /v1/playlists/{favorite_playlist_id}/songs` với đúng body của app 3.2.3:
  `singer`, `song_id`, `song_name`, `song_url`, `lyric`, `source`, `status`,
  `imageURL`; mặc định giống app là `source=nct`, `status=1`. Service nhận
  `device_id` hoặc `entry_id` + `serial_number`.

### Tests

- API test cho body thêm bài, service test cho ánh xạ playback và trường hợp
  thiếu bài, browser test cho nút trái tim.
- Ruff, validate repository, media player test, panel browser test và HA
  compatibility pass.

## [1.27.2] - 2026-10-29

### Fixed

- Sửa import `ConfigType` từ `homeassistant.helpers.typing` thay vì
  `homeassistant.core` để integration tải được trên Home Assistant mới dùng
  Python 3.14. Không đổi entity, service hay dữ liệu đã lưu.

### Tests

- Import integration và chạy hassfest 2026.10.4 với Home Assistant 2026.10.4.
- Unit test, ruff và validate repository pass.

## [1.27.1] - 2026-10-29

### Fixed

- Thêm `CONFIG_SCHEMA` cho integration chỉ dùng config entry để đáp ứng kiểm
  tra hassfest.
- Bỏ bộ lọc thiết bị khỏi `target` của service nhắc hẹn vì Home Assistant không
  hỗ trợ; thêm trường chọn thiết bị `device_id` trong `data` cho cả năm service.
  YAML dùng `data.device_id` thay cho `target.device_id`, hoặc vẫn truyền
  `entry_id` + `serial_number`.
- Chuyển tên, mô tả action và field sang `strings.json` cùng bản dịch
  `translations/en.json`, `translations/vi.json`; sửa selector trạng thái và
  danh sách reminder ID cho đúng schema của Home Assistant.

### Tests

- Kiểm tra toàn bộ selector trong `services.yaml` bằng Home Assistant 2026.2.3.
- Unit test nhắc hẹn, ruff, validate repository và hassfest 2026.2.3 pass.

## [1.27.0] - 2026-10-29

### Added

- **Bài hát yêu thích MAIKA**: mục mới trong **Thư viện giải trí** đọc playlist
  yêu thích của tài khoản MAIKA đang đăng nhập và phát trực tiếp qua cast cloud.
  Mục này chỉ xuất hiện khi tài khoản trả về `favorite_playlist_id`. Danh sách
  tải đủ các trang theo `meta_data.total_page` thay vì chỉ 100 bài đầu.
- **Nhắc hẹn trên loa**: mục **Nhắc hẹn** trong panel cho phép xem, tạo và xóa
  lịch nhắc qua cloud MAIKA. Hỗ trợ một lần/hằng ngày/hằng tuần/hằng tháng/hằng
  năm, báo trước 0–60 phút và lời đọc TTS tùy chọn; danh sách tải theo loa đang
  chọn khi mở mục và tự cập nhật sau khi tạo/xóa.
- Thêm endpoint panel `GET/POST /api/maika/panel/reminders` và helper kiểm tra
  thời gian, nội dung, tần suất trước khi gửi lên MAIKA.
- **Service nhắc hẹn cho automation**: `maika.create_reminder`,
  `maika.update_reminder`, `maika.set_reminder_enabled`,
  `maika.delete_reminders` và `maika.mute_reminders`. Service nhận device
  target hoặc `entry_id` + `serial_number`, xác minh reminder thuộc đúng loa
  trước khi sửa/xóa và trả lỗi rõ ràng khi chọn thiếu hoặc trùng loa.

### Changed

- **Panel gọn hơn trên điện thoại**: chỉ mục **Tổng quan** mở sẵn; Trò chuyện,
  Giọng nói, Thiết bị, Thiết lập và phần media được gom thành mục có nút mở/đóng.
  Chọn mục trên thanh điều hướng sẽ tự mở đúng phần; trạng thái mở được giữ khi
  dữ liệu loa cập nhật.
- **Gom nhiều cách nói vào một rule**: nhập các câu cách nhau bằng dấu phẩy cho
  cùng một thiết bị/thao tác. Bộ đếm và giới hạn 200 tính theo từng câu; kiểm
  tra trùng vẫn áp dụng sau khi bỏ dấu và chuẩn hóa chữ.
- **Tự cập nhật rule khi đổi Entity ID**: Home Assistant rename entity sẽ cập
  nhật cột entity trong các rule liên quan, giữ nguyên comment, thông số và bố
  cục dòng.

### Tests

- Thêm unit test tách câu theo dấu phẩy, giới hạn, trùng lặp và rewrite Entity ID
  (kể cả CRLF/comment); panel browser kiểm tra accordion, bộ đếm câu và luồng
  lưu câu lệnh.
- Thêm unit test payload/parse/lọc nhắc hẹn, wire format endpoint playlist và
  reminder, browse/phát bài yêu thích; panel browser kiểm tra tải nhắc hẹn, tạo,
  xóa và phát bài yêu thích.
- Thêm unit test service nhắc hẹn: chọn loa qua device/entry/serial, chặn loa
  mơ hồ, scope reminder ID theo loa, cập nhật một phần, bật/tắt, xóa, mute và
  từ chối ngày mute sai định dạng.
- Unit test, panel browser, ruff và validate repository pass.

## [1.26.0] - 2026-10-26

### Added

- **Hỏi trạng thái Home Assistant bằng giọng nói**: thêm thao tác **Đọc trạng
  thái và trả lời** cho cảm biến, cảm biến nhị phân và các entity đang hỗ trợ
  câu lệnh. Loa đọc câu trả lời ngắn bằng TTS, ví dụ “Nhiệt độ phòng khách là
  28,5 độ C” hoặc nhiệt độ hiện tại, độ ẩm và nhiệt độ đặt của điều hòa.
- Chọn entity TTS trong **Thiết lập → Giọng nói → Giọng đọc câu trả lời trạng
  thái**; nếu chỉ có một TTS thì tự chọn. Vẫn dùng loa MAIKA đã chọn cho âm
  phản hồi và yêu cầu bật cast cloud.
- Sensor câu lệnh lưu thêm `response_text` để kiểm tra câu trả lời đã gửi.

### Changed

- Thao tác `read` không gọi service điều khiển, không chạy âm báo thành công và
  ẩn nút **Chạy thử** vì chỉ có tác dụng khi nói với loa.
- Điều khiển điều hòa bằng câu lệnh sẵn có vẫn giữ nguyên: bật/tắt, đặt nhiệt
  độ, chọn chế độ, tốc độ quạt và đảo gió.

### Safety

- Chỉ đọc entity do người dùng chọn trong rule; không nhận template hoặc entity
  ID từ câu nói.
- Câu trả lời được giới hạn độ dài, bỏ ký tự điều khiển và chỉ phát qua loa
  thuộc đúng config entry MAIKA.

### Tests

- Thêm unit test định dạng nhiệt độ/độ ẩm điều hòa, rule `read` và gọi
  `tts.speak`; panel browser kiểm tra chọn cảm biến, ẩn nút chạy thử và lưu
  entity TTS.
- Unit test, panel browser, ruff, validate và build pass.

## [1.25.0] - 2026-10-26

### Changed

- **Gộp thiết lập vào một tab Thiết lập**: Trợ lý Maika, Bản quyền, Cấu hình
  loa và Công cụ nay nằm trong một tab thay vì bốn mục riêng trên thanh điều
  hướng.
- Mỗi nhóm là một accordion có nút mũi tên để mở/đóng. Trợ lý Maika mở sẵn;
  trạng thái mở/đóng được giữ khi dữ liệu loa cập nhật.
- Giữ nguyên entity, handler và toàn bộ chức năng nhập key, chỉnh cấu hình,
  làm mới và khởi động lại loa; không thay đổi dữ liệu integration.

### Tests

- Panel browser: kiểm tra một tab Thiết lập, đủ bốn accordion, điều khiển bằng
  bàn phím, giữ trạng thái mở khi dữ liệu cập nhật và không tràn ngang ở
  320–1920px.
- Unit test, panel browser, ruff và validate repository pass.

## [1.24.0] - 2026-10-26

### Changed

- **Gộp thông tin loa vào một tab Thiết bị**: trạng thái, tên & vị trí, thông tin
  thiết bị, firmware và bảo hành nay nằm trong cùng một tab thay vì tách thành
  nhiều mục trên thanh điều hướng.
- Mỗi nhóm thông tin là một accordion có nút mũi tên để mở/đóng; trạng thái mở
  được giữ khi dữ liệu loa cập nhật. Trạng thái loa mở sẵn, các nhóm còn lại thu
  gọn để panel gọn hơn trên điện thoại.
- Giữ nguyên entity, handler và toàn bộ chức năng chỉnh tên, xem firmware và bảo
  hành; không thay đổi dữ liệu integration.

### Tests

- Panel browser: kiểm tra một tab Thiết bị, đủ năm accordion, điều khiển bằng
  bàn phím, giữ trạng thái mở khi dữ liệu cập nhật và không tràn ngang ở
  320–1920px.
- Unit test, panel browser, ruff và validate repository pass.

## [1.23.0] - 2026-10-25

### Added

- **Tìm kiếm NhạcCủaTui**: thêm tìm bài qua `GET /api/v1/search/song` và `media_player/search_media`. Panel có ô tìm ngay trong thư viện giải trí; kết quả trả về track `maika_nct_track`, chọn bài sẽ cast qua cloud MAIKA như luồng NhạcCủaTui hiện có.
- Hỗ trợ `SEARCH_MEDIA` trong `supported_features`, để trình duyệt media Home Assistant và lệnh WebSocket `media_player/search_media` dùng được.

### Tests

- Thêm unit test chuẩn hóa search, query rỗng không gọi API, search trả track và panel gửi đúng `media_player/search_media`.
- Unit test media player/NhạcCủaTui, panel browser, ruff, validate và build pass.

## [1.22.1] - 2026-10-25

### Fixed

- **NhạcCủaTui không thấy trong trình duyệt media**: thêm mục gốc `NhạcCủaTui` trực tiếp dưới **MAIKA**, thay vì chỉ nằm cuối `Thư viện giải trí MAIKA`. Vẫn giữ lối vào trong thư viện và panel.

### Tests

- Cập nhật kiểm tra cây gốc MAIKA gồm `maika_playlist`, `maika_nct_root`, `maika_cs_root`.
- Unit test media player/NhạcCủaTui và panel browser pass.

## [1.22.0] - 2026-10-25

### Added

- **NhạcCủaTui trong Thư viện giải trí MAIKA**: thêm thư mục `NhạcCủaTui` với **Bài hát mới** (`song/feed`) và **Top thịnh hành** (`playlist/charts` + `app/charts/more`). Chọn bài sẽ lấy stream công khai mới nhất từ API NhạcCủaTui, ưu tiên stream không cần VIP rồi tới 320 kbps, sau đó cast qua MAIKA cloud.
- Phát trực tiếp link NhạcCủaTui qua `media_player.play_media` với URL `/song/<key>`, link `/bai-hat/...<key>.html`, hoặc `nct:<key>`.
- Panel nhận `maika_nct_track`, hiển thị bài NhạcCủaTui và gửi đúng `media_content_type` khi phát.

### Changes

- Thêm `custom_components/maika/nhaccuatui.py` và `MaikaApiClient.async_nct_json`.
- Thêm khóa dịch lỗi NhạcCủaTui cho `strings.json`, `en.json`, `vi.json`.

### Tests

- Thêm `scripts/test_nhaccuatui.py` cho parser stream/chart/URL.
- `test_media_player.py`: duyệt cây NhạcCủaTui, phát track, link trực tiếp, mã lỗi.
- Panel browser: fixture và kiểm tra phát `maika_nct_track`.
- Kiểm tra API trực tiếp: feed, 12 chart, chart 50 bài, detail stream 320.
- Chưa kiểm thử cast/phát trên loa MAIKA thật.

## [1.21.1] - 2026-10-25

### Fixed

- **Sửa lỗi "Không tải được thư viện giải trí" khi mở kênh**: API Content Store đã chuyển danh sách media từ `rel_channel_category.medias` sang `category.medias`. Query `ContentChannelMedias` và parser được cập nhật theo schema hiện tại; trước đó Hasura trả `field 'medias' not found in type: 'rel_channel_category'` và integration báo lỗi chung.
- Giữ tương thích với response cũ nếu `medias` vẫn nằm trực tiếp trên relation.

### Tests

- Cập nhật fixture Content Store sang cấu trúc `category.medias`; thêm kiểm tra query không quay lại shape cũ. `validate_repository.py` pass.

## [1.21.0] - 2026-10-24

### Added

- **Proxy media add-on qua HTTPS của Home Assistant**: khi loa MAIKA nhận URL relay HTTP LAN của YouTube Pro (`:2032/api/media-*`) và Home Assistant có `external_url` HTTPS, integration đăng ký một URL proxy tạm thời trên Home Assistant và stream response của add-on qua đó. Loa chỉ cần truy cập Home Assistant bằng HTTPS, không cần nginx riêng hay mở thêm cổng.
- Token proxy ngẫu nhiên, chỉ dùng cho URL add-on đã xác thực (IP private, cổng 2032, path media), hết hạn sau 24 giờ; không proxy URL tùy ý.

### Changed

- `cast_ready_url` ưu tiên proxy HTTPS cho media add-on trước khi fallback sang địa chỉ LAN HTTP cũ.
- Kiểm thử: thêm `scripts/test_media_relay.py`; 99 test pass; `validate_repository.py` pass.

## [1.20.4] - 2026-10-24

### Changed

- **HACS tải từng tệp thay vì release asset**: GitHub đang trả header
  `content-security-policy` khoảng 9 KB trên redirect tải release, vượt giới hạn
  8190 byte của `aiohttp` trong HACS 2.0.5, gây lỗi
  `LineTooLong: Got more than 8190 bytes when reading`. `hacs.json` chuyển sang
  `zip_release: false` để HACS dùng đường tải file thay thế; không thay đổi mã
  integration. Có thể bật lại `zip_release` khi HACS phát hành bản sửa.
- Vẫn phát hành `maika.zip` và `maika-manual.zip` cho cài thủ công/lưu trữ.
- Kiểm thử: 99 test pass; `validate_repository.py` pass.

## [1.20.3] - 2026-10-24

### Fixed

- **Không ép cổng media khi có `cloud_cast_base_url`**: bản 1.20.2 giữ cổng gốc cho mọi URL được viết lại, nên nếu người dùng đặt base URL HTTPS không kèm cổng (ví dụ `https://ha.example.com`) thì URL media Home Assistant có thể bị thêm `:8123`. Nay chỉ giữ cổng gốc ở nhánh tự chọn host LAN; nhánh override dùng đúng scheme/host/cổng của base URL.
- Kiểm thử: 99 test pass; `validate_repository.py` pass.

## [1.20.2] - 2026-10-24

### Fixed

- **Cloud cast giữ nguyên cổng media của add-on**: khi host media là `homeassistant.local` (hoặc host không phân giải được), `cast_ready_url` từng thay cả host lẫn cổng bằng URL Home Assistant, biến `http://homeassistant.local:2032/api/media/...` thành `http://<LAN-IP>:8123/api/media/...` nên loa tải nhầm vào Home Assistant và im lặng. Nay giữ cổng gốc (ví dụ `2032`) khi URL có cổng tường minh; URL media của Home Assistant không đổi.
- Kiểm thử: 99 test pass; `validate_repository.py` thêm kiểm tra giữ cổng `2032` cho URL relay add-on.

## [1.20.1] - 2026-10-15

### Fixed

- **Duyệt Thư viện giải trí vào mục con bị trống**: truy vấn media của kênh
  (`_QUERY_CHANNEL_MEDIAS`) chọn trường `type` trên `media` — trường này không
  tồn tại trên đối tượng media (tài liệu Apollo trong APK dùng
  `_type { description value }`). Hasura từ chối cả truy vấn nên mọi mục con của
  **Thư viện giải trí** hiện trống; nay chọn đúng `_type` và lọc `is_published`.

### Changed

- **Gộp lịch sử vào hội thoại**: bỏ mục **Lịch sử** riêng. Câu lệnh MAIKA nghe
  qua micro nay nằm chung dòng thời gian với **Trò chuyện**, sắp theo thời gian,
  kèm nhãn kết quả (Đã thực hiện / Lỗi / Đang chạy / Chưa có rule) và khử trùng
  với câu lệnh vừa gõ trong chat trong 60 giây.
- **Hội thoại cập nhật gần thời gian thực**: khi mục **Trò chuyện** đang mở,
  panel tự nạp lại mỗi 4 giây (bỏ qua khi tab ẩn, đang gửi lệnh hoặc có hộp thoại
  mở) và sau khi gửi thì thăm dò phản hồi nhanh hơn (mỗi 1,5 giây, tối đa 10 lần).
  Nội dung đang gõ và focus bàn phím được giữ nguyên nhờ cơ chế vá DOM hiện có.

### Tests

- Cập nhật kiểm thử trình duyệt: lịch sử giờ kiểm trong thẻ chat theo đúng thứ
  tự thời gian, thêm kiểm tra gộp mục con thư viện hiển thị đúng truy vấn mới.

## [1.20.0] - 2026-10-15

### Added

- **Lịch sử câu lệnh được lưu lại**: lịch sử câu lệnh MAIKA nghe được giờ được
  ghi xuống HA `Store` (`maika.command_history.<entry_id>`) và khôi phục sau khi
  khởi động lại Home Assistant, thay vì chỉ giữ trong bộ nhớ coordinator.
- **Trò chuyện với loa từ panel**: mục "Trò chuyện" cho phép gõ câu lệnh rồi
  gửi tới loa đang chọn, đúng luồng app gốc — một event `Recognize` namespace
  `SpeechRecognizer` (`rawSpeech`) gửi qua `https://chatbot.iviet.com/stream`
  với header `device-id`/`olli-session-id` trỏ đúng loa. Panel hiện câu lệnh đã
  gửi và tự nạp lại để bắt phản hồi `TextToSpeech`/`SpeechSynthesizer`. Backend:
  `api.async_send_voice_text`, `coordinator.async_send_chat`, endpoint panel
  `POST /api/maika/panel/chat`.
- **Chọn media Content Store ngay trong panel**: nút "Thư viện giải trí" trên
  thẻ điều khiển mở hộp thoại duyệt `maika_cs_*` (kênh → media → tập/bài, thể
  loại, nổi bật) và phát bài bằng `play_media` `maika_cs_track`, thay vì chỉ
  qua trình duyệt media của Home Assistant.
- **Tối ưu không gian panel**: nút mở thư viện gộp vào hàng bài đang phát dạng
  nút icon, bỏ hàng nút riêng trong thẻ điều khiển.

### Tests

- Thêm kiểm thử lịch sử bền vững (lưu/khôi phục) và chat (gửi + bắt phản hồi,
  từ chối loa lạ/câu rỗng) trong `scripts/test_live_playback.py` (44 kiểm thử).
- Thêm kiểm thử trình duyệt cho mục Trò chuyện và thư viện Content Store trong
  panel (`scripts/test_panel_browser.mjs`, fixture `scripts/fixtures/panel.html`).
- Chưa gửi lệnh chat tới loa vật lý; mới xác minh tĩnh từ APK và mock/stub.

## [1.19.0] - 2026-10-15

### Added

- **Thư viện giải trí MAIKA trong trình duyệt media**: thêm nhánh duyệt
  `maika_cs_root` cho Content Store gốc (kênh/radio, thể loại, nội dung nổi
  bật), đi qua `media_player.browse_media`. Duyệt kênh → media → tập/bài và
  duyệt nổi bật theo thể loại đều dùng các read operation Apollo GraphQL đã
  reverse engineer từ APK 3.2.3 (`ContentChannels`, `ContentChannelMedias`,
  `ContentCategories`, `ContentHighlights`, `ContentEpisodes`) qua endpoint
  `https://core.ocs.iviet.com/v1/graphql` với cùng token MAIKA. Mỗi bài là một
  `maika_cs_track` mang URL `audio`; `play_media` cast URL đó lên loa qua đường
  `CommandHandOver/SystemControl` + `Play/AudioPlayer` hiện có.

### Preserved

- Giữ nguyên key, tài khoản, câu lệnh, cấu hình và bản nháp. Duyệt Content Store
  không cần cloud cast; chỉ `play_media` cho `maika_cs_track` mới theo cờ
  `enable_experimental_cloud_cast`.

### Tests

- Thêm `scripts/test_content_store.py` (parser kênh/media/thể loại/nổi bật/tập,
  `async_validate`) và các kiểm thử media player cho cây duyệt Content Store,
  mở rộng media thành tập và gate cast khi phát. Validator gọi
  `validate_content_store()`; tổng media player tăng từ 43 lên 49 kiểm thử.
- Chưa gọi API thật và chưa phát trên loa vật lý; mới xác minh tĩnh từ APK và
  mock/stub.

## [1.18.0] - 2026-10-15

### Added

- **Chọn bài trực tiếp trong danh sách bài trên loa**: bấm tên bài đang phát
  trong mục Điều khiển MAIKA để mở danh sách `latest_playlist` của loa và chọn
  bài, không cần bấm Trước/Tiếp. Integration duyệt queue native qua
  `media_player.browse_media` (`maika_playlist`/`maika_song`) và chọn bài bằng
  đúng một `JumpCommandIssued` với `songKey`, sau khi đọc lại playlist và xác
  minh bài còn thuộc đúng loa. Tính năng chạy cả khi tắt cast cloud; URL và
  `media-source://` vẫn theo cờ cast như trước.

### Fixed

- **Tên bài hiển thị lệch khi ra lệnh bằng giọng nói**: dữ liệu live chỉ có
  volume hoặc phản hồi cũ bị coi là mới có thể ghi đè metadata REST mới, khiến
  panel hiện tên bài trước cho tới khi bấm Tiếp. Coordinator giờ kiểm tra độ
  mới theo từng field và chỉ nhận playback/playlist khi thực sự mới; phản hồi
  chỉ có volume không đủ để hoàn tất waiter bằng cache cũ.
- Metadata playback cũ bị bỏ khi `songKey` đổi hoặc bị xóa, và giữ lại khi chỉ
  là cập nhật một phần của cùng bài; thu hẹp race giữa vòng poll và event mới.
- Đăng ký `media_control` theo thế hệ `/connect`, tự đăng ký lại khi reconnect
  và dừng đúng lúc unload; làm mới playback theo loa được dedupe.

### Preserved

- Giữ nguyên key, tài khoản, câu lệnh, cấu hình và bản nháp; không dựng playlist
  giả từ lịch sử, URL cast hay suy luận câu nói.

### Tests

- Thêm 40 kiểm thử live playback và 43 kiểm thử media player bằng HA stub: độ
  mới theo field, giữ metadata cùng bài, race event/poll, vòng đời subscription,
  nhánh browse native, xác minh revision/thành viên queue và đúng một
  `JumpCommandIssued`. `validate_live_playback()` được nối vào validator.
- Bộ trình duyệt thêm luồng mở/chọn/thử lại/đóng danh sách bài, đánh dấu bài
  đang phát theo thuộc tính, khôi phục focus, phím Esc và hủy phản hồi đến muộn.
- Chưa kiểm thử trên loa và Home Assistant thực tế; mới xác minh tĩnh từ APK và
  mock/stub.

## [1.17.0] - 2026-10-14

### Added

- **Nút Dừng phát** cho media player: nút vuông cạnh nút play/pause trong mục
  Điều khiển MAIKA, đồng thời hỗ trợ action `media_player.media_stop`.
  API đã xác minh chưa có lệnh stop riêng: integration gửi `PauseCommandIssued`,
  báo `paused` và giữ vị trí để phát tiếp. Không giả báo `idle`, reset vị trí
  hoặc xóa hàng đợi trên loa. Nút có hiệu ứng nhấn, tôn trọng Giảm chuyển động
  và vô hiệu hóa khi loa mất kết nối hoặc backend chưa hỗ trợ `STOP`.

### Fixed

- **Vị trí phát bị cộng dồn sai sau khi dữ liệu live cập nhật**:
  `media_position_updated_at` trước đây chỉ được đặt khi cast/seek, nên khi loa
  báo `offsetInMilliseconds` mới, Home Assistant vẫn cộng thêm thời gian đã trôi
  qua kể từ mốc cũ và hiển thị vị trí nhảy về phía trước. Entity giờ cập nhật
  mốc khi vị trí, bài hát hoặc trạng thái thay đổi; không cộng thời gian tạm
  dừng vào lần phát tiếp và không đổi mốc khi chỉ cập nhật âm lượng.
- **Tua ±30 giây** tính từ vị trí tại lúc bấm, không dùng vị trí cũ khi render.
  Backend giữ thời lượng sau khi tua, kẹp vị trí trong khoảng hợp lệ và từ chối
  số không hữu hạn. Không dùng lại URL cast cũ khi metadata đã chuyển bài.
- Payload tua giữ loại media card `audio` giống lần phát đầu, không gửi nhầm
  MIME `audio/mpeg` vào trường `type` của giao thức MAIKA.
- Panel cập nhật thanh thời gian và khả năng điều khiển khi chỉ các thuộc tính
  này thay đổi, không cần chờ tên bài hoặc trạng thái phát đổi.
- Build release không xóa cả thư mục output, giữ lại các artifact khác.

### Preserved

- Giữ nguyên key, tài khoản, câu lệnh, cấu hình và bản nháp.

### Tests

- Thêm 13 kiểm thử playback với HA stub vào validator: dừng, lỗi cloud,
  pause/resume, timestamp, giới hạn tua và cache nguồn cast.
- Bộ trình duyệt kiểm tra nút Dừng phát, loa offline/backend cũ và tua từ vị
  trí tại lúc bấm. Chưa kiểm thử trên loa và Home Assistant thực tế.
- Test vuốt chạm cũ đôi lúc thất bại theo timing máy (cũng gặp trên bản gốc);
  lần xác nhận cuối chạy đầy đủ và qua, gồm 18 tổ hợp kích thước/giao diện.

## [1.16.0] - 2026-10-13

### Added

- **Nút tua nhanh ±30 giây** trong mục Điều khiển MAIKA, cạnh thanh thời gian.
  Bấm để tua lùi/tới 30 giây quanh vị trí hiện tại; tự kẹp trong khoảng
  0..thời lượng bài, gửi cùng cơ chế `mediaOffset` như thanh tua.

### Changed

- Bộ kiểm thử trình duyệt rút gọn số bước mô phỏng vuốt chạm để không phụ
  thuộc tốc độ máy; vẫn kiểm tra vuốt chạm, giới hạn hai đầu và chống vuốt
  quá ngắn.

### Preserved

- Giữ nguyên key, tài khoản, câu lệnh, cấu hình và bản nháp.

### Tests

- Bộ trình duyệt thêm kiểm tra nút tua ±30 giây gửi `media_seek` với giá trị
  được kẹp đúng; toàn bộ kiểm thử cũ vẫn qua. HA giả lập/Chromium, chưa kiểm
  thử trên loa và Home Assistant thực tế.

## [1.15.0] - 2026-10-13

### Fixed

- **Cast nhạc local từ Home Assistant**: loa không tải được file khi Home
  Assistant tạo URL bằng tên mDNS như `homeassistant.local`, tên nội bộ
  `supervisor`/`hassio` hoặc địa chỉ loopback mà loa không phân giải được.
  Integration giờ tự đổi scheme/host/port sang địa chỉ LAN mà loa truy cập
  được, giữ nguyên đường dẫn và chữ ký `authSig`, nên `/local/...`,
  `/media/local/...`, `media-source://` và TTS đều cast được.

### Added

- **Tua bài đang cast**: thêm feature `SEEK`; `media_player.media_seek` gửi lại
  `CommandHandOver` kèm `mediaOffset` để loa phát tiếp từ vị trí mới. Panel có
  thanh thời gian kéo tới/lui được cho loa đang cast từ Home Assistant.
- Ô **Địa chỉ Home Assistant cho loa tải nhạc** trong Cấu hình để tự chỉ định
  địa chỉ LAN; để trống thì integration tự dò.
- Chấp nhận thêm MIME audio thường gặp khi cast (FLAC, WAV, OGG, Opus, WebM và
  `application/ogg`); firmware tự nhận dạng nội dung từ URL.
- `media_duration` đọc từ trường lượng phát nếu loa báo, giúp thanh thời gian
  hiển thị đúng.

### Changed

- **Giảm độ trễ cast**: sau cast, play/pause, next/previous và đổi âm lượng,
  integration cập nhật trạng thái ngay rồi làm mới dữ liệu loa ở chế độ nền
  thay vì chờ thêm một vòng gọi cloud, nên phát nhạc YouTube/online vào loa
  nhanh hơn và thanh âm lượng mượt hơn.

### Preserved

- Giữ nguyên key, tài khoản, câu lệnh, cấu hình và bản nháp; không đổi API đã
  có (chỉ thêm option và tham số mới). Người đã có key dùng bình thường.

### Tests

- Ruff lint/format, `validate_repository.py` (thêm kiểm tra dò địa chỉ LAN,
  viết lại URL cast, override, trường hợp TLS và ô cấu hình mới), `node --check`
  hai file JS và bộ kiểm thử trình duyệt (thêm thanh tua gửi `media_seek`).
  HA giả lập/Chromium, chưa kiểm thử trên loa và Home Assistant thực tế.

## [1.14.0] - 2026-10-12

### Added

- Mục **Lịch sử** trong panel: liệt kê các câu lệnh gần đây MAIKA đã nghe
  (câu nói, thiết bị/ thao tác, thời gian, kết quả Đã thực hiện / Lỗi /
  Đang chạy / Chưa có rule). Lấy trực tiếp từ cảm biến câu lệnh để cập nhật
  ngay, có bản dự phòng từ snapshot. Giữ tối đa 20 câu lệnh gần nhất.
- **Nhắc hạn key**: panel hiện băng nhắc khi key còn ≤ 7 ngày (hoặc đã hết
  hạn); Home Assistant tạo thông báo hệ thống một lần mỗi ngày. Key vĩnh
  viễn không nhắc và không hiện hạn.
- **Thư viện âm phản hồi**: nguồn âm báo mới "Thư viện MP3 trên Home
  Assistant". Panel quét `/config/www`, `/config/mp3`, `/config/media` cho
  các file mp3/m4a/aac/wav/ogg/flac và phục vụ qua `/maika_media/...` để
  loa tải về.

### Changed

- Dòng **Hạn dùng** dùng hạn thật của key (`license_expires_at`) do máy chủ
  ký kèm, thay vì hạn lease ngắn hạn. Cần cập nhật worker cấp phép để có
  trường này; nếu chưa cập nhật, panel giữ cách hiển thị cũ.

### Preserved

- Giữ nguyên key, tài khoản, câu lệnh, cấu hình và bản nháp; không đổi API
  đã có (chỉ thêm tham số mới). Người đã có key dùng bình thường.

### Tests

- Bộ trình duyệt kiểm tra chọn file thư viện và lưu `voice_success_audio_path`,
  lịch sử câu lệnh (ưu tiên cảm biến, dự phòng snapshot) và nhắc hạn theo
  gói. Worker cấp phép: `npm run check` (32 test) gồm kiểm tra
  `license_expires_at` trong lease. HA giả lập/Chromium, chưa kiểm thử trên
  loa và Home Assistant thực tế.

## [1.13.0] - 2026-10-12

### Changed

- Bỏ nút **Hoạt ảnh**: chuyển động bật tự động, chỉ tắt khi thiết bị bật
  **Giảm chuyển động**. Không cần bật/tắt thủ công và không lưu lựa chọn.

### Added

- Key gói **Vĩnh viễn** không còn hiện dòng **Hạn dùng**; tiêu đề mục ghi rõ
  "Key vĩnh viễn, không giới hạn thời gian". Gói theo tháng/năm vẫn hiện hạn.

### Improved

- Giao diện tông cam Liquid Glass mượt hơn: logo có nhịp sóng nhỏ, mục đang
  chọn có vệt sáng, thẻ nổi nhẹ khi rê chuột, thanh cuộn tông cam, nút chính
  chuyển sắc và badge/ô trạng thái có phản sáng.

### Preserved

- Giữ nguyên key, tài khoản, câu lệnh, cấu hình và bản nháp; không đổi API
  hay dữ liệu license. Người đã có key dùng bình thường.

### Tests

- Chạy lại bộ trình duyệt ở 320–1920px: bỏ kiểm thử nút hoạt ảnh, thêm kiểm
  tra hoạt ảnh tự động theo **Giảm chuyển động**, dừng khi khuất/ẩn tab, và
  kiểm tra ẩn/hiện dòng hạn dùng theo gói. HA giả lập/Chromium, chưa kiểm thử
  trên loa và Home Assistant thực tế.

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
