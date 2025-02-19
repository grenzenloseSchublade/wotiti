from datetime import datetime
import os
import sqlite3
from sqlite3 import Error
from utils import DATABASE_PATH, PATH_TO_DATA
import pandas as pd

def create_connection(db_file=DATABASE_PATH):
    """Create a database connection to the SQLite database specified by db_file."""
    print(f"Creating database connection to {db_file}...")

    # Check if the directory exists
    directory = os.path.dirname(db_file)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory '{directory}' created.")

    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Database connection created successfully.")
        return conn
    except Error as e:
        print(f"Error creating database connection: {e}")
        return None  # Ensure None is returned in case of an error
    return conn

def create_main_table(conn):
    """Create the main table in the SQLite database."""
    print("Creating main table in the database...")
    try:
        sql_create_main_table = '''
                                CREATE TABLE IF NOT EXISTS users (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    name TEXT UNIQUE NOT NULL
                                );
                            '''
        cursor = conn.cursor()
        cursor.execute(sql_create_main_table)
        print("Main table created successfully.")
    except Error as e:
        print(f"Error creating main table: {e}")

def create_user_table(conn, name):
    """Create a subtable for a user in the SQLite database."""
    print(f"Creating table for user '{name}' in the database...")
    try:
        sql_create_user_table = f'''
                                CREATE TABLE IF NOT EXISTS {name}_events (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    project TEXT NOT NULL,
                                    event_type TEXT CHECK(event_type IN ('start', 'stop')),
                                    timestamp DATETIME NOT NULL,
                                    date TEXT NOT NULL
                                );
                            '''
        cursor = conn.cursor()
        cursor.execute(sql_create_user_table)
        print(f"Table for user '{name}' created successfully.")
    except Error as e:
        print(f"Error creating table for user '{name}': {e}")

def read_database(db_path=PATH_TO_DATA):
    """Read the SQLite database and return the data as a pandas DataFrame."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all user tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        
        data = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            table_data = pd.DataFrame(rows, columns=columns)
            table_data['user'] = table_name.replace('_events', '')
            data.append(table_data)
        
        conn.close()
        return pd.concat(data, ignore_index=True)
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return pd.DataFrame()

def check_user(conn, name):
    """Insert a new user into the main table if not already exists."""
    print(f"Check user '{name}'...")
    sql_check_user = '''SELECT id FROM users WHERE name = ?'''
    sql_insert_user = '''INSERT INTO users(name) VALUES(?)'''
    try:
        cur = conn.cursor()
        cur.execute(sql_check_user, (name,))
        user = cur.fetchone()
        if user is None:
            cur.execute(sql_insert_user, (name,))
            conn.commit()
            print(f"User '{name}' inserted successfully.")
            return cur.lastrowid
        else:
            print(f"User '{name}' already exists.")
            return user[0]
    except sqlite3.Error as e:
        print(f"Error inserting user '{name}': {e}")
        return None

def log_start(project="1", name="Hans", timestamp=None, date=None, conn=None):
    """Log the start time of a session."""
    if not (name and date):
        print("Name and date are required to log a session.")
        return

    # Ensure the user table exists
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}_events';")
    if not cursor.fetchone():
        create_user_table(conn, name)

    timestamp = timestamp.strftime("%d-%m-%Y %H:%M:%S") if timestamp else datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    cursor.execute(f'''
        INSERT INTO {name}_events (project, event_type, timestamp, date)
        VALUES (?, ?, ?, ?)
    ''', (project, 'start', timestamp, date))
    conn.commit()
    print(f"Start time for project {project} logged for user '{name}' on {date}: {timestamp}")

def log_stop(project="1", name="Hans", timestamp=None, date=None, conn=None):
    """Log the stop time of a session."""
    if not (name and date):
        print("Name and date are required to log a session.")
        return

    timestamp = timestamp.strftime("%d-%m-%Y %H:%M:%S") if timestamp else datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT id FROM {name}_events
        WHERE project = ? AND event_type = 'start' AND date = ?
        ORDER BY timestamp DESC LIMIT 1
    ''', (project, date))
    if not cursor.fetchone():
        print(f"No start entry found for project {project} on {date} for user '{name}'.")
        return

    cursor.execute(f'''
        INSERT INTO {name}_events (project, event_type, timestamp, date)
        VALUES (?, ?, ?, ?)
    ''', (project, 'stop', timestamp, date))
    conn.commit()
    print(f"Stop time for project {project} logged for user '{name}' on {date}: {timestamp}")

def calculate_duration(project="1", name="Hans", conn=None):
    """Calculate the total duration of a session."""
    if not name:
        print("Name is required to calculate session duration.")
        return

    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}_events';")
    if not cursor.fetchone():
        print(f"No table found for user '{name}'.")
        create_user_table(conn, name)

    cursor.execute(f'''
        SELECT event_type, timestamp
        FROM {name}_events
        WHERE project = ?
        ORDER BY timestamp
    ''', (project,))
    
    events = cursor.fetchall()
    total_duration = 0
    start_time = None
    
    for event in events:
        event_type, timestamp_str = event
        timestamp = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S")
        
        if event_type == 'start':
            start_time = timestamp
        elif event_type == 'stop' and start_time is not None:
            stop_time = timestamp
            duration = (stop_time - start_time).total_seconds()
            total_duration += duration
            start_time = None
            
    return total_duration
