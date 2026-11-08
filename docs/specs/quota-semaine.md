# spec: quota-semaine — Le quota de la semaine en points de fenêtre

**Statut :** Draft
**Enjeu :** 1
**Mode :** Par tranches — trois tranches, deux d'entre elles parallélisables ; Enjeu 1 (lecture seule de données locales, aucun envoi, aucune écriture hors affichage).
**Epic :** à ouvrir à l'arbitrage

## Énoncé du problème

Le quota hebdomadaire s'exprime en pourcentage de la semaine, ce qui ne dit pas combien de fenêtres de 5 h il reste. L'auteur veut le lire dans l'unité qu'il manipule tous les jours : le point de fenêtre (1 % d'une fenêtre de 5 h). Pour cela il faut connaître le **total de la semaine** : combien de points de fenêtre valent 100 % de la semaine (de l'ordre de 1 000 chez lui). Ce total n'est pas publié et peut changer d'une semaine à l'autre : il faut l'estimer à partir de ce qu'on observe, et dire honnêtement avec quelle précision.

## Solution

L'interface affiche, en haut de l'onglet « Consommation », une ligne pour la semaine en cours :

> Semaine : 46 % — ≈ 540 / 1 180 points de fenêtre (± 40, mesuré cette semaine)

Le **total de la semaine** s'estime en rapprochant, tout au long de la semaine, les points de fenêtre consommés (cumulés) et le pourcentage hebdomadaire. Comme le pourcentage hebdomadaire est un entier, chaque observation n'apporte qu'une **fourchette** pour le total ; on prend l'**intersection** de toutes les fourchettes de la semaine. Elle ne fait que se resserrer : l'estimation s'affine à chaque variation, sans bruit statistique, et rend sa propre marge d'erreur. Tant que la fourchette est trop large (début de semaine), on affiche le total de la semaine précédente, étiqueté comme tel.

## User stories

1. En tant qu'auteur, je veux **voir la consommation de la semaine en points de fenêtre, rapportée au total de la semaine**, afin de savoir combien de fenêtres pleines il me reste.
2. En tant qu'auteur, je veux que **ce total soit mesuré sur mes propres relevés, semaine après semaine**, afin qu'il suive un changement de quota sans que je règle quoi que ce soit.
3. En tant qu'auteur, je veux **lire la marge d'erreur et l'origine du total** (mesuré cette semaine, ou repris de la semaine précédente), afin de ne pas lire une précision que la mesure n'a pas.

## Décisions d'implémentation

Vocabulaire : [CONTEXT.md](../../CONTEXT.md) — **fenêtre**, **variation**, **instantané**. Deux termes à y ajouter : **point de fenêtre** (1 % d'une fenêtre ; le mot est déjà dans l'interface) et **total de la semaine** (le nombre de points de fenêtre qui valent 100 % de la semaine). Source : [ADR-0002](../adr/0002-releve-du-quota-par-la-statusline.md).

### Faits vérifiés sur les données de l'auteur (8 novembre 2026)

- `variations.jsonl` porte déjà `rate_limits.seven_day.used_percentage` et `.resets_at` à côté de `five_hour` : **aucun changement de la statusline ni de la collecte**.
- Les pourcentages sont **entiers** aux deux niveaux (valeurs vues : 12, 16, 17, 20, 34 ; 23, 37, 46).
- La remise à zéro hebdomadaire tombe **le lundi à 06:00 heure locale** (`resets_at` = 2 nov et 9 nov, 06:00 heure de Paris). C'est le moment où les deux compteurs partent de zéro.
- Une ligne peut ne porter que `seven_day` (fenêtre de 5 h fermée) : elle apporte une observation hebdomadaire sans point de fenêtre.
- Il n'y a que **8 variations** aujourd'hui : la stabilité du total d'une semaine à l'autre n'est pas vérifiable. C'est la question ouverte principale.

### Module de calcul

Un **nouveau module `semaine.py`**, sans `tkinter`, qui lit `variations.jsonl` par `jsonl.read` et expose une seule fonction publique, `semaine.estimation(system) -> Semaine | None`. `Semaine` porte une ligne déjà mise en forme (comme `consommation.ParHeure.pied`). Il ne modifie pas `consommation.py` : la règle « baisse ignorée, plus haut suivi » y est dupliquée en trois lignes plutôt qu'extraite, pour garder les deux fonctionnalités indépendantes. Les heures passent par `System.local_time`, comme dans `consommation`.

1. **Semaine** : les variations se groupent par `seven_day.resets_at` ; le début est `fin − 7 j`. Une variation sans `seven_day` est rattachée à la semaine dont l'intervalle contient son heure ; une ligne illisible, ou sans aucune limite, est ignorée.
2. **Points de fenêtre cumulés `S`** : dans une semaine, pour chaque fenêtre (groupée par `five_hour.resets_at`), on suit le plus haut pourcentage en partant de 0 au début de la fenêtre ; une hausse apporte `pct − plus haut` points à `S`, une baisse ou une valeur égale n'en apporte pas. On n'a pas besoin de dater ces points : seule la somme compte, donc la **consommation non datée** compte aussi.
3. **Observation** : à chaque variation qui porte `seven_day`, on note le couple `(S, w)` : `S` cumulé jusque-là, `w` le pourcentage hebdomadaire.
4. **Fourchette d'une observation** : le pourcentage est entier, mais on ne sait pas s'il est arrondi ou tronqué, donc la valeur réelle est dans `]w − 1 ; w + 1[` (constante `MARGE = 1`). Chaque fenêtre touchée ajoute la même incertitude à `S` : `e = MARGE × (nombre de fenêtres de la semaine déjà vues)`. Le total `T` (points de fenêtre pour 100 % de la semaine) vérifie
   `100 × (S − e) / (w + MARGE) ≤ T ≤ 100 × (S + e) / (w − MARGE)`,
   la borne haute valant l'infini si `w ≤ MARGE`. Une observation avec `S = 0` ou `w = 0` n'apporte rien et est sautée.
5. **Estimation de la semaine** : intersection de toutes les fourchettes, `bas = max` des bornes basses, `haut = min` des bornes hautes ; total = milieu, marge = demi-largeur. Exemples :
   - première fenêtre à 83 points, hebdomadaire passé de 0 à 7 % : `T` entre 1 025 et 1 400, soit 1 212 ± 187 (15 %) : trop large ;
   - fin de semaine, `S = 710`, `w = 60`, neuf fenêtres : `T` entre 1 149 et 1 219, soit 1 184 ± 35 (3 %).
6. **Semaine mesurable** : si une fenêtre commence avant le début de la semaine (`fin − 5 h < début`), elle contient de la consommation de la semaine précédente qu'on ne sait pas séparer : la semaine n'est **pas mesurable**, on ne retient aucune observation. Si l'intersection est vide (`bas > haut`) — typiquement une consommation hors terminal que la statusline n'a pas vue —, la semaine n'est pas mesurable non plus. On n'invente rien : on retombe sur la règle 7.
7. **Quel total afficher** (seuil `LARGEUR_MAX = 10 %`, la demi-largeur rapportée au total) :
   - semaine en cours mesurable et sous le seuil → son estimation, étiquetée « mesuré cette semaine » ;
   - sinon, l'estimation finale de la **semaine passée la plus récente** qui est mesurable et sous le seuil → étiquetée « semaine précédente » ;
   - sinon → pas de total : la ligne montre seulement le pourcentage, « total inconnu ».
8. **Semaine en cours** : celle dont la fin est après l'horloge de `System`. Si la dernière semaine connue est déjà finie, la semaine en cours vient de commencer (fin = fin connue + 7 j) : consommation 0, total repris de la semaine précédente. Sans aucune variation, `estimation` rend `None`.
9. **Consommé affiché** : `w_dernier × T / 100`, avec le dernier `w` de la semaine en cours ; sur une semaine mesurée il rejoint `S`, sur un total repris il reste cohérent avec lui.
10. **Mise en forme** : points arrondis à la dizaine, comme la marge ; milliers séparés par une espace insécable. Exemples : `Semaine : 46 % — ≈ 540 / 1 180 points de fenêtre (± 40, mesuré cette semaine)` ; `Semaine : 7 % — ≈ 80 / 1 180 points de fenêtre (semaine précédente)` ; `Semaine : 7 % — total inconnu`.

### Interface

- `gui.py` ajoute **un seul `ttk.Label`** en haut de l'onglet « Consommation », rempli par `refresh_consommation` avec la ligne de `semaine.estimation`. Il reste visible même sans variation de fenêtre ; sans aucune variation, le message vide existant s'affiche seul. Rien d'autre ne change dans l'onglet. *(tranché par défaut : l'interface n'affichait aucun pourcentage de semaine ; c'est la place la plus proche de « à côté de hebdomadaire »)*
- `gui.py` n'est toujours pas testé automatiquement.

### Exigences non fonctionnelles du PRD

Aucun processus résident (le calcul se fait à l'ouverture de l'interface) ; rien n'est écrit sur disque ; aucune dépendance tierce ; aucune nouvelle donnée conservée. Le calcul est linéaire dans le nombre de variations, à l'échelle de 1,5 Mo par mois au plus.

### Docs et PRD

- `CONTEXT.md` : les deux termes ci-dessus.
- `docs/prd.md` : une ligne de fonctionnalité 7 `quota-semaine` sous « Ensuite » (bloqué par 6), une ligne de révision.
- `README.md` : une phrase dans la section du relevé, pour dire que l'onglet « Consommation » donne le quota de la semaine en points de fenêtre.
- `docs/agents/codebase-map.md` : une entrée « Quota de la semaine » dans le commit final de `/build`, avec ce que `grep` ne donne pas : `variations.jsonl` est lu avec `seven_day`, la règle de la semaine non mesurable, et le fait que la source du total (cette semaine ou précédente) se lit dans la ligne.

## Découpage en tranches

| # | Tranche | Dépend de | Touche |
|---|---|---|---|
| 01 | `semaine.py` + `tests/test_semaine.py` : le calcul, de bout en bout, jusqu'à la ligne mise en forme | — | `src/quotasynch/semaine.py`, `tests/test_semaine.py` |
| 02 | L'étiquette de l'onglet « Consommation » | 01 | `src/quotasynch/gui.py` |
| 03 | Docs : `CONTEXT.md`, `prd.md`, `README.md` | — | fichiers `.md` seuls |

Les tranches 01 et 03 se lancent en parallèle (aucun fichier commun) ; la 02 attend la 01. Chaque tranche passe `uv run poe check` avant son commit. La carte du code se met à jour dans le commit final.

## Décisions de test

- Le calcul s'observe à l'interface publique `semaine.estimation` : on écrit des lignes dans `variations.jsonl` d'une `Machine` (`tests/conftest.py`, horloge fixe `NOW`, le 26 octobre 2026 à 10:01 ; prévoir des fins de semaine cohérentes avec elle) puis on lit la ligne rendue, comme `tests/test_consommation.py`. Pas de test fonction par fonction.
- Les cas qui portent la règle :
  - une semaine à une fenêtre (83 points, hebdomadaire de 0 à 7 %) → fourchette large, repli sur le total précédent s'il existe, sinon « total inconnu » ;
  - une semaine complète à pourcentages cohérents → total et marge attendus, source « mesuré cette semaine » ;
  - **le total se resserre** : ajouter une variation ne peut pas élargir la fourchette ;
  - une variation sans `five_hour` apporte son `w` sans toucher `S` ;
  - une baisse du pourcentage de fenêtre n'apporte rien (session inactive) ;
  - une fenêtre qui commence avant le début de la semaine → semaine non mesurable ;
  - une intersection vide → semaine non mesurable, repli sur la précédente ;
  - semaine tout juste commencée (aucune variation, horloge après la fin de la dernière) → consommation 0, total précédent ;
  - aucune variation → `None` ; ligne illisible ou sans limite → ignorée ;
  - arrondi à la dizaine, séparateur de milliers, formes de la ligne (mesuré / précédente / inconnu).
- `gui.py` n'est pas testé automatiquement.

## Hors-scope

- La commande `status` (elle lit les relevés, pas les variations) et l'export.
- Des seuils réglables dans `config.toml` : `MARGE` et `LARGEUR_MAX` restent des constantes.
- Séparer la consommation selon le modèle (Opus, Sonnet) : un total unique par semaine.
- Récupérer de la consommation que la statusline n'a pas vue (panneau VS Code sans « Use Terminal »).
- Des graphiques, une prévision de fin de semaine, une alerte.

## Questions ouvertes

- **Arrondi ou troncature** du pourcentage entier : `MARGE = 1` couvre les deux au prix de fourchettes deux fois plus larges qu'avec une demi-unité, et centre l'estimation à ± 0,5 point près si la valeur est tronquée. À trancher avec des données : un pourcentage de fenêtre vu plusieurs fois à des instants proches du même `S` ne le dit pas ; seul un cumul sur plusieurs semaines le montrera.
- **Stabilité du total** d'une semaine à l'autre : seules 8 variations existent. Après deux à trois semaines, comparer les totaux finals ; s'ils bougent de plus de leur marge, la reprise de la semaine précédente (règle 7) est trop optimiste et il vaut mieux afficher « total inconnu » plus tôt.
- **Le total dépend-il du modèle utilisé** ? Si oui, une intersection vide deviendra fréquente et c'est le signal à surveiller.
- **Fenêtre à cheval sur la remise à zéro** (règle 6) : la semaine est écartée en entier, ce qui est sûr mais peut faire perdre une semaine. Si cela arrive souvent, séparer la consommation de cette fenêtre avant et après `resets_at` demande une variation vue de chaque côté.
