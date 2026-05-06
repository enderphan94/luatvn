"""Tìm kiếm bản án / quyết định / án lệ trên luatvietnam.vn.

Phase 4 — case law search. Khác statutes vì:
  - URL section: /ban-an/tim-ban-an.html
  - Form GET: SearchKeyword + LawJudgTypeId + TypeSearch
  - Listing: article.post-document
  - Không có khái niệm "hiệu lực" — bản án là phán quyết đã chốt
  - Detail page rất dài (toàn văn bản án) — Phase 4 chỉ làm listing, không fetch detail
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
SEARCH_URL = f"{BASE}/ban-an/tim-ban-an.html"

# LawJudgTypeId — type filter (verify từ form HTML)
CASE_TYPE_ALL = 0
CASE_TYPE_BAN_AN = 1     # Bản án
CASE_TYPE_QUYET_DINH = 2 # Quyết định
CASE_TYPE_AN_LE = 3      # Án lệ

REQUEST_DELAY = 1.5

# Pattern: "Bản án số 132/2025/HNGĐ-ST" hoặc "Quyết định số 76/2026/QĐST-HNGĐ"
_CASE_NUMBER_RE = re.compile(
    r"(?:Bản án|Quyết định|Án lệ)\s+số\s+([\w/\-]+)",
    re.UNICODE,
)
# Doc-id từ URL: ...-3-1378801-d11.html
_CASE_ID_RE = re.compile(r"-(\d+)-d(\d+)\.html$")


def search_cases(
    session: requests.Session,
    keyword: str,
    case_type: int = CASE_TYPE_ALL,
    max_pages: int = 2,
) -> list[dict]:
    """Tìm bản án. Trả list dict {title, url, case_id, case_number, case_kind, summary, court, issue_date, trial_level, case_topic}."""
    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for page in range(1, max_pages + 1):
        params = {
            "SearchKeyword": keyword,
            "LawJudgTypeId": case_type,
            "TypeSearch": 0,
        }
        if page > 1:
            params["page"] = page

        r = get_with_retry(session, SEARCH_URL, params=params, timeout=20)
        r.raise_for_status()

        page_results = _parse_listing(r.text)
        if not page_results:
            break

        new_count = 0
        for d in page_results:
            if d["url"] not in seen_urls:
                seen_urls.add(d["url"])
                all_results.append(d)
                new_count += 1

        if new_count == 0:
            break

        if page < max_pages:
            time.sleep(REQUEST_DELAY)

    return all_results


def _parse_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []

    for art in soup.select("article.post-document"):
        h = art.select_one("h3.entry-title > a")
        if not h:
            continue

        title = (h.get("title") or h.get_text(" ", strip=True)).strip()
        href = h.get("href", "").strip()
        if not title or not href:
            continue
        url = urljoin(BASE, href)

        # Summary
        summary_el = art.select_one("div.entry-summary")
        summary = ""
        if summary_el:
            for sp in summary_el.find_all("span", class_="bg-yelow"):
                sp.unwrap()
            summary = summary_el.get_text(" ", strip=True)

        # Case type (Hôn nhân gia đình, Hình sự, Dân sự, ...)
        topic_el = art.select_one("div.item-tags a.link-color")
        case_topic = topic_el.get_text(" ", strip=True) if topic_el else None

        # Metadata col3: Ban hành + Cấp xét xử
        issue_date = None
        trial_level = None
        for row in art.select("div.doc-col3 div.row-info"):
            label_el = row.select_one("span.color-darkgray")
            if not label_el:
                continue
            label = label_el.get_text(" ", strip=True).rstrip(":").strip()
            spans = row.find_all("span")
            value = ""
            for s in spans[1:]:
                value = s.get_text(" ", strip=True)
                if value:
                    break
            if "Ban hành" in label:
                m = re.match(r"(\d{2}/\d{2}/\d{4})", value)
                issue_date = m.group(1) if m else value
            elif "Cấp" in label:
                trial_level = value

        # Court name từ title — regex "của <Tòa án ...> về"
        court = _extract_court_from_title(title)

        out.append({
            "title": title,
            "url": url,
            "case_id": _extract_case_id(href),
            "case_kind": _extract_case_kind(href, title),
            "case_number": _extract_case_number(title),
            "summary": summary[:400],
            "case_topic": case_topic,
            "issue_date": issue_date,
            "trial_level": trial_level,
            "court": court,
        })
    return out


_COURT_RE = re.compile(r"của\s+(Tòa án[^,]+?)(?:,\s*tỉnh|\s+về|\s*$)", re.UNICODE)


def _extract_court_from_title(title: str) -> Optional[str]:
    m = _COURT_RE.search(title)
    return m.group(1).strip() if m else None


def _extract_case_id(href: str) -> Optional[str]:
    m = _CASE_ID_RE.search(href)
    return m.group(1) if m else None


def _extract_case_kind(href: str, title: str) -> Optional[str]:
    """d11 = Bản án, d12 = Quyết định, d13 = Án lệ (heuristic)."""
    m = _CASE_ID_RE.search(href)
    if m:
        kind = m.group(2)
        return {"11": "Bản án", "12": "Quyết định", "13": "Án lệ"}.get(kind)
    # Fallback từ title
    for k in ["Bản án", "Quyết định", "Án lệ"]:
        if title.startswith(k):
            return k
    return None


def _extract_case_number(title: str) -> Optional[str]:
    m = _CASE_NUMBER_RE.search(title)
    return m.group(1) if m else None


if __name__ == "__main__":
    from auth import get_session
    sess = get_session()

    print("=== Search bản án 'ly hôn' ===")
    results = search_cases(sess, "ly hôn", max_pages=1)
    print(f"Tổng: {len(results)} bản án\n")
    for d in results[:5]:
        print(f"[{d['case_kind']}] {d['title'][:90]}")
        print(f"  Số: {d['case_number']!r}, Ban hành: {d['issue_date']}, Cấp: {d['trial_level']}")
        print(f"  Loại vụ/việc: {d['case_topic']}")
        print(f"  Tòa: {d['court'][:80] if d['court'] else None!r}")
        print(f"  URL: {d['url']}")
        print()
