"""
Statistik-Berechnungsmodul für die Zeiterfassungsanalyse.

Dieses Modul enthält Funktionen zur Analyse von Arbeitszeitdaten, einschließlich:
- Grundlegende Statistiken (Durchschnitte, Summen)
- Zeitreihenanalyse (Trends, Muster)
- Fortgeschrittene Analysen (Clustering, Regression, ANOVA)

Die Funktionen erwarten Zeitstempel im Format 'dd-mm-yyyy HH:MM:SS' und
arbeiten mit pandas DataFrames für effiziente Datenverarbeitung.
"""

from datetime import datetime

import numpy as np
import polars as pl
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

# Konstanten für Zeitkonvertierung
TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
DATE_FORMAT = "%d-%m-%Y"

def _unique_list(data, column):
    return data.select(pl.col(column).unique()).to_series().to_list()

def _paired_durations_hours(group):
    starts = group.filter(pl.col("event_type") == "start").select("timestamp").to_series().to_list()
    stops = group.filter(pl.col("event_type") == "stop").select("timestamp").to_series().to_list()
    min_length = min(len(starts), len(stops))
    if min_length == 0:
        return []
    return [
        (stops[i] - starts[i]).total_seconds() / 3600
        for i in range(min_length)
    ]

def calculate_hours_per_project(data):
    """Calculates total hours per project for each user."""
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "project", "timestamp"])
    hours = []
    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        durations = _paired_durations_hours(group)
        total_hours = sum(durations) if durations else 0
        hours.append({"user": user, "project": project, "total_hours": total_hours})
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
        group = data.filter(pl.col("user") == user)
        durations = _paired_durations_hours(group)
        total_hours_user = sum(durations) if durations else 0
        total_hours.append({"user": user, "total_hours": total_hours_user})

    return pl.DataFrame(total_hours), date_range

def calculate_average_hours_per_user(data):
    """Calculates average hours per user."""
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "timestamp"])
    average_hours = []

    for user in _unique_list(data, "user"):
        if user == "users":
            continue
        group = data.filter(pl.col("user") == user)
        durations = _paired_durations_hours(group)
        if not durations:
            average_hours.append({"user": user, "average_hours": 0})
            continue
        total_hours_user = sum(durations)
        num_days = max(1, group.select(pl.col("date").unique()).height)
        average_hours_user = total_hours_user / num_days
        average_hours.append({"user": user, "average_hours": average_hours_user})

    return pl.DataFrame(average_hours)

def calculate_average_hours_per_period(data, period_days):
    """Calculates average hours per user for a given period in days."""
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "timestamp"])
    average_hours = []
    for user in _unique_list(data, "user"):
        if user == "users":
            continue
        group = data.filter(pl.col("user") == user)
        durations = _paired_durations_hours(group)
        total_hours = sum(durations) if durations else 0
        num_days = group.select(pl.col("date").unique()).height
        num_periods = max(1, num_days / period_days)
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
            stats_rows.append({
                "user": user,
                "project": project,
                "avg_hours": sum(durations) / len(durations),
                "min_hours": min(durations),
                "max_hours": max(durations),
                "std_hours": std_hours,
            })

    return pl.DataFrame(stats_rows)

def calculate_daily_project_hours(data):
    """
    Berechnet die tägliche Arbeitszeit pro User und Projekt.

    Features:
    - Gesamtarbeitszeit pro Tag
    - Aufschlüsselung nach Projekten
    - Identifikation von Arbeitstagen

    Args:
        data (pl.DataFrame): DataFrame mit Spalten [user, project, event_type, timestamp, date]

    Returns:
        pl.DataFrame: Tägliche Stunden mit Spalten [user, date, project, hours]
    """
    if data.is_empty():
        return pl.DataFrame()
    data = data.sort(["user", "date", "project", "timestamp"])
    daily_hours = []

    for (user, date, project), group in data.partition_by(["user", "date", "project"], as_dict=True).items():
        durations = _paired_durations_hours(group)
        if durations:
            daily_hours.append({
                "user": user,
                "date": date,
                "project": project,
                "hours": sum(durations),
            })

    return pl.DataFrame(daily_hours)

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
                    switches.append({
                        "user": user,
                        "date": date,
                        "from_project": current_project,
                        "to_project": row["project"],
                        "pause_minutes": pause_minutes,
                        "switch_time": row["timestamp"].strftime("%H:%M"),
                    })
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
        pl.DataFrame: Tagesmuster mit [user, project, avg_start_hour, most_common_start_hour]
    """
    if data.is_empty():
        return pl.DataFrame()
    # Timestamps are already parsed as Datetime by read_database().
    # If they're still strings (e.g. from CSV), parse them.
    ts_dtype = data.schema.get("timestamp")
    if ts_dtype is None or not str(ts_dtype).startswith("Datetime"):
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%d-%m-%Y %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
        ]
        data = data.with_columns(
            pl.coalesce([
                pl.col("timestamp").cast(pl.Utf8).str.strptime(pl.Datetime, fmt, strict=False)
                for fmt in formats
            ]).alias("timestamp")
        )
        data = data.filter(pl.col("timestamp").is_not_null())
    data = data.with_columns(pl.col("timestamp").dt.hour().alias("hour"))
    patterns = []

    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        starts = group.filter(pl.col("event_type") == "start")
        if starts.is_empty():
            patterns.append({
                "user": user,
                "project": project,
                "avg_start_hour": None,
                "most_common_start_hour": None,
                "earliest_start": None,
                "latest_start": None,
            })
            continue

        hours = [h for h in starts.select("hour").to_series().to_list() if h is not None]
        most_common = max(set(hours), key=hours.count) if hours else None
        patterns.append({
            "user": user,
            "project": project,
            "avg_start_hour": float(np.mean(hours)) if hours else None,
            "most_common_start_hour": most_common,
            "earliest_start": min(hours) if hours else None,
            "latest_start": max(hours) if hours else None,
        })

    return pl.DataFrame(patterns)

def analyze_time_series(data):
    """Analysiert Zeitreihen-Muster in den Arbeitsdaten."""
    if data.is_empty():
        return pl.DataFrame(), pl.DataFrame(), pl.DataFrame()

    daily_hours = []
    for (user, date), group in data.partition_by(["user", "date"], as_dict=True).items():
        if user == "users":
            continue

        durations = _paired_durations_hours(group)
        if not durations:
            continue
        total_hours = sum(durations)

        date_obj = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                date_obj = datetime.strptime(date, fmt)
                break
            except ValueError:
                continue
        if not date_obj:
            print(f"Warnung: Datum '{date}' konnte nicht geparst werden")
            continue

        daily_hours.append({
            "user": user,
            "date": date,
            "weekday": date_obj.strftime("%A"),
            "week": date_obj.isocalendar().week,
            "hours": total_hours,
        })

    daily_df = pl.DataFrame(daily_hours)
    if daily_df.is_empty():
        return daily_df, pl.DataFrame(), pl.DataFrame()

    weekly_avg = (
        daily_df.group_by(["user", "week"])
        .agg(pl.col("hours").mean().alias("hours"))
        .sort(["user", "week"])
    )
    weekday_avg = (
        daily_df.group_by(["user", "weekday"])
        .agg(pl.col("hours").mean().alias("hours"))
    )
    weekday_order = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }
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

        user_features.append({
            "user": user,
            "avg_start_hour": avg_start_hour,
            "switches_per_day": switches_per_day,
            "avg_duration": avg_duration,
        })

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
            'cluster': cluster,
            'size': cluster_data.height,
            'avg_start': float(cluster_data['avg_start_hour'].mean()),
            'avg_switches': float(cluster_data['switches_per_day'].mean()),
            'avg_duration': float(cluster_data['avg_duration'].mean()),
            'users': cluster_data['user'].to_list()
        }
        cluster_profiles.append(profile)

    return features_df, cluster_profiles

def perform_regression_analysis(data):
    """
    Führt Regressionsanalyse für Arbeitsdauer durch.

    Prädiktoren:
    - User-ID (kategorisch)
    - Projekt (kategorisch)
    - Startstunde (numerisch)
    - Wochentag (kategorisch)

    Modelldetails:
    - Lineare Regression
    - One-Hot-Encoding für kategorische Variablen
    - R²-Score für Modellbewertung

    Anwendungsfälle:
    1. Vorhersage von Arbeitsdauern
    2. Identifikation wichtiger Einflussfaktoren
    3. Planung von Ressourcen

    Args:
        data (pl.DataFrame): Arbeitszeitdaten

    Returns:
        dict: Regressionsergebnisse mit Model, Importance, R², Predictions
    """
    if data.is_empty():
        return {}

    # Feature-Vorbereitung
    work_sessions = []

    for (user, project), group in data.partition_by(["user", "project"], as_dict=True).items():
        if user == "users":
            continue

        starts = group.filter(pl.col("event_type") == "start").select("timestamp").to_series().to_list()
        stops = group.filter(pl.col("event_type") == "stop").select("timestamp").to_series().to_list()
        min_length = min(len(starts), len(stops))
        if min_length == 0:
            continue

        for start, stop in zip(starts[:min_length], stops[:min_length], strict=False):
            duration = (stop - start).total_seconds() / 3600
            work_sessions.append({
                "user": user,
                "project": project,
                "start_hour": start.hour,
                "weekday": start.weekday(),
                "duration": duration,
            })

    sessions_df = pl.DataFrame(work_sessions)
    if sessions_df.is_empty():
        return {}

    # Dummy-Variablen für kategorische Features
    X_df = sessions_df.select(["user", "project", "start_hour", "weekday"]).to_dummies()
    X = X_df.to_numpy()
    y = sessions_df["duration"].to_numpy()

    # Regression
    model = LinearRegression()
    model.fit(X, y)

    # Feature Importance
    importance = pl.DataFrame({
        "feature": X_df.columns,
        "importance": np.abs(model.coef_),
    }).sort("importance", descending=True)

    # Modellperformance
    predictions = model.predict(X)
    r2_score = model.score(X, y)

    return {
        'model': model,
        "importance": importance,
        "r2_score": r2_score,
        "actual_vs_predicted": pl.DataFrame({
            "actual": y,
            "predicted": predictions,
        }),
    }

def perform_anova_analysis(data):
    """
    Führt ANOVA-Tests für Gruppenunterschiede durch.

    Analysierte Unterschiede:
    1. Zwischen Usern
    2. Zwischen Projekten

    Statistische Tests:
    - Einfaktorielle ANOVA
    - Tukey's HSD Post-hoc Test
    - p-Wert Analyse

    Interpretationshilfen:
    - p < 0.05: Signifikante Unterschiede
    - Tukey-Gruppen für paarweise Vergleiche
    - Effektgrößen für praktische Relevanz

    Args:
        data (pl.DataFrame): Arbeitszeitdaten

    Returns:
        dict: ANOVA-Ergebnisse mit F-Statistik, p-Werten und Tukey-Tests
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

        work_durations.extend([{
            "user": user,
            "project": project,
            "duration": float(duration),
        } for duration in durations])

    durations_df = pl.DataFrame(work_durations)

    try:
        if durations_df.is_empty() or durations_df["user"].n_unique() < 2 or durations_df["project"].n_unique() < 2:
            return {}

        # ANOVA zwischen Usern
        user_groups = [
            group["duration"].to_numpy()
            for group in durations_df.partition_by("user", as_dict=True).values()
        ]
        f_stat_users, p_value_users = stats.f_oneway(*user_groups)

        # ANOVA zwischen Projekten
        project_groups = [
            group["duration"].to_numpy()
            for group in durations_df.partition_by("project", as_dict=True).values()
        ]
        f_stat_projects, p_value_projects = stats.f_oneway(*project_groups)

        # Post-hoc Tests (Tukey's HSD)
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        tukey_users = pairwise_tukeyhsd(durations_df["duration"].to_numpy(),
                                        durations_df["user"].to_numpy())
        tukey_projects = pairwise_tukeyhsd(durations_df["duration"].to_numpy(),
                                           durations_df["project"].to_numpy())

        return {
            'user_anova': {
                'f_statistic': float(f_stat_users),
                'p_value': float(p_value_users),
                'tukey': tukey_users
            },
            'project_anova': {
                'f_statistic': float(f_stat_projects),
                'p_value': float(p_value_projects),
                'tukey': tukey_projects
            }
        }
    except Exception as e:
        print(f"Fehler in ANOVA-Analyse: {str(e)}")
        return None
