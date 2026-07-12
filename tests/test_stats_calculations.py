"""Tests für Workday-Filter und Übersichts-Aggregation in stats_calculations.py."""

import logging
import os
import sys
from datetime import datetime

import polars as pl
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from stats_calculations import (
    _filter_workdays,
    _paired_durations_hours,
    calculate_overview,
)


def _df(events):
    """events: list of (user, project, event_type, timestamp_str)"""
    rows = []
    for u, p, et, ts in events:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        rows.append(
            {
                "user": u,
                "project": p,
                "event_type": et,
                "timestamp": dt,
                "date": dt.strftime("%d-%m-%Y"),
            }
        )
    return pl.DataFrame(rows)


def test_paired_durations_logs_warning_on_unbalanced(caplog):
    df = _df(
        [
            ("u", "p", "start", "2024-01-08 09:00:00"),
            ("u", "p", "stop", "2024-01-08 17:00:00"),
            ("u", "p", "start", "2024-01-09 09:00:00"),
            # vergessenes stop
        ]
    )
    with caplog.at_level(logging.DEBUG):
        result = _paired_durations_hours(df)
    assert len(result) == 1
    assert result[0] == pytest.approx(8.0)
    assert any("ungepaart" in r.message for r in caplog.records)


def test_filter_workdays_drops_saturday():
    df = _df(
        [
            ("u", "p", "start", "2024-01-06 10:00:00"),  # Samstag
            ("u", "p", "stop", "2024-01-06 11:00:00"),
            ("u", "p", "start", "2024-01-08 10:00:00"),  # Montag
            ("u", "p", "stop", "2024-01-08 11:00:00"),
        ]
    )
    filt = _filter_workdays(df, country="DE", subdiv=None, include_holidays=True, count_weekend_work=False)
    assert filt.height == 2
    # Es bleiben nur Montags-Events.
    dates = filt.select(pl.col("date")).to_series().to_list()
    assert set(dates) == {"08-01-2024"}


def test_filter_workdays_keeps_weekend_when_count_weekend_work_true():
    df = _df(
        [
            ("u", "p", "start", "2024-01-06 10:00:00"),  # Samstag
            ("u", "p", "stop", "2024-01-06 11:00:00"),
        ]
    )
    filt = _filter_workdays(df, country="DE", subdiv=None, include_holidays=True, count_weekend_work=True)
    assert filt.height == 2


def test_filter_workdays_drops_german_holiday():
    df = _df(
        [
            ("u", "p", "start", "2024-10-03 10:00:00"),  # Tag der Dt. Einheit (Do)
            ("u", "p", "stop", "2024-10-03 11:00:00"),
            ("u", "p", "start", "2024-10-04 10:00:00"),
            ("u", "p", "stop", "2024-10-04 11:00:00"),
        ]
    )
    filt = _filter_workdays(df, country="DE", subdiv=None, include_holidays=True, count_weekend_work=False)
    dates = set(filt.select(pl.col("date")).to_series().to_list())
    assert dates == {"04-10-2024"}


def test_calculate_overview_basic():
    df = _df(
        [
            ("alice", "P1", "start", "2024-01-08 09:00:00"),
            ("alice", "P1", "stop", "2024-01-08 17:00:00"),
            ("bob", "P2", "start", "2024-01-06 10:00:00"),  # Wochenende
            ("bob", "P2", "stop", "2024-01-06 12:00:00"),
            ("alice", "P1", "start", "2024-01-09 09:00:00"),  # offen
        ]
    )
    ov = calculate_overview(df)
    assert set(ov["users"]) == {"alice", "bob"}
    assert set(ov["projects"]) == {"P1", "P2"}
    assert ov["total_hours"] == pytest.approx(10.0)
    assert ov["n_sessions"] == 2
    assert ov["data_quality"]["open_sessions"] == 1
    assert ov["data_quality"]["weekend_entries"] >= 2


def test_calculate_overview_empty():
    ov = calculate_overview(pl.DataFrame())
    assert ov["total_hours"] == 0.0
    assert ov["users"] == []


def test_calculate_hour_weekday_matrix_basic():
    from stats_calculations import calculate_hour_weekday_matrix

    # 2024-01-08 is a Monday (weekday 0); 09:00-11:00 = 2h across hours 9,10.
    df = _df([("u", "p", "start", "2024-01-08 09:00:00"), ("u", "p", "stop", "2024-01-08 11:00:00")])
    m = calculate_hour_weekday_matrix(df)
    by = {(r["weekday"], r["hour"]): r["hours"] for r in m.iter_rows(named=True)}
    assert by[(0, 9)] == pytest.approx(1.0)
    assert by[(0, 10)] == pytest.approx(1.0)


def test_calculate_start_hour_distribution():
    from stats_calculations import calculate_start_hour_distribution

    df = _df(
        [
            ("u", "p", "start", "2024-01-08 09:00:00"),
            ("u", "p", "stop", "2024-01-08 11:00:00"),
            ("u", "p", "start", "2024-01-09 09:30:00"),
            ("u", "p", "stop", "2024-01-09 10:00:00"),
        ]
    )
    dist = calculate_start_hour_distribution(df)
    counts = {r["hour"]: r["count"] for r in dist.iter_rows(named=True)}
    assert counts == {9: 2}


def test_calculate_session_duration_distribution():
    from stats_calculations import calculate_session_duration_distribution

    df = _df(
        [
            ("u", "p", "start", "2024-01-08 09:00:00"),
            ("u", "p", "stop", "2024-01-08 11:00:00"),
            ("u", "p", "start", "2024-01-09 09:00:00"),
            ("u", "p", "stop", "2024-01-09 09:30:00"),
        ]
    )
    dist = calculate_session_duration_distribution(df)
    vals = sorted(dist["duration_hours"].to_list())
    assert vals == pytest.approx([0.5, 2.0])


def test_calculate_break_statistics():
    from stats_calculations import calculate_break_statistics

    events = _df([("u", "p", "start", "2024-01-08 09:00:00"), ("u", "p", "stop", "2024-01-08 12:00:00")])
    breaks = pl.DataFrame(
        [
            {"break_kind": "short", "duration_seconds": 900, "date": "2024-01-08"},
            {"break_kind": "manual", "duration_seconds": 1800, "date": "2024-01-08"},
        ]
    )
    stats = calculate_break_statistics(breaks, events)
    assert stats["totals"]["work_hours"] == pytest.approx(3.0)
    assert stats["totals"]["break_hours"] == pytest.approx(0.75)
    assert not stats["per_day"].is_empty()


# ---------------------------------------------------------------------------
# LIFO-Paarung, Mitternachts-Split und sessionweises Filtern (Bugfixes)
# ---------------------------------------------------------------------------


def test_time_series_splits_midnight_session():
    """Mitternachts-Session: Start und Stop tragen verschiedene ``date``-Werte.

    Die Zeitreihe muss die Stunden aus den Zeitstempeln anteilig auf beide
    Tage verteilen — ein Partitionieren nach der Event-``date``-Spalte würde
    die Paarung zerreißen (0 Stunden statt 1h + 1h).
    """
    from stats_calculations import analyze_time_series, calculate_daily_project_hours

    df = _df(
        [
            ("u", "p", "start", "2024-01-08 23:00:00"),  # Mo 23:00
            ("u", "p", "stop", "2024-01-09 01:00:00"),  # Di 01:00
        ]
    )
    daily_df, weekly_avg, weekday_avg = analyze_time_series(df)
    by_date = {r["date"]: r["hours"] for r in daily_df.iter_rows(named=True)}
    assert by_date == {"2024-01-08": pytest.approx(1.0), "2024-01-09": pytest.approx(1.0)}
    weekdays = {r["date"]: r["weekday"] for r in daily_df.iter_rows(named=True)}
    assert weekdays == {"2024-01-08": "Mo", "2024-01-09": "Di"}
    assert not weekly_avg.is_empty()
    assert not weekday_avg.is_empty()

    # Tages-Aggregation liefert denselben Split.
    daily = calculate_daily_project_hours(df)
    by_day = {r["date"]: r["hours"] for r in daily.iter_rows(named=True)}
    assert by_day == {"2024-01-08": pytest.approx(1.0), "2024-01-09": pytest.approx(1.0)}


def test_orphan_start_does_not_shift_pairing():
    """Verwaister Start + spätere komplette Sessions: LIFO-Paarung.

    Positionsweises Zippen würde den verwaisten Start vom Vortag mit dem
    ersten Stop des Folgetags zu einem 27h-Mega-Paar verketten. Die
    LIFO-Paarung überspringt den verwaisten Start und muss dasselbe Ergebnis
    liefern wie ``db_helper.calculate_daily_duration`` auf denselben Daten.
    """
    import sqlite3

    from db_helper import calculate_daily_duration
    from stats_calculations import calculate_daily_project_hours, calculate_hours_per_project

    events = [
        ("start", "2024-01-08 09:00:00"),  # verwaist (Stop vergessen)
        ("start", "2024-01-09 09:00:00"),
        ("stop", "2024-01-09 12:00:00"),
        ("start", "2024-01-09 13:00:00"),
        ("stop", "2024-01-09 15:00:00"),
    ]
    df = _df([("u", "p", et, ts) for et, ts in events])

    hours = calculate_hours_per_project(df)
    assert hours["total_hours"].to_list() == pytest.approx([5.0])  # NICHT 27h + 6h

    daily = calculate_daily_project_hours(df)
    by_day = {r["date"]: r["hours"] for r in daily.iter_rows(named=True)}
    assert by_day == {"2024-01-09": pytest.approx(5.0)}

    # Referenz: kanonische Berechnung aus db_helper auf denselben Events.
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, "
        "project TEXT, event_type TEXT, timestamp DATETIME, date TEXT)"
    )
    conn.execute("INSERT INTO users (name) VALUES ('u')")
    for et, ts in events:
        conn.execute(
            "INSERT INTO events (user_id, project, event_type, timestamp, date) VALUES (1, 'p', ?, ?, ?)",
            (et, ts, ts[:10]),
        )
    conn.commit()
    try:
        ref_seconds = calculate_daily_duration(project="p", name="u", date="09-01-2024", conn=conn)
    finally:
        conn.close()
    assert by_day["2024-01-09"] * 3600 == pytest.approx(ref_seconds)


def test_workday_filter_drops_complete_sessions_not_single_events():
    """Der Werktags-Filter verwirft ganze Sessions, nie einzelne Paar-Hälften.

    Eine Freitag-Nacht-Session (Stop am Samstag) bleibt komplett erhalten
    (Zuordnung über den Start); eine reine Samstags-Session fliegt komplett
    raus. Danach müssen alle verbleibenden Events sauber paarbar sein.
    """
    df = _df(
        [
            ("u", "p", "start", "2024-01-05 23:00:00"),  # Freitag
            ("u", "p", "stop", "2024-01-06 01:00:00"),  # Samstag (gehört zum Fr-Start!)
            ("u", "p", "start", "2024-01-06 10:00:00"),  # Samstag
            ("u", "p", "stop", "2024-01-06 11:00:00"),  # Samstag
            ("u", "p", "start", "2024-01-08 09:00:00"),  # Montag
            ("u", "p", "stop", "2024-01-08 10:00:00"),  # Montag
        ]
    )
    filt = _filter_workdays(df, country="DE", subdiv=None, include_holidays=True, count_weekend_work=False)
    # Fr-Nacht-Paar (inkl. Sa-Stop) + Mo-Paar bleiben, Sa-Paar fliegt komplett.
    assert filt.height == 4
    n_starts = filt.filter(pl.col("event_type") == "start").height
    n_stops = filt.filter(pl.col("event_type") == "stop").height
    assert n_starts == n_stops == 2
    durations = sorted(_paired_durations_hours(filt))
    assert durations == pytest.approx([1.0, 2.0])


def test_filter_sessions_by_date_range_keeps_pairs_together():
    """Datumsbereichs-Filter: Sessions gehören per Start-Zeitstempel zum Tag.

    Eine Mitternachts-Session am Bereichsrand wird komplett verworfen bzw.
    komplett behalten — nie nur eine Paar-Hälfte (die die Paarung verschöbe).
    """
    from stats_calculations import filter_sessions_by_date_range

    df = _df(
        [
            ("u", "p", "start", "2024-01-08 23:00:00"),  # vor dem Bereich
            ("u", "p", "stop", "2024-01-09 01:00:00"),  # in den Bereich hineinragend
            ("u", "p", "start", "2024-01-09 09:00:00"),
            ("u", "p", "stop", "2024-01-09 10:00:00"),
        ]
    )
    filt = filter_sessions_by_date_range(df, "2024-01-09", "2024-01-09")
    # Nur die reine 09.01.-Session bleibt; der einzelne Stop um 01:00 fliegt
    # mit seinem Start zusammen raus.
    assert filt.height == 2
    durations = _paired_durations_hours(filt)
    assert durations == pytest.approx([1.0])

    # Ohne Grenzen: unverändert.
    assert filter_sessions_by_date_range(df, None, None).height == 4


# ---------------------------------------------------------------------------
# Audit-Fixes: Kalender-Durchschnitt, ISO-Wochen, ANOVA-Gates, Startzeiten,
# Wochenend-Override, Lazy-Imports, KW-Matrix
# ---------------------------------------------------------------------------


def test_period_average_uses_calendar_span():
    """Wochenschnitt = Stunden / Kalender-Spanne, nicht / aktive Tage.

    21 aktive Tage (je 4h) über eine 29-Tage-Spanne: 84h. Richtig sind
    84 / (29/7) ≈ 20.28 h/Woche — die alte Rechnung über aktive Tage
    lieferte 84 / (21/7) = 28 h/Woche (~+40 % aufgebläht).
    """
    from stats_calculations import calculate_average_hours_per_period

    active_days = [f"2026-06-{d:02d}" for d in range(1, 21)] + ["2026-06-29"]
    assert len(active_days) == 21
    events = []
    for day in active_days:
        events.append(("u", "p", "start", f"{day} 09:00:00"))
        events.append(("u", "p", "stop", f"{day} 13:00:00"))
    df = _df(events)

    result = calculate_average_hours_per_period(df, 7)
    avg = result.filter(pl.col("user") == "u")["average_hours"][0]
    assert avg == pytest.approx(84.0 * 7 / 29, rel=1e-6)  # NICHT 28.0


def test_weekly_avg_keys_carry_iso_year():
    """KW1/2025 und KW1/2026 dürfen nicht zusammengeworfen werden.

    2025-01-01 liegt in ISO 2025-W01, 2025-12-31 in ISO 2026-W01 — gleiche
    Wochennummer, verschiedene ISO-Jahre.
    """
    from stats_calculations import analyze_time_series

    df = _df(
        [
            ("u", "p", "start", "2025-01-01 09:00:00"),
            ("u", "p", "stop", "2025-01-01 11:00:00"),  # 2h
            ("u", "p", "start", "2025-12-31 09:00:00"),
            ("u", "p", "stop", "2025-12-31 13:00:00"),  # 4h
        ]
    )
    _daily, weekly_avg, weekday_avg = analyze_time_series(df)
    assert weekly_avg.height == 2  # NICHT zu einer "Woche 1" verschmolzen
    labels = weekly_avg["week"].to_list()
    assert labels == ["2025-KW01", "2026-KW01"]  # chronologisch sortiert
    hours = dict(zip(labels, weekly_avg["hours"].to_list(), strict=True))
    assert hours["2025-KW01"] == pytest.approx(2.0)
    assert hours["2026-KW01"] == pytest.approx(4.0)
    # Ehrlichkeits-Spalte: Stichprobengröße je Gruppe.
    assert "n_days" in weekly_avg.columns
    assert weekly_avg["n_days"].to_list() == [1, 1]
    assert "n_days" in weekday_avg.columns


def test_project_anova_runs_with_single_user():
    """Projekt-ANOVA braucht nur ≥2 Projekte — auch mit einem einzigen User."""
    from stats_calculations import perform_anova_analysis

    events = []
    # Projekt A: kurze Sessions; Projekt B: lange Sessions (je 3 Stück).
    for day, dur_h in [(1, 1.0), (2, 2.0), (3, 1.5)]:
        events.append(("u", "A", "start", f"2026-06-{day:02d} 09:00:00"))
        stop_min = int(dur_h * 60)
        events.append(("u", "A", "stop", f"2026-06-{day:02d} {9 + stop_min // 60:02d}:{stop_min % 60:02d}:00"))
    for day, dur_h in [(4, 4.0), (5, 5.0), (8, 4.5)]:
        events.append(("u", "B", "start", f"2026-06-{day:02d} 09:00:00"))
        stop_min = int(dur_h * 60)
        events.append(("u", "B", "stop", f"2026-06-{day:02d} {9 + stop_min // 60:02d}:{stop_min % 60:02d}:00"))
    df = _df(events)

    results = perform_anova_analysis(df)
    assert results is not None
    assert "project_anova" in results  # lief trotz nur einem User
    assert "user_anova" not in results  # <2 User → keine User-ANOVA
    assert results["project_anova"]["f_statistic"] > 0
    assert 0.0 <= results["project_anova"]["p_value"] <= 1.0


def test_week_matrix_midnight_split_and_iso_boundaries():
    """KW-Matrix: Mitternachts-Splits landen auf den richtigen Wochentagen,
    ISO-Wochengrenzen (Montag) werden respektiert, Summen sind konsistent.

    ISO 2026-W28 = Mo 2026-07-06 .. So 2026-07-12.
    """
    from stats_calculations import available_iso_weeks, calculate_week_matrix

    df = _df(
        [
            # So (W27) 23:00 → Mo (W28) 01:00: nur der Mo-Anteil zählt in W28.
            ("u", "P1", "start", "2026-07-05 23:00:00"),
            ("u", "P1", "stop", "2026-07-06 01:00:00"),
            # Di 23:00 → Mi 01:00: je 1h auf Di und Mi.
            ("u", "P1", "start", "2026-07-07 23:00:00"),
            ("u", "P1", "stop", "2026-07-08 01:00:00"),
            # So innerhalb der Woche: 2h.
            ("u", "P2", "start", "2026-07-12 10:00:00"),
            ("u", "P2", "stop", "2026-07-12 12:00:00"),
            # Mo der Folgewoche (W29): gehört NICHT in W28.
            ("u", "P2", "start", "2026-07-13 09:00:00"),
            ("u", "P2", "stop", "2026-07-13 10:00:00"),
        ]
    )

    m = calculate_week_matrix(df, 2026, 28)
    assert m["days"] == [f"2026-07-{d:02d}" for d in range(6, 13)]  # Mo..So
    assert m["projects"] == ["P1", "P2"]
    assert m["hours"][("P1", "2026-07-06")] == pytest.approx(1.0)  # Mo-Anteil der So-Nacht-Session
    assert m["hours"][("P1", "2026-07-07")] == pytest.approx(1.0)  # Di-Anteil
    assert m["hours"][("P1", "2026-07-08")] == pytest.approx(1.0)  # Mi-Anteil
    assert m["hours"][("P2", "2026-07-12")] == pytest.approx(2.0)
    # Nichts aus Nachbarwochen; keine Null-Einträge in "hours".
    assert all(day in m["days"] for _p, day in m["hours"])
    assert all(v > 0 for v in m["hours"].values())
    # Summen konsistent: Tage, Projekte und Gesamtsumme.
    assert m["day_totals"]["2026-07-06"] == pytest.approx(1.0)
    assert m["day_totals"]["2026-07-09"] == 0.0  # Tag ohne Einträge vorhanden, 0.0
    assert m["project_totals"] == {"P1": pytest.approx(3.0), "P2": pytest.approx(2.0)}
    assert m["total"] == pytest.approx(5.0)
    assert sum(m["day_totals"].values()) == pytest.approx(m["total"])
    assert sum(m["project_totals"].values()) == pytest.approx(m["total"])

    # Verfügbare Wochen: W27 (So-Anteil), W28, W29 — sortiert.
    assert available_iso_weeks(df) == [(2026, 27), (2026, 28), (2026, 29)]

    # Leere Woche: Struktur bleibt vollständig.
    empty = calculate_week_matrix(df, 2026, 20)
    assert empty["projects"] == []
    assert empty["total"] == 0.0
    assert len(empty["day_totals"]) == 7


def test_daily_patterns_average_uses_minutes():
    """Startzeit-Durchschnitt in Dezimalstunden, nicht auf volle Stunden gestutzt."""
    from stats_calculations import analyze_daily_patterns

    df = _df(
        [
            ("u", "p", "start", "2026-06-01 09:30:00"),
            ("u", "p", "stop", "2026-06-01 10:00:00"),
            ("u", "p", "start", "2026-06-02 09:45:00"),
            ("u", "p", "stop", "2026-06-02 10:30:00"),
        ]
    )
    patterns = analyze_daily_patterns(df)
    row = patterns.row(0, named=True)
    assert row["avg_start_hour"] == pytest.approx(9.625)  # NICHT 9.0
    assert row["earliest_start"] == pytest.approx(9.5)
    assert row["latest_start"] == pytest.approx(9.75)
    assert row["most_common_start_hour"] == 9  # Modus bleibt volle Stunde


def test_workday_filter_ui_override_beats_config(monkeypatch):
    """Der Dashboard-Schalter gewinnt immer — auch wenn die Config das
    Wochenend-Ausschließen deaktiviert hat (exclude_weekends_in_averages=False).
    """
    import stats_calculations as sc

    monkeypatch.setattr(
        sc,
        "load_config",
        lambda: {
            "holiday_country": "DE",
            "holiday_subdiv": "",
            "include_holidays_in_exclusion": True,
            "count_weekend_work": False,
            "exclude_weekends_in_averages": False,
        },
    )
    df = _df(
        [
            ("u", "p", "start", "2024-01-06 10:00:00"),  # Samstag
            ("u", "p", "stop", "2024-01-06 11:00:00"),
            ("u", "p", "start", "2024-01-08 10:00:00"),  # Montag
            ("u", "p", "stop", "2024-01-08 11:00:00"),
        ]
    )
    # Expliziter Override False → Wochenende raus, trotz Config.
    assert sc._apply_workday_filter(df, override_count_weekend_work=False).height == 2
    # Expliziter Override True → alles bleibt.
    assert sc._apply_workday_filter(df, override_count_weekend_work=True).height == 4
    # Kein Override → Config-Default (kein Ausschluss) greift.
    assert sc._apply_workday_filter(df, override_count_weekend_work=None).height == 4


def test_module_imports_without_sklearn_scipy():
    """scipy/sklearn/statsmodels werden lazy geladen — der Modul-Import darf
    ohne sie funktionieren (Subprozess mit Import-Blocker)."""
    import subprocess

    src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    code = (
        "import sys\n"
        f"sys.path.insert(0, {src!r})\n"
        "class Block:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in ('sklearn', 'scipy', 'statsmodels'):\n"
        "            raise ImportError('blocked: ' + name)\n"
        "        return None\n"
        "sys.meta_path.insert(0, Block())\n"
        "import stats_calculations\n"
        "print('IMPORT_OK')\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "IMPORT_OK" in result.stdout


def test_regression_returns_honest_r2_label_and_numeric_start_hour():
    """r2_label deklariert in-sample-Anpassung; start_hour bleibt numerisches Feature."""
    from stats_calculations import perform_regression_analysis

    events = []
    for day in range(1, 9):
        events.append(("u", "A" if day % 2 else "B", "start", f"2026-06-{day:02d} {8 + day % 3:02d}:00:00"))
        events.append(("u", "A" if day % 2 else "B", "stop", f"2026-06-{day:02d} {12 + day % 4:02d}:00:00"))
    results = perform_regression_analysis(_df(events))
    assert results["r2_label"] == "Modellanpassung (in-sample R²)"
    # start_hour wurde NICHT dummy-codiert (eine numerische Spalte, keine start_hour_*-Dummies).
    features = results["importance"]["feature"].to_list()
    assert "start_hour" in features
    assert not any(f.startswith("start_hour_") for f in features)


def test_new_calcs_handle_empty():
    from stats_calculations import (
        calculate_break_statistics,
        calculate_hour_weekday_matrix,
        calculate_session_duration_distribution,
        calculate_start_hour_distribution,
    )

    empty = pl.DataFrame()
    assert calculate_hour_weekday_matrix(empty).is_empty()
    assert calculate_start_hour_distribution(empty).is_empty()
    assert calculate_session_duration_distribution(empty).is_empty()
    bs = calculate_break_statistics(empty, empty)
    assert bs["totals"]["break_hours"] == 0.0
