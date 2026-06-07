"""
models.py - 資料模型定義

這個檔案定義了整個專案中使用的核心資料結構（dataclass）：
- SourceConfig：新聞來源的設定結構（網址、XPath、時區等）
- NewsItem：代表一則新聞項目（標題、連結、來源等）
- Article：代表一篇完整的文章（包含新聞項目 + 提取到的內文）
- ExtractedContent：文章內文提取的中間結果（純文字 + 提取方法）
- RaceEntry：MotoGP 賽程行事曆的單一賽站資料

這些 dataclass 都使用 frozen=True，表示建立後不可修改（唯讀），
這樣可以確保資料在傳遞過程中不會被意外竄改。

依賴關係：
- 被 runner.py、cli.py、sources.py、rss.py、config.py、extractors.py、calendar_data.py 等模組引用
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


# ============================================================
# SourceConfig - 新聞來源設定結構（唯讀 dataclass）
# ============================================================
# 代表一個新聞來源的完整設定，包含：
#   name                - 新聞來源顯示名稱（例如 "Crash.net MotoGP"）
#   listing_url         - 新聞列表頁網址（用來直接掃描網頁找新聞）
#   rss_url             - RSS 訂閱網址（可選，有則優先使用）
#   article_link_xpaths - 從 HTML 中提取文章連結的 XPath 規則
#   title_xpaths        - 從 HTML 中提取標題的 XPath 規則
#   max_listing_links   - 掃描列表頁時最多取多少個連結（預設 30）
#   timezone_name       - 該來源的時區（例如 "Europe/London"）
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
# NewsItem - 新聞項目資料結構
# ============================================================
# 代表從新聞來源發現的「一則新聞」，包含：
#   source       - 新聞來源名稱（例如 "Crash.net MotoGP"）
#   title        - 新聞標題
#   url          - 新聞的網址連結
#   published_at - 發佈時間（可能為 None）
#   summary      - 新聞摘要（可能為 None）
#   raw_meta     - 額外的原始 metadata，以字典形式儲存
# ============================================================
@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    raw_meta: dict[str, str] = field(default_factory=dict)


# ============================================================
# Article - 完整文章資料結構
# ============================================================
# 代表一篇已經提取過內文的完整文章，包含：
#   item              - 對應的 NewsItem（這則新聞的基本資訊）
#   text              - 提取到的文章內文純文字
#   extraction_method - 使用哪種方法提取的（例如 "trafilatura" 或 "lxml-paragraph-fallback"）
#   extracted_at      - 提取的時間戳記
# ============================================================
@dataclass(frozen=True)
class Article:
    item: NewsItem
    text: str
    extraction_method: str
    extracted_at: datetime


# ============================================================
# ExtractedContent - 文章內文提取的中間結果
# ============================================================
# 在 extractors.py 提取文章內文時使用，作為提取策略鏈的中間產物。
# 最終會將 text 和 method 轉換為 Article 資料結構。
#
#   text   - 提取到的純文字內容
#   method - 使用了哪種提取方法（如 "trafilatura"、"gpone-lxml-sections"、"lxml-paragraph-fallback"）
# ============================================================
@dataclass(frozen=True)
class ExtractedContent:
    text: str
    method: str


# ============================================================
# RaceEntry - MotoGP 賽程行事曆的單一賽站資料
# ============================================================
# 在 calendar_data.py 中使用，代表一站 MotoGP 比賽的完整資訊。
#   round_number - 第幾站（1-22）
#   date         - 比賽日期（date 物件）
#   grand_prix   - 大獎賽全名（如 "Hungary Grand Prix of Hungary"）
#   country      - 國家名稱（如 "Hungary"）
# ============================================================
@dataclass(frozen=True)
class RaceEntry:
    round_number: int       # 第幾站（1-22）
    date: date              # 比賽日期
    grand_prix: str         # 大獎賽全名
    country: str            # 國家名稱
