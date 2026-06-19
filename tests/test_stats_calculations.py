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
