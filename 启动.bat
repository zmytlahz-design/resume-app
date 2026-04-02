@echo off
chcp 65001 >nul 2>&1
setlocal
cd /d "%~dp0"

echo.
echo  ======================================
echo    AI Resume Agent
echo  ======================================
echo.

echo [1/4] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [X] Docker not found. Install and start Docker Desktop.
    pause
    exit /b 1
)

echo [1.1/4] Checking Python...
py -3 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [X] Python launcher ^(py -3^) not found.
    pause
    exit /b 1
)

echo [1.2/4] Checking Node.js / npm...
call npm -v >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [X] npm not found. Install Node.js.
    pause
    exit /b 1
)

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo [2/4] Starting PostgreSQL...

docker start resume-postgres >nul 2>&1
if errorlevel 1 (
    docker run -d --name resume-postgres -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=resume_app postgres:16-alpine >nul 2>&1
    if errorlevel 1 (
        echo  [X] PostgreSQL failed. Check Docker Desktop.
        pause
        exit /b 1
    )
)
echo  Waiting for PostgreSQL...
timeout /t 3 /nobreak >nul

echo [3/4] Starting backend FastAPI...
powershell -NoProfile -Command "$wd='%~dp0backend'; $out='%LOG_DIR%\backend.log'; $err='%LOG_DIR%\backend.err.log'; Start-Process -FilePath 'py' -ArgumentList '-3','-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8011','--reload' -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden; exit 0" >nul 2>&1

echo [4/4] Starting frontend Vite...
if not exist "%~dp0frontend\node_modules\.bin\vite.cmd" (
    echo  Running npm install...
    powershell -NoProfile -Command "$wd='%~dp0frontend'; $out='%LOG_DIR%\frontend.install.log'; $err='%LOG_DIR%\frontend.install.err.log'; Start-Process -FilePath 'npm.cmd' -ArgumentList 'install' -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -Wait -WindowStyle Hidden"
)
powershell -NoProfile -Command "$wd='%~dp0frontend'; $out='%LOG_DIR%\frontend.log'; $err='%LOG_DIR%\frontend.err.log'; Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden; exit 0" >nul 2>&1

echo.
echo  OK - processes started. Waiting for HTTP ports...
echo  Frontend: http://localhost:5173
echo  Backend:  http://localhost:8011
echo.
echo  Logs:
echo    %LOG_DIR%\backend.log
echo    %LOG_DIR%\frontend.log

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\wait-for-dev.ps1"

pause
