@echo off
rem Single-file build: dist\FusedAuto.exe
setlocal
cd /d "%~dp0"
if not exist .venv-build (
    py -3.12 -m venv .venv-build || python -m venv .venv-build
)
call .venv-build\Scripts\activate.bat
python -m pip install -r requirements.txt || goto :error
if exist dist\FusedAuto rmdir /s /q dist\FusedAuto
python -m PyInstaller --noconfirm FusedAuto_onefile.spec || goto :error
echo.
echo Build finished: dist\FusedAuto.exe  (single file - copy it anywhere)
goto :eof
:error
echo Build FAILED.
exit /b 1
