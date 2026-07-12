"""
Statistik-Berechnungsmodul für die Zeiterfassungsanalyse.

Dieses Modul enthält Funktionen zur Analyse von Arbeitszeitdaten, einschließlich:
- Grundlegende Statistiken (Durchschnitte, Summen)
- Zeitreihenanalyse (Trends, Muster)
- Fortgeschrittene Analysen (Clustering, Regression, ANOVA)

Die Funktionen erwarten Zeitstempel im Format 'dd-mm-yyyy HH:MM:SS' und
arbeiten mit pandas DataFrames für effiziente Datenverarbeitung.
"""

import logging
from datetime import datetime

import numpy as np
import polars as pl

# Hinweis: scipy/sklearn/statsmodels werden bewusst NICHT auf Modulebene
# importiert (kosten >1s Startzeit), sondern lokal in den perform_*-Funktionen
# — das Modul muss auch ohne diese Pakete importierbar sein.
from db_helper import merge_intervals_seconds, pair_sessions_lifo
from utils import is_non_workday, load_config

logger = logging.getLogger(__name__)

# Konstanten für Zeitkonvertierung
TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
DATE_FORMAT = "%d-%m-%Y"


def _unique_list(data, column):
    return data.select(pl.col(column).unique()).to_series().to_list()


def _paired_sessions(group) -> list[tuple[datetime, datetime]]:
    """LIFO-gepaarte, vollständige Sessions einer (User, Projekt)-Gruppe.

    Nutzt die **kanonische** Paarung aus :func:`db_helper.pair_sessions_lifo`,
    damit Statistik und Anzeige identisch paaren (Invariante des Projekts).
    Verwaiste Starts/Stops werden übersprungen und nur geloggt — sie
    verschieben die Paarung der übrigen Sessions nicht.

    Returns:
        list[tuple]: ``(start_dt, stop_dt)`` je vollständiger Session.
    """
    events = [
        (etype, ts)
        for etype, ts in zip(group["event_type"].to_list(), group["timestamp"].to_list(), strict=True)
        if ts is not None
    ]
    sessions = []
    orphans = 0
    for start_ts, stop_ts in pair_sessions_lifo(events):
        if start_ts is None or stop_ts is None:
            orphans += 1
            continue
        sessions.append((start_ts, stop_ts))
    if orphans:
        logger.debug(
            "_paired_sessions: %d ungepaarte Events übersprungen — %d vollständige Sessions gezählt.",
            orphans,
            len(sessions),
        )
    return sessions


def _paired_durations_hours(group):
    """Dauern (in Stunden) der LIFO-gepaarten Sessions einer Gruppe."""
    return [(stop_ts - start_ts).total_seconds() / 3600 for start_ts, stop_ts in _paired_sessions(group)]


def _merged_total_hours(group) -> float:
    """Gesamtstunden einer (User, Projekt)-Gruppe als **Vereinigung** der
    gepaarten Intervalle (überlappende Sessions zählen nicht doppelt).

    Bewusst dieselbe Semantik wie die Dauer-Summen der App
    (``db_helper.calculate_duration``/``calculate_daily_duration``: LIFO +
    Intervall-Union). Die Tages-LISTE der App paart dagegen FIFO und zeigt
    Sessions einzeln — bei (nur durch manuelle Edits möglichen) überlappenden
    Sessions desselben Projekts kann die Summe der Listenzeilen daher über
    diesem Union-Total liegen. Maßgeblich für Stunden-Summen ist die Union
    (keine Doppelzählung), identisch in Timer-Anzeige und Dashboard.
    """
    return merge_intervals_seconds(_paired_sessions(group)) / 3600.0


# ---------------------------------------------------------------------------
# Wochenend-/Feiertags-Filter für Durchschnitts- & Trendberechnungen.
# Summen, Pies und Daily-Breakdown bleiben unverändert.
# ---------------------------------------------------------------------------


def _filter_complete_sessions(data: pl.DataFrame, keep_session) -> pl.DataFrame:
    """Filtert Events **sessionweise** statt eventweise.

    Events werden je (User, Projekt) per LIFO gepaart (kanonisch, identisch
    zur Anzeige — siehe :func:`db_helper.pair_sessions_lifo`). ``keep_session``
    erhält den Anker-Zeitstempel einer Session (den Start; bei verwaisten
    Stops den Stop) und entscheidet, ob **beide** Events des Paares behalten
    werden. So kann der Filter nie eine Paar-Hälfte verwerfen und die Paarung
    nachgelagerter Berechnungen verschieben (z. B. bei Mitternachts-Sessions
    am Bereichsrand).
    """
    if data.is_empty():
        return data
    keep_mask = [True] * data.height
    data_idx = data.with_row_index("_row_idx")
    for _key, group in data_idx.partition_by(["user", "project"], as_dict=True).items():
        rows = list(group.select(["_row_idx", "event_type", "timestamp"]).iter_rows())
        events = [(etype, ts) for _idx, etype, ts in rows if etype in ("start", "stop") and ts is not None]
        # Verworfene Sessions als Multimenge (event_type, timestamp) zählen —
        # identische Events sind austauschbar, die Zuordnung ist damit exakt.
        drop_counts: dict[tuple, int] = {}
        for start_ts, stop_ts in pair_sessions_lifo(events):
            anchor = start_ts if start_ts is not None else stop_ts
            if keep_session(anchor):
                continue
            for etype, ts in (("start", start_ts), ("stop", stop_ts)):
                if ts is not None:
                    key = (etype, ts)
                    drop_counts[key] = drop_counts.get(key, 0) + 1
        for row_idx, etype, ts in rows:
            if ts is None:
                continue
            if etype in ("start", "stop"):
                key = (etype, ts)
                if drop_counts.get(key, 0) > 0:
                    drop_counts[key] -= 1
                    keep_mask[row_idx] = False
            elif not keep_session(ts):
                keep_mask[row_idx] = False
    return data.filter(pl.Series(keep_mask))


def _filter_workdays(
    data: pl.DataFrame,
    *,
    country: str = "DE",
    subdiv: str | None = None,
    include_holidays: bool = True,
    count_weekend_work: bool = False,
) -> pl.DataFrame:
    """Filtert **Sessions** auf Werktage. ``count_weekend_work=True`` umgeht den Filter.

    Gefiltert wird sessionweise (Zuordnung über den Session-Start), nicht
    eventweise: Start und Stop eines Paares bleiben immer zusammen, damit
    sich die LIFO-Paarung nachgelagerter Berechnungen nicht verschiebt.
    """
    if data.is_empty() or count_weekend_work:
        return data

    def _keep(ts) -> bool:
        return not is_non_workday(ts, country=country, subdiv=subdiv, include_holidays=include_holidays)

    try:
        return _filter_complete_sessions(data, _keep)
    except Exception:  # noqa: BLE001
        # Sichtbar scheitern statt still UNGEFILTERTE Daten liefern — die
        # Zahlen wandern ins Firmensystem; leere Charts + Log-Traceback sind
        # dem stillen Falschwert vorzuziehen.
        logger.exception("Sessionweiser Filter fehlgeschlagen — liefere leeres Ergebnis.")
        return data.clear()


def filter_sessions_by_date_range(
    data: pl.DataFrame,
    start_date: str | None,
    end_date: str | None,
) -> pl.DataFrame:
    """Filtert Events sessionweise auf einen Datumsbereich (``YYYY-MM-DD``).

    Eine Session gehört per **Start-Zeitstempel** zu einem Tag; Start und
    Stop werden gemeinsam behalten oder verworfen. Gedacht als Ersatz für
    eventweise ``date``-Spalten-Filter (die bei Mitternachts-Sessions am
    Bereichsrand eine Paar-Hälfte abschneiden und die Paarung verschieben).
    """
    if data.is_empty() or (not start_date and not end_date):
        return data

    def _keep(ts) -> bool:
        day = ts.strftime("%Y-%m-%d")
        if start_date and day < start_date:
            return False
        return not (end_date and day > end_date)

    try:
        return _filter_complete_sessions(data, _keep)
    except Exception:  # noqa: BLE001
        # Sichtbar scheitern statt still UNGEFILTERTE Daten liefern — die
        # Zahlen wandern ins Firmensystem; leere Charts + Log-Traceback sind
        # dem stillen Falschwert vorzuziehen.
        logger.exception("Sessionweiser Filter fehlgeschlagen — liefere leeres Ergebnis.")
        return data.clear()


def _workday_settings() -> dict:
    """Liest Workday-Einstellungen aus der Config (mit Defaults)."""
    cfg = load_config()
    return {
        "country": cfg.get("holiday_country", "DE") or "DE",
        "subdiv": (cfg.get("holiday_subdiv") or "") or None,
        "include_holidays": bool(cfg.get("include_holidays_in_exclusion", True)),
        "count_weekend_work": bool(cfg.get("count_weekend_work", False)),
        "exclude_weekends_in_averages": bool(cfg.get("exclude_weekends_in_averages", True)),
    }


def _apply_workday_filter(data: pl.DataFrame, override_count_weekend_work: bool | None = None) -> pl.DataFrame:
    """Wendet den Workday-Filter an. Ein expliziter UI-Override gewinnt IMMER.

    ``override_count_weekend_work`` kommt vom Dashboard-Schalter
    "Wochenenden einbeziehen" (``True``/``False``); die Config-Flags
    (``exclude_weekends_in_averages``, ``count_weekend_work``) liefern nur den
    **Default**, wenn kein Override (``None``) übergeben wird. Früher wurde bei
    ``exclude_weekends_in_averages=False`` der Override ignoriert — der
    Schalter war dann wirkungslos.
    """
    s = _workday_settings()
    if override_count_weekend_work is not None:
        count_weekend = bool(override_count_weekend_work)
    else:
        # Kein Override: Config entscheidet. Ist das Ausschließen von
        # Wochenenden in Durchschnitten deaktiviert, bleibt alles ungefiltert.
        if not s["exclude_weekends_in_averages"]:
            return data
        count_weekend = s["count_weekend_work"]
    return _filter_workdays(
        data,
        country=s["country"],
        subdiv=s["subdiv"],
        include_holidays=s["include_holidays"],
        count_weekend_work=count_weekend,
    )


def calculate_hours_per_project(data):
    """Calculates total hours per project for each user."""
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "project", "timestamp"])
    hours = []
    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        hours.append({"user": user, "project": project, "total_hours": _merged_total_hours(group)})
    return pl.DataFrame(hours)


def calculate_total_hours_per_user(data):
    """Calculates total hours per user."""
    if data.is_empty():
        return pl.DataFrame(), ""
    data = data.sort(["user", "timestamp"])
    min_ts = data.select(pl.col("timestamp").min()).to_series()[0]
    max_ts = data.select(pl.col("timestamp").max()).to_series()[0]
    date_range = ""
    if min_ts and max_ts:
        date_range = f"{min_ts.strftime('%Y-%m-%d %H:%M:%S')} - {max_ts.strftime('%Y-%m-%d %H:%M:%S')}"

    total_hours = []
    for user in _unique_list(data, "user"):
        if user == "users":
            continue
        # Paarung immer je (User, Projekt) — projektübergreifendes Paaren
        # würde parallele Projekte falsch verketten.
        user_data = data.filter(pl.col("user") == user)
        total_hours_user = sum(
            _merged_total_hours(group) for group in user_data.partition_by(["project"], as_dict=True).values()
        )
        total_hours.append({"user": user, "total_hours": total_hours_user})

    return pl.DataFrame(total_hours), date_range


def calculate_average_hours_per_user(data, count_weekend_work: bool | None = None):
    """Calculates average hours per user."""
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "timestamp"])
    average_hours = []

    for user in _unique_list(data, "user"):
        if user == "users":
            continue
        group = data.filter(pl.col("user") == user)
        # Paarung je (User, Projekt), Summe über die Projekte des Users.
        total_hours_user = sum(
            _merged_total_hours(project_group)
            for project_group in group.partition_by(["project"], as_dict=True).values()
        )
        if total_hours_user <= 0:
            average_hours.append({"user": user, "average_hours": 0})
            continue
        # Nenner: nur Tage mit SESSION-STARTS. Der sessionweise Wochenend-
        # Filter behält Mitternachts-Paare komplett — der Stop-Tag einer
        # Übernacht-Session ist aber kein zusätzlicher Arbeitstag und würde
        # den Durchschnitt sonst drücken (Session-Anker = Start-Tag).
        num_days = max(
            1,
            group.filter(pl.col("event_type") == "start").select(pl.col("date").unique()).height,
        )
        average_hours_user = total_hours_user / num_days
        average_hours.append({"user": user, "average_hours": average_hours_user})

    return pl.DataFrame(average_hours)


def calculate_average_hours_per_period(data, period_days, count_weekend_work: bool | None = None):
    """Kalenderbasierter Perioden-Durchschnitt der Stunden je User.

    Semantik: Gesamtstunden geteilt durch die Anzahl der Perioden im
    **Kalender-Zeitraum** (erster bis letzter Zeitstempel des Users,
    inklusive), nicht durch die Zahl der Tage mit Einträgen. Nur Tage mit
    Einträgen zu zählen würde den Schnitt systematisch aufblähen (z. B.
    21 aktive Tage über 29 Kalendertage: ~+40 % pro Woche).

    Args:
        period_days: Periodenlänge in Tagen (7 = Woche, 30 = Monat, ...).
    """
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "timestamp"])
    average_hours = []
    for user in _unique_list(data, "user"):
        if user == "users":
            continue
        group = data.filter(pl.col("user") == user)
        # Paarung je (User, Projekt), Summe über die Projekte des Users.
        total_hours = sum(
            _merged_total_hours(project_group)
            for project_group in group.partition_by(["project"], as_dict=True).values()
        )
        # Kalender-Spanne (inkl. Randtage) statt Anzahl aktiver Tage.
        min_ts = group.select(pl.col("timestamp").min()).to_series()[0]
        max_ts = group.select(pl.col("timestamp").max()).to_series()[0]
        span_days = (max_ts.date() - min_ts.date()).days + 1 if min_ts and max_ts else 1
        num_periods = max(1.0, span_days / period_days)
        average_hours_user = total_hours / num_periods
        average_hours.append({"user": user, "average_hours": average_hours_user, "period_days": period_days})
    return pl.DataFrame(average_hours)


def calculate_project_time_stats(data):
    """
    Berechnet detaillierte Zeitstatistiken pro Projekt und User.

    Features:
    - Durchschnittliche Arbeitszeit pro Projekt
    - Minimale und maximale Arbeitsdauer
    - Standardabweichung für Konsistenzanalyse

    Args:
        data (pl.DataFrame): DataFrame mit Spalten [user, project, event_type, timestamp]

    Returns:
        pl.DataFrame: Statistiken mit Spalten [user, project, avg_hours, min_hours, max_hours, std_hours]
    """
    if data.is_empty():
        return pl.DataFrame()

    data = data.sort(["user", "project", "timestamp"])
    stats_rows = []

    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        durations = _paired_durations_hours(group)
        if durations:
            std_hours = float(np.std(durations, ddof=1)) if len(durations) > 1 else 0.0
            stats_rows.append(
                {
                    "user": user,
                    "project": project,
                    "avg_hours": sum(durations) / len(durations),
                    "min_hours": min(durations),
                    "max_hours": max(durations),
                    "std_hours": std_hours,
                }
            )

    return pl.DataFrame(stats_rows)


def calculate_daily_project_hours(data):
    """
    Berechnet die tägliche Arbeitszeit pro User und Projekt.

    Sessions, die über Mitternacht laufen, werden anteilig auf beide Tage
    verteilt: 23:50 → 00:30 ergibt 10 min auf Tag A und 30 min auf Tag B.

    Args:
        data (pl.DataFrame): DataFrame mit Spalten [user, project, event_type, timestamp, date]

    Returns:
        pl.DataFrame: Tägliche Stunden mit Spalten [user, date, project, hours]
    """
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "project", "timestamp"])
    # Aggregiere Teil-Intervalle in dict mit Schlüssel (user, day_str, project).
    # ``day_str`` wird hier konsequent aus dem Zeitstempel abgeleitet, nicht
    # aus der gespeicherten ``date``-Spalte (siehe Bugfix Tag-Zuordnung).
    bucket: dict[tuple, list] = {}

    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        for start_ts, stop_ts in _paired_sessions(group):
            if stop_ts <= start_ts:
                continue
            _split_session_into_days(bucket, user, project, start_ts, stop_ts)

    if not bucket:
        return pl.DataFrame()
    # Vereinigung der Intervalle pro Tag — identisch zur Semantik von
    # ``db_helper.calculate_daily_duration`` (kein Doppelzählen, 24h-Deckel).
    rows = [
        {"user": user, "date": day, "project": project, "hours": merge_intervals_seconds(intervals) / 3600.0}
        for (user, day, project), intervals in bucket.items()
    ]
    return pl.DataFrame(rows)


def _split_session_into_days(bucket, user, project, start_ts, stop_ts):
    """Schneidet eine Session an Tagesgrenzen und sammelt die Teil-Intervalle je Tag."""
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    cursor = start_ts
    end = stop_ts
    while cursor < end:
        day_end = _dt.combine(cursor.date(), _dt.min.time()) + _td(days=1)
        chunk_end = min(day_end, end)
        if chunk_end > cursor:
            day_str = cursor.strftime("%Y-%m-%d")
            key = (user, day_str, project)
            bucket.setdefault(key, []).append((cursor, chunk_end))
        cursor = chunk_end


def available_iso_weeks(data: pl.DataFrame) -> list[tuple[int, int]]:
    """Sortierte ISO-Kalenderwochen ``(iso_year, iso_week)``, die in den Daten vorkommen.

    Grundlage sind die Tages-Daten aus :func:`calculate_daily_project_hours`
    (Mitternachts-Split inklusive) — eine Session, die in eine neue Woche
    hineinragt, macht auch diese Woche verfügbar.
    """
    if data is None or data.is_empty():
        return []
    daily = calculate_daily_project_hours(data.filter(pl.col("user") != "users") if not data.is_empty() else data)
    if daily.is_empty():
        return []
    weeks: set[tuple[int, int]] = set()
    for day in daily.select(pl.col("date").unique()).to_series().to_list():
        iso = datetime.strptime(day, "%Y-%m-%d").date().isocalendar()
        weeks.add((iso.year, iso.week))
    return sorted(weeks)


def calculate_week_matrix(data: pl.DataFrame, iso_year: int, iso_week: int) -> dict:
    """KW-Report-Daten: Projekt × Wochentag-Matrix einer ISO-Kalenderwoche.

    Wochen sind ISO-Wochen (Montag bis Sonntag). Basis ist
    :func:`calculate_daily_project_hours` (LIFO-Paarung, Mitternachts-Split,
    Intervall-Union) — eine Session Di 23:00 → Mi 01:00 zählt also anteilig
    auf beide Tage. Vereinfachung für den Ein-User-Fall: Es wird über ALLE
    User in ``data`` aggregiert (das Dashboard filtert vorgelagert).

    Rückgabe:
    {
      "days": ["2026-07-06", ..., "2026-07-12"],           # ISO-Daten Mo..So der KW
      "projects": ["Backend API", ...],                      # sortiert, nur Projekte mit Stunden in der KW
      "hours": {(project, iso_date): float},                 # Dezimalstunden > 0
      "day_totals": {iso_date: float},                       # alle 7 Tage, 0.0 ohne Einträge
      "project_totals": {project: float},
      "total": float,
    }
    """
    from datetime import date as _date
    from datetime import timedelta as _td

    monday = _date.fromisocalendar(int(iso_year), int(iso_week), 1)
    days = [(monday + _td(days=i)).isoformat() for i in range(7)]

    result = {
        "days": days,
        "projects": [],
        "hours": {},
        "day_totals": dict.fromkeys(days, 0.0),
        "project_totals": {},
        "total": 0.0,
    }
    if data is None or data.is_empty():
        return result

    daily = calculate_daily_project_hours(data)
    if daily.is_empty():
        return result

    week_rows = daily.filter(pl.col("user") != "users").filter(pl.col("date").is_in(days))
    hours: dict[tuple[str, str], float] = {}
    for row in week_rows.iter_rows(named=True):
        key = (row["project"], row["date"])
        hours[key] = hours.get(key, 0.0) + float(row["hours"])
    hours = {k: v for k, v in hours.items() if v > 0}

    result["hours"] = hours
    result["projects"] = sorted({project for project, _day in hours})
    for (project, day), h in hours.items():
        result["day_totals"][day] += h
        result["project_totals"][project] = result["project_totals"].get(project, 0.0) + h
    result["total"] = sum(result["project_totals"].values())
    return result


def calculate_project_switches(data):
    """
    Analysiert Projektwechsel und Pausen zwischen Projekten.

    Features:
    - Anzahl der Projektwechsel pro Tag
    - Pausendauer zwischen Projekten
    - Wechselmuster zwischen spezifischen Projekten

    Beispiel:
    - User wechselt von Projekt A zu B mit 30 Minuten Pause
    - Identifikation häufiger Projektkombinationen

    Args:
        data (pl.DataFrame): Arbeitszeitdaten

    Returns:
        pl.DataFrame: Wechselstatistiken mit [user, date, from_project, to_project, pause_minutes]
    """
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "date", "timestamp"])
    switches = []

    for (user, date), group in data.partition_by(["user", "date"], as_dict=True).items():
        events = group.sort("timestamp")
        current_project = None
        last_stop = None

        for row in events.iter_rows(named=True):
            if row["event_type"] == "start":
                if current_project and current_project != row["project"] and last_stop is not None:
                    pause_minutes = (row["timestamp"] - last_stop).total_seconds() / 60
                    switches.append(
                        {
                            "user": user,
                            "date": date,
                            "from_project": current_project,
                            "to_project": row["project"],
                            "pause_minutes": pause_minutes,
                            "switch_time": row["timestamp"].strftime("%H:%M"),
                        }
                    )
                current_project = row["project"]
            else:
                last_stop = row["timestamp"]

    return pl.DataFrame(switches)


def analyze_daily_patterns(data):
    """
    Untersucht tageszeitliche Arbeitsmuster.

    Features:
    - Durchschnittliche Startzeiten pro Projekt
    - Häufigste Arbeitszeiten
    - Produktivitätsmuster über den Tag

    Mustertypen:
    1. Frühe Starter (vor 8 Uhr)
    2. Kernzeitarbeiter (9-17 Uhr)
    3. Spätarbeiter (nach 17 Uhr)

    Args:
        data (pl.DataFrame): Arbeitszeitdaten

    Returns:
        pl.DataFrame: Tagesmuster mit [user, project, avg_start_hour,
            most_common_start_hour, earliest_start, latest_start].
            ``avg_start_hour``, ``earliest_start`` und ``latest_start`` sind
            **Dezimalstunden** (9:30 → 9.5) — volle Stunden zu mitteln wäre
            systematisch ~30 min zu früh. ``most_common_start_hour`` bleibt
            die volle Stunde (Modus über Stunden-Bins).
    """
    if data.is_empty():
        return pl.DataFrame()
    # Timestamps are already parsed as Datetime by read_database().
    # If they're still strings (e.g. from CSV), parse them.
    ts_dtype = data.schema.get("timestamp")
    if ts_dtype is None or not str(ts_dtype).startswith("Datetime"):
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]
        data = data.with_columns(
            pl.coalesce(
                [pl.col("timestamp").cast(pl.Utf8).str.strptime(pl.Datetime, fmt, strict=False) for fmt in formats]
            ).alias("timestamp")
        )
        data = data.filter(pl.col("timestamp").is_not_null())
    # Dezimalstunden (9:30 → 9.5) für Durchschnitt/Min/Max; volle Stunde nur
    # für den Modus (most_common_start_hour).
    data = data.with_columns(
        pl.col("timestamp").dt.hour().alias("hour"),
        (pl.col("timestamp").dt.hour() + pl.col("timestamp").dt.minute() / 60.0).alias("decimal_hour"),
    )
    patterns = []

    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        starts = group.filter(pl.col("event_type") == "start")
        if starts.is_empty():
            patterns.append(
                {
                    "user": user,
                    "project": project,
                    "avg_start_hour": None,
                    "most_common_start_hour": None,
                    "earliest_start": None,
                    "latest_start": None,
                }
            )
            continue

        hours = [h for h in starts.select("hour").to_series().to_list() if h is not None]
        decimal_hours = [h for h in starts.select("decimal_hour").to_series().to_list() if h is not None]
        most_common = max(set(hours), key=hours.count) if hours else None
        patterns.append(
            {
                "user": user,
                "project": project,
                "avg_start_hour": float(np.mean(decimal_hours)) if decimal_hours else None,
                "most_common_start_hour": most_common,
                "earliest_start": min(decimal_hours) if decimal_hours else None,
                "latest_start": max(decimal_hours) if decimal_hours else None,
            }
        )

    return pl.DataFrame(patterns)


def analyze_time_series(data, count_weekend_work: bool | None = None):
    """Analysiert Zeitreihen-Muster in den Arbeitsdaten.

    Die Tagesstunden werden aus den Zeitstempeln der LIFO-gepaarten Sessions
    abgeleitet (``calculate_daily_project_hours``) statt aus der pro Event
    gespeicherten ``date``-Spalte: Bei Mitternachts-Sessions tragen Start und
    Stop verschiedene ``date``-Werte — ein Partitionieren danach würde die
    Paarung zerreißen. So wird die Session korrekt anteilig auf beide Tage
    verteilt.

    Semantik der Durchschnitte: **Ø je gearbeitetem Tag** (bedingter
    Mittelwert) — Tage ohne Einträge fließen nicht als 0 ein. Die Spalte
    ``n_days`` (Stichprobengröße je Gruppe) macht das sichtbar, z. B. für
    Hover-Texte.

    Returns:
        tuple: ``(daily_df, weekly_avg, weekday_avg)``
            - daily_df: [user, date, weekday, iso_year, iso_week, week, hours]
            - weekly_avg: [user, iso_year, iso_week, week, hours, n_days] —
              gruppiert nach **(ISO-Jahr, ISO-Woche)**, chronologisch sortiert.
              ``week`` ist ein eindeutiges Label wie ``"2026-KW01"`` (die
              Wochennummer allein würde KW1/2025 mit KW1/2026 vermischen).
            - weekday_avg: [user, weekday, hours, n_days] — Mo..So sortiert.
    """
    if data.is_empty():
        return pl.DataFrame(), pl.DataFrame(), pl.DataFrame()

    daily = calculate_daily_project_hours(data)
    if daily.is_empty():
        return pl.DataFrame(), pl.DataFrame(), pl.DataFrame()

    per_day = (
        daily.filter(pl.col("user") != "users")
        .group_by(["user", "date"])
        .agg(pl.col("hours").sum().alias("hours"))
        .sort(["user", "date"])
    )

    _WDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    daily_hours = []
    for row in per_day.iter_rows(named=True):
        date_obj = datetime.strptime(row["date"], "%Y-%m-%d")
        iso = date_obj.isocalendar()
        daily_hours.append(
            {
                "user": row["user"],
                "date": row["date"],
                "weekday": _WDAY_DE[date_obj.weekday()],
                "iso_year": iso.year,
                "iso_week": iso.week,
                # Eindeutiges, chronologisch sortierbares Wochen-Label —
                # die Wochennummer allein würde Jahre vermischen.
                "week": f"{iso.year}-KW{iso.week:02d}",
                "hours": row["hours"],
            }
        )

    daily_df = pl.DataFrame(daily_hours)
    if daily_df.is_empty():
        return daily_df, pl.DataFrame(), pl.DataFrame()

    # Ø je gearbeitetem Tag; n_days = Zahl der eingeflossenen Tage (Ehrlichkeit
    # der bedingten Mittelwerte, s. Docstring).
    weekly_avg = (
        daily_df.group_by(["user", "iso_year", "iso_week", "week"])
        .agg(pl.col("hours").mean().alias("hours"), pl.len().alias("n_days"))
        .sort(["user", "iso_year", "iso_week"])
    )
    weekday_avg = daily_df.group_by(["user", "weekday"]).agg(
        pl.col("hours").mean().alias("hours"), pl.len().alias("n_days")
    )
    weekday_order = {"Mo": 1, "Di": 2, "Mi": 3, "Do": 4, "Fr": 5, "Sa": 6, "So": 7}
    weekday_avg = (
        weekday_avg.with_columns(
            pl.col("weekday").map_elements(lambda d: weekday_order.get(d, 999)).alias("weekday_order")
        )
        .sort(["user", "weekday_order"])
        .drop("weekday_order")
    )

    return daily_df, weekly_avg, weekday_avg


def perform_cluster_analysis(data):
    """
    Führt Clusteranalyse der Arbeitsmuster durch.

    Analysierte Merkmale:
    1. Durchschnittliche Startzeit
    2. Projektwechselhäufigkeit
    3. Arbeitsdauer

    Clustering-Methode:
    - K-Means mit automatischer k-Bestimmung
    - Standardisierte Features
    - Ellenbogenmethode für optimales k

    Cluster-Interpretation:
    - "Frühe Konzentrierte": Früher Start, wenig Wechsel
    - "Flexible Wechsler": Mittlere Startzeit, viele Wechsel
    - "Späte Beständige": Später Start, moderate Wechsel

    Args:
        data (pl.DataFrame): Arbeitszeitdaten

    Returns:
        tuple: (features_df, cluster_profiles)
            - features_df: DataFrame mit User-Features und Cluster-Zuordnung
            - cluster_profiles: Liste der Cluster-Charakteristiken
    """
    if data.is_empty():
        return pl.DataFrame(), []

    # Lokale Imports: sklearn kostet >1s Startzeit und wird nur hier gebraucht
    # (Muster wie der statsmodels-Import in perform_anova_analysis).
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    # Feature-Extraktion für Clustering
    user_features = []
    for user in _unique_list(data, "user"):
        if user == "users":
            continue
        user_data = data.filter(pl.col("user") == user)

        start_times = user_data.filter(pl.col("event_type") == "start").select("timestamp").to_series().to_list()
        avg_start_hour = float(np.mean([t.hour for t in start_times])) if start_times else 0.0

        num_days = max(1, user_data.select(pl.col("date").unique()).height)
        switches_per_day = calculate_project_switches(user_data).height / num_days

        avg_hours_df = calculate_average_hours_per_user(user_data)
        avg_row = avg_hours_df.filter(pl.col("user") == user)
        avg_duration = avg_row["average_hours"][0] if avg_row.height > 0 else 0

        user_features.append(
            {
                "user": user,
                "avg_start_hour": avg_start_hour,
                "switches_per_day": switches_per_day,
                "avg_duration": avg_duration,
            }
        )

    features_df = pl.DataFrame(user_features)

    if features_df.is_empty() or features_df.height < 2:
        return features_df, []

    # Standardisierung der Features
    scaler = StandardScaler()
    X = scaler.fit_transform(features_df.select(["avg_start_hour", "switches_per_day", "avg_duration"]).to_numpy())

    # Clustering (optimal k wird automatisch bestimmt)
    k_range = range(2, min(5, len(X) + 1))
    inertias = []

    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)

    # Optimales k durch Ellenbogenmethode
    if len(inertias) < 2:
        optimal_k = k_range[0] if k_range else 2
    else:
        optimal_k = k_range[np.argmin(np.diff(inertias)) + 1]

    # Finales Clustering
    kmeans = KMeans(n_clusters=optimal_k, random_state=42)
    clusters = kmeans.fit_predict(X)
    features_df = features_df.with_columns(pl.Series("cluster", clusters))

    # Cluster-Charakteristiken
    cluster_profiles = []
    for cluster in range(optimal_k):
        cluster_data = features_df.filter(pl.col("cluster") == cluster)
        profile = {
            "cluster": cluster,
            "size": cluster_data.height,
            "avg_start": float(cluster_data["avg_start_hour"].mean()),
            "avg_switches": float(cluster_data["switches_per_day"].mean()),
            "avg_duration": float(cluster_data["avg_duration"].mean()),
            "users": cluster_data["user"].to_list(),
        }
        cluster_profiles.append(profile)

    return features_df, cluster_profiles


def perform_regression_analysis(data):
    """
    Führt Regressionsanalyse für Arbeitsdauer durch.

    Prädiktoren:
    - User-ID (kategorisch, One-Hot)
    - Projekt (kategorisch, One-Hot)
    - Startstunde (numerisch, volle Stunde des Session-Starts)
    - Wochentag (kategorisch, One-Hot)

    Modelldetails:
    - Lineare Regression
    - One-Hot-Encoding nur für die kategorischen Variablen
    - R² ist die **In-Sample-Modellanpassung** (auf den Trainingsdaten),
      keine Vorhersagegenauigkeit — es gibt kein Holdout/keine
      Kreuzvalidierung. Deshalb liefert das Ergebnis das ehrliche Label
      ``r2_label`` ("Modellanpassung (in-sample R²)") mit.

    Anwendungsfälle:
    1. Explorative Identifikation wichtiger Einflussfaktoren
    2. Grobe Einordnung, wie viel Varianz die Prädiktoren erklären

    Args:
        data (pl.DataFrame): Arbeitszeitdaten

    Returns:
        dict: Regressionsergebnisse mit model, importance, r2_score,
            r2_label, actual_vs_predicted
    """
    if data.is_empty():
        return {}

    # Lokaler Import: sklearn nur bei Bedarf laden (Startzeit).
    from sklearn.linear_model import LinearRegression

    # Feature-Vorbereitung
    work_sessions = []

    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        if user == "users":
            continue

        for start, stop in _paired_sessions(group):
            duration = (stop - start).total_seconds() / 3600
            work_sessions.append(
                {
                    "user": user,
                    "project": project,
                    "start_hour": start.hour,
                    "weekday": start.weekday(),
                    "duration": duration,
                }
            )

    sessions_df = pl.DataFrame(work_sessions)
    if sessions_df.is_empty():
        return {}

    # Dummy-Variablen NUR für die kategorischen Features — start_hour bleibt
    # numerisch (wie im Docstring beschrieben).
    X_df = sessions_df.select(["user", "project", "start_hour", "weekday"]).to_dummies(
        columns=["user", "project", "weekday"]
    )
    X = X_df.to_numpy()
    y = sessions_df["duration"].to_numpy()

    # Regression
    model = LinearRegression()
    model.fit(X, y)

    # Feature Importance
    importance = pl.DataFrame(
        {
            "feature": X_df.columns,
            "importance": np.abs(model.coef_),
        }
    ).sort("importance", descending=True)

    # Modellperformance
    predictions = model.predict(X)
    r2_score = model.score(X, y)

    return {
        "model": model,
        "importance": importance,
        "r2_score": r2_score,
        # Ehrliches Label: in-sample-Anpassung, keine Vorhersagegenauigkeit.
        "r2_label": "Modellanpassung (in-sample R²)",
        "actual_vs_predicted": pl.DataFrame(
            {
                "actual": y,
                "predicted": predictions,
            }
        ),
    }


def perform_anova_analysis(data):
    """
    Führt ANOVA-Tests für Gruppenunterschiede durch.

    Analysierte Unterschiede (unabhängig voneinander gegated):
    1. Zwischen Usern — nur wenn ≥2 User vorhanden sind
    2. Zwischen Projekten — nur wenn ≥2 Projekte vorhanden sind

    Im (realen) Ein-User-Fall enthält das Ergebnis also nur ``project_anova``;
    ``user_anova`` fehlt dann. Konsumenten müssen die Schlüssel einzeln prüfen.

    Statistische Tests:
    - Einfaktorielle ANOVA
    - Tukey's HSD Post-hoc Test

    Ehrlichkeits-Hinweis: Die Ergebnisse sind **explorativ**. Die
    Beobachtungseinheiten sind einzelne Sessions desselben Users/Projekts und
    damit nicht unabhängig (Messwiederholung) — die p-Werte sind formal nicht
    belastbar und nur als grobe Orientierung zu lesen.

    Args:
        data (pl.DataFrame): Arbeitszeitdaten

    Returns:
        dict: ANOVA-Ergebnisse; Schlüssel ``user_anova`` und/oder
            ``project_anova`` (je mit f_statistic, p_value, tukey), nur
            sofern die jeweilige Analyse möglich war. Leeres dict sonst.
    """
    if data.is_empty():
        return {}

    work_durations = []

    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        if user == "users":
            continue

        durations = _paired_durations_hours(group)
        if not durations:
            continue

        work_durations.extend(
            [
                {
                    "user": user,
                    "project": project,
                    "duration": float(duration),
                }
                for duration in durations
            ]
        )

    durations_df = pl.DataFrame(work_durations)

    try:
        if durations_df.is_empty():
            return {}

        # Lokale Imports: scipy/statsmodels nur bei Bedarf laden (Startzeit).
        from scipy import stats
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        results = {}

        # ANOVA zwischen Usern — braucht ≥2 User. Getrennt von der
        # Projekt-ANOVA gegated: Im Ein-User-Fall (Normalfall dieser App)
        # bleibt die Projekt-Analyse sonst grundlos leer.
        if durations_df["user"].n_unique() >= 2:
            user_groups = [
                group["duration"].to_numpy() for group in durations_df.partition_by("user", as_dict=True).values()
            ]
            f_stat_users, p_value_users = stats.f_oneway(*user_groups)
            tukey_users = pairwise_tukeyhsd(durations_df["duration"].to_numpy(), durations_df["user"].to_numpy())
            results["user_anova"] = {
                "f_statistic": float(f_stat_users),
                "p_value": float(p_value_users),
                "tukey": tukey_users,
            }

        # ANOVA zwischen Projekten — braucht ≥2 Projekte (User-Anzahl egal).
        if durations_df["project"].n_unique() >= 2:
            project_groups = [
                group["duration"].to_numpy() for group in durations_df.partition_by("project", as_dict=True).values()
            ]
            f_stat_projects, p_value_projects = stats.f_oneway(*project_groups)
            tukey_projects = pairwise_tukeyhsd(durations_df["duration"].to_numpy(), durations_df["project"].to_numpy())
            results["project_anova"] = {
                "f_statistic": float(f_stat_projects),
                "p_value": float(p_value_projects),
                "tukey": tukey_projects,
            }

        return results
    except Exception as e:
        print(f"Fehler in ANOVA-Analyse: {str(e)}")
        return None


# ---------------------------------------------------------------------------
# Übersichts-Berechnung für den neuen Dashboard-Tab "Übersicht".
# Liefert einen reinen Daten-Dict — keine Plotly-Abhängigkeit hier.
# ---------------------------------------------------------------------------


def calculate_overview(data: pl.DataFrame) -> dict:
    """Aggregiert Eckdaten über alle Events für die Übersichts-Seite.

    Gibt Felder zurück:
        projects, users, total_hours, date_min, date_max,
        n_workdays_with_entries, n_sessions, data_quality{
            open_sessions, weekend_entries, holiday_entries
        }
    """
    empty = {
        "projects": [],
        "users": [],
        "total_hours": 0.0,
        "date_min": "",
        "date_max": "",
        "n_workdays_with_entries": 0,
        "n_sessions": 0,
        "data_quality": {"open_sessions": 0, "weekend_entries": 0, "holiday_entries": 0},
    }
    if data is None or data.is_empty():
        return empty

    s = _workday_settings()

    # Projekte & Benutzer (defensiver Filter gegen "users"-Header).
    projects = sorted(p for p in _unique_list(data, "project") if p)
    users = sorted(u for u in _unique_list(data, "user") if u and u != "users")

    # Gesamtstunden + Sessions (LIFO-gepaart) und offene Starts (open sessions).
    total_hours = 0.0
    n_sessions = 0
    open_sessions = 0
    for (user, _project), group in data.partition_by(["user", "project"], as_dict=True).items():
        if user == "users":
            continue
        events = [
            (etype, ts)
            for etype, ts in zip(group["event_type"].to_list(), group["timestamp"].to_list(), strict=True)
            if ts is not None
        ]
        intervals = []
        for start_ts, stop_ts in pair_sessions_lifo(events):
            if start_ts is not None and stop_ts is not None:
                intervals.append((start_ts, stop_ts))
            elif start_ts is not None:
                open_sessions += 1
        n_sessions += len(intervals)
        total_hours += merge_intervals_seconds(intervals) / 3600.0

    # Zeitraum.
    try:
        min_ts = data.select(pl.col("timestamp").min()).to_series()[0]
        max_ts = data.select(pl.col("timestamp").max()).to_series()[0]
        # Einheitliches Anzeigeformat der App: TT.MM.JJJJ
        date_min = min_ts.strftime("%d.%m.%Y") if min_ts else ""
        date_max = max_ts.strftime("%d.%m.%Y") if max_ts else ""
    except Exception:  # noqa: BLE001
        date_min, date_max = "", ""

    # Arbeitstage = unique Datums-Spalten-Einträge.
    try:
        n_days = data.select(pl.col("date").unique()).height
    except Exception:  # noqa: BLE001
        n_days = 0

    # Wochenend-/Feiertags-Eintragszahl auf timestamp-Ebene.
    weekend_entries = 0
    holiday_entries = 0
    try:
        timestamps = data.select("timestamp").to_series().to_list()
        for ts in timestamps:
            if ts is None:
                continue
            if hasattr(ts, "weekday") and ts.weekday() >= 5:
                weekend_entries += 1
            else:
                from utils import is_holiday  # lokal, vermeidet Zirkular-Import oben

                if is_holiday(ts, country=s["country"], subdiv=s["subdiv"]):
                    holiday_entries += 1
    except Exception:  # noqa: BLE001
        pass

    return {
        "projects": projects,
        "users": users,
        "total_hours": round(total_hours, 2),
        "date_min": date_min,
        "date_max": date_max,
        "n_workdays_with_entries": int(n_days),
        "n_sessions": int(n_sessions),
        "data_quality": {
            "open_sessions": int(open_sessions),
            "weekend_entries": int(weekend_entries),
            "holiday_entries": int(holiday_entries),
        },
    }


# ---------------------------------------------------------------------------
# Zusätzliche Auswertungen: Pausen, Heatmap, Verteilungen
# ---------------------------------------------------------------------------
def calculate_break_statistics(breaks_df, events_df) -> dict:
    """Aggregiert Pausen (break_events) und stellt sie der Arbeitszeit gegenüber.

    Args:
        breaks_df: DataFrame aus ``utils.read_break_events`` (Spalten u.a.
            ``date``, ``duration_seconds``, ``break_kind``).
        events_df: Arbeits-Events (für die Arbeitsstunden pro Tag).

    Returns:
        dict mit ``per_day`` ([date, work_hours, break_hours]),
        ``by_kind`` ([break_kind, hours]) und ``totals``
        ({work_hours, break_hours, ratio}).
    """
    # Arbeitsstunden pro Tag (über alle Projekte/User summiert).
    work_per_day = pl.DataFrame(schema={"date": pl.Utf8, "work_hours": pl.Float64})
    if events_df is not None and not events_df.is_empty():
        daily = calculate_daily_project_hours(events_df)
        if not daily.is_empty():
            work_per_day = daily.group_by("date").agg(pl.col("hours").sum().alias("work_hours")).sort("date")

    break_per_day = pl.DataFrame(schema={"date": pl.Utf8, "break_hours": pl.Float64})
    by_kind = pl.DataFrame(schema={"break_kind": pl.Utf8, "hours": pl.Float64})
    total_break_hours = 0.0
    if breaks_df is not None and not breaks_df.is_empty():
        b = breaks_df.filter(pl.col("duration_seconds").is_not_null())
        if not b.is_empty():
            b = b.with_columns((pl.col("duration_seconds") / 3600.0).alias("hours"))
            break_per_day = b.group_by("date").agg(pl.col("hours").sum().alias("break_hours")).sort("date")
            by_kind = b.group_by("break_kind").agg(pl.col("hours").sum().alias("hours")).sort("break_kind")
            total_break_hours = float(b.select(pl.col("hours").sum()).to_series()[0] or 0.0)

    per_day = work_per_day.join(break_per_day, on="date", how="full", coalesce=True).sort("date")
    per_day = per_day.with_columns(
        pl.col("work_hours").fill_null(0.0),
        pl.col("break_hours").fill_null(0.0),
    )

    total_work_hours = 0.0
    if not per_day.is_empty():
        total_work_hours = float(per_day.select(pl.col("work_hours").sum()).to_series()[0] or 0.0)
    ratio = (total_break_hours / total_work_hours) if total_work_hours > 0 else 0.0

    return {
        "per_day": per_day,
        "by_kind": by_kind,
        "totals": {
            "work_hours": round(total_work_hours, 2),
            "break_hours": round(total_break_hours, 2),
            "ratio": round(ratio, 3),
        },
    }


def calculate_hour_weekday_matrix(data) -> pl.DataFrame:
    """Stunden je (Wochentag, Tagesstunde) für eine Heatmap.

    Sessions werden stundenweise anteilig verteilt (auch über Mitternacht).
    Rückgabe: DataFrame [weekday (0=Mo..6=So), hour (0..23), hours].
    """
    if data is None or data.is_empty():
        return pl.DataFrame(schema={"weekday": pl.Int64, "hour": pl.Int64, "hours": pl.Float64})
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    data = data.sort(["user", "project", "timestamp"])
    bucket: dict[tuple, float] = {}
    for (_u, _p), group in data.partition_by(["user", "project"], as_dict=True).items():
        for start_ts, stop_ts in _paired_sessions(group):
            if stop_ts <= start_ts:
                continue
            cursor = start_ts
            while cursor < stop_ts:
                hour_end = _dt.combine(cursor.date(), _dt.min.time()) + _td(hours=cursor.hour + 1)
                chunk_end = min(hour_end, stop_ts)
                seconds = (chunk_end - cursor).total_seconds()
                if seconds > 0:
                    key = (cursor.weekday(), cursor.hour)
                    bucket[key] = bucket.get(key, 0.0) + seconds / 3600.0
                cursor = chunk_end
    if not bucket:
        return pl.DataFrame(schema={"weekday": pl.Int64, "hour": pl.Int64, "hours": pl.Float64})
    rows = [{"weekday": wd, "hour": hr, "hours": h} for (wd, hr), h in bucket.items()]
    return pl.DataFrame(rows).sort(["weekday", "hour"])


def calculate_start_hour_distribution(data) -> pl.DataFrame:
    """Häufigkeit der Start-Uhrzeiten (Stunde 0..23) über alle Start-Events."""
    if data is None or data.is_empty():
        return pl.DataFrame(schema={"hour": pl.Int64, "count": pl.Int64})
    starts = data.filter(pl.col("event_type") == "start").filter(pl.col("timestamp").is_not_null())
    if starts.is_empty():
        return pl.DataFrame(schema={"hour": pl.Int64, "count": pl.Int64})
    return (
        starts.with_columns(pl.col("timestamp").dt.hour().alias("hour"))
        .group_by("hour")
        .agg(pl.len().alias("count"))
        .sort("hour")
    )


def calculate_session_duration_distribution(data) -> pl.DataFrame:
    """Liste der Session-Dauern (Stunden) über alle (User, Projekt)-Gruppen."""
    if data is None or data.is_empty():
        return pl.DataFrame(schema={"duration_hours": pl.Float64})
    data = data.sort(["user", "project", "timestamp"])
    durations: list[float] = []
    for _key, group in data.partition_by(["user", "project"], as_dict=True).items():
        durations.extend(_paired_durations_hours(group))
    durations = [d for d in durations if d > 0]
    if not durations:
        return pl.DataFrame(schema={"duration_hours": pl.Float64})
    return pl.DataFrame({"duration_hours": durations})
