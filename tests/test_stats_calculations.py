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
