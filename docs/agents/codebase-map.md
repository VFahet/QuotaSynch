# Carte du code

Où regarder en premier. **Ce fichier ne décrit pas le code** — il dit ce que `grep` ne donne pas : le mot que le code emploie vraiment, ce qui casse à distance, ce qu'il ne faut pas lire.

Une zone entre quand un agent y a travaillé : `/build` ajoute ou corrige une entrée dans le commit qui la périme. Une entrée qui contredit le disque est un bug à corriger, pas une piste à suivre. Avant d'ajouter une ligne : *change-t-elle où l'agent regarde en premier ?* Sinon elle n'entre pas.

## Ancrage planifié (`src/quotasynch/`)

- **Point d'entrée** : `cli.main`. Il est lancé par `quotasynch`, par `python -m quotasynch` et par la tâche planifiée (`-m quotasynch run`, via `pythonw.exe`). `uninstall` est la seule commande qui ne charge pas la configuration.
- **Tout ce qui touche au système passe par `system.System`** (horloge, lanceur de processus, environnement, chemins `%APPDATA%\QuotaSynch\config.toml` et `%LOCALAPPDATA%\QuotaSynch\{state.json,task.xml}`). Les tests construisent un `System` avec des doubles (`tests/conftest.py`) ; n'appeler `subprocess` ou `datetime.now` nulle part ailleurs.
- **« Fenêtre ouverte »** : la règle des 5 h vit dans `anchoring.window_open`, appelée par `run` et par `status`. Changer ce que « ouverte » veut dire, c'est là.
- **Fichier d'état** : `state.json`, la seule clé `last_send`, avec fuseau obligatoire ; un fichier sans fuseau ou illisible est lu comme absent (donc le prochain ancrage envoie). Voir l'ADR-0001.
- **Planificateur** : `scheduler.build_task_xml` produit un XML **UTF-16** pour `schtasks /Create /XML`. Un déclencheur quotidien par `config.anchors`, `WakeToRun` suit `config.wake`. Accepté par un vrai `schtasks` en octobre 2026 ; les tests ne vérifient que le XML, pas Windows.
- **Les heures de `config.toml` sont validées à la lecture** (`config.load_config`) : `run`, `install` et `status` refusent toutes une configuration invalide.
