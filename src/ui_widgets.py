"""Kleine, wiederverwendbare UI-Bausteine (tkinter), geteilt von App und WeekView."""

from tkinter import Label, Toplevel

# Farbpalette für die Projekt-Farbcodierung in der Wochenansicht. Distinkte,
# kräftige Farben; die Zuordnung erfolgt stabil über den Projektnamen.
WEEK_PROJECT_COLORS = [
    "#000080",
    "#008000",
    "#800000",
    "#808000",
    "#800080",
    "#008080",
    "#D2691E",
    "#0000FF",
    "#C00000",
    "#006666",
]


def project_color(name: str) -> str:
    """Liefert eine stabile (laufübergreifend gleiche) Farbe für einen Projektnamen."""
    if not name:
        return WEEK_PROJECT_COLORS[0]
    idx = sum(ord(c) for c in name) % len(WEEK_PROJECT_COLORS)
    return WEEK_PROJECT_COLORS[idx]


class _ToolTip:
    """Lightweight hover tooltip for any tkinter widget.

    Instanzen sind wiederverwendbar: ``set_text`` ändert den Text nachträglich,
    ohne neue Event-Bindings anzulegen — wichtig für langlebige Widgets, die
    bei jedem Refresh neuen Tooltip-Text bekommen (sonst akkumulieren die
    ``add="+"``-Bindings unbegrenzt).
    """

    _DELAY_MS = 400

    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._tw = None
        self._label = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def set_text(self, text: str) -> None:
        """Ändert den Tooltip-Text; leerer Text deaktiviert das Popup.

        Ein gerade offenes Popup wird mit aktualisiert bzw. geschlossen —
        sonst zeigt es beim 30-s-Auto-Refresh der Wochenansicht veraltete Werte.
        """
        self._text = text
        if self._tw is None:
            return
        if not text:
            self._hide()
        elif self._label is not None:
            self._label.config(text=text)

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self._widget.after(self._DELAY_MS, self._show)

    def _cancel(self):
        if self._after_id:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self, _event=None):
        self._after_id = None
        # Widget kann zwischen Hover und Ablauf der 400 ms zerstört worden sein
        # (Refresh baut Segment-Labels neu) — dann still nichts anzeigen.
        if self._tw or not self._text or not self._widget.winfo_exists():
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 2
        self._tw = tw = Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        self._label = Label(
            tw,
            text=self._text,
            bg="#FFFFE0",
            fg="black",
            font=("MS Sans Serif", 9),
            relief="solid",
            borderwidth=1,
            padx=4,
            pady=2,
            wraplength=320,
        )
        self._label.pack()

    def _hide(self, _event=None):
        self._cancel()
        if self._tw:
            self._tw.destroy()
            self._tw = None
            self._label = None
