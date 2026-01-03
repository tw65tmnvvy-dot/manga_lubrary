#!/usr/bin/env python3
"""
Manga Library - simple cross-platform Tkinter app

Features:
- Store books in a local SQLite database
- Wishlist support
- Show current library and wishlist
- Print lists (writes a temporary text file and sends to system print)

This file is meant to be runnable directly with Python 3.8+ (Tkinter is in the stdlib).
"""
import sqlite3
import csv
from typing import List, Dict
from tkinter import filedialog
import shutil
import uuid
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except Exception:
    HAS_PIL = False
import sys
import os
import platform
import subprocess
import tempfile
import zipfile
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

DB_PATH = Path.home() / '.manga_library.db'
IMAGES_DIR = Path.home() / '.manga_library_images'
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = Path.home() / '.manga_library_config.json'


def load_config():
    default = {
        'resize_enabled': True,
        'max_width': 800,
        'max_height': 1200,
        # preview size used in the UI for cover thumbnails (pixels)
        'preview_width': 300,
        'preview_height': 440,
        'quality': 85,
        'optimize': True,
    }
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                default.update(cfg)
    except Exception:
        pass
    return default


def save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


CONFIG = load_config()


class DataStore:
    def __init__(self, path=DB_PATH):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                year TEXT,
                notes TEXT,
                cover TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wishlist (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                notes TEXT,
                cover TEXT
            )
            """
        )
        self.conn.commit()
        # ensure existing DBs get the cover column
        self._ensure_cover_column()

    def _ensure_cover_column(self):
        cur = self.conn.cursor()
        # check books
        cur.execute("PRAGMA table_info(books)")
        cols = [r[1] for r in cur.fetchall()]
        if 'cover' not in cols:
            cur.execute("ALTER TABLE books ADD COLUMN cover TEXT")
        cur.execute("PRAGMA table_info(wishlist)")
        cols = [r[1] for r in cur.fetchall()]
        if 'cover' not in cols:
            cur.execute("ALTER TABLE wishlist ADD COLUMN cover TEXT")
        self.conn.commit()

    # Books
    def add_book(self, title, author='', year='', notes=''):
        # cover will be handled separately; this signature may be extended
        cur = self.conn.cursor()
        cur.execute("INSERT INTO books (title,author,year,notes,cover) VALUES (?,?,?,?,?)", (title, author, year, notes, None))
        self.conn.commit()
        return cur.lastrowid

    def list_books(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id,title,author,year,notes,cover FROM books ORDER BY title")
        return cur.fetchall()

    def delete_book(self, book_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM books WHERE id=?", (book_id,))
        self.conn.commit()

    # Wishlist
    def add_wishlist(self, title, notes=''):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO wishlist (title,notes,cover) VALUES (?,?,?)", (title, notes, None))
        self.conn.commit()
        return cur.lastrowid

    def list_wishlist(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id,title,notes,cover FROM wishlist ORDER BY title")
        return cur.fetchall()

    def delete_wishlist(self, wi_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM wishlist WHERE id=?", (wi_id,))
        self.conn.commit()

    def move_wishlist_to_books(self, wi_id, author='', year=''):
        cur = self.conn.cursor()
        cur.execute("SELECT title,notes,cover FROM wishlist WHERE id=?", (wi_id,))
        row = cur.fetchone()
        if not row:
            return False
        title, notes, cover = row
        cur.execute("INSERT INTO books (title,author,year,notes,cover) VALUES (?,?,?,?,?)", (title, author, year, notes, cover))
        cur.execute("DELETE FROM wishlist WHERE id=?", (wi_id,))
        self.conn.commit()
        return True

    def set_book_cover(self, book_id, src_path):
        """Copy cover image into images dir and update record to point to it."""
        if not src_path:
            return
        src = Path(src_path)
        if not src.exists():
            return
        # optionally resize/optimize image using Pillow
        ext = src.suffix
        dest = IMAGES_DIR / f"book_{book_id}{ext}"
        try:
            if HAS_PIL and CONFIG.get('resize_enabled', True):
                img = Image.open(str(src))
                img.thumbnail((CONFIG.get('max_width', 800), CONFIG.get('max_height', 1200)))
                img.save(str(dest), quality=int(CONFIG.get('quality', 85)), optimize=bool(CONFIG.get('optimize', True)))
            else:
                shutil.copy(src, dest)
        except Exception:
            shutil.copy(src, dest)
        cur = self.conn.cursor()
        cur.execute("UPDATE books SET cover=? WHERE id=?", (str(dest), book_id))
        self.conn.commit()

    def export_covers(self, target_zip):
        """Create a zip archive containing all cover images and a metadata file."""
        with zipfile.ZipFile(target_zip, 'w') as zf:
            # include images dir
            for p in IMAGES_DIR.glob('*'):
                zf.write(p, arcname=p.name)
            # add metadata indicating type
            zf.writestr('metadata.txt', 'manga_library_covers')
        return True

    def import_covers(self, source_zip):
        try:
            with zipfile.ZipFile(source_zip, 'r') as zf:
                zf.extractall(IMAGES_DIR)
            return True
        except Exception:
            return False

    def set_wishlist_cover(self, wish_id, src_path):
        if not src_path:
            return
        src = Path(src_path)
        if not src.exists():
            return
        ext = src.suffix
        dest = IMAGES_DIR / f"wish_{wish_id}{ext}"
        try:
            if HAS_PIL and CONFIG.get('resize_enabled', True):
                img = Image.open(str(src))
                img.thumbnail((CONFIG.get('max_width', 800), CONFIG.get('max_height', 1200)))
                img.save(str(dest), quality=int(CONFIG.get('quality', 85)), optimize=bool(CONFIG.get('optimize', True)))
            else:
                shutil.copy(src, dest)
        except Exception:
            shutil.copy(src, dest)
        cur = self.conn.cursor()
        cur.execute("UPDATE wishlist SET cover=? WHERE id=?", (str(dest), wish_id))
        self.conn.commit()

    def export_all(self, target_zip):
        """Export DB and images into a zip for backup."""
        try:
            with zipfile.ZipFile(target_zip, 'w') as zf:
                # add DB file
                if self.path.exists():
                    zf.write(self.path, arcname=self.path.name)
                # add images
                for p in IMAGES_DIR.glob('*'):
                    zf.write(p, arcname=f'images/{p.name}')
            return True
        except Exception:
            return False

    def import_all(self, source_zip):
        try:
            with zipfile.ZipFile(source_zip, 'r') as zf:
                # extract DB into user home
                for member in zf.namelist():
                    if member == self.path.name:
                        zf.extract(member, Path.home())
                    elif member.startswith('images/'):
                        zf.extract(member, IMAGES_DIR.parent)
            return True
        except Exception:
            return False


class CSVDataStore:
    """A simple CSV-backed datastore for max compatibility (no sqlite needed).

    Files are stored in the user's home directory as:
      - .manga_library_books.csv
      - .manga_library_wishlist.csv
    """

    def __init__(self, dirpath: Path = None):
        self.dirpath = Path(dirpath) if dirpath else Path.home()
        self.books_file = self.dirpath / '.manga_library_books.csv'
        self.wish_file = self.dirpath / '.manga_library_wishlist.csv'
        self._ensure_files()

    def _ensure_files(self):
        if not self.books_file.exists():
            with open(self.books_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'title', 'author', 'year', 'notes', 'cover'])
                writer.writeheader()
        if not self.wish_file.exists():
            with open(self.wish_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'title', 'notes', 'cover'])
                writer.writeheader()

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_csv(self, path: Path, rows: List[Dict[str, str]]):
        # atomic write
        tmp = path.with_suffix('.tmp')
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            if path == self.books_file:
                fieldnames = ['id', 'title', 'author', 'year', 'notes', 'cover']
            else:
                fieldnames = ['id', 'title', 'notes', 'cover']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        tmp.replace(path)

    def _next_id(self, rows: List[Dict[str, str]]) -> int:
        maxid = 0
        for r in rows:
            try:
                rid = int(r.get('id') or 0)
                if rid > maxid:
                    maxid = rid
            except Exception:
                continue
        return maxid + 1

    # Books
    def add_book(self, title, author='', year='', notes=''):
        rows = self._read_csv(self.books_file)
        nid = self._next_id(rows)
        rows.append({'id': str(nid), 'title': title, 'author': author, 'year': year, 'notes': notes, 'cover': ''})
        self._write_csv(self.books_file, rows)
        return nid

    def list_books(self):
        rows = self._read_csv(self.books_file)
        out = []
        for r in rows:
            try:
                out.append((int(r['id']), r['title'], r.get('author', ''), r.get('year', ''), r.get('notes', ''), r.get('cover', '')))
            except Exception:
                continue
        # sort by title
        out.sort(key=lambda x: x[1].lower() if x[1] else '')
        return out

    def delete_book(self, book_id):
        rows = self._read_csv(self.books_file)
        rows = [r for r in rows if str(r.get('id')) != str(book_id)]
        self._write_csv(self.books_file, rows)

    def set_book_cover(self, book_id, src_path):
        if not src_path:
            return
        src = Path(src_path)
        if not src.exists():
            return
        ext = src.suffix
        dest = IMAGES_DIR / f"book_{book_id}{ext}"
        shutil.copy(src, dest)
        rows = self._read_csv(self.books_file)
        for r in rows:
            if str(r.get('id')) == str(book_id):
                r['cover'] = str(dest)
        self._write_csv(self.books_file, rows)
        return True

    # Wishlist
    def add_wishlist(self, title, notes=''):
        rows = self._read_csv(self.wish_file)
        nid = self._next_id(rows)
        rows.append({'id': str(nid), 'title': title, 'notes': notes, 'cover': ''})
        self._write_csv(self.wish_file, rows)
        return nid

    def list_wishlist(self):
        rows = self._read_csv(self.wish_file)
        out = []
        for r in rows:
            try:
                out.append((int(r['id']), r['title'], r.get('notes', ''), r.get('cover', '')))
            except Exception:
                continue
        out.sort(key=lambda x: x[1].lower() if x[1] else '')
        return out

    def delete_wishlist(self, wi_id):
        rows = self._read_csv(self.wish_file)
        rows = [r for r in rows if str(r.get('id')) != str(wi_id)]
        self._write_csv(self.wish_file, rows)

    def move_wishlist_to_books(self, wi_id, author='', year=''):
        wrows = self._read_csv(self.wish_file)
        match = None
        for r in wrows:
            if str(r.get('id')) == str(wi_id):
                match = r
                break
        if not match:
            return False
        # add to books
        nid = self.add_book(match.get('title', ''), author, year, match.get('notes', ''))
        if match.get('cover'):
            # copy existing cover file to new book id
            try:
                src = Path(match.get('cover'))
                if src.exists():
                    self.set_book_cover(nid, src)
            except Exception:
                pass
        # remove from wishlist
        wrows = [r for r in wrows if str(r.get('id')) != str(wi_id)]
        self._write_csv(self.wish_file, wrows)
        return True


class App(tk.Tk):
    def __init__(self, store: DataStore):
        super().__init__()
        self.store = store
        self.title('Manga Library')
        self.geometry('800x520')

        self._create_widgets()
        self._refresh_all()

    def _create_widgets(self):
        # Notebook: Library / Wishlist
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=8, pady=8)

        self.lib_frame = ttk.Frame(nb)
        self.wish_frame = ttk.Frame(nb)
        nb.add(self.lib_frame, text='Library')
        nb.add(self.wish_frame, text='Wishlist')

        # Library frame
        lf = self.lib_frame
        lf.columnconfigure(0, weight=1)
        lf.columnconfigure(1, weight=0)

        self.book_listbox = tk.Listbox(lf)
        self.book_listbox.grid(row=0, column=0, sticky='nsew', padx=6, pady=6)
        self.book_listbox.bind('<<ListboxSelect>>', self.on_book_select)

        lib_right = ttk.Frame(lf)
        lib_right.grid(row=0, column=1, sticky='ns', padx=6, pady=6)

        ttk.Button(lib_right, text='Add Book', command=self.add_book_dialog).pack(fill='x', pady=4)
        ttk.Button(lib_right, text='Remove Book', command=self.remove_selected_book).pack(fill='x', pady=4)
        ttk.Button(lib_right, text='Print Library', command=lambda: self.print_list(kind='books')).pack(fill='x', pady=4)
        ttk.Button(lib_right, text='Refresh', command=self._refresh_books).pack(fill='x', pady=4)
        # Cover preview
        # Increase label size so images display larger; width/height are in text units
        self.cover_label = tk.Label(lib_right, text='No cover', width=30, height=18, bd=1, relief='sunken')
        self.cover_label.pack(pady=8)


        # Wishlist frame
        wf = self.wish_frame
        wf.columnconfigure(0, weight=1)
        wf.columnconfigure(1, weight=0)

        self.wish_listbox = tk.Listbox(wf)
        self.wish_listbox.grid(row=0, column=0, sticky='nsew', padx=6, pady=6)
        self.wish_listbox.bind('<<ListboxSelect>>', self.on_wish_select)

        wish_right = ttk.Frame(wf)
        wish_right.grid(row=0, column=1, sticky='ns', padx=6, pady=6)

        ttk.Button(wish_right, text='Add to Wishlist', command=self.add_wishlist_dialog).pack(fill='x', pady=4)
        ttk.Button(wish_right, text='Remove from Wishlist', command=self.remove_selected_wishlist).pack(fill='x', pady=4)
        ttk.Button(wish_right, text='Move to Library', command=self.move_selected_wishlist).pack(fill='x', pady=4)
        ttk.Button(wish_right, text='Print Wishlist', command=lambda: self.print_list(kind='wishlist')).pack(fill='x', pady=4)
        ttk.Button(wish_right, text='Refresh', command=self._refresh_wishlist).pack(fill='x', pady=4)
        # wishlist cover preview (re-use same image label)
        self.wish_cover_label = tk.Label(wish_right, text='No cover', width=30, height=18, bd=1, relief='sunken')
        self.wish_cover_label.pack(pady=8)

        # Change cover buttons
        ttk.Button(lib_right, text='Change cover', command=self.change_cover_selected).pack(fill='x', pady=2)
        ttk.Button(wish_right, text='Change wish cover', command=self.change_wish_cover_selected).pack(fill='x', pady=2)

        # Status bar
        self.status = ttk.Label(self, text='Ready', relief='sunken', anchor='w')
        self.status.pack(fill='x', side='bottom')

        # Menu
        men = tk.Menu(self)
        self.config(menu=men)
        helpm = tk.Menu(men, tearoff=0)
        men.add_cascade(label='Help', menu=helpm)
        helpm.add_command(label='Minimum requirements', command=self.show_requirements)
        helpm.add_command(label='About', command=lambda: messagebox.showinfo('About', 'Manga Library\nSimple Tkinter app'))

        tools = tk.Menu(men, tearoff=0)
        men.add_cascade(label='Tools', menu=tools)
        tools.add_command(label='Export Covers...', command=self.export_covers_dialog)
        tools.add_command(label='Import Covers...', command=self.import_covers_dialog)
        tools.add_separator()
        tools.add_command(label='Export full backup...', command=self.export_all_dialog)
        tools.add_command(label='Import full backup...', command=self.import_all_dialog)
        tools.add_separator()
        tools.add_command(label='Migrate storage...', command=self.migrate_dialog)
        tools.add_command(label='Settings...', command=self.open_settings_dialog)

    def _refresh_all(self):
        self._refresh_books()
        self._refresh_wishlist()

    def _refresh_books(self):
        self.book_listbox.delete(0, tk.END)
        self.books = self.store.list_books()
        for b in self.books:
            bid, title, author, year, notes, cover = b
            disp = f"{title}"
            if author:
                disp += f" — {author}"
            if year:
                disp += f" ({year})"
            self.book_listbox.insert(tk.END, disp)
        self.status.config(text=f'Books: {len(self.books)}')

    def _refresh_wishlist(self):
        self.wish_listbox.delete(0, tk.END)
        self.wishlist = self.store.list_wishlist()
        for w in self.wishlist:
            wid, title, notes, cover = w
            self.wish_listbox.insert(tk.END, title)
        # Don't override library status line, show wishlist count in title
        self.status.config(text=f'Library: {len(self.books)} | Wishlist: {len(self.wishlist)}')

    # Book actions
    def add_book_dialog(self):
        title = simpledialog.askstring('Add Book', 'Title:')
        if not title:
            return
        author = simpledialog.askstring('Add Book', 'Author (optional):') or ''
        year = simpledialog.askstring('Add Book', 'Year (optional):') or ''
        notes = simpledialog.askstring('Add Book', 'Notes (optional):') or ''
        cover_path = filedialog.askopenfilename(title='Select cover image (optional)', filetypes=[('Image files','*.png;*.jpg;*.jpeg;*.gif;*.bmp'),('All files','*.*')])
        book_id = self.store.add_book(title.strip(), author.strip(), year.strip(), notes.strip())
        if cover_path:
            try:
                # store cover via backend
                if hasattr(self.store, 'set_book_cover'):
                    self.store.set_book_cover(book_id, cover_path)
            except Exception:
                pass
        self._refresh_books()

    def remove_selected_book(self):
        sel = self.book_listbox.curselection()
        if not sel:
            messagebox.showinfo('Info', 'No book selected')
            return
        idx = sel[0]
        bid = self.books[idx][0]
        if messagebox.askyesno('Confirm', 'Delete selected book?'):
            self.store.delete_book(bid)
            self._refresh_books()

    def on_book_select(self, evt):
        sel = self.book_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        b = self.books[idx]
        bid, title, author, year, notes, cover = b
        details = f"Title: {title}\nAuthor: {author}\nYear: {year}\nNotes: {notes}"
        # Show small popup
        messagebox.showinfo('Book details', details)
        # show cover preview
        self._show_cover(cover)

    # Wishlist actions
    def add_wishlist_dialog(self):
        title = simpledialog.askstring('Add to Wishlist', 'Title:')
        if not title:
            return
        notes = simpledialog.askstring('Add to Wishlist', 'Notes (optional):') or ''
        cover_path = filedialog.askopenfilename(title='Select cover image (optional)', filetypes=[('Image files','*.png;*.jpg;*.jpeg;*.gif;*.bmp'),('All files','*.*')])
        wid = self.store.add_wishlist(title.strip(), notes.strip())
        if cover_path and hasattr(self.store, 'set_wishlist_cover'):
            try:
                self.store.set_wishlist_cover(wid, cover_path)
            except Exception:
                pass
        self._refresh_wishlist()

    def remove_selected_wishlist(self):
        sel = self.wish_listbox.curselection()
        if not sel:
            messagebox.showinfo('Info', 'No wishlist item selected')
            return
        idx = sel[0]
        wid = self.wishlist[idx][0]
        if messagebox.askyesno('Confirm', 'Remove selected wishlist item?'):
            self.store.delete_wishlist(wid)
            self._refresh_wishlist()

    def move_selected_wishlist(self):
        sel = self.wish_listbox.curselection()
        if not sel:
            messagebox.showinfo('Info', 'No wishlist item selected')
            return
        idx = sel[0]
        wid = self.wishlist[idx][0]
        author = simpledialog.askstring('Move to Library', 'Author (optional):') or ''
        year = simpledialog.askstring('Move to Library', 'Year (optional):') or ''
        ok = self.store.move_wishlist_to_books(wid, author.strip(), year.strip())
        if ok:
            self._refresh_all()

    def on_wish_select(self, evt):
        sel = self.wish_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        w = self.wishlist[idx]
        wid, title, notes, cover = w
        messagebox.showinfo('Wishlist item', f"Title: {title}\nNotes: {notes}")
        self._show_cover(cover)

    def show_requirements(self):
        txt = (
            'Minimum requirements:\n'
            '- Python 3.8 or newer (3.9+ recommended)\n'
            '- Tk (usually included with Python on Windows/Mac)\n'
            "Optional for standalone builds:\n"
            "- PyInstaller (pip install pyinstaller) to create .exe/.app files\n"
            "Installation scripts included: install.sh (mac/linux) and install.bat (windows).\n"
        )
        messagebox.showinfo('Minimum requirements', txt)

    def _show_cover(self, cover_path, for_wish=False):
        """Display cover image in the corresponding preview label."""
        label = self.wish_cover_label if for_wish else self.cover_label
        if not cover_path:
            label.config(image='', text='No cover')
            if not for_wish:
                self.cover_photo = None
            else:
                self.wish_cover_photo = None
            return

        p = Path(cover_path)
        if not p.exists():
            label.config(image='', text='No cover')
            return

        try:
            if HAS_PIL:
                img = Image.open(str(p))
                # Respect user-configured preview size (pixels)
                pw = CONFIG.get('preview_width', 300)
                ph = CONFIG.get('preview_height', 440)
                img.thumbnail((pw, ph))
                photo = ImageTk.PhotoImage(img)
            else:
                # limited support without PIL (PNG/GIF)
                photo = tk.PhotoImage(file=str(p))
            label.config(image=photo, text='')
            if for_wish:
                self.wish_cover_photo = photo
            else:
                self.cover_photo = photo
        except Exception:
            label.config(image='', text='No cover')
            if for_wish:
                self.wish_cover_photo = None
            else:
                self.cover_photo = None

    # UI actions for cover management and backups
    def change_cover_selected(self):
        sel = self.book_listbox.curselection()
        if not sel:
            messagebox.showinfo('Info', 'No book selected')
            return
        idx = sel[0]
        bid = self.books[idx][0]
        path = filedialog.askopenfilename(title='Select new cover image', filetypes=[('Image files','*.png;*.jpg;*.jpeg;*.gif;*.bmp'),('All files','*.*')])
        if not path:
            return
        try:
            if hasattr(self.store, 'set_book_cover'):
                self.store.set_book_cover(bid, path)
            self._refresh_books()
        except Exception as e:
            messagebox.showerror('Error', f'Could not set cover: {e}')

    def change_wish_cover_selected(self):
        sel = self.wish_listbox.curselection()
        if not sel:
            messagebox.showinfo('Info', 'No wishlist item selected')
            return
        idx = sel[0]
        wid = self.wishlist[idx][0]
        path = filedialog.askopenfilename(title='Select new cover image', filetypes=[('Image files','*.png;*.jpg;*.jpeg;*.gif;*.bmp'),('All files','*.*')])
        if not path:
            return
        try:
            if hasattr(self.store, 'set_wishlist_cover'):
                self.store.set_wishlist_cover(wid, path)
            self._refresh_wishlist()
        except Exception as e:
            messagebox.showerror('Error', f'Could not set cover: {e}')

    def export_covers_dialog(self):
        path = filedialog.asksaveasfilename(title='Export covers to zip', defaultextension='.zip', filetypes=[('Zip files','*.zip')])
        if not path:
            return
        ok = False
        try:
            if hasattr(self.store, 'export_covers'):
                ok = self.store.export_covers(path)
            else:
                # default: zip images dir
                with zipfile.ZipFile(path, 'w') as zf:
                    for p in IMAGES_DIR.glob('*'):
                        zf.write(p, arcname=p.name)
                ok = True
        except Exception as e:
            messagebox.showerror('Error', f'Export failed: {e}')
            return
        if ok:
            messagebox.showinfo('Export', f'Exported covers to {path}')

    def import_covers_dialog(self):
        path = filedialog.askopenfilename(title='Import covers from zip', filetypes=[('Zip files','*.zip')])
        if not path:
            return
        ok = False
        try:
            if hasattr(self.store, 'import_covers'):
                ok = self.store.import_covers(path)
            else:
                with zipfile.ZipFile(path, 'r') as zf:
                    zf.extractall(IMAGES_DIR)
                ok = True
        except Exception as e:
            messagebox.showerror('Error', f'Import failed: {e}')
            return
        if ok:
            messagebox.showinfo('Import', f'Imported covers from {path}')
            self._refresh_all()

    def export_all_dialog(self):
        path = filedialog.asksaveasfilename(title='Export full backup', defaultextension='.zip', filetypes=[('Zip files','*.zip')])
        if not path:
            return
        ok = False
        try:
            if hasattr(self.store, 'export_all'):
                ok = self.store.export_all(path)
            else:
                # CSV store: bundle CSV files and images
                with zipfile.ZipFile(path, 'w') as zf:
                    for f in [Path.home() / '.manga_library_books.csv', Path.home() / '.manga_library_wishlist.csv']:
                        if f.exists():
                            zf.write(f, arcname=f.name)
                    for p in IMAGES_DIR.glob('*'):
                        zf.write(p, arcname=f'images/{p.name}')
                ok = True
        except Exception as e:
            messagebox.showerror('Error', f'Export failed: {e}')
            return
        if ok:
            messagebox.showinfo('Export', f'Exported backup to {path}')

    def import_all_dialog(self):
        path = filedialog.askopenfilename(title='Import full backup', filetypes=[('Zip files','*.zip')])
        if not path:
            return
        ok = False
        try:
            if hasattr(self.store, 'import_all'):
                ok = self.store.import_all(path)
            else:
                with zipfile.ZipFile(path, 'r') as zf:
                    for member in zf.namelist():
                        if member.endswith('.csv'):
                            zf.extract(member, Path.home())
                        elif member.startswith('images/'):
                            zf.extract(member, IMAGES_DIR.parent)
                ok = True
        except Exception as e:
            messagebox.showerror('Error', f'Import failed: {e}')
            return
        if ok:
            messagebox.showinfo('Import', f'Imported backup from {path}')
            self._refresh_all()

    def open_settings_dialog(self):
        global CONFIG
        cfg = CONFIG.copy()
        # ask simple settings
        resize = messagebox.askyesno('Resize images', f"Resize and optimize images on import? Currently {'On' if cfg.get('resize_enabled') else 'Off'}")
        cfg['resize_enabled'] = resize
        try:
            w = simpledialog.askinteger('Max width', 'Max image width (px):', initialvalue=cfg.get('max_width', 800))
            if w:
                cfg['max_width'] = int(w)
            h = simpledialog.askinteger('Max height', 'Max image height (px):', initialvalue=cfg.get('max_height', 1200))
            if h:
                cfg['max_height'] = int(h)
            q = simpledialog.askinteger('Quality', 'JPEG quality (10-95):', initialvalue=cfg.get('quality', 85))
            if q:
                cfg['quality'] = int(q)
            # Preview dimensions for the UI thumbnails
            pw = simpledialog.askinteger('Preview width', 'Cover preview width (px):', initialvalue=cfg.get('preview_width', 300))
            if pw:
                cfg['preview_width'] = int(pw)
            ph = simpledialog.askinteger('Preview height', 'Cover preview height (px):', initialvalue=cfg.get('preview_height', 440))
            if ph:
                cfg['preview_height'] = int(ph)
        except Exception:
            pass
        save_config(cfg)
        CONFIG = load_config()
        # Refresh UI to reflect new preview settings
        try:
            self._refresh_all()
        except Exception:
            pass

    def migrate_dialog(self):
        # choose direction based on current store
        if isinstance(self.store, CSVDataStore):
            if not messagebox.askyesno('Migrate to SQLite', 'This will copy CSV data into a new SQLite database and use SQLite storage. Continue?'):
                return
            # perform migrate CSV -> SQLite
            self._migrate_csv_to_sqlite()
            messagebox.showinfo('Migrate', 'Migration to SQLite complete. Restart the app with --storage sqlite to use the SQLite DB.')
        else:
            if not messagebox.askyesno('Migrate to CSV', 'This will export SQLite data to CSV files and switch to CSV storage. Continue?'):
                return
            self._migrate_sqlite_to_csv()
            messagebox.showinfo('Migrate', 'Migration to CSV complete. Restart the app without --storage to use CSV storage.')

    def _migrate_csv_to_sqlite(self):
        # create sqlite DB and copy data
        db = DataStore()
        # books
        for b in self.store.list_books():
            bid, title, author, year, notes, cover = b
            new_id = db.add_book(title, author, year, notes)
            if cover:
                try:
                    db.set_book_cover(new_id, cover)
                except Exception:
                    pass
        # wishlist
        for w in self.store.list_wishlist():
            wid, title, notes, cover = w
            new_id = db.add_wishlist(title, notes)
            if cover:
                try:
                    db.set_wishlist_cover(new_id, cover)
                except Exception:
                    pass

    def _migrate_sqlite_to_csv(self):
        csvs = CSVDataStore()
        for b in self.store.list_books():
            bid, title, author, year, notes, cover = b
            nid = csvs.add_book(title, author, year, notes)
            if cover:
                try:
                    csvs.set_book_cover(nid, cover)
                except Exception:
                    pass
        for w in self.store.list_wishlist():
            wid, title, notes, cover = w
            nid = csvs.add_wishlist(title, notes)
            if cover:
                try:
                    csvs.set_book_cover(nid, cover)
                except Exception:
                    pass

    def print_list(self, kind='books'):
        # Create a simple text representation and send to system print
        if kind == 'books':
            rows = self.store.list_books()
            heading = 'Library'
        else:
            rows = self.store.list_wishlist()
            heading = 'Wishlist'

        lines = [heading, '=' * 40]
        if kind == 'books':
            for r in rows:
                # r: id,title,author,year,notes,cover
                _, title, author, year, notes, cover = r
                l = title
                if author:
                    l += f' — {author}'
                if year:
                    l += f' ({year})'
                if notes:
                    l += f'\n    {notes}'
                lines.append(l)
        else:
            for r in rows:
                # r: id,title,notes,cover
                _, title, notes, cover = r
                l = title
                if notes:
                    l += f'\n    {notes}'
                lines.append(l)

        txt = '\n\n'.join(lines)
        # Write temporary file
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt') as tf:
            tf.write(txt)
            tempname = tf.name

        # Try platform-specific print
        try:
            sysplt = platform.system()
            if sysplt == 'Darwin':
                subprocess.run(['lp', tempname])
            elif sysplt == 'Windows':
                # notepad /p prints file
                subprocess.run(['notepad', '/p', tempname], check=False)
            else:
                # Linux or other: try lpr
                subprocess.run(['lpr', tempname], check=False)
            messagebox.showinfo('Print', f'Sent {kind} to printer (file: {tempname})')
        except Exception as e:
            messagebox.showerror('Print error', f'Could not print: {e}\nThe list was saved to {tempname}')


def main():
    # choose storage backend: default to CSV for maximum compatibility on systems
    # where users may not have additional components installed.
    storage = 'csv'
    # allow override with env var or command line arg
    if 'MANGA_STORAGE' in os.environ:
        storage = os.environ['MANGA_STORAGE'].lower()
    for i, a in enumerate(sys.argv):
        if a == '--storage' and i + 1 < len(sys.argv):
            storage = sys.argv[i + 1].lower()

    if storage == 'sqlite':
        store = DataStore()
    else:
        store = CSVDataStore()

    app = App(store)
    app.mainloop()


if __name__ == '__main__':
    main()
