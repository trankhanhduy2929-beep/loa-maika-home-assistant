# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| Latest release | Yes |
| Older releases | Best effort |

## Reporting a vulnerability

Không mở public issue cho lỗ hổng hoặc dữ liệu bí mật. Dùng GitHub private vulnerability report:

`https://github.com/trankhanhduy2929-beep/loa-maika-home-assistant/security/advisories/new`

Nếu chức năng này chưa bật, liên hệ maintainer bằng kênh riêng được công bố trên GitHub profile.

Không gửi credential thật, token, SIP password, backup Home Assistant hoặc diagnostic chưa redact.

## Scope

- Xử lý credential/token.
- Command injection hoặc bypass allowlist.
- Rò rỉ raw speech, profile, Wi-Fi hoặc playback history.
- ZIP/path traversal hoặc release artifact bị chèn file ngoài ý muốn.
- Hành vi phá hủy thiết bị.

