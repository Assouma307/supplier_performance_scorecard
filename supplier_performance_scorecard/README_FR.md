# Évaluation des performances et des risques fournisseurs — Odoo 19 Community

## Fonctionnalités
- Scorecards par fournisseur, société et période.
- Indicateurs de ponctualité des réceptions et de complétude des commandes d’achat.
- Score global pondéré, fiabilité des données et niveau de risque.
- Historique des évaluations et génération en lot.
- Risk Alerts, activités de suivi et clôture des alertes.
- Tableau de bord par société, indicateurs clés, graphiques et analyses.

## Installation
1. Copier `supplier_performance_scorecard` dans le répertoire des modules personnalisés.
2. Redémarrer Odoo et mettre à jour la liste des applications.
3. Installer le module. Choisir le français (`fr_FR`) dans la langue de l’utilisateur pour charger les traductions.

## Limite du calcul
La ponctualité utilise la date prévue actuellement enregistrée sur chaque réception terminée. La complétude utilise les quantités actuellement reçues sur les commandes d’achat. Une modification ultérieure peut influencer une nouvelle évaluation d’une période passée ; chaque évaluation enregistrée conserve son résultat et ses notes de calcul.
