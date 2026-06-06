from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .datetime_utils import to_utc_plus_8
from .models import Article, NewsItem
from .reporter import (
    DEFAULT_REPORT_DIR,
    build_report_markdown,
    open_report_in_chrome,
    write_report,
)
from .runner import MotoGPScraper


def format_datetime(value: datetime | None) -> str:
    converted = to_utc_plus_8(value)
    if converted is None:
        return ""
    return converted.isoformat(timespec="seconds")


def escape_table_cell(value: str | None) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ").strip()


def render_news_table(items: list[NewsItem]) -> str:
    lines = [
        "| # | Title | Link | Published At (UTC+8) |",
        "|---:|---|---|---|",
    ]
    for index, item in enumerate(items, start=1):
        title = escape_table_cell(item.title)
        published = escape_table_cell(format_datetime(item.published_at))
        lines.append(f"| {index} | {title} | {item.url} | {published} |")
    return "\n".join(lines)


def render_articles(articles: list[Article]) -> str:
    sections: list[str] = []
    for index, article in enumerate(articles, start=1):
        title = article.item.title
        body = article.text.strip() or "[No article text extracted]"
        sections.append(
            "\n".join(
                [
                    f"## {index}. {title}",
                    "",
                    f"Source: {article.item.source}",
                    f"URL: {article.item.url}",
                    f"Published At (UTC+8): {format_datetime(article.item.published_at)}",
                    f"Extraction: {article.extraction_method}",
                    "",
                    body,
                ]
            )
        )
    return "\n\n".join(sections)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape latest MotoGP news articles.")
    parser.add_argument("--limit", type=int, default=10, help="Number of news items to list.")
    parser.add_argument(
        "--skip-articles",
        action="store_true",
        help="Only print the latest-news table; do not fetch article bodies.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_REPORT_DIR,
        help="Directory for generated HTML reports.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Write the HTML report but do not open it in Chrome/browser.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scraper = MotoGPScraper()

    items = scraper.latest_news(limit=args.limit)
    table_markdown = render_news_table(items)
    # 目前主要閱讀方式是 HTML 報告，CLI 表格保留給後續 LLM 流程但不輸出。
    # print(table_markdown)

    articles: list[Article] = []
    articles_markdown = ""

    if not args.skip_articles:
        for item in items:
            try:
                articles.append(scraper.fetch_article(item))
            except Exception as exc:
                print(f"\n[WARN] Failed to fetch article {item.url}: {exc}", file=sys.stderr)

        articles_markdown = render_articles(articles)
        # 目前主要閱讀方式是 HTML 報告，CLI 內文保留給後續 LLM 流程但不輸出。
        # print("\n\n# Article Text\n")
        # print(articles_markdown)

    generated_at = datetime.now()
    report_markdown = build_report_markdown(
        table_markdown=table_markdown,
        articles_markdown=articles_markdown,
        generated_at=generated_at,
    )
    report_path = write_report(report_markdown, output_dir=args.output_dir, now=generated_at)
    print(f"\nHTML report saved: {report_path.resolve()}")

    if not args.no_open:
        open_report_in_chrome(report_path)

    return 0
