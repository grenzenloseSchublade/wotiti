"""Wochen-Kachel („Zeitmaschine"): 7-Tage-Übersicht mit projektweise gefärbten Balken.

Aus ``app.py`` extrahiert; hält eine Back-Referenz auf die App für DB-Verbindung,
Config, Formatierung und Refresh-Hooks. Die Kachel überlagert per ``place()``
den Listbox-Bereich und wird über den „Woche ›"/„‹ Timer"-Link umgeschaltet.
"""

import logging
from datetime import datetime, timedelta
from tkinter import Button, Frame, Label

from db_helper import (
    compute_last_n_days_hours,
    compute_last_n_days_hours_by_project,
    get_daily_meta_for_range,
    set_daily_transferred_bulk,
)
from ui_widgets import WEEK_PROJECT_COLORS, _ToolTip
from utils import is_holiday, save_config

logger = logging.getLogger(__name__)


class WeekView:
    """Baut und rendert die Wochen-Kachel; initial verborgen."""

    def __init__(self, app, parent: Frame):
        self.app = app
        self.active = False
        self.offset = 0  # Tages-Offset in 7er-Schritten, 0 = aktuelle Woche
        self.all_projects = True

        self.frame = Frame(parent, bg="#C0C0C0", border=2, relief="sunken", padx=5, pady=5)
        # Per place() über die Listbox gelegt: nimmt exakt 100% des
        # db_content_frame ein, ohne die Grid-Größe zu beeinflussen.
        # place()-Widgets liegen immer über grid()-Widgets (plattformsicher).
        self.frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.frame.place_forget()  # initial verborgen

        # Navigationszeile: ‹ Titel › (zentriert)
        nav_frame = Frame(self.frame, bg="#C0C0C0")
        nav_frame.grid(row=0, column=0, columnspan=7, sticky="ew", padx=4, pady=(0, 2))

        nav_inner = Frame(nav_frame, bg="#C0C0C0")
        nav_inner.pack(expand=True)

        self._btn_back = Button(
            nav_inner,
            text="‹",
            command=self.scroll_back,
            bg="#C0C0C0",
            fg="#000080",
            font=("MS Sans Serif", 10, "bold"),
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            width=4,
        )
        self._btn_back.pack(side="left")
        _ToolTip(self._btn_back, "Eine Woche zurück")

        self._title_label = Label(
            nav_inner,
            text="Zeitmaschine",
            bg="#C0C0C0",
            fg="#000080",
            font=("MS Sans Serif", 10, "bold"),
        )
        self._title_label.pack(side="left", padx=4)

        self._btn_forward = Button(
            nav_inner,
            text="›",
            command=self.scroll_forward,
            bg="#C0C0C0",
            fg="#000080",
            font=("MS Sans Serif", 10, "bold"),
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            width=4,
        )
        self._btn_forward.pack(side="left")
        self._btn_forward.configure(state="disabled")
        _ToolTip(self._btn_forward, "Eine Woche vor (bis zur aktuellen)")

        # Umschalter "Alle Projekte" / "Nur aktuelles" (rechts in der Navizeile).
        self._btn_mode = Button(
            nav_frame,
            text="Nur aktuelles",
            command=self.toggle_mode,
            bg="#C0C0C0",
            fg="#666666",
            font=("MS Sans Serif", 8),
            relief="flat",
            borderwidth=0,
            cursor="hand2",
        )
        self._btn_mode.pack(side="right")
        _ToolTip(self._btn_mode, "Zwischen allen Projekten und nur dem gewählten Projekt umschalten")

        # „✓ Woche": markiert alle sichtbaren (Projekt, Tag)-Einträge der Woche
        # als übertragen; wenn schon alles übertragen ist, wird zu „↺ Woche"
        # (zurücknehmen). Kein Bestätigungsdialog — der Toggle selbst ist das Undo.
        self._btn_transfer = Button(
            nav_frame,
            text="✓ Woche",
            command=self._on_week_transfer,
            bg="#C0C0C0",
            fg="#666666",
            font=("MS Sans Serif", 8),
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            state="disabled",
        )
        self._btn_transfer.pack(side="right", padx=(0, 8))
        _ToolTip(
            self._btn_transfer,
            "Alle Zeiten dieser Woche als »ins Firmensystem übertragen« markieren bzw. zurücksetzen",
        )
        # Sichtbare (Projekt, ISO-Tag)-Paare der aktuell gerenderten Woche +
        # deren KW; wird in refresh() gepflegt und vom Wochen-Button genutzt.
        self._week_items: list[tuple[str, str]] = []
        self._week_kw = 0

        self._day_frames: list[Frame] = []
        for col in range(7):
            self.frame.grid_columnconfigure(col, weight=1, uniform="weekday")
            cell = Frame(self.frame, bg="#C0C0C0")
            cell.grid(row=1, column=col, sticky="nsew", padx=2)
            self._day_frames.append(cell)
        self.frame.grid_rowconfigure(1, weight=1)

        # Ein wiederverwendbarer Tooltip je (persistenter) Tageszelle. Bei jedem
        # Refresh nur den Text tauschen — neue _ToolTip-Instanzen würden ihre
        # add="+"-Bindings auf den langlebigen Zellen unbegrenzt akkumulieren.
        self._cell_tips = [_ToolTip(cell, "") for cell in self._day_frames]

        # Legende für die Projekt-Farben (wird in refresh() gefüllt).
        self._legend_frame = Frame(self.frame, bg="#C0C0C0")
        self._legend_frame.grid(row=2, column=0, columnspan=7, sticky="ew", padx=4, pady=(2, 0))

    # ------------------------------------------------------------------
    # Sichtbarkeit + Navigation
    # ------------------------------------------------------------------
    def show(self) -> None:
        self.active = True
        # place() über Listbox — 100% Größe, plattformsicher.
        self.frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.refresh()

    def hide(self) -> None:
        self.active = False
        self.frame.place_forget()

    def toggle_mode(self) -> None:
        """Schaltet zwischen "alle Projekte" und "nur aktuelles Projekt" um."""
        self.all_projects = not self.all_projects
        self._btn_mode.configure(text="Nur aktuelles" if self.all_projects else "Alle Projekte")
        self.refresh()

    def scroll_back(self) -> None:
        """Scrollt die Wochenansicht 7 Tage in die Vergangenheit."""
        self.offset -= 7
        self.refresh()

    def scroll_forward(self) -> None:
        """Scrollt die Wochenansicht 7 Tage Richtung Gegenwart."""
        self.offset = min(self.offset + 7, 0)
        self.refresh()

    # ------------------------------------------------------------------
    # Übertragen-Status (Tages-Klick + Wochen-Button)
    # ------------------------------------------------------------------
    def _transfer_toggle(self, items: list[tuple[str, str]], scope_label: str) -> None:
        """Toggelt den Übertragen-Status für ``items`` = [(project, date_iso)].

        Zielzustand: sind bereits **alle** Einträge übertragen, wird
        zurückgesetzt, sonst gesetzt (selbstkorrigierend bei Mischzuständen).
        Wirkt auf genau die sichtbaren Paare — im Modus „Nur aktuelles" also
        nur auf das gewählte Projekt (»what you see is what you check«).
        """
        app = self.app
        if not app.db_conn or not items:
            return
        name = app._get_name_silent()
        if not name:
            return
        # Getippte Notiz sichern — der Toggle lädt das Notizfeld weiter unten neu.
        app._flush_pending_note()
        # Zustand frisch aus der DB lesen (nicht aus dem letzten Render).
        dates = sorted({d for _, d in items})
        meta = get_daily_meta_for_range(app.db_conn, name, dates)
        target = not all(meta.get((p, d), {}).get("transferred") for p, d in items)
        today_iso = datetime.now().date().strftime("%Y-%m-%d")
        changed = set_daily_transferred_bulk(
            app.db_conn, name, items, target, transferred_at=(today_iso if target else None)
        )
        verb = "als übertragen markiert" if target else "auf offen zurückgesetzt"
        noun = "Eintrag" if changed == 1 else "Einträge"
        app.write(f"{scope_label}: {changed} {noun} {verb}.")
        # Tagesliste + Haupt-Checkbox nachziehen (falls Datum/Projekt betroffen).
        app.update_db_content()
        app._load_note()
        self.refresh()

    def _on_day_transfer(self, iso_date: str, projects: list[str], label: str) -> None:
        self._transfer_toggle([(p, iso_date) for p in projects], label)

    def _on_week_transfer(self) -> None:
        self._transfer_toggle(list(self._week_items), f"KW {self._week_kw}")

    # ------------------------------------------------------------------
    # Projektfarben (persistiert in config['project_colors'])
    # ------------------------------------------------------------------
    def _ensure_project_colors(self, projects) -> dict[str, str]:
        """Liefert stabile, laufübergreifende Farben für alle ``projects``.

        Die Zuordnung wird in ``config['project_colors']`` persistiert. Neue
        Projekte erhalten die Palettenfarbe, die unter den bereits zugewiesenen
        am seltensten vorkommt (maximiert Unterscheidbarkeit; erst ab >10
        Projekten sind Wiederholungen unvermeidbar). ``save_config`` (mit
        fsync!) läuft höchstens **einmal** pro Aufruf und nur, wenn tatsächlich
        neue Projekte zugewiesen wurden — nicht mitten im Rendern pro Projekt.
        """
        mapping = self.app.config.get("project_colors")
        if not isinstance(mapping, dict):
            mapping = {}
            self.app.config["project_colors"] = mapping
        result: dict[str, str] = {}
        changed = False
        for name in projects:
            if not name:
                result[name] = WEEK_PROJECT_COLORS[0]
                continue
            existing = mapping.get(name)
            if existing in WEEK_PROJECT_COLORS:
                result[name] = existing
                continue
            # Seltenste Palettenfarbe wählen (stabile Reihenfolge bei Gleichstand).
            usage = {c: 0 for c in WEEK_PROJECT_COLORS}
            for c in mapping.values():
                if c in usage:
                    usage[c] += 1
            chosen = min(WEEK_PROJECT_COLORS, key=lambda c: (usage[c], WEEK_PROJECT_COLORS.index(c)))
            mapping[name] = chosen
            result[name] = chosen
            changed = True
        if changed:
            try:
                save_config(self.app.config)
            except OSError as e:  # noqa: BLE001
                logger.warning("Projektfarben konnten nicht gespeichert werden: %s", e)
        return result

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Zeichnet die Kalenderwoche (Mo–So) als gestapelte, projektweise eingefaerbte Balken.

        Standardmaessig werden **alle Projekte gleichzeitig** mit stabiler
        Projektfarbe dargestellt (Umschalter "Nur aktuelles" fuer die
        Einzelprojekt-Ansicht). Wochenende/Feiertag werden ueber die Datumsfarbe
        und den Zellhintergrund kodiert, die Balkenfarbe steht fuer das Projekt.
        """
        app = self.app
        # Vorherige Inhalte je Tag + Legende loeschen; Zell-Tooltips leeren
        # (leerer Text = kein Popup), statt neue Instanzen zu binden.
        for cell, tip in zip(self._day_frames, self._cell_tips, strict=True):
            tip.set_text("")
            for child in cell.winfo_children():
                child.destroy()
        for child in self._legend_frame.winfo_children():
            child.destroy()
        # Bis zum erfolgreichen Render gibt es nichts zu markieren.
        self._week_items = []
        self._btn_transfer.configure(state="disabled", text="✓ Woche", fg="#B0B0B0")

        if not app.db_conn:
            return
        name = app._get_name_silent()
        if not name:
            return
        project = app._get_project_silent()
        if not self.all_projects and not project:
            return
        try:
            # Kalenderwoche Mo–So statt rollierendem 7-Tage-Fenster: so decken
            # KW-Titel, „✓ Woche" und die Legendensummen genau die ISO-Woche ab
            # (konsistent mit dem KW-Report im Dashboard und dem Übertragen-
            # Workflow). end_date = Sonntag der gewählten Woche; zukünftige Tage
            # der laufenden Woche haben schlicht keine Events (0 h).
            today_date = datetime.now().date()
            monday = today_date - timedelta(days=today_date.weekday())
            end_date = monday + timedelta(days=self.offset + 6)
            if self.all_projects:
                days = compute_last_n_days_hours_by_project(app.db_conn, name, n=7, end_date=end_date)
            else:
                # Einzelprojekt in dasselbe {project: hours}-Format bringen.
                single = compute_last_n_days_hours(app.db_conn, name, project, n=7, end_date=end_date)
                days = [(iso, {project: h} if h > 0 else {}) for iso, h in single]
        except Exception as e:  # noqa: BLE001
            logger.warning("Wochenansicht konnte nicht berechnet werden: %s", e)
            return

        # Titel und Navigation aktualisieren.
        kw = end_date.isocalendar()[1]
        self._week_kw = kw
        self._title_label.config(text=f"Zeitmaschine · KW {kw}")
        if self.offset < 0:
            self._btn_forward.configure(state="normal", fg="#000080")
        else:
            self._btn_forward.configure(state="disabled", fg="#B0B0B0")

        today = datetime.now().date()
        day_totals = [sum(by_proj.values()) for _, by_proj in days]
        max_hours = max(max(day_totals, default=0.0), 1.0)
        BAR_BLOCKS_MAX = 14

        # Distinkte, laufübergreifend stabile Farbe je Projekt. Die Zuordnung
        # hängt NUR am Projektnamen (persistiert in der Config), nicht an der
        # Wochenzusammensetzung — sonst springen Farben zwischen Wochen.
        all_projects = sorted({p for _, by_proj in days for p in by_proj})
        color_map = self._ensure_project_colors(all_projects)

        # Notiz + Übertragungs-Status je Projekt/Tag für die 7 Tage (ein Batch-Query).
        meta_map = get_daily_meta_for_range(app.db_conn, name, [iso for iso, _ in days])

        _h_country = app.config.get("holiday_country", "DE") or "DE"
        _h_subdiv = app.config.get("holiday_subdiv", "") or None

        _WDAY_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        seen_projects: set[str] = set()
        for (cell, cell_tip), (iso_date, by_proj) in zip(
            zip(self._day_frames, self._cell_tips, strict=True), days, strict=False
        ):
            try:
                d = datetime.strptime(iso_date, "%Y-%m-%d").date()
            except ValueError:
                continue
            weekday = d.weekday()  # 0=Mo, 6=So
            is_weekend = weekday >= 5
            is_today = d == today and self.offset == 0
            _is_hol = is_holiday(d, country=_h_country, subdiv=_h_subdiv)

            if _is_hol:
                date_fg = "#CC4444"
            elif is_weekend:
                date_fg = "#888888"
            else:
                date_fg = "#000000"

            # Heute-Marker: leicht hellerer Hintergrund + sunken bevel
            if is_today:
                cell_bg = "#E8E8E8"
                cell.configure(bg=cell_bg, relief="sunken", borderwidth=1)
            else:
                cell_bg = "#C0C0C0"
                cell.configure(bg=cell_bg, relief="flat", borderwidth=0)

            day_total = sum(by_proj.values())
            # Tag vollständig übertragen, wenn er Zeiten hat und alle Projekte
            # dieses Tages den Übertragen-Status tragen.
            day_transferred = bool(by_proj) and all(meta_map.get((p, iso_date), {}).get("transferred") for p in by_proj)

            # Wochentag (bold) und Datum als zwei Labels
            Label(cell, text=_WDAY_DE[weekday], bg=cell_bg, fg=date_fg, font=("MS Sans Serif", 8, "bold")).pack(
                side="top", pady=(2, 0)
            )
            Label(cell, text=d.strftime("%d.%m"), bg=cell_bg, fg=date_fg, font=("MS Sans Serif", 8)).pack(side="top")

            # Gesamtstunden des Tages ("—" wenn leer); ✓ wenn voll übertragen.
            # Bei vorhandenen Zeiten klickbar: toggelt den Übertragen-Status
            # aller sichtbaren Projekte des Tages (schneller Abhak-Workflow).
            if day_total == 0.0:
                Label(cell, text="—", bg=cell_bg, fg="#888888", font=("MS Sans Serif", 8, "bold")).pack(side="top")
            else:
                total_text = app._fmt_hours_hm(day_total) + (" ✓" if day_transferred else "")
                total_lbl = Label(
                    cell,
                    text=total_text,
                    bg=cell_bg,
                    fg=("#008000" if day_transferred else date_fg),
                    font=("MS Sans Serif", 8, "bold"),
                    cursor="hand2",
                )
                total_lbl.pack(side="top")
                day_label = f"{_WDAY_DE[weekday]} {d.strftime('%d.%m.')}"
                day_projects = sorted(by_proj)
                total_lbl.bind(
                    "<Button-1>",
                    lambda _e, i=iso_date, ps=day_projects, lb=day_label: self._on_day_transfer(i, ps, lb),
                )
                _ToolTip(
                    total_lbl,
                    "Klick: Tag als »übertragen« markieren"
                    if not day_transferred
                    else "Klick: Übertragen-Status des Tages zurücksetzen",
                )

            # Gestapelte, projektweise eingefaerbte Block-Segmente (groesstes oben).
            tooltip_lines = [f"{_WDAY_DE[weekday]} {d.strftime('%d.%m')}: {app._fmt_hours_hm(day_total)}"]
            for proj, hrs in sorted(by_proj.items(), key=lambda kv: (-kv[1], kv[0])):
                seen_projects.add(proj)
                meta = meta_map.get((proj, iso_date), {})
                note = meta.get("note", "")
                transferred = bool(meta.get("transferred"))
                n_blocks = max(1, int(round((hrs / max_hours) * BAR_BLOCKS_MAX)))
                # Übertragen = schraffiert (▒), offen = solide (█); Projektfarbe bleibt.
                block_char = "▒" if transferred else "█"
                seg = Label(
                    cell,
                    text="\n".join([block_char] * n_blocks),
                    bg=cell_bg,
                    fg=color_map.get(proj, WEEK_PROJECT_COLORS[0]),
                    font=("Courier New", 7),
                )
                seg.pack(side="top")
                # Hover über den Balken: Projektname + getrackte Zeit + Status + Notiz.
                seg_tip = f"{proj}: {app._fmt_hours_hm(hrs)} ({_WDAY_DE[weekday]} {d.strftime('%d.%m')})"
                line = f"  {proj}: {app._fmt_hours_hm(hrs)}"
                if transferred:
                    at = meta.get("transferred_at")
                    when = ""
                    if at:
                        try:
                            when = " am " + datetime.strptime(at, "%Y-%m-%d").strftime("%d.%m.%Y")
                        except ValueError:
                            when = ""
                    seg_tip += f"\n✓ übertragen{when}"
                    line += f" [übertragen{when}]"
                if note:
                    seg_tip += f"\nNotiz: {note}"
                    line += f" — {note}"
                _ToolTip(seg, seg_tip)
                tooltip_lines.append(line)

            cell_tip.set_text("\n".join(tooltip_lines))

        # Wochen-Button: aktiv sobald die Woche Zeiten hat; Label spiegelt die
        # Aktion (✓ = markieren, ↺ = alles ist übertragen → zurücknehmen).
        self._week_items = [(p, iso) for iso, by_proj in days for p in by_proj]
        if self._week_items:
            week_done = all(meta_map.get((p, iso), {}).get("transferred") for p, iso in self._week_items)
            self._btn_transfer.configure(
                state="normal",
                fg="#666666",
                text=("↺ Woche" if week_done else "✓ Woche"),
            )

        # Legende: Farbsymbol + Projektname + Wochensumme fuer alle in dieser
        # Woche aktiven Projekte, plus Σ-Gesamt. Summen aus den bereits
        # geladenen Tagesdaten — kein zusätzlicher DB-Zugriff.
        if seen_projects:
            proj_totals: dict[str, float] = {}
            for _iso, by_proj in days:
                for p, h in by_proj.items():
                    proj_totals[p] = proj_totals.get(p, 0.0) + h
            Label(self._legend_frame, text="Projekte:", bg="#C0C0C0", fg="#404040", font=("MS Sans Serif", 8)).pack(
                side="left", padx=(0, 4)
            )
            for proj in sorted(seen_projects):
                total = app._fmt_hours_hm(proj_totals.get(proj, 0.0)).removesuffix(" h")
                Label(
                    self._legend_frame,
                    text=f"█ {proj} {total}",
                    bg="#C0C0C0",
                    fg=color_map.get(proj, WEEK_PROJECT_COLORS[0]),
                    font=("MS Sans Serif", 8, "bold"),
                ).pack(side="left", padx=4)
            Label(
                self._legend_frame,
                text=f"Σ {app._fmt_hours_hm(sum(proj_totals.values()))}",
                bg="#C0C0C0",
                fg="#404040",
                font=("MS Sans Serif", 8, "bold"),
            ).pack(side="left", padx=(8, 0))
