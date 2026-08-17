# Kích hoạt thương mại

Từ bản `1.6.0`, integration cần một activation lease hợp lệ trước khi kết nối
tài khoản MAIKA. Cơ chế này dùng Home Assistant instance ID, không dùng MAC
address.

## Easy Mode: gắn máy đầu tiên tự động

Server bàn giao mặc định dùng:

```toml
AUTO_APPROVE_FIRST_INSTALLATION = "true"
```

Luồng khách hàng:

1. Người bán tạo license lifetime, mặc định một máy.
2. Khách cài integration qua HACS hoặc ZIP.
3. Khách nhập URL máy chủ kích hoạt và license key.
4. Home Assistant đầu tiên dùng key được chuyển thẳng sang trạng thái `active`.
5. Server trả signed lease ngay, không cần gửi mã chờ người bán duyệt.
6. Khách nhập tài khoản MAIKA và sử dụng.

Home Assistant thứ hai dùng cùng key bị `activation_limit` khi license chỉ cho
phép một máy. Khi chuyển máy, người bán revoke installation cũ và rotate key
trên web quản trị Vercel.

## Chế độ duyệt tay dự phòng

Đặt biến Worker thành:

```toml
AUTO_APPROVE_FIRST_INSTALLATION = "false"
```

Khi đó luồng khách hàng là:

1. Người bán tạo customer và license trên server riêng.
2. Khách cài integration qua HACS hoặc ZIP.
3. Khách nhập URL máy chủ kích hoạt và license key.
4. Integration tạo mã dạng `MAIKA-XXXX-XXXX-XXXX-XXXX`.
5. Server lưu yêu cầu ở trạng thái `pending`.
6. Khách gửi mã cài đặt cho người bán.
7. Người bán đối chiếu mã và duyệt installation.
8. Khách bấm kiểm tra lại, sau đó mới nhập tài khoản MAIKA.

Entry đã tạo trước `1.6.0` sẽ không tải cho đến khi được kích hoạt tại
**Settings → Devices & services → MAIKA Speaker → Configure → License và kích
hoạt**.

## Dữ liệu gửi tới activation server

- License key ở lần kích hoạt đầu tiên.
- SHA-256 hash tạo từ Home Assistant instance ID và namespace riêng của MAIKA.
- Mã cài đặt rút gọn từ cùng hash.
- Phiên bản integration, phiên bản Home Assistant và nonce ngẫu nhiên.
- Refresh token ngẫu nhiên cho các lần làm mới sau.

Không gửi MAC address, Home Assistant instance ID gốc, tài khoản/mật khẩu
MAIKA, access token MAIKA, serial loa, entity, câu nói hoặc dữ liệu thiết bị.

## Lease và offline grace

- Server ký entitlement bằng Ed25519 private key.
- Integration chỉ chứa public key để xác minh chữ ký.
- Lease mặc định có hiệu lực 48 giờ.
- Khi activation server mất kết nối, lease đã ký được dùng thêm tối đa bảy
  ngày offline grace.
- Integration làm mới định kỳ khoảng 12 giờ, có jitter để tránh mọi khách gọi
  server cùng lúc.
- `revoked`, `rejected`, `deactivated`, license hết hạn hoặc grace hết hạn sẽ
  làm entry ngừng tải.

Refresh token và lease được lưu trong private Home Assistant storage
`/config/.storage/maika.license`, không nằm trong config entry hoặc diagnostic.

## Vận hành server

Server mẫu nằm ngoài repository public tại `ket_qua/maika-license-server` và
dùng Cloudflare Worker + D1. Secret triển khai nằm tại
`ket_qua/maika-license-secrets`; tuyệt đối không push hai thư mục này vào
repository integration public.

Sau khi deploy Worker, có thể giữ trường URL trong config flow hoặc ghi URL mặc
định vào release:

```bash
python3 scripts/configure_licensing.py \
  --server-url https://YOUR-WORKER.workers.dev
```

Không thay public key nếu chưa có kế hoạch rotation. Nếu mất Ed25519 private
key hiện tại, server không thể cấp lease mới mà các bản integration đã phát
hành chấp nhận.

## Giới hạn chống sao chép

Repository HACS vẫn dùng MIT và mã Python được cài trực tiếp trên máy khách.
License server ngăn chia sẻ thông thường và quản lý số installation, nhưng
không thể ngăn tuyệt đối người có kỹ thuật sửa mã client để bỏ kiểm tra.

Muốn enforcement mạnh hơn, chức năng có giá trị phải phụ thuộc vào dịch vụ do
người bán vận hành. Không chuyển credential MAIKA qua server trung gian nếu
không có quyền, chính sách bảo mật và nhu cầu kỹ thuật rõ ràng.
