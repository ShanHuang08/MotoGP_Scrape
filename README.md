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

`playwright` is included for GPone browser fallback. The scraper first tries the locally installed Chrome browser, so a separate Playwright browser download is usually not required. If Chrome is not installed, run `python -m playwright install chromium` once after installing the requirements.

## Run

```powershell
python main.py --limit 10
```

This writes both HTML and Markdown reports under:

```text
latest_news_reports/
```

Report filenames include the run date/time and `latest news`, for example:

```text
2026-06-06 135115 latest news.html
2026-06-06 135115 latest news.md
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

# Open the Markdown report after writing both HTML and Markdown
python main.py --limit 10 --format markdown

# Disable auto-organization into race weekend folders
python main.py --limit 10 --no-organize

# Markdown-open mode with other options combined
python main.py --limit 5 --format markdown --skip-articles --output-dir reports

# Run unit tests
python main.py --unit-test
```

> Scraping now always writes both `.html` and `.md`. `--format` only decides which file is opened automatically.

## Quick Overview 快速理解

這個專案是一個 MotoGP 新聞爬蟲，運作流程像一條生產線：

```
main.py（入口）
  → cli.py（命令列介面，解析參數 + 組報告 + 存檔）
    → report_organizer.py（根據行事曆自動收納報告到比賽資料夾）
      → calendar_data.py（2026 MotoGP 22 站賽程行事曆）
    → runner.py（MotoGPScraper 主控制器，指揮所有模組）
      → sources.py（去各個新聞網站「發現」新聞列表）
        → config.py（儲存新聞來源的設定：URL、XPath、時區等）
        → rss.py（解析 RSS 訂閱格式的新聞）
        → http_client.py（負責發 HTTP 請求下載網頁）
        → extractors.py（用 lxml 解析 HTML 連結，用 trafilatura 提取文章內文）
      → datetime_utils.py（日期時間解析 + 時區轉換為 UTC+8）
      → models.py（定義資料結構：NewsItem 新聞項目、Article 完整文章）
    → reporter.py（生成報告：HTML 或 Markdown + 用 Chrome 開啟 HTML 報告）
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
| `reporter.py` | 排版印刷廠（把 Markdown 報告轉成漂亮 HTML 或純 .md 檔 + 開瀏覽器） |
| `datetime_utils.py` | 時鐘（解析各種日期格式 + 統一轉成 UTC+8） |
| `models.py` | 資料的容器（定義新聞和文章長什麼樣） |
| `calendar_data.py` | 賽事行事曆（2026 年 22 站比賽日期和名稱） |
| `report_organizer.py` | 收納管家（根據行事曆自動將報告歸類到比賽資料夾） |
| `translator.py` | 翻譯機（預留接口，尚未實作） |

## Structure

```text
main.py
run_tests.py           # Unit test runner
motogp_scraper/
  __init__.py        # Package entry; exports MotoGPScraper
  cli.py             # CLI arguments, report orchestration
  config.py          # Source URLs, RSS URLs, XPath rules, timezone per source
  datetime_utils.py  # Date/time parsing, timezone handling, UTC+8 conversion
  extractors.py      # Reusable lxml and trafilatura extraction helpers; site-specific cleaners
  http_client.py     # HTTP fetch layer, with Windows curl fallback
  models.py          # NewsItem and Article dataclasses
  reporter.py        # HTML/Markdown report builder, CSS styling, Chrome/browser opener
  calendar_data.py    # 2026 MotoGP calendar (22 rounds with dates and GP names)
  report_organizer.py # Auto-organize reports into race weekend folders
  rss.py             # RSS/Atom parser
  runner.py          # MotoGPScraper workflow with weighted RSS/HTML selection
  sources.py         # RSS-first source discovery with HTML fallback
  translator.py      # On-demand OpenAI translation from generated Markdown reports
tests/
  __init__.py
  conftest.py            # 共用 fixtures（make_news_item, make_article, make_extracted, make_race_entry 等）
  test_datetime_utils.py # parse_datetime, ensure_timezone, to_utc_plus_8
  test_runner.py         # _dedupe_by_url, _select_weighted_latest, _is_rss_item
  test_extractors.py     # normalize_url, extract_published_at_with_lxml, remove_motorsport_tail_noise, extract_article_text, clean_article_text_for_site
  test_reporter.py       # _split_markdown_table_row, _normalize_row
  test_report_organizer.py # _build_race_folder_name, _parse_report_date
  test_models.py         # Article, ExtractedContent, RaceEntry（frozen 唯讀性、欄位存取、相等性）
  test_calendar_data.py  # MOTOGP_2026_CALENDAR 完整性、find_race_nearby、get_race_window
```

## Key Strategies

### Source Discovery

Each configured source is tried in order:

1. **RSS** (if `rss_url` is set): download RSS XML → parse into NewsItem list
2. **HTML listing** (fallback): download listing page → XPath link extraction → fetch each article page for title and publish date

### Weighted Selection

`MotoGPScraper.latest_news()` uses a weighted selection strategy (`RSS_SHARE = 0.5`):

1. Split items into RSS-sourced and HTML-sourced groups
2. Sort each group by publish time (UTC+8), newest first
3. Allocate 50% of the limit to RSS items, the rest to HTML items
4. If one group doesn't have enough, overflow goes to the other
5. Final result is re-sorted by time

When article bodies are fetched, the final table is built from successfully extracted articles so the table and article sections stay aligned. If a selected GPone article is still blocked after fallback, it is removed from both the table and the article section.

There is one lightweight backfill guard for widespread blocking: if fewer than 75% of the requested article bodies are fetched successfully, the CLI asks for a slightly larger candidate list and attempts to add up to 20% more successful article bodies. With `--limit 20`, this means fewer than 15 successful bodies triggers up to four backfill articles.

### Article Extraction

1. **GPone** (site-specific): dedicated XPath targeting `article/div/section/div` nodes
2. **The Race** (site-specific): dedicated article `section` extraction, excluding embedded latest-stories blocks
3. **trafilatura** (default): intelligent main-content extraction, filters ads and navbars
4. **lxml paragraph fallback**: extracts long `<p>` paragraphs from `<article>`/`<main>`/`<p>`
5. **Motorsport.com cleanup**: strips photo galleries, subscription prompts, and comment sections from extracted text

Bot-protection pages are filtered before they reach the report. Common markers such as `Just a moment...` and `Enable JavaScript and cookies to continue` are treated as `blocked-page`. For GPone articles, the scraper then tries a Playwright browser fallback using a persistent local browser profile (`.gpone_browser_profile/`). If the browser fallback still cannot recover the article, the CLI logs a warning and continues with the remaining selected articles.

### Timezone Handling

All timestamps are converted to **UTC+8** for display. Each source declares its own `timezone_name` (e.g. `Europe/London`, `Europe/Rome`, `UTC`) so publish dates are correctly interpreted before conversion.

### Report Output

The report pipeline writes two output formats on each scrape:

**HTML（預設）：**
1. `cli.py` renders a Markdown table + article sections
2. `reporter.build_report_markdown()` assembles the full Markdown document
3. `reporter.build_report_html()` converts Markdown to a styled HTML page with embedded CSS
4. `reporter.write_report()` saves the HTML file (UTF-8 with BOM for Windows compatibility)
5. `reporter.open_report_in_chrome()` opens the report in Chrome (or OS default)

**Markdown：**
1. `cli.py` renders a Markdown table + article sections（表格 Link 欄位使用 `[link](url)` 格式）
2. `reporter.build_report_markdown()` assembles the full Markdown document
3. `reporter.write_report_markdown()` saves the raw `.md` file (UTF-8)，不經過 HTML 轉換
4. `--format markdown` only changes which output file is opened automatically

### Report Auto-Organization

Reports are automatically organized into race weekend folders based on the 2026 MotoGP calendar:

1. On each run, `report_organizer.py` checks today's date against `calendar_data.py`
2. If today is within ±3 days of a race, a folder is created (e.g. `2026 Round 8 Hungary Grand Prix of Hungary`)
3. Existing reports within the date window are moved into that folder
4. The new report is also saved directly into the folder
5. If today is not near any race weekend, reports stay in the root `latest_news_reports/` folder

Use `--no-organize` to disable this behavior.

## Unit Tests

專案內建單元測試（基於 **pytest** 框架），放在 `tests/` 資料夾下，涵蓋核心資料物件、純函數與提取邏輯：

| 測試檔案 | 測試範圍 |
|----------|----------|
| `test_datetime_utils.py` | `parse_datetime()`、`ensure_timezone()`、`to_utc_plus_8()` |
| `test_runner.py` | `_dedupe_by_url()`、`_select_weighted_latest()`、`_is_rss_item()` |
| `test_extractors.py` | `normalize_url()`、`extract_published_at_with_lxml()`、`remove_motorsport_tail_noise()`、`extract_article_text()`、`clean_article_text_for_site()` |
| `test_reporter.py` | `_split_markdown_table_row()`、`_normalize_row()` |
| `test_report_organizer.py` | `_build_race_folder_name()`、`_parse_report_date()` |
| `test_models.py` | `Article`、`ExtractedContent`、`RaceEntry`（frozen 唯讀性、欄位存取、相等性） |
| `test_calendar_data.py` | `MOTOGP_2026_CALENDAR` 完整性、`find_race_nearby()`、`get_race_window()` |

**共用 Fixtures（`conftest.py`）：**

| Fixture | 用途 |
|---------|------|
| `make_news_item` | 快速建立測試用的 `NewsItem` 工廠函數 |
| `sample_news_item` | 預建的 `NewsItem` 樣本 |
| `scraper` | `MotoGPScraper` 實例 |
| `make_article` | 快速建立測試用的 `Article` 工廠函數 |
| `sample_article` | 預建的 `Article` 樣本 |
| `make_extracted` | 快速建立測試用的 `ExtractedContent` 工廠函數 |
| `make_race_entry` | 快速建立測試用的 `RaceEntry` 工廠函數 |
| `sample_race_entry` | 預建的 `RaceEntry` 樣本（匈牙利站） |

執行方式：

```powershell
# 透過 CLI 執行
python main.py --unit-test

# 或直接執行 run_tests.py
python run_tests.py

# 或直接用 pytest（需先安裝）
pytest tests/ -v
```

## Configured News Sources

| Source | RSS | HTML Fallback | Timezone |
|--------|-----|---------------|----------|
| Crash.net MotoGP | Yes | Backup | Europe/London |
| GPone MotoGP EN | No | Primary | Europe/Rome |
| GPone MotoGP IT | No | Primary | Europe/Rome |
| GPone MotoGP ES | No | Primary | Europe/Madrid |
| The Race MotoGP | No | Primary | Europe/London |
| Motorsport.com MotoGP | Yes | Backup | UTC |
| Motorsport.com ES MotoGP | Yes | Backup | Europe/Madrid |

## Translation Hook

Translations are on-demand so scraping does not spend tokens automatically. First generate a report, then choose a specific article from the generated Markdown file:

```powershell
python main.py --translate-report "latest_news_reports\2026-06-20 101500 latest news.md" --translate-article 3
```

The translation prompt is read from `AI_translator_prompt.md`. The OpenAI API key is read from `OPENAI_API_KEY` first, then from local `API_SECRET_KEY.txt`. The secret file is ignored by git.

Useful options:

```powershell
python main.py --translate-report "report.md" --translate-article 3 --translate-model gpt-5
python main.py --translate-report "report.md" --translate-article 2,5,7,14
python main.py --translate-report "report.md" --translate-article 3 --translation-output-dir translated_reports
python main.py --translate-report "report.md" --translate-article 3 --no-open
```

Translation output is HTML only. When multiple article numbers are provided, each article is translated with a separate API call and combined into one HTML file.
