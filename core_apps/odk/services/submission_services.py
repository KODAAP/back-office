from typing import Dict, List

from .base_service import BaseODKService
from .exceptions import ODKValidationError


class ODKSubmissionService(BaseODKService):
    """Service pour la gestion des soumissions ODK"""

    def get_form_submissions(self, project_id: int, form_id: str) -> List[Dict]:
        """Récupère les soumissions d'un formulaire spécifique"""
        try:
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}/submissions",
                headers={"X-Extended-Metadata": "true"},
            )
        except Exception as e:
            self._log_action(
                "list_submissions",
                "submission",
                f"{project_id}/{form_id}",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
            raise

    def get_submission(self, project_id: int, form_id: str, instance_id: str) -> Dict:
        """Récupère une soumission spécifique"""
        try:
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}/submissions/{instance_id}",
                headers={"X-Extended-Metadata": "true"},
            )
        except Exception as e:
            self._log_action(
                "get_submission",
                "submission",
                f"{project_id}/{form_id}/{instance_id}",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
            raise

    def export_submissions(
        self, project_id: int, form_id: str, to: str = "csv"
    ) -> bytes:
        """Exporte les soumissions d'un formulaire en CSV ou XLSX"""
        try:
            result = self._make_request(
                "POST",
                f"projects/{project_id}/forms/{form_id}/submissions.csv",
                return_json=False,
            )
            if to == "xlsx":
                from io import BytesIO, StringIO

                import pandas as pd

                df = pd.read_csv(StringIO(result.decode("utf-8")))
                output = BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Submissions")
                return output.getvalue()

            return result

        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "export_submissions_csv",
                "submission",
                f"{project_id}/{form_id}",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
            raise

    def submissions_data(self, project_id: int, form_id: str):
        try:
            headers = {"content-type": "application/json"}
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}.svc/Submissions?$expand=*",
                headers=headers,
            )
        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "export_submissions_data",
                "submission",
                f" project:{project_id}| form:{form_id} ",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )

    def zip_submissions(self, project_id: int, form_id: str):
        try:
            return self._make_request(
                "GET",
                f"projects/{project_id}/forms/{form_id}/submissions.csv.zip?attachments=false",
                return_json=False,
            )
        except ODKValidationError:
            raise
        except Exception as e:
            self._log_action(
                "export_submissions_zip",
                "submission",
                f" project:{project_id}| form:{form_id} ",
                {
                    "error": str(e),
                    "odk_account": (
                        self.current_account["id"] if self.current_account else None
                    ),
                },
                success=False,
            )
