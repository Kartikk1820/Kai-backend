
**Role:** You are a Staff-Level Backend Architect and Django/Python Expert.

**Task:** Build the backend REST API for "KC Portal," an internal operating system handling Bid Tracking, Task Management (Kanban), and HRMS (Payroll/Leave). The frontend is being built entirely separately in Angular by another team. You are strictly responsible for the Django + DRF API backend, MySQL database schema, Redis/Celery asynchronous workers, and system observability.

---

### **Core System Design Philosophy (Strict Adherence Required)**

You must build this backend as a deterministic state machine. You are forbidden from writing loose CRUD endpoints where any data can be patched at any time. Adhere to the following rules:

1. **Every Action is a State Transition:** Do not use basic `UpdateAPIView` for business logic. Changing a Bid from "Drafting" to "Review" or a Task from "In Progress" to "Done" must be treated as a strict state transition via a dedicated service method or explicit API action (e.g., `POST /api/bids/{id}/transition/`).
2. **Every State has a Defined Input:** State transitions require heavily validated inputs. Use DRF Serializers strictly as Input Contracts. If a transition requires a file attachment and a comment, the serializer must enforce it before the state changes.
3. **Every Input has a Defined & Single Producer:** The API must explicitly validate *who* or *what* is producing the input.
   * *Producer: System/Celery* (e.g., 72hr automated reminder trigger).
   * *Producer: Google Sheets Webhook* (e.g., external bid update).
   * *Producer: Authenticated User via Angular* (e.g., moving a task card).
   * Ensure strict Role-Based Access Control (RBAC) at the object level so only authorized producers can trigger specific state changes.

4. **Always Provide Feedback (Observability):** Every API response must follow a strict, standardized JSON envelope. Every state transition must generate an internal Audit Log (who, what, when, previous_state, new_state) and emit structured application logs.

---

### **1. Architecture & Infrastructure Specs**

* **Framework:** Django 5.2 (LTS) + Django REST Framework 3.15.x.
* **Database:** MySQL 8.x (Primary source of truth).
* **Caching & Queues:** Redis 7.x (Broker for Celery and caching layer).
* **Async Workers:** Celery 5.x (Strictly for state transitions triggered by time, e.g., payroll runs, or external I/O, e.g., PDF generation and Resend email dispatch).
* **Authentication:** `django-allauth` for Google Workspace OAuth2 SSO + `djangorestframework-simplejwt` to provide stateless JWTs to the Angular frontend.

**Pinned Core Dependencies (use these exact major versions):**
```
Django==5.2
djangorestframework==3.15.*
celery==5.*
django-allauth==0.63.*
djangorestframework-simplejwt==5.*
django-fsm==3.*
mysqlclient==2.*
redis==5.*
structlog==24.*
weasyprint==62.*
```
Provide a `requirements.txt` as one of the deliverables.

---

### **2. Authentication Flow**

The Angular frontend authenticates via Google Workspace SSO using the following flow. You must implement all endpoints described here.

1. **Initiate SSO:** Angular redirects the user to `GET /api/auth/google/login/` — handled by `django-allauth`, which redirects to Google's OAuth2 consent screen.
2. **Callback:** Google redirects back to `GET /api/auth/google/callback/`. `django-allauth` validates the OAuth2 token and creates/retrieves the Django `User`.
3. **JWT Issuance:** After successful allauth authentication, a custom callback view issues a `simplejwt` access token + refresh token pair and redirects Angular to `{FRONTEND_URL}/auth/callback?access=<token>&refresh=<token>`.
4. **Authenticated Requests:** Angular includes `Authorization: Bearer <access_token>` on every API request. A custom DRF middleware extracts the `request_id` from this header context and injects it into every log line.
5. **Token Refresh:** `POST /api/auth/token/refresh/` — standard simplejwt endpoint.
6. **Logout:** `POST /api/auth/logout/` — blacklists the refresh token via simplejwt's token blacklist app.

---

### **3. Database Models & State Definitions**

Design the models using a Finite State Machine (FSM) approach (use `django-fsm`).

**A. User & RBAC Model:**

* Extend `AbstractUser`.
* Base Roles: `Admin`, `Employee`, `Client`.
* Sub-Positions (Employees only): `Proposal Writer`, `Senior VP`, etc.
* **Rule:** Permissions are derived dynamically from the sub-position.

**B. Bid Model:**

* **States:** `Capture`, `Drafting`, `Review`, `Submitted`, `Won`, `Lost`.
* **Producer:** Google Sheets Sync (System) OR Manual Entry (User).
* **Logic:** Changing a Bid state to `Drafting` must trigger a Celery task that acts as a Producer to create specific default Tasks in the Task Model.
* **Sync Field:** Include a `sync_status` field with values `SYNCED | PENDING | FAILED` to track Google Sheets sync state.

**C. Task Model (Kanban):**

* **States:** `To Do`, `In Progress`, `Review`, `Done`.
* **Inputs:** Assigned User, Linked Bid (optional), Deadline.
* **SLA / Escalation Logic:** The Task model must include an `is_escalated` boolean flag (not a separate state). A periodic Celery beat task runs every hour to query tasks where `deadline < now() + 24h` and `state != Done`, sets `is_escalated = True`, writes an AuditLog entry, and triggers a notification. The Angular UI uses this flag to render an "Escalated" badge.

**D. HRMS Models (Leave & Payroll):**

* **Leave States:** `Requested`, `Approved`, `Rejected`.
  * **Producer for `Approved` / `Rejected`:** Only users with the `Admin` role OR an employee's direct manager (determined by a `manager` ForeignKey on the `User` model) may trigger these transitions. RBAC must be enforced at the service layer.
* **Payroll:** Uses `WeasyPrint` for generating PDF salary slips.
* **State:** Payroll runs are triggered on the 1st of the month by Celery beat (Producer: System), transitioning employee payroll status from `Pending` to `Processed` and dispatching emails via Resend.

---

### **4. The API Contract (Angular Team Handoff)**

You must design the API to be cleanly consumed by the Angular frontend.

**A. Standardized Response Envelope:**
All endpoints must return data in this strict format. You must implement a Custom DRF Renderer to enforce this.

*Success Response:*
```json
{
  "meta": {
    "status": "success",
    "code": 200,
    "timestamp": "2024-10-24T12:00:00Z",
    "request_id": "uuid-for-log-tracing"
  },
  "data": { "...": "..." },
  "errors": null
}
```

*Error Response (validation, permission, or server errors):*
```json
{
  "meta": {
    "status": "error",
    "code": 422,
    "timestamp": "2024-10-24T12:00:00Z",
    "request_id": "uuid-for-log-tracing"
  },
  "data": null,
  "errors": [
    { "field": "attachment", "message": "A file attachment is required to move to Review." },
    { "field": "non_field_errors", "message": "Transition from Drafting to Won is not permitted." }
  ]
}
```

**B. Pagination & Filtering:**
All list endpoints (e.g., `GET /api/bids/`, `GET /api/tasks/`) must:
* Use **cursor-based pagination** (not offset-based) to handle real-time data correctly.
* Support filtering via query parameters. Examples: `?state=Drafting`, `?assigned_to=5`, `?is_escalated=true`, `?linked_bid=12`.
* Support ordering via `?ordering=-created_at`.
* Use `django-filter` for the filtering backend.

**C. Service Layer Pattern:**
Do NOT put business logic inside DRF Views/ViewSets.

* **Views:** Only handle HTTP parsing, JWT validation, and RBAC permission checks.
* **Serializers:** Only handle Input/Output validation and type coercion.
* **Services (`services.py`):** All state transitions happen here.
  * *Example:* `BidService.transition_to_review(bid_id, user, payload)`
  * The service layer is responsible for database transactions (`transaction.atomic`), emitting audit logs, and enqueuing side-effect Celery tasks.

---

### **5. Bidirectional Sync Engine (Google Sheets)**

This is the most complex state machine in the app. Implement the sync engine as follows:

* **Producer 1 (Google Sheets → KC Portal):** Define a webhook endpoint `POST /api/webhooks/google-sheets/` that accepts batched row updates. Validate the payload using **HMAC-SHA256**: Google Sheets sends an `X-Hub-Signature-256` header; the endpoint must recompute the HMAC using a shared secret stored in `settings.GOOGLE_SHEETS_WEBHOOK_SECRET` and reject any request where the signatures do not match (respond `403 Forbidden`).
* **Producer 2 (Angular User → Google Sheets):** When a user updates a Bid via the API, the Service Layer updates MySQL (the primary source of truth) and immediately enqueues a Celery task to push the mutation back to the Google Sheets API.
* **Conflict Resolution:** Implement a "Last Write Wins" strategy based on a `last_modified_timestamp` field on the Bid model. If the incoming timestamp from Google Sheets is older than the stored `last_modified_timestamp`, discard the update and log it as a conflict.
* **Feedback:** If the Celery task fails to write to Google Sheets after all retries, it must set the Bid's `sync_status` to `FAILED` and log the exception with `structlog`, so the Angular UI can display a "Sync Error" badge.

---

### **6. Observability, Logging & Feedback**

Implement a rigorous feedback loop so we always know exactly how a state was reached.

1. **Audit Model:** Create an `AuditLog` table. Every time a Service Layer method commits a state change for a Bid, Task, or Leave Request, it writes a row: `[Timestamp] | [Actor ID (User or System)] | [Model] | [Object ID] | [Old State] | [New State] | [IP Address/Context]`.
2. **Structured Logging:** Use `structlog` outputting JSON. Every log entry must include the `request_id` injected by a custom DRF middleware, allowing us to trace an Angular button click all the way through the Celery worker queue.

---

### **Deliverables Expected from You:**

1. The exact Django project app structure (folders and key files).
2. A `requirements.txt` with all pinned dependencies.
3. The Django code for the Base Models, defining the strict state fields using `django-fsm`.
4. The DRF Serializer (Input Contract) and Service Layer (State Transition) for moving a Bid from `Capture` to `Drafting`, including triggering auto-tasks via Celery.
5. The Custom DRF JSON Renderer to enforce the standardized response envelope (both success and error formats).
6. The HMAC-SHA256 webhook validation logic for the Google Sheets sync endpoint.
7. A `pytest` test for the Bid `Capture → Drafting` state transition service that:
   * Mocks the Celery task enqueue.
   * Asserts the AuditLog entry is created with the correct `old_state` and `new_state`.
   * Asserts that an unauthorized user cannot trigger the transition (RBAC check).