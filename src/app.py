from tkinter import Button, Text, Scrollbar, VERTICAL, END, Frame, Entry, Label, Listbox
import sys
import time
from datetime import datetime
from db_helper import create_connection, create_main_table, create_user_table, check_user, log_start, log_stop, calculate_duration
from config import DATABASE_PATH

class App:
    def __init__(self, master):
        print("Initializing the application GUI...")
        self.master = master
        master.title("WOTITI - WOrkTImeTImer")
        master.configure(bg='#C0C0C0')  # Windows 98 background color

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
        self.frame = Frame(master, bg='#C0C0C0')
        self.frame.grid(padx=10, pady=10, sticky="nsew")

        # Button frame
        self.button_frame = Frame(self.frame, bg='#C0C0C0')
        self.button_frame.grid(row=0, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Click Me button
        self.button = Button(self.button_frame, text="Click Me", command=self.on_button_click, bg='#D4D0C8', fg='black', font=('MS Sans Serif', 10))
        self.button.grid(row=0, column=0, pady=5, padx=5, sticky="ew")

        # Clear Console button
        self.clear_button = Button(self.button_frame, text="Clear Console", command=self.clear_console, bg='#D4D0C8', fg='black', font=('MS Sans Serif', 10))
        self.clear_button.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

        # Start button
        self.start_button = Button(self.button_frame, text="Start", command=self.start_session, bg='#D4D0C8', fg='black', font=('MS Sans Serif', 10))
        self.start_button.grid(row=0, column=2, pady=5, padx=5, sticky="ew")

        # Stop button
        self.stop_button = Button(self.button_frame, text="Stop", command=self.stop_session, bg='#D4D0C8', fg='black', font=('MS Sans Serif', 10))
        self.stop_button.grid(row=0, column=3, pady=5, padx=5, sticky="ew")
        self.stop_button.config(state="disabled", bg='#A9A9A9')

        # Calculate Duration button
        self.calculate_button = Button(self.button_frame, text="Update TimyTime", command=self.calculate_duration, bg='#D4D0C8', fg='black', font=('MS Sans Serif', 10))
        self.calculate_button.grid(row=0, column=4, pady=5, padx=5, sticky="ew")

        # Entry frame
        self.entry_frame = Frame(self.frame, bg='#C0C0C0')
        self.entry_frame.grid(row=1, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Name label and entry
        self.name_label = Label(self.entry_frame, text="Name:", bg='#C0C0C0', fg='black', font=('MS Sans Serif', 10))
        self.name_label.grid(row=0, column=0, pady=5, padx=5, sticky="w")
        self.name_entry = Entry(self.entry_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        self.name_entry.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        self.name_entry.insert(0, "Hans")  # Default value

        # Datum label and entry
        self.date_label = Label(self.entry_frame, text="Datum:", bg='#C0C0C0', fg='black', font=('MS Sans Serif', 10))
        self.date_label.grid(row=0, column=2, pady=5, padx=5, sticky="w")
        self.date_entry = Entry(self.entry_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        self.date_entry.grid(row=0, column=3, pady=5, padx=5, sticky="ew")
        self.date_entry.insert(0, str(datetime.today().strftime('%Y-%m-%d')))  # Default value

        # Heute button
        self.heute_button = Button(self.entry_frame, text="Heute", command=self.set_today_date, bg='#D4D0C8', fg='black', font=('MS Sans Serif', 10))
        self.heute_button.grid(row=0, column=4, pady=5, padx=5, sticky="ew")

        # project label and entry
        self.project_label = Label(self.entry_frame, text="Projekt:", bg='#C0C0C0', fg='black', font=('MS Sans Serif', 10))
        self.project_label.grid(row=0, column=5, pady=5, padx=5, sticky="w")
        self.project_entry = Entry(self.entry_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        self.project_entry.grid(row=0, column=6, pady=5, padx=5, sticky="ew")
        self.project_entry.insert(0, "1")  # Default value

        # Timer frame
        self.timer_frame = Frame(self.frame, bg='#C0C0C0')
        self.timer_frame.grid(row=2, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Timer label
        self.timer_label = Label(self.timer_frame, text="Timer: 00:00:00", bg='#C0C0C0', fg='red', font=('MS Sans Serif<', 16, 'bold'))
        self.timer_label.grid(row=0, column=0, pady=5, padx=5, sticky="w")

        # Database content frame
        self.db_content_frame = Frame(self.frame, bg='#C0C0C0')
        self.db_content_frame.grid(row=3, column=0, columnspan=6, pady=5, padx=5, sticky="nsew")

        # Database content listbox
        self.db_content_listbox = Listbox(self.db_content_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        self.db_content_listbox.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for Database content listbox
        self.scrollbar_listbox = Scrollbar(self.db_content_frame, orient=VERTICAL, command=self.db_content_listbox.yview, bg='#C0C0C0', width=20)
        self.scrollbar_listbox.grid(row=0, column=1, sticky="ns")
        self.db_content_listbox['yscrollcommand'] = self.scrollbar_listbox.set

        # Console frame
        self.console_frame = Frame(self.frame, bg='#C0C0C0')
        self.console_frame.grid(row=4, column=0, columnspan=6, sticky="nsew")

        # Console text widget
        self.console = Text(self.console_frame, wrap='word', state='disabled', height=10, bg='black', fg='white', font=('Courier', 10))
        self.console.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for console
        self.scrollbar = Scrollbar(self.console_frame, orient=VERTICAL, command=self.console.yview, bg='#C0C0C0', width=20)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.console['yscrollcommand'] = self.scrollbar.set

        # Configure grid weights
        self.frame.grid_rowconfigure(3, weight=1)
        self.frame.grid_rowconfigure(4, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_columnconfigure(2, weight=1)
        self.frame.grid_columnconfigure(3, weight=1)
        self.frame.grid_columnconfigure(4, weight=1)
        self.frame.grid_columnconfigure(5, weight=1)
        self.frame.grid_columnconfigure(6, weight=1)
        self.console_frame.grid_rowconfigure(0, weight=1)
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.db_content_frame.grid_rowconfigure(0, weight=1)
        self.db_content_frame.grid_columnconfigure(0, weight=1)

        # Redirect stdout and stderr to the console
        sys.stdout = self
        sys.stderr = self

        # Database connection
        try:
            self.db_conn = create_connection(DATABASE_PATH)
            if self.db_conn:
                create_main_table(self.db_conn)
                check_user(self.db_conn, "Hans")
                create_user_table(self.db_conn, "Hans")
                self.update_db_content()
        except Exception as e:
            self.write(f"Failed to connect to the database: {e}", error=True)
            self.db_conn = None

        self.session_active = {}
        self.timer_running = False
        self.timer_start_time = None
        self.update_timer_realtime()

    def on_button_click(self):
        print("Button clicked!")

    def start_session(self):
        if self.db_conn:
            project = self.get_project()
            name = self.get_name()
            date = self.get_date()
            if project is not None and name and date:
                if self.session_active.get((name, project), False):
                    self.write("Session already started. Please stop the session before starting again.", error=True)
                else:
                    print("Starting session...")
                    user_id = check_user(self.db_conn, name)
                    if user_id is not None:
                        cursor = self.db_conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (f"{name}_events",))
                        if cursor.fetchone() is None:
                            create_user_table(self.db_conn, name)
                        log_start(project=project, name=name, date=date, conn=self.db_conn)
                        self.session_active[(name, project)] = True
                        self.timer_running = True
                        self.timer_start_time = time.time()
                        self.update_db_content()
                        self.start_button.config(state="disabled", bg='#A9A9A9')
                        self.stop_button.config(state="normal", bg='#D4D0C8')

    def stop_session(self):
        if self.db_conn:
            project = self.get_project()
            name = self.get_name()
            date = self.get_date()
            if project is not None and name:
                if not self.session_active.get((name, project), True):
                    self.write("Session not started. Please start the session before stopping.", error=True)
                else:
                    print("Stopping session...")
                    log_stop(project=project, name=name, date=date, conn=self.db_conn)
                    self.session_active[(name, project)] = False
                    self.timer_running = False
                    self.update_db_content()
                    self.start_button.config(state="normal", bg='#D4D0C8')
                    self.stop_button.config(state="disabled", bg='#A9A9A9')

    def calculate_duration(self):
        if self.db_conn:
            project = self.get_project()
            name = self.get_name()
            if project is not None and name:
                print("Calculating duration...")
                duration = calculate_duration(project=project, name=name, conn=self.db_conn)
                print(f"Total duration: {duration} seconds")
                self.update_timer(duration)

    def get_project(self):
        try:
            return self.project_entry.get()
        except ValueError:
            self.write("Invalid project ID. Please enter an integer.", error=True)
            return None

    def get_name(self):
        return self.name_entry.get()

    def get_date(self):
        return self.date_entry.get()

    def set_today_date(self):
        """Sets the date entry to today's date."""
        self.date_entry.delete(0, END)
        self.date_entry.insert(0, str(datetime.today().strftime('%Y-%m-%d')))

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

    def update_db_content(self):
        """Update the database content listbox with the latest data."""
        self.db_content_listbox.delete(0, END)
        if self.db_conn:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT name FROM users")
            users = cursor.fetchall()
            for user in users:
                user_name = user[0]
                self.db_content_listbox.insert(END, f"User: {user_name}")
                cursor.execute(f"SELECT project, event_type, timestamp FROM {user_name}_events ORDER BY timestamp")
                events = cursor.fetchall()
                for event in events:
                    project, event_type, timestamp = event
                    self.db_content_listbox.insert(END, f"  Projekt {project}: {event_type} at {timestamp}")

    def update_timer_realtime(self):
        """Update the timer label with the elapsed time."""
        project = self.get_project()
        name = self.get_name()

        if project is not None and name and self.session_active.get((name, project)):
            duration = calculate_duration(project=project, name=name, conn=self.db_conn) if self.db_conn else 0
            if self.timer_running:
                elapsed_time = time.time() - self.timer_start_time + duration
            else:
                elapsed_time = duration
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_label.config(text=f"Timer ({name}, Projekt {project}): {int(hours):02}:{int(minutes):02}:{int(seconds):02}")
        # TODO was wenn datenbank noch komplett leer? 
        # else:
        #     self.timer_label.config(text="Timer: 00:00:00")

        # Update rate in ms 
        self.master.after(1000, self.update_timer_realtime)

    def update_timer(self, duration):
        """Update the timer label with the elapsed time."""
        project = self.get_project()
        name = self.get_name()

        if project is not None and name:
            #duration = calculate_duration(project=project, name=name, conn=self.db_conn) if self.db_conn else 0
            if self.timer_running:
                elapsed_time = time.time() - self.timer_start_time + duration
            else:
                elapsed_time = duration
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_label.config(text=f"Timer ({name}, Projekt {project}): {int(hours):02}:{int(minutes):02}:{int(seconds):02}")
