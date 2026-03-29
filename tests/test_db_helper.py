import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
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

