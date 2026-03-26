@echo off
REM VeritySwarm — Cloudflare Tunnel Setup
REM Run this ONCE to establish the permanent tunnel
REM throne.verityswarm.com → localhost:8888
REM
REM PREREQUISITES:
REM   1. Cloudflare nameservers already set on verityswarm.com:
REM      aryanna.ns.cloudflare.com  /  kyree.ns.cloudflare.com
REM   2. cloudflared installed (already confirmed: v2025.8.1)
REM   3. Run this script as ADMINISTRATOR

echo.
echo [VeritySwarm] Cloudflare Tunnel Setup
echo ========================================
echo.

REM ── STEP 1: Login to Cloudflare (opens browser) ──────────────────────────
echo [1/5] Logging in to Cloudflare...
echo       A browser window will open. Authorize cloudflared for verityswarm.com
echo.
cloudflared tunnel login
if %ERRORLEVEL% neq 0 (
    echo ERROR: Login failed. Ensure you have access to verityswarm.com in Cloudflare.
    pause
    exit /b 1
)
echo [1/5] Login complete.
echo.

REM ── STEP 2: Create the tunnel ─────────────────────────────────────────────
echo [2/5] Creating tunnel 'verityswarm-prod'...
cloudflared tunnel create verityswarm-prod
if %ERRORLEVEL% neq 0 (
    echo ERROR: Tunnel creation failed. It may already exist.
    echo Try: cloudflared tunnel list
)
echo.

REM ── STEP 3: Extract tunnel ID ─────────────────────────────────────────────
echo [3/5] Getting tunnel ID...
FOR /F "tokens=1" %%i IN ('cloudflared tunnel list ^| findstr "verityswarm-prod" ^| awk "{print $1}"') DO SET TUNNEL_ID=%%i
echo       Tunnel ID: %TUNNEL_ID%
echo.

REM ── STEP 4: Create DNS CNAME route ───────────────────────────────────────
echo [4/5] Creating DNS route: throne.verityswarm.com → tunnel...
cloudflared tunnel route dns verityswarm-prod throne.verityswarm.com
if %ERRORLEVEL% neq 0 (
    echo ERROR: DNS route creation failed. Check Cloudflare dashboard.
)
echo.

REM ── STEP 5: Write config.yml ──────────────────────────────────────────────
echo [5/5] Writing config file...
set CONFIG_DIR=%USERPROFILE%\.cloudflared

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM The tunnel ID will be in the credentials file — read it
echo tunnel: %TUNNEL_ID% > "%CONFIG_DIR%\config.yml"
echo credentials-file: %CONFIG_DIR%\%TUNNEL_ID%.json >> "%CONFIG_DIR%\config.yml"
echo. >> "%CONFIG_DIR%\config.yml"
echo ingress: >> "%CONFIG_DIR%\config.yml"
echo   - hostname: throne.verityswarm.com >> "%CONFIG_DIR%\config.yml"
echo     service: http://localhost:8888 >> "%CONFIG_DIR%\config.yml"
echo   - service: http_status:404 >> "%CONFIG_DIR%\config.yml"

echo       Config written to: %CONFIG_DIR%\config.yml
echo.

REM ── STEP 6: Install as NSSM service ──────────────────────────────────────
echo [BONUS] Installing as NSSM service 'CloudflaredTunnel'...
where nssm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    nssm install CloudflaredTunnel cloudflared tunnel run verityswarm-prod
    nssm set CloudflaredTunnel DisplayName "VeritySwarm Cloudflare Tunnel"
    nssm set CloudflaredTunnel Description "Permanent tunnel: throne.verityswarm.com → localhost:8888"
    nssm set CloudflaredTunnel Start SERVICE_AUTO_START
    nssm set CloudflaredTunnel AppStdout "%USERPROFILE%\AnchorWithin\logs\cloudflared.log"
    nssm set CloudflaredTunnel AppStderr "%USERPROFILE%\AnchorWithin\logs\cloudflared_err.log"
    nssm start CloudflaredTunnel
    echo       NSSM service installed and started.
) else (
    echo       NSSM not found — start tunnel manually:
    echo       cloudflared tunnel run verityswarm-prod
)

echo.
echo ========================================
echo [VeritySwarm] Tunnel setup complete!
echo   URL:     https://throne.verityswarm.com
echo   Target:  http://localhost:8888
echo   Verify:  cloudflared tunnel info verityswarm-prod
echo ========================================
echo.
pause
