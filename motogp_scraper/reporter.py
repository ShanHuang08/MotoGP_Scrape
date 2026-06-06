from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


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
    """依照目前報告格式做輕量轉換：標題、表格、metadata、一般段落。"""
    lines = markdown.splitlines()
    html_parts: list[str] = []
    paragraph_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()

        # 空白行代表段落結束。
        if not line.strip():
            _flush_paragraph(paragraph_lines, html_parts)
            index += 1
            continue

        # Markdown 表格區塊轉成 <table><thead><tbody>。
        if _is_table_start(lines, index):
            _flush_paragraph(paragraph_lines, html_parts)
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            html_parts.append(_render_markdown_table(table_lines))
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
            _flush_paragraph(paragraph_lines, html_parts)
            heading = line[3:].strip()
            heading_id = _slugify(heading)
            article_class = " article-heading" if re.match(r"^\d+\.", heading) else ""
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
    return "\n".join(f"    {part}" for part in html_parts)


def write_report(markdown: str, *, output_dir: str | Path, now: datetime) -> Path:
    """寫出 HTML 報告；檔名包含日期與 latest news，副檔名固定為 .html。"""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{now:%Y-%m-%d %H%M%S} latest news.html"
    report_path = report_dir / filename
    report_path.write_text(build_report_html(markdown), encoding="utf-8-sig")
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


def _render_markdown_table(table_lines: list[str]) -> str:
    """將 Markdown 表格轉成真正的 HTML table。"""
    header_cells = _split_markdown_table_row(table_lines[0])
    body_rows = [
        _split_markdown_table_row(row)
        for row in table_lines[2:]
        if row.strip().startswith("|")
    ]

    header_html = "".join(f"<th>{html.escape(cell)}</th>" for cell in header_cells)
    rows_html: list[str] = []
    for row in body_rows:
        cells = _normalize_row(row, len(header_cells))
        cell_html = "".join(f"<td>{_format_table_cell(cell)}</td>" for cell in cells)
        rows_html.append(f"<tr>{cell_html}</tr>")

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
