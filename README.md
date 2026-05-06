# vn-legal-search — Claude Code Plugin

Plugin tự động tra cứu văn bản pháp luật Việt Nam từ [luatvietnam.vn](https://luatvietnam.vn): đăng nhập, search theo từ khóa thực tế, lọc hiệu lực, trích điều khoản, kết nối liên ngành, tìm bản án.

**Slash command:** `/luat <từ khóa>`
**Skill:** auto-trigger khi user hỏi về văn bản pháp luật VN

---

## Cài đặt (5 phút)

### Bước 1 — Clone repo về `~/luatvn`

```bash
cd ~
git clone https://github.com/enderphan94/luatvn.git
cd luatvn
```

> **Tại sao `~/luatvn`?** Slash command `/luat` mặc định tìm skill ở `$HOME/luatvn`. Nếu clone chỗ khác, phải set `export LUATVN_HOME=<path>` trong `~/.zshrc` hoặc `~/.bashrc`.

### Bước 2 — Setup Python venv + dependencies

```bash
cd skills/vn-legal-search
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Yêu cầu Python 3.9+.

### Bước 3 — Tạo `.env` với tài khoản luatvietnam.vn

**Mỗi người dùng tài khoản RIÊNG, KHÔNG share.**

```bash
cp .env.example .env
nano .env  # hoặc code .env / vim .env
```

Điền vào:

```ini
LUATVN_USERNAME=email_của_bạn@example.com
LUATVN_PASSWORD=mật_khẩu_của_bạn
LUATVN_SESSION_TTL=3600
```

**Tạo tài khoản luatvietnam.vn:**
1. Truy cập https://luatvietnam.vn
2. Bấm "Đăng ký" góc phải
3. Verify email
4. Free có giới hạn — gói trả phí mới đọc full nội dung văn bản

**Bảo mật:**
- File `.env` đã trong `.gitignore` → KHÔNG commit lên git
- Plaintext local-only — không upload đâu
- Đổi password trên luatvietnam.vn → cập nhật `.env` → xoá `cache/.session`

### Bước 4 — Test login

```bash
# Vẫn ở skills/vn-legal-search/
.venv/bin/python auth.py
```

Output mong đợi:
```
=== Cookies sau khi login ===
  .LuatVietNamSSO = ...
=== Verify GET / ===
Status: 200, body length: ...
Login OK — phát hiện: ['logout', '<username>', 'Tài khoản']
```

### Bước 5 — Cài plugin vào Claude Code

**Cách A — Plugin local (development):**

```bash
# Mở Claude Code với plugin của bạn
claude --plugin-dir ~/luatvn
```

**Cách B — Plugin install vĩnh viễn:**

Trong Claude Code session, chạy slash command:
```
/plugin install ~/luatvn
```

(Tham khảo doc Claude Code mới nhất nếu cách trên thay đổi: https://code.claude.com/docs/en/plugins)

### Bước 6 — Test

Trong Claude Code, gõ:

```
/luat thuế thu nhập cá nhân
/luat sa thải
/luat ly hôn đơn phương
/luat đất thổ cư
/luat sàn giao dịch tín chỉ carbon
```

Pipeline mất ~30-60s/query (rate-limit 1.5s/request × 10 fetches).

---

## Cấu trúc plugin

```
luatvn/                                       ← plugin root
├── .claude-plugin/
│   └── plugin.json                          ← Plugin manifest (name, version, ...)
├── README.md                                ← File này
├── .gitignore
├── commands/
│   └── luat.md                              ← Slash command /luat
└── skills/
    └── vn-legal-search/                     ← Skill (auto-trigger)
        ├── SKILL.md                         ← Skill metadata
        ├── README.md                        ← Tech docs
        ├── .env / .env.example              ← Credentials
        ├── requirements.txt
        ├── auth.py                          ← Login ASP.NET Antiforgery
        ├── http_util.py                     ← HTTP retry helper
        ├── search.py                        ← Search statute listing
        ├── detail.py                        ← Parse detail page + articles
        ├── ban_an.py                        ← Search bản án/quyết định
        ├── filter.py                        ← Score + filter hiệu lực
        ├── analyzer.py                      ← Synonym + domain mapping
        ├── formatter.py                     ← Markdown output
        ├── pipeline.py                      ← End-to-end pipeline
        ├── cli.py                           ← CLI cho /luat command
        ├── tests/                           ← 53 unit tests
        └── cache/                           ← Cookies cache (gitignored)
```

---

## Tính năng

- ✅ **Login tự động** — ASP.NET Antiforgery flow, cache cookies 1 giờ, retry transient errors
- ✅ **Search 16 domains** — thuế / lao động / BHXH / kinh doanh / BĐS / hôn nhân / hình sự / dân sự / SHTT / giáo dục / môi trường / hành chính / TC-NH / giao thông / y tế / XNK
- ✅ **125+ synonym mappings** + 80+ parent law mappings → query "ly dị" tự expand thành "Luật Hôn nhân và Gia đình"
- ✅ **Phát hiện hiệu lực thật** — KHÔNG tin filter site (đã verify nhiều lần site trả văn bản đã expire), parse status từ detail page
- ✅ **Trích điều khoản cụ thể** — query "làm thêm giờ" → BLLĐ 2019 Điều 98 (rate 150%/200%/300%)
- ✅ **Bản án/quyết định** — tìm phán quyết tòa án thực tế từ `/ban-an/`
- ✅ **Cross-law mapping** — tự liên kết với Bộ luật khung
- ✅ **53 unit tests** — cover toàn bộ logic

---

## Sử dụng

### Cách 1 — Slash command

```
/luat <từ khóa>
```

### Cách 2 — Để Claude tự kích hoạt

Hỏi tự nhiên về luật VN, vd:
- "Quy định về làm thêm giờ ở Việt Nam thế nào?"
- "Luật Bảo hiểm xã hội 2024 có gì mới?"

### Cách 3 — CLI trực tiếp

```bash
cd ~/luatvn/skills/vn-legal-search
.venv/bin/python cli.py --query "thuế thu nhập cá nhân" \
  --market-meaning "thuế tính trên lương" \
  --legal-meaning "thuế đối với thu nhập chịu thuế" \
  --max-fetch 10 --quiet
```

---

## Đóng góp

### Khi gặp query "miss synonym" (ra kết quả sai)

Tạo issue / PR với 4 thông tin:

```
1. Query thực tế:        "đăng ký hộ khẩu"
2. Tên Luật/Bộ luật gốc: "Luật Cư trú"
3. Domain phù hợp:       hành chính (1 trong 16 domains)
4. Từ đồng nghĩa:        ["sổ hộ khẩu", "đăng ký thường trú", ...]
```

Sửa [`skills/vn-legal-search/analyzer.py`](skills/vn-legal-search/analyzer.py) ở 3 chỗ:
- `SYNONYM_MAPPING` — mở rộng query
- `PARENT_LAW_MAPPING` — trỏ Luật gốc
- `_DOMAIN_KEYWORDS[<domain>]` — detect domain

### Khi luatvietnam.vn đổi cấu trúc HTML

Dev tools (skill dir, prefix `_inspect_`):
- `_inspect_search.py` — dump search listing
- `_inspect_detail.py` — dump detail page
- `_inspect_content.py` — dump nội dung điều khoản
- `_inspect_banan.py` — dump bản án page
- `_test_bypass_filter.py` — test EffectStatusIds=0 strategy

### Run unit tests

```bash
cd skills/vn-legal-search
.venv/bin/python -m unittest discover tests
```

---

## Bảo mật

- **KHÔNG commit `.env`** — `git status` check trước khi push
- **KHÔNG share password** trong issue/PR/Slack
- **KHÔNG hardcode credentials** trong Python code
- Cookies cache 1 giờ trong `cache/.session` — auto-expire, đừng share

---

## Roadmap

- [x] Phase 1 — auth + search listing
- [x] Phase 2 — detail parser + filter + cross-law + pipeline
- [x] Phase 3 — article extraction + 60+ synonyms
- [x] Phase 4 — bản án + 53 unit tests + retry + stale session
- [x] Phase 5 — public git + Vietnamese setup guide
- [x] Phase 6 — Claude Code plugin format (`.claude-plugin/plugin.json`)
- [ ] Phase 7 — submit lên Claude Code marketplace (khi có)

---

## License

MIT

## Tác giả

[@enderphan94](https://github.com/enderphan94)
