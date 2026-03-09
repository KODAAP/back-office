# from typing import TYPE_CHECKING
#
# from core_apps.projects.models import  Projects
#
# if TYPE_CHECKING:
#     from django.contrib.auth import get_user_model
#
#     from core_apps.profiles.models import Profile
#
#     User = get_user_model()
#     # Annotation pour dire à l'IDE que User a un attribut profile
#     User.profile = Profile
#
#
# class ODKPermissionMixin:
#     """Mixin pour la gestion des permissions ODK"""
#
#     # Annotation de type pour indiquer à l'IDE que django_user existera
#     django_user: "User"
#
#     def _validate_user_and_profile(self) -> "Profile":
#         """Valide l'existence de django_user et son profil, retourne le profil"""
#         if not hasattr(self, "django_user") or not self.django_user:
#             raise AttributeError("django_user must be defined in the service class")
#
#         if not hasattr(self.django_user, "profile") or not self.django_user.profile:
#             raise AttributeError("User must have a profile with odk_role defined")
#
#         return self.django_user.profile
#
#     def _is_high_privilege_role(self, profile) -> bool:
#         """Vérifie si l'utilisateur a un rôle privilégié (Manager ou Administrator)"""
#         return profile.odk_role in [
#             profile.ODKRole.MANAGER,
#             profile.ODKRole.ADMINISTRATOR,
#         ]
#
#     def _user_can_access_project_id(self, project_id: int) -> bool:
#         """Vérifie si l'utilisateur Django peut accéder au projet ODK"""
#         profile = self._validate_user_and_profile()
#
#         # Admin ODK peut tout voir
#         if profile.odk_role == profile.ODKRole.ADMINISTRATOR:
#             return True
#
#         # Manager ODK peut voir tous les projets
#         if profile.odk_role == profile.ODKRole.MANAGER:
#             return True
#         return False
#         # Vérification des permissions spécifiques au projet
#         # try:
#         #     project = Projects.objects.get(odk_id=project_id)
#         #
#         #     try:
#         #         # Si une permission explicite existe
#         #         ProjectPermissions.objects.get(user=self.django_user, project=project)
#         #         return True
#         #     except ProjectPermissions.DoesNotExist:
#         #
#         #         return profile.odk_role == profile.ODKRole.DATA_COLLECTOR
#         # except Projects.DoesNotExist:
#         #     # Si le projet n'est pas encore dans la DB, on autorise l'accès aux superviseurs et +
#         #     return profile.odk_role in [
#         #         profile.ODKRole.DATA_COLLECTOR,
#         #         profile.ODKRole.MANAGER,
#         #         profile.ODKRole.ADMINISTRATOR,
#         #     ]
#
#     def _user_can_create_project(self) -> bool:
#         """Vérifie si l'utilisateur peut créer un nouveau projet"""
#         profile = self._validate_user_and_profile()
#
#         # Seuls les managers et administrateurs peuvent créer des projets
#         return self._is_high_privilege_role(profile)
#
#     def _user_can_modify_project(self, project_id: int) -> bool:
#         """Vérifie si l'utilisateur peut modifier un projet"""
#         profile = self._validate_user_and_profile()
#
#         # Admin peut tout modifier
#         if profile.odk_role == profile.ODKRole.ADMINISTRATOR:
#             return True
#
#         # Manager peut modifier tous les projets
#         if profile.odk_role == profile.ODKRole.MANAGER:
#             return True
#
#         # Pour les autres, vérifier les permissions spécifiques
#         return self._user_can_access_project_id(project_id)
