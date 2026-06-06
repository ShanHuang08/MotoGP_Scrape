from __future__ import annotations

import math
import sys
from datetime import datetime, timezone

from .config import DEFAULT_SOURCES, SourceConfig
from .datetime_utils import to_utc_plus_8
from .extractors import extract_article_text
from .http_client import fetch_text
from .models import Article, NewsItem
from .sources import discover_source_items


RSS_SHARE = 0.65


class MotoGPScraper:
    def __init__(self, sources: tuple[SourceConfig, ...] = DEFAULT_SOURCES) -> None:
        self.sources = sources

    def latest_news(self, *, limit: int = 10) -> list[NewsItem]:
        all_items: list[NewsItem] = []
        for source in self.sources:
            try:
                all_items.extend(discover_source_items(source))
            except Exception as exc:
                print(f"[WARN] Failed to discover {source.name}: {exc}", file=sys.stderr)

        unique_items = self._dedupe_by_url(all_items)
        return self._select_weighted_latest(unique_items, limit=limit)

    def fetch_article(self, item: NewsItem) -> Article:
        # HTML fallback 來源在 discovery 階段可能已抓過文章頁，優先使用快取避免重複請求。
        markup = item.raw_meta.get("article_markup") or fetch_text(item.url)
        extracted = extract_article_text(markup, url=item.url)
        return Article(
            item=item,
            text=extracted.text,
            extraction_method=extracted.method,
            extracted_at=datetime.now(timezone.utc),
        )

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

    @staticmethod
    def _is_rss_item(item: NewsItem) -> bool:
        return item.raw_meta.get("discovery_method") == "rss"

    @staticmethod
    def _sort_datetime_utc8(item: NewsItem) -> datetime:
        converted = to_utc_plus_8(item.published_at)
        return converted or datetime.min.replace(tzinfo=timezone.utc)

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
