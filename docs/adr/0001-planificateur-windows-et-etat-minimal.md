# Le Planificateur de tâches Windows déclenche, un fichier d'état évite les doublons

Les ancrages sont des déclencheurs d'une tâche du Planificateur de tâches Windows, avec rattrapage natif (`StartWhenAvailable`) et réveil du PC optionnel. À chaque exécution, le programme lit la date du dernier envoi dans un petit fichier d'état et fait un saut si une fenêtre est déjà ouverte : plusieurs ancrages manqués ne produisent ainsi qu'un seul message au réveil.

On a écarté une tâche qui se déclenche toutes les 5 min avec un script qui décide seul : 288 lancements par jour et du code de planification à écrire, contre l'exigence « léger » du projet. À rouvrir si le rattrapage natif se révèle peu fiable en conditions réelles.

Le fichier d'état ne contient que la date du dernier envoi. Le journal des envois (heure prévue, heure réelle, résultat) est une autre fonctionnalité et ne s'y greffe pas.
