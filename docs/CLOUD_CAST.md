# Cloud cast âm thanh tới loa MAIKA

## Trạng thái

Từ phiên bản `1.1.0`, integration có feature `media_player.play_media` thử nghiệm, mặc định tắt. Feature này dùng lệnh cast thật của ứng dụng MAIKA Android 3.2.3 thay vì Bluetooth hoặc giả lập nút resume. Phiên bản `1.1.1` cho phép cờ `announce=true`; phiên bản `1.2.0` thêm MP4/AAC, duyệt media source và mute âm lượng đầu ra; phiên bản `1.5.0` dùng cùng đường cast để phát một URL MP3 cố định sau rule HASS thành công; phiên bản `1.5.1` gửi phản hồi tự động trực tiếp qua MAIKA client để bỏ độ trễ service media player trung gian.

Schema đã được xác minh bằng phân tích tĩnh APK. Bản build này chưa phát thử trên loa vật lý trong môi trường bàn giao, vì vậy cần bật có chủ đích và thử bằng clip ngắn trước khi dùng trong automation quan trọng.

## Protocol tìm thấy trong APK

Ứng dụng gửi request sau tới `POST https://chatbot.iviet.com/stream`, trong header `meta` là JSON được Base64:

```json
{
  "event": {
    "header": {
      "messageId": "messageId-<uuid>",
      "name": "CommandHandOver",
      "namespace": "SystemControl"
    },
    "payload": {
      "fromDeviceId": "<client id của integration>",
      "messageInfo": {
        "eventHeader": {
          "dialogRequestId": "<uuid>",
          "messageId": "messageId-<uuid>",
          "name": "Play",
          "namespace": "AudioPlayer"
        },
        "mediaCard": {
          "format": "AUDIO_MPEG",
          "title": "<title>",
          "url": "<audio URL>",
          "type": "audio"
        },
        "mediaOffset": 0
      },
      "toDeviceId": ["<serial của đúng loa>"]
    }
  }
}
```

APK dùng `ConstApp` device ID làm `fromDeviceId`, danh sách serial loa được chọn làm `toDeviceId`, rồi gửi object `MetaStreamCastingMediaRequest` qua cùng sender `/stream` với các command hiện có.

## Bật tính năng

1. Mở **Settings → Devices & services → MAIKA Speaker → Configure**.
2. Bật **Cast âm thanh cloud thử nghiệm**.
3. Lưu tùy chọn; config entry sẽ reload.
4. Kiểm tra entity loa có feature `PLAY_MEDIA` và `BROWSE_MEDIA`.

## Phát URL MP3

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

Các `media_content_type` được chấp nhận:

- `audio/mpeg`
- `audio/mp3`
- `audio/x-mpeg`
- `audio/mp4`
- `audio/aac`
- `audio/m4a`
- `audio/x-m4a`
- `audio/x-aac`
- `audio/mp4a-latm`
- `audio`
- `music`
- `url`

APK nhận `streamFormat` động từ nội dung cloud nhưng chỉ chứa literal fallback `AUDIO_MPEG`. Integration dùng fallback này cho cả MP3/MPEG và MP4/AAC để firmware tự nhận dạng URL. WAV, FLAC, OGG, Opus, WebM và video chưa được quảng bá là hỗ trợ.

Khi cloud cast bật, entity có thể duyệt các nguồn audio Home Assistant bằng `BROWSE_MEDIA`. Mute trên media player là mute âm thanh đầu ra bằng cách đặt volume về 0 và khôi phục mức trước đó; nó độc lập với switch tắt micro vật lý.

## Media source và TTS Home Assistant

Integration resolve `media-source://` bằng API media source chính thức rồi dùng `async_process_play_media_url` để đổi đường dẫn Home Assistant thành URL phát được và ký URL khi cần.

Ví dụ dùng media source:

```yaml
action: media_player.play_media
target:
  entity_id: media_player.maika
data:
  media:
    media_content_id: "media-source://media_source/local/chuong.mp3"
    media_content_type: "audio/mpeg"
    metadata: {}
```

Ví dụ dùng một entity TTS đã cấu hình:

```yaml
action: tts.speak
target:
  entity_id: tts.google_translate_vi_com
data:
  media_player_entity_id: media_player.maika
  message: "Xin chào từ Home Assistant"
```

TTS hoạt động với provider tạo MP3/MPEG hoặc MP4/AAC nếu URL cuối cùng có thể được loa truy cập. Home Assistant gọi media player với `announce=true`; integration chấp nhận cờ này nhưng protocol cast MAIKA chỉ có lệnh `Play`, nên clip TTS thay thế nội dung đang phát và không tự phát lại nội dung trước đó.

### Âm báo thành công sau rule HASS

Tùy chọn URL MP3 không cố hủy hội thoại trước khi biết kết quả điều khiển. Integration gọi service entity với `blocking=true`; chỉ khi lời gọi hoàn tất không exception mới gửi trực tiếp `CommandHandOver/AudioPlayer/Play` tới đúng serial loa với URL đã cấu hình và MIME cố định `audio/mpeg`. Nếu rule không khớp hoặc service HASS lỗi, không có `Pause`, `Play` hay command audio nào được gửi, nên thiết bị native của MAIKA tiếp tục hoạt động bình thường.

Để trống URL là tắt phản hồi. Nếu config entry chỉ có một media player MAIKA, loa được chọn tự động; khi có nhiều loa, người dùng chọn một loa cố định. URL có thể là `/local/*.mp3` qua địa chỉ HTTP(S) đầy đủ của Home Assistant, miễn là loa truy cập được địa chỉ đó.

Để phản hồi nhanh nhất, dùng file MP3 mono rất ngắn, dung lượng nhỏ, không redirect và ưu tiên URL LAN trực tiếp `http://<IP_HASS>:8123/local/...` nếu loa cùng mạng. URL HTTPS qua DuckDNS/reverse proxy có thêm DNS, TLS và có thể hairpin qua Internet nên thường bắt đầu phát chậm hơn.

APK 3.2.3 không cung cấp command hủy riêng cho câu trả lời conversation. `AudioPlayer/Play` trong `SystemControl/CommandHandOver` chỉ có thể thay nội dung đang phát theo best-effort. Vì vậy tính năng có thể che hoặc cắt câu “không có thiết bị”, nhưng không đảm bảo không nghe thấy phần đầu của câu đó.

## Điều kiện mạng

- URL public HTTPS thường dễ truy cập nhất.
- URL local `http://<IP-HASS>:8123/...` chỉ hoạt động khi loa truy cập được Home Assistant trong cùng mạng.
- Nếu Home Assistant tạo URL bằng hostname mà loa không phân giải được, hãy cấu hình **Internal URL** phù hợp trong Network settings.
- URL có query token hoặc chữ ký tạm được gửi nguyên vẹn trong metadata tới cloud MAIKA.
- Không dùng URL chứa bí mật dài hạn. Ưu tiên URL tạm, file ngắn và quyền tối thiểu.

## Giới hạn và safeguard

- Feature mặc định tắt.
- Chỉ chấp nhận URL `http://` hoặc `https://` có hostname; chặn localhost, loopback, link-local, multicast, unspecified và địa chỉ reserved dạng IP literal.
- Từ chối URL chứa username/password, ký tự điều khiển hoặc dài hơn 8192 ký tự.
- Chỉ target serial của entity được gọi; không có service chọn danh sách serial tùy ý.
- Không expose raw JSON hoặc raw MAIKA command.
- Không hỗ trợ `enqueue=add` hoặc `enqueue=next`.
- Chấp nhận `announce=true` để phát TTS theo kiểu thay thế; không có native announcement, ducking hoặc tự khôi phục nội dung trước đó.
- Không quảng bá stop, seek theo giây hoặc power vì APK chỉ có pause/resume/next/previous và jump theo `songKey`.
- Không upload/proxy file qua integration; loa tự lấy URL.
- HTTP 2xx chỉ xác nhận cloud nhận request, không đảm bảo firmware đã phát thành công.

## Checklist test loa thật

1. Đặt volume loa thấp.
2. Dùng một file MP3 HTTPS ngắn, không lặp.
3. Gọi `media_player.play_media` từ Developer Tools.
4. Kiểm tra loa phát, state chuyển playing và `DeviceInfo` cập nhật.
5. Sau đó thử `/local/*.mp3`, media source và TTS theo thứ tự.
6. Nếu không phát, kiểm tra URL từ một thiết bị khác trong cùng Wi-Fi với loa trước khi báo lỗi protocol.

Không đưa credential, access token, URL đã ký còn hiệu lực hoặc serial thật vào issue công khai.
