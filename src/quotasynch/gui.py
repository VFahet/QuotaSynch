"""L'interface `tkinter` : les heures d'ancrage et le journal."""

import tkinter
from tkinter import ttk

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


class Interface:
    def __init__(self, root: tkinter.Tk, system: System) -> None:
        self.system = system
        root.title("QuotaSynch")
        frame = ttk.Frame(root, padding=12)
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

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
        self.table = ttk.Treeview(
            frame, columns=[c[0] for c in COLUMNS], show="headings", height=12
        )
        for key, title, width in COLUMNS:
            self.table.heading(key, text=title)
            self.table.column(key, width=width, anchor="w", stretch=key == "detail")
        self.table.grid(row=6, column=0, sticky="nsew")
        self.empty = ttk.Label(frame, text=EMPTY_JOURNAL)
        self.empty.grid(row=7, column=0, sticky="w")
        frame.rowconfigure(6, weight=1)

        view = self.load_hours()
        if view.problem:
            self.show(
                f"Configuration invalide : {view.problem}. Corrigez les heures puis enregistrez "
                "(le modèle et le message reviendront à leurs valeurs par défaut)."
            )
        self.refresh_journal()

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


def open_interface(system: System) -> None:
    """Ouvre l'interface et rend la main quand elle est fermée."""
    root = tkinter.Tk()
    Interface(root, system)
    root.mainloop()
