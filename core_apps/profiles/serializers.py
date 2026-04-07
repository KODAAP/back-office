from django_countries.serializer_fields import CountryField
from rest_framework import serializers

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source="user.first_name")
    user_id = serializers.ReadOnlyField(source="user.pkid")
    last_name = serializers.ReadOnlyField(source="user.last_name")
    username = serializers.ReadOnlyField(source="user.username")
    full_name = serializers.ReadOnlyField(source="user.get_full_name")
    country_of_origin = CountryField(name_only=True)
    avatar = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)
    last_login = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "user_id",
            "first_name",
            "last_name",
            "username",
            "full_name",
            "gender",
            "country_of_origin",
            "city_of_origin",
            "bio",
            "odk_role",
            "date_joined",
            "last_login",
            "avatar",
        ]

    def get_avatar(self, obj: Profile) -> str | None:
        try:
            return obj.avatar.url
        except AttributeError:
            return None

    def get_last_login(self, obj: Profile):
        request = self.context.get("request")
        if request and request.user:
            from core_apps.common.permissions_config import ADMIN_ROLES

            try:
                if (
                    request.user.is_superuser
                    or request.user.profile.odk_role in ADMIN_ROLES
                ):
                    last = obj.user.last_login
                    return last.isoformat() if last else None
            except Profile.DoesNotExist:
                if request.user.is_superuser:
                    last = obj.user.last_login
                    return last.isoformat() if last else None
        return None


class UpdateProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    username = serializers.CharField(source="user.username")
    country_of_origin = CountryField(name_only=True)
    gender = serializers.ChoiceField(choices=Profile.Gender.choices)
    odk_role = serializers.CharField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "first_name",
            "last_name",
            "username",
            "gender",
            "country_of_origin",
            "city_of_origin",
            "bio",
            "odk_role",
            "phone_number",
        ]


class RoleUpdateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=Profile.ODKRole.choices, source="odk_role")

    class Meta:
        model = Profile
        fields = ["role"]


class AvatarUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["avatar"]
