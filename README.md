# MotoGP News Scraper

Scrapes the latest MotoGP news from configured sources, preferring RSS feeds when available and falling back to HTML discovery with `lxml`. Article bodies are extracted with `trafilatura`. Results are generated as a styled HTML report and opened in the browser.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you want dependencies installed inside this project folder:

```powershell
python -m pip install -r requirements.txt --target .deps
$env:PYTHONPATH = "$PWD\.deps"
```

## Run

```powershell
python main.py --limit 10
```

This writes an HTML report under:

```text
latest_news_reports/
```

Report filenames include the run date/time and `latest news`, for example:

```text
2026-06-06 135115 latest news.html
```

By default the HTML report is opened in Chrome when Chrome is found. If Chrome is not found, the program falls back to the OS default opener.

Useful options:

```powershell
# Generate the HTML file but do not open the browser
python main.py --limit 10 --no-open

# Only write the latest-news table, without fetching article bodies
python main.py --limit 10 --skip-articles

# Change the report folder
python main.py --limit 10 --output-dir reports
```

## Quick Overview 快速理解

這個專案是一個 MotoGP 新聞爬蟲，運作流程像一條生產線：

```
main.py（入口）
  → cli.py（命令列介面，解析參數 + 組報告 + 存檔）
    → runner.py（MotoGPScraper 主控制器，指揮所有模組）
      → sources.py（去各個新聞網站「發現」新聞列表）
        → config.py（儲存新聞來源的設定：URL、XPath、時區等）
        → rss.py（解析 RSS 訂閱格式的新聞）
        → http_client.py（負責發 HTTP 請求下載網頁）
        → extractors.py（用 lxml 解析 HTML 連結，用 trafilatura 提取文章內文）
      → datetime_utils.py（日期時間解析 + 時區轉換為 UTC+8）
      → models.py（定義資料結構：NewsItem 新聞項目、Article 完整文章）
    → reporter.py（生成 HTML 報告 + 用 Chrome 開啟）
    → translator.py（預留的翻譯功能，目前未實作）
```

### 簡單比喻

| 檔案 | 比喻 |
|------|------|
| `config.py` | 通訊錄（記著要去哪些網站抓新聞，以及各站時區） |
| `http_client.py` | 郵差（負責去網站把網頁下載回來） |
| `rss.py` | 讀 RSS 格式的解析器 |
| `extractors.py` | 從 HTML 裡「提取」連結和文章內容的工具（含各站專用清理） |
| `sources.py` | 決定用 RSS 還是直接掃描網頁來找新聞 |
| `runner.py` | 大總管，把所有東西串起來（含加權選取策略） |
| `cli.py` | 使用者介面（接收指令、組報告） |
| `reporter.py` | 排版印刷廠（把 Markdown 報告轉成漂亮 HTML + 開瀏覽器） |
| `datetime_utils.py` | 時鐘（解析各種日期格式 + 統一轉成 UTC+8） |
| `models.py` | 資料的容器（定義新聞和文章長什麼樣） |
| `translator.py` | 翻譯機（預留接口，尚未實作） |

## Structure

```text
main.py
motogp_scraper/
  __init__.py        # Package entry; exports MotoGPScraper
  cli.py             # CLI arguments, report orchestration
  config.py          # Source URLs, RSS URLs, XPath rules, timezone per source
  datetime_utils.py  # Date/time parsing, timezone handling, UTC+8 conversion
  extractors.py      # Reusable lxml and trafilatura extraction helpers; site-specific cleaners
  http_client.py     # HTTP fetch layer, with Windows curl fallback
  models.py          # NewsItem and Article dataclasses
  reporter.py        # HTML report builder, CSS styling, Chrome/browser opener
  rss.py             # RSS/Atom parser
  runner.py          # MotoGPScraper workflow with weighted RSS/HTML selection
  sources.py         # RSS-first source discovery with HTML fallback
  translator.py      # Placeholder for future LLM translation
```

## Key Strategies

### Source Discovery

Each configured source is tried in order:

1. **RSS** (if `rss_url` is set): download RSS XML → parse into NewsItem list
2. **HTML listing** (fallback): download listing page → XPath link extraction → fetch each article page for title and publish date

### Weighted Selection

`MotoGPScraper.latest_news()` uses a weighted selection strategy (`RSS_SHARE = 0.65`):

1. Split items into RSS-sourced and HTML-sourced groups
2. Sort each group by publish time (UTC+8), newest first
3. Allocate ~65% of the limit to RSS items, the rest to HTML items
4. If one group doesn't have enough, overflow goes to the other
5. Final result is re-sorted by time

### Article Extraction

1. **GPone** (site-specific): dedicated XPath targeting `article/div/section/div` nodes
2. **trafilatura** (default): intelligent main-content extraction, filters ads and navbars
3. **lxml paragraph fallback**: extracts long `<p>` paragraphs from `<article>`/`<main>`/`<p>`
4. **Motorsport.com cleanup**: strips photo galleries, subscription prompts, and comment sections from extracted text

### Timezone Handling

All timestamps are converted to **UTC+8** for display. Each source declares its own `timezone_name` (e.g. `Europe/London`, `Europe/Rome`, `UTC`) so publish dates are correctly interpreted before conversion.

### HTML Report Output

The report pipeline:

1. `cli.py` renders a Markdown table + article sections
2. `reporter.build_report_markdown()` assembles the full Markdown document
3. `reporter.build_report_html()` converts Markdown to a styled HTML page with embedded CSS
4. `reporter.write_report()` saves the HTML file (UTF-8 with BOM for Windows compatibility)
5. `reporter.open_report_in_chrome()` opens the report in Chrome (or OS default)

## Configured News Sources

| Source | RSS | HTML Fallback | Timezone |
|--------|-----|---------------|----------|
| Crash.net MotoGP | Yes | Backup | Europe/London |
| GPone MotoGP | No | Primary | Europe/Rome |
| Motorsport.com MotoGP | Yes | Backup | UTC |

## Translation Hook

LLM translation is intentionally not implemented yet. `motogp_scraper/translator.py` is reserved for adding that integration later.
