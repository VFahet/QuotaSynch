# Source du relevé du quota

Question : d'où `releve-quota` peut-il lire le pourcentage consommé de la fenêtre de 5 h, sans processus résident et à un coût de quota nul ou minimal ? Établi le 2026-10-28 sur Claude Code 2.1.312, abonnement Pro, Windows 11.

## Verdicts

| # | Hypothèse | Verdict |
|---|---|---|
| H1 | Claude Code expose le % de la fenêtre de 5 h et son heure de réinitialisation | **Confirmée** (statusline) |
| H2 | La statusline peut alimenter un fichier lu ailleurs | **Confirmée** dans son principe, non testée |
| H3 | Une source officielle existe hors session | **Infirmée** : aucune source officielle trouvée |
| H4 | La statusline de l'auteur est libre | **Infirmée** : il en a déjà une |
| H5 | Les hooks reçoivent le quota | **Non examinée** |
| H6 | L'interface est stable | **Partielle** : documentée, mais des défauts sont signalés |

## H1 — le pourcentage et le reset existent

Source primaire : [Customize your status line](https://code.claude.com/docs/en/statusline).

- `rate_limits.five_hour.used_percentage` et `rate_limits.seven_day.used_percentage` : « Percentage of the 5-hour or 7-day rate limit consumed, from 0 to 100 ».
- `rate_limits.five_hour.resets_at` et `rate_limits.seven_day.resets_at` : « Unix epoch seconds when the 5-hour or 7-day rate limit window resets ».
- Présent « only for claude.ai Pro and Max subscribers [...] and only after the first API response in the session ». Chaque fenêtre « may be independently absent », et Claude Code l'abandonne une fois son `resets_at` passé.
- Cohérent avec la machine de l'auteur : `~/.claude/.credentials.json` indique `subscriptionType: pro`.

## H2 — la statusline peut alimenter un fichier

Même source.

- La commande reçoit le JSON sur stdin et affiche ce qu'elle imprime. Elle accepte n'importe quel script (« runs any shell script »), donc elle peut écrire un fichier d'instantané. Je ne l'ai pas essayé.
- Déclenchement : à chaque événement de la session, avec un anti-rebond de 300 ms ; en option, `refreshInterval` relance la commande toutes les N secondes (minimum 1) ; elle est aussi relancée quand une fenêtre atteint son `resets_at`. Un nouveau déclenchement annule le script en cours.
- Sous Windows : Git Bash s'il est installé, sinon PowerShell.
- **Limite structurante** : la statusline ne tourne que pendant une session Claude Code ouverte.

## H3 — hors session

Aucune source officielle.

- **Endpoint `https://api.anthropic.com/api/oauth/usage`** : lu par Usage Monitor for Claude et d'autres. Sa documentation le dit « undocumented internal endpoints [...] may change without notice ». Réponse : `five_hour.utilization` et `resets_at` (ISO 8601), `seven_day`, un tableau `limits`, des champs à nom de code. Les en-têtes requis et son coût en quota ne sont pas documentés. Il demande le jeton OAuth de `~/.claude/.credentials.json`, dont le `accessToken` est de courte durée (`expiresAt` à 13:31 le jour du relevé) : il faut le renouveler. **Je n'ai ni appelé l'endpoint ni lu le jeton.**
- **`claude -p` en `stream-json`** : un événement `rate_limit_event` existe d'après des sources communautaires, qui se contredisent sur son format (millisecondes ou secondes, fraction ou pourcentage) et sur son moment d'émission (limite atteinte ou approchée). Rien dans [le CLI reference](https://code.claude.com/docs/en/cli-reference) officiel. Une demande de fonctionnalité réclame ces données dans `--output-format json`, ce qui suggère qu'elles y manquent. Chaque lecture enverrait en outre un message, donc consommerait du quota et pourrait ouvrir une fenêtre.

## H4 — conflit de statusline

`~/.claude/settings.json` contient déjà une `statusLine` (bash et `jq`, qui affiche modèle, dossier, branche, coût, lignes). Il n'y a qu'une commande de statusline : un relevé devra s'y insérer sans la remplacer, en lisant stdin une seule fois.

## H5 — hooks

Non examinés. À vérifier si la statusline ne suffit pas.

## H6 — stabilité

La statusline est documentée avec un tableau de champs, donc c'est l'interface la plus sûre. Des issues signalent pourtant `rate_limits` parfois absent du JSON ([#45133](https://claudeissues.com/issue/45133-rate-limits-seven-day-five-hour-missing-from-statusline-json-input)) et un pourcentage qui dérive entre terminaux ouverts ([#75408](https://claudeissues.com/issue/75408-statusline-rate-limits-five-hour-used-percentage-drifts-across-concurrently-open)). Ce sont des sources communautaires, non vérifiées ici.

## Ce que cela change pour `releve-quota`

- La condition du PRD est levée : l'indicateur `rate_limits` existe chez l'auteur, avec un format documenté.
- Le relevé « à intervalle régulier et avant la fin de chaque fenêtre » est **garanti seulement pendant les sessions** si on s'appuie sur la source officielle. Hors session, il reste l'endpoint non documenté, fragile et lié au jeton OAuth.
- Décision à trancher au cadrage : instantané de la statusline seul (officiel, trous quand aucune session n'est ouverte), ou endpoint non documenté (continu, fragile), ou les deux.

## À vérifier à la main

- Qu'un script de statusline puisse écrire un fichier sous Windows, avec l'`input` lu une seule fois.
- Le contenu réel du JSON de la statusline chez l'auteur, après une première réponse.
- Le coût en quota d'un appel à `/api/oauth/usage`, et ses en-têtes.
