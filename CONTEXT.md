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

**Interface** :
L'écran `tkinter` ouvert par `quotasynch gui`, où l'on règle les heures d'ancrage et où l'on lit le journal.
_À éviter_ : fenêtre (le mot désigne la période de quota), GUI, application
