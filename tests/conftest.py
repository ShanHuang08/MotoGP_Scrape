"""
conftest.py - pytest 共用 fixtures

提供所有測試模組共享的 fixture：
- make_news_item     : 快速建立測試用的 NewsItem
- scraper            : MotoGPScraper 實例
- sample_news_item   : 預建的 NewsItem 樣本
- make_article       : 快速建立測試用的 Article
- sample_article     : 預建的 Article 樣本
- make_extracted     : 快速建立測試用的 ExtractedContent
- make_race_entry    : 快速建立測試用的 RaceEntry
- sample_race_entry  : 預建的 RaceEntry 樣本（匈牙利站）
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from motogp_scraper.models import Article, ExtractedContent, NewsItem, RaceEntry
from motogp_scraper.runner import MotoGPScraper


# ============================================================
# make_news_item fixture - 建立測試用的 NewsItem 工廠函數
# ============================================================
@pytest.fixture
def make_news_item():
    """
    回傳一個工廠函數，用於快速建立測試用的 NewsItem。

    用法：
        item = make_news_item("https://a.com/1")
        item = make_news_item("https://a.com/1", title="Title", discovery_method="html")
    """

    def _factory(
        url: str,
        *,
        source: str = "test",
        title: str = "Test",
        published_at: datetime | None = None,
        discovery_method: str = "rss",
    ) -> NewsItem:
        return NewsItem(
            source=source,
            title=title,
            url=url,
            published_at=published_at or datetime(2024, 1, 1, tzinfo=timezone.utc),
            raw_meta={"discovery_method": discovery_method},
        )

    return _factory


# ============================================================
# sample_news_item fixture - 預建的 NewsItem 樣本
# ============================================================
@pytest.fixture
def sample_news_item(make_news_item) -> NewsItem:
    """預建的 NewsItem 樣本，可直接用於 Article 等測試。"""
    return make_news_item(
        "https://example.com/motogp/news/test-article",
        source="Test Source",
        title="Test MotoGP Article",
        published_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


# ============================================================
# scraper fixture - MotoGPScraper 實例
# ============================================================
@pytest.fixture
def scraper() -> MotoGPScraper:
    """回傳一個 MotoGPScraper 實例，供測試使用。"""
    return MotoGPScraper()


# ============================================================
# make_article fixture - 建立測試用的 Article 工廠函數
# ============================================================
@pytest.fixture
def make_article(make_news_item):
    """
    回傳一個工廠函數，用於快速建立測試用的 Article。

    用法：
        article = make_article()
        article = make_article(text="Hello", extraction_method="trafilatura")
    """

    def _factory(
        *,
        url: str = "https://example.com/news/test",
        title: str = "Test Article",
        text: str = "Article body content.",
        extraction_method: str = "trafilatura",
        extracted_at: datetime | None = None,
        image_url: str | None = None,
    ) -> Article:
        item = make_news_item(url, title=title)
        return Article(
            item=item,
            text=text,
            extraction_method=extraction_method,
            extracted_at=extracted_at or datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            image_url=image_url,
        )

    return _factory


# ============================================================
# sample_article fixture - 預建的 Article 樣本
# ============================================================
@pytest.fixture
def sample_article(make_article) -> Article:
    """預建的 Article 樣本。"""
    return make_article(
        url="https://example.com/motogp/news/sample",
        title="Sample MotoGP News",
        text="This is the article body. It contains multiple sentences for testing.",
        extraction_method="trafilatura",
    )


# ============================================================
# make_extracted fixture - 建立測試用的 ExtractedContent 工廠函數
# ============================================================
@pytest.fixture
def make_extracted():
    """
    回傳一個工廠函數，用於快速建立測試用的 ExtractedContent。

    用法：
        ec = make_extracted()
        ec = make_extracted(text="Hello", method="lxml-paragraph-fallback")
    """

    def _factory(
        text: str = "Extracted text content.",
        method: str = "trafilatura",
    ) -> ExtractedContent:
        return ExtractedContent(text=text, method=method)

    return _factory


# ============================================================
# make_race_entry fixture - 建立測試用的 RaceEntry 工廠函數
# ============================================================
@pytest.fixture
def make_race_entry():
    """
    回傳一個工廠函數，用於快速建立測試用的 RaceEntry。

    用法：
        race = make_race_entry()
        race = make_race_entry(round_number=8, race_date=date(2026, 6, 7))
    """

    def _factory(
        *,
        round_number: int = 8,
        race_date: date | None = None,
        grand_prix: str = "Hungary Grand Prix of Hungary",
        country: str = "Hungary",
    ) -> RaceEntry:
        return RaceEntry(
            round_number=round_number,
            date=race_date or date(2026, 6, 7),
            grand_prix=grand_prix,
            country=country,
        )

    return _factory


# ============================================================
# sample_race_entry fixture - 預建的 RaceEntry 樣本（匈牙利站）
# ============================================================
@pytest.fixture
def sample_race_entry(make_race_entry) -> RaceEntry:
    """預建的 RaceEntry 樣本：2026 Round 8 匈牙利站。"""
    return make_race_entry()
