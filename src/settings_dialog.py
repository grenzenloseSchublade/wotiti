"""Einstellungs-Dialog: Datenbank, Benutzer/Projekt, Auswertung, Pomodoro & Co.

Aus ``app.py`` extrahiert; hält eine Back-Referenz auf die App für Config,
DB-Verbindung, Widgets und die geteilten Helfer (``_activate_database``,
``_save_config_safe``, ``_refresh_comboboxes``, …), die auch außerhalb des
Dialogs gebraucht werden und deshalb auf der App bleiben. Der komplette
Aufbau passiert im Konstruktor; der Dialog ist modal (``grab_set``) und
schreibt erst bei »Speichern« in die Config.
"""

import contextlib
import glob
import logging
import os
import subprocess
import sys
import threading
from shutil import which
from tkinter import (
    END,
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    LabelFrame,
    Listbox,
    Spinbox,
    StringVar,
    Toplevel,
    messagebox,
)
from tkinter.ttk import Combobox

if sys.platform.startswith("win"):
    import winsound
else:
    winsound = None

from db_helper import (
    create_break_events_table,
    create_connection,
    create_events_table,
    create_main_table,
    get_all_projects,
    get_all_users,
    get_archivable_overview,
    set_archived,
)
from ui_widgets import _ToolTip
from utils import PATH_TO_DATA, PATH_TO_SOUNDS, POMODORO_INT_RANGES

logger = logging.getLogger(__name__)


class SettingsDialog:
    """Baut und zeigt das Einstellungsfenster (modal, zentriert über der App)."""

    def __init__(self, app):
        self.app = app
        # Phase 2.1: Settings sind jederzeit öffenbar; nur DB-Sektion wird
        # bei laufender Session ausgegraut, weil ein DB-Wechsel mitten in
        # einer Session den State korrumpieren würde.
        sessions_active = any(self.app.session_active.values())

        win = Toplevel(self.app.master)
        win.title("Einstellungen")
        win.configure(bg="#C0C0C0")
        # Unsichtbar aufbauen, erst fertig zentriert zeigen (kein Aufblitzen
        # oben links) — siehe App._show_modal.
        win.withdraw()
        win.transient(self.app.master)
        # Geometrie wird am Ende aus dem tatsächlichen Inhalt berechnet
        # (winfo_reqheight), damit das Fenster auf Windows wie Linux trotz
        # unterschiedlicher Font-Metriken genau passt und die unteren Buttons
        # nie abgeschnitten werden.

        lbl = {"bg": "#C0C0C0", "fg": "black", "font": ("MS Sans Serif", 10)}
        btn = {"bg": "#D4D0C8", "fg": "black", "font": ("MS Sans Serif", 10), "relief": "raised", "borderwidth": 2}

        # ── Datenbank ──
        # Reihenfolge der Sektionen wird am Ende über _pack_settings_sections()
        # festgelegt (task-basiert statt nach Code-Historie). Daher hier KEIN
        # .pack() bei der Erstellung — nur Frame + Inhalt aufbauen.
        db_frame = LabelFrame(
            win, text="Datenbank", bg="#C0C0C0", fg="black", font=("MS Sans Serif", 10, "bold"), padx=8, pady=8
        )

        Label(db_frame, text="Aktive Datenbank:", **lbl).grid(row=0, column=0, sticky="w", pady=2)
        db_var = Combobox(db_frame, font=("MS Sans Serif", 10), width=35)
        db_var.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        def _refresh_db_list():
            dbs = sorted(glob.glob(os.path.join(PATH_TO_DATA, "**", "*.db"), recursive=True))
            # Die aktive DB immer anbieten und anzeigen — auch wenn sie (über
            # »Durchsuchen…«) außerhalb des Datenordners liegt. Sonst zeigte
            # die Combobox nach »Laden« einen falschen Pfad (ersten Treffer).
            if self.app._db_path and self.app._db_path not in dbs:
                dbs.insert(0, self.app._db_path)
            db_var["values"] = dbs
            if self.app._db_path in dbs:
                db_var.set(self.app._db_path)
            elif dbs:
                db_var.set(dbs[0])

        _refresh_db_list()

        btn_row = Frame(db_frame, bg="#C0C0C0")
        btn_row.grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky="ew")

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
                        self.app.write(f"Neue Datenbank erstellt: {path}")
                except Exception as e:
                    messagebox.showerror("Fehler", f"Datenbank konnte nicht erstellt werden:\n{e}", parent=win)

        def _delete_db():
            target = db_var.get().strip()
            if not target or not os.path.isfile(target):
                messagebox.showwarning("Keine Auswahl", "Bitte eine vorhandene Datenbank auswählen.", parent=win)
                return
            if os.path.abspath(target) == os.path.abspath(self.app._db_path):
                messagebox.showwarning(
                    "Nicht möglich",
                    "Die aktive Datenbank kann nicht gelöscht werden.\nBitte zuerst eine andere Datenbank auswählen.",
                    parent=win,
                )
                return
            if messagebox.askyesno(
                "Datenbank löschen",
                f"Datenbank wirklich löschen?\n\n{target}\n\nDieser Vorgang kann nicht rückgängig gemacht werden!",
                parent=win,
            ):
                try:
                    os.remove(target)
                    _refresh_db_list()
                    logger.info("Datenbank gelöscht: %s", target)
                    self.app.write(f"Datenbank gelöscht: {target}")
                except OSError as e:
                    messagebox.showerror("Fehler", f"Löschen fehlgeschlagen:\n{e}", parent=win)

        def _after_db_load():
            # »Laden« lässt den Dialog offen (ungespeicherte Felder bleiben
            # stehen) — nur die DB-abhängige Anzeige wird nachgezogen: die
            # DB-Liste (Combobox springt auf die jetzt aktive DB) und die
            # Vorschlagslisten für Standard-Benutzer/-Projekt aus der neuen DB.
            _refresh_db_list()
            if self.app.db_conn:
                default_user_var["values"] = get_all_users(self.app.db_conn)
                default_proj_var["values"] = get_all_projects(self.app.db_conn)

        Button(
            btn_row,
            text="Laden",
            command=lambda: self.app._activate_database(db_var.get(), win, on_success=_after_db_load),
            **{k: v for k, v in btn.items() if k != "fg"},
            fg="#006400",
        ).pack(side="left", padx=(0, 5))
        Button(btn_row, text="Durchsuchen...", command=_browse_db, **btn).pack(side="left", padx=(0, 5))
        Button(btn_row, text="Neue DB", command=_new_db, **btn).pack(side="left", padx=(0, 5))
        Button(
            btn_row, text="DB löschen", command=_delete_db, fg="#B00020", **{k: v for k, v in btn.items() if k != "fg"}
        ).pack(side="left")

        # Dezenter Hinweis: diese Buttons wirken sofort, nicht erst beim
        # »Speichern« des Dialogs (Bestands-Stil: klein/grau).
        Label(
            db_frame,
            text="Laden, Neue DB und DB löschen wirken sofort — unabhängig von »Speichern«.",
            bg="#C0C0C0",
            fg="#666666",
            font=("MS Sans Serif", 8),
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(3, 0))

        db_frame.grid_columnconfigure(1, weight=1)

        # Phase 2.1: DB-Sektion sperren, solange eine Session läuft.
        if sessions_active:
            db_var.config(state="disabled")
            for child in btn_row.winfo_children():
                with contextlib.suppress(Exception):
                    child.config(state="disabled")
            Label(
                db_frame,
                text="Bitte alle laufenden Sessions stoppen, um den DB-Pfad zu ändern.",
                bg="#C0C0C0",
                fg="#B00020",
                font=("MS Sans Serif", 9, "italic"),
                wraplength=480,
                justify="left",
            ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # ── Benutzer ──
        user_frame = LabelFrame(
            win, text="Benutzer & Projekt", bg="#C0C0C0", fg="black", font=("MS Sans Serif", 10, "bold"), padx=8, pady=8
        )

        Label(user_frame, text="Standard-Benutzer:", **lbl).grid(row=0, column=0, sticky="w", pady=2)
        default_user_var = Combobox(user_frame, font=("MS Sans Serif", 10), width=20)
        default_user_var.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        if self.app.db_conn:
            default_user_var["values"] = get_all_users(self.app.db_conn)
        default_user_var.set(self.app.config.get("default_user", "Hans"))

        Label(user_frame, text="Standard-Projekt:", **lbl).grid(row=1, column=0, sticky="w", pady=2)
        default_proj_var = Combobox(user_frame, font=("MS Sans Serif", 10), width=20)
        default_proj_var.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        if self.app.db_conn:
            default_proj_var["values"] = get_all_projects(self.app.db_conn)
        default_proj_var.set(self.app.config.get("default_project", "1"))

        user_frame.grid_columnconfigure(1, weight=1)

        # ── Dashboard ──
        dash_frame = LabelFrame(
            win,
            text="Auswertung",
            bg="#C0C0C0",
            fg="black",
            font=("MS Sans Serif", 10, "bold"),
            padx=8,
            pady=8,
        )

        Label(dash_frame, text="Port:", **lbl).grid(row=0, column=0, sticky="w", pady=2)
        port_var = Spinbox(
            dash_frame, from_=1024, to=65535, width=8, font=("MS Sans Serif", 10), bg="#FFFFFF", fg="black"
        )
        port_var.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        port_var.delete(0, END)
        port_var.insert(0, str(self.app.config.get("dashboard_port", 8052)))

        Label(dash_frame, text="Theme:", **lbl).grid(row=1, column=0, sticky="w", pady=2)
        theme_var = Combobox(
            dash_frame, font=("MS Sans Serif", 10), width=15, values=["Modern", "Synthwave"], state="readonly"
        )
        theme_var.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        theme_var.set(self.app.config.get("theme", "Modern"))

        # Feiertage (wirken in den Auswertungen).
        Label(dash_frame, text="Feiertagsland (ISO):", **lbl).grid(row=2, column=0, sticky="w", pady=2)
        holiday_country_var = StringVar(value=str(self.app.config.get("holiday_country", "DE") or ""))
        Entry(
            dash_frame, textvariable=holiday_country_var, font=("MS Sans Serif", 10), width=10, bg="#FFFFFF", fg="black"
        ).grid(row=2, column=1, padx=5, pady=2, sticky="w")
        Label(dash_frame, text="Region (optional):", **lbl).grid(row=3, column=0, sticky="w", pady=2)
        holiday_subdiv_var = StringVar(value=str(self.app.config.get("holiday_subdiv", "") or ""))
        Entry(
            dash_frame, textvariable=holiday_subdiv_var, font=("MS Sans Serif", 10), width=10, bg="#FFFFFF", fg="black"
        ).grid(row=3, column=1, padx=5, pady=2, sticky="w")

        # Statistik-Optionen: wirken auf die Durchschnitts-/Trend-Auswertungen.
        # Bisher nur per Hand-Edit der config.json erreichbar (cfg-4) — jetzt im
        # Dialog, da sie konzeptuell zur Auswertung gehören (passend zu den
        # Feiertagsfeldern darüber).
        exclude_weekends_var = BooleanVar(value=bool(self.app.config.get("exclude_weekends_in_averages", True)))
        include_holidays_var = BooleanVar(value=bool(self.app.config.get("include_holidays_in_exclusion", True)))
        count_weekend_work_var = BooleanVar(value=bool(self.app.config.get("count_weekend_work", False)))
        for _row, (_text, _var) in enumerate(
            (
                ("Wochenenden aus Durchschnitten ausschließen", exclude_weekends_var),
                ("Feiertage ebenfalls ausschließen", include_holidays_var),
                ("Wochenend-Arbeit in Auswertungen zählen", count_weekend_work_var),
            ),
            start=4,
        ):
            Checkbutton(
                dash_frame,
                text=_text,
                variable=_var,
                bg="#C0C0C0",
                fg="black",
                selectcolor="#C0C0C0",
                activebackground="#C0C0C0",
                font=("MS Sans Serif", 10),
            ).grid(row=_row, column=0, columnspan=2, sticky="w", pady=2)

        # ── Pomodoro ──
        pomodoro_frame = LabelFrame(
            win, text="Pomodoro & Pausen", bg="#C0C0C0", fg="black", font=("MS Sans Serif", 10, "bold"), padx=8, pady=8
        )

        pomodoro_enabled_var = BooleanVar(value=self.app.pomodoro_enabled)
        pomodoro_auto_var = BooleanVar(value=self.app.pomodoro_auto_break)
        pomodoro_sound_enabled_var = BooleanVar(value=self.app.pomodoro_sound_enabled)

        Checkbutton(
            pomodoro_frame,
            text="Pomodoro aktiv",
            variable=pomodoro_enabled_var,
            bg="#C0C0C0",
            fg="black",
            selectcolor="#C0C0C0",
            activebackground="#C0C0C0",
            font=("MS Sans Serif", 10),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        # Spinbox-Grenzen aus der Single Source of Truth (POMODORO_INT_RANGES),
        # damit UI, Save-Check und Loader denselben Bereich verwenden.
        _work_lo, _work_hi, _ = POMODORO_INT_RANGES["pomodoro_work_minutes"]
        _break_lo, _break_hi, _ = POMODORO_INT_RANGES["pomodoro_break_minutes"]
        _long_lo, _long_hi, _ = POMODORO_INT_RANGES["pomodoro_long_break_minutes"]
        _every_lo, _every_hi, _ = POMODORO_INT_RANGES["pomodoro_long_break_every"]

        Label(pomodoro_frame, text="Arbeitszeit (min):", **lbl).grid(row=1, column=0, sticky="w", pady=2)
        pomodoro_work_var = Spinbox(
            pomodoro_frame, from_=_work_lo, to=_work_hi, width=8, font=("MS Sans Serif", 10), bg="#FFFFFF", fg="black"
        )
        pomodoro_work_var.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        pomodoro_work_var.delete(0, END)
        pomodoro_work_var.insert(0, str(self.app.pomodoro_work_minutes))

        Label(pomodoro_frame, text="Kurze Pause (min):", **lbl).grid(row=2, column=0, sticky="w", pady=2)
        pomodoro_break_var = Spinbox(
            pomodoro_frame, from_=_break_lo, to=_break_hi, width=8, font=("MS Sans Serif", 10), bg="#FFFFFF", fg="black"
        )
        pomodoro_break_var.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        pomodoro_break_var.delete(0, END)
        pomodoro_break_var.insert(0, str(self.app.pomodoro_break_minutes))

        Label(pomodoro_frame, text="Lange Pause (min):", **lbl).grid(row=3, column=0, sticky="w", pady=2)
        pomodoro_long_break_var = Spinbox(
            pomodoro_frame, from_=_long_lo, to=_long_hi, width=8, font=("MS Sans Serif", 10), bg="#FFFFFF", fg="black"
        )
        pomodoro_long_break_var.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        pomodoro_long_break_var.delete(0, END)
        pomodoro_long_break_var.insert(0, str(self.app.pomodoro_long_break_minutes))

        Label(pomodoro_frame, text="Lange Pause alle N:", **lbl).grid(row=4, column=0, sticky="w", pady=2)
        pomodoro_every_var = Spinbox(
            pomodoro_frame, from_=_every_lo, to=_every_hi, width=8, font=("MS Sans Serif", 10), bg="#FFFFFF", fg="black"
        )
        pomodoro_every_var.grid(row=4, column=1, padx=5, pady=2, sticky="w")
        pomodoro_every_var.delete(0, END)
        pomodoro_every_var.insert(0, str(self.app.pomodoro_long_break_every))

        # Hinweis: "Auto-Stop bei Idle" wurde in die Sektion "Zeiterfassung &
        # Anzeige" verschoben (SO-3) — es ist von der Pomodoro-Technik
        # unabhängig und wirkt auch bei deaktiviertem Pomodoro.

        # POM-04: Diese Checkbox steuert NICHT den Pausenstart (der erfolgt bei
        # aktivem Pomodoro immer), sondern ob die Session NACH der Pause
        # automatisch fortgesetzt wird (_finish_break). Label entsprechend
        # benannt, damit es das tatsächliche Verhalten beschreibt.
        _auto_resume_cb = Checkbutton(
            pomodoro_frame,
            text="Nach Pause automatisch fortsetzen",
            variable=pomodoro_auto_var,
            bg="#C0C0C0",
            fg="black",
            selectcolor="#C0C0C0",
            activebackground="#C0C0C0",
            font=("MS Sans Serif", 10),
        )
        _auto_resume_cb.grid(row=0, column=2, columnspan=2, sticky="w", pady=2)
        _ToolTip(_auto_resume_cb, "Session nach Ablauf einer Pomodoro-Pause automatisch weiterlaufen lassen")

        Checkbutton(
            pomodoro_frame,
            text="Sound aktiv",
            variable=pomodoro_sound_enabled_var,
            bg="#C0C0C0",
            fg="black",
            selectcolor="#C0C0C0",
            activebackground="#C0C0C0",
            font=("MS Sans Serif", 10),
        ).grid(row=1, column=2, columnspan=2, sticky="w", pady=2)

        Label(pomodoro_frame, text="Sound Datei:", **lbl).grid(row=3, column=2, sticky="w", pady=2)
        sound_file_entry = Entry(pomodoro_frame, bg="#FFFFFF", fg="black", font=("MS Sans Serif", 10), width=28)
        sound_file_entry.grid(row=3, column=3, padx=5, pady=2, sticky="ew")
        sound_file_entry.insert(0, self.app.pomodoro_sound_local_path)

        def _browse_sound():
            from tkinter import filedialog

            path = filedialog.askopenfilename(
                initialdir=PATH_TO_SOUNDS,
                filetypes=[("Audio", "*.wav *.opus *.ogg *.mp3 *.m4a"), ("Alle Dateien", "*.*")],
                parent=win,
            )
            if path:
                try:
                    rel = os.path.relpath(path, PATH_TO_DATA).replace("\\", "/")
                except ValueError:
                    rel = path
                sound_file_entry.delete(0, END)
                sound_file_entry.insert(0, rel)

        Button(
            pomodoro_frame,
            text="...",
            command=_browse_sound,
            width=2,
            bg="#D4D0C8",
            fg="black",
            font=("MS Sans Serif", 8),
            relief="raised",
            borderwidth=1,
            pady=0,
        ).grid(row=3, column=4, padx=(2, 0), pady=2)

        def _preview_sound():
            """Play first 7 seconds of the selected sound file."""
            path = self.app._resolve_sound_path(sound_file_entry.get().strip())
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
                            cmd = (
                                [exe, "-nodisp", "-autoexit", "-t", "7", path]
                                if "ffplay" in exe
                                else [exe, "--no-video", "--end=7", path]
                            )
                            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return
                    elif sys.platform == "darwin" and which("afplay"):
                        subprocess.Popen(
                            ["afplay", "-t", "7", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                        return
                    else:
                        for cmd_name in ("paplay", "ffplay", "mpv", "play", "aplay"):
                            exe = which(cmd_name)
                            if not exe:
                                continue
                            if cmd_name == "aplay" and not is_wav:
                                continue
                            if cmd_name == "ffplay":
                                subprocess.Popen(
                                    [exe, "-nodisp", "-autoexit", "-t", "7", path],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                            elif cmd_name == "mpv":
                                subprocess.Popen(
                                    [exe, "--no-video", "--end=7", path],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                            else:
                                subprocess.Popen([exe, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return
                    self.app.master.after(0, self.app.master.bell)
                except Exception as e:
                    logger.warning("Sound preview failed: %s", e)

            threading.Thread(target=_worker, daemon=True).start()

        Button(
            pomodoro_frame,
            text="\u25b6",
            command=_preview_sound,
            width=2,
            bg="#D4D0C8",
            fg="black",
            font=("MS Sans Serif", 8),
            relief="raised",
            borderwidth=1,
            pady=0,
        ).grid(row=3, column=5, padx=(2, 0), pady=2)

        pomodoro_frame.grid_columnconfigure(3, weight=1)

        # ── Zeiterfassung & Anzeige ──
        # Bündelt verhaltensbezogene Optionen, die unabhängig von Pomodoro und
        # vom Dashboard sind: Auto-Stop bei Inaktivität (SO-3) und die
        # Darstellung der Start/Stop-Liste (SO-4).
        time_frame = LabelFrame(
            win,
            text="Zeiterfassung & Anzeige",
            bg="#C0C0C0",
            fg="black",
            font=("MS Sans Serif", 10, "bold"),
            padx=8,
            pady=8,
        )

        Label(time_frame, text="Auto-Stop bei Idle (min, 0=aus):", **lbl).grid(row=0, column=0, sticky="w", pady=2)
        idle_timeout_var = Spinbox(
            time_frame, from_=0, to=1440, width=8, font=("MS Sans Serif", 10), bg="#FFFFFF", fg="black"
        )
        idle_timeout_var.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        idle_timeout_var.delete(0, END)
        idle_timeout_var.insert(0, str(self.app.idle_timeout_minutes))

        # Start/Stop-Liste: Gruppierung nach Projekt (Default) vs. chronologisch.
        entry_chrono_var = BooleanVar(value=bool(self.app.config.get("entry_list_chronological", False)))
        chrono_check = Checkbutton(
            time_frame,
            text="Einträge chronologisch statt nach Projekt gruppieren",
            variable=entry_chrono_var,
            bg="#C0C0C0",
            fg="black",
            selectcolor="#C0C0C0",
            activebackground="#C0C0C0",
            font=("MS Sans Serif", 10),
        )
        chrono_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        # Bei laufender Session sperren: die Umstellung der Session-Darstellung
        # soll nicht mitten in einer Session erfolgen (sonst wirkt sie verworfen).
        if sessions_active:
            chrono_check.config(state="disabled", fg="#888888", disabledforeground="#888888")
            Label(
                time_frame,
                text="Während einer laufenden Session nicht änderbar — bitte zuerst stoppen.",
                bg="#C0C0C0",
                fg="#B00020",
                font=("MS Sans Serif", 9, "italic"),
                wraplength=480,
                justify="left",
            ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 2))

        # Anzeigehöhe des Notizfelds (rein visuell, Inhalt bleibt einzeilig).
        Label(time_frame, text="Notizfeld-Höhe (Zeilen):", **lbl).grid(row=3, column=0, sticky="w", pady=2)
        note_lines_var = Spinbox(
            time_frame, from_=1, to=6, width=8, font=("MS Sans Serif", 10), bg="#FFFFFF", fg="black"
        )
        note_lines_var.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        note_lines_var.delete(0, END)
        note_lines_var.insert(0, str(int(self.app.config.get("note_field_lines", 2))))
        time_frame.grid_columnconfigure(1, weight=1)

        # ── Verwaltung (Benutzer/Projekte archivieren) ──
        # Ersetzt das frühere Benutzerverwaltungs-Fenster: Hinzufügen passiert
        # weiterhin schlank über die Comboboxen im Hauptfenster; hier kann man
        # Einträge aus den Auswahl-Listen AUSBLENDEN (archivieren) und wieder
        # einblenden. Daten (Events, Notizen, Statistik) bleiben unangetastet.
        mgmt_frame = LabelFrame(
            win, text="Verwaltung", bg="#C0C0C0", fg="black", font=("MS Sans Serif", 10, "bold"), padx=8, pady=8
        )
        show_archived_var = BooleanVar(value=False)
        mgmt_lists: dict[str, Listbox] = {}
        mgmt_rows: dict[str, list[tuple[str, bool, int]]] = {"users": [], "projects": []}

        def _refresh_mgmt():
            overview = get_archivable_overview(self.app.db_conn)
            for kind in ("users", "projects"):
                listbox = mgmt_lists[kind]
                listbox.delete(0, END)
                rows = [r for r in overview[kind] if show_archived_var.get() or not r[1]]
                mgmt_rows[kind] = rows
                for entry_name, entry_archived, n_events in rows:
                    suffix = "  [ausgeblendet]" if entry_archived else ""
                    listbox.insert(END, f"{entry_name}  ({n_events} Einträge){suffix}")

        def _toggle_archived(kind: str):
            listbox = mgmt_lists[kind]
            sel = listbox.curselection()
            if not sel:
                return
            entry_name, entry_archived, _n = mgmt_rows[kind][sel[0]]
            if not entry_archived:
                # Guards: aktive Auswahl, Default-Benutzer bzw. laufende
                # Session nicht ausblenden (Default würde beim nächsten Start
                # sonst still reaktiviert bzw. auf einen anderen ausweichen).
                if kind == "users" and entry_name == self.app.name_entry.get().strip():
                    messagebox.showinfo(
                        "Nicht möglich", "Der aktuell ausgewählte Benutzer kann nicht ausgeblendet werden.", parent=win
                    )
                    return
                if kind == "users" and entry_name == (self.app.config.get("default_user") or "").strip():
                    messagebox.showinfo(
                        "Nicht möglich",
                        "Dieser Benutzer ist als Standard-Benutzer eingetragen — zuerst oben ändern.",
                        parent=win,
                    )
                    return
                if kind == "projects" and entry_name == self.app._get_project_silent():
                    messagebox.showinfo(
                        "Nicht möglich", "Das aktuell ausgewählte Projekt kann nicht ausgeblendet werden.", parent=win
                    )
                    return
                in_session = any(
                    running
                    and ((kind == "users" and s_name == entry_name) or (kind == "projects" and s_proj == entry_name))
                    for (s_name, s_proj), running in self.app.session_active.items()
                )
                if in_session:
                    messagebox.showinfo(
                        "Nicht möglich",
                        "Eintrag hat eine laufende Session und kann nicht ausgeblendet werden.",
                        parent=win,
                    )
                    return
            set_archived(self.app.db_conn, "user" if kind == "users" else "project", entry_name, not entry_archived)
            self.app._combobox_dirty = True
            self.app._refresh_comboboxes(force=True)
            _refresh_mgmt()

        for col, (kind, title) in enumerate((("users", "Benutzer"), ("projects", "Projekte"))):
            Label(mgmt_frame, text=f"{title}:", **lbl).grid(row=0, column=col, sticky="w", padx=(0, 8))
            listbox = Listbox(mgmt_frame, bg="#FFFFFF", fg="black", font=("MS Sans Serif", 9), height=4, width=28)
            listbox.grid(row=1, column=col, sticky="nsew", padx=(0, 8), pady=2)
            mgmt_lists[kind] = listbox
            Button(mgmt_frame, text="Aus-/Einblenden", command=lambda k=kind: _toggle_archived(k), **btn).grid(
                row=2, column=col, sticky="w", padx=(0, 8), pady=(2, 0)
            )
        Checkbutton(
            mgmt_frame,
            text="Ausgeblendete anzeigen",
            variable=show_archived_var,
            command=_refresh_mgmt,
            bg="#C0C0C0",
            fg="black",
            font=("MS Sans Serif", 9),
            activebackground="#C0C0C0",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        # Dezenter Hinweis: Archivieren wirkt sofort, nicht erst beim »Speichern«.
        Label(
            mgmt_frame,
            text="Aus-/Einblenden wirkt sofort — unabhängig von »Speichern«.",
            bg="#C0C0C0",
            fg="#666666",
            font=("MS Sans Serif", 8),
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))
        mgmt_frame.grid_columnconfigure(0, weight=1)
        mgmt_frame.grid_columnconfigure(1, weight=1)
        _refresh_mgmt()

        # ── Entwickler ──
        # Bewusst nur eine Zeile: Pfad + Öffnen (der frühere eingebettete
        # Log-Viewer machte den Dialog fast bildschirmhoch). Für Live-Meldungen
        # gibt es die Konsole im Hauptfenster.
        dev_frame = LabelFrame(
            win, text="Entwickler", bg="#C0C0C0", fg="black", font=("MS Sans Serif", 10, "bold"), padx=8, pady=8
        )
        log_path = os.path.join(PATH_TO_DATA, "wotiti.log")
        Label(dev_frame, text=f"Logdatei: {log_path}", **lbl).grid(row=0, column=0, sticky="w")

        def _open_log():
            try:
                if sys.platform.startswith("win"):
                    os.startfile(log_path)  # noqa: S606
                else:
                    subprocess.Popen(["xdg-open", log_path])
            except Exception as e:  # noqa: BLE001
                messagebox.showwarning("Log öffnen", f"Logdatei konnte nicht geöffnet werden: {e}", parent=win)

        Button(dev_frame, text="Log öffnen", command=_open_log, **btn).grid(row=0, column=1, sticky="e", padx=(8, 0))
        dev_frame.grid_columnconfigure(0, weight=1)

        # ── Speichern / Abbrechen ──
        # VOR den Sektionen packen: pack beschneidet bei zu kleinem Fenster die
        # zuletzt gepackten Widgets zuerst — nur so bleibt die Buttonleiste am
        # unteren Rand (side="bottom") immer sichtbar.
        action_frame = Frame(win, bg="#C0C0C0")
        action_frame.pack(side="bottom", fill="x", padx=10, pady=(10, 10))

        # ── Sektionen in task-basierter Reihenfolge packen (SO-9) ──
        # Top-to-bottom nach Änderungshäufigkeit: häufig angepasste Optionen
        # oben, einmalig/gesperrtes (Datenbank, Verwaltung) sowie die
        # Log-Zeile (Entwickler) unten.
        sections = [user_frame, pomodoro_frame, time_frame, dash_frame, db_frame, mgmt_frame, dev_frame]
        for i, section in enumerate(sections):
            section.pack(fill="x", padx=10, pady=(10, 5) if i == 0 else 5)

        def _save():
            # Lazy-Import: app.py importiert dieses Modul auf Modulebene —
            # ein Modul-Import von app hier wäre zirkulär (gleiches Muster
            # wie die filedialog-Importe in den Nachbar-Closures).
            from app import NEW_PROJECT_LABEL

            new_db = db_var.get().strip()
            new_port = port_var.get().strip()
            # Phase 2.1: Bei laufender Session/Pause DB-Pfad-Wechsel hart ablehnen.
            # LIVE prüfen, nicht das beim Öffnen eingefrorene sessions_active:
            # Session oder Pause kann gestartet worden sein, während der Dialog
            # offen war.
            tracking_live = any(self.app.session_active.values()) or self.app._break_active
            db_would_change = bool(new_db) and os.path.abspath(new_db) != os.path.abspath(self.app._db_path)
            if tracking_live and db_would_change:
                messagebox.showwarning(
                    "Session aktiv",
                    "DB-Pfad kann nicht gewechselt werden, solange eine Session oder Pause läuft.",
                    parent=win,
                )
                return
            if not new_port.isdigit() or not (1024 <= int(new_port) <= 65535):
                messagebox.showwarning("Ungültiger Port", "Port muss zwischen 1024 und 65535 liegen.", parent=win)
                return

            # Range-Validierung gegen die Single Source of Truth (POMODORO_INT_RANGES),
            # damit getippte Werte nicht gespeichert und beim nächsten Start still
            # auf den Default zurückgesetzt werden (POM-03).
            numeric_fields = [
                (pomodoro_work_var.get().strip(), "Arbeitszeit", "pomodoro_work_minutes"),
                (pomodoro_break_var.get().strip(), "Kurze Pause", "pomodoro_break_minutes"),
                (pomodoro_long_break_var.get().strip(), "Lange Pause", "pomodoro_long_break_minutes"),
                (pomodoro_every_var.get().strip(), "Lange Pause alle N", "pomodoro_long_break_every"),
            ]
            for value, label, cfg_key in numeric_fields:
                lo, hi, _ = POMODORO_INT_RANGES[cfg_key]
                if not value.isdigit() or not (lo <= int(value) <= hi):
                    messagebox.showwarning(
                        "Ungültiger Wert", f"{label} muss zwischen {lo} und {hi} liegen.", parent=win
                    )
                    return

            idle_timeout_raw = idle_timeout_var.get().strip()
            if not idle_timeout_raw.isdigit():
                messagebox.showwarning("Ungültiger Wert", "Idle-Timeout muss eine Zahl ≥ 0 sein (0 = aus).", parent=win)
                return

            note_lines_raw = note_lines_var.get().strip()
            if not note_lines_raw.isdigit() or not (1 <= int(note_lines_raw) <= 6):
                messagebox.showwarning(
                    "Ungültiger Wert", "Notizfeld-Höhe muss zwischen 1 und 6 Zeilen liegen.", parent=win
                )
                return

            raw_sound_path = sound_file_entry.get().strip() or "sounds/StartupSound.wav"
            sound_path = raw_sound_path.replace("\\", "/")
            if os.path.isabs(sound_path):
                try:
                    sound_path = os.path.relpath(sound_path, PATH_TO_DATA).replace("\\", "/")
                except ValueError:
                    messagebox.showwarning(
                        "Ungültiger Sound-Pfad",
                        "Bitte einen relativen Pfad unterhalb von data/ verwenden (z. B. sounds/StartupSound.wav).",
                        parent=win,
                    )
                    return

            new_config = {
                **self.app.config,
                "database_path": new_db if new_db else self.app._db_path,
                "default_user": default_user_var.get().strip() or "Hans",
                "default_project": (dp if (dp := default_proj_var.get().strip()) and dp != NEW_PROJECT_LABEL else "1"),
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
                "idle_timeout_minutes": int(idle_timeout_raw),
                "note_field_lines": int(note_lines_raw),
                "holiday_country": holiday_country_var.get().strip() or "DE",
                "holiday_subdiv": holiday_subdiv_var.get().strip(),
                "entry_list_chronological": bool(entry_chrono_var.get()),
                "exclude_weekends_in_averages": bool(exclude_weekends_var.get()),
                "include_holidays_in_exclusion": bool(include_holidays_var.get()),
                "count_weekend_work": bool(count_weekend_work_var.get()),
            }
            if self.app._save_config_safe(new_config):
                logger.info(
                    "Einstellungen gespeichert: theme=%s, port=%s, db=%s",
                    new_config["theme"],
                    new_config["dashboard_port"],
                    new_config["database_path"],
                )
            self.app.config = new_config
            was_pomodoro_enabled = self.app.pomodoro_enabled
            self.app.pomodoro_enabled = bool(new_config.get("pomodoro_enabled", False))
            self.app.pomodoro_work_minutes = int(new_config.get("pomodoro_work_minutes", 25))
            self.app.pomodoro_break_minutes = int(new_config.get("pomodoro_break_minutes", 5))
            self.app.pomodoro_long_break_minutes = int(new_config.get("pomodoro_long_break_minutes", 15))
            self.app.pomodoro_long_break_every = int(new_config.get("pomodoro_long_break_every", 4))
            self.app.pomodoro_auto_break = bool(new_config.get("pomodoro_auto_break", True))
            self.app.pomodoro_sound_enabled = bool(new_config.get("pomodoro_sound_enabled", True))
            self.app.pomodoro_sound_local_path = str(
                new_config.get("pomodoro_sound_local_path", "sounds/StartupSound.wav")
            ).strip()
            self.app.idle_timeout_minutes = int(new_config.get("idle_timeout_minutes", 120))
            self.app.note_entry.configure(height=int(new_config.get("note_field_lines", 2)))
            self.app._preload_sound()

            self.app._reconcile_pomodoro_runtime(was_pomodoro_enabled)

            # Switch database if changed — Pfadvergleich per abspath wie beim
            # Live-Session-Guard oben: eine andere SCHREIBWEISE desselben
            # Pfads (./-Präfix, ..-Segment) passiert sonst den Guard, würde
            # hier aber als „geändert" gelten und _open_database (inklusive
            # close_stale_sessions!) auf die laufende Session loslassen.
            old_path = self.app._db_path
            db_changed = os.path.abspath(new_config["database_path"]) != os.path.abspath(old_path)
            if db_changed and self.app._open_database(new_config["database_path"]):
                self.app.write(f"Datenbank gewechselt: {self.app._db_path}")
                logger.info("Datenbank gewechselt: %s → %s", old_path, self.app._db_path)

            self.app._combobox_dirty = True
            self.app._refresh_comboboxes(force=True)
            # Auswahl NUR ohne laufende Session/Pause umstellen: Pause/Stop
            # arbeiten über die Comboboxen — ein stilles Umschalten auf die
            # Defaults würde sie vom laufenden (Benutzer, Projekt)-Paar
            # wegdrehen und die Session verwaisen lassen.
            if not any(self.app.session_active.values()) and not self.app._break_active:
                self.app.name_entry.set(new_config["default_user"])
                self.app._set_project(new_config["default_project"])
            # Nach DB-Wechsel auf den jüngsten Tag mit Daten springen, damit die
            # neue Datenbank sofort sichtbar geladen ist (nicht auf einem leeren Tag).
            if db_changed:
                self.app._jump_to_latest_data_date(new_config["default_user"])
            self.app._force_date_refresh()

            if int(new_port) != self.app._stats_port:
                self.app.write(
                    f"Port-Änderung ({self.app._stats_port} → {new_port}) wird beim nächsten App-Start wirksam."
                )

            win.destroy()

        Button(action_frame, text="Speichern", command=_save, **btn).pack(side="left", padx=(0, 10))
        Button(action_frame, text="Abbrechen", command=win.destroy, **btn).pack(side="left")
        Button(action_frame, text="Über WoTITI", command=lambda: self.app._open_about(win), **btn).pack(side="right")

        # Phase 2.6: Esc = Abbrechen.
        win.bind("<Escape>", lambda _e: win.destroy())

        # Fenster an den tatsächlichen Inhalt anpassen und zentrieren. reqheight
        # spiegelt die plattformspezifischen Font-Metriken wider, sodass nichts
        # gestaucht und nichts (v.a. die Buttonleiste) abgeschnitten wird.
        win.update_idletasks()
        w = max(560, win.winfo_reqwidth())
        h = win.winfo_reqheight()
        sh = win.winfo_screenheight()
        h = min(h, sh - 80)  # nie höher als der Bildschirm
        x = self.app.master.winfo_x() + (self.app.master.winfo_width() - w) // 2
        y = max(0, self.app.master.winfo_y() + (self.app.master.winfo_height() - h) // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.minsize(w, min(h, 560))
        self.app._show_modal(win)
