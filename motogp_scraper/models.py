"""
models.py - 資料模型定義

這個檔案定義了整個專案中使用的兩個核心資料結構（dataclass）：
- NewsItem：代表一則新聞項目（標題、連結、來源等）
- Article：代表一篇完整的文章（包含新聞項目 + 提取到的內文）

這兩個 dataclass 都使用 frozen=True，表示建立後不可修改（唯讀），
這樣可以確保資料在傳遞過程中不會被意外竄改。

依賴關係：
- 被 runner.py、cli.py、sources.py、rss.py 等模組引用
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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
