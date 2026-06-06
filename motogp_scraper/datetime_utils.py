"""
datetime_utils.py - 日期時間工具模組

提供日期解析和時區轉換的功能，被多個模組引用。

主要函數：
- parse_datetime()    - 多策略解析日期字串（RFC 2822 / ISO 8601 / dateparser）
- ensure_timezone()   - 確保 datetime 有時區資訊（沒有則補上預設時區）
- to_utc_plus_8()     - 將任何時區的 datetime 轉換為 UTC+8

依賴關係：
- 被 cli.py、extractors.py、runner.py、rss.py 調用
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo


# UTC+8 時區常數
UTC_PLUS_8 = timezone(timedelta(hours=8))


# 日期解析策略列表：依優先順序嘗試
# 每個策略是一個 (名稱, callable) tuple，callable 接收 cleaned 字串，回傳 datetime 或拋出例外
_PARSERS: list[tuple[str, callable]] = []


def _init_parsers() -> None:
    """延遲初始化解析器列表（dateparser 是 optional dependency，避免 startup 載入太慢）。"""
    if _PARSERS:
        return

    def _rfc2822(value: str) -> datetime:
        return parsedate_to_datetime(value)

    def _iso8601(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    _PARSERS.append(("rfc2822", _rfc2822))
    _PARSERS.append(("iso8601", _iso8601))

    # dateparser 是 optional dependency，只有需要時才 import
    try:
        import dateparser

        def _dateparser_fallback(value: str) -> datetime | None:
            return dateparser.parse(
                value,
                settings={"RETURN_AS_TIMEZONE_AWARE": True},
            )

        _PARSERS.append(("dateparser", _dateparser_fallback))
    except ImportError:
        pass


def parse_datetime(value: str | None, *, default_timezone: str = "UTC") -> datetime | None:
    """
    嘗試多種策略解析日期字串，依優先順序：
    1. RFC 2822（RSS 常用格式，如 "Mon, 01 Jan 2024 12:00:00 GMT"）
    2. ISO 8601（如 "2024-01-01T12:00:00Z"）
    3. dateparser 庫（萬用解析，作為最後手段）

    任一策略成功就回傳結果，全部失敗則回傳 None。
    """
    if not value:
        return None

    cleaned = " ".join(value.split())
    _init_parsers()

    for _name, parser_fn in _PARSERS:
        try:
            result = parser_fn(cleaned)
            if result is not None:
                return ensure_timezone(result, default_timezone=default_timezone)
        except (TypeError, ValueError, OverflowError):
            continue

    return None


# ============================================================
# ensure_timezone - 確保 datetime 有時區資訊
# ============================================================
# 如果 datetime 已經有時區就直接回傳，
# 沒有則補上 default_timezone 指定的時區（預設 UTC）。
# ============================================================
def ensure_timezone(value: datetime, *, default_timezone: str = "UTC") -> datetime:
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=ZoneInfo(default_timezone))


# ============================================================
# to_utc_plus_8 - 轉換為 UTC+8 時區
# ============================================================
# 將任何時區的 datetime 轉換為 UTC+8。
# 如果輸入 None 則回傳 None；如果沒有時區則假設為 UTC。
# ============================================================
def to_utc_plus_8(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(UTC_PLUS_8)
