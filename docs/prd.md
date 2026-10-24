# PRD — QuotaSynch

## Problème

Un abonné Claude Pro travaille le matin, l'après-midi et le soir. Son quota se renouvelle par fenêtres de 5 h qui démarrent à son premier message : il ne choisit donc pas l'heure à laquelle elles commencent, et ne sait pas quand il retrouvera du quota. Quand le quota est épuisé, il attend, sans pouvoir prévoir combien de temps. Son contournement actuel est d'attendre et de constater après coup. Il n'a aucune donnée sur la part de quota qu'il consomme réellement par fenêtre.

## Acteurs

Par ordre de gravité de la douleur :

1. **L'auteur**, abonné Pro, sur un PC Windows portable mis en veille la nuit. Il est servi en premier.
2. **Les autres abonnés Claude Code** qui trouveront le dépôt GitHub open source et auront le même besoin.
3. À nommer : un troisième acteur concret n'a pas été identifié.

## Métriques de succès

1. Part des jours où la fenêtre de quota démarre à l'heure d'ancrage prévue, à ±10 min près, relevée avec l'heure de réinitialisation fournie par Claude Code. Point de départ : 0 %, rien n'est contrôlé aujourd'hui.
2. Nombre de fois par semaine où le quota atteint 100 % avant la fin de la fenêtre. Point de départ : à relever sur les deux premières semaines d'usage. Si la métrique 1 monte et que celle-ci ne baisse pas, l'outil fixe les heures sans réduire l'attente.

Si l'indicateur de quota n'est pas disponible chez l'auteur, seule la métrique 2 est conservée, mesurée à la main.

## Périmètre

- Choisir les heures de départ des fenêtres de quota.
- Envoyer à ces heures un message minimal, par l'abonnement.
- Rattraper un envoi manqué dès que le PC est de nouveau disponible.
- Garder une trace de chaque envoi, réussi ou en échec.
- Relever le pourcentage de quota consommé à intervalle régulier et juste avant la fin de chaque fenêtre.
- Exporter ces relevés pour analyse.

## Hors-périmètre

- **macOS et Linux** : aucun besoin exprimé.
- **Notifications téléphone et version cloud** : le PC portable suffit.
- **Calcul automatique des horaires** : il suppose les données de consommation, qui n'existent pas encore.
- **Analyse graphique poussée** : l'export suffit, l'analyse se fait ailleurs.
- **Contournement des limites d'usage** : l'outil ne fait que choisir l'heure de départ, il n'augmente pas le quota.

## Exigences non fonctionnelles

- Aucun processus résident ; chaque exécution dure moins de 60 s.
- Moins de 1 Mo de données conservées par mois.
- Les envois passent par l'abonnement, jamais par une clé API : 0 appel facturé à l'API.
- Tout reste local ; aucune conversation n'est lue ni stockée.
- Fonctionne sur Windows 10 et 11, sur batterie comme sur secteur.
- Un envoi manqué est rattrapé au prochain réveil, sans plafond de retard, et le retard est consigné.
- Aucun secret ni donnée personnelle dans le dépôt, publié sous licence MIT.

## Contraintes données

- Abonnement Pro ; Claude Code 2.1.x déjà installé et connecté.
- Python 3.13 et `uv` déjà présents sur la machine de l'auteur.
- Projet solo, très petit, dépôt public sur GitHub.
- Risque : l'indicateur de quota (`rate_limits`) n'est pas une interface garantie. Il peut être absent ou changer de format selon la version.

## Fonctionnalités

### Lot 1 — MVP · gelé

1. **Ancrage planifié** `ancrage-planifie` — l'auteur choisit ses heures de départ et le message part à chacune, avec rattrapage si le PC était indisponible.
2. **Journal des envois** `journal-envois` — chaque envoi laisse une trace de l'heure prévue, de l'heure réelle et du résultat · bloqué par 1

### Ensuite · ordre indicatif, non gelé

3. **Relevé du quota** `releve-quota` — le pourcentage consommé est relevé à intervalle régulier et avant la fin de chaque fenêtre · bloqué par 1
4. **Export des relevés** `export-releves` — les relevés sortent dans un format ouvrable ailleurs · bloqué par 3

### Plus tard · non ordonné

5. **Calcul automatique des horaires** `horaires-auto` — les heures de départ se proposent d'après les données récoltées.

## Questions ouvertes

- Le troisième acteur : à nommer par l'auteur.
- Le format exact et la disponibilité de `rate_limits` chez l'auteur : à vérifier sur sa version de Claude Code, avant la fonctionnalité 3.

## Révisions

| Date | Ce qui change | Pourquoi |
| ---- | ------------- | -------- |
| 2026-10-24 | Création | — |
