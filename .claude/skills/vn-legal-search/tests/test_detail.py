"""Test detail.py — status normalization, article parsing."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from detail import _normalize_status, _parse_articles  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402


class TestNormalizeStatus(unittest.TestCase):
    def test_con_hieu_luc(self):
        self.assertEqual(_normalize_status("Còn hiệu lực"), "Còn hiệu lực")
        self.assertEqual(_normalize_status("Có hiệu lực"), "Còn hiệu lực")

    def test_het_hieu_luc(self):
        self.assertEqual(_normalize_status("Hết hiệu lực"), "Hết hiệu lực")
        self.assertEqual(_normalize_status("Hết Hiệu lực"), "Hết hiệu lực")

    def test_het_mot_phan(self):
        self.assertEqual(_normalize_status("Hết hiệu lực một phần"), "Hết hiệu lực một phần")
        self.assertEqual(_normalize_status("Đã sửa đổi"), "Hết hiệu lực một phần")
        self.assertEqual(_normalize_status("Đã được sửa đổi"), "Hết hiệu lực một phần")

    def test_chua_ap_dung(self):
        self.assertEqual(_normalize_status("Chưa áp dụng"), "Chưa áp dụng")
        self.assertEqual(_normalize_status("Chưa có hiệu lực"), "Chưa áp dụng")

    def test_none_or_empty(self):
        self.assertIsNone(_normalize_status(None))
        self.assertIsNone(_normalize_status(""))

    def test_unknown_returns_raw(self):
        self.assertEqual(_normalize_status("Trạng thái lạ"), "Trạng thái lạ")


class TestParseArticles(unittest.TestCase):
    def _soup(self, body: str):
        return BeautifulSoup(
            f"<html><body><div class='tab-noi-dung'>{body}</div></body></html>",
            "lxml",
        )

    def test_basic_articles(self):
        body = """
        <p>Điều 1. Phạm vi điều chỉnh
        Văn bản này quy định về A B C.</p>
        <p>Điều 2. Đối tượng áp dụng
        Áp dụng đối với X Y Z.</p>
        """
        arts = _parse_articles(self._soup(body))
        self.assertEqual(len(arts), 2)
        self.assertEqual(arts[0]["number"], "1")
        self.assertEqual(arts[0]["title"], "Phạm vi điều chỉnh")
        self.assertIn("A B C", arts[0]["body"])
        self.assertEqual(arts[1]["number"], "2")

    def test_filter_inline_references(self):
        """'Điều 51 Luật Quản lý thuế' không period → không match. Nếu match nhầm thì
        title bắt đầu 'Luật ' phải bị loại."""
        body = """
        <p>Điều 1. Nội dung
        Theo Điều 51. Luật Quản lý thuế quy định...</p>
        """
        arts = _parse_articles(self._soup(body))
        # Article 1 vẫn vào, nhưng article 51 (false positive) phải bị filter
        nums = [a["number"] for a in arts]
        self.assertIn("1", nums)
        # Nếu '51' được match (do period), title sẽ là 'Luật Quản lý thuế' → bị filter
        self.assertNotIn("51", nums)

    def test_handles_newline_between_number_and_period(self):
        """'Điều 5\n. Title' phải match."""
        body = "<p>Điều 5\n. Title của Điều 5\nNội dung điều 5.</p>"
        arts = _parse_articles(self._soup(body))
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0]["number"], "5")

    def test_dedup_by_number(self):
        """Cùng 1 article xuất hiện 2 lần (TOC + nội dung) → giữ bản dài hơn."""
        body = """
        <p>Điều 1. Phạm vi</p>
        <p>Điều 1. Phạm vi
        Đây là nội dung đầy đủ rất dài có nhiều thông tin chi tiết.</p>
        """
        arts = _parse_articles(self._soup(body))
        self.assertEqual(len(arts), 1)
        self.assertIn("nội dung đầy đủ", arts[0]["body"])

    def test_no_container(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        self.assertEqual(_parse_articles(soup), [])

    def test_alphabetic_suffix(self):
        """'Điều 28A. ...' phải hỗ trợ."""
        body = "<p>Điều 28A. Title nâng cao</p>"
        arts = _parse_articles(self._soup(body))
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0]["number"], "28A")


if __name__ == "__main__":
    unittest.main()
