from tkinter import Button, Text, Scrollbar, VERTICAL, END, Frame, Entry, Label
import sys
import os
import time
from db_helper import create_connection, create_table, insert_data, log_start, log_stop, calculate_duration
from config import DATABASE_PATH

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
        self.button_frame.grid(row=0, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Click Me button
        self.button = Button(self.button_frame, text="Click Me", command=self.on_button_click, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.button.grid(row=0, column=0, pady=5, padx=5, sticky="ew")

        # Insert Default Entry button
        self.insert_button = Button(self.button_frame, text="Insert Default Entry", command=self.insert_default_entry, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.insert_button.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

        # Clear Console button
        self.clear_button = Button(self.button_frame, text="Clear Console", command=self.clear_console, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.clear_button.grid(row=0, column=2, pady=5, padx=5, sticky="ew")

        # Start button
        self.start_button = Button(self.button_frame, text="Start", command=self.start_session, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.start_button.grid(row=0, column=3, pady=5, padx=5, sticky="ew")

        # Stop button
        self.stop_button = Button(self.button_frame, text="Stop", command=self.stop_session, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.stop_button.grid(row=0, column=4, pady=5, padx=5, sticky="ew")

        # Calculate Duration button
        self.calculate_button = Button(self.button_frame, text="Calculate Duration", command=self.calculate_duration, bg='#4CAF50', fg='white', font=('Helvetica', 12, 'bold'))
        self.calculate_button.grid(row=0, column=5, pady=5, padx=5, sticky="ew")

        # Name label and entry
        self.name_label = Label(self.frame, text="Name:", bg='#2e2e2e', fg='white', font=('Helvetica', 12, 'bold'))
        self.name_label.grid(row=1, column=0, pady=5, padx=5, sticky="w")
        self.name_entry = Entry(self.frame, bg='#1e1e1e', fg='white', font=('Helvetica', 12, 'bold'))
        self.name_entry.grid(row=1, column=1, pady=5, padx=5, sticky="ew")

        # Session ID label and entry
        self.session_id_label = Label(self.frame, text="Session ID:", bg='#2e2e2e', fg='white', font=('Helvetica', 12, 'bold'))
        self.session_id_label.grid(row=1, column=2, pady=5, padx=5, sticky="w")
        self.session_id_entry = Entry(self.frame, bg='#1e1e1e', fg='white', font=('Helvetica', 12, 'bold'))
        self.session_id_entry.grid(row=1, column=3, pady=5, padx=5, sticky="ew")

        # Console frame
        self.console_frame = Frame(self.frame, bg='#2e2e2e')
        self.console_frame.grid(row=2, column=0, columnspan=6, sticky="nsew")

        # Console text widget
        self.console = Text(self.console_frame, wrap='word', state='disabled', height=10, bg='#1e1e1e', fg='white', font=('Courier', 10))
        self.console.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for console
        self.scrollbar = Scrollbar(self.console_frame, orient=VERTICAL, command=self.console.yview, bg='#2e2e2e', width=20)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.console['yscrollcommand'] = self.scrollbar.set

        # Configure grid weights
        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_columnconfigure(2, weight=1)
        self.frame.grid_columnconfigure(3, weight=1)
        self.frame.grid_columnconfigure(4, weight=1)
        self.frame.grid_columnconfigure(5, weight=1)
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

    def start_session(self):
        if self.db_conn:
            session_id = self.get_session_id()
            name = self.get_name()
            if session_id is not None:
                print("Starting session...")
                log_start(session_id=session_id, name=name, conn=self.db_conn)

    def stop_session(self):
        if self.db_conn:
            session_id = self.get_session_id()
            name = self.get_name()
            if session_id is not None:
                print("Stopping session...")
                log_stop(session_id=session_id, name=name, conn=self.db_conn)

    def calculate_duration(self):
        if self.db_conn:
            session_id = self.get_session_id()
            if session_id is not None:
                print("Calculating duration...")
                duration = calculate_duration(session_id=session_id, conn=self.db_conn)
                print(f"Total duration: {duration} seconds")

    def get_session_id(self):
        try:
            return int(self.session_id_entry.get())
        except ValueError:
            self.write("Invalid session ID. Please enter an integer.", error=True)
            return None

    def get_name(self):
        return self.name_entry.get()

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
