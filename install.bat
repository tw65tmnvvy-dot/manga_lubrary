@echo off
REM Simple installer script for Windows (cmd) for non-technical users.
SETLOCAL EnableDelayedExpansion
SET VENV_NAME=manga-env

echo Checking for Python (3.8+)...
python -c "import sys; print(sys.version_info.major, sys.version_info.minor)" > "%TEMP%\pyver.txt" 2>nul
IF %ERRORLEVEL% NEQ 0 (
	echo Python was not found on your system.
	echo Please install Python 3.8 or newer from https://www.python.org/downloads/windows
	echo After installing, re-open this command prompt and run this script again.
	pause
	exit /b 1
)
for /f "tokens=1,2" %%a in ('python -c "import sys; print(sys.version_info.major, sys.version_info.minor)"') do (
	set PY_MAJOR=%%a
	set PY_MINOR=%%b
)

if %PY_MAJOR% LSS 3 (
	echo Python 3.8 or newer is required. Found version: %PY_MAJOR%.%PY_MINOR%
	echo Please install Python 3.8+ from https://www.python.org/downloads/windows
	pause
	exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 8 (
	echo Python 3.8 or newer is required. Found version: %PY_MAJOR%.%PY_MINOR%
	echo Please install Python 3.8+ from https://www.python.org/downloads/windows
	pause
	exit /b 1
)

echo Creating virtual environment in .\%VENV_NAME% ...
if not exist %VENV_NAME% (
	python -m venv %VENV_NAME%
)

echo Activating virtual environment and installing requirements...
call %VENV_NAME%\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
	echo pip install failed. You can try running: python -m pip install -r requirements.txt
	pause
)

REM Quick check whether this Python has sqlite3 support (optional)
echo Checking for sqlite3 support in Python...
python -c "import sqlite3; print(sqlite3.sqlite_version)" > "%TEMP%\sqlcheck.txt" 2>nul
IF %ERRORLEVEL% NEQ 0 (
	echo.
	echo Warning: sqlite3 support not detected. The application will continue and use CSV storage by default.
	echo If you prefer SQLite, please install the official Python distribution from https://python.org/downloads/windows and rerun this script.
	pause
)

echo To run the app:
echo   call %VENV_NAME%\Scripts\activate
echo   python manga_library.py --storage sqlite   ^(optional if you installed sqlite support^)

echo If you want a standalone executable later, install pyinstaller and run:
echo   pip install pyinstaller
echo   pyinstaller --onefile --windowed manga_library.py

pause
ENDLOCAL
