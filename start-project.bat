@echo off
echo Starting HostelSense main website (port 5000)...
start "HostelSense - Main Website" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate && python app.py"

timeout /t 2 /nobreak >nul

echo Starting Face Verification service (port 5001)...
start "HostelSense - Face Service" cmd /k "cd /d %~dp0face-service && call venv\Scripts\activate && python app.py"

echo.
echo Both servers are starting in separate windows.
echo Main website:   http://127.0.0.1:5000
echo Face service:   http://127.0.0.1:5001
echo.
echo You can close this window now.
pause
