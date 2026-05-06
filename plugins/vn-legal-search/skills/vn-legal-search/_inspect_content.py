"""Inspect: cấu trúc nội dung điều khoản trong detail page."""
from pathlib import Path
from bs4 import BeautifulSoup

# Dùng sample đã có (Thông tư 40/2021/TT-BTC)
html = (Path(__file__).parent / "cache" / "detail_sample.html").read_text()
soup = BeautifulSoup(html, "lxml")

# Strip noise
for t in soup.select("div.tooltip-content-1, div.tooltip-text-1"):
    t.decompose()

print("=== div.tab-noi-dung — content tab ===")
content = soup.select_one("div.tab-noi-dung")
if content:
    print(f"Length: {len(content.get_text())}")
    print(f"Direct child tags:")
    for child in list(content.children)[:10]:
        if hasattr(child, "name") and child.name:
            cls = child.get("class")
            preview = child.get_text(" ", strip=True)[:80]
            print(f"  <{child.name} class={cls}> {preview!r}")

print("\n=== item-article (articles) ===")
articles = soup.select("div.item-article")
print(f"Tổng: {len(articles)} article elements")
for i, a in enumerate(articles[:5]):
    cls = a.get("class")
    txt = a.get_text(" ", strip=True)
    print(f"\n[{i+1}] class={cls}")
    print(f"  text[:200]: {txt[:200]!r}")

print("\n=== Tìm pattern 'Điều X.' để biết cách phân chia ===")
import re
text = soup.get_text("\n", strip=True)
matches = re.findall(r"(Điều\s+\d+[\.\s][^\n]{0,80})", text)
print(f"Phát hiện {len(matches)} 'Điều N.' headers")
for m in matches[:10]:
    print(f"  - {m[:90]!r}")

# Tìm tag chứa "Điều X." như heading
print("\n=== Tag candidates cho 'Điều N.' heading ===")
seen_sigs = set()
for tag in soup.find_all(["b", "strong", "h2", "h3", "h4", "p", "div"]):
    txt = tag.get_text(" ", strip=True)
    if re.match(r"^Điều\s+\d+\.", txt) and len(txt) < 200:
        sig = (tag.name, tuple(tag.get("class") or []))
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        print(f"  <{tag.name} class={tag.get('class')}> {txt[:100]!r}")
        if len(seen_sigs) >= 10:
            break
