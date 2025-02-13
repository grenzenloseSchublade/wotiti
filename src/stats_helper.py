import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
import random
from config import GENERATE_DATABASE_NAME
from db_helper import create_connection, create_main_table, create_user_table, check_user, log_start, log_stop
import json

def read_database(db_path=GENERATE_DATABASE_NAME):
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

def generate_sample_data(num_users, num_entries_per_user, storage_type, timeblock_min, start_date, end_date, project_max=10, fixed_interval=None, path_to_save=GENERATE_DATABASE_NAME, add_to_existing=False, entries_per_day=1):
    """
    Generate sample data and store it in the specified format.
    
    Parameters:
    - num_users: Number of users to generate data for.
    - num_entries_per_user: Number of entries per user.
    - storage_type: Type of storage ('csv', 'db', or 'both').
    - timeblock_min: Minimum time block in minutes between start and stop times.
    - start_date: Start date for the entries (format: 'dd-mm-yyyy').
    - end_date: End date for the entries (format: 'dd-mm-yyyy').
    - project_max: Maximum number of projects to generate.
    - fixed_interval: Fixed time interval per day for start and stop times (format: 'HH:MM-HH:MM').
    - path_to_save: Path to save the generated data.
    - add_to_existing: Whether to add to existing data or overwrite.
    - entries_per_day: Number of entries to generate per day.
    """
    try:
        conn = create_connection(GENERATE_DATABASE_NAME)
        if conn:
            create_main_table(conn)
            start_date = datetime.strptime(start_date, "%d-%m-%Y")
            end_date = datetime.strptime(end_date, "%d-%m-%Y")
            date_range = (end_date - start_date).days
            if date_range == 0:
                date_range = 1  # Avoid division by zero

            data = []
            for user_id in range(1, num_users + 1):
                user_name = f"user_{user_id}"
                check_user(conn, user_name)
                create_user_table(conn, user_name)
                
                for entry_id in range(1, num_entries_per_user + 1):
                    date = start_date + timedelta(days=(entry_id // entries_per_day) % date_range)
                    date_str = date.strftime("%d-%m-%Y")
                    
                    project = f"projekt_{random.randint(1, project_max)}"
                    
                    if fixed_interval:
                        start_time_str, stop_time_str = fixed_interval.split('-')
                        min_start_time = datetime.strptime(f"{date_str} {start_time_str}", "%d-%m-%Y %H:%M")
                        max_stop_time = datetime.strptime(f"{date_str} {stop_time_str}", "%d-%m-%Y %H:%M")
                        
                        # Generate random start time within the defined interval
                        total_minutes = (max_stop_time - min_start_time).seconds // 60
                        random_start_minutes = random.randint(0, total_minutes - timeblock_min)
                        start_time = min_start_time + timedelta(minutes=random_start_minutes)
                        
                        # Ensure stop time is at least timeblock_min minutes after start time
                        random_stop_minutes = random.randint(timeblock_min, total_minutes - random_start_minutes)
                        stop_time = start_time + timedelta(minutes=random_stop_minutes)
                    else:
                        start_time = date + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                        stop_time = start_time + timedelta(minutes=random.randint(timeblock_min, 120))

                    log_start(project=project, name=user_name, timestamp=start_time, date=date_str, conn=conn)
                    log_stop(project=project, name=user_name, timestamp=stop_time, date=date_str, conn=conn)
                    
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

            if storage_type in ["csv", "both"]:
                df = pd.DataFrame(data)
                path_to_save = os.path.dirname(GENERATE_DATABASE_NAME) + "/generate_database.csv"
                
                if os.path.exists(path_to_save) and add_to_existing:
                    df.to_csv(path_to_save, mode='a', header=False, index=False)
                else:
                    save_to_csv(df, path_to_save)
            
            if storage_type in ["db", "both"]:
                conn.commit()
                print(f"Sample data inserted into the database at {GENERATE_DATABASE_NAME} successfully.")
            
            conn.close()
    except Exception as e:
        print(f"Error generating sample data: {e}")


def generate_random_sample_data():
    """Generate sample data with random values for start_date, end_date, and fixed_interval."""
    num_users = random.randint(1, 10)
    num_entries_per_user = random.randint(15, 20)
    storage_type = random.choice(["both"])
    timeblock_min = random.randint(10, 60)
    
    start_date = datetime.now() - timedelta(days=random.randint(1, 30))
    end_date = start_date + timedelta(days=random.randint(1, 10))
    start_date_str = start_date.strftime("%d-%m-%Y")
    end_date_str = end_date.strftime("%d-%m-%Y")
    project_max = random.randint(1, 5)
    
    start_hour = random.randint(0, 23)
    end_hour = random.randint(start_hour + 1, 24)
    fixed_interval = f"{start_hour:02d}:00-{end_hour:02d}:00"
    add_to_existing = False
    
    params = {
        "num_users": num_users,
        "num_entries_per_user": num_entries_per_user,
        "storage_type": storage_type,
        "timeblock_min": timeblock_min,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "project_max": project_max,
        "fixed_interval": fixed_interval,
        "add_to_existing": add_to_existing
    }
    
    generate_sample_data(
        num_users=num_users,
        num_entries_per_user=num_entries_per_user,
        storage_type=storage_type,
        timeblock_min=timeblock_min,
        start_date=start_date_str,
        end_date=end_date_str,
        project_max=project_max,
        fixed_interval=fixed_interval,
        add_to_existing=add_to_existing
    )

    # Save parameters to JSON file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_filename = f"{os.path.dirname(GENERATE_DATABASE_NAME)}/run_{timestamp}.json"
    with open(json_filename, 'w') as json_file:
        json.dump(params, json_file, indent=4)


# Example usage
if __name__ == "__main__":
    generate_random_sample_data()
    #generate_sample_data(num_users=5, num_entries_per_user=10, storage_type="both", timeblock_min=15, start_date="01-01-2023", end_date="10-01-2023", fixed_interval="09:00-17:00", add_to_existing=True)
    # data = read_database()
    # if not data.empty:
    #     save_to_csv(data, "database/generate_database.csv")
