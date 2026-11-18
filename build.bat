@echo off
rem FusedAuto build script (Windows). Creates .venv-build, installs requirements, builds dist\FusedAuto\
setlocal
cd /d "%~dp0"
if not exist .venv-build (
    py -3.12 -m venv .venv-build || python -m venv .venv-build
)
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :error
python -m PyInstaller --noconfirm FusedAuto.spec || goto :error
rem License texts (LICENSE, LGPL/GPL, third-party notices) are bundled by the spec file.
echo.
echo Build finished: dist\FusedAuto\FusedAuto.exe
goto :eof
:error
echo Build FAILED.
exit /b 1
