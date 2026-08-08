# gpnews 全域指令修改計畫

## 目標

把目前的執行方式：

```powershell
python main.py
```

改成在任何資料夾都可以直接執行：

```powershell
gpnews
```

並且 `gpnews --limit 10`、`gpnews --no-open`、`gpnews --unit-test` 等參數要等同於：

```powershell
python C:\Users\Shan\Workspace2\MotoGP_Scrape\main.py --limit 10
```

## 建議方案

採用 Windows wrapper 指令，不改動現有 Python CLI 架構。

新增一個專案內的 `bin\gpnews.cmd`，內容負責：

1. 找到 MotoGP_Scrape 專案根目錄
2. 切到專案根目錄，避免相對路徑如 `.deps`、`latest_news_reports` 出問題
3. 執行 `python main.py`
4. 原樣轉交所有 CLI 參數

概念如下：

```bat
@echo off
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"
python "%PROJECT_ROOT%\main.py" %*
```

## 預計修改檔案

| 檔案 | 動作 | 用途 |
|------|------|------|
| `bin\gpnews.cmd` | 新增 | 提供全域可執行的 `gpnews` 指令 |
| `scripts\install_gpnews_path.ps1` | 新增 | 把 `bin` 加進使用者 PATH |
| `motogp_scraper\cli.py` | 更新 | 把 CLI help 裡的程式名稱與範例改成 `gpnews` |
| `README.md` | 更新 | 補上全域指令安裝與使用方式，並把執行範例改成 `gpnews` |

## PATH 安裝策略

不要把整個專案根目錄加到 PATH，只把這個資料夾加進 PATH：

```text
C:\Users\Shan\Workspace2\MotoGP_Scrape\bin
```

原因：

- PATH 裡只需要可執行 wrapper
- 避免專案根目錄裡其他檔案意外變成 shell 可搜尋項目
- 之後如果還要新增其他小工具，也可以集中放在 `bin`

## 安裝腳本設計

新增 `scripts\install_gpnews_path.ps1`，功能：

1. 算出專案的 `bin` 絕對路徑
2. 讀取目前使用者 PATH
3. 如果 PATH 已經包含該路徑，就顯示已安裝
4. 如果沒有，就加入使用者 PATH
5. 提醒使用者重新開一個 PowerShell 視窗

建議使用 .NET API 修改使用者 PATH，不使用 `setx`，避免 PATH 過長時被截斷。

概念如下：

```powershell
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BinPath = Join-Path $ProjectRoot "bin"
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($CurrentPath -split ";" -contains $BinPath) {
    Write-Host "gpnews is already on PATH: $BinPath"
    exit 0
}

$NewPath = ($CurrentPath.TrimEnd(";") + ";" + $BinPath).TrimStart(";")
[Environment]::SetEnvironmentVariable("Path", $NewPath, "User")

Write-Host "Added gpnews to PATH: $BinPath"
Write-Host "Open a new PowerShell window, then run: gpnews --help"
```

## 驗證步驟

完成修改後依序驗證：

```powershell
# 1. 直接用 wrapper 跑
.\bin\gpnews.cmd --help

# 2. 安裝 PATH
.\scripts\install_gpnews_path.ps1

# 3. 重新開一個 PowerShell 視窗後確認指令位置
where gpnews

# 4. 確認全域指令可用
gpnews --help

# 5. 確認原 CLI 參數仍可轉交
gpnews --limit 5 --skip-articles --no-open
```

## CLI Help 範例同步修改

`gpnews` 安裝完成後，使用者最常看到的是：

```powershell
gpnews --help
```

所以 `motogp_scraper\cli.py` 裡的 help 也要一起改，不能再出現 `python main.py ...`。

建議調整 `build_parser()`：

1. 設定 `prog="gpnews"`
2. 加上 `epilog`
3. 所有 examples 都使用 `gpnews`
4. 保留原本所有參數名稱，不改 CLI 行為

概念如下：

```python
parser = argparse.ArgumentParser(
    prog="gpnews",
    description="Scrape latest MotoGP news articles.",
    epilog=(
        "Examples:\n"
        "  gpnews --limit 10\n"
        "  gpnews --limit 10 --no-open\n"
        "  gpnews --limit 10 --skip-articles\n"
        "  gpnews --limit 10 --output-dir reports\n"
        "  gpnews --limit 10 --no-organize\n"
        "  gpnews --unit-test\n"
        "  gpnews --translate-report \"latest_news_reports\\2026-06-20 101500 latest news.md\" --translate-article 3"
    ),
    formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(
        prog,
        max_help_position=36,
    ),
)
```

預期 `gpnews --help` 顯示：

```text
usage: gpnews [-h] [--limit LIMIT] ...

Examples:
  gpnews --limit 10
  gpnews --limit 10 --no-open
  gpnews --limit 10 --skip-articles
  gpnews --limit 10 --output-dir reports
  gpnews --limit 10 --no-organize
  gpnews --unit-test
```

## 風險與注意事項

- 如果系統沒有 `python` 指令，`gpnews` 也會失敗；可在 wrapper 裡加入 fallback，改成先找 `python`，再找 `py -3`。
- PATH 修改後，已開啟的 PowerShell 視窗通常不會立刻吃到新 PATH，需要重新開視窗。
- 這個方案是 Windows 專用；如果未來要支援 macOS/Linux，可以再加 `bin/gpnews` shell script。
- wrapper 會切到專案根目錄執行，這樣目前報告輸出與本地相依套件路徑最安全。
- `README.md`、`main.py` 檔頭註解、`cli.py` help examples 需要同步改成 `gpnews`，避免文件與實際指令不一致。

## 建議實作順序

1. 新增 `bin\gpnews.cmd`
2. 本機驗證 `.\bin\gpnews.cmd --help`
3. 更新 `motogp_scraper\cli.py`，把 `prog` 與 help examples 改成 `gpnews`
4. 新增 `scripts\install_gpnews_path.ps1`
5. 執行安裝腳本，把 `bin` 加入 User PATH
6. 重新開 PowerShell，驗證 `gpnews --help`
7. 更新 `README.md` 和 `main.py` 檔頭註解裡的執行範例
