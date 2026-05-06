"""Inspect: dump structure xung quanh 1 result đầu tiên."""
from pathlib import Path
from bs4 import BeautifulSoup

html = (Path(__file__).parent / "cache" / "search_sample.html").read_text()
soup = BeautifulSoup(html, "lxml")

first = soup.select_one("h2.doc-title")
print("=== First h2.doc-title ===")
print(first.prettify()[:600])

print("\n=== Closest meaningful ancestor ===")
# Tìm ancestor là 1 'card' chứa toàn bộ metadata cho 1 doc
node = first
for _ in range(8):
    node = node.parent
    if node is None:
        break
    cls = node.get("class") if node.name else None
    print(f"  <{node.name} class={cls} id={node.get('id') if node.name else None}>")

print("\n=== Result item — dùng ancestor có class chứa 'item' hoặc 'doc' ===")
# Theo kinh nghiệm, container thường là div cha gần nhất
item = first.find_parent(class_=lambda c: c and any(k in " ".join(c) for k in ["item", "result", "doc-list", "list-item"]))
if item:
    print(f"Found: <{item.name} class={item.get('class')}>")
    print("--- Full HTML ---")
    print(item.prettify()[:2500])
else:
    # Fallback: lấy parent div chứa h2 + sibling
    item = first.find_parent("div")
    print(f"Fallback parent div: class={item.get('class') if item else None}")
    print(item.prettify()[:2500] if item else "—")
