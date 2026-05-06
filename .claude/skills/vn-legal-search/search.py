"""Tìm kiếm văn bản pháp luật trên luatvietnam.vn.

Phase 1 — tối thiểu chạy được:
  - Fetch trang search (1 keyword × 1 effect_status × pages 1..N)
  - Parse danh sách: title, URL, doc_id, doc_type, doc_number, summary
  - Hỗ trợ pagination
  - Stub fetch_detail() — Phase 2 sẽ fill metadata (issue_date, effect_status, ...)

Cấu trúc HTML xác nhận từ inspect:
  div.post-type-doc
    h2.doc-title > a[title=clean_title][href=relative_url]
    div.doc-summary  → text snippet (có <span class="bg_yelow"> highlight)
"""
from __future__ import annotations

import re
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from http_util import get_with_retry

BASE = "https://luatvietnam.vn"
SEARCH_URL = f"{BASE}/van-ban/tim-van-ban.html"

EFFECT_VALID = 1     # Còn hiệu lực
EFFECT_EXPIRED = 2   # Hết hiệu lực — KHÔNG dùng
EFFECT_FUTURE = 3    # Chưa áp dụng

REQUEST_DELAY = 1.5  # Giây giữa các request — tránh bị rate-limit


# Doc number patterns: "82/2025/NĐ-CP", "04/2007/QH12", "40/2021/TT-BTC", ...
_DOC_NUMBER_RE = re.compile(r"\d+[/-]\d{4}[/-][A-ZĐĐ\-]+", re.UNICODE)
# Doc id ở cuối URL: ...-396148-d1.html
_DOC_ID_RE = re.compile(r"-(\d+)-d\d+\.html$")
# Doc type ở đầu title (heuristic — sẽ được Phase 2 verify từ detail page)
_DOC_TYPES = [
    "Bộ luật", "Luật", "Pháp lệnh", "Nghị quyết", "Nghị định",
    "Quyết định", "Thông tư liên tịch", "Thông tư", "Chỉ thị",
    "Công văn", "Hướng dẫn", "Bản án",
]


def search(
    session: requests.Session,
    keyword: str,
    effect_status: int = EFFECT_VALID,
    max_pages: int = 3,
) -> list[dict]:
    """Tìm kiếm văn bản. Trả list dict {title, url, doc_id, doc_type, doc_number, summary, effect_status_filter}.

    Lưu ý: tự động dừng khi không còn kết quả mới.
    """
    if effect_status == EFFECT_EXPIRED:
        raise ValueError("Không search 'Hết hiệu lực' (EffectStatusIds=2) — vi phạm rule.")

    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for page in range(1, max_pages + 1):
        params = _build_params(keyword, effect_status, page)
        r = get_with_retry(session, SEARCH_URL, params=params, timeout=20)
        r.raise_for_status()

        page_results = _parse_list(r.text, effect_status_filter=effect_status)
        if not page_results:
            break

        new_in_page = 0
        for d in page_results:
            if d["url"] not in seen_urls:
                seen_urls.add(d["url"])
                all_results.append(d)
                new_in_page += 1

        # Không thêm được gì → đã hết
        if new_in_page == 0:
            break

        if page < max_pages:
            time.sleep(REQUEST_DELAY)

    return all_results


def _build_params(keyword: str, effect_status: int, page: int) -> dict:
    p = {
        "keywords": keyword,
        "SearchOptions": 1,
        "SearchByDate": "issueDate",
        "DateFromString": "",
        "DateToString": "",
        "DocTypeIds": 0,
        "OrganIds": 0,
        "EffectStatusIds": effect_status,
        "FieldIds": 0,
        "LanguageId": 0,
        "SignerIds": 0,
    }
    if page > 1:
        p["page"] = page
    return p


def _parse_list(html: str, effect_status_filter: int) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []

    for item in soup.select("div.post-type-doc"):
        h2 = item.select_one("h2.doc-title > a")
        if not h2:
            continue

        title = (h2.get("title") or h2.get_text(" ", strip=True)).strip()
        href = h2.get("href", "").strip()
        if not title or not href:
            continue
        url = urljoin(BASE, href)

        summary_el = item.select_one("div.doc-summary")
        summary = ""
        if summary_el:
            # Loại bỏ span highlight để có text sạch
            for sp in summary_el.find_all("span", class_="bg_yelow"):
                sp.unwrap()
            summary = summary_el.get_text(" ", strip=True)

        out.append({
            "title": title,
            "url": url,
            "doc_id": _extract_doc_id(href),
            "doc_type": _extract_doc_type(title),
            "doc_number": _extract_doc_number(title),
            "summary": summary,
            "effect_status_filter": _effect_label(effect_status_filter),
        })
    return out


def _extract_doc_id(href: str) -> Optional[str]:
    m = _DOC_ID_RE.search(href)
    return m.group(1) if m else None


def _extract_doc_number(title: str) -> Optional[str]:
    m = _DOC_NUMBER_RE.search(title)
    return m.group(0) if m else None


def _extract_doc_type(title: str) -> Optional[str]:
    for t in _DOC_TYPES:
        if title.startswith(t + " "):
            return t
    return None


def _effect_label(status: int) -> str:
    return {
        EFFECT_VALID: "Còn hiệu lực",
        EFFECT_FUTURE: "Chưa áp dụng",
    }.get(status, "Không xác định")


def fetch_detail(session: requests.Session, url: str) -> str:
    """Fetch HTML chi tiết của 1 văn bản. Có rate-limit delay + retry."""
    time.sleep(REQUEST_DELAY)
    r = get_with_retry(session, url, timeout=20)
    r.raise_for_status()
    return r.text


if __name__ == "__main__":
    from auth import get_session

    sess = get_session()

    print("=== Search: 'thuế thu nhập cá nhân' (Còn hiệu lực, max 2 trang) ===")
    results = search(sess, "thuế thu nhập cá nhân", EFFECT_VALID, max_pages=2)
    print(f"Tổng: {len(results)} văn bản\n")
    for i, d in enumerate(results[:8], 1):
        print(f"[{i}] {d['title'][:90]}")
        print(f"    type={d['doc_type']!r}  number={d['doc_number']!r}  id={d['doc_id']}")
        print(f"    {d['url']}\n")

    print("\n=== Search: 'hợp đồng lao động' (Chưa áp dụng, max 1 trang) ===")
    future = search(sess, "hợp đồng lao động", EFFECT_FUTURE, max_pages=1)
    print(f"Tổng: {len(future)} văn bản (sẽ áp dụng trong tương lai)\n")
    for d in future[:5]:
        print(f"  ⚠️ {d['title'][:90]}")
