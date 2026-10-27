@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Competition Finder - spare laptop web deploy
echo  Run this ON THE SPARE LAPTOP, after copying this folder
echo  to a LOCAL folder (not OneDrive), e.g. C:\stratgen
echo ============================================================
echo.

rem --- 1. Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python not found.
    echo     Install it from python.org and tick "Add python.exe to PATH".
    echo     Then run this script again.
    pause
    exit /b 1
)
echo [ok] Python found.

rem --- 2. Dependencies ---
python -m pip install --quiet --disable-pip-version-check requests openpyxl
echo [ok] Dependencies installed (requests, openpyxl).

rem --- 3. Tailscale ---
where tailscale >nul 2>nul
if errorlevel 1 (
    echo [X] Tailscale not found.
    echo     Install it:  winget install Tailscale.Tailscale
    echo     Then open the Tailscale app and sign in with the SAME
    echo     account as your main laptop (it joins tailnet taila24302).
    echo     Then run this script again.
    pause
    exit /b 1
)
tailscale status >nul 2>nul
if errorlevel 1 (
    echo [X] Tailscale is installed but not logged in / not connected.
    echo     Sign in via the Tailscale app, then run this script again.
    pause
    exit /b 1
)
echo [ok] Tailscale is connected.

rem --- 4. Start the dashboard (no window, local only) ---
taskkill /f /im pythonw.exe >nul 2>nul
start "" pythonw server.py
timeout /t 3 /nobreak >nul
echo [ok] Dashboard started on 127.0.0.1:8765.

rem --- 5. Expose it to the whole internet (public HTTPS, survives reboots) ---
tailscale funnel --bg 8765 --yes
if errorlevel 1 (
    echo.
    echo [X] Funnel failed to start. Most likely cause: Funnel is not enabled
    echo     for this tailnet yet. One-time fix: open
    echo     https://console.tailscale.com , go to DNS, enable "Funnel",
    echo     then run this script again.
    pause
    exit /b 1
)
echo [ok] Funnel is on.

rem --- 6. Show the public URL ---
for /f "tokens=2" %%a in ('tailscale status --self 2^>nul') do set NODE=%%a
echo.
echo ============================================================
if defined NODE (
    echo  PUBLIC URL - works from any device, no login needed:
    echo.
    echo     https://%NODE%.taila24302.ts.net/
) else (
    echo  Your public URL is shown in the Tailscale app or at
    echo  https://console.tailscale.com (it looks like
    echo  https://this-laptop.taila24302.ts.net/)
)
echo ============================================================
echo.
echo To make the dashboard auto-start after a reboot, put a shortcut to
echo "start_server.bat" in your Startup folder (Win+R, type shell:startup).
echo Tailscale and the funnel survive reboots on their own.
echo.
echo To stop sharing the public URL later:  tailscale funnel --https=443 off
pause
