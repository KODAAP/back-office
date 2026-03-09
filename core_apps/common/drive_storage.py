import io
import logging
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)


@deconstructible
class GoogleDriveStorage(Storage):
    # Constants
    DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
    FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
    DEFAULT_MIME_TYPE = "application/octet-stream"

    MIME_TYPES = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }

    def __init__(self):
        self.service = self._get_service()
        self.folder_id = self._get_folder_id()

    def _get_folder_id(self):
        """Get and validate Google Drive folder ID from settings"""
        folder_id = getattr(settings, "GOOGLE_DRIVE_FOLDER_ID", None)
        if not folder_id:
            raise ImproperlyConfigured("GOOGLE_DRIVE_FOLDER_ID must be set in settings")
        return folder_id

    def _get_service(self):
        """Initialize Google Drive service"""
        try:
            service_account_file = getattr(
                settings, "GOOGLE_SERVICE_ACCOUNT_FILE", None
            )
            if not service_account_file or not os.path.exists(service_account_file):
                raise ImproperlyConfigured(
                    "GOOGLE_SERVICE_ACCOUNT_FILE must be set and file must exist"
                )

            credentials = Credentials.from_service_account_file(
                service_account_file, scopes=[self.DRIVE_SCOPE]
            )
            return build("drive", "v3", credentials=credentials)
        except Exception as e:
            logger.error(f"Error initializing Google Drive service: {e}")
            raise

    def _save(self, name, content):
        """Save file to Google Drive"""
        try:
            folder_path = self.get_folder_url(name)
            file_name = self.get_image_name(name)

            target_folder_id = self._ensure_folder_exists(folder_path)
            file_id = self._upload_file(file_name, content, target_folder_id)

            self._make_public(file_id)
            logger.info(f"File {name} uploaded successfully, ID: {file_id}")
            return folder_path + file_id
        except Exception as e:
            logger.error(f"Error saving {name}: {e}")
            raise

    def _ensure_folder_exists(self, folder_path):
        """Ensure folder structure exists and return final folder ID"""
        current_folder_id = self.folder_id

        if not folder_path:
            return current_folder_id

        folder_names = folder_path.strip("/").split("/")
        for folder_name in folder_names:
            if not folder_name:  # Skip empty folder names
                continue
            current_folder_id = self._get_or_create_folder(
                folder_name, current_folder_id
            )

        return current_folder_id

    def _get_or_create_folder(self, folder_name, parent_id):
        """Get existing folder or create new one"""
        # Search for existing folder
        query = (
            f"name='{folder_name}' and mimeType='{self.FOLDER_MIME_TYPE}' "
            f"and '{parent_id}' in parents and trashed=false"
        )
        results = (
            self.service.files()
            .list(
                q=query,
                spaces="drive",
                supportsAllDrives=True,
                fields="files(id, name)",
            )
            .execute()
        )

        folders = results.get("files", [])
        if folders:
            return folders[0]["id"]

        # Create new folder
        folder_metadata = {
            "name": folder_name,
            "mimeType": self.FOLDER_MIME_TYPE,
            "parents": [parent_id],
            "driveId": self.folder_id,
        }
        folder = (
            self.service.files()
            .create(body=folder_metadata, supportsAllDrives=True, fields="id")
            .execute()
        )
        return folder.get("id")

    def _upload_file(self, file_name, content, parent_folder_id):
        """Upload file content to Google Drive"""
        file_metadata = {"name": file_name, "parents": [parent_folder_id]}

        content.seek(0)
        media = MediaIoBaseUpload(
            io.BytesIO(content.read()),
            mimetype=self._get_mimetype(file_name),
            resumable=True,
        )

        file = (
            self.service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )

        return file.get("id")

    def _make_public(self, file_id):
        """Make file public"""
        try:
            permission = {"type": "anyone", "role": "reader"}
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                supportsAllDrives=True,
            ).execute()
        except Exception as e:
            logger.warning(f"Unable to make file public: {e}")

    def _get_mimetype(self, name):
        """Determine MIME type based on extension"""
        extension = name.lower().split(".")[-1]
        return self.MIME_TYPES.get(extension, self.DEFAULT_MIME_TYPE)

    def delete(self, name):
        """Delete file from Google Drive"""
        try:
            file_id = self.get_image_name(name)
            self.service.files().delete(
                fileId=file_id, supportsAllDrives=True
            ).execute()
            logger.info(f"File {name} deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting {name}: {e}")

    def exists(self, name):
        """Check if file exists"""
        try:
            file_id = self.get_image_name(name)
            self.service.files().get(fileId=file_id, supportsAllDrives=True).execute()
            return True
        except Exception:
            return False

    def url(self, name):
        """Return public URL for file"""
        file_id = self.get_image_name(name)
        if not file_id:
            return None
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w400-h300"

    def size(self, name):
        """Return file size"""
        try:
            file_id = self.get_image_name(name)
            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="size",
                    supportsAllDrives=True,
                )
                .execute()
            )
            return int(file.get("size", 0))
        except Exception:
            return 0

    def get_image_name(self, name):
        """Extract file name from path"""
        return name.split("/")[-1]

    def get_folder_url(self, name):
        """Extract folder path from file name"""
        folders = name.split("/")[:-1]
        if not folders:
            return ""
        return "/".join(folders) + "/"
