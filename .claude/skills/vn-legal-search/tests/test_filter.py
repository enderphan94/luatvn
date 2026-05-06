"""Test filter.py — scoring, normalization, drop expired, ranking."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from filter import (  # noqa: E402
    GROUP_FUTURE,
    GROUP_PARTIAL,
    GROUP_VALID,
    filter_and_rank,
    find_relevant_articles,
    normalize_vi,
    score,
)


class TestNormalizeVi(unittest.TestCase):
    def test_strip_diacritics(self):
        self.assertEqual(normalize_vi("Đường"), "duong")
        self.assertEqual(normalize_vi("Việt Nam"), "viet nam")
        self.assertEqual(normalize_vi("HÔN NHÂN"), "hon nhan")

    def test_idempotent(self):
        s = normalize_vi("thuế thu nhập cá nhân")
        self.assertEqual(normalize_vi(s), s)

    def test_special_d(self):
        self.assertEqual(normalize_vi("Đảng Cộng sản"), "dang cong san")

    def test_empty(self):
        self.assertEqual(normalize_vi(""), "")
        self.assertEqual(normalize_vi(None), "")


class TestScore(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 5, 6)
        self.kws = [normalize_vi("thuế thu nhập cá nhân"), normalize_vi("TNCN")]

    def test_perfect_match(self):
        d = {
            "title": "Luật Thuế thu nhập cá nhân 2025 TNCN",
            "doc_type": "Luật",
            "issue_date": "10/12/2025",
            "summary_text": "thuế thu nhập cá nhân TNCN",
        }
        s = score(d, self.kws, self.today)
        # Title match cả 2 kw + Luật (20) + recent (~20) + summary (20)
        self.assertGreater(s, 90)

    def test_high_relevance_partial_kw(self):
        """Title chỉ chứa 1/2 keyword (tự nhiên với synonyms như TNCN)."""
        d = {
            "title": "Luật Thuế thu nhập cá nhân 2025",
            "doc_type": "Luật",
            "issue_date": "10/12/2025",
            "summary_text": "thuế thu nhập cá nhân TNCN",
        }
        s = score(d, self.kws, self.today)
        # Title 1/2 + type 20 + recency ~20 + summary 2/2 = ~75-80
        self.assertGreater(s, 70)
        self.assertLess(s, 85)

    def test_old_doc_lower_recency(self):
        d_old = {
            "title": "Luật Thuế thu nhập cá nhân 2007",
            "doc_type": "Luật",
            "issue_date": "21/11/2007",
            "summary_text": "thuế",
        }
        d_new = {
            "title": "Luật Thuế thu nhập cá nhân 2025",
            "doc_type": "Luật",
            "issue_date": "10/12/2025",
            "summary_text": "thuế",
        }
        self.assertLess(score(d_old, self.kws, self.today), score(d_new, self.kws, self.today))

    def test_type_hierarchy(self):
        base = {
            "title": "X về thuế thu nhập cá nhân",
            "issue_date": "01/01/2024",
            "summary_text": "thuế",
        }
        s_luat = score({**base, "doc_type": "Luật"}, self.kws, self.today)
        s_thongtu = score({**base, "doc_type": "Thông tư"}, self.kws, self.today)
        s_unknown = score({**base, "doc_type": None}, self.kws, self.today)
        self.assertGreater(s_luat, s_thongtu)
        self.assertGreater(s_thongtu, s_unknown)

    def test_no_keyword_match(self):
        d = {
            "title": "Luật Đất đai",
            "doc_type": "Luật",
            "issue_date": "01/01/2024",
            "summary_text": "không có gì",
        }
        s = score(d, self.kws, self.today)
        # Vẫn có type 20 + recency, nhưng title=0, summary=0
        self.assertLess(s, 50)


class TestFilterAndRank(unittest.TestCase):
    def test_drop_expired(self):
        docs = [
            {"title": "Luật A", "doc_number": "1/2007", "doc_type": "Luật",
             "effect_status_normalized": "Còn hiệu lực", "issue_date": "01/01/2024"},
            {"title": "Luật B", "doc_number": "2/2010", "doc_type": "Luật",
             "effect_status_normalized": "Hết hiệu lực", "issue_date": "01/01/2024"},
            {"title": "Luật C", "doc_number": "3/2025", "doc_type": "Luật",
             "effect_status_normalized": "Chưa áp dụng", "issue_date": "01/01/2025"},
        ]
        out = filter_and_rank(docs, ["luật"])
        valid_titles = [d["title"] for d in out[GROUP_VALID]]
        self.assertIn("Luật A", valid_titles)
        self.assertNotIn("Luật B", valid_titles)  # bị drop
        self.assertNotIn("Luật B", [d["title"] for d in out[GROUP_FUTURE]])
        self.assertIn("Luật C", [d["title"] for d in out[GROUP_FUTURE]])

    def test_partial_group(self):
        docs = [
            {"title": "Luật X", "doc_number": "1/2019", "doc_type": "Luật",
             "effect_status_normalized": "Hết hiệu lực một phần",
             "issue_date": "01/01/2019"},
        ]
        out = filter_and_rank(docs, ["luật"])
        self.assertEqual(len(out[GROUP_PARTIAL]), 1)
        self.assertEqual(len(out[GROUP_VALID]), 0)

    def test_dedup_by_doc_number(self):
        docs = [
            {"title": "Luật A v1", "doc_number": "1/2024", "doc_type": "Luật",
             "effect_status_normalized": "Còn hiệu lực", "issue_date": "01/01/2024"},
            {"title": "Luật A v2", "doc_number": "1/2024", "doc_type": "Luật",
             "effect_status_normalized": "Còn hiệu lực", "issue_date": "01/01/2024"},
        ]
        out = filter_and_rank(docs, ["luật"])
        self.assertEqual(len(out[GROUP_VALID]), 1)

    def test_fallback_to_filter_label(self):
        """Nếu effect_status_normalized=None nhưng listing đến từ filter Còn hiệu lực → giữ."""
        docs = [
            {"title": "Luật Y", "doc_number": "5/2024", "doc_type": "Luật",
             "effect_status_normalized": None,
             "effect_status_filter": "Còn hiệu lực",
             "issue_date": "01/01/2024"},
        ]
        out = filter_and_rank(docs, ["luật"])
        self.assertEqual(len(out[GROUP_VALID]), 1)

    def test_sorted_by_score_desc(self):
        docs = [
            {"title": "Luật A không match", "doc_number": "1/2010",
             "doc_type": "Thông tư", "effect_status_normalized": "Còn hiệu lực",
             "issue_date": "01/01/2010"},
            {"title": "Luật ly hôn đầy đủ", "doc_number": "2/2025",
             "doc_type": "Luật", "effect_status_normalized": "Còn hiệu lực",
             "issue_date": "01/01/2025"},
        ]
        out = filter_and_rank(docs, ["ly hôn"])
        self.assertEqual(out[GROUP_VALID][0]["title"], "Luật ly hôn đầy đủ")


class TestFindRelevantArticles(unittest.TestCase):
    def test_returns_top_n(self):
        articles = [
            {"number": "1", "title": "Phạm vi", "body": "không liên quan"},
            {"number": "98", "title": "Tiền lương làm thêm giờ", "body": "rate 150% 200% 300%"},
            {"number": "125", "title": "Sa thải", "body": "trộm cắp đánh bạc"},
        ]
        out = find_relevant_articles(articles, ["làm thêm giờ"], top_n=2)
        self.assertEqual(len(out), 1)  # chỉ 1 article match
        self.assertEqual(out[0]["number"], "98")

    def test_min_score_filter(self):
        articles = [
            {"number": "1", "title": "X", "body": "Y"},
        ]
        out = find_relevant_articles(articles, ["khong match"], min_score=0.5)
        self.assertEqual(len(out), 0)

    def test_empty_input(self):
        self.assertEqual(find_relevant_articles([], ["x"]), [])
        self.assertEqual(find_relevant_articles([{"number": "1"}], []), [])


if __name__ == "__main__":
    unittest.main()
