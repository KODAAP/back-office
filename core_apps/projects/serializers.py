from django.contrib.auth import get_user_model

from rest_framework import serializers

from core_apps.common.permissions_config import PERMISSION_SETS

from .models import Projects

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

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
        ]
        read_only_fields = [
            "id",
            "pkid",
            "odk_id",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by and obj.created_by.get_full_name is not None:
            return obj.created_by.get_full_name
        elif obj.created_by:
            return obj.created_by.username
        return None

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
