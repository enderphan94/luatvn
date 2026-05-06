# luatvn — Skill Tra Cứu Văn Bản Pháp Luật Việt Nam

Claude Code skill tự động tra cứu văn bản pháp luật Việt Nam từ [luatvietnam.vn](https://luatvietnam.vn): đăng nhập, search theo từ khóa thực tế, lọc hiệu lực, trích điều khoản cụ thể, kết nối liên ngành, và tìm bản án liên quan.

Slash command: `/luat <từ khóa>`

---

## Cài đặt cho đồng nghiệp mới (5 phút)

### Bước 1 — Clone repo

```bash
cd ~  # hoặc chỗ nào bạn muốn lưu project
git clone https://github.com/enderphan94/luatvn.git
cd luatvn
```

### Bước 2 — Tạo venv + cài Python deps

```bash
cd .claude/skills/vn-legal-search

# Tạo venv riêng (không chung với system Python)
python3 -m venv .venv

# Cài dependencies
.venv/bin/pip install -r requirements.txt
```

Yêu cầu: Python 3.9+ (đã test với 3.9 và 3.12).

### Bước 3 — Tạo file `.env` với tài khoản luatvietnam.vn của bạn

**QUAN TRỌNG:** mỗi người dùng tài khoản RIÊNG, không share.

```bash
# Vẫn ở trong .claude/skills/vn-legal-search/
cp .env.example .env
```

Mở `.env` bằng editor (vd. `nano .env` hoặc VSCode), điền 3 dòng:

```ini
LUATVN_USERNAME=email_của_bạn@example.com
LUATVN_PASSWORD=mật_khẩu_của_bạn
LUATVN_SESSION_TTL=3600
```

**Tạo tài khoản nếu chưa có:**
1. Truy cập https://luatvietnam.vn
2. Bấm "Đăng ký" góc phải trên
3. Verify email
4. Tài khoản free có giới hạn — gói trả phí mới đọc được full nội dung văn bản

**Lưu ý bảo mật:**
- File `.env` đã trong `.gitignore` → KHÔNG bao giờ bị commit lên git
- Password lưu plaintext local — chỉ trên máy bạn, không upload đâu cả
- Nếu lộ tài khoản: đổi mật khẩu trên luatvietnam.vn, sửa lại file `.env`, xoá `cache/.session`

### Bước 4 — Test

```bash
# Vẫn ở .claude/skills/vn-legal-search/
.venv/bin/python auth.py
```

Output mong đợi:
```
=== Cookies sau khi login ===
  .LuatVietNamSSO = ...
  .AspNetCore.Antiforgery.* = ...
=== Verify GET / ===
Status: 200, body length: ...
Login OK — phát hiện: ['logout', 'tkt', 'Tài khoản']
```

Nếu thấy "Login OK" → setup xong, có thể dùng `/luat`.

Nếu thấy lỗi:
- `Đăng nhập thất bại (HTTP 401)` → kiểm tra lại username/password trong `.env`
- `Không tìm thấy credentials` → file `.env` chưa tồn tại hoặc sai tên biến
- Network error → kiểm tra kết nối internet

### Bước 5 — Restart Claude Code để load slash command

```bash
# Quit Claude Code hoàn toàn rồi mở lại tại thư mục project
cd ~/luatvn  # nếu bạn clone vào ~
claude  # hoặc dùng UI app
```

Gõ `/luat <từ khóa>` để test:

```
/luat thuế thu nhập cá nhân
/luat sa thải
/luat ly hôn đơn phương
/luat đất thổ cư
```

---

## Cấu trúc project

```
luatvn/
├── README.md                              ← File này
├── .gitignore                             ← Block .env, .venv, cache
└── .claude/
    ├── commands/
    │   └── luat.md                        ← Slash command /luat
    └── skills/
        └── vn-legal-search/
            ├── SKILL.md                   ← Skill metadata (auto-trigger)
            ├── README.md                  ← Tech doc của skill
            ├── .env.example               ← Template credentials
            ├── .env                       ← Credentials thật (gitignored)
            ├── requirements.txt           ← Python deps
            ├── auth.py                    ← Login (ASP.NET Antiforgery)
            ├── http_util.py               ← HTTP retry helper
            ├── search.py                  ← Search statute listing
            ├── detail.py                  ← Parse detail page + articles
            ├── ban_an.py                  ← Search bản án/quyết định
            ├── filter.py                  ← Score + filter by hiệu lực
            ├── analyzer.py                ← Synonym + domain mapping
            ├── formatter.py               ← Markdown output
            ├── pipeline.py                ← End-to-end pipeline
            ├── cli.py                     ← CLI cho /luat command
            ├── tests/                     ← 53 unit tests
            ├── cache/                     ← Cookies cache (gitignored)
            └── .venv/                     ← venv (gitignored)
```

---

## Sử dụng

### Cách 1: Dùng slash command `/luat`

Trong Claude Code, gõ:
```
/luat <từ khóa cần tìm>
```

Ví dụ:
- `/luat thuế thu nhập cá nhân`
- `/luat hợp đồng lao động sa thải`
- `/luat sàn giao dịch tín chỉ carbon`
- `/luat đăng ký hộ khẩu`
- `/luat tranh chấp đất đai`

Pipeline mất ~30-60s/query (rate-limit 1.5s/request × ~10 fetches).

### Cách 2: Để Claude tự kích hoạt skill

Hỏi Claude bình thường về văn bản pháp luật VN, vd.:
- "Quy định về làm thêm giờ ở Việt Nam thế nào?"
- "Luật Bảo hiểm xã hội 2024 có gì mới?"

Claude sẽ tự load skill `vn-legal-search` (đã đăng ký với mô tả phù hợp).

### Cách 3: CLI trực tiếp

```bash
cd .claude/skills/vn-legal-search
.venv/bin/python cli.py --query "thuế thu nhập cá nhân" \
  --market-meaning "thuế tính trên lương" \
  --legal-meaning "thuế đối với thu nhập chịu thuế" \
  --max-fetch 10 --quiet
```

---

## Tính năng

- ✅ Đăng nhập tự động (ASP.NET Antiforgery flow), cache cookies 1 giờ
- ✅ Search × 4 keyword × 3 trạng thái hiệu lực, dedup, retry HTTP transient errors
- ✅ Parse đầy đủ metadata: ngày ban hành / áp dụng / hết hạn, người ký, cơ quan, lĩnh vực
- ✅ Phát hiện chính xác trạng thái hiệu lực thật (KHÔNG tin filter site, đã verify nhiều lần site filter sai)
- ✅ Trích điều khoản cụ thể (Điều 98 Bộ luật Lao động về tiền lương làm thêm giờ, ...)
- ✅ 16 domains: thuế / lao động / BHXH / kinh doanh / BĐS / hôn nhân / hình sự / dân sự / SHTT / giáo dục / môi trường / hành chính / TC-NH / giao thông / y tế / XNK
- ✅ 125+ synonym mappings, 80+ parent law mappings
- ✅ Tìm bản án/quyết định/án lệ liên quan từ section `/ban-an/`
- ✅ Cross-law mapping: tự động liên kết Bộ luật khung cho mỗi lĩnh vực
- ✅ 53 unit tests cover toàn bộ logic (filter / detail / analyzer / ban_an)

---

## Đóng góp

### Khi gặp query bị "miss synonym" (ra kết quả sai)

Tạo issue hoặc PR với 4 thông tin:

```
1. Query thực tế:        vd. "đăng ký hộ khẩu"
2. Tên Luật/Bộ luật gốc: vd. "Luật Cư trú"
3. Domain phù hợp:       hành chính / lao động / dân sự / ... (16 domains)
4. Từ đồng nghĩa:        vd. ["sổ hộ khẩu", "đăng ký thường trú", ...]
```

Sửa file [`.claude/skills/vn-legal-search/analyzer.py`](.claude/skills/vn-legal-search/analyzer.py) ở 3 chỗ:
- `SYNONYM_MAPPING` — mở rộng query
- `PARENT_LAW_MAPPING` — trỏ về Luật gốc
- `_DOMAIN_KEYWORDS[<domain>]` — thêm keyword detect domain

### Khi site luatvietnam.vn đổi cấu trúc HTML

Dev tools có sẵn (đã trong skill dir, file prefix `_inspect_*.py`):
- `_inspect_search.py` — dump HTML trang search listing
- `_inspect_detail.py` — dump HTML trang detail
- `_inspect_content.py` — dump HTML phần nội dung điều khoản
- `_inspect_banan.py` — dump HTML trang bản án
- `_test_bypass_filter.py` — test EffectStatusIds=0 strategy

Chạy để xem HTML mới, rồi sửa selector trong file tương ứng (`search.py`, `detail.py`, `ban_an.py`).

### Chạy unit tests

```bash
cd .claude/skills/vn-legal-search
.venv/bin/python -m unittest discover tests
```

53 tests, expect ~5ms total.

---

## Cảnh báo bảo mật

- **KHÔNG commit `.env`** — đã có trong `.gitignore` nhưng luôn check `git status` trước khi push
- **KHÔNG share password** trong issue / PR / Slack — mỗi người tài khoản riêng
- **KHÔNG hardcode credentials** trong file Python nào
- Token cookies cache 1 giờ trong `cache/.session` — auto-expire, đừng share file này

---

## Roadmap

- [x] Phase 1 — auth + search listing
- [x] Phase 2 — detail parser + filter + cross-law + pipeline
- [x] Phase 3 — article extraction + scoring + 60+ synonym mappings
- [x] Phase 4 — bản án + unit tests + HTTP retry + stale session recovery
- [x] Phase 5 — public git repo + Vietnamese setup guide
- [ ] Phase 6 — đóng gói thành Claude Code plugin chuẩn (`.claude-plugin/plugin.json`)

---

## License

MIT (hoặc tuỳ tác giả enderphan94 quyết định).

## Tác giả

[@enderphan94](https://github.com/enderphan94)
