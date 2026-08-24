# Quản trị repository GitHub

## 1. Repository đã cấu hình

Source này đã được cấu hình cho repository:

```text
https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant
```

Kiểm tra metadata trước mỗi lần push:

```bash
python3 scripts/validate_repository.py
```

Chỉ cần chạy lại script sau nếu repository được chuyển sang owner hoặc tên khác:

```bash
python3 scripts/configure_repository.py --owner OWNER_MOI --repo TEN_REPOSITORY_MOI
```

## 2. Giấy phép

Repository sử dụng giấy phép MIT trong file `LICENSE`. Nếu muốn đổi giấy phép, cập nhật file này trước khi tạo release.

MIT cho phép sao chép và phân phối lại client. Phần thu phí là activation
service, hỗ trợ và quyền sử dụng dịch vụ; không mô tả client public là phần mềm
không thể sao chép.

## 3. Chuẩn bị activation server

Deploy server private trong `../maika-license-server` trước khi phát hành bản
`1.7.0`. Không đưa server private, thư mục `../maika-license-secrets`, database
export hoặc customer data vào repository GitHub này.

Sau khi Worker có URL HTTPS, ghi URL mặc định vào release để khách không phải
nhập thủ công:

```bash
python3 scripts/configure_licensing.py \
  --server-url https://YOUR-WORKER.workers.dev \
  --public-key-b64-file /DUONG_DAN/SIGNING_PUBLIC_KEY_B64.txt
```

Nếu chưa chạy lệnh này, config flow vẫn hoạt động nhưng khách phải tự nhập URL
activation server. Xem `docs/LICENSING.md` và README của server private.

Khi nâng cấp Worker/D1 đã có khách, không truyền
`--public-key-b64-file` theo một key local khác và không upload lại signing
private key ngẫu nhiên. Giữ đúng public key đã phát hành cho client hiện hữu;
Easy Mode mới tự bảo toàn điểm này.

## 4. Kiểm thử local

```bash
python3 -m pip install ruff==0.16.3
ruff check .
ruff format --check .
python3 scripts/validate_repository.py
python3 scripts/build_release.py --tag v1.7.0 \
  --public-key-b64-file /DUONG_DAN/SIGNING_PUBLIC_KEY_B64.txt
python3 scripts/package_source.py --tag v1.7.0 \
  --public-key-b64-file /DUONG_DAN/SIGNING_PUBLIC_KEY_B64.txt
```

Artifact được tạo trong `dist/`:

- `maika.zip`: ZIP chuẩn HACS, nội dung integration nằm ở root archive.
- `maika-manual.zip`: ZIP cài thủ công, chứa `custom_components/maika`.
- `maika-vX.Y.Z-hacs.zip`: bản sao ZIP HACS có tên kèm version để bàn giao.
- `maika-vX.Y.Z-manual.zip`: bản sao ZIP thủ công có tên kèm version.
- `SHA256SUMS.txt`: checksum của toàn bộ ZIP HACS và ZIP cài thủ công.

## 5. Đồng bộ repository GitHub hiện có

Clone repository, sau đó chép nội dung thư mục bàn giao vào clone nhưng giữ nguyên thư mục `.git`:

```bash
git clone https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant.git
cd loa-maika-home-assistant
rsync -a --exclude='.git/' /DUONG_DAN/ket_qua/loa-maika-home-assistant/ ./
git add -A
git commit -m "Configure MAIKA integration repository"
git push origin main
```

Không commit thư mục `dist/`; release workflow sẽ build lại artifact.

## 6. Cấu hình trang GitHub

Description và Topics là **Repository settings trên GitHub**, không nằm trong
README, `hacs.json` hoặc source ZIP. Trên trang chính repository, bấm biểu tượng
bánh răng cạnh mục **About**, nhập các giá trị sau rồi bấm **Save changes**:

- Repository phải đặt **Public** để HACS đọc được `hacs.json`, manifest và release asset.
- Description: `Unofficial MAIKA smart speaker integration for Home Assistant`.
- Topics: `home-assistant`, `hacs`, `maika`, `smart-speaker`, `vietnam`.
- Bật Issues.
- Bật Private vulnerability reporting nếu tài khoản/repository hỗ trợ.
- Kiểm tra GitHub nhận diện license là **MIT** ở phần About.

HACS báo `no description` hoặc `no valid topics` cho tới khi hai trường About
này được lưu trên GitHub; commit thêm file vào repository không thể thay thế
bước cấu hình này.

## 7. Tạo release

Đảm bảo version trong `custom_components/maika/manifest.json` là `1.7.0`, sau đó:

```bash
git tag v1.7.0
git push origin v1.7.0
```

Workflow `release.yml` kiểm tra tag/version, tạo GitHub Release và upload hai ZIP cùng checksum.

Không di chuyển hoặc ghi đè tag `v1.6.0` vì release đó đã được công bố. Đưa bản
vá CI/Windows lên `main`, chờ workflow Validate xanh rồi tạo tag `v1.7.0` từ
commit mới.

Chỉ khi một tag mới chạy thất bại trước khi GitHub Release được tạo thì mới xóa
tag lỗi và tạo lại từ commit đã sửa:

```bash
git tag -d v1.7.0
git push origin :refs/tags/v1.7.0
git tag v1.7.0
git push origin v1.7.0
```

## 8. Cài qua HACS

Ngay khi repository public và có release, người dùng có thể thêm nó dưới dạng HACS custom repository. Để xin vào HACS default store, làm theo quy trình publish chính thức của HACS sau khi repository đáp ứng lịch sử release, description, topics và validation.
