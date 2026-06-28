"""
test_runner.py - 爬蟲主控制器私有方法的單元測試 (pytest)

測試範圍（第一梯隊）：
- _dedupe_by_url()          : URL 去重 + 末尾斜線正規化
- _select_weighted_latest() : RSS/HTML 加權選取 + 溢出補足
- _is_rss_item()            : 判斷是否為 RSS 來源

執行方式：
    python main.py --unit-test
    或
    pytest tests/test_runner.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from motogp_scraper.models import NewsItem
from motogp_scraper.runner import BlockedArticleError, MotoGPScraper


# ============================================================
# _dedupe_by_url 測試
# ============================================================
class TestDedupeByUrl:
    """_dedupe_by_url - 以 URL 去重"""

    def test_no_duplicates(self, scraper: MotoGPScraper, make_news_item) -> None:
        """沒有重複 URL 時，全部保留"""
        items = [make_news_item("https://a.com/1"), make_news_item("https://a.com/2")]
        result = scraper._dedupe_by_url(items)
        assert len(result) == 2

    def test_removes_exact_duplicates(self, scraper: MotoGPScraper, make_news_item) -> None:
        """完全相同的 URL 只保留第一個"""
        items = [make_news_item("https://a.com/1"), make_news_item("https://a.com/1")]
        result = scraper._dedupe_by_url(items)
        assert len(result) == 1
        assert result[0].url == "https://a.com/1"

    def test_trailing_slash_normalization(self, scraper: MotoGPScraper, make_news_item) -> None:
        """末尾有無 / 視為同一個 URL"""
        items = [make_news_item("https://a.com/1"), make_news_item("https://a.com/1/")]
        result = scraper._dedupe_by_url(items)
        assert len(result) == 1

    def test_keeps_first_occurrence(self, scraper: MotoGPScraper, make_news_item) -> None:
        """重複時保留第一個出現的項目"""
        item_a = make_news_item("https://a.com/1", title="First")
        item_b = make_news_item("https://a.com/1/", title="Second")
        result = scraper._dedupe_by_url([item_a, item_b])
        assert len(result) == 1
        assert result[0].title == "First"

    def test_empty_list(self, scraper: MotoGPScraper) -> None:
        """空列表回傳空列表"""
        assert scraper._dedupe_by_url([]) == []

    def test_many_duplicates(self, scraper: MotoGPScraper, make_news_item) -> None:
        """多個重複項目，只保留唯一 URL"""
        items = [
            make_news_item("https://a.com/1"),
            make_news_item("https://a.com/2"),
            make_news_item("https://a.com/1"),
            make_news_item("https://a.com/2/"),
            make_news_item("https://a.com/3"),
        ]
        result = scraper._dedupe_by_url(items)
        assert len(result) == 3


class TestFetchArticle:
    """fetch_article - article body fetching and filtering."""

    def test_blocked_page_raises_without_article(
        self, scraper: MotoGPScraper, make_news_item, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            MotoGPScraper,
            "_fetch_blocked_article_with_browser",
            staticmethod(lambda url: None),
        )
        item = make_news_item(
            "https://www.gpone.com/it/2026/06/23/motogp/example.html",
            discovery_method="html",
        )
        item.raw_meta["article_markup"] = """
        <html>
          <head><title>Just a moment...</title></head>
          <body>Enable JavaScript and cookies to continue</body>
        </html>
        """

        with pytest.raises(BlockedArticleError):
            scraper.fetch_article(item)

    def test_gpone_blocked_page_uses_browser_fallback(
        self, scraper: MotoGPScraper, make_news_item, monkeypatch
    ) -> None:
        fallback_html = """
        <html><body>
        <div id="block-gpone-content">
            <article><div>
                <section><div></div><div><p>Recovered GPone article body.</p></div></section>
            </div></article>
        </div>
        </body></html>
        """
        monkeypatch.setattr(
            MotoGPScraper,
            "_fetch_blocked_article_with_browser",
            staticmethod(lambda url: fallback_html),
        )
        item = make_news_item(
            "https://www.gpone.com/it/2026/06/23/motogp/example.html",
            discovery_method="html",
        )
        item.raw_meta["article_markup"] = """
        <html>
          <head><title>Just a moment...</title></head>
          <body>Enable JavaScript and cookies to continue</body>
        </html>
        """

        article = scraper.fetch_article(item)

        assert article.extraction_method == "gpone-lxml-sections"
        assert article.text == "Recovered GPone article body."


# ============================================================
# _select_weighted_latest 測試
# ============================================================
class TestSelectWeightedLatest:
    """_select_weighted_latest - RSS/HTML 加權選取"""

    @pytest.mark.parametrize("limit", [0, -1, -100], ids=["zero", "neg1", "neg100"])
    def test_non_positive_limit_returns_empty(
        self, scraper: MotoGPScraper, make_news_item, limit: int
    ) -> None:
        """limit <= 0 回傳空列表"""
        items = [make_news_item("https://a.com/1")]
        assert scraper._select_weighted_latest(items, limit=limit) == []

    def test_fewer_items_than_limit(self, scraper: MotoGPScraper, make_news_item) -> None:
        """項目少於 limit 時，全部回傳"""
        items = [
            make_news_item("https://a.com/1", discovery_method="rss"),
            make_news_item("https://a.com/2", discovery_method="html"),
        ]
        result = scraper._select_weighted_latest(items, limit=10)
        assert len(result) == 2

    def test_rss_items_prioritized(self, scraper: MotoGPScraper, make_news_item) -> None:
        """RSS 來源佔比 50%，10 筆中應有 5 筆 RSS"""
        rss_items = [
            make_news_item(
                f"https://rss.com/{i}",
                discovery_method="rss",
                published_at=datetime(2024, 1, 1, i, 0, tzinfo=timezone.utc),
            )
            for i in range(10)
        ]
        html_items = [
            make_news_item(
                f"https://html.com/{i}",
                discovery_method="html",
                published_at=datetime(2024, 1, 1, i, 0, tzinfo=timezone.utc),
            )
            for i in range(10)
        ]
        result = scraper._select_weighted_latest(rss_items + html_items, limit=10)
        rss_count = sum(1 for item in result if item.raw_meta.get("discovery_method") == "rss")
        assert rss_count == 5

    def test_overflow_from_rss_to_html(self, scraper: MotoGPScraper, make_news_item) -> None:
        """RSS 不夠時，溢出給 HTML 補足"""
        rss_items = [
            make_news_item("https://rss.com/1", discovery_method="rss"),
            make_news_item("https://rss.com/2", discovery_method="rss"),
        ]
        html_items = [
            make_news_item(
                f"https://html.com/{i}",
                discovery_method="html",
                published_at=datetime(2024, 1, 1, i, 0, tzinfo=timezone.utc),
            )
            for i in range(10)
        ]
        result = scraper._select_weighted_latest(rss_items + html_items, limit=10)
        assert len(result) == 10

    def test_overflow_from_html_to_rss(self, scraper: MotoGPScraper, make_news_item) -> None:
        """HTML 不夠時，溢出給 RSS 補足"""
        rss_items = [
            make_news_item(
                f"https://rss.com/{i}",
                discovery_method="rss",
                published_at=datetime(2024, 1, 1, i, 0, tzinfo=timezone.utc),
            )
            for i in range(10)
        ]
        html_items = [make_news_item("https://html.com/1", discovery_method="html")]
        result = scraper._select_weighted_latest(rss_items + html_items, limit=10)
        assert len(result) == 10

    def test_result_sorted_by_time_desc(self, scraper: MotoGPScraper, make_news_item) -> None:
        """結果按 UTC+8 時間降序排列（最新在前）"""
        items = [
            make_news_item(
                "https://a.com/1",
                published_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            ),
            make_news_item(
                "https://a.com/2",
                published_at=datetime(2024, 1, 1, 20, 0, tzinfo=timezone.utc),
            ),
            make_news_item(
                "https://a.com/3",
                published_at=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            ),
        ]
        result = scraper._select_weighted_latest(items, limit=3)
        urls = [item.url for item in result]
        assert urls == ["https://a.com/2", "https://a.com/3", "https://a.com/1"]

    def test_empty_items_returns_empty(self, scraper: MotoGPScraper) -> None:
        """空列表回傳空列表"""
        assert scraper._select_weighted_latest([], limit=10) == []

    @pytest.mark.parametrize(
        "method", ["rss", "html"], ids=["only-rss", "only-html"]
    )
    def test_single_source_type(
        self, scraper: MotoGPScraper, make_news_item, method: str
    ) -> None:
        """全部是同一種類型的項目時正常運作"""
        items = [
            make_news_item(f"https://{method}.com/{i}", discovery_method=method)
            for i in range(5)
        ]
        result = scraper._select_weighted_latest(items, limit=3)
        assert len(result) == 3

    def test_lower_weight_sources_are_capped_for_limit_10(
        self, scraper: MotoGPScraper, make_news_item
    ) -> None:
        items = []
        for index in range(5):
            items.append(
                make_news_item(
                    f"https://motogpnews.com/{index}",
                    source="MotoGPNews",
                    discovery_method="rss",
                    published_at=datetime(2024, 1, 2, index, tzinfo=timezone.utc),
                )
            )
            items.append(
                make_news_item(
                    f"https://crash.net/{index}",
                    source="Crash.net MotoGP",
                    discovery_method="rss",
                    published_at=datetime(2024, 1, 1, index, tzinfo=timezone.utc),
                )
            )
            items.append(
                make_news_item(
                    f"https://the-race.com/{index}",
                    source="The Race MotoGP",
                    discovery_method="html",
                    published_at=datetime(2024, 1, 2, index, tzinfo=timezone.utc),
                )
            )
            items.append(
                make_news_item(
                    f"https://gpone.com/{index}",
                    source="GPone MotoGP EN",
                    discovery_method="html",
                    published_at=datetime(2024, 1, 1, index, tzinfo=timezone.utc),
                )
            )

        result = scraper._select_weighted_latest(items, limit=10)
        assert len(result) == 10
        assert sum(1 for item in result if item.source == "MotoGPNews") == 1
        assert sum(1 for item in result if item.source == "The Race MotoGP") == 1

    def test_lower_weight_sources_can_reach_three_for_limit_20(
        self, scraper: MotoGPScraper, make_news_item
    ) -> None:
        items = []
        for index in range(10):
            items.append(
                make_news_item(
                    f"https://motogpnews.com/{index}",
                    source="MotoGPNews",
                    discovery_method="rss",
                    published_at=datetime(2024, 1, 2, index, tzinfo=timezone.utc),
                )
            )
            items.append(
                make_news_item(
                    f"https://motorsport.com/{index}",
                    source="Motorsport.com MotoGP",
                    discovery_method="rss",
                    published_at=datetime(2024, 1, 1, index, tzinfo=timezone.utc),
                )
            )
            items.append(
                make_news_item(
                    f"https://the-race.com/{index}",
                    source="The Race MotoGP",
                    discovery_method="html",
                    published_at=datetime(2024, 1, 2, index, tzinfo=timezone.utc),
                )
            )
            items.append(
                make_news_item(
                    f"https://gpone.com/{index}",
                    source="GPone MotoGP EN",
                    discovery_method="html",
                    published_at=datetime(2024, 1, 1, index, tzinfo=timezone.utc),
                )
            )

        result = scraper._select_weighted_latest(items, limit=20)
        assert len(result) == 20
        assert sum(1 for item in result if item.source == "MotoGPNews") == 3
        assert sum(1 for item in result if item.source == "The Race MotoGP") == 3

    def test_low_weight_source_without_date_does_not_overflow(
        self, scraper: MotoGPScraper
    ) -> None:
        item = NewsItem(
            source="The Race MotoGP",
            title="No date",
            url="https://www.the-race.com/motogp/no-date/",
            published_at=None,
            raw_meta={"discovery_method": "html"},
        )

        assert scraper._sort_selection_priority(item) == datetime.min.replace(
            tzinfo=timezone.utc
        )


# ============================================================
# _is_rss_item 測試
# ============================================================
class TestIsRssItem:
    """_is_rss_item - 判斷是否為 RSS 來源"""

    def test_rss_item_returns_true(self, make_news_item) -> None:
        """discovery_method='rss' 回傳 True"""
        item = make_news_item("https://a.com/1", discovery_method="rss")
        assert MotoGPScraper._is_rss_item(item) is True

    def test_html_item_returns_false(self, make_news_item) -> None:
        """discovery_method='html' 回傳 False"""
        item = make_news_item("https://a.com/1", discovery_method="html")
        assert MotoGPScraper._is_rss_item(item) is False

    def test_empty_meta_returns_false(self) -> None:
        """空 raw_meta 回傳 False"""
        item = NewsItem(source="test", title="Test", url="https://a.com/1", raw_meta={})
        assert MotoGPScraper._is_rss_item(item) is False
