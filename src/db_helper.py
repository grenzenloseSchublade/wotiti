import sqlite3
from sqlite3 import Error
import os 
from config import DATABASE_PATH

def create_connection(db_file=DATABASE_PATH):
    """Create a database connection to the SQLite database specified by db_file."""
    print(f"Creating database connection to {db_file}...")
    
    # Überprüfen, ob das Verzeichnis bereits existiert
    directory = os.path.dirname(db_file)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Das Verzeichnis '{directory}' wurde erstellt.")

    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Database connection created successfully.")
        return conn
    except Error as e:
        print(f"Error creating database connection: {e}")

    return conn


def create_table(conn):
    """Create a table in the SQLite database."""
    print("Creating table in the database...")
    try:
        sql_create_table = """CREATE TABLE IF NOT EXISTS data (
                                id integer PRIMARY KEY,
                                value text NOT NULL
                            );"""
        cursor = conn.cursor()
        cursor.execute(sql_create_table)
        print("Table created successfully.")
    except Error as e:
        print(f"Error creating table: {e}")


def insert_data(conn, value):
    """Insert a new row into the data table."""
    print("Insert data...")
    sql = '''INSERT INTO data(value) VALUES(?)'''
    try:
        cur = conn.cursor()
        cur.execute(sql, (value,))
        conn.commit()
        print("Data inserted successfully.")
        return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
        return None