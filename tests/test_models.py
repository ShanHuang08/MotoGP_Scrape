"""
test_models.py - 資料模型的單元測試 (pytest)

測試範圍：
- Article          : frozen dataclass 唯讀性 + 欄位存取
- ExtractedContent : frozen dataclass 唯讀性 + 欄位存取
- RaceEntry        : frozen dataclass 唯讀性 + 欄位存取

執行方式：
    python main.py --unit-test
    或
    pytest tests/test_models.py -v
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone

import pytest

from motogp_scraper.models import Article, ExtractedContent, NewsItem, RaceEntry


# ============================================================
# Article 測試
# ============================================================
class TestArticle:
    """Article - 完整文章資料結構"""

    def test_field_access(self, sample_article: Article) -> None:
        """欄位可正確存取"""
        assert sample_article.item is not None
        assert isinstance(sample_article.item, NewsItem)
        assert sample_article.text == "This is the article body. It contains multiple sentences for testing."
        assert sample_article.extraction_method == "trafilatura"
        assert isinstance(sample_article.extracted_at, datetime)

    def test_frozen_raises_on_set_text(self, sample_article: Article) -> None:
        """frozen=True 設定 text 欄位應拋出 FrozenInstanceError"""
        with pytest.raises(FrozenInstanceError):
            sample_article.text = "changed"  # type: ignore[misc]

    def test_frozen_raises_on_set_method(self, sample_article: Article) -> None:
        """frozen=True 設定 extraction_method 欄位應拋出 FrozenInstanceError"""
        with pytest.raises(FrozenInstanceError):
            sample_article.extraction_method = "changed"  # type: ignore[misc]

    def test_frozen_raises_on_set_item(self, sample_article: Article) -> None:
        """frozen=True 設定 item 欄位應拋出 FrozenInstanceError"""
        with pytest.raises(FrozenInstanceError):
            sample_article.item = None  # type: ignore[misc]

    def test_nested_news_item_fields(self, sample_article: Article) -> None:
        """Article 內的 NewsItem 欄位可正確存取"""
        item = sample_article.item
        assert item.source == "test"
        assert item.title == "Sample MotoGP News"
        assert item.url == "https://example.com/motogp/news/sample"

    def test_custom_article(self, make_article) -> None:
        """用 make_article fixture 自訂 Article"""
        article = make_article(
            text="Custom body",
            extraction_method="lxml-paragraph-fallback",
        )
        assert article.text == "Custom body"
        assert article.extraction_method == "lxml-paragraph-fallback"

    @pytest.mark.parametrize(
        "method",
        ["trafilatura", "gpone-lxml-sections", "lxml-paragraph-fallback", "empty"],
        ids=["trafilatura", "gpone", "lxml-fallback", "empty"],
    )
    def test_various_extraction_methods(self, make_article, method: str) -> None:
        """參數化測試：不同提取方法都能正確存入"""
        article = make_article(extraction_method=method)
        assert article.extraction_method == method

    def test_empty_text_article(self, make_article) -> None:
        """空文字 Article 可正常建立"""
        article = make_article(text="", extraction_method="empty")
        assert article.text == ""


# ============================================================
# ExtractedContent 測試
# ============================================================
class TestExtractedContent:
    """ExtractedContent - 文章內文提取的中間結果"""

    def test_field_access(self, make_extracted) -> None:
        """欄位可正確存取"""
        ec = make_extracted(text="Hello world", method="trafilatura")
        assert ec.text == "Hello world"
        assert ec.method == "trafilatura"

    def test_frozen_raises_on_set_text(self, make_extracted) -> None:
        """frozen=True 設定 text 應拋出 FrozenInstanceError"""
        ec = make_extracted()
        with pytest.raises(FrozenInstanceError):
            ec.text = "changed"  # type: ignore[misc]

    def test_frozen_raises_on_set_method(self, make_extracted) -> None:
        """frozen=True 設定 method 應拋出 FrozenInstanceError"""
        ec = make_extracted()
        with pytest.raises(FrozenInstanceError):
            ec.method = "changed"  # type: ignore[misc]

    def test_empty_text(self) -> None:
        """空文字 ExtractedContent"""
        ec = ExtractedContent(text="", method="empty")
        assert ec.text == ""
        assert ec.method == "empty"

    @pytest.mark.parametrize(
        "method",
        ["trafilatura", "gpone-lxml-sections", "lxml-paragraph-fallback", "empty"],
        ids=["trafilatura", "gpone", "lxml-fallback", "empty"],
    )
    def test_various_methods(self, method: str) -> None:
        """參數化測試：不同提取方法名稱都能正確存入"""
        ec = ExtractedContent(text="test", method=method)
        assert ec.method == method

    def test_equality(self) -> None:
        """相同內容的 ExtractedContent 相等"""
        a = ExtractedContent(text="hello", method="trafilatura")
        b = ExtractedContent(text="hello", method="trafilatura")
        assert a == b

    def test_inequality_text(self) -> None:
        """不同文字內容不相等"""
        a = ExtractedContent(text="hello", method="trafilatura")
        b = ExtractedContent(text="world", method="trafilatura")
        assert a != b

    def test_inequality_method(self) -> None:
        """不同方法不相等"""
        a = ExtractedContent(text="hello", method="trafilatura")
        b = ExtractedContent(text="hello", method="empty")
        assert a != b


# ============================================================
# RaceEntry 測試
# ============================================================
class TestRaceEntry:
    """RaceEntry - MotoGP 賽程行事曆的單一賽站資料"""

    def test_field_access(self, sample_race_entry: RaceEntry) -> None:
        """欄位可正確存取"""
        assert sample_race_entry.round_number == 8
        assert sample_race_entry.date == date(2026, 6, 7)
        assert sample_race_entry.grand_prix == "Hungary Grand Prix of Hungary"
        assert sample_race_entry.country == "Hungary"

    def test_frozen_raises_on_set_round(self, sample_race_entry: RaceEntry) -> None:
        """frozen=True 設定 round_number 應拋出 FrozenInstanceError"""
        with pytest.raises(FrozenInstanceError):
            sample_race_entry.round_number = 1  # type: ignore[misc]

    def test_frozen_raises_on_set_date(self, sample_race_entry: RaceEntry) -> None:
        """frozen=True 設定 date 應拋出 FrozenInstanceError"""
        with pytest.raises(FrozenInstanceError):
            sample_race_entry.date = date(2026, 1, 1)  # type: ignore[misc]

    def test_frozen_raises_on_set_gp(self, sample_race_entry: RaceEntry) -> None:
        """frozen=True 設定 grand_prix 應拋出 FrozenInstanceError"""
        with pytest.raises(FrozenInstanceError):
            sample_race_entry.grand_prix = "changed"  # type: ignore[misc]

    def test_custom_race_entry(self, make_race_entry) -> None:
        """用 make_race_entry fixture 自訂 RaceEntry"""
        race = make_race_entry(
            round_number=1,
            race_date=date(2026, 3, 1),
            grand_prix="Thailand PT Grand Prix of Thailand",
            country="Thailand",
        )
        assert race.round_number == 1
        assert race.country == "Thailand"

    @pytest.mark.parametrize(
        "round_number, race_date, country",
        [
            (1, date(2026, 3, 1), "Thailand"),
            (8, date(2026, 6, 7), "Hungary"),
            (22, date(2026, 11, 29), "Valencian Community"),
        ],
        ids=["round-1", "round-8", "round-22"],
    )
    def test_various_races(
        self, make_race_entry, round_number: int, race_date: date, country: str
    ) -> None:
        """參數化測試：不同站號和日期的 RaceEntry"""
        race = make_race_entry(round_number=round_number, race_date=race_date, country=country)
        assert race.round_number == round_number
        assert race.date == race_date
        assert race.country == country

    def test_equality(self, make_race_entry) -> None:
        """相同內容的 RaceEntry 相等"""
        a = make_race_entry(round_number=8, race_date=date(2026, 6, 7))
        b = make_race_entry(round_number=8, race_date=date(2026, 6, 7))
        assert a == b

    def test_inequality(self, make_race_entry) -> None:
        """不同站號的 RaceEntry 不相等"""
        a = make_race_entry(round_number=8)
        b = make_race_entry(round_number=9)
        assert a != b
