# SDLC de ce dépôt

Ce que les skills `/frame`, `/build` et `/patch` lisent avant d'écrire. Édité à la main quand le dépôt change ; `/setup` l'a écrit une fois.

## Branches

- Le trunk est `main`. Il est toujours livrable.
- Une **fonctionnalité** — une spec `docs/specs/<feature-slug>.md` — vit sur `feature/<feature-slug>`, créée par `/frame` depuis un trunk à jour, qui y commite la spec. `/build` y commite les tranches, une par commit.
- `patch/<slug>` : un changement sans spec, par `/patch`. `fix/<slug>` : un bug diagnostiqué par `/diagnosing-bugs`, livré par `/patch`. `prototype/<name>` : du code jetable, conservé hors du trunk comme source primaire, jamais mergé.
- Quand `/build` lance plusieurs tranches en parallèle, chacune travaille dans un worktree sur `tranche/<feature-slug>-<NN>`, mergée dans la branche de fonctionnalité dès qu'elle est finie. Ces branches sont internes et se suppriment après merge.

## Commits

Tout commit de ce dépôt, quel que soit le skill ou la session qui le fait, commence par son type : `<type>: <description>`. Seuls les commits de merge gardent le message de git.

| Type | Pour |
|---|---|
| `feat` | un comportement nouveau |
| `fix` | un bug corrigé |
| `refactor` | le code change, le comportement non |
| `perf` | plus rapide ou plus sobre, même comportement |
| `test` | des tests seuls, ajoutés ou corrigés |
| `docs` | de la documentation seule — spec, ADR, `CONTEXT.md`, tickets en fichiers |
| `style` | de la mise en forme seule |
| `ci` | la configuration de la CI |
| `chore` | le reste : dépendances, outillage, configuration du dépôt, `docs/agents/`, entretien |
| `revert` | l'annulation d'un commit précédent |

Le type suit le contenu du commit, pas le skill qui le fait : une tranche est le plus souvent un `feat`, un `fix` ou un `refactor` si c'est ce qu'elle fait ; le cadrage de `/frame` est un `docs` ; le commit final de `/build` — corrections, carte, statut — prend le type de ce qui y domine. Un changement qui casse un usage existant prend un `!` : `feat!:`.

## Merge

**Automatique**, dès qu'un remote GitHub existe (il n'y en a pas encore : tant que c'est le cas, pas de PR, on commite sur la branche et on merge en local). `/build` et `/patch` mergent eux-mêmes leur PR quand la vérification passe — la commande de vérification ci-dessous passe en local, ou la CI est verte si le dépôt en a une — et que l'Enjeu de la fonctionnalité est sous 5. Une fonctionnalité à Enjeu 5 attend l'accord de l'utilisateur. Force-pusher reste un geste de l'utilisateur.

Projet solo et très petit : peu de formalisme. Un changement trivial passe par `/patch`, sans spec.

## Tracker

Les tickets de ce dépôt sont des issues GitHub. CLI `gh` pour toutes les opérations ; le dépôt se déduit de `git remote -v`. Le remote n'existe pas encore : à créer avant le premier ticket (`gh repo create`, dépôt public, licence MIT).

| Niveau | Ici | Marque |
|---|---|---|
| **spec** | `docs/specs/<feature-slug>.md` | un fichier versionné, `**Statut :**` en tête |
| **epic** | une issue `spec: <feature-slug> — <titre>` | le préfixe de titre, label `spec` |
| **ticket** | une sous-issue de l'epic | `Parent : #<epic>` en tête du corps, label `ticket` |

Chaque fonctionnalité a son epic, découpée ou non : `/frame` l'ouvre à l'arbitrage. Menée d'une traite, elle n'a pas de sous-issues.

Le corps de l'epic est **mince** : un lien vers le fichier de spec, rien d'autre — la spec ne s'y recopie jamais, deux corps dérivent. Les tickets s'y rattachent en sous-issues natives (`gh api` sur l'endpoint sub-issues), qui affichent la progression seules ; à défaut, une task list `- [ ] #<n>` dans le corps de l'epic.

**Blocage** : les dépendances natives — `gh api --method POST repos/<owner>/<repo>/issues/<ticket>/dependencies/blocked_by -F issue_id=<id-bdd-du-bloqueur>`, l'id de base de données venant de `gh api repos/<owner>/<repo>/issues/<n> --jq .id`. À défaut, une ligne `Bloqué par : #<n>, #<n>` en tête du corps.

**Un ticket se ferme au commit de sa tranche** — `gh issue close <n> --comment "<commit> sur feature/<slug>"` — c'est ce qui débloque ses dépendants. L'epic se ferme au merge de la PR.

Un `#42` nu n'est pas un lien dans un fichier `.md` du dépôt : depuis `docs/specs/`, écrire l'URL complète.

Opérations : `gh issue create --title --body --label spec|ticket`, `gh issue view <n> --comments`, `gh issue list --state open --json number,title,body,labels`, `gh issue edit`, `gh issue close`.

## Vérification

- Stack : Python 3.13 avec `uv`, bibliothèque standard autant que possible (outil Windows léger, lancé par le Planificateur de tâches, sans processus résident)
- Commande unique : `uv run poe check`, qui enchaîne formatage, lint, types et tests
- Formatage et lint : `ruff` · Types : `mypy` (strict) · Tests : `pytest`
- Navigateur : aucun
- CI : aucune

Cette commande fait foi : `/build` la lance avant chaque commit de tranche et avant la PR, `/patch` avant son commit. Ce qu'elle applique, la revue ne le rapporte pas.

## Standards

Ce que ce dépôt attend d'un changement au-delà de ce que l'outillage applique. La revue de `/build` lit cette section ; ce qui y est écrit l'emporte sur sa base de smells par défaut.

- Léger avant tout : pas de processus résident, moins de 60 s par exécution, pas de dépendance tierce sans raison, car l'outil tourne sur un portable et se publie en open source.
- Aucun secret ni donnée personnelle dans le dépôt : il est public.
- Les envois passent par l'abonnement de l'utilisateur, jamais par une clé API : toute variable `ANTHROPIC_API_KEY` est retirée de l'environnement de l'appel.

## Docs de domaine

Avant d'explorer le code : `docs/agents/codebase-map.md` d'abord — où regarder, pas ce qu'il y a —, puis `CONTEXT.md` pour le vocabulaire, puis les ADR de `docs/adr/` qui couvrent la zone. Un fichier absent : continuer sans le signaler ; `/frame` les crée quand un terme ou une décision se tranche.

Dans toute sortie, le concept du domaine porte le nom que `CONTEXT.md` lui donne. Une sortie qui contredit un ADR le dit : *contredit l'ADR-0007, mais mérite d'être rouvert parce que…*
