# Proposition Agile : Dashboard d'Enquête & Système d'Export ODK

Ce document présente la stratégie de développement pour l'interface de gestion des enquêtes basée sur ODK Central, découpée en plusieurs sprints de deux/trois semaines.

## 📅 Sprint 3+ : Pilotage & Gestion des Données (Fondations)

**Objectif :** Permettre aux utilisateurs de suivre l'avancement, de consulter les données et de corriger les erreurs via Enketo.

### User Stories

1. **US 1 - KPIs & Monitoring :** En tant que *user|admin|Manager*🚀️ , je veux voir le nombre total de soumissions et un graphique de progression quotidienne sur le dashboard pour suivre l'activité du terrain.
2. **US 2 - Consultation Tabulaire :** En tant que *user|admin|Manager*, je veux visualiser l'ensemble des soumissions dans un tableau interactif (recherche, filtres) pour valider la qualité des données.
3. **US 3 - Correction via Enketo :** En tant que *user|admin|Manager*, je veux pouvoir ouvrir une soumission spécifique directement dans Enketo depuis le tableau pour corriger des erreurs de saisie.
4. **US 4 - Automatisation des Liens :** En tant que *user|admin|Manager*, je veux que des liens de collecte (unique et multiple) soient générés par défaut pour chaque enquête afin de faciliter leur diffusion.
5. **US 5 - Intégration et Déploiement :** En tant que *développeur*, je veux installer et configurer l'environnement de développement et de production, y compris l'intégration avec Enketo, pour démarrer le projet.

---

## 📅 Sprint 4 : Exports Avancés & Visualisation SIG

**Objectif :** Fournir des outils d'extraction de données complexes (multimédia, SIG) et une analyse spatiale.

### User Stories

6. **US 6 - Export Tabulaire Intelligent (Excel/CSV) :** En tant que *user|admin|Manager*, je veux exporter les données en choisissant d'inclure les labels (multi-langues) et en nettoyant les préfixes de groupes pour obtenir un fichier directement exploitable.
7. **US 7 - Export Multimédia Simple (ZIP) :** En tant que *user|admin|Manager*, je veux télécharger un ZIP où les photos sont renommées (`nom_question_index`) pour faciliter le classement des preuves terrain.
8. **US 8 - Export Cartographique (SHP) :** En tant qu'expert SIG, je veux exporter les données géoréférencées au format Shapefile pour les intégrer dans mes outils professionnels (QGIS, ArcGIS).
9. **US 9 - Vue Carte Interactive :** En tant que *user|admin|Manager*, je veux visualiser mes points/traces/formes sur une carte avec une gestion de couches par question géo pour analyser la répartition spatiale.

---

## 📅 Sprint 5 : Amélioration de la Structure d'Export

**Objectif :** Organiser les exports multimédia de manière structurée pour une utilisation simplifiée.

### User Stories

10. **US 10 - Organisation Avancée de l'Export ZIP :** En tant que *user|admin|Manager*, je veux un export ZIP structuré avec :
    * Un dossier pour chaque feuille de données (principale et répétitions).
    * Dans chaque dossier de feuille, un sous-dossier par question contenant des pièces jointes.
    * Les fichiers de pièces jointes renommés selon le format `nom_de_la_question_index_de_ligne`.
    * Le nom du fichier de la pièce jointe remplaçant la valeur originale dans les données exportées pour un référencement facile.

---

## 🛠 Défis Techniques & Solutions

### 1. Mapping Dynamique des Labels (XLSForm)

* **Défi :** ODK Central renvoie des noms techniques (ex: `bat/photo_1`). L'utilisateur veut les labels (ex: "Photo du bâtiment").
* **Solution :** Parser le fichier de définition (`.xml` ou `.xlsx`) pour créer un dictionnaire de correspondance. Cachez ce dictionnaire dans Redis ou une DB pour éviter de le recalculer à chaque export.

### 2. Performance des Exports Volumineux (ZIP & SHP)

* **Défi :** La compression de milliers de photos ou le traitement géospatial lourd risque de causer des Timeouts HTTP.
* **Solution :** Implémenter un système de **Background Jobs** (ex: Celery ou RQ en Python). L'utilisateur lance l'export et reçoit une notification de téléchargement une fois le fichier prêt.

### 3. Contraintes du Format Shapefile

* **Défi :** Le format `.dbf` limite les noms de colonnes à 10 caractères et les fichiers peuvent être corrompus si l'encodage n'est pas UTF-8.
* **Solution :** Utiliser la librairie `Fiona` ou `Geopandas` pour gérer la troncature intelligente des noms de colonnes et assurer la compatibilité SIG.

### 4. Transformation de Données & Structuration (ZIP)

* **Défi :** L'US 10 exige de renommer les médias et de modifier en temps réel leurs références dans les fichiers CSV/Excel pour qu'ils pointent vers les nouveaux chemins. La gestion des hiérarchies (repeats) multiplie cette complexité et la pression sur les ressources (RAM).
* **Solution :** Implémenter un moteur de transformation de données (ETL) traitant les lignes et fichiers en parallèle. Utiliser le *streaming* pour la génération du ZIP afin d'éviter les saturations de mémoire sur les exports de plusieurs Go.

---

## 💡 Recommandations Stratégiques

1. **Moteur d'Export Découplé :** Développez un service d'exportation indépendant du frontend. Cela permet de faire évoluer les formats (ex: ajouter du GeoJSON ou du PDF) sans impacter l'interface.
2. **Gestion Multi-langue :** Prévoyez dès le début une option dans le modal d'export pour choisir la langue (`label::Français`, `label::English`) basée sur les colonnes disponibles dans le XLSForm original.
3. **UX de Téléchargement :** Pour les pièces jointes, proposez une barre de progression réelle au lieu d'un simple loader tournant, car ces fichiers peuvent atteindre plusieurs Go.
4. **Enketo Edit Integration :** Assurez-vous d'utiliser l'API `submission/edit` d'ODK Central pour garantir que les modifications ne créent pas de nouvelles instances mais mettent bien à jour les existantes.
