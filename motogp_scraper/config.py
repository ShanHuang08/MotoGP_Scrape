from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceConfig:
    name: str
    listing_url: str
    rss_url: str | None = None
    article_link_xpaths: tuple[str, ...] = field(default_factory=tuple)
    title_xpaths: tuple[str, ...] = field(default_factory=tuple)
    max_listing_links: int = 30
    timezone_name: str = "UTC"


DEFAULT_SOURCES: tuple[SourceConfig, ...] = (
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
