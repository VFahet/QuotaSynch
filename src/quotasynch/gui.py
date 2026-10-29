"""L'interface `tkinter` : les heures d'ancrage, le journal et la consommation."""

import tkinter
from tkinter import ttk

from quotasynch import consommation
from quotasynch.config import ConfigError
from quotasynch.interface import HoursView, journal_rows, load_hours, save_hours
from quotasynch.scheduler import SchedulerError
from quotasynch.system import System

COLUMNS = (
    ("planned", "Prévue", 110),
    ("actual", "Réelle", 110),
    ("delay", "Retard", 70),
    ("result", "Résultat", 80),
    ("detail", "Détail", 320),
)
EMPTY_JOURNAL = "Aucun ancrage pour l'instant."
HOURS_COLUMNS = (
    ("heure", "Heure", 80),
    ("moyenne", "Points de fenêtre par jour", 220),
)
WINDOW_COLUMNS = (
    ("debut", "Début", 110),
    ("fin", "Fin", 110),
    ("plus_haut", "Plus haut", 90),
    ("cent", "Heure du 100 %", 110),
    ("datee", "Part datée", 90),
)
EMPTY_USAGE = (
    "Aucune variation pour l'instant. Ouvrez Claude Code dans un terminal avec la statusline "
    "du README : elle les écrit à chaque changement du quota."
)


class Interface:
    def __init__(self, root: tkinter.Tk, system: System) -> None:
        self.system = system
        root.title("QuotaSynch")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.onglets = ttk.Notebook(root)
        self.onglets.grid(sticky="nsew")

        frame = ttk.Frame(self.onglets, padding=12)
        frame.columnconfigure(0, weight=1)
        self.onglets.add(frame, text="Ancrages")

        ttk.Label(frame, text="Heures d'ancrage").grid(row=0, column=0, sticky="w")
        self.hours = tkinter.Listbox(frame, height=5, exportselection=False)
        self.hours.grid(row=1, column=0, sticky="ew")
        controls = ttk.Frame(frame)
        controls.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.new_hour = tkinter.StringVar()
        entry = ttk.Entry(controls, textvariable=self.new_hour, width=8)
        entry.grid(row=0, column=0)
        entry.bind("<Return>", lambda _event: self.add_hour())
        ttk.Button(controls, text="Ajouter l'heure (HH:MM)", command=self.add_hour).grid(
            row=0, column=1, padx=6
        )
        ttk.Button(controls, text="Retirer l'heure choisie", command=self.remove_hour).grid(
            row=0, column=2
        )
        ttk.Button(frame, text="Enregistrer les heures", command=self.save).grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )
        self.message = ttk.Label(frame, wraplength=560)
        self.message.grid(row=4, column=0, sticky="w", pady=(4, 0))

        ttk.Label(frame, text="Journal").grid(row=5, column=0, sticky="w", pady=(12, 0))
        self.table = _table(frame, COLUMNS, height=12, stretch="detail")
        self.table.grid(row=6, column=0, sticky="nsew")
        self.empty = ttk.Label(frame, text=EMPTY_JOURNAL)
        self.empty.grid(row=7, column=0, sticky="w")
        frame.rowconfigure(6, weight=1)

        self.build_consommation()

        view = self.load_hours()
        if view.problem:
            self.show(
                f"Configuration invalide : {view.problem}. Corrigez les heures puis enregistrez "
                "(le modèle et le message reviendront à leurs valeurs par défaut)."
            )
        self.refresh_journal()
        self.refresh_consommation()

    def build_consommation(self) -> None:
        tab = ttk.Frame(self.onglets, padding=12)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        self.onglets.add(tab, text="Consommation")

        self.usage = ttk.Frame(tab)
        self.usage.columnconfigure(0, weight=1)
        self.usage.grid(row=0, column=0, sticky="nsew")
        ttk.Label(self.usage, text="Heures de la journée").grid(row=0, column=0, sticky="w")
        self.hour_table = _table(self.usage, HOURS_COLUMNS, height=12)
        _with_scrollbar(self.usage, self.hour_table, row=1)
        self.footer = ttk.Label(self.usage, wraplength=560)
        self.footer.grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(self.usage, text="Fenêtres").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.window_table = _table(self.usage, WINDOW_COLUMNS, height=8)
        _with_scrollbar(self.usage, self.window_table, row=4)
        self.usage.rowconfigure(1, weight=1)
        self.usage.rowconfigure(4, weight=1)

        self.usage_empty = ttk.Label(tab, text=EMPTY_USAGE, wraplength=560)
        self.usage_empty.grid(row=0, column=0, sticky="nw")

    def load_hours(self) -> HoursView:
        view = load_hours(self.system)
        self.hours.delete(0, "end")
        for hour in view.hours:
            self.hours.insert("end", hour)
        return view

    def show(self, text: str) -> None:
        self.message.configure(text=text)

    def hour_list(self) -> list[str]:
        return [str(self.hours.get(i)) for i in range(self.hours.size())]

    def add_hour(self) -> None:
        text = self.new_hour.get().strip()
        if text:
            self.hours.insert("end", text)
            self.new_hour.set("")

    def remove_hour(self) -> None:
        for index in reversed(self.hours.curselection()):  # type: ignore[no-untyped-call]
            self.hours.delete(index)

    def save(self) -> None:
        try:
            result = save_hours(self.system, self.hour_list())
        except SchedulerError as erreur:
            self.load_hours()
            self.show(
                "Heures enregistrées dans la configuration, mais la tâche planifiée n'a pas "
                f"été mise à jour : {erreur}. Enregistrez de nouveau pour réessayer."
            )
            return
        except (ConfigError, OSError) as erreur:
            self.show(f"Heures non enregistrées : {erreur}")
            return
        self.load_hours()
        self.show(f"Heures enregistrées. {result}")

    def refresh_journal(self) -> None:
        self.table.delete(*self.table.get_children())
        rows = journal_rows(self.system)
        for row in rows:
            self.table.insert(
                "", "end", values=(row.planned, row.actual, row.delay, row.result, row.detail)
            )
        if rows:
            self.empty.grid_remove()
        else:
            self.empty.grid()

    def refresh_consommation(self) -> None:
        hours = consommation.par_heure(self.system)
        if hours is None:
            self.usage.grid_remove()
            self.usage_empty.grid()
            return
        self.usage_empty.grid_remove()
        self.usage.grid()

        self.hour_table.delete(*self.hour_table.get_children())
        for line in hours.lignes:
            self.hour_table.insert("", "end", values=(line.heure, line.moyenne))
        self.footer.configure(text=hours.pied)

        self.window_table.delete(*self.window_table.get_children())
        for window in consommation.par_fenetre(self.system):
            self.window_table.insert(
                "",
                "end",
                values=(window.debut, window.fin, window.plus_haut, window.cent, window.datee),
            )


def _table(
    parent: tkinter.Misc,
    columns: tuple[tuple[str, str, int], ...],
    height: int,
    stretch: str | None = None,
) -> ttk.Treeview:
    """Un tableau en lecture seule, une colonne par (clé, titre, largeur)."""
    table = ttk.Treeview(parent, columns=[c[0] for c in columns], show="headings", height=height)
    for key, title, width in columns:
        table.heading(key, text=title)
        table.column(key, width=width, anchor="w", stretch=key == stretch)
    return table


def _with_scrollbar(parent: tkinter.Misc, table: ttk.Treeview, row: int) -> None:
    table.grid(row=row, column=0, sticky="nsew")
    bar = ttk.Scrollbar(parent, orient="vertical", command=table.yview)
    bar.grid(row=row, column=1, sticky="ns")
    table.configure(yscrollcommand=bar.set)


def open_interface(system: System) -> None:
    """Ouvre l'interface et rend la main quand elle est fermée."""
    root = tkinter.Tk()
    Interface(root, system)
    root.mainloop()
