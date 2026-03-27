from tkinter import Button, Text, Scrollbar, VERTICAL, END, Frame, Entry, Label, Listbox, W, E, Toplevel
from tkinter.ttk import Combobox
import sys
import threading
import webbrowser
import time
import socket
import re
from datetime import datetime
from db_helper import create_connection, create_main_table, check_user, check_project, log_start, log_stop, calculate_duration, migrate_legacy_user_tables, migrate_projects_to_table, get_all_users, get_all_projects
from utils import DATABASE_PATH

class App:
    def __init__(self, master, stats_port=None):
        self.master = master
        self._ui_thread = threading.current_thread()
        self._stats_port = stats_port
        master.title("WoTITI - Work Time Timer")
        master.configure(bg='#C0C0C0')

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

        # --- Shared configs ---
        button_config = {
            'bg': '#D4D0C8', 'fg': 'black', 'font': ('MS Sans Serif', 10),
            'relief': 'raised', 'borderwidth': 2
        }
        label_config = {
            'bg': '#C0C0C0', 'fg': 'black', 'font': ('MS Sans Serif', 10)
        }
        entry_config = {
            'bg': '#FFFFFF', 'fg': 'black', 'font': ('MS Sans Serif', 10)
        }

        # =====================================================
        # ROW 0: Primary action buttons (Start / Stop) + secondary
        # =====================================================
        self.button_frame = Frame(self.frame, bg='#C0C0C0')
        self.button_frame.grid(row=0, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Start button - prominent, green tint
        self.start_button = Button(
            self.button_frame, text="\u25B6  Start", height=2, width=12,
            command=self.start_session,
            bg='#D4D0C8', fg='black', font=('MS Sans Serif', 11, 'bold'),
            activebackground='#90EE90', relief='raised', borderwidth=2
        )
        self.start_button.grid(row=0, column=0, pady=5, padx=5, sticky=W+E)

        # Stop button - prominent, red tint when active
        self.stop_button = Button(
            self.button_frame, text="\u25A0  Stop", height=2, width=12,
            command=self.stop_session,
            bg='#A9A9A9', fg='black', font=('MS Sans Serif', 11, 'bold'),
            activebackground='#FF6B6B', relief='raised', borderwidth=2,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, pady=5, padx=5, sticky=W+E)

        # Separator
        sep = Frame(self.button_frame, width=20, bg='#C0C0C0')
        sep.grid(row=0, column=2, padx=5)

        # Gesamtzeit button (was "Update TimyTimer")
        self.calculate_button = Button(
            self.button_frame, text="Gesamtzeit", command=self.update_duration, **button_config
        )
        self.calculate_button.grid(row=0, column=3, pady=5, padx=5, sticky=W+E)

        # Statistics Dashboard button
        self.stats_button = Button(
            self.button_frame, text="Stats Dashboard", command=self.open_stats_dashboard, **button_config
        )
        self.stats_button.grid(row=0, column=4, pady=5, padx=5, sticky=W+E)

        # User Management button
        self.user_mgmt_button = Button(
            self.button_frame, text="Benutzer...", command=self.open_user_management, **button_config
        )
        self.user_mgmt_button.grid(row=0, column=5, pady=5, padx=5, sticky=W+E)

        # Configure button frame columns
        self.button_frame.grid_columnconfigure(0, weight=2)
        self.button_frame.grid_columnconfigure(1, weight=2)
        self.button_frame.grid_columnconfigure(2, weight=0)
        self.button_frame.grid_columnconfigure(3, weight=1)
        self.button_frame.grid_columnconfigure(4, weight=1)
        self.button_frame.grid_columnconfigure(5, weight=1)

        # =====================================================
        # ROW 1: Entry frame (Name, Datum, Projekt)
        # =====================================================
        self.entry_frame = Frame(self.frame, bg='#C0C0C0', border=2, relief="sunken", padx=2, pady=2)
        self.entry_frame.grid(row=1, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Name label and combobox
        self.name_label = Label(self.entry_frame, text="Name:", **label_config)
        self.name_label.grid(row=0, column=0, pady=5, padx=5, sticky="w")
        self.name_entry = Combobox(self.entry_frame, font=('MS Sans Serif', 10), width=20)
        self.name_entry.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        self.name_entry.set("Hans")

        # Datum label and entry
        self.date_label = Label(self.entry_frame, text="Datum:", **label_config)
        self.date_label.grid(row=0, column=2, pady=5, padx=5, sticky="w")
        self.date_entry = Entry(self.entry_frame, **entry_config)
        self.date_entry.grid(row=0, column=3, pady=5, padx=5, sticky="ew")
        self.date_entry.insert(0, str(datetime.today().strftime('%d-%m-%Y')))

        # Heute button
        self.heute_button = Button(self.entry_frame, text="Heute", command=self.set_today_date, **button_config)
        self.heute_button.grid(row=0, column=4, pady=5, padx=5, sticky="ew")

        # Project label and combobox
        self.project_label = Label(self.entry_frame, text="Projekt:", **label_config)
        self.project_label.grid(row=0, column=5, pady=5, padx=5, sticky="w")
        self.project_entry = Combobox(self.entry_frame, font=('MS Sans Serif', 10), width=20)
        self.project_entry.grid(row=0, column=6, pady=5, padx=5, sticky="ew")
        self.project_entry.set("1")

        # Configure entry frame columns — ensure combobox/entry columns are wide enough
        for col in range(7):
            if col in (1, 3, 6):
                self.entry_frame.grid_columnconfigure(col, weight=2, minsize=150)
            else:
                self.entry_frame.grid_columnconfigure(col, weight=0)

        # =====================================================
        # ROW 2: Timer display
        # =====================================================
        self.timer_frame = Frame(self.frame, bg='#C0C0C0', border=2, relief="sunken", padx=5, pady=5)
        self.timer_frame.grid(row=2, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        self.timer_time_label = Label(
            self.timer_frame, text="00:00:00", bg='#C0C0C0', fg='red',
            font=('MS Sans Serif', 20, 'bold')
        )
        self.timer_time_label.grid(row=0, column=0, pady=5, padx=10, sticky="w")

        self.timer_name_label = Label(
            self.timer_frame, text="", bg='#C0C0C0', fg='#000080',
            font=('MS Sans Serif', 12)
        )
        self.timer_name_label.grid(row=0, column=1, pady=5, padx=10, sticky="w")

        self.timer_project_label = Label(
            self.timer_frame, text="", bg='#C0C0C0', fg='#000080',
            font=('MS Sans Serif', 12)
        )
        self.timer_project_label.grid(row=0, column=2, pady=5, padx=10, sticky="w")

        self.timer_frame.grid_columnconfigure(0, weight=0)
        self.timer_frame.grid_columnconfigure(1, weight=1)
        self.timer_frame.grid_columnconfigure(2, weight=1)

        # Keep legacy reference for tests
        self.timer_label = self.timer_time_label

        # =====================================================
        # ROW 3: Database content listbox
        # =====================================================
        self.db_content_frame = Frame(self.frame, bg='#C0C0C0')
        self.db_content_frame.grid(row=3, column=0, columnspan=6, pady=5, padx=5, sticky="nsew")

        self.db_content_listbox = Listbox(self.db_content_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        self.db_content_listbox.grid(row=0, column=0, sticky="nsew")

        self.scrollbar_listbox = Scrollbar(self.db_content_frame, orient=VERTICAL, command=self.db_content_listbox.yview, bg='#C0C0C0', width=20)
        self.scrollbar_listbox.grid(row=0, column=1, sticky="ns")
        self.db_content_listbox['yscrollcommand'] = self.scrollbar_listbox.set

        # =====================================================
        # ROW 4: Console + Clear button
        # =====================================================
        self.console_frame = Frame(self.frame, bg='#C0C0C0')
        self.console_frame.grid(row=4, column=0, columnspan=6, sticky="nsew")

        # Clear Console button above console, right-aligned
        self.console_toolbar = Frame(self.console_frame, bg='#C0C0C0')
        self.console_toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.clear_button = Button(
            self.console_toolbar, text="Clear Console", command=self.clear_console,
            bg='#D4D0C8', fg='black', font=('MS Sans Serif', 8), relief='raised', borderwidth=1
        )
        self.clear_button.pack(side='right', padx=2, pady=1)

        self.console = Text(self.console_frame, wrap='word', state='disabled', height=8, bg='black', fg='white', font=('Courier', 10))
        self.console.grid(row=1, column=0, sticky="nsew")

        self.scrollbar = Scrollbar(self.console_frame, orient=VERTICAL, command=self.console.yview, bg='#C0C0C0', width=20)
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.console['yscrollcommand'] = self.scrollbar.set

        # =====================================================
        # Grid weights
        # =====================================================
        self.frame.grid_rowconfigure(3, weight=1)
        self.frame.grid_rowconfigure(4, weight=1)
        for col in range(7):
            self.frame.grid_columnconfigure(col, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)
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
                migrate_projects_to_table(self.db_conn)
                self._refresh_comboboxes()
                self.update_db_content()
        except Exception as e:
            self.write(f"Failed to connect to the database: {e}", error=True)
            self.db_conn = None

        self.session_active = {}
        self.timer_running = False
        self.timer_start_time = None
        self.update_timer_realtime()

        # Session protection: ask before closing with active session
        master.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        """Handle window close — stop active sessions first."""
        active = [k for k, v in self.session_active.items() if v]
        if active:
            from tkinter import messagebox
            name, project = active[0]
            if messagebox.askyesno(
                "Session aktiv",
                f"Session f\u00fcr '{name}' (Projekt {project}) l\u00e4uft noch.\nSession beenden und App schlie\u00dfen?"
            ):
                for (n, p) in active:
                    date = self.get_date() or datetime.today().strftime('%d-%m-%Y')
                    log_stop(project=p, name=n, date=date, conn=self.db_conn)
                self.master.destroy()
            # else: do nothing, keep app open
        else:
            self.master.destroy()

    def _refresh_comboboxes(self):
        """Refresh user and project comboboxes from database."""
        if self.db_conn:
            users = get_all_users(self.db_conn)
            self.name_entry['values'] = users
            projects = get_all_projects(self.db_conn)
            self.project_entry['values'] = projects

    # ----- User Management Window -----
    def open_user_management(self):
        """Open a separate user management window."""
        win = Toplevel(self.master)
        win.title("Benutzerverwaltung")
        win.configure(bg='#C0C0C0')
        win.geometry("400x350")
        win.transient(self.master)
        win.grab_set()

        label_config = {'bg': '#C0C0C0', 'fg': 'black', 'font': ('MS Sans Serif', 10)}
        button_config = {'bg': '#D4D0C8', 'fg': 'black', 'font': ('MS Sans Serif', 10), 'relief': 'raised', 'borderwidth': 2}

        Label(win, text="Benutzer in der Datenbank:", **label_config).pack(pady=(10, 5), padx=10, anchor="w")

        list_frame = Frame(win, bg='#C0C0C0')
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        user_listbox = Listbox(list_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        user_listbox.pack(side='left', fill='both', expand=True)
        sb = Scrollbar(list_frame, orient=VERTICAL, command=user_listbox.yview, bg='#C0C0C0')
        sb.pack(side='right', fill='y')
        user_listbox['yscrollcommand'] = sb.set

        def refresh_list():
            user_listbox.delete(0, END)
            for u in get_all_users(self.db_conn):
                user_listbox.insert(END, u)

        refresh_list()

        # New user frame
        new_frame = Frame(win, bg='#C0C0C0')
        new_frame.pack(fill='x', padx=10, pady=5)
        Label(new_frame, text="Neuer Benutzer:", **label_config).pack(side='left', padx=(0, 5))
        new_entry = Entry(new_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        new_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        def add_user():
            name = new_entry.get().strip()
            if not name:
                return
            if not re.match(r'^[A-Za-z0-9_\-\s]+$', name):
                from tkinter import messagebox
                messagebox.showwarning("Ung\u00fcltiger Name", "Name darf nur Buchstaben, Zahlen, Leerzeichen, - und _ enthalten.", parent=win)
                return
            check_user(self.db_conn, name)
            new_entry.delete(0, END)
            refresh_list()
            self._refresh_comboboxes()

        Button(new_frame, text="Hinzuf\u00fcgen", command=add_user, **button_config).pack(side='left')

        # Select user button
        btn_frame = Frame(win, bg='#C0C0C0')
        btn_frame.pack(fill='x', padx=10, pady=(5, 10))

        def select_user():
            sel = user_listbox.curselection()
            if sel:
                name = user_listbox.get(sel[0])
                self.name_entry.set(name)
                self.update_db_content()
                win.destroy()

        Button(btn_frame, text="Benutzer ausw\u00e4hlen", command=select_user, **button_config).pack(side='left', padx=(0, 5))
        Button(btn_frame, text="Schlie\u00dfen", command=win.destroy, **button_config).pack(side='right')

    # ----- Session management -----
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
                    self._refresh_comboboxes()
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
                duration = calculate_duration(project=project, name=name, conn=self.db_conn)
                print(f"Total duration: {duration:.0f} seconds")
                self.update_timer(duration)
            else:
                self.write("Invalid duration. Please try again.", error=True)
                return None

    # ----- Input getters with validation -----
    def get_project(self):
        val = self.project_entry.get().strip()
        if not val:
            self.write("Projekt darf nicht leer sein.", error=True)
            return None
        return val

    def get_name(self):
        val = self.name_entry.get().strip()
        if not val:
            self.write("Name darf nicht leer sein.", error=True)
            return None
        return val

    def get_date(self):
        val = self.date_entry.get().strip()
        if not val:
            self.write("Datum darf nicht leer sein.", error=True)
            return None
        # Validate format DD-MM-YYYY
        if not re.match(r'^\d{2}-\d{2}-\d{4}$', val):
            self.write(f"Ung\u00fcltiges Datumsformat: '{val}'. Erwartet: DD-MM-YYYY", error=True)
            return None
        return val

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

            # Filter by currently selected user
            current_name = self.name_entry.get().strip()
            if current_name:
                cursor.execute("""
                    SELECT u.name, e.project, e.event_type, e.timestamp
                    FROM events e
                    JOIN users u ON u.id = e.user_id
                    WHERE u.name = ?
                    ORDER BY e.timestamp
                """, (current_name,))
            else:
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
        project = self._get_project_silent()
        name = self._get_name_silent()

        if project is not None and name and self.session_active.get((name, project)):
            duration = calculate_duration(project=project, name=name, conn=self.db_conn) if self.db_conn else 0
            if self.timer_running:
                elapsed_time = time.time() - self.timer_start_time + duration
            else:
                elapsed_time = duration
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_time_label.config(text=f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}")
            self.timer_name_label.config(text=f"[{name}]")
            self.timer_project_label.config(text=f"Projekt: {project}")
        self.master.after(1000, self.update_timer_realtime)

    def update_timer(self, duration):
        """Update the timer label with the elapsed time."""
        project = self._get_project_silent()
        name = self._get_name_silent()

        if project is not None and name:
            if self.timer_running:
                elapsed_time = time.time() - self.timer_start_time + duration
            else:
                elapsed_time = duration
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            self.timer_time_label.config(text=f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}")
            self.timer_name_label.config(text=f"[{name}]")
            self.timer_project_label.config(text=f"Projekt: {project}")
        else:
            self.write("Invalid project or name. Please try again.", error=True)

    def _get_project_silent(self):
        """Get project without validation errors (for timer updates)."""
        val = self.project_entry.get().strip()
        return val if val else None

    def _get_name_silent(self):
        """Get name without validation errors (for timer updates)."""
        val = self.name_entry.get().strip()
        return val if val else None

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
