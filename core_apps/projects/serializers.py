from django.contrib.auth import get_user_model

from rest_framework import serializers

from core_apps.common.permissions_config import PERMISSION_SETS

from .models import Projects

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    permission_level = serializers.SerializerMethodField()
    has_manager = serializers.SerializerMethodField()

    class Meta:
        model = Projects
        fields = [
            "id",
            "odk_id",
            "pkid",
            "name",
            "description",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
            "permission_level",
            "has_manager",
            "archived",
        ]
        read_only_fields = [
            "id",
            "pkid",
            "odk_id",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
            "permission_level",
            "has_manager",
            "archived",
        ]

    def get_created_by_name(self, obj) -> str:
        if obj.created_by and obj.created_by.get_full_name is not None:
            return obj.created_by.get_full_name
        elif obj.created_by:
            return obj.created_by.username
        return None

    def get_permission_level(self, obj) -> str:
        target_user = self.context.get("target_user")
        if target_user:
            from core_apps.projects.services import get_user_permission_level

            return get_user_permission_level(target_user, obj)
        return None

    def get_has_manager(self, obj) -> bool:
        from guardian.shortcuts import get_users_with_perms

        from core_apps.profiles.models import Profile

        users_with_perms = get_users_with_perms(
            obj, attach_perms=True, with_group_users=False
        )
        for user, perms in users_with_perms.items():
            if "manage_project" in perms:
                # Vérifier si l'utilisateur est un manager (et non un administrateur global)
                # car les administrateurs ont accès à tout par défaut,
                # mais "has_manager" implique généralement une attribution spécifique.
                try:
                    if user.profile.odk_role == Profile.ODKRole.MANAGER:
                        return True
                except Profile.DoesNotExist:
                    continue
        return False

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class AssignProjectPermissionSerializer(serializers.Serializer):
    """Serializer pour assigner des permissions à un utilisateur."""

    user_id = serializers.IntegerField()
    permission_level = serializers.ChoiceField(choices=list(PERMISSION_SETS.keys()))

    def validate_user_id(self, value):
        if not User.objects.filter(pkid=value).exists():
            raise serializers.ValidationError("User not found")
        return value


class ProjectPermissionUserSerializer(serializers.ModelSerializer):
    """Serializer pour afficher un utilisateur avec ses permissions."""

    full_name = serializers.ReadOnlyField(source="get_full_name")
    permission_level = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["pkid", "email", "full_name", "permission_level"]

    def get_permission_level(self, obj):
        project = self.context.get("project")
        if project:
            from core_apps.projects.services import get_user_permission_level

            return get_user_permission_level(obj, project)
        return None
