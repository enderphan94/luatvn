---
name: vn-legal-search
description: Tra cứu văn bản pháp luật Việt Nam từ luatvietnam.vn. Đăng nhập tự động bằng credentials trong .env, search bằng từ khóa thực tế hoặc thuật ngữ pháp lý, lọc theo hiệu lực (chỉ trả văn bản còn áp dụng + chưa áp dụng, bỏ qua hết hiệu lực), parse metadata, kết nối liên ngành với Bộ luật chung. Dùng khi user hỏi về luật, nghị định, thông tư, văn bản pháp lý, hiệu lực, hoặc tranh chấp pháp lý ở Việt Nam.
---

# Skill: Tìm Kiếm Văn Bản Pháp Luật Việt Nam

## Setup (1 lần)

User cần tạo file `.env` trong cùng thư mục skill này:

```
LUATVN_USERNAME=email_của_user
LUATVN_PASSWORD=mật_khẩu
LUATVN_SESSION_TTL=3600
```

`.gitignore` đã chặn `.env` và `cache/` khỏi git. Chạy `.venv/bin/pip install -r requirements.txt` lần đầu để cài deps.

## Quy trình — DÙNG `pipeline.run()` (one-shot)

```python
from pipeline import run, PipelineConfig

result = run(
    query="thuế thu nhập cá nhân",
    market_meaning="Thuế tính trên lương hàng tháng / thưởng / cổ tức",
    legal_meaning="Thuế đối với thu nhập chịu thuế từ tiền lương, tiền công, kinh doanh, đầu tư vốn...",
    conclusion="Văn bản chính: Luật 04/2007/QH12 (sẽ hết 01/07/2026, thay bằng Luật 109/2025/QH15)...",
    config=PipelineConfig(max_detail_fetch=10),
)
print(result["markdown"])
```

`pipeline.run()` tự động làm 7 bước:

1. **Phân tích keyword** (`analyzer.analyze`): mở rộng synonyms + thêm "Luật <query>" + detect domain
2. **Đăng nhập** (`auth.get_session`): cache cookies 1 giờ, không login lặp
3. **Search song song** với 2 chiến lược:
   - Keyword thường → `EffectStatusIds=1` (Còn hiệu lực) + `=3` (Chưa áp dụng)
   - Keyword "Luật/Bộ luật <X>" → `EffectStatusIds=0` (Tất cả) — **bypass filter site vì đã verify nó không tin được**
4. **Prelim sort + ưu tiên primary law**: titles bắt đầu "Luật/Bộ luật/Pháp lệnh" được fetch detail trước
5. **Fetch detail** top K (default 10), parse status thật từ `div.khung_docquyen` + bảng metadata + **articles** (split `div.tab-noi-dung` theo "Điều N." pattern)
6. **Filter + score** (`filter.filter_and_rank`):
   - Drop hoàn toàn "Hết hiệu lực" (không liệt kê tên)
   - "Chưa áp dụng" → group `future` ⚠️
   - "Hết hiệu lực một phần" + "Đã sửa đổi" → group `partial` ⚡
   - Score 0-100: title 40 + type hierarchy 20 + recency 20 + summary 20
7. **Trích article relevant** (Phase 3): top 3 doc/nhóm × top 3 article/doc theo `find_relevant_articles()` — score article = title 3 + body 2 + density 1
8. **Format markdown** (`formatter.format_results`): doc + điều khoản cụ thể với body excerpt blockquote

### Claude điền 3 trường (vì cần lý luận):
- `market_meaning`: nghĩa thực tế thị trường
- `legal_meaning`: nghĩa pháp lý chính thức  
- `conclusion`: kết luận tổng hợp sau khi đọc top kết quả

### Quy tắc bắt buộc
- ❌ KHÔNG search `EFFECT_EXPIRED=2` — `search.py` sẽ raise ValueError
- ❌ KHÔNG tin `EffectStatusIds=1` của site (đã verify nhiều lần trả văn bản đã expire)
- ❌ KHÔNG hardcode credentials trong code
- ❌ KHÔNG bỏ qua văn bản thay thế khi đã biết có văn bản mới (replacement_docs đã được parse sẵn)
- ✅ LUÔN verify effect_status từ detail page, không từ filter URL
- ✅ LUÔN gắn ⚠️ cho "Chưa áp dụng", ⚡ cho "Hết hiệu lực một phần"
- ✅ LUÔN kết nối liên ngành ở phần cuối (`analyzer.get_cross_laws(domain)`)

### Cross-law mapping (built-in `analyzer.py`)
Mỗi domain map tới các Bộ luật chung:
- **Thuế** → BLDS 2015, Luật QLT 2019, BLHS 2015 Đ.200
- **Lao động** → BLLĐ 2019, BLDS 2015, Luật BHXH 2014 (sửa đổi 2024), BLHS 2015 Đ.214-216
- **Kinh doanh / Doanh nghiệp** → Luật DN 2020, BLDS 2015, Luật ĐT 2020, Luật TM 2005
- **BĐS** → Luật ĐĐ 2024, Luật NƠ 2023, BLDS 2015, Luật KDBĐS 2023
- **Hình sự** → BLHS 2015 (sđ 2017), BLTTHS 2015 (sđ 2021)
- **Dân sự** → BLDS 2015, BLTTDS 2015 (sđ 2020)
- **Hôn nhân** → Luật HNGĐ 2014, BLDS 2015
- **SHTT** → Luật SHTT 2005 (sđ 2022), BLDS 2015, BLHS 2015 Đ.225-226
- **Giáo dục** → Luật GD 2019, Luật GDĐH 2018

### Output template (đã built-in trong `formatter.py`)

```markdown
## 🔍 Kết Quả Tìm Kiếm: "[Từ khóa]"

### 📖 Phân Tích Từ Khóa
| Chiều | Nội Dung |
|---|---|
| Nghĩa thực tế thị trường | ... |
| Nghĩa pháp lý chính thức | ... |
| Từ đồng nghĩa | kw1, kw2, kw3 |
| Lĩnh vực | ... |

### ✅ Văn Bản Còn Hiệu Lực
#### [^1] Tên văn bản đầy đủ — Số ký hiệu
- Loại / Cơ quan / Ngày ban hành / Ngày áp dụng
- **Liên quan vì:** [lý do]
- **Nội dung chính:** [tóm tắt]
- 🔗 [URL]

### ⚠️ Văn Bản Chưa Áp Dụng
[Tương tự + cảnh báo "Hiệu lực từ DD/MM/YYYY"]

### ⚡ Văn Bản Hết Hiệu Lực Một Phần
[Tương tự + nêu rõ điều còn / điều thay thế]

### 🔗 Kết Nối Liên Ngành
| Bộ luật | Điều khoản | Liên quan |
|---|---|---|
| ... | ... | ... |

### 📌 Kết Luận
[Văn bản nào áp dụng chính, lưu ý, khuyến nghị]
```

## Quy tắc
- ✅ Luôn dùng `auth.get_session()` — không bao giờ login thủ công, luôn tận dụng cache
- ✅ Rate-limit: tối đa 20-30 docs/phiên, delay 1.5s giữa request fetch detail
- ✅ Verify effect_status từ detail page, không tin filter listing 100% (đã quan sát filter EffectStatusIds=3 trả cả văn bản cũ)
- ❌ Không hardcode credentials trong code
- ❌ Không truy vấn `EFFECT_EXPIRED=2`
- ❌ Không trả văn bản thiếu nhãn hiệu lực

## Files trong skill
- `auth.py` — login (ASP.NET Antiforgery → POST form → cache cookies + verify validity)
- `http_util.py` — `get_with_retry()` cho 5xx / timeout / connection errors
- `search.py` — search listing + pagination + `fetch_detail()`
- `detail.py` — parse detail page → effect_status, dates, signer, replacement_docs, **articles** (Điều N split)
- `ban_an.py` — search bản án/quyết định (`/ban-an/tim-ban-an.html`)
- `filter.py` — score docs + drop "Hết hiệu lực" + group valid/future/partial + `find_relevant_articles()`
- `analyzer.py` — `expand_keywords` (60+ synonyms, 20+ parent-laws) + `detect_domain` + `get_cross_laws`
- `formatter.py` — format markdown: docs + articles + cases + cross-laws
- `pipeline.py` — entry point Python `run(query, ...)`
- `cli.py` — entry point CLI cho `/luat` slash command
- `tests/test_*.py` — 53 unit tests (filter, detail, analyzer, ban_an)
- `cache/.session` — JSON cookies, TTL từ `LUATVN_SESSION_TTL`
- `_inspect_*.py`, `_test_*.py` — dev tools khi site đổi cấu trúc
