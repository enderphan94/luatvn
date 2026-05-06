---
description: Tra cứu văn bản pháp luật Việt Nam từ luatvietnam.vn — login tự động, lọc hiệu lực, kết nối liên ngành
argument-hint: <từ khóa cần tìm>
---

User cần tra cứu văn bản pháp luật Việt Nam với từ khóa: **$ARGUMENTS**

Làm theo các bước SAU ĐÂY (không bỏ bước nào):

### Bước 1 — Phân tích từ khóa (BẮT BUỘC, trước khi search)

Suy nghĩ về từ khóa và ghi NGẮN GỌN cho user thấy:
- **Nghĩa thực tế thị trường**: cách dùng phổ thông ngoài đời (vd. "thuế lương hàng tháng")
- **Nghĩa pháp lý chính thức**: thuật ngữ chuẩn trong văn bản luật (vd. "thu nhập chịu thuế từ tiền lương, tiền công")

Hai chuỗi này sẽ được truyền vào pipeline để hiện trong output cuối.

### Bước 2 — Chạy pipeline + PASTE KẾT QUẢ

Dùng Bash chạy CLI. Plugin tìm skill dir theo thứ tự: `$CLAUDE_PLUGIN_ROOT` (tự inject khi installed via plugin marketplace) → `$LUATVN_HOME` → `~/luatvn` → glob fallback:

```bash
SKILL=""
[ -n "$CLAUDE_PLUGIN_ROOT" ] && SKILL="$CLAUDE_PLUGIN_ROOT/skills/vn-legal-search"
[ -z "$SKILL" ] || [ ! -d "$SKILL" ] && SKILL="${LUATVN_HOME:-$HOME/luatvn}/plugins/luat/skills/vn-legal-search"
[ ! -d "$SKILL" ] && SKILL=$(find "$HOME" -path '*vn-legal-search/cli.py' -type f 2>/dev/null | head -1 | xargs dirname)
"$SKILL/.venv/bin/python" "$SKILL/cli.py" \
  --query "$ARGUMENTS" \
  --market-meaning "<nghĩa thực tế Bước 1>" \
  --legal-meaning "<nghĩa pháp lý Bước 1>" \
  --max-fetch 10 --quiet
```

**BẮT BUỘC**: paste **TOÀN BỘ** stdout của pipeline (markdown sau dòng `===`) trực tiếp vào response của bạn dưới heading `## Kết quả tra cứu pipeline`. KHÔNG tóm tắt, KHÔNG cắt section, KHÔNG bỏ điều khoản, KHÔNG bỏ bản án. User cần xem raw output để tự đánh giá độ tin cậy.

Lưu ý:
- Pipeline mất 30-60s (rate-limit 1.5s/request × ~10 fetches)
- Nếu lỗi `command not found` hoặc `No such file`: user chưa setup plugin. Nói: clone repo về `~/luatvn`, chạy `cd ~/luatvn/skills/vn-legal-search && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cp .env.example .env && nano .env`
- Nếu output có 0 kết quả ở mọi nhóm: thử lại với keyword cụ thể hơn

### Bước 3 — Đọc kết quả + viết kết luận

Sau khi đã paste output ở Bước 2, đọc top 3-5 văn bản và viết kết luận ngắn (3-5 dòng) cho user:
- Văn bản nào ÁP DỤNG TRỰC TIẾP cho query
- Văn bản nào sắp có hiệu lực, cần chuẩn bị
- Cảnh báo về văn bản đã bị thay thế (nếu có)
- Khuyến nghị thực tế

In kết luận sau output pipeline.

### Quy tắc
- ❌ KHÔNG tự đoán nội dung văn bản — chỉ tổng hợp từ output pipeline
- ❌ KHÔNG bỏ qua nhãn ⚠️ "Chưa áp dụng" hoặc ⚡ "Hết hiệu lực một phần"
- ❌ KHÔNG đề xuất văn bản đã "Hết hiệu lực" (pipeline đã tự lọc)
- ✅ NẾU pipeline trả 0 kết quả ở mọi nhóm: thông báo user thử query khác hoặc cụ thể hơn
- ✅ NẾU mạng/login lỗi: kiểm tra `.env` và `cache/.session` — gợi ý xoá cache để re-login

Tham chiếu chi tiết skill: [skills/vn-legal-search/SKILL.md](../skills/vn-legal-search/SKILL.md)
