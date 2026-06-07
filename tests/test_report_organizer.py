"""
test_report_organizer.py - 報告整理模組的單元測試 (pytest)

測試範圍：
- _build_race_folder_name() : 建立比賽資料夾名稱
- _parse_report_date()      : 從報告檔名解析出日期

執行方式：
    python main.py --unit-test
    或
    pytest tests/test_report_organizer.py -v
"""

from __future__ import annotations

from datetime import date

import pytest

from motogp_scraper.models import RaceEntry
from motogp_scraper.report_organizer import (
    _build_race_folder_name,
    _parse_report_date,
)


# ============================================================
# _build_race_folder_name 測試
# ============================================================
class TestBuildRaceFolderName:
    """_build_race_folder_name - 建立比賽資料夾名稱"""

    def test_default_format(self, sample_race_entry: RaceEntry) -> None:
        """預設匈牙利站的資料夾名稱"""
        result = _build_race_folder_name(sample_race_entry)
        assert result == "2026 Round 8 Hungary Grand Prix of Hungary"

    def test_round_1(self, make_race_entry) -> None:
        """第一站泰國"""
        race = make_race_entry(
            round_number=1,
            race_date=date(2026, 3, 1),
            grand_prix="Thailand PT Grand Prix of Thailand",
        )
        result = _build_race_folder_name(race)
        assert result == "2026 Round 1 Thailand PT Grand Prix of Thailand"

    def test_round_22(self, make_race_entry) -> None:
        """最後一站瓦倫西亞"""
        race = make_race_entry(
            round_number=22,
            race_date=date(2026, 11, 29),
            grand_prix="Valencian Community Motul Grand Prix of Valencia",
        )
        result = _build_race_folder_name(race)
        assert result == "2026 Round 22 Valencian Community Motul Grand Prix of Valencia"

    def test_contains_year(self, sample_race_entry: RaceEntry) -> None:
        """資料夾名稱包含年份"""
        result = _build_race_folder_name(sample_race_entry)
        assert str(sample_race_entry.date.year) in result

    def test_contains_round_number(self, sample_race_entry: RaceEntry) -> None:
        """資料夾名稱包含站號"""
        result = _build_race_folder_name(sample_race_entry)
        assert f"Round {sample_race_entry.round_number}" in result

    def test_contains_grand_prix(self, sample_race_entry: RaceEntry) -> None:
        """資料夾名稱包含大獎賽名稱"""
        result = _build_race_folder_name(sample_race_entry)
        assert sample_race_entry.grand_prix in result

    @pytest.mark.parametrize(
        "round_number, race_date, grand_prix, expected",
        [
            (1, date(2026, 3, 1), "Thailand PT Grand Prix of Thailand",
             "2026 Round 1 Thailand PT Grand Prix of Thailand"),
            (12, date(2026, 8, 9), "United Kingdom Qatar Airways Grand Prix of Great Britain",
             "2026 Round 12 United Kingdom Qatar Airways Grand Prix of Great Britain"),
            (22, date(2026, 11, 29), "Valencian Community Motul Grand Prix of Valencia",
             "2026 Round 22 Valencian Community Motul Grand Prix of Valencia"),
        ],
        ids=["round-1", "round-12", "round-22"],
    )
    def test_various_races(
        self, make_race_entry, round_number: int, race_date: date,
        grand_prix: str, expected: str,
    ) -> None:
        """參數化測試：不同站號和大獎賽名稱的資料夾名稱"""
        race = make_race_entry(
            round_number=round_number,
            race_date=race_date,
            grand_prix=grand_prix,
        )
        assert _build_race_folder_name(race) == expected


# ============================================================
# _parse_report_date 測試
# ============================================================
class TestParseReportDate:
    """_parse_report_date - 從報告檔名解析出日期"""

    # ---- 正常格式 ----

    def test_html_report(self) -> None:
        """HTML 報告檔名解析日期"""
        result = _parse_report_date("2026-06-06 140105 latest news.html")
        assert result == date(2026, 6, 6)

    def test_md_report(self) -> None:
        """Markdown 報告檔名解析日期"""
        result = _parse_report_date("2026-06-06 140105 latest news.md")
        assert result == date(2026, 6, 6)

    def test_different_time(self) -> None:
        """不同時間戳記的報告"""
        result = _parse_report_date("2026-12-31 235959 latest news.html")
        assert result == date(2026, 12, 31)

    def test_beginning_of_year(self) -> None:
        """年初日期"""
        result = _parse_report_date("2026-01-01 000000 latest news.md")
        assert result == date(2026, 1, 1)

    # ---- 無效格式 ----

    def test_no_date_prefix(self) -> None:
        """沒有日期前綴的檔名回傳 None"""
        assert _parse_report_date("latest news.html") is None

    def test_invalid_format(self) -> None:
        """格式不符回傳 None"""
        assert _parse_report_date("report_2026-06-06.html") is None

    def test_empty_string(self) -> None:
        """空字串回傳 None"""
        assert _parse_report_date("") is None

    def test_partial_date(self) -> None:
        """不完整的日期回傳 None"""
        assert _parse_report_date("2026-06-") is None

    def test_invalid_month(self) -> None:
        """無效月份（13）回傳 None"""
        assert _parse_report_date("2026-13-01 120000 latest news.html") is None

    def test_invalid_day(self) -> None:
        """無效日期（2/30）回傳 None"""
        assert _parse_report_date("2026-02-30 120000 latest news.html") is None

    # ---- parametrize 測試 ----

    @pytest.mark.parametrize(
        "filename, expected_date",
        [
            ("2026-03-01 100000 latest news.html", date(2026, 3, 1)),
            ("2026-06-07 180000 latest news.md", date(2026, 6, 7)),
            ("2026-11-29 230000 latest news.html", date(2026, 11, 29)),
        ],
        ids=["march", "june", "november"],
    )
    def test_various_valid_dates(self, filename: str, expected_date: date) -> None:
        """參數化測試：不同有效日期都能正確解析"""
        assert _parse_report_date(filename) == expected_date

    @pytest.mark.parametrize(
        "filename",
        [
            "not-a-date.html",
            "2026/06/06 report.html",
            "",
            "abcdefg",
            "2026-00-01 120000 news.html",  # month=0
        ],
        ids=["no-date", "slash-sep", "empty", "random", "month-zero"],
    )
    def test_various_invalid_filenames(self, filename: str) -> None:
        """參數化測試：各種無效檔名都回傳 None"""
        assert _parse_report_date(filename) is None
