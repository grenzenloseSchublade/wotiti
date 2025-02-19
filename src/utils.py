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
PATH_TO_DASHBOARD_DATA = "wotiti/data"
DATABASE_PATH = "data/app_database.db" 
GENERATE_DATABASE_PATH = "data/generate_database.db"



def save_to_csv(data, csv_path):
    """Save the DataFrame to a CSV file."""
    try:
        data.to_csv(csv_path, index=False)
        print(f"Data saved to {csv_path} successfully.")
    except Exception as e:
        print(f"Error saving data to CSV: {e}")


def read_database(db_path):
    """Reads SQLite database, returns data as pandas DataFrame."""
    try:
        with sqlite3.connect(db_path) as conn:
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            tables = [table[0] for table in conn.execute(query).fetchall()]
            data = []
            for table_name in tables:
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                df['user'] = table_name.replace('_events', '')
                data.append(df)
            return pd.concat(data, ignore_index=True)
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return pd.DataFrame()

def read_parameters(file_path):
    """Reads parameters from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
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
