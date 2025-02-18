import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
import random

from data_handling.db_helper import create_connection, create_main_table, create_user_table, check_user, log_start, log_stop
import json
from config import GENERATE_DATABASE_PATH, PATH_TO_DATA


def read_database(db_path=PATH_TO_DATA):
    """Read the SQLite database and return the data as a pandas DataFrame."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all user tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        
        data = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            table_data = pd.DataFrame(rows, columns=columns)
            table_data['user'] = table_name.replace('_events', '')
            data.append(table_data)
        
        conn.close()
        return pd.concat(data, ignore_index=True)
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return pd.DataFrame()


def save_to_csv(data, csv_path):
    """Save the DataFrame to a CSV file."""
    try:
        data.to_csv(csv_path, index=False)
        print(f"Data saved to {csv_path} successfully.")
    except Exception as e:
        print(f"Error saving data to CSV: {e}")


def generate_sample_data(num_users, storage_type, timeblock_min, start_date, end_date, 
                         project_max=10, fixed_interval=None, 
                         path_to_save=GENERATE_DATABASE_PATH, add_to_existing=False):
    """
    Generate sample data and store it in the specified format.
    
    Parameters:
    - num_users: Number of users to generate data for.
    - storage_type: Type of storage ('csv', 'db', or 'both').
    - timeblock_min: Minimum time block in minutes between start and stop times.
    - start_date: Start date for the entries (format: 'dd-mm-yyyy').
    - end_date: End date for the entries (format: 'dd-mm-yyyy').
    - project_max: Maximum number of projects to generate.
    - fixed_interval: Fixed time interval per day for start and stop times (format: 'HH:MM-HH:MM').
    - path_to_save: Path to save the generated data.
    - add_to_existing: Whether to add to existing data or overwrite.
    """

    database_path = f"{path_to_save}/generate_database.db"
    csv_path = f"{path_to_save}/generate_database.csv"

    try:
        conn = create_connection(database_path)
        if conn:
            create_main_table(conn)
            start_date = datetime.strptime(start_date, "%d-%m-%Y")
            end_date = datetime.strptime(end_date, "%d-%m-%Y")
            date_range = (end_date - start_date).days + 1  # Inclusive range

            data = []
            for user_id in range(1, num_users + 1):
                user_name = f"user_{user_id}"
                check_user(conn, user_name)
                create_user_table(conn, user_name)
                
                for day_offset in range(date_range):
                    date = start_date + timedelta(days=day_offset)
                    date_str = date.strftime("%d-%m-%Y")
                    total_minutes_worked = 0
                    last_stop_time = date

                    # Generate events for a single day until 12 hours (720 minutes) of work is reached
                    while total_minutes_worked < 720:
                        project = f"projekt_{random.randint(1, project_max)}"
                        
                        if fixed_interval:
                            start_time_str, stop_time_str = fixed_interval.split('-')
                            min_start_time = datetime.strptime(
                                f"{date_str} {start_time_str}", "%d-%m-%Y %H:%M"
                            )
                            max_stop_time = datetime.strptime(
                                f"{date_str} {stop_time_str}", "%d-%m-%Y %H:%M"
                            )
                            
                            total_interval_minutes = (max_stop_time - min_start_time).seconds // 60
                            random_start_minutes = random.randint(0, 120)
                            start_time = min_start_time + timedelta(minutes=random_start_minutes)
                            
                            random_stop_minutes = random.randint(
                                timeblock_min, total_interval_minutes - random_start_minutes
                            )
                            stop_time = start_time + timedelta(minutes=random_stop_minutes)
                            
                            if start_time < last_stop_time:
                                start_time = last_stop_time + timedelta(minutes=random.randint(1, 60))
                                stop_time = start_time + timedelta(minutes=random.randint(timeblock_min, 120))
                        else:
                            delay = random.randint(1, 60)
                            start_time = last_stop_time + timedelta(minutes=delay)
                            stop_time = start_time + timedelta(minutes=random.randint(timeblock_min, 120))

                        log_start(
                            project=project, name=user_name, timestamp=start_time, 
                            date=date_str, conn=conn
                        )
                        log_stop(
                            project=project, name=user_name, timestamp=stop_time, 
                            date=date_str, conn=conn
                        )
                        
                        data.append({
                            "user": user_name,
                            "project": project,
                            "event_type": "start",
                            "timestamp": start_time.strftime("%d-%m-%Y %H:%M:%S"),
                            "date": date_str
                        })
                        data.append({
                            "user": user_name,
                            "project": project,
                            "event_type": "stop",
                            "timestamp": stop_time.strftime("%d-%m-%Y %H:%M:%S"),
                            "date": date_str
                        })

                        total_minutes_worked += (stop_time - start_time).seconds // 60
                        last_stop_time = stop_time

            if storage_type in ["csv", "both"]:
                df = pd.DataFrame(data)
                if add_to_existing:
                    df.to_csv(csv_path, mode='a', header=False, index=False)
                else:
                    save_to_csv(df, csv_path)
            
            if storage_type in ["db", "both"]:
                conn.commit()
                print(f"Sample data inserted into the database at {database_path} successfully.")
            
            conn.close()
    except sqlite3.Error as e:
        print(f"Error generating sample data: {e}")

def generate_random_sample_data():
    """Generate sample data with random values for start_date, end_date, and fixed_interval."""
    num_users = random.randint(4, 9)
    storage_type = "both"
    timeblock_min = random.randint(30, 120)
    
    start_date = datetime.now() - timedelta(days=random.randint(1, 30))
    end_date = start_date + timedelta(days=random.randint(30, 30)) # 1 Monat
    start_date_str = start_date.strftime("%d-%m-%Y")
    end_date_str = end_date.strftime("%d-%m-%Y")
    project_max = random.randint(2, 4)
    
    start_hour = random.randint(0, 23)
    end_hour = random.randint(start_hour + 1, 24)
    start_hour = 9
    end_hour = 17
    fixed_interval = f"{start_hour:02d}:00-{end_hour:02d}:00"
    add_to_existing = False
    
    # Create directory for the generated data
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = PATH_TO_DATA + f"/{timestamp}"
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory '{directory}' created.")

    generate_sample_data(
        num_users=num_users,
        storage_type=storage_type,
        timeblock_min=timeblock_min,
        start_date=start_date_str,
        end_date=end_date_str,
        project_max=project_max,
        fixed_interval=fixed_interval,
        path_to_save=directory,
        add_to_existing=add_to_existing
    )

    # Save parameters to JSON file
    params = {
        "num_users": num_users,
        "storage_type": storage_type,
        "timeblock_min": timeblock_min,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "project_max": project_max,
        "fixed_interval": fixed_interval,
        "path_to_save": directory,
        "add_to_existing": add_to_existing
    }

    # Save parameters to JSON file
    with open(os.path.join(directory, "generation_params.json"), "w") as f:
        json.dump(params, f, indent=4)


if __name__ == "__main__":
    generate_random_sample_data()
