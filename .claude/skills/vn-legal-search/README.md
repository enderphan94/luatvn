# vn-legal-search

Claude Code skill tra cứu văn bản pháp luật Việt Nam từ [luatvietnam.vn](https://luatvietnam.vn).

## Trạng thái

**Phase 1 + 2 + 3 + 4 — DONE.** Verify trên `luatvietnam.vn` (2026-05):
- ✅ **Login**: ASP.NET Antiforgery flow (GET token → POST form-encoded). Cookies persist + auto re-login khi cache stale.
- ✅ **Search listing**: parser `div.post-type-doc`, pagination, dedup theo URL.
- ✅ **Detail parser**: extract effect_status / dates / signer / issued_by / fields / replacement_docs / **articles**.
- ✅ **Filter + scoring**: score 0–100 (title 40 + type 20 + recency 20 + summary 20). Drop "Hết hiệu lực", group valid/future/partial.
- ✅ **Article extraction**: split `div.tab-noi-dung` theo "Điều N." pattern, filter false positives, score title 3/body 2/density 1.
- ✅ **Cross-law mapping**: 9 lĩnh vực, 60+ synonym entries, 20+ parent-law mappings.
- ✅ **Bản án / Quyết định (Phase 4)**: search `/ban-an/tim-ban-an.html`, parse listing với case_number / case_kind / topic / court / trial_level / issue_date.
- ✅ **HTTP retry (Phase 4)**: `http_util.get_with_retry()` với exponential backoff cho 5xx/timeout/connection errors.
- ✅ **Stale session detection (Phase 4)**: cached session được verify bằng homepage check, auto re-login nếu invalid.
- ✅ **Unit tests (Phase 4)**: 53 tests trong `tests/`, cover filter / detail / analyzer / ban_an logic.
- ✅ **Pipeline end-to-end**: query → search × N keywords × {VALID, FUTURE, ALL} → fetch detail top K → filter → extract articles → search bản án → format markdown.

### ⚠️ Phát hiện quan trọng về site
**Site filter `EffectStatusIds=1` (Còn hiệu lực) KHÔNG TIN ĐƯỢC.** Verify (2026-05):
- Search "thuế thu nhập cá nhân" + filter Còn hiệu lực → trả Nghị định 82/2025 (đã expire 01/01/2026)
- Search "hợp đồng lao động" + filter Còn hiệu lực → KHÔNG trả Bộ luật Lao động 2019, chỉ trả 1994/2012 (đã hết)

→ Pipeline tự động dùng `EffectStatusIds=0` (tất cả) cho keyword "Luật <X>" / "Bộ luật <X>" và verify status thật từ detail page parser. Không bao giờ trust filter của site.

## Setup

```bash
cd .claude/skills/vn-legal-search

# 1. Cài deps trong venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Tạo .env (chép từ template, điền creds thật)
cp .env.example .env
# Edit .env
```

## Smoke test

```bash
# Module tests
.venv/bin/python auth.py        # Login OK
.venv/bin/python search.py      # 20 results × 2 query
.venv/bin/python detail.py      # metadata + articles
.venv/bin/python filter.py      # drop Hết hiệu lực, score
.venv/bin/python analyzer.py    # expand keywords + domain
.venv/bin/python formatter.py   # markdown sample
.venv/bin/python ban_an.py      # 20 bản án ly hôn

# Unit tests (53 tests)
.venv/bin/python -m unittest discover tests

# End-to-end pipeline
.venv/bin/python pipeline.py "thuế thu nhập cá nhân"
.venv/bin/python pipeline.py "sa thải"
.venv/bin/python pipeline.py "ly hôn đơn phương"
.venv/bin/python pipeline.py "tranh chấp đất đai"
```

## Output thực tế (verify 2026-05)

**Query `"sa thải"`** → BLLĐ 2019, **Điều 125 (sa thải)** — score article 2.53:
> Hình thức xử lý kỷ luật sa thải được người sử dụng lao động áp dụng trong trường hợp:
> 1. Trộm cắp, tham ô, đánh bạc, cố ý gây thương tích, sử dụng ma tuý tại nơi làm việc;
> 2. Tiết lộ bí mật kinh doanh, bí mật công nghệ, xâm phạm SHTT...

**Query `"làm thêm giờ"`** → BLLĐ 2019, **Điều 98 (tiền lương làm thêm giờ)** — score 2.6:
> 1. Vào ngày thường, ít nhất bằng 150%;
> 2. Vào ngày nghỉ hằng tuần, ít nhất bằng 200%;
> 3. Vào ngày lễ, tết, ngày nghỉ có hưởng lương, ít nhất bằng 300%.

**Query `"thuế thu nhập cá nhân"`** → trả luật chính + replacement chain:
- ⚠️ **Luật TNCN 2025** (`109/2025/QH15`) — Chưa áp dụng (01/07/2026)
- ⚡ **Luật TNCN 2007** (`04/2007/QH12`) — Hết một phần, hết hoàn toàn 01/07/2026
- ⚡ **Luật sửa đổi 9 Luật** (`56/2024/QH15`)
- Cross-law: BLDS 2015, Luật QLT 2019, BLHS 2015 Đ.200

## Sử dụng trong Claude Code

Skill được load tự động khi user hỏi văn bản pháp luật VN. Claude:

1. Phân tích từ khóa (Claude điền market_meaning + legal_meaning)
2. Gọi `pipeline.run(query, ...)` → markdown đầy đủ
3. Có thể bổ sung kết luận sau khi đọc top docs

Chi tiết hành vi: xem [SKILL.md](SKILL.md).

## Bảo mật

- `.env` và `cache/` đã trong `.gitignore` — không commit
- Token cookies cache 1 giờ (cấu hình `LUATVN_SESSION_TTL`)
- Rate-limit: 1.5s/request fetch detail, max 10 docs/session

## Cấu trúc

```
vn-legal-search/
├── SKILL.md               ← Hướng dẫn cho Claude (frontmatter chuẩn)
├── README.md              ← File này
├── .env / .env.example    ← Credentials (gitignored)
├── .gitignore
├── requirements.txt
├── auth.py                ← Login (ASP.NET Antiforgery) + session cache
├── search.py              ← Search listing + pagination + fetch_detail()
├── detail.py              ← Detail page parser → metadata đầy đủ
├── filter.py              ← Scoring + drop Hết hiệu lực + nhóm valid/future/partial
├── analyzer.py            ← Expand keywords + domain detection + cross-laws
├── formatter.py           ← Markdown output template
├── pipeline.py            ← Entry point end-to-end
├── _inspect_search.py     ← Dev: dump HTML khi parser fail
├── _inspect_detail.py     ← Dev: tương tự cho detail page
├── _test_bypass_filter.py ← Dev: verify EffectStatusIds=0 strategy
├── cache/
│   ├── .session           ← Cookies JSON (gitignored)
│   ├── search_sample.html ← Mẫu HTML (gitignored)
│   └── detail_sample.html
└── .venv/                 ← venv (gitignored)
```

## Roadmap

- [x] **Phase 1** — auth + search listing
- [x] **Phase 2** — detail parser, filter, formatter, pipeline, cross-law
- [x] **Phase 3** — article extraction + scoring, expanded SYNONYM_MAPPING (60+), parent-law mapping (20+)
- [x] **Phase 4** — bản án search + unit tests (53) + HTTP retry + stale session recovery
- [ ] **Phase 5** (next) — đóng gói thành Claude Code plugin với manifest `.claude-plugin/plugin.json`
