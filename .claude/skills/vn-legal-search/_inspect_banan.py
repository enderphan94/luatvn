"""Inspect: kết quả search bản án thật."""
from pathlib import Path
from auth import get_session, BASE
from bs4 import BeautifulSoup

sess = get_session()

url = f"{BASE}/ban-an/tim-ban-an.html"
params = {
    "SearchKeyword": "ly hôn",
    "LawJudgTypeId": "0",
    "TypeSearch": "0",
}
r = sess.get(url, params=params, timeout=20)
print(f"Status: {r.status_code}, length: {len(r.text)}\n")

cache = Path(__file__).parent / "cache"
(cache / "banan_search.html").write_text(r.text)
print(f"Saved → cache/banan_search.html\n")

soup = BeautifulSoup(r.text, "lxml")

# Tìm container 1 result
print("=== Headings có 'Quyết định' / 'Bản án' / 'Án lệ' ===")
for h in soup.find_all(["h1", "h2", "h3", "h4"])[:25]:
    txt = h.get_text(" ", strip=True)
    if any(k in txt for k in ["Quyết định", "Bản án", "Án lệ"]):
        cls = h.get("class")
        a = h.find("a")
        href = a.get("href") if a else None
        print(f"  <{h.name} class={cls}> {txt[:90]!r}")
        if href:
            print(f"    href: {href[:100]}")

# Tìm container post-type-doc hoặc tương tự
print("\n=== Common container classes ===")
from collections import Counter
ctr = Counter()
for tag in soup.find_all(True):
    for c in tag.get("class") or []:
        ctr[c] += 1
for cls, n in ctr.most_common(20):
    if 5 < n < 200:
        print(f"  .{cls}: {n}")

# Inspect 1 result item đầu tiên
print("\n=== First result item (h2 chứa link bản án) ===")
first = None
for h in soup.find_all(["h2", "h3"]):
    a = h.find("a")
    if a and "/ban-an/" in (a.get("href", "") or ""):
        href = a.get("href", "")
        if any(p in href for p in ["quyet-dinh-", "ban-an-", "an-le-"]):
            first = h
            break
if first:
    print(f"Found: <{first.name} class={first.get('class')}>")
    parent = first.parent
    for _ in range(5):
        if parent is None:
            break
        cls = parent.get("class") if parent.name else None
        print(f"  parent: <{parent.name} class={cls}>")
        parent = parent.parent

    # Container = parent của parent thường
    item = first.find_parent("div")
    if item:
        print(f"\n--- Container (first parent div) class={item.get('class')} ---")
        print(item.prettify()[:2000])
