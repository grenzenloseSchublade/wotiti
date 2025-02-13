import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
import random
from config import GENERATE_DATABASE_NAME
from db_helper import create_connection, create_main_table, create_user_table, check_user, log_start, log_stop

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

def generate_sample_data(num_users, num_entries_per_user, storage_type, timeblock_min, start_date, end_date, path_to_save=GENERATE_DATABASE_NAME):
    """Generate sample data and store it in the specified format."""
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
                
                for entry_id in range(1, num_entries_per_user+1):
                    date = start_date + timedelta(days=entry_id % date_range)
                    date_str = date.strftime("%d-%m-%Y")
                    
                    start_time = date + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                    stop_time = start_time + timedelta(minutes=random.randint(timeblock_min, 120))
                    
                    log_start(project=1, name=user_name, timestamp=start_time, date=date_str, conn=conn)
                    log_stop(project=1, name=user_name, timestamp=stop_time, date=date_str, conn=conn)
                    
                    data.append({
                        "user": user_name,
                        "project": 1,
                        "event_type": "start",
                        "timestamp": start_time.strftime("%d-%m-%Y %H:%M:%S"),
                        "date": date_str
                    })
                    data.append({
                        "user": user_name,
                        "project": 1,
                        "event_type": "stop",
                        "timestamp": stop_time.strftime("%d-%m-%Y %H:%M:%S"),
                        "date": date_str
                    })

            if storage_type in ["csv", "both"]:
                df = pd.DataFrame(data)
                path_to_save = os.path.dirname(GENERATE_DATABASE_NAME) + "/generate_database.csv"
                save_to_csv(df, path_to_save)
            
            if storage_type in ["db", "both"]:
                conn.commit()
                print(f"Sample data inserted into the database at {GENERATE_DATABASE_NAME} successfully.")
            
            conn.close()
    except Exception as e:
        print(f"Error generating sample data: {e}")

# Example usage
if __name__ == "__main__":

    generate_sample_data(num_users=5, num_entries_per_user=10, storage_type="both", timeblock_min=15, start_date="01-01-2023", end_date="01-01-2023")
    # data = read_database()
    # if not data.empty:
    #     save_to_csv(data, "database/generate_database.csv")
