"""
cli.py - 命令行介面（Command Line Interface）

這個檔案是使用者與程式互動的入口，負責：
1. 解析命令行參數（使用 argparse）
2. 調用 MotoGPScraper 執行爬蟲
3. 將結果格式化為 Markdown，交給 reporter.py 生成報告

主要函數：
- format_datetime()     - 將 datetime 轉成 UTC+8 的 ISO 格式字串
- escape_table_cell()   - 轉義 Markdown 表格中的特殊字元
- render_news_table()   - 將新聞列表渲染成 Markdown 表格字串
- render_articles()     - 將文章內文渲染成 Markdown 格式字串
- build_parser()        - 建立命令行參數解析器
- main()                - 主程式入口（解析參數 → 爬蟲 → 組報告 → 存檔 → 開瀏覽器）

命令行參數：
- --limit N         : 取得多少篇新聞（預設 20）
- --skip-articles   : 只產生新聞列表，不下載文章內文
- --format TYPE     : 報告輸出格式，html 或 markdown（預設 html）
- --output-dir PATH : 報告檔存到哪個資料夾
- --no-organize     : 不自動根據行事曆收納報告到比賽資料夾
- --no-open         : 只寫報告檔，不自動用瀏覽器開啟（HTML 和 Markdown 都適用）
- --unit-test       : 執行 tests/ 資料夾下的單元測試後結束

依賴關係：
- 被 main.py 調用
- 調用 runner.py 的 MotoGPScraper
- 調用 reporter.py 的報告生成函數
- 調用 report_organizer.py 的報告收納函數
- 引用 models.py 的 Article 和 NewsItem
- 調用 datetime_utils.py 的 to_utc_plus_8
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from .datetime_utils import to_utc_plus_8
from .models import Article, NewsItem
from .report_organizer import organize_reports_for_race
from .reporter import (
    DEFAULT_REPORT_DIR,
    build_report_markdown,
    open_report_in_chrome,
    open_url_in_chrome,
    write_report,
    write_report_markdown,
)
from .translator import (
    DEFAULT_API_KEY_FILE,
    DEFAULT_PROMPT_FILE,
    DEFAULT_TRANSLATION_MODEL,
    TranslationError,
    translate_articles_from_markdown,
)

ARTICLE_BACKFILL_TRIGGER_RATIO = 0.75
ARTICLE_BACKFILL_SHARE = 0.20
GPONE_NEWS_URL = "https://www.gpone.com/en/news/ontrack/motogp"


# ============================================================
# format_datetime - 格式化日期時間為 UTC+8 的 ISO 字串
# ============================================================
# 將 datetime 轉為 UTC+8 後輸出 ISO 格式字串（如 "2024-06-01T20:30:45"）。
# 如果傳入 None，回傳空字串。
# ============================================================
def format_datetime(value: datetime | None) -> str:
    converted = to_utc_plus_8(value)
    if converted is None:
        return ""
    return converted.isoformat(timespec="seconds")


# ============================================================
# escape_table_cell - 轉義 Markdown 表格中的特殊字元
# ============================================================
# 把 "|" 轉義為 "\|"，把換行符替換為空格，去除首尾空白。
# ============================================================
def escape_table_cell(value: str | None) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ").strip()


# ============================================================
# render_news_table - 將新聞列表渲染成 Markdown 表格字串
# ============================================================
# format="html" 時，Link 欄位顯示原始 URL，HTML 轉換器會自動變成可點擊連結。
# format="markdown" 時，Link 欄位使用 [link](url) 格式，方便 Markdown 閱讀器點擊。
# 只負責組字串並 return，不會 print。
# ============================================================
def render_news_table(items: list[NewsItem], *, format: str = "html") -> str:
    lines = [
        "| # | Title | Link | Published At (UTC+8) |",
        "|---:|---|---|---|",
    ]
    for index, item in enumerate(items, start=1):
        title = escape_table_cell(item.title)
        published = escape_table_cell(format_datetime(item.published_at))
        # markdown 模式使用 [link](url) 格式，html 模式保持原始 URL
        link_cell = f"[link]({item.url})" if format == "markdown" else item.url
        lines.append(f"| {index} | {title} | {link_cell} | {published} |")
    return "\n".join(lines)


# ============================================================
# render_articles - 將文章內文渲染成 Markdown 格式字串
# ============================================================
# 每篇文章包含：標題、來源、URL、發佈時間(UTC+8)、提取方式、內文。
# 只負責組字串並 return，不會 print。
# ============================================================
def format_capture_summary(items: list[NewsItem]) -> str:
    """Return a concise source-count summary for the final captured report items."""
    if not items:
        return "No news captured."

    counts = Counter(item.source for item in items)
    parts = [
        f"{count} {source} news"
        for source, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ]
    return f"{', '.join(parts)} have been captured."


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
                    f"Image: {article.image_url or ''}",
                    "",
                    body,
                ]
            )
        )
    return "\n\n".join(sections)


def parse_article_indexes(value: str) -> list[int]:
    """Parse comma-separated article numbers for on-demand translation."""
    indexes: list[int] = []
    for part in value.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        try:
            index = int(stripped)
        except ValueError as exc:
            raise TranslationError(f"Invalid article number: {stripped}") from exc
        if index <= 0:
            raise TranslationError(f"Article number must be positive: {index}")
        indexes.append(index)

    if not indexes:
        raise TranslationError("At least one article number is required.")
    return indexes


# ============================================================
# build_parser - 建立命令行參數解析器
# ============================================================
# 定義 --limit, --skip-articles, --format, --output-dir, --no-organize, --no-open 六個參數。
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape latest MotoGP news articles.",
        # 自訂 HelpFormatter：加大 max_help_position 讓說明文字不會被擠到下一行
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=36),
    )
    parser.add_argument("--limit", type=int, default=20, help="Number of news items to list.")
    parser.add_argument(
        "--skip-articles",
        action="store_true",
        help="Only print the latest-news table; do not fetch article bodies.",
    )
    # --format: 報告輸出格式，支援 html（預設）和 markdown
    parser.add_argument(
        "--format",
        choices=["html", "markdown"],
        default="html",
        help="Report output format: html (default) or markdown.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_REPORT_DIR,
        help="Directory for generated reports.",
    )
    parser.add_argument(
        "--no-organize",
        action="store_true",
        help="Do not auto-organize reports into race weekend folders.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Write the report but do not open it in Chrome/browser.",
    )
    parser.add_argument(
        "--translate-report",
        help="Translate one article from an existing latest-news Markdown report.",
    )
    parser.add_argument(
        "--translate-article",
        help="Article number(s) to translate from --translate-report, e.g. 3 or 2,5,7,14.",
    )
    parser.add_argument(
        "--translate-model",
        default=DEFAULT_TRANSLATION_MODEL,
        help=f"OpenAI model for translation (default: {DEFAULT_TRANSLATION_MODEL}).",
    )
    parser.add_argument(
        "--api-key-file",
        default=DEFAULT_API_KEY_FILE,
        help=f"Local OpenAI API key file (default: {DEFAULT_API_KEY_FILE}).",
    )
    parser.add_argument(
        "--translation-prompt",
        default=DEFAULT_PROMPT_FILE,
        help=f"Translation prompt file (default: {DEFAULT_PROMPT_FILE}).",
    )
    parser.add_argument(
        "--translation-output-dir",
        help="Directory for translated HTML output. Defaults to the Markdown report folder.",
    )
    # --unit-test: 執行單元測試後直接結束，不進行爬蟲流程
    parser.add_argument(
        "--unit-test",
        action="store_true",
        help="Run unit tests from the tests/ folder and exit.",
    )
    return parser


# ============================================================
# main - 命令行主程式入口（整個程式的核心流程）
# ============================================================
# 步驟 0：根據行事曆檢查比賽周末，自動收納舊報告到對應資料夾
# 步驟 1：解析命令行參數
# 步驟 2：建立 MotoGPScraper，調用 latest_news() 取得新聞列表
# 步驟 3：渲染新聞表格 Markdown 字串
# 步驟 4：如果沒有 --skip-articles，逐個下載文章內文並渲染
# 步驟 5：根據 --format 參數，產生 HTML 或 Markdown 報告並寫入檔案
# 步驟 6：如果沒有 --no-open，用 Chrome 開啟報告（HTML 和 Markdown 都適用）
# ============================================================
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # 單元測試模式：執行 tests/ 資料夾下所有測試後直接結束
    if args.unit_test:
        from run_tests import run_all_tests
        success = run_all_tests(verbosity=2)
        return 0 if success else 1

    if args.translate_report:
        if args.translate_article is None:
            print(
                "[ERROR] --translate-article is required with --translate-report.",
                file=sys.stderr,
            )
            return 1
        try:
            article_indexes = parse_article_indexes(args.translate_article)
            report_path = translate_articles_from_markdown(
                args.translate_report,
                article_indexes=article_indexes,
                model=args.translate_model,
                api_key_file=args.api_key_file,
                prompt_file=args.translation_prompt,
                output_dir=args.translation_output_dir,
            )
        except TranslationError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

        print(f"\nTranslated HTML saved: {Path(report_path).resolve()}")
        if not args.no_open:
            open_report_in_chrome(report_path)
        return 0

    from .runner import MotoGPScraper

    scraper = MotoGPScraper()

    # 步驟 0：根據行事曆檢查今天是否在某站比賽的窗口內，
    # 如果是則建立比賽資料夾並搬移舊報告，同時決定新報告的輸出目錄
    if not args.no_organize:
        output_dir, race = organize_reports_for_race(report_dir=args.output_dir)
    else:
        output_dir = args.output_dir
        race = None

    items = scraper.latest_news(limit=args.limit)
    # 根據輸出格式調整表格渲染方式（markdown 模式會使用 [link](url) 格式）
    articles: list[Article] = []
    articles_markdown = ""
    gpone_attempted = 0
    gpone_fetched = 0

    if not args.skip_articles:
        for item in items:
            is_gpone = "gpone.com" in item.url
            if is_gpone:
                gpone_attempted += 1
            try:
                article = scraper.fetch_article(item)
            except Exception as exc:
                print(f"\n[WARN] Failed to fetch article {item.url}: {exc}", file=sys.stderr)
                continue

            articles.append(article)
            if is_gpone:
                gpone_fetched += 1

        backfill_threshold = math.ceil(args.limit * ARTICLE_BACKFILL_TRIGGER_RATIO)
        if args.limit > 0 and len(articles) < backfill_threshold:
            backfill_target = max(1, math.ceil(args.limit * ARTICLE_BACKFILL_SHARE))
            expanded_limit = args.limit + (backfill_target * 2)
            seen_urls = {item.url.rstrip("/") for item in items}
            backfilled = 0

            print(
                f"\n[INFO] Only fetched {len(articles)}/{args.limit} article bodies; "
                f"trying up to {backfill_target} backfill article(s).",
                file=sys.stderr,
            )
            for item in scraper.latest_news(limit=expanded_limit):
                normalized_url = item.url.rstrip("/")
                if normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)
                is_gpone = "gpone.com" in item.url
                if is_gpone:
                    gpone_attempted += 1
                try:
                    article = scraper.fetch_article(item)
                except Exception as exc:
                    print(f"\n[WARN] Failed to fetch article {item.url}: {exc}", file=sys.stderr)
                    continue

                articles.append(article)
                if is_gpone:
                    gpone_fetched += 1
                backfilled += 1
                if backfilled >= backfill_target:
                    break

        articles_markdown = render_articles(articles)

    table_items = [article.item for article in articles] if not args.skip_articles else items
    table_markdown = render_news_table(table_items, format=args.format)
    print(f"\n[INFO] {format_capture_summary(table_items)}")

    generated_at = datetime.now()
    report_markdown = build_report_markdown(
        table_markdown=table_markdown,
        articles_markdown=articles_markdown,
        generated_at=generated_at,
    )

    # 原文報告同時輸出 HTML（給人讀）與 Markdown（給 AI 翻譯讀）。
    html_report_path = write_report(report_markdown, output_dir=output_dir, now=generated_at)
    markdown_report_path = write_report_markdown(
        report_markdown, output_dir=output_dir, now=generated_at
    )
    print(f"\nHTML report saved: {html_report_path.resolve()}")
    print(f"Markdown report saved: {markdown_report_path.resolve()}")

    report_path = markdown_report_path if args.format == "markdown" else html_report_path

    # 兩種格式都自動用瀏覽器開啟（除非指定 --no-open）
    # Markdown 檔需要有瀏覽器 Markdown 擴充套件才能正確渲染
    if not args.no_open:
        open_report_in_chrome(report_path)

    if gpone_attempted > 0 and gpone_fetched == 0:
        print(
            f"\n[INFO] GPone article bodies all failed ({gpone_attempted} attempted); "
            f"opening {GPONE_NEWS_URL}",
            file=sys.stderr,
        )
        open_url_in_chrome(GPONE_NEWS_URL)

    return 0
