@echo off
chcp 65001 >nul
setlocal

rem ===================================================================
rem  Life2English · 本地演示界面启动脚本（Windows）
rem  仅使用 Python 标准库，不需要安装任何第三方依赖。
rem ===================================================================

cd /d "%~dp0"

echo ============================================================
echo   Life2English - 生活场景驱动的英语学习
echo   本地模拟版：不调用任何外部 API，不产生费用
echo ============================================================
echo.

rem 优先使用 py 启动器，其次 python
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo [错误] 未检测到 Python。请先安装 Python 3.10 及以上版本。
        echo         下载地址：https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
)

%PY% -X utf8 "scripts\web_server.py" %*
set "CODE=%errorlevel%"

if not "%CODE%"=="0" (
    echo.
    echo [提示] 服务异常退出（代码 %CODE%）。常见原因：
    echo        1. 端口 8770 已被占用 —— 可改用：启动演示界面.bat --port 8771
    echo        2. Python 版本过低 —— 需要 3.10 及以上
    echo.
    pause
)

endlocal
