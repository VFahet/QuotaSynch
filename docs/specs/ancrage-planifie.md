# spec: ancrage-planifie — Ancrage planifié

**Statut :** Draft
**Enjeu :** 1
**Mode :** Direct — une session, cinq tranches environ, Enjeu 1, une PR lisible.
**Epic :** https://github.com/VFahet/QuotaSynch/issues/1

## Énoncé du problème

L'auteur, abonné Claude Pro, ne choisit pas l'heure à laquelle ses fenêtres de quota démarrent : elles commencent à son premier message. Il ne sait donc pas quand il retrouvera du quota. Il veut que trois fenêtres consécutives couvrent sa journée, à des heures qu'il a fixées, sans y penser et même si son portable dormait à l'heure prévue.

## Solution

L'auteur lance une commande d'installation une fois. Ensuite, chaque jour, un message minimal part de lui-même à chacune de ses heures d'ancrage : 5 h 00, 10 h 01 et 15 h 02, ce qui donne les fenêtres 5 h–10 h, 10 h 01–15 h 01 et 15 h 02–20 h 02. Si le PC le permet, il se réveille pour envoyer à l'heure. Sinon, l'envoi est rattrapé dès que le PC redevient disponible. Si une fenêtre est déjà ouverte quand un ancrage devait partir, cet ancrage est sauté. L'auteur peut changer ses heures dans un fichier de configuration et vérifier l'état de l'installation.

## User stories

1. En tant qu'auteur, je veux **choisir mes heures d'ancrage dans un fichier de configuration**, afin que mes fenêtres démarrent quand je l'ai décidé.
2. En tant qu'auteur, je veux **installer et désinstaller la planification d'une commande**, afin de ne pas manipuler le Planificateur de tâches à la main.
3. En tant qu'auteur, je veux **qu'un message minimal parte à chaque heure d'ancrage, par mon abonnement**, afin que la fenêtre démarre à cette heure sans consommer d'API facturée.
4. En tant qu'auteur, je veux **que le PC se réveille à l'heure d'ancrage quand il le peut**, afin que l'heure soit tenue à ±10 min même la nuit.
5. En tant qu'auteur, je veux **qu'un ancrage manqué soit rattrapé dès que le PC redevient disponible**, afin de ne pas perdre la fenêtre de la journée.
6. En tant qu'auteur, je veux **qu'un ancrage soit sauté quand une fenêtre est déjà ouverte**, afin qu'un réveil tardif n'envoie pas plusieurs messages pour rien.
7. En tant qu'auteur, je veux **voir l'état de l'installation et la date du dernier envoi**, afin de vérifier que l'outil tourne sans ouvrir le Planificateur.
8. En tant qu'auteur, je veux **qu'un envoi en échec se signale par un code de sortie non nul et un message d'erreur**, afin de ne pas croire à tort qu'une fenêtre a démarré.

## Décisions d'implémentation

Architecture : voir [ADR-0001](../adr/0001-planificateur-windows-et-etat-minimal.md). Vocabulaire : [CONTEXT.md](../../CONTEXT.md).

- **Commande unique** `quotasynch` avec `install`, `uninstall`, `run` et `status`. `run` est ce que la tâche exécute ; elle ne tourne jamais en résident.
- **Configuration** : fichier TOML dans `%APPDATA%\QuotaSynch\config.toml`, lu avec `tomllib`. Contient les heures d'ancrage, le modèle, le message, et un réglage de réveil du PC (global, par défaut activé). Sans fichier, les valeurs par défaut sont 05:00, 10:01 et 15:02, tous les jours. Une configuration dont deux heures d'ancrage sont espacées de moins de 5 h est refusée à `install`. *(tranché par défaut)*
- **Planification** : `install` crée une seule tâche du Planificateur avec un déclencheur quotidien par heure d'ancrage, via `schtasks /Create /XML` (aucune dépendance). La tâche porte le rattrapage natif (`StartWhenAvailable`), le réveil du PC (`WakeToRun`) quand il est activé, et reste autorisée sur batterie. Elle tourne sous le compte de l'auteur, session ouverte, pour retrouver les identifiants de l'abonnement. Si le réveil n'est pas possible, le rattrapage natif prend le relais.
- **Envoi** : `claude -p` avec un message minimal, lancé depuis un dossier vide dédié (`%LOCALAPPDATA%\QuotaSynch\`) pour ne charger aucun `CLAUDE.md`. Le modèle est celui de la config, par défaut `haiku`. `ANTHROPIC_API_KEY` est retirée de l'environnement de l'appel. Les options exactes de `claude` sont à confirmer au build contre la version installée (2.1.309).
- **Saut** : `run` lit la date du dernier envoi réussi dans `%LOCALAPPDATA%\QuotaSynch\state.json`. Si moins de 5 h se sont écoulées, il saute. Après un envoi réussi, il écrit la date. Un envoi en échec n'écrit rien, donc le prochain déclenchement réessaie. Un rattrapage tardif décale donc la fenêtre et peut faire sauter l'ancrage suivant ; c'est voulu. *(tranché par défaut)*
- **Fuseau** : heure locale ; le changement d'heure est géré par le Planificateur. *(tranché par défaut)*
- **Exigences non fonctionnelles du PRD qui portent ici** : aucun processus résident ; moins de 60 s par exécution (le délai d'attente de l'appel à `claude` est inférieur à cela) ; moins de 1 Mo de données conservées par mois (ici : un fichier d'état de quelques octets) ; 0 appel facturé à l'API ; aucune conversation lue ni stockée ; Windows 10 et 11, sur batterie comme sur secteur.
- **Ce que la fonctionnalité ne fait pas** : pas de journal des envois (fonctionnalité `journal-envois`), pas de relevé du quota ni d'export. L'état ne garde que la date du dernier envoi.
- **Outillage** : la première tranche pose `uv`, `ruff`, `mypy`, `pytest` et la commande unique `uv run poe check` (voir `sdlc.md`). Le dépôt n'a pas encore de remote ; la création du dépôt public sous licence MIT est faite avant le premier ticket.
- **Pas d'interface graphique** : aucune question de design system.

## Décisions de test

- Le comportement s'observe à l'interface de la commande : `run`, `install`, `uninstall`, `status`. On ne teste pas fonction par fonction.
- La logique de décision (saut ou envoi, lecture de la config, refus d'heures trop proches) se teste avec une horloge et un fichier d'état injectés, sans toucher au Planificateur.
- L'appel à `claude` et à `schtasks` est remplacé par un double aux frontières du système, et on vérifie ce qu'ils reçoivent : arguments de l'envoi, absence de `ANTHROPIC_API_KEY` dans l'environnement, XML de la tâche (déclencheurs, `StartWhenAvailable`, `WakeToRun`).
- Pas d'art antérieur : le dépôt n'a pas de suite de tests ; la première tranche l'établit.
- **Vérification manuelle, une seule fois, par l'auteur** : un envoi réel avec le modèle par défaut `haiku`, puis contrôle que l'heure de réinitialisation affichée par Claude Code se décale. Elle consomme du quota réel et démarre une fenêtre : l'agent ne la lance pas. Si l'heure ne bouge pas, on bascule sur le modèle par défaut de Claude Code. Le test du rattrapage au réveil se fait aussi à la main (veille, puis réveil).

## Hors-scope

- Journal des envois, relevé du quota, export, calcul automatique des horaires.
- Heures d'ancrage différentes selon les jours de la semaine.
- Réglage de réveil heure par heure (le réglage est global).
- macOS et Linux.

## Questions ouvertes

- **Le message minimal démarre-t-il bien une fenêtre avec `haiku` ?** À vérifier à la main par l'auteur avant le merge (voir Décisions de test). Si non : modèle par défaut.
- **Le réveil programmé fonctionne-t-il sur ce portable, sur batterie ?** À vérifier à la main par l'auteur ; sinon le rattrapage seul s'applique.
- **Le rattrapage natif est-il fiable ?** Si non, rouvrir l'ADR-0001.
