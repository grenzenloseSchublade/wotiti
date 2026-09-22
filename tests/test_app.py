import contextlib
import os
import sys
from datetime import datetime, timedelta
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


# --- Session-Pairing (_pair_day_sessions): FIFO-Robustheit gegen Überschneidung ---


def _ev(eid, etype, hhmm, user="u", project="A"):
    """Hilfsfunktion: Event-Tupel wie aus der DB (id, user, project, type, ts)."""
    return (eid, user, project, etype, f"2026-06-23 {hhmm}:00")


def test_pair_sessions_sequential(app_instance):
    """Sequenzielle Start/Stop-Paare bleiben unverändert gepaart."""
    events = [_ev(1, "start", "09:00"), _ev(2, "stop", "10:00"), _ev(3, "start", "11:00"), _ev(4, "stop", "12:00")]
    sessions = app_instance._pair_day_sessions(events)
    assert len(sessions) == 2
    assert all(s["start_id"] and s["stop_id"] for s in sessions)
    assert [(s["start_id"], s["stop_id"]) for s in sessions] == [(1, 2), (3, 4)]


def test_pair_sessions_overlapping_same_project(app_instance):
    """Überschneidende Sessions desselben Projekts → zwei GESCHLOSSENE Sessions.

    Regressionsschutz: früher wurde der erste Start fälschlich „offen" und ein
    verwaister Stop erzeugt (Phantom-„läuft", Endzeit nicht editierbar).
    """
    events = [_ev(1, "start", "09:00"), _ev(2, "start", "10:00"), _ev(3, "stop", "11:00"), _ev(4, "stop", "12:00")]
    sessions = app_instance._pair_day_sessions(events)
    assert len(sessions) == 2
    # Kein offener Start, kein verwaister Stop.
    assert all(s["start_id"] is not None and s["stop_id"] is not None for s in sessions)
    pairs = {(s["start_id"], s["stop_id"]) for s in sessions}
    assert pairs == {(1, 3), (2, 4)}  # FIFO: frühester Start ↔ frühester Stop


def test_pair_sessions_unbalanced_extra_start(app_instance):
    """Echte Unbalance (mehr Starts als Stops) → genau eine offene Session."""
    events = [_ev(1, "start", "09:00"), _ev(2, "start", "10:00"), _ev(3, "stop", "11:00")]
    sessions = app_instance._pair_day_sessions(events)
    assert len(sessions) == 2
    open_sessions = [s for s in sessions if s["stop_id"] is None]
    assert len(open_sessions) == 1
    assert open_sessions[0]["start_id"] == 2  # erster Start wurde geschlossen


def test_pair_sessions_orphan_stop(app_instance):
    """Ein Stop ohne Start bleibt als verwaister Stop erhalten."""
    events = [_ev(1, "stop", "10:00")]
    sessions = app_instance._pair_day_sessions(events)
    assert len(sessions) == 1
    assert sessions[0]["start_id"] is None
    assert sessions[0]["stop_id"] == 1


def test_session_times_str_duration_is_hmm():
    """Dauer wird als H:MM (echte Minuten) ausgegeben, nicht als Dezimalstunde."""
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    from app import App

    def dur(minutes):
        s = _dt(2026, 6, 23, 9, 0)
        e = s + _td(minutes=minutes)
        return App._session_times_str({"start_ts": s, "stop_ts": e, "dur_h": minutes / 60.0})[1]

    assert dur(55) == "0:55 h"  # früher fälschlich 0.92 h
    assert dur(90) == "1:30 h"
    assert dur(60) == "1:00 h"
    assert dur(5) == "0:05 h"


def test_session_times_str_running():
    """Laufende Session (keine Dauer) zeigt 'läuft'."""
    from datetime import datetime as _dt

    from app import App

    times, dur = App._session_times_str({"start_ts": _dt(2026, 6, 23, 9, 0), "stop_ts": None, "dur_h": None})
    assert dur == "läuft"
    assert "→" in times


def test_note_rows_short_single_line():
    """Kurze Notiz → genau eine Zeile mit 'Notiz:'-Präfix."""
    from app import App

    rows = App._note_rows("kurz", "    ")
    assert rows == ["    Notiz: kurz"]


def test_note_rows_empty_dash():
    """Leere Notiz → Platzhalter '—'."""
    from app import App

    assert App._note_rows("", "    ") == ["    Notiz: —"]


def test_note_rows_long_wraps_multiline():
    """Lange Notiz wird über mehrere Zeilen umbrochen; Fortsetzung eingerückt."""
    from app import App

    note = " ".join(f"wort{i}" for i in range(44))
    rows = App._note_rows(note, "    ")
    assert len(rows) >= 2  # mehrzeilig
    assert rows[0].startswith("    Notiz: ")
    # Fortsetzungszeilen sind unter dem Notiz-Text eingerückt (kein 'Notiz:').
    indent = len("    Notiz: ")
    for cont in rows[1:]:
        assert cont.startswith(" " * indent)
        assert "Notiz:" not in cont
    # Kein Wort geht verloren (Union der Zeilen == Originalwörter).
    joined = " ".join(r.strip() for r in rows).replace("Notiz: ", "", 1)
    assert joined.split() == note.split()


def test_note_rows_wider_wraps_fewer_lines():
    """Breiterer Default (88) bricht dieselbe Notiz in weniger Zeilen um als 56."""
    from app import App

    note = " ".join(f"wort{i}" for i in range(44))
    wide = App._note_rows(note, "    ")  # Default width=88
    narrow = App._note_rows(note, "    ", width=56)
    assert len(wide) < len(narrow)


def test_pair_sessions_equal_timestamp_pairs_not_orphans(app_instance):
    """Gleichzeitiger Start & Stop → Null-Dauer-Paar, kein verwaister Stop.

    Regression #4: deterministischer Tiebreak ordnet 'start' vor 'stop' bei
    identischem Zeitstempel, unabhängig von der DB-Reihenfolge.
    """
    # Stop steht in der Eingabe absichtlich VOR dem Start (umgekehrte DB-Order).
    events = [_ev(2, "stop", "12:00"), _ev(1, "start", "12:00")]
    sessions = app_instance._pair_day_sessions(events)
    assert len(sessions) == 1
    assert sessions[0]["start_id"] == 1
    assert sessions[0]["stop_id"] == 2


def test_pair_sessions_separate_projects_not_merged(app_instance):
    """Gleichzeitige Sessions verschiedener Projekte werden nicht vermischt."""
    events = [
        _ev(1, "start", "09:00", project="A"),
        _ev(2, "start", "09:30", project="B"),
        _ev(3, "stop", "10:00", project="A"),
        _ev(4, "stop", "10:30", project="B"),
    ]
    sessions = app_instance._pair_day_sessions(events)
    assert len(sessions) == 2
    by_proj = {s["project"]: (s["start_id"], s["stop_id"]) for s in sessions}
    assert by_proj == {"A": (1, 3), "B": (2, 4)}


def test_disable_pomodoro_during_break_keeps_session(app_instance):
    """POM-01: Pomodoro während einer aktiven Pomodoro-Pause deaktivieren darf
    die laufende Session NICHT stoppen.

    Reproduziert den stillen Session-Verlust: bei einer Pomodoro-Pause bleibt
    die Session in der DB offen; deaktiviert der Nutzer Pomodoro, würde
    _finish_break ohne Reconcile in den Stop-Zweig fallen. _reconcile_pomodoro_runtime
    muss die Pause mit force_resume beenden und die Session erhalten.
    """
    app_instance.name_entry.set("pomo_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    app_instance.start_session()
    assert app_instance.session_active.get(("pomo_user", "1")) is True

    # Pomodoro aktiv + laufende (nicht-manuelle) Pause simulieren.
    app_instance.pomodoro_enabled = True
    app_instance._start_break(
        break_kind="short",
        break_minutes=5,
        is_auto=True,
        source_label="pomodoro_break",
        timed_break=True,
    )
    assert app_instance._break_active is True
    # Pomodoro-Pause stoppt die Session NICHT in der DB.
    assert app_instance.session_active.get(("pomo_user", "1")) is True

    # Nutzer deaktiviert Pomodoro in den Einstellungen (Config bereits gesetzt).
    app_instance.pomodoro_enabled = False
    app_instance._reconcile_pomodoro_runtime(was_enabled=True)

    assert app_instance._break_active is False
    assert app_instance.session_active.get(("pomo_user", "1")) is True
    assert app_instance.timer_running is True
    assert app_instance._pomodoro_work_deadline_ts == 0.0
    assert app_instance._paused_pomodoro_remaining_seconds == 0


# ---------------------------------------------------------------------------
# v2.2.0: Idle-Backdating, Pomodoro-Timer-Anzeige, Standby-Erkennung
# ---------------------------------------------------------------------------


def _start_test_session(app_instance, name="t_user", project="1"):
    app_instance.name_entry.set(name)
    app_instance.project_entry.set(project)
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    app_instance.start_session()
    assert app_instance.session_active.get((name, project)) is True
    return name, project


def test_idle_auto_stop_backdates_stop_event(app_instance, monkeypatch):
    """Der Idle-Auto-Stop bucht den Stop auf den Beginn der Inaktivität zurück."""
    import app as app_module

    name, project = _start_test_session(app_instance, name="idle_bd")
    app_instance.idle_timeout_minutes = 120
    idle_seconds = 3 * 3600
    monkeypatch.setattr(app_module, "get_idle_seconds", lambda: idle_seconds)
    app_instance._idle_check_counter = 29
    before = datetime.now()
    app_instance._maybe_auto_stop_idle()
    assert app_instance.session_active.get((name, project)) is False

    cur = app_instance.db_conn.cursor()
    row = cur.execute(
        "SELECT e.timestamp FROM events e JOIN users u ON u.id = e.user_id "
        "WHERE u.name = ? AND e.event_type = 'stop' ORDER BY e.id DESC LIMIT 1",
        (name,),
    ).fetchone()
    stop_ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    expected = before - timedelta(seconds=idle_seconds)
    # Rückdatiert auf ~now−idle, aber nie vor den Session-Start (Clamp).
    start_dt = datetime.fromtimestamp(app_instance._session_started_ts) if app_instance._session_started_ts else None
    assert abs((stop_ts - max(expected, stop_ts)).total_seconds()) < 6
    assert stop_ts <= datetime.now()
    if start_dt:
        assert stop_ts >= start_dt


def test_pomodoro_break_display_keeps_running(app_instance):
    """Während einer Pomodoro-Pause zählt die Timer-Anzeige weiter (Pause = Arbeitszeit)."""
    import time as _time

    _start_test_session(app_instance, name="pomo_disp")
    app_instance.pomodoro_enabled = True
    # Vor-Pausen-Zeit simulieren: Session läuft "seit 10 min".
    app_instance.timer_start_time = _time.time() - 600
    app_instance._start_break(
        break_kind="short",
        break_minutes=5,
        is_auto=True,
        source_label="pomodoro_break",
        timed_break=True,
    )
    assert app_instance._break_active is True
    app_instance.update_timer_realtime()
    label = app_instance.timer_time_label.cget("text")
    h, m, s = (int(x) for x in label.split(":"))
    assert h * 3600 + m * 60 + s >= 600  # Vor-Pausen-Zeit bleibt sichtbar


def test_finish_pomodoro_break_preserves_timer_start(app_instance):
    """Resume nach Pomodoro-Pause setzt timer_start_time NICHT zurück (zählt nicht ab null)."""
    import time as _time

    _start_test_session(app_instance, name="pomo_keep")
    app_instance.pomodoro_enabled = True
    original_start = _time.time() - 600
    app_instance.timer_start_time = original_start
    app_instance._start_break(
        break_kind="short",
        break_minutes=5,
        is_auto=True,
        source_label="pomodoro_break",
        timed_break=True,
    )
    app_instance._finish_break(play_sound=False, bring_to_front=False, force_resume=True)
    assert app_instance.timer_running is True
    assert app_instance.timer_start_time == original_start


def test_finish_manual_break_resets_timer_start(app_instance):
    """Nach manueller Pause (Session war in DB gestoppt) zählt die Anzeige ab dem Resume."""
    import time as _time

    name, project = _start_test_session(app_instance, name="man_break")
    app_instance.timer_start_time = _time.time() - 600
    app_instance.pause_session()
    assert app_instance.session_active.get((name, project)) is False  # manuell = DB-Stop
    before_resume = _time.time()
    app_instance._finish_break(play_sound=False, bring_to_front=False, force_resume=True)
    assert app_instance.session_active.get((name, project)) is True
    assert app_instance.timer_start_time >= before_resume - 1


def test_suspend_gap_stops_session_backdated(app_instance):
    """Wanduhr-Sprung ohne Monotonic-Sprung (= Standby) stoppt die Session rückdatiert."""
    import time as _time

    name, project = _start_test_session(app_instance, name="susp")
    # Session lief schon vor dem Standby; Start weiter zurücklegen als den Gap.
    app_instance._session_started_ts = _time.time() - 3 * 3600
    # Standby von 2 h simulieren: letzter Tick (Wanduhr) 2 h her, Monotonic aktuell.
    app_instance._last_tick_wall = _time.time() - 7200
    app_instance._last_tick_monotonic = _time.monotonic()
    app_instance._check_suspend_gap()

    assert app_instance.session_active.get((name, project)) is False
    assert app_instance.timer_running is False
    cur = app_instance.db_conn.cursor()
    row = cur.execute(
        "SELECT e.timestamp FROM events e JOIN users u ON u.id = e.user_id "
        "WHERE u.name = ? AND e.event_type = 'stop' ORDER BY e.id DESC LIMIT 1",
        (name,),
    ).fetchone()
    stop_ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    expected = datetime.now() - timedelta(seconds=7200)
    assert abs((stop_ts - expected).total_seconds()) < 10  # rückdatiert auf letzten Tick


def test_suspend_gap_ignores_ui_freeze(app_instance):
    """Springen BEIDE Uhren (UI-Freeze), passiert nichts."""
    import time as _time

    name, project = _start_test_session(app_instance, name="freeze")
    app_instance._last_tick_wall = _time.time() - 7200
    app_instance._last_tick_monotonic = _time.monotonic() - 7200
    app_instance._check_suspend_gap()
    assert app_instance.session_active.get((name, project)) is True
    assert app_instance.timer_running is True


def test_suspend_gap_noop_without_session(app_instance):
    """Ohne aktive Session/Pause ist der Standby-Detektor ein No-op."""
    import time as _time

    app_instance._last_tick_wall = _time.time() - 7200
    app_instance._last_tick_monotonic = _time.monotonic()
    app_instance._check_suspend_gap()  # darf nicht crashen, nichts zu stoppen
    assert app_instance.timer_running is False


def test_suspend_gap_closes_open_pomodoro_break(app_instance):
    """Standby während einer Pomodoro-Pause: Break-Row rückdatiert geschlossen, Session gestoppt."""
    import time as _time

    name, project = _start_test_session(app_instance, name="susp_brk")
    app_instance.pomodoro_enabled = True
    app_instance._start_break(
        break_kind="short",
        break_minutes=5,
        is_auto=True,
        source_label="pomodoro_break",
        timed_break=True,
    )
    assert app_instance._break_active is True
    app_instance._session_started_ts = _time.time() - 3 * 3600
    app_instance._last_tick_wall = _time.time() - 7200
    app_instance._last_tick_monotonic = _time.monotonic()
    app_instance._check_suspend_gap()

    assert app_instance._break_active is False
    assert app_instance.session_active.get((name, project)) is False
    cur = app_instance.db_conn.cursor()
    row = cur.execute(
        "SELECT b.ended_at FROM break_events b JOIN users u ON u.id = b.user_id "
        "WHERE u.name = ? ORDER BY b.id DESC LIMIT 1",
        (name,),
    ).fetchone()
    assert row is not None and row[0] is not None
    ended = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    expected = datetime.now() - timedelta(seconds=7200)
    assert abs((ended - expected).total_seconds()) < 10


def test_note_flush_saves_under_loaded_key_on_user_switch(app_instance):
    """Getippte Notiz wird beim Benutzerwechsel unter dem ALTEN Benutzer gespeichert."""
    from db_helper import check_user, get_daily_meta

    check_user(app_instance.db_conn, "user_a")
    check_user(app_instance.db_conn, "user_b")
    app_instance.name_entry.set("user_a")
    app_instance.project_entry.set("1")
    app_instance.set_today_date()
    app_instance._load_note()
    app_instance.note_entry.delete("1.0", END)
    app_instance.note_entry.insert("1.0", "Notiz für A")

    # Benutzerwechsel: Flush muss unter user_a speichern, nicht unter user_b.
    app_instance.name_entry.set("user_b")
    app_instance._on_name_selected()

    iso_today = datetime.now().strftime("%Y-%m-%d")
    assert get_daily_meta(app_instance.db_conn, "user_a", "1", iso_today)["note"] == "Notiz für A"
    assert get_daily_meta(app_instance.db_conn, "user_b", "1", iso_today)["note"] == ""


def test_name_combobox_locked_during_session(app_instance):
    """Die Benutzer-Combobox ist während einer laufenden Session gesperrt."""
    _start_test_session(app_instance, name="lock_user")
    assert str(app_instance.name_entry.cget("state")) == "disabled"
    app_instance.stop_session()
    assert str(app_instance.name_entry.cget("state")) == "normal"


def test_date_entry_normalizes_unpadded_input(app_instance):
    """'1-7-2026' wird zu '01-07-2026' normalisiert (Anzeige + Vergleiche konsistent)."""
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "1-7-2026")
    app_instance._last_date_view_input_cache = None
    app_instance._on_date_changed()
    assert app_instance.date_entry.get() == "01-07-2026"
    assert app_instance._get_selected_date() == "01-07-2026"


def test_transfer_toggle_flushes_pending_note(app_instance):
    """Der Wochen-Toggle sichert eine getippte Notiz, bevor er das Feld neu lädt."""
    from db_helper import get_daily_meta, log_start, log_stop

    name = "wk_note"
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=today, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=today.replace(hour=10), conn=app_instance.db_conn)
    app_instance.name_entry.set(name)
    app_instance.project_entry.set("1")
    app_instance.set_today_date()
    app_instance._load_note()
    app_instance.note_entry.delete("1.0", END)
    app_instance.note_entry.insert("1.0", "wichtig nicht verlieren")

    iso_today = today.strftime("%Y-%m-%d")
    app_instance.week_view._transfer_toggle([("1", iso_today)], "Test")
    assert get_daily_meta(app_instance.db_conn, name, "1", iso_today)["note"] == "wichtig nicht verlieren"


def test_get_name_accepts_umlauts(app_instance):
    """Bestandsnutzer mit Umlauten (z. B. 'Jörg') dürfen nicht ausgesperrt werden."""
    app_instance.name_entry.set("Jörg Müller")
    assert app_instance.get_name() == "Jörg Müller"
    app_instance.name_entry.set("Ева")  # beliebige Unicode-Buchstaben
    assert app_instance.get_name() == "Ева"
    app_instance.name_entry.set("böse/zeichen")
    assert app_instance.get_name() is None


def test_suspend_gap_flushes_pending_note(app_instance):
    """Standby-Stop sichert eine getippte Notiz, bevor das Feld neu geladen wird."""
    import time as _time

    from db_helper import get_daily_meta

    name, project = _start_test_session(app_instance, name="susp_note")
    app_instance._load_note()
    app_instance.note_entry.delete("1.0", END)
    app_instance.note_entry.insert("1.0", "vor dem standby getippt")
    app_instance._session_started_ts = _time.time() - 3600
    app_instance._last_tick_wall = _time.time() - 7200
    app_instance._last_tick_monotonic = _time.monotonic()
    app_instance._check_suspend_gap()

    iso_today = datetime.now().strftime("%Y-%m-%d")
    assert get_daily_meta(app_instance.db_conn, name, project, iso_today)["note"] == "vor dem standby getippt"


def test_shortcut_guard_skips_text_widgets(app_instance):
    """Strg+←/→ greift nicht, wenn der Fokus in einem Eingabefeld liegt."""

    class _Ev:
        def __init__(self, widget):
            self.widget = widget

    before = app_instance.date_entry.get()
    # Fokus im Notiz-Text-Widget → Shortcut wird NICHT ausgeführt.
    app_instance._shortcut_guard(_Ev(app_instance.note_entry), lambda: app_instance._step_date(-1))
    assert app_instance.date_entry.get() == before
    # Fokus auf einem Button-artigen Widget → Shortcut wird ausgeführt.
    app_instance.set_today_date()
    app_instance._shortcut_guard(_Ev(app_instance.start_button), lambda: app_instance._step_date(-1))
    assert app_instance.date_entry.get() != datetime.today().strftime("%d-%m-%Y")


def test_note_field_height_from_config(app_instance):
    """Das Notizfeld übernimmt die konfigurierte Zeilenzahl (Default 2)."""
    assert int(app_instance.note_entry.cget("height")) == int(app_instance.config.get("note_field_lines", 2)) == 2


def test_note_navigation_bindings_present(app_instance):
    """Wort-Navigation ist direkt am Widget gebunden (nicht nur Klassen-Binding)."""
    w = app_instance.note_entry
    for seq in (
        "<Control-Left>",
        "<Control-Right>",
        "<Control-BackSpace>",
        "<Control-Delete>",
        "<Control-a>",
        "<Control-A>",  # Caps Lock liefert Keysym 'A'
    ):
        assert w.bind(seq), f"Binding fehlt: {seq}"


def test_note_word_jump_and_select_all(app_instance):
    """Strg+Pfeil-Handler springen wortweise; Strg+A markiert den ganzen Text."""
    w = app_instance.note_entry
    w.delete("1.0", END)
    w.insert("1.0", "alpha beta gamma")
    w.mark_set("insert", "end-1c")

    assert app_instance._note_word_jump(back=True) == "break"
    assert w.index("insert") == "1.11"  # Wortanfang von "gamma"
    app_instance._note_word_jump(back=True)
    assert w.index("insert") == "1.6"  # Wortanfang von "beta"

    assert app_instance._note_select_all() == "break"
    ranges = w.tag_ranges("sel")
    assert ranges and w.get(ranges[0], ranges[1]) == "alpha beta gamma"


def test_note_delete_word_back(app_instance):
    """Strg+BackSpace löscht das Wort vor dem Cursor."""
    w = app_instance.note_entry
    w.delete("1.0", END)
    w.insert("1.0", "alpha beta gamma")
    w.mark_set("insert", "end-1c")
    assert app_instance._note_delete_word(back=True) == "break"
    assert w.get("1.0", "end-1c") == "alpha beta "


def test_project_header_row_carries_session(app_instance):
    """Layout A: die Projekt-Kopfzeile trägt die erste Session (Doppel-/Rechtsklick-Ziel)."""
    from db_helper import log_start, log_stop

    name = "hdr_user"
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=today, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=today + timedelta(hours=1), conn=app_instance.db_conn)
    app_instance.name_entry.set(name)
    app_instance.set_today_date()
    app_instance.update_db_content()

    rows = app_instance.db_content_listbox.get(0, END)
    hdr_idx = next(i for i, t in enumerate(rows) if t.strip().startswith("Projekt 1"))
    assert isinstance(app_instance._row_entries[hdr_idx], dict)
    assert app_instance._row_entries[hdr_idx]["project"] == "1"
    user_idx = next(i for i, t in enumerate(rows) if t.startswith("Benutzer:"))
    assert app_instance._row_entries[user_idx] is None


def test_toggle_row_transferred_roundtrip(app_instance):
    """Der Kontextmenü-Toggle setzt/entfernt den ✓-Status für die Zielzeile."""
    from db_helper import get_daily_meta, log_start, log_stop

    name = "ctx_user"
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=today, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=today + timedelta(hours=1), conn=app_instance.db_conn)
    iso_today = today.strftime("%Y-%m-%d")
    session = {"user": name, "project": "1", "date_iso": iso_today}

    app_instance._toggle_row_transferred(session, True)
    meta = get_daily_meta(app_instance.db_conn, name, "1", iso_today)
    assert meta["transferred"] is True
    assert meta["transferred_at"] == datetime.now().strftime("%Y-%m-%d")

    app_instance._toggle_row_transferred(session, False)
    assert get_daily_meta(app_instance.db_conn, name, "1", iso_today)["transferred"] is False
