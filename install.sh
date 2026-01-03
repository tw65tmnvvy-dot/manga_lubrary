#!/usr/bin/env bash
# Simple installer script for macOS / Linux for non-technical users.
set -e

VENV_NAME="manga-env"

echo "Creating virtual environment in ./\$VENV_NAME ..."
python3 -m venv "$VENV_NAME"
echo "Activating virtual environment and installing requirements..."
source "$VENV_NAME/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt || true

# Quick check whether this Python has sqlite3 support (optional)
echo "Checking for sqlite3 support in Python..."
python3 - <<'PY'
try:
	import sqlite3
	print('sqlite3 available, version', sqlite3.sqlite_version)
	raise SystemExit(0)
except Exception:
	print('sqlite3 NOT available in this Python. The app will still run with CSV storage (default).')
	print('If you want sqlite storage, install the official Python from https://python.org and re-run this script.')
	raise SystemExit(2)
PY
RC=$?
if [ $RC -ne 0 ]; then
	echo
	echo "Warning: sqlite3 support not detected. The application will continue and use CSV storage by default."
	echo "If you prefer SQLite, please install an official Python distribution from https://python.org and rerun this script."
	read -p "Press Enter to continue (CSV storage will be used) or Ctrl+C to abort..." _
fi

echo "To run the app:"
echo "  source $VENV_NAME/bin/activate"
echo "  python3 manga_library.py"

echo "If you want a standalone executable later, install pyinstaller and run:\n  pyinstaller --onefile --windowed manga_library.py"
