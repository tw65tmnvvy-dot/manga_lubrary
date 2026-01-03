# Manga Library

A small cross-platform (Windows/macOS/Linux) Python application to manage a manga or book collection and a wishlist.

## What this includes

- `manga_library.py` — the main Tkinter application (single-file runnable)
- `requirements.txt` — minimal requirements; PyInstaller is optional and used for packaging
- `install.sh` and `install.bat` — helper installer scripts for non-technical users

## Minimum requirements

- Python 3.8 or newer (3.9+ recommended)
- Tk (usually included with Python on macOS and Windows installers)
- Optional: `pyinstaller` to create a standalone .exe or .app

### SQLite support (dummy-proof instructions)

The application ships with two storage backends:

- CSV (default) — works everywhere and requires no extra components.
- SQLite — uses Python's `sqlite3` module and is convenient and fast.

Most official Python installers include `sqlite3`. If you want SQLite storage you should verify your Python has sqlite support. Run this in a Terminal / PowerShell:

```bash
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

If the command prints a version (for example `3.39.2`) you're good to go. If it fails with an ImportError, follow one of these options:

- Windows: Download and run the official installer from https://python.org/downloads. The installer includes sqlite3. After installing, re-open Terminal/PowerShell and re-run the check above.
- macOS: Use the installer from https://python.org or use Homebrew (`brew install python`). If you used Homebrew and the check still fails you may need to reinstall Python ensuring sqlite development headers were present.

If you do not want to modify Python, no action is required — the app defaults to CSV storage. To run using SQLite explicitly (after ensuring sqlite support) start the app with:

```bash
python3 manga_library.py --storage sqlite
```

Or set the environment variable:

```bash
export MANGA_STORAGE=sqlite
```

## Quick start (for non-nerds)

macOS / Linux:

```bash
# open a Terminal and run these three commands (copy/paste)
python3 -m venv manga-env
source manga-env/bin/activate
pip install -r requirements.txt
python3 manga_library.py
```

Windows (PowerShell):

```powershell
python -m venv manga-env
manga-env\Scripts\Activate.ps1
pip install -r requirements.txt
python manga_library.py
```

You can also run the included `install.sh` (mac/linux) or `install_windows.bat` (Windows) which automate the steps above.
`install_windows.bat` checks for a suitable Python (3.8+) and installs all required packages including Pillow. If Python is missing or too old it will show a link to the official Python installer and stop, so nothing is changed on the system until you install a supported Python.

## Creating a standalone application

To create a single-file executable for distribution use PyInstaller.

On the same platform you want to distribute for (PyInstaller is platform-specific):

```bash
# Example for macOS
pip install pyinstaller
pyinstaller --onefile --windowed manga_library.py
# the .app or executable will be in the dist/ folder
```

On Windows run the same commands in a Windows environment to produce an .exe.

Notes:
- For macOS, you may prefer to use `--windowed` and a `.spec` to make a proper `.app` bundle.
- Code-signing and notarization are not handled by this guide.

## Printing

The app will create a temporary text file with your list and try to send it to the system print command:
- macOS: `lp` (usually available)
- Windows: `notepad /p` (sends file to default printer)
- Linux: `lpr`

If printing fails, the app will tell you where the temporary file was created so you can open and print it manually.

## Cover images

You can add a cover image when adding a book or wishlist item. The app will store images in `~/.manga_library_images/`.

- For best image compatibility (JPEG/PNG resizing) install Pillow (`pip install Pillow`).
- If Pillow is not available, the app will attempt to display PNG/GIF images using Tkinter's native support, but JPEG may not display.


## Next steps and improvements

- Add CSV or PDF export
- Add barcode/cover image support
- Add search and filtering
- Create proper installers (Inno Setup / pkgbuild) for true one-click installs

## License

Use freely and modify for personal use.
