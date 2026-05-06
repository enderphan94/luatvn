"""Test analyzer.py — keyword expansion, domain detection, parent law mapping."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer import analyze, detect_domain, expand_keywords, get_cross_laws  # noqa: E402


class TestExpandKeywords(unittest.TestCase):
    def test_includes_original(self):
        out = expand_keywords("thuế thu nhập cá nhân")
        self.assertIn("thuế thu nhập cá nhân", out)

    def test_parent_law_mapping(self):
        """Topic có PARENT_LAW_MAPPING → tên Luật được thêm."""
        out = expand_keywords("ly hôn đơn phương")
        self.assertTrue(any("Hôn nhân và Gia đình" in k for k in out))

    def test_synonym_expansion(self):
        out = expand_keywords("thuế thu nhập cá nhân")
        self.assertTrue(any("TNCN" in k for k in out))

    def test_no_duplicate_normalized(self):
        out = expand_keywords("Luật Thuế thu nhập cá nhân")
        # Original starts with "Luật ", không thêm "Luật <X>" prefix nữa
        normalized = [k.lower() for k in out]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_max_5_keywords(self):
        out = expand_keywords("hợp đồng lao động")
        self.assertLessEqual(len(out), 5)

    def test_fallback_luat_prefix(self):
        """Topic không trong mapping → fallback 'Luật <query>'."""
        out = expand_keywords("một topic không tồn tại")
        self.assertTrue(any(k.startswith("Luật ") for k in out))


class TestDetectDomain(unittest.TestCase):
    def test_thue(self):
        self.assertEqual(detect_domain("thuế thu nhập cá nhân"), "thuế")
        self.assertEqual(detect_domain("VAT GTGT"), "thuế")

    def test_lao_dong(self):
        self.assertEqual(detect_domain("hợp đồng lao động"), "lao động")
        self.assertEqual(detect_domain("làm thêm giờ"), "lao động")
        self.assertEqual(detect_domain("sa thải"), "lao động")

    def test_hon_nhan(self):
        self.assertEqual(detect_domain("ly hôn đơn phương"), "hôn nhân")
        self.assertEqual(detect_domain("kết hôn"), "hôn nhân")

    def test_hinh_su(self):
        self.assertEqual(detect_domain("trộm cắp tài sản"), "hình sự")
        self.assertEqual(detect_domain("tội phạm"), "hình sự")

    def test_default(self):
        # Query không match domain nào → default 'dân sự'
        self.assertEqual(detect_domain("xyz123 không match"), "dân sự")


class TestGetCrossLaws(unittest.TestCase):
    def test_known_domain(self):
        out = get_cross_laws("thuế")
        self.assertGreater(len(out), 0)
        self.assertTrue(any("Quản lý thuế" in c["name"] for c in out))

    def test_unknown_domain(self):
        self.assertEqual(get_cross_laws("nonexistent"), [])


class TestAnalyze(unittest.TestCase):
    def test_full_pipeline(self):
        a = analyze("sa thải lao động")
        self.assertEqual(a["domain"], "lao động")
        self.assertGreater(len(a["expanded_keywords"]), 1)
        self.assertGreater(len(a["cross_laws"]), 0)
        self.assertEqual(a["query"], "sa thải lao động")


if __name__ == "__main__":
    unittest.main()
