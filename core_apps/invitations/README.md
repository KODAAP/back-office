# Module Invitations

## Vue d'ensemble

Le module `invitations` gère le système d'invitation d'utilisateurs. Il permet aux utilisateurs authentifiés d'inviter de nouvelles personnes à rejoindre la plateforme via un lien d'inscription sécurisé.

---

## Structure des fichiers

```
invitations/
├── __init__.py
├── admin.py          # Configuration admin Django
├── apps.py           # Configuration de l'application
├── models.py         # Modèle UserInvitation
├── serializers.py    # Serializers DRF
├── urls.py           # Routes API
├── views.py          # Vues API
└── migrations/       # Migrations de base de données
```

---

## Modèle : UserInvitation

### Champs


| Champ        | Type               | Description                                         |
| ------------ | ------------------ | --------------------------------------------------- |
| `email`      | `EmailField`       | Adresse email de l'invité (indexé)                |
| `token`      | `CharField(64)`    | Token unique d'invitation (auto-généré)          |
| `invited_by` | `ForeignKey(User)` | Utilisateur ayant envoyé l'invitation              |
| `expires_at` | `DateTimeField`    | Date d'expiration de l'invitation                   |
| `is_used`    | `BooleanField`     | Indique si l'invitation a été utilisée           |
| `used_at`    | `DateTimeField`    | Date d'utilisation (nullable)                       |
| `created_at` | `DateTimeField`    | Date de création (hérité de TimeStampedModel)    |
| `updated_at` | `DateTimeField`    | Date de modification (hérité de TimeStampedModel) |

### Méthodes

#### `save(*args, **kwargs)`

Génère automatiquement :

- Un token sécurisé (32 bytes URL-safe) si non défini
- Une date d'expiration (7 jours à partir de maintenant) si non définie

#### `is_valid() -> bool`

Vérifie si l'invitation est valide :

- Non déjà utilisée (`is_used == False`)
- Non expirée (`expires_at > now`)

#### `mark_as_used()`

Marque l'invitation comme utilisée et enregistre la date d'utilisation.

#### `send_invitation_email()`

Envoie un email d'invitation à l'adresse spécifiée contenant :

- Le nom de l'inviteur
- Un lien vers la page d'inscription avec le token
- Les informations du site (configuré via settings)

---

## API Endpoints

### 1. Envoyer une invitation

```http
POST /api/invitations/send/
```

**Permission** : Authentification requise

**Request Body** :

```json
{
    "email": "nouveau@example.com"
}
```

**Response (201 Created)** :

```json
{
    "id": 1,
    "email": "nouveau@example.com",
    "created_at": "2026-03-22T10:00:00Z",
    "expires_at": "2026-03-29T10:00:00Z",
    "is_used": false
}
```

**Erreurs possibles** :

- `400` : Email invalide ou utilisateur déjà existant
- `500` : Erreur lors de l'envoi de l'email

---

### 2. Envoyer des invitations en masse

```http
POST /api/invitations/bulk/
```

**Permission** : Authentification requise

**Request Body** :

```json
{
    "emails": [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    ]
}
```

**Contraintes** :

- Minimum 1 email
- Maximum 100 emails
- Les doublons sont automatiquement supprimés

**Response (200 OK)** :

```json
{
    "total": 3,
    "successful": 2,
    "failed": 1,
    "details": {
        "success": [
            {"email": "user1@example.com", "invitation_id": 1},
            {"email": "user2@example.com", "invitation_id": 2}
        ],
        "failed": [
            {"email": "user3@example.com", "reason": "Un utilisateur avec cet email existe déjà"}
        ]
    }
}
```

---

### 3. Valider un token d'invitation

```http
GET /api/invitations/validate/?token=<token>
```

**Permission** : Publique (AllowAny)

**Response (200 OK)** :

```json
{
    "valid": true,
    "email": "nouveau@example.com"
}
```

**Erreurs possibles** :

- `400` : Token manquant ou invitation expirée/utilisée
- `404` : Token invalide (non trouvé)

---

### 4. Accepter une invitation (créer un compte)

```http
POST /api/invitations/accept/
```

**Permission** : Publique (AllowAny)

**Request Body** :

```json
{
    "token": "abc123...",
    "first_name": "Jean",
    "last_name": "Dupont",
    "password": "motdepasse123",
    "password_confirm": "motdepasse123"
}
```

**Contraintes** :

- `password` : minimum 8 caractères
- `password_confirm` : doit correspondre à `password`
- `first_name` : maximum 60 caractères
- `last_name` : maximum 60 caractères

**Response (201 Created)** :

```json
{
    "message": "Compte créé avec succès",
    "email": "nouveau@example.com"
}
```

**Erreurs possibles** :

- `400` : Mot de passe trop court ou mots de passe non correspondants
- `400` : Invitation expirée ou déjà utilisée
- `404` : Token invalide

---

## Configuration requise

### Settings Django

```python
# URL du frontend (pour générer les liens d'invitation)
FRONTEND_URL = "http://localhost:8080"

# Nom du site (utilisé dans les emails)
SITE_NAME = "Koda"

# Email expéditeur
DEFAULT_FROM_EMAIL = "noreply@example.com"
```

### Template email

L'email d'invitation utilise le template :

```
templates/emails/invitation.html
```

Variables disponibles dans le template :

- `{{ invited_by }}` : Nom complet de l'inviteur
- `{{ site_name }}` : Nom du site
- `{{ invitation_link }}` : Lien complet d'invitation
- `{{ email }}` : Email de l'invité
- `{{ current_year }}` : Année courante

---

## Dépendances

- `core_apps.common.models.TimeStampedModel` : Modèle de base avec timestamps
- `core_apps.common.tasks.send_email_task` : Tâche Celery pour l'envoi d'emails
- `core_apps.users.models.User` : Modèle utilisateur

---

## Sécurité

- **Tokens** : Générés avec `secrets.token_urlsafe(32)` (cryptographiquement sécurisé)
- **Expiration** : 7 jours par défaut
- **Usage unique** : Une invitation ne peut être utilisée qu'une seule fois
- **Validation côté client** : Les serializers valident l'unicité des emails et la correspondance des mots de passe
- **Transactions atomiques** : Les opérations critiques sont encapsulées dans des transactions

---

## Logs

Le module journalise les événements suivants :


| Événement         | Niveau | Message                                        |
| ------------------- | ------ | ---------------------------------------------- |
| Invitation envoyée | INFO   | `Invitation sent to {email} by {user}`         |
| Erreur d'envoi      | ERROR  | `Error sending invitation to {email}: {error}` |
| Compte créé       | INFO   | `User {email} registered via invitation`       |
