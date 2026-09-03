import logging

from django.conf import settings
from rest_framework.request import Request

from rest_framework_simplejwt.authentication import AuthUser, JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import Token

# Configure logging for the authentication module
logger = logging.getLogger(__name__)


class CookieAuthentication(JWTAuthentication):
    """
    Custom authentication class that extends JWT authentication to support both
    cookie-based and header-based token authentication.

    This class first checks for the token in the request header, and if not found,
    looks for it in the cookies. This allows for flexible authentication methods
    while maintaining security.
    """

    def authenticate(self, request: Request) -> tuple[AuthUser, Token] | None:
        """
        Authenticate the request by checking for a valid JWT token.

        Args:
            request (Request): The incoming request object containing headers and cookies

        Returns:
            Optional[Tuple[AuthUser, Token]]: A tuple containing the authenticated user
            and validated token if authentication succeeds, None otherwise

        Flow:
            1. Check for token in request header
            2. If not in header, check for token in cookies
            3. Validate token if found
            4. Return user and token if validation succeeds
        """
        header = self.get_header(request)
        raw_token = None

        # Try to get token from header first
        if header is not None:
            raw_token = self.get_raw_token(header)
        # If not in header, try to get from cookies
        elif settings.COOKIE_NAME in request.COOKIES:
            raw_token = request.COOKIES.get(settings.COOKIE_NAME)

        if raw_token is not None:
            try:
                # Validate the token and get associated user
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

            except TokenError as e:
                # Log any token validation errors
                logger.error(f"Token validation error: {str(e)}")
        return None
