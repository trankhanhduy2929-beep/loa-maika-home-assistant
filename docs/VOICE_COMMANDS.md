# Sensor và rule câu lệnh giọng nói

## Luồng dữ liệu

Khi được bật, integration đọc câu MAIKA cloud đã nhận dạng từ:

```text
/stream: Conversation/StartListening cho từng serial loa
└── đăng ký mirror hội thoại vào client Home Assistant

/connect
└── speakerConversationResponse
    └── header.rawSpeech
```

APK MAIKA 3.2.3 gửi `StartListening` với payload `deviceId` và `type: conversation` khi người dùng mở lịch sử hội thoại của một loa. Bản `1.3.2` thực hiện bước này tự động cho mọi loa trong tài khoản, đăng ký lại sau mỗi reconnect và gửi `StopListening` best-effort khi integration unload.

Câu mới nhất được đưa vào sensor `last_voice_command`. Frame hiện không cung cấp serial loa đủ tin cậy nên đây là sensor cấp tài khoản, không gắn vào một loa cụ thể.

## Bật tính năng

1. Mở **Settings → Devices & services → MAIKA Speaker**.
2. Chọn **Configure**.
3. Bật **Sensor câu lệnh mới nhất và rule điều khiển**.
4. Nhập rule, mỗi rule một dòng.
5. Lưu để config entry reload.

Tính năng mặc định tắt. Khi bật, state sensor và attributes có thể được Home Assistant Recorder lưu vào lịch sử.

## Âm phản hồi MP3 cho rule HASS

Từ bản `1.7.2`, integration mặc định gửi MP3 theo chế độ ưu tiên ngay khi rule
đã vượt qua kiểm tra entity/service. Bản `1.7.0` đã thêm file MAIKA MP3 có sẵn
trên portal:

1. Bật **Cast âm thanh cloud thử nghiệm**.
2. Bật sensor/rule câu lệnh.
3. Chọn **Tắt**, **MP3 MAIKA tích hợp** hoặc **URL MP3 tùy chỉnh** tại trường
   **Nguồn âm báo thành công**.
4. Với MP3 tích hợp, integration dùng URL public
   `PORTAL_PUBLIC_URL/mp3/maika.mp3`; với URL tùy chỉnh, nhập URL HTTP(S) như
   các bản cũ.
5. Nếu config entry có nhiều loa, chọn media player MAIKA cần phát. Với đúng
   một loa, integration tự chọn và ẩn trường chọn loa.
6. Chọn **Ưu tiên: che giọng mặc định** hoặc **Sau khi HASS thành công** tại
   trường **Thời điểm phát âm báo**.

Luồng xử lý được giới hạn như sau:

```text
câu nói không khớp rule
└── không gửi Pause, Play hoặc lệnh audio; MAIKA xử lý bình thường

câu nói khớp nhưng kiểm tra entity/service lỗi
└── không gửi Play; MAIKA xử lý bình thường

chế độ ưu tiên và rule hợp lệ
├── gửi trực tiếp MAIKA cloud cast Play với cùng mã hội thoại
└── chạy service HASS song song và ghi kết quả thật vào sensor

chế độ sau-thành-công
└── chỉ gửi Play sau khi service HASS hoàn tất không lỗi
```

Do APK/protocol chưa có lệnh hủy riêng cho phản hồi hội thoại, integration không
thể đảm bảo tắt tuyệt đối âm báo “không có thiết bị”. Tùy mạng và cloud, người
dùng vẫn có thể nghe một phần phản hồi MAIKA trước khi file MP3 thay thế nó.
Nếu service HASS lỗi sau khi cast ưu tiên đã hoàn tất, sensor ghi
`played_before_failure`.

Bản `1.5.1` đã bỏ vòng service media player. Bản `1.7.2` tiếp tục bỏ thời gian
chờ service HASS khỏi đường cast ưu tiên và tái sử dụng mã hội thoại của frame
`speakerConversationResponse`.

Cấu hình cũ chỉ có `voice_success_audio_url` vẫn hoạt động và được tự hiểu là
nguồn tùy chỉnh. Integration không tải hoặc lưu nội dung MP3 trong Home
Assistant; loa nhận URL qua cloud MAIKA và tự tải file.

Frame cloud chưa cung cấp serial nguồn đủ tin cậy, vì vậy người dùng chọn một loa xác nhận cố định. Nếu có nhiều loa, chọn đúng loa dùng để ra các rule HASS.

## Cú pháp rule

```text
câu lệnh | entity_id | action
câu lệnh | entity_id | action | {"tham_so": gia_tri}
```

Cú pháp ba cột của các bản cũ vẫn hoạt động. Cột JSON thứ tư chỉ cần khi action
có tham số như độ sáng, nhiệt độ, phần trăm quạt, vị trí rèm hoặc âm lượng.

Ví dụ phổ biến:

```text
# Có thể dùng dòng chú thích bắt đầu bằng dấu #
bật đèn phòng khách | light.den_phong_khach | turn_on
bật đèn 70 phần trăm | light.den_phong_khach | turn_on | {"brightness_pct":70}
đèn màu đỏ | light.den_phong_khach | turn_on | {"rgb_color":[255,0,0]}
mở rèm một nửa | cover.rem_phong_khach | set_cover_position | {"position":50}
đặt điều hòa 26 độ | climate.may_lanh | set_temperature | {"temperature":26}
quạt mức 60 | fan.quat_phong_khach | set_percentage | {"percentage":60}
tivi âm lượng 30 | media_player.tivi | volume_set | {"volume_level":0.3}
chạy cảnh đi ngủ | scene.di_ngu | turn_on
bấm chuông | button.chuong | press
robot về sạc | vacuum.robot | return_to_base
chọn chế độ eco | select.che_do | select_option | {"option":"eco"}
```

Action có thể viết ngắn như `turn_on` hoặc đầy đủ như `light.turn_on`; nếu viết
đầy đủ, domain phải trùng với domain của entity. Integration luôn tự ép target về
`entity_id` trong rule.

## Thiết bị và action hỗ trợ

| Domain | Action được phép |
|---|---|
| `light` | `turn_on`, `turn_off`, `toggle`; độ sáng, transition, flash, effect, nhiệt màu, RGB/RGBW/RGBWW, HS, XY |
| `switch`, `input_boolean` | `turn_on`, `turn_off`, `toggle` |
| `camera` | `turn_on`, `turn_off`, bật/tắt phát hiện chuyển động |
| `remote` | `turn_on`, `turn_off`, `toggle`; tham số `activity` tùy chọn |
| `fan` | bật/tắt/toggle, tăng/giảm tốc độ, phần trăm, preset, hướng quay, oscillation |
| `cover` | mở/đóng/dừng/toggle, vị trí rèm, mở/đóng/dừng/toggle tilt, vị trí tilt |
| `valve` | mở/đóng/dừng/toggle, đặt vị trí |
| `climate` | bật/tắt/toggle, nhiệt độ, HVAC mode, preset, độ ẩm, fan mode, swing mode |
| `humidifier` | bật/tắt/toggle, độ ẩm, mode |
| `water_heater` | bật/tắt, nhiệt độ, away mode, operation mode |
| `media_player` | bật/tắt/toggle, play/pause/stop, bài trước/sau, âm lượng, mute, seek, source, sound mode, shuffle, repeat, clear playlist |
| `scene` | `turn_on`, transition tùy chọn |
| `script` | `turn_on`, `turn_off`, `toggle` |
| `automation` | `trigger`, `turn_on`, `turn_off`, `toggle` |
| `button`, `input_button` | `press` |
| `vacuum` | `start`, `pause`, `stop`, `return_to_base`, `clean_spot`, `locate`, tốc độ quạt |
| `lawn_mower` | `start_mowing`, `pause`, `dock` |
| `number`, `input_number` | đặt giá trị; `input_number` có thêm tăng/giảm |
| `select`, `input_select` | chọn option, đầu/cuối, tiếp theo/trước đó |
| `counter` | tăng, giảm, reset, đặt giá trị |
| `timer` | start, pause, cancel, finish, change; duration dùng `HH:MM:SS` |
| `text`, `input_text` | đặt chuỗi bằng `set_value` |
| `siren` | bật/tắt/toggle; tone, duration và volume tùy chọn |
| `lock` | chỉ `lock`; không cho mở khóa bằng voice rule |

Tên action và field phải đúng schema Home Assistant. Ví dụ:

```text
quạt quay | fan.quat | oscillate | {"oscillating":true}
điều hòa chế độ lạnh | climate.may_lanh | set_hvac_mode | {"hvac_mode":"cool"}
tắt tiếng tivi | media_player.tivi | volume_mute | {"is_volume_muted":true}
hẹn giờ 5 phút | timer.hen_gio | start | {"duration":"00:05:00"}
```

Mỗi giá trị được kiểm tra kiểu và khoảng trước khi lưu. JSON chỉ là object phẳng;
chỉ mảng màu ngắn được chấp nhận, object lồng nhau và `null` bị từ chối. Tối đa
200 rule; mỗi JSON tối đa 2.048 ký tự và 12 field.

Không thể truyền `entity_id`, target, device/area/floor, context, variables,
credential, password hoặc token trong JSON. Các service hệ thống, restart Home
Assistant, update/install, factory reset, raw command, mở khóa và alarm control
panel không nằm trong allowlist. Với logic ngoài allowlist, hãy gọi một `script`
hoặc `automation` do chính quản trị viên Home Assistant tạo.

## Quy tắc khớp câu

Rule khớp toàn bộ câu sau khi:

- Chuyển về chữ thường.
- Bỏ dấu tiếng Việt, gồm `đ` → `d`.
- Bỏ dấu câu/ký hiệu.
- Gộp khoảng trắng liên tiếp.

Ví dụ rule `bật đèn phòng khách` khớp `Bật đèn phòng khách!` và `bat den phong khach`, nhưng không khớp `Maika bật đèn phòng khách ngay`.

Hai rule trở thành giống nhau sau chuẩn hóa sẽ bị từ chối. Entity ID sai định dạng hoặc action ngoài allowlist cũng bị từ chối ngay tại form cấu hình.

## Chống chạy lặp

Cloud có thể gửi lại cùng frame. Integration tạo khóa từ message ID và câu đã chuẩn hóa, giữ trong 5 phút. Bản lặp không cập nhật sensor và không gọi service lần hai.

Nên dùng `turn_on` hoặc `turn_off` khi có thể. `toggle` vẫn an toàn trước frame lặp đã biết, nhưng hai câu nói thật sự khác message ID vẫn đảo trạng thái hai lần như mong đợi.

## Thuộc tính sensor

| Thuộc tính | Ý nghĩa |
|---|---|
| `stream_connected` | Integration đang kết nối `/connect` hay không |
| `stream_generation` | Số lần handshake stream thành công từ khi integration load |
| `stream_frame_count` | Tổng frame an toàn đã decode, gồm handshake |
| `stream_directive_count` | Số frame có directive header |
| `last_stream_frame_kind` | `connect`, `api_keys`, `directive` hoặc `unknown` |
| `last_stream_frame_type` | `header.type` gần nhất, không chứa nội dung câu nói |
| `last_stream_frame_name` | `header.name` gần nhất |
| `last_stream_frame_namespace` | `header.namespace` gần nhất |
| `last_stream_frame_at` | Thời điểm nhận frame gần nhất |
| `last_stream_frame_has_raw_speech` | Frame gần nhất có trường câu nói hay không; không chứa nội dung câu |
| `voice_subscription_status` | `subscribed`, `partial`, `failed`, `waiting_for_stream`, `no_devices` hoặc `disabled` |
| `voice_subscription_target_count` | Số loa cần đăng ký nghe |
| `voice_subscription_count` | Số loa đã đăng ký thành công trong thế hệ stream hiện tại |
| `voice_subscription_last_at` | Thời điểm thử đăng ký gần nhất |
| `voice_subscription_last_error` | Mã lỗi an toàn nếu đăng ký thất bại |
| `configured_rule_count` | Số rule hợp lệ đã nạp khi integration reload |
| `received_at` | Thời điểm integration nhận frame |
| `normalized` | Câu sau chuẩn hóa dùng để so khớp |
| `matched` | Có rule khớp hay không |
| `matched_phrase` | Câu đã cấu hình trong rule |
| `target_entity_id` | Entity đích |
| `action` | Action allowlist đã khớp, ví dụ `set_temperature` |
| `service` | Service thực tế, ví dụ `switch.turn_on` |
| `service_data` | Tham số JSON đã lọc; không chứa target/entity ID |
| `entity_state_before` | State entity trước khi gọi service |
| `entity_state_after` | State quan sát được ngay sau khi service hoàn tất |
| `executed` | Service đã hoàn tất thành công |
| `result` | `not_matched`, `pending`, `executed` hoặc `failed` |
| `error` | Tên loại lỗi nếu service thất bại |
| `success_audio_status` | `pending`, `played` hoặc `failed`; không có khi URL phản hồi để trống |
| `success_audio_error` | Mã lỗi hoặc tên loại exception an toàn nếu play/cast thất bại |

Các mã lỗi kiểm tra trước service:

- `entity_not_found`: entity ID viết sai hoặc entity chưa được load.
- `entity_unavailable`: entity đang ở state `unavailable`.
- `service_not_supported`: domain entity không đăng ký action tương ứng.

Với switch, rule đúng phải dùng domain `switch`, không phải `swtich`:

```text
bật đèn phòng khách | switch.den_phong_khach | turn_on
tắt đèn phòng khách | switch.den_phong_khach | turn_off
```

## Kiểm tra khi không chạy

Mở **Developer Tools → States**, chọn entity **Câu lệnh giọng nói mới nhất**, nói lại câu lệnh rồi đọc attributes theo thứ tự:

1. `stream_connected: false`: integration chưa nhận được stream cloud; reload integration và kiểm tra kết nối MAIKA.
2. `voice_subscription_status` khác `subscribed`: xem `voice_subscription_last_error`; reload integration để thử đăng ký lại.
3. `voice_subscription_count` nhỏ hơn `voice_subscription_target_count`: chỉ một phần loa đã được cloud chấp nhận đăng ký.
4. `stream_frame_count` không tăng sau reload: `/connect` chỉ mở HTTP nhưng chưa decode được handshake/frame.
5. `stream_frame_count` tăng nhưng `stream_directive_count` không tăng khi nói: cloud chưa mirror hội thoại của loa vào client.
6. `last_stream_frame_type` không thành `speakerConversationResponse`: cloud có frame nhưng chưa gửi schema hội thoại mong đợi.
7. `configured_rule_count: 0`: rule chưa được lưu hoặc integration chưa reload.
8. State sensor không đổi dù `last_stream_frame_has_raw_speech: true`: tải diagnostics và mở issue vì parser đã thấy trường câu nhưng chưa nhận được chuỗi hợp lệ.
9. `matched: false`: lấy chính giá trị `normalized` đang hiển thị để sửa câu bên trái dấu `|`.
10. `error: entity_not_found`: copy entity ID chính xác từ Developer Tools; kiểm tra đặc biệt `switch`, không phải `swtich`.
11. `error: entity_unavailable`: sửa kết nối integration tạo entity đích.
12. `error: service_not_supported`: entity đó không hỗ trợ action đã cấu hình.
13. `result: executed`: service đã chạy; so sánh `entity_state_before` và `entity_state_after` để kiểm tra state quan sát được.
14. `success_audio_status: pending`: rule đang xử lý; ở chế độ ưu tiên, cast có thể đã được gửi song song với service HASS.
15. `success_audio_status: failed`: đọc `success_audio_error`; kiểm tra URL MP3, loa MAIKA, trạng thái available và tùy chọn cloud cast.
16. `success_audio_status: played`: lời gọi play/cast đã hoàn tất không lỗi; đây không phải telemetry xác nhận loa vật lý đã phát thành tiếng.
17. `success_audio_status: played_before_failure`: clip ưu tiên đã được gửi trước khi service HASS trả lỗi.

Để ra lệnh, nói wake word rồi nói đúng câu bên trái rule, ví dụ: **“Maika, bật đèn phòng khách”**. Phần wake word thường không nằm trong `rawSpeech`; nếu sensor hiển thị câu khác, dùng chính state/`normalized` thực tế để sửa rule.

## Dùng sensor trong automation riêng

Với logic phức tạp hơn allowlist, có thể dùng state hoặc thuộc tính `normalized`
của sensor trong automation Home Assistant do chính người quản trị tạo. Một lựa
chọn gọn hơn là tạo script HASS an toàn rồi dùng rule `script.ten_script | turn_on`.

Ví dụ kiểm tra state trực tiếp:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.cau_lenh_giong_noi_moi_nhat
    attribute: received_at
conditions:
  - condition: state
    entity_id: sensor.cau_lenh_giong_noi_moi_nhat
    state: "chạy cảnh buổi tối"
actions:
  - action: scene.turn_on
    target:
      entity_id: scene.buoi_toi
```

Trigger theo `received_at` để chỉ chạy một lần cho mỗi câu mới; thay đổi thuộc tính kết quả từ `pending` sang `executed` sẽ không kích hoạt lại automation. Entity ID sensor thực tế phụ thuộc tên integration trong Home Assistant; chọn entity từ giao diện thay vì đoán tên.

## Quyền riêng tư

- Câu nói đã đi qua cloud MAIKA trước khi integration nhận được.
- Khi bật sensor, nội dung có thể được Recorder, backup hoặc integration khác đọc.
- Diagnostics của integration redact toàn bộ `last_voice_command` và `voice_command_rules`, nhưng vẫn phải kiểm tra file thủ công trước khi chia sẻ.
- Có thể exclude sensor trong Recorder hoặc tắt tính năng nếu không cần lịch sử câu nói.
