@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

if defined GPNEWS_PYTHON if exist "%GPNEWS_PYTHON%" (
    "%GPNEWS_PYTHON%" "%PROJECT_ROOT%\main.py" %*
    exit /b %ERRORLEVEL%
)

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    "%PROJECT_ROOT%\.venv\Scripts\python.exe" "%PROJECT_ROOT%\main.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%PROJECT_ROOT%\main.py" %*
    exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%PROJECT_ROOT%\main.py" %*
    exit /b %ERRORLEVEL%
)

echo [ERROR] Python 3 was not found. Install Python or add it to PATH. 1>&2
exit /b 1
