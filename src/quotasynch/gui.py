"""L'interface `tkinter` : les heures d'ancrage et le journal."""

import tkinter
from tkinter import ttk

from quotasynch.interface import JournalRow, journal_rows, load_hours
from quotasynch.system import System

COLUMNS = (
    ("planned", "Prévue", 110),
    ("actual", "Réelle", 110),
    ("delay", "Retard", 70),
    ("result", "Résultat", 80),
    ("detail", "Détail", 320),
)


def _journal_table(parent: ttk.Frame, rows: list[JournalRow]) -> ttk.Treeview:
    table = ttk.Treeview(parent, columns=[c[0] for c in COLUMNS], show="headings", height=12)
    for key, title, width in COLUMNS:
        table.heading(key, text=title)
        table.column(key, width=width, anchor="w", stretch=key == "detail")
    for row in rows:
        table.insert("", "end", values=(row.planned, row.actual, row.delay, row.result, row.detail))
    return table


def open_interface(system: System) -> None:
    """Ouvre l'interface et rend la main quand elle est fermée."""
    root = tkinter.Tk()
    root.title("QuotaSynch")
    frame = ttk.Frame(root, padding=12)
    frame.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    hours = load_hours(system)
    ttk.Label(frame, text="Heures d'ancrage").grid(row=0, column=0, sticky="w")
    ttk.Label(frame, text=", ".join(hours.hours)).grid(row=1, column=0, sticky="w")
    if hours.problem:
        ttk.Label(frame, text=hours.problem, wraplength=560).grid(row=2, column=0, sticky="w")

    ttk.Label(frame, text="Journal").grid(row=3, column=0, sticky="w", pady=(12, 0))
    rows = journal_rows(system)
    if rows:
        _journal_table(frame, rows).grid(row=4, column=0, sticky="nsew")
    else:
        ttk.Label(frame, text="Aucun ancrage pour l'instant.").grid(row=4, column=0, sticky="w")
    frame.columnconfigure(0, weight=1)
    root.mainloop()
