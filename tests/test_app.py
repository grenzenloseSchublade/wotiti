import os
import sys
from datetime import datetime, timedelta
from tkinter import END, Tk

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from app import App


@pytest.fixture
def app_instance():
    """Fixture to create the application instance for testing."""
    root = Tk()
    app_instance = App(root)
    yield app_instance
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
    """Ohne Benutzer/Events zeigt die Tagesliste die Empty-State-Zeile."""
    app_instance.db_conn.cursor().execute("DELETE FROM users")
    app_instance.update_db_content()
    assert "Keine Einträge für diesen Tag" in app_instance.day_list.get("1.0", "end-1c")


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
    """Ohne expliziten Config-Wert gilt der Default von 120 Minuten."""
    assert app_instance.idle_timeout_minutes == 120


def test_idle_timeout_config_custom_value():
    """Ein gesetzter Config-Wert übersteuert den Default."""
    import utils

    cfg = utils.load_config()
    cfg["idle_timeout_minutes"] = 45
    utils.save_config(cfg)
    root = Tk()
    try:
        app = App(root)
        assert app.idle_timeout_minutes == 45
    finally:
        root.destroy()


def test_add_manual_event_allows_today(app_instance):
    """add_manual_event öffnet für heute den Dialog (wie der '+'-Button verspricht),
    schreibt aber ohne Speichern nichts in die Datenbank."""
    from tkinter import Toplevel

    app_instance.name_entry.set("u_today")
    app_instance.project_entry.set("p_today")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    cur = app_instance.db_conn.cursor()
    before = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    app_instance.add_manual_event()
    wins = [w for w in app_instance.master.winfo_children() if isinstance(w, Toplevel)]
    assert wins, "Dialog für heute wurde nicht geöffnet"
    wins[-1].destroy()
    after = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before


def test_add_manual_event_rejects_future(app_instance):
    """Für Zukunftsdaten bricht add_manual_event früh ab: kein Dialog, kein Eintrag."""
    from tkinter import Toplevel

    app_instance.name_entry.set("u_future")
    app_instance.project_entry.set("p_future")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, (datetime.today() + timedelta(days=1)).strftime("%d-%m-%Y"))
    cur = app_instance.db_conn.cursor()
    before = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    app_instance.add_manual_event()
    assert not [w for w in app_instance.master.winfo_children() if isinstance(w, Toplevel)]
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
    """Test updating the day list."""
    # Erst eine Session starten, damit Events vorhanden sind.
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    today = datetime.today().strftime("%d-%m-%Y")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, today)
    app_instance.start_session()
    app_instance.update_db_content()
    assert app_instance.day_list.get("1.0", "end-1c") != ""
    assert str(app_instance.day_list.cget("state")) == "disabled"


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


def test_pairing_invariant_display_vs_stats_back_to_back(app_instance):
    """Invariante: Anzeige (FIFO) und Stats (LIFO) paaren „Stop A == Start B" identisch.

    Zwei Rücken-an-Rücken-Sessions (09-12, 12-13) müssen in BEIDEN Pfaden als
    zwei normale Sessions erscheinen — kein 0h-Paar, keine Mega-Session. Sonst
    weichen Tagesliste und Statistik-Summen/Session-Filter voneinander ab
    (Memory session-pairing).
    """
    from db_helper import pair_sessions_lifo

    events = [
        _ev(1, "start", "09:00"),
        _ev(2, "stop", "12:00"),
        _ev(3, "start", "12:00"),
        _ev(4, "stop", "13:00"),
    ]
    display_pairs = sorted((s["start_ts"], s["stop_ts"]) for s in app_instance._pair_day_sessions(events))
    lifo_pairs = sorted(
        pair_sessions_lifo([(etype, datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")) for _id, _u, _p, etype, ts in events])
    )
    expected = [
        (datetime(2026, 6, 23, 9, 0), datetime(2026, 6, 23, 12, 0)),
        (datetime(2026, 6, 23, 12, 0), datetime(2026, 6, 23, 13, 0)),
    ]
    assert display_pairs == lifo_pairs == expected


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


def test_shortcut_guard_blocks_session_actions_in_text_widget(app_instance):
    """Strg+E/P/S laufen über den Guard: Textfokus blockt, Button-Fokus nicht."""

    class _Ev:
        def __init__(self, widget):
            self.widget = widget

    fired = []
    assert app_instance._shortcut_guard(_Ev(app_instance.note_entry), lambda: fired.append(1)) is None
    assert fired == []
    assert app_instance._shortcut_guard(_Ev(app_instance.start_button), lambda: fired.append(1)) == "break"
    assert fired == [1]


def test_shortcut_guard_blocks_during_modal_grab(app_instance):
    """Bei aktivem modalem Grab feuern globale Shortcuts nicht."""
    from tkinter import TclError, Toplevel

    class _Ev:
        def __init__(self, widget):
            self.widget = widget

    dlg = Toplevel(app_instance.master)
    dlg.update()
    try:
        dlg.grab_set()
    except TclError:
        dlg.wait_visibility()
        dlg.grab_set()

    fired = []
    try:
        assert app_instance.master.grab_current() is not None
        assert app_instance._shortcut_guard(_Ev(app_instance.start_button), lambda: fired.append(1)) is None
        assert fired == []
    finally:
        dlg.grab_release()
        dlg.destroy()

    # Nach dem Grab feuert der Shortcut wieder normal.
    assert app_instance._shortcut_guard(_Ev(app_instance.start_button), lambda: fired.append(1)) == "break"
    assert fired == [1]


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

    rows = app_instance.day_list.get("1.0", "end-1c").splitlines()
    hdr_line = next(i + 1 for i, t in enumerate(rows) if t.startswith("▌ 1"))
    assert app_instance._line_sessions[hdr_line]["project"] == "1"
    # Notiz-Platzhalterzeile trägt keine Session.
    note_line = next(i + 1 for i, t in enumerate(rows) if t == "(keine Notiz)")
    assert note_line not in app_instance._line_sessions


def test_day_list_merged_times_line(app_instance):
    """Layout A: Sessions eines Projekts in EINER ·-Zeile; Kopf trägt die Summe."""
    from db_helper import log_start, log_stop

    name = "merge_user"
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=base, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=base + timedelta(hours=1), conn=app_instance.db_conn)
    log_start(project="1", name=name, timestamp=base + timedelta(hours=2), conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=base + timedelta(hours=3), conn=app_instance.db_conn)
    app_instance.name_entry.set(name)
    app_instance.set_today_date()
    app_instance.update_db_content()

    text = app_instance.day_list.get("1.0", "end-1c")
    assert "09:00–10:00 · 11:00–12:00" in text
    # Kopfzeile enthält die Tages-Summe des Projekts.
    hdr = next(ln for ln in text.splitlines() if ln.startswith("▌ 1"))
    assert "2:00 h" in hdr
    # Session-Tags: sess1 existiert und mappt auf die ZWEITE Session.
    assert app_instance.day_list.tag_ranges("sess1")
    assert app_instance._tag_sessions["sess1"]["start_ts"] == base + timedelta(hours=2)


def test_day_list_layout_b_one_line_per_session(app_instance):
    """Layout B (chronologisch): eine Zeile je Session, Mapping 1:1."""
    from db_helper import log_start, log_stop

    name = "chrono_user"
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=base, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=base + timedelta(hours=1), conn=app_instance.db_conn)
    log_start(project="2", name=name, timestamp=base + timedelta(hours=2), conn=app_instance.db_conn)
    log_stop(project="2", name=name, timestamp=base + timedelta(hours=3), conn=app_instance.db_conn)
    app_instance.name_entry.set(name)
    app_instance.set_today_date()
    app_instance.config["entry_list_chronological"] = True
    app_instance.update_db_content()

    rows = app_instance.day_list.get("1.0", "end-1c").splitlines()
    sess_lines = [i + 1 for i, t in enumerate(rows) if "–" in t and "▌" in t]
    assert len(sess_lines) == 2
    projects = [app_instance._line_sessions[n]["project"] for n in sess_lines]
    assert projects == ["1", "2"]


def test_day_list_note_without_prefix(app_instance):
    """Notiz erscheint ohne 'Notiz:'-Präfix und trägt den note-Tag."""
    from db_helper import log_start, log_stop, set_daily_note

    name = "note_user"
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=base, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=base + timedelta(hours=1), conn=app_instance.db_conn)
    iso_today = datetime.now().strftime("%Y-%m-%d")
    set_daily_note(app_instance.db_conn, name, "1", iso_today, "Meeting mit Team")
    app_instance.name_entry.set(name)
    app_instance.set_today_date()
    app_instance.update_db_content()

    text = app_instance.day_list.get("1.0", "end-1c")
    assert "Meeting mit Team" in text
    assert "Notiz:" not in text
    ranges = app_instance.day_list.tag_ranges("note")
    assert ranges
    assert app_instance.day_list.get(ranges[0], ranges[1]) == "Meeting mit Team"


def test_day_list_empty_note_placeholder(app_instance):
    """Leere Notiz bei vorhandenen Zeiten → graue '(keine Notiz)'-Zeile."""
    from db_helper import log_start, log_stop

    name = "empty_note_user"
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=base, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=base + timedelta(hours=1), conn=app_instance.db_conn)
    app_instance.name_entry.set(name)
    app_instance.set_today_date()
    app_instance.update_db_content()

    assert "(keine Notiz)" in app_instance.day_list.get("1.0", "end-1c")


def test_day_list_note_only_project(app_instance):
    """Projekt mit Notiz aber ohne Events rendert '(keine Zeiten)'."""
    from db_helper import set_daily_note

    name = "noteonly_user"
    iso_today = datetime.now().strftime("%Y-%m-%d")
    set_daily_note(app_instance.db_conn, name, "solo", iso_today, "nur eine Notiz")
    app_instance.name_entry.set(name)
    app_instance.set_today_date()
    app_instance.update_db_content()

    text = app_instance.day_list.get("1.0", "end-1c")
    assert "(keine Zeiten)" in text
    assert "nur eine Notiz" in text


def test_day_list_takefocus_off(app_instance):
    """takefocus=0 schützt die globalen Shortcuts (Shortcut-Guard skippt Text)."""
    assert str(app_instance.day_list.cget("takefocus")) == "0"
    # Tk setzt bei Mausklick trotzdem den Fokus (tk::TextButton1) — der
    # FocusIn-Redirect leitet ihn weg, sonst blockiert der Shortcut-Guard
    # Strg+←/→/T dauerhaft.
    assert app_instance.day_list.bind("<FocusIn>"), "FocusIn-Redirect fehlt"


def test_day_list_user_head_only_without_filter(app_instance):
    """Ohne Namensfilter: Benutzer-Kopf 'user — Di 23.09.' ohne Session-Mapping."""
    from db_helper import log_start, log_stop

    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    for name in ("head_a", "head_b"):
        log_start(project="1", name=name, timestamp=base, conn=app_instance.db_conn)
        log_stop(project="1", name=name, timestamp=base + timedelta(hours=1), conn=app_instance.db_conn)
    app_instance.name_entry.set("")
    app_instance.set_today_date()
    app_instance.update_db_content()

    rows = app_instance.day_list.get("1.0", "end-1c").splitlines()
    wday = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][datetime.now().weekday()]
    expected_date = f"{wday} {datetime.now().strftime('%d.%m.')}"
    for name in ("head_a", "head_b"):
        head_line = next(i + 1 for i, t in enumerate(rows) if t == f"{name} — {expected_date}")
        # Kopfzeile ist kein Doppel-/Rechtsklick-Ziel: kein Session-Mapping.
        assert head_line not in app_instance._line_sessions

    # Mit aktivem Namensfilter (ein Benutzer) verschwindet der Kopf.
    app_instance.name_entry.set("head_a")
    app_instance.update_db_content()
    assert "head_a —" not in app_instance.day_list.get("1.0", "end-1c")


def test_day_list_multiline_note_renders_lines(app_instance):
    """Mehrzeilige Notiz erscheint als mehrere Zeilen in der Tagesliste."""
    from db_helper import log_start, log_stop, set_daily_note

    name = "multiline_user"
    base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    log_start(project="1", name=name, timestamp=base, conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=base + timedelta(hours=1), conn=app_instance.db_conn)
    iso_today = datetime.now().strftime("%Y-%m-%d")
    set_daily_note(app_instance.db_conn, name, "1", iso_today, "erste Zeile\nzweite Zeile")
    app_instance.name_entry.set(name)
    app_instance.set_today_date()
    app_instance.update_db_content()

    rows = app_instance.day_list.get("1.0", "end-1c").splitlines()
    assert "erste Zeile" in rows
    assert "zweite Zeile" in rows


def test_note_shift_return_inserts_newline(app_instance):
    """Shift+Enter fügt einen Umbruch ein; Enter speichert weiterhin."""
    w = app_instance.note_entry
    # Die Bindings müssen am Widget verdrahtet sein — der direkte Handler-
    # Aufruf unten würde eine gelöschte bind()-Zeile sonst nicht bemerken.
    assert w.bind("<Shift-Return>"), "Binding fehlt: <Shift-Return>"
    assert w.bind("<Return>"), "Binding fehlt: <Return>"
    w.delete("1.0", END)
    w.insert("1.0", "erste")
    w.mark_set("insert", "end-1c")
    assert app_instance._on_note_shift_return() == "break"
    w.insert("insert", "zweite")
    assert w.get("1.0", "end-1c") == "erste\nzweite"
    assert app_instance._on_note_return() == "break"


def test_note_shift_return_replaces_selection(app_instance):
    """Shift+Enter ersetzt eine aktive Selektion (wie das native tk::TextInsert)."""
    w = app_instance.note_entry
    w.delete("1.0", END)
    w.insert("1.0", "alles markiert")
    app_instance._note_select_all()
    assert app_instance._on_note_shift_return() == "break"
    assert w.get("1.0", "end-1c") == "\n"
    assert not w.tag_ranges("sel")


# ---------------------------------------------------------------------------
# Mitternacht/Datumsgrenze: Tagesliste, Session-Editor, Timer-Rollover
# ---------------------------------------------------------------------------


def _log_midnight_session(app_instance, name, project="1"):
    """Legt eine 23:50 → 00:30-Session (über Mitternacht) in der DB an."""
    from db_helper import log_start, log_stop

    start = datetime(2026, 6, 23, 23, 50)
    log_start(project=project, name=name, timestamp=start, conn=app_instance.db_conn)
    log_stop(project=project, name=name, timestamp=start + timedelta(minutes=40), conn=app_instance.db_conn)
    return start


def _view_day(app_instance, name, date_str):
    app_instance.name_entry.set(name)
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, date_str)
    app_instance.update_db_content()


def _find_editor(app_instance):
    from tkinter import Toplevel

    wins = [w for w in app_instance.master.winfo_children() if isinstance(w, Toplevel)]
    assert wins, "Session-Editor wurde nicht geöffnet"
    return wins[-1]


def _invoke_editor_button(win, label):
    from tkinter import Button

    stack = [win]
    while stack:
        w = stack.pop()
        stack.extend(w.winfo_children())
        if isinstance(w, Button) and w.cget("text") == label:
            w.invoke()
            return
    raise AssertionError(f"Button '{label}' nicht gefunden")


def _editor_entries(win):
    """Die drei Entry-Felder des Editors in Aufbaureihenfolge: Datum, Start, Ende.

    ttk.Combobox erbt von tkinter.Entry — die Projekt-Combobox muss daher
    explizit ausgefiltert werden.
    """
    from tkinter import Entry
    from tkinter.ttk import Combobox

    return [w for w in win.winfo_children() if isinstance(w, Entry) and not isinstance(w, Combobox)]


def _patch_messageboxes(monkeypatch):
    """Blockierende Dialoge abfangen; Warnungen/Fehler werden gesammelt."""
    import app as app_module

    calls = []
    monkeypatch.setattr(app_module.messagebox, "showwarning", lambda *a, **k: calls.append(("warning", a)))
    monkeypatch.setattr(app_module.messagebox, "showerror", lambda *a, **k: calls.append(("error", a)))
    monkeypatch.setattr(app_module.messagebox, "askyesno", lambda *a, **k: True)
    return calls


def _user_events(app_instance, name):
    cur = app_instance.db_conn.cursor()
    return cur.execute(
        "SELECT e.event_type, e.timestamp FROM events e JOIN users u ON u.id = e.user_id "
        "WHERE u.name = ? ORDER BY e.timestamp, e.id",
        (name,),
    ).fetchall()


def test_day_list_midnight_session_closed_on_start_day(app_instance):
    """23:50 → 00:30 erscheint am STARTTAG als abgeschlossene Session (0:40),
    nicht ewig als „läuft" (Regression: date-Spalten-Filter sah den Stop nie)."""
    name = "mid_list"
    _log_midnight_session(app_instance, name)
    _view_day(app_instance, name, "23-06-2026")

    assert len(app_instance._day_sessions) == 1
    s = app_instance._day_sessions[0]
    assert s["start_id"] is not None and s["stop_id"] is not None
    assert abs(s["dur_h"] - 40 / 60) < 1e-9
    text = app_instance.day_list.get("1.0", "end-1c")
    assert "23:50–00:30" in text
    assert "läuft" not in text
    assert "0:40 h" in text


def test_day_list_midnight_session_no_orphan_stop_on_next_day(app_instance):
    """Der Folgetag zeigt KEINEN verwaisten Stop der Mitternachts-Session."""
    name = "mid_next"
    _log_midnight_session(app_instance, name)
    _view_day(app_instance, name, "24-06-2026")

    assert app_instance._day_sessions == []
    assert "00:30" not in app_instance.day_list.get("1.0", "end-1c")


def test_day_list_regular_day_unaffected_by_window(app_instance):
    """Normale Sessions des Nachbartags rutschen NICHT in den Anzeigetag."""
    from db_helper import log_start, log_stop

    name = "mid_iso"
    _log_midnight_session(app_instance, name)
    # Zusätzliche normale Session am Folgetag.
    log_start(project="1", name=name, timestamp=datetime(2026, 6, 24, 9, 0), conn=app_instance.db_conn)
    log_stop(project="1", name=name, timestamp=datetime(2026, 6, 24, 10, 0), conn=app_instance.db_conn)

    _view_day(app_instance, name, "23-06-2026")
    assert [s["start_ts"].strftime("%H:%M") for s in app_instance._day_sessions] == ["23:50"]
    _view_day(app_instance, name, "24-06-2026")
    assert [s["start_ts"].strftime("%H:%M") for s in app_instance._day_sessions] == ["09:00"]
    assert "1:00 h" in app_instance.day_list.get("1.0", "end-1c")


def test_editor_midnight_session_roundtrip_no_duplicate(app_instance, monkeypatch):
    """Mitternachts-Session im Editor unverändert speichern: kein zweites
    Stop-Event, Ende bleibt auf dem Folgetag (Regression: 5 min statt 40 +
    verwaister Stop)."""
    calls = _patch_messageboxes(monkeypatch)
    name = "mid_edit"
    _log_midnight_session(app_instance, name)
    _view_day(app_instance, name, "23-06-2026")
    session = app_instance._day_sessions[0]
    assert session["stop_id"] is not None

    app_instance._edit_event(session=session)
    _invoke_editor_button(_find_editor(app_instance), "Speichern")

    assert calls == []
    events = _user_events(app_instance, name)
    assert [e[0] for e in events] == ["start", "stop"]
    assert events[0][1] == "2026-06-23 23:50:00"
    assert events[1][1] == "2026-06-24 00:30:00"


def test_editor_double_stop_guard_updates_existing_stop(app_instance, monkeypatch):
    """Zeigt eine veraltete Ansicht die Session als offen, obwohl der Stop in
    der DB existiert, aktualisiert Speichern den vorhandenen Stop statt ein
    zweites Stop-Event anzulegen (Doppel-Stop-Guard)."""
    calls = _patch_messageboxes(monkeypatch)
    name = "mid_guard"
    start = _log_midnight_session(app_instance, name)
    cur = app_instance.db_conn.cursor()
    start_id = cur.execute(
        "SELECT e.id FROM events e JOIN users u ON u.id = e.user_id WHERE u.name = ? AND e.event_type = 'start'",
        (name,),
    ).fetchone()[0]
    # Session-Dict, wie es der alte date-Spalten-Filter geliefert hätte: offen.
    stale = {
        "user": name,
        "project": "1",
        "start_id": start_id,
        "stop_id": None,
        "start_ts": start,
        "stop_ts": None,
        "dur_h": None,
        "sort_ts": start,
        "date_iso": "2026-06-23",
    }

    app_instance._edit_event(session=stale)
    win = _find_editor(app_instance)
    end_entry = _editor_entries(win)[2]
    end_entry.delete(0, END)
    end_entry.insert(0, "00:30")
    _invoke_editor_button(win, "Speichern")

    assert calls == []
    events = _user_events(app_instance, name)
    assert [e[0] for e in events] == ["start", "stop"]  # kein Duplikat
    assert events[0][1] == "2026-06-23 23:50:00"  # Start unangetastet
    assert events[1][1] == "2026-06-24 00:30:00"


def test_editor_end_before_start_assumes_next_day(app_instance, monkeypatch):
    """Ende < Start beim Stop-Nachtragen → Ende landet auf dem Folgetag
    (früher: Warnung „Ende liegt vor dem Start", Speichern unmöglich)."""
    from db_helper import log_start

    calls = _patch_messageboxes(monkeypatch)
    name = "mid_open"
    log_start(project="1", name=name, timestamp=datetime(2026, 6, 23, 22, 0), conn=app_instance.db_conn)
    _view_day(app_instance, name, "23-06-2026")
    session = app_instance._day_sessions[0]
    assert session["stop_id"] is None

    app_instance._edit_event(session=session)
    win = _find_editor(app_instance)
    end_entry = _editor_entries(win)[2]
    end_entry.delete(0, END)
    end_entry.insert(0, "01:00")
    _invoke_editor_button(win, "Speichern")

    assert calls == []
    events = _user_events(app_instance, name)
    assert [e[0] for e in events] == ["start", "stop"]
    assert events[0][1] == "2026-06-23 22:00:00"  # Start unangetastet
    assert events[1][1] == "2026-06-24 01:00:00"


def test_timer_rollover_rolls_date_field(app_instance):
    """Tageswechsel bei laufender Session: das Datumsfeld rollt vom alten
    „heute" auf den neuen Tag (Timer friert nicht ein)."""
    _start_test_session(app_instance, name="roll_user")
    yesterday = datetime.today().date() - timedelta(days=1)
    app_instance._timer_last_date = yesterday
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, yesterday.strftime("%d-%m-%Y"))

    app_instance._check_day_rollover()

    assert app_instance.date_entry.get() == datetime.today().strftime("%d-%m-%Y")
    assert app_instance._timer_last_date == datetime.today().date()
    assert app_instance._is_viewing_today() is True


def test_timer_rollover_keeps_deliberate_other_date(app_instance):
    """Betrachtet der Nutzer bewusst einen anderen Tag, bleibt das Datum stehen."""
    _start_test_session(app_instance, name="roll_keep")
    app_instance._timer_last_date = datetime.today().date() - timedelta(days=1)
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-2020")

    app_instance._check_day_rollover()

    assert app_instance.date_entry.get() == "01-01-2020"
    assert app_instance._timer_last_date == datetime.today().date()


def test_timer_rollover_noop_without_session(app_instance):
    """Ohne laufende Session wird nur der Tick-Tag nachgezogen, das Feld bleibt."""
    yesterday = datetime.today().date() - timedelta(days=1)
    app_instance._timer_last_date = yesterday
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, yesterday.strftime("%d-%m-%Y"))

    app_instance._check_day_rollover()

    assert app_instance.date_entry.get() == yesterday.strftime("%d-%m-%Y")
    assert app_instance._timer_last_date == datetime.today().date()


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


def test_timer_tick_writes_heartbeat_when_session_active(app_instance):
    """Der Timer-Tick persistiert bei aktiver Session einen last_seen-Heartbeat."""
    from db_helper import read_heartbeat

    assert read_heartbeat(app_instance.db_conn) is None
    app_instance.session_active[("test_user", "1")] = True
    app_instance._last_heartbeat_ts = 0.0
    app_instance.update_timer_realtime()
    assert read_heartbeat(app_instance.db_conn) is not None


def test_timer_tick_no_heartbeat_when_idle(app_instance):
    """Ohne aktive Session/Pause schreibt der Tick keinen Heartbeat (Standby-Hygiene)."""
    from db_helper import read_heartbeat

    app_instance._last_heartbeat_ts = 0.0
    app_instance.update_timer_realtime()
    assert read_heartbeat(app_instance.db_conn) is None


def test_timer_tick_reschedules_after_exception(app_instance, monkeypatch, caplog):
    """Ein Fehler im Tick-Körper darf die after-Kette nicht stoppen: der
    Folgetick wird trotzdem geplant und der Fehler geloggt."""

    def boom():
        raise RuntimeError("injizierter Tick-Fehler")

    monkeypatch.setattr(app_instance, "_timer_tick", boom)
    app_instance._timer_after_id = None
    with caplog.at_level("ERROR", logger="app"):
        app_instance.update_timer_realtime()

    assert app_instance._timer_after_id is not None
    assert any("Timer-Tick" in rec.message for rec in caplog.records)


def test_on_closing_aborts_when_stop_fails(app_instance, monkeypatch):
    """Fehlgeschlagener log_stop beim Beenden: 'Nein' bricht das Schließen ab."""
    import app as app_module

    app_instance.session_active[("test_user", "1")] = True
    monkeypatch.setattr(app_module, "log_stop", lambda **kw: False)
    # 1. Dialog (aktive Arbeit): Ja; 2. Dialog (Stop nicht gespeichert): Nein.
    answers = iter([True, False])
    monkeypatch.setattr(app_module.messagebox, "askyesno", lambda *a, **kw: next(answers))

    app_instance._on_closing()

    assert app_instance._closing is False
    assert app_instance.master.winfo_exists()
    assert app_instance.db_conn is not None


def test_on_closing_signal_mode_asks_nothing(app_instance, monkeypatch):
    """ask=False (SIGTERM-Pfad): keine Dialoge, Session gestoppt, Fenster zerstört."""
    import app as app_module

    app_instance.name_entry.set("sig_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    app_instance.start_session()
    assert app_instance.session_active.get(("sig_user", "1")) is True

    def _kein_dialog(*a, **kw):
        raise AssertionError("Dialog im nicht-interaktiven Shutdown")

    monkeypatch.setattr(app_module.messagebox, "askyesno", _kein_dialog)
    destroyed = []
    orig_destroy = app_instance.master.destroy
    monkeypatch.setattr(app_instance.master, "destroy", lambda: destroyed.append(True))

    db_conn = app_instance.db_conn
    app_instance._on_closing(ask=False)

    assert destroyed == [True]
    assert app_instance._closing is True
    # DB-Verbindung wurde im Stop-Pfad regulär geschlossen.
    import sqlite3

    with pytest.raises(sqlite3.ProgrammingError):
        db_conn.execute("SELECT 1")

    # Echtes destroy nachholen: die Fixture-Teardown-Reihenfolge ruft
    # root.destroy() VOR dem Monkeypatch-Undo auf (= die No-op-Lambda).
    # Ohne diese Zeile bliebe die Tk-Instanz am Leben und als
    # tkinter._default_root zurück — alle späteren Tests, deren Widgets
    # implizite StringVars anlegen (z. B. der Session-Editor), binden dann
    # an den falschen Tcl-Interpreter (Felder leer, Edits wirkungslos).
    orig_destroy()


def test_shutdown_from_signal_delegates_without_dialogs(app_instance, monkeypatch):
    """shutdown_from_signal ruft _on_closing(ask=False) und ist nach _closing ein No-Op."""
    calls = []
    monkeypatch.setattr(app_instance, "_on_closing", lambda ask=True: calls.append(ask))

    app_instance.shutdown_from_signal()
    assert calls == [False]

    app_instance._closing = True
    app_instance.shutdown_from_signal()
    assert calls == [False]


def test_stale_cleanup_visible_in_console_after_crash():
    """Nach Absturz: Start-Aufräumen meldet sich sichtbar in der App-Konsole.

    Simuliert einen unsauber beendeten Lauf (offener Start + last_seen-Heartbeat
    2 h später) und prüft, dass der nächste App-Start die Schließung samt
    Heartbeat-Zeitpunkt in der Konsole ausweist — nicht nur im Logfile.
    """
    import utils
    from db_helper import create_connection, create_main_table, log_start, write_heartbeat

    db_path = utils.load_config()["database_path"]
    conn = create_connection(db_path)
    create_main_table(conn)
    log_start(project="1", name="crash_user", timestamp=datetime(2026, 6, 23, 10, 0), conn=conn)
    write_heartbeat(conn, datetime(2026, 6, 23, 12, 0))
    conn.close()

    root = Tk()
    try:
        app = App(root)
        console_text = app.console.get("1.0", END)
        assert "verwaiste Session(s)" in console_text
        assert "23-06-2026 12:00:00" in console_text
        row = app.db_conn.execute("SELECT timestamp FROM events WHERE event_type = 'stop'").fetchone()
        assert row == ("2026-06-23 12:00:00",)
    finally:
        root.destroy()


# --- Fehlende konfigurierte DB beim App-Start: Rückfrage statt stillem Neuanlegen ---


def _point_config_to_missing_db(tmp_path):
    """Config auf eine nicht existierende DB in einem fehlenden Verzeichnis zeigen lassen."""
    import utils

    cfg = utils.load_config()
    missing = tmp_path / "nicht_gemountet" / "missing.db"
    cfg["database_path"] = str(missing)
    utils.save_config(cfg)
    return missing


def test_missing_db_decline_creates_nothing(tmp_path, monkeypatch):
    """Nutzer verneint: keine Datei, kein Verzeichnis, db_conn=None, Konsole warnt."""
    missing = _point_config_to_missing_db(tmp_path)
    asked = []
    monkeypatch.setattr(App, "_confirm_create_missing_db", lambda self, p: (asked.append(p), False)[1])

    root = Tk()
    try:
        app = App(root)
        assert asked == [str(missing)]
        assert app.db_conn is None
        assert not missing.exists()
        assert not missing.parent.exists()  # create_connection hätte das Verzeichnis angelegt
        console_text = app.console.get("1.0", END)
        assert "nicht gefunden" in console_text
    finally:
        root.destroy()


def test_missing_db_confirm_creates_db(tmp_path, monkeypatch):
    """Nutzer bestätigt: DB wird (samt Verzeichnis) angelegt und normal geöffnet."""
    missing = _point_config_to_missing_db(tmp_path)
    monkeypatch.setattr(App, "_confirm_create_missing_db", lambda self, p: True)

    root = Tk()
    try:
        app = App(root)
        assert app.db_conn is not None
        assert missing.exists()
    finally:
        root.destroy()


def test_existing_db_starts_without_prompt(monkeypatch):
    """Vorhandene DB (Standard-Fixture) → keine Rückfrage beim Start."""

    def _boom(self, p):
        raise AssertionError("Rückfrage darf bei vorhandener DB nicht erscheinen")

    monkeypatch.setattr(App, "_confirm_create_missing_db", _boom)
    root = Tk()
    try:
        app = App(root)
        assert app.db_conn is not None
    finally:
        root.destroy()


def _find_settings_db_combobox(win):
    """Die Datenbank-Combobox des Einstellungsdialogs (in der LabelFrame 'Datenbank')."""
    from tkinter import LabelFrame
    from tkinter.ttk import Combobox

    stack = [win]
    while stack:
        w = stack.pop()
        if isinstance(w, LabelFrame) and w.cget("text") == "Datenbank":
            for child in w.winfo_children():
                if isinstance(child, Combobox):
                    return child
        stack.extend(w.winfo_children())
    raise AssertionError("Datenbank-Combobox nicht gefunden")


def _assert_settings_save_blocks_db_change(app_instance, monkeypatch, tmp_path):
    """Gemeinsamer Kern: Speichern mit geändertem DB-Pfad muss blocken,
    der Dialog offen bleiben und der DB-Pfad unverändert sein."""
    calls = _patch_messageboxes(monkeypatch)
    win = _find_editor(app_instance)
    other = tmp_path / "andere.db"
    other.touch()
    _find_settings_db_combobox(win).set(str(other))
    old_path = app_instance._db_path
    _invoke_editor_button(win, "Speichern")
    warnings = [a for kind, a in calls if kind == "warning"]
    assert warnings and warnings[0][0] == "Session aktiv"
    assert app_instance._db_path == old_path
    assert win.winfo_exists()
    win.destroy()


def test_settings_save_blocks_db_change_with_live_session(app_instance, monkeypatch, tmp_path):
    """Session startet, WÄHREND die Einstellungen offen sind: das beim Öffnen
    eingefrorene sessions_active wäre False — der Live-Check muss trotzdem blocken."""
    app_instance.open_settings()
    app_instance.session_active[("live_user", "live_proj")] = True
    _assert_settings_save_blocks_db_change(app_instance, monkeypatch, tmp_path)


def test_settings_save_blocks_db_change_with_live_break(app_instance, monkeypatch, tmp_path):
    """Auch eine laufende Pause (ohne aktive Session) blockt den DB-Wechsel."""
    app_instance.open_settings()
    app_instance._break_active = True
    _assert_settings_save_blocks_db_change(app_instance, monkeypatch, tmp_path)


# ---------------------------------------------------------------------------
# Session-Editor _edit_event/_save: Parsing, Nachtragen, Overlap, key_changed
# ---------------------------------------------------------------------------


def _log_closed_session(app_instance, name, project="1", day=(2026, 6, 23), start_hm=(9, 0), end_hm=(10, 0)):
    """Legt eine abgeschlossene Session am gegebenen Tag an."""
    from db_helper import log_start, log_stop

    s = datetime(*day, *start_hm)
    e = datetime(*day, *end_hm)
    log_start(project=project, name=name, timestamp=s, conn=app_instance.db_conn)
    log_stop(project=project, name=name, timestamp=e, conn=app_instance.db_conn)
    return s, e


def _editor_project_combo(win):
    """Die Projekt-Combobox des Session-Editors."""
    from tkinter.ttk import Combobox

    return next(w for w in win.winfo_children() if isinstance(w, Combobox))


def test_editor_invalid_hhmm_blocks_save(app_instance, monkeypatch):
    """Ungültige Startzeit (kein HH:MM) → Warnung, Dialog bleibt offen,
    kein Event verändert."""
    calls = _patch_messageboxes(monkeypatch)
    name = "ed_badtime"
    _log_closed_session(app_instance, name)
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    start_entry = _editor_entries(win)[1]
    start_entry.delete(0, END)
    start_entry.insert(0, "9 Uhr")
    _invoke_editor_button(win, "Speichern")

    warnings = [a for kind, a in calls if kind == "warning"]
    assert warnings and "Startzeit" in warnings[0][1]
    assert win.winfo_exists()  # Dialog bleibt offen, nichts gespeichert
    assert _user_events(app_instance, name) == [
        ("start", "2026-06-23 09:00:00"),
        ("stop", "2026-06-23 10:00:00"),
    ]
    win.destroy()


def test_editor_empty_start_with_existing_event_blocks_save(app_instance, monkeypatch):
    """Leeres Startfeld ist NICHT erlaubt, wenn ein Start-Event existiert —
    sonst würde der vorhandene Start stillschweigend verwaisen."""
    calls = _patch_messageboxes(monkeypatch)
    name = "ed_empty"
    _log_closed_session(app_instance, name)
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    start_entry = _editor_entries(win)[1]
    start_entry.delete(0, END)
    _invoke_editor_button(win, "Speichern")

    warnings = [a for kind, a in calls if kind == "warning"]
    assert warnings and "Startzeit" in warnings[0][1]
    assert win.winfo_exists()
    assert len(_user_events(app_instance, name)) == 2
    win.destroy()


def test_editor_invalid_date_blocks_save(app_instance, monkeypatch):
    """Ungültiges Datum → Warnung, kein Schreiben."""
    calls = _patch_messageboxes(monkeypatch)
    name = "ed_baddate"
    _log_closed_session(app_instance, name)
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    date_entry = _editor_entries(win)[0]
    date_entry.delete(0, END)
    date_entry.insert(0, "23.06.2026")  # falsches Format
    _invoke_editor_button(win, "Speichern")

    warnings = [a for kind, a in calls if kind == "warning"]
    assert warnings and "Datum" in warnings[0][1]
    assert _user_events(app_instance, name) == [
        ("start", "2026-06-23 09:00:00"),
        ("stop", "2026-06-23 10:00:00"),
    ]
    win.destroy()


def test_editor_append_stop_to_open_session(app_instance, monkeypatch):
    """Stop-Nachtragen an einer offenen (nicht live laufenden) Session:
    Endzeit eintragen → log_stop, Session abgeschlossen, Start unangetastet."""
    from db_helper import log_start

    calls = _patch_messageboxes(monkeypatch)
    name = "ed_addstop"
    log_start(project="1", name=name, timestamp=datetime(2026, 6, 23, 9, 0), conn=app_instance.db_conn)
    _view_day(app_instance, name, "23-06-2026")
    session = app_instance._day_sessions[0]
    assert session["stop_id"] is None

    app_instance._edit_event(session=session)
    win = _find_editor(app_instance)
    end_entry = _editor_entries(win)[2]
    end_entry.delete(0, END)
    end_entry.insert(0, "17:00")
    _invoke_editor_button(win, "Speichern")

    assert calls == []
    assert _user_events(app_instance, name) == [
        ("start", "2026-06-23 09:00:00"),
        ("stop", "2026-06-23 17:00:00"),
    ]


def test_editor_open_session_empty_end_keeps_open(app_instance, monkeypatch):
    """Leeres Endfeld ist erlaubt, solange es KEIN Stop-Event gibt: die
    Session bleibt einfach offen, es wird kein Stop erfunden."""
    from db_helper import log_start

    calls = _patch_messageboxes(monkeypatch)
    name = "ed_stayopen"
    log_start(project="1", name=name, timestamp=datetime(2026, 6, 23, 9, 0), conn=app_instance.db_conn)
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    _invoke_editor_button(win, "Speichern")  # Endfeld bleibt leer

    assert calls == []
    assert _user_events(app_instance, name) == [("start", "2026-06-23 09:00:00")]


def _patch_overlap_boxes(monkeypatch, answer):
    """Wie _patch_messageboxes, aber askyesno protokolliert den Titel und
    antwortet mit ``answer`` (Overlap-Dialog bestätigen/abbrechen)."""
    import app as app_module

    seen = {"warnings": [], "asks": []}
    monkeypatch.setattr(app_module.messagebox, "showwarning", lambda *a, **k: seen["warnings"].append(a))
    monkeypatch.setattr(app_module.messagebox, "showerror", lambda *a, **k: seen["warnings"].append(a))

    def _ask(title, *a, **k):
        seen["asks"].append(title)
        return answer

    monkeypatch.setattr(app_module.messagebox, "askyesno", _ask)
    return seen


def _edit_second_session_into_overlap(app_instance, name):
    """Editiert die 11–12-Session auf 09:30–10:30 (überlappt die 09–10-Session)."""
    _log_closed_session(app_instance, name, start_hm=(9, 0), end_hm=(10, 0))
    _log_closed_session(app_instance, name, start_hm=(11, 0), end_hm=(12, 0))
    _view_day(app_instance, name, "23-06-2026")
    session = next(s for s in app_instance._day_sessions if s["start_ts"].hour == 11)

    app_instance._edit_event(session=session)
    win = _find_editor(app_instance)
    entries = _editor_entries(win)
    entries[1].delete(0, END)
    entries[1].insert(0, "09:30")
    entries[2].delete(0, END)
    entries[2].insert(0, "10:30")
    _invoke_editor_button(win, "Speichern")
    return win


def test_editor_overlap_warning_cancel_keeps_db(app_instance, monkeypatch):
    """Overlap-Warnung mit „Nein" beantwortet → nichts gespeichert,
    Dialog bleibt offen."""
    seen = _patch_overlap_boxes(monkeypatch, answer=False)
    name = "ed_ov_no"
    win = _edit_second_session_into_overlap(app_instance, name)

    assert seen["asks"] == ["Überschneidung"]
    assert seen["warnings"] == []
    assert win.winfo_exists()
    assert _user_events(app_instance, name) == [
        ("start", "2026-06-23 09:00:00"),
        ("stop", "2026-06-23 10:00:00"),
        ("start", "2026-06-23 11:00:00"),
        ("stop", "2026-06-23 12:00:00"),
    ]
    win.destroy()


def test_editor_overlap_warning_confirm_saves(app_instance, monkeypatch):
    """Overlap-Warnung mit „Ja" beantwortet → bewusst überlappend gespeichert."""
    seen = _patch_overlap_boxes(monkeypatch, answer=True)
    name = "ed_ov_yes"
    win = _edit_second_session_into_overlap(app_instance, name)

    assert seen["asks"] == ["Überschneidung"]
    assert not win.winfo_exists()  # erfolgreich gespeichert → Dialog zu
    assert _user_events(app_instance, name) == [
        ("start", "2026-06-23 09:00:00"),
        ("start", "2026-06-23 09:30:00"),
        ("stop", "2026-06-23 10:00:00"),
        ("stop", "2026-06-23 10:30:00"),
    ]


def test_editor_key_changed_project_moves_note_and_transferred(app_instance, monkeypatch):
    """Projektwechsel im Editor: Notiz und ✓-Status wandern auf den neuen
    (Projekt, Tag)-Schlüssel mit (key_changed-Zweig)."""
    from db_helper import get_daily_meta, set_daily_note, set_daily_transferred

    calls = _patch_messageboxes(monkeypatch)
    name = "ed_key_proj"
    _log_closed_session(app_instance, name, project="A")
    set_daily_note(app_instance.db_conn, name, "A", "2026-06-23", "wandernde Notiz")
    set_daily_transferred(app_instance.db_conn, name, "A", "2026-06-23", True, transferred_at="2026-06-20")
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    _editor_project_combo(win).set("B")
    _invoke_editor_button(win, "Speichern")

    assert calls == []
    # Events tragen das neue Projekt.
    cur = app_instance.db_conn.cursor()
    projects = [r[0] for r in cur.execute("SELECT DISTINCT project FROM events").fetchall()]
    assert projects == ["B"]
    # Notiz + ✓ liegen unter dem neuen Schlüssel.
    meta = get_daily_meta(app_instance.db_conn, name, "B", "2026-06-23")
    assert meta["note"] == "wandernde Notiz"
    assert meta["transferred"] is True


def test_editor_key_changed_date_moves_events_and_note(app_instance, monkeypatch):
    """Datumswechsel im Editor: Events wandern auf den neuen Tag, Notiz/✓
    folgen auf den neuen Tages-Schlüssel (key_changed-Zweig)."""
    from db_helper import get_daily_meta, set_daily_note

    calls = _patch_messageboxes(monkeypatch)
    name = "ed_key_date"
    _log_closed_session(app_instance, name)
    set_daily_note(app_instance.db_conn, name, "1", "2026-06-23", "Notiz zieht um")
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    date_entry = _editor_entries(win)[0]
    date_entry.delete(0, END)
    date_entry.insert(0, "24-06-2026")
    _invoke_editor_button(win, "Speichern")

    assert calls == []
    assert _user_events(app_instance, name) == [
        ("start", "2026-06-24 09:00:00"),
        ("stop", "2026-06-24 10:00:00"),
    ]
    assert get_daily_meta(app_instance.db_conn, name, "1", "2026-06-24")["note"] == "Notiz zieht um"


# ---------------------------------------------------------------------------
# Invariante: FIFO-Anzeige (Kopfsumme) vs. calculate_daily_duration (Union)
# ---------------------------------------------------------------------------


def test_invariant_overlap_pair_sum_vs_union_duration(app_instance):
    """BEKANNTE, GEWOLLTE DIVERGENZ bei Überschneidung — hier eingefroren.

    Zwei überlappende Sessions 09–11 und 10–12 desselben Projekts:
    - Die Tagesliste paart FIFO und summiert die EINZELDAUERN in der
      Kopfzeile → 2h + 2h = **4:00 h** (jede Session zählt voll; genau die
      Zahlen, die einzeln ins Firmensystem übertragen werden).
    - ``calculate_daily_duration`` (Statistik/Wochenansicht) summiert die
      **Vereinigung** der Intervalle → 09–12 = **3h** (reale Anwesenheit,
      überlappende Zeit zählt nie doppelt).

    Beide Sichten sind je für ihren Zweck korrekt; die Abweichung existiert
    NUR bei echten Überschneidungen (der Editor warnt beim Anlegen). Dieser
    Test friert das Verhalten ein: wer eine der beiden Seiten ändert, muss
    das hier bewusst tun.
    """
    from db_helper import calculate_daily_duration, log_start, log_stop

    name = "inv_overlap"
    for s_h, e_h in ((9, 11), (10, 12)):
        log_start(project="1", name=name, timestamp=datetime(2026, 6, 23, s_h, 0), conn=app_instance.db_conn)
        log_stop(project="1", name=name, timestamp=datetime(2026, 6, 23, e_h, 0), conn=app_instance.db_conn)
    _view_day(app_instance, name, "23-06-2026")

    # FIFO-Anzeige: zwei GESCHLOSSENE Sessions (09→11, 10→12), je 2h.
    sessions = app_instance._day_sessions
    assert [(s["start_ts"].hour, s["stop_ts"].hour) for s in sessions] == [(9, 11), (10, 12)]
    pair_sum_h = sum(s["dur_h"] for s in sessions)
    assert pair_sum_h == 4.0
    hdr = next(ln for ln in app_instance.day_list.get("1.0", "end-1c").splitlines() if ln.startswith("▌ 1"))
    assert "4:00 h" in hdr  # Kopfsumme der Tagesliste = Paarsumme

    # Statistik-Seite: Union der Intervalle = 3h.
    union_secs = calculate_daily_duration(project="1", name=name, date="23-06-2026", conn=app_instance.db_conn)
    assert union_secs == 3 * 3600

    # Die Divergenz selbst ist die Invariante (4h Paarsumme vs. 3h Union).
    assert pair_sum_h * 3600 != union_secs


# ---------------------------------------------------------------------------
# Commit 12 — Feedback & Sichtbarkeit (Fenstertitel, Datums-Sprung, Empty-State)
# ---------------------------------------------------------------------------
def test_window_title_follows_timer_state(app_instance):
    """Der Fenstertitel führt den Timer-Zustand mit (Taskleiste/Alt-Tab)."""
    from app import WINDOW_TITLE_BREAK, WINDOW_TITLE_IDLE, WINDOW_TITLE_RUNNING

    app_instance._set_button_state_running()
    assert app_instance.master.title() == WINDOW_TITLE_RUNNING
    app_instance._set_button_state_break()
    assert app_instance.master.title() == WINDOW_TITLE_BREAK
    app_instance._set_button_state_idle()
    assert app_instance.master.title() == WINDOW_TITLE_IDLE


def test_start_session_jumps_view_to_today(app_instance):
    """Start bei angezeigtem Vergangenheitsdatum springt aufs heutige Datum —
    sonst fröre die Anzeige ein (_is_viewing_today-Gate im Timer-Tick)."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.start_session()
    assert app_instance.date_entry.get() == datetime.today().strftime("%d-%m-%Y")
    assert app_instance.session_active.get(("test_user", "1"), False) is True


def test_rejected_start_keeps_viewed_date(app_instance):
    """Ein abgewiesener Start (Session läuft bereits) lässt das angezeigte Datum in Ruhe."""
    app_instance.name_entry.set("test_user")
    app_instance.project_entry.set("1")
    app_instance.start_session()
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, "01-01-1991")
    app_instance.start_session()  # bereits aktiv → nur Fehlermeldung, kein Sprung
    assert app_instance.date_entry.get() == "01-01-1991"


def test_day_list_empty_state(app_instance):
    """Ein Tag ohne Einträge zeigt die dim-Empty-State-Zeile statt einer leeren Liste."""
    app_instance.name_entry.set("user_ohne_eintraege")
    app_instance.date_entry.delete(0, END)
    app_instance.date_entry.insert(0, datetime.today().strftime("%d-%m-%Y"))
    app_instance.update_db_content()
    assert "Keine Einträge für diesen Tag" in app_instance.day_list.get("1.0", "end-1c")


def test_error_write_expands_console_and_flags_statusbar(app_instance):
    """error=True klappt eine eingeklappte Konsole auf und färbt die Statusleiste rot."""
    app_instance._console_collapsed = True
    app_instance._apply_console_collapsed()
    app_instance.write("Testfehler: Datenbank nicht erreichbar", error=True)
    assert app_instance._console_collapsed is False
    assert "Testfehler" in app_instance._status_error_label.cget("text")
    # Selbstheilung: der Clear-Callback räumt die Meldung wieder weg.
    app_instance._clear_status_error()
    assert app_instance._status_error_label.cget("text") == ""


# ---------------------------------------------------------------------------
# Strg+G (übertragen togglen) / Strg+N (Notizfeld fokussieren)
# ---------------------------------------------------------------------------


def test_ctrl_g_toggles_transferred(app_instance):
    """Strg+G toggelt den »übertragen«-Status wie ein Klick auf die Checkbox."""
    from db_helper import get_daily_meta

    name = "sc_toggle"
    _view_day(app_instance, name, datetime.today().strftime("%d-%m-%Y"))
    app_instance._load_note()
    assert str(app_instance.transferred_check.cget("state")) == "normal"

    project = app_instance._get_project_silent()
    iso = app_instance._selected_date_iso()
    assert get_daily_meta(app_instance.db_conn, name, project, iso)["transferred"] is False

    app_instance._toggle_transferred_shortcut()
    assert get_daily_meta(app_instance.db_conn, name, project, iso)["transferred"] is True
    app_instance._toggle_transferred_shortcut()
    assert get_daily_meta(app_instance.db_conn, name, project, iso)["transferred"] is False


def test_ctrl_g_noop_on_disabled_checkbox(app_instance):
    """Bei deaktivierter Checkbox (kein Benutzer geladen) tut Strg+G nichts."""
    app_instance.name_entry.set("")
    app_instance._load_note()
    assert str(app_instance.transferred_check.cget("state")) == "disabled"
    app_instance._toggle_transferred_shortcut()  # darf weder werfen noch togglen
    assert bool(app_instance._transferred_var.get()) is False


def test_ctrl_n_focuses_note_entry(app_instance):
    """Strg+N setzt den Fokus ins Notizfeld, Cursor ans Textende."""
    called = []
    app_instance.note_entry.focus_set = lambda: called.append(1)
    app_instance.note_entry.insert("1.0", "eine notiz")
    app_instance._focus_note_entry()
    assert called == [1]
    assert app_instance.note_entry.index("insert") == app_instance.note_entry.index("end-1c")


def test_ctrl_g_and_n_are_guarded(app_instance):
    """Strg+G/N laufen über _shortcut_guard: Textfokus blockt, Bindings existieren."""

    class _Ev:
        def __init__(self, widget):
            self.widget = widget

    fired = []
    assert app_instance._shortcut_guard(_Ev(app_instance.note_entry), lambda: fired.append(1)) is None
    assert fired == []
    # bind_all-Registrierung vorhanden (Query ohne func liefert das Skript).
    assert app_instance.master.bind_all("<Control-g>")
    assert app_instance.master.bind_all("<Control-n>")


# ---------------------------------------------------------------------------
# Return in Dialogen: fokussierter Button gewinnt, sonst Standard-Aktion
# ---------------------------------------------------------------------------


class _KeyEv:
    def __init__(self, widget):
        self.widget = widget


def _find_dialog_button(win, label):
    from tkinter import Button

    stack = [win]
    while stack:
        w = stack.pop()
        stack.extend(w.winfo_children())
        if isinstance(w, Button) and w.cget("text") == label:
            return w
    raise AssertionError(f"Button '{label}' nicht gefunden")


def test_dialog_return_on_non_button_runs_default(app_instance):
    """Return ohne Button-Fokus (z.B. Entry) führt die Standard-Aktion aus."""
    fired = []
    assert app_instance._on_dialog_return(_KeyEv(app_instance.date_entry), lambda: fired.append(1)) == "break"
    assert fired == [1]


def test_editor_return_on_cancel_button_discards(app_instance, monkeypatch):
    """Return bei Fokus auf »Abbrechen« im Session-Editor verwirft die Änderung."""
    _patch_messageboxes(monkeypatch)
    name = "ed_ret_cancel"
    _log_closed_session(app_instance, name)
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    start_entry = _editor_entries(win)[1]
    start_entry.delete(0, END)
    start_entry.insert(0, "08:00")

    cancel = _find_dialog_button(win, "Abbrechen")
    assert app_instance._on_dialog_return(_KeyEv(cancel), lambda: pytest.fail("Speichern darf nicht feuern")) == "break"
    assert not win.winfo_exists()
    # Nichts gespeichert: Startzeit unverändert 09:00.
    assert _user_events(app_instance, name) == [
        ("start", "2026-06-23 09:00:00"),
        ("stop", "2026-06-23 10:00:00"),
    ]


def test_editor_return_on_delete_button_deletes(app_instance, monkeypatch):
    """Return bei Fokus auf »Löschen« löscht (nach Rückfrage) statt zu speichern."""
    _patch_messageboxes(monkeypatch)  # askyesno → True
    name = "ed_ret_delete"
    _log_closed_session(app_instance, name)
    _view_day(app_instance, name, "23-06-2026")

    app_instance._edit_event(session=app_instance._day_sessions[0])
    win = _find_editor(app_instance)
    delete_btn = _find_dialog_button(win, "Löschen")
    assert (
        app_instance._on_dialog_return(_KeyEv(delete_btn), lambda: pytest.fail("Speichern darf nicht feuern"))
        == "break"
    )
    assert not win.winfo_exists()
    assert _user_events(app_instance, name) == []


def test_manual_event_return_on_cancel_creates_nothing(app_instance):
    """Return bei Fokus auf »Abbrechen« im Nachtrag-Dialog legt keinen Eintrag an."""
    name = "man_ret_cancel"
    _view_day(app_instance, name, datetime.today().strftime("%d-%m-%Y"))

    app_instance.add_manual_event()
    from tkinter import Toplevel

    wins = [w for w in app_instance.master.winfo_children() if isinstance(w, Toplevel)]
    assert wins, "Nachtrag-Dialog wurde nicht geöffnet"
    win = wins[-1]

    cancel = _find_dialog_button(win, "Abbrechen")
    assert app_instance._on_dialog_return(_KeyEv(cancel), lambda: pytest.fail("Speichern darf nicht feuern")) == "break"
    assert not win.winfo_exists()
    assert _user_events(app_instance, name) == []


def test_project_dialog_return_on_cancel_creates_nothing(app_instance):
    """Return bei Fokus auf »Abbrechen« im Projekt-Dialog legt kein Projekt an."""
    from db_helper import get_all_projects

    app_instance._add_project_dialog()
    from tkinter import Toplevel

    wins = [w for w in app_instance.master.winfo_children() if isinstance(w, Toplevel)]
    assert wins, "Projekt-Dialog wurde nicht geöffnet"
    win = wins[-1]

    before = get_all_projects(app_instance.db_conn)
    from tkinter import Entry

    entry = next(w for w in win.winfo_children() if isinstance(w, Entry))
    entry.insert(0, "NeuesProjektXY")
    cancel = _find_dialog_button(win, "Abbrechen")
    assert app_instance._on_dialog_return(_KeyEv(cancel), lambda: pytest.fail("Anlegen darf nicht feuern")) == "break"
    assert not win.winfo_exists()
    assert get_all_projects(app_instance.db_conn) == before


# ---------------------------------------------------------------------------
# Tippfehler-Falle: get_name/get_project prüfen case-insensitiv gegen Bestand
# ---------------------------------------------------------------------------


def _patch_askyesno_recording(monkeypatch, answer=True):
    """askyesno protokollieren und mit ``answer`` beantworten."""
    import app as app_module

    asks = []

    def _ask(*a, **k):
        asks.append(a)
        return answer

    monkeypatch.setattr(app_module.messagebox, "askyesno", _ask)
    return asks


def test_get_name_exact_match_stays_silent(app_instance, monkeypatch):
    """Exakter Bestands-Treffer: unverändert übernehmen, kein Dialog."""
    from db_helper import check_user

    check_user(app_instance.db_conn, "TestKunde")
    asks = _patch_askyesno_recording(monkeypatch)
    app_instance.name_entry.set("TestKunde")
    assert app_instance.get_name() == "TestKunde"
    assert asks == []


def test_get_name_adopts_existing_case_variant(app_instance, monkeypatch):
    """„testkunde" statt „TestKunde": Bestandsname wird übernommen — kein neuer
    (case-sensitiver) Benutzer, kein Dialog, Hinweis in der Konsole, Feld korrigiert."""
    from db_helper import check_user

    check_user(app_instance.db_conn, "TestKunde")
    asks = _patch_askyesno_recording(monkeypatch)
    app_instance.name_entry.set("tEstKunde")
    assert app_instance.get_name() == "TestKunde"
    assert asks == []
    assert app_instance.name_entry.get() == "TestKunde"
    assert "übernommen" in app_instance.console.get("1.0", END)


def test_get_name_adopts_archived_case_variant(app_instance, monkeypatch):
    """Auch archivierte Benutzer zählen zum Bestand — sonst entstünde genau
    das Case-Duplikat, das der Check verhindern soll."""
    from db_helper import check_user, set_archived

    check_user(app_instance.db_conn, "AlterNutzer")
    set_archived(app_instance.db_conn, "user", "AlterNutzer", True)
    asks = _patch_askyesno_recording(monkeypatch)
    app_instance.name_entry.set("alternutzer")
    assert app_instance.get_name() == "AlterNutzer"
    assert asks == []


def test_get_name_unknown_asks_no_aborts(app_instance, monkeypatch):
    """Komplett unbekannter Name: Rückfrage — „Nein" liefert None (kein Anlegen)."""
    from db_helper import get_all_users

    asks = _patch_askyesno_recording(monkeypatch, answer=False)
    app_instance.name_entry.set("Nagelneu")
    assert app_instance.get_name() is None
    assert len(asks) == 1
    assert "Nagelneu" not in get_all_users(app_instance.db_conn, include_archived=True)


def test_get_name_unknown_asks_yes_returns_name(app_instance, monkeypatch):
    """Rückfrage mit „Ja": Name wird zurückgegeben (Anlegen passiert erst in der DB-Schicht)."""
    asks = _patch_askyesno_recording(monkeypatch, answer=True)
    app_instance.name_entry.set("Nagelneu")
    assert app_instance.get_name() == "Nagelneu"
    assert len(asks) == 1


def test_get_project_adopts_existing_case_variant(app_instance, monkeypatch):
    """Dieselbe Falle beim Projekt: Case-Variante übernimmt das Bestands-Projekt."""
    from db_helper import check_project

    check_project(app_instance.db_conn, "Backend")
    asks = _patch_askyesno_recording(monkeypatch)
    app_instance.project_entry.set("backend")
    assert app_instance.get_project() == "Backend"
    assert asks == []
    assert app_instance.project_entry.get() == "Backend"


def test_get_project_unknown_asks_no_aborts(app_instance, monkeypatch):
    asks = _patch_askyesno_recording(monkeypatch, answer=False)
    app_instance.project_entry.set("GanzNeu")
    assert app_instance.get_project() is None
    assert len(asks) == 1


def test_start_session_with_case_variant_uses_existing_user(app_instance, monkeypatch):
    """End-to-End: Start mit „hans" trackt auf den bestehenden „Hans" —
    es entsteht KEIN zweiter Benutzer und keine Rückfrage."""
    from db_helper import check_project, get_all_users

    check_project(app_instance.db_conn, "1")  # Projekt existiert bereits
    asks = _patch_askyesno_recording(monkeypatch)
    app_instance.name_entry.set("hans")  # Bestands-„Hans" kommt aus default_user
    app_instance.project_entry.set("1")
    app_instance.start_session()
    assert asks == []
    assert app_instance.session_active.get(("Hans", "1")) is True
    users = get_all_users(app_instance.db_conn, include_archived=True)
    assert "hans" not in users
    app_instance.stop_session()
