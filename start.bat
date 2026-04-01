@echo off
chcp 65001 >nul 2>&1
title 两阶段图像处理应用

echo ============================================
echo   两阶段图像处理应用 - 启动中...
echo   后端地址: http://localhost:8666
echo   前端请打开: frontend\index.html
echo ============================================
echo.

cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先创建: python -m venv .venv
    pause
    exit /b 1
)

echo [启动] 后端服务 (端口 8666)...
start "后端服务 - 端口8666" /min .venv\Scripts\python.exe .venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8666

timeout /t 2 /nobreak >nul
echo.
echo [完成] 服务已启动!
echo        后端 API: http://localhost:8666
echo        健康检查: http://localhost:8666/api/health
echo        前端页面: 请在浏览器打开 frontend\index.html
echo.
echo [提示] 前端设置中后端地址请填写: http://localhost:8666
echo        关闭此窗口即可停止服务
echo.
pause
