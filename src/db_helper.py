from datetime import datetime
import os
import sqlite3
from sqlite3 import Error
from utils import DATABASE_PATH, PATH_TO_DATA
import pandas as pd

# Konstanten für Datumsformate
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

def create_connection(db_file=DATABASE_PATH):
    """Create a database connection to the SQLite database specified by db_file."""
    try:
        directory = os.path.dirname(db_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory '{directory}' created.")

        conn = sqlite3.connect(db_file)
        print("Database connection created successfully.")
        return conn
    except Error as e:
        print(f"Error creating database connection: {e}")
        return None

def execute_sql(conn, sql_statement, params=None):
    """Execute SQL statement with error handling."""
    if conn is None:
        print("Error: No database connection.")
        return False
    
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql_statement, params)
        else:
            cursor.execute(sql_statement)
        conn.commit()
        return True
    except Error as e:
        print(f"Error executing SQL: {e}")
        return False
    finally:
        cursor.close()

def create_main_table(conn):
    """Create the main table in the SQLite database."""
    sql_create_main_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    '''
    success = execute_sql(conn, sql_create_main_table)
    if success:
        print("Main table created successfully.")
    return success

def create_user_table(conn, name):
    """Create a subtable for a user in the SQLite database."""
    sql_create_user_table = f'''
        CREATE TABLE IF NOT EXISTS {name}_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            event_type TEXT CHECK(event_type IN ('start', 'stop')),
            timestamp DATETIME NOT NULL,
            date TEXT NOT NULL
        );
    '''
    success = execute_sql(conn, sql_create_user_table)
    if success:
        print(f"Table for user '{name}' created successfully.")
    return success

def check_user(conn, name):
    """Insert a new user into the main table if not already exists."""
    if not name or not conn:
        print("Error: Invalid user name or connection.")
        return None

    try:
        cur = conn.cursor()
        # Prüfe ob Benutzer existiert
        cur.execute('SELECT id FROM users WHERE name = ?', (name,))
        user = cur.fetchone()
        
        if user is None:
            # Füge neuen Benutzer hinzu
            cur.execute('INSERT INTO users(name) VALUES(?)', (name,))
            conn.commit()
            user_id = cur.lastrowid
            print(f"User '{name}' inserted successfully.")
            return user_id
        
        print(f"User '{name}' already exists.")
        return user[0]
    except Error as e:
        print(f"Error checking user: {e}")
        return None
    finally:
        cur.close()

def log_event(conn, project, name, event_type, timestamp=None, date=None):
    """Log an event (start/stop) for a session."""
    if not all([conn, name, date, event_type in ['start', 'stop']]):
        print("Error: Missing required parameters.")
        return False

    try:
        cursor = conn.cursor()
        
        # Ensure user table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}_events';")
        if not cursor.fetchone():
            if not create_user_table(conn, name):
                return False

        # Format timestamp
        timestamp_str = timestamp.strftime(TIMESTAMP_FORMAT) if timestamp else datetime.now().strftime(TIMESTAMP_FORMAT)

        # Insert event
        cursor.execute(f'''
            INSERT INTO {name}_events (project, event_type, timestamp, date)
            VALUES (?, ?, ?, ?)
        ''', (project, event_type, timestamp_str, date))
        conn.commit()
        
        print(f"{event_type.capitalize()} time for project {project} logged for user '{name}' on {date}: {timestamp_str}")
        return True
    except Error as e:
        print(f"Error logging {event_type} event: {e}")
        return False
    finally:
        cursor.close()

def log_start(project="1", name="Hans", timestamp=None, date=None, conn=None):
    """Log the start time of a session."""
    return log_event(conn, project, name, 'start', timestamp, date)

def log_stop(project="1", name="Hans", timestamp=None, date=None, conn=None):
    """Log the stop time of a session."""
    if not log_event(conn, project, name, 'stop', timestamp, date):
        return False
        
    return True

def calculate_duration(project="1", name="Hans", conn=None):
    """Calculate the total duration of a session."""
    if not conn or not name:
        print("Error: Connection and name are required.")
        return 0

    try:
        cursor = conn.cursor()
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
            timestamp = datetime.strptime(timestamp_str, TIMESTAMP_FORMAT)
            
            if event_type == 'start':
                start_time = timestamp
            elif event_type == 'stop' and start_time is not None:
                duration = (timestamp - start_time).total_seconds()
                total_duration += duration
                start_time = None
                
        return total_duration
    except Error as e:
        print(f"Error calculating duration: {e}")
        return 0
    finally:
        cursor.close()

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
