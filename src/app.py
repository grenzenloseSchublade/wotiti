import contextlib
import glob
import logging
import os
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from shutil import which
from tkinter import (
    END,
    VERTICAL,
    BooleanVar,
    Button,
    Checkbutton,
    E,
    Entry,
    Frame,
    Label,
    LabelFrame,
    Listbox,
    Scrollbar,
    Spinbox,
    Text,
    Toplevel,
    W,
    messagebox,
)
from tkinter.ttk import Combobox

if sys.platform.startswith("win"):
    import winsound
else:
    winsound = None

from db_helper import (
    TIMESTAMP_FORMAT,
    calculate_duration,
    check_user,
    close_stale_breaks,
    create_break_events_table,
    create_connection,
    create_events_table,
    create_main_table,
    delete_event,
    get_all_projects,
    get_all_users,
    get_event_by_id,
    get_open_break,
    log_break_start,
    log_break_stop,
    log_start,
    log_stop,
    migrate_legacy_user_tables,
    migrate_projects_to_table,
    update_event,
)
from utils import (
    DATABASE_PATH,
    PATH_TO_DATA,
    PATH_TO_SOUNDS,
    load_config,
    save_config,
)

logger = logging.getLogger(__name__)


class App:
    def __init__(self, master, stats_port=None):
        self.master = master
        self._ui_thread = threading.current_thread()
        self._stats_port = stats_port
        self.config = load_config()
        self._db_path = self.config.get("database_path", DATABASE_PATH)
        self._mini_mode = False
        self._closing = False
        self._drag_data = {"x": 0, "y": 0}
        self._combobox_dirty = True
        self._cached_users = []
        self._cached_projects = []
        self._full_geometry = ""
        self._mini_width = 300
        self._mini_height = 75
        self._mini_last_position = str(self.config.get("mini_window_position", "")).strip()
        self._break_active = False
        self._break_end_ts = 0.0
        self._break_started_ts = 0.0
        self._current_break_kind = "short"
        self._current_break_source = "pomodoro_break"
        self._pomodoro_cycles = 0
        self._session_started_ts = 0.0
        self._pomodoro_work_deadline_ts = 0.0
        self._paused_pomodoro_remaining_seconds = 0
        self._last_break_project = None
        self._last_break_user = None
        os.makedirs(PATH_TO_SOUNDS, exist_ok=True)

        # Pomodoro settings (persisted in config)
        self.pomodoro_enabled = bool(self.config.get("pomodoro_enabled", False))
        self.pomodoro_work_minutes = int(self.config.get("pomodoro_work_minutes", 25))
        self.pomodoro_break_minutes = int(self.config.get("pomodoro_break_minutes", 5))
        self.pomodoro_long_break_minutes = int(self.config.get("pomodoro_long_break_minutes", 15))
        self.pomodoro_long_break_every = int(self.config.get("pomodoro_long_break_every", 4))
        self.pomodoro_auto_break = bool(self.config.get("pomodoro_auto_break", True))
        self.pomodoro_sound_enabled = bool(self.config.get("pomodoro_sound_enabled", True))
        self.pomodoro_sound_local_path = str(self.config.get("pomodoro_sound_local_path", "sounds/StartupSound.wav")).strip()
        self._cached_sound_path = ""
        self._cached_sound_player = ""

        master.title("WoTITI - Work Time Timer")
        master.configure(bg='#C0C0C0')

        # Restore last window geometry when available, fallback to sensible size.
        saved_geometry = str(self.config.get("window_geometry", "")).strip()
        if re.match(r"^\d+x\d+\+\d+\+\d+$", saved_geometry):
            master.geometry(saved_geometry)
        else:
            master.geometry("720x540")
        master.minsize(640, 440)

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
            self.button_frame, text="\u25B6 Start", height=2, width=8,
            command=self.start_session,
            bg='#D4D0C8', fg='black', font=('MS Sans Serif', 10, 'bold'),
            activebackground='#90EE90', relief='raised', borderwidth=2
        )
        self.start_button.grid(row=0, column=0, pady=5, padx=3, sticky=W+E)

        # Pause button - toggle pause/resume
        self.pause_button = Button(
            self.button_frame, text="\u25AE\u25AE Pause", height=2, width=8,
            command=self.pause_session,
            bg='#A9A9A9', fg='black', font=('MS Sans Serif', 10, 'bold'),
            activebackground='#FFD700', relief='raised', borderwidth=2,
            state="disabled"
        )
        self.pause_button.grid(row=0, column=1, pady=5, padx=3, sticky=W+E)

        # Stop button - ends session completely
        self.stop_button = Button(
            self.button_frame, text="\u25A0 Stop", height=2, width=8,
            command=self.stop_session,
            bg='#A9A9A9', fg='black', font=('MS Sans Serif', 10, 'bold'),
            activebackground='#FF6B6B', relief='raised', borderwidth=2,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=2, pady=5, padx=3, sticky=W+E)

        # Separator
        self.button_separator = Frame(self.button_frame, width=10, bg='#C0C0C0')
        self.button_separator.grid(row=0, column=3, padx=2)

        self.calculate_button = Button(
            self.button_frame, text="Aktualisieren", command=self.update_duration, **button_config
        )
        self.calculate_button.grid(row=0, column=4, pady=5, padx=3, sticky=W+E)

        self.stats_button = Button(
            self.button_frame, text="Auswertung", command=self.open_stats_dashboard, **button_config
        )
        self.stats_button.grid(row=0, column=5, pady=5, padx=3, sticky=W+E)

        self.user_mgmt_button = Button(
            self.button_frame, text="Benutzer", command=self.open_user_management, **button_config
        )
        self.user_mgmt_button.grid(row=0, column=6, pady=5, padx=3, sticky=W+E)

        self.settings_button = Button(
            self.button_frame, text="\u2699 Einst.", command=self.open_settings, **button_config
        )
        self.settings_button.grid(row=0, column=7, pady=5, padx=3, sticky=W+E)

        self.mini_button = Button(
            self.button_frame, text="\u25BD Mini", command=self._toggle_mini_mode, **button_config
        )
        self.mini_button.grid(row=0, column=8, pady=5, padx=3, sticky=W+E)

        # Configure button frame columns
        self.button_frame.grid_columnconfigure(0, weight=2)
        self.button_frame.grid_columnconfigure(1, weight=2)
        self.button_frame.grid_columnconfigure(2, weight=2)
        self.button_frame.grid_columnconfigure(3, weight=0)
        self.button_frame.grid_columnconfigure(4, weight=1)
        self.button_frame.grid_columnconfigure(5, weight=1)
        self.button_frame.grid_columnconfigure(6, weight=1)
        self.button_frame.grid_columnconfigure(7, weight=1)
        self.button_frame.grid_columnconfigure(8, weight=1)

        # =====================================================
        # ROW 1: Entry frame (Name, Datum, Projekt)
        # =====================================================
        self.entry_frame = Frame(self.frame, bg='#C0C0C0', border=2, relief="sunken", padx=2, pady=2)
        self.entry_frame.grid(row=1, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        # Name label and combobox
        self.name_label = Label(self.entry_frame, text="Name:", **label_config)
        self.name_label.grid(row=0, column=0, pady=5, padx=3, sticky="w")
        self.name_entry = Combobox(self.entry_frame, font=('MS Sans Serif', 10), width=14)
        self.name_entry.grid(row=0, column=1, pady=5, padx=3, sticky="ew")
        self.name_entry.set("Hans")

        # Datum label and entry
        self.date_label = Label(self.entry_frame, text="Datum (TT-MM-JJJJ):", **label_config)
        self.date_label.grid(row=0, column=2, pady=5, padx=3, sticky="w")
        self.date_entry = Entry(self.entry_frame, **entry_config, width=12)
        self.date_entry.grid(row=0, column=3, pady=5, padx=3, sticky="ew")
        self.date_entry.insert(0, str(datetime.today().strftime('%d-%m-%Y')))

        # Heute button
        self.heute_button = Button(self.entry_frame, text="Heute", command=self.set_today_date, **button_config)
        self.heute_button.grid(row=0, column=4, pady=5, padx=3, sticky="ew")

        # Project label and combobox
        self.project_label = Label(self.entry_frame, text="Projekt:", **label_config)
        self.project_label.grid(row=0, column=5, pady=5, padx=3, sticky="w")
        self.project_entry = Combobox(self.entry_frame, font=('MS Sans Serif', 10), width=14)
        self.project_entry.grid(row=0, column=6, pady=5, padx=3, sticky="ew")
        self.project_entry.set("1")

        # Configure entry frame columns — ensure combobox/entry columns are flexible
        for col in range(7):
            if col == 3:
                self.entry_frame.grid_columnconfigure(col, weight=1, minsize=80)
            elif col in (1, 6):
                self.entry_frame.grid_columnconfigure(col, weight=2, minsize=100)
            else:
                self.entry_frame.grid_columnconfigure(col, weight=0)

        # =====================================================
        # ROW 2: Timer display
        # =====================================================
        self.timer_frame = Frame(self.frame, bg='#C0C0C0', border=2, relief="sunken", padx=5, pady=5)
        self.timer_frame.grid(row=2, column=0, columnspan=6, pady=5, padx=5, sticky="ew")

        self.timer_time_label = Label(
            self.timer_frame, text="00:00:00", bg='#C0C0C0', fg='red',
            font=('MS Sans Serif', 28, 'bold')
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

        self.break_time_label = Label(
            self.timer_frame, text="--:--", bg='#C0C0C0', fg='#0000FF',
            font=('MS Sans Serif', 12, 'bold')
        )
        self.break_time_label.grid(row=0, column=3, pady=5, padx=10, sticky="e")

        self.timer_frame.grid_columnconfigure(0, weight=0)
        self.timer_frame.grid_columnconfigure(1, weight=1)
        self.timer_frame.grid_columnconfigure(2, weight=1)
        self.timer_frame.grid_columnconfigure(3, weight=0)

        # Keep legacy reference for tests
        self.timer_label = self.timer_time_label

        # =====================================================
        # ROW 3: Database content listbox
        # =====================================================
        self.db_content_frame = Frame(self.frame, bg='#C0C0C0')
        self.db_content_frame.grid(row=3, column=0, columnspan=6, pady=5, padx=5, sticky="nsew")

        self.db_content_listbox = Listbox(self.db_content_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10))
        self.db_content_listbox.grid(row=0, column=0, sticky="nsew")
        self.db_content_listbox.bind('<Double-1>', self._edit_event)
        self._event_ids: list[int | None] = []

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
            self.console_toolbar, text="Konsole leeren", command=self.clear_console,
            bg='#D4D0C8', fg='black', font=('MS Sans Serif', 8), relief='raised', borderwidth=1
        )
        self.clear_button.pack(side='right', padx=2, pady=1)
        self.copy_console_button = Button(
            self.console_toolbar, text="Copy", command=self._copy_console,
            bg='#D4D0C8', fg='black', font=('MS Sans Serif', 8), relief='raised', borderwidth=1
        )
        self.copy_console_button.pack(side='right', padx=2, pady=1)

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

        # =====================================================
        # MINI MODE: Dedicated Toplevel window (hidden by default)
        # =====================================================
        self._mini_toplevel = Toplevel(master)
        self._mini_toplevel.title("WoTITI Mini")
        self._mini_toplevel.overrideredirect(True)
        self._mini_toplevel.attributes('-topmost', True)
        self._mini_toplevel.geometry(f"{self._mini_width}x{self._mini_height}")
        self._mini_toplevel.configure(bg='#C0C0C0')
        self._mini_toplevel.resizable(False, False)
        self._mini_toplevel.protocol("WM_DELETE_WINDOW", self._exit_mini_mode)
        self._mini_toplevel.withdraw()

        self._mini_toplevel.grid_rowconfigure(0, weight=1)
        self._mini_toplevel.grid_columnconfigure(0, weight=1)

        self._mini_frame = Frame(self._mini_toplevel, bg='#C0C0C0')
        self._mini_frame.grid(padx=4, pady=4, sticky='nsew')
        mini_btn = {'bg': '#D4D0C8', 'fg': 'black', 'font': ('MS Sans Serif', 9),
                    'relief': 'raised', 'borderwidth': 2}

        # Row 0: Buttons
        self._mini_start_btn = Button(
            self._mini_frame, text="\u25B6", command=self.start_session,
            width=3, height=1, bg='#D4D0C8', fg='green',
            font=('MS Sans Serif', 11, 'bold'), relief='raised', borderwidth=2)
        self._mini_start_btn.grid(row=0, column=0, padx=2, pady=2, sticky='ew')

        self._mini_pause_btn = Button(
            self._mini_frame, text="\u25AE\u25AE", command=self.pause_session,
            width=3, height=1, bg='#A9A9A9', fg='#B8860B',
            font=('MS Sans Serif', 11, 'bold'), relief='raised', borderwidth=2,
            state="disabled")
        self._mini_pause_btn.grid(row=0, column=1, padx=2, pady=2, sticky='ew')

        self._mini_stop_btn = Button(
            self._mini_frame, text="\u25A0", command=self.stop_session,
            width=2, height=1, bg='#A9A9A9', fg='red',
            font=('MS Sans Serif', 11, 'bold'), relief='raised', borderwidth=2,
            state="disabled")
        self._mini_stop_btn.grid(row=0, column=2, padx=2, pady=2, sticky='ew')

        self._mini_restore_btn = Button(
            self._mini_frame, text="\u25B3", command=self._toggle_mini_mode, width=2, **mini_btn)
        self._mini_restore_btn.grid(row=0, column=3, padx=2, pady=2, sticky='ew')

        # Row 1: Timer + Break + Projekt
        self._mini_timer_label = Label(
            self._mini_frame, text="00:00:00", bg='#C0C0C0', fg='red',
            font=('MS Sans Serif', 18, 'bold'))
        self._mini_timer_label.grid(row=1, column=0, padx=4, pady=2, sticky='w')

        self._mini_break_label = Label(
            self._mini_frame, text="", bg='#C0C0C0', fg='#0000FF',
            font=('MS Sans Serif', 10, 'bold'))
        self._mini_break_label.grid(row=1, column=1, padx=2, pady=2, sticky='w')

        self._mini_project_combo = Combobox(
            self._mini_frame, font=('MS Sans Serif', 9), width=7)
        self._mini_project_combo.grid(row=1, column=2, columnspan=2, padx=4, pady=2, sticky='ew')

        self._mini_frame.grid_columnconfigure(0, weight=1)
        self._mini_frame.grid_columnconfigure(1, weight=0)
        self._mini_frame.grid_columnconfigure(2, weight=1)
        self._mini_frame.grid_columnconfigure(3, weight=1)

        # Enable dragging on mini mode (always bound, Toplevel handles visibility)
        self._mini_frame.bind("<Button-1>", self._drag_start)
        self._mini_frame.bind("<B1-Motion>", self._drag_move)
        self._mini_timer_label.bind("<Button-1>", self._drag_start)
        self._mini_timer_label.bind("<B1-Motion>", self._drag_move)

        # Reflect dashboard status on the button
        self.update_stats_button_state()

        # Database connection
        try:
            self.db_conn = create_connection(self._db_path)
            if self.db_conn:
                logger.info("Datenbankverbindung hergestellt: %s", self._db_path)
                create_main_table(self.db_conn)
                create_events_table(self.db_conn)
                create_break_events_table(self.db_conn)
                close_stale_breaks(self.db_conn)
                default_user = self.config.get("default_user", "Hans")
                check_user(self.db_conn, default_user)
                migrate_legacy_user_tables(self.db_conn)
                migrate_projects_to_table(self.db_conn)
                self._refresh_comboboxes(force=True)
                self.name_entry.set(default_user)
                default_project = self.config.get("default_project", "1")
                self.project_entry.set(default_project)
                self.update_db_content()
        except Exception as e:
            logger.error("Datenbankverbindung fehlgeschlagen: %s", e)
            self.write(f"Datenbankverbindung fehlgeschlagen: {e}", error=True)
            self.db_conn = None

        self.session_active = {}
        self.timer_running = False
        self.timer_start_time = None
        self.update_timer_realtime()

        # Keyboard shortcuts
        master.bind("<Control-s>", lambda e: self.start_session())
        master.bind("<Control-e>", lambda e: self.stop_session())
        master.bind("<Control-m>", lambda e: self._toggle_mini_mode())
        master.bind("<Control-p>", lambda e: self.pause_session())

        # Session protection: ask before closing with active session
        master.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Pre-resolve sound path and player executable for instant playback.
        self._preload_sound()

    def _on_closing(self):
        """Handle window close — stop active sessions and breaks first."""
        active = [k for k, v in self.session_active.items() if v]

        if self._break_active or active:
            msg_parts = []
            if self._break_active:
                msg_parts.append("Eine Pause ist aktiv.")
            if active:
                name, project = active[0]
                msg_parts.append(f"Session f\u00fcr '{name}' (Projekt {project}) l\u00e4uft noch.")
            msg_parts.append("Alles beenden und App schlie\u00dfen?")
            if not messagebox.askyesno("Aktive Arbeit", "\n".join(msg_parts)):
                return  # User cancelled

        if self._break_active:
            self._finish_break(play_sound=False, bring_to_front=False, auto_resume=False)

        try:
            geometry = self._full_geometry if self._mini_mode and self._full_geometry else self.master.geometry()
            if geometry:
                self.config["window_geometry"] = geometry
                save_config(self.config)
        except OSError as e:
            logger.warning("Fenstergröße konnte nicht gespeichert werden: %s", e)

        # Re-check: manual break may have closed the session already.
        active = [k for k, v in self.session_active.items() if v]
        if active:
            for (n, p) in active:
                date = datetime.today().strftime('%d-%m-%Y')
                log_stop(project=p, name=n, date=date, conn=self.db_conn)

        self._closing = True
        if self.db_conn:
            try:
                self.db_conn.close()
                logger.info("Datenbankverbindung geschlossen.")
            except Exception as e:
                logger.error("Fehler beim Schlie\u00dfen der DB: %s", e)
        with contextlib.suppress(Exception):
            self._mini_toplevel.destroy()
        self.master.destroy()

    def _toggle_mini_mode(self):
        """Toggle between full and compact mini mode."""
        if self._mini_mode:
            self._exit_mini_mode()
        else:
            self._enter_mini_mode()

    def _enter_mini_mode(self):
        """Switch to compact always-on-top Toplevel; hide main window."""
        self._mini_mode = True
        self._full_geometry = self.master.geometry()

        # Sync project values from main to mini
        self._mini_project_combo['values'] = self.project_entry['values']
        self._mini_project_combo.set(self.project_entry.get().strip())
        self._mini_timer_label.configure(text=self.timer_time_label.cget('text'))
        self._mini_break_label.configure(text=self.break_time_label.cget('text'))

        # Lock project combo during active session or break to prevent orphaned sessions.
        if any(self.session_active.values()) or self._break_active:
            self._mini_project_combo.config(state='disabled')
        else:
            self._mini_project_combo.config(state='readonly')

        # Show mini Toplevel first, then hide main window. This avoids a
        # transient "no window visible" state on some window managers.
        self.master.update_idletasks()
        if re.match(r"^\+\d+\+\d+$", self._mini_last_position):
            self._mini_toplevel.geometry(f"{self._mini_width}x{self._mini_height}{self._mini_last_position}")
        else:
            x = self.master.winfo_x()
            y = self.master.winfo_y()
            self._mini_toplevel.geometry(f"{self._mini_width}x{self._mini_height}+{x}+{y}")
        self._mini_toplevel.deiconify()
        self._mini_toplevel.lift()
        with contextlib.suppress(Exception):
            self._mini_toplevel.focus_force()
        self.master.withdraw()

    def _exit_mini_mode(self):
        """Hide mini Toplevel, restore main window."""
        self._mini_mode = False

        # Persist mini position for the next open.
        with contextlib.suppress(Exception):
            self._mini_last_position = f"+{self._mini_toplevel.winfo_x()}+{self._mini_toplevel.winfo_y()}"
            self.config["mini_window_position"] = self._mini_last_position
            save_config(self.config)

        # Sync project selection back from mini to main
        self.project_entry.set(self._mini_project_combo.get().strip())

        # Restore main window first, then hide mini Toplevel.
        self.master.geometry(self._full_geometry)
        self.master.deiconify()
        self.master.lift()
        self._mini_toplevel.withdraw()

    def _drag_start(self, event):
        """Record starting position for window drag."""
        self._drag_data["x"] = event.x_root - self._mini_toplevel.winfo_x()
        self._drag_data["y"] = event.y_root - self._mini_toplevel.winfo_y()

    def _drag_move(self, event):
        """Move window as mouse drags."""
        x = event.x_root - self._drag_data["x"]
        y = event.y_root - self._drag_data["y"]
        self._mini_toplevel.geometry(f"+{x}+{y}")
        self._mini_last_position = f"+{x}+{y}"

    def _refresh_comboboxes(self, force=False):
        """Refresh user and project comboboxes from database (cached)."""
        if not self.db_conn:
            return
        if not force and not self._combobox_dirty:
            return
        users = get_all_users(self.db_conn)
        projects = get_all_projects(self.db_conn)
        if users != self._cached_users:
            self._cached_users = users
            self.name_entry['values'] = users
        if projects != self._cached_projects:
            self._cached_projects = projects
            self.project_entry['values'] = projects
            self._mini_project_combo['values'] = projects
        self._combobox_dirty = False

    # ----- User Management Window -----
    def open_user_management(self):
        """Open a separate user management window."""
        win = Toplevel(self.master)
        win.title("Benutzerverwaltung")
        win.configure(bg='#C0C0C0')
        w, h = 400, 350
        x = self.master.winfo_x() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.transient(self.master)
        win.wait_visibility()
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

                messagebox.showwarning("Ung\u00fcltiger Name", "Name darf nur Buchstaben, Zahlen, Leerzeichen, - und _ enthalten.", parent=win)
                return
            check_user(self.db_conn, name)
            new_entry.delete(0, END)
            refresh_list()
            self._combobox_dirty = True
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
    # ----- Settings Window -----
    def open_settings(self):
        """Open the settings/configuration window."""
        # Block if any session is active
        active = [k for k, v in self.session_active.items() if v]
        if active:
            messagebox.showwarning(
                "Session aktiv",
                "Bitte alle laufenden Sessions stoppen, bevor die Einstellungen geöffnet werden.",
                parent=self.master,
            )
            return

        win = Toplevel(self.master)
        win.title("Einstellungen")
        win.configure(bg='#C0C0C0')
        w, h = 560, 780
        x = self.master.winfo_x() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.transient(self.master)
        win.wait_visibility()
        win.grab_set()

        lbl = {'bg': '#C0C0C0', 'fg': 'black', 'font': ('MS Sans Serif', 10)}
        btn = {'bg': '#D4D0C8', 'fg': 'black', 'font': ('MS Sans Serif', 10), 'relief': 'raised', 'borderwidth': 2}

        # ── Datenbank ──
        db_frame = LabelFrame(win, text="Datenbank", bg='#C0C0C0', fg='black',
                              font=('MS Sans Serif', 10, 'bold'), padx=8, pady=8)
        db_frame.pack(fill='x', padx=10, pady=(10, 5))

        Label(db_frame, text="Aktive Datenbank:", **lbl).grid(row=0, column=0, sticky='w', pady=2)
        db_var = Combobox(db_frame, font=('MS Sans Serif', 10), width=35)
        db_var.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        def _refresh_db_list():
            dbs = sorted(glob.glob(os.path.join(PATH_TO_DATA, "**", "*.db"), recursive=True))
            db_var['values'] = dbs
            if self._db_path in dbs:
                db_var.set(self._db_path)
            elif dbs:
                db_var.set(dbs[0])

        _refresh_db_list()

        btn_row = Frame(db_frame, bg='#C0C0C0')
        btn_row.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky='ew')

        def _browse_db():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                initialdir=PATH_TO_DATA,
                filetypes=[("SQLite Datenbank", "*.db"), ("Alle Dateien", "*.*")],
                parent=win,
            )
            if path:
                db_var.set(path)

        def _new_db():
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                initialdir=PATH_TO_DATA,
                defaultextension=".db",
                filetypes=[("SQLite Datenbank", "*.db")],
                parent=win,
            )
            if path:
                try:
                    conn = create_connection(path)
                    if conn:
                        create_main_table(conn)
                        create_events_table(conn)
                        create_break_events_table(conn)
                        conn.close()
                        _refresh_db_list()
                        db_var.set(path)
                        logger.info("Neue Datenbank erstellt: %s", path)
                        self.write(f"Neue Datenbank erstellt: {path}")
                except Exception as e:
                    messagebox.showerror("Fehler", f"Datenbank konnte nicht erstellt werden:\n{e}", parent=win)

        def _delete_db():
            target = db_var.get().strip()
            if not target or not os.path.isfile(target):
                messagebox.showwarning("Keine Auswahl", "Bitte eine vorhandene Datenbank auswählen.", parent=win)
                return
            if os.path.abspath(target) == os.path.abspath(self._db_path):
                messagebox.showwarning("Nicht möglich", "Die aktive Datenbank kann nicht gelöscht werden.\nBitte zuerst eine andere Datenbank auswählen.", parent=win)
                return
            if messagebox.askyesno("Datenbank löschen",
                                   f"Datenbank wirklich löschen?\n\n{target}\n\nDieser Vorgang kann nicht rückgängig gemacht werden!",
                                   parent=win):
                try:
                    os.remove(target)
                    _refresh_db_list()
                    logger.info("Datenbank gelöscht: %s", target)
                    self.write(f"Datenbank gelöscht: {target}")
                except OSError as e:
                    messagebox.showerror("Fehler", f"Löschen fehlgeschlagen:\n{e}", parent=win)

        Button(btn_row, text="Durchsuchen...", command=_browse_db, **btn).pack(side='left', padx=(0, 5))
        Button(btn_row, text="Neue DB", command=_new_db, **btn).pack(side='left', padx=(0, 5))
        Button(btn_row, text="DB löschen", command=_delete_db, fg='#B00020', **{k: v for k, v in btn.items() if k != 'fg'}).pack(side='left')

        db_frame.grid_columnconfigure(1, weight=1)

        # ── Benutzer ──
        user_frame = LabelFrame(win, text="Benutzer & Projekt", bg='#C0C0C0', fg='black',
                                font=('MS Sans Serif', 10, 'bold'), padx=8, pady=8)
        user_frame.pack(fill='x', padx=10, pady=5)

        Label(user_frame, text="Standard-Benutzer:", **lbl).grid(row=0, column=0, sticky='w', pady=2)
        default_user_var = Combobox(user_frame, font=('MS Sans Serif', 10), width=20)
        default_user_var.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        if self.db_conn:
            default_user_var['values'] = get_all_users(self.db_conn)
        default_user_var.set(self.config.get("default_user", "Hans"))

        Label(user_frame, text="Standard-Projekt:", **lbl).grid(row=1, column=0, sticky='w', pady=2)
        default_proj_var = Combobox(user_frame, font=('MS Sans Serif', 10), width=20)
        default_proj_var.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        if self.db_conn:
            default_proj_var['values'] = get_all_projects(self.db_conn)
        default_proj_var.set(self.config.get("default_project", "1"))

        user_frame.grid_columnconfigure(1, weight=1)

        # ── Dashboard ──
        dash_frame = LabelFrame(win, text="Auswertung (Dashboard)", bg='#C0C0C0', fg='black',
                                font=('MS Sans Serif', 10, 'bold'), padx=8, pady=8)
        dash_frame.pack(fill='x', padx=10, pady=5)

        Label(dash_frame, text="Port:", **lbl).grid(row=0, column=0, sticky='w', pady=2)
        port_var = Spinbox(dash_frame, from_=1024, to=65535, width=8,
                           font=('MS Sans Serif', 10), bg='#FFFFFF', fg='black')
        port_var.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        port_var.delete(0, END)
        port_var.insert(0, str(self.config.get("dashboard_port", 8052)))

        Label(dash_frame, text="Theme:", **lbl).grid(row=1, column=0, sticky='w', pady=2)
        theme_var = Combobox(dash_frame, font=('MS Sans Serif', 10), width=15,
                             values=["Modern", "Synthwave"], state='readonly')
        theme_var.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        theme_var.set(self.config.get("theme", "Modern"))

        # ── Pomodoro ──
        pomodoro_frame = LabelFrame(win, text="Pomodoro & Pause", bg='#C0C0C0', fg='black',
                        font=('MS Sans Serif', 10, 'bold'), padx=8, pady=8)
        pomodoro_frame.pack(fill='x', padx=10, pady=5)

        pomodoro_enabled_var = BooleanVar(value=self.pomodoro_enabled)
        pomodoro_auto_var = BooleanVar(value=self.pomodoro_auto_break)
        pomodoro_sound_enabled_var = BooleanVar(value=self.pomodoro_sound_enabled)

        Checkbutton(
            pomodoro_frame,
            text="Pomodoro aktiv",
            variable=pomodoro_enabled_var,
            bg='#C0C0C0',
            fg='black',
            selectcolor='#C0C0C0',
            activebackground='#C0C0C0',
            font=('MS Sans Serif', 10),
        ).grid(row=0, column=0, columnspan=2, sticky='w', pady=2)

        Label(pomodoro_frame, text="Arbeitszeit (min):", **lbl).grid(row=1, column=0, sticky='w', pady=2)
        pomodoro_work_var = Spinbox(pomodoro_frame, from_=1, to=120, width=8,
                        font=('MS Sans Serif', 10), bg='#FFFFFF', fg='black')
        pomodoro_work_var.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        pomodoro_work_var.delete(0, END)
        pomodoro_work_var.insert(0, str(self.pomodoro_work_minutes))

        Label(pomodoro_frame, text="Kurze Pause (min):", **lbl).grid(row=2, column=0, sticky='w', pady=2)
        pomodoro_break_var = Spinbox(pomodoro_frame, from_=1, to=60, width=8,
                         font=('MS Sans Serif', 10), bg='#FFFFFF', fg='black')
        pomodoro_break_var.grid(row=2, column=1, padx=5, pady=2, sticky='w')
        pomodoro_break_var.delete(0, END)
        pomodoro_break_var.insert(0, str(self.pomodoro_break_minutes))

        Label(pomodoro_frame, text="Lange Pause (min):", **lbl).grid(row=3, column=0, sticky='w', pady=2)
        pomodoro_long_break_var = Spinbox(pomodoro_frame, from_=1, to=120, width=8,
                          font=('MS Sans Serif', 10), bg='#FFFFFF', fg='black')
        pomodoro_long_break_var.grid(row=3, column=1, padx=5, pady=2, sticky='w')
        pomodoro_long_break_var.delete(0, END)
        pomodoro_long_break_var.insert(0, str(self.pomodoro_long_break_minutes))

        Label(pomodoro_frame, text="Lange Pause alle N:", **lbl).grid(row=4, column=0, sticky='w', pady=2)
        pomodoro_every_var = Spinbox(pomodoro_frame, from_=2, to=12, width=8,
                         font=('MS Sans Serif', 10), bg='#FFFFFF', fg='black')
        pomodoro_every_var.grid(row=4, column=1, padx=5, pady=2, sticky='w')
        pomodoro_every_var.delete(0, END)
        pomodoro_every_var.insert(0, str(self.pomodoro_long_break_every))

        Checkbutton(
            pomodoro_frame,
            text="Auto-Pause",
            variable=pomodoro_auto_var,
            bg='#C0C0C0',
            fg='black',
            selectcolor='#C0C0C0',
            activebackground='#C0C0C0',
            font=('MS Sans Serif', 10),
        ).grid(row=0, column=2, columnspan=2, sticky='w', pady=2)

        Checkbutton(
            pomodoro_frame,
            text="Sound aktiv",
            variable=pomodoro_sound_enabled_var,
            bg='#C0C0C0',
            fg='black',
            selectcolor='#C0C0C0',
            activebackground='#C0C0C0',
            font=('MS Sans Serif', 10),
        ).grid(row=1, column=2, columnspan=2, sticky='w', pady=2)

        Label(pomodoro_frame, text="Sound Datei:", **lbl).grid(row=3, column=2, sticky='w', pady=2)
        sound_file_entry = Entry(pomodoro_frame, bg='#FFFFFF', fg='black', font=('MS Sans Serif', 10), width=28)
        sound_file_entry.grid(row=3, column=3, padx=5, pady=2, sticky='ew')
        sound_file_entry.insert(0, self.pomodoro_sound_local_path)

        def _browse_sound():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                initialdir=PATH_TO_SOUNDS,
                filetypes=[("Audio", "*.wav *.opus *.ogg *.mp3 *.m4a"), ("Alle Dateien", "*.*")],
                parent=win,
            )
            if path:
                try:
                    rel = os.path.relpath(path, PATH_TO_DATA).replace('\\', '/')
                except ValueError:
                    rel = path
                sound_file_entry.delete(0, END)
                sound_file_entry.insert(0, rel)

        Button(pomodoro_frame, text="...", command=_browse_sound, width=2,
               bg='#D4D0C8', fg='black', font=('MS Sans Serif', 8),
               relief='raised', borderwidth=1, pady=0).grid(row=3, column=4, padx=(2, 0), pady=2)

        def _preview_sound():
            """Play first 7 seconds of the selected sound file."""
            path = self._resolve_sound_path(sound_file_entry.get().strip())
            if not path or not os.path.isfile(path):
                messagebox.showwarning("Sound", f"Datei nicht gefunden:\n{path}", parent=win)
                return

            def _worker():
                try:
                    is_wav = path.lower().endswith(".wav")
                    if sys.platform.startswith("win"):
                        if is_wav:
                            if winsound is None:
                                raise RuntimeError("winsound module not available")
                            winsound.PlaySound(path, winsound.SND_FILENAME)
                            return
                        exe = which("ffplay") or which("mpv")
                        if exe:
                            cmd = ([exe, "-nodisp", "-autoexit", "-t", "7", path]
                                   if "ffplay" in exe
                                   else [exe, "--no-video", "--end=7", path])
                            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return
                    elif sys.platform == "darwin" and which("afplay"):
                        subprocess.Popen(["afplay", "-t", "7", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
                    else:
                        for cmd_name in ("paplay", "ffplay", "mpv", "play", "aplay"):
                            exe = which(cmd_name)
                            if not exe:
                                continue
                            if cmd_name == "aplay" and not is_wav:
                                continue
                            if cmd_name == "ffplay":
                                subprocess.Popen([exe, "-nodisp", "-autoexit", "-t", "7", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            elif cmd_name == "mpv":
                                subprocess.Popen([exe, "--no-video", "--end=7", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            else:
                                subprocess.Popen([exe, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return
                    self.master.after(0, self.master.bell)
                except Exception as e:
                    logger.warning("Sound preview failed: %s", e)

            threading.Thread(target=_worker, daemon=True).start()

        Button(pomodoro_frame, text="\u25B6", command=_preview_sound, width=2,
               bg='#D4D0C8', fg='black', font=('MS Sans Serif', 8),
               relief='raised', borderwidth=1, pady=0).grid(row=3, column=5, padx=(2, 0), pady=2)

        pomodoro_frame.grid_columnconfigure(3, weight=1)

        # ── Entwickler ──
        dev_frame = LabelFrame(win, text="Entwickler", bg='#C0C0C0', fg='black',
                               font=('MS Sans Serif', 10, 'bold'), padx=8, pady=8)
        dev_frame.pack(fill='both', expand=True, padx=10, pady=5)

        log_text = Text(dev_frame, wrap='word', state='disabled', height=8,
                        bg='black', fg='#00ff00', font=('Courier', 9))
        log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = Scrollbar(dev_frame, orient='vertical', command=log_text.yview,
                               bg='#C0C0C0', width=14)
        log_scroll.grid(row=0, column=1, sticky="ns")
        log_text['yscrollcommand'] = log_scroll.set
        dev_frame.grid_rowconfigure(0, weight=1)
        dev_frame.grid_columnconfigure(0, weight=1)

        log_path = os.path.join(PATH_TO_DATA, "wotiti.log")

        def _load_log():
            log_text.configure(state='normal')
            log_text.delete('1.0', END)
            if os.path.isfile(log_path):
                try:
                    with open(log_path, encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    log_text.insert(END, content if content else "(Logdatei ist leer)")
                except Exception as e:
                    log_text.insert(END, f"Fehler beim Lesen: {e}")
            else:
                log_text.insert(END, "(Keine Logdatei vorhanden)")
            log_text.configure(state='disabled')
            log_text.see(END)

        log_btn_frame = Frame(dev_frame, bg='#C0C0C0')
        log_btn_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(4, 0))

        def _clear_log():
            if os.path.isfile(log_path):
                with open(log_path, 'w', encoding='utf-8'):
                    pass
            _load_log()

        Button(log_btn_frame, text="Aktualisieren", command=_load_log, **btn).pack(side='left')
        Button(log_btn_frame, text="Log löschen", command=_clear_log, **btn).pack(side='left', padx=(8, 0))
        Button(log_btn_frame, text="Copy", command=lambda: self._copy_text_widget(log_text),
               **btn).pack(side='left', padx=(8, 0))

        _load_log()

        # ── Speichern / Abbrechen ──
        action_frame = Frame(win, bg='#C0C0C0')
        action_frame.pack(fill='x', padx=10, pady=(10, 10))

        def _save():
            new_db = db_var.get().strip()
            new_port = port_var.get().strip()
            if not new_port.isdigit() or not (1024 <= int(new_port) <= 65535):
                messagebox.showwarning("Ungültiger Port", "Port muss zwischen 1024 und 65535 liegen.", parent=win)
                return

            numeric_fields = [
                (pomodoro_work_var.get().strip(), "Arbeitszeit"),
                (pomodoro_break_var.get().strip(), "Kurze Pause"),
                (pomodoro_long_break_var.get().strip(), "Lange Pause"),
                (pomodoro_every_var.get().strip(), "Lange Pause alle N"),
            ]
            for value, label in numeric_fields:
                if not value.isdigit() or int(value) <= 0:
                    messagebox.showwarning("Ungültiger Wert", f"{label} muss eine positive Zahl sein.", parent=win)
                    return

            raw_sound_path = sound_file_entry.get().strip() or "sounds/StartupSound.wav"
            sound_path = raw_sound_path.replace('\\', '/')
            if os.path.isabs(sound_path):
                try:
                    sound_path = os.path.relpath(sound_path, PATH_TO_DATA).replace('\\', '/')
                except ValueError:
                    messagebox.showwarning(
                        "Ungültiger Sound-Pfad",
                        "Bitte einen relativen Pfad unterhalb von data/ verwenden (z. B. sounds/StartupSound.wav).",
                        parent=win,
                    )
                    return

            new_config = {
                **self.config,
                "database_path": new_db if new_db else self._db_path,
                "default_user": default_user_var.get().strip() or "Hans",
                "default_project": default_proj_var.get().strip() or "1",
                "dashboard_port": int(new_port),
                "theme": theme_var.get(),
                "pomodoro_enabled": bool(pomodoro_enabled_var.get()),
                "pomodoro_work_minutes": int(pomodoro_work_var.get().strip()),
                "pomodoro_break_minutes": int(pomodoro_break_var.get().strip()),
                "pomodoro_long_break_minutes": int(pomodoro_long_break_var.get().strip()),
                "pomodoro_long_break_every": int(pomodoro_every_var.get().strip()),
                "pomodoro_auto_break": bool(pomodoro_auto_var.get()),
                "pomodoro_sound_enabled": bool(pomodoro_sound_enabled_var.get()),
                "pomodoro_sound_local_path": sound_path,
            }
            save_config(new_config)
            logger.info("Einstellungen gespeichert: theme=%s, port=%s, db=%s",
                        new_config["theme"], new_config["dashboard_port"],
                        new_config["database_path"])
            self.config = new_config
            self.pomodoro_enabled = bool(new_config.get("pomodoro_enabled", False))
            self.pomodoro_work_minutes = int(new_config.get("pomodoro_work_minutes", 25))
            self.pomodoro_break_minutes = int(new_config.get("pomodoro_break_minutes", 5))
            self.pomodoro_long_break_minutes = int(new_config.get("pomodoro_long_break_minutes", 15))
            self.pomodoro_long_break_every = int(new_config.get("pomodoro_long_break_every", 4))
            self.pomodoro_auto_break = bool(new_config.get("pomodoro_auto_break", True))
            self.pomodoro_sound_enabled = bool(new_config.get("pomodoro_sound_enabled", True))
            self.pomodoro_sound_local_path = str(new_config.get("pomodoro_sound_local_path", "sounds/StartupSound.wav")).strip()
            self._preload_sound()

            # Switch database if changed
            old_path = self._db_path
            if new_config["database_path"] != old_path:
                try:
                    if self.db_conn:
                        self.db_conn.close()
                    self._db_path = new_config["database_path"]
                    self.db_conn = create_connection(self._db_path)
                    if self.db_conn:
                        create_main_table(self.db_conn)
                        create_events_table(self.db_conn)
                        create_break_events_table(self.db_conn)
                        migrate_legacy_user_tables(self.db_conn)
                        migrate_projects_to_table(self.db_conn)
                    self.write(f"Datenbank gewechselt: {self._db_path}")
                    logger.info("Datenbank gewechselt: %s → %s", old_path, self._db_path)
                except Exception as e:
                    logger.error("Fehler beim DB-Wechsel: %s", e)
                    self.write(f"Fehler beim DB-Wechsel: {e}", error=True)

            self._combobox_dirty = True
            self._refresh_comboboxes(force=True)
            self.name_entry.set(new_config["default_user"])
            self.project_entry.set(new_config["default_project"])
            self.update_db_content()

            if int(new_port) != self._stats_port:
                self.write(f"Port-Änderung ({self._stats_port} → {new_port}) wird beim nächsten App-Start wirksam.")

            win.destroy()

        Button(action_frame, text="Speichern", command=_save, **btn).pack(side='left', padx=(0, 10))
        Button(action_frame, text="Abbrechen", command=win.destroy, **btn).pack(side='left')
    # ----- Session management -----
    def _set_button_state_idle(self):
        """Set buttons to idle state: Start enabled, Pause+Stop disabled."""
        self.start_button.config(state="normal", bg='#D4D0C8', text="\u25B6 Start")
        self.pause_button.config(state="disabled", bg='#A9A9A9', text="\u25AE\u25AE Pause")
        self.stop_button.config(state="disabled", bg='#A9A9A9')
        self._mini_start_btn.config(state="normal", bg='#D4D0C8', text="\u25B6")
        self._mini_pause_btn.config(state="disabled", bg='#A9A9A9', text="\u25AE\u25AE")
        self._mini_stop_btn.config(state="disabled", bg='#A9A9A9')
        self._mini_project_combo.config(state='readonly')
        self.project_entry.config(state='normal')

    def _set_button_state_running(self):
        """Set buttons to running state: Start disabled, Pause+Stop enabled."""
        self.start_button.config(state="disabled", bg='#A9A9A9', text="\u25B6 Start")
        self.pause_button.config(state="normal", bg='#D4D0C8', text="\u25AE\u25AE Pause")
        self.stop_button.config(state="normal", bg='#D4D0C8')
        self._mini_start_btn.config(state="disabled", bg='#A9A9A9', text="\u25B6")
        self._mini_pause_btn.config(state="normal", bg='#D4D0C8', text="\u25AE\u25AE")
        self._mini_stop_btn.config(state="normal", bg='#D4D0C8')
        self._mini_project_combo.config(state='disabled')
        self.project_entry.config(state='disabled')

    def _set_button_state_break(self):
        """Set buttons to break state: Start='Resume', Pause disabled, Stop enabled."""
        self.start_button.config(state="normal", bg='#D4D0C8', text="\u25B6 Weiter")
        self.pause_button.config(state="disabled", bg='#A9A9A9', text="\u25AE\u25AE Pause")
        self.stop_button.config(state="normal", bg='#D4D0C8')
        self._mini_start_btn.config(state="normal", bg='#D4D0C8', text="\u25B6")
        self._mini_pause_btn.config(state="disabled", bg='#A9A9A9', text="\u25AE\u25AE")
        self._mini_stop_btn.config(state="normal", bg='#D4D0C8')
        self._mini_project_combo.config(state='disabled')
        self.project_entry.config(state='disabled')

    def start_session(self):
        if self.db_conn:
            if self._break_active:
                # Start button acts as Resume during a break — always resume.
                self._finish_break(play_sound=True, bring_to_front=True, force_resume=True)
                return
            project = self.get_project()
            name = self.get_name()
            date = self.get_date()
            if project is not None and name and date:
                if self.session_active.get((name, project), False):
                    self.write("Session bereits gestartet. Bitte zuerst stoppen.", error=True)
                else:
                    logger.info("Session gestartet: user=%s, project=%s, date=%s", name, project, date)
                    log_start(project=project, name=name, date=date, conn=self.db_conn)
                    self.session_active[(name, project)] = True
                    self.timer_running = True
                    self.timer_start_time = time.time()
                    self._session_started_ts = time.time()
                    self._pomodoro_cycles = 0
                    if self.pomodoro_enabled and self._pomodoro_work_deadline_ts <= 0:
                        self._pomodoro_work_deadline_ts = time.time() + (self.pomodoro_work_minutes * 60)
                    self._combobox_dirty = True
                    self._refresh_comboboxes()
                    self.update_db_content()
                    self._set_button_state_running()

    def stop_session(self):
        """End the session completely. If a break is active, close it first without auto-resume."""
        if self._break_active:
            self._finish_break(play_sound=False, bring_to_front=False, auto_resume=False)

        if not self.db_conn:
            return
        project = self.get_project()
        name = self.get_name()
        date = self.get_date()
        if project is not None and name:
            if not self.session_active.get((name, project), False):
                # Session may already be closed (e.g. manual break closed it).
                self._set_button_state_idle()
                return
            logger.info("Session gestoppt: user=%s, project=%s", name, project)
            log_stop(project=project, name=name, date=date, conn=self.db_conn)
            self.session_active[(name, project)] = False
            self.timer_running = False
            self._session_started_ts = 0.0
            self._pomodoro_work_deadline_ts = 0.0
            self._paused_pomodoro_remaining_seconds = 0
            self._pomodoro_cycles = 0
            self.update_db_content()
            self._set_button_state_idle()

    def pause_session(self):
        """Start a manual break. Does not resume — use Start for that."""
        if self._break_active:
            return

        if not self.timer_running:
            self.write("Keine laufende Session für Pause vorhanden.", error=True)
            return
        self._start_break(
            break_kind="manual",
            break_minutes=0,
            is_auto=False,
            source_label="custom_break",
            timed_break=False,
        )

    def _start_break(
        self,
        break_kind: str,
        break_minutes: int,
        is_auto: bool,
        source_label: str,
        timed_break: bool = True,
    ):
        """Start a break phase and persist it in break_events."""
        if self._break_active or not self.db_conn:
            logger.debug("_start_break aborted: break_active=%s, db=%s",
                         self._break_active, bool(self.db_conn))
            return

        project = self._get_project_silent()
        name = self._get_name_silent()
        date = self.get_date()
        if not project or not name or not date:
            logger.warning("_start_break aborted: project=%s, name=%s, date=%s",
                           project, name, date)
            return

        # Close stale breaks that may linger from a crashed session.
        stale = get_open_break(project=project, name=name, conn=self.db_conn)
        if stale is not None:
            logger.info("Closing stale open break #%s before starting new break.", stale["id"])
            log_break_stop(project=project, name=name, conn=self.db_conn)

        if self.session_active.get((name, project), False):
            if source_label == "custom_break":
                # Manual break: stop the session so pause time is NOT work time.
                log_stop(project=project, name=name, date=date, conn=self.db_conn)
                self.session_active[(name, project)] = False
                self._session_started_ts = 0.0
            # For pomodoro_break: session stays open in DB (break = work time).
            self.timer_running = False

        self._break_active = True
        self._current_break_kind = break_kind
        self._current_break_source = source_label
        self._break_started_ts = time.time()
        self._break_end_ts = self._break_started_ts + max(1, int(break_minutes) * 60) if timed_break else 0.0
        self._last_break_project = project
        self._last_break_user = name

        if self.pomodoro_enabled and break_kind == "manual":
            remaining = max(1, int(self._pomodoro_work_deadline_ts - time.time())) if self._pomodoro_work_deadline_ts else max(1, self.pomodoro_work_minutes * 60)
            self._paused_pomodoro_remaining_seconds = remaining
            self._pomodoro_work_deadline_ts = 0.0

        log_break_start(
            project=project,
            name=name,
            break_kind=break_kind,
            is_auto=is_auto,
            source=source_label,
            pomodoro_cycle=self._pomodoro_cycles if self.pomodoro_enabled else None,
            work_interval_minutes=self.pomodoro_work_minutes if self.pomodoro_enabled else None,
            conn=self.db_conn,
        )

        self._set_button_state_break()

        self._play_pause_sound()
        self._bring_main_window_to_front()
        if timed_break:
            self.write(f"Pause gestartet ({break_minutes} min).")
        else:
            self.write("Manuelle Pause gestartet.")

    def _finish_break(self, play_sound: bool = True, bring_to_front: bool = True,
                       auto_resume: bool = True, force_resume: bool = False):
        """Finish an active break. Resume if auto_resume or force_resume."""
        if not self._break_active or not self.db_conn:
            return

        project = self._last_break_project or self._get_project_silent()
        name = self._last_break_user or self._get_name_silent()
        date = self.get_date() or datetime.today().strftime('%d-%m-%Y')
        if not project or not name:
            return

        log_break_stop(project=project, name=name, conn=self.db_conn)
        ended_kind = self._current_break_kind
        self._break_active = False
        self._break_end_ts = 0.0
        self._break_started_ts = 0.0
        self.break_time_label.config(text="--:--")
        self._mini_break_label.config(text="")

        if play_sound:
            self._play_pause_sound()
        if bring_to_front:
            self._bring_main_window_to_front()

        # Decide whether to resume the work session.
        ended_source = self._current_break_source
        self._current_break_source = ""
        should_resume = force_resume or (
            auto_resume and (
                ended_kind == "manual"
                or (self.pomodoro_auto_break and self.pomodoro_enabled)
            )
        )

        if should_resume:
            if ended_source == "custom_break":
                # Manual break: session was stopped, so re-open it.
                log_start(project=project, name=name, date=date, conn=self.db_conn)
                self.session_active[(name, project)] = True
                self._session_started_ts = time.time()
            # For pomodoro_break: session was never stopped, no DB write needed.
            self.timer_running = True
            self.timer_start_time = time.time()
            if ended_kind == "manual" and self._paused_pomodoro_remaining_seconds > 0:
                self._pomodoro_work_deadline_ts = time.time() + self._paused_pomodoro_remaining_seconds
            else:
                self._pomodoro_work_deadline_ts = time.time() + (self.pomodoro_work_minutes * 60)
            self._paused_pomodoro_remaining_seconds = 0
            self._set_button_state_running()
            self.write("Pause beendet. Session fortgesetzt.")
        else:
            # Not resuming. If session is still active (pomodoro break didn't
            # stop it), close it now to avoid a stuck state.
            if self.session_active.get((name, project), False):
                log_stop(project=project, name=name, date=date, conn=self.db_conn)
                self.session_active[(name, project)] = False
                self.timer_running = False
                self._session_started_ts = 0.0
                self._pomodoro_work_deadline_ts = 0.0
                self._paused_pomodoro_remaining_seconds = 0
            self._set_button_state_idle()
            self.write("Pause beendet.")

        self.update_db_content()

    def _bring_main_window_to_front(self):
        """Bring the visible window to front when break starts/ends."""
        try:
            if self._mini_mode:
                self._mini_toplevel.lift()
                self._mini_toplevel.focus_force()
            else:
                self.master.deiconify()
                self.master.lift()
                self.master.attributes('-topmost', True)
                self.master.after(250, lambda: self.master.attributes('-topmost', False))
                self.master.focus_force()
        except Exception as e:
            logger.warning("Window focus failed: %s", e)

    def _preload_sound(self):
        """Cache sound path and player executable for instant playback."""
        path = self._resolve_sound_path(self.pomodoro_sound_local_path)
        if not path or not os.path.isfile(path):
            logger.warning("Configured sound file not found: %s", path)
            # Fallback to packaged default sound for standalone builds.
            fallback_path = self._resolve_sound_path("sounds/StartupSound.wav")
            if fallback_path and os.path.isfile(fallback_path):
                path = fallback_path
                logger.info("Using fallback sound file: %s", fallback_path)
            else:
                logger.warning("Fallback sound file not found: %s", fallback_path)
                self._cached_sound_path = ""
                self._cached_sound_player = ""
                return

        self._cached_sound_path = path

        if sys.platform.startswith("win"):
            if path.lower().endswith(".wav") and winsound is not None:
                self._cached_sound_player = "winsound"
            else:
                self._cached_sound_player = which("ffplay") or which("mpv") or ""
        elif sys.platform == "darwin":
            self._cached_sound_player = which("afplay") or ""
        else:
            for name in ("paplay", "ffplay", "mpv", "play", "aplay"):
                exe = which(name)
                if exe:
                    if name == "aplay" and not path.lower().endswith(".wav"):
                        continue
                    self._cached_sound_player = exe
                    return
            self._cached_sound_player = ""

    def _play_pause_sound(self):
        """Play pause sound asynchronously using cached player."""
        if not self.pomodoro_sound_enabled:
            return

        sound_path = self._cached_sound_path
        player = self._cached_sound_player
        if not sound_path or not os.path.isfile(sound_path):
            self._preload_sound()
            sound_path = self._cached_sound_path
            player = self._cached_sound_player
        if not sound_path:
            logger.warning("Sound playback skipped: no valid sound file available")
            return

        def _worker():
            try:
                if sys.platform.startswith("win"):
                    if player == "winsound":
                        if winsound is None:
                            raise RuntimeError("winsound module not available")
                        winsound.PlaySound(sound_path, winsound.SND_FILENAME)
                        return
                    if player:
                        cmd = ([player, "-nodisp", "-autoexit", sound_path]
                               if "ffplay" in player
                               else [player, "--no-video", sound_path])
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
                elif sys.platform == "darwin" and player:
                    subprocess.Popen([player, sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                elif player:
                    player_name = os.path.basename(player)
                    if player_name == "ffplay":
                        subprocess.Popen([player, "-nodisp", "-autoexit", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif player_name == "mpv":
                        subprocess.Popen([player, "--no-video", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen([player, sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                self.master.after(0, self.master.bell)
            except Exception as e:
                logger.warning("Sound playback failed: %s", e)

        threading.Thread(target=_worker, daemon=True).start()

    def _resolve_sound_path(self, configured_path: str) -> str:
        """Resolve relative sound paths against data directory for source and EXE mode."""
        candidate = (configured_path or "sounds/StartupSound.wav").strip().replace('\\', '/')
        if os.path.isabs(candidate):
            return candidate
        return os.path.join(PATH_TO_DATA, candidate)

    def update_duration(self):
        if self.db_conn:
            project = self.get_project()
            name = self.get_name()
            if project is not None and name:
                duration = calculate_duration(project=project, name=name, conn=self.db_conn)
                logger.info("Dauer aktualisiert: user=%s, project=%s, %.0f s", name, project, duration)
                self.update_timer(duration)
            else:
                self.write("Ungültige Dauer. Bitte erneut versuchen.", error=True)
                return None

    # ----- Input getters with validation -----
    def _active_project_combo(self):
        """Return the currently visible project combobox."""
        return self._mini_project_combo if self._mini_mode else self.project_entry

    def get_project(self):
        val = self._active_project_combo().get().strip()
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
        # Validate format DD-MM-YYYY and semantic correctness
        try:
            datetime.strptime(val, '%d-%m-%Y')
        except ValueError:
            self.write(f"Ungültiges Datum: '{val}'. Erwartet: DD-MM-YYYY", error=True)
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

    def _copy_text_widget(self, text_widget):
        """Copies the full content of a Text widget to the system clipboard."""
        content = text_widget.get("1.0", END).strip()
        self.master.clipboard_clear()
        self.master.clipboard_append(content)

    def _copy_console(self):
        """Copies the main console content to the clipboard."""
        self._copy_text_widget(self.console)

    def _fallback_write(self, message, error=False):
        """Writes to real stdout/stderr when GUI is unavailable."""
        stream = sys.__stderr__ if error else sys.__stdout__
        if stream is not None:
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
        self._event_ids = []
        if self.db_conn:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
            if cursor.fetchone() is None:
                return

            # Filter by currently selected user, show only today
            today_str = datetime.today().strftime('%d-%m-%Y')
            current_name = self.name_entry.get().strip()
            if current_name:
                cursor.execute("""
                    SELECT e.id, u.name, e.project, e.event_type, e.timestamp
                    FROM events e
                    JOIN users u ON u.id = e.user_id
                    WHERE u.name = ? AND e.date = ?
                    ORDER BY e.timestamp
                    LIMIT 500
                """, (current_name, today_str))
            else:
                cursor.execute("""
                    SELECT e.id, u.name, e.project, e.event_type, e.timestamp
                    FROM events e
                    JOIN users u ON u.id = e.user_id
                    WHERE e.date = ?
                    ORDER BY u.name, e.timestamp
                    LIMIT 500
                """, (today_str,))
            events = cursor.fetchall()
            current_user = None
            for event_id, user_name, project, event_type, timestamp in events:
                if user_name != current_user:
                    current_user = user_name
                    self.db_content_listbox.insert(END, f"User: {user_name}")
                    self._event_ids.append(None)
                self.db_content_listbox.insert(END, f"  Projekt {project}: {event_type} at {timestamp}")
                self._event_ids.append(event_id)

    def _edit_event(self, event=None):
        """Open edit dialog for the selected event (double-click handler)."""
        sel = self.db_content_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._event_ids):
            return
        event_id = self._event_ids[idx]
        if event_id is None:
            return  # Header row

        ev = get_event_by_id(self.db_conn, event_id)
        if ev is None:
            self.write("Eintrag nicht gefunden.", error=True)
            return

        win = Toplevel(self.master)
        win.title("Eintrag bearbeiten")
        win.configure(bg='#C0C0C0')
        w, h = 420, 220
        x = self.master.winfo_x() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.transient(self.master)
        win.wait_visibility()
        win.grab_set()

        lbl_cfg = {'bg': '#C0C0C0', 'fg': 'black', 'font': ('MS Sans Serif', 10)}
        entry_cfg = {'font': ('MS Sans Serif', 10), 'bg': '#FFFFFF', 'fg': 'black',
                     'relief': 'sunken', 'borderwidth': 2}

        # Row 0: Event type (read-only)
        Label(win, text="Typ:", **lbl_cfg).grid(row=0, column=0, padx=8, pady=4, sticky='w')
        Label(win, text=ev["event_type"].upper(), bg='#C0C0C0', fg='black',
              font=('MS Sans Serif', 10, 'bold')).grid(row=0, column=1, padx=8, pady=4, sticky='w')

        # Row 1: Project
        Label(win, text="Projekt:", **lbl_cfg).grid(row=1, column=0, padx=8, pady=4, sticky='w')
        proj_combo = Combobox(win, font=('MS Sans Serif', 10), width=28)
        proj_combo['values'] = self.project_entry['values']
        proj_combo.set(ev["project"])
        proj_combo.grid(row=1, column=1, padx=8, pady=4, sticky='ew')

        # Row 2: Date
        Label(win, text="Datum (TT-MM-JJJJ):", **lbl_cfg).grid(row=2, column=0, padx=8, pady=4, sticky='w')
        date_entry = Entry(win, **entry_cfg, width=30)
        date_entry.insert(0, ev["date"])
        date_entry.grid(row=2, column=1, padx=8, pady=4, sticky='ew')

        # Row 3: Timestamp
        Label(win, text="Zeitstempel:", **lbl_cfg).grid(row=3, column=0, padx=8, pady=4, sticky='w')
        ts_entry = Entry(win, **entry_cfg, width=30)
        ts_entry.insert(0, ev["timestamp"])
        ts_entry.grid(row=3, column=1, padx=8, pady=4, sticky='ew')

        win.grid_columnconfigure(1, weight=1)

        # Buttons
        btn_cfg = {'bg': '#D4D0C8', 'fg': 'black', 'font': ('MS Sans Serif', 10),
                   'relief': 'raised', 'borderwidth': 2}
        btn_frame = Frame(win, bg='#C0C0C0')
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

        def _save():
            new_project = proj_combo.get().strip()
            new_date = date_entry.get().strip()
            new_ts = ts_entry.get().strip()
            if not new_project:
                messagebox.showwarning("Fehler", "Projekt darf nicht leer sein.", parent=win)
                return
            if not new_date:
                messagebox.showwarning("Fehler", "Datum darf nicht leer sein.", parent=win)
                return
            try:
                datetime.strptime(new_date, '%d-%m-%Y')
            except ValueError:
                messagebox.showwarning("Fehler", f"Ungültiges Datum: '{new_date}'.\nErwartet: TT-MM-JJJJ", parent=win)
                return
            try:
                datetime.strptime(new_ts, TIMESTAMP_FORMAT)
            except ValueError:
                messagebox.showwarning("Fehler", f"Ungültiger Zeitstempel: '{new_ts}'.\nErwartet: JJJJ-MM-TT HH:MM:SS", parent=win)
                return
            if update_event(self.db_conn, event_id, new_project, new_ts, new_date):
                logger.info("Event %s bearbeitet.", event_id)
                self.write(f"Eintrag {event_id} aktualisiert.")
                self._combobox_dirty = True
                self._refresh_comboboxes()
                self.update_db_content()
                win.destroy()
            else:
                messagebox.showerror("Fehler", "Eintrag konnte nicht gespeichert werden.", parent=win)

        def _delete():
            if not messagebox.askyesno("Eintrag löschen",
                                       f"Eintrag #{event_id} wirklich löschen?\n\n"
                                       f"Typ: {ev['event_type'].upper()}\n"
                                       f"Projekt: {ev['project']}\n"
                                       f"Zeitstempel: {ev['timestamp']}",
                                       parent=win):
                return
            if delete_event(self.db_conn, event_id):
                logger.info("Event %s gelöscht.", event_id)
                self.write(f"Eintrag {event_id} gelöscht.")
                self._combobox_dirty = True
                self._refresh_comboboxes()
                self.update_db_content()
                win.destroy()
            else:
                messagebox.showerror("Fehler", "Eintrag konnte nicht gelöscht werden.", parent=win)

        Button(btn_frame, text="Speichern", command=_save, **btn_cfg).pack(side='left', padx=5)
        Button(btn_frame, text="Löschen", command=_delete, bg='#D4D0C8', fg='red',
               font=('MS Sans Serif', 10), relief='raised', borderwidth=2).pack(side='left', padx=5)
        Button(btn_frame, text="Abbrechen", command=win.destroy, **btn_cfg).pack(side='left', padx=5)

    def update_timer_realtime(self):
        """Update the timer label with the elapsed time."""
        project = self._get_project_silent()
        name = self._get_name_silent()

        if self._break_active:
            if self._current_break_kind == "manual":
                elapsed = max(0, int(time.time() - self._break_started_ts))
                bmin, bsec = divmod(elapsed, 60)
                break_text = f"{bmin:02}:{bsec:02}"
            else:
                remaining = max(0, int(self._break_end_ts - time.time()))
                bmin, bsec = divmod(remaining, 60)
                break_text = f"{bmin:02}:{bsec:02}"
                if remaining == 0:
                    self._finish_break(play_sound=True, bring_to_front=True)
            self.break_time_label.config(text=break_text)
            self._mini_break_label.config(text=break_text)
        else:
            self.break_time_label.config(text="--:--")
            self._mini_break_label.config(text="")

        if project is not None and name and self.session_active.get((name, project)):
            duration = calculate_duration(project=project, name=name, conn=self.db_conn) if self.db_conn else 0
            if self.timer_running:
                start_ts = self.timer_start_time or time.time()
                elapsed_time = time.time() - start_ts + duration
            else:
                elapsed_time = duration
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            time_text = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            self.timer_time_label.config(text=time_text)
            self.timer_name_label.config(text=f"[{name}]")
            self.timer_project_label.config(text=f"Projekt: {project}")
            # Sync to mini mode timer
            self._mini_timer_label.config(text=time_text)

            if self.pomodoro_enabled and not self._break_active and self.timer_running:
                if self._pomodoro_work_deadline_ts <= 0:
                    self._pomodoro_work_deadline_ts = time.time() + (self.pomodoro_work_minutes * 60)
                if time.time() >= self._pomodoro_work_deadline_ts:
                    self._pomodoro_cycles += 1
                    long_break_due = (self._pomodoro_cycles % max(1, self.pomodoro_long_break_every)) == 0
                    break_minutes = self.pomodoro_long_break_minutes if long_break_due else self.pomodoro_break_minutes
                    break_kind = "long" if long_break_due else "short"
                    self._pomodoro_work_deadline_ts = 0.0
                    self._start_break(
                        break_kind=break_kind,
                        break_minutes=break_minutes,
                        is_auto=True,
                        source_label="pomodoro_break",
                        timed_break=True,
                    )
        if not self._closing:
            self.master.after(1000, self.update_timer_realtime)

    def update_timer(self, duration):
        """Update the timer label with the elapsed time."""
        project = self._get_project_silent()
        name = self._get_name_silent()

        if project is not None and name:
            if self.timer_running:
                start_ts = self.timer_start_time or time.time()
                elapsed_time = time.time() - start_ts + duration
            else:
                elapsed_time = duration
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)
            time_text = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            self.timer_time_label.config(text=time_text)
            self.timer_name_label.config(text=f"[{name}]")
            self.timer_project_label.config(text=f"Projekt: {project}")
            self._mini_timer_label.config(text=time_text)
        else:
            self.write("Ungültiges Projekt oder Name.", error=True)

    def _get_project_silent(self):
        """Get project without validation errors (for timer updates)."""
        val = self._active_project_combo().get().strip()
        return val if val else None

    def _get_name_silent(self):
        """Get name without validation errors (for timer updates)."""
        val = self.name_entry.get().strip()
        return val if val else None

    def open_stats_dashboard(self):
        """Opens the statistics dashboard."""
        if not self._stats_port or not self._is_dashboard_running():
            self.write("Dashboard läuft noch nicht.", error=True)
            return

        try:
            url = f"http://127.0.0.1:{self._stats_port}/"
            logger.info("Dashboard geöffnet: %s", url)
            webbrowser.open(url)
        except Exception as e:
            self.write(f"Dashboard konnte nicht geöffnet werden: {e}", error=True)

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
        if not self._closing:
            self.master.after(2000, self.update_stats_button_state)
