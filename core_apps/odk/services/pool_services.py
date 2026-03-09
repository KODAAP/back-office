import logging
import threading
from contextlib import contextmanager
from multiprocessing.context import TimeoutError
from queue import Empty, Queue

from django.conf import settings
from django.utils import timezone

import requests

logger = logging.getLogger(__name__)


class ODKAccountPool:
    """Singleton class to manage a pool of ODK accounts for concurrent access"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ODKAccountPool, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.accounts = [
            {
                "email": settings.ODK_ADMIN_EMAIL,
                "password": settings.ODK_ADMIN_PASSWORD,
                "id": 5,
            }
        ]

        # Additional accounts if configured
        if hasattr(settings, "ODK_ADMIN_EMAIL_2") and hasattr(
            settings, "ODK_ADMIN_PASSWORD_2"
        ):
            self.accounts.append(
                {
                    "email": settings.ODK_ADMIN_EMAIL_2,
                    "password": settings.ODK_ADMIN_PASSWORD_2,
                    "id": 6,
                }
            )

        self.account_queue = Queue()
        self.account_locks = {}
        self.account_sessions = {}

        # Initialize Queue and locks for each account
        for account in self.accounts:
            self.account_queue.put(account)
            self.account_locks[account["id"]] = threading.Lock()

        self._initialized = True
        logger.info(f"ODK Account Pool initialized with {len(self.accounts)} compte(s)")

    @contextmanager
    def acquire_account(self, timeout=30):
        """Context manager to acquire an ODK account for use"""
        account = self.get_account(timeout)
        try:
            yield account
        finally:
            self.return_account(account)

    def get_account(self, timeout=30) -> dict:
        """Récupère un compte disponible du pool"""
        thread_id = threading.current_thread().ident
        try:
            account = self.account_queue.get(timeout=timeout)
            logger.debug(f"ODK account {account['id']} assigned to thread {thread_id}")
            return account
        except Empty:
            logger.error(
                f"No ODK account available after {timeout} seconds (thread: {thread_id})"
            )
            raise TimeoutError(
                f"No ODK account available after {timeout} seconds"
            ) from None
        except Exception as e:
            logger.error(f"Error retrieving account: {e} (thread: {thread_id})")
            raise Exception(f"Error retrieving ODK account: {e}") from e

    def return_account(self, account) -> None:
        """Remet un compte dans le pool"""
        thread_id = threading.current_thread().ident
        self.account_queue.put(account)
        logger.debug(
            f"ODK account {account['id']} returned to the pool by thread {thread_id}"
        )

    def get_session_for_account(self, account) -> dict:
        """Get session for a specific account, creating or resetting it if necessary"""
        account_id = account["id"]

        with self.account_locks[account_id]:
            session_info = self.account_sessions.get(account_id)
            current_time = timezone.now()
            # Réinitialise la session si elle est expirée ou absente
            if (
                session_info is None
                or session_info.get("expires_at")
                and session_info["expires_at"] < current_time
            ):
                logger.debug(f"Resetting session for account {account_id}")
                self.account_sessions[account_id] = {
                    "session": requests.Session(),
                    "token": None,
                    "expires_at": None,
                }
            return self.account_sessions[account_id]

    def close_sessions(self):
        for account_id, session_info in self.account_sessions.items():
            if session_info["session"]:
                session_info["session"].close()
                logger.debug(f"Session closed for account {account_id}")
        self.account_sessions.clear()
