from tkinter import Button, Text, Scrollbar, VERTICAL, END, Frame
import sys
import os
import time
from db_helper import create_connection, create_table, insert_data
from config import DATABASE_PATH
# import plotly.graph_objects as go

class App:
    def __init__(self, master):
        print("Initializing the application GUI...")
        self.master = master
        master.title("Fancy GUI App")
        master.configure(bg='#2e2e2e')

        # Set window size based on screen resolution
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        window_width = int(screen_width * 0.5)
        window_height = int(screen_height * 0.5)
        master.geometry(f"{window_width}x{window_height}")

        # Make the window resizable
        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)

        # Main frame
        self.frame = Frame(master, bg='#2e2e2e')
        self.frame.grid(padx=10, pady=10, sticky="nsew")

        # Button frame
        self.button_frame = Frame(self.frame, bg='#2e2e2e')
        self.button_frame.grid(row=0, column=0, columnspan=3, pady=5, padx=5, sticky="ew")

        # Click Me button
        self.button = Button(self.button_frame, text="Click Me", command=self.on_button_click, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.button.grid(row=0, column=0, pady=5, padx=5, sticky="ew")

        # Insert Default Entry button
        self.insert_button = Button(self.button_frame, text="Insert Default Entry", command=self.insert_default_entry, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.insert_button.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

        # Clear Console button
        self.clear_button = Button(self.button_frame, text="Clear Console", command=self.clear_console, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.clear_button.grid(row=0, column=2, pady=5, padx=5, sticky="ew")

        # Console frame
        self.console_frame = Frame(self.frame, bg='#2e2e2e')
        self.console_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # Console text widget
        self.console = Text(self.console_frame, wrap='word', state='disabled', height=10, bg='#1e1e1e', fg='white', font=('Courier', 10))
        self.console.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for console
        self.scrollbar = Scrollbar(self.console_frame, orient=VERTICAL, command=self.console.yview, bg='#2e2e2e', width=20)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.console['yscrollcommand'] = self.scrollbar.set

        # Configure grid weights
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_columnconfigure(2, weight=1)
        self.console_frame.grid_rowconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)

        # Redirect stdout and stderr to the console
        sys.stdout = self
        sys.stderr = self

        # Database connection
        try:
            self.db_conn = create_connection("database/app_database.db")
            if self.db_conn:
                create_table(self.db_conn)
        except Exception as e:
            self.write(f"Failed to connect to the database: {e}", error=True)
            self.db_conn = None

    def on_button_click(self):
        print("Button clicked!")

    def insert_default_entry(self):
        if self.db_conn:
            print("Inserting default entry into the database...")
            insert_data(self.db_conn, "Default Entry")

    def clear_console(self):
        """Clears the console text widget."""
        self.console.configure(state='normal')
        self.console.delete(1.0, END)
        self.console.configure(state='disabled')

    def write(self, message, error=False):
        """Writes a message to the console with a timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if message.strip():
            message = f"[{timestamp}] {message}"
        self.console.configure(state='normal')
        if error:
            self.console.insert(END, message, 'error')
            self.console.tag_config('error', font='red')
        else:
            self.console.insert(END, message)
        self.console.configure(state='disabled')
        self.console.see(END)

    def flush(self):
        pass
