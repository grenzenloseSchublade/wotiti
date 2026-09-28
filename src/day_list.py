"""Tagesliste: Text-Widget mit Projekt-Gruppen, Zeiten, Notizen und ✓-Status.

Aus ``app.py`` extrahiert; hält eine Back-Referenz auf die App für DB-Verbindung,
Config, Datums-/Benutzerauswahl und die geteilten Helfer (``_pair_day_sessions``,
``_session_times_str``, ``_edit_event``), die auch der Session-Editor braucht und
die deshalb auf der App bleiben. Die App exponiert dünne Delegates/Properties
(``day_list``, ``update_db_content``, ``_day_sessions``, …) für bestehende
Call-Sites und Tests.
"""

from datetime import datetime
from tkinter import END, VERTICAL, Menu, Scrollbar, Text

from db_helper import (
    _WINDOW_MARGIN_DAYS,
    DATE_FORMAT,
    UI_DATE_FORMAT,
    _timestamp_window,
    fetch_day_events,
    get_daily_meta,
    get_daily_meta_for_range,
    set_daily_transferred,
)
from ui_widgets import _ToolTip, resolve_project_color
from utils import fmt_hours_hm

# Wochentags-Kürzel für die Kopfzeile (deutsch, Mo=0).
_WDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class DayListView:
    """Baut und rendert die Tagesliste; hält die Klick-Mappings der Zeilen."""

    def __init__(self, app, parent):
        self.app = app

        # Tagesliste als Text-Widget: Tags liefern die visuelle Hierarchie
        # (Projekt fett + Farbbalken, Zeiten eingerückt, Notizen grau).
        # takefocus=0 ist zwingend: _shortcut_guard (App) überspringt fokussierte
        # Text-Widgets — bekäme die Liste je Fokus, schluckte sie Strg+←/→/T.
        self.widget = Text(
            parent,
            bg="#FFFFFF",
            fg="black",
            font=("MS Sans Serif", 10),
            relief="sunken",
            borderwidth=2,
            wrap="word",
            state="disabled",
            cursor="arrow",
            takefocus=0,
            # Kein Innenabstand/Fokusrahmen: die Zeilen-Hervorhebung (hover/
            # active_line) reicht so bündig von Rand zu Rand; die Einrückung
            # des Inhalts übernehmen die lmargin-Werte der Tags.
            padx=0,
            highlightthickness=0,
        )
        self.widget.grid(row=0, column=0, sticky="nsew")
        # Fokus sofort wegleiten: Tks tk::TextButton1 setzt bei Mausklick
        # BEDINGUNGSLOS den Fokus (takefocus=0 wirkt nur auf Tab-Traversal) —
        # ein fokussiertes Text-Widget würde über _shortcut_guard die globalen
        # Shortcuts Strg+←/→/T blockieren, bis man woanders hinklickt.
        self.widget.bind("<FocusIn>", lambda _e: app.master.focus_set())
        self.widget.bind("<Double-1>", app._edit_event)
        self.widget.bind("<Button-3>", self._show_row_context_menu)
        self.widget.bind("<Motion>", self._on_motion)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<Configure>", lambda _e: self._update_tabs())
        _ToolTip(self.widget, "Doppelklick: Session bearbeiten · Rechtsklick: Menü")
        # Klick-Auflösung: Zeilennummer → Session (Kopf-/Zeiten-Zeile),
        # Session-Tag → Session (präzise auf der ·-getrennten Zeiten-Zeile)
        # und flache Session-Liste des Tages für den Open-Start-Scan.
        # Projekt-Kopfzeilen (Layout A) tragen die erste Session des Projekts,
        # damit Doppel-/Rechtsklick auch dort funktioniert.
        self._line_sessions: dict[int, dict] = {}
        self._tag_sessions: dict[str, dict] = {}
        self._day_sessions: list[dict] = []
        self._tabs_ready = False
        self._init_tags()

        self.scrollbar = Scrollbar(parent, orient=VERTICAL, command=self.widget.yview, bg="#C0C0C0", width=16)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.widget["yscrollcommand"] = self.scrollbar.set

    def _init_tags(self) -> None:
        """Definiert die festen Text-Tags der Tagesliste (einmalig beim Aufbau).

        Reihenfolge ist relevant: später definierte Tags haben in Tk höhere
        Priorität — ``dur`` überschreibt so das Fett der Kopfzeile, ``dim``
        das Grau von ``note``.
        """
        tw = self.widget
        # Basis-Einzug für jede Zeile (Widget hat padx=0, s. __init__). Als
        # erster Tag definiert = niedrigste Priorität: times/note überschreiben.
        tw.tag_configure("base", lmargin1=4, lmargin2=4)
        tw.tag_configure("user", font=("MS Sans Serif", 9), foreground="#404040", spacing1=6, spacing3=2)
        tw.tag_configure("proj_head", font=("MS Sans Serif", 10, "bold"), spacing1=8)
        tw.tag_configure("dur", font=("MS Sans Serif", 10))
        tw.tag_configure("check", foreground="#008000")
        tw.tag_configure("times", lmargin1=24, lmargin2=24)
        tw.tag_configure("note", lmargin1=24, lmargin2=24, foreground="#606060")
        tw.tag_configure("dim", foreground="#808080")
        tw.tag_configure("hover", background="#ECECEC")
        tw.tag_configure("active_line", background="#D8D8D8")

    def _update_tabs(self) -> None:
        """Setzt den rechtsbündigen Tab-Stop der Kopfzeilen auf die Widgetbreite."""
        width = self.widget.winfo_width()
        if width > 1:
            self.widget.tag_configure("proj_head", tabs=(width - 24, "right"))

    def _bar_tag(self, project: str) -> str:
        """Lazy-Tag für den Projekt-Farbbalken (▌) in der Projektfarbe.

        Nutzt ``resolve_project_color`` (persistierte config-Farbe zuerst,
        Fallback Hash-Farbe) — Balken und Wochen-Segmente zeigen so dieselbe
        Farbe.
        """
        color = resolve_project_color(self.app.config, project)
        tag = f"bar_{color.lstrip('#')}"
        self.widget.tag_configure(tag, foreground=color)
        return tag

    def refresh(self) -> None:
        """Baut die Tagesliste (Text-Widget) aus der Datenbank neu auf."""
        tw = self.widget
        for t in tw.tag_names():
            if t.startswith("sess"):
                tw.tag_delete(t)
        self._line_sessions = {}
        self._tag_sessions = {}
        self._day_sessions = []
        if not self._tabs_ready:
            tw.update_idletasks()
            self._tabs_ready = True
        self._update_tabs()
        tw.configure(state="normal")
        try:
            tw.delete("1.0", END)
            self._render(tw)
        finally:
            tw.configure(state="disabled")

    def _render(self, tw) -> None:
        """Rendert den Inhalt der Tagesliste (läuft mit state='normal')."""
        app = self.app
        if app.db_conn:
            cursor = app.db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events';")
            if cursor.fetchone() is None:
                return

            # Filter by currently selected user and the date shown in the date field
            view_date = app._get_selected_date()
            suffix = "" if app._is_viewing_today() else "  (nicht heute)"
            # Kalenderwoche des angezeigten Datums — die KW braucht man beim
            # Übertragen der Zeiten ins Firmensystem ständig.
            try:
                kw = f" · KW {datetime.strptime(view_date, '%d-%m-%Y').isocalendar()[1]}"
            except (ValueError, TypeError):
                kw = ""
            app._status_date_label.config(text=f"Ansicht: {view_date}{kw}{suffix}")
            current_name = app.name_entry.get().strip()
            # Anzeige-Limit: höchstens ``limit`` Events des Anzeigetags werden
            # als Sessions gerendert (Schutz vor entarteten Datenbeständen).
            limit = 500
            # Events über das Timestamp-Fenster des Anzeigetags laden statt über
            # die date-Spalte: nur so wird eine Mitternachts-Session (23:50 →
            # 00:30) vollständig gepaart — über die date-Spalte bliebe sie am
            # Starttag ewig „laufend" und hinterließe am Folgetag einen
            # verwaisten Stop. Rand ±_WINDOW_MARGIN_DAYS wie in
            # calculate_daily_duration, damit Start UND Stop tagübergreifender
            # Sessions mitgelesen werden.
            try:
                view_day = datetime.strptime(view_date, UI_DATE_FORMAT).date()
            except ValueError:
                return
            ts_lo, ts_hi = _timestamp_window(view_day, view_day)
            # SQL-Deckel nur als Schutz vor entarteten Datenbeständen — auf die
            # Fensterbreite skaliert, damit Randtage den Anzeigetag nicht aus
            # dem Limit verdrängen.
            window_limit = limit * (2 * _WINDOW_MARGIN_DAYS + 1)
            events = fetch_day_events(app.db_conn, ts_lo, ts_hi, user=current_name or None, limit=window_limit)
            # Deckel erreicht? Dann kann ORDER BY timestamp auch späte Events
            # des ANZEIGETAGS abgeschnitten haben — das wird unten ehrlich
            # ausgewiesen statt still verschluckt.
            window_truncated = len(events) == window_limit
            view_iso = view_day.strftime(DATE_FORMAT)
            chronological = bool(app.config.get("entry_list_chronological", False))
            # Nur Sessions des Anzeigetags behalten: eine Session gehört zum Tag
            # ihres Starts (ein verwaister Stop zum Tag des Stops) — die
            # Mitternachts-Session erscheint so vollständig am Starttag.
            day_sessions_all = [
                s
                for s in (app._pair_day_sessions(events) if events else [])
                if s["sort_ts"] and s["sort_ts"].date() == view_day
            ]
            # Auf das Event-Limit des Anzeigetags kürzen (wie das frühere SQL
            # LIMIT, nur nach dem Paaren): gezählt werden je Session die Events,
            # die am Anzeigetag liegen — der Folgetag-Stop einer Mitternachts-
            # Session zählt nicht mit. Die Hinweiszeile unten speist sich aus
            # GENAU dieser Kürzung und bleibt so immer ehrlich.
            sessions = []
            shown_events = 0
            for s in day_sessions_all:
                n = sum(1 for ts in (s["start_ts"], s["stop_ts"]) if ts is not None and ts.date() == view_day)
                if shown_events + n > limit:
                    break
                shown_events += n
                sessions.append(s)
            hidden_sessions = len(day_sessions_all) - len(sessions)

            # Meta (Notiz/✓) je (user, project) cachen — wenige Abfragen/Tag.
            meta_cache: dict[tuple, dict] = {}

            def _meta(user, project):
                key = (user, project)
                if key not in meta_cache:
                    meta_cache[key] = (
                        get_daily_meta(app.db_conn, user, project, view_iso)
                        if view_iso
                        else {"note": "", "transferred": False, "transferred_at": None}
                    )
                return meta_cache[key]

            # Projekte mit Notiz/✓ aber OHNE Events an dem Tag ermitteln, damit
            # eine Hauptfenster-Notiz nie unsichtbar bleibt (z. B. Default-Projekt
            # ohne Sessions). meta_cache wird dabei direkt vorbefüllt.
            event_pairs = {(s["user"], s["project"]) for s in sessions}
            note_only: dict[str, list] = {}
            if view_iso:
                if current_name:
                    for (proj, _d), m in get_daily_meta_for_range(app.db_conn, current_name, [view_iso]).items():
                        if (m["note"] or m["transferred"]) and (current_name, proj) not in event_pairs:
                            meta_cache[(current_name, proj)] = m
                            note_only.setdefault(current_name, []).append(proj)
                else:
                    cur2 = app.db_conn.cursor()
                    cur2.execute(
                        "SELECT u.name, n.project, n.note, n.transferred, n.transferred_at "
                        "FROM daily_notes n JOIN users u ON u.id = n.user_id "
                        "WHERE n.date = ? AND (n.note != '' OR n.transferred = 1)",
                        (view_iso,),
                    )
                    for uname, proj, note, transferred, tat in cur2.fetchall():
                        if (uname, proj) not in event_pairs:
                            meta_cache[(uname, proj)] = {
                                "note": note or "",
                                "transferred": bool(transferred),
                                "transferred_at": tat,
                            }
                            note_only.setdefault(uname, []).append(proj)

            if sessions or note_only:

                def _emit(segments, session=None):
                    """Fügt eine Zeile aus (Text, Tags)-Segmenten ein + Mapping."""
                    line_no = int(tw.index("end-1c").split(".")[0])
                    for text, tags in segments:
                        tw.insert(END, text, ("base", *tags))
                    tw.insert(END, "\n")
                    if session is not None:
                        self._line_sessions[line_no] = session

                def _range_str(s):
                    start = s["start_ts"].strftime("%H:%M") if s["start_ts"] else "..."
                    stop = s["stop_ts"].strftime("%H:%M") if s["stop_ts"] else "..."
                    return f"{start}–{stop}"

                def _note_line(note):
                    if note:
                        _emit([(note, ("note",))])
                    else:
                        _emit([("(keine Notiz)", ("note", "dim"))])

                def _register(s):
                    """Session in Tag-/Tages-Mapping aufnehmen; liefert (dict, Tag)."""
                    full = {**s, "date_iso": view_iso}
                    stag = f"sess{len(self._day_sessions)}"
                    self._day_sessions.append(full)
                    self._tag_sessions[stag] = full
                    return full, stag

                # Bewusst KEINE Datums-Kopfzeile mehr: das Datum steht bereits
                # im (gelb markierten) Datumsfeld und in der Statusleiste.

                # Nutzer in Erscheinungsreihenfolge (Events zuerst, dann Notiz-only).
                users_order = []
                for s in sessions:
                    if s["user"] not in users_order:
                        users_order.append(s["user"])
                for uname in note_only:
                    if uname not in users_order:
                        users_order.append(uname)

                # Benutzer-Kopf nur, wenn die Zuordnung nicht ohnehin klar ist
                # (kein Benutzer-Filter oder mehrere Benutzer sichtbar).
                show_user_head = not current_name or len(users_order) > 1
                try:
                    d = datetime.strptime(view_date, UI_DATE_FORMAT)
                    head_date = f"{_WDAY_DE[d.weekday()]} {d.strftime('%d.%m.')}"
                except ValueError:
                    head_date = view_date

                for user in users_order:
                    if show_user_head:
                        _emit([(f"{user} — {head_date}", ("user",))])
                    user_sessions = [s for s in sessions if s["user"] == user]
                    if not chronological:
                        # Layout A: nach Projekt gruppiert.
                        projects_order = []
                        for s in user_sessions:
                            if s["project"] not in projects_order:
                                projects_order.append(s["project"])
                        for project in projects_order:
                            meta = _meta(user, project)
                            bar = self._bar_tag(project)
                            proj_sessions = [ps for ps in user_sessions if ps["project"] == project]
                            total_h = sum(ps["dur_h"] or 0.0 for ps in proj_sessions)
                            # Kopfzeile trägt die erste Session, damit Doppel-/
                            # Rechtsklick auch auf ihr den Editor bzw. das Menü öffnet.
                            head = [
                                ("▌ ", ("proj_head", bar)),
                                (project, ("proj_head",)),
                                ("\t", ("proj_head",)),
                                (fmt_hours_hm(total_h), ("dur",)),
                            ]
                            if meta["transferred"]:
                                head.append((" ✓", ("check",)))
                            _emit(head, {**proj_sessions[0], "date_iso": view_iso})
                            segs = []
                            first_full = None
                            for s in proj_sessions:
                                full, stag = _register(s)
                                first_full = first_full or full
                                if segs:
                                    segs.append((" · ", ("times",)))
                                segs.append((_range_str(s), ("times", stag)))
                            _emit(segs, first_full)
                            _note_line(meta["note"])
                    else:
                        # Layout B: chronologisch, Projekt je Zeile.
                        for s in user_sessions:
                            meta = _meta(user, s["project"])
                            full, stag = _register(s)
                            _, dur = app._session_times_str(s)
                            segs = [
                                ("▌ ", (self._bar_tag(s["project"]),)),
                                (f"{_range_str(s)}  ", (stag,)),
                                (s["project"], ()),
                                (f"  ({dur})", ("dur",)),
                            ]
                            if meta["transferred"]:
                                segs.append((" ✓", ("check",)))
                            _emit(segs, full)
                            _note_line(meta["note"])

                    # Notiz/✓-Projekte ohne Zeiten ans Ende der Nutzergruppe.
                    for project in sorted(note_only.get(user, [])):
                        meta = _meta(user, project)
                        head = [
                            ("▌ ", ("proj_head", self._bar_tag(project))),
                            (project, ("proj_head",)),
                            ("  (keine Zeiten)", ("dim",)),
                        ]
                        if meta["transferred"]:
                            head.append((" ✓", ("check",)))
                        _emit(head)
                        _note_line(meta["note"])

                # Phase 2.4: Hinweis, wenn das Listenlimit greift — der Zähler
                # kommt aus der tatsächlichen Kürzung oben, nicht aus einem
                # separaten COUNT, der davon abweichen könnte.
                if hidden_sessions:
                    word = "weitere Session" if hidden_sessions == 1 else "weitere Sessions"
                    _emit([(f"... {hidden_sessions} {word} ausgeblendet (Limit {limit} Events/Tag)", ("dim",))])
            else:
                # Empty-State: sichtbar machen, dass der Tag wirklich leer ist
                # (und nicht etwa die Liste defekt) — dezent im dim-Grau.
                tw.insert(END, "Keine Einträge für diesen Tag\n", ("base", "dim"))
            if window_truncated:
                # Der SQL-Deckel hat zugeschlagen: das ±3-Tage-Ladefenster war
                # voll, auch Sessions des Anzeigetags können fehlen.
                tw.insert(
                    END,
                    f"... Anzeige evtl. unvollständig: Ladefenster-Limit ({window_limit} Events) erreicht\n",
                    ("base", "dim"),
                )

    def _event_session(self, event) -> dict | None:
        """Session unter dem Mauszeiger; None auf Kopf-/Notiz-/Leerbereich."""
        tw = self.widget
        idx = tw.index(f"@{event.x},{event.y}")
        # index() clampt auch Klicks weit unterhalb der letzten Zeile auf
        # deren Index — nur reagieren, wenn der Klick die Zeile wirklich trifft.
        info = tw.dlineinfo(idx)
        if not info or not (info[1] <= event.y <= info[1] + info[3]):
            return None
        # Session-Tags zuerst: auf der ·-Zeitenzeile trifft der Klick so die
        # exakte Session statt nur der ersten der Zeile.
        for t in tw.tag_names(idx):
            if t in self._tag_sessions:
                return self._tag_sessions[t]
        return self._line_sessions.get(int(idx.split(".")[0]))

    @staticmethod
    def _full_line(line: int) -> tuple[str, str]:
        """Tag-Bereich einer ganzen Zeile inkl. Zeilenumbruch.

        Nur mit dem ``\\n`` füllt Tk den Tag-Hintergrund bis zum rechten
        Rand; ``line.end`` endet am letzten Zeichen — die Hervorhebung wirkte
        dann je nach Textlänge rechts unterschiedlich abgeschnitten.
        """
        return f"{line}.0", f"{line + 1}.0"

    def _on_motion(self, event) -> None:
        """Hinterlegt die Zeile unter dem Cursor (Klick-Affordanz)."""
        tw = self.widget
        tw.tag_remove("hover", "1.0", END)
        idx = tw.index(f"@{event.x},{event.y}")
        info = tw.dlineinfo(idx)
        line = int(idx.split(".")[0])
        if info and info[1] <= event.y <= info[1] + info[3] and line in self._line_sessions:
            tw.tag_add("hover", *self._full_line(line))

    def _on_leave(self, _event=None) -> None:
        self.widget.tag_remove("hover", "1.0", END)

    def _show_row_context_menu(self, event):
        """Rechtsklick auf eine Session-Zeile: Menü mit Bearbeiten + ✓-Toggle."""
        session = self._event_session(event)
        if session is None:
            return  # Kopf-/Notiz-/Limit-Zeile ohne Session
        tw = self.widget
        line = int(tw.index(f"@{event.x},{event.y}").split(".")[0])
        tw.tag_remove("active_line", "1.0", END)
        tw.tag_add("active_line", *self._full_line(line))

        menu = Menu(tw, tearoff=0)
        # Tk räumt Menü-Widgets nicht selbst ab — ohne destroy akkumuliert
        # jeder Rechtsklick ein Widget über die gesamte App-Laufzeit.
        menu.bind(
            "<Unmap>",
            lambda _e: (tw.tag_remove("active_line", "1.0", END), menu.after_idle(menu.destroy)),
        )
        menu.add_command(label="Bearbeiten…", command=lambda s=session: self.app._edit_event(session=s))
        date_iso = session.get("date_iso")
        if date_iso:
            meta = get_daily_meta(self.app.db_conn, session["user"], session["project"], date_iso)
            label = "Übertragen-Häkchen entfernen" if meta["transferred"] else "Als übertragen markieren"
            menu.add_command(
                label=label,
                command=lambda s=session, t=not meta["transferred"]: self._toggle_row_transferred(s, t),
            )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Ohne grab_release bleibt unter X11 ein Pointer-Grab hängen.
            menu.grab_release()

    def _toggle_row_transferred(self, session: dict, transferred: bool) -> None:
        """Setzt den »übertragen«-Status für die (Benutzer, Projekt, Tag)-Zeile.

        Gleiches Verhalten wie die Haupt-Checkbox (_on_transferred_toggled),
        nur mit explizitem Ziel statt der aktuellen Combobox-Auswahl.
        """
        app = self.app
        if not app.db_conn:
            return
        user, project, date_iso = session["user"], session["project"], session.get("date_iso")
        if not date_iso:
            return
        today_iso = datetime.now().date().strftime(DATE_FORMAT)
        set_daily_transferred(app.db_conn, user, project, date_iso, transferred, today_iso)
        # Falls genau dieser Eintrag gerade im Notiz-/✓-Bereich geladen ist,
        # Checkbox nachziehen (Flush zuerst, damit getippter Text nicht verloren geht).
        if app._note_loaded_key == (user, project, date_iso):
            app._flush_pending_note()
            app._load_note()
        self.refresh()
        if app._week_view_active:
            app._refresh_week_view()
