from django.utils import timezone
from rest_framework import serializers

from core_apps.invitations.models import UserInvitation
from core_apps.users.models import User


class InvitationSerializer(serializers.ModelSerializer):
    """Serializer pour afficher les informations d'une invitation"""

    status = serializers.SerializerMethodField()

    class Meta:
        model = UserInvitation
        fields = [
            "id",
            "email",
            "created_at",
            "expires_at",
            "is_used",
            "used_at",
            "status",
        ]
        read_only_fields = ["id", "created_at", "expires_at", "is_used", "used_at"]

    def get_status(self, obj):
        if obj.is_used:
            return "accepted"
        if obj.expires_at < timezone.now():
            return "expired"
        return "pending"


class SendInvitationSerializer(serializers.Serializer):
    """Serializer pour envoyer une invitation"""

    email = serializers.EmailField()

    def validate_email(self, value):
        # Vérifier que l'utilisateur n'existe pas déjà
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Un utilisateur avec cet email existe déjà."
            )
        return value


class BulkInvitationSerializer(serializers.Serializer):
    """Serializer pour envoyer des invitations en masse"""

    emails = serializers.ListField(
        child=serializers.EmailField(), min_length=1, max_length=100
    )

    def validate_emails(self, value):
        # Retirer les doublons
        unique_emails = list(set(value))
        return unique_emails


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer pour accepter une invitation et créer un compte"""

    token = serializers.CharField()
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Les mots de passe ne correspondent pas."}
            )
        return data
