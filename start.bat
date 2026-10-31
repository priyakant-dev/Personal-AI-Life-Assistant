@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   PERSONAL AI LIFE ASSISTANT
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  set PY=python
) else (
  set PY=py -3
)
if not exist "venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  %PY% -m venv venv
  if errorlevel 1 goto error
)
echo [2/3] Installing/checking dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
echo [3/3] Starting app at http://127.0.0.1:8000
echo Keep this window open while using the app.
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
goto end
:error
echo.
echo ERROR: Setup failed. Check the messages above and ensure Python 3.10+ is installed.
pause
:end
endlocal
