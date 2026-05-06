"""CLI wrapper cho pipeline. Cho phép gọi từ slash command hoặc shell.

Usage:
    cli.py --query "thuế thu nhập cá nhân" \
           [--market-meaning "..."] \
           [--legal-meaning "..."] \
           [--conclusion "..."] \
           [--max-pages 2] [--max-fetch 10] \
           [--no-future] [--quiet]
"""
from __future__ import annotations

import argparse
import sys

from pipeline import PipelineConfig, run


def main() -> int:
    p = argparse.ArgumentParser(description="Tra cứu văn bản pháp luật Việt Nam")
    p.add_argument("--query", required=True, help="Từ khóa tra cứu")
    p.add_argument("--market-meaning", default="", help="Nghĩa thực tế thị trường")
    p.add_argument("--legal-meaning", default="", help="Nghĩa pháp lý chính thức")
    p.add_argument("--conclusion", default="", help="Kết luận tổng hợp")
    p.add_argument("--max-pages", type=int, default=2, help="Số trang search/keyword")
    p.add_argument("--max-fetch", type=int, default=10, help="Số doc fetch detail")
    p.add_argument("--max-keywords", type=int, default=3, help="Số keyword tối đa")
    p.add_argument("--no-future", action="store_true", help="Bỏ qua 'Chưa áp dụng'")
    p.add_argument("--quiet", action="store_true", help="Tắt log pipeline")
    args = p.parse_args()

    cfg = PipelineConfig(
        max_pages_per_keyword=args.max_pages,
        max_detail_fetch=args.max_fetch,
        max_keywords=args.max_keywords,
        fetch_future=not args.no_future,
        verbose=not args.quiet,
    )

    result = run(
        query=args.query,
        market_meaning=args.market_meaning,
        legal_meaning=args.legal_meaning,
        conclusion=args.conclusion,
        config=cfg,
    )

    print("\n" + "=" * 80)
    print(result["markdown"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
