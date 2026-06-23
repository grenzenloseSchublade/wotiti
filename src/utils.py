from __future__ import annotations

import contextlib
import glob
import json
import logging
import os
import sqlite3
import sys
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from tkinter import Tk, filedialog

import polars as pl

logger = logging.getLogger(__name__)

APP_VERSION = "2.0.1"
APP_AUTHOR = "grenzenloseSchublade"
APP_LICENSE = "MIT"

# Color schemes
MODERN_COLORS = {
    "background": "#282a36",
    "text": "#f8f8f2",
    "primary": "#6272a4",
    "secondary": "#44475a",
    "accent": "#8be9fd",
}
SYNTHWAVE_COLORS = {
    "background": "#1a1a2e",
    "text": "#e0e0e0",
    "primary": "#e94560",
    "secondary": "#16213e",
    "accent": "#00d4ff",
}

MODERN_SEQUENCE = ["#8be9fd", "#ff79c6", "#f1fa8c", "#50fa7b", "#ffb86c", "#bd93f9", "#ff5555", "#6272a4"]
SYNTHWAVE_SEQUENCE = ["#00d4ff", "#ff00ff", "#ffff00", "#e94560", "#50fa7b", "#bd93f9", "#ff5555", "#ff79c6"]

THEMES = {
    "Modern": {"colors": MODERN_COLORS, "sequence": MODERN_SEQUENCE},
    "Synthwave": {"colors": SYNTHWAVE_COLORS, "sequence": SYNTHWAVE_SEQUENCE},
}


def get_theme_colors(theme_name: str | None = None) -> tuple[dict[str, str], list[str]]:
    """Gibt das Farbschema für ein Theme zurück. Fällt auf Modern zurück."""
    if theme_name is None:
        theme_name = load_config().get("theme", "Modern")
    theme = THEMES.get(theme_name, THEMES["Modern"])
    return theme["colors"], theme["sequence"]


# Pfade
if getattr(sys, "frozen", False):
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
    "single_instance": True,
    # Automatischer Stopp einer laufenden Session nach so vielen Minuten
    # systemweiter Inaktivität (Maus/Tastatur). 0 deaktiviert die Funktion.
    "idle_timeout_minutes": 120,
    # Wochenend-/Feiertags-Filter für Durchschnitts- und Trend-Statistiken.
    # Summen und Pies bleiben unangetastet.
    "holiday_country": "DE",
    "holiday_subdiv": "NW",
    "exclude_weekends_in_averages": True,
    "include_holidays_in_exclusion": True,
    "count_weekend_work": False,
    # Start/Stop-Liste: False = nach Projekt gruppiert (Default), True = chronologisch.
    "entry_list_chronological": False,
    # Stabile, laufübergreifende Projekt→Farbe-Zuordnung für die Wochenansicht
    # ({Projektname: "#RRGGBB"}). Verhindert, dass Farben je nach Wochen-
    # zusammensetzung springen.
    "project_colors": {},
}


# ---------------------------------------------------------------------------
# Wochenend-/Feiertags-Helper (für Stats-Filterung)
# ---------------------------------------------------------------------------

_HOLIDAYS_IMPORT_WARNED = False


def _try_import_holidays():
    """Liefert das ``holidays``-Modul oder ``None`` (mit Warnung einmalig)."""
    global _HOLIDAYS_IMPORT_WARNED
    try:
        import holidays as _holidays_mod  # noqa: PLC0415

        return _holidays_mod
    except ImportError:
        if not _HOLIDAYS_IMPORT_WARNED:
            logger.warning("Optionales Paket 'holidays' nicht verfügbar — Feiertags-Filter wird ignoriert.")
            _HOLIDAYS_IMPORT_WARNED = True
        return None


def is_weekend(d) -> bool:
    """True, wenn ``d`` Samstag oder Sonntag ist. ``d`` ist ``date``/``datetime``."""
    try:
        return d.weekday() >= 5
    except AttributeError:
        return False


def _holiday_set_for_year(country: str, subdiv: str | None, year: int):
    """Gecachte Holiday-Lookup-Map für (country, subdiv, year). Leer bei Fehler."""
    return _holiday_set_cached(country or "DE", (subdiv or None), int(year))


@lru_cache(maxsize=128)
def _holiday_set_cached(country: str, subdiv: str | None, year: int) -> frozenset:
    mod = _try_import_holidays()
    if mod is None:
        return frozenset()
    try:
        kwargs: dict = {"years": [year]}
        if subdiv:
            kwargs["subdiv"] = subdiv
        h = mod.country_holidays(country, **kwargs)
        return frozenset(h.keys())
    except (KeyError, NotImplementedError, Exception) as e:  # noqa: BLE001
        logger.warning("Feiertags-Lookup für %s/%s/%s fehlgeschlagen: %s", country, subdiv, year, e)
        return frozenset()


def is_holiday(d, country: str = "DE", subdiv: str | None = None) -> bool:
    """True, wenn ``d`` ein Feiertag in ``country``/``subdiv`` ist."""
    # Normalisiere datetime -> date (holidays-Lib liefert date-Keys).
    target = d.date() if hasattr(d, "date") and callable(d.date) else d
    year = getattr(target, "year", None)
    if year is None:
        return False
    holiday_dates = _holiday_set_cached(country or "DE", (subdiv or None), int(year))
    return target in holiday_dates


def is_non_workday(d, *, country: str = "DE", subdiv: str | None = None, include_holidays: bool = True) -> bool:
    """True, wenn ``d`` Wochenende oder (optional) Feiertag ist."""
    return is_weekend(d) or (include_holidays and is_holiday(d, country=country, subdiv=subdiv))


def _validate_config(cfg: dict) -> dict:
    """Validiert geladene Konfiguration und ersetzt ungültige Werte durch Defaults.

    Phase 4.6: Schützt vor Tippfehlern in ``config.json`` und vor
    Typ-Drift (z. B. Strings statt Integern bei Pomodoro-Werten).
    """
    out = dict(cfg)
    int_fields = {
        "dashboard_port": (1024, 65535, 8052),
        "pomodoro_work_minutes": (1, 240, 25),
        "pomodoro_break_minutes": (1, 60, 5),
        "pomodoro_long_break_minutes": (1, 240, 15),
        "pomodoro_long_break_every": (2, 12, 4),
    }
    for key, (lo, hi, default) in int_fields.items():
        try:
            v = int(out.get(key, default))
            if not (lo <= v <= hi):
                raise ValueError
            out[key] = v
        except (TypeError, ValueError):
            logger.warning("Config: '%s' ungültig (%r) — verwende Default %s.", key, out.get(key), default)
            out[key] = default
    bool_fields = ["pomodoro_enabled", "pomodoro_auto_break", "pomodoro_sound_enabled", "single_instance"]
    for key in bool_fields:
        if not isinstance(out.get(key), bool):
            out[key] = bool(DEFAULT_CONFIG[key])
    if out.get("theme") not in THEMES:
        out["theme"] = "Modern"
    for key in ("default_user", "default_project", "pomodoro_sound_local_path"):
        if not isinstance(out.get(key), str) or not out[key].strip():
            out[key] = DEFAULT_CONFIG[key]
    # Feiertags-/Wochenend-Felder.
    for key in ("holiday_country", "holiday_subdiv"):
        v = out.get(key, DEFAULT_CONFIG[key])
        out[key] = str(v).strip() if isinstance(v, str) else DEFAULT_CONFIG[key]
    for key in (
        "exclude_weekends_in_averages",
        "include_holidays_in_exclusion",
        "count_weekend_work",
        "entry_list_chronological",
    ):
        if not isinstance(out.get(key), bool):
            out[key] = bool(DEFAULT_CONFIG[key])
    return out


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
            return _validate_config(cfg)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("config.json konnte nicht gelesen werden (%s) — Defaults.", e)
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Speichert die Konfiguration in config.json (atomar via tmp + rename)."""
    os.makedirs(PATH_TO_DATA, exist_ok=True)
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        f.flush()
        with contextlib.suppress(OSError):
            os.fsync(f.fileno())
    os.replace(tmp_path, CONFIG_PATH)


def clamp_note(text: str, max_words: int = 20) -> str:
    """Normalisiert eine Notiz: einzeilig, Whitespace kollabiert, max. ``max_words`` Wörter."""
    if not text:
        return ""
    words = text.split()
    if len(words) > max_words:
        words = words[:max_words]
    return " ".join(words)


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
        "%Y-%m-%d %H:%M:%S",  # Standardformat
        "%d-%m-%Y %H:%M:%S",  # Altes Format
        "%Y/%m/%d %H:%M:%S",  # Alternative Schreibweise
        "%d/%m/%Y %H:%M:%S",  # Alternative Schreibweise
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


def read_database(
    db_path: str,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    user: str | None = None,
) -> pl.DataFrame:
    """Liest die Datenbank (events-Schema) und konvertiert Timestamps.

    Optionale Filter (Phase 3.5) reduzieren die übertragene Datenmenge bereits
    in SQL — wichtig bei großen Datenbanken, da das Stats-Dashboard sonst
    bei jedem Refresh die gesamte Tabelle materialisiert. ``from_date`` und
    ``to_date`` werden gegen ``events.timestamp`` geprüft (ISO-Präfix); der
    User-Filter ist eine exakte Namens-Übereinstimmung.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
            if cursor.fetchone() is None:
                return pl.DataFrame()

            base_query = """
                SELECT u.name AS user, e.project, e.event_type, e.timestamp, e.date
                FROM events e
                JOIN users u ON u.id = e.user_id
            """
            clauses: list[str] = []
            params: list = []
            if from_date is not None:
                clauses.append("e.timestamp >= ?")
                params.append(from_date.strftime("%Y-%m-%d %H:%M:%S"))
            if to_date is not None:
                clauses.append("e.timestamp <= ?")
                params.append(to_date.strftime("%Y-%m-%d %H:%M:%S"))
            if user:
                clauses.append("u.name = ?")
                params.append(user)
            if clauses:
                base_query += " WHERE " + " AND ".join(clauses)
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            combined_data = pl.DataFrame(rows, schema=columns, orient="row")
            if combined_data.is_empty():
                return combined_data

            # Vektorisierte Timestamp-Konvertierung
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
            ]
            parsed_ts = pl.coalesce(
                [pl.col("timestamp").cast(pl.Utf8).str.strptime(pl.Datetime, fmt, strict=False) for fmt in formats]
            )
            combined_data = combined_data.with_columns(parsed_ts.alias("timestamp"))

            # Füge das Datum als separate Spalte hinzu (YYYY-MM-DD Format)
            combined_data = combined_data.with_columns(pl.col("timestamp").dt.strftime("%Y-%m-%d").alias("date"))

            return combined_data

    except sqlite3.Error as e:
        logger.error("Fehler beim Lesen der Datenbank: %s", e)
        return pl.DataFrame()


def read_break_events(db_path: str) -> pl.DataFrame:
    """Liest die ``break_events``-Tabelle (Pausen/Pomodoro) als DataFrame.

    Spalten: user, project, break_kind, started_at (Datetime), ended_at,
    duration_seconds, is_auto, pomodoro_cycle. Leere/fehlende Tabelle → leerer
    DataFrame. ``started_at`` wird in ein Datetime + ``date`` (YYYY-MM-DD) konvertiert.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='break_events';")
            if cursor.fetchone() is None:
                return pl.DataFrame()
            cursor.execute(
                """
                SELECT u.name AS user, b.project, b.break_kind, b.started_at, b.ended_at,
                       b.duration_seconds, b.is_auto, b.pomodoro_cycle
                FROM break_events b
                JOIN users u ON u.id = b.user_id
                """
            )
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = pl.DataFrame(rows, schema=columns, orient="row")
            if data.is_empty():
                return data
            started = pl.col("started_at").cast(pl.Utf8).str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False)
            data = data.with_columns(started.alias("started_at"))
            data = data.with_columns(pl.col("started_at").dt.strftime("%Y-%m-%d").alias("date"))
            return data
    except sqlite3.Error as e:
        logger.error("Fehler beim Lesen der break_events: %s", e)
        return pl.DataFrame()


def read_parameters(file_path: str) -> dict:
    """Reads parameters from a JSON file."""
    try:
        with open(file_path, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Parameter-Datei konnte nicht gelesen werden: %s", e)
        return {}


def browse_directory(parent=None) -> str:
    """Browses for a directory using a Tkinter dialog.

    Wenn ``parent`` gegeben ist, wird der Dialog *modal* und zuverlässig in den
    Vordergrund gebracht (Topmost-Toggle). Andernfalls wird ein temporärer
    Hidden-Root erstellt.
    """
    if parent is not None:
        try:
            parent.attributes("-topmost", True)
            parent.lift()
            parent.focus_force()
            parent.update_idletasks()
            directory = filedialog.askdirectory(parent=parent, initialdir=PATH_TO_DASHBOARD_DATA)
        finally:
            with contextlib.suppress(Exception):
                parent.attributes("-topmost", False)
        return directory
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()
    root.update_idletasks()
    directory = filedialog.askdirectory(parent=root, initialdir=PATH_TO_DASHBOARD_DATA)
    root.destroy()
    return directory


def get_app_database_path(directory: str = PATH_TO_DATA) -> str | None:
    """Returns the app_database.db path if it exists in the directory."""
    db_path = os.path.join(directory, "app_database.db")
    return db_path if os.path.isfile(db_path) else None


def find_latest_example_dataset(
    directory: str = PATH_TO_DATA, update_progress: Callable | None = None
) -> tuple[str | None, str | None]:
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
