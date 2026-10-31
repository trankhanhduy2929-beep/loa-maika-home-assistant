# MAIKA Speaker for Home Assistant

[![Validate](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/trankhanhduy2929-beep/loa-maika-home-assistant)](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)


Custom integration **không chính thức** để kết nối loa MAIKA với Home Assistant qua cloud MAIKA.
Bản hiện tại: **v1.29.4**.

Từ bản `1.6.0`, integration dùng activation server riêng để cấp quyền cho từng
Home Assistant. Mã cài đặt được tạo từ hash của Home Assistant instance ID,
không dùng MAC address và không gửi credential MAIKA tới activation server.

## Cài nhanh

Repository cài đặt chính thức của bản custom này:

`https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant`

[![Mở HACS trên Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=trankhanhduy2929-beep&repository=loa-maika-home-assistant&category=integration)

1. Mở liên kết trên hoặc vào **HACS → Integrations → ⋮ → Custom repositories**.
2. Dán URL repository ở trên, chọn loại **Integration**, rồi bấm **Add**.
3. Tìm **MAIKA Speaker**, chọn **Download**, sau đó khởi động lại Home Assistant.
4. Vào **Settings → Devices & services → Add integration**, tìm **MAIKA Speaker**.

Repository GitHub phải ở chế độ **Public** để HACS đọc được metadata và release.
Khi nâng cấp từ bản cũ, chỉ cần bấm **Update** trong HACS rồi restart; không xóa
integration, không xóa thiết bị và không cần nhập lại license key.

## Tính năng

- Tạo **27 entity cho mỗi loa**.
- Điều khiển volume, mute âm lượng đầu ra, play/pause, next/previous.
- Cast MP3/MPEG và MP4/AAC từ URL, media source hoặc TTS Home Assistant tới loa qua cloud MAIKA (thử nghiệm, mặc định tắt).
- Có thể phát MP3 MAIKA tích hợp hoặc URL MP3 riêng theo chế độ ưu tiên để che
  câu trả lời mặc định của loa, hoặc chỉ phát sau khi HASS thành công.
- Chọn bài trong danh sách bài trên loa ngay trong panel, kể cả khi tắt cast cloud.
- Duyệt **Thư viện giải trí MAIKA** (kênh/radio, thể loại, nội dung nổi bật) trong trình duyệt media của Home Assistant hoặc ngay trong panel.
- Duyệt và phát **Bài hát yêu thích** của tài khoản MAIKA qua cast cloud, ngay trong Thư viện giải trí; danh sách tải đủ các trang playlist.
- Bấm nút trái tim cạnh bài đang phát trong panel hoặc gọi service `maika.add_current_to_favorites` để lưu bài MAIKA hiện tại vào playlist yêu thích của tài khoản.
- Xem, tạo và xóa **nhắc hẹn** phát trên loa (một lần hoặc lặp lại, báo trước, lời đọc TTS tùy chọn) trong mục **Nhắc hẹn** của panel hoặc bằng service Home Assistant.
- Duyệt, tìm kiếm và phát **NhạcCủaTui** ngay trên mục MAIKA và trong thư viện giải trí: bài hát mới, top thịnh hành, tìm theo tên bài/ca sĩ; phát link bài NhạcCủaTui bằng `media_player.play_media`.
- Gõ câu lệnh **trò chuyện với loa** từ panel; integration gửi event `Recognize` tới đúng loa và hiện phản hồi của loa.
- **Lịch sử câu lệnh được lưu lại** qua các lần khởi động lại Home Assistant.
- Duyệt các nguồn audio Home Assistant trực tiếp từ giao diện media player.
- Tắt hoặc bật lại micro vật lý.
- Cấu hình độ nhạy wake word, phản hồi wake word và giọng TTS.
- Đổi tên loa, tên gọi và địa chỉ.
- Theo dõi online, Wi-Fi, firmware, bảo hành, playback và các thông tin chẩn đoán.
- Tự tìm loa qua stream cloud nếu API danh sách thiết bị MAIKA tạm trả lỗi 5xx.
- Restart an toàn; không expose factory reset.
- Sensor câu nói mới nhất và rule toàn câu để điều khiển đèn, quạt, rèm, điều
  hòa, media, scene, script, robot hút bụi và helper Home Assistant, mặc định tắt.
- Hỏi trạng thái cảm biến hoặc điều hòa bằng câu lệnh đã đặt; loa trả lời bằng
  TTS, ví dụ “Nhiệt độ phòng khách là 28,5 độ C”.

## Panel quản lý loa trong sidebar

Từ bản `1.9.0`, tích hợp tự thêm mục **MAIKA** vào sidebar Home Assistant. Panel
hiển thị thông tin loa (tên, model, hãng, serial, firmware, wifi, trạng thái,
bài đang phát), toàn bộ cảm biến, nút, công tắc và lựa chọn của tích hợp; đồng
thời hiển thị bản quyền đang dùng (key, gói, hạn) và cho nhập/đổi key, chỉnh cấu
hình ngay tại panel thay vì mở phần **Cấu hình**. Từ bản `1.9.2`, nếu một tài
khoản MAIKA có nhiều loa, panel hiện hàng chip chọn loa và chỉ hiển thị entity
của loa đang chọn. Bản `1.9.4` tối ưu điện thoại/tablet/máy tính, có thanh
chuyển mục nhanh và lựa chọn **Tự động / Sáng / Tối** ở góc trên. Giao diện
giữ nội dung đang nhập khi loa cập nhật, hỗ trợ giảm chuyển động; không cần
cài thêm Mushroom hoặc card-mod. Bản `1.10.0` có mục **Giọng nói** riêng:
chọn thiết bị/automation, chọn thao tác và nhập câu nói — không cần viết rule.
Kích hoạt chỉ cần dán key, không còn ô URL máy chủ. Từ `1.10.1`, bỏ nút
**Configure / Tùy chọn MAIKA** bên trang tích hợp: nhập/thay key tại
**MAIKA → Thiết lập → Bản quyền**, chỉnh tính năng tại **Thiết lập → Cấu hình loa** và **Giọng nói**.
Panel vẫn mở được khi key hết hạn hoặc tài khoản chưa kết nối để bạn tự
thay key; dữ liệu và cài đặt cũ được giữ nguyên. Thêm/xóa tài khoản, tải lại
và đăng nhập lại vẫn dùng chức năng chuẩn của Home Assistant. Chi tiết xem
[docs/PANEL.md](docs/PANEL.md).

Bản `1.29.4` cho chọn bài là phát ngay, thanh thời gian chạy thời gian thực và nút trái tim luôn bấm được khi loa trực tuyến. Bản `1.29.3` thêm thanh tiến trình phát có thời gian, nhận diện bài yêu thích đang phát và đồng bộ trạng thái trái tim với playlist MAIKA. Bản `1.29.2` bỏ thanh mini-player dưới panel, tự tìm playlist **Bài hát yêu thích** khi login thiếu ID và gửi payload thêm bài giống app MAIKA 3.2.3. Bản `1.29.1` sửa offset khi đổi bài, cập nhật ngay bài mới từ thư viện/yêu thích/NhạcCủaTui, hiển thị thể loại Content Store thành thư mục và tách lịch sử nhắc hẹn.

Bản `1.28.0` thêm nút trái tim cạnh bài đang phát và service `maika.add_current_to_favorites` để lưu bài MAIKA hiện tại vào **Bài hát yêu thích**.

Bản `1.27.2` sửa import `ConfigType` để integration tải được trên Home Assistant dùng Python 3.14 mới. Không đổi entity hay dữ liệu đã lưu.

Bản `1.27.1` sửa khai báo service nhắc hẹn để hợp lệ với hassfest: chọn loa bằng trường `device_id` trong `data` thay vì `target`, vẫn hỗ trợ `entry_id` + `serial_number`.

Bản `1.27.0` thêm **Nhắc hẹn** trên loa (panel và service automation), **Bài hát yêu thích** có tải đủ trang playlist, và giao diện panel gọn hơn trên điện thoại.

Bản `1.26.0` thêm thao tác **Đọc trạng thái và trả lời** cho câu lệnh giọng nói.
Chọn cảm biến hoặc điều hòa, chọn giọng TTS rồi đặt câu như “nhiệt độ phòng
khách bao nhiêu”; loa trả lời bằng giọng nói. Điều khiển điều hòa bằng câu lệnh
vẫn dùng các thao tác sẵn có.

Bản `1.25.0` gộp **Trợ lý Maika**, **Bản quyền**, **Cấu hình loa** và
**Công cụ** vào một tab **Thiết lập**. Mỗi nhóm là một accordion; trợ lý mở
sẵn, ba nhóm còn lại thu gọn và trạng thái mở/đóng được giữ khi dữ liệu cập
nhật. Không đổi entity hay cấu hình.

Bản `1.24.0` gộp **Trạng thái loa**, **Tên & vị trí**, **Thông tin thiết bị**,
**Firmware & hệ thống** và **Bảo hành** vào một tab **Thiết bị**. Mỗi nhóm là
một accordion có nút mũi tên để mở/đóng; trạng thái loa mở sẵn và trạng thái
mở/đóng được giữ khi dữ liệu cập nhật. Không đổi entity hay cấu hình.

Bản `1.23.0` thêm **tìm kiếm NhạcCủaTui** trong panel và qua
`media_player/search_media` của Home Assistant. Nhập tên bài hoặc ca sĩ trong ô
tìm của thư viện giải trí; kết quả dùng chung luồng cast NhạcCủaTui. Cần bật cast
cloud để phát, và chưa kiểm thử phát trên loa thật.

Bản `1.22.1` đưa **NhạcCủaTui** ra thẳng mục gốc **MAIKA** trong trình duyệt
media Home Assistant, không chỉ nằm cuối Thư viện giải trí. Không đổi dữ liệu hay
cấu hình; sau khi cập nhật chỉ cần restart Home Assistant rồi mở lại trình duyệt
media.

Bản `1.22.0` thêm **NhạcCủaTui trong thư viện MAIKA**: mục `NhạcCủaTui` có
**Bài hát mới** và **Top thịnh hành** (danh sách chart đầy đủ khi mở). Chọn bài
sẽ lấy stream công khai từ API NhạcCủaTui rồi cast qua cloud MAIKA; stream
không cần VIP được ưu tiên, sau đó tới chất lượng 320 kbps. Có thể phát trực tiếp bằng `media_player.play_media` với link
`https://www.nhaccuatui.com/song/<key>` hoặc `nct:<key>`. Tính năng cần bật cast
cloud; chưa kiểm thử phát trên loa thật.

Bản `1.20.3` chỉ giữ cổng media gốc ở nhánh tự chọn host LAN, không ép cổng
khi người dùng đã đặt `cloud_cast_base_url` (tránh thêm `:8123` vào URL HTTPS có
cổng mặc định). Bản `1.20.2` sửa **cast đám mây giữ nguyên cổng media của add-on**: khi host
media là `homeassistant.local` hoặc không phân giải được, integration từng thay
cả host lẫn cổng bằng URL Home Assistant nên `http://homeassistant.local:2032/...`
bị đổi thành `http://<LAN-IP>:8123/...`, loa tải nhầm vào Home Assistant và im
lặng. Nay cổng tường minh (ví dụ `2032`) được giữ nguyên; URL media của Home
Assistant không đổi. Chưa kiểm thử trên loa thật.

Bản `1.20.1` **gộp lịch sử câu lệnh vào mục Trò chuyện** (bỏ mục Lịch sử riêng;
câu lệnh nghe qua micro và chat nằm chung một dòng thời gian, kèm nhãn kết quả) và
tự làm mới hội thoại mỗi 4 giây khi mục Trò chuyện đang mở để phản hồi tới gần như
thời gian thực mà không mất nội dung đang gõ. Bản này cũng **sửa lỗi duyệt Thư viện
giải trí**: truy vấn media của kênh trước đây chọn trường `type` không tồn tại
(đúng là `_type`), khiến máy chủ GraphQL từ chối cả truy vấn và các mục con hiện
trống. Tính năng dựa trên phân tích tĩnh APK và mock, chưa kiểm thử trên loa thật.

Bản `1.20.0` thêm **Trò chuyện với loa** và **Thư viện giải trí trong panel**.
Mục **Trò chuyện** cho phép gõ câu lệnh rồi gửi tới loa đang chọn theo đúng luồng
app gốc: một event `Recognize` (namespace `SpeechRecognizer`, `rawSpeech`) tới
`chatbot.iviet.com/stream` với header `device-id`/`olli-session-id` trỏ đúng loa.
Panel hiện câu lệnh đã gửi và tự nạp lại để bắt phản hồi `TextToSpeech`/
`SpeechSynthesizer`. Nút **Thư viện giải trí** trên thẻ điều khiển mở hộp thoại
duyệt Content Store (`maika_cs_*`) và phát bài bằng `maika_cs_track`. Lịch sử câu
lệnh MAIKA giờ được **lưu xuống `Store`** và khôi phục sau khi restart. Tính năng
mới dựa trên phân tích tĩnh APK và mock, chưa kiểm thử trên loa thật.

Bản `1.19.0` thêm **Thư viện giải trí MAIKA** vào trình duyệt media của Home
Assistant: duyệt kênh/radio, thể loại và nội dung nổi bật từ Content Store gốc
của app qua GraphQL (`core.ocs.iviet.com`). Chọn một bài là cast URL `audio` do
Content Store trả về lên loa, dùng cùng đường cast cloud MAIKA. Duyệt không cần
cast cloud; chỉ khi phát mới theo cờ `enable_experimental_cloud_cast`. Tính năng
mới dựa trên phân tích tĩnh APK và mock, chưa kiểm thử trên loa thật.

Bản `1.18.0` cho **chọn bài trực tiếp trong danh sách bài trên loa**: bấm tên
bài đang phát để mở danh sách `latest_playlist` của loa rồi chọn bài, không cần
bấm Trước/Tiếp. Integration duyệt queue native qua `media_player.browse_media`
và chọn bài bằng một `JumpCommandIssued` với `songKey`, chạy cả khi tắt cast
cloud. Bản này cũng sửa việc **tên bài hiển thị lệch khi ra lệnh bằng giọng
nói**, do phản hồi live chỉ có volume hoặc cache cũ ghi đè metadata REST mới.

Bản `1.17.0` thêm **nút Dừng phát** trong mục Điều khiển MAIKA và feature
`STOP` cho action `media_player.media_stop`. API đã xác minh chưa có lệnh stop
riêng, nên nút dừng dùng `PauseCommandIssued`, báo `paused` và giữ vị trí để
phát tiếp; không reset vị trí hoặc xóa hàng đợi trên loa. Bản này sửa mốc vị
trí sau dữ liệu live/pause/resume, tua ±30 giây theo thời điểm bấm và giữ thời
lượng sau khi tua; chặn giá trị tua không hữu hạn và nguồn cast cũ khác bài.

Bản `1.16.0` thêm **nút tua nhanh ±30 giây** cạnh thanh thời gian trong mục
Điều khiển MAIKA: bấm để tua lùi/tới 30 giây quanh vị trí hiện tại, giá trị
được tự kẹp trong khoảng 0..thời lượng bài và gửi cùng cơ chế `mediaOffset`
như thanh tua.

Bản `1.15.0` sửa cast nhạc local khi Home Assistant tạo URL bằng tên mDNS
(`homeassistant.local`), tên nội bộ (`supervisor`/`hassio`) hoặc địa chỉ
loopback mà loa không phân giải được: integration tự đổi scheme/host/port
sang địa chỉ LAN mà loa truy cập được. Bản này cũng thêm tính năng tua bài
đang cast bằng `media_player.media_seek` (thanh thời gian trong panel), ô
**Địa chỉ Home Assistant cho loa tải nhạc** trong **Thiết lập → Cấu hình loa** để tự chỉ định
địa chỉ LAN, chấp nhận thêm MIME audio (FLAC, WAV, OGG, Opus, WebM) và giảm
độ trễ sau cast/play/pause/next/previous/đổi âm lượng.

Bản `1.14.0` thêm mục **Lịch sử** (các câu lệnh gần đây kèm kết quả), **nhắc
hạn key** (băng nhắc trong panel khi còn ≤ 7 ngày và thông báo hệ thống một
lần mỗi ngày) và **thư viện âm phản hồi**: chọn file MP3 có sẵn trong
`/config/www`, `/config/mp3` hoặc `/config/media` thay vì dán URL. Cài đặt
tại **Giọng nói → Âm báo khi thành công → Thư viện MP3 trên Home Assistant**.
Home Assistant phải truy cập được từ Internet để loa tải file.

Bản `1.13.0` tiếp tục **tông cam MAIKA + Liquid Glass**: thẻ kính mờ, viền
sáng và nút cam chuyển sắc, có thêm nhịp sóng nhỏ ở logo, vệt sáng trên mục
đang chọn và thẻ nổi nhẹ khi rê chuột. Khi loa đang phát, ảnh loa chuyển
động nhẹ, có vòng sóng và dải sóng trang trí; tạm dừng, tắt tiếng hoặc mất
kết nối thì dừng hiệu ứng phát nhạc. Đây không phải sóng âm thu từ micro.

Hoạt ảnh **tự động bật**, chỉ tắt khi thiết bị bật **Giảm chuyển động**; không
còn nút bật/tắt hoạt ảnh. Với key **vĩnh viễn**, mục **Thiết lập → Bản quyền** ẩn dòng
**Hạn dùng** và ghi rõ không giới hạn thời gian; gói theo tháng/năm vẫn hiện
hạn. **Vuốt ngang đổi loa**, bản nháp key/câu lệnh và mọi cài đặt vẫn giữ
nguyên. Phần phát URL MP3/AAC mở bằng **Phát âm thanh từ đường dẫn**.

Bản vá `1.11.1` sửa lỗi không cuộn được bằng con lăn chuột khi panel nhúng
trong Home Assistant. Cuộn trang, cuộn danh sách câu lệnh và vuốt điện thoại
vẫn dùng thao tác tự nhiên. Sau khi cập nhật, khởi động lại HA và tải lại
trang bằng **Ctrl+F5**; không cần xoá integration hoặc nhập lại key.

## Cài bằng HACS

Repository này hỗ trợ HACS custom repository. Nếu không dùng nút cài nhanh ở trên,
thêm thủ công theo bốn bước:

1. Mở **HACS → Integrations → ⋮ → Custom repositories**.
2. Nhập `https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant`.
3. Chọn category **Integration**, bấm **Add**, rồi chọn **Download**.
4. Restart Home Assistant và thêm integration **MAIKA Speaker**.

Từ `1.20.4`, repository tạm đặt `zip_release: false` để HACS tải từng tệp thay
vì tải release asset. Cách này tránh lỗi GitHub trả header
`content-security-policy` dài hơn 8190 byte làm HACS 2.0.5 báo
`LineTooLong`. Nếu HACS vẫn báo lỗi, cài thủ công theo mục dưới; không cần xóa
integration, thiết bị hay license key.

## Cài thủ công

Tải `maika-manual.zip` từ GitHub Release, giải nén vào `/config` và kiểm tra:

```text
/config/custom_components/maika/manifest.json
```

Sau đó restart Home Assistant.

## File phát hành v1.29.4

- `maika.zip` và `maika-v1.29.4-hacs.zip`: gói nội dung integration để lưu trữ;
  HACS `1.29.4` tải từng tệp nên không dùng các asset này.
- `maika-manual.zip` và `maika-v1.29.4-manual.zip`: cài thủ công vào `/config`.
- `SHA256SUMS.txt`: checksum SHA-256 của toàn bộ ZIP cài đặt.
- `loa-maika-home-assistant-v1.29.4-github-source.zip`: source sạch để bàn giao.

## Cấu hình

1. Vào **Settings → Devices & services → Add integration**.
2. Tìm **MAIKA Speaker**.
3. Bấm link portal hiển thị trong form để đăng ký/đăng nhập, dùng thử 1 ngày,
   thanh toán PayOS hoặc xem lại key cũ; sau đó sao chép license key và dán vào form.
4. Với Easy Mode, Home Assistant đầu tiên dùng key được gắn tự động và form
   chuyển thẳng sang bước tài khoản MAIKA.
5. Chỉ khi người bán bật chế độ duyệt tay, gửi mã cài đặt hiển thị trên màn
   hình rồi bấm kiểm tra lại sau khi được duyệt.
6. Nhập số điện thoại hoặc email/Gmail cùng mật khẩu tài khoản MAIKA. Số điện
   thoại có thể ở dạng nội địa `084...` hoặc quốc tế `+8484...`; integration sẽ
   tự chuẩn hóa trước khi đăng nhập.

Email/Gmail phải có mật khẩu tài khoản MAIKA. Tài khoản chỉ được tạo bằng nút
**Đăng nhập bằng Google** nhưng chưa đặt mật khẩu MAIKA chưa thể dùng trực tiếp,
vì luồng đó cần Google ID token OAuth chứ không nhận mật khẩu Gmail.

Home Assistant lưu credential trong config entry để đăng nhập lại. Integration chỉ giữ access token trong bộ nhớ và không dùng/lưu refresh token.

Activation server chỉ nhận installation hash, license metadata và phiên bản;
không nhận số điện thoại/mật khẩu MAIKA. Lease ký số có thời hạn 48 giờ và cho
phép chạy offline thêm tối đa bảy ngày khi server tạm mất kết nối. Xem
[Kích hoạt thương mại](docs/LICENSING.md).

## Điều khiển nhà bằng giọng nói

Mở **MAIKA → Giọng nói** trong sidebar Home Assistant:

1. Chọn **Thiết bị / Automation / Kịch bản / Cảnh**, tìm bằng tên quen thuộc.
2. Chọn thao tác: bật/tắt, bấm nút, đặt độ sáng, nhiệt độ, tốc độ, mở rèm…
3. Nhập câu nói, ví dụ **bật đèn phòng khách**, rồi bấm **Lưu câu lệnh**.
   Nếu tính năng đang tắt, nút **Lưu & bật điều khiển** sẽ bật cùng lúc.

Không phải nhập entity ID, service hoặc JSON. Có sẵn nút **Sửa**, **Thêm cách
nói**, **Xóa** và **Chạy thử**; chạy thử điều khiển thật nên luôn có xác nhận.

Câu lệnh cũ tự hiện trong danh sách và vẫn dùng bình thường. Automation mới
mặc định kiểm tra điều kiện; có thể chọn bỏ qua để chạy trực tiếp. Câu nói
khớp toàn bộ sau khi bỏ hoa/thường, dấu tiếng Việt, khoảng trắng thừa và dấu
câu; câu có thêm từ sẽ không chạy. Xem hướng dẫn và cú pháp cũ (không bắt buộc) tại
[Câu lệnh giọng nói](docs/VOICE_COMMANDS.md).

Nếu thiết bị không chạy, mở entity **Câu lệnh giọng nói mới nhất** trong Developer Tools → States. `stream_connected` phải là `true`, `voice_subscription_status` phải là `subscribed`, `voice_subscription_count` phải bằng `voice_subscription_target_count` và `stream_frame_count` phải tăng sau khi reload. Sau khi nói, `last_stream_frame_type` cần thành `speakerConversationResponse`; khi rule khớp, `result` phải là `executed`. Integration báo rõ `entity_not_found`, `entity_unavailable` hoặc `service_not_supported` thay vì báo thành công giả.

### Âm phản hồi custom không bị chèn xuống dưới

Từ bản `1.5.0`, có thể phát một file MP3 ngắn để thay thế best-effort câu báo sai của MAIKA:

1. Bật **Cast âm thanh cloud** ở **Cấu hình loa**.
2. Vào **Giọng nói → Giọng nói & âm phản hồi**, bật điều khiển thiết bị HASS.
3. Chọn **Âm MAIKA có sẵn** để dùng `/mp3/maika.mp3` trên portal,
   **File MP3 của bạn (URL)** hoặc **Không phát âm báo**.
4. Chỉ khi chọn MP3 riêng mới cần điền URL file.
5. Nếu tài khoản có nhiều loa, chọn một loa phát phản hồi. Với đúng một loa,
   integration tự chọn; chưa tự phân biệt chắc chắn loa nào vừa nghe câu nói.
6. Tại **Thời điểm phản hồi**, chọn **Ưu tiên che giọng mặc định của loa**.
   Chế độ này gửi MP3 ngay khi rule hợp lệ và dùng lại mã hội thoại của câu nói.
   Nếu muốn chỉ phát khi thao tác không lỗi, chọn **Sau khi điều khiển thành công**.
7. Bấm **Lưu cài đặt giọng nói**.

Ở chế độ **Ưu tiên**, clip được gửi trước/khi service HASS đang chạy để giảm hiện
tượng câu mặc định phát trước. Nếu service HASS lỗi, clip đang phát có thể đã bắt
đầu; sensor sẽ ghi `played_before_failure`. APK MAIKA 3.2.3 không có command hủy
TTS/conversation riêng, nên không thể cam kết tắt tuyệt đối giọng mặc định. Chế
độ **Sau khi HASS thành công** chỉ gửi `AudioPlayer/Play` sau khi service hoàn tất
không lỗi.

Từ bản `1.5.1`, đường phản hồi tự động gửi cast trực tiếp qua MAIKA client ngay sau khi action HASS thành công, bỏ một vòng service media player và bước refresh đồng bộ để giảm độ trễ. Để giảm thời gian tải file, nên dùng clip MP3 rất ngắn và URL LAN trực tiếp như `http://<IP_HASS>:8123/local/NHACCHUONG/demo.mp3` nếu loa truy cập được Home Assistant; URL DuckDNS/reverse proxy HTTPS thường chậm hơn do DNS, TLS và hairpin Internet.

Tùy chọn URL cũ từ trước `1.7.0` được tự hiểu là **URL MP3 tùy chỉnh**, nên
người dùng nâng cấp không phải cấu hình lại. Trong sensor,
`success_audio_status: played` nghĩa yêu cầu play/cast đã hoàn tất không lỗi,
không phải telemetry xác nhận tuyệt đối loa vật lý đã phát thành tiếng. URL cấu
hình bị redact khỏi diagnostics. Xem [Câu lệnh giọng nói](docs/VOICE_COMMANDS.md).

## Cloud cast thử nghiệm

Trong **MAIKA → Thiết lập → Cấu hình loa**, bật **Cast âm thanh cloud** rồi bấm **Lưu cấu hình**; tích hợp tự tải lại. Entity loa sẽ có thêm feature `PLAY_MEDIA`, `BROWSE_MEDIA` và `SEEK`.

Ví dụ phát MP3 trực tiếp:

```yaml
action: media_player.play_media
target:
  entity_id: media_player.maika
data:
  media:
    media_content_id: "https://example.org/audio/chime.mp3"
    media_content_type: "audio/mpeg"
    metadata: {}
```

Ví dụ TTS dùng service hiện có của Home Assistant:

```yaml
action: tts.speak
target:
  entity_id: tts.google_translate_vi_com
data:
  media_player_entity_id: media_player.maika
  message: "Xin chào từ Home Assistant"
```

URL sau khi Home Assistant resolve, kể cả query token tạm nếu có, được gửi tới cloud MAIKA và loa phải truy cập được URL đó. Từ `1.15.0`, nếu URL do Home Assistant tạo dùng tên mDNS như `homeassistant.local`, tên nội bộ `supervisor`/`hassio` hay địa chỉ loopback mà loa không phân giải được, tích hợp tự đổi phần scheme/host/port sang địa chỉ LAN của Home Assistant, giữ nguyên đường dẫn và chữ ký `authSig`. Nếu mạng có cấu hình đặc biệt, điền **Địa chỉ Home Assistant cho loa tải nhạc** trong Cấu hình để chỉ định thủ công.

Bản `1.15.0` chấp nhận MP3/MPEG, MP4/AAC và thêm các định dạng audio thường gặp như FLAC, WAV, OGG, Opus, WebM (firmware tự nhận dạng URL); MIME `audio/mp4` từ TTS vẫn được hỗ trợ. Cờ `announce=true` được xử lý theo kiểu thay thế nội dung đang phát và không tự khôi phục nội dung cũ. Bài đang cast từ Home Assistant có thể tua bằng `media_player.media_seek` (hoặc thanh thời gian trong panel). Cloud cast không hỗ trợ queue `add/next`, stop thật, video hay URL có username/password. Xem [Cloud cast](docs/CLOUD_CAST.md).

## Dịch vụ nhắc hẹn

Các service `maika.create_reminder`, `maika.update_reminder`,
`maika.set_reminder_enabled`, `maika.delete_reminders` và
`maika.mute_reminders` thao tác trên đúng loa MAIKA đã chọn. Trong Developer
Tools → Actions, chọn loa ở trường **Thiết bị**; khi gọi bằng YAML, truyền
`device_id` trong `data` hoặc dùng `entry_id` + `serial_number`.

```yaml
action: maika.create_reminder
data:
  device_id: 0123456789abcdef0123456789abcdef
  event: "Uống thuốc"
  start_at: "2026-11-01T07:30:00+07:00"
  frequency: daily
  alert_prior: 10
  custom_tts: "Đã đến giờ uống thuốc"
```

`start_at` dùng giờ địa phương của Home Assistant; `alert_prior` tính bằng phút
(0–1440). `frequency` nhận `once`, `daily`, `weekly`, `monthly` hoặc `yearly`.
Service từ chối nhắc hẹn trong quá khứ, giới hạn độ dài nội dung và luôn kiểm
tra reminder ID thuộc đúng loa trước khi sửa, xóa hoặc tắt nhắc.

```yaml
action: maika.set_reminder_enabled
target:
  device_id: 0123456789abcdef0123456789abcdef
data:
  reminder_id: 42
  enabled: false
```

`maika.delete_reminders` nhận `reminder_ids` (một hoặc nhiều ID).
`maika.mute_reminders` nhận thêm `mute_days` theo định dạng `YYYY-MM-DD`.
`maika.update_reminder` chỉ gửi các trường được truyền, nên có thể đổi giờ, tần
suất, nội dung, lời đọc hoặc trạng thái mà không cần gửi lại toàn bộ nhắc hẹn.

## Tài liệu

- [Cài đặt và phát hành](REPOSITORY_SETUP.md)
- [Danh sách entity](docs/ENTITIES.md)
- [Kích hoạt thương mại](docs/LICENSING.md)
- [Câu lệnh giọng nói](docs/VOICE_COMMANDS.md)
- [Bridge HASS/Assist](docs/ASSIST_BRIDGE.md)
- [Cloud cast](docs/CLOUD_CAST.md)
- [Phân tích API](docs/API_RESEARCH.md)
- [Ghi chú bảo mật chi tiết](docs/SECURITY_NOTES.md)
- [Chính sách bảo mật](SECURITY.md)

## Tương thích

- Home Assistant tối thiểu khai báo cho HACS: `2026.2.0`.
- Đã smoke test runtime trên Home Assistant `2026.2.3`.
- Đã đối chiếu API source Home Assistant `2026.8.2` ngày 2026-08-16.

## Lưu ý

- Đây là cloud API reverse-engineered, không được OLLI/MAIKA hỗ trợ chính thức.
- Endpoint hoặc schema có thể thay đổi mà không báo trước.
- Không gửi diagnostic, backup hoặc log chưa redact lên issue công khai.
- Không có APK, credential, token, serial thật hoặc SIP credential trong repository.
- Không có activation private key, admin token, license pepper hoặc database khách hàng trong repository.
- Brand icon được dùng để nhận diện integration; MAIKA và OLLI vẫn thuộc chủ sở hữu tương ứng.

## Disclaimer

MAIKA và OLLI là nhãn hiệu của chủ sở hữu tương ứng. Repository này độc lập, không liên kết, không được tài trợ và không được xác nhận bởi OLLI.
