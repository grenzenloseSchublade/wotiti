import pytest
from tkinter import Tk, END
import sys
import os
import time
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from app import App

@pytest.fixture
def app():
    """Fixture to create the application instance for testing."""
    root = Tk()
    app = App(root)
    yield app
    root.destroy()

def test_start_session(app):
    """Test starting a session."""
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.date_entry.delete(0, END)
    app.date_entry.insert(0, "1991-01-01")
    app.start_session()
    assert app.session_active.get(("test_user", 1), True) is True


############################################################


def test_set_today_date(app):
    """Test setting today's date."""
    app.set_today_date()
    assert app.date_entry.get() == datetime.today().strftime('%d-%m-%Y')

def test_clear_console_with_error(app):
    """Test clearing the console when there is an error message."""
    app.console.configure(state='normal')
    app.console.insert(END, "Error message", 'error')
    app.console.configure(state='disabled')
    app.clear_console()
    assert app.console.get("1.0", END).strip() == ""

def test_update_db_content_no_users(app):
    """Test updating the database content listbox with no users."""
    app.db_conn.cursor().execute("DELETE FROM users")
    app.update_db_content()
    assert app.db_content_listbox.size() == 0

def test_update_timer_with_duration(app):
    """Test updating the timer with a specific duration."""
    app.timer_running = False
    app.update_timer(3600)  # 1 hour
    assert "01:00:00" in app.timer_label.cget("text")

def test_start_session_invalid_project(app):
    """Test starting a session with an invalid project ID."""
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "invalid")
    app.date_entry.delete(0, END)
    app.date_entry.insert(0, "1991-01-01")
    app.start_session()
    assert app.session_active.get(("test_user", None)) is None

def test_start_session_no_name(app):
    """Test starting a session without a name."""
    app.name_entry.delete(0, END)
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.date_entry.delete(0, END)
    app.date_entry.insert(0, "1991-01-01")
    app.start_session()
    assert app.session_active.get(("", 1)) is None

def test_start_session_no_date(app):
    """Test starting a session without a date."""
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.date_entry.delete(0, END)
    app.start_session()
    assert app.session_active.get(("test_user", 1)) is None

def test_stop_session_invalid_project(app):
    """Test stopping a session with an invalid project ID."""
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "invalid")
    app.date_entry.delete(0, END)
    app.date_entry.insert(0, "1991-01-01")
    app.stop_session()
    assert app.session_active.get(("test_user", None)) is None

def test_stop_session_no_name(app):
    """Test stopping a session without a name."""
    app.name_entry.delete(0, END)
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.date_entry.delete(0, END)
    app.date_entry.insert(0, "1991-01-01")
    app.stop_session()
    assert app.session_active.get(("", 1)) is None

def test_stop_session_no_date(app):
    """Test stopping a session without a date."""
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.date_entry.delete(0, END)
    app.stop_session()
    assert app.session_active.get(("test_user", 1)) is None

def test_start_session_already_active(app):
    """Test starting a session when one is already active."""
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.date_entry.delete(0, END)
    app.date_entry.insert(0, "1991-01-01")
    app.start_session()
    app.start_session()
    assert "Session already started" in app.console.get("1.0", END)

def test_update_db_content(app):
    """Test updating the database content listbox."""
    app.update_db_content()
    assert app.db_content_listbox.size() > 0

def test_clear_console_with_text(app):
    """Test clearing the console when there is text."""
    app.console.configure(state='normal')
    app.console.insert(END, "Test message")
    app.console.configure(state='disabled')
    app.clear_console()
    assert app.console.get("1.0", END).strip() == ""

def test_clear_console(app):
    """Test clearing the console."""
    app.console.configure(state='normal')
    app.console.insert(END, "Test message")
    app.console.configure(state='disabled')
    app.clear_console()
    assert app.console.get("1.0", END).strip() == ""

def test_get_project(app):
    """Test getting the project ID."""
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    assert app.get_project() == "1"

def test_get_name(app):
    """Test getting the user name."""
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    assert app.get_name() == "test_user"

def test_get_date(app):
    """Test getting the date."""
    app.date_entry.delete(0, END)
    app.date_entry.insert(0, "01.01.1991")
    assert app.get_date() == "01.01.1991"

def test_write_to_console(app):
    """Test writing to the console."""
    test_message = "This is a test message."
    app.write(test_message)
    assert test_message in app.console.get("1.0", END)

def test_start_session_without_db_connection(app):
    """Test starting a session without a database connection."""
    app.db_conn = None
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.start_session()
    assert app.session_active.get(("test_user", 1)) is None

def test_stop_session_without_db_connection(app):
    """Test stopping a session without a database connection."""
    app.db_conn = None
    app.name_entry.delete(0, END)
    app.name_entry.insert(0, "test_user")
    app.project_entry.delete(0, END)
    app.project_entry.insert(0, "1")
    app.stop_session()
    assert app.session_active.get(("test_user", 1)) is None

def test_clear_console_with_no_text(app):
    """Test clearing the console when there is no text."""
    app.clear_console()
    assert app.console.get("1.0", END).strip() == ""
