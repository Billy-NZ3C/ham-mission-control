@echo off
rem Double-click to start the clock relay. Leave this window open (you can minimise it).
cd /d "%~dp0"
where py >nul 2>nul && (py clock_relay.py) || (python clock_relay.py)
echo.
echo The relay stopped. If it says Python was not found, install it from python.org (tick "Add python.exe to PATH").
pause
