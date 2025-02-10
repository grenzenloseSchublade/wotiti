import sqlite3
from sqlite3 import Error

def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file."""
    print(f"Creating database connection to {db_file}...")
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
    print(f"Inserting data into the table: {value}")
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