"""
test_calendar_data.py - 賽程行事曆模組的單元測試 (pytest)

測試範圍：
- find_race_nearby()       : 檢查日期是否在比賽窗口內
- get_race_window()        : 取得比賽日期窗口範圍
- MOTOGP_2026_CALENDAR     : 行事曆資料完整性驗證

執行方式：
    python main.py --unit-test
    或
    pytest tests/test_calendar_data.py -v
"""

from __future__ import annotations

from datetime import date

import pytest

from motogp_scraper.models import RaceEntry
from motogp_scraper.calendar_data import (
    MOTOGP_2026_CALENDAR,
    find_race_nearby,
    get_race_window,
)


# ============================================================
# MOTOGP_2026_CALENDAR 完整性測試
# ============================================================
class TestCalendarData:
    """MOTOGP_2026_CALENDAR - 行事曆資料完整性"""

    def test_calendar_has_22_rounds(self) -> None:
        """行事曆應有 22 站"""
        assert len(MOTOGP_2026_CALENDAR) == 22

    def test_round_numbers_sequential(self) -> None:
        """站號從 1 到 22 連續"""
        round_numbers = [race.round_number for race in MOTOGP_2026_CALENDAR]
        assert round_numbers == list(range(1, 23))

    def test_all_dates_in_2026(self) -> None:
        """所有比賽日期都在 2026 年"""
        for race in MOTOGP_2026_CALENDAR:
            assert race.date.year == 2026

    def test_dates_chronologically_ordered(self) -> None:
        """日期按時間順序排列"""
        dates = [race.date for race in MOTOGP_2026_CALENDAR]
        assert dates == sorted(dates)

    def test_no_duplicate_dates(self) -> None:
        """沒有重複日期"""
        dates = [race.date for race in MOTOGP_2026_CALENDAR]
        assert len(dates) == len(set(dates))

    def test_all_entries_are_race_entry(self) -> None:
        """所有項目都是 RaceEntry 實例"""
        for race in MOTOGP_2026_CALENDAR:
            assert isinstance(race, RaceEntry)

    def test_first_round_is_thailand(self) -> None:
        """第一站是泰國"""
        assert MOTOGP_2026_CALENDAR[0].country == "Thailand"
        assert MOTOGP_2026_CALENDAR[0].round_number == 1

    def test_last_round_is_valencia(self) -> None:
        """最後一站是瓦倫西亞"""
        assert MOTOGP_2026_CALENDAR[-1].country == "Valencian Community"
        assert MOTOGP_2026_CALENDAR[-1].round_number == 22

    def test_all_grand_prix_non_empty(self) -> None:
        """所有大獎賽名稱非空"""
        for race in MOTOGP_2026_CALENDAR:
            assert race.grand_prix
            assert len(race.grand_prix) > 5

    def test_all_countries_non_empty(self) -> None:
        """所有國家名稱非空"""
        for race in MOTOGP_2026_CALENDAR:
            assert race.country


# ============================================================
# find_race_nearby 測試
# ============================================================
class TestFindRaceNearby:
    """find_race_nearby - 檢查日期是否在比賽窗口內"""

    def test_exact_race_date(self) -> None:
        """比賽當天精確命中"""
        # 匈牙利站 2026-06-07
        result = find_race_nearby(date(2026, 6, 7))
        assert result is not None
        assert result.round_number == 8
        assert result.country == "Hungary"

    def test_one_day_before(self) -> None:
        """比賽前一天在窗口內"""
        result = find_race_nearby(date(2026, 6, 6))
        assert result is not None
        assert result.round_number == 8

    def test_one_day_after(self) -> None:
        """比賽後一天在窗口內"""
        result = find_race_nearby(date(2026, 6, 8))
        assert result is not None
        assert result.round_number == 8

    def test_three_days_before(self) -> None:
        """比賽前 3 天在窗口邊界"""
        result = find_race_nearby(date(2026, 6, 4))
        assert result is not None
        assert result.round_number == 8

    def test_three_days_after(self) -> None:
        """比賽後 3 天在窗口邊界"""
        result = find_race_nearby(date(2026, 6, 10))
        assert result is not None
        assert result.round_number == 8

    def test_four_days_before_outside_window(self) -> None:
        """比賽前 4 天在窗口外（匈牙利 6/7 前 4 天是 6/3，但義大利 5/31 在窗口內）"""
        # 6/3 距離匈牙利 4 天 → 超出，但距離義大利 5/31 只有 3 天 → 命中義大利
        result = find_race_nearby(date(2026, 6, 3))
        assert result is not None
        assert result.round_number == 7  # 義大利站

        # 要找到真正不在任何站窗口內的日期：遠離所有比賽
        result2 = find_race_nearby(date(2026, 7, 20))
        assert result2 is None

    def test_four_days_after_outside_window(self) -> None:
        """比賽後 4 天在窗口外"""
        result = find_race_nearby(date(2026, 6, 11))
        assert result is None

    def test_far_away_date(self) -> None:
        """遠離所有比賽的日期回傳 None"""
        result = find_race_nearby(date(2026, 8, 1))
        assert result is None

    def test_custom_window_days(self) -> None:
        """自訂窗口大小（±1 天）"""
        # 匈牙利站 6/7，±1 天窗口 → 6/6~6/8
        result = find_race_nearby(date(2026, 6, 6), window_days=1)
        assert result is not None
        assert result.round_number == 8

        # ±1 天窗口，6/5 在外面
        result_outside = find_race_nearby(date(2026, 6, 5), window_days=1)
        assert result_outside is None

    def test_closer_race_wins(self) -> None:
        """同時在兩站窗口內時，距離較近的優先"""
        # 第 7 站義大利 5/31，第 8 站匈牙利 6/7
        # 6/4 距離匈牙利 3 天、距離義大利 4 天 → 匈牙利
        result = find_race_nearby(date(2026, 6, 4))
        assert result is not None
        assert result.round_number == 8

    def test_first_round(self) -> None:
        """第一站泰國 3/1"""
        result = find_race_nearby(date(2026, 3, 1))
        assert result is not None
        assert result.round_number == 1
        assert result.country == "Thailand"

    def test_last_round(self) -> None:
        """最後一站瓦倫西亞 11/29"""
        result = find_race_nearby(date(2026, 11, 29))
        assert result is not None
        assert result.round_number == 22

    # ---- parametrize: 多站命中測試 ----

    @pytest.mark.parametrize(
        "target, expected_round",
        [
            (date(2026, 3, 1), 1),    # 泰國
            (date(2026, 5, 10), 5),   # 法國
            (date(2026, 6, 7), 8),    # 匈牙利
            (date(2026, 8, 9), 12),   # 英國
            (date(2026, 11, 29), 22), # 瓦倫西亞
        ],
        ids=["thailand", "france", "hungary", "britain", "valencia"],
    )
    def test_exact_dates_hit_correct_round(self, target: date, expected_round: int) -> None:
        """參數化測試：多站的精確日期都能命中正確站號"""
        result = find_race_nearby(target)
        assert result is not None
        assert result.round_number == expected_round


# ============================================================
# get_race_window 測試
# ============================================================
class TestGetRaceWindow:
    """get_race_window - 取得比賽日期窗口範圍"""

    def test_default_window(self, sample_race_entry: RaceEntry) -> None:
        """預設 ±3 天窗口：6/7 → (6/4, 6/10)"""
        start, end = get_race_window(sample_race_entry)
        assert start == date(2026, 6, 4)
        assert end == date(2026, 6, 10)

    def test_custom_window_1(self, sample_race_entry: RaceEntry) -> None:
        """±1 天窗口：6/7 → (6/6, 6/8)"""
        start, end = get_race_window(sample_race_entry, window_days=1)
        assert start == date(2026, 6, 6)
        assert end == date(2026, 6, 8)

    def test_custom_window_7(self, sample_race_entry: RaceEntry) -> None:
        """±7 天窗口：6/7 → (5/31, 6/14)"""
        start, end = get_race_window(sample_race_entry, window_days=7)
        assert start == date(2026, 5, 31)
        assert end == date(2026, 6, 14)

    def test_window_zero(self, sample_race_entry: RaceEntry) -> None:
        """±0 天窗口：只有當天"""
        start, end = get_race_window(sample_race_entry, window_days=0)
        assert start == sample_race_entry.date
        assert end == sample_race_entry.date

    def test_window_crosses_month(self, make_race_entry) -> None:
        """窗口跨月份：3/1 ± 3 天 → (2/26, 3/4)"""
        race = make_race_entry(race_date=date(2026, 3, 1))
        start, end = get_race_window(race)
        assert start == date(2026, 2, 26)
        assert end == date(2026, 3, 4)

    def test_window_symmetry(self, sample_race_entry: RaceEntry) -> None:
        """窗口對稱：race.date - start == end - race.date"""
        start, end = get_race_window(sample_race_entry, window_days=5)
        assert (sample_race_entry.date - start).days == 5
        assert (end - sample_race_entry.date).days == 5
