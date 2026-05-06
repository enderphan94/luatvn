"""Test ban_an.py — listing parser, regex extractors."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ban_an import (  # noqa: E402
    _extract_case_id,
    _extract_case_kind,
    _extract_case_number,
    _extract_court_from_title,
    _parse_listing,
)


class TestExtractors(unittest.TestCase):
    def test_case_number(self):
        title = "Bản án số 132/2025/HNGĐ-ST ngày 11/12/2025 của Tòa án..."
        self.assertEqual(_extract_case_number(title), "132/2025/HNGĐ-ST")

    def test_case_number_quyet_dinh(self):
        title = "Quyết định số 22/2025/QĐST-HNGĐ ngày 11/12/2025"
        self.assertEqual(_extract_case_number(title), "22/2025/QĐST-HNGĐ")

    def test_case_number_none(self):
        self.assertIsNone(_extract_case_number("Random title không match"))

    def test_case_id_from_url(self):
        href = "/ban-an/ban-an-132-2025-hngd-st-3-1378801-d11.html"
        self.assertEqual(_extract_case_id(href), "1378801")

    def test_case_kind_d11_d12(self):
        self.assertEqual(
            _extract_case_kind("/ban-an/ban-an-x-d11.html", "Bản án số 1"),
            "Bản án",
        )
        self.assertEqual(
            _extract_case_kind("/ban-an/quyet-dinh-x-d12.html", "Quyết định"),
            "Quyết định",
        )

    def test_case_kind_fallback_from_title(self):
        self.assertEqual(
            _extract_case_kind("/ban-an/no-suffix.html", "Bản án số 1 ngày..."),
            "Bản án",
        )

    def test_court_from_title(self):
        title = "Bản án số 132/2025/HNGĐ-ST ngày 11/12/2025 của Tòa án nhân dân khu vực 8 - Lào Cai, tỉnh Lào Cai về vụ án ly hôn"
        self.assertEqual(
            _extract_court_from_title(title),
            "Tòa án nhân dân khu vực 8 - Lào Cai",
        )

    def test_court_no_match(self):
        self.assertIsNone(_extract_court_from_title("Random title"))


class TestParseListing(unittest.TestCase):
    def test_minimal_article(self):
        html = """
        <article class="post-document">
          <div class="doc-col1"><span class="doc-number">1</span></div>
          <div class="doc-col2">
            <header class="entry-header">
              <h3 class="entry-title">
                <a href="/ban-an/ban-an-1-2025-st-3-9999-d11.html"
                   title="Bản án số 1/2025/HNGĐ-ST ngày 01/01/2025 của Tòa án nhân dân khu vực 1 - Hà Nội về vụ án ly hôn">
                   Bản án số 1
                </a>
              </h3>
            </header>
            <div class="entry-summary searchsummary">Tóm tắt vụ án</div>
            <div class="entry-meta">
              <div class="item-tags">
                <span class="color-darkgray">Loại vụ/việc:</span>
                <a class="link-color" href="#">Hôn nhân gia đình</a>
              </div>
            </div>
          </div>
          <div class="doc-col3">
            <div class="row-info">
              <span class="color-darkgray">Ban hành:</span>
              <span>01/01/2025</span>
            </div>
            <div class="row-info">
              <span class="color-darkgray">Cấp xét xử:</span>
              <span class="link-color">Sơ thẩm</span>
            </div>
          </div>
        </article>
        """
        results = _parse_listing(html)
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r["case_number"], "1/2025/HNGĐ-ST")
        self.assertEqual(r["case_kind"], "Bản án")
        self.assertEqual(r["case_id"], "9999")
        self.assertEqual(r["case_topic"], "Hôn nhân gia đình")
        self.assertEqual(r["issue_date"], "01/01/2025")
        self.assertEqual(r["trial_level"], "Sơ thẩm")
        self.assertEqual(r["court"], "Tòa án nhân dân khu vực 1 - Hà Nội")

    def test_empty_html(self):
        self.assertEqual(_parse_listing("<html></html>"), [])


if __name__ == "__main__":
    unittest.main()
