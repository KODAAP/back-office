# core_apps/odk/services/exceptions.py

import ast
import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ODKValidationError(Exception):
    """Exception levée lors d'erreurs de validation ODK"""

    def __init__(self, message, error_detail=None, status_code=None):
        super().__init__(message)
        self.error_detail = error_detail
        self.status_code = status_code

    def parse_python_literal(self, py_str: str):
        """
        Parse une chaîne représentant un littéral Python (dict/list) en objet Python safe.
        """
        try:
            if not (py_str.startswith("{") and py_str.endswith("}")):
                return None
            parsed = ast.literal_eval(py_str)
            if not isinstance(parsed, dict):
                return None
            return parsed
        except (ValueError, SyntaxError, TypeError) as e:
            logger.warning(f"Failed to parse Python literal '{py_str[:50]}...': {e}")
            return None

    def extract_validation_messages(self):
        """
        Extraire et structurer les messages en format compact {message, error, warnings}.
        """
        validations = {"message": None, "error": None, "warnings": []}

        raw_messages = []
        if self.error_detail:
            if isinstance(self.error_detail, dict):
                if "message" in self.error_detail:
                    raw_messages.append(self.error_detail["message"])
                if "details" in self.error_detail:
                    if isinstance(self.error_detail["details"], list):
                        raw_messages.extend(self.error_detail["details"])
                    else:
                        raw_messages.append(str(self.error_detail["details"]))
            elif isinstance(self.error_detail, list):
                raw_messages = self.error_detail
            else:
                raw_messages.append(str(self.error_detail))

        # Parse si >=2 messages
        if len(raw_messages) >= 2:
            validations["message"] = raw_messages[0]
            parsed = self.parse_python_literal(raw_messages[1])
            if parsed:
                if "error" in parsed and parsed["error"]:
                    validations["error"] = (
                        parsed["error"]
                        if isinstance(parsed["error"], str)
                        else str(parsed["error"])
                    )

                if "warnings" in parsed and parsed["warnings"]:
                    warnings_obj = parsed["warnings"]
                    if (
                        isinstance(warnings_obj, dict)
                        and "xlsFormWarnings" in warnings_obj
                    ):
                        validations["warnings"] = warnings_obj["xlsFormWarnings"]
                    elif isinstance(warnings_obj, list):
                        validations["warnings"] = warnings_obj
        elif len(raw_messages) == 1:
            validations["message"] = raw_messages[0]

        return validations

    def to_response(self, error_message="Validation error", log_message=None):
        """Créer une Response structurée et compacte pour cette exception de validation"""
        if log_message:
            logger.error(log_message)

        validations = self.extract_validation_messages()

        response_data = {
            "error": error_message,
            "details": str(
                self
            ),  # Renommé de 'detail' à 'details' pour matcher ta demande
            "validations": validations,
        }

        # Use the stored status_code if available, otherwise default to 400
        http_status = (
            self.status_code if self.status_code else status.HTTP_400_BAD_REQUEST
        )

        return Response(response_data, status=http_status)
