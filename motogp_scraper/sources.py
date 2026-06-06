"""
sources.py - 新聞來源探索器

負責從各個新聞網站「發現」新聞項目，是整個爬蟲流程的第一步。

主要函數：
- discover_source_items() - 主入口：決定用 RSS 還是網頁掃描來找新聞
- discover_from_rss()     - 用 RSS 訂閱方式取得新聞列表
- discover_from_listing() - 直接掃描新聞列表網頁找連結

發現策略：
1. 如果有 rss_url，優先使用 RSS（速度快、資料完整）
2. 如果 RSS 失敗或沒有設定，退回到網頁掃描方式

網頁掃描流程：下載列表頁 HTML → XPath 提取連結 → 逐個下載文章頁提取標題和日期 →
將文章 HTML 暫存到 raw_meta（避免 fetch_article 時重抓）

依賴關係：
- 被 runner.py 調用
- 調用 config.py、extractors.py、http_client.py、rss.py、models.py
"""

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


# ============================================================
# discover_from_rss - 透過 RSS 訂閱取得新聞列表
# ============================================================
# 下載 RSS XML 並解析為 NewsItem 列表。沒有 RSS 網址則回傳空列表。
# ============================================================
def discover_from_rss(source: SourceConfig) -> list[NewsItem]:
    if not source.rss_url:
        return []

    markup = fetch_text(source.rss_url)
    return parse_rss_items(
        markup,
        source_name=source.name,
        default_timezone=source.timezone_name,
    )


# ============================================================
# discover_from_listing - 透過掃描新聞列表網頁取得新聞列表
# ============================================================
# 下載列表頁 HTML，用 XPath 提取連結，逐個下載文章頁提取標題和日期。
# 注意：每個連結都要下載一次，所以速度較慢。
# 文章 HTML 會暫存到 raw_meta["article_markup"]，避免後續重抓。
# ============================================================
def discover_from_listing(source: SourceConfig) -> list[NewsItem]:
    markup = fetch_text(source.listing_url)
    links = extract_links_with_lxml(
        markup,
        base_url=source.listing_url, # 基底 URL
        xpaths=source.article_link_xpaths, # 連結 XPath
        limit=source.max_listing_links, # 最多取多少個連結
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


# ============================================================
# discover_source_items - 新聞來源探索的主入口函數
# ============================================================
# 優先使用 RSS，失敗則退回到網頁掃描。
# ============================================================
def discover_source_items(source: SourceConfig) -> list[NewsItem]:
    if source.rss_url:
        try:
            rss_items = discover_from_rss(source)
            if rss_items:
                return rss_items
        except Exception:
            pass

    return discover_from_listing(source)
