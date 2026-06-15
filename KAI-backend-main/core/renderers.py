from rest_framework.renderers import JSONRenderer
from django.utils import timezone
import uuid

class StandardizedJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)
            
        response = renderer_context.get('response', None)
        request = renderer_context.get('request', None)

        status_code = response.status_code if response else 200
        request_id = getattr(request, 'request_id', str(uuid.uuid4()))

        meta = {
            "status": "success" if status_code < 400 else "error",
            "code": status_code,
            "timestamp": timezone.now().isoformat(),
            "request_id": request_id
        }

        # Handling errors
        if status_code >= 400:
            errors = []
            if isinstance(data, dict):
                for field, error_list in data.items():
                    if isinstance(error_list, list):
                        for error in error_list:
                            errors.append({"field": field, "message": str(error)})
                    else:
                        errors.append({"field": field, "message": str(error_list)})
            elif isinstance(data, list):
                for error in data:
                    errors.append({"field": "non_field_errors", "message": str(error)})
            else:
                errors.append({"field": "non_field_errors", "message": str(data)})
            
            return super().render({
                "meta": meta,
                "data": None,
                "errors": errors
            }, accepted_media_type, renderer_context)

        # Handling success
        return super().render({
            "meta": meta,
            "data": data,
            "errors": None
        }, accepted_media_type, renderer_context)
