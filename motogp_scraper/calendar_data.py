"""
calendar_data.py - 2026 MotoGP 賽程行事曆

儲存 2026 年賽季所有 22 站的比賽資訊，供 report_organizer.py 使用。
資料結構 RaceEntry 定義在 models.py，本檔案只負責存放行事曆資料和查詢函數。

主要函數：
- find_race_nearby()  - 檢查指定日期是否在某一站的 ±N 天窗口內

依賴關係：
- 被 report_organizer.py 引用
"""

from __future__ import annotations

from datetime import date, timedelta

from .models import RaceEntry


# ============================================================
# MOTOGP_2026_CALENDAR - 2026 年 MotoGP 完整賽程表（22 站）
# ============================================================
MOTOGP_2026_CALENDAR: tuple[RaceEntry, ...] = (
    RaceEntry(1,  date(2026, 3, 1),   "Thailand PT Grand Prix of Thailand", "Thailand"),
    RaceEntry(2,  date(2026, 3, 22),  "Brazil Estrella Galicia 0,0 Grand Prix of Brazil", "Brazil"),
    RaceEntry(3,  date(2026, 3, 29),  "United States Red Bull Grand Prix of the United States", "United States"),
    RaceEntry(4,  date(2026, 4, 26),  "Spain Estrella Galicia 0,0 Grand Prix of Spain", "Spain"),
    RaceEntry(5,  date(2026, 5, 10),  "France Michelin Grand Prix of France", "France"),
    RaceEntry(6,  date(2026, 5, 17),  "Catalonia Monster Energy Grand Prix of Catalunya", "Catalonia"),
    RaceEntry(7,  date(2026, 5, 31),  "Italy Brembo Grand Prix of Italy", "Italy"),
    RaceEntry(8,  date(2026, 6, 7),   "Hungary Grand Prix of Hungary", "Hungary"),
    RaceEntry(9,  date(2026, 6, 21),  "Czech Republic Grand Prix of Czechia", "Czech Republic"),
    RaceEntry(10, date(2026, 6, 28),  "Netherlands Grand Prix of the Netherlands", "Netherlands"),
    RaceEntry(11, date(2026, 7, 12),  "Germany Liqui Moly Grand Prix of Germany", "Germany"),
    RaceEntry(12, date(2026, 8, 9),   "United Kingdom Qatar Airways Grand Prix of Great Britain", "United Kingdom"),
    RaceEntry(13, date(2026, 8, 30),  "Aragon Grand Prix of Aragon", "Aragon"),
    RaceEntry(14, date(2026, 9, 13),  "San Marino Red Bull Grand Prix of San Marino and the Rimini Riviera", "San Marino"),
    RaceEntry(15, date(2026, 9, 20),  "Austria Grand Prix of Austria", "Austria"),
    RaceEntry(16, date(2026, 10, 4),  "Japan Motul Grand Prix of Japan", "Japan"),
    RaceEntry(17, date(2026, 10, 11), "Indonesia Pertamina Grand Prix of Indonesia", "Indonesia"),
    RaceEntry(18, date(2026, 10, 25), "Australia Grand Prix of Australia", "Australia"),
    RaceEntry(19, date(2026, 11, 1),  "Malaysia Petronas Grand Prix of Malaysia", "Malaysia"),
    RaceEntry(20, date(2026, 11, 8),  "Qatar Qatar Airways Grand Prix of Qatar", "Qatar"),
    RaceEntry(21, date(2026, 11, 22), "Portugal Repsol Grand Prix of Portugal", "Portugal"),
    RaceEntry(22, date(2026, 11, 29), "Valencian Community Motul Grand Prix of Valencia", "Valencian Community"),
)


# ============================================================
# find_race_nearby - 檢查指定日期是否在某站比賽的窗口範圍內
# ============================================================
# 參數：
#     target_date - 要檢查的日期（通常是今天）
#     window_days - 允許的天數差異（預設 3，即 ±3 天）
#
# 回傳：
#     如果在某站的窗口內 → 回傳該 RaceEntry
#     如果不在任何站的窗口內 → 回傳 None
#
# 如果同時在兩站的窗口內（極少見），回傳距離較近的那一站。
# 如果距離相同，回傳較早的那一站。
# ============================================================
def find_race_nearby(
    target_date: date,
    window_days: int = 3,
) -> RaceEntry | None:
    """檢查 target_date 是否在某一站的 ±window_days 天內。"""
    best_race: RaceEntry | None = None
    best_distance: int = window_days + 1  # 初始化為超出窗口的值

    for race in MOTOGP_2026_CALENDAR:
        distance = abs((target_date - race.date).days)
        if distance <= window_days and distance < best_distance:
            best_race = race
            best_distance = distance

    return best_race


# ============================================================
# get_race_window - 取得某站比賽的日期窗口範圍
# ============================================================
# 回傳 (window_start, window_end) 的 date tuple。
# 例如 window_days=3 且比賽在 6/7，則回傳 (6/4, 6/10)。
# ============================================================
def get_race_window(
    race: RaceEntry,
    window_days: int = 3,
) -> tuple[date, date]:
    """回傳比賽日期 ±window_days 的窗口範圍。"""
    start = race.date - timedelta(days=window_days)
    end = race.date + timedelta(days=window_days)
    return start, end
