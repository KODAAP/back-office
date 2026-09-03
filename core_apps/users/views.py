import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from djoser.social.views import ProviderAuthView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core_apps.common.permissions import CanChangeODKRole
from core_apps.invitations.models import UserInvitation
from core_apps.profiles.models import Profile
from core_apps.users.models import User
from core_apps.users.serializers import UserDashboardSerializer

logger = logging.getLogger(__name__)


def send_welcome_email(user):
    if not settings.DEBUG:  # Production only
        try:
            site_name = getattr(settings, "SITE_NAME", "Sycosur2")
            send_mail(
                subject=f"Welcome on {site_name} !",
                message=f"""
                Hello {user.get_full_name},
                Thank you for registering via your OAuth account.
                You can now access all {site_name} features.
                The {site_name} team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"Error sending email to {user.email}: {e}")


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str | None = None
) -> None:
    access_token_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    cookie_settings = {
        "path": settings.COOKIE_PATH,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTPONLY,
        "samesite": settings.COOKIE_SAMESITE,
        "max_age": access_token_lifetime,
    }
    response.set_cookie("access", access_token, **cookie_settings)

    if refresh_token:
        refresh_token_lifetime = settings.SIMPLE_JWT[
            "REFRESH_TOKEN_LIFETIME"
        ].total_seconds()
        refresh_cookie_settings = cookie_settings.copy()
        refresh_cookie_settings["max_age"] = refresh_token_lifetime
        response.set_cookie("refresh", refresh_token, **refresh_cookie_settings)

    logged_in_cookie_settings = cookie_settings.copy()
    logged_in_cookie_settings["httponly"] = False
    response.set_cookie("logged_in", "true", **logged_in_cookie_settings)


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        token_res = super().post(request, *args, **kwargs)

        if token_res.status_code == status.HTTP_200_OK:
            access_token = token_res.data.get("access")
            refresh_token = token_res.data.get("refresh")

            if access_token and refresh_token:
                set_auth_cookies(
                    token_res,
                    access_token=access_token,
                    refresh_token=refresh_token,
                )

                token_res.data.pop("access", None)
                token_res.data.pop("refresh", None)

                token_res.data["message"] = "Login Successful."
            else:
                token_res.data["message"] = "Login Failed"
                logger.error("Access or refresh token not found in login response data")

        return token_res


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        refresh_token = request.COOKIES.get("refresh")

        if refresh_token:
            request.data["refresh"] = refresh_token

        refresh_res = super().post(request, *args, **kwargs)

        if refresh_res.status_code == status.HTTP_200_OK:
            access_token = refresh_res.data.get("access")
            refresh_token = refresh_res.data.get("refresh")

            if access_token and refresh_token:
                set_auth_cookies(
                    refresh_res,
                    access_token=access_token,
                    refresh_token=refresh_token,
                )

                refresh_res.data.pop("access", None)
                refresh_res.data.pop("refresh", None)

                refresh_res.data["message"] = "Access tokens refreshed successfully"
            else:
                refresh_res.data["message"] = (
                    "Access or refresh tokens not found in refresh response data"
                )
                logger.error(
                    "Access or refresh token not found in refresh response data"
                )

        return refresh_res


class CustomProviderAuthView(ProviderAuthView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        provider_res = super().post(request, *args, **kwargs)

        if provider_res.status_code == status.HTTP_201_CREATED:
            access_token = provider_res.data.get("access")
            refresh_token = provider_res.data.get("refresh")

            if access_token and refresh_token:
                set_auth_cookies(
                    provider_res,
                    access_token=access_token,
                    refresh_token=refresh_token,
                )
                send_welcome_email(request.user)
                provider_res.data.pop("access", None)
                provider_res.data.pop("refresh", None)
                provider_res.data["message"] = "You are logged in Successful."

            else:
                provider_res.data["message"] = (
                    "Access or refresh token not found in provider response"
                )
                logger.error(
                    "Access or refresh token not found in provider response data"
                )

        return provider_res


class LogoutAPIView(APIView):
    def post(self, request: Request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("access")
        response.delete_cookie("refresh")
        response.delete_cookie("logged_in")
        return response


class UserDashboardView(APIView):
    """
    Vue retournant les KPIs pour le dashboard utilisateur.

    Cette vue calcule le nombre total d'utilisateurs, la variation mensuelle,
    les utilisateurs actifs, le nombre d'administrateurs et les invitations en attente.
    """

    permission_classes = [IsAuthenticated, CanChangeODKRole]

    def get(self, request: Request) -> Response:
        """
        Récupère les statistiques du dashboard.

        Args:
            request (Request): L'objet de la requête.

        Returns:
            Response: Les statistiques formatées via UserDashboardSerializer.
        """
        now = timezone.now()
        last_month = now - timedelta(days=30)

        # 1. Total Users & Variation
        total_users = User.objects.count()
        users_last_month = User.objects.filter(date_joined__lte=last_month).count()
        variation = total_users - users_last_month

        # 2. Active Users
        active_users_count = User.objects.filter(is_active=True).count()
        active_rate = (active_users_count / total_users * 100) if total_users > 0 else 0

        # 3. Administrators
        admin_count = Profile.objects.filter(
            odk_role=Profile.ODKRole.ADMINISTRATOR
        ).count()
        admin_rate = (admin_count / total_users * 100) if total_users > 0 else 0

        # 4. Pending Invites (Non expirées et non utilisées)
        pending_invites = UserInvitation.objects.filter(
            expires_at__gt=now, is_used=False
        ).count()

        data = {
            "total_users": total_users,
            "users_variation_count": variation,
            "active_users": active_users_count,
            "active_rate": round(active_rate, 2),
            "total_admins": admin_count,
            "admins_rate": round(admin_rate, 2),
            "pending_invites": pending_invites,
        }

        serializer = UserDashboardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
