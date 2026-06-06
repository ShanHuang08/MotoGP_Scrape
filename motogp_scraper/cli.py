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
- --limit N         : 取得多少篇新聞（預設 10）
- --skip-articles   : 只產生新聞列表，不下載文章內文
- --format TYPE     : 報告輸出格式，html 或 markdown（預設 html）
- --output-dir PATH : 報告檔存到哪個資料夾
- --no-organize     : 不自動根據行事曆收納報告到比賽資料夾
- --no-open         : 只寫報告檔，不自動用瀏覽器開啟（HTML 和 Markdown 都適用）

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
import sys
from datetime import datetime

from .datetime_utils import to_utc_plus_8
from .models import Article, NewsItem
from .report_organizer import organize_reports_for_race
from .reporter import (
    DEFAULT_REPORT_DIR,
    build_report_markdown,
    open_report_in_chrome,
    write_report,
    write_report_markdown,
)
from .runner import MotoGPScraper


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
    parser.add_argument("--limit", type=int, default=10, help="Number of news items to list.")
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
    table_markdown = render_news_table(items, format=args.format)

    articles: list[Article] = []
    articles_markdown = ""

    if not args.skip_articles:
        for item in items:
            try:
                articles.append(scraper.fetch_article(item))
            except Exception as exc:
                print(f"\n[WARN] Failed to fetch article {item.url}: {exc}", file=sys.stderr)

        articles_markdown = render_articles(articles)

    generated_at = datetime.now()
    report_markdown = build_report_markdown(
        table_markdown=table_markdown,
        articles_markdown=articles_markdown,
        generated_at=generated_at,
    )

    # 根據 --format 參數決定輸出 HTML 或 Markdown 報告
    # 使用 output_dir（可能已被收納器改為比賽資料夾路徑）
    if args.format == "markdown":
        # Markdown 模式：直接寫出 .md 檔案，不經過 HTML 轉換
        report_path = write_report_markdown(
            report_markdown, output_dir=output_dir, now=generated_at
        )
        print(f"\nMarkdown report saved: {report_path.resolve()}")
    else:
        # HTML 模式（預設）：轉成 HTML 報告並寫出
        report_path = write_report(
            report_markdown, output_dir=output_dir, now=generated_at
        )
        print(f"\nHTML report saved: {report_path.resolve()}")

    # 兩種格式都自動用瀏覽器開啟（除非指定 --no-open）
    # Markdown 檔需要有瀏覽器 Markdown 擴充套件才能正確渲染
    if not args.no_open:
        open_report_in_chrome(report_path)

    return 0
