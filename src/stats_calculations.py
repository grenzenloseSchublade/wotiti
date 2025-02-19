"""
Statistik-Berechnungsmodul für die Zeiterfassungsanalyse.

Dieses Modul enthält Funktionen zur Analyse von Arbeitszeitdaten, einschließlich:
- Grundlegende Statistiken (Durchschnitte, Summen)
- Zeitreihenanalyse (Trends, Muster)
- Fortgeschrittene Analysen (Clustering, Regression, ANOVA)

Die Funktionen erwarten Zeitstempel im Format 'dd-mm-yyyy HH:MM:SS' und
arbeiten mit pandas DataFrames für effiziente Datenverarbeitung.
"""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from scipy import stats
import numpy as np
from datetime import datetime, timedelta

# Konstanten für Zeitkonvertierung
TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
DATE_FORMAT = "%d-%m-%Y"

def calculate_hours_per_project(data):
    """Calculates total hours per project for each user."""
    # Timestamps sind bereits datetime-Objekte
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    hours = []
    for (user, project), group in data.groupby(['user', 'project']):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        min_length = min(len(start_times), len(stop_times))
        total_hours = (stop_times.iloc[:min_length].values - start_times.iloc[:min_length].values).sum().astype('timedelta64[h]').astype(int)
        hours.append({'user': user, 'project': project, 'total_hours': total_hours})
    return pd.DataFrame(hours)

def calculate_total_hours_per_user(data):
    """Calculates total hours per user."""
    # Keine Kopie mehr nötig, da wir die Daten nicht modifizieren
    data = data.sort_values(by=['user', 'timestamp'])
    
    # Formatiere Datumsbereich nur für die Ausgabe
    start_date = data['timestamp'].min().strftime("%Y-%m-%d %H:%M:%S")
    end_date = data['timestamp'].max().strftime("%Y-%m-%d %H:%M:%S")
    date_range = f"{start_date} - {end_date}"
    
    total_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        
        # Timestamps sind bereits datetime-Objekte
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        
        min_length = min(len(start_times), len(stop_times))
        total_hours_user = sum((stop_times.iloc[i] - start_times.iloc[i]).total_seconds() / 3600 
                              for i in range(min_length))
        total_hours.append({'user': user, 'total_hours': total_hours_user})
    
    return pd.DataFrame(total_hours), date_range

def calculate_average_hours_per_user(data):
    """Calculates average hours per user."""
    data = data.copy()
    # Timestamps sind bereits datetime-Objekte, müssen nicht konvertiert werden
    data = data.sort_values(by=['user', 'timestamp'])
    average_hours = []
    
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        
        # Extrahiere Start- und Endzeiten
        start_times = pd.to_datetime(group[group['event_type'] == 'start']['timestamp'])
        stop_times = pd.to_datetime(group[group['event_type'] == 'stop']['timestamp'])
        
        # Berechne die Gesamtstunden
        total_hours_user = (stop_times.values - start_times.values).sum().astype('timedelta64[h]').astype(int)
        average_hours_user = total_hours_user / len(group['date'].unique())
        average_hours.append({'user': user, 'average_hours': average_hours_user})
    
    return pd.DataFrame(average_hours)

def calculate_average_hours_per_period(data, period_days):
    """Calculates average hours per user for a given period in days."""
    # Timestamps sind bereits datetime-Objekte
    data = data.sort_values(by=['user', 'timestamp'])
    average_hours = []
    for user, group in data.groupby('user'):
        if user == 'users':
            continue
        start_times = group[group['event_type'] == 'start']['timestamp'].reset_index(drop=True)
        stop_times = group[group['event_type'] == 'stop']['timestamp'].reset_index(drop=True)
        min_length = min(len(start_times), len(stop_times))
        total_hours = sum((stop_times.iloc[i] - start_times.iloc[i]).total_seconds() / 3600 for i in range(min_length))
        
        # Calculate the number of days the user has data for
        num_days = len(group['date'].unique())
        
        # Ensure that the number of periods is at least 1
        num_periods = max(1, num_days / period_days)
        
        average_hours_user = total_hours / num_periods
        average_hours.append({'user': user, 'average_hours': average_hours_user, 'period_days': period_days})
    return pd.DataFrame(average_hours)

def calculate_project_time_stats(data):
    """
    Berechnet detaillierte Zeitstatistiken pro Projekt und User.
    
    Features:
    - Durchschnittliche Arbeitszeit pro Projekt
    - Minimale und maximale Arbeitsdauer
    - Standardabweichung für Konsistenzanalyse
    
    Args:
        data (pd.DataFrame): DataFrame mit Spalten [user, project, event_type, timestamp]
    
    Returns:
        pd.DataFrame: Statistiken mit Spalten [user, project, avg_hours, min_hours, max_hours, std_hours]
    """
    data = data.copy()
    if not isinstance(data['timestamp'], pd.DatetimeIndex):
        data['timestamp'] = pd.to_datetime(data['timestamp'], format=TIMESTAMP_FORMAT)
    
    # Timestamps sind bereits datetime-Objekte
    data = data.sort_values(by=['user', 'project', 'timestamp'])
    stats = []
    
    for (user, project), group in data.groupby(['user', 'project']):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        
        if len(start_times) == len(stop_times):
            durations = [(stop - start).total_seconds() / 3600 
                        for start, stop in zip(start_times, stop_times)]
            
            stats.append({
                'user': user,
                'project': project,
                'avg_hours': sum(durations) / len(durations),
                'min_hours': min(durations),
                'max_hours': max(durations),
                'std_hours': pd.Series(durations).std()
            })
    
    return pd.DataFrame(stats)

def calculate_daily_project_hours(data):
    """
    Berechnet die tägliche Arbeitszeit pro User und Projekt.
    
    Features:
    - Gesamtarbeitszeit pro Tag
    - Aufschlüsselung nach Projekten
    - Identifikation von Arbeitstagen
    
    Args:
        data (pd.DataFrame): DataFrame mit Spalten [user, project, event_type, timestamp, date]
    
    Returns:
        pd.DataFrame: Tägliche Stunden mit Spalten [user, date, project, hours]
    """
    # Timestamps sind bereits datetime-Objekte
    data = data.sort_values(by=['user', 'date', 'project', 'timestamp'])
    daily_hours = []
    
    for (user, date, project), group in data.groupby(['user', 'date', 'project']):
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        
        if len(start_times) == len(stop_times):
            total_hours = sum((stop - start).total_seconds() / 3600 
                            for start, stop in zip(start_times, stop_times))
            
            daily_hours.append({
                'user': user,
                'date': date,
                'project': project,
                'hours': total_hours
            })
    
    return pd.DataFrame(daily_hours)

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
        data (pd.DataFrame): Arbeitszeitdaten
    
    Returns:
        pd.DataFrame: Wechselstatistiken mit [user, date, from_project, to_project, pause_minutes]
    """
    # Timestamps sind bereits datetime-Objekte
    data = data.sort_values(by=['user', 'date', 'timestamp'])
    switches = []
    
    for (user, date), group in data.groupby(['user', 'date']):
        events = group.sort_values('timestamp')
        current_project = None
        last_stop = None
        
        for _, row in events.iterrows():
            if row['event_type'] == 'start':
                if current_project and current_project != row['project']:
                    pause_minutes = (row['timestamp'] - last_stop).total_seconds() / 60
                    switches.append({
                        'user': user,
                        'date': date,
                        'from_project': current_project,
                        'to_project': row['project'],
                        'pause_minutes': pause_minutes,
                        'switch_time': row['timestamp'].strftime('%H:%M')
                    })
                current_project = row['project']
            else:  # stop event
                last_stop = row['timestamp']
    
    return pd.DataFrame(switches)

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
        data (pd.DataFrame): Arbeitszeitdaten
    
    Returns:
        pd.DataFrame: Tagesmuster mit [user, project, avg_start_hour, most_common_start_hour]
    """
    # Timestamps sind bereits datetime-Objekte
    data = data.copy()
    data['hour'] = data['timestamp'].dt.hour
    patterns = []
    
    for (user, project), group in data.groupby(['user', 'project']):
        starts = group[group['event_type'] == 'start']
        
        patterns.append({
            'user': user,
            'project': project,
            'avg_start_hour': starts['hour'].mean(),
            'most_common_start_hour': starts['hour'].mode().iloc[0],
            'earliest_start': starts['hour'].min(),
            'latest_start': starts['hour'].max()
        })
    
    return pd.DataFrame(patterns)

def analyze_time_series(data):
    """Analysiert Zeitreihen-Muster in den Arbeitsdaten."""
    # Tägliche Gesamtstunden pro User
    daily_hours = []
    
    for (user, date), group in data.groupby(['user', 'date']):
        if user == 'users':
            continue
            
        start_times = group[group['event_type'] == 'start']['timestamp']
        stop_times = group[group['event_type'] == 'stop']['timestamp']
        
        if len(start_times) == len(stop_times):
            total_hours = sum((stop - start).total_seconds() / 3600 
                            for start, stop in zip(start_times, stop_times))
            
            # Versuche zuerst das Standard-Format (YYYY-MM-DD)
            try:
                date_obj = pd.to_datetime(date, format='%Y-%m-%d')
            except ValueError:
                # Falls das fehlschlägt, versuche das alternative Format (DD-MM-YYYY)
                try:
                    date_obj = pd.to_datetime(date, format='%d-%m-%Y')
                except ValueError:
                    print(f"Warnung: Datum '{date}' konnte nicht geparst werden")
                    continue
            
            daily_hours.append({
                'user': user,
                'date': date,
                'weekday': date_obj.day_name(),
                'week': date_obj.isocalendar().week,
                'hours': total_hours
            })
    
    daily_df = pd.DataFrame(daily_hours)
    
    # Wöchentliche Durchschnitte
    weekly_avg = daily_df.groupby(['user', 'week'])['hours'].mean().reset_index()
    
    # Tägliche Durchschnitte nach Wochentag
    weekday_avg = daily_df.groupby(['user', 'weekday'])['hours'].mean().reset_index()
    weekday_avg['weekday'] = pd.Categorical(
        weekday_avg['weekday'], 
        categories=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        ordered=True
    )
    weekday_avg = weekday_avg.sort_values('weekday')
    
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
        data (pd.DataFrame): Arbeitszeitdaten
    
    Returns:
        tuple: (features_df, cluster_profiles)
            - features_df: DataFrame mit User-Features und Cluster-Zuordnung
            - cluster_profiles: Liste der Cluster-Charakteristiken
    """
    # Feature-Extraktion für Clustering
    user_features = []
    
    for user in data['user'].unique():
        if user == 'users':
            continue
            
        user_data = data[data['user'] == user]
        
        # Durchschnittliche Startzeit
        start_times = user_data[user_data['event_type'] == 'start']['timestamp']
        avg_start_hour = start_times.dt.hour.mean()
        
        # Projektwechsel pro Tag
        switches_per_day = len(calculate_project_switches(user_data)) / len(user_data['date'].unique())
        
        # Durchschnittliche Arbeitsdauer
        avg_duration = calculate_average_hours_per_user(user_data)['average_hours'].iloc[0]
        
        user_features.append({
            'user': user,
            'avg_start_hour': avg_start_hour,
            'switches_per_day': switches_per_day,
            'avg_duration': avg_duration
        })
    
    features_df = pd.DataFrame(user_features)
    
    # Standardisierung der Features
    scaler = StandardScaler()
    X = scaler.fit_transform(features_df.drop('user', axis=1))
    
    # Clustering (optimal k wird automatisch bestimmt)
    k_range = range(2, min(5, len(X) + 1))
    inertias = []
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)
    
    # Optimales k durch Ellenbogenmethode
    optimal_k = k_range[np.argmin(np.diff(inertias)) + 1]
    
    # Finales Clustering
    kmeans = KMeans(n_clusters=optimal_k, random_state=42)
    features_df['cluster'] = kmeans.fit_predict(X)
    
    # Cluster-Charakteristiken
    cluster_profiles = []
    for cluster in range(optimal_k):
        cluster_data = features_df[features_df['cluster'] == cluster]
        profile = {
            'cluster': cluster,
            'size': len(cluster_data),
            'avg_start': cluster_data['avg_start_hour'].mean(),
            'avg_switches': cluster_data['switches_per_day'].mean(),
            'avg_duration': cluster_data['avg_duration'].mean(),
            'users': cluster_data['user'].tolist()
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
        data (pd.DataFrame): Arbeitszeitdaten
    
    Returns:
        dict: Regressionsergebnisse mit Model, Importance, R², Predictions
    """
    data = data.copy()
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data['timestamp'] = data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Feature-Vorbereitung
    work_sessions = []
    
    for (user, project), group in data.groupby(['user', 'project']):
        if user == 'users':
            continue
            
        starts = group[group['event_type'] == 'start']
        stops = group[group['event_type'] == 'stop']
        
        for start, stop in zip(starts['timestamp'], stops['timestamp']):
            start_dt = pd.to_datetime(start)
            duration = (pd.to_datetime(stop) - start_dt).total_seconds() / 3600
            
            work_sessions.append({
                'user': user,
                'project': project,
                'start_hour': start_dt.hour,
                'weekday': start_dt.weekday(),
                'duration': duration
            })
    
    sessions_df = pd.DataFrame(work_sessions)
    
    # Dummy-Variablen für kategorische Features
    X = pd.get_dummies(sessions_df[['user', 'project', 'start_hour', 'weekday']])
    y = sessions_df['duration']
    
    # Regression
    model = LinearRegression()
    model.fit(X, y)
    
    # Feature Importance
    importance = pd.DataFrame({
        'feature': X.columns,
        'importance': abs(model.coef_)
    }).sort_values('importance', ascending=False)
    
    # Modellperformance
    predictions = model.predict(X)
    r2_score = model.score(X, y)
    
    return {
        'model': model,
        'importance': importance,
        'r2_score': r2_score,
        'actual_vs_predicted': pd.DataFrame({
            'actual': y,
            'predicted': predictions
        })
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
        data (pd.DataFrame): Arbeitszeitdaten
    
    Returns:
        dict: ANOVA-Ergebnisse mit F-Statistik, p-Werten und Tukey-Tests
    """
    work_durations = []
    
    for (user, project), group in data.groupby(['user', 'project']):
        if user == 'users':
            continue
            
        starts = group[group['event_type'] == 'start']['timestamp']
        stops = group[group['event_type'] == 'stop']['timestamp']
        
        # Berechne Dauern direkt mit datetime-Objekten
        durations = [(stop - start).total_seconds() / 3600
                    for start, stop in zip(starts, stops)]
        
        work_durations.extend([{
            'user': user,
            'project': project,
            'duration': float(duration)  # Konvertiere zu float für die Analyse
        } for duration in durations])
    
    durations_df = pd.DataFrame(work_durations)
    
    try:
        # ANOVA zwischen Usern
        user_groups = [group['duration'].values 
                      for _, group in durations_df.groupby('user')]
        f_stat_users, p_value_users = stats.f_oneway(*user_groups)
        
        # ANOVA zwischen Projekten
        project_groups = [group['duration'].values 
                         for _, group in durations_df.groupby('project')]
        f_stat_projects, p_value_projects = stats.f_oneway(*project_groups)
        
        # Post-hoc Tests (Tukey's HSD)
        from statsmodels.stats.multicomp import pairwise_tukeyhsd
        
        tukey_users = pairwise_tukeyhsd(durations_df['duration'], 
                                       durations_df['user'])
        tukey_projects = pairwise_tukeyhsd(durations_df['duration'], 
                                          durations_df['project'])
        
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
