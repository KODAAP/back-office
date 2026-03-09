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


# from django.core.files.temp import NamedTemporaryFile
# import requests
# from core_apps.profiles.models import Profile
# from django.core.files.storage import FileSystemStorage
# import os
# import hashlib
#
#
# def save_profile(backend, user, response, *args, **kwargs):
#     if backend.name == "google-oauth2":
#         avatar_url = response.get("picture", None)
#         if avatar_url:
#             # Récupérer ou créer le profil
#             profile, created = Profile.objects.get_or_create(user=user)
#
#             # Créer un hash de l'URL pour détecter les changements
#             url_hash = hashlib.md5(avatar_url.encode()).hexdigest()
#
#             # Vérifier si on a besoin de mettre à jour la photo
#             should_update = created or not profile.avatar or getattr(profile, 'avatar_url_hash', None) != url_hash
#
#             if should_update:
#                 # Si le profil existe déjà et a une photo, supprimer l'ancienne photo
#                 if not created and profile.avatar:
#                     if os.path.isfile(profile.avatar.path):
#                         os.remove(profile.avatar.path)
#
#                 # Télécharger la nouvelle photo
#                 response_img = requests.get(avatar_url)
#                 if response_img.status_code == 200:
#                     img_temp = NamedTemporaryFile(delete=True)
#                     img_temp.write(response_img.content)
#                     img_temp.flush()
#
#                     # Sauvegarder la nouvelle photo
#                     profile.avatar.save(f"{user.email}_photo", img_temp, save=True)
#
#                     # Sauvegarder le hash de l'URL (nécessite d'ajouter ce champ au modèle Profile)
#                     # profile.avatar_url_hash = url_hash
#                     profile.save()
