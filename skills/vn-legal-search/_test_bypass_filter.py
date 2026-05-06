"""Test: search KHÔNG dùng EffectStatusIds filter — dependent hoàn toàn vào detail-page parser."""
from auth import get_session
from search import search, fetch_detail
from detail import parse_detail

sess = get_session()

print("=== Search 'Bộ luật Lao động' với EffectStatusIds=0 (tất cả) ===")
results = search(sess, "Bộ luật Lao động", effect_status=0, max_pages=2)
print(f"Tổng: {len(results)} docs")

# Lọc chỉ những doc có title bắt đầu bằng "Bộ luật" hoặc "Luật"
laws = [d for d in results if d["title"].startswith(("Bộ luật", "Luật ", "Bộ Luật"))]
print(f"Lọc title 'Luật/Bộ luật': {len(laws)} docs\n")

for d in laws[:10]:
    print(f"- {d['title'][:90]}")
    print(f"  {d['url']}")

# Fetch detail của top 5 laws và xem status thật
print("\n=== Fetch detail + parse status thật ===")
for d in laws[:5]:
    try:
        html = fetch_detail(sess, d["url"])
        meta = parse_detail(html)
        print(f"\n{d['title'][:80]}")
        print(f"  doc_number = {meta['doc_number']}")
        print(f"  status     = {meta['effect_status_normalized']!r}")
        print(f"  issue/apply= {meta['issue_date']} → {meta['apply_date']}")
        print(f"  expire     = {meta['expire_date']}")
    except Exception as e:
        print(f"  ERR: {e}")
