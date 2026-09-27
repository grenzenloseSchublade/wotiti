import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from db_helper import (
    calculate_duration,
    check_project,
    check_user,
    create_connection,
    create_main_table,
    delete_event,
    delete_session,
    fetch_day_events,
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


def test_pair_sessions_lifo_overlap():
    """LIFO-Helper: jüngster offener Start bindet den Stop (nested 09-12, 10-11)."""
    from datetime import datetime as _dt

    from db_helper import pair_sessions_lifo

    evs = [
        ("start", _dt(2026, 6, 23, 9, 0)),
        ("start", _dt(2026, 6, 23, 10, 0)),
        ("stop", _dt(2026, 6, 23, 11, 0)),
        ("stop", _dt(2026, 6, 23, 12, 0)),
    ]
    pairs = set(pair_sessions_lifo(evs))
    assert pairs == {
        (_dt(2026, 6, 23, 10, 0), _dt(2026, 6, 23, 11, 0)),
        (_dt(2026, 6, 23, 9, 0), _dt(2026, 6, 23, 12, 0)),
    }


def test_pair_sessions_lifo_back_to_back_no_zero_pair():
    """Stop A == Start B (Rücken-an-Rücken) → zwei normale Sessions.

    Regression: Der frühere Tiebreak (Start vor Stop bei Gleichstand) ließ den
    Stop um 12:00 den GLEICHZEITIGEN Start binden → 0h-Paar plus Mega-Session
    09-13 — im Widerspruch zur FIFO-Tagesliste.
    """
    from datetime import datetime as _dt

    from db_helper import pair_sessions_lifo

    evs = [
        ("start", _dt(2026, 6, 23, 9, 0)),
        ("stop", _dt(2026, 6, 23, 12, 0)),
        ("start", _dt(2026, 6, 23, 12, 0)),
        ("stop", _dt(2026, 6, 23, 13, 0)),
    ]
    pairs = sorted(pair_sessions_lifo(evs))
    assert pairs == [
        (_dt(2026, 6, 23, 9, 0), _dt(2026, 6, 23, 12, 0)),
        (_dt(2026, 6, 23, 12, 0), _dt(2026, 6, 23, 13, 0)),
    ]


def test_pair_sessions_lifo_lone_equal_ts_pair_stays_zero_duration():
    """Einzelnes Start/Stop-Paar mit identischem Zeitstempel bleibt 0h-Paar.

    Ohne älteren offenen Start bindet der Stop den gleichzeitigen Start —
    keine zwei Waisen (verwaister Stop + ewig „offener" Start).
    """
    from datetime import datetime as _dt

    from db_helper import pair_sessions_lifo

    ts = _dt(2026, 6, 23, 12, 0)
    for evs in ([("start", ts), ("stop", ts)], [("stop", ts), ("start", ts)]):
        assert list(pair_sessions_lifo(evs)) == [(ts, ts)]


def test_close_stale_sessions_back_to_back_closes_younger_start(db_conn):
    """Rücken-an-Rücken + Absturz: Der JÜNGERE Start ist der offene.

    start 09, stop 12, start 12 (App stirbt) → der Stop um 12:00 gehört zur
    09-12-Session; close_stale_sessions muss den 12:00-Start schließen (Stop
    bei 12:00), nicht den 09:00-Start — sonst wären die 3 h verloren.
    """
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, close_stale_sessions

    log_start(project="p", name="btb_user", timestamp=_dt(2026, 6, 23, 9, 0), conn=db_conn)
    log_stop(project="p", name="btb_user", timestamp=_dt(2026, 6, 23, 12, 0), conn=db_conn)
    log_start(project="p", name="btb_user", timestamp=_dt(2026, 6, 23, 12, 0), conn=db_conn)

    assert close_stale_sessions(db_conn) == 1
    stops = [
        r[0] for r in db_conn.execute("SELECT timestamp FROM events WHERE event_type = 'stop' ORDER BY id").fetchall()
    ]
    assert stops == ["2026-06-23 12:00:00", "2026-06-23 12:00:00"]
    assert calculate_daily_duration(project="p", name="btb_user", date="23-06-2026", conn=db_conn) == 3 * 3600


def test_log_stop_dst_fold_clamped_to_start(db_conn, monkeypatch):
    """Zeitumstellung (Uhr zurück): LIVE-Stop (now()-Pfad) naiv VOR dem
    offenen Start → geclampt.

    Ohne Clamp würde der Stop beim Paaren zur Waise und die Session bliebe
    scheinbar offen (Zeit via close_stale_sessions endgültig weg). Der Clamp
    greift NUR ohne expliziten Zeitstempel — daher wird hier now() gepatcht.
    """
    from datetime import datetime as _dt

    import db_helper
    from db_helper import pair_sessions_lifo

    log_start(project="p", name="dst_user", timestamp=_dt(2026, 10, 25, 2, 45), conn=db_conn)

    class _FoldNow(_dt):
        """now() liefert die bereits zurückgestellte Uhr (02:15 im Fold)."""

        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 25, 2, 15)

    monkeypatch.setattr(db_helper, "datetime", _FoldNow)
    assert log_stop(project="p", name="dst_user", conn=db_conn) is True  # Live-Stop: kein Timestamp

    rows = db_conn.execute("SELECT event_type, timestamp FROM events ORDER BY id").fetchall()
    assert rows == [("start", "2026-10-25 02:45:00"), ("stop", "2026-10-25 02:45:00")]
    ts = _dt(2026, 10, 25, 2, 45)
    assert list(pair_sessions_lifo([("start", ts), ("stop", ts)])) == [(ts, ts)]


def test_log_stop_explicit_backdated_within_hour_not_clamped(db_conn):
    """Editor-Nachtrag: expliziter Stop < 1 h VOR dem offenen Start bleibt exakt.

    13:30 zu einem offenen Start 14:00 gehört oft zu einem GANZ ANDEREN,
    vergessenen Start — er darf nie still auf 14:00 hochgeclampt werden
    (Regression: FIFO paarte sonst Phantom-Arbeitszeit ins Firmensystem).
    """
    from datetime import datetime as _dt

    log_start(project="p", name="edit_user", timestamp=_dt(2026, 6, 23, 14, 0), conn=db_conn)
    assert log_stop(project="p", name="edit_user", timestamp=_dt(2026, 6, 23, 13, 30), conn=db_conn) is True

    row = db_conn.execute("SELECT timestamp FROM events WHERE event_type = 'stop'").fetchone()
    assert row == ("2026-06-23 13:30:00",)


def test_log_stop_far_before_start_not_clamped(db_conn):
    """Bewusst rückdatierter Stop (> 1 h vor dem offenen Start) bleibt unberührt."""
    from datetime import datetime as _dt

    log_start(project="p", name="manual_user", timestamp=_dt(2026, 6, 23, 9, 0), conn=db_conn)
    log_stop(project="p", name="manual_user", timestamp=_dt(2026, 6, 22, 17, 0), conn=db_conn)

    row = db_conn.execute("SELECT timestamp FROM events WHERE event_type = 'stop'").fetchone()
    assert row == ("2026-06-22 17:00:00",)


def test_log_break_stop_invalid_started_at_returns_false(db_conn):
    """Hand-editierter ``started_at`` → ValueError wird gefangen, kein Crash."""
    from db_helper import create_break_events_table, log_break_stop

    create_break_events_table(db_conn)
    user_id = check_user(db_conn, "brk_user")
    db_conn.execute(
        "INSERT INTO break_events (user_id, project, break_kind, started_at, is_auto, source)"
        " VALUES (?, 'p', 'manual', 'kaputt', 0, 'manual_break')",
        (user_id,),
    )
    db_conn.commit()
    assert log_break_stop(project="p", name="brk_user", conn=db_conn) is False


def test_merge_intervals_seconds_union():
    """merge_intervals_seconds zählt überlappende Intervalle nur einmal (Union)."""
    from datetime import datetime as _dt

    from db_helper import merge_intervals_seconds

    ivs = [
        (_dt(2026, 6, 23, 9, 0), _dt(2026, 6, 23, 12, 0)),  # 3h
        (_dt(2026, 6, 23, 10, 0), _dt(2026, 6, 23, 11, 0)),  # genested
        (_dt(2026, 6, 23, 13, 0), _dt(2026, 6, 23, 14, 0)),  # disjunkt 1h
    ]
    assert merge_intervals_seconds(ivs) == 4 * 3600  # Union: 3h + 1h


def test_daily_duration_union_on_overlap(db_conn):
    """Überschneidende Sessions zählen als Vereinigung, nicht doppelt.

    09-11 (2h) + 10-12 (2h) überlappen 10-11 → reale Arbeitszeit 09-12 = 3h.
    """
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 9, 0), conn=db_conn)
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 10, 0), conn=db_conn)
    log_stop(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 11, 0), conn=db_conn)
    log_stop(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 12, 0), conn=db_conn)

    secs = calculate_daily_duration(project="P", name="test_user", date="23-06-2026", conn=db_conn)
    assert secs == 3 * 3600


def test_daily_duration_orphan_no_inflation(db_conn):
    """Regression >22h: ein verwaister Start darf keine Folgetage aufblähen.

    Vergessener Start am 20.06 (kein Stopp) + zwei normale 8h-Tage → 0/8/8h,
    nicht 15/32/17h (FIFO-Cross-Day-Mega-Paar).
    """
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 20, 9, 0), conn=db_conn)  # Waise
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 21, 9, 0), conn=db_conn)
    log_stop(project="P", name="test_user", timestamp=_dt(2026, 6, 21, 17, 0), conn=db_conn)
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 22, 9, 0), conn=db_conn)
    log_stop(project="P", name="test_user", timestamp=_dt(2026, 6, 22, 17, 0), conn=db_conn)

    def d(iso):
        return calculate_daily_duration(project="P", name="test_user", date=iso, conn=db_conn)

    assert d("20-06-2026") == 0
    assert d("21-06-2026") == 8 * 3600
    assert d("22-06-2026") == 8 * 3600


def test_daily_duration_never_exceeds_24h(db_conn):
    """Invariante: eine Tages-Dauer kann strukturell nie > 24h sein."""
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    # Stark überlappende Sessions am selben Tag.
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 0, 0), conn=db_conn)
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 0, 30), conn=db_conn)
    log_stop(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 23, 30), conn=db_conn)
    log_stop(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 23, 59), conn=db_conn)

    secs = calculate_daily_duration(project="P", name="test_user", date="23-06-2026", conn=db_conn)
    assert secs <= 24 * 3600


def test_close_stale_sessions_interleaved_double_open(db_conn):
    """close_stale schließt auch einen verschachtelten Doppel-Start (start,start,stop).

    Der frühere NOT-EXISTS-Detektor übersah das (beide Starts haben einen
    späteren Stopp). LIFO erkennt den unpaarigen Start und schließt ihn.
    """
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, close_stale_sessions, create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 9, 0), conn=db_conn)
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 10, 0), conn=db_conn)
    log_stop(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 11, 0), conn=db_conn)

    assert close_stale_sessions(db_conn) == 1
    # Erneuter Lauf ist idempotent.
    assert close_stale_sessions(db_conn) == 0
    # Danach keine offene Session mehr → Dauer = reale 1h (10-11), Waise = 0.
    assert calculate_daily_duration(project="P", name="test_user", date="23-06-2026", conn=db_conn) == 3600


def test_close_stale_sessions_single_orphan(db_conn):
    """Klassischer Fall: ein Start ohne Stopp wird mit Null-Dauer geschlossen."""
    from datetime import datetime as _dt

    from db_helper import close_stale_sessions, create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 9, 0), conn=db_conn)
    assert close_stale_sessions(db_conn) == 1
    assert close_stale_sessions(db_conn) == 0


def test_write_read_clear_heartbeat(db_conn):
    """write_heartbeat persistiert genau einen last_seen; Überschreiben und Löschen."""
    from datetime import datetime as _dt

    from db_helper import clear_heartbeat, read_heartbeat, write_heartbeat

    assert read_heartbeat(db_conn) is None
    assert write_heartbeat(db_conn, _dt(2026, 6, 23, 10, 0)) is True
    assert read_heartbeat(db_conn) == _dt(2026, 6, 23, 10, 0)
    assert write_heartbeat(db_conn, _dt(2026, 6, 23, 10, 1)) is True
    assert read_heartbeat(db_conn) == _dt(2026, 6, 23, 10, 1)
    row_count = db_conn.execute("SELECT COUNT(*) FROM app_state WHERE key = 'last_seen'").fetchone()[0]
    assert row_count == 1
    assert clear_heartbeat(db_conn) is True
    assert read_heartbeat(db_conn) is None


def test_close_stale_sessions_uses_heartbeat(db_conn):
    """Verwaister Start endet auf dem letzten Heartbeat statt mit Null-Dauer."""
    from datetime import datetime as _dt

    from db_helper import (
        calculate_daily_duration,
        close_stale_sessions,
        read_heartbeat,
        write_heartbeat,
    )

    check_user(db_conn, "test_user")
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 10, 0), conn=db_conn)
    write_heartbeat(db_conn, _dt(2026, 6, 23, 12, 0))

    assert close_stale_sessions(db_conn) == 1
    # Stop-Event liegt auf dem Heartbeat, date-Spalte konsistent dazu.
    row = db_conn.execute("SELECT timestamp, date FROM events WHERE event_type = 'stop'").fetchone()
    assert row == ("2026-06-23 12:00:00", "23-06-2026")
    assert calculate_daily_duration(project="P", name="test_user", date="23-06-2026", conn=db_conn) == 7200
    # Heartbeat ist verbraucht — ein zweiter Lauf schließt nichts erneut.
    assert read_heartbeat(db_conn) is None
    assert close_stale_sessions(db_conn) == 0


def test_close_stale_sessions_heartbeat_before_start(db_conn):
    """Heartbeat VOR dem verwaisten Start: Fallback auf Null-Dauer am Start."""
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, close_stale_sessions, write_heartbeat

    check_user(db_conn, "test_user")
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 10, 0), conn=db_conn)
    write_heartbeat(db_conn, _dt(2026, 6, 23, 9, 0))

    assert close_stale_sessions(db_conn) == 1
    row = db_conn.execute("SELECT timestamp FROM events WHERE event_type = 'stop'").fetchone()
    assert row == ("2026-06-23 10:00:00",)
    assert calculate_daily_duration(project="P", name="test_user", date="23-06-2026", conn=db_conn) == 0


def test_stale_sessions_and_heartbeat_on_legacy_db_without_app_state(db_conn):
    """Alt-DB ohne app_state-Tabelle läuft unverändert (Guards, Null-Dauer)."""
    from datetime import datetime as _dt

    from db_helper import close_stale_sessions, read_heartbeat, write_heartbeat

    db_conn.execute("DROP TABLE app_state")
    db_conn.commit()

    assert read_heartbeat(db_conn) is None
    assert write_heartbeat(db_conn, _dt(2026, 6, 23, 12, 0)) is False

    check_user(db_conn, "test_user")
    log_start(project="P", name="test_user", timestamp=_dt(2026, 6, 23, 10, 0), conn=db_conn)
    assert close_stale_sessions(db_conn) == 1
    row = db_conn.execute("SELECT timestamp FROM events WHERE event_type = 'stop'").fetchone()
    assert row == ("2026-06-23 10:00:00",)
    assert close_stale_sessions(db_conn) == 0


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


def test_delete_session_removes_both_events(db_conn):
    """delete_session entfernt Start- und Stop-Event in einem Rutsch."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="proj1", name="test_user", date="01-01-2025", conn=db_conn)
    log_stop(project="proj1", name="test_user", date="01-01-2025", conn=db_conn)
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM events ORDER BY id")
    ids = [r[0] for r in cur.fetchall()]
    cur.close()
    assert len(ids) == 2

    assert delete_session(db_conn, ids[0], ids[1]) is True
    assert get_event_by_id(db_conn, ids[0]) is None
    assert get_event_by_id(db_conn, ids[1]) is None


def test_delete_session_skips_none_ids(db_conn):
    """Eine offene Session (stop_id None) löscht nur das vorhandene Event."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    check_user(db_conn, "test_user")
    log_start(project="proj1", name="test_user", date="01-01-2025", conn=db_conn)
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM events ORDER BY id DESC LIMIT 1")
    start_id = cur.fetchone()[0]
    cur.close()

    assert delete_session(db_conn, start_id, None) is True
    assert get_event_by_id(db_conn, start_id) is None


def test_delete_session_no_ids(db_conn):
    """Ohne gültige IDs gibt delete_session False zurück."""
    from db_helper import create_events_table

    create_events_table(db_conn)
    assert delete_session(db_conn, None, None) is False


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


# ---------------------------------------------------------------------------
# set_daily_transferred_bulk (Tages-/Wochen-Häkchen der Wochenansicht)
# ---------------------------------------------------------------------------


def test_set_daily_transferred_bulk_sets_and_counts(db_conn):
    """Bulk-Setzen markiert alle Paare und liefert die Anzahl geänderter Zeilen."""
    from db_helper import get_daily_meta, set_daily_transferred_bulk

    check_user(db_conn, "u1")
    items = [("A", "2025-06-02"), ("B", "2025-06-02"), ("A", "2025-06-03")]
    changed = set_daily_transferred_bulk(db_conn, "u1", items, True, transferred_at="2025-06-05")
    assert changed == 3
    for project, date_iso in items:
        meta = get_daily_meta(db_conn, "u1", project, date_iso)
        assert meta["transferred"] is True
        assert meta["transferred_at"] == "2025-06-05"


def test_set_daily_transferred_bulk_preserves_existing_transferred_at(db_conn):
    """Bereits übertragene Zeilen behalten ihr ursprüngliches transferred_at."""
    from db_helper import get_daily_meta, set_daily_transferred, set_daily_transferred_bulk

    check_user(db_conn, "u1")
    set_daily_transferred(db_conn, "u1", "A", "2025-06-02", True, transferred_at="2025-06-01")

    items = [("A", "2025-06-02"), ("B", "2025-06-02")]
    changed = set_daily_transferred_bulk(db_conn, "u1", items, True, transferred_at="2025-06-05")
    # Nur B ist neu — A war schon übertragen und zählt nicht als Änderung.
    assert changed == 1
    assert get_daily_meta(db_conn, "u1", "A", "2025-06-02")["transferred_at"] == "2025-06-01"
    assert get_daily_meta(db_conn, "u1", "B", "2025-06-02")["transferred_at"] == "2025-06-05"


def test_set_daily_transferred_bulk_clear_removes_empty_rows(db_conn):
    """Zurücksetzen entfernt Zeilen ohne Notiz (Aufräum-Semantik) und erhält Notizen."""
    from db_helper import get_daily_meta, set_daily_note, set_daily_transferred_bulk

    check_user(db_conn, "u1")
    set_daily_note(db_conn, "u1", "A", "2025-06-02", "wichtige Notiz")
    items = [("A", "2025-06-02"), ("B", "2025-06-02")]
    set_daily_transferred_bulk(db_conn, "u1", items, True, transferred_at="2025-06-05")

    changed = set_daily_transferred_bulk(db_conn, "u1", items, False)
    assert changed == 2
    # A behält die Notiz, ist aber nicht mehr übertragen.
    meta_a = get_daily_meta(db_conn, "u1", "A", "2025-06-02")
    assert meta_a["note"] == "wichtige Notiz"
    assert meta_a["transferred"] is False
    # B war notizlos → Zeile weg (Default-Meta).
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_notes WHERE project = 'B'")
    assert cur.fetchone()[0] == 0


def test_set_daily_transferred_bulk_empty_input(db_conn):
    """Leere Liste bzw. fehlende Verbindung → 0 Änderungen, kein Fehler."""
    from db_helper import set_daily_transferred_bulk

    check_user(db_conn, "u1")
    assert set_daily_transferred_bulk(db_conn, "u1", [], True) == 0
    assert set_daily_transferred_bulk(None, "u1", [("A", "2025-06-02")], True) == 0
    # Leere Projekt-/Datums-Strings im Batch werden übersprungen.
    assert set_daily_transferred_bulk(db_conn, "u1", [("", "2025-06-02"), ("A", "")], True) == 0


# ---------------------------------------------------------------------------
# Timestamp-Fenster der Dauer-/Wochenberechnung (Freeze-Fix-Regression)
# ---------------------------------------------------------------------------


def test_week_hours_ignores_events_outside_window(db_conn):
    """Alte Events (außerhalb des ±1-Tage-Fensters) ändern die Wochensummen nicht."""
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import compute_last_n_days_hours_by_project, log_start, log_stop

    check_user(db_conn, "u1")
    # Alte Historie, 30 Tage vor dem Fenster.
    log_start(project="P", name="u1", timestamp=_dt(2025, 5, 1, 9, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 5, 1, 17, 0), conn=db_conn)
    # Im Fenster: 2 h.
    log_start(project="P", name="u1", timestamp=_dt(2025, 6, 2, 9, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 6, 2, 11, 0), conn=db_conn)

    days = dict(compute_last_n_days_hours_by_project(db_conn, "u1", n=7, end_date=_date(2025, 6, 3)))
    assert abs(days["2025-06-02"]["P"] - 2.0) < 0.01
    assert sum(sum(d.values()) for d in days.values()) == pytest.approx(2.0, abs=0.01)


def test_week_hours_midnight_session_at_window_start(db_conn):
    """Session 23:00 (Vortag des Fensters) → 01:00 (erster Fenstertag) ⇒ 1 h am ersten Tag."""
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import compute_last_n_days_hours_by_project, log_start, log_stop

    check_user(db_conn, "u1")
    # Fenster = 2025-05-28 .. 2025-06-03; Session startet am 27. um 23:00.
    log_start(project="P", name="u1", timestamp=_dt(2025, 5, 27, 23, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 5, 28, 1, 0), conn=db_conn)

    days = dict(compute_last_n_days_hours_by_project(db_conn, "u1", n=7, end_date=_date(2025, 6, 3)))
    assert abs(days["2025-05-28"]["P"] - 1.0) < 0.01


def test_week_hours_midnight_session_at_window_end(db_conn):
    """Session 23:00 (letzter Fenstertag) → 01:00 (Folgetag) ⇒ 1 h am letzten Tag."""
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import compute_last_n_days_hours_by_project, log_start, log_stop

    check_user(db_conn, "u1")
    log_start(project="P", name="u1", timestamp=_dt(2025, 6, 3, 23, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 6, 4, 1, 0), conn=db_conn)

    days = dict(compute_last_n_days_hours_by_project(db_conn, "u1", n=7, end_date=_date(2025, 6, 3)))
    assert abs(days["2025-06-03"]["P"] - 1.0) < 0.01


def test_week_hours_orphan_stop_outside_margin_dropped(db_conn):
    """Verwaister Stop im Fenster paart nicht mehr mit Wochen-altem verwaisten Start.

    Bewusste Verhaltensänderung des Timestamp-Fensters: früher hätte die
    LIFO-Paarung über die Voll-Historie ein Phantom-Paar über Wochen gebildet
    (bis zu 24 h pro Zwischentag); jetzt wird der Stop ohne Start verworfen.
    """
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import TIMESTAMP_FORMAT as _TS_FMT
    from db_helper import compute_last_n_days_hours_by_project, log_start

    user_id = check_user(db_conn, "u1")
    # Verwaister Start 3 Wochen vor dem Fenster.
    log_start(project="P", name="u1", timestamp=_dt(2025, 5, 10, 9, 0), conn=db_conn)
    # Verwaister Stop mitten im Fenster (direkt eingefügt, um close_stale zu umgehen).
    cur = db_conn.cursor()
    stop_ts = _dt(2025, 6, 2, 12, 0)
    cur.execute(
        "INSERT INTO events (user_id, project, event_type, timestamp, date) VALUES (?, 'P', 'stop', ?, ?)",
        (user_id, stop_ts.strftime(_TS_FMT), stop_ts.strftime("%d-%m-%Y")),
    )
    db_conn.commit()

    days = dict(compute_last_n_days_hours_by_project(db_conn, "u1", n=7, end_date=_date(2025, 6, 3)))
    assert sum(sum(d.values()) for d in days.values()) == 0.0


def test_daily_duration_ignores_far_history(db_conn):
    """calculate_daily_duration nutzt das Timestamp-Fenster (±1 Tag) statt der Voll-Historie."""
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, log_start, log_stop

    check_user(db_conn, "u1")
    # Weit entfernte Session (gleiches Projekt) — darf den Zieltag nicht beeinflussen.
    log_start(project="P", name="u1", timestamp=_dt(2025, 1, 15, 9, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 1, 15, 17, 0), conn=db_conn)
    # Zieltag: genau 90 min.
    log_start(project="P", name="u1", timestamp=_dt(2025, 6, 2, 10, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 6, 2, 11, 30), conn=db_conn)

    assert abs(calculate_daily_duration(project="P", name="u1", date="02-06-2025", conn=db_conn) - 5400) < 2
    assert calculate_daily_duration(project="P", name="u1", date="20-01-2025", conn=db_conn) == 0


def test_week_hours_session_spanning_two_midnights(db_conn):
    """Session Fr 22:00 → So 01:00 (2 Mitternächte, App lief durch) wird voll verbucht."""
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, compute_last_n_days_hours_by_project, log_start, log_stop

    check_user(db_conn, "u1")
    # 2025-06-06 (Fr) 22:00 → 2025-06-08 (So) 01:00.
    log_start(project="P", name="u1", timestamp=_dt(2025, 6, 6, 22, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 6, 8, 1, 0), conn=db_conn)

    days = dict(compute_last_n_days_hours_by_project(db_conn, "u1", n=7, end_date=_date(2025, 6, 8)))
    assert abs(days["2025-06-06"]["P"] - 2.0) < 0.01  # Fr: 22-24 Uhr
    assert abs(days["2025-06-07"]["P"] - 24.0) < 0.01  # Sa: kompletter Tag
    assert abs(days["2025-06-08"]["P"] - 1.0) < 0.01  # So: 0-1 Uhr
    # Auch am Fensterrand: Fenster endet AM Freitag → Fr braucht den So-Stop (+3-Tage-Rand).
    assert abs(calculate_daily_duration(project="P", name="u1", date="06-06-2025", conn=db_conn) - 7200) < 2


def test_timezone_aware_timestamp_row_is_skipped(db_conn):
    """Eine tz-behaftete Timestamp-Zeile (hand-editierte DB) crasht die Paarung nicht."""
    from datetime import date as _date
    from datetime import datetime as _dt

    from db_helper import calculate_daily_duration, compute_last_n_days_hours_by_project, log_start, log_stop

    user_id = check_user(db_conn, "u1")
    log_start(project="P", name="u1", timestamp=_dt(2025, 6, 2, 9, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 6, 2, 10, 0), conn=db_conn)
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO events (user_id, project, event_type, timestamp, date) "
        "VALUES (?, 'P', 'start', '2025-06-02 11:00:00+02:00', '02-06-2025')",
        (user_id,),
    )
    db_conn.commit()

    # Kein TypeError; die aware-Zeile wird wie früher (strptime) verworfen.
    assert abs(calculate_daily_duration(project="P", name="u1", date="02-06-2025", conn=db_conn) - 3600) < 2
    days = dict(compute_last_n_days_hours_by_project(db_conn, "u1", n=3, end_date=_date(2025, 6, 3)))
    assert abs(days["2025-06-02"]["P"] - 1.0) < 0.01


def test_set_daily_transferred_single_preserves_transferred_at(db_conn):
    """Auch der Einzel-Writer überschreibt transferred_at bei erneutem Setzen nicht mehr.

    Einheitliche Semantik mit dem Bulk-Writer (gemeinsamer Kern
    _apply_transferred_row): das ursprüngliche Übertragungsdatum bleibt stehen.
    """
    from db_helper import get_daily_meta, set_daily_transferred

    check_user(db_conn, "u1")
    set_daily_transferred(db_conn, "u1", "A", "2025-06-02", True, transferred_at="2025-06-01")
    set_daily_transferred(db_conn, "u1", "A", "2025-06-02", True, transferred_at="2025-06-09")
    assert get_daily_meta(db_conn, "u1", "A", "2025-06-02")["transferred_at"] == "2025-06-01"


# ---------------------------------------------------------------------------
# Archivierung (v2.2.0): Benutzer/Projekte ausblenden statt löschen
# ---------------------------------------------------------------------------


def test_archived_user_hidden_from_default_list(db_conn):
    """Archivierte Benutzer fehlen in get_all_users, erscheinen mit include_archived."""
    from db_helper import get_all_users, set_archived

    check_user(db_conn, "aktiv")
    check_user(db_conn, "alt")
    assert set_archived(db_conn, "user", "alt", True) is True
    assert get_all_users(db_conn) == ["aktiv"]
    assert get_all_users(db_conn, include_archived=True) == ["aktiv", "alt"]
    # Wieder einblenden.
    assert set_archived(db_conn, "user", "alt", False) is True
    assert get_all_users(db_conn) == ["aktiv", "alt"]


def test_archived_project_hidden_but_data_preserved(db_conn):
    """Archivierte Projekte verschwinden aus der Auswahl; Events bleiben erhalten."""
    from datetime import datetime as _dt

    from db_helper import (
        calculate_daily_duration,
        check_project,
        get_all_projects,
        log_start,
        log_stop,
        set_archived,
    )

    check_user(db_conn, "u1")
    check_project(db_conn, "Altprojekt")
    log_start(project="Altprojekt", name="u1", timestamp=_dt(2025, 6, 2, 9, 0), conn=db_conn)
    log_stop(project="Altprojekt", name="u1", timestamp=_dt(2025, 6, 2, 10, 0), conn=db_conn)

    set_archived(db_conn, "project", "Altprojekt", True)
    assert "Altprojekt" not in get_all_projects(db_conn)
    assert "Altprojekt" in get_all_projects(db_conn, include_archived=True)
    # Daten unangetastet: Dauer weiterhin berechenbar.
    assert abs(calculate_daily_duration(project="Altprojekt", name="u1", date="02-06-2025", conn=db_conn) - 3600) < 2


def test_archivable_overview_counts_events(db_conn):
    """get_archivable_overview liefert Name, Flag und Event-Anzahl."""
    from datetime import datetime as _dt

    from db_helper import get_archivable_overview, log_start, log_stop, set_archived

    check_user(db_conn, "u1")
    log_start(project="P", name="u1", timestamp=_dt(2025, 6, 2, 9, 0), conn=db_conn)
    log_stop(project="P", name="u1", timestamp=_dt(2025, 6, 2, 10, 0), conn=db_conn)
    set_archived(db_conn, "user", "u1", True)

    overview = get_archivable_overview(db_conn)
    assert ("u1", True, 2) in overview["users"]
    assert any(name == "P" and count == 2 for name, _a, count in overview["projects"])


def test_set_archived_rejects_bad_input(db_conn):
    """Ungültige Art/Name/Verbindung → False, kein Fehler."""
    from db_helper import set_archived

    check_user(db_conn, "u1")
    assert set_archived(db_conn, "group", "u1", True) is False
    assert set_archived(db_conn, "user", "", True) is False
    assert set_archived(None, "user", "u1", True) is False
    assert set_archived(db_conn, "user", "gibtsnicht", True) is False


# --- Commit 9: Verbindungs-Pragmas (WAL, synchronous, foreign_keys) ---------


def test_create_connection_sets_pragmas(tmp_path):
    """create_connection aktiviert WAL, synchronous=NORMAL und foreign_keys."""
    db_file = str(tmp_path / "pragma.db")
    conn = create_connection(db_file)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1  # 1 = NORMAL
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_foreign_keys_enforced_on_write(tmp_path):
    """foreign_keys=ON weist Events mit nicht existentem user_id ab."""
    import sqlite3

    conn = create_connection(str(tmp_path / "fk.db"))
    try:
        create_main_table(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO events (user_id, project, event_type, timestamp, date)"
                " VALUES (99999, 'P', 'start', '2025-06-02 09:00:00', '02-06-2025')"
            )
    finally:
        conn.close()


def test_old_journal_db_opens_and_reads(tmp_path):
    """Alt-DB im klassischen Rollback-Journal öffnet, liest und rollt zurück.

    Simuliert eine vor der WAL-Umstellung angelegte Datenbank: Schema + Daten
    ohne Pragmas geschrieben (journal_mode=delete). create_connection muss sie
    öffnen, auf WAL heben und die Daten unverändert liefern; der dokumentierte
    Rollback (PRAGMA journal_mode=DELETE) muss das Dateiformat zurückstellen.
    """
    import sqlite3

    db_file = str(tmp_path / "alt.db")
    old = sqlite3.connect(db_file)  # bewusst OHNE create_connection
    old.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    old.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,"
        " project TEXT, event_type TEXT, timestamp DATETIME, date TEXT,"
        " FOREIGN KEY (user_id) REFERENCES users(id))"
    )
    old.execute("INSERT INTO users (name) VALUES ('alt_user')")
    old.execute(
        "INSERT INTO events (user_id, project, event_type, timestamp, date)"
        " VALUES (1, 'P', 'start', '2025-06-02 09:00:00', '02-06-2025')"
    )
    old.commit()
    assert old.execute("PRAGMA journal_mode").fetchone()[0].lower() == "delete"
    old.close()

    conn = create_connection(db_file)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        rows = conn.execute("SELECT user_id, project, event_type FROM events").fetchall()
        assert rows == [(1, "P", "start")]
        # Dokumentierter Rollback: zurück aufs klassische Journal.
        assert conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower() == "delete"
    finally:
        conn.close()


# --- Commit 11: migrate_legacy_user_tables (Alt-DB bleibt importierbar) -----


def _make_legacy_db(path, tables):
    """Baut eine synthetische Alt-Schema-DB: nur ``user_<name>``-Eventtabellen.

    ``tables``: {tabellenname: [(project, event_type, timestamp, date), ...]}.
    Bewusst mit nacktem sqlite3.connect angelegt — wie eine DB aus der Zeit
    vor der zentralen events-Tabelle.
    """
    import sqlite3

    old = sqlite3.connect(path)
    for table_name, rows in tables.items():
        old.execute(
            f'CREATE TABLE "{table_name}" ('
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " project TEXT NOT NULL,"
            " event_type TEXT,"
            " timestamp DATETIME NOT NULL,"
            " date TEXT NOT NULL)"
        )
        old.executemany(
            f'INSERT INTO "{table_name}" (project, event_type, timestamp, date) VALUES (?, ?, ?, ?)',
            rows,
        )
    old.commit()
    old.close()


def test_migrate_legacy_user_tables_full_and_idempotent(tmp_path):
    """Alt-Schema-DB (user_<name>-Tabellen): Migration vollständig, zweiter
    Lauf idempotent (Marker in migration_log) — der Beweis, dass alte DBs
    importierbar bleiben."""
    from db_helper import migrate_legacy_user_tables

    db_file = str(tmp_path / "legacy.db")
    hans_rows = [
        ("P1", "start", "2020-05-04 09:00:00", "04-05-2020"),
        ("P1", "stop", "2020-05-04 17:00:00", "04-05-2020"),
        ("P2", "start", "2020-05-05 08:30:00", "05-05-2020"),
    ]
    karla_rows = [("P1", "start", "2020-05-04 10:00:00", "04-05-2020")]
    _make_legacy_db(db_file, {"hans_events": hans_rows, "karla_events": karla_rows})

    conn = create_connection(db_file)
    try:
        assert create_main_table(conn) is True
        assert migrate_legacy_user_tables(conn) is True

        # Benutzer wurden aus den Tabellennamen angelegt.
        users = dict(conn.execute("SELECT name, id FROM users").fetchall())
        assert set(users) == {"hans", "karla"}

        # Daten vollständig und feldgenau übernommen.
        migrated = conn.execute(
            "SELECT u.name, e.project, e.event_type, e.timestamp, e.date"
            " FROM events e JOIN users u ON u.id = e.user_id ORDER BY e.id"
        ).fetchall()
        assert migrated == [("hans", *r) for r in hans_rows] + [("karla", *r) for r in karla_rows]

        # Marker je Tabelle gesetzt; Legacy-Tabellen bleiben unangetastet.
        log_tables = {r[0] for r in conn.execute("SELECT table_name FROM migration_log").fetchall()}
        assert log_tables == {"hans_events", "karla_events"}
        assert conn.execute('SELECT COUNT(*) FROM "hans_events"').fetchone()[0] == len(hans_rows)

        # Zweiter Lauf (z. B. nächster App-Start): keine Duplikate.
        assert migrate_legacy_user_tables(conn) is True
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == len(hans_rows) + len(karla_rows)
        assert conn.execute("SELECT COUNT(*) FROM migration_log").fetchone()[0] == 2
    finally:
        conn.close()


def test_migrate_legacy_skips_non_legacy_schema(tmp_path):
    """Eine *_events-Tabelle ohne Legacy-Spalten wird defensiv übersprungen
    (kein Marker, keine Events) — die Migration läuft trotzdem durch."""
    import sqlite3

    from db_helper import migrate_legacy_user_tables

    db_file = str(tmp_path / "kaputt.db")
    old = sqlite3.connect(db_file)
    old.execute('CREATE TABLE "kaputt_events" (id INTEGER PRIMARY KEY, payload TEXT)')
    old.execute("INSERT INTO \"kaputt_events\" (payload) VALUES ('x')")
    old.commit()
    old.close()

    conn = create_connection(db_file)
    try:
        create_main_table(conn)
        assert migrate_legacy_user_tables(conn) is True
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM migration_log").fetchone()[0] == 0
        # break_events (endet ebenfalls auf _events) darf nie als Legacy gelten.
        assert "break_events" not in {r[0] for r in conn.execute("SELECT table_name FROM migration_log").fetchall()}
    finally:
        conn.close()


def test_migrate_legacy_without_connection_returns_false():
    from db_helper import migrate_legacy_user_tables

    assert migrate_legacy_user_tables(None) is False


# --- Commit 11: Break-Lebenszyklus (Crash-Recovery während einer Pause) -----


def test_get_open_break_roundtrip(db_conn):
    """log_break_start → get_open_break liefert die offene Pause; nach
    log_break_stop ist sie geschlossen (Dauer korrekt)."""
    from datetime import datetime as _dt

    from db_helper import get_open_break, log_break_start, log_break_stop

    check_user(db_conn, "brk_user")
    assert get_open_break("P", "brk_user", conn=db_conn) is None

    started = _dt(2026, 6, 23, 12, 0)
    assert (
        log_break_start(
            project="P",
            name="brk_user",
            break_kind="short",
            is_auto=True,
            source="pomodoro_break",
            started_at=started,
            conn=db_conn,
        )
        is True
    )
    ob = get_open_break("P", "brk_user", conn=db_conn)
    assert ob is not None
    assert ob["break_kind"] == "short"
    assert ob["started_at"] == "2026-06-23 12:00:00"
    assert ob["is_auto"] is True
    assert ob["source"] == "pomodoro_break"

    assert log_break_stop(project="P", name="brk_user", ended_at=started + timedelta(minutes=10), conn=db_conn) is True
    assert get_open_break("P", "brk_user", conn=db_conn) is None
    row = db_conn.execute("SELECT ended_at, duration_seconds FROM break_events WHERE id = ?", (ob["id"],)).fetchone()
    assert row == ("2026-06-23 12:10:00", 600)


def test_log_break_start_no_duplicate_open_break(db_conn):
    """Ein zweiter Start bei bereits offener Pause legt KEINE zweite Zeile an."""
    from datetime import datetime as _dt

    from db_helper import log_break_start

    check_user(db_conn, "brk_dup")
    started = _dt(2026, 6, 23, 12, 0)
    assert log_break_start(project="P", name="brk_dup", break_kind="manual", started_at=started, conn=db_conn) is True
    assert (
        log_break_start(
            project="P", name="brk_dup", break_kind="manual", started_at=started + timedelta(minutes=1), conn=db_conn
        )
        is True
    )
    assert db_conn.execute("SELECT COUNT(*) FROM break_events WHERE ended_at IS NULL").fetchone()[0] == 1


def test_close_stale_breaks_after_crash(db_conn):
    """Crash während einer Pause: der nächste Start schließt die verwaiste
    Pause mit ended_at = started_at und Dauer 0 (Spiegel von
    close_stale_sessions) — die Wanduhr-Zeit über den Crash hinweg ist keine
    Pause. Zweiter Lauf ist idempotent."""
    from datetime import datetime as _dt

    from db_helper import close_stale_breaks, get_open_break, log_break_start

    check_user(db_conn, "brk_crash")
    started = _dt(2026, 6, 22, 15, 0)  # „gestern" — App danach abgestürzt
    log_break_start(project="P", name="brk_crash", break_kind="long", started_at=started, conn=db_conn)
    assert get_open_break("P", "brk_crash", conn=db_conn) is not None

    assert close_stale_breaks(db_conn) == 1
    assert get_open_break("P", "brk_crash", conn=db_conn) is None
    row = db_conn.execute("SELECT started_at, ended_at, duration_seconds FROM break_events").fetchone()
    assert row == ("2026-06-22 15:00:00", "2026-06-22 15:00:00", 0)

    assert close_stale_breaks(db_conn) == 0  # idempotent


def test_close_stale_breaks_noop_cases(db_conn):
    """Ohne Verbindung bzw. ohne offene Pausen: 0; geschlossene Pausen bleiben
    unangetastet."""
    from datetime import datetime as _dt

    from db_helper import close_stale_breaks, log_break_start, log_break_stop

    assert close_stale_breaks(None) == 0
    assert close_stale_breaks(db_conn) == 0

    check_user(db_conn, "brk_ok")
    started = _dt(2026, 6, 23, 12, 0)
    log_break_start(project="P", name="brk_ok", break_kind="short", started_at=started, conn=db_conn)
    log_break_stop(project="P", name="brk_ok", ended_at=started + timedelta(minutes=5), conn=db_conn)
    assert close_stale_breaks(db_conn) == 0
    row = db_conn.execute("SELECT ended_at, duration_seconds FROM break_events").fetchone()
    assert row == ("2026-06-23 12:05:00", 300)


# ---------------------------------------------------------------------------
# backup_database_daily: tägliches Backup mit Rotation (sqlite3-Backup-API)
# ---------------------------------------------------------------------------


def _make_backup_source_db(path):
    """Frische DB mit einem Benutzer — als Quelle für Backup-Tests."""
    conn = create_connection(str(path))
    create_main_table(conn)
    check_user(conn, "backup_user")
    return conn


def test_backup_database_daily_creates_todays_backup(tmp_path):
    """Erstes Backup des Tages: backups/<name>-YYYY-MM-DD.db, lesbare Kopie."""
    from datetime import datetime as _dt

    from db_helper import backup_database_daily

    db_path = tmp_path / "meine.db"
    conn = _make_backup_source_db(db_path)
    try:
        target = backup_database_daily(conn, str(db_path))
    finally:
        conn.close()

    expected = tmp_path / "backups" / f"meine-{_dt.now().strftime('%Y-%m-%d')}.db"
    assert target == str(expected)
    assert expected.is_file()
    # Konsistente, lesbare Kopie (Backup-API kopiert auch den WAL-Anteil mit).
    backup_conn = create_connection(str(expected))
    try:
        assert get_all_users(backup_conn) == ["backup_user"]
    finally:
        backup_conn.close()
    # Kein .tmp-Rest der atomaren Erstellung.
    assert list((tmp_path / "backups").glob("*.tmp")) == []


def test_backup_database_daily_idempotent_same_day(tmp_path):
    """Zweiter Aufruf am selben Tag: gleiche Datei, kein Neuschreiben."""
    from db_helper import backup_database_daily

    db_path = tmp_path / "app.db"
    conn = _make_backup_source_db(db_path)
    try:
        first = backup_database_daily(conn, str(db_path))
        stat_before = os.stat(first)
        check_user(conn, "spaeter_user")  # DB ändert sich NACH dem Backup
        second = backup_database_daily(conn, str(db_path))
    finally:
        conn.close()

    assert second == first
    assert os.stat(first).st_mtime_ns == stat_before.st_mtime_ns  # nicht neu geschrieben
    assert len(list((tmp_path / "backups").glob("*.db"))) == 1
    # Der später angelegte Benutzer ist im (älteren) Tages-Backup nicht enthalten.
    backup_conn = create_connection(first)
    try:
        assert get_all_users(backup_conn) == ["backup_user"]
    finally:
        backup_conn.close()


def test_backup_database_daily_rotation_keeps_last_seven(tmp_path):
    """Nur die jüngsten 7 Backups DIESER DB bleiben; fremde Stämme unberührt."""
    from datetime import datetime as _dt

    from db_helper import backup_database_daily

    db_path = tmp_path / "app.db"
    conn = _make_backup_source_db(db_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    old_names = [f"app-2020-01-{d:02d}.db" for d in range(1, 10)]  # 9 alte Backups
    for n in old_names:
        (backup_dir / n).write_bytes(b"alt")
    (backup_dir / "andere-2020-01-01.db").write_bytes(b"fremd")  # anderer DB-Stamm

    try:
        assert backup_database_daily(conn, str(db_path)) is not None
    finally:
        conn.close()

    kept = sorted(p.name for p in backup_dir.glob("app-*.db"))
    today_name = f"app-{_dt.now().strftime('%Y-%m-%d')}.db"
    assert len(kept) == 7
    assert kept == sorted([*old_names[3:], today_name])  # die 3 ältesten sind weg
    assert (backup_dir / "andere-2020-01-01.db").exists()  # fremder Stamm bleibt


def test_backup_database_daily_failure_returns_none(tmp_path):
    """Backup-Fehler („backups" ist eine Datei → makedirs scheitert):
    None statt Exception — der App-Start darf nie am Backup scheitern."""
    from db_helper import backup_database_daily

    db_path = tmp_path / "app.db"
    conn = _make_backup_source_db(db_path)
    (tmp_path / "backups").write_text("blockiert")
    try:
        assert backup_database_daily(conn, str(db_path)) is None
    finally:
        conn.close()
    assert (tmp_path / "backups").read_text() == "blockiert"


def test_backup_database_daily_noop_without_conn_or_file(tmp_path):
    """Ohne Verbindung bzw. ohne existierende DB-Datei: None, kein Ordner."""
    from db_helper import backup_database_daily

    assert backup_database_daily(None, str(tmp_path / "x.db")) is None
    conn = _make_backup_source_db(tmp_path / "y.db")
    try:
        assert backup_database_daily(conn, str(tmp_path / "fehlt.db")) is None
    finally:
        conn.close()
    assert not (tmp_path / "backups").exists()


def test_fetch_day_events_window_filter_order_limit(db_conn):
    """fetch_day_events: Fenster [lo, hi), optionale Filter, Chronologie, Limit."""
    day = datetime(2023, 10, 2, 9, 0, 0)
    log_start(project="A", name="anna", timestamp=day, conn=db_conn)
    log_stop(project="A", name="anna", timestamp=day.replace(hour=10), conn=db_conn)
    log_start(project="B", name="bernd", timestamp=day.replace(hour=11), conn=db_conn)
    # Außerhalb des Fensters — darf nie auftauchen.
    log_start(project="A", name="anna", timestamp=datetime(2023, 10, 9, 9, 0, 0), conn=db_conn)

    lo, hi = "2023-10-02 00:00:00", "2023-10-03 00:00:00"
    rows = fetch_day_events(db_conn, lo, hi)
    # Zeilenformat (id, user, project, event_type, timestamp), chronologisch.
    assert [(r[1], r[2], r[3]) for r in rows] == [
        ("anna", "A", "start"),
        ("anna", "A", "stop"),
        ("bernd", "B", "start"),
    ]
    assert [r[4] for r in rows] == sorted(r[4] for r in rows)

    assert fetch_day_events(db_conn, lo, hi, user="anna") == [r for r in rows if r[1] == "anna"]
    assert fetch_day_events(db_conn, lo, hi, user="anna", project="A") == [
        r for r in rows if r[1] == "anna" and r[2] == "A"
    ]
    assert fetch_day_events(db_conn, lo, hi, limit=2) == rows[:2]
    assert fetch_day_events(None, lo, hi) == []
