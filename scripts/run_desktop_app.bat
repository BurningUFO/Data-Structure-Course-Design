@echo off
REM 启动 Windows 桌面版校园导览 (pywebview 窗口)
REM 首次运行需要先执行 build_windows_desktop.ps1 打包出 .exe
REM 如果已经有 .venv-desktop,也可以直接以源码模式启动

setlocal
cd /d "%~dp0\.."

set SITE=
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--site" (
    set SITE=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--smoke" (
    set SMOKE=--smoke
    shift
    goto parse_args
)
if /i "%~1"=="-h" goto usage
if /i "%~1"=="--help" goto usage
shift
goto parse_args

:usage
echo Usage: %~nx0 [--site PKU] [--smoke]
echo   --site   站点 ID,例如 PKU / THU / FDU
echo   --smoke  不开窗口,只跑后端健康检查 (/api/health)
exit /b 0

:args_done

REM ---- 选择运行方式 ----
REM 1) 优先用打包好的 .exe (如果没有就走源码模式)
set EXE=%~dp0..\dist\IntelligentCampusGuide\IntelligentCampusGuide.exe
if exist "%EXE%" goto run_exe

REM 2) 源码模式: 优先用 .venv-desktop,否则用系统 py
set VENV_PY=%~dp0..\.venv-desktop\Scripts\python.exe
if exist "%VENV_PY%" (
    set PYEXE="%VENV_PY%"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL%==0 (
        set PYEXE=py -3
    ) else (
        where python >nul 2>&1
        if %ERRORLEVEL%==0 (
            set PYEXE=python
        ) else (
            echo [ERROR] 没找到 Python,请先安装 3.10+,或运行 scripts\build_windows_desktop.ps1 打包
            pause
            exit /b 1
        )
    )
)

echo ============================================================
echo  TourGraph 智能校园导览  -  桌面窗口
echo ============================================================
echo  没找到打包好的 exe,使用源码模式启动
echo  (如需独立 exe,请运行 scripts\build_windows_desktop.ps1)
echo ============================================================
echo.

set CMD=%PYEXE% -B -m src.ui.desktop_app
if not "%SITE%"=="" set CMD=%CMD% --site %SITE%
if defined SMOKE set CMD=%CMD% --smoke

%CMD%
goto :eof

:run_exe
echo ============================================================
echo  TourGraph 智能校园导览  -  桌面窗口 (打包版)
echo ============================================================
echo.

set CMD="%EXE%"
if not "%SITE%"=="" set CMD=%CMD% --site %SITE%
if defined SMOKE set CMD=%CMD% --smoke

%CMD%