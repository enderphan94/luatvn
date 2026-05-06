"""Inspect: dump table metadata + replacement docs section."""
from pathlib import Path
from bs4 import BeautifulSoup

html = (Path(__file__).parent / "cache" / "detail_sample.html").read_text()
soup = BeautifulSoup(html, "lxml")

print("=== item-status (effect status block) ===")
for el in soup.select("div.item-status, div.khung_docquyen, div.fix_docquyen"):
    print(f"  <{el.name} class={el.get('class')}>")
    print(f"    {el.get_text(' | ', strip=True)[:300]}")
    print()

print("\n=== Metadata table (Cơ quan ban hành, Số:, Ngày ban hành) ===")
# Tìm tất cả <tr> chứa label "Cơ quan ban hành:" hoặc "Ngày ban hành"
keywords = ["Cơ quan ban hành", "Số công báo", "Ngày ban hành", "Người ký",
            "Ngày hiệu lực", "Loại văn bản", "Lĩnh vực", "Ngày hết hiệu lực"]
for tr in soup.find_all("tr"):
    txt = tr.get_text(" | ", strip=True)
    if any(k in txt for k in keywords) and len(txt) < 600:
        print(f"  TR: {txt[:300]}")

print("\n=== tab-tom-tat (summary) — first 500 chars ===")
tomtat = soup.select_one("div.tab-tom-tat")
if tomtat:
    print(tomtat.get_text(" ", strip=True)[:500])

print("\n=== tab-hieu-luc (effect history) — full text ===")
hieuluc = soup.select_one("div.tab-hieu-luc")
if hieuluc:
    print(hieuluc.get_text(" | ", strip=True)[:800])

print("\n=== Replacement / related docs (rows-mixvb) ===")
for row in soup.select("div.rows-mixvb")[:5]:
    title = row.select_one("div.title-mixvb")
    time_el = row.select_one("div.time-mixvb-post")
    a = row.find("a")
    print(f"  - title: {title.get_text(' ', strip=True)[:120] if title else '—'!r}")
    print(f"    time:  {time_el.get_text(' ', strip=True) if time_el else '—'!r}")
    print(f"    link:  {a.get('href') if a else '—'!r}")
