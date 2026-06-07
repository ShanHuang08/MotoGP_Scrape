"""
test_datetime_utils.py - 日期時間工具模組的單元測試 (pytest)

測試範圍（第一 + 第二梯隊）：
- parse_datetime()  : RFC 2822 / ISO 8601 / dateparser / 空值 / 無效值
- ensure_timezone() : 已有時區 / 無時區補預設
- to_utc_plus_8()   : None / naive / aware datetime

執行方式：
    python main.py --unit-test
    或
    pytest tests/test_datetime_utils.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import pytest

from motogp_scraper.datetime_utils import (
    parse_datetime,
    ensure_timezone,
    to_utc_plus_8,
    UTC_PLUS_8,
)


# ============================================================
# parse_datetime 測試
# ============================================================
class TestParseDatetime:
    """parse_datetime - 多策略日期解析"""

    # ---- RFC 2822（RSS 常用格式）----

    def test_rfc2822_gmt(self) -> None:
        """RFC 2822 格式，GMT 時區"""
        result = parse_datetime("Mon, 01 Jan 2024 12:30:59 GMT")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 59

    def test_rfc2822_with_timezone_offset(self) -> None:
        """RFC 2822 格式，帶 +0200 時區偏移"""
        result = parse_datetime("Fri, 06 Jun 2026 14:30:00 +0200")
        assert result is not None
        assert result.year == 2026
        assert result.month == 6
        assert result.day == 6

    # ---- ISO 8601 ----

    def test_iso8601_zulu(self) -> None:
        """ISO 8601 格式，Z 結尾（UTC）"""
        result = parse_datetime("2024-06-01T12:00:00Z")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 12

    def test_iso8601_with_offset(self) -> None:
        """ISO 8601 格式，帶 +02:00 偏移"""
        result = parse_datetime("2024-06-01T12:00:00+02:00")
        assert result is not None
        assert result.hour == 12

    def test_iso8601_date_only(self) -> None:
        """ISO 8601 只有日期部分（2024-01-15）"""
        result = parse_datetime("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    # ---- dateparser 備用策略 ----

    def test_dateparser_natural_language(self) -> None:
        """dateparser 自然語言格式（"June 1, 2024"）"""
        dateparser = pytest.importorskip("dateparser")
        result = parse_datetime("June 1, 2024")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6

    # ---- 空值 / 無效值（使用 parametrize）----

    @pytest.mark.parametrize(
        "value",
        [None, "", "   ", "not-a-date-at-all", "xyzabc123!@#"],
        ids=["none", "empty", "whitespace", "invalid", "gibberish"],
    )
    def test_invalid_values_return_none(self, value: str | None) -> None:
        """None / 空字串 / 空白 / 無效字串 / 亂碼 都回傳 None"""
        assert parse_datetime(value) is None

    # ---- 時區處理 ----

    def test_timezone_naive_gets_default_utc(self) -> None:
        """解析結果若無時區，預設補上 UTC"""
        result = parse_datetime("2024-01-15", default_timezone="UTC")
        assert result is not None
        assert result.tzinfo is not None

    def test_timezone_naive_gets_london(self) -> None:
        """解析結果若無時區，補上 Europe/London"""
        result = parse_datetime("2024-01-15", default_timezone="Europe/London")
        assert result is not None
        assert result.tzinfo is not None

    # ---- 空白清理 ----

    def test_leading_trailing_whitespace(self) -> None:
        """前後有空白應自動清理"""
        result = parse_datetime("  2024-06-01T12:00:00Z  ")
        assert result is not None
        assert result.year == 2024

    # ---- 多格式 parametrize 測試 ----

    @pytest.mark.parametrize(
        "value, expected_year, expected_month",
        [
            ("2024-01-01T00:00:00Z", 2024, 1),
            ("2025-12-31T23:59:59Z", 2025, 12),
            ("Mon, 01 Jan 2024 00:00:00 GMT", 2024, 1),
        ],
        ids=["iso-jan", "iso-dec", "rfc-jan"],
    )
    def test_various_valid_dates(self, value: str, expected_year: int, expected_month: int) -> None:
        """參數化測試：多種有效日期格式都能正確解析"""
        result = parse_datetime(value)
        assert result is not None
        assert result.year == expected_year
        assert result.month == expected_month


# ============================================================
# ensure_timezone 測試
# ============================================================
class TestEnsureTimezone:
    """ensure_timezone - 確保 datetime 有時區資訊"""

    def test_naive_gets_default_utc(self) -> None:
        """無時區的 datetime 補上預設 UTC"""
        naive = datetime(2024, 1, 1, 12, 0, 0)
        result = ensure_timezone(naive)
        assert result.tzinfo is not None
        # ZoneInfo("UTC") 與 timezone.utc 功能相同但物件不同，用 utcoffset 比較
        assert result.utcoffset() == timedelta(0)

    def test_naive_gets_custom_timezone(self) -> None:
        """無時區的 datetime 補上指定的 Europe/Rome"""
        naive = datetime(2024, 1, 1, 12, 0, 0)
        result = ensure_timezone(naive, default_timezone="Europe/Rome")
        assert result.tzinfo is not None
        assert str(result.tzinfo) == "Europe/Rome"

    def test_already_has_timezone_unchanged(self) -> None:
        """已有時區的 datetime 不改變"""
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_timezone(aware, default_timezone="Europe/Rome")
        assert result.tzinfo == timezone.utc  # 保持原來的 UTC


# ============================================================
# to_utc_plus_8 測試
# ============================================================
class TestToUtcPlus8:
    """to_utc_plus_8 - 轉換為 UTC+8 時區"""

    def test_none_returns_none(self) -> None:
        """傳入 None 回傳 None"""
        assert to_utc_plus_8(None) is None

    def test_utc_converts_to_plus8(self) -> None:
        """UTC 時間正確轉換為 UTC+8（+8 小時）"""
        utc_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = to_utc_plus_8(utc_time)
        assert result is not None
        assert result.hour == 20
        assert result.day == 1

    def test_utc_crosses_midnight(self) -> None:
        """UTC 時間跨日轉換（22:00 UTC → 次日 06:00 UTC+8）"""
        utc_time = datetime(2024, 1, 1, 22, 0, 0, tzinfo=timezone.utc)
        result = to_utc_plus_8(utc_time)
        assert result is not None
        assert result.hour == 6
        assert result.day == 2

    def test_naive_assumed_utc(self) -> None:
        """無時區的 datetime 假設為 UTC 再轉換"""
        naive = datetime(2024, 1, 1, 0, 0, 0)
        result = to_utc_plus_8(naive)
        assert result is not None
        # 00:00 UTC → 08:00 UTC+8
        assert result.hour == 8

    def test_already_plus8_unchanged(self) -> None:
        """已經是 UTC+8 的時間不變"""
        plus8 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC_PLUS_8)
        result = to_utc_plus_8(plus8)
        assert result is not None
        assert result.hour == 12

    def test_other_timezone_converts(self) -> None:
        """其他時區（Europe/London UTC+0）正確轉換"""
        london_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=ZoneInfo("Europe/London"))
        result = to_utc_plus_8(london_time)
        assert result is not None
        # 英國夏天 BST = UTC+1，所以 12:00 BST = 11:00 UTC = 19:00 UTC+8
        assert result.hour == 19

    # ---- parametrize: 多組時區轉換 ----

    @pytest.mark.parametrize(
        "utc_hour, expected_hour, expected_day_offset",
        [
            (0, 8, 0),     # 00:00 UTC → 08:00 UTC+8（同日）
            (16, 0, 1),    # 16:00 UTC → 00:00 UTC+8（次日）
            (23, 7, 1),    # 23:00 UTC → 07:00 UTC+8（次日）
            (6, 14, 0),    # 06:00 UTC → 14:00 UTC+8（同日）
        ],
        ids=["midnight", "4pm→midnight", "11pm→7am", "6am→2pm"],
    )
    def test_utc_to_plus8_parametrized(
        self, utc_hour: int, expected_hour: int, expected_day_offset: int
    ) -> None:
        """參數化測試：多組 UTC → UTC+8 轉換"""
        utc_time = datetime(2024, 1, 1, utc_hour, 0, 0, tzinfo=timezone.utc)
        result = to_utc_plus_8(utc_time)
        assert result is not None
        assert result.hour == expected_hour
        assert result.day == 1 + expected_day_offset
