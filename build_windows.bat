@echo off
REM Build a Windows standalone executable and create an installer using Inno Setup.
REM Run this on a Windows machine with Python installed and Inno Setup (ISCC) available.

:: Create a venv and install requirements (optional)
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Build the single-file executable with PyInstaller
pyinstaller --noconfirm --onefile --windowed --name MangaLibrary manga_library.py

:: Locate ISCC (Inno Setup Compiler). You can install Inno Setup from https://jrsoftware.org/isinfo.php
set ISCC_PATH="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC_PATH% goto :haveiscc
set ISCC_PATH="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist %ISCC_PATH% goto :haveiscc
echo Could not find ISCC.exe. Please install Inno Setup and rerun this script, or edit this batch to point to ISCC.exe.
echo Inno Setup: https://jrsoftware.org/isinfo.php
pause
exit /b 1

:haveiscc
echo Using ISCC at %ISCC_PATH%

:: Build installer. Pass the path to the produced exe to the ISS script via /DMyAppExe.
set EXE_PATH=%CD%\dist\MangaLibrary.exe
"%ISCC_PATH%" /DMyAppExe="%EXE_PATH%" windows_installer.iss

if %ERRORLEVEL% EQU 0 (
    echo Installer built successfully.
) else (
    echo Installer build failed with error %ERRORLEVEL%.
)

pause
