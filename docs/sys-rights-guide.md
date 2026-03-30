### Aperçu du Système de Permissions

Le projet Sycosur utilise **Django Guardian** pour une gestion fine des permissions au niveau objet (object-level permissions), combinée à des rôles ODK stockés dans le profil utilisateur (`odk_role`).

- **Permissions globales** : Rôles `administrator` et `manager` bypassent les checks granulaires.
- **Permissions objet** : Définies sur le modèle `Projects`, assignées par niveaux (`read`, `submit`, `contribute`, `manage`).
- **Intégration DRF** : Classes custom `HasProjectPermission` (et dérivées pour forms/submissions) appliquées sur les vues.
- **Endpoints dédiés** : Assignation, révocation, listing des permissions par projet.
- **Automatisation** : Signal assigne `manage` au créateur ; exposition dans `/users/me`.
- **Filtrage** : Listes restreintes aux objets accessibles (`get_objects_for_user`).

Le système est **majoritairement complet et sécurisé** : vues protégées, filtrage queryset, checks robustes (profil absent géré), idempotence.

#### Permissions Custom du Modèle `Projects`
Définies dans `core_apps\projects\models.py` (lignes 38-51) :
```
access_project, archive_project, restore_project, manage_project
view_form, create_form, edit_form, delete_form
view_submission, add_submission, edit_submission, delete_submission
```

#### Rôles ODK (`Profile.odk_role`)
```
data_collector : read/submit
insuco_user : read/submit/contribute
manager/administrator : tous niveaux + bypass
```

### Configuration Centralisée
`core_apps\common\permissions_config.py` :
- `PERMISSION_SETS` : Hiérarchie des niveaux (cumulatifs).
```
read: access_project, view_form, view_submission
submit: + add_submission
contribute: + edit_submission, create_form, edit_form
manage: + manage_project, archive_project, restore_project, delete_form, delete_submission
```
- `ADMIN_ROLES = ['administrator', 'manager']`
- `ROLE_ALLOWED_LEVELS` : Limites par rôle.

**Settings** (`config\settings\common.py`) :
```
AUTHENTICATION_BACKENDS inclut guardian.backends.ObjectPermissionBackend
GUARDIAN_RENDER_403 = True
```

### Classes de Permissions DRF
`core_apps\common\permissions.py` :
- **`HasProjectPermission`** : Mapping méthode → perm (GET: `access_project`, PATCH/PUT/DELETE: `manage_project`).
  - Bypass admin/manager.
  - `has_object_permission` utilise `view.required_permission` ou mapping.
  - POST création : check `add_projects` global ou rôle.
- **`HasFormPermission`** / **`HasSubmissionPermission`** : Héritent, mappings spécifiques (view_form/create_form/etc.).

Appliées sur **toutes les vues projets** (`permission_classes = [HasProjectPermission]`).

### Services (`core_apps\projects\services.py`)
- `assign_project_permission(user, project, level)` : Supprime ancien niveau, assigne nouveau (idempotent). Vérifie rôle autorisé.
- `revoke_project_permissions(user, project)` : Supprime tout.
- `get_project_users_with_permissions(project)` / `get_user_permission_level(user, project)` : Utilitaires Guardian.

**Guardian shortcuts** : `assign_perm`, `remove_perm`, `get_users_with_perms`.

### Vues et Endpoints API (`core_apps\projects\views.py`)
#### Projets de base
- `GET /projects/` (`ProjectListCreateView`) : Filtré par `get_objects_for_user(access_project)`. Params: `?add_deleted`, `?add_archived`.
- `POST /projects/` : Création (rôle manager/admin ou `add_projects` global).
- `GET/PUT/PATCH/DELETE /projects/{pkid}/` (`ProjectDetailView`) : CRUD standard.

#### Actions custom
```
PATCH /projects/{pk}/archive/ : archive_project
PATCH /projects/{pk}/unarchive/ : archive_project (note: réutilise archive_project)
PATCH /projects/{pk}/restore/ : restore_project
```

#### Gestion permissions (`/projects/{pkid}/permissions/`)
```
POST /assign/ : {user_id, permission_level} → 201
DELETE /{user_id}/revoke/ → 204
GET / → liste users + niveaux
```
- Protégées par `manage_project` (assign/revoke) ou `access_project` (list).

### Assignation Automatique
`core_apps\projects\signals.py` + `apps.py.ready()` :
- `post_save` sur `Projects` : Assigne `manage` au `created_by` si nouveau.

### Exposition des Permissions
`/users/me` (`core_apps\users\serializers.py#CustomUserSerializer`) :
- `permissions.projects` : Liste projets + `permission_level` + liste perms.

**Exemple réponse** (admin) :
```json
"permissions": {
  "role": "administrator",
  "is_admin": true,
  "projects": [{"pkid":1, "name":"...", "permission_level":"manage", "permissions":["access_project", ...]}]
}
```

### Commande Management
```
python manage.py assign_permissions --user-email=user@example.com --project-id=1 --level=contribute
```

### Bonnes Pratiques et Dépannage
#### Vérifier permissions
```python
# Shell
from guardian.shortcuts import get_objects_for_user
qs = get_objects_for_user(user, 'projects.access_project', Projects)
user.has_perm('projects.manage_project', project)

from core_apps.projects.services import get_user_permission_level
get_user_permission_level(user, project)
```

#### Ajouter permission_classes à une vue ODK
```python
class SomeFormView(...):
    permission_classes = [HasFormPermission]
    required_permission = 'projects.view_form'  # si custom
```

#### Problèmes courants
- **Profil absent** : Géré (no bypass, ValueError dans services → 400).
- **Liste expose projets** : Résolu par filtrage queryset.
- **Unarchive utilise archive_project** : À aligner si besoin (`restore_project` ?).
- **ODK views** : Permissions manuelles/services ? Ajouter `HasFormPermission` si pas fait.
- **Tests** : Ajouter intégration (pytest + fixtures users/projets/perms).
- **Logs** : Audit via `log_audit_action` sur archive/restore/unarchive.

#### Améliorations
- Transactions sur assign/revoke.
- Cache perms par user/projet.
- Admin Guardian pour visu.
- Hiérarchie rôles plus stricte.

**Docs sources** : `docs\guide_permissions.md` (guide implémentation), `docs\MakeItPerfect.md` (corrections appliquées).

Ce doc reflète l'état **actuel (2026-01-20)** : système mature, prêt prod. Pour debug : logs + shell Guardian.
