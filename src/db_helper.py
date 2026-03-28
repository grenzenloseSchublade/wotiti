from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import datetime
from sqlite3 import Error

import polars as pl

from utils import DATABASE_PATH, PATH_TO_DATA

logger = logging.getLogger(__name__)

# Konstanten für Datumsformate
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

def create_connection(db_file: str = DATABASE_PATH) -> sqlite3.Connection | None:
    """Create a database connection to the SQLite database specified by db_file."""
    try:
        directory = os.path.dirname(db_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.debug("Directory '%s' created.", directory)

        conn = sqlite3.connect(db_file)
        logger.debug("Database connection created successfully.")
        return conn
    except Error as e:
        logger.error("Error creating database connection: %s", e)
        return None

def execute_sql(conn: sqlite3.Connection | None, sql_statement: str, params: tuple | None = None) -> bool:
    """Execute SQL statement with error handling."""
    if conn is None:
        logger.error("No database connection.")
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
        logger.error("Error executing SQL: %s", e)
        return False
    finally:
        cursor.close()

def create_main_table(conn: sqlite3.Connection) -> bool:
    """Create the main table in the SQLite database."""
    sql_create_main_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    '''
    success = execute_sql(conn, sql_create_main_table)
    if success:
        logger.debug("Main table created successfully.")
        create_events_table(conn)
        create_projects_table(conn)
    return success

def create_events_table(conn: sqlite3.Connection) -> bool:
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
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_events_project_user ON events(project, user_id);")
    return success

def create_projects_table(conn: sqlite3.Connection) -> bool:
    """Create the projects table in the SQLite database."""
    sql_create_projects_table = '''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    '''
    return execute_sql(conn, sql_create_projects_table)

def migrate_legacy_user_tables(conn: sqlite3.Connection | None) -> bool:
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

            cursor.execute(f"""
                INSERT INTO events (user_id, project, event_type, timestamp, date)
                SELECT ?, project, event_type, timestamp, date
                FROM "{table_name}"
            """, (user_id,))

            cursor.execute(
                "INSERT INTO migration_log (table_name, migrated_at) VALUES (?, ?);",
                (table_name, datetime.now().strftime(TIMESTAMP_FORMAT))
            )

        conn.commit()
        return True
    except Error as e:
        logger.error("Error migrating legacy tables: %s", e)
        return False
    finally:
        cursor.close()

def check_user(conn: sqlite3.Connection | None, name: str) -> int | None:
    """Insert a new user into the main table if not already exists. Returns user_id."""
    if not name or not conn:
        logger.debug("Invalid user name or connection.")
        return None

    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE name = ?', (name,))
        user = cur.fetchone()

        if user is None:
            cur.execute('INSERT INTO users(name) VALUES(?)', (name,))
            conn.commit()
            user_id = cur.lastrowid
            logger.info("User '%s' created.", name)
            return user_id

        return user[0]
    except Error as e:
        logger.error("Error checking user: %s", e)
        return None
    finally:
        cur.close()

def check_project(conn: sqlite3.Connection | None, name: str) -> int | None:
    """Insert a new project if not already exists. Returns project_id."""
    if not name or not conn:
        logger.debug("Invalid project name or connection.")
        return None

    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM projects WHERE name = ?', (name,))
        project = cur.fetchone()

        if project is None:
            cur.execute('INSERT INTO projects(name) VALUES(?)', (name,))
            conn.commit()
            project_id = cur.lastrowid
            logger.info("Project '%s' created.", name)
            return project_id

        return project[0]
    except Error as e:
        logger.error("Error checking project: %s", e)
        return None
    finally:
        cur.close()

def get_all_users(conn: sqlite3.Connection | None) -> list[str]:
    """Return list of all user names from the database."""
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('SELECT name FROM users ORDER BY name')
        return [row[0] for row in cur.fetchall()]
    except Error:
        return []
    finally:
        cur.close()

def get_all_projects(conn: sqlite3.Connection | None) -> list[str]:
    """Return list of all project names from the projects table."""
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('SELECT name FROM projects ORDER BY name')
        return [row[0] for row in cur.fetchall()]
    except Error:
        return []
    finally:
        cur.close()

def migrate_projects_to_table(conn: sqlite3.Connection | None) -> bool:
    """Migrate existing project names from events into the projects table."""
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute('SELECT DISTINCT project FROM events')
        for (name,) in cur.fetchall():
            if name:
                check_project(conn, name)
        return True
    except Error as e:
        logger.error("Error migrating projects: %s", e)
        return False
    finally:
        cur.close()

def log_event(conn: sqlite3.Connection | None, project: str, name: str, event_type: str, timestamp: datetime | None = None, date: str | None = None) -> bool:
    """Log an event (start/stop) for a session."""
    if not all([conn, name, date, event_type in ['start', 'stop']]):
        logger.error("Missing required parameters for log_event.")
        return False

    try:
        cursor = conn.cursor()
        user_id = check_user(conn, name)
        if user_id is None:
            return False

        # Ensure project exists in projects table
        check_project(conn, project)

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
        logger.error("Error logging %s event: %s", event_type, e)
        return False
    finally:
        cursor.close()

def log_start(project: str = "1", name: str = "Hans", timestamp: datetime | None = None, date: str | None = None, conn: sqlite3.Connection | None = None) -> bool:
    """Log the start time of a session."""
    return log_event(conn, project, name, 'start', timestamp, date)

def log_stop(project: str = "1", name: str = "Hans", timestamp: datetime | None = None, date: str | None = None, conn: sqlite3.Connection | None = None) -> bool:
    """Log the stop time of a session."""
    return log_event(conn, project, name, 'stop', timestamp, date)

def calculate_duration(project: str = "1", name: str = "Hans", conn: sqlite3.Connection | None = None) -> float:
    """Calculate the total duration of a session."""
    if not conn or not name:
        logger.debug("Connection and name are required.")
        return 0

    try:
        cursor = conn.cursor()
        # Look up user_id directly to avoid side effects
        cursor.execute('SELECT id FROM users WHERE name = ?', (name,))
        row = cursor.fetchone()
        if row is None:
            return 0
        user_id = row[0]
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
        logger.error("Error calculating duration: %s", e)
        return 0
    finally:
        cursor.close()

def read_database(db_path: str = PATH_TO_DATA) -> pl.DataFrame:
    """Read the SQLite database and return the data as a pandas DataFrame."""
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
            return pl.DataFrame(rows, schema=columns)
    except sqlite3.Error as e:
        logger.error("Error reading database: %s", e)
        return pl.DataFrame()
