from __future__ import annotations

import glob
import json
import logging
import os
import sqlite3
import sys
from collections.abc import Callable
from datetime import datetime
from tkinter import Tk, filedialog

import polars as pl

logger = logging.getLogger(__name__)

# Color schemes
MODERN_COLORS = {
    'background': '#282a36', 'text': '#f8f8f2', 'primary': '#6272a4',
    'secondary': '#44475a', 'accent': '#8be9fd'
}
SYNTHWAVE_COLORS = {
    'background': '#1a1a2e', 'text': '#e0e0e0', 'primary': '#e94560',
    'secondary': '#16213e', 'accent': '#00d4ff'
}

MODERN_SEQUENCE = [
    '#8be9fd', '#ff79c6', '#f1fa8c', '#50fa7b',
    '#ffb86c', '#bd93f9', '#ff5555', '#6272a4'
]
SYNTHWAVE_SEQUENCE = [
    '#00d4ff', '#ff00ff', '#ffff00', '#e94560',
    '#50fa7b', '#bd93f9', '#ff5555', '#ff79c6'
]

THEMES = {
    'Modern': {'colors': MODERN_COLORS, 'sequence': MODERN_SEQUENCE},
    'Synthwave': {'colors': SYNTHWAVE_COLORS, 'sequence': SYNTHWAVE_SEQUENCE},
}


def get_theme_colors(theme_name: str | None = None) -> tuple[dict[str, str], list[str]]:
    """Gibt das Farbschema für ein Theme zurück. Fällt auf Modern zurück."""
    if theme_name is None:
        theme_name = load_config().get("theme", "Modern")
    theme = THEMES.get(theme_name, THEMES["Modern"])
    return theme['colors'], theme['sequence']

# Pfade
if getattr(sys, 'frozen', False):
    # PyInstaller frozen EXE: use the directory containing the executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATH_TO_DATA = os.path.join(BASE_DIR, "data")
PATH_TO_SOUNDS = os.path.join(PATH_TO_DATA, "sounds")
PATH_TO_DASHBOARD_DATA = PATH_TO_DATA
DATABASE_PATH = os.path.join(PATH_TO_DATA, "app_database.db")
GENERATE_DATABASE_PATH = os.path.join(PATH_TO_DATA, "beispieldaten.db")
CONFIG_PATH = os.path.join(PATH_TO_DATA, "config.json")

DEFAULT_CONFIG = {
    "database_path": DATABASE_PATH,
    "default_user": "Hans",
    "default_project": "1",
    "dashboard_port": 8052,
    "theme": "Modern",
    "window_geometry": "",
    "mini_window_position": "",
    "pomodoro_enabled": False,
    "pomodoro_work_minutes": 25,
    "pomodoro_break_minutes": 5,
    "pomodoro_long_break_minutes": 15,
    "pomodoro_long_break_every": 4,
    "pomodoro_auto_break": True,
    "pomodoro_sound_enabled": True,
    "pomodoro_sound_local_path": "sounds/StartupSound.wav",
}


def load_config() -> dict:
    """Lädt die Konfiguration aus config.json oder gibt Defaults zurück."""
    os.makedirs(PATH_TO_DATA, exist_ok=True)
    os.makedirs(PATH_TO_SOUNDS, exist_ok=True)
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            # Fehlende Schlüssel mit Defaults auffüllen
            for key, value in DEFAULT_CONFIG.items():
                cfg.setdefault(key, value)

            return cfg
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Speichert die Konfiguration in config.json (atomar via tmp + rename)."""
    os.makedirs(PATH_TO_DATA, exist_ok=True)
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    os.replace(tmp_path, CONFIG_PATH)



def save_to_csv(data: pl.DataFrame, csv_path: str) -> None:
    """Save the DataFrame to a CSV file."""
    try:
        if isinstance(data, pl.DataFrame):
            data.write_csv(csv_path)
        else:
            logger.error("CSV-Export fehlgeschlagen: Daten sind kein Polars DataFrame.")
            return
        logger.info("Daten gespeichert: %s", csv_path)
    except (OSError, ValueError, TypeError) as e:
        logger.error("CSV-Export fehlgeschlagen: %s", e)

def convert_timestamp_format(timestamp_str: str | None) -> datetime | None:
    """
    Konvertiert verschiedene Timestamp-Formate in datetime-Objekte.
    """
    if timestamp_str is None:
        return None
    for date_format in [
        '%Y-%m-%d %H:%M:%S',  # Standardformat
        '%d-%m-%Y %H:%M:%S',  # Altes Format
        '%Y/%m/%d %H:%M:%S',  # Alternative Schreibweise
        '%d/%m/%Y %H:%M:%S'   # Alternative Schreibweise
    ]:
        try:
            return datetime.strptime(timestamp_str, date_format)
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError) as e:
        logger.warning("Timestamp-Konvertierung fehlgeschlagen: %s — %s", timestamp_str, e)
        return None

def read_database(db_path: str) -> pl.DataFrame:
    """Liest die Datenbank (events-Schema) und konvertiert Timestamps in datetime-Objekte."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
            if cursor.fetchone() is None:
                return pl.DataFrame()

            query = """
                SELECT u.name AS user, e.project, e.event_type, e.timestamp, e.date
                FROM events e
                JOIN users u ON u.id = e.user_id
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            combined_data = pl.DataFrame(rows, schema=columns, orient="row")
            if combined_data.is_empty():
                return combined_data

            # Vektorisierte Timestamp-Konvertierung
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%d-%m-%Y %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S',
            ]
            parsed_ts = pl.coalesce([
                pl.col("timestamp").cast(pl.Utf8).str.strptime(pl.Datetime, fmt, strict=False)
                for fmt in formats
            ])
            combined_data = combined_data.with_columns(parsed_ts.alias("timestamp"))

            # Füge das Datum als separate Spalte hinzu (YYYY-MM-DD Format)
            combined_data = combined_data.with_columns(
                pl.col("timestamp").dt.strftime('%Y-%m-%d').alias("date")
            )

            return combined_data

    except sqlite3.Error as e:
        logger.error("Fehler beim Lesen der Datenbank: %s", e)
        return pl.DataFrame()

def read_parameters(file_path: str) -> dict:
    """Reads parameters from a JSON file."""
    try:
        with open(file_path, encoding='utf-8') as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Parameter-Datei konnte nicht gelesen werden: %s", e)
        return {}

def browse_directory() -> str:
    """Browses for a directory using a Tkinter dialog."""
    root = Tk()
    root.withdraw()
    directory = filedialog.askdirectory(initialdir=PATH_TO_DASHBOARD_DATA)
    root.destroy()
    return directory

def get_app_database_path(directory: str = PATH_TO_DATA) -> str | None:
    """Returns the app_database.db path if it exists in the directory."""
    db_path = os.path.join(directory, "app_database.db")
    return db_path if os.path.isfile(db_path) else None

def find_latest_example_dataset(directory: str = PATH_TO_DATA, update_progress: Callable | None = None) -> tuple[str | None, str | None]:
    """Finds the newest example dataset (beispieldaten.db + parameter*.json) recursively."""
    if update_progress:
        update_progress(20, "Searching for example datasets...")

    db_candidates = glob.glob(os.path.join(directory, "**", "beispieldaten.db"), recursive=True)
    if not db_candidates:
        return None, None

    newest = None
    newest_mtime = -1
    newest_param = None

    for db_path in db_candidates:
        db_dir = os.path.dirname(db_path)
        param_candidates = glob.glob(os.path.join(db_dir, "parameter*.json"))
        if not param_candidates:
            continue
        db_mtime = os.path.getmtime(db_path)
        if db_mtime > newest_mtime:
            newest = db_path
            newest_mtime = db_mtime
            newest_param = max(param_candidates, key=os.path.getmtime)

    return newest, newest_param
