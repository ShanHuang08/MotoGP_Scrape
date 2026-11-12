"""2027 暫定賽程及跨年度報告分類的回歸測試。"""

from datetime import date, timedelta

import pytest

from motogp_scraper.calendar_data import MOTOGP_2027_CALENDAR, find_race_nearby
from motogp_scraper.report_organizer import organize_reports_for_race


def test_calendar_2027_integrity():
    assert len(MOTOGP_2027_CALENDAR) == 22
    assert [race.round_number for race in MOTOGP_2027_CALENDAR] == list(range(1, 23))
    expected_dates = [
        (3, 7), (3, 14), (4, 4), (4, 11), (4, 25), (5, 9),
        (5, 16), (5, 30), (6, 13), (6, 27), (7, 11), (7, 18),
        (8, 15), (8, 29), (9, 12), (9, 19), (10, 3), (10, 17),
        (10, 24), (10, 31), (11, 14), (11, 28),
    ]
    assert [race.date for race in MOTOGP_2027_CALENDAR] == [
        date(2027, month, day) for month, day in expected_dates
    ]
    assert all(race.circuit and race.grand_prix and race.country for race in MOTOGP_2027_CALENDAR)
    assert MOTOGP_2027_CALENDAR[3].country == "Argentina"
    assert MOTOGP_2027_CALENDAR[20].circuit == "Adelaide Street Circuit, Adelaide"


@pytest.mark.parametrize("race", MOTOGP_2027_CALENDAR)
@pytest.mark.parametrize("offset", [-3, 0, 3])
def test_2027_race_windows(race, offset):
    assert find_race_nearby(race.date + timedelta(days=offset)) == race


@pytest.mark.parametrize("target", [date(2027, 1, 1), date(2027, 3, 3), date(2027, 12, 2), date(2028, 3, 7)])
def test_outside_calendar(target):
    assert find_race_nearby(target) is None


def test_2027_report_folder(tmp_path):
    # 只操作測試暫存目錄，不搬動使用者既有報告。
    output_dir, race = organize_reports_for_race(tmp_path, today=date(2027, 3, 7))
    assert race == MOTOGP_2027_CALENDAR[0]
    assert output_dir.name == "2027 Round 1 Thailand Grand Prix of Thailand"
    assert output_dir.is_dir()
