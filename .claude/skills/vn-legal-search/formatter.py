"""Format kết quả tìm kiếm thành Markdown theo template chuẩn (xem SKILL.md)."""
from __future__ import annotations

from filter import GROUP_FUTURE, GROUP_PARTIAL, GROUP_VALID


def format_results(
    query: str,
    analysis: dict,
    grouped: dict[str, list[dict]],
    cases: list[dict] = None,
    market_meaning: str = "",
    legal_meaning: str = "",
    conclusion: str = "",
) -> str:
    """Tạo markdown output đầy đủ.

    Args:
        query: từ khóa user gốc
        analysis: từ analyzer.analyze() — chứa expanded_keywords, domain, cross_laws
        grouped: từ filter.filter_and_rank() — {valid: [...], future: [...], partial: [...]}
        market_meaning: mô tả nghĩa thực tế (Claude điền)
        legal_meaning: mô tả nghĩa pháp lý (Claude điền)
        conclusion: kết luận tổng hợp (Claude điền)
    """
    parts: list[str] = []
    parts.append(f"## 🔍 Kết Quả Tìm Kiếm: \"{query}\"\n")

    # Phân tích từ khóa
    parts.append("### 📖 Phân Tích Từ Khóa\n")
    parts.append("| Chiều | Nội Dung |")
    parts.append("|---|---|")
    parts.append(f"| **Nghĩa thực tế thị trường** | {market_meaning or '_(chờ Claude điền)_'} |")
    parts.append(f"| **Nghĩa pháp lý chính thức** | {legal_meaning or '_(chờ Claude điền)_'} |")
    parts.append(
        f"| **Từ đồng nghĩa / liên quan** | "
        f"{', '.join(analysis.get('expanded_keywords', []))} |"
    )
    parts.append(f"| **Lĩnh vực pháp lý** | {analysis.get('domain', '—')} |")
    parts.append("\n---\n")

    # Văn bản còn hiệu lực
    valid = grouped.get(GROUP_VALID, [])
    parts.append(f"### ✅ Văn Bản Còn Hiệu Lực ({len(valid)})\n")
    if not valid:
        parts.append("_Không tìm thấy văn bản nào còn hiệu lực phù hợp._\n")
    else:
        for i, d in enumerate(valid, 1):
            parts.append(_format_doc(d, idx=i, status_icon="✅"))
    parts.append("\n---\n")

    # Chưa áp dụng
    future = grouped.get(GROUP_FUTURE, [])
    if future:
        parts.append(f"### ⚠️ Văn Bản Chưa Áp Dụng ({len(future)})\n")
        parts.append(
            "> ⚠️ **Cảnh báo:** các văn bản dưới đây **chưa có hiệu lực thi hành**. "
            "Tham khảo để chuẩn bị, KHÔNG áp dụng trong thực tế hiện tại.\n"
        )
        for i, d in enumerate(future, 1):
            parts.append(_format_doc(d, idx=i, status_icon="⚠️"))
        parts.append("\n---\n")

    # Hết hiệu lực một phần
    partial = grouped.get(GROUP_PARTIAL, [])
    if partial:
        parts.append(f"### ⚡ Văn Bản Hết Hiệu Lực Một Phần ({len(partial)})\n")
        parts.append(
            "> ⚡ Một số điều khoản đã bị thay thế. Kiểm tra điều cụ thể trước khi áp dụng.\n"
        )
        for i, d in enumerate(partial, 1):
            parts.append(_format_doc(d, idx=i, status_icon="⚡"))
        parts.append("\n---\n")

    # Phase 4: Bản án / Quyết định
    if cases:
        parts.append(f"### ⚖️ Bản Án / Quyết Định Liên Quan ({len(cases)})\n")
        parts.append(
            "> Phán quyết thực tế của tòa án đã có. Tham khảo cách tòa áp dụng "
            "luật, KHÔNG phải nguồn pháp luật bắt buộc.\n"
        )
        for i, c in enumerate(cases, 1):
            kind = c.get("case_kind", "Văn bản")
            num = c.get("case_number", "—")
            date = c.get("issue_date", "")
            level = c.get("trial_level", "")
            topic = c.get("case_topic", "")
            url = c.get("url", "")
            title = c.get("title", "")

            head_bits = [f"**{kind} số {num}**"]
            if date:
                head_bits.append(f"_{date}_")
            if level:
                head_bits.append(f"({level})")
            parts.append(f"\n{i}. " + " ".join(head_bits))
            if topic:
                parts.append(f"   - Loại vụ/việc: **{topic}**")
            court = c.get("court")
            if court:
                parts.append(f"   - Tòa: {court[:120]}")
            summary = c.get("summary", "")
            if summary:
                parts.append(f"   - Tóm tắt: {summary[:240]}…")
            if url:
                parts.append(f"   - 🔗 [Đọc đầy đủ]({url})")
        parts.append("\n---\n")

    # Liên ngành
    cross = analysis.get("cross_laws", [])
    if cross:
        parts.append("### 🔗 Kết Nối Liên Ngành\n")
        parts.append("| Bộ Luật / Luật Chung | Điều Khoản | Nội Dung Liên Quan |")
        parts.append("|---|---|---|")
        for c in cross:
            parts.append(f"| **{c['name']}** | {c['ref']} | {c['note']} |")
        parts.append("\n---\n")

    # Kết luận
    if conclusion:
        parts.append("### 📌 Kết Luận\n")
        parts.append(conclusion)

    return "\n".join(parts)


def _format_doc(d: dict, idx: int, status_icon: str) -> str:
    """Format 1 doc thành block markdown."""
    lines: list[str] = []
    title = d.get("title", "—")
    num = d.get("doc_number") or "—"
    lines.append(f"\n#### [{status_icon} {idx}] {title}")
    lines.append(f"_Số: **{num}**_")

    meta_bits: list[str] = []
    if d.get("doc_type"):
        meta_bits.append(f"**Loại:** {d['doc_type']}")
    if d.get("issued_by"):
        meta_bits.append(f"**Cơ quan:** {d['issued_by']}")
    if d.get("issue_date"):
        meta_bits.append(f"**Ban hành:** {d['issue_date']}")
    if d.get("apply_date"):
        meta_bits.append(f"**Áp dụng:** {d['apply_date']}")
    if d.get("expire_date"):
        meta_bits.append(f"**Hết hiệu lực:** {d['expire_date']}")
    if d.get("signer"):
        meta_bits.append(f"**Người ký:** {d['signer']}")
    if meta_bits:
        lines.append("- " + " · ".join(meta_bits))

    score_val = d.get("score")
    if score_val is not None:
        lines.append(f"- **Điểm relevance:** {score_val}/100")

    summary = d.get("summary_text") or d.get("summary") or ""
    if summary:
        snippet = summary.strip()
        if len(snippet) > 280:
            snippet = snippet[:280] + "…"
        lines.append(f"- **Trích:** {snippet}")

    # Phase 3: hiển thị điều khoản cụ thể
    rel_arts = d.get("relevant_articles") or []
    if rel_arts:
        lines.append(f"- **🎯 Điều khoản liên quan ({len(rel_arts)}):**")
        for art in rel_arts:
            num = art.get("number", "?")
            title = art.get("title", "")
            body = (art.get("body") or "").strip()
            score_a = art.get("_article_score")
            # Cắt body hiển thị ~400 chars
            if len(body) > 420:
                body = body[:420].rstrip() + "…"
            score_str = f" _(score {score_a})_" if score_a else ""
            head = f"**Điều {num}**" + (f" — {title}" if title else "")
            lines.append(f"  - {head}{score_str}")
            # Indent body với blockquote
            for ln in body.split("\n"):
                ln = ln.strip()
                if ln:
                    lines.append(f"    > {ln}")

    rep = d.get("replacement_docs") or []
    if rep:
        lines.append(f"- **Văn bản liên quan / sửa đổi ({len(rep)}):**")
        for r in rep[:4]:
            t = r.get("title", "")
            ed = r.get("effect_date", "")
            url = r.get("url")
            if url:
                lines.append(f"  - [{t}]({url}) — _{ed}_")
            else:
                lines.append(f"  - {t} — _{ed}_")

    url = d.get("url")
    if url:
        lines.append(f"- 🔗 [Xem văn bản đầy đủ]({url})")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sample = {
        GROUP_VALID: [
            {
                "title": "Luật Thuế thu nhập cá nhân 2007",
                "doc_number": "04/2007/QH12",
                "doc_type": "Luật",
                "issued_by": "Quốc hội",
                "issue_date": "21/11/2007",
                "apply_date": "01/01/2009",
                "summary_text": "Quy định về thuế thu nhập cá nhân...",
                "score": 81.54,
                "url": "https://luatvietnam.vn/...",
                "replacement_docs": [],
            },
        ],
        GROUP_FUTURE: [],
        GROUP_PARTIAL: [],
    }
    analysis = {
        "expanded_keywords": ["thuế thu nhập cá nhân", "TNCN"],
        "domain": "thuế",
        "cross_laws": [
            {"name": "Luật Quản lý thuế 2019", "ref": "Toàn bộ", "note": "Thủ tục"}
        ],
    }
    print(format_results(
        "thuế thu nhập cá nhân",
        analysis,
        sample,
        market_meaning="Thuế tính trên lương hàng tháng",
        legal_meaning="Thuế đối với thu nhập chịu thuế từ tiền lương",
        conclusion="Văn bản chính: Luật 04/2007/QH12.",
    ))
