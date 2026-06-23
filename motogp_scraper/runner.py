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

from .config import DEFAULT_SOURCES
from .datetime_utils import to_utc_plus_8
from .extractors import extract_article_text, extract_image_url_with_lxml
from .http_client import fetch_text
from .models import Article, NewsItem, SourceConfig
from .sources import discover_source_items


class BlockedArticleError(RuntimeError):
    """Raised when a fetched article is a bot-protection page, not article content."""


# RSS 來源佔比：50% 的名額優先分配給 RSS 來源的新聞
RSS_SHARE = 0.5


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
            raise BlockedArticleError(f"Blocked page received for {item.url}")
        image_url = extract_image_url_with_lxml(markup, base_url=item.url)
        return Article(
            item=item,
            text=extracted.text,
            extraction_method=extracted.method,
            extracted_at=datetime.now(timezone.utc),
            image_url=image_url,
        )

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

        rss_items.sort(key=self._sort_datetime_utc8, reverse=True)
        non_rss_items.sort(key=self._sort_datetime_utc8, reverse=True)

        rss_limit = min(len(rss_items), math.ceil(limit * RSS_SHARE))
        non_rss_limit = min(len(non_rss_items), limit - rss_limit)
        selected = rss_items[:rss_limit] + non_rss_items[:non_rss_limit]

        if len(selected) < limit:
            selected_urls = {item.url.rstrip("/") for item in selected}
            overflow = [
                item
                for item in rss_items[rss_limit:] + non_rss_items[non_rss_limit:]
                if item.url.rstrip("/") not in selected_urls
            ]
            overflow.sort(key=self._sort_datetime_utc8, reverse=True)
            selected.extend(overflow[: limit - len(selected)])

        selected.sort(key=self._sort_datetime_utc8, reverse=True)
        return selected[:limit]

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
