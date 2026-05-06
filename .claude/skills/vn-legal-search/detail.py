"""Parse detail page của 1 văn bản → metadata đầy đủ.

Cấu trúc xác nhận từ inspect:
  - Effect status:  div.khung_docquyen / fix_docquyen → "Hiệu lực: DD/MM/YYYY Tình trạng: ..."
  - Metadata table: <tr> chứa <td.bg-f7f7f7><strong>Label:</strong></td><td>Value</td>
  - Tomtat:         div.tab-tom-tat (toàn văn metadata + ngày cập nhật)
  - Hieuluc:        div.tab-hieu-luc (lịch sử thay đổi hiệu lực)
  - Lien quan:      div.rows-mixvb (văn bản thay thế / sửa đổi / dẫn chiếu)

Tooltip noise: div.tooltip-1, div.tooltip-content-1, div.tooltip-text-1 — phải decompose() trước parse.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE = "https://luatvietnam.vn"

# Mapping label → field key. Label sẽ được normalize (rstrip ':', strip whitespace).
_LABEL_TO_FIELD = {
    "Cơ quan ban hành": "issued_by",
    "Số hiệu": "doc_number",
    "Loại văn bản": "doc_type",
    "Người ký": "signer",
    "Ngày ban hành": "issue_date",
    "Ngày hết hiệu lực": "expire_date",
    "Ngày hiệu lực": "apply_date",
    "Ngày có hiệu lực": "apply_date",
    "Lĩnh vực": "fields",
}

_STATUS_RE = re.compile(r"Tình trạng[^:]*:\s*([^|\n]+?)(?:\s+Chế độ|\s*$)")
_EFFECT_DATE_RE = re.compile(r"Hiệu lực:\s*(\d{2}/\d{2}/\d{4})")
_DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")


def parse_detail(html: str) -> dict:
    """Parse 1 detail page → dict metadata.

    Trả về:
      effect_status, effect_status_normalized, apply_date, expire_date,
      issue_date, issued_by, doc_type, doc_number, signer, fields,
      summary_text, replacement_docs (list of {title, effect_date, url}),
      effect_history (str)
    """
    soup = BeautifulSoup(html, "lxml")

    # Strip tooltip noise — nếu không, label cell sẽ chứa cả định nghĩa tooltip
    for t in soup.select("div.tooltip-content-1, div.tooltip-text-1"):
        t.decompose()

    out: dict = {
        "effect_status": None,
        "effect_status_normalized": None,
        "apply_date": None,
        "expire_date": None,
        "issue_date": None,
        "issued_by": None,
        "doc_type": None,
        "doc_number": None,
        "signer": None,
        "fields": [],
        "summary_text": "",
        "replacement_docs": [],
        "effect_history": "",
        "articles": [],  # list of {number, title, body, full_text}
    }

    # Effect status + apply_date từ khung_docquyen
    quyen = soup.select_one("div.khung_docquyen, div.fix_docquyen")
    if quyen:
        txt = quyen.get_text(" ", strip=True)
        m = _STATUS_RE.search(txt)
        if m:
            out["effect_status"] = m.group(1).strip()
        m = _EFFECT_DATE_RE.search(txt)
        if m:
            out["apply_date"] = m.group(1)

    # Metadata từ <tr>
    out.update(_parse_metadata_rows(soup))

    # Tomtat
    tomtat = soup.select_one("div.tab-tom-tat")
    if tomtat:
        out["summary_text"] = tomtat.get_text(" ", strip=True)

    # Effect history
    hieuluc = soup.select_one("div.tab-hieu-luc")
    if hieuluc:
        out["effect_history"] = hieuluc.get_text(" ", strip=True)[:1000]

    # Replacement docs
    out["replacement_docs"] = _parse_replacement_docs(soup)

    # Articles (Điều N) — chỉ lấy mucluclv5 (article level), bỏ Chương/Mục
    out["articles"] = _parse_articles(soup)

    out["effect_status_normalized"] = _normalize_status(out["effect_status"])
    return out


# Pattern "Điều N." ở đầu paragraph — yêu cầu period sau số để phân biệt với
# inline references như "Điều 51 Luật Quản lý thuế" (không period).
_ARTICLE_SPLIT_RE = re.compile(r"\bĐiều\s+(\d+[a-zA-Z]?)\s*\.\s*")
# Phrases để filter false positives (header trong reference)
_FALSE_HEAD_PREFIXES = (
    "nghị định", "luật ", "bộ luật", "thông tư", "quyết định",
    "pháp lệnh", "hiến pháp", "công văn", "chỉ thị",
)


def _parse_articles(soup: BeautifulSoup) -> list[dict]:
    """Trả list articles từ div.tab-noi-dung, split theo 'Điều N.' pattern."""
    container = soup.select_one("div.tab-noi-dung")
    if not container:
        return []

    text = container.get_text("\n", strip=True)
    # Loại nhãn UI lặp lại
    text = re.sub(r"\bĐang theo dõi\b", "", text)

    matches = list(_ARTICLE_SPLIT_RE.finditer(text))
    if not matches:
        return []

    out = []
    seen_numbers = set()
    for i, m in enumerate(matches):
        num = m.group(1)

        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[body_start:body_end].strip()
        if not chunk:
            continue

        # Title = từ đầu chunk đến dấu xuống dòng đầu tiên hoặc dấu chấm câu
        title_line = chunk.split("\n", 1)[0]
        title_match = re.match(r"([^.\n]{2,180})", title_line)
        title = title_match.group(1).strip() if title_match else ""

        # False positive filter: title bắt đầu bằng "Nghị định"/"Luật"/... → đây là reference
        if any(title.lower().startswith(p) for p in _FALSE_HEAD_PREFIXES):
            continue

        # Body = phần sau title (trong chunk)
        if title and chunk.startswith(title):
            body = chunk[len(title):].lstrip(". \n").strip()
        else:
            body = chunk.lstrip(". \n").strip()

        # Dedup theo number — đôi khi cùng 1 điều xuất hiện 2 lần (TOC + nội dung)
        if num in seen_numbers:
            # Giữ bản dài hơn (thường là nội dung thật, không phải TOC)
            for existing in out:
                if existing["number"] == num and len(body) > len(existing["body"]):
                    existing["title"] = title
                    existing["body"] = body
                    existing["full_text"] = f"Điều {num}. {title}. {body}".strip()
            continue
        seen_numbers.add(num)

        out.append({
            "number": num,
            "title": title,
            "body": body,
            "full_text": f"Điều {num}. {title}. {body}".strip(),
        })
    return out


def _parse_metadata_rows(soup: BeautifulSoup) -> dict:
    """Walk tất cả <tr>, tìm các cell có <strong>Label:</strong> rồi lấy <td> kế tiếp."""
    out: dict = {}
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        i = 0
        while i < len(tds):
            cell = tds[i]
            strong = cell.find("strong")
            if strong:
                label = strong.get_text(" ", strip=True).rstrip(":").strip()
                key = _LABEL_TO_FIELD.get(label)
                if key and i + 1 < len(tds):
                    raw = tds[i + 1].get_text(" ", strip=True)
                    if key in ("issue_date", "expire_date", "apply_date"):
                        m = _DATE_RE.search(raw)
                        out[key] = m.group(0) if m else raw or None
                    elif key == "fields":
                        out[key] = [
                            v.strip() for v in re.split(r"[,\n]+", raw) if v.strip()
                        ]
                    else:
                        out[key] = raw or None
                    i += 2
                    continue
            i += 1
    return out


def _parse_replacement_docs(soup: BeautifulSoup) -> list[dict]:
    out = []
    for row in soup.select("div.rows-mixvb"):
        title_el = row.select_one("div.title-mixvb")
        time_el = row.select_one("div.time-mixvb-post")
        a = row.find("a")

        if not title_el:
            continue

        title = title_el.get_text(" ", strip=True)
        time_text = time_el.get_text(" ", strip=True) if time_el else ""
        # Title đôi khi append "Hiệu lực: DD/MM/YYYY" — cắt bỏ
        if time_text and title.endswith(time_text):
            title = title[: -len(time_text)].strip()

        href = a.get("href", "") if a else ""
        if href.startswith("javascript:"):
            url = None
        elif href:
            url = urljoin(BASE, href.split("#")[0])
        else:
            url = None

        out.append({
            "title": title,
            "effect_date": time_text.replace("Hiệu lực:", "").strip() if time_text else "",
            "url": url,
        })
    return out


def _normalize_status(raw: Optional[str]) -> Optional[str]:
    """Chuẩn hoá để filter dùng: 'Còn hiệu lực' / 'Hết hiệu lực' / 'Chưa áp dụng' / 'Hết hiệu lực một phần' / None."""
    if not raw:
        return None
    s = raw.strip().lower()
    if "hết hiệu lực một phần" in s or "một phần" in s:
        return "Hết hiệu lực một phần"
    # 'Đã sửa đổi' = đã bị sửa đổi/bổ sung — vẫn là văn bản gốc đang dùng nhưng có điều bị thay đổi
    if "đã sửa đổi" in s or "đã được sửa đổi" in s or "sửa đổi, bổ sung" in s:
        return "Hết hiệu lực một phần"
    if "hết hiệu lực" in s or "hết\xa0hiệu lực" in s:
        return "Hết hiệu lực"
    if "chưa" in s and ("áp dụng" in s or "có hiệu lực" in s):
        return "Chưa áp dụng"
    if "còn" in s and "hiệu lực" in s:
        return "Còn hiệu lực"
    if "có hiệu lực" in s:
        return "Còn hiệu lực"
    return raw.strip()


if __name__ == "__main__":
    from auth import get_session
    from search import fetch_detail

    sess = get_session()
    test_url = (
        f"{BASE}/thue/thong-tu-40-2021-tt-btc-huong-dan-thue-gtgt-thue-tncn-"
        f"voi-ho-kinh-doanh-203539-d1.html"
    )
    html = fetch_detail(sess, test_url)
    meta = parse_detail(html)

    print("=== Parsed metadata ===")
    for k, v in meta.items():
        if k == "summary_text":
            print(f"  {k}: {v[:120]!r}...")
        elif k == "effect_history":
            print(f"  {k}: {v[:80]!r}...")
        elif k == "replacement_docs":
            print(f"  {k}: ({len(v)} docs)")
            for d in v[:3]:
                print(f"    - {d['title'][:80]!r} | {d['effect_date']} | {d['url']}")
        else:
            print(f"  {k}: {v!r}")
