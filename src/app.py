from tkinter import Button, Text, Scrollbar, VERTICAL, END, Frame, Entry, Label, Listbox, W, E, N, S
import sys
import threading
import webbrowser
import time
import socket
from datetime import datetime
from db_helper import create_connection, create_main_table, check_user, log_start, log_stop, calculate_duration, migrate_legacy_user_tables
from utils import DATABASE_PATH

class App:
    def __init__(self, master, stats_port=None):
        print("Initializing the application GUI...")
        self.master = master
        self._ui_thread = threading.current_thread()
        self._stats_port = stats_port
        master.title("WoTITI - Work Time Timer")
        master.configure(bg='#C0C0C0')  # Windows 98 background color

        # Set window size based on screen resolution
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        window_width = int(screen_width * 0.5)  # Adjusted width
        window_height = int(screen_height * 0.5) # Adjusted height
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

        # Button configuration
        button_config = {
            'bg': '#D4D0C8', 'fg': 'black', 'font': ('MS Sans Serif', 10)
        }
        button_sticky = {'sticky': W + E}

        # Click Me button
        self.button = Button(self.button_frame, text="Click Me", command=self.on_button_click, **button_config)
        self.button.grid(row=0, column=0, pady=5, padx=5, **button_sticky)

        # Clear Console button
        self.clear_button = Button(self.button_frame, text="Clear Console", command=self.clear_console, **button_config)
        self.clear_button.grid(row=0, column=1, pady=5, padx=5, **button_sticky)

        # Start button
        self.start_button = Button(self.button_frame, text="Start", height=2, width=8, command=self.start_session, **button_config)
        self.start_button.grid(row=0, column=2, pady=5, padx=5, **button_sticky)

        # Stop button
        self.stop_button = Button(self.button_frame, text="Stop", height=2, width=8, command=self.stop_session, **button_config)
        self.stop_button.grid(row=0, column=3, pady=5, padx=5, **button_sticky)
        self.stop_button.config(state="disabled", bg='#A9A9A9')

        # Update Duration button
        self.calculate_button = Button(self.button_frame, text="Update TimyTimer", command=self.update_duration, **button_config)
        self.calculate_button.grid(row=0, column=4, pady=5, padx=5, **button_sticky)

        # Statistics Dashboard button
        self.stats_button = Button(self.button_frame, text="Open Stats Dashboard", command=self.open_stats_dashboard, **button_config)
        self.stats_button.grid(row=0, column=5, pady=5, padx=5, **button_sticky)

        # Entry frame
        self.entry_frame = Frame(self.frame, bg='#C0C0C0', border=2, relief="sunken", padx=2, pady=2)
        self.entry_frame.grid(row=1, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Entry configuration
        entry_config = {
            'bg': '#FFFFFF', 'fg': 'black', 'font': ('MS Sans Serif', 10)
        }
        label_config = {
            'bg': '#C0C0C0', 'fg': 'black', 'font': ('MS Sans Serif', 10)
        }

        # Name label and entry
        self.name_label = Label(self.entry_frame, text="Name:", **label_config)
        self.name_label.grid(row=0, column=0, pady=5, padx=5, sticky="w")
        self.name_entry = Entry(self.entry_frame, **entry_config)
        self.name_entry.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        self.name_entry.insert(0, "Hans")  # Default value

        # Datum label and entry
        self.date_label = Label(self.entry_frame, text="Datum:", **label_config)
        self.date_label.grid(row=0, column=2, pady=5, padx=5, sticky="w")
        self.date_entry = Entry(self.entry_frame, **entry_config)
        self.date_entry.grid(row=0, column=3, pady=5, padx=5, sticky="ew")
        self.date_entry.insert(0, str(datetime.today().strftime('%d-%m-%Y')))  # Default value

        # Heute button
        self.heute_button = Button(self.entry_frame, text="Heute", command=self.set_today_date, **button_config)
        self.heute_button.grid(row=0, column=4, pady=5, padx=5, sticky="ew")

        # project label and entry
        self.project_label = Label(self.entry_frame, text="Projekt:", **label_config)
        self.project_label.grid(row=0, column=5, pady=5, padx=5, sticky="w")
        self.project_entry = Entry(self.entry_frame, **entry_config)
        self.project_entry.grid(row=0, column=6, pady=5, padx=5, sticky="ew")
        self.project_entry.insert(0, "1")  # Default value

        # Timer frame
        self.timer_frame = Frame(self.frame, bg='#C0C0C0', border=2, relief="sunken", padx=5, pady=5)
        self.timer_frame.grid(row=2, column=0, columnspan=6, pady=5, padx=5, sticky="ew")
        self.timer_label = Label(self.timer_frame, text="[Zeit] 00:00:00 \t [Name] \t\t [Projekt]", bg='#C0C0C0', fg='red', font=('MS Sans Serif<', 16, 'bold'))
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

        # Reflect dashboard status on the button
        self.update_stats_button_state()

        # Database connection
        try:
            self.db_conn = create_connection(DATABASE_PATH)
            if self.db_conn:
                create_main_table(self.db_conn)
                check_user(self.db_conn, "Hans")
                migrate_legacy_user_tables(self.db_conn)
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
                if not self.session_active.get((name, project), False):
                    self.write("Session not started. Please start the session before stopping.", error=True)
                else:
                    print("Stopping session...")
                    log_stop(project=project, name=name, date=date, conn=self.db_conn)
                    self.session_active[(name, project)] = False
                    self.timer_running = False
                    self.update_db_content()
                    self.start_button.config(state="normal", bg='#D4D0C8')
                    self.stop_button.config(state="disabled", bg='#A9A9A9')

    def update_duration(self):
        if self.db_conn:
            project = self.get_project()
            name = self.get_name()
            if project is not None and name:
                print("Calculating duration...")
                duration = calculate_duration(project=project, name=name, conn=self.db_conn)
                print(f"Total duration: {duration} seconds")
                self.update_timer(duration)
            else:
                self.write("Invalid duration. Please try again.", error=True)
                return None

    def get_project(self):
        try:
            return self.project_entry.get()
        except ValueError:
            self.write("Invalid project ID. Please try again.", error=True)
            return None

    def get_name(self):
        try:
            return self.name_entry.get()
        except ValueError:
            self.write("Invalid name. Please try again.", error=True)
            return None

    def get_date(self):
        try:
            return self.date_entry.get()
        except ValueError:
            self.write("Invalid date. Please try again.", error=True)
            return None

    def set_today_date(self):
        """Sets the date entry to today's date."""
        self.date_entry.delete(0, END)
        self.date_entry.insert(0, str(datetime.today().strftime('%d-%m-%Y')))

    def clear_console(self):
        """Clears the console text widget."""
        self.console.configure(state='normal')
        self.console.delete(1.0, END)
        self.console.configure(state='disabled')

    def _fallback_write(self, message, error=False):
        """Writes to real stdout/stderr when GUI is unavailable."""
        stream = sys.__stderr__ if error else sys.__stdout__
        stream.write(message + "\n")
        stream.flush()

    def flush(self):
        """Support file-like API for redirected stdout/stderr."""
        try:
            sys.__stdout__.flush()
            sys.__stderr__.flush()
        except Exception:
            pass

    def write(self, message, error=False):
        """Writes a message to the console with a timestamp."""
        if threading.current_thread() is not self._ui_thread:
            try:
                if self.master.winfo_exists():
                    self.master.after(0, lambda: self.write(message, error))
                else:
                    self._fallback_write(message, error=error)
            except Exception:
                self._fallback_write(message, error=error)
            return

        try:
            if not self.console.winfo_exists():
                self._fallback_write(message, error=error)
                return
        except Exception:
            self._fallback_write(message, error=error)
            return

        timestamp = time.strftime("%d-%m-%Y %H:%M:%S")
        if message.strip():
            message = f"[{timestamp}] {message}"
        try:
            self.console.configure(state='normal')
            if error:
                self.console.insert(END, message, 'error')
                self.console.tag_config('error', foreground='red')
            else:
                self.console.insert(END, message)
            self.console.configure(state='disabled')
            self.console.see(END)
        except Exception:
            self._fallback_write(message, error=error)

    def update_db_content(self):
        """Update the database content listbox with the latest data."""
        self.db_content_listbox.delete(0, END)
        if self.db_conn:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
            if cursor.fetchone() is None:
                return

            cursor.execute("""
                SELECT u.name, e.project, e.event_type, e.timestamp
                FROM events e
                JOIN users u ON u.id = e.user_id
                ORDER BY u.name, e.timestamp
            """)
            events = cursor.fetchall()
            current_user = None
            for user_name, project, event_type, timestamp in events:
                if user_name != current_user:
                    current_user = user_name
                    self.db_content_listbox.insert(END, f"User: {user_name}")
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
            self.timer_label.config(text=f"[Zeit] {int(hours):02}:{int(minutes):02}:{int(seconds):02} \t [Name] {name} \t [Projekt] {project}")
        # Update rate in ms 
        self.master.after(1000, self.update_timer_realtime)

    def update_timer(self, duration):
        """Update the timer label with the elapsed time."""
        project = self.get_project()
        name = self.get_name()

        if project is not None and name:
            if self.timer_running:
                elapsed_time = time.time() - self.timer_start_time + duration
            else:
                elapsed_time = duration
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_label.config(text=f"[Zeit] {int(hours):02}:{int(minutes):02}:{int(seconds):02} \t [Name] {name} \t [Projekt] {project}")
        else:
            self.write("Invalid project or name. Please try again.", error=True)

    def open_stats_dashboard(self):
        """Opens the statistics dashboard."""
        if not self._stats_port or not self._is_dashboard_running():
            self.write("Stats dashboard is not running yet.", error=True)
            return

        try:
            url = f"http://127.0.0.1:{self._stats_port}/"
            print(f"Opening statistics dashboard at {url}")
            webbrowser.open(url)
        except Exception as e:
            self.write(f"Failed to open statistics dashboard: {e}", error=True)

    def _is_dashboard_running(self):
        if not self._stats_port:
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                return sock.connect_ex(("127.0.0.1", self._stats_port)) == 0
        except Exception:
            return False

    def update_stats_button_state(self):
        """Update stats button color based on dashboard status."""
        is_running = self._is_dashboard_running()
        if is_running:
            self.stats_button.config(bg="#D4D0C8", fg="black")
        else:
            self.stats_button.config(bg="#B00020", fg="white")
        self.master.after(2000, self.update_stats_button_state)
