import logging
from typing import Dict, List, Optional

from .baseService import BaseODKService
from .exceptions import ODKValidationError

logger = logging.getLogger(__name__)


class ODKPublicAccessService(BaseODKService):
    """Service for managing ODK Public Access Links"""

    # Extract constants for better maintainability
    EXTENDED_METADATA_HEADER = "X-Extended-Metadata"
    TOKEN_PREVIEW_LENGTH = 10
    ENKETO_SINGLE_PATH = "/-/single/"

    def __init__(self, django_user, request=None):
        super().__init__(django_user, request=request)

    def _get_enketo_id(self, project_id: int, form_id: str) -> Optional[str]:
        """Extract EnketoId retrieval logic"""
        form_data = self._make_request("GET", f"projects/{project_id}/forms/{form_id}")
        return form_data.get("enketoId")

    def _build_public_url(self, enketo_id: str, token: str) -> str:
        """Extract public URL generation logic"""
        base_domain = self.base_url.replace("/v1", "")
        return f"{base_domain}{self.ENKETO_SINGLE_PATH}{enketo_id}?st={token}"

    def _enhance_link_with_url(
        self, link_data: Dict, project_id: int, form_id: str
    ) -> None:
        """Extract logic for adding public URL to link data"""
        if token := link_data.get("token"):
            if enketo_id := self._get_enketo_id(project_id, form_id):
                link_data["public_url"] = self._build_public_url(enketo_id, token)

    def _get_current_account_id(self) -> Optional[str]:
        """Extract current account ID retrieval logic"""
        return self.current_account.get("id") if self.current_account else None

    def create_public_link(
        self, project_id: int, form_id: str, display_name: str, once: bool = False
    ) -> Dict:
        """Create a new Public Access Link for a form"""
        payload = {"displayName": display_name, "once": once}
        link_data = self._make_request(
            "POST", f"projects/{project_id}/forms/{form_id}/public-links", json=payload
        )

        self._enhance_link_with_url(link_data, project_id, form_id)

        self._log_action(
            "create_public_link",
            "public_link",
            f"{project_id}/{form_id}",
            {
                "display_name": display_name,
                "once": once,
                "link_id": link_data.get("id"),
                "odk_account": self._get_current_account_id(),
            },
            success=True,
        )

        return link_data

    def list_public_links(
        self, project_id: int, form_id: str, extended: bool = False
    ) -> List[Dict]:
        """List all Public Access Links for a form"""
        headers = {self.EXTENDED_METADATA_HEADER: "true"} if extended else {}
        links_data = self._make_request(
            "GET",
            f"projects/{project_id}/forms/{form_id}/public-links",
            headers=headers,
        )

        if links_data:
            if enketo_id := self._get_enketo_id(project_id, form_id):
                for link in links_data:
                    if token := link.get("token"):
                        link["public_url"] = self._build_public_url(enketo_id, token)

        return links_data

    def revoke_public_link(self, token: str) -> bool:
        """Revoke a Public Access Link"""
        self._make_request("DELETE", f"sessions/{token}")
        self._log_action(
            "revoke_public_link",
            "public_link",
            token,
            {
                "token": f"{token}",
                "odk_account": self._get_current_account_id(),
            },
            success=True,
        )
        return True
