import os

from django.core.files.storage import FileSystemStorage
from django.core.files.temp import NamedTemporaryFile

import requests

from core_apps.profiles.models import Profile


def save_profile(backend, user, response, *args, **kwargs):
    if backend.name == "google-oauth2":
        avatar_url = response.get("picture", None)
        if avatar_url:
            response = requests.get(avatar_url)
            if response.status_code == 200:
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(response.content)
                img_temp.flush()
                profile, created = Profile.objects.get_or_create(user=user)

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

                profile.avatar.save(f"{user.email}_photo", img_temp, save=True)
