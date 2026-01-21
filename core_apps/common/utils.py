import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_client_ip(request) -> Optional[str]:
    """Extract the client IP address from a Django request.

    It prioritizes the X-Forwarded-For header (first IP) when present
    to properly handle requests behind proxies/load balancers. Falls back
    to REMOTE_ADDR.
    """
    if request is None:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Take the first IP in the list
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit_action(
    *,
    user: Any,
    action: str,
    resource_type: str,
    resource_id: str | int,
    details: dict | None = None,
    success: bool = True,
    request=None,
    ip_address: str | None = None,
    raise_on_error: bool = False,
):

    try:
        # Local import to avoid potential circular imports at module load time
        from core_apps.common.models import AuditLogs

        ip = ip_address or (get_client_ip(request) if request is not None else None)
        payload = {
            "user": user,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "details": details or {},
            "success": success,
            "ip_address": ip,
        }
        return AuditLogs.objects.create(**payload)
    except Exception as e:
        logger.error(
            f"Failed to write audit log for action '{action}' on '{resource_type}': {e}"
        )
        if raise_on_error:
            raise
        return None
