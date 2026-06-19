import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from db_helper import (
    calculate_duration,
    check_project,
    check_user,
    create_connection,
    create_main_table,
    delete_event,
    get_all_projects,
    get_all_users,
    get_event_by_id,
    log_start,
    log_stop,
    update_event,
)

TEST_DB_PATH = "tests/test_database.db"


@pytest.fixture
def db_conn():
    """Fixture to create a database connection for testing."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    conn = create_connection(TEST_DB_PATH)
    create_main_table(conn)
    yield conn
    conn.close()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_create_connection(db_conn):
    """Test creating a database connection."""
    assert db_conn is not None


def test_create_main_table(db_conn):
    """Test creating the main table."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    table = cursor.fetchone()
    assert table is not None


def test_events_table_created(db_conn):
    """Test creating the events table."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
    table = cursor.fetchone()
    assert table is not None


def test_check_user(db_conn):
    """Test checking and inserting a user into the main table."""
    user_id = check_user(db_conn, "test_user")
    assert user_id is not None


def test_log_start(db_conn):
    """Test logging the start time of a session."""
    user_id = check_user(db_conn, "test_user")
    log_start(project=1, name="test_user", date="2023-10-01", conn=db_conn)
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM events WHERE event_type='start' AND user_id = ?;", (user_id,))
    event = cursor.fetchone()
    assert event is not None


def test_log_stop(db_conn):
    """Test logging the stop time of a session."""
    user_id = check_user(db_conn, "test_user")
    log_start(project=1, name="test_user", date="2023-10-01", conn=db_conn)
    log_stop(project=1, name="test_user", date="2023-10-01", conn=db_conn)
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM events WHERE event_type='stop' AND user_id = ?;", (user_id,))
    event = cursor.fetchone()
    assert event is not None


def test_log_start_without_user(db_conn):
    """Test logging the start time without creating a user."""
    log_start(project=1, name="non_existent_user", date="2023-10-01", conn=db_conn)
    user_id = check_user(db_conn, "non_existent_user")
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM events WHERE event_type='start' AND user_id = ?;", (user_id,))
    event = cursor.fetchone()
    assert event is not None


def test_check_user_existing(db_conn):
    """Test checking an existing user."""
    check_user(db_conn, "test_user")
    user_id = check_user(db_conn, "test_user")
    assert user_id is not None


def test_calculate_duration(db_conn):
    """Test calculating duration from events."""
    check_user(db_conn, "test_user")
    log_start(project=1, name="test_user", date="2023-10-01", conn=db_conn)
    log_stop(project=1, name="test_user", date="2023-10-01", conn=db_conn)
    duration = calculate_duration(project=1, name="test_user", conn=db_conn)
    assert duration >= 0


def test_get_all_users(db_conn):
    """Test getting all users."""
    check_user(db_conn, "alice")
    check_user(db_conn, "bob")
    users = get_all_users(db_conn)
    assert "alice" in users
    assert "bob" in users


def test_get_all_users_empty(db_conn):
    """Test getting all users when table is empty."""
    users = get_all_users(db_conn)
    assert isinstance(users, list)


def test_get_all_projects(db_conn):
    """Test getting all projects."""
    check_user(db_conn, "test_user")
    log_start(project="proj_a", name="test_user", date="2023-10-01", conn=db_conn)
    log_start(project="proj_b", name="test_user", date="2023-10-01", conn=db_conn)
    projects = get_all_projects(db_conn)
    assert "proj_a" in projects
    assert "proj_b" in projects


def test_check_user_no_spam(db_conn, capsys):
    """Test that check_user does not print 'already exists' for existing users."""
    check_user(db_conn, "test_user")
    # Clear captured output
    capsys.readouterr()
    # Call again — should NOT print "already exists"
    check_user(db_conn, "test_user")
    captured = capsys.readouterr()
    assert "already exists" not in captured.out


def test_projects_table_created(db_conn):
    """Test that the projects table is created by create_main_table."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects';")
    table = cursor.fetchone()
    assert table is not None


def test_check_project(db_conn):
    """Test creating a new project."""
    project_id = check_project(db_conn, "my_project")
    assert project_id is not None


def test_check_project_existing(db_conn):
    """Test that check_project returns same id for existing project."""
    id1 = check_project(db_conn, "my_project")
    id2 = check_project(db_conn, "my_project")
    assert id1 == id2


def test_get_all_projects_from_table(db_conn):
    """Test that get_all_projects reads from the projects table."""
    check_project(db_conn, "alpha")
    check_project(db_conn, "beta")
    projects = get_all_projects(db_conn)
    assert "alpha" in projects
    assert "beta" in projects


def test_migrate_projects_to_table(db_conn):
    """Test migrating existing projects from events to projects table."""
    check_user(db_conn, "test_user")
    log_start(project="proj_x", name="test_user", date="2023-10-01", conn=db_conn)
    log_start(project="proj_y", name="test_user", date="2023-10-01", conn=db_conn)
    # proj_x and proj_y were auto-created by log_event's check_project call
    projects = get_all_projects(db_conn)
    assert "proj_x" in projects
    assert "proj_y" in projects


def test_log_event_creates_project(db_conn):
    """Test that logging an event auto-creates the project in projects table."""
    check_user(db_conn, "test_user")
    log_start(project="auto_project", name="test_user", date="2023-10-01", conn=db_conn)
    projects = get_all_projects(db_conn)
    assert "auto_project" in projects


def test_get_event_by_id(db_conn):
    """Test retrieving a single event by its ID."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="proj1", name="test_user", date="01-01-2025", conn=db_conn)
    # Get the event id
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1")
    event_id = cur.fetchone()[0]
    cur.close()

    ev = get_event_by_id(db_conn, event_id)
    assert ev is not None
    assert ev["project"] == "proj1"
    assert ev["event_type"] == "start"
    assert ev["user"] == "test_user"


def test_get_event_by_id_not_found(db_conn):
    """Test that get_event_by_id returns None for non-existent ID."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    assert get_event_by_id(db_conn, 99999) is None


def test_update_event(db_conn):
    """Test updating an existing event's project, timestamp, and date."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="old_proj", name="test_user", date="01-01-2025", conn=db_conn)
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1")
    event_id = cur.fetchone()[0]
    cur.close()

    result = update_event(db_conn, event_id, "new_proj", "2025-06-15 10:30:00", "15-06-2025")
    assert result is True

    ev = get_event_by_id(db_conn, event_id)
    assert ev["project"] == "new_proj"
    assert ev["timestamp"] == "2025-06-15 10:30:00"
    assert ev["date"] == "15-06-2025"


def test_update_event_invalid_timestamp(db_conn):
    """Test that update_event rejects invalid timestamp format."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="proj1", name="test_user", date="01-01-2025", conn=db_conn)
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1")
    event_id = cur.fetchone()[0]
    cur.close()

    result = update_event(db_conn, event_id, "proj1", "NOT-A-TIMESTAMP", "01-01-2025")
    assert result is False


def test_delete_event(db_conn):
    """Test deleting an event by ID."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="proj1", name="test_user", date="01-01-2025", conn=db_conn)
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1")
    event_id = cur.fetchone()[0]
    cur.close()

    result = delete_event(db_conn, event_id)
    assert result is True
    assert get_event_by_id(db_conn, event_id) is None


def test_delete_event_not_found(db_conn):
    """Test that deleting a non-existent event returns False."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    assert delete_event(db_conn, 99999) is False


# -----------------------------------------------------------------------------
# Bugfix-Regression: Tag-Zuordnung (Phase 1)
# -----------------------------------------------------------------------------


def _seed_user_and_event(db_conn, ts_str, date_str):
    """Hilfsfunktion: legt User+Event direkt per SQL an (umgeht Validierung)."""
    from db_helper import check_user, create_events_table

    create_events_table(db_conn)
    user_id = check_user(db_conn, "u1")
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO events (user_id, project, event_type, timestamp, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, "p1", "start", ts_str, date_str),
    )
    db_conn.commit()
    event_id = cur.lastrowid
    cur.close()
    return event_id


def test_update_event_derives_date_from_timestamp(db_conn):
    """update_event ignoriert ein abweichendes ``date`` und leitet es ab."""
    event_id = _seed_user_and_event(db_conn, "2025-04-29 10:00:00", "29-04-2025")
    # User schickt neuen Zeitstempel auf 30-04-2025, vergisst Datums-Sync.
    ok = update_event(db_conn, event_id, "p1", "2025-04-30 14:00:00", "29-04-2025")
    assert ok is True
    ev = get_event_by_id(db_conn, event_id)
    assert ev["date"] == "30-04-2025"
    assert ev["timestamp"] == "2025-04-30 14:00:00"


def test_update_event_accepts_consistent_date(db_conn):
    event_id = _seed_user_and_event(db_conn, "2025-04-29 10:00:00", "29-04-2025")
    ok = update_event(db_conn, event_id, "p1", "2025-04-30 14:00:00", "30-04-2025")
    assert ok is True
    assert get_event_by_id(db_conn, event_id)["date"] == "30-04-2025"


def test_log_event_derives_date_when_none(db_conn):
    """log_start ohne ``date`` darf trotzdem schreiben."""
    from datetime import datetime as _dt

    from db_helper import create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "u1")
    ts = _dt(2025, 4, 30, 12, 0, 0)
    ok = log_start(project="p1", name="u1", timestamp=ts, conn=db_conn)
    assert ok is True
    cur = db_conn.cursor()
    cur.execute("SELECT timestamp, date FROM events ORDER BY id DESC LIMIT 1")
    ts_str, date_str = cur.fetchone()
    cur.close()
    assert ts_str == "2025-04-30 12:00:00"
    assert date_str == "30-04-2025"


def test_migrate_repair_dates_fixes_drift(db_conn):
    """Migration repariert events.date, das vom Zeitstempel abweicht."""
    from db_helper import create_events_table, migrate_repair_dates

    create_events_table(db_conn)
    check_user(db_conn, "u1")
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO events (user_id, project, event_type, timestamp, date) "
        "VALUES (1, 'p', 'start', '2025-04-30 14:00:00', '29-04-2025')"
    )
    cur.execute(
        "INSERT INTO events (user_id, project, event_type, timestamp, date) "
        "VALUES (1, 'p', 'stop', '2025-04-30 15:00:00', '30-04-2025')"
    )
    db_conn.commit()
    repaired = migrate_repair_dates(db_conn)
    assert repaired == 1
    cur.execute("SELECT timestamp, date FROM events ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    assert rows[0] == ("2025-04-30 14:00:00", "30-04-2025")
    assert rows[1] == ("2025-04-30 15:00:00", "30-04-2025")
    # Zweiter Aufruf darf nicht erneut anlegen / ändern.
    assert migrate_repair_dates(db_conn) == 0


def test_validate_event_pair_detects_negative_duration(db_conn):
    """validate_event_pair erkennt Stop-vor-Start-Paare."""
    from datetime import datetime as _dt

    from db_helper import (
        create_events_table,
        log_start,
        log_stop,
        validate_event_pair,
    )

    create_events_table(db_conn)
    check_user(db_conn, "u1")
    log_start(project="p", name="u1", timestamp=_dt(2025, 4, 30, 14, 0), conn=db_conn)
    log_stop(project="p", name="u1", timestamp=_dt(2025, 4, 30, 13, 0), conn=db_conn)
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM events WHERE event_type = 'stop'")
    stop_id = cur.fetchone()[0]
    cur.close()
    ok, msg = validate_event_pair(db_conn, stop_id)
    assert ok is False
    assert "vor" in msg.lower() or "before" in msg.lower()


def test_calculate_daily_duration_splits_midnight(db_conn):
    """calculate_daily_duration verteilt Sessions über Mitternacht anteilig."""
    from datetime import datetime as _dt

    from db_helper import (
        calculate_daily_duration,
        create_events_table,
        log_start,
        log_stop,
    )

    create_events_table(db_conn)
    check_user(db_conn, "u1")
    # Session 23:50 → 00:30 (40 min: 10 min am Tag A, 30 min am Tag B).
    log_start(project="p", name="u1", timestamp=_dt(2025, 4, 30, 23, 50), conn=db_conn)
    log_stop(project="p", name="u1", timestamp=_dt(2025, 5, 1, 0, 30), conn=db_conn)

    sec_a = calculate_daily_duration(project="p", name="u1", date="30-04-2025", conn=db_conn)
    sec_b = calculate_daily_duration(project="p", name="u1", date="01-05-2025", conn=db_conn)
    # Toleranz für Sekunden-Bruchteile.
    assert abs(sec_a - 600) < 2
    assert abs(sec_b - 1800) < 2


def test_compute_last_n_days_hours_by_project(db_conn):
    """Aggregation liefert pro Tag ein {project: hours}-Dict über alle Projekte."""
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import compute_last_n_days_hours_by_project, log_start, log_stop

    check_user(db_conn, "u1")
    # Tag 02-06-2025: 2 h Projekt A + 1 h Projekt B.
    log_start(project="A", name="u1", timestamp=_dt(2025, 6, 2, 9, 0), conn=db_conn)
    log_stop(project="A", name="u1", timestamp=_dt(2025, 6, 2, 11, 0), conn=db_conn)
    log_start(project="B", name="u1", timestamp=_dt(2025, 6, 2, 13, 0), conn=db_conn)
    log_stop(project="B", name="u1", timestamp=_dt(2025, 6, 2, 14, 0), conn=db_conn)

    days = compute_last_n_days_hours_by_project(db_conn, "u1", n=3, end_date=_date(2025, 6, 3))
    assert len(days) == 3
    by_day = dict(days)
    target = by_day["2025-06-02"]
    assert abs(target["A"] - 2.0) < 0.01
    assert abs(target["B"] - 1.0) < 0.01
    # Tage ohne Einträge sind leere Dicts.
    assert by_day["2025-06-03"] == {}


def test_compute_last_n_days_hours_by_project_midnight_split(db_conn):
    """Mitternachts-Sessions werden je Projekt anteilig auf beide Tage verteilt."""
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import compute_last_n_days_hours_by_project, log_start, log_stop

    check_user(db_conn, "u1")
    # 23:30 -> 00:30 = 30 min Vortag + 30 min Folgetag, Projekt P.
    log_start(project="P", name="u1", timestamp=_dt(2025, 6, 1, 23, 30), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 6, 2, 0, 30), conn=db_conn)
    days = dict(compute_last_n_days_hours_by_project(db_conn, "u1", n=3, end_date=_date(2025, 6, 3)))
    assert abs(days["2025-06-01"]["P"] - 0.5) < 0.02
    assert abs(days["2025-06-02"]["P"] - 0.5) < 0.02


def test_compute_last_n_days_hours_by_project_unknown_user(db_conn):
    """Unbekannter Nutzer → n leere Tages-Dicts, kein Fehler."""
    from datetime import date as _date

    from db_helper import compute_last_n_days_hours_by_project

    days = compute_last_n_days_hours_by_project(db_conn, "nobody", n=2, end_date=_date(2025, 6, 3))
    assert len(days) == 2
    assert all(d == {} for _, d in days)


def test_calculate_daily_break_duration_range(db_conn):
    """Pausendauer wird über den Tag korrekt summiert (Range-Query)."""
    from datetime import datetime as _dt

    from db_helper import calculate_daily_break_duration, log_break_start, log_break_stop

    check_user(db_conn, "u1")
    log_break_start(project="p", name="u1", break_kind="manual", started_at=_dt(2025, 6, 2, 10, 0), conn=db_conn)
    log_break_stop(project="p", name="u1", ended_at=_dt(2025, 6, 2, 10, 15), conn=db_conn)
    total = calculate_daily_break_duration(name="u1", date="02-06-2025", conn=db_conn)
    assert abs(total - 900) < 2
    # Anderer Tag → 0.
    assert calculate_daily_break_duration(name="u1", date="03-06-2025", conn=db_conn) == 0
