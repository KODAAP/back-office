from django.contrib.auth import get_user_model

from django_countries.serializer_fields import CountryField
from djoser.serializers import UserCreateSerializer, UserSerializer
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from core_apps.profiles.models import Profile

User = get_user_model()


class UserPermissionsSerializer(serializers.Serializer):
    """Serializer to expose user permissions."""

    is_admin = serializers.SerializerMethodField()
    globals = serializers.SerializerMethodField()
    projects = serializers.SerializerMethodField()

    def get_globals(self, obj) -> list:
        return list(obj.get_all_permissions())

    def get_is_admin(self, obj) -> bool:
        from core_apps.common.permissions_config import ADMIN_ROLES

        return obj.profile.odk_role in ADMIN_ROLES or obj.is_superuser

    def get_projects(self, obj) -> list:
        """Returns the projects with their permission levels."""
        from core_apps.common.permissions_config import ADMIN_ROLES, PERMISSION_SETS
        from core_apps.projects.models import Projects
        from core_apps.projects.services import get_user_permission_level

        user = obj

        # Admin/Manager have access to all projects
        if user.profile.odk_role in ADMIN_ROLES:
            projects = Projects.objects.filter(deleted=False, archived=False)
            return [
                {
                    "pkid": p.pkid,
                    "name": p.name,
                    "permission_level": "manage",
                    "permissions": list(PERMISSION_SETS["manage"]),
                }
                for p in projects
            ]

        # For other users, retrieve specific permissions
        result = []
        for project in Projects.objects.filter(deleted=False, archived=False):
            level = get_user_permission_level(user, project)
            if level:
                result.append(
                    {
                        "pkid": project.pkid,
                        "name": project.name,
                        "permission_level": level,
                        "permissions": list(PERMISSION_SETS[level]),
                    }
                )

        return result


class CustomUserSerializer(UserSerializer):
    full_name = serializers.ReadOnlyField(source="get_full_name")
    gender = serializers.ReadOnlyField(source="profile.gender")
    slug = serializers.ReadOnlyField(source="profile.slug")
    odk_role = serializers.ReadOnlyField(source="profile.odk_role")
    phone_number = PhoneNumberField(source="profile.phone_number")
    country = CountryField(source="profile.country_of_origin")
    city = serializers.ReadOnlyField(source="profile.city_of_origin")
    avatar = serializers.ReadOnlyField(source="profile.avatar.url")
    permissions = UserPermissionsSerializer(source="*", read_only=True)
    is_oauth_user = serializers.BooleanField(read_only=True)
    last_login = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "slug",
            "full_name",
            "gender",
            "odk_role",
            "phone_number",
            "country",
            "city",
            "avatar",
            "date_joined",
            "last_login",
            "is_oauth_user",
            "permissions",
        ]
        read_only_fields = ["id", "email", "date_joined", "last_login"]

    def get_last_login(self, obj):
        request = self.context.get("request")
        if request and request.user:
            from core_apps.common.permissions_config import ADMIN_ROLES

            try:
                if (
                    request.user.is_superuser
                    or request.user.profile.odk_role in ADMIN_ROLES
                ):
                    last = obj.last_login
                    return last.isoformat() if last else None
            except Profile.DoesNotExist:
                if request.user.is_superuser:
                    last = obj.last_login
                    return last.isoformat() if last else None
        return None


class CreateUserSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ["id", "email", "first_name", "last_name", "password"]


class UpdateODKRoleSerializer(UserSerializer):
    odk_role = serializers.ChoiceField(choices=Profile.ODKRole.choices, required=True)

    class Meta:
        model = Profile
        fields = ["odk_role"]
