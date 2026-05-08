from django.core.files.storage import FileSystemStorage
from django.core.files.temp import NamedTemporaryFile

import requests

from core_apps.profiles.models import Profile


# TODO: fonction à revoir
def save_profile(backend, user, response, *args, **kwargs):
    if backend.name == "google-oauth2":
        avatar_url = response.get("picture", None)
        if avatar_url:
            response = requests.get(avatar_url)
            if response.status_code == 200:
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(response.content)
                img_temp.flush()
                _ = FileSystemStorage()
                profile, created = Profile.objects.get_or_create(user=user)
                profile.avatar.save(f"{user.email}_photo", img_temp, save=True)

                profile.save()
