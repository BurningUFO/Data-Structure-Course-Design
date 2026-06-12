@echo off
chcp 65001 >nul
title TourGraph 智能校园导览 - 启动菜单

cd /d "%~dp0\.."

:MENU
cls
echo ============================================================
echo   TourGraph 智能校园导览  -  启动菜单
echo ============================================================
echo.
echo   [1] Web 版演示  (浏览器打开 http://127.0.0.1:8765)
echo   [2] Windows 桌面窗口版  (pywebview)
echo   [3] Windows 桌面窗口 - 仅健康检查 (不开窗口)
echo   [4] 退出
echo.
set /p CHOICE=请选择 [1-4]:

if "%CHOICE%"=="1" call "%~dp0run_web_demo.bat" %*
if "%CHOICE%"=="2" call "%~dp0run_desktop_app.bat"
if "%CHOICE%"=="3" (
    call "%~dp0run_desktop_app.bat" --smoke
    echo.
    pause
    goto MENU
)
if "%CHOICE%"=="4" exit /b 0
goto MENU