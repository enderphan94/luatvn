"""End-to-end pipeline: query → search → fetch top N detail → filter → format.

Đây là entry point Phase 2. Dùng khi:
  - Test toàn bộ flow tự động
  - Claude gọi từ skill — sẽ override các tham số market_meaning/legal_meaning/conclusion bằng phân tích của mình

Quy trình:
  1. analyze(query) → keywords mở rộng + domain + cross-laws
  2. search × N keywords × {Còn hiệu lực, Chưa áp dụng}
  3. dedup theo URL
  4. fetch_detail() top K kết quả → parse metadata
  5. filter_and_rank() với scoring + drop "Hết hiệu lực"
  6. format_results() → markdown
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

from analyzer import analyze
from auth import get_session
from ban_an import search_cases
from detail import parse_detail
from filter import filter_and_rank, find_relevant_articles
from formatter import format_results
from search import EFFECT_FUTURE, EFFECT_VALID, fetch_detail, search

EFFECT_ALL = 0  # Site filter cho 'Tất cả' — bypass khi site filter không tin được


@dataclass
class PipelineConfig:
    max_pages_per_keyword: int = 2
    max_detail_fetch: int = 10
    max_keywords: int = 4
    fetch_future: bool = True
    request_delay: float = 1.5
    verbose: bool = True
    # Phase 3: trích article relevant cho top N doc trong mỗi nhóm
    extract_articles_top_n: int = 3   # số doc/nhóm được trích article
    articles_per_doc: int = 3         # số article hiển thị/doc
    # Phase 4: bản án / quyết định
    fetch_cases: bool = True
    max_cases: int = 8                # số bản án hiển thị


# Title prefix giúp phân loại "văn bản gốc" để ưu tiên fetch trước
_PRIMARY_PREFIXES = ("Luật ", "Bộ luật ", "Bộ Luật ", "Pháp lệnh ")


def _is_primary_law(title: str) -> bool:
    return any(title.startswith(p) for p in _PRIMARY_PREFIXES)


def _is_primary_keyword(kw: str) -> bool:
    """Keyword có dạng 'Luật <X>' / 'Bộ luật <X>' — dùng status=0 để bypass site filter."""
    nk = kw.strip().lower()
    return nk.startswith(("luật ", "bộ luật ", "pháp lệnh "))


def run(
    query: str,
    market_meaning: str = "",
    legal_meaning: str = "",
    conclusion: str = "",
    config: PipelineConfig = None,
    session: requests.Session = None,
) -> dict:
    """Chạy full pipeline. Trả {markdown, analysis, grouped, raw_listing, fetched_count}."""
    config = config or PipelineConfig()
    session = session or get_session()

    # 1. Phân tích
    analysis = analyze(query)
    keywords = analysis["expanded_keywords"][: config.max_keywords]
    print(f"[pipeline] domain={analysis['domain']}, keywords={keywords}")

    # 2. Search song song theo keyword × status.
    #    LƯU Ý: Site filter EffectStatusIds=1 KHÔNG TIN ĐƯỢC (đã verify) —
    #    với keyword 'Luật/Bộ luật <X>', dùng EffectStatusIds=0 để site trả luật gốc,
    #    rồi để detail-page parser xác định status thật.
    listing: dict[str, dict] = {}
    for kw in keywords:
        if _is_primary_keyword(kw):
            statuses = [EFFECT_ALL]
        else:
            statuses = [EFFECT_VALID]
            if config.fetch_future:
                statuses.append(EFFECT_FUTURE)
        for stat in statuses:
            label = {EFFECT_ALL: "ALL", EFFECT_VALID: "VALID", EFFECT_FUTURE: "FUTURE"}[stat]
            print(f"[pipeline]   search {kw!r} status={label}")
            results = search(session, kw, stat, max_pages=config.max_pages_per_keyword)
            for d in results:
                url = d["url"]
                if url not in listing:
                    listing[url] = d
            time.sleep(config.request_delay)
    print(f"[pipeline] listing collected: {len(listing)} docs")

    # 3. Top K — ưu tiên Luật/Bộ luật trước, rồi fill bằng prelim score
    from filter import normalize_vi as _norm
    from filter import score as _score
    from datetime import date

    norm_kws = [_norm(k) for k in keywords]
    today = date.today()
    prelim = sorted(
        listing.values(),
        key=lambda d: _score(d, norm_kws, today),
        reverse=True,
    )

    primary = [d for d in prelim if _is_primary_law(d.get("title", ""))]
    secondary = [d for d in prelim if not _is_primary_law(d.get("title", ""))]
    to_fetch = primary + secondary
    to_fetch = to_fetch[: config.max_detail_fetch]
    print(
        f"[pipeline] prelim: {len(prelim)} sorted | primary (Luật/Bộ luật): {len(primary)} "
        f"| fetching detail for top {len(to_fetch)}"
    )
    if config.verbose:
        for d in to_fetch:
            mark = "★" if _is_primary_law(d.get("title", "")) else " "
            print(f"  {mark} {d.get('title', '')[:90]}")

    # 4. Fetch detail + parse
    enriched: list[dict] = []
    for d in to_fetch:
        try:
            html = fetch_detail(session, d["url"])
            meta = parse_detail(html)
            merged = {**d, **meta}
            enriched.append(merged)
            if config.verbose:
                print(
                    f"  ✓ {d.get('doc_number')} → status={meta.get('effect_status_normalized')!r} "
                    f"(issue={meta.get('issue_date')}, expire={meta.get('expire_date')})"
                )
        except Exception as e:
            print(f"[pipeline] WARN fetch {d['url']}: {e}")
            continue

    # 5. Filter + rank
    grouped = filter_and_rank(enriched, keywords)
    print(
        f"[pipeline] grouped: valid={len(grouped['valid'])}, "
        f"future={len(grouped['future'])}, partial={len(grouped['partial'])}"
    )

    # 5b. Trích article relevant cho top N doc của mỗi nhóm
    for group_name, items in grouped.items():
        for d in items[: config.extract_articles_top_n]:
            arts = d.get("articles") or []
            if arts:
                d["relevant_articles"] = find_relevant_articles(
                    arts, keywords, top_n=config.articles_per_doc
                )
            else:
                d["relevant_articles"] = []
        # Drop articles bulk khỏi các doc khác để output gọn
        for d in items[config.extract_articles_top_n:]:
            d.pop("articles", None)

    # 5c. Phase 4: tìm bản án / quyết định liên quan
    cases: list[dict] = []
    if config.fetch_cases:
        try:
            print(f"[pipeline] searching cases for {query!r}")
            cases = search_cases(session, query, max_pages=1)[: config.max_cases]
            print(f"[pipeline] cases: {len(cases)}")
        except Exception as e:
            print(f"[pipeline] WARN cases search: {e}")

    # 6. Format
    markdown = format_results(
        query,
        analysis,
        grouped,
        cases=cases,
        market_meaning=market_meaning,
        legal_meaning=legal_meaning,
        conclusion=conclusion,
    )

    return {
        "markdown": markdown,
        "analysis": analysis,
        "grouped": grouped,
        "cases": cases,
        "raw_listing": listing,
        "fetched_count": len(enriched),
    }


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "thuế thu nhập cá nhân"
    out = run(
        query,
        market_meaning="(test) nghĩa thực tế",
        legal_meaning="(test) nghĩa pháp lý",
        conclusion="(test) kết luận",
        config=PipelineConfig(
            max_pages_per_keyword=1,
            max_detail_fetch=8,
            max_keywords=4,
            fetch_future=False,
        ),
    )
    print("\n" + "=" * 80)
    print(out["markdown"])
