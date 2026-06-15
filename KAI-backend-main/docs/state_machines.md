# KC Portal - Finite State Machines (FSM)

The KC Portal backend operates fundamentally as a deterministic state machine. We do not use loose CRUD endpoints. Instead, states transition only via designated **Service Layer** methods enforcing strict rules.

We use `django-fsm` under the hood to manage state fields.

## 1. Bid State Machine

**Model:** `bids.models.Bid`

**Allowed States:**
- `Capture`
- `Drafting`
- `Review`
- `Submitted`
- `Won`
- `Lost`

**Transitions:**
- `Capture` -> `Drafting`: Requires a valid comment and kickoff date. Dispatches a Celery task to auto-generate baseline kanban tasks.
- `Drafting` -> `Review`
- `Review` -> `Submitted`
- `Submitted` -> `Won` or `Lost`

*Note: The Bid model also tracks `sync_status` (`SYNCED`, `PENDING`, `FAILED`) to manage bidirectional data flow with Google Sheets.*

## 2. Task State Machine (Kanban)

**Model:** `tasks.models.Task`

**Allowed States:**
- `To Do`
- `In Progress`
- `Review`
- `Done`

**SLA Escalation:** 
Tasks do not have an `Escalated` state. Instead, they use a boolean flag `is_escalated = True`. This is evaluated by an hourly Celery beat job checking if a task is nearing its deadline and not yet `Done`.

## 3. Leave Request State Machine (HRMS)

**Model:** `hrms.models.LeaveRequest`

**Allowed States:**
- `Requested`
- `Approved`
- `Rejected`

**Access Control:**
Transitions to `Approved` or `Rejected` require the actor to be an `Admin` or the employee's direct `manager` (enforced at the Service layer).

---

## Audit Logs

Any successful state transition on the models above is recorded in the `core_auditlog` table. This provides a rigorous paper trail:
- **Timestamp**
- **Actor** (User ID, or 'System'/'Celery')
- **Old State** & **New State**
- **Payload Context**
