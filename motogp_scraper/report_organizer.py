"""
report_organizer.py - 報告自動收納/分類模組

根據 MotoGP 行事曆，自動將報告歸類到對應的比賽周末資料夾。

運作邏輯：
1. 檢查今天的日期是否在某一站比賽的 ±3 天窗口內
2. 如果是 → 在 latest_news_reports 目錄下建立該站資料夾
   （如 "2026 Round 8 Hungary Grand Prix of Hungary"）
3. 掃描目錄中現有報告，將日期落在窗口內的報告搬移到該資料夾
4. 回傳最終的輸出目錄路徑（讓 cli.py 直接把新報告存進去）

如果今天不在任何比賽周末窗口內，則不做任何收納動作，
報告直接存在 latest_news_reports 根目錄。

主要函數：
- organize_reports_for_race() - 檢查日期並執行收納

輔助函數：
- _parse_report_date()        - 從報告檔名解析出日期
- _build_race_folder_name()   - 建立資料夾名稱
- _move_reports_to_folder()   - 將舊報告搬移到資料夾

依賴關係：
- 被 cli.py 調用
- 引用 calendar_data.py 的行事曆資料
"""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from .calendar_data import RaceEntry, find_race_nearby, get_race_window


# ============================================================
# organize_reports_for_race - 主收納函數
# ============================================================
# 參數：
#     report_dir  - 報告輸出根目錄（如 "latest_news_reports"）
#     today       - 今天的日期（預設為 date.today()）
#     window_days - 比賽日期 ±N 天的窗口範圍（預設 3）
#
# 回傳：
#     (output_dir, race) tuple：
#     - output_dir : 新報告應該存放的目錄（可能是子資料夾或原始目錄）
#     - race       : 對應的 RaceEntry，如果不在任何比賽窗口則為 None
#
# 安全機制：
#     - 如果比賽資料夾已存在，跳過搬移步驟，直接回傳該資料夾路徑
#     - 不會重複建立資料夾，也不會覆蓋已有的報告檔案
# ============================================================
def organize_reports_for_race(
    report_dir: str | Path,
    today: date | None = None,
    window_days: int = 3,
) -> tuple[Path, RaceEntry | None]:
    """檢查今天是否接近某站比賽，自動收納舊報告並回傳輸出目錄。"""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    if today is None:
        today = date.today()

    # 步驟 1：檢查今天是否在某站比賽的窗口內
    race = find_race_nearby(today, window_days=window_days)

    if race is None:
        # 不在任何比賽窗口內，不做收納，直接回傳原始目錄
        return report_dir, None

    # 步驟 2：建立該站比賽的資料夾
    folder_name = _build_race_folder_name(race)
    race_folder = report_dir / folder_name

    if race_folder.exists() and race_folder.is_dir():
        # 資料夾已存在（之前執行過），跳過搬移舊報告的步驟，
        # 直接將新報告存入這個資料夾，避免任何覆蓋風險
        print(f"\n[INFO] Race folder already exists: {folder_name}")
        return race_folder, race

    # 資料夾不存在，首次建立並搬移窗口內的舊報告
    race_folder.mkdir(parents=True, exist_ok=True)

    # 步驟 3：取得該站的日期窗口範圍
    window_start, window_end = get_race_window(race, window_days=window_days)

    # 步驟 4：搬移落在窗口內的舊報告到該資料夾
    moved_count = _move_reports_to_folder(report_dir, race_folder, window_start, window_end)

    if moved_count > 0:
        print(f"\n[INFO] Organized {moved_count} report(s) into: {folder_name}")

    return race_folder, race


# ============================================================
# _build_race_folder_name - 建立比賽資料夾名稱
# ============================================================
# 格式："2026 Round 8 Hungary Grand Prix of Hungary"
# ============================================================
def _build_race_folder_name(race: RaceEntry) -> str:
    """建立如 '2026 Round 8 Hungary Grand Prix of Hungary' 的資料夾名稱。"""
    return f"{race.date.year} Round {race.round_number} {race.grand_prix}"


# ============================================================
# _parse_report_date - 從報告檔名解析出日期
# ============================================================
# 報告檔名格式：
#   "2026-06-06 140105 latest news.html"
#   "2026-06-06 140105 latest news.md"
# 解析前 10 個字元取得日期。
# ============================================================
def _parse_report_date(filename: str) -> date | None:
    """從檔名解析報告日期，格式不符則回傳 None。"""
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", filename)
    if not match:
        return None
    try:
        return date(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )
    except ValueError:
        return None


# ============================================================
# _move_reports_to_folder - 將窗口內的舊報告搬移到資料夾
# ============================================================
# 掃描 report_dir 根目錄的所有報告檔案，
# 如果日期落在 [window_start, window_end] 範圍內，
# 就搬到 race_folder 裡。
# ============================================================
def _move_reports_to_folder(
    report_dir: Path,
    race_folder: Path,
    window_start: date,
    window_end: date,
) -> int:
    """搬移符合日期範圍的報告，回傳搬移了多少個檔案。"""
    moved = 0
    # 只掃描報告檔案（.html 和 .md），不掃描子資料夾
    for file_path in sorted(report_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in (".html", ".md"):
            continue

        report_date = _parse_report_date(file_path.name)
        if report_date is None:
            continue

        # 日期在窗口內 → 搬移到比賽資料夾
        if window_start <= report_date <= window_end:
            destination = race_folder / file_path.name
            # 如果目標已經有同名檔案，加上序號避免覆蓋
            if destination.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                counter = 1
                while destination.exists():
                    destination = race_folder / f"{stem}_{counter}{suffix}"
                    counter += 1
            shutil.move(str(file_path), str(destination))
            moved += 1

    return moved
