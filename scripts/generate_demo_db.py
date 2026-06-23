#!/usr/bin/env python3
"""Erzeugt eine realistische, zufällig (seeded) generierte Demo-Datenbank für wotiti.

Befüllt Nutzer, Projekte, Start/Stop-Sessions (inkl. mehrfach am selben Tag
besuchter Projekte), Mittags-/Pomodoro-Pausen sowie Notizen + »übertragen«-Status
je (Projekt, Tag) — damit alle Features sofort sichtbar sind: Wochenansicht mit
stabilen Projektfarben, Start/Stop-Session-Liste (beide Layouts), Notizen,
✓/schraffierter Übertragen-Status und die Dashboard-Auswertungen.

Die Daten enden am tatsächlichen heutigen Tag, damit die »letzte Woche« in der
Wochenansicht gefüllt ist. Erneutes Ausführen aktualisiert die Datenbank auf das
aktuelle Datum.

Aufruf:  python3 scripts/generate_demo_db.py [ziel.db]
Default-Ziel:  data/demo/demo_database.db
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from db_helper import (  # noqa: E402
    check_user,
    create_connection,
    create_main_table,
    log_break_start,
    log_break_stop,
    log_event,
    set_daily_note,
    set_daily_transferred,
)

SEED = 42
DAYS_BACK = 28  # Zeitraum: heute minus DAYS_BACK Tage … heute

# Default-Nutzer der App zuerst (config default_user="Hans") → sofort sichtbar.
USERS = ["Hans", "Erika"]

PROJECTS = [
    "Website Relaunch",
    "Kundensupport",
    "Interne Doku",
    "Backend API",
    "Recherche",
]

# Kurze, realistische Notizen (≤ ~15 Wörter) — passend zu set_daily_note (max 20).
NOTES_POOL = [
    "Sprint-Planung und Backlog verfeinert",
    "Bugfix im Login-Flow, Ticket #142 geschlossen",
    "Kundentermin: Anforderungen für Release 2.0 besprochen",
    "Code-Review und Merge der Feature-Branch",
    "Doku für die API-Endpunkte aktualisiert",
    "Telefonsupport, mehrere Tickets abgearbeitet",
    "Recherche zu Caching-Strategien",
    "Deployment vorbereitet und auf Staging getestet",
    "Team-Meeting und Retro",
    "Datenbank-Migration geschrieben und getestet",
    "Refactoring des Zahlungsmoduls",
    "Konzept für neues Dashboard skizziert",
]


def _rand_session_blocks(rng, day):
    """Liefert eine Liste von (project, start_dt, end_dt)-Blöcken für einen Tag.

    Mit ~40 % Wahrscheinlichkeit wird ein Projekt am selben Tag erneut besucht
    (Muster A, B, A) — zeigt Gruppierung vs. chronologisches Layout.
    """
    start_h = rng.randint(7, 9)
    start_m = rng.choice([0, 15, 30, 45])
    cursor = datetime(day.year, day.month, day.day, start_h, start_m)

    n_blocks = rng.choice([1, 2, 2, 3, 3, 4])
    if rng.random() < 0.40 and n_blocks >= 3:
        a, b = rng.sample(PROJECTS, 2)
        plan = [a, b, a] + ([rng.choice(PROJECTS)] if n_blocks == 4 else [])
    else:
        plan = [rng.choice(PROJECTS) for _ in range(n_blocks)]

    blocks = []
    for i, project in enumerate(plan):
        dur = timedelta(minutes=rng.randint(60, 150))
        start = cursor
        end = start + dur
        blocks.append((project, start, end))
        gap = timedelta(minutes=rng.randint(5, 20))
        # Nach dem ersten/zweiten Block eine längere Mittagspause einlegen.
        if i == (1 if len(plan) >= 3 else 0):
            gap = timedelta(minutes=rng.randint(30, 60))
        cursor = end + gap
    return blocks


def generate(target_db: str) -> dict:
    rng = random.Random(SEED)
    os.makedirs(os.path.dirname(target_db), exist_ok=True)
    if os.path.exists(target_db):
        os.remove(target_db)

    conn = create_connection(target_db)
    if conn is None:
        raise SystemExit(f"Konnte keine DB anlegen: {target_db}")
    create_main_table(conn)  # legt users, events, break_events, projects, daily_notes an

    for u in USERS:
        check_user(conn, u)

    today = datetime.now().date()
    stats = {"events": 0, "breaks": 0, "notes": 0, "transferred": 0, "days": 0}

    for user in USERS:
        # Erika arbeitet seltener (zeigt Mehrbenutzer-Gruppierung dezent).
        work_prob = 0.92 if user == "Hans" else 0.45
        for offset in range(DAYS_BACK, -1, -1):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5 and rng.random() > 0.15:
                continue  # Wochenende meist frei
            if rng.random() > work_prob:
                continue
            blocks = _rand_session_blocks(rng, day)
            if not blocks:
                continue
            stats["days"] += 1

            day_projects = set()
            for project, start, end in blocks:
                log_event(conn, project, user, "start", start)
                log_event(conn, project, user, "stop", end)
                stats["events"] += 2
                day_projects.add(project)

            # Mittagspause (~12–13 Uhr) als langer Break auf dem ersten Projekt.
            lunch_proj = blocks[0][0]
            lunch_start = datetime(day.year, day.month, day.day, 12, rng.choice([0, 15, 30]))
            lunch_end = lunch_start + timedelta(minutes=rng.randint(30, 60))
            log_break_start(lunch_proj, user, "long", is_auto=False, source="manual", started_at=lunch_start, conn=conn)
            log_break_stop(lunch_proj, user, ended_at=lunch_end, conn=conn)
            stats["breaks"] += 1
            # Gelegentlich eine kurze Pomodoro-Pause am Nachmittag.
            if rng.random() < 0.4:
                sb_start = datetime(day.year, day.month, day.day, rng.randint(14, 16), rng.choice([0, 30]))
                sb_end = sb_start + timedelta(minutes=5)
                log_break_start(lunch_proj, user, "short", started_at=sb_start, conn=conn)
                log_break_stop(lunch_proj, user, ended_at=sb_end, conn=conn)
                stats["breaks"] += 1

            # Notizen + Übertragen-Status je (Projekt, Tag).
            day_iso = day.strftime("%Y-%m-%d")
            older_than_week = offset > 7
            # Am aktuellsten Tag (Default-Ansicht von "Hans") Notizen garantieren,
            # damit das Feature sofort sichtbar ist.
            force_note = user == "Hans" and offset == 0
            for project in day_projects:
                if force_note or rng.random() < 0.65:
                    set_daily_note(conn, user, project, day_iso, rng.choice(NOTES_POOL))
                    stats["notes"] += 1
                # Ältere Tage sind meist schon ins Firmensystem übertragen,
                # die aktuelle Woche überwiegend noch offen.
                transfer_prob = 0.85 if older_than_week else 0.2
                if rng.random() < transfer_prob:
                    booked_on = (day + timedelta(days=1)).strftime("%Y-%m-%d")
                    set_daily_transferred(conn, user, project, day_iso, True, booked_on)
                    stats["transferred"] += 1

    conn.close()
    return stats


if __name__ == "__main__":
    out = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.join(os.path.dirname(__file__), "..", "data", "demo", "demo_database.db")
    )
    out = os.path.abspath(out)
    result = generate(out)
    print(f"Demo-Datenbank erstellt: {out}")
    for k, v in result.items():
        print(f"  {k}: {v}")
