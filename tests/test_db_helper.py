import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from db_helper import create_connection, create_main_table, check_user, log_start, log_stop, calculate_duration

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

