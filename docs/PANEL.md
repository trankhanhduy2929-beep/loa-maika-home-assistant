# Panel quản lý loa MAIKA

Từ bản `1.9.0`, tích hợp MAIKA tự đăng ký một mục **MAIKA** trong sidebar Home
Assistant. Từ `1.9.1`, panel dùng giao diện dashboard dạng sections; từ `1.9.2`,
panel hỗ trợ nhiều loa trong cùng tài khoản; từ `1.9.3`, panel ghép thực thể theo
`unique_id` nên tên loa đặt kiểu nào (`wifi_relay`, `amply_ke_sach`,…) cũng không
đọc nhầm thực thể. Bản `1.9.4` dùng lưới 4 cột khi panel rộng hơn 1100px,
2 cột từ 621–1100px và 1 cột khi rộng tối đa 620px. Bố cục tính theo vùng
panel còn lại, không chỉ theo màn hình, nên vẫn phù hợp khi mở sidebar HA.
Từ `1.10.0`, mục **Giọng nói** có trình tạo câu lệnh trực quan và panel không
hiện ô URL máy chủ kích hoạt. Từ `1.10.1`, panel là nơi cấu hình sau khi
cài đặt; nút **Configure / Tùy chọn MAIKA** bên trang tích hợp đã được bỏ.
Các tuỳ chọn cũ tự tiếp tục được dùng, không cần nhập lại.

## Liquid Glass và hoạt ảnh từ v1.12.0 (cập nhật v1.13.0)

- Tông cam MAIKA, nền sáng kem/tối nâu than, thẻ kính mờ và viền phản sáng.
  Ảnh loa gọn bên cạnh tên/trạng thái, nút cam chuyển sắc. Ô nhập giữ nền
  rõ để không khó đọc nội dung.
- Khi HA báo loa đang phát và không tắt tiếng: ảnh loa chuyển động nhẹ,
  vòng sóng lan và dải sóng chạy, thanh phát nhạc có vệt sáng chậm.
  Tạm dừng/tắt tiếng/mất kết nối hoặc chưa rõ trạng thái thì dừng hiệu ứng
  phát nhạc. Sóng là minh hoạ trạng thái, không đo âm thanh hay thu micro.
- Từ `1.13.0`, hoạt ảnh **bật tự động** và không còn nút bật/tắt. Logo có
  nhịp sóng nhỏ, mục đang chọn có vệt sáng chạy, thẻ nổi nhẹ khi rê chuột.
- Hệ thống bật **Giảm chuyển động** thì hoạt ảnh tự tắt (không cần thao
  tác). Nền kính chuyển sang nền đặc khi thiết bị yêu cầu giảm trong
  suốt/tăng tương phản hoặc không hỗ trợ backdrop-filter.
- Từ `1.13.0`, key **vĩnh viễn** không hiện dòng **Hạn dùng**; gói theo
  tháng vẫn hiện hạn bình thường.
- **Vuốt ngang trên thẻ loa** để chuyển loa trong cùng tài khoản. Có nút
  trước/sau, số thứ tự và phím trái/phải khi thẻ được focus. Một loa thì ẩn
  các nút này; vuốt tới đầu/cuối không tự quay vòng.
- Vuốt dọc vẫn cuộn trang; thanh chọn mục/loa cuộn ngang tự nhiên. Cử chỉ
  ngắn, nhiều ngón hoặc bị huỷ không đổi loa. Các ô nhập/nút không bắt vuốt.
- Vuốt chỉ đổi loa đang xem: không thực thi lệnh, không đổi tài khoản,
  không tự lưu. Không chuyển loa khi panel đang thao tác hoặc đang lưu/chạy
  thử câu lệnh. Bản nháp key, cấu hình chung và giọng nói vẫn giữ nguyên.
- Chạm **Tạo câu lệnh** trên thẻ loa để tới Giọng nói. Mở
  **Phát âm thanh từ đường dẫn** trong Điều khiển MAIKA để nhập URL MP3/AAC;
  ô nhập và trạng thái mở vẫn giữ khi có cập nhật dữ liệu.
- Hiệu ứng nhấn, kéo/chuyển loa và viền sáng dùng transform/opacity; dừng
  khi ra khỏi vùng nhìn, tab bị ẩn hoặc thiết bị bật **Giảm chuyển động**.
  Không cần cài thêm thư viện giao diện và không có vòng lặp JS khi đứng yên.

## Lịch sử, nhắc hạn và thư viện âm phản hồi từ v1.14.0

- Lịch sử câu lệnh gần đây (câu nói, thiết bị/thao tác, thời gian và kết quả
  Đã thực hiện / Lỗi / Đang chạy / Chưa có rule) được gộp vào mục **Trò chuyện**
  từ v1.20.1. Panel ưu tiên thuộc tính `recent_commands` của cảm biến câu lệnh
  để cập nhật ngay, dự phòng bằng snapshot; giữ tối đa 20 câu lệnh.
- **Nhắc hạn key**: mục **Bản quyền** hiện băng nhắc khi key còn ≤ 7 ngày
  hoặc đã hết hạn, và Home Assistant tạo thông báo hệ thống một lần mỗi
  ngày. Key vĩnh viễn không nhắc. Dòng **Hạn dùng** dùng hạn thật
  `license_expires_at` do máy chủ ký kèm (cần worker cấp phép đã cập nhật).
- **Thư viện âm phản hồi**: chọn nguồn "Thư viện MP3 trên Home Assistant",
  panel quét `/config/www`, `/config/mp3`, `/config/media` (mp3, m4a, aac,
  wav, ogg, flac) và phục vụ file qua `/maika_media/...`. Đường dẫn được
  kiểm tra trong danh sách cho phép, không cho thoát thư mục. Home Assistant
  phải truy cập được từ Internet (Settings → System → Network) để loa tải.

## Trò chuyện và thư viện giải trí từ v1.20.0

- Mục **Trò chuyện** cho phép gõ câu lệnh rồi bấm **Gửi** tới loa đang chọn,
  đúng luồng app gốc: panel gọi `POST /api/maika/panel/chat`, coordinator gửi
  một event `Recognize` (`SpeechRecognizer`, `rawSpeech`) tới
  `chatbot.iviet.com/stream` với header `device-id`/`olli-session-id` trỏ đúng
  loa. Hội thoại hiện câu lệnh đã gửi (bong bóng bên phải) và phản hồi
  `TextToSpeech`/`SpeechSynthesizer` của loa (bong bóng bên trái). Sau khi gửi,
  panel tự nạp lại nhanh để bắt phản hồi; lượt chat tối đa 500 ký tự và giữ 50
  lượt gần nhất.
- **Gộp lịch sử vào hội thoại (v1.20.1)**: mục riêng **Lịch sử** được bỏ, các
  câu lệnh MAIKA nghe qua micro nay nằm chung dòng thời gian với chat, có kèm
  nhãn kết quả. Khi mục **Trò chuyện** đang mở, panel tự làm mới mỗi 4 giây để
  hội thoại và câu lệnh cập nhật gần như thời gian thực mà không mất nội dung
  đang gõ.
- Nút icon **Thư viện giải trí** trên hàng bài đang phát mở hộp thoại duyệt
  Content Store (`maika_cs_*`): kênh → media → tập/bài, thể loại và nội dung
  nổi bật. Chọn một bài phát qua `media_player.play_media` kiểu `maika_cs_track`;
  nút quay lại trên breadcrumb trở về mục cha.
- Ô **Tìm bài hát trên NhạcCủaTui** trong hộp thoại thư viện gọi
  `media_player/search_media`; kết quả là track `maika_nct_track`, chọn bài sẽ
  cast qua cloud MAIKA. Enter hoặc nút **Tìm** đều chạy tìm kiếm; lỗi có nút
  **Thử lại**.
- **Lịch sử câu lệnh** giờ được lưu xuống HA `Store`
  (`maika.command_history.<entry_id>`) và khôi phục sau khi khởi động lại.

## Giao diện sáng / tối và điều hướng

- Từ `1.11.1`, panel giới hạn chiều cao theo vùng nhìn ngay cả khi khung HA
  không có chiều cao cố định. Lăn chuột trên ảnh, thanh chọn hay các thẻ đều
  cuộn được trang; danh sách câu lệnh cuộn riêng và chuyển sang cuộn trang
  khi tới đầu/cuối. Không dùng listener chặn wheel, nên cuộn ngang trackpad
  và cử chỉ trên điện thoại vẫn giữ nguyên.

- Chọn **Tự động / Sáng / Tối** trên thanh công cụ. **Tự động** theo chế độ
  sáng/tối của Home Assistant; lựa chọn được nhớ riêng trong trình duyệt.
  Nếu trình duyệt chặn lưu trữ, vẫn đổi được cho phiên đang mở.
- Chạm **Tổng quan / Trò chuyện / Giọng nói / Thiết bị / Trợ lý / Bản quyền /
  Cấu hình / Công cụ** để tới đúng mục. Vuốt ngang thanh mục trên điện thoại.
- Nút menu ở góc trên mở sidebar HA khi màn hình hẹp. Thanh công cụ bám trên
  đầu khi cuộn; trên màn hình thấp (điện thoại ngang) thanh này cuộn cùng nội dung.
- Animation nhẹ cho thẻ, trạng thái phát nhạc và nút; tự tắt theo cài đặt
  **Giảm chuyển động** của thiết bị và tạm dừng khi tab không hiển thị.
- Các nút/ô nhập có nhãn hỗ trợ trình đọc màn hình, focus bàn phím rõ và vùng
  chạm lớn. Không cần cài Mushroom hoặc card-mod.

## Bố cục

1. **Ảnh loa + trạng thái**: ảnh loa MAIKA, tên loa, chấm online, chip Trực
   tuyến / Wi-Fi / Micro / Âm lượng.
2. **Điều khiển MAIKA**: media player đang phát gì (bấm tên bài để mở danh sách
   bài trên loa), nút icon thư viện mở hộp thoại **Thư viện giải trí** (Content
   Store), nút trước – phát/tạm dừng – dừng – sau, mute, thanh âm lượng,
   thanh thời gian kéo tua (khi loa báo thời lượng), form cast URL MP3/AAC qua
   cloud.
3. **Thiết bị**: một tab gồm năm accordion mở/đóng bằng nút mũi tên:
   - **Trạng thái loa** (mở sẵn): 6 tile — trực tuyến, Wi-Fi, âm lượng, đang
     phát, cuộc gọi, yêu thích.
   - **Tên & vị trí**: sửa trực tiếp tên loa, tên khi gọi, địa chỉ (lưu bằng
     `text.set_value`).
   - **Thông tin thiết bị**: model, phòng, ngôn ngữ, Wi-Fi SSID, serial, ngày
     kích hoạt, trạng thái.
   - **Firmware & hệ thống**: phiên bản firmware, trạng thái cập nhật, nhà sản
     xuất.
   - **Bảo hành**: còn/hết bảo hành và ngày hết hạn — chỉ hiện khi loa có dữ
     liệu.
4. **Trợ lý Maika**: chọn giọng đọc, độ nhạy đánh thức, phản hồi khi gọi, công
   tắc tắt microphone.
5. **Bản quyền**: trạng thái, gói, hạn dùng, key dạng rút gọn, mã cài đặt, form
   nhập key mới và liên kết mua/gia hạn.
6. **Cấu hình**: chu kỳ cập nhật, cast âm thanh cloud, địa chỉ Home Assistant
   cho loa tải nhạc (tuỳ chọn), nút lưu và nút tải lại integration. Lưu tại đây
   không ghi đè cấu hình giọng nói.
7. **Công cụ**: làm mới trạng thái và khởi động lại loa (có xác nhận).
8. **Giọng nói**, nằm ngay sau điều khiển MAIKA: trình tạo câu lệnh ba bước,
   danh sách tìm kiếm/sửa/thêm cách nói/xóa/chạy thử, cài đặt âm phản hồi.

Nếu có nhiều config entry, các chip chọn **tài khoản** xuất hiện ở đầu panel.
Nếu một tài khoản có nhiều loa, thêm hàng chip chọn **loa** ngay bên dưới: chạm
để đổi loa và mọi mục trong panel (media, trợ lý, các accordion trong tab Thiết
bị, công cụ) chỉ hiển thị entity của loa đó.
Mục **Bản quyền**, **Giọng nói** và **Cấu hình** là của tài khoản/Home Assistant nên dùng
chung cho mọi loa.

## Thao tác

- **Kích hoạt / thay key**: dán key mới vào ô *License key* rồi bấm
  **Kích hoạt / thay key**. Hệ thống tự thay máy sang key mới, không cần admin
  xoá máy và không cần xoá key cũ. Không cần nhập URL: dùng máy chủ đã lưu,
  hoặc máy chủ mặc định nếu chưa từng kích hoạt.
- **Lưu cấu hình**: chỉnh các trường rồi bấm **Lưu cấu hình**; tích hợp tự tải
  lại để áp dụng. Các trường đang gõ không bị mất khi dữ liệu loa cập nhật.
- **Giọng nói**: chọn loại mục (thiết bị/automation/script/scene), tìm theo tên,
  chọn thao tác và thông số, nhập câu muốn nói rồi lưu. Không cần gõ mã rule.
  Nút **Lưu & bật điều khiển** cho biết tính năng sẽ được bật cùng lúc lưu lệnh.
- **Chạy thử**: chỉ thực hiện sau khi bạn xác nhận; không kiểm thử khả năng
  nhận dạng giọng nói hay phát MP3. Lưu câu lệnh không tự điều khiển thiết bị.
- **Âm phản hồi**: chọn MP3 có sẵn/URL riêng/tắt, thời điểm và loa MAIKA trong
  cùng tài khoản. Bật cast cloud ở Cấu hình; nếu nhiều loa cần chọn một loa
  phát, không tự suy ra loa nhận câu nói. Ưu tiên che giọng chỉ là best-effort.
- **Đổi loa**: cấu hình và key chưa lưu vẫn giữ khi chuyển loa cùng tài khoản;
  ô cast và tên/vị trí tách theo loa. Có xác nhận trước khi đổi tài khoản nếu
  đang có bản nháp giọng nói; không đổi tài khoản khi đang lưu/chạy thử.
- **Xung đột cấu hình**: nếu câu lệnh hoặc âm phản hồi đã bị sửa ở tab khác,
  máy chủ từ chối ghi đè. Bản nháp còn nguyên để bạn xem lại; nút **Tải lại
  cấu hình đã lưu** yêu cầu xác nhận bỏ bản nháp trước khi nạp dữ liệu mới.
- **Địa chỉ Home Assistant cho loa tải nhạc**: để trống cho integration tự dò;
  chỉ điền địa chỉ LAN khi cast nhạc local từ Home Assistant bị lỗi.
- **Tua nhạc**: kéo thanh thời gian, hoặc bấm **−30s / +30s** để tua nhanh quanh vị
  trí hiện tại, khi loa đang cast bài từ Home Assistant; lệnh gửi lại luồng từ vị
  trí mới nên bài sẽ phát tiếp tại đó.
- **Dừng phát**: nút vuông riêng gọi `media_player.media_stop`. API đã xác minh
  chưa có stop native nên integration gửi pause, báo **Tạm dừng** và giữ vị trí
  để phát tiếp; không reset bài hoặc xóa hàng đợi trên loa. Nút vô hiệu hóa khi
  loa mất kết nối hoặc integration đang chạy chưa hỗ trợ `STOP`.
- **Chọn bài trên loa**: bấm tên bài đang phát trong Điều khiển MAIKA để mở danh
  sách bài (`latest_playlist`) do loa cung cấp, kể cả khi tắt cloud cast. Danh
  sách hiển thị bài đang phát, trạng thái đang tải/trống/mất kết nối và nút thử
  lại khi đọc lỗi. Chọn một bài gửi `media_player.play_media` kiểu `maika_song`;
  hộp thoại đóng khi xong, có thể đóng bằng phím Esc, và danh sách tự vô hiệu
  nếu dữ liệu của loa khác về sau. Không tự dựng playlist từ lịch sử hay câu nói.
- **Tải lại integration**: bấm nút trong mục Cấu hình nếu cần nạp lại thủ công.
- **Mất mạng**: thông báo lỗi hiển thị trên đầu panel; bấm nút làm mới để thử
  lại. Dữ liệu đã tải trước đó vẫn hiện để tham khảo.

## Khi key hết hạn hoặc loa chưa kết nối

Panel vẫn đăng ký ngay khi Home Assistant bắt đầu tải tài khoản MAIKA,
trước khi kiểm tra license và kết nối loa. Mở **MAIKA → Bản quyền** để
nhập/thay key kể cả khi tích hợp đang báo cần kích hoạt. Một số trạng thái
loa có thể chưa có dữ liệu; không cần xoá thiết bị hoặc nhờ admin xoá máy.
Panel không bị gỡ khi tải lại; chỉ gỡ khi xoá tài khoản MAIKA cuối cùng.

Trang **Settings → Devices & services** vẫn dùng để thêm/xoá, bật/tắt, tải
lại tích hợp và đăng nhập lại khi Home Assistant yêu cầu. Lần cài đầu tiên
vẫn có bước kích hoạt và nhập tài khoản MAIKA; chỉ bỏ màn hình tuỳ chọn
bị trùng với panel, không bỏ xác thực license.

## Cập nhật từ bản cũ

Cập nhật custom integration lên `1.19.0`, khởi động lại Home Assistant rồi tải
lại trang bằng **Ctrl+F5**/mở lại ứng dụng. Không xoá integration, thiết bị hoặc license key.
Đây là nâng cấp panel Home Assistant; portal Vercel và hệ thống thanh toán
không thay đổi. Đã kiểm tra bằng trình duyệt Chromium với HA giả lập ở các
kích thước 320–1920px; cần kiểm tra thêm trên loa và ứng dụng HA thực tế.
Các câu lệnh đã lưu tự hiện trong mục Giọng nói. Những dòng chưa sửa (kể cả
comment và thông số nâng cao) được giữ lại; không cần tạo lại lệnh.

## Bảo mật

- Các API của panel đều yêu cầu phiên đăng nhập Home Assistant.
- Key đầy đủ không bao giờ được gửi tới trình duyệt; panel chỉ nhận `key_hint`
  (dạng rút gọn) từ lease đã ký.
- Mọi lỗi khi đăng ký panel đều được bắt và ghi log, không làm hỏng tích hợp.
