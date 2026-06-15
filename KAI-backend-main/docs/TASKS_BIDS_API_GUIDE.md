# Tasks & Bids API — cURL Examples

This guide covers all endpoints for the **Tasks (Kanban Board)** and **Bids** modules.

> **Prerequisites:** Obtain a JWT token first. See `API_TESTING_GUIDE.md` §2 for the full auth workflow.

```bash
# Quick token export (run this first)
TOKEN_JSON=$(curl -s -X POST http://localhost:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "john.employee@example.com", "password": "password123"}')
export TOKEN=$(echo $TOKEN_JSON | grep -o '"access":"[^"]*' | cut -d'"' -f4)
export ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin"}' \
  | grep -o '"access":"[^"]*' | cut -d'"' -f4)
```

---

## 1. Tasks Module (`/api/tasks/`)

### A. Filter Options (Sidebar Dropdowns)

```bash
# Returns assignees, linked bids, clients, and priority list for the filter panel
curl -X GET http://localhost:8000/api/tasks/filters/ \
  -H "Authorization: Bearer $TOKEN"
```

**Example response:**
```json
{
  "assignees": [
    { "id": 1, "full_name": "Admin User", "avatar_initials": "AU" }
  ],
  "linked_bids": [
    { "id": 1, "title": "Cloud Infrastructure Upgrade", "client_name": "Acme Corp" }
  ],
  "clients": [{ "id": 50, "name": "Acme Corp" }],
  "priorities": ["high", "medium", "low"]
}
```

---

### B. Kanban Board (`GET /api/tasks/board/`)

```bash
# All tasks grouped by column
curl -X GET http://localhost:8000/api/tasks/board/ \
  -H "Authorization: Bearer $TOKEN"

# My tasks only (assigned to me)
curl -X GET "http://localhost:8000/api/tasks/board/?view=mine" \
  -H "Authorization: Bearer $TOKEN"

# Filter by priority
curl -X GET "http://localhost:8000/api/tasks/board/?priority=high&priority=medium" \
  -H "Authorization: Bearer $TOKEN"

# Filter by assignee
curl -X GET "http://localhost:8000/api/tasks/board/?assignee_id=2" \
  -H "Authorization: Bearer $TOKEN"

# Search by title/description
curl -X GET "http://localhost:8000/api/tasks/board/?search=RFP" \
  -H "Authorization: Bearer $TOKEN"

# Show only overdue tasks
curl -X GET "http://localhost:8000/api/tasks/board/?overdue=true" \
  -H "Authorization: Bearer $TOKEN"

# Tasks linked to a specific bid opportunity
curl -X GET "http://localhost:8000/api/tasks/board/?bid_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response:**
```json
{
  "todo":        [ /* Task objects */ ],
  "in_progress": [ /* Task objects */ ],
  "review":      [ /* Task objects */ ],
  "done":        [ /* Task objects */ ]
}
```

---

### C. Create a Task (`POST /api/tasks/`)

```bash
# Minimal task (status defaults to 'todo', position_index defaults to 0)
curl -X POST http://localhost:8000/api/tasks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Review RFP Requirements",
    "priority": "high"
  }'

# Full task with assignee, due date, and linked bid
curl -X POST http://localhost:8000/api/tasks/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Draft Executive Summary",
    "description": "Write the executive summary for section L.",
    "priority": "high",
    "assignee_id": 2,
    "linked_bid_id": 1,
    "due_date": "2026-07-01T17:00:00Z"
  }'
```

---

### D. Update a Task (`PATCH /api/tasks/{id}/`)

```bash
# Change description
curl -X PATCH http://localhost:8000/api/tasks/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated instructions — focus on section M."}'

# Reassign to a different user
curl -X PATCH http://localhost:8000/api/tasks/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_id": 3}'

# Escalate priority
curl -X PATCH http://localhost:8000/api/tasks/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"priority": "high"}'
```

---

### E. Move a Task — Drag & Drop (`PATCH /api/tasks/{id}/move/`)

Fires when a user drags a card to a new column or position on the Kanban board.

```bash
# Move to In Progress column
curl -X PATCH http://localhost:8000/api/tasks/1/move/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress", "position_index": 0}'

# Move to Review, 3rd position
curl -X PATCH http://localhost:8000/api/tasks/1/move/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "review", "position_index": 2}'

# Mark as Done
curl -X PATCH http://localhost:8000/api/tasks/1/move/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "done", "position_index": 0}'
```

---

### F. Delete a Task (`DELETE /api/tasks/{id}/`)

```bash
curl -X DELETE http://localhost:8000/api/tasks/1/ \
  -H "Authorization: Bearer $TOKEN"
# → 204 No Content
```

---

### G. Comments

#### Add a Comment (`POST /api/tasks/{id}/comments/`)
```bash
curl -X POST http://localhost:8000/api/tasks/1/comments/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "I have started working on the executive summary."}'
```

**Example response:**
```json
{
  "id": 55,
  "task_id": 1,
  "author": { "full_name": "John Doe", "avatar_initials": "JD" },
  "body": "I have started working on the executive summary.",
  "created_at": "2026-06-08T10:00:00Z",
  "updated_at": "2026-06-08T10:00:00Z",
  "is_edited": false
}
```

#### Delete a Comment (`DELETE /api/tasks/{task_id}/comments/{comment_id}/`)
```bash
curl -X DELETE http://localhost:8000/api/tasks/1/comments/55/ \
  -H "Authorization: Bearer $TOKEN"
# → 204 No Content
```

---

## 2. Bids Module (`/api/bids/`)

### A. Filter Options (Sidebar Dropdowns)

```bash
# Returns clients, writers, presales staff, states, categories, and statuses
curl -X GET http://localhost:8000/api/bids/filter-options/ \
  -H "Authorization: Bearer $TOKEN"
```

**Example response:**
```json
{
  "clients":    [ { "id": 1, "name": "Alpha Corp", "shortcode": "ALP" } ],
  "writers":    [ { "id": 2, "full_name": "John Doe", "email": "john.employee@example.com", "avatar_initials": "JD" } ],
  "presales":   [ { "id": 1, "full_name": "Admin User", "email": "admin@example.com", "avatar_initials": "AU" } ],
  "states":     ["CA", "NY", "TX", "FL", "WA"],
  "categories": ["IT Services", "Consulting", "Construction"],
  "statuses":   ["in_progress", "submitted", "no_go", "unsubmitted", "cancelled", "postponed"]
}
```

---

### B. List Opportunities — Grouped View (`GET /api/bids/opportunities/`)

Each opportunity includes its nested `client_bids` array.

```bash
# All opportunities (grouped with nested submissions)
curl -X GET http://localhost:8000/api/bids/opportunities/ \
  -H "Authorization: Bearer $TOKEN"

# Filter by US state
curl -X GET "http://localhost:8000/api/bids/opportunities/?state=WA" \
  -H "Authorization: Bearer $TOKEN"

# Filter by category
curl -X GET "http://localhost:8000/api/bids/opportunities/?category=IT+Services" \
  -H "Authorization: Bearer $TOKEN"

# Filter by submission status (can repeat for multiple)
curl -X GET "http://localhost:8000/api/bids/opportunities/?status=in_progress&status=submitted" \
  -H "Authorization: Bearer $TOKEN"

# Filter by assigned writer
curl -X GET "http://localhost:8000/api/bids/opportunities/?writer_id=2" \
  -H "Authorization: Bearer $TOKEN"

# Filter by client
curl -X GET "http://localhost:8000/api/bids/opportunities/?client_id=1" \
  -H "Authorization: Bearer $TOKEN"

# Filter by due date range
curl -X GET "http://localhost:8000/api/bids/opportunities/?date_from=2026-06-01&date_to=2026-07-31" \
  -H "Authorization: Bearer $TOKEN"

# Search by title or agency
curl -X GET "http://localhost:8000/api/bids/opportunities/?search=Cloud" \
  -H "Authorization: Bearer $TOKEN"
```

---

### C. Create a Bid Opportunity (`POST /api/bids/opportunities/`)

```bash
curl -X POST http://localhost:8000/api/bids/opportunities/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agency": "Department of Energy",
    "title": "Renewable Grid Consulting",
    "solicitation_number": "DOE-2026-RFP-099",
    "state": "TX",
    "due_date": "2026-07-01T00:00:00Z",
    "bid_link": "https://sam.gov/opp/example",
    "category": "Consulting",
    "pre_bid_info": "Attend pre-bid meeting on June 20.",
    "qa_notes": ""
  }'
# → 201 Created — returns BidOpportunity with empty client_bids []
```

---

### D. Get Single Opportunity (`GET /api/bids/opportunities/{id}/`)

```bash
curl -X GET http://localhost:8000/api/bids/opportunities/1/ \
  -H "Authorization: Bearer $TOKEN"
```

---

### E. Flat List of All Submissions (`GET /api/bids/client-bids/`)

Returns all `ClientBid` records as a flat list (used in the "flat" view mode). Supports the same filter params as `/opportunities/`, plus direct status/writer/client filters.

```bash
# All client bids flat
curl -X GET http://localhost:8000/api/bids/client-bids/ \
  -H "Authorization: Bearer $TOKEN"

# Only submitted
curl -X GET "http://localhost:8000/api/bids/client-bids/?status=submitted" \
  -H "Authorization: Bearer $TOKEN"

# By writer
curl -X GET "http://localhost:8000/api/bids/client-bids/?writer_id=2" \
  -H "Authorization: Bearer $TOKEN"
```

---

### F. Update a Client Bid Submission (`PATCH /api/bids/client-bids/{id}/`)

```bash
# Change status to submitted
curl -X PATCH http://localhost:8000/api/bids/client-bids/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "submitted"}'

# Assign a writer
curl -X PATCH http://localhost:8000/api/bids/client-bids/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"writer_id": 2}'

# Update portal credentials and submission method
curl -X PATCH http://localhost:8000/api/bids/client-bids/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "portal_username": "alpha_portal_user",
    "portal_password": "s3cur3pass",
    "submission_method": "portal"
  }'

# Set internal deadline and add a comment
curl -X PATCH http://localhost:8000/api/bids/client-bids/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "internal_deadline": "2026-06-28T17:00:00Z",
    "comments": "Draft submitted to writer. Awaiting review."
  }'

# Mark as No Go
curl -X PATCH http://localhost:8000/api/bids/client-bids/1/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "no_go"}'
```

---

### G. Sync Status — Polled every 60s (`GET /api/bids/sync-status/`)

```bash
curl -X GET http://localhost:8000/api/bids/sync-status/ \
  -H "Authorization: Bearer $TOKEN"
```

**Example response:**
```json
{
  "last_synced": "2026-06-08T07:00:00Z",
  "is_syncing": false,
  "sync_errors": []
}
```

---

### H. Trigger Manual Sync (`POST /api/bids/sync-now/`)

```bash
curl -X POST http://localhost:8000/api/bids/sync-now/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
# → 202 Accepted: {"message": "Sync started."}
```

---

## 3. Valid Enum Values (Quick Reference)

### Task Status (for `/move/` endpoint)
| Value | Description |
|-------|-------------|
| `todo` | To Do column |
| `in_progress` | In Progress column |
| `review` | Review column |
| `done` | Done column |

### Task Priority
| Value |
|-------|
| `high` |
| `medium` |
| `low` |

### ClientBid Status
| Value | Description |
|-------|-------------|
| `in_progress` | Actively being worked on |
| `submitted` | Submitted to agency |
| `no_go` | Decided not to bid |
| `unsubmitted` | Missed deadline / not submitted |
| `cancelled` | RFP was cancelled |
| `postponed` | Submission postponed |

### ClientBid Submission Method
| Value |
|-------|
| `portal` |
| `physical` |
| `email` |
| `portal_and_physical` |
| `fax` |
| `email_and_physical` |
