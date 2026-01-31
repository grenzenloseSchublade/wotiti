import sqlite3
import json
import os
import glob
from datetime import datetime
from tkinter import Tk, filedialog
import polars as pl

# Color schemes
MODERN_COLORS = {
    'background': '#282a36', 'text': '#f8f8f2', 'primary': '#6272a4',
    'secondary': '#44475a', 'accent': '#8be9fd'
}
SYNTHWAVE_COLORS = {
    'background': '#1f1f1f', 'text': '#e0e0e0', 'blue': '#00d4ff',
    'pink': '#ff00ff', 'yellow': '#ffff00'
}

# Pfade
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATH_TO_DATA = os.path.join(BASE_DIR, "data")
PATH_TO_DASHBOARD_DATA = PATH_TO_DATA
DATABASE_PATH = os.path.join(PATH_TO_DATA, "app_database.db")
GENERATE_DATABASE_PATH = os.path.join(PATH_TO_DATA, "generate_database.db")



def save_to_csv(data, csv_path):
    """Save the DataFrame to a CSV file."""
    try:
        if isinstance(data, pl.DataFrame):
            data.write_csv(csv_path)
        else:
            print("Error saving data to CSV: data is not a Polars DataFrame.")
            return
        print(f"Data saved to {csv_path} successfully.")
    except (OSError, ValueError, TypeError) as e:
        print(f"Error saving data to CSV: {e}")


def convert_timestamp_format(timestamp_str):
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
        print(f"Fehler bei der Konvertierung von {timestamp_str}: {e}")
        return None

def read_database(db_path):
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
        print(f"Fehler beim Lesen der Datenbank: {e}")
        return pl.DataFrame()

def read_parameters(file_path):
    """Reads parameters from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading parameters: {e}")
        return {}

def browse_directory():
    """Browses for a directory using a Tkinter dialog."""
    root = Tk()
    root.withdraw()
    directory = filedialog.askdirectory(initialdir=PATH_TO_DASHBOARD_DATA)
    root.destroy()
    return directory

def get_app_database_path(directory=PATH_TO_DATA):
    """Returns the app_database.db path if it exists in the directory."""
    db_path = os.path.join(directory, "app_database.db")
    return db_path if os.path.isfile(db_path) else None

def find_latest_example_dataset(directory=PATH_TO_DATA, update_progress=None):
    """Finds the newest example dataset (generate_database.db + parameter_run_*.json) recursively."""
    if update_progress:
        update_progress(20, "Searching for example datasets...")

    db_candidates = glob.glob(os.path.join(directory, "**", "generate_database.db"), recursive=True)
    if not db_candidates:
        return None, None

    newest = None
    newest_mtime = -1
    newest_param = None

    for db_path in db_candidates:
        db_dir = os.path.dirname(db_path)
        param_candidates = glob.glob(os.path.join(db_dir, "parameter_run_*.json"))
        if not param_candidates:
            continue
        db_mtime = os.path.getmtime(db_path)
        if db_mtime > newest_mtime:
            newest = db_path
            newest_mtime = db_mtime
            newest_param = max(param_candidates, key=os.path.getmtime)

    return newest, newest_param
