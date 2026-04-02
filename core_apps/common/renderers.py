import json
from typing import Any, Dict, Optional, Union

from django.utils.translation import gettext_lazy as _

from rest_framework.renderers import JSONRenderer


class GenericJSONRenderer(JSONRenderer):
    """
    Custom JSON renderer that standardizes API response format.

    This renderer wraps the response data in a consistent structure with the
    following format:
    {
        "status_code": HTTP_STATUS_CODE,
        "object_label": RESPONSE_DATA
    }

    The object_label can be customized per view by setting the `object_label`
    attribute on the view class.
    """

    charset = "utf-8"
    object_label = "object"  # Default object label if not specified in the view

    def render(
        self,
        data: Any,
        accepted_media_type: Optional[str] = None,
        renderer_context: Optional[Dict] = None,
    ) -> Union[bytes, str]:
        """
        Render the data into a standardized format.

        Args:
            data: The data to be rendered, typically from the serializer
            accepted_media_type: The media type accepted by the request
            renderer_context: Context information about the rendering process

        Returns:
            Encoded JSON string with standardized format

        Raises:
            ValueError: If response object is not found in the renderer context
        """
        # Ensure renderer_context is a dictionary
        if renderer_context is None:
            renderer_context = {}

        # Get the view to check for a custom object_label
        view = renderer_context.get("view")
        if hasattr(view, "object_label"):
            object_label = view.object_label
        else:
            object_label = self.object_label

        # Get the response object to extract the status code
        response = renderer_context.get("response")
        if not response:
            raise ValueError(_("Response not found in renderer context"))

        status_code = response.status_code

        # handle case where data is None
        # if data is None:
        #     data = {}

        # Pass error responses directly to the parent renderer
        # This preserves the error format from DRF
        errors = data.get("errors", None) if isinstance(data, dict) else None
        if errors is not None:
            return super(GenericJSONRenderer, self).render(data)

        # TODO: uncomment this and remove results key from list responses
        if isinstance(data, list):
            data = data

        # Format successful responses with our standard structure
        formatted_response = {"status_code": status_code, object_label: data}

        # Encode and return the JSON response
        return json.dumps(formatted_response).encode(self.charset)
