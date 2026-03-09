# GoogleDriveStorage

## Description

`GoogleDriveStorage` est une classe de stockage Django personnalisée qui permet de stocker des fichiers sur Google Drive. Elle implémente l'interface de stockage standard de Django (`Storage`) et peut être utilisée comme un système de fichiers alternatif pour les fichiers média et statiques.

## Prérequis

Pour utiliser cette classe, vous devez configurer les éléments suivants :

1. Un compte de service Google avec accès à l'API Google Drive
2. Un fichier de clé de compte de service (JSON)
3. Un dossier Google Drive où les fichiers seront stockés

## Configuration

Ajoutez les paramètres suivants dans votre fichier `settings.py` :

```python
# Chemin vers le fichier de compte de service Google (fichier JSON)
GOOGLE_SERVICE_ACCOUNT_FILE = 'chemin/vers/votre-fichier-compte-service.json'

# ID du dossier Google Drive où les fichiers seront stockés
GOOGLE_DRIVE_FOLDER_ID = 'votre-id-de-dossier-google-drive'

# Configuration pour utiliser GoogleDriveStorage comme système de stockage par défaut (optionnel)
DEFAULT_FILE_STORAGE = 'core_apps.common.drive_storage.GoogleDriveStorage'
```

## Utilisation basique

### Stockage direct de fichiers

```python
from core_apps.common.drive_storage import GoogleDriveStorage

# Créer une instance du stockage
storage = GoogleDriveStorage()

# Enregistrer un fichier
with open('mon_image.jpg', 'rb') as f:
    file_path = storage._save('dossier/mon_image.jpg', f)

# L'URL publique du fichier
url = storage.url(file_path)

# Vérifier si un fichier existe
exists = storage.exists(file_path)

# Supprimer un fichier
storage.delete(file_path)
```

### Utilisation avec les modèles Django

```python
from django.db import models
from core_apps.common.drive_storage import GoogleDriveStorage

class MonModel(models.Model):
    image = models.ImageField(
        upload_to='images/',
        storage=GoogleDriveStorage()
    )
```

## Utilisation avancée

### Upload asynchrone avec Celery

Vous pouvez utiliser Celery pour télécharger des fichiers en arrière-plan :

```python
@shared_task(name="upload_file_to_drive")
def upload_file_to_drive(file_id, file_content):
    storage = GoogleDriveStorage()
    filename = f"file_{file_id}.jpg"
    file_url = storage._save(filename, file_content)
    # Mise à jour de votre modèle avec l'URL du fichier
    # ...
```

## Structure des dossiers

La classe supporte automatiquement la création de dossiers imbriqués. Par exemple, si vous enregistrez un fichier à `photos/2025/07/image.jpg`, la structure de dossiers sera créée dans Google Drive.

## Limitations

- Cette implémentation est optimisée pour les fichiers image, mais prend en charge d'autres types de fichiers
- Les URLs générées pointent vers des miniatures Google Drive avec une taille fixe (400x300)
- Les fichiers sont rendus publics par défaut (paramètre configurable dans la méthode `_make_public`)

## Types MIME supportés

Les types MIME suivants sont explicitement pris en charge :
- jpg/jpeg: image/jpeg
- png: image/png
- gif: image/gif
- webp: image/webp

Pour les autres extensions, le type MIME par défaut est `application/octet-stream`.
