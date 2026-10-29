# QuotaSynch

Un petit outil Windows qui démarre les fenêtres de quota de Claude Code à des heures fixes, en envoyant un message minimal à ces heures.

## Vocabulaire

**Fenêtre** :
Une période de 5 h de quota de l'abonnement, qui démarre au premier message envoyé à Claude Code.
_À éviter_ : session, période, cycle

**Ancrage** :
Un envoi de message minimal à une heure choisie, pour qu'une fenêtre démarre à cette heure.
_À éviter_ : ping, réveil, déclenchement

**Heure d'ancrage** :
L'heure du jour à laquelle un ancrage est prévu.
_À éviter_ : horaire, créneau

**Rattrapage** :
L'envoi d'un ancrage manqué dès que le PC redevient disponible, quel que soit le retard.
_À éviter_ : reprise, retry

**Saut** :
Un ancrage non envoyé parce qu'une fenêtre est déjà ouverte au moment où il devait partir.
_À éviter_ : ignoré, annulé

**Journal** :
Le fichier qui garde une ligne par ancrage : heure prévue, heure réelle, résultat.
_À éviter_ : log, historique, trace

**Heure prévue** :
La dernière heure d'ancrage inférieure ou égale à l'instant où l'ancrage s'exécute, déduite de la configuration.
_À éviter_ : heure cible, heure planifiée

**Retard** :
L'écart entre l'heure réelle et l'heure prévue d'un ancrage.
_À éviter_ : décalage, latence

**Instantané** :
Le dernier état des limites de quota, écrit par la statusline de Claude Code dans un fichier local, que le relevé lit.
_À éviter_ : snapshot, cache

**Relevé** :
Le pourcentage de quota consommé lu à un instant, avec l'heure de fin de la fenêtre : une ligne du fichier des relevés.
_À éviter_ : mesure, échantillon

**Variation** :
Un changement de l'instantané, consigné par la statusline avec son heure à la seconde près : une ligne du fichier des variations.
_À éviter_ : historique, événement, delta

**Point non daté** :
Un point de fenêtre consommé dont on ne peut pas dire à quelle heure, parce que l'observation précédente date de plus de 30 min : il est compté à part, jamais réparti sur des heures.
_À éviter_ : point estimé, point lissé

**Interface** :
L'écran `tkinter` ouvert par `quotasynch gui`, où l'on règle les heures d'ancrage et où l'on lit le journal.
_À éviter_ : fenêtre (le mot désigne la période de quota), GUI, application
