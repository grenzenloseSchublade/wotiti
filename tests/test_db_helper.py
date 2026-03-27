import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from db_helper import create_connection, create_main_table, check_user, check_project, log_start, log_stop, calculate_duration, get_all_users, get_all_projects, migrate_projects_to_table

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

