"""
config.py - 新聞來源設定檔

定義了：
1. SourceConfig - 每個新聞來源的設定結構
2. DEFAULT_SOURCES - 預設的三個新聞來源網站設定

SourceConfig 欄位：
- name                : 新聞來源顯示名稱
- listing_url         : 新聞列表頁網址（用來直接掃描網頁找新聞）
- rss_url             : RSS 訂閱網址（如果有提供，優先使用）
- article_link_xpaths : 用來從 HTML 中提取新聞連結的 XPath 規則
- title_xpaths        : 用來從 HTML 中提取標題的 XPath 規則
- max_listing_links   : 掃描列表頁時最多取多少個連結（預設 30）
- timezone_name       : 該來源的時區名稱（如 "Europe/London"）

依賴關係：
- 被 runner.py 和 sources.py 引用
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================
# SourceConfig - 新聞來源設定結構（唯讀 dataclass）
# ============================================================
@dataclass(frozen=True)
class SourceConfig:
    name: str                                          # 新聞來源顯示名稱
    listing_url: str                                   # 新聞列表頁網址
    rss_url: str | None = None                         # RSS 訂閱網址（可選）
    article_link_xpaths: tuple[str, ...] = field(default_factory=tuple)  # 提取文章連結的 XPath 規則
    title_xpaths: tuple[str, ...] = field(default_factory=tuple)         # 提取標題的 XPath 規則
    max_listing_links: int = 30                        # 掃描列表頁時最多取多少個連結
    timezone_name: str = "UTC"                         # 該來源的時區（例如 "Europe/London"）


# ============================================================
# DEFAULT_SOURCES - 預設的三個 MotoGP 新聞來源
# ============================================================
# 1. Crash.net - 有 RSS，時區 Europe/London
# 2. GPone - 無 RSS（純網頁掃描），時區 Europe/Rome
# 3. Motorsport.com - 有 RSS，時區 UTC
# ============================================================
DEFAULT_SOURCES: tuple[SourceConfig, ...] = (
    # ---- 來源 1: Crash.net MotoGP ----
    SourceConfig(
        name="Crash.net MotoGP",
        listing_url="https://www.crash.net/motogp/news",
        rss_url="https://www.crash.net/rss/motogp",
        article_link_xpaths=(
            "//a[contains(@href, '/motogp/news/')]/@href",
            "//article//a/@href",
        ),
        timezone_name="Europe/London",
    ),
    # ---- 來源 2: GPone MotoGP（無 RSS，純網頁掃描）----
    SourceConfig(
        name="GPone MotoGP",
        listing_url="https://www.gpone.com/en/news/ontrack/motogp",
        article_link_xpaths=(
            "//a[contains(@href, '/en/news/ontrack/motogp/')]/@href",
            "//a[contains(@href, '/en/20') and contains(@href, '/motogp/')]/@href",
            "//article//a/@href",
        ),
        timezone_name="Europe/Rome",
    ),
    # ---- 來源 3: Motorsport.com MotoGP ----
    SourceConfig(
        name="Motorsport.com MotoGP",
        listing_url="https://www.motorsport.com/motogp/news/",
        rss_url="https://www.motorsport.com/rss/motogp/news/",
        article_link_xpaths=(
            "//a[contains(@href, '/motogp/news/')]/@href",
            "//article//a/@href",
        ),
        timezone_name="UTC",
    ),
)
