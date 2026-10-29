"""L'interface `tkinter` : les heures d'ancrage, le journal et la consommation."""

import tkinter
from tkinter import ttk

from quotasynch import consommation
from quotasynch.config import ConfigError
from quotasynch.interface import (
    HoursView,
    journal_rows,
    load_hours,
    pied_heures,
    save_hours,
)
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
    ("cent", "100 % à", 90),
    ("datee", "Part datée", 90),
)
EMPTY_CONSOMMATION = (
    "Aucune variation pour l'instant : elles s'écrivent quand Claude Code tourne dans un "
    "terminal avec la statusline du README."
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
        onglet = ttk.Frame(self.onglets, padding=12)
        onglet.columnconfigure(0, weight=1)
        self.onglets.add(onglet, text="Consommation")

        self.conso_contenu = ttk.Frame(onglet)
        self.conso_contenu.columnconfigure(0, weight=1)
        self.conso_contenu.grid(row=0, column=0, sticky="nsew")
        contenu = self.conso_contenu

        ttk.Label(contenu, text="Heures de la journée").grid(row=0, column=0, sticky="w")
        self.heures = ttk.Treeview(
            contenu, columns=[c[0] for c in HOURS_COLUMNS], show="headings", height=24
        )
        for key, title, width in HOURS_COLUMNS:
            self.heures.heading(key, text=title)
            self.heures.column(key, width=width, anchor="w")
        self.heures.grid(row=1, column=0, sticky="nsew")
        self.pied_heures = ttk.Label(contenu, wraplength=560)
        self.pied_heures.grid(row=2, column=0, sticky="w", pady=(4, 0))

        ttk.Label(contenu, text="Fenêtres").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.fenetres = ttk.Treeview(
            contenu, columns=[c[0] for c in WINDOW_COLUMNS], show="headings", height=12
        )
        for key, title, width in WINDOW_COLUMNS:
            self.fenetres.heading(key, text=title)
            self.fenetres.column(key, width=width, anchor="w")
        self.fenetres.grid(row=4, column=0, sticky="nsew")

        self.conso_vide = ttk.Label(onglet, text=EMPTY_CONSOMMATION, wraplength=560)
        self.conso_vide.grid(row=0, column=0, sticky="w")

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
        par_heure = consommation.par_heure(self.system)
        if par_heure is None:
            self.conso_contenu.grid_remove()
            self.conso_vide.grid()
            return
        self.conso_vide.grid_remove()
        self.conso_contenu.grid()

        self.heures.delete(*self.heures.get_children())
        for ligne in par_heure.lignes:
            self.heures.insert("", "end", values=(ligne.heure, ligne.moyenne))
        self.pied_heures.configure(text=pied_heures(par_heure))

        self.fenetres.delete(*self.fenetres.get_children())
        for fenetre in consommation.par_fenetre(self.system):
            self.fenetres.insert(
                "",
                "end",
                values=(fenetre.debut, fenetre.fin, fenetre.plus_haut, fenetre.cent, fenetre.datee),
            )


def open_interface(system: System) -> None:
    """Ouvre l'interface et rend la main quand elle est fermée."""
    root = tkinter.Tk()
    Interface(root, system)
    root.mainloop()
