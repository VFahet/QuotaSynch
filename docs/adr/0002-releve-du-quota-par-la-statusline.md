# Le relevé du quota lit un instantané écrit par la statusline, pas l'API

Le pourcentage de quota consommé n'est exposé officiellement que par la statusline de Claude Code (`rate_limits`). QuotaSynch ne le demande pas à l'API : la statusline de l'auteur écrit l'objet `rate_limits` dans un fichier local, l'instantané, et une seconde tâche du Planificateur de tâches, toutes les 15 min, en tire un relevé quand l'instantané a changé. QuotaSynch ne modifie jamais `settings.json` : la documentation donne la ligne à ajouter à sa statusline.

On a écarté l'endpoint `/api/oauth/usage`, qui donnerait un relevé continu sans session, parce qu'il n'est pas documenté (« may change without notice »), qu'il oblige à lire et à renouveler le jeton OAuth de l'utilisateur, et que le dépôt est public. On a écarté `claude -p`, qui consommerait du quota à chaque lecture et pourrait ouvrir une fenêtre. À rouvrir si les trous du relevé gênent l'analyse.

## Conséquences

- Il n'y a pas de relevé tant qu'aucune session Claude Code n'est ouverte, et un usage sur claude.ai ou Claude Desktop ne bouge l'instantané qu'à la prochaine réponse reçue dans Claude Code.
- La seconde tâche lance environ 96 fois par jour un programme qui lit un fichier et n'écrit rien quand rien n'a changé. L'[ADR-0001](0001-planificateur-windows-et-etat-minimal.md) écartait une tâche toutes les 5 min dont le script décidait seul de la planification : ici le script ne décide d'aucun envoi, et les ancrages gardent leurs déclencheurs natifs.
