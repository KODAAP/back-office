import logging

from django.db import transaction

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core_apps.invitations.models import UserInvitation
from core_apps.invitations.serializers import (
    AcceptInvitationSerializer,
    BulkInvitationSerializer,
    InvitationSerializer,
    SendInvitationSerializer,
)
from core_apps.users.models import User

logger = logging.getLogger(__name__)


class SendInvitationView(APIView):
    """Envoyer une invitation par email"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SendInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            with transaction.atomic():
                # Créer l'invitation
                invitation = UserInvitation.objects.create(
                    email=email, invited_by=request.user
                )

                # Envoyer l'email
                invitation.send_invitation_email()

                logger.info(f"Invitation sent to {email} by {request.user.email}")

        except Exception as e:
            logger.error(f"Error sending invitation to {email}: {e}")
            # L'invitation n'est pas créée grâce au transaction.atomic
            return Response(
                {"error": "Erreur lors de l'envoi de l'email"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
        )


class ValidateInvitationView(APIView):
    """Valider un token d'invitation"""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        token = request.query_params.get("token")

        if not token:
            return Response(
                {"error": "Token manquant"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invitation = UserInvitation.objects.get(token=token)

            if not invitation.is_valid():
                return Response(
                    {"error": "Cette invitation a expiré ou a déjà été utilisée"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response({"valid": True, "email": invitation.email})

        except UserInvitation.DoesNotExist:
            return Response(
                {"error": "Token invalide"}, status=status.HTTP_404_NOT_FOUND
            )


class BulkInvitationView(APIView):
    """Envoyer des invitations en masse"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = BulkInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        emails = serializer.validated_data["emails"]

        success_list = []
        failed_list = []

        for email in emails:
            try:
                with transaction.atomic():
                    # Vérifier si utilisateur existe déjà
                    if User.objects.filter(email=email).exists():
                        raise Exception("Un utilisateur avec cet email existe déjà")

                    # Vérifier si invitation non-utilisée existe déjà
                    existing_invitation = UserInvitation.objects.filter(
                        email=email, is_used=False
                    ).first()

                    if existing_invitation and existing_invitation.is_valid():
                        raise Exception("Une invitation valide existe déjà")

                    # Créer l'invitation
                    invitation = UserInvitation.objects.create(
                        email=email, invited_by=request.user
                    )

                    # Envoyer l'email
                    invitation.send_invitation_email()

                    success_list.append(
                        {"email": email, "invitation_id": invitation.id}
                    )

                    logger.info(f"Invitation sent to {email} by {request.user.email}")

            except Exception as e:
                logger.error(f"Error sending invitation to {email}: {e}")
                failed_list.append({"email": email, "reason": str(e)})

        return Response(
            {
                "total": len(emails),
                "successful": len(success_list),
                "failed": len(failed_list),
                "details": {"success": success_list, "failed": failed_list},
            },
            status=status.HTTP_200_OK,
        )


class AcceptInvitationView(APIView):
    """Accepter une invitation et créer le compte"""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        try:
            invitation = UserInvitation.objects.get(token=token)

            if not invitation.is_valid():
                return Response(
                    {"error": "Cette invitation a expiré ou a déjà été utilisée"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Créer l'utilisateur
            user = User.objects.create_user(
                email=invitation.email,
                first_name=serializer.validated_data["first_name"],
                last_name=serializer.validated_data["last_name"],
                password=serializer.validated_data["password"],
                is_active=True,  # Actif par défaut
            )
            # Marquer l'invitation comme utilisée
            invitation.mark_as_used()

            logger.info(f"User {user.email} registered via invitation")

            return Response(
                {"message": "Compte créé avec succès", "email": user.email},
                status=status.HTTP_201_CREATED,
            )

        except UserInvitation.DoesNotExist:
            return Response(
                {"error": "Token invalide"}, status=status.HTTP_404_NOT_FOUND
            )
