# Bảng entity MAIKA trong Home Assistant

Integration tạo **27 entity cho mỗi loa** đã có trong tài khoản tại lúc config entry được load. Khi bật tính năng câu lệnh giọng nói, integration tạo thêm **1 sensor cấp tài khoản** không gắn sai vào một loa cụ thể.

Entity ID thực tế có thể khác; cột `Key` là khóa unique nội bộ/translation key, không phải cam kết entity ID.

## Media player — 1 entity

| Key | Chức năng | Nguồn/API | Ghi chú |
|---|---|---|---|
| `media_player` | Trạng thái, metadata, volume, play, pause, next, previous, cloud cast tùy chọn | REST detail + `DeviceInfo`; command `/stream` | Device class `speaker`; command chỉ available khi loa online |

### Feature của media player

- `VOLUME_SET`: quy đổi Home Assistant `0.0..1.0` sang MAIKA `0..100`, bước mặc định 5%.
- `VOLUME_MUTE`: mute đầu ra bằng volume 0 và khôi phục mức trước đó; không phải switch micro vật lý.
- `PLAY`: `ResumeCommandIssued`.
- `PAUSE`: `PauseCommandIssued`.
- `NEXT_TRACK`: `NextCommandIssued`.
- `PREVIOUS_TRACK`: `PreviousCommandIssued`.
- `PLAY_MEDIA`: chỉ bật khi option `enable_experimental_cloud_cast` được bật; gửi `CommandHandOver/SystemControl` chứa `Play/AudioPlayer` và `mediaCard` tới đúng serial loa.
- `BROWSE_MEDIA`: chỉ bật cùng cloud cast; duyệt các nguồn audio từ Home Assistant media source.
- Metadata khi cloud cung cấp: content ID/URL, title, artist/narrator, album, playlist, artwork, media type và position.

Cloud cast hỗ trợ URL HTTP(S), đường dẫn Home Assistant và `media-source://` cho MP3/MPEG hoặc MP4/AAC. Cờ `announce=true` dùng bởi `tts.speak` được chấp nhận theo kiểu thay thế nội dung đang phát; không hỗ trợ queue `add/next`, stop thật, seek theo giây, native announcement có khôi phục, video hoặc URL có username/password. Xem `docs/CLOUD_CAST.md`.

## Switch — 1 entity

| Key | Category | Chức năng | API |
|---|---|---|---|
| `microphone_mute` | Config | ON = tắt micro; OFF = bật micro | `Mute` / `Unmute`, namespace `Recording` |

State được lấy từ `DeviceInfo.mute`; nếu chưa nhận live data, entity đánh dấu assumed state.

## Select — 3 entity

| Key | Category | Giá trị | REST field |
|---|---|---|---|
| `wakeword_sensitivity` | Config | `low`, `medium`, `high` | `wakeword_sensitivity_level` |
| `wakeword_response` | Config | silent, ringtone, default | `wakeword_response_type` |
| `tts_voice` | Config | Danh sách code lấy động từ cloud | `tts_voice` |

Giá trị TTS không nằm trong danh sách hiện tại vẫn được giữ làm option để entity không thành invalid khi backend thêm voice mới.

## Text setting — 3 entity

| Key | Category | Chức năng | REST field |
|---|---|---|---|
| `speaker_name` | Config | Tên thiết bị | `name` |
| `calling_name` | Config | Tên gọi của loa/người dùng | `calling_name` |
| `address` | Config | Địa chỉ dùng bởi dịch vụ MAIKA | `address` |

Giới hạn text là 0–255 ký tự. `address` là dữ liệu riêng tư; chỉ nhập khi thật sự cần.

## Sensor — 11 entity

| Key | Category | State | Nguồn |
|---|---|---|---|
| `volume` | Thường | Phần trăm `0..100` | `volume` REST/live |
| `firmware_version` | Diagnostic | Phiên bản firmware | `firmware_version` |
| `firmware_update_status` | Diagnostic | Trạng thái update do cloud trả | `firmware_update_status` |
| `model` | Diagnostic | Model loa | `model` |
| `serial_number` | Diagnostic | Serial/device ID | `device_id` |
| `wifi_ssid` | Diagnostic | SSID đang kết nối, fallback Wi-Fi đầu tiên | `wifi[]` |
| `activated_at` | Diagnostic | Timestamp kích hoạt | `activated_at` |
| `warranty_expire_date` | Diagnostic | Timestamp hết bảo hành | `warranty_expire_date` |
| `room` | Diagnostic | Tên phòng do MAIKA lưu | `room` |
| `default_language` | Diagnostic | Ngôn ngữ mặc định | `default_language` |
| `playback_status` | Thường | start/resume/paused/finished hoặc giá trị backend | `current_playback.status` |

Sensor volume được giữ song song với thuộc tính `media_player.volume_level` để tiện lịch sử, template và automation theo phần trăm nguyên.

## Sensor câu lệnh cấp tài khoản — tùy chọn

| Key | State | Thuộc tính chính | Nguồn |
|---|---|---|---|
| `last_voice_command` | Câu nói mới nhất, tối đa 255 ký tự | `received_at`, `normalized`, `matched`, `matched_phrase`, `target_entity_id`, `action`, `service`, `service_data`, `executed`, `result`, `error` | `/connect` → `speakerConversationResponse.rawSpeech` |

Sensor chỉ được tạo khi option `enable_voice_command_sensor` bật. Frame hội thoại hiện chưa có serial loa đủ tin cậy, vì vậy sensor dùng unique ID theo config entry và không gắn vào một device loa cụ thể.

State và attributes có thể được Home Assistant Recorder lưu vào lịch sử. Nếu không muốn lưu câu nói, tắt tính năng hoặc exclude entity sensor này trong cấu hình Recorder. Xem `docs/VOICE_COMMANDS.md`.

## Binary sensor — 6 entity

| Key | Category | ON khi | Nguồn |
|---|---|---|---|
| `online` | Thường | Cloud báo loa online | `online` |
| `wifi_connected` | Thường | Có phần tử `wifi[].connected = true` | `wifi[]` |
| `available_to_call` | Thường | Loa sẵn sàng nhận cuộc gọi | `available_to_call` |
| `favorite` | Thường | Thiết bị được đánh dấu yêu thích | `is_favorite` |
| `device_active` | Diagnostic | `status == 1` | `status` read-only |
| `warranty_active` | Diagnostic | Ngày hết bảo hành lớn hơn hiện tại | `warranty_expire_date` |

Parser boolean chấp nhận boolean, `0/1` và chuỗi boolean phổ biến; dữ liệu không nhận dạng được trả `unknown` thay vì đoán sai.

## Button — 2 entity

| Key | Category | Hành động | Ghi chú |
|---|---|---|---|
| `restart` | Config | Gửi `Reboot/SystemControl` | Không tự xác nhận; dùng cẩn thận |
| `refresh_status` | Diagnostic | Gọi `GetDeviceInfo` rồi poll REST | Không thay đổi cấu hình |

## Entity không tạo và lý do

| Dữ liệu/lệnh | Quyết định |
|---|---|
| `Reset/SystemControl` | Không expose vì factory reset phá hủy cấu hình |
| `sip_id`, `sip_auth_user`, `sip_password` | Không expose vì là credential |
| `avatarURL` write | Không expose vì endpoint cập nhật chưa được xác minh |
| `status` write | Chỉ đọc qua `device_active`; không cho ghi vì ngữ nghĩa activation chưa rõ |
| `user_profile`, `persona`, `settings`, `meta_data`, `local_media_info`, `tssv_config` | Object riêng tư/opaque, không phù hợp entity state |
| `user_id`, internal database ID | Chỉ dùng nội bộ, không có giá trị điều khiển |
| Lệnh arbitrary/raw command | Không expose để tránh bypass allowlist an toàn |
| Entity TTS riêng của MAIKA | Không tạo; có thể dùng service `tts.speak` của Home Assistant qua `media_player` khi cloud cast được bật |

## Nhiều loa và loa thêm mới

- Mỗi serial tạo một Home Assistant device riêng với identifier `(maika, serial)`.
- Tất cả entity gắn vào device tương ứng.
- Nếu thêm loa mới sau khi integration đang chạy, reload config entry hoặc restart Home Assistant để tạo bộ entity cho loa mới.
- Polling vẫn cập nhật dữ liệu các loa đã được tạo.
