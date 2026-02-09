@echo off
REM ========================================
REM Windows 自动安装脚本
REM 自动检测并安装项目依赖
REM ========================================

setlocal enabledelayedexpansion

echo ============================================================
echo         语音助手系统 - 自动安装脚本 (Windows)
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python
    echo [INFO] 请先安装 Python 3.10+ 从 https://www.python.org/
    pause
    exit /b 1
)

REM 获取 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>&1') do set PYTHON_VERSION=%%i
echo [INFO] Python 版本: %PYTHON_VERSION%

REM 检测架构
echo [INFO] 检测系统架构...
systeminfo | findstr /C /C:"64-bit" >nul
if errorlevel 1 (
    set ARCH_TYPE=x86
    echo [INFO] 这是 32 位系统 (不支持)
    pause
    exit /b 1
) else (
    set ARCH_TYPE=amd64
    echo [INFO] 检测到 AMD64 (64位) 架构
)

REM 检查虚拟环境
if defined VIRTUAL_ENV (
    echo [INFO] 虚拟环境已激活: %VIRTUAL_ENV%
) else (
    echo [WARN] 未检测到虚拟环境
    echo [INFO] 创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [INFO] 虚拟环境创建成功

    echo [INFO] 激活虚拟环境...
    call .venv\Scripts\activate.bat
    echo [INFO] 虚拟环境已激活
)

REM 更新 pip
echo.
echo [INFO] 更新 pip...
python -m pip install --upgrade pip setuptools wheel

REM 安装 Python 依赖
echo [INFO] 安装 Python 依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
)

REM 验证安装
echo.
echo [INFO] 验证安装...
python -c "import yaml, numpy, openwakeword; print('[SUCCESS] 所有依赖安装成功')"
if errorlevel 1 (
    echo [ERROR] 依赖验证失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                      安装完成！
echo ============================================================
echo.
echo [INFO] 下一步操作:
echo   1. 配置系统: copy config.example.yaml config.yaml
echo   2. 运行测试: python tests\manual\test_hardware.py
echo   3. 运行主程序: python main.py
echo.

pause
