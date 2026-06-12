@echo off
REM 启动 Web 版校园导览演示
REM 默认地址: http://127.0.0.1:8765
REM 关闭方式: 直接关掉命令行窗口,或者按 Ctrl+C

setlocal
cd /d "%~dp0\.."

REM 解析参数 (端口 / site)
set PORT=8765
set SITE=
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--port" (
    set PORT=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--site" (
    set SITE=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-h" goto usage
if /i "%~1"=="--help" goto usage
shift
goto parse_args

:usage
echo Usage: %~nx0 [--port 8765] [--site PKU]
echo   --port  HTTP 端口 (默认 8765)
echo   --site  站点 ID,例如 PKU / THU / FDU (留空使用 global_sites.json 默认值)
exit /b 0

:args_done

REM 优先用 py -3 (项目里通用),找不到再回退到 python
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYEXE=py -3
) else (
    where python >nul 2>&1
    if %ERRORLEVEL%==0 (
        set PYEXE=python
    ) else (
        echo [ERROR] 没找到 py 或 python,请先安装 Python 3.10+
        pause
        exit /b 1
    )
)

echo ============================================================
echo  TourGraph 智能校园导览  -  Web 演示
echo  启动后请在浏览器打开: http://127.0.0.1:%PORT%
echo  按 Ctrl+C 或直接关闭本窗口即可停止服务
echo ============================================================
echo.

set CMD=%PYEXE% -m src.ui.demo_server --host 127.0.0.1 --port %PORT%
if not "%SITE%"=="" set CMD=%CMD% --site %SITE%

REM 等服务起来再弹浏览器
start "" http://127.0.0.1:%PORT%/
%CMD%

endlocal