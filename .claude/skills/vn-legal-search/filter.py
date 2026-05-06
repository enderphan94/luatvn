"""Lọc & xếp hạng văn bản theo hiệu lực + relevance.

Quy tắc bắt buộc (xem SKILL.md):
  - Bỏ hoàn toàn "Hết hiệu lực" (kể cả không liệt kê tên)
  - "Chưa áp dụng" → gắn nhãn ⚠️
  - "Hết hiệu lực một phần" → gắn nhãn ⚡
  - Có replacement_doc → vẫn liệt kê doc gốc nhưng note văn bản mới

Scoring (max 100):
  - 40 pts: keyword match trong title (accent-insensitive)
  - 20 pts: doc type hierarchy (Bộ luật/Luật > Nghị định > Thông tư > ...)
  - 20 pts: recency (issue_date càng mới càng cao, 0 sau 20 năm)
  - 20 pts: keyword match trong summary
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

# Doc type score
_TYPE_SCORE = {
    "Bộ luật": 20,
    "Luật": 20,
    "Pháp lệnh": 18,
    "Nghị quyết": 15,
    "Nghị định": 15,
    "Thông tư liên tịch": 12,
    "Thông tư": 10,
    "Quyết định": 8,
    "Hướng dẫn": 7,
    "Chỉ thị": 5,
    "Công văn": 3,
}

# Status nào được giữ lại
KEEP_STATUSES = {"Còn hiệu lực", "Chưa áp dụng", "Hết hiệu lực một phần"}
DROP_STATUSES = {"Hết hiệu lực"}

GROUP_VALID = "valid"     # Còn hiệu lực
GROUP_FUTURE = "future"   # Chưa áp dụng — ⚠️
GROUP_PARTIAL = "partial" # Hết hiệu lực một phần — ⚡
_STATUS_TO_GROUP = {
    "Còn hiệu lực": GROUP_VALID,
    "Chưa áp dụng": GROUP_FUTURE,
    "Hết hiệu lực một phần": GROUP_PARTIAL,
}


def normalize_vi(s: str) -> str:
    """Lowercase + bỏ dấu để fuzzy compare. Không dùng dep ngoài."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("đ", "d").replace("Đ", "D")
    return s.casefold()


def filter_and_rank(
    docs: list[dict],
    keywords: list[str],
    today: Optional[date] = None,
) -> dict[str, list[dict]]:
    """Input: list dict đã merge listing + parsed detail.
    Output: dict {valid: [...], future: [...], partial: [...]} đã sort score giảm dần.

    Mỗi doc trong output có thêm field `score` (float) và `_group` (str).
    Doc 'Hết hiệu lực' bị loại bỏ hoàn toàn.
    """
    today = today or date.today()
    norm_kws = [normalize_vi(k) for k in keywords if k]

    grouped: dict[str, list[dict]] = {GROUP_VALID: [], GROUP_FUTURE: [], GROUP_PARTIAL: []}

    seen_numbers: set[str] = set()  # dedup theo doc_number

    for d in docs:
        status = d.get("effect_status_normalized")

        # Quy tắc: bỏ hết hiệu lực
        if status in DROP_STATUSES:
            continue
        if status not in KEEP_STATUSES:
            # Status không xác định (None) → tạm coi là valid nếu listing đến từ filter=Còn hiệu lực
            if d.get("effect_status_filter") == "Còn hiệu lực":
                status = "Còn hiệu lực"
            elif d.get("effect_status_filter") == "Chưa áp dụng":
                status = "Chưa áp dụng"
            else:
                continue

        # Dedup theo doc_number (tránh trùng giữa 2 lần search keyword khác nhau)
        num = d.get("doc_number")
        if num and num in seen_numbers:
            continue
        if num:
            seen_numbers.add(num)

        d = dict(d)
        d["score"] = score(d, norm_kws, today)
        d["_group"] = _STATUS_TO_GROUP[status]
        d["effect_status_normalized"] = status

        grouped[d["_group"]].append(d)

    for g in grouped.values():
        g.sort(key=lambda x: x["score"], reverse=True)

    return grouped


def score(doc: dict, norm_keywords: list[str], today: date) -> float:
    """Trả score 0..100."""
    title = doc.get("title", "")
    summary = doc.get("summary_text") or doc.get("summary") or ""
    doc_type = doc.get("doc_type")
    issue_date = doc.get("issue_date")

    # Title match (40)
    norm_title = normalize_vi(title)
    title_hits = sum(1 for kw in norm_keywords if kw and kw in norm_title)
    title_score = min(title_hits / max(len(norm_keywords), 1), 1.0) * 40

    # Type hierarchy (20)
    type_score = _TYPE_SCORE.get(doc_type, 3) if doc_type else 3
    type_score = min(type_score, 20)

    # Recency (20) — 0 sau 20 năm
    rec_score = _recency_score(issue_date, today) * 20

    # Summary match (20)
    norm_summary = normalize_vi(summary)
    sum_hits = sum(1 for kw in norm_keywords if kw and kw in norm_summary)
    sum_score = min(sum_hits / max(len(norm_keywords), 1), 1.0) * 20

    return round(title_score + type_score + rec_score + sum_score, 2)


def find_relevant_articles(
    articles: list[dict],
    keywords: list[str],
    top_n: int = 3,
    min_score: float = 0.5,
) -> list[dict]:
    """Lọc + xếp hạng articles theo keyword relevance.

    Score theo:
      - Title match (0-3 điểm: 0=miss, 1=có 1 keyword, 3=tất cả keyword)
      - Body match (0-2 điểm: tỉ lệ keyword unique xuất hiện)
      - Body density bonus (0-1 điểm: keyword xuất hiện > 1 lần)

    Trả top_n articles có score >= min_score, kèm field `_article_score`.
    """
    if not articles or not keywords:
        return []

    norm_kws = [normalize_vi(k) for k in keywords if k]
    scored = []
    for a in articles:
        title = a.get("title", "") or ""
        body = a.get("body", "") or ""
        nt = normalize_vi(title)
        nb = normalize_vi(body)

        # Title weight cao hơn
        title_hits = sum(1 for k in norm_kws if k and k in nt)
        title_score = min(title_hits / max(len(norm_kws), 1), 1.0) * 3

        # Body presence
        body_hits = sum(1 for k in norm_kws if k and k in nb)
        body_score = min(body_hits / max(len(norm_kws), 1), 1.0) * 2

        # Density bonus
        density = sum(nb.count(k) for k in norm_kws if k) / max(len(nb) // 200, 1)
        density_score = min(density / 5, 1.0)

        s = round(title_score + body_score + density_score, 2)
        if s >= min_score:
            scored.append({**a, "_article_score": s})

    scored.sort(key=lambda x: x["_article_score"], reverse=True)
    return scored[:top_n]


def _recency_score(issue_date: Optional[str], today: date) -> float:
    if not issue_date:
        return 0.0
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", issue_date)
    if not m:
        return 0.0
    try:
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return 0.0
    years = (today - d).days / 365.25
    return max(0.0, 1.0 - years / 20.0)


if __name__ == "__main__":
    # Smoke test
    docs = [
        {
            "title": "Luật Thuế thu nhập cá nhân 2007",
            "doc_number": "04/2007/QH12",
            "doc_type": "Luật",
            "issue_date": "21/11/2007",
            "summary_text": "thuế thu nhập cá nhân",
            "effect_status_normalized": "Còn hiệu lực",
        },
        {
            "title": "Thông tư 40/2021/TT-BTC hướng dẫn thuế GTGT, thuế TNCN với hộ kinh doanh",
            "doc_number": "40/2021/TT-BTC",
            "doc_type": "Thông tư",
            "issue_date": "01/06/2021",
            "summary_text": "thuế thu nhập cá nhân hộ kinh doanh",
            "effect_status_normalized": "Hết hiệu lực",  # → bị loại
        },
        {
            "title": "Nghị định 12/2023/NĐ-CP gia hạn nộp thuế",
            "doc_number": "12/2023/NĐ-CP",
            "doc_type": "Nghị định",
            "issue_date": "14/04/2023",
            "summary_text": "gia hạn thuế",
            "effect_status_normalized": "Còn hiệu lực",
        },
    ]
    out = filter_and_rank(docs, ["thuế thu nhập cá nhân", "thuế"])
    for group, items in out.items():
        print(f"\n=== {group.upper()} ({len(items)}) ===")
        for d in items:
            print(f"  score={d['score']:>5.2f}  {d['title'][:80]}")
