@echo off
setlocal
chcp 65001 >nul
title AI 简历诊断 Agent

echo.
echo  ======================================
echo    AI 简历诊断 Agent
echo  ======================================
echo.

echo [1/4] 检查 Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  × 未检测到 Docker，请先安装并启动 Docker Desktop。
    pause
    exit /b 1
)

echo [1.1/4] 检查 Python...
py -3 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  × 未检测到 Python Launcher^(`py -3`^)，请先安装 Python。
    pause
    exit /b 1
)

echo [1.2/4] 检查 Node.js / npm...
call npm -v >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  × 未检测到 npm，请先安装 Node.js。
    pause
    exit /b 1
)

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo [2/4] 启动 Redis...
docker start resume-redis >nul 2>&1
if %errorlevel% neq 0 (
    docker run -d --name resume-redis -p 6379:6379 redis:7-alpine >nul 2>&1
    if %errorlevel% neq 0 (
        echo  × Redis 启动失败，请检查 Docker Desktop 状态。
        pause
        exit /b 1
    )
)

echo [3/4] 启动后端 FastAPI（同窗口后台）...
powershell -NoProfile -Command "$wd='%~dp0backend'; $out='%LOG_DIR%\backend.log'; $err='%LOG_DIR%\backend.err.log'; Start-Process -FilePath 'py' -ArgumentList '-3','-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8011','--reload' -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden" >nul 2>&1
set "ERR_BACK=%errorlevel%"
if %errorlevel% neq 0 (
    echo  × 后端启动命令执行失败。
    pause
    exit /b 1
)

echo [4/4] 启动前端 Vite（同窗口后台）...
if not exist "%~dp0frontend\node_modules\.bin\vite.cmd" (
    echo  检测到前端依赖未安装，正在执行 npm install...
    powershell -NoProfile -Command "$wd='%~dp0frontend'; $out='%LOG_DIR%\frontend.install.log'; $err='%LOG_DIR%\frontend.install.err.log'; Start-Process -FilePath 'npm.cmd' -ArgumentList 'install' -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -Wait -WindowStyle Hidden" >nul 2>&1
)
powershell -NoProfile -Command "$wd='%~dp0frontend'; $out='%LOG_DIR%\frontend.log'; $err='%LOG_DIR%\frontend.err.log'; Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden" >nul 2>&1
set "ERR_FRONT=%errorlevel%"
if %errorlevel% neq 0 (
    echo  × 前端启动命令执行失败。
    pause
    exit /b 1
)

echo.
echo  √ 启动完成！
echo.
echo  前端地址：http://localhost:5173
echo  后端地址：http://localhost:8011
echo.
echo  日志文件：
echo    %LOG_DIR%\backend.log
echo    %LOG_DIR%\frontend.log

start "" "http://localhost:5173"

pause
