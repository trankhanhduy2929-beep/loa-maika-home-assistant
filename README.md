# MAIKA Speaker for Home Assistant

[![Validate](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/trankhanhduy2929-beep/loa-maika-home-assistant)](https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)


Custom integration **không chính thức** để kết nối loa MAIKA với Home Assistant qua cloud MAIKA.

Từ bản `1.6.0`, integration dùng activation server riêng để cấp quyền cho từng
Home Assistant. Mã cài đặt được tạo từ hash của Home Assistant instance ID,
không dùng MAC address và không gửi credential MAIKA tới activation server.

## Tính năng

- Tạo **27 entity cho mỗi loa**.
- Điều khiển volume, mute âm lượng đầu ra, play/pause, next/previous.
- Cast MP3/MPEG và MP4/AAC từ URL, media source hoặc TTS Home Assistant tới loa qua cloud MAIKA (thử nghiệm, mặc định tắt).
- Có thể phát một file MP3 cố định trên loa chỉ sau khi rule giọng nói Home Assistant chạy thành công; chỉ cần điền URL và lệnh MAIKA khác không bị chặn.
- Duyệt các nguồn audio Home Assistant trực tiếp từ giao diện media player.
- Tắt hoặc bật lại micro vật lý.
- Cấu hình độ nhạy wake word, phản hồi wake word và giọng TTS.
- Đổi tên loa, tên gọi và địa chỉ.
- Theo dõi online, Wi-Fi, firmware, bảo hành, playback và các thông tin chẩn đoán.
- Restart an toàn; không expose factory reset.
- Sensor câu nói mới nhất và rule toàn câu để bật/tắt/toggle entity Home Assistant, mặc định tắt.

## Cài bằng HACS

Repository này hỗ trợ HACS custom repository.

Repository GitHub phải ở chế độ **Public** để HACS đọc metadata và release asset.

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=trankhanhduy2929-beep&repository=loa-maika-home-assistant&category=integration)

Hoặc thêm thủ công:

1. Mở **HACS → Integrations**.
2. Chọn menu → **Custom repositories**.
3. Nhập `https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant`.
4. Chọn category **Integration**.
5. Cài **MAIKA Speaker** và restart Home Assistant.

## Cài thủ công

Tải `maika-manual.zip` từ GitHub Release, giải nén vào `/config` và kiểm tra:

```text
/config/custom_components/maika/manifest.json
```

Sau đó restart Home Assistant.

## Cấu hình

1. Vào **Settings → Devices & services → Add integration**.
2. Tìm **MAIKA Speaker**.
3. Nhập URL activation server do người bán cung cấp và license key.
4. Với Easy Mode, Home Assistant đầu tiên dùng key được gắn tự động và form
   chuyển thẳng sang bước tài khoản MAIKA.
5. Chỉ khi người bán bật chế độ duyệt tay, gửi mã cài đặt hiển thị trên màn
   hình rồi bấm kiểm tra lại sau khi được duyệt.
6. Nhập số điện thoại và mật khẩu tài khoản MAIKA.

Home Assistant lưu credential trong config entry để đăng nhập lại. Integration chỉ giữ access token trong bộ nhớ và không dùng/lưu refresh token.

Activation server chỉ nhận installation hash, license metadata và phiên bản;
không nhận số điện thoại/mật khẩu MAIKA. Lease ký số có thời hạn 48 giờ và cho
phép chạy offline thêm tối đa bảy ngày khi server tạm mất kết nối. Xem
[Kích hoạt thương mại](docs/LICENSING.md).

## Câu lệnh cố định từ loa

Trong **Devices & services → MAIKA Speaker → Configure**:

1. Bật **Sensor câu lệnh mới nhất và rule điều khiển**.
2. Nhập mỗi rule trên một dòng theo dạng `câu lệnh | entity_id | action`.
3. Lưu để integration reload.

Ví dụ:

```text
bật đèn phòng khách | light.den_phong_khach | turn_on
tắt đèn phòng khách | light.den_phong_khach | turn_off
đổi trạng thái quạt | fan.quat_phong_khach | toggle
```

Chỉ hỗ trợ `turn_on`, `turn_off`, `toggle`. Câu nói phải khớp toàn bộ sau khi bỏ hoa/thường, dấu tiếng Việt, khoảng trắng thừa và dấu câu; câu có thêm từ sẽ không chạy. Sensor là entity cấp tài khoản vì frame cloud hiện không cung cấp serial loa đáng tin cậy. Nội dung sensor có thể được Recorder lưu vào lịch sử; xem [Câu lệnh giọng nói](docs/VOICE_COMMANDS.md).

Nếu thiết bị không chạy, mở entity **Câu lệnh giọng nói mới nhất** trong Developer Tools → States. `stream_connected` phải là `true`, `voice_subscription_status` phải là `subscribed`, `voice_subscription_count` phải bằng `voice_subscription_target_count` và `stream_frame_count` phải tăng sau khi reload. Sau khi nói, `last_stream_frame_type` cần thành `speakerConversationResponse`; khi rule khớp, `result` phải là `executed`. Integration báo rõ `entity_not_found`, `entity_unavailable` hoặc `service_not_supported` thay vì báo thành công giả.

### Âm báo MP3 chỉ khi HASS thành công

Từ bản `1.5.0`, có thể phát một file MP3 ngắn để thay thế best-effort câu báo sai của MAIKA:

1. Bật **Cast âm thanh cloud thử nghiệm**.
2. Bật **Sensor câu lệnh mới nhất và rule điều khiển**.
3. Dán địa chỉ HTTP(S) vào **URL MP3 báo thành công**; để trống là tắt.
4. Nếu config entry có nhiều loa, chọn loa phát âm báo. Với đúng một loa, integration tự chọn và chỉ cần điền URL.
5. Lưu để integration reload.

Integration không gửi `Pause`. Chỉ sau khi service như `switch.turn_on` hoàn tất không lỗi, integration mới gửi cast `AudioPlayer/Play` với URL đã nhập và `audio/mpeg`. Câu không khớp rule, rule lỗi, entity unavailable và lệnh điều khiển thiết bị native của MAIKA không nhận lệnh audio từ tính năng này, vì vậy MAIKA vẫn nói và điều khiển bình thường. Protocol không có lệnh hủy hội thoại native nên việc thay câu “không có thiết bị” chỉ là best-effort; đôi khi có thể nghe một phần phản hồi MAIKA trước âm báo.

Từ bản `1.5.1`, đường phản hồi tự động gửi cast trực tiếp qua MAIKA client ngay sau khi action HASS thành công, bỏ một vòng service media player và bước refresh đồng bộ để giảm độ trễ. Để giảm thời gian tải file, nên dùng clip MP3 rất ngắn và URL LAN trực tiếp như `http://<IP_HASS>:8123/local/NHACCHUONG/demo.mp3` nếu loa truy cập được Home Assistant; URL DuckDNS/reverse proxy HTTPS thường chậm hơn do DNS, TLS và hairpin Internet.

Trong sensor, `success_audio_status: played` nghĩa yêu cầu play/cast đã hoàn tất không lỗi, không phải telemetry xác nhận tuyệt đối loa vật lý đã phát thành tiếng. URL cấu hình bị redact khỏi diagnostics. Xem [Câu lệnh giọng nói](docs/VOICE_COMMANDS.md).

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
