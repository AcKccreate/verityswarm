@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  AnchorWithin Revenue Services Setup
REM  Run as Administrator on the Windows machine
REM ═══════════════════════════════════════════════════════════════════

echo.
echo ═══════════════════════════════════════════
echo   AnchorWithin Revenue Services Setup
echo ═══════════════════════════════════════════
echo.

REM ─── 1. Restart Telegram Commander Service ─────────────────────────
echo [1/4] Restarting AnchorWithinTelegram service...
nssm restart AnchorWithinTelegram
if %ERRORLEVEL% NEQ 0 (
    echo   WARNING: Service restart failed. You may need to install it first:
    echo   nssm install AnchorWithinTelegram python "%~dp0telegram_commander.py"
    echo   nssm set AnchorWithinTelegram AppDirectory "%~dp0"
    echo   nssm start AnchorWithinTelegram
) else (
    echo   DONE: AnchorWithinTelegram restarted
)
echo.

REM ─── 2. Schedule Content Poster (daily 10am) ──────────────────────
echo [2/4] Scheduling AnchorContentPoster (daily at 10:00am)...
schtasks /create /tn "AnchorContentPoster" /tr "python -m marketing.auto_poster" /sc daily /st 10:00 /f
if %ERRORLEVEL% EQU 0 (
    echo   DONE: Content poster scheduled for 10:00am daily
) else (
    echo   FAILED: Could not create scheduled task
)
echo.

REM ─── 3. Schedule Directory Submitter (daily 11am) ──────────────────
echo [3/4] Scheduling AnchorDirectorySubmit (daily at 11:00am)...
schtasks /create /tn "AnchorDirectorySubmit" /tr "python -m marketing.directory_submitter" /sc daily /st 11:00 /f
if %ERRORLEVEL% EQU 0 (
    echo   DONE: Directory submitter scheduled for 11:00am daily
) else (
    echo   FAILED: Could not create scheduled task
)
echo.

REM ─── 4. Schedule Morning Revenue Check (daily 7am) ────────────────
echo [4/4] Scheduling MorningRevenue (daily at 7:00am)...
schtasks /create /tn "MorningRevenue" /tr "python -m marketing.morning_revenue_check" /sc daily /st 07:00 /f
if %ERRORLEVEL% EQU 0 (
    echo   DONE: Morning revenue check scheduled for 7:00am daily
) else (
    echo   FAILED: Could not create scheduled task
)
echo.

REM ─── Summary ───────────────────────────────────────────────────────
echo ═══════════════════════════════════════════
echo   Setup Complete! Verify with:
echo.
echo   schtasks /query /tn "AnchorContentPoster"
echo   schtasks /query /tn "AnchorDirectorySubmit"
echo   schtasks /query /tn "MorningRevenue"
echo   nssm status AnchorWithinTelegram
echo ═══════════════════════════════════════════
echo.

REM ─── Run content poster + directory submitter right now ────────────
echo Running content poster NOW...
python -m marketing.auto_poster
echo.
echo Running directory submitter for resume-optimizer NOW...
python -m marketing.directory_submitter --tool resume-optimizer
echo.

echo All done. Revenue machines are running.
pause
