# spec: releve-quota — Relevé du quota

**Statut :** Draft
**Enjeu :** 1
**Mode :** <rempli à l'arbitrage>

## Énoncé du problème

L'auteur ne sait pas quelle part de son quota il consomme réellement par fenêtre. Usage Monitor for Claude affiche le pourcentage actuel, mais ne garde rien : une fois la fenêtre réinitialisée, le chiffre est perdu. L'auteur ne peut donc ni savoir si ses fenêtres atteignent 100 % avant leur fin, ni vérifier à quelle heure elles ont réellement démarré.

## Solution

Une ligne ajoutée à la statusline de l'auteur écrit, à chaque mise à jour, l'état des limites de quota dans un fichier local, l'instantané. Une seconde tâche du Planificateur lance `quotasynch releve` toutes les 15 min : si l'instantané est plus récent que le dernier relevé, elle ajoute au fichier des relevés une ligne avec le pourcentage de la fenêtre, celui de la semaine et leurs heures de fin. Rien n'est écrit quand aucune session n'a été ouverte entre deux passages. `quotasynch status` montre le dernier relevé.

## User stories

1. En tant qu'auteur, je veux **une ligne à ajouter à ma statusline qui écrit l'instantané**, afin de ne rien changer d'autre à ma configuration et de n'écrire que les limites de quota.
2. En tant qu'auteur, je veux **que `quotasynch releve` ajoute un relevé du pourcentage de la fenêtre et de la semaine, avec leurs heures de fin**, afin de garder l'historique de ma consommation.
3. En tant qu'auteur, je veux **qu'aucune ligne ne s'écrive quand l'instantané est absent, illisible, déjà relevé ou sans limites**, afin que le fichier ne contienne que des relevés utiles.
4. En tant qu'auteur, je veux **que `install` pose une tâche qui relève toutes les 15 min, et que `uninstall` la retire**, afin que le dernier relevé avant la fin d'une fenêtre date d'au plus 15 min sans que je lance quoi que ce soit.
5. En tant qu'auteur, je veux **voir le dernier relevé dans `quotasynch status`**, afin de vérifier d'un coup d'œil que la chaîne fonctionne.

## Décisions d'implémentation

Architecture : [ADR-0002](../adr/0002-releve-du-quota-par-la-statusline.md) (la source est l'instantané de la statusline, pas l'API), qui nuance l'[ADR-0001](../adr/0001-planificateur-windows-et-etat-minimal.md). Vocabulaire : [CONTEXT.md](../../CONTEXT.md) — **instantané** et **relevé** ; le mot « fenêtre » désigne la période de quota.

- **Source** : `rate_limits.five_hour` et `rate_limits.seven_day` du JSON que Claude Code envoie à la statusline (`used_percentage` de 0 à 100, `resets_at` en secondes epoch), documentés dans [la page statusline](https://code.claude.com/docs/en/statusline). Aucun appel réseau, aucun jeton lu, aucun message envoyé : coût de quota nul.
- **Instantané** : fichier `snapshot.json` dans `%LOCALAPPDATA%\QuotaSynch\`, qui ne contient que l'objet `rate_limits` — jamais le reste du JSON de la statusline, qui porte le dossier de travail et le chemin de la conversation. Il est écrit dans un fichier temporaire puis renommé, pour qu'une lecture ne tombe pas sur un fichier à moitié écrit.
- **Intégration à la statusline** (décision de l'utilisateur) : QuotaSynch ne modifie jamais `settings.json`. Le README donne la ligne à ajouter à une statusline existante, pour Git Bash (`jq`) — celle de l'auteur — et lue sur stdin une seule fois. Les autres interpréteurs ne sont pas couverts.
- **Relevé** : fichier `releves.jsonl` dans `%LOCALAPPDATA%\QuotaSynch\`, une ligne JSON par relevé, en ajout seul, à clés françaises qu'on ne renomme pas sans migrer : `heure` (date ISO 8601 avec fuseau), `fenetre_pct`, `fenetre_fin` (ISO 8601 avec fuseau), `semaine_pct`, `semaine_fin`, `age` (secondes entre l'écriture de l'instantané et le relevé). Une limite absente de l'instantané donne `null` pour ses deux champs. Une ligne illisible est ignorée à la lecture.
- **Quand écrire** : un relevé n'est écrit que si l'instantané existe, se lit, contient au moins une des deux limites, et est plus récent que le dernier relevé ; sinon `releve` ne fait rien et sort avec le code 0. Il ne lit jamais la configuration : il ne dépend pas de `config.toml`.
- **Tâche du Planificateur** : une tâche à part, `QuotaSynch-releve`, avec un déclencheur répété toutes les 15 min, sans réveil du PC et sans rattrapage (un relevé manqué n'a rien à rattraper : l'instantané reste le même). Poser, retirer et savoir si elle existe suivent le code de la tâche d'ancrage. `install` pose les deux tâches ; `uninstall` retire les deux ; l'« Enregistrer » de l'interface, qui réutilise `install`, pose donc aussi la seconde.
- **`status`** : une ligne s'ajoute, `dernier relevé : fenêtre <n> %, semaine <n> % (il y a <n> min)`, ou `dernier relevé : aucun`. *(tranché par défaut)*
- **Échec d'écriture du relevé** : `releve` écrit un avertissement sur stderr et sort avec le code 1 ; aucun envoi n'est en jeu. *(tranché par défaut)*
- **Pas de commande de lecture, pas d'interface** : la lecture passe par `status` et par le fichier. L'interface ne change pas. *(tranché par défaut)*
- **Exigences non fonctionnelles du PRD qui portent ici** : aucun processus résident ; moins de 60 s par exécution (`releve` lit un fichier, la tâche est limitée à 1 min) ; moins de 1 Mo de données par mois (au plus 96 lignes par jour d'environ 150 octets, soit 430 Ko par mois en usage continu, bien moins avec la règle de nouveauté) ; tout reste local ; aucune conversation lue ni stockée (l'instantané ne garde que `rate_limits`) ; aucun secret ni donnée personnelle dans le dépôt ; aucun appel à l'API, facturé ou non.
- **Contribution aux métriques** : `fenetre_fin` moins 5 h donne le démarrage réel de la fenêtre, à comparer à l'heure d'ancrage prévue : c'est la métrique 1 (±10 min), enfin mesurable. Les relevés qui atteignent 100 % avant la fin de la fenêtre donnent la métrique 2.
- **Limites connues** : pas de relevé tant qu'aucune session Claude Code n'est ouverte ; l'usage sur claude.ai ou Claude Desktop ne bouge le pourcentage qu'à la prochaine réponse reçue dans Claude Code, donc le relevé sous-estime alors la consommation (l'auteur en a une petite part). Le pourcentage peut aussi dériver entre plusieurs terminaux ouverts, d'après des signalements communautaires.
- **Aucune interface nouvelle** : pas de question de design system.

## Décisions de test

- Le comportement s'observe à l'interface de la commande, comme pour `ancrage-planifie` et `journal-envois` : `releve`, `status`, `install` et `uninstall` avec un `System` aux doubles (horloge, lanceur de processus, chemins), qui prolonge `tests/test_run.py`, `tests/test_status.py` et `tests/test_install.py`. On vérifie le contenu de `releves.jsonl` après `releve` : un relevé avec les deux limites, avec une seule, et l'absence de ligne pour un instantané absent, illisible, vide de limites ou déjà relevé.
- La règle de nouveauté se teste avec une horloge injectée et des dates de modification posées sur l'instantané.
- La tâche se teste au XML, comme `scheduler.build_task_xml` : un déclencheur répété toutes les 15 min, sans réveil, sans rattrapage, avec la limite d'une minute ; `install` et `uninstall` appellent `schtasks` pour les deux noms de tâche.
- Pas de test automatique de la ligne de statusline, qui vit dans la configuration de l'auteur. **Vérification manuelle, une seule fois, par l'auteur** : ajouter la ligne à sa statusline, ouvrir une session Claude Code, voir apparaître `snapshot.json` avec le seul objet `rate_limits`, lancer `quotasynch releve` puis `quotasynch status`, et contrôler la tâche `QuotaSynch-releve` dans le Planificateur. Elle ne lance aucun envoi.

## Hors-scope

- L'endpoint `/api/oauth/usage` et la lecture du jeton OAuth ; `claude -p` comme source.
- Modifier `settings.json` ou fournir une statusline complète.
- L'export des relevés (`export-releves`), le calcul automatique des horaires, l'affichage des relevés dans l'interface, tout graphique.
- Une alerte, de rythme ou autre : Usage Monitor for Claude les fait déjà.
- La limite `spend_limit` des passerelles d'entreprise et les limites par modèle.
- Rotation ou purge des relevés.
- Les interpréteurs de statusline autres que Git Bash.

## Questions ouvertes

- **Le contenu réel de `rate_limits`** chez l'auteur reste à constater sur une vraie session : la recherche s'appuie sur la documentation, non sur un essai. Si un champ manque, l'auteur le signale avant la tranche concernée.
- **Les hooks** n'ont pas été examinés comme source possible : à ouvrir seulement si la statusline s'avère insuffisante.
