"""
config.py - 新聞來源設定檔

定義了 DEFAULT_SOURCES：預設的四個 MotoGP 新聞來源網站設定。

SourceConfig 的類別定義已移至 models.py，本模組只負責提供預設的來源清單。

依賴關係：
- 引用 models.py 的 SourceConfig
- 被 runner.py 和 sources.py 引用
"""

from __future__ import annotations

from .models import SourceConfig


# ============================================================
# DEFAULT_SOURCES - 預設的 MotoGP 新聞來源
# ============================================================
# 1. Crash.net - 有 RSS，時區 Europe/London
# 2. GPone - 無 RSS（純網頁掃描），時區 Europe/Rome
# 3. Motorsport.com（英文版）- 有 RSS，時區 UTC
# 4. Motorsport.com ES（西班牙文版）- 有 RSS，時區 Europe/Madrid
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
        name="GPone MotoGP EN",
        listing_url="https://www.gpone.com/en/news/ontrack/motogp",
        article_link_xpaths=(
            "//a[contains(@href, '/en/news/ontrack/motogp/')]/@href",
            "//a[contains(@href, '/en/20') and contains(@href, '/motogp/')]/@href",
            "//article//a/@href",
        ),
        timezone_name="Europe/Rome",
    ),
    # ---- 來源 3: GPone MotoGP IT（無 RSS，純網頁掃描）----
    SourceConfig(
        name="GPone MotoGP IT",
        listing_url="https://www.gpone.com/it/news/ontrack/motogp",
        article_link_xpaths=(
            "//a[contains(@href, '/it/news/ontrack/motogp/')]/@href",
            "//a[contains(@href, '/it/20') and contains(@href, '/motogp/')]/@href",
            "//article//a/@href",
        ),
        timezone_name="Europe/Rome",
    ),
    # ---- 來源 4: GPone MotoGP ES（無 RSS，純網頁掃描）----
    SourceConfig(
        name="GPone MotoGP ES",
        listing_url="https://www.gpone.com/es/news/ontrack/motogp",
        article_link_xpaths=(
            "//a[contains(@href, '/es/news/ontrack/motogp/')]/@href",
            "//a[contains(@href, '/es/20') and contains(@href, '/motogp/')]/@href",
            "//article//a/@href",
        ),
        timezone_name="Europe/Madrid",
    ),
    # ---- 來源 5: The Race MotoGP（無 RSS，純網頁掃描）----
    SourceConfig(
        name="The Race MotoGP",
        listing_url="https://www.the-race.com/motogp",
        article_link_xpaths=(
            "//*[@id='lt-user-email']/div/section/div[1]/div[2]/article/a/@href",
            "//*[@id='lt-user-email']/div/section/div[1]/div[3]/article[1]/a/@href",
            "//*[@id='lt-user-email']/div/section/div[1]/div[3]/article[2]/a/@href",
            "//a[contains(@href, '/motogp/') and not(contains(@href, '#'))]/@href",
        ),
        title_xpaths=(
            "//*[@id='lt-user-email']/div[1]/main/article/header/h1",
            "//main//article//header//h1",
        ),
        max_listing_links=12,
        timezone_name="Europe/London",
    ),
    # ---- 來源 3: Motorsport.com MotoGP（英文版）----
    SourceConfig(
        name="MotoGPNews",
        listing_url="https://www.motogpnews.com/news/",
        rss_url="https://www.motogpnews.com/news/feed/",
        article_link_xpaths=(
            "//a[contains(@href, 'motogpnews.com/20')]/@href",
        ),
        title_xpaths=(
            "//*[@id='hero-header']/div[3]/h1",
            "//main//article//h1",
            "//h1",
        ),
        max_listing_links=12,
        timezone_name="Europe/London",
    ),
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
    # ---- 來源 4: Motorsport.com ES MotoGP（西班牙文版）----
    # 原文標題和內文保持西班牙文，編碼由 charset_normalizer 自動偵測。
    SourceConfig(
        name="Motorsport.com ES MotoGP",
        listing_url="https://es.motorsport.com/motogp/news/",
        rss_url="https://es.motorsport.com/rss/motogp/news/",
        article_link_xpaths=(
            "//a[contains(@href, '/motogp/news/')]/@href",
            "//article//a/@href",
        ),
        timezone_name="Europe/Madrid",
    ),
)
