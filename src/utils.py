import sqlite3
import json
import os
import glob
from tkinter import Tk, filedialog
import pandas as pd

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
PATH_TO_DATA = "data" 
PATH_TO_DASHBOARD_DATA = "data"
DATABASE_PATH = "data/app_database.db" 
GENERATE_DATABASE_PATH = "data/generate_database.db"



def save_to_csv(data, csv_path):
    """Save the DataFrame to a CSV file."""
    try:
        data.to_csv(csv_path, index=False)
        print(f"Data saved to {csv_path} successfully.")
    except (OSError, ValueError, TypeError) as e:
        print(f"Error saving data to CSV: {e}")


def convert_timestamp_format(timestamp_str):
    """
    Konvertiert verschiedene Timestamp-Formate in datetime-Objekte.
    """
    # Versuche verschiedene Formate
    for date_format in [
        '%Y-%m-%d %H:%M:%S',  # Standardformat
        '%d-%m-%Y %H:%M:%S',  # Altes Format
        '%Y/%m/%d %H:%M:%S',  # Alternative Schreibweise
        '%d/%m/%Y %H:%M:%S'   # Alternative Schreibweise
    ]:
        try:
            return pd.to_datetime(timestamp_str, format=date_format)
        except (ValueError, TypeError):
            continue

    # Wenn kein Format passt, versuche es mit automatischer Erkennung
    try:
        return pd.to_datetime(timestamp_str, dayfirst=True)
    except (ValueError, TypeError) as e:
        print(f"Fehler bei der Konvertierung von {timestamp_str}: {e}")
        return pd.NaT

def read_database(db_path):
    """Liest die Datenbank (events-Schema) und konvertiert Timestamps in datetime-Objekte."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
            if cursor.fetchone() is None:
                return pd.DataFrame()

            query = """
                SELECT u.name AS user, e.project, e.event_type, e.timestamp, e.date
                FROM events e
                JOIN users u ON u.id = e.user_id
            """
            combined_data = pd.read_sql_query(query, conn)
            if combined_data.empty:
                return combined_data

            # Vektorisierte Timestamp-Konvertierung
            combined_data['timestamp'] = pd.to_datetime(
                combined_data['timestamp'],
                errors='coerce',
                infer_datetime_format=True,
                dayfirst=True
            )

            # Füge das Datum als separate Spalte hinzu (YYYY-MM-DD Format)
            combined_data['date'] = combined_data['timestamp'].dt.strftime('%Y-%m-%d')

            return combined_data

    except sqlite3.Error as e:
        print(f"Fehler beim Lesen der Datenbank: {e}")
        return pd.DataFrame()

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

def find_database_and_parameters(directory=PATH_TO_DATA, update_progress=None):
    """Finds the database and parameters files in the given directory."""
    if update_progress:
        update_progress(20, "Searching for database and parameter files...")
    db_path = glob.glob(os.path.join(directory, "generate_database.db"))
    param_path = glob.glob(os.path.join(directory, "parameter_run_*.json"))
    db_path = db_path[0] if db_path else None
    param_path = param_path[0] if param_path else None
    return db_path, param_path
