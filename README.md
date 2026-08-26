# MAIKA Speaker for Home Assistant

[![Validate](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/trankhanhduy2929-beep/loa-maika-home-assistant)](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)


Custom integration **không chính thức** để kết nối loa MAIKA với Home Assistant qua cloud MAIKA.
Bản phát hành hiện tại: **v1.8.1**.

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
- Duyệt các nguồn audio Home Assistant trực tiếp từ giao diện media player.
- Tắt hoặc bật lại micro vật lý.
- Cấu hình độ nhạy wake word, phản hồi wake word và giọng TTS.
- Đổi tên loa, tên gọi và địa chỉ.
- Theo dõi online, Wi-Fi, firmware, bảo hành, playback và các thông tin chẩn đoán.
- Tự tìm loa qua stream cloud nếu API danh sách thiết bị MAIKA tạm trả lỗi 5xx.
- Restart an toàn; không expose factory reset.
- Sensor câu nói mới nhất và rule toàn câu để điều khiển đèn, quạt, rèm, điều
  hòa, media, scene, script, robot hút bụi và helper Home Assistant, mặc định tắt.

## Cài bằng HACS

Repository này hỗ trợ HACS custom repository. Nếu không dùng nút cài nhanh ở trên,
thêm thủ công theo bốn bước:

1. Mở **HACS → Integrations → ⋮ → Custom repositories**.
2. Nhập `https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant`.
3. Chọn category **Integration**, bấm **Add**, rồi chọn **Download**.
4. Restart Home Assistant và thêm integration **MAIKA Speaker**.

## Cài thủ công

Tải `maika-manual.zip` từ GitHub Release, giải nén vào `/config` và kiểm tra:

```text
/config/custom_components/maika/manifest.json
```

Sau đó restart Home Assistant.

## File phát hành v1.8.1

- `maika.zip`: asset chuẩn để HACS tự tải.
- `maika-v1.8.1-hacs.zip`: bản HACS có tên kèm version để lưu trữ/bàn giao.
- `maika-manual.zip` và `maika-v1.8.1-manual.zip`: cài thủ công vào `/config`.
- `SHA256SUMS.txt`: checksum SHA-256 của toàn bộ ZIP cài đặt.
- `loa-maika-home-assistant-v1.8.1-github-source.zip`: source sạch để bàn giao.

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

## Câu lệnh cố định từ loa

Trong **Devices & services → MAIKA Speaker → Configure**:

1. Bật **Sensor câu lệnh mới nhất và rule điều khiển**.
2. Nhập mỗi rule theo dạng `câu lệnh | entity_id | action`; thêm cột JSON thứ tư
   khi cần độ sáng, nhiệt độ, phần trăm quạt, vị trí rèm hoặc âm lượng.
3. Lưu để integration reload.

Ví dụ:

```text
bật đèn phòng khách | light.den_phong_khach | turn_on
bật đèn 70 phần trăm | light.den_phong_khach | turn_on | {"brightness_pct":70}
mở rèm một nửa | cover.rem_phong_khach | set_cover_position | {"position":50}
đặt điều hòa 26 độ | climate.may_lanh | set_temperature | {"temperature":26}
quạt mức 60 | fan.quat_phong_khach | set_percentage | {"percentage":60}
chạy cảnh đi ngủ | scene.di_ngu | turn_on
```

Rule hỗ trợ nhiều domain phổ biến với allowlist action/field riêng; cú pháp ba cột
cũ vẫn giữ nguyên. JSON không thể đổi target hoặc gọi service hệ thống. Câu nói
phải khớp toàn bộ sau khi bỏ hoa/thường, dấu tiếng Việt, khoảng trắng thừa và
dấu câu; câu có thêm từ sẽ không chạy. Xem bảng action và ví dụ đầy đủ tại
[Câu lệnh giọng nói](docs/VOICE_COMMANDS.md).

Nếu thiết bị không chạy, mở entity **Câu lệnh giọng nói mới nhất** trong Developer Tools → States. `stream_connected` phải là `true`, `voice_subscription_status` phải là `subscribed`, `voice_subscription_count` phải bằng `voice_subscription_target_count` và `stream_frame_count` phải tăng sau khi reload. Sau khi nói, `last_stream_frame_type` cần thành `speakerConversationResponse`; khi rule khớp, `result` phải là `executed`. Integration báo rõ `entity_not_found`, `entity_unavailable` hoặc `service_not_supported` thay vì báo thành công giả.

### Âm phản hồi custom không bị chèn xuống dưới

Từ bản `1.5.0`, có thể phát một file MP3 ngắn để thay thế best-effort câu báo sai của MAIKA:

1. Bật **Cast âm thanh cloud thử nghiệm**.
2. Bật **Sensor câu lệnh mới nhất và rule điều khiển**.
3. Tại **Nguồn âm báo thành công**, chọn **MP3 MAIKA tích hợp** để dùng file
   `/mp3/maika.mp3` công khai trên portal, **URL MP3 tùy chỉnh** để giữ file
   riêng trong HASS/Internet, hoặc **Tắt**.
4. Chỉ khi chọn URL tùy chỉnh mới cần điền **URL MP3 thành công tùy chỉnh**.
5. Nếu config entry có nhiều loa, chọn loa phát âm báo. Với đúng một loa,
   integration tự chọn.
6. Tại **Thời điểm phát âm báo**, giữ **Ưu tiên: che giọng mặc định** (mặc định).
   Chế độ này gửi MP3 ngay khi rule hợp lệ và dùng lại mã hội thoại của câu nói.
   Nếu muốn giữ hành vi cũ, chọn **Sau khi HASS thành công**.
7. Lưu để integration reload.

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

Trong **Devices & services → MAIKA Speaker → Configure**, bật **Cast âm thanh cloud thử nghiệm** rồi reload integration. Entity loa sẽ có thêm feature `PLAY_MEDIA` và `BROWSE_MEDIA`.

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

URL sau khi Home Assistant resolve, kể cả query token tạm nếu có, được gửi tới cloud MAIKA và loa phải truy cập được URL đó. Bản `1.2.0` chấp nhận MP3/MPEG và MP4/AAC, gồm MIME `audio/mp4` thường gặp từ TTS. Cờ `announce=true` được xử lý theo kiểu thay thế nội dung đang phát và không tự khôi phục nội dung cũ. Cloud cast không hỗ trợ queue `add/next`, stop thật, seek theo giây, video hay URL có username/password. Xem [Cloud cast](docs/CLOUD_CAST.md).

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
