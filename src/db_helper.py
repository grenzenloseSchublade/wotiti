from datetime import datetime
import os
import re
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
        create_events_table(conn)
    return success

def create_events_table(conn):
    """Create the centralized events table in the SQLite database."""
    sql_create_events_table = '''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project TEXT NOT NULL,
            event_type TEXT CHECK(event_type IN ('start', 'stop')),
            timestamp DATETIME NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    '''
    success = execute_sql(conn, sql_create_events_table)
    if success:
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);")
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);")
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

def migrate_legacy_user_tables(conn):
    """Migrate legacy {name}_events tables into the centralized events table."""
    if conn is None:
        return False

    if not create_events_table(conn):
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_log (
                table_name TEXT PRIMARY KEY,
                migrated_at DATETIME NOT NULL
            );
        """)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_events';")
        tables = [row[0] for row in cursor.fetchall()]
        pattern = re.compile(r"^[A-Za-z0-9_]+_events$")

        for table_name in tables:
            if table_name in ("events", "sqlite_sequence"):
                continue
            if not pattern.match(table_name):
                continue

            cursor.execute("SELECT 1 FROM migration_log WHERE table_name = ?;", (table_name,))
            if cursor.fetchone() is not None:
                continue

            user_name = table_name[:-7]
            user_id = check_user(conn, user_name)
            if user_id is None:
                continue

            cursor.execute("""
                INSERT INTO events (user_id, project, event_type, timestamp, date)
                SELECT ?, project, event_type, timestamp, date
                FROM "{}"
            """.format(table_name), (user_id,))

            cursor.execute(
                "INSERT INTO migration_log (table_name, migrated_at) VALUES (?, ?);",
                (table_name, datetime.now().strftime(TIMESTAMP_FORMAT))
            )

        conn.commit()
        return True
    except Error as e:
        print(f"Error migrating legacy tables: {e}")
        return False
    finally:
        cursor.close()

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
            create_events_table(conn)
            return user_id
        
        print(f"User '{name}' already exists.")
        create_events_table(conn)
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
        user_id = check_user(conn, name)
        if user_id is None:
            return False
        if not create_events_table(conn):
            return False

        # Format timestamp
        timestamp_str = timestamp.strftime(TIMESTAMP_FORMAT) if timestamp else datetime.now().strftime(TIMESTAMP_FORMAT)

        # Insert event
        cursor.execute('''
            INSERT INTO events (user_id, project, event_type, timestamp, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, project, event_type, timestamp_str, date))
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
        user_id = check_user(conn, name)
        if user_id is None:
            return 0
        cursor.execute('''
            SELECT event_type, timestamp
            FROM events
            WHERE project = ? AND user_id = ?
            ORDER BY timestamp
        ''', (project, user_id))
        
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
            df = pd.read_sql_query(query, conn)
            return df
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return pd.DataFrame()
