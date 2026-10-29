# QuotaSynch

Un petit outil Windows qui envoie un message minimal à Claude Code à des heures choisies, pour que les fenêtres de quota de 5 h démarrent à heures fixes. Rien ne tourne en continu : le Planificateur de tâches Windows lance l'outil aux heures d'ancrage, pendant moins d'une minute.

## Utilisation

Prérequis : Windows 10 ou 11, [`uv`](https://docs.astral.sh/uv/), Claude Code installé et connecté à un abonnement.

```
uv run quotasynch install     # crée la tâche planifiée
uv run quotasynch status      # tâche, configuration, dernier envoi
uv run quotasynch uninstall   # supprime la tâche
```

Par défaut, un message part chaque jour à 05:00, 10:01 et 15:02, et le PC est réveillé si Windows le permet. Sinon, l'envoi est rattrapé dès que le PC redevient disponible.

## Configuration

`%APPDATA%\QuotaSynch\config.toml` (facultatif ; relancer `install` après modification) :

```toml
anchors = ["05:00", "10:01", "15:02"]   # HH:MM, espacées d'au moins 5 h
model = "haiku"
message = "ok"
wake = true                              # réveiller le PC aux heures d'ancrage
```

Les envois passent par l'abonnement : `ANTHROPIC_API_KEY` est retirée de l'environnement de l'appel.

## Relevé du quota

Le relevé lit le pourcentage de quota que Claude Code transmet à la statusline : aucun appel réseau, aucun jeton lu. Pour l'alimenter, ajoutez ces deux lignes à votre statusline Git Bash, après `input=$(cat)` (`jq` doit être installé) :

```bash
qs="$LOCALAPPDATA/QuotaSynch"; tmp="$qs/instantane.$$.tmp"
{ mkdir -p "$qs" && printf '%s' "$input" | jq -c 'select(.rate_limits != null) | {rate_limits: .rate_limits}' > "$tmp" && [ -s "$tmp" ] && { cmp -s "$tmp" "$qs/instantane.json" || jq -c '{heure: (now | floor)} + .' "$tmp" >> "$qs/variations.jsonl"; true; } && mv -f "$tmp" "$qs/instantane.json"; rm -f "$tmp"; } >/dev/null 2>&1 || true
```

Elles écrivent l'instantané, sans rien afficher. Quand il change, elles ajoutent aussi une ligne à `variations.jsonl` : l'heure à la seconde près (`heure`, en secondes depuis 1970) et l'objet `rate_limits`. Ce fichier sert à savoir à quel moment le quota se consomme, plus finement que le relevé toutes les 15 min. Deux sessions ouvertes peuvent y alterner : une session restée inactive renvoie un pourcentage ancien, donc plus bas. Comme le pourcentage d'une fenêtre ne fait que monter, c'est le plus haut atteint qui compte. L'instantané ne garde que l'objet `rate_limits` : ni le dossier de travail, ni le chemin de la conversation. Tant que Claude Code n'a pas reçu de réponse, il n'y a pas de `rate_limits` et rien n'est écrit. QuotaSynch ne modifie jamais `settings.json`. La tâche `QuotaSynch-releve`, posée par `install`, lance `quotasynch releve` toutes les 15 min et n'ajoute une ligne que si l'instantané a été réécrit depuis le dernier relevé.

Limites :

- pas de relevé tant qu'aucune session Claude Code n'est ouverte ;
- l'usage sur claude.ai ou Claude Desktop ne fait bouger le pourcentage qu'à la prochaine réponse reçue dans Claude Code ;
- le panneau graphique de l'extension VS Code n'exécute pas la statusline : pour que ce que vous y faites soit relevé, activez « Use Terminal » (réglage `claudeCode.useTerminal`, dans Extensions > Claude Code) ou lancez `claude` dans le terminal intégré ;
- seul Git Bash est couvert : les autres interpréteurs de statusline ne le sont pas.

Les fichiers sont dans `%LOCALAPPDATA%\QuotaSynch\` : `instantane.json` (l'instantané), `variations.jsonl` (les variations, écrites par la statusline seule) et `releves.jsonl` (les relevés, une ligne JSON par relevé, ajoutée à la fin). Une ligne porte `heure`, `fenetre_pct`, `fenetre_fin`, `semaine_pct`, `semaine_fin` et `age` (secondes entre l'écriture de l'instantané et le relevé). `uv run quotasynch status` montre le dernier relevé.

## Développement

`uv run poe check` enchaîne formatage, lint, types et tests.

Licence MIT.
