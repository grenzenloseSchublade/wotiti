import contextlib
import os
import sys
from datetime import datetime
from tkinter import END, Tk

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from app import App
from utils import DATABASE_PATH


@pytest.fixture
def app_instance():
    """Fixture to create the application instance for testing."""
    root = Tk()
    app_instance = App(root)
    yield app_instance
    print(os.path.abspath(os.path.dirname(DATABASE_PATH)))
    with contextlib.suppress(OSError):
        os.remove(DATABASE_PATH)
    root.destroy()


def test_start_session(app_instance):
    """Test starting a session."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.start_session()
    assert app_instance.session_active.get(("test_user", "1"), False) is True


def test_set_today_date(app_instance):
    """Test setting today's date."""
    app_instance.set_today_date()
    assert app_instance.date_entry.get() == datetime.today().strftime("%d-%m-%Y")


def test_clear_console_with_error(app_instance):
    """Test clearing the console when there is an error message."""
    app_instance.console.configure(state="normal")
    app_instance.console.insert(END, "Error message", "error")
    app_instance.console.configure(state="disabled")
    app_instance.clear_console()
    assert app_instance.console.get("1.0", END).strip() == ""


def test_update_db_content_no_users(app_instance):
    """Test updating the database content listbox with no users."""
    app_instance.db_conn.cursor().execute("DELETE FROM users")
    app_instance.update_db_content()
    assert app_instance.db_content_listbox.size() == 0


def test_update_timer_with_duration(app_instance):
    """Test updating the timer with a specific duration."""
    app_instance.timer_running = False
    app_instance.update_timer(3600)  # 1 hour
    assert "01:00:00" in app_instance.timer_label.cget("text")


def test_project_color_stable():
    """project_color liefert stabile Farben aus der Palette."""
    from app import WEEK_PROJECT_COLORS, project_color

    assert project_color("ProjektX") == project_color("ProjektX")
    assert project_color("ProjektX") in WEEK_PROJECT_COLORS
    assert project_color("") in WEEK_PROJECT_COLORS


def test_new_project_sentinel_in_combobox(app_instance):
    """Die Projekt-Combobox enthält den 'Neues Projekt'-Sentinel."""
    from app import NEW_PROJECT_LABEL
    from db_helper import check_project

    check_project(app_instance.db_conn, "Demo")
    app_instance._combobox_dirty = True
    app_instance._refresh_comboboxes(force=True)
    values = list(app_instance.project_entry["values"])
    assert NEW_PROJECT_LABEL in values
    assert "Demo" in values


def test_idle_timeout_config_default(app_instance):
    """Idle-Timeout wird aus der Konfiguration übernommen (Default 120)."""
    assert isinstance(app_instance.idle_timeout_minutes, int)


def test_add_manual_event_rejects_today(app_instance):
    """add_manual_event legt für heute/Zukunft nichts an (früher Abbruch, kein Dialog)."""
    app_instance.name_entry.set("u_today")
    app_instance.project_entry.set("p_today")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    cur = app_instance.db_conn.cursor()
    before = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    app_instance.add_manual_event()
    after = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before


def test_maybe_auto_stop_idle(app_instance, monkeypatch):
    """Eine laufende Session wird bei Überschreiten des Idle-Limits gestoppt."""
    import app as app_module

    app_instance.name_entry.set("idle_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    app_instance.start_session()
    assert app_instance.session_active.get(("idle_user", "1")) is True

    app_instance.idle_timeout_minutes = 120
    # OS meldet 3 h Inaktivität → Auto-Stop.
    monkeypatch.setattr(app_module, "get_idle_seconds", lambda: 3 * 3600)
    app_instance._idle_check_counter = 29  # nächster Aufruf erreicht die 30er-Schwelle
    app_instance._maybe_auto_stop_idle()
    assert app_instance.session_active.get(("idle_user", "1")) is False
    assert app_instance.timer_running is False


def test_get_project_rejects_sentinel(app_instance):
    """Der Sentinel-Eintrag wird nie als echtes Projekt zurückgegeben."""
    from app import NEW_PROJECT_LABEL

    app_instance.project_entry.set(NEW_PROJECT_LABEL)
    assert app_instance._get_project_silent() is None
    assert app_instance.get_project() is None


def test_set_project_syncs_last_valid(app_instance):
    """_set_project hält _last_valid_project synchron und filtert den Sentinel."""
    from app import NEW_PROJECT_LABEL

    app_instance._set_project("Alpha")
    assert app_instance.project_entry.get() == "Alpha"
    assert app_instance._last_valid_project == "Alpha"
    app_instance._set_project(NEW_PROJECT_LABEL)
    assert app_instance.project_entry.get() == "1"
    assert app_instance._last_valid_project == "1"


def test_step_date(app_instance):
    """Der Tag-Stepper verschiebt das Datum um genau einen Tag."""
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "10-06-2025")
    app_instance._step_date(1)
    assert app_instance.date_entry.get() == "11-06-2025"
    app_instance._step_date(-1)
    assert app_instance.date_entry.get() == "10-06-2025"


def test_maybe_auto_stop_idle_unavailable(app_instance, monkeypatch):
    """Ohne verfügbare Idle-Erkennung (None) bleibt die Session laufen."""
    import app as app_module

    app_instance.name_entry.set("idle_user2")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    app_instance.start_session()
    app_instance.idle_timeout_minutes = 120
    monkeypatch.setattr(app_module, "get_idle_seconds", lambda: None)
    app_instance._idle_check_counter = 29
    app_instance._maybe_auto_stop_idle()
    assert app_instance.session_active.get(("idle_user2", "1")) is True


def test_start_session_invalid_project(app_instance):
    """Test starting a session with an invalid project ID."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("invalid")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.start_session()
    # "invalid" is still a valid project string, session should start
    assert app_instance.session_active.get(("test_user", "invalid"), False) is True


def test_start_session_no_name(app_instance):
    """Test starting a session without a name."""
    app_instance.name_entry.set("")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.start_session()
    assert app_instance.session_active.get(("", "1")) is None


def test_start_session_no_date(app_instance):
    """Sessions starten ohne UI-Datum: das Datum wird aus dem realen
    Zeitstempel in der DB-Schicht abgeleitet (siehe Phase 1.3)."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.start_session()
    assert app_instance.session_active.get(("test_user", "1")) is True


def test_stop_session_invalid_project(app_instance):
    """Test stopping a session with an invalid project ID."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("invalid")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.stop_session()
    assert app_instance.session_active.get(("test_user", "invalid")) is None


def test_stop_session_no_name(app_instance):
    """Test stopping a session without a name."""
    app_instance.name_entry.set("")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.stop_session()
    assert app_instance.session_active.get(("", "1")) is None


def test_stop_session_no_date(app_instance):
    """Test stopping a session without a date."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.stop_session()
    assert app_instance.session_active.get(("test_user", "1")) is None


def test_start_session_already_active(app_instance):
    """Test starting a session when one is already active."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.start_session()
    app_instance.start_session()
    assert "Session bereits gestartet" in app_instance.console.get("1.0", END)


def test_update_db_content(app_instance):
    """Test updating the database content listbox."""
    # Erst eine Session starten, damit Events vorhanden sind.
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    today = datetime.today().strftime("%d-%m-%Y")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, today)
    app_instance.start_session()
    app_instance.update_db_content()
    assert app_instance.db_content_listbox.size() > 0


def test_clear_console_with_text(app_instance):
    """Test clearing the console when there is text."""
    app_instance.console.configure(state="normal")
    app_instance.console.insert(END, "Test message")
    app_instance.console.configure(state="disabled")
    app_instance.clear_console()
    assert app_instance.console.get("1.0", END).strip() == ""


def test_clear_console(app_instance):
    """Test clearing the console."""
    app_instance.console.configure(state="normal")
    app_instance.console.insert(END, "Test message")
    app_instance.console.configure(state="disabled")
    app_instance.clear_console()
    assert app_instance.console.get("1.0", END).strip() == ""


def test_get_project(app_instance):
    """Test getting the project ID."""
    app_instance.project_entry.set("1")
    assert app_instance.get_project() == "1"


def test_get_name(app_instance):
    """Test getting the user name."""
    app_instance.name_entry.set("test_user")
    assert app_instance.get_name() == "test_user"


def test_get_date(app_instance):
    """Test getting the date."""
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    assert app_instance.get_date() == "01-01-1991"


def test_get_date_invalid_format(app_instance):
    """Test getting the date with invalid format."""
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01.01.1991")
    assert app_instance.get_date() is None


def test_write_to_console(app_instance):
    """Test writing to the console."""
    test_message = "This is a test message."
    app_instance.write(test_message)
    assert test_message in app_instance.console.get("1.0", END)


def test_start_session_without_db_connection(app_instance):
    """Test starting a session without a database connection."""
    app_instance.db_conn = None
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.start_session()
    assert app_instance.session_active.get(("test_user", "1")) is None


def test_stop_session_without_db_connection(app_instance):
    """Test stopping a session without a database connection."""
    app_instance.db_conn = None
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.stop_session()
    assert app_instance.session_active.get(("test_user", "1")) is None


def test_clear_console_with_no_text(app_instance):
    """Test clearing the console when there is no text."""
    app_instance.clear_console()
    assert app_instance.console.get("1.0", END).strip() == ""
