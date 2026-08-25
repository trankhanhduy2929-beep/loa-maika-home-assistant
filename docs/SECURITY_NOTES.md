# Bảo mật và quyền riêng tư

## Trạng thái credential bàn giao

- Không có số điện thoại, mật khẩu test, access token, refresh token, SIP credential hoặc serial thật trong thư mục `ket_qua`.
- Không hardcode credential trong source, tài liệu hoặc ZIP.
- Nên đổi mật khẩu tài khoản test sau khi hoàn tất vì credential đã được chia sẻ trong phiên làm việc.

## Credential trong Home Assistant

Integration cần số điện thoại và mật khẩu để đăng nhập lại khi access token hết hạn vì không có refresh flow đủ tin cậy.

- Form mật khẩu dùng password selector để giao diện che ký tự.
- Home Assistant lưu số điện thoại và mật khẩu trong config entry nội bộ.
- Integration không ghi access token hoặc refresh token xuống đĩa.
- Access token chỉ nằm trong memory của process Home Assistant.
- Refresh token từ login response không được giữ lại.
- Reauthentication từ chối credential của một tài khoản khác với unique ID hiện tại.

Do config entry nằm trong `/config/.storage` và thường đi vào backup, cần:

- Bảo vệ quyền truy cập `/config`.
- Mã hóa/giới hạn quyền truy cập backup.
- Không gửi nguyên backup cho bên thứ ba.
- Dùng tài khoản MAIKA riêng cho môi trường thử nghiệm nếu có thể.

## Dữ liệu gửi qua mạng

| Đích | Dữ liệu |
|---|---|
| `users.iviet.com` | Credential login, device list/detail và setting update |
| `chatbot.iviet.com` | Token, command, URL media cast, trạng thái stream và text giọng nói khi cloud phát directive |
| Activation server của người bán | License key ở lần đầu, installation hash, activation code, refresh token, phiên bản HA/integration và nonce |

Activation server không nhận MAC, instance ID gốc, credential MAIKA, token
MAIKA, serial loa, entity hoặc nội dung câu lệnh giọng nói.

## Bảo mật activation

- Installation hash là SHA-256 của namespace integration và Home Assistant
  instance ID; raw ID không rời khỏi Home Assistant.
- Server chỉ lưu HMAC hash của license key và refresh token.
- Entitlement được ký Ed25519; client public chỉ chứa public key.
- Lease hết hạn sau 48 giờ và offline grace mặc định kết thúc sau bảy ngày.
- Refresh token và lease nằm trong private storage `maika.license`, không nằm
  trong diagnostic.
- Diagnostics redact license key, lease token, refresh token, license ID,
  installation hash và activation code.
- Activation server URL bắt buộc HTTPS, không nhận userinfo, query, fragment
  hoặc IP literal.
- Private signing key, admin token và license pepper không nằm trong repository
  public hoặc release ZIP.

Sensor/rule giọng nói không xử lý âm thanh local: âm thanh/text đã được MAIKA cloud xử lý trước khi Home Assistant nhận `rawSpeech`.

## Quyền riêng tư cloud cast

- Mặc định tắt và phải bật trong options.
- Toàn bộ URL phát, gồm query token hoặc chữ ký tạm do Home Assistant tạo, nằm trong metadata gửi tới cloud MAIKA.
- Không dùng URL chứa credential dài hạn hoặc file riêng tư không cần thiết.
- Integration không tải, inspect hoặc proxy nội dung; loa/MAIKA là bên truy cập URL.
- HTTP local chỉ nên dùng khi tin cậy mạng LAN và loa truy cập được Home Assistant.

## Âm báo MP3 sau rule HASS

- Mặc định tắt và phụ thuộc đồng thời vào sensor/rule giọng nói cùng cloud cast.
- Chỉ rule khớp chính xác và service HASS hoàn tất thành công mới gọi `media_player.play_media`; câu không khớp, entity unavailable hoặc service lỗi không gửi command âm thanh tới MAIKA.
- Không gửi `Pause` trước khi phát, tránh làm im loa nếu URL media hoặc cloud cast thất bại.
- Chỉ cho chọn media player MAIKA thuộc đúng config entry; runtime kiểm tra lại entity registry và trạng thái available.
- URL MP3 được lưu trong options Home Assistant và bị redact khỏi diagnostics vì query string có thể chứa token tạm.
- Integration không log URL khi cast lỗi; log chỉ ghi tên loại exception an toàn.
- URL đầy đủ vẫn được gửi qua metadata cloud MAIKA; không đặt credential dài hạn hoặc secret vào URL.
- Đường cast trực tiếp `1.5.1` vẫn kiểm tra URL, config entry, entity registry, unique ID, serial loa và trạng thái available trước khi gửi command.

## Safeguard đã triển khai

- Allowlist REST field được phép ghi.
- Không có factory-reset button/service.
- Không có arbitrary command service.
- Cast dùng schema cố định và chỉ target serial của entity được gọi.
- Cast chỉ nhận HTTP(S), chặn URL userinfo/ký tự trắng/URL quá dài và IP literal loopback, link-local, multicast, unspecified hoặc reserved.
- Cast không hỗ trợ queue `add/next`; `announce=true` chỉ được xử lý như phát thay thế để tương thích TTS, không tự khôi phục nội dung cũ.
- MP4/AAC dùng cùng fallback `AUDIO_MPEG` tìm thấy trong APK; integration không chuyển mã hoặc tải nội dung media.
- Mute của media player chỉ đặt volume đầu ra về 0; switch micro vật lý vẫn là entity riêng.
- Không expose SIP credential.
- Không expose write `status` hoặc avatar.
- Volume bị clamp `0..100`.
- Scan interval bị giới hạn `15..3600` giây.
- Retry auth tối đa một lần cho mỗi request.
- Event stream có giới hạn buffer 1 MiB và backoff reconnect.
- Pending future bị cancel khi unload.
- Duplicate speech bị chặn trong 5 phút.
- Sensor/rule câu lệnh giọng nói mặc định tắt; domain, action và từng field JSON đều qua allowlist cố định, có kiểm tra kiểu/range và giới hạn kích thước.
- JSON rule không thể ghi đè entity/target, truyền credential, object lồng nhau hoặc gọi service hệ thống/raw command; mở khóa và alarm control panel không được expose.
- Coordinator luôn ép `entity_id` từ rule sau khi tạo service data, nên payload không thể đổi target lúc chạy.
- Âm báo MP3 ưu tiên chỉ chạy khi rule vượt qua kiểm tra entity/service; chế độ sau-thành-công chỉ phát khi service HASS thành công. Không có command hủy hội thoại chưa được xác minh.
- Diagnostics redact nội dung rule và toàn bộ bản ghi câu lệnh mới nhất.
- Diagnostic chủ động redact credential, device ID, SSID, profile, metadata và lịch sử playback phổ biến.
- Entry không kết nối cloud MAIKA trước khi activation lease hợp lệ.
- Khi refresh server lỗi, chỉ lease có chữ ký còn trong active/grace mới được dùng.

## Diagnostic

Home Assistant diagnostic vẫn nên được xem là dữ liệu nhạy cảm. Integration redact nhiều key, nhưng backend có thể thêm key mới chưa biết.

Trước khi chia sẻ diagnostic:

1. Mở file và kiểm tra thủ công.
2. Tìm số điện thoại, email, địa chỉ, tên, SSID, serial, token và nội dung media.
3. Xóa/redact thêm nếu cần.
4. Không chia sẻ file `.storage/core.config_entries`.

## Rủi ro API không chính thức

- OLLI có thể đổi endpoint/schema hoặc chặn client không phải app.
- Dùng integration có thể chịu điều khoản dịch vụ của MAIKA/OLLI.
- Sai schema command có thể tạo hành vi ngoài dự kiến.
- Cloud outage làm entity unavailable hoặc stale.
- Credential bị thay đổi sẽ tạo reauth flow.

Chỉ nâng cấp protocol sau khi kiểm thử read-only hoặc same-value trước. Không thử `Reset` trên loa đang sử dụng.

## Khuyến nghị vận hành

- Chạy Home Assistant và custom component ở bản được cập nhật bảo mật.
- Chỉ cấp quyền truy cập Home Assistant cho người tin cậy.
- Dùng HTTPS/reverse proxy đúng cách khi truy cập HA từ Internet.
- Theo dõi log lỗi xác thực nhưng không bật network body logging chứa header/token.
- Kiểm tra automation dùng nút restart để tránh vòng lặp.
- Ưu tiên action xác định như `turn_on`, `turn_off`, `set_percentage` thay vì `toggle`; exclude sensor câu lệnh khỏi Recorder nếu không muốn lưu lịch sử câu nói.
- Reload integration sau khi thêm/xóa loa trong tài khoản.
