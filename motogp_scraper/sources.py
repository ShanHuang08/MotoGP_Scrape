from __future__ import annotations

from .config import SourceConfig
from .extractors import (
    extract_links_with_lxml,
    extract_published_at_with_lxml,
    extract_title_with_lxml,
)
from .http_client import fetch_text
from .models import NewsItem
from .rss import parse_rss_items


def discover_from_rss(source: SourceConfig) -> list[NewsItem]:
    if not source.rss_url:
        return []

    markup = fetch_text(source.rss_url)
    return parse_rss_items(
        markup,
        source_name=source.name,
        default_timezone=source.timezone_name,
    )


def discover_from_listing(source: SourceConfig) -> list[NewsItem]:
    markup = fetch_text(source.listing_url)
    links = extract_links_with_lxml(
        markup,
        base_url=source.listing_url,
        xpaths=source.article_link_xpaths,
        limit=source.max_listing_links,
    )

    items: list[NewsItem] = []
    for url in links:
        try:
            article_markup = fetch_text(url)
        except Exception:
            continue

        title = extract_title_with_lxml(article_markup, source.title_xpaths) or url
        published_at = extract_published_at_with_lxml(
            article_markup,
            url=url,
            default_timezone=source.timezone_name,
        )
        items.append(
            NewsItem(
                source=source.name,
                title=title,
                url=url,
                published_at=published_at,
                raw_meta={
                    "discovery_method": "html",
                    # HTML fallback 來源已經抓過文章頁；先暫存起來，避免正文階段重抓時被防護頁擋住。
                    "article_markup": article_markup,
                },
            )
        )

    return items


def discover_source_items(source: SourceConfig) -> list[NewsItem]:
    if source.rss_url:
        try:
            rss_items = discover_from_rss(source)
            if rss_items:
                return rss_items
        except Exception:
            pass

    return discover_from_listing(source)
