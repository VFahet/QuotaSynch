# spec: journal-envois — Journal des envois et interface

**Statut :** Draft
**Enjeu :** 1
**Mode :** Direct — une session, cinq tranches environ, Enjeu 1, une PR lisible.
**Epic :** https://github.com/VFahet/QuotaSynch/issues/3

## Énoncé du problème

L'auteur n'a aucune trace de ce que l'outil a fait : il ne sait pas si l'ancrage de 5 h est parti, s'il a été sauté ou s'il a échoué, ni avec quel retard après une veille. Aujourd'hui `status` ne montre que la date du dernier envoi réussi, et une erreur de `run` se perd, car la tâche tourne sans console. Pour changer ses heures d'ancrage, il doit éditer un fichier TOML à la main puis relancer `install`.

## Solution

Chaque exécution d'un ancrage laisse une ligne dans un journal : heure prévue, heure réelle, résultat (envoyé, saut ou échec), et un détail quand il y en a un. `status` affiche le dernier ancrage. Une commande `quotasynch gui` ouvre une petite interface, à la demande, qui montre le journal avec le retard de chaque ancrage et permet de modifier les heures d'ancrage : « Enregistrer » réécrit la configuration et met à jour la tâche du Planificateur. L'interface se ferme avec sa fenêtre système et ne laisse aucun processus.

## User stories

1. En tant qu'auteur, je veux **que chaque ancrage laisse une ligne dans le journal (heure prévue, heure réelle, résultat)**, afin de savoir ce que l'outil a fait sans deviner.
2. En tant qu'auteur, je veux **qu'une configuration invalide soit aussi consignée comme un échec**, afin de ne pas ignorer une tâche qui échoue sans console.
3. En tant qu'auteur, je veux **voir le dernier ancrage dans `quotasynch status`**, afin de vérifier d'un coup d'œil que l'outil tourne.
4. En tant qu'auteur, je veux **ouvrir l'interface par `quotasynch gui`**, afin d'avoir un écran plutôt que des fichiers.
5. En tant qu'auteur, je veux **lire le journal dans l'interface, avec le retard de chaque ancrage**, afin de voir si mes fenêtres démarrent à l'heure prévue.
6. En tant qu'auteur, je veux **modifier mes heures d'ancrage dans l'interface et les enregistrer**, afin que la configuration et les tâches planifiées suivent sans que je touche au TOML ni au Planificateur.

## Décisions d'implémentation

Architecture : [ADR-0001](../adr/0001-planificateur-windows-et-etat-minimal.md) (le journal est un fichier à part de `state.json`). Vocabulaire : [CONTEXT.md](../../CONTEXT.md) — le mot « fenêtre » désigne la période de quota ; l'écran s'appelle l'**interface**.

- **Journal** : fichier `journal.jsonl` dans `%LOCALAPPDATA%\QuotaSynch\`, une ligne JSON par ancrage, en ajout seul. Champs : `prevue` (date ISO 8601 avec fuseau, ou `null`), `reelle` (idem), `resultat` (`envoye`, `saut` ou `echec`), `detail` (texte ou `null`). Aucune rotation : environ 10 Ko par mois pour 3 ancrages par jour, très en dessous du plafond de 1 Mo du PRD. Une ligne illisible est ignorée à la lecture.
- **Heure prévue** : la dernière heure d'ancrage inférieure ou égale à l'instant de l'exécution, déduite de la configuration. Plusieurs ancrages manqués donnent une seule ligne. Le retard consigné est donc mesuré depuis la dernière heure d'ancrage, pas depuis la première manquée : il est sous-estimé après une longue veille. Le rendre exact demanderait une tâche par heure d'ancrage et rouvrirait l'ADR-0001.
- **Résultats consignés** : `envoye`, `saut` (détail : depuis quand la fenêtre est ouverte), `echec` (détail : la dernière ligne d'erreur de `claude`, jamais le contenu d'une conversation). Une configuration invalide ou illisible est un `echec` avec `prevue` à `null`.
- **Échec d'écriture du journal** : `run` écrit un avertissement sur stderr et garde le code de sortie de l'envoi, car la fenêtre de quota est déjà démarrée. *(tranché par défaut)*
- **`status`** : une ligne s'ajoute, `dernier ancrage : <résultat>, prévu <hh:mm>, parti <hh:mm> (retard <n> min)`. Il n'y a pas de commande `journal` : la lecture passe par `status`, le fichier et l'interface. *(tranché par défaut)*
- **`state.json`** ne change pas : il reste la seule source de la règle de saut.
- **Interface** : `tkinter` (bibliothèque standard, aucune dépendance), lancée par `quotasynch gui`, à la demande. Elle ne tourne que le temps qu'elle est ouverte. Elle contient deux zones : les heures d'ancrage (liste modifiable : ajout, suppression, saisie `hh:mm`) avec un bouton « Enregistrer », et le journal (les derniers ancrages, plus récent en haut : prévue, réelle, retard, résultat, détail). Le modèle, le message et le réglage de réveil se modifient dans le fichier seulement. *(tranché par défaut)*
- **Enregistrer** (décision de l'utilisateur) : l'interface valide les heures avec la même règle que la lecture de la configuration (dont le refus de deux heures espacées de moins de 5 h), réécrit `config.toml` — qui reste la source de vérité —, puis recrée la tâche avec le même code que `install`. Une erreur de validation ou de `schtasks` s'affiche dans l'interface. Les commentaires écrits à la main dans le TOML sont perdus à la réécriture. Si la tâche n'était pas installée, « Enregistrer » l'installe.
- **Séparation** : la logique de l'interface (lignes du tableau, validation et enregistrement du formulaire) vit dans un module sans `tkinter`, appelé par une couche d'affichage fine.
- **Exigences non fonctionnelles du PRD qui portent ici** : aucun processus résident ; moins de 60 s par exécution de `run` (l'écriture du journal est négligeable) ; moins de 1 Mo de données par mois ; tout reste local ; aucune conversation lue ni stockée (le détail d'un échec est une ligne d'erreur de `claude`, pas une conversation).
- **Contribution aux métriques** : le journal donne le retard de chaque ancrage, ce qui sert la métrique 1 (départ à ±10 min) ; elle se mesure avec l'heure de réinitialisation fournie par Claude Code, qui reste hors de cette fonctionnalité.
- **Construite sans design system** : `docs/design.md` n'existe pas ; l'interface utilise l'apparence par défaut de `tkinter`, le style viendra plus tard si l'auteur lance `/design-system`.

## Décisions de test

- Le comportement s'observe à l'interface de la commande, comme pour `ancrage-planifie` : `run`, `status` et `install` avec un `System` aux doubles (horloge, lanceur de processus, chemins), qui prolonge `tests/test_run.py`, `tests/test_status.py` et `tests/test_install.py`. On vérifie le contenu du journal après `run` pour chacun des trois résultats, y compris la configuration invalide (`prevue` à `null`) et l'échec d'écriture du journal (code de sortie inchangé).
- La déduction de l'heure prévue se teste avec une horloge injectée : avant la première heure du jour, entre deux heures, après la dernière.
- L'interface se teste à la logique sans `tkinter` : lignes du tableau pour un journal donné, enregistrement du formulaire (configuration réécrite, tâche recréée avec le bon XML, erreur affichée pour deux heures trop proches). Même art antérieur que `tests/test_config.py` et `tests/test_install.py`.
- Pas de test automatique de l'affichage `tkinter`. **Vérification manuelle, une seule fois, par l'auteur** : ouvrir `quotasynch gui`, voir le journal, changer une heure, enregistrer, puis contrôler la tâche dans le Planificateur. Elle ne lance aucun envoi réel.

## Hors-scope

- Relevé du quota, export, calcul automatique des horaires.
- Modifier le modèle, le message ou le réglage de réveil depuis l'interface.
- Commande `journal`, filtres ou recherche dans le journal, graphiques.
- Rotation ou purge du journal.
- Retard exact depuis le premier ancrage manqué (demanderait une tâche par heure d'ancrage).
- Choix de l'apparence de l'interface (`/design-system`).

## Questions ouvertes

- **Le PRD** place encore l'interface hors de `journal-envois` (il ne la mentionne pas) : l'auteur la met à jour avec `/prd`. Cette spec fait foi en attendant.
- **`tkinter` est-il présent** dans le Python 3.13 que `uv` installe chez l'auteur ? À vérifier au build, sinon l'auteur tranche (installer le composant ou changer de bibliothèque).
