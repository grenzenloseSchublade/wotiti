from datetime import datetime
import os 
import sqlite3
from sqlite3 import Error
from config import DATABASE_PATH

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

    return conn

def create_table(conn):
    """Create a table in the SQLite database."""
    print("Creating table in the database...")
    try:
        sql_create_table = '''
                            CREATE TABLE IF NOT EXISTS events (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT,
                                session_id INTEGER NOT NULL,
                                event_type TEXT CHECK(event_type IN ('start', 'stop')),
                                timestamp DATETIME NOT NULL
                            );
                        '''
        cursor = conn.cursor()
        cursor.execute(sql_create_table)
        print("Table created successfully.")
    except Error as e:
        print(f"Error creating table: {e}")

def insert_data(conn, value):
    """Insert a new row into the data table."""
    print("Insert data...")
    sql = '''INSERT INTO data(value) VALUES(?)'''
    try:
        cur = conn.cursor()
        cur.execute(sql, (value,))
        conn.commit()
        print("Data inserted successfully.")
        return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        return None

def log_start(session_id=1, name=None, conn=None):
    """Log the start time of a session."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (name, session_id, event_type, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (name, session_id, 'start', timestamp))
    conn.commit()
    print(f"Start time for session {session_id} logged: {timestamp}")

def log_stop(session_id=1, name=None, conn=None):
    """Log the stop time of a session."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO events (name, session_id, event_type, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (name, session_id, 'stop', timestamp))
    conn.commit()
    print(f"Stop time for session {session_id} logged: {timestamp}")

def calculate_duration(session_id=1, conn=None):
    """Calculate the total duration of a session."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT event_type, timestamp
        FROM events
        WHERE session_id = ?
        ORDER BY timestamp
    ''', (session_id,))
    
    events = cursor.fetchall()
    total_duration = 0
    start_time = None
    
    for event in events:
        event_type, timestamp_str = event
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        
        if event_type == 'start':
            start_time = timestamp
        elif event_type == 'stop' and start_time is not None:
            stop_time = timestamp
            duration = (stop_time - start_time).total_seconds()
            total_duration += duration
            start_time = None
    
    print(f"Total duration for session {session_id}: {total_duration} seconds")
    return total_duration
