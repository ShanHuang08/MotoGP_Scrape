"""
reporter.py - 報告生成器（HTML 與 Markdown 雙格式輸出）

負責將爬蟲結果轉成報告檔，支援兩種輸出格式：
- HTML 報告：帶 CSS 樣式的精美網頁，可用 Chrome 直接開啟閱讀
- Markdown 報告：純文字 .md 檔，適合後續 LLM 處理或用 Markdown 編輯器閱讀

主要函數：
- build_report_markdown()    - 組合成 Markdown 格式的報告內容（兩種格式共用）
- build_report_html()        - 將 Markdown 轉成完整 HTML 頁面（含嵌入 CSS）
- markdown_report_to_html()  - 輕量 Markdown → HTML 轉換（標題/表格/段落/metadata）
- write_report()             - 將 HTML 報告寫入檔案（UTF-8 with BOM）
- write_report_markdown()    - 將 Markdown 報告寫入 .md 檔案（UTF-8）
- open_report_in_chrome()    - 用 Chrome 開啟報告（找不到 Chrome 則用系統預設）

內部輔助函數：
- _render_markdown_table()   - Markdown 表格 → HTML <table>
- _split_markdown_table_row()- 切開 Markdown 表格行，支援 escaped pipe 轉義
- _format_table_cell()       - 表格中的 URL 變成可點擊連結
- _extract_article_heading_ids() - 從 Markdown 預先掃描文章標題 ID，供表格錨點使用
- _render_metadata_line()    - Source/URL/Published 做成 metadata block
- _report_css()              - 報告的 CSS 樣式（嵌入 HTML 中）
- _find_chrome()             - 尋找 Windows Chrome 安裝位置

依賴關係：
- 被 cli.py 調用
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# 預設報告輸出目錄
DEFAULT_REPORT_DIR = "latest_news_reports"


def build_report_markdown(
    *,
    table_markdown: str,
    articles_markdown: str,
    generated_at: datetime,
) -> str:
    """先組出固定格式的文字內容，再交給 build_report_html() 轉成真正 HTML。"""
    article_section = articles_markdown.strip() or "[No article text extracted]"
    return "\n".join(
        [
            "# MotoGP Latest News",
            "",
            f"Generated at: {generated_at.isoformat(timespec='seconds')}",
            "",
            "## Latest News",
            "",
            table_markdown,
            "",
            "## Article Text",
            "",
            article_section,
            "",
        ]
    )


def build_report_html(markdown: str, *, title: str = "MotoGP Latest News") -> str:
    """把本專案產生的 Markdown-like 內容轉成可讀性較好的 HTML 頁面。"""
    escaped_title = html.escape(title)
    body_html = markdown_report_to_html(markdown)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{escaped_title}</title>",
            "  <style>",
            _report_css(),
            "  </style>",
            "</head>",
            "<body>",
            '  <main class="page">',
            body_html,
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def markdown_report_to_html(markdown: str) -> str:
    """
    依照目前報告格式做輕量轉換：標題、表格、段落、metadata。

    HTML 專屬增強功能：
    - 表格 Title 欄位變成錨點連結，點擊可跳轉到對應文章段落
    - 每篇文章結尾自動加入「↑ Back to table」返回目錄連結
    - 平滑滾動效果（由 CSS scroll-behavior 控制）
    """
    # 預先掃描文章標題 ID，供表格中的 Title 欄位建立錨點連結
    article_ids = _extract_article_heading_ids(markdown)

    lines = markdown.splitlines()
    html_parts: list[str] = []
    paragraph_lines: list[str] = []
    index = 0
    # 追蹤目前所在的文章編號，用來插入「返回目錄」連結
    current_article_index: int | None = None

    while index < len(lines):
        line = lines[index].rstrip()

        # 空白行代表段落結束。
        if not line.strip():
            _flush_paragraph(paragraph_lines, html_parts)
            index += 1
            continue

        # Markdown 表格區塊轉成 <table><thead><tbody>，並傳入 article_ids 建立錨點。
        if _is_table_start(lines, index):
            _flush_paragraph(paragraph_lines, html_parts)
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            html_parts.append(_render_markdown_table(table_lines, article_ids=article_ids))
            continue

        # # MotoGP Latest News 轉成 h1，並加上與 markdown reader 類似的 anchor。
        if line.startswith("# "):
            _flush_paragraph(paragraph_lines, html_parts)
            heading = line[2:].strip()
            heading_id = _slugify(heading)
            html_parts.append(
                f'<h1 id="{heading_id}">'
                f'<a class="mdr-anchor" href="#{heading_id}" id="0" aria-hidden="true"></a>'
                f"{html.escape(heading)}</h1>"
            )
            index += 1
            continue

        # ## Latest News / ## Article Text / ## 1. Title 轉成 h2。
        if line.startswith("## "):
            heading = line[3:].strip()
            heading_id = _slugify(heading)
            article_match = re.match(r"^(\d+)\.", heading)

            # 遇到新的文章段落時，先在前一篇文章結尾插入「返回目錄」連結
            if article_match:
                new_index = int(article_match.group(1))
                if current_article_index is not None and new_index != current_article_index:
                    _flush_paragraph(paragraph_lines, html_parts)
                    html_parts.append(
                        '<p class="back-to-toc">'
                        '<a href="#latest-news">\u2191 Back to table</a></p>'
                    )
                current_article_index = new_index

            _flush_paragraph(paragraph_lines, html_parts)
            article_class = " article-heading" if article_match else ""
            html_parts.append(
                f'<h2 id="{heading_id}" class="section-heading{article_class}">'
                f"{html.escape(heading)}</h2>"
            )
            index += 1
            continue

        # Source / URL / Published / Extraction 這類資訊做成 metadata 列。
        if _is_metadata_line(line):
            _flush_paragraph(paragraph_lines, html_parts)
            html_parts.append(_render_metadata_line(line))
            index += 1
            continue

        # 其他文字都當作文章段落，遇到空白行再輸出成 <p>。
        paragraph_lines.append(line)
        index += 1

    _flush_paragraph(paragraph_lines, html_parts)

    # 最後一篇文章也要加入「返回目錄」連結
    if current_article_index is not None:
        html_parts.append(
            '<p class="back-to-toc">'
            '<a href="#latest-news">\u2191 Back to table</a></p>'
        )

    return "\n".join(f"    {part}" for part in html_parts)


def write_report(markdown: str, *, output_dir: str | Path, now: datetime) -> Path:
    """
    寫出 HTML 報告；檔名包含日期與 latest news，副檔名固定為 .html。

    參數：
        markdown   - 由 build_report_markdown() 產生的 Markdown 報告內容
        output_dir - 輸出資料夾路徑
        now        - 用來產生檔名的時間戳記

    回傳：寫出的檔案 Path 物件
    """
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{now:%Y-%m-%d %H%M%S} latest news.html"
    report_path = report_dir / filename
    report_path.write_text(build_report_html(markdown), encoding="utf-8-sig")
    return report_path


# ============================================================
# write_report_markdown - 將 Markdown 報告寫入 .md 檔案
# ============================================================
# 與 write_report() 類似，但直接將 Markdown 原文寫入 .md 檔案，
# 不經過 HTML 轉換。適合後續 LLM 處理或用 Markdown 編輯器閱讀。
# ============================================================
def write_report_markdown(markdown: str, *, output_dir: str | Path, now: datetime) -> Path:
    """
    寫出 Markdown 報告；檔名包含日期，副檔名為 .md。

    參數：
        markdown   - 由 build_report_markdown() 產生的 Markdown 報告內容
        output_dir - 輸出資料夾路徑
        now        - 用來產生檔名的時間戳記

    回傳：寫出的檔案 Path 物件
    """
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{now:%Y-%m-%d %H%M%S} latest news.md"
    report_path = report_dir / filename
    report_path.write_text(markdown, encoding="utf-8")
    return report_path


def open_report_in_chrome(path: str | Path) -> bool:
    """優先用 Chrome 開啟報告；找不到 Chrome 時，改用系統預設開啟方式。"""
    absolute_path = Path(path).resolve()
    file_url = absolute_path.as_uri()

    chrome_path = _find_chrome()
    if chrome_path:
        subprocess.Popen([str(chrome_path), file_url])
        return True

    if sys.platform.startswith("win"):
        os.startfile(str(absolute_path))  # type: ignore[attr-defined]
        return True

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, file_url])
    return True


def _render_markdown_table(table_lines: list[str], *, article_ids: dict[int, str] | None = None) -> str:
    """
    將 Markdown 表格轉成真正的 HTML table。

    參數：
        table_lines  - Markdown 表格的原始行列表
        article_ids  - 文章編號 → heading id 的映射，用來將 Title 欄位變成錨點連結。
                       例如 {1: "1-some-title", 2: "2-another-title"}
    """
    header_cells = _split_markdown_table_row(table_lines[0])
    body_rows = [
        _split_markdown_table_row(row)
        for row in table_lines[2:]
        if row.strip().startswith("|")
    ]

    # 找出 Title 欄位在哪一欄，以便後續插入錨點連結
    title_col_index: int | None = None
    for i, cell in enumerate(header_cells):
        if cell.strip().lower() == "title":
            title_col_index = i
            break

    header_html = "".join(f"<th>{html.escape(cell)}</th>" for cell in header_cells)
    rows_html: list[str] = []
    for row_index, row in enumerate(body_rows):
        cells = _normalize_row(row, len(header_cells))
        cell_parts: list[str] = []
        for col_index, cell in enumerate(cells):
            # Title 欄位變成錨點連結，點擊可跳轉到對應文章段落
            if (
                title_col_index is not None
                and col_index == title_col_index
                and article_ids
                and (row_index + 1) in article_ids
            ):
                article_id = article_ids[row_index + 1]
                escaped = html.escape(cell)
                cell_parts.append(
                    f'<td><a href="#{article_id}" class="toc-link">{escaped}</a></td>'
                )
            else:
                cell_parts.append(f"<td>{_format_table_cell(cell)}</td>")
        rows_html.append(f"<tr>{''.join(cell_parts)}</tr>")

    return "\n".join(
        [
            '<div class="table-wrap">',
            "<table>",
            f"<thead><tr>{header_html}</tr></thead>",
            f"<tbody>{''.join(rows_html)}</tbody>",
            "</table>",
            "</div>",
        ]
    )


def _split_markdown_table_row(row: str) -> list[str]:
    """切開 Markdown table row，並支援被 escape 的 \\|。"""
    stripped = row.strip().strip("|")
    cells: list[str] = []
    current: list[str] = []
    escaped = False

    for char in stripped:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)

    cells.append("".join(current).strip())
    return cells


def _normalize_row(row: list[str], width: int) -> list[str]:
    """確保每列欄位數一致，避免 HTML 表格錯位。"""
    if len(row) >= width:
        return row[:width]
    return row + [""] * (width - len(row))


def _format_table_cell(value: str) -> str:
    """表格裡如果是 URL，就直接變成可點擊連結。"""
    escaped = html.escape(value)
    if value.startswith(("http://", "https://")):
        return f'<a href="{escaped}" target="_blank" rel="noopener noreferrer">{escaped}</a>'
    return escaped


def _render_metadata_line(line: str) -> str:
    """將 Source、URL、Published、Extraction 轉成較容易掃讀的 metadata block。"""
    key, value = line.split(":", 1)
    key_html = html.escape(key.strip())
    value = value.strip()
    if value.startswith(("http://", "https://")):
        value_html = (
            f'<a href="{html.escape(value)}" target="_blank" rel="noopener noreferrer">'
            f"{html.escape(value)}</a>"
        )
    else:
        value_html = html.escape(value)
    return f'<p class="meta"><strong>{key_html}:</strong> {value_html}</p>'


def _flush_paragraph(paragraph_lines: list[str], html_parts: list[str]) -> None:
    """把累積的一般文字輸出成 <p>，再清空暫存。"""
    if not paragraph_lines:
        return
    paragraph = " ".join(line.strip() for line in paragraph_lines if line.strip())
    if paragraph:
        html_parts.append(f"<p>{html.escape(paragraph)}</p>")
    paragraph_lines.clear()


def _is_table_start(lines: list[str], index: int) -> bool:
    """判斷目前行是否為 Markdown 表格開頭。"""
    if index + 1 >= len(lines):
        return False
    current = lines[index].strip()
    next_line = lines[index + 1].strip()
    return current.startswith("|") and next_line.startswith("|") and set(next_line) <= {"|", "-", ":", " "}


def _is_metadata_line(line: str) -> bool:
    """判斷文章 metadata 行。"""
    return line.startswith(("Generated at:", "Source:", "URL:", "Published At", "Extraction:"))


def _slugify(value: str) -> str:
    """產生簡單 anchor id。"""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


# ============================================================
# _extract_article_heading_ids - 預先掃描文章標題的 anchor ID
# ============================================================
# 掃描 Markdown 中 "## N. Title" 格式的文章標題，
# 回傳 {文章編號: slugified_id} 的映射。
# 例如 "## 1. Rossi wins" → {1: "1-rossi-wins"}
# 這些 ID 會與 markdown_report_to_html() 中產生的 h2 id 一致。
# ============================================================
def _extract_article_heading_ids(markdown: str) -> dict[int, str]:
    """從 Markdown 預先掃描文章標題，回傳 {編號: anchor_id} 映射。"""
    result: dict[int, str] = {}
    for line in markdown.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            match = re.match(r"^(\d+)\.", heading)
            if match:
                index = int(match.group(1))
                result[index] = _slugify(heading)
    return result


def _report_css() -> str:
    """集中管理 HTML 報告樣式，輸出時直接嵌入 HTML 原始碼。"""
    return """
    :root {
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --text: #16202a;
      --muted: #5d6b7a;
      --line: #d9e0e7;
      --accent: #c52b2f;
      --accent-soft: #fff1f1;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 16px;
      line-height: 1.65;
    }
    .page {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 56px;
    }
    h1 {
      margin: 0 0 10px;
      font-size: 34px;
      line-height: 1.15;
      letter-spacing: 0;
    }
    h2 {
      margin: 34px 0 14px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      font-size: 24px;
      line-height: 1.25;
      letter-spacing: 0;
    }
    h2.article-heading {
      color: var(--accent);
      font-size: 22px;
    }
    .mdr-anchor {
      display: inline-block;
      width: 0;
      height: 0;
      overflow: hidden;
    }
    p {
      margin: 0 0 14px;
      max-width: 860px;
    }
    p.meta {
      max-width: none;
      margin: 3px 0;
      color: var(--muted);
      font-size: 14px;
    }
    p.meta strong {
      color: var(--text);
    }
    a {
      color: #0b63ce;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .table-wrap {
      overflow-x: auto;
      margin: 16px 0 24px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 2px 8px rgba(16, 24, 40, 0.05);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      line-height: 1.45;
    }
    thead {
      background: #eef2f6;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
    }
    th:first-child,
    td:first-child {
      width: 52px;
      text-align: right;
      color: var(--muted);
    }
    tbody tr:nth-child(even) {
      background: #fafbfc;
    }
    tbody tr:hover {
      background: var(--accent-soft);
    }
    /* 平滑滾動：點擊錨點連結時不會瞬間跳轉 */
    html {
      scroll-behavior: smooth;
    }
    /* 錨點跳轉時保留上方間距，避免標題貼在視窗頂端 */
    h2[id] {
      scroll-margin-top: 20px;
    }
    /* 表格中的目錄連結樣式 */
    a.toc-link {
      font-weight: 600;
    }
    /* 返回目錄按鈕樣式 */
    .back-to-toc {
      margin-top: 8px;
    }
    .back-to-toc a {
      color: var(--muted);
      font-size: 14px;
    }
    .back-to-toc a:hover {
      color: var(--accent);
    }
    """.strip()


def _find_chrome() -> Path | None:
    """尋找 Windows 常見 Chrome 安裝位置，也支援 CHROME_PATH 環境變數。"""
    if not sys.platform.startswith("win"):
        return None

    candidates = [
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return path
    return None
