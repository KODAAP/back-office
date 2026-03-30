### Corrélation entre Individual Form, Draft Form et Published Form Versions dans ODK Central

#### Architecture des Formulaires ODK

Dans l'API ODK Central, la gestion des formulaires suit un workflow structuré avec trois concepts principaux :

**1. Individual Form (Formulaire individuel)**
- Représente l'entité principale du formulaire avec un `xmlFormId` unique
- Contient les métadonnées de base : nom, version, état, dates de création/mise à jour
- Sert de conteneur pour les versions draft et published

**2. Draft Form (Formulaire brouillon)**
- Version de travail du formulaire accessible via `/projects/{projectId}/forms/{xmlFormId}/draft`
- Permet de tester et modifier le formulaire avant publication
- Possède un token de test spécifique pour les tests
- Peut être créé, modifié et supprimé sans affecter la version publiée
- Les attachments sont gérés séparément pour le draft

**3. Published Form Versions (Versions publiées)**
- Versions finalisées du formulaire accessibles via `/projects/{projectId}/forms/{xmlFormId}/versions`
- Immuables une fois publiées
- Utilisées pour la collecte de données réelle
- Chaque version publiée a un `publishedAt` timestamp et un `publishedBy` actor

#### Relations et Workflow

```
Individual Form
├── Draft Form (0 ou 1)
│   ├── Draft Token (pour tests)
│   ├── Draft Submissions
│   └── Draft Attachments
└── Published Versions (0 à N)
    ├── Version 1.0 (historique)
    ├── Version 1.1 (historique)
    └── Version actuelle
```

Le cycle de vie typique :
1. Création d'un formulaire → Draft automatiquement créé
2. Test et modification du Draft
3. Publication du Draft → Devient une version publiée
4. Le Draft peut être supprimé ou remplacé par une nouvelle version

### Endpoints Essentiels pour un MVP

#### **Gestion des Projets**
```
GET /v1/projects
POST /v1/projects
GET /v1/projects/{id}
PUT /v1/projects/{id}
```

#### **Gestion des Formulaires (Core)**
```
# Liste des formulaires
GET /v1/projects/{projectId}/forms

# Création d'un nouveau formulaire
POST /v1/projects/{projectId}/forms

# Détails d'un formulaire
GET /v1/projects/{projectId}/forms/{xmlFormId}

# Suppression d'un formulaire
DELETE /v1/projects/{projectId}/forms/{xmlFormId}
```

#### **Gestion des Drafts (Essentiel pour MVP)**
```
# Détails du draft
GET /v1/projects/{projectId}/forms/{xmlFormId}/draft

# Création/Mise à jour du draft
POST /v1/projects/{projectId}/forms/{xmlFormId}/draft

# Publication du draft
POST /v1/projects/{projectId}/forms/{xmlFormId}/draft/publish

# Suppression du draft
DELETE /v1/projects/{projectId}/forms/{xmlFormId}/draft
```

#### **Gestion des Versions Publiées**
```
# Liste des versions publiées
GET /v1/projects/{projectId}/forms/{xmlFormId}/versions

# Détails d'une version spécifique
GET /v1/projects/{projectId}/forms/{xmlFormId}/versions/{version}

# Définition XML d'une version
GET /v1/projects/{projectId}/forms/{xmlFormId}/versions/{version}.xml
```

#### **Gestion des Soumissions (Essential)**
```
# Liste des soumissions
GET /v1/projects/{projectId}/forms/{xmlFormId}/submissions

# Création d'une soumission
POST /v1/projects/{projectId}/forms/{xmlFormId}/submissions

# Détails d'une soumission
GET /v1/projects/{projectId}/forms/{xmlFormId}/submissions/{instanceId}

# Export CSV des soumissions
GET /v1/projects/{projectId}/forms/{xmlFormId}/submissions.csv.zip
```

#### **Gestion des Attachments (Optionnel pour MVP)**
```
# Liste des attachments
GET /v1/projects/{projectId}/forms/{xmlFormId}/draft/attachments
GET /v1/projects/{projectId}/forms/{xmlFormId}/attachments

# Upload d'un attachment
POST /v1/projects/{projectId}/forms/{xmlFormId}/draft/attachments/{name}

# Téléchargement d'un attachment
GET /v1/projects/{projectId}/forms/{xmlFormId}/attachments/{filename}
```

#### **Endpoints OpenRosa (Pour compatibilité mobile)**
```
# Liste des formulaires pour les clients mobiles
GET /v1/projects/{projectId}/formList

# Définition XML pour les clients mobiles
GET /v1/projects/{projectId}/forms/{xmlFormId}.xml

# Soumission via OpenRosa
POST /v1/projects/{projectId}/submission
```

#### **Authentification**
```
POST /v1/sessions (login)
DELETE /v1/sessions (logout)
GET /v1/users/current (utilisateur courant)
```

#### **Endpoints de Test (Recommandés pour MVP)**
```
# Test du draft avec token
GET /v1/test/{draftToken}/projects/{projectId}/forms/{xmlFormId}.xml
POST /v1/test/{draftToken}/projects/{projectId}/submission

# Soumissions de test
GET /v1/projects/{projectId}/forms/{xmlFormId}/draft/submissions
```

### Recommandations pour l'Implémentation MVP

1. **Commencer par les endpoints de base** : projets, formulaires, drafts
2. **Implémenter le workflow draft → publish** pour permettre les tests
3. **Ajouter la gestion des soumissions** pour la collecte de données
4. **Intégrer OpenRosa** pour la compatibilité mobile
5. **Reporter les fonctionnalités avancées** : attachments complexes, versioning avancé, OData

Cette architecture permet une séparation claire entre développement/test (draft) et production (published), essentielle pour un workflow de formulaires robuste.
