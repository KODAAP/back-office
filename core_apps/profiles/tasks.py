import os
from uuid import UUID

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

from celery import shared_task

from .models import Profile, avatar_upload_path


@shared_task(name="upload_avatar_to_media")
def upload_avatar_to_media(
    profile_id: UUID, image_content: bytes, original_filename: str
) -> None:
    profile = Profile.objects.get(id=profile_id)
    storage = FileSystemStorage(location=settings.MEDIA_ROOT)

    # Supprimer l'ancien avatar du disque s'il existe
    # (et s'il ne s'agit pas de l'avatar par défaut)
    if (
        profile.avatar
        and profile.avatar.name
        and "default-avatar" not in profile.avatar.name
    ):
        old_avatar_path = profile.avatar.path
        if os.path.isfile(old_avatar_path):
            os.remove(old_avatar_path)

    # Utiliser la fonction avatar_upload_path pour générer le bon chemin
    filename = avatar_upload_path(profile, original_filename)

    # Créer un ContentFile à partir des bytes
    content_file = ContentFile(image_content, name=original_filename)

    # Sauvegarder le fichier
    file_url = storage.save(filename, content_file)

    # Mettre à jour le profile avec le nouveau chemin
    profile.avatar = file_url
    profile.save()
