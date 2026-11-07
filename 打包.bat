@echo off
chcp 65001 >nul
title 打包 PDF 隐私打码工具
cd /d "%~dp0"

echo.
echo ==========================================
echo   正在打包 PDF 隐私打码工具
echo   第一次打包大约需要 1-3 分钟，请勿关闭窗口
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没有找到 python。请先安装 Python 3.10 以上版本，
  echo         安装时记得勾选 "Add Python to PATH"。
  echo.
  pause
  exit /b 1
)

echo [1/5] 检查依赖...
python -m pip install -r requirements.txt --quiet
python -m pip install pyinstaller --quiet

echo [2/5] 同步项目地址到文档与 exe 属性...
python dev\sync_url.py

echo [3/5] 开始打包...
python -m PyInstaller "pdfmask.spec" --noconfirm --clean
if errorlevel 1 (
  echo.
  echo [失败] 打包出错，请把上面的红色文字截图反馈。
  pause
  exit /b 1
)

echo.
echo [4/5] 同步到本机日常使用的那一份...
python dev\sync_local_copy.py --close
if errorlevel 1 (
  echo.
  echo [提示] 本地副本没同步成功（不影响 dist 里的成品）。
  echo         如果是因为程序正在运行，关掉后再单独执行：
  echo         python dev\sync_local_copy.py
  echo.
)

echo.
echo [5/5] 完成。
echo 生成的程序在：%~dp0dist\PDF隐私打码工具.exe
echo.
if exist "%~dp0dist\PDF隐私打码工具.exe" explorer "%~dp0dist"
pause
