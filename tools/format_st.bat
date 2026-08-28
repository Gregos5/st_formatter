@echo off
setlocal

set "REPO_ROOT=%~dp0.."
set "REPORT=%REPO_ROOT%\st_format_report.txt"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PYTHON=python"
    ) else (
        echo Could not find "py -3" or "python" on PATH. Install Python 3 to run the ST formatter.
        exit /b 3
    )
)

echo IEC 61131-3 Structured Text formatter
echo Target: %REPO_ROOT%\code
echo.

pushd "%REPO_ROOT%"

if /I "%~1"=="write" (
    echo Mode: WRITE - files under code\ will be modified in place, but only after each one
    echo passes its own self-validation check ^(see tools\st_formatter\validator.py^).
    %PYTHON% -m tools.st_formatter code --write --diff --report "%REPORT%"
) else (
    echo Mode: CHECK - dry run, no files will be modified.
    echo Pass "write" as the first argument to this script to apply changes.
    %PYTHON% -m tools.st_formatter code --check --diff --report "%REPORT%"
)

set "RC=%ERRORLEVEL%"
popd

echo.
echo Full report written to: %REPORT%
exit /b %RC%
