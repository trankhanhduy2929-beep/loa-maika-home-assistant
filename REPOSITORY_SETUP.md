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
`1.6.0`. Không đưa server private, thư mục `../maika-license-secrets`, database
export hoặc customer data vào repository GitHub này.

Sau khi Worker có URL HTTPS, ghi URL mặc định vào release để khách không phải
nhập thủ công:

```bash
python3 scripts/configure_licensing.py \
  --server-url https://YOUR-WORKER.workers.dev
```

Nếu chưa chạy lệnh này, config flow vẫn hoạt động nhưng khách phải tự nhập URL
activation server. Xem `docs/LICENSING.md` và README của server private.

## 4. Kiểm thử local

```bash
python3 -m pip install ruff==0.16.3
ruff check .
ruff format --check .
python3 scripts/validate_repository.py
python3 scripts/build_release.py --tag v1.6.0
python3 scripts/package_source.py --tag v1.6.0
```

Artifact được tạo trong `dist/`:

- `maika.zip`: ZIP chuẩn HACS, nội dung integration nằm ở root archive.
- `maika-manual.zip`: ZIP cài thủ công, chứa `custom_components/maika`.
- `SHA256SUMS.txt`: checksum của hai ZIP.

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

- Repository phải đặt **Public** để HACS đọc được `hacs.json`, manifest và release asset.
- Description: `Unofficial MAIKA smart speaker integration for Home Assistant`.
- Topics: `home-assistant`, `hacs`, `maika`, `smart-speaker`, `vietnam`.
- Bật Issues.
- Bật Private vulnerability reporting nếu tài khoản/repository hỗ trợ.
- Kiểm tra GitHub nhận diện license là **MIT** ở phần About.

## 7. Tạo release

Đảm bảo version trong `custom_components/maika/manifest.json` là `1.6.0`, sau đó:

```bash
git tag v1.6.0
git push origin v1.6.0
```

Workflow `release.yml` kiểm tra tag/version, tạo GitHub Release và upload hai ZIP cùng checksum.

Nếu tag `v1.6.0` đã chạy thất bại trước khi các file sửa được push, xóa tag đó rồi tạo lại từ commit mới:

```bash
git tag -d v1.6.0
git push origin :refs/tags/v1.6.0
git tag v1.6.0
git push origin v1.6.0
```

## 8. Cài qua HACS

Ngay khi repository public và có release, người dùng có thể thêm nó dưới dạng HACS custom repository. Để xin vào HACS default store, làm theo quy trình publish chính thức của HACS sau khi repository đáp ứng lịch sử release, description, topics và validation.
