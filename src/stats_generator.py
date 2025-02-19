import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
import random

from db_helper import create_connection, create_main_table, create_user_table, check_user, log_start, log_stop
import json
from utils import save_to_csv, PATH_TO_DATA

# Konstanten für die Datengenerierung
MIN_START_HOUR = 7
MAX_START_HOUR = 10
MIN_END_HOUR = 15
MAX_END_HOUR = 18
MIN_DAILY_HOURS = 6
MAX_DAILY_HOURS = 9
MIN_TIMEBLOCK = 20
MAX_TIMEBLOCK = 300
MIN_PROJECTS = 2
MAX_PROJECTS = 4
DEFAULT_NUM_USERS = 5

def generate_random_sample_data():
    """Generate sample data with random values and user-specific parameters."""
    storage_type = "both"
    
    # Datum und Zeitraum
    start_date = datetime(2025, 1, 1)
    end_date = start_date + timedelta(days=30)
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    # Benutzerspezifische Parameter
    user_params = {}
    for user_id in range(1, DEFAULT_NUM_USERS + 1):
        user_params[f"user_{user_id}"] = {
            'timeblock_min': random.randint(MIN_TIMEBLOCK, 45),
            'max_timeblock': random.randint(180, MAX_TIMEBLOCK),
            'project_max': random.randint(MIN_PROJECTS, MAX_PROJECTS),
            'fixed_interval': f"{random.randint(MIN_START_HOUR,MAX_START_HOUR):02d}:00-{random.randint(MIN_END_HOUR,MAX_END_HOUR):02d}:00",
            'min_daily_hours': random.randint(MIN_DAILY_HOURS, 7),
            'max_daily_hours': random.randint(8, MAX_DAILY_HOURS)
        }
    
    # Verzeichnis für generierte Daten
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = os.path.join(PATH_TO_DATA, timestamp)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Verzeichnis '{directory}' erstellt.")

    # Aufruf mit user_params
    generate_sample_data(
        storage_type=storage_type,
        start_date=start_date_str,
        end_date=end_date_str,
        path_to_save=directory,
        user_params=user_params
    )

    # Parameter in JSON-Datei speichern
    params = {
        "num_users": len(user_params),
        "storage_type": storage_type,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "user_specific_params": user_params,
        "path_to_save": directory
    }

    json_filename = os.path.join(directory, f"parameter_run_{timestamp}.json")
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(params, json_file, indent=4)

def generate_sample_data(storage_type, start_date, end_date, path_to_save=PATH_TO_DATA, user_params=None):
    """
    Generate sample data and store it in the specified format.
    
    Parameters:
    - storage_type: Type of storage ('csv', 'db', or 'both')
    - start_date: Start date for the entries (format: 'dd-mm-yyyy')
    - end_date: End date for the entries (format: 'dd-mm-yyyy')
    - path_to_save: Path to save the generated data
    - user_params: Dictionary containing user-specific parameters
    """
    # Eingabevalidierung
    if storage_type not in ['csv', 'db', 'both']:
        raise ValueError("storage_type muss 'csv', 'db' oder 'both' sein")
    if not user_params:
        raise ValueError("user_params ist erforderlich und darf nicht leer sein")
    if not os.path.exists(path_to_save):
        raise ValueError(f"Pfad existiert nicht: {path_to_save}")

    database_path = os.path.join(path_to_save, "generate_database.db")
    csv_path = os.path.join(path_to_save, "generate_database.csv")
    all_data = []

    try:
        conn = create_connection(database_path)
        if not conn:
            raise sqlite3.Error("Keine Datenbankverbindung möglich")

        create_main_table(conn)
        print(f"\nStarte Datengenerierung für {len(user_params)} User")
        print(f"Zeitraum: {start_date} bis {end_date}")
        print(f"Speichertyp: {storage_type}")
        
        # Datum einmal konvertieren
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        date_range = (end_date_obj - start_date_obj).days + 1

        # Für jeden User in user_params
        for user_name, user_config in user_params.items():
            print(f"\nGeneriere Daten für {user_name}")
            print(f"Konfiguration: {user_config}")
            
            # Erstelle User in der Datenbank
            check_user(conn, user_name)
            create_user_table(conn, user_name)

            for day_offset in range(date_range):
                date = start_date_obj + timedelta(days=day_offset)
                date_str = date.strftime("%Y-%m-%d")
                
                # Ziel-Arbeitszeit für diesen Tag (in Minuten)
                target_minutes = random.randint(
                    user_config['min_daily_hours'] * 60,
                    user_config['max_daily_hours'] * 60
                )
                total_minutes_worked = 0
                current_block_duration = 0
                last_stop_time = date
                
                print(f"Tag {date_str} - Ziel: {target_minutes} Minuten")

                while total_minutes_worked < target_minutes:
                    project = f"projekt_{random.randint(1, user_config['project_max'])}"
                    
                    # Prüfen ob eine Pause nötig ist
                    if current_block_duration >= user_config['max_timeblock']:
                        pause_duration = random.randint(20, 45)
                        last_stop_time = last_stop_time + timedelta(minutes=pause_duration)
                        current_block_duration = 0
                        print(f"Pause von {pause_duration} Minuten eingelegt")
                        continue

                    if user_config['fixed_interval']:
                        start_time_str, stop_time_str = user_config['fixed_interval'].split('-')
                        base_start_time = datetime.strptime(
                            f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M"
                        )
                        base_stop_time = datetime.strptime(
                            f"{date_str} {stop_time_str}", "%Y-%m-%d %H:%M"
                        )
                        
                        # Zeitfenster definieren
                        min_start_time = base_start_time - timedelta(minutes=30)
                        max_start_time = base_start_time + timedelta(minutes=30)
                        min_stop_time = base_stop_time - timedelta(minutes=30)
                        max_stop_time = base_stop_time + timedelta(minutes=30)
                        
                        # Start-Zeit bestimmen
                        if last_stop_time.time() < min_start_time.time():
                            start_time = min_start_time
                        else:
                            start_time = last_stop_time + timedelta(minutes=random.randint(5, 15))

                        if start_time > max_stop_time:
                            break
                        
                        # Berechnung der maximalen Dauer für diesen Block
                        remaining_target = target_minutes - total_minutes_worked
                        max_possible_duration = min(
                            180,  # Max 3 Stunden pro Block
                            user_config['max_timeblock'] - current_block_duration,
                            (max_stop_time - start_time).seconds // 60,
                            remaining_target
                        )
                        
                        # Prüfen ob noch genügend Zeit verfügbar ist
                        if max_possible_duration <= user_config['timeblock_min']:
                            if remaining_target >= user_config['timeblock_min']:
                                duration = remaining_target
                            else:
                                break
                        else:
                            duration = random.randint(user_config['timeblock_min'], max_possible_duration)
                        
                        stop_time = start_time + timedelta(minutes=duration)
                        
                        # Sicherstellen, dass Stop-Zeit im erlaubten Bereich liegt
                        if stop_time > max_stop_time:
                            stop_time = max_stop_time
                            duration = (stop_time - start_time).seconds // 60
                            if duration < user_config['timeblock_min']:
                                break
                        
                        # Tracking-Variablen aktualisieren
                        block_duration = (stop_time - start_time).seconds // 60
                        current_block_duration += block_duration
                        total_minutes_worked += block_duration
                        
                        # Zeiten loggen
                        log_start(project=project, name=user_name, timestamp=start_time, 
                                date=date_str, conn=conn)
                        log_stop(project=project, name=user_name, timestamp=stop_time, 
                               date=date_str, conn=conn)
                        
                        all_data.extend([
                            {
                                "user": user_name,
                                "project": project,
                                "event_type": "start",
                                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                                "date": date_str
                            },
                            {
                                "user": user_name,
                                "project": project,
                                "event_type": "stop",
                                "timestamp": stop_time.strftime("%Y-%m-%d %H:%M:%S"),
                                "date": date_str
                            }
                        ])
                        
                        last_stop_time = stop_time
                        
                        print(f"Block: {block_duration}min, "
                              f"Total: {total_minutes_worked}/{target_minutes}min")

        # Speichere alle Daten am Ende
        if storage_type in ["csv", "both"]:
            df = pd.DataFrame(all_data)
            save_to_csv(df, csv_path)
            print(f"\nDaten in CSV gespeichert: {csv_path}")
        
        if storage_type in ["db", "both"]:
            conn.commit()
            print(f"Daten in Datenbank gespeichert: {database_path}")
        
        conn.close()
        print("\nDatengenerierung erfolgreich abgeschlossen!")
        
    except sqlite3.Error as e:
        print(f"Datenbankfehler: {e}")
    except Exception as e:
        print(f"Fehler bei der Datengenerierung: {e}")

if __name__ == "__main__":
    generate_random_sample_data()