# Phân tích APK và API MAIKA

## Phạm vi

Phân tích tĩnh và kiểm tra động có giới hạn trên gói APK/XAPK do người dùng cung cấp. Mục tiêu là tìm API cần thiết để tích hợp loa MAIKA với Home Assistant mà không dùng lệnh phá hủy hoặc thay đổi trạng thái ngoài ý muốn.

Ngày chốt kết quả: **2026-08-15**.

## Nhận dạng gói

| Thuộc tính | Giá trị |
|---|---|
| File đầu vào | `MAIKA Virtual Assistant_3.2.3.zip` |
| Package | `olli.ai.com.maika` |
| Version name | `3.2.3` |
| Version code | `170` |
| Min SDK | `24` |
| Target SDK | `36` |
| SHA256 ZIP | `26cffcbbaf5bb37c2a2cb2b3d481777b88eba31f98e33d0b07068a0104528fdc` |
| SHA256 base APK | `3cc8b19489f3274bc7f3bf14e9826605eed48bed7f402d3dbb028e5b10ddb6d7` |
| JADX | `1.5.6` |
| apktool | `3.0.3` |

Gói ZIP chứa base APK, split ABI `armeabi_v7a`, split density `mdpi`, icon và manifest bundle.

## Kiến trúc cloud tìm thấy

| Host | Vai trò trong integration |
|---|---|
| `https://users.iviet.com` | Login, danh sách loa, detail loa, cập nhật setting, danh sách giọng |
| `https://chatbot.iviet.com` | Gửi command và nhận stream event |
| `https://smarthome.iviet.com` | Linking/sync nhà thông minh; chỉ dùng trong nghiên cứu, không dùng bởi integration |
| `https://content-gateway.maika.ai` | Chat/TTS của ứng dụng; không dùng bởi integration |

Tất cả kết nối trong integration dùng HTTPS thông qua shared `aiohttp` session của Home Assistant.

## Xác thực

### Login

```http
POST https://users.iviet.com/v1/auth/otp/login
Content-Type: application/json
```

Body:

```json
{
  "phone_number": "<phone>",
  "password": "<password>"
}
```

Response thành công chứa `access_token`, `refresh_token`, user `id` và `expire_time`. APK 3.2.3 không cho thấy một refresh endpoint đủ tin cậy để dùng độc lập. Integration do đó:

1. Chỉ giữ access token trong bộ nhớ.
2. Không lưu refresh token.
3. Đăng nhập lại bằng credential khi token hết hạn hoặc request nhận 401.
4. Chỉ retry authentication một lần cho mỗi request để tránh vòng lặp vô hạn.

### Hai kiểu Authorization

- REST `users.iviet.com`: `Authorization: Bearer <access_token>`.
- Chatbot `/stream` và `/connect`: `Authorization: <access_token>` không có tiền tố `Bearer`.

Đây là khác biệt quan trọng; dùng sai kiểu header sẽ nhận lỗi xác thực.

## REST speaker API

| Method | Endpoint | Trạng thái |
|---|---|---|
| `GET` | `/v1/user-device?page=1&limit=100` | Đã xác minh live |
| `GET` | `/v1/user-device/{id}` | Đã xác minh live |
| `PUT` | `/v1/user-device/{id}` | Đã xác minh live với cùng giá trị hiện tại |
| `GET` | `/v1/user/tts_speaker_voices` | Đã xác minh live |

### Setting được integration cho phép ghi

- `name`
- `calling_name`
- `address`
- `wakeword_sensitivity_level`
- `wakeword_response_type`
- `tts_voice`

Body PUT gồm `id`, `device_id` và trường thay đổi.

### Trường cố ý không cho ghi

- `status`: ý nghĩa vòng đời/activation chưa đủ chắc chắn.
- `avatarURL`: API cập nhật avatar riêng chưa được xác minh.
- SIP credential: dữ liệu bí mật, chỉ phục vụ tính năng gọi điện nội bộ.
- Mọi field không nằm trong allowlist.

## Chatbot command protocol

Command được gửi bằng:

```http
POST https://chatbot.iviet.com/stream
Content-Type: application/octet-stream
meta: <Base64 JSON>
```

`meta` sau khi Base64 decode có dạng:

```json
{
  "event": {
    "header": {
      "dialogRequestId": "<uuid>",
      "messageId": "messageId-<uuid>",
      "name": "SetVolume",
      "namespace": "SystemControl"
    },
    "payload": {
      "deviceId": "<speaker serial>",
      "volume": 50
    }
  }
}
```

Các header phụ quan trọng gồm `device-id`, `device-type`, `version-info`, `olli-session-id`, `source`, `client-version`, `user-id`, `language-code` và `Authorization` raw token.

## Command đã ánh xạ

| Chức năng | Header name | Namespace | Payload chính | Mức xác minh |
|---|---|---|---|---|
| Âm lượng | `SetVolume` | `SystemControl` | `deviceId`, `volume` | Live, gửi cùng giá trị hiện tại |
| Lấy trạng thái | `GetDeviceInfo` | `ClientInformation` | `deviceId`, `fields` | Live |
| Tắt micro | `Mute` | `Recording` | `deviceId` | Tĩnh từ APK |
| Bật micro | `Unmute` | `Recording` | `deviceId` | Tĩnh từ APK |
| Pause | `PauseCommandIssued` | `PlaybackController` | `deviceId` | Tĩnh từ APK |
| Resume | `ResumeCommandIssued` | `PlaybackController` | `deviceId` | Tĩnh từ APK |
| Next | `NextCommandIssued` | `PlaybackController` | `deviceId` | Tĩnh từ APK |
| Previous | `PreviousCommandIssued` | `PlaybackController` | `deviceId` | Tĩnh từ APK |
| Jump item | `JumpCommandIssued` | `PlaybackController` | `deviceId`, `songKey` | Tĩnh từ APK; không phải seek theo giây |
| Bắt đầu mirror hội thoại | `StartListening` | `Conversation` | `deviceId`, `type=conversation` | Tĩnh từ APK; triển khai từ `1.3.2` |
| Dừng mirror hội thoại | `StopListening` | `Conversation` | `deviceId`, `type=conversation` | Tĩnh từ APK; best-effort khi unload từ `1.3.2` |
| Restart | `Reboot` | `SystemControl` | `toDeviceId` | Tĩnh từ APK |
| Factory reset | `Reset` | `SystemControl` | `toDeviceId` | Tìm thấy nhưng cố ý không expose |

Integration chỉ triển khai các command không phá hủy. `Reset` hoàn toàn không có entity/service.

## Event stream `/connect`

```http
GET https://chatbot.iviet.com/connect
```

Response là stream dài hạn với frame:

```text
$START_JSON
{...JSON...}
$END_JSON
```

Integration:

- Dùng incremental UTF-8 decoder để không làm hỏng tiếng Việt khi byte multibyte bị chia giữa hai chunk.
- Giữ buffer tối đa 1 MiB.
- Tự reconnect với exponential backoff 1–60 giây.
- Tự login lại khi stream nhận 401.
- Hủy task và waiter đúng lúc unload config entry.

### `DeviceInfo`

`GetDeviceInfo` yêu cầu các field:

```text
current_playback,volume,latest_playlist,device_id,mute
```

Cloud trả directive `ClientInformation/DeviceInfo`; integration merge dữ liệu này với REST detail để có volume, mute và playback gần thời gian thực.

### `speakerConversationResponse`

APK xử lý directive có `header.type = speakerConversationResponse`. `HeaderDirective` chứa `rawSpeech`, `sessionId`, `messageId` và metadata khác. Đây là điểm vào của sensor câu lệnh và rule entity Home Assistant.

Rà soát bổ sung ngày **2026-08-16** tìm thấy bước đăng ký còn thiếu trong bản `1.3.1`: khi mở màn hình lịch sử hội thoại của loa, APK gửi `Conversation/StartListening` với `deviceId` của loa và `type = conversation`; khi rời màn hình, APK gửi `StopListening`. Bản `1.5.0` gửi `StartListening` cho từng loa khi voice sensor/rule được bật, đăng ký lại theo từng thế hệ `/connect` và dừng best-effort lúc unload.

Parser `1.3.2` cũng chấp nhận directive nằm trực tiếp ở root hoặc trong wrapper `directive`, `event`, `message`, `response`, `data`. Telemetry chỉ lưu loại frame và các trường header giới hạn 128 ký tự; raw payload, token, credential và serial không được đưa vào sensor chẩn đoán.

Integration chỉ xử lý `rawSpeech` khi:

1. Sensor/rule câu lệnh được bật thủ công.
2. Type đúng `speakerConversationResponse`.
3. Nội dung câu nói là chuỗi không rỗng.
4. Message chưa được xử lý trong cửa sổ dedupe 5 phút.

Câu không khớp rule vẫn cập nhật sensor nhưng không gọi service entity hoặc gửi lệnh audio tới loa.

## Nghiên cứu TTS

APK có hai đường TTS đáng chú ý:

1. `POST https://content-gateway.maika.ai/api/command/speak` với `SpeakRequest`; response body được ứng dụng tiêu thụ như audio.
2. `TextToSpeech/StreamAudio` qua chatbot với payload `text`, `encodeFormat`, `language`, `voiceCode` và tùy chọn `deviceId`.

Kiểm tra ngày 2026-08-15 cho thấy `StreamAudio` trả HTTP 200 với body binary/non-JSON trực tiếp cho HTTP client và không quan sát thấy directive mới trên session `/connect` trong 12 giây. Điều này phù hợp với code APK dùng response làm audio preview trong ứng dụng.

Endpoint TTS này vẫn không được dùng để phát trực tiếp trên loa vì response là audio dành cho HTTP client. Thay vào đó, nghiên cứu tiếp theo tìm thấy protocol media handover riêng của ứng dụng.

## Cloud media handover

APK 3.2.3 có lệnh cast từ ứng dụng điện thoại tới loa vật lý:

- Outer header: `CommandHandOver`, namespace `SystemControl`.
- Nested event header: `Play`, namespace `AudioPlayer`.
- `fromDeviceId`: device/client ID của ứng dụng.
- `toDeviceId`: danh sách serial loa được chọn.
- `mediaCard`: `format`, `title`, URL trực tiếp và media `type`.
- `mediaOffset`: offset mili giây.

Call site audio tạo `MediaCard`, giữ `streamFormat` động do message cloud cung cấp và đặt fallback `format = AUDIO_MPEG` khi chuỗi này rỗng, rồi gửi `MetaStreamCastingMediaRequest` bằng cùng sender `/stream` với command hiện có. Khi không kế thừa một media message cũ, app tự tạo `dialogRequestId` và `messageId` mới.

Sender APK nhận `ResponseBody` nhưng không parse nội dung khi request thành công. Client Python vì vậy chỉ dùng HTTP status và trường JSON `status=false` nếu body tình cờ là JSON; body 2xx dạng text/binary được coi là acknowledgement hợp lệ.

Integration `1.1.0` ánh xạ đường này thành `media_player.play_media` opt-in:

1. `fromDeviceId` dùng config-entry client ID hiện có.
2. `toDeviceId` luôn là list chỉ chứa serial của entity được gọi.
3. Payload cố định `type = audio`, `format = AUDIO_MPEG`, offset `0`.
4. Home Assistant media source được resolve trước khi gửi.
5. Chỉ URL HTTP(S) hợp lệ được chấp nhận; không expose raw command.

Rà soát bổ sung ngày 2026-08-16 xác nhận APK không chứa playback command `Stop` hoặc seek theo mili giây. Enum chỉ có pause, resume, next, previous và `JumpCommandIssued`; jump nhận `songKey`, nên integration không ánh xạ nó thành `media_player.seek`. Bản `1.2.0` chấp nhận MIME MP4/AAC nhưng vẫn dùng fallback `AUDIO_MPEG` đã xác minh để firmware tự nhận dạng nội dung URL.

Schema đã được xác minh tĩnh từ APK nhưng chưa được xác nhận bằng phát âm thanh trên loa vật lý trong bản bàn giao này. Do đó feature mặc định tắt và được ghi rõ là thử nghiệm.

## Smart-home linking

APK mới và APK lịch sử 2.5.0 lấy danh sách partner/OAuth hoàn toàn từ backend `smarthome.iviet.com`; không có cấu hình Home Assistant cố định trong app.

Trên tài khoản test tại thời điểm phân tích:

- Các biến thể API partner v1 đến v1.4 không trả provider HASS/Home Assistant.
- `linking/status?partner=HASS` có thể trả linked do dấu vết lịch sử.
- `intent/sync` vẫn trả danh sách thiết bị rỗng.
- Không thực hiện unlink để tránh thay đổi tài khoản.

Kết luận: custom integration/add-on cục bộ không thể tự thêm provider HASS vào inventory MAIKA. Việc này cần backend OLLI mở lại provider, OAuth redirect/callback và adapter sync/control tương ứng.

## Dữ liệu detail và quyết định entity

REST detail còn chứa các nhóm dữ liệu như SIP, profile/persona, metadata, local media, TSSV config và cấu hình nội bộ. Chúng không được biến thành entity vì một hoặc nhiều lý do:

- Bí mật hoặc nhận dạng cá nhân.
- Không có ngữ nghĩa ổn định.
- Là object lớn/opaque, không phù hợp state model của Home Assistant.
- Trùng với device registry hoặc entity an toàn khác.

Danh sách 27 entity an toàn/hữu ích nằm trong `docs/ENTITIES.md`.

## Ma trận xác minh

| Hạng mục | Kết quả |
|---|---|
| SHA256 và bundle manifest | Pass |
| Login test account | Pass |
| List/detail/voice REST | Pass |
| `/connect` session | Pass |
| `GetDeviceInfo` live | Pass |
| `SetVolume` cùng giá trị | Pass, không đổi âm lượng |
| PUT wakeword sensitivity cùng giá trị | Pass, không đổi setting |
| Parser frame JSON | Pass |
| Parser prefix Assist | Pass, gồm dấu câu/không dấu |
| Python compile | Pass |
| JSON validation | Pass |
| Ruff lint/format | Pass |
| HA loader 2026.2.3 | Pass |
| 27 entity smoke test 2026.2.3 | Pass |
| Đối chiếu source HA 2026.8.1 | Pass |
| `CommandHandOver` media cast trong APK | Pass, xác minh tĩnh |
| `media_player.play_media` payload/build | Pass, kiểm thử local không gửi cloud |
| Cloud cast phát trên loa vật lý | Chưa xác minh |
| Voice command vật lý → Assist | Chưa xác minh |
| Assist response → loa MAIKA | Không triển khai |

## Nguồn chính

- APK `MAIKA Virtual Assistant 3.2.3` do người dùng cung cấp.
- APK lịch sử 2.5.0 dùng để so sánh cơ chế partner.
- Hướng dẫn nhà thông minh OLLI: `https://olli.vn/pages/huong-dan-ket-noi-nha-thong-minh`
- Bài cập nhật MAIKA 2022: `https://blog.olli.vn/2022/05/27/ban-cap-nhat-mung-sinh-nhat-maika-2022/`
- Home Assistant config flow: `https://developers.home-assistant.io/docs/config_entries_config_flow_handler/`
- Home Assistant fetching data: `https://developers.home-assistant.io/docs/integration_fetching_data/`
- Home Assistant entity model: `https://developers.home-assistant.io/docs/core/entity/`
- Home Assistant source tag kiểm tra: `https://github.com/home-assistant/core/tree/2026.8.1`

## Cảnh báo bảo trì

Các endpoint không có tài liệu công khai ổn định. Nếu MAIKA đổi version app, host, header hoặc JSON schema, cần decompile lại APK mới, so sánh protocol và kiểm thử bằng lệnh không phá hủy trước khi nâng version integration.
