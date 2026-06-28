"""
runner.py - 爬蟲主控制器（大總管）

定義了 MotoGPScraper 類別，是整個專案的核心控制器。
負責把其他模組串起來，完成完整的爬蟲流程。

主要方法：
- latest_news()   - 從所有來源收集新聞，去重，加權選取，排序
- fetch_article() - 下載並提取一篇新聞文章的內文

加權選取策略 (RSS_SHARE = 0.5)：
- 將新聞分為 RSS 來源和 HTML 來源兩組
- 50% 的名額分配給 RSS 來源，剩下的給 HTML 來源
- 各組按發佈時間 (UTC+8) 降序排序
- 如果某一組不夠，溢出的名額轉給另一組

依賴關係：
- 被 cli.py 調用
- 調用 config.py、sources.py、http_client.py、extractors.py、datetime_utils.py、models.py
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from .browser_fallback import fetch_gpone_article_with_playwright
from .config import DEFAULT_SOURCES
from .datetime_utils import to_utc_plus_8
from .extractors import extract_article_text, extract_image_url_with_lxml
from .http_client import fetch_text
from .models import Article, NewsItem, SourceConfig
from .source_weights import RSS_SHARE, SOURCE_PRIORITY_DELAYS, source_article_cap
from .sources import discover_source_items


class BlockedArticleError(RuntimeError):
    """Raised when a fetched article is a bot-protection page, not article content."""


# ============================================================
# MotoGPScraper - MotoGP 新聞爬蟲主控制器
# ============================================================
class MotoGPScraper:
    def __init__(self, sources: tuple[SourceConfig, ...] = DEFAULT_SOURCES) -> None:
        self.sources = sources

    # ============================================================
    # latest_news - 收集最新新聞
    # ============================================================
    # 流程：遍歷所有來源 → 去重 → 加權選取 → 排序 → 回傳前 limit 筆
    # ============================================================
    def latest_news(self, *, limit: int = 10) -> list[NewsItem]:
        all_items: list[NewsItem] = []
        for source in self.sources:
            try:
                all_items.extend(discover_source_items(source))
            except Exception as exc:
                print(f"[WARN] Failed to discover {source.name}: {exc}", file=sys.stderr)

        unique_items = self._dedupe_by_url(all_items)
        return self._select_weighted_latest(unique_items, limit=limit)

    # ============================================================
    # fetch_article - 下載並提取一篇新聞文章的內文
    # ============================================================
    # HTML fallback 來源在 discovery 階段可能已抓過文章頁，
    # 優先使用快取（raw_meta["article_markup"]）避免重複請求。
    # ============================================================
    def fetch_article(self, item: NewsItem) -> Article:
        # HTML fallback 來源在 discovery 階段可能已抓過文章頁，優先使用快取避免重複請求。
        markup = item.raw_meta.get("article_markup") or fetch_text(item.url)
        extracted = extract_article_text(markup, url=item.url)
        if extracted.method == "blocked-page":
            fallback_markup = self._fetch_blocked_article_with_browser(item.url)
            if fallback_markup:
                markup = fallback_markup
                extracted = extract_article_text(markup, url=item.url)
            if extracted.method == "blocked-page":
                raise BlockedArticleError(f"Blocked page received for {item.url}")
        image_url = extract_image_url_with_lxml(markup, base_url=item.url)
        return Article(
            item=item,
            text=extracted.text,
            extraction_method=extracted.method,
            extracted_at=datetime.now(timezone.utc),
            image_url=image_url,
        )

    @staticmethod
    def _fetch_blocked_article_with_browser(url: str) -> str | None:
        host = urlparse(url).netloc.lower()
        if "gpone.com" not in host:
            return None
        return fetch_gpone_article_with_playwright(url)

    # ============================================================
    # _select_weighted_latest - 加權選取最新新聞（私有方法）
    # ============================================================
    # 將新聞分為 RSS 組和 HTML 組，依 RSS_SHARE 比例分配名額。
    # 各組按 UTC+8 時間降序排序，不夠時互相補足。
    # ============================================================
    def _select_weighted_latest(self, items: list[NewsItem], *, limit: int) -> list[NewsItem]:
        if limit <= 0:
            return []

        rss_items = [item for item in items if self._is_rss_item(item)]
        non_rss_items = [item for item in items if not self._is_rss_item(item)]

        rss_items.sort(key=self._sort_selection_priority, reverse=True)
        non_rss_items.sort(key=self._sort_selection_priority, reverse=True)

        rss_limit = min(len(rss_items), math.ceil(limit * RSS_SHARE))
        non_rss_limit = min(len(non_rss_items), limit - rss_limit)
        selected = self._take_with_source_caps(rss_items, count=rss_limit, report_limit=limit)
        selected += self._take_with_source_caps(
            non_rss_items,
            count=non_rss_limit,
            report_limit=limit,
            already_selected=selected,
        )

        # First backfill pass: still respect per-source caps so lower-priority
        # sources do not crowd out GPone, Crash.net, or Motorsport too early.
        if len(selected) < limit:
            selected_urls = {item.url.rstrip("/") for item in selected}
            overflow = [
                item
                for item in rss_items[rss_limit:] + non_rss_items[non_rss_limit:]
                if item.url.rstrip("/") not in selected_urls
            ]
            overflow.sort(key=self._sort_selection_priority, reverse=True)
            selected.extend(
                self._take_with_source_caps(
                    overflow,
                    count=limit - len(selected),
                    report_limit=limit,
                    already_selected=selected,
                )
            )

        # Final fallback: relax the per-source caps if the capped pass could
        # not reach the requested limit. This keeps reports from coming up short.
        if len(selected) < limit:
            selected_urls = {item.url.rstrip("/") for item in selected}
            overflow = [
                item
                for item in rss_items + non_rss_items
                if item.url.rstrip("/") not in selected_urls
            ]
            overflow.sort(key=self._sort_selection_priority, reverse=True)
            selected.extend(overflow[: limit - len(selected)])

        selected.sort(key=self._sort_datetime_utc8, reverse=True)
        return selected[:limit]

    @classmethod
    def _take_with_source_caps(
        cls,
        items: list[NewsItem],
        *,
        count: int,
        report_limit: int,
        already_selected: list[NewsItem] | None = None,
    ) -> list[NewsItem]:
        selected: list[NewsItem] = []
        source_counts: dict[str, int] = {}
        for item in already_selected or []:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1

        for item in items:
            if len(selected) >= count:
                break
            source_limit = source_article_cap(item.source, report_limit)
            if source_counts.get(item.source, 0) >= source_limit:
                continue
            selected.append(item)
            source_counts[item.source] = source_counts.get(item.source, 0) + 1

        return selected

    # ============================================================
    # _is_rss_item - 判斷新聞是否來自 RSS（私有靜態方法）
    # ============================================================
    # 檢查 raw_meta 中的 discovery_method 是否為 "rss"。
    # ============================================================
    @staticmethod
    def _is_rss_item(item: NewsItem) -> bool:
        return item.raw_meta.get("discovery_method") == "rss"

    # ============================================================
    # _sort_datetime_utc8 - 排序鍵：將發佈時間轉為 UTC+8（私有靜態方法）
    # ============================================================
    # 用於排序時統一時區比較。沒有時間的項目會被排到最後。
    # ============================================================
    @staticmethod
    def _sort_datetime_utc8(item: NewsItem) -> datetime:
        converted = to_utc_plus_8(item.published_at)
        return converted or datetime.min.replace(tzinfo=timezone.utc)

    @classmethod
    def _sort_selection_priority(cls, item: NewsItem) -> datetime:
        base_time = cls._sort_datetime_utc8(item)
        delay = SOURCE_PRIORITY_DELAYS.get(item.source)
        if delay and base_time != datetime.min.replace(tzinfo=timezone.utc):
            return base_time - delay
        return base_time

    # ============================================================
    # _dedupe_by_url - 去重函數（私有靜態方法）
    # ============================================================
    # 以 URL 為準去重，會去掉末尾 "/" 比較以避免重複。
    # ============================================================
    @staticmethod
    def _dedupe_by_url(items: list[NewsItem]) -> list[NewsItem]:
        seen: set[str] = set()
        unique: list[NewsItem] = []
        for item in items:
            normalized = item.url.rstrip("/")
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(item)
        return unique
