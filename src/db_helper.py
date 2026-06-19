from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from sqlite3 import Error

import polars as pl

from utils import DATABASE_PATH, PATH_TO_DATA

logger = logging.getLogger(__name__)

# Konstanten für Datumsformate
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
# In der ``events.date``-Spalte verwendete UI-Darstellung (Tag-Reiter, Listbox).
UI_DATE_FORMAT = "%d-%m-%Y"


def derive_date_from_timestamp(timestamp: str | datetime | None) -> str | None:
    """Leitet aus einem Zeitstempel den UI-Datums-String (DD-MM-YYYY) ab.

    Akzeptiert ``datetime``-Objekte sowie Strings im Standardformat
    ``%Y-%m-%d %H:%M:%S``. Liefert ``None`` bei ungültiger Eingabe.
    """
    if timestamp is None:
        return None
    if isinstance(timestamp, datetime):
        return timestamp.strftime(UI_DATE_FORMAT)
    try:
        return datetime.strptime(str(timestamp), TIMESTAMP_FORMAT).strftime(UI_DATE_FORMAT)
    except (ValueError, TypeError):
        return None


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
    sql_create_main_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """
    success = execute_sql(conn, sql_create_main_table)
    if success:
        logger.debug("Main table created successfully.")
        create_events_table(conn)
        create_break_events_table(conn)
        create_projects_table(conn)
    return success


def create_events_table(conn: sqlite3.Connection) -> bool:
    """Create the centralized events table in the SQLite database."""
    sql_create_events_table = """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project TEXT NOT NULL,
            event_type TEXT CHECK(event_type IN ('start', 'stop')),
            timestamp DATETIME NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """
    success = execute_sql(conn, sql_create_events_table)
    if success:
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);")
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);")
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_events_project_user ON events(project, user_id);")
        # Häufiger Filter: Listbox-Tagessicht und Tagesdauer-Berechnung.
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_events_user_date ON events(user_id, date);")
    return success


def create_break_events_table(conn: sqlite3.Connection) -> bool:
    """Create the break events table in the SQLite database."""
    sql_create_break_events_table = """
        CREATE TABLE IF NOT EXISTS break_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project TEXT NOT NULL,
            break_kind TEXT NOT NULL CHECK(break_kind IN ('short', 'long', 'manual')),
            started_at DATETIME NOT NULL,
            ended_at DATETIME,
            duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
            is_auto INTEGER NOT NULL DEFAULT 1 CHECK(is_auto IN (0, 1)),
            source TEXT NOT NULL DEFAULT 'pomodoro_break',
            pomodoro_cycle INTEGER,
            work_interval_minutes INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """
    success = execute_sql(conn, sql_create_break_events_table)
    if success:
        execute_sql(
            conn, "CREATE INDEX IF NOT EXISTS idx_break_events_user_started ON break_events(user_id, started_at);"
        )
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_break_events_project ON break_events(project);")
        execute_sql(conn, "CREATE INDEX IF NOT EXISTS idx_break_events_open ON break_events(user_id, ended_at);")
        # Migrate existing tables that lack the new columns.
        _migrate_break_events_columns(conn)
    return success


def _migrate_break_events_columns(conn: sqlite3.Connection) -> None:
    """Add pomodoro_cycle and work_interval_minutes if missing (existing DBs)."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(break_events)")
        existing = {row[1] for row in cursor.fetchall()}
        if "pomodoro_cycle" not in existing:
            cursor.execute("ALTER TABLE break_events ADD COLUMN pomodoro_cycle INTEGER")
        if "work_interval_minutes" not in existing:
            cursor.execute("ALTER TABLE break_events ADD COLUMN work_interval_minutes INTEGER")
        conn.commit()
        cursor.close()
    except Error as e:
        logger.warning("break_events column migration: %s", e)


def create_projects_table(conn: sqlite3.Connection) -> bool:
    """Create the projects table in the SQLite database."""
    sql_create_projects_table = """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """
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
        # Tabellen, die zwar dem Pattern entsprechen, aber kein Legacy-User-Schema sind.
        non_legacy_tables = {"events", "sqlite_sequence", "break_events"}
        legacy_required_cols = {"project", "event_type", "timestamp", "date"}

        for table_name in tables:
            if table_name in non_legacy_tables:
                continue
            if not pattern.match(table_name):
                continue

            # Defensiv: nur migrieren, wenn die Legacy-Spalten wirklich vorhanden sind.
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            cols = {row[1] for row in cursor.fetchall()}
            if not legacy_required_cols.issubset(cols):
                logger.debug(
                    "Skip Migration für %s: fehlende Spalten %s",
                    table_name,
                    legacy_required_cols - cols,
                )
                continue

            cursor.execute("SELECT 1 FROM migration_log WHERE table_name = ?;", (table_name,))
            if cursor.fetchone() is not None:
                continue

            user_name = table_name[:-7]
            user_id = check_user(conn, user_name)
            if user_id is None:
                continue

            cursor.execute(
                f"""
                INSERT INTO events (user_id, project, event_type, timestamp, date)
                SELECT ?, project, event_type, timestamp, date
                FROM "{table_name}"
            """,
                (user_id,),
            )

            cursor.execute(
                "INSERT INTO migration_log (table_name, migrated_at) VALUES (?, ?);",
                (table_name, datetime.now().strftime(TIMESTAMP_FORMAT)),
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
    name = name.strip()
    if not name:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE name = ?", (name,))
        user = cur.fetchone()

        if user is None:
            cur.execute("INSERT INTO users(name) VALUES(?)", (name,))
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
    name = name.strip()
    if not name:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
        project = cur.fetchone()

        if project is None:
            cur.execute("INSERT INTO projects(name) VALUES(?)", (name,))
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
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM users ORDER BY name")
        return [row[0] for row in cur.fetchall()]
    except Error as e:
        logger.error("Error reading users: %s", e)
        return []
    finally:
        if cur is not None:
            cur.close()


def get_all_projects(conn: sqlite3.Connection | None) -> list[str]:
    """Return list of all project names from the projects table."""
    if not conn:
        return []
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM projects ORDER BY name")
        return [row[0] for row in cur.fetchall()]
    except Error as e:
        logger.error("Error reading projects: %s", e)
        return []
    finally:
        if cur is not None:
            cur.close()


def migrate_projects_to_table(conn: sqlite3.Connection | None) -> bool:
    """Migrate existing project names from events into the projects table."""
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT project FROM events")
        for (name,) in cur.fetchall():
            if name:
                check_project(conn, name)
        return True
    except Error as e:
        logger.error("Error migrating projects: %s", e)
        return False
    finally:
        cur.close()


def log_event(
    conn: sqlite3.Connection | None,
    project: str,
    name: str,
    event_type: str,
    timestamp: datetime | None = None,
    date: str | None = None,
) -> bool:
    """Log an event (start/stop) for a session.

    ``date`` ist optional: wird er nicht (oder inkonsistent) angegeben, wird er
    aus ``timestamp`` (bzw. ``datetime.now()``) abgeleitet. Damit ist die
    ``events.date``-Spalte garantiert konsistent zum Zeitstempel — Single
    Source of Truth ist immer der Zeitstempel.
    """
    if not conn or not name or event_type not in ("start", "stop"):
        logger.error("Missing required parameters for log_event.")
        return False
    project = str(project).strip()
    name = str(name).strip()

    try:
        cursor = conn.cursor()
        user_id = check_user(conn, name)
        if user_id is None:
            return False

        # Ensure project exists in projects table
        check_project(conn, project)

        # Format timestamp (Single Source of Truth)
        ts_obj = timestamp if timestamp else datetime.now()
        timestamp_str = ts_obj.strftime(TIMESTAMP_FORMAT)

        # Datum konsequent aus Zeitstempel ableiten. Vom Aufrufer übergebenes
        # ``date`` wird verworfen, wenn es vom Zeitstempel abweicht.
        derived_date = ts_obj.strftime(UI_DATE_FORMAT)
        provided = str(date).strip() if date else ""
        if provided and provided != derived_date:
            logger.warning(
                "log_event: date '%s' weicht vom Zeitstempel ab — verwende '%s'.",
                provided,
                derived_date,
            )
        final_date = derived_date

        # Insert event
        cursor.execute(
            """
            INSERT INTO events (user_id, project, event_type, timestamp, date)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user_id, project, event_type, timestamp_str, final_date),
        )
        conn.commit()

        logger.info(
            "%s logged: user=%s project=%s date=%s ts=%s",
            event_type.capitalize(),
            name,
            project,
            final_date,
            timestamp_str,
        )
        return True
    except Error as e:
        logger.error("Error logging %s event: %s", event_type, e)
        return False
    finally:
        cursor.close()


def log_start(
    project: str = "1",
    name: str = "Hans",
    timestamp: datetime | None = None,
    date: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Log the start time of a session."""
    return log_event(conn, project, name, "start", timestamp, date)


def log_stop(
    project: str = "1",
    name: str = "Hans",
    timestamp: datetime | None = None,
    date: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Log the stop time of a session."""
    return log_event(conn, project, name, "stop", timestamp, date)


def log_break_start(
    project: str,
    name: str,
    break_kind: str,
    is_auto: bool = True,
    source: str = "pomodoro_break",
    started_at: datetime | None = None,
    pomodoro_cycle: int | None = None,
    work_interval_minutes: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Log the start of a break. Avoids duplicate open breaks for same user/project."""
    if not conn or not project or not name or break_kind not in {"short", "long", "manual"}:
        return False

    cursor = None
    try:
        cursor = conn.cursor()
        user_id = check_user(conn, name)
        if user_id is None:
            return False

        check_project(conn, project)

        cursor.execute(
            """
            SELECT id FROM break_events
            WHERE user_id = ? AND project = ? AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (user_id, project),
        )
        if cursor.fetchone() is not None:
            return True

        start_str = (started_at or datetime.now()).strftime(TIMESTAMP_FORMAT)
        cursor.execute(
            """
            INSERT INTO break_events
                (user_id, project, break_kind, started_at, is_auto, source,
                 pomodoro_cycle, work_interval_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                project,
                break_kind,
                start_str,
                1 if is_auto else 0,
                source,
                pomodoro_cycle,
                work_interval_minutes,
            ),
        )
        conn.commit()
        return True
    except Error as e:
        logger.error("Error logging break start: %s", e)
        return False
    finally:
        if cursor:
            cursor.close()


def log_break_stop(
    project: str,
    name: str,
    ended_at: datetime | None = None,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """Close the latest open break for user/project and store duration."""
    if not conn or not project or not name:
        return False

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return False
        user_id = row[0]

        cursor.execute(
            """
            SELECT id, started_at
            FROM break_events
            WHERE user_id = ? AND project = ? AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (user_id, project),
        )
        open_break = cursor.fetchone()
        if open_break is None:
            return True

        break_id, started_at_str = open_break
        stop_dt = ended_at or datetime.now()
        stop_str = stop_dt.strftime(TIMESTAMP_FORMAT)
        start_dt = datetime.strptime(started_at_str, TIMESTAMP_FORMAT)
        raw_duration = int((stop_dt - start_dt).total_seconds())
        if raw_duration < 0:
            logger.warning(
                "Break #%s: Stop (%s) liegt vor Start (%s) — Dauer auf 0 gesetzt.",
                break_id,
                stop_str,
                started_at_str,
            )
        duration = max(0, raw_duration)

        cursor.execute(
            """
            UPDATE break_events
            SET ended_at = ?, duration_seconds = ?
            WHERE id = ?
            """,
            (stop_str, duration, break_id),
        )
        conn.commit()
        return True
    except Error as e:
        logger.error("Error logging break stop: %s", e)
        return False
    finally:
        if cursor:
            cursor.close()


def get_open_break(project: str, name: str, conn: sqlite3.Connection | None = None) -> dict | None:
    """Return the currently open break for user/project if present."""
    if not conn or not project or not name:
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return None
        user_id = row[0]
        cursor.execute(
            """
            SELECT id, break_kind, started_at, is_auto, source
            FROM break_events
            WHERE user_id = ? AND project = ? AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (user_id, project),
        )
        r = cursor.fetchone()
        if r is None:
            return None
        return {
            "id": r[0],
            "break_kind": r[1],
            "started_at": r[2],
            "is_auto": bool(r[3]),
            "source": r[4],
        }
    except Error as e:
        logger.error("Error reading open break: %s", e)
        return None
    finally:
        if cursor:
            cursor.close()


def close_stale_breaks(conn: sqlite3.Connection | None = None) -> int:
    """Close all open breaks left over from a previous session (e.g. after crash)."""
    if not conn:
        return 0
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, started_at FROM break_events WHERE ended_at IS NULL")
        stale = cursor.fetchall()
        if not stale:
            return 0
        now_str = datetime.now().strftime(TIMESTAMP_FORMAT)
        for break_id, started_at_str in stale:
            try:
                start_dt = datetime.strptime(started_at_str, TIMESTAMP_FORMAT)
                duration = max(0, int((datetime.now() - start_dt).total_seconds()))
            except (ValueError, TypeError):
                duration = 0
            cursor.execute(
                "UPDATE break_events SET ended_at = ?, duration_seconds = ? WHERE id = ?",
                (now_str, duration, break_id),
            )
        conn.commit()
        logger.info("Closed %d stale open break(s) from previous session.", len(stale))
        return len(stale)
    except Error as e:
        logger.warning("Error closing stale breaks: %s", e)
        return 0
    finally:
        if cursor:
            cursor.close()


def calculate_duration(project: str = "1", name: str = "Hans", conn: sqlite3.Connection | None = None) -> float:
    """Calculate the total duration of a session across all days."""
    if not conn or not name:
        logger.debug("Connection and name are required.")
        return 0

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return 0
        user_id = row[0]
        cursor.execute(
            """
            SELECT event_type, timestamp
            FROM events
            WHERE project = ? AND user_id = ?
            ORDER BY timestamp
        """,
            (project, user_id),
        )

        events = cursor.fetchall()
        total_duration = 0
        start_time = None

        for event in events:
            event_type, timestamp_str = event
            timestamp = datetime.strptime(timestamp_str, TIMESTAMP_FORMAT)

            if event_type == "start":
                start_time = timestamp
            elif event_type == "stop" and start_time is not None:
                duration = (timestamp - start_time).total_seconds()
                total_duration += duration
                start_time = None

        return total_duration
    except (Error, ValueError) as e:
        logger.error("Error calculating duration: %s", e)
        return 0
    finally:
        if cursor is not None:
            cursor.close()


def calculate_daily_duration(
    project: str = "1",
    name: str = "Hans",
    date: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> float:
    """Calculate the duration for a single day only.

    Sessions, die Mitternacht überspannen, werden anteilig auf beide Tage
    verteilt — d. h. eine Session 23:50 → 00:30 trägt 10 min zum Vortag
    und 30 min zum Folgetag bei.
    """
    if not conn or not name:
        return 0
    if date is None:
        date = datetime.now().strftime("%d-%m-%Y")

    try:
        target_day = datetime.strptime(date, "%d-%m-%Y").date()
    except ValueError:
        return 0

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return 0
        user_id = row[0]
        # Lade alle Events für (user, project) und paare start/stop. Damit
        # können auch Sessions korrekt verbucht werden, deren Start- bzw.
        # Stop-Event auf einen anderen Tag fällt (Mitternachts-Split).
        cursor.execute(
            """
            SELECT event_type, timestamp
            FROM events
            WHERE project = ? AND user_id = ?
            ORDER BY timestamp
        """,
            (project, user_id),
        )

        events = cursor.fetchall()
        total_seconds = 0.0
        start_time: datetime | None = None
        from datetime import timedelta as _td

        for event_type, timestamp_str in events:
            try:
                ts = datetime.strptime(timestamp_str, TIMESTAMP_FORMAT)
            except ValueError:
                continue
            if event_type == "start":
                start_time = ts
            elif event_type == "stop" and start_time is not None:
                # Anteil dieser Session, der in ``target_day`` fällt.
                day_start = datetime.combine(target_day, datetime.min.time())
                day_end = day_start + _td(days=1)
                chunk_start = max(start_time, day_start)
                chunk_end = min(ts, day_end)
                if chunk_end > chunk_start:
                    total_seconds += (chunk_end - chunk_start).total_seconds()
                start_time = None

        return total_seconds
    except Error as e:
        logger.error("Error calculating daily duration: %s", e)
        return 0
    finally:
        if cursor is not None:
            cursor.close()


def get_last_start_date(conn: sqlite3.Connection | None, name: str, project: str) -> str | None:
    """Return the ``date`` column of the most recent unmatched start event."""
    if not conn or not name or not project:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return None
        user_id = row[0]
        cursor.execute(
            """
            SELECT e.date FROM events e
            WHERE e.user_id = ? AND e.project = ? AND e.event_type = 'start'
              AND NOT EXISTS (
                  SELECT 1 FROM events e2
                  WHERE e2.user_id = e.user_id AND e2.project = e.project
                    AND e2.event_type = 'stop' AND e2.timestamp > e.timestamp
              )
            ORDER BY e.timestamp DESC LIMIT 1
        """,
            (user_id, project),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Error as e:
        logger.error("Error fetching last start date: %s", e)
        return None


def _resolve_user_id(conn, name) -> int | None:
    """Liefert die user_id zum Namen oder ``None`` (mit Fehler-Logging)."""
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Error as e:
        logger.error("Error resolving user id: %s", e)
        return None
    finally:
        if cursor is not None:
            cursor.close()


def _hours_by_project_day(conn, user_id, days, project_filter=None) -> dict[str, dict[str, float]]:
    """Verteilt abgeschlossene Sessions sekundengenau auf ``days`` je Projekt.

    Ein **einziger** Scan über die Events des Nutzers (optional auf ein Projekt
    gefiltert). Start/Stop werden je Projekt gepaart; jede Session wird anteilig
    auf die Ziel-Tage verteilt (Mitternachts-Split), identisch zur Semantik von
    :func:`calculate_daily_duration`.

    Rückgabe: ``{YYYY-MM-DD: {project: seconds}}`` (nur belegte Einträge).
    """
    day_bounds = [
        (
            d.strftime("%Y-%m-%d"),
            datetime.combine(d, datetime.min.time()),
            datetime.combine(d, datetime.min.time()) + timedelta(days=1),
        )
        for d in days
    ]
    out: dict[str, dict[str, float]] = {iso: {} for iso, _, _ in day_bounds}

    cursor = None
    try:
        cursor = conn.cursor()
        if project_filter is not None:
            cursor.execute(
                "SELECT project, event_type, timestamp FROM events WHERE user_id = ? AND project = ? ORDER BY project, timestamp",
                (user_id, project_filter),
            )
        else:
            cursor.execute(
                "SELECT project, event_type, timestamp FROM events WHERE user_id = ? ORDER BY project, timestamp",
                (user_id,),
            )
        rows = cursor.fetchall()
    except Error as e:
        logger.error("Error reading events for week view: %s", e)
        return out
    finally:
        if cursor is not None:
            cursor.close()

    current_project = None
    start_time: datetime | None = None
    for project, event_type, ts_str in rows:
        if project != current_project:
            current_project = project
            start_time = None
        try:
            ts = datetime.strptime(ts_str, TIMESTAMP_FORMAT)
        except ValueError:
            continue
        if event_type == "start":
            start_time = ts
        elif event_type == "stop" and start_time is not None:
            for iso, day_start, day_end in day_bounds:
                chunk_start = max(start_time, day_start)
                chunk_end = min(ts, day_end)
                if chunk_end > chunk_start:
                    secs = (chunk_end - chunk_start).total_seconds()
                    out[iso][project] = out[iso].get(project, 0.0) + secs
            start_time = None
    return out


def compute_last_n_days_hours(
    conn: sqlite3.Connection | None,
    name: str,
    project: str,
    n: int = 7,
    end_date=None,
) -> list[tuple[str, float]]:
    """Berechnet die Arbeitsstunden pro Tag für ``n`` Tage bis ``end_date`` (inkl.).

    Liefert eine Liste der Länge ``n`` mit ``(YYYY-MM-DD, hours)`` — Tage ohne
    Einträge erhalten ``0.0``. Sessions über Mitternacht werden anteilig verbucht.
    Ein einziger DB-Scan (siehe :func:`_hours_by_project_day`).

    ``end_date`` ist ein ``date``-Objekt; Default = heute.
    """
    if not conn or not name or not project or n <= 0:
        return []

    user_id = _resolve_user_id(conn, name)
    last_day = end_date if end_date is not None else datetime.now().date()
    days = [last_day - timedelta(days=off) for off in range(n - 1, -1, -1)]
    if user_id is None:
        return [(d.strftime("%Y-%m-%d"), 0.0) for d in days]

    by_day = _hours_by_project_day(conn, user_id, days, project_filter=project)
    result: list[tuple[str, float]] = []
    for d in days:
        iso = d.strftime("%Y-%m-%d")
        result.append((iso, by_day.get(iso, {}).get(project, 0.0) / 3600.0))
    return result


def compute_last_n_days_hours_by_project(
    conn: sqlite3.Connection | None,
    name: str,
    n: int = 7,
    end_date=None,
) -> list[tuple[str, dict[str, float]]]:
    """Wie :func:`compute_last_n_days_hours`, aber **alle Projekte** des Nutzers.

    Liefert eine Liste der Länge ``n`` mit ``(YYYY-MM-DD, {project: hours})`` —
    nur Projekte mit Stunden > 0 erscheinen im Tages-Dict. Ein einziger DB-Scan.
    """
    if not conn or not name or n <= 0:
        return []

    last_day = end_date if end_date is not None else datetime.now().date()
    days = [last_day - timedelta(days=off) for off in range(n - 1, -1, -1)]
    user_id = _resolve_user_id(conn, name)
    if user_id is None:
        return [(d.strftime("%Y-%m-%d"), {}) for d in days]

    by_day = _hours_by_project_day(conn, user_id, days)
    result: list[tuple[str, dict[str, float]]] = []
    for d in days:
        iso = d.strftime("%Y-%m-%d")
        hours = {proj: secs / 3600.0 for proj, secs in by_day.get(iso, {}).items() if secs > 0}
        result.append((iso, hours))
    return result


def close_stale_sessions(conn: sqlite3.Connection | None) -> int:
    """Close orphaned start events that have no matching stop (from unclean shutdown).

    Returns the number of sessions closed.
    """
    if not conn:
        return 0
    closed = 0
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id, e.user_id, e.project, e.timestamp, e.date
            FROM events e
            WHERE e.event_type = 'start'
              AND NOT EXISTS (
                  SELECT 1 FROM events e2
                  WHERE e2.user_id = e.user_id
                    AND e2.project = e.project
                    AND e2.event_type = 'stop'
                    AND e2.timestamp > e.timestamp
              )
        """)
        orphans = cursor.fetchall()
        for event_id, user_id, project, ts_str, date_str in orphans:
            try:
                ts = datetime.strptime(ts_str, TIMESTAMP_FORMAT)
            except ValueError:
                ts = datetime.now()
            cursor.execute(
                """
                INSERT INTO events (user_id, project, event_type, timestamp, date)
                VALUES (?, ?, 'stop', ?, ?)
            """,
                (user_id, project, ts.strftime(TIMESTAMP_FORMAT), date_str),
            )
            closed += 1
            logger.info("Closed stale session: event #%s (user_id=%s, project=%s)", event_id, user_id, project)
        if closed:
            conn.commit()
    except Error as e:
        logger.error("Error closing stale sessions: %s", e)
    return closed


def calculate_daily_break_duration(
    name: str = "Hans",
    date: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> float:
    """Sum completed break durations for a user on a given day (all projects)."""
    if not conn or not name:
        return 0
    if date is None:
        date = datetime.now().strftime("%d-%m-%Y")
    # break_events.started_at is stored as YYYY-MM-DD HH:MM:SS. Use a half-open
    # range [day 00:00:00, next day 00:00:00) instead of LIKE so the index on
    # (user_id, started_at) is used reliably.
    try:
        from datetime import timedelta as _td

        day = datetime.strptime(date, "%d-%m-%Y").date()
    except ValueError:
        return 0
    lower = datetime.combine(day, datetime.min.time()).strftime(TIMESTAMP_FORMAT)
    upper = datetime.combine(day + _td(days=1), datetime.min.time()).strftime(TIMESTAMP_FORMAT)

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row is None:
            return 0
        user_id = row[0]
        cursor.execute(
            """
            SELECT COALESCE(SUM(duration_seconds), 0)
            FROM break_events
            WHERE user_id = ?
              AND started_at >= ?
              AND started_at < ?
              AND duration_seconds IS NOT NULL
        """,
            (user_id, lower, upper),
        )
        total = cursor.fetchone()[0]
        return float(total)
    except Error as e:
        logger.error("Error calculating daily break duration: %s", e)
        return 0
    finally:
        if cursor is not None:
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


def get_event_by_id(conn: sqlite3.Connection | None, event_id: int) -> dict | None:
    """Return a single event as dict, or None if not found."""
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT e.id, u.name, e.project, e.event_type, e.timestamp, e.date
            FROM events e
            JOIN users u ON u.id = e.user_id
            WHERE e.id = ?
        """,
            (event_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "user": row[1],
            "project": row[2],
            "event_type": row[3],
            "timestamp": row[4],
            "date": row[5],
        }
    except Error as e:
        logger.error("Error fetching event %s: %s", event_id, e)
        return None
    finally:
        cur.close()


def update_event(
    conn: sqlite3.Connection | None,
    event_id: int,
    project: str,
    timestamp: str,
    date: str | None = None,
) -> bool:
    """Update project, timestamp und (abgeleitetes) date eines Events.

    ``date`` wird IMMER aus ``timestamp`` abgeleitet — ein abweichend
    übergebener Wert führt zu einer Warnung und wird ignoriert. Damit kann
    die UI den Zeitstempel ändern, ohne dass die Tag-Zuordnung veraltet.
    """
    if not conn:
        return False
    cur = None
    try:
        # Validate timestamp format and derive date.
        parsed_ts = datetime.strptime(timestamp, TIMESTAMP_FORMAT)
        derived_date = parsed_ts.strftime(UI_DATE_FORMAT)
        if date and str(date).strip() and str(date).strip() != derived_date:
            logger.warning(
                "update_event(%s): date '%s' weicht vom Zeitstempel ab — verwende '%s'.",
                event_id,
                date,
                derived_date,
            )
        final_date = derived_date

        # Verwende eine explizite Transaktion, damit ``check_project`` und
        # das UPDATE atomar sind.
        with conn:
            check_project(conn, project)
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE events SET project = ?, timestamp = ?, date = ?
                WHERE id = ?
            """,
                (project, timestamp, final_date, event_id),
            )
        logger.info(
            "Event %s updated: project=%s, timestamp=%s, date=%s",
            event_id,
            project,
            timestamp,
            final_date,
        )
        return cur.rowcount > 0
    except (Error, ValueError) as e:
        logger.error("Error updating event %s: %s", event_id, e)
        return False
    finally:
        if cur:
            cur.close()


def validate_event_pair(conn: sqlite3.Connection | None, event_id: int) -> tuple[bool, str]:
    """Prüft Plausibilität eines Events ggü. seinem Pendant (start↔stop).

    Liefert ``(ok, message)``. ``ok=False`` bedeutet, dass die zeitliche
    Reihenfolge verletzt ist (Stop vor Start oder Start nach Stop des Paares).
    Findet sich kein passendes Pendant, gilt der Eintrag als zulässig
    (z. B. offene Session ohne Stop).
    """
    if not conn:
        return False, "Keine Datenbankverbindung."
    ev = get_event_by_id(conn, event_id)
    if ev is None:
        return False, "Eintrag nicht gefunden."
    try:
        ts = datetime.strptime(ev["timestamp"], TIMESTAMP_FORMAT)
    except ValueError:
        return False, f"Ungültiger Zeitstempel: {ev['timestamp']}"

    cur = conn.cursor()
    try:
        if ev["event_type"] == "stop":
            # Suche das zuletzt eingefügte Start-Event desselben (User, Projekt)
            # vor diesem Stop. Wir orientieren uns an ``id`` (Insertion Order),
            # damit auch Pairs erkannt werden, deren Reihenfolge durch eine
            # Bearbeitung verkehrt wurde (Stop-vor-Start temporär).
            cur.execute(
                """
                SELECT e.timestamp FROM events e
                JOIN users u ON u.id = e.user_id
                WHERE u.name = ? AND e.project = ? AND e.event_type = 'start'
                  AND e.id < ?
                ORDER BY e.id DESC LIMIT 1
                """,
                (ev["user"], ev["project"], event_id),
            )
            row = cur.fetchone()
            if row is None:
                return True, "Kein zugehöriger Start gefunden — geprüft."
            try:
                start_ts = datetime.strptime(row[0], TIMESTAMP_FORMAT)
            except ValueError:
                return True, ""
            if ts < start_ts:
                return False, f"Stop ({ts}) liegt vor zugehörigem Start ({start_ts})."
            return True, ""
        else:  # start
            # Nachfolgender Stop desselben (User, Projekt) per Insertion Order.
            cur.execute(
                """
                SELECT e.timestamp FROM events e
                JOIN users u ON u.id = e.user_id
                WHERE u.name = ? AND e.project = ? AND e.event_type = 'stop'
                  AND e.id > ?
                ORDER BY e.id ASC LIMIT 1
                """,
                (ev["user"], ev["project"], event_id),
            )
            row = cur.fetchone()
            if row is None:
                return True, "Kein zugehöriger Stop gefunden — offene Session."
            try:
                stop_ts = datetime.strptime(row[0], TIMESTAMP_FORMAT)
            except ValueError:
                return True, ""
            if ts > stop_ts:
                return False, f"Start ({ts}) liegt nach zugehörigem Stop ({stop_ts})."
            return True, ""
    finally:
        cur.close()


def migrate_repair_dates(conn: sqlite3.Connection | None) -> int:
    """Repariert ``events.date``-Werte, die vom Zeitstempel abweichen.

    Wird einmalig pro Datenbank ausgeführt (Marker in ``migration_log``).
    Gibt die Anzahl reparierter Zeilen zurück.
    """
    if not conn:
        return 0
    marker = "repair_dates_v1"
    try:
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS migration_log (
                table_name TEXT PRIMARY KEY,
                migrated_at DATETIME NOT NULL
            )"""
        )
        cur.execute("SELECT 1 FROM migration_log WHERE table_name = ?", (marker,))
        if cur.fetchone() is not None:
            return 0
        # In der DB ist ``timestamp`` als ``YYYY-MM-DD HH:MM:SS`` gespeichert,
        # ``date`` als ``DD-MM-YYYY``. Berechne erwarteten Wert per substr().
        derived_expr = "substr(timestamp,9,2) || '-' || substr(timestamp,6,2) || '-' || substr(timestamp,1,4)"
        with conn:
            cur.execute(f"UPDATE events SET date = {derived_expr} WHERE date IS NULL OR date != {derived_expr}")
            repaired = cur.rowcount
            cur.execute(
                "INSERT INTO migration_log (table_name, migrated_at) VALUES (?, ?)",
                (marker, datetime.now().strftime(TIMESTAMP_FORMAT)),
            )
        if repaired:
            logger.info("migrate_repair_dates: %d Zeilen repariert.", repaired)
        return repaired
    except Error as e:
        logger.error("migrate_repair_dates fehlgeschlagen: %s", e)
        return 0


def delete_event(conn: sqlite3.Connection | None, event_id: int) -> bool:
    """Delete a single event by ID."""
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        logger.info("Event %s deleted.", event_id)
        return cur.rowcount > 0
    except Error as e:
        logger.error("Error deleting event %s: %s", event_id, e)
        return False
    finally:
        cur.close()
