# spec: consommation-horaire — Consommation par heure

**Statut :** Implemented
**Enjeu :** 1
**Mode :** Direct — une session, trois tranches, Enjeu 1 (lecture seule de données locales), une PR lisible.
**Epic :** https://github.com/VFahet/QuotaSynch/issues/14

## Énoncé du problème

L'auteur veut savoir à peu près à quel moment de la journée il consomme son quota, pour choisir ses heures d'ancrage. Les relevés toutes les 15 min ne le disent pas bien : la consommation d'un long intervalle ne peut pas être répartie sans inventer. Une moyenne naïve mentirait de deux façons : en étalant des points sur des heures où rien ne s'est passé, et en affichant 0 là où l'on ne sait rien.

## Solution

Un onglet « Consommation » dans l'interface, calculé à partir des variations que la statusline consigne à la seconde près. Il montre deux tableaux. **Heures de la journée** : pour chaque heure, les points de fenêtre consommés en moyenne par jour. **Fenêtres** : pour chaque fenêtre de 5 h, le pourcentage le plus haut atteint, l'heure du 100 % et la part de la consommation qu'on a pu dater. Une consommation qu'on ne peut pas dater n'est jamais répartie : elle est comptée à part, et sa part est affichée.

## User stories

1. En tant qu'auteur, je veux **voir pour chaque heure de la journée les points de fenêtre consommés en moyenne par jour, avec la période couverte et la part non datée**, afin de savoir à quelles heures je consomme sans être trompé par les trous.
2. En tant qu'auteur, je veux **voir pour chaque fenêtre le pourcentage le plus haut atteint, l'heure du 100 % et la part datée**, afin de savoir quelles fenêtres je vide et quand.
3. En tant qu'auteur, je veux **retrouver ces deux tableaux dans un onglet « Consommation » de l'interface, à côté des ancrages**, afin de les consulter sans commande.

## Décisions d'implémentation

Vocabulaire : [CONTEXT.md](../../CONTEXT.md) — **variation**, **instantané**, **fenêtre**, **point non daté**. Source : [ADR-0002](../adr/0002-releve-du-quota-par-la-statusline.md).

- **Source** : `variations.jsonl` seul, dans `%LOCALAPPDATA%\QuotaSynch\`, écrit par la statusline : `heure` (secondes depuis 1970) et `rate_limits` tel quel. Seule `rate_limits.five_hour` sert ; une ligne sans elle, ou illisible, est ignorée. Les relevés restent pour `status`. *(tranché par défaut)*
- **Nouveau module de calcul**, sans `tkinter`, testé : lit les variations par `jsonl` et rend deux listes de lignes déjà mises en forme pour l'affichage, comme `interface.journal_rows`. `System` gagne le chemin du fichier des variations. Les heures sont converties en heure locale de leur propre date (`System.local_time`), pour qu'un changement d'heure ne décale pas l'historique ; corrigé à la revue, le fuseau fixe de l'horloge le décalait d'une heure.
- **Fenêtre** : les variations se groupent par heure de fin (`resets_at`) ; le début est `fin − 5 h`.
- **Règle de datation** (décision de l'utilisateur) : dans une fenêtre, on suit le plus haut pourcentage atteint et l'heure à laquelle il a été vu pour la dernière fois, en partant de 0 au début de la fenêtre. Une variation plus basse est ignorée : une session inactive renvoie un pourcentage ancien. Une variation plus haute apporte `pct − plus haut` points. Ces points sont **datés** à l'heure d'horloge de la variation si la précédente observation date de **30 min** au plus. Sinon, ils sont **non datés**. Une variation égale au plus haut met à jour l'heure de la dernière observation.
- **Moyenne par heure** (décision de l'utilisateur) : le total des points datés dans cette heure divisé par le nombre de jours de la période. La période va du jour de la première variation à aujourd'hui inclus. Une heure qui n'a reçu aucun point daté affiche « — », jamais 0. Le pied du tableau donne la période, le nombre de jours et la part non datée en pourcentage du total des points.
- **Ligne de fenêtre** : début et fin (`jj/mm HH:MM`), plus haut pourcentage, heure du premier 100 % ou « — », part datée en pourcentage des points de la fenêtre. Les plus récentes d'abord, 50 au plus. *(tranché par défaut)*
- **Arrondis** : les moyennes à une décimale, les parts en pourcentage entier. *(tranché par défaut)*
- **Interface** (décision de l'utilisateur) : un `ttk.Notebook` à deux onglets, « Ancrages » (l'écran actuel, inchangé) et « Consommation » (les deux tableaux, un message quand il n'y a encore aucune variation). Construite **sans design system**, avec les widgets `ttk` déjà utilisés. Le contenu se calcule à l'ouverture. *(tranché par défaut)*
- **Pas de séparation semaine et week-end, pas de pourcentage de semaine** : un point de semaine représente trop de consommation pour qu'on le date. *(tranché par défaut)*
- **Exigences non fonctionnelles du PRD** : aucun processus résident (le calcul tourne à l'ouverture de l'interface) ; tout reste local ; aucune dépendance tierce. Volume de `variations.jsonl` : environ 150 octets par variation, jusqu'à 1,5 Mo par mois en très gros usage, au-dessus du plafond de 1 Mo : écart accepté et consigné au PRD.
- **PRD** (décision de l'utilisateur) : une ligne de fonctionnalité `consommation-horaire`. Ce qui était exclu sous « Analyse graphique poussée » devient « Graphiques et analyses poussées » : des tableaux simples dans l'interface entrent.

## Décisions de test

- Le calcul s'observe à l'interface publique du nouveau module : on écrit des lignes dans `variations.jsonl` d'une `Machine` (`tests/conftest.py`, horloge fixe `NOW`), puis on lit les lignes rendues, comme `tests/test_interface.py` le fait pour `journal_rows`. Pas de test fonction par fonction.
- Les cas qui portent la règle : une hausse à moins de 30 min de l'observation précédente est datée, au-delà elle est non datée ; le premier pourcentage d'une fenêtre est daté seulement s'il est vu dans les 30 min de son début ; une baisse est ignorée et ne date rien ; une valeur égale prolonge l'observation ; une heure sans point daté rend « — » ; une ligne illisible ou sans `five_hour` est ignorée ; aucune variation rend des tableaux vides.
- `gui.py` n'est pas testé automatiquement, comme aujourd'hui.

## Hors-scope

- Les graphiques, la semaine, la séparation des jours.
- L'export (fonctionnalité 4) et le calcul automatique des horaires (fonctionnalité 5).
- L'usage hors terminal, qui n'apparaît qu'en points non datés.

## Questions ouvertes

- Les seuils (30 min, une décimale) se règlent avec de vraies données, après une à deux semaines : l'auteur tranche.
- Si la part non datée dépasse durablement 50 %, la vue par heure perd son sens : à revoir avec l'auteur.
