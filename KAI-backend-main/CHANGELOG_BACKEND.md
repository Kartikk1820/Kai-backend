# KAI Portal — Backend Changes (v0.1)

This pass implements the **foundation + Tasks module + HRMS module** per the agreed spec.

## Foundation
- **Settings**: fully environment-driven (python-decouple). PostgreSQL via `DATABASE_URL`.
  Secrets, DEBUG, hosts, CORS, JWT lifetimes, Celery, email all from env. Production
  hardening (HSTS, secure cookies) auto-applies when `DEBUG=False`.
- **CORS**: lightweight built-in middleware (no extra dependency).
- **Standardized errors**: custom DRF exception handler so every error flows through the
  `{ meta, data, errors }` envelope.
- **Pagination**: `StandardCursorPagination`.

## RBAC (new)
- `core.permissions_catalog`: fixed catalog of atomic permission keys, grouped by module.
- `core.models.Role` + `UserRole`: roles are bundles of permission keys; users hold many roles.
- `User.effective_permissions()`: union of role perms + per-user grants − revokes.
  Admins implicitly hold every key.
- `core.permissions.HasPermissionKey` / `HasAnyPermissionKey`: DRF permission classes.
- `/auth/me/` returns the user's effective permissions (frontend stops fabricating them).
- Manager rights stack with role rights (relationship OR permission), enforced in services.
- `seed_rbac` management command seeds Employee / Manager / HR Manager / Admin.

## Users / Auth
- `User`: added `Manager` role, `must_change_password`, per-user `extra_permissions` /
  `revoked_permissions`, `full_name`/`avatar_initials` helpers.
- First-login forced password change; admin-only user creation; admin password reset.
- Admin user & role CRUD endpoints under `/auth/admin/...`.

## Tasks (rebuilt end-to-end)
- Models: `Team`, `Task` (FSM, `KAI-###` keys via `TaskKeyCounter`), `Comment`,
  `Attachment` (media/), `TaskLink` (relates_to / blocks / is_blocked_by, mirrored).
- **Guarded FSM**: all status changes go through `TaskService.transition` — drag and
  buttons both call it. Illegal jumps are rejected; admin override is audited.
  Blocking requires a reason. (The old direct-status-write path is gone.)
- Neighbour-based ordering (`reorder`) — no full renumber.
- Board endpoint returns all five columns in one query (N+1-safe with annotations).
- Object-level permissions on edit/delete (reporter/assignee/admin/manager).
- Comments add/edit/delete; attachments upload/download/delete; links add/remove.
- Teams CRUD + membership (Admin + Manager via `team.manage`).
- Removed the phantom `Bid` service/task that referenced a non-existent model.

## HRMS (rebuilt)
- **Leave**: approval is atomic — decrements balance, writes `leave` attendance rows,
  audits, and notifies. Approver = Admin/HR (permission) OR direct manager.
- **Attendance**: simple clock in/out; overnight-safe working-hours; admin mark.
  (Late detection & overtime removed per decision.)
- **Payroll**: `PayrollRun` + idempotent `PayrollRecord` (unique per employee/month/
  year/type). Salary = base − advance recovery − unpaid-leave deduction. Celery task
  runs on the 1st for the previous month.
- **Incentives** (new): one per employee/month (mergeable); scheduler (15th) + send-now;
  generates an incentive slip; notifies.
- **PDF slips**: rendered via Playwright (headless Chromium) for full-CSS, web-font
  accurate output on the KAI theme, with a dependency-free minimal-PDF fallback if the
  browser isn't installed. One-time setup: `playwright install --with-deps chromium`.
- Leave balances are fixed annual buckets, editable by Admin/Manager.

## Notifications (new app)
- In-app notifications with unread count, list, mark-read / mark-all-read.
- Triggers: leave approved/rejected, leave submitted (→ manager), incentive granted/sent,
  task assigned. Email path is a dormant interface (console backend by default).

## Infra
- `docker-compose.yml`: Postgres 16 + Redis 7 + web + celery + celery-beat.
- `Dockerfile`: Postgres + WeasyPrint system libs.
- `.env.example` provided.

## Tests
- `tasks/tests/test_tasks.py` and `hrms/tests/test_hrms.py` — 10 tests, all passing,
  covering FSM guards, admin override, audit, atomic leave, payroll idempotency, incentives.
