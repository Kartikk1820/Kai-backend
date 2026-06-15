# KC Portal - API Contract

To provide a consistent and predictable interface for the Angular frontend team, this backend implements a strict API JSON Envelope.

## Standardized JSON Envelope

Every API response, whether successful or an error, will follow the exact same structural format. This is enforced globally by the `StandardizedJSONRenderer` in the `core` app.

### Success Response Example

```json
{
  "meta": {
    "status": "success",
    "code": 200,
    "timestamp": "2024-10-24T12:00:00Z",
    "request_id": "8f8b89d4-1a35-4e78-90b1-123456789abc"
  },
  "data": {
    "id": 1,
    "title": "Government Bid 2025",
    "state": "Drafting"
  },
  "errors": null
}
```

### Error Response Example

```json
{
  "meta": {
    "status": "error",
    "code": 422,
    "timestamp": "2024-10-24T12:05:00Z",
    "request_id": "8f8b89d4-1a35-4e78-90b1-123456789abc"
  },
  "data": null,
  "errors": [
    { "field": "comment", "message": "This field is required to transition to Drafting." },
    { "field": "non_field_errors", "message": "You do not have permission to perform this action." }
  ]
}
```

## Pagination

List endpoints use **Cursor-Based Pagination** by default (`rest_framework.pagination.CursorPagination`) to ensure data stability when polling or when records are rapidly changing.

## Observability & Request Tracing

Notice the `request_id` in the `meta` object above. 
The backend middleware automatically injects a `X-Request-ID` header (or generates one if absent) and attaches it to:
1. All API Responses.
2. The `structlog` context (meaning every application log generated during that request contains the ID).

This allows seamless end-to-end tracing from an Angular user action through the API down to async Celery workers.
