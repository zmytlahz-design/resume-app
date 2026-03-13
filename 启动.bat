@echo off
chcp 65001 >nul
title AI 简历诊断 Agent

echo.
echo  ╔══════════════════════════════════╗
echo  ║   AI 简历诊断 Agent              ║
echo  ╚══════════════════════════════════╝
echo.

echo [1/2] 启动服务中...
docker-compose -p resume-app up -d --build
if %errorlevel% neq 0 (
    echo.
    echo  × 启动失败！请确认 Docker Desktop 已运行。
    pause
    exit /b 1
)

echo.
echo  √ 启动成功！
echo.
echo  打开浏览器访问：http://localhost:3088
echo.

start http://localhost:3088

pause
