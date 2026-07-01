# How to Add a New Permission

Reference guide. Uses `bid.create_opportunity` as worked example throughout.

---

## Step 1 — Add key constant + CATALOG entry

**File:** `core/permissions_catalog.py`

```python
# 1a. Add constant near related keys
BID_CREATE_OPPORTUNITY = 'bid.create_opportunity'

# 1b. Add to CATALOG dict (creates a new group if needed)
CATALOG = {
    # ... existing groups ...
    'Bids': [
        (BID_CREATE_OPPORTUNITY, 'Create new bid opportunities'),
    ],
}
```

`ALL_KEYS` is auto-computed from `CATALOG` — no extra step. Admin gets it automatically.

---

## Step 2 — Assign to role bundles

Still in `core/permissions_catalog.py`:

```python
ROLE_BUNDLES = {
    'Employee': [
        # omit — employees cannot create opportunities
    ],
    'Manager': [
        # ... existing keys ...
        BID_CREATE_OPPORTUNITY,
    ],
    'Admin': list(ALL_KEYS),  # gets it automatically
}
```

Then re-seed the DB (safe to run on live data — uses update_or_create):

```bash
python manage.py seed_rbac
```

---

## Step 3 — Enforce on the backend view

**File:** `bids/views.py` (or whichever app owns the endpoint)

```python
from core.permissions import HasPermissionKey

class BidOpportunityListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), HasPermissionKey.of('bid.create_opportunity')()]
        return [IsAuthenticated()]
```

Users without the key get **403 Forbidden** with the standard error envelope.

---

## Step 4 — Storage (nothing new needed)

Keys are plain strings in existing JSONFields:

| Table / field | Contains |
|---|---|
| `core_role.permission_keys` | `["bid.create_opportunity", ...]` after seed |
| `users_user.extra_permissions` | Individual grants (e.g. one Employee given access) |
| `users_user.revoked_permissions` | Individual revokes (e.g. a Manager had it removed) |

No migration required.

---

## Step 5 — Frontend: permission arrives automatically

`/auth/me/` already returns `permissions: sorted(user.effective_permissions())`.
After seed_rbac, any Manager logging in will see `"bid.create_opportunity"` in that list.

---

## Step 6 — Gate UI elements in Angular

**Component TS:**

```typescript
import { PermissionService } from '../../core/services/permission.service';

constructor(private permService: PermissionService) {}

get canCreateOpportunity(): boolean {
  return this.permService.can('bid.create_opportunity');
}
```

**Template:**

```html
<button *ngIf="canCreateOpportunity" (click)="openNewBidModal()">
  + New Bid Opportunity
</button>
```

`PermissionService.can(key)` checks `AuthService.has(key)` which reads
`currentUser.permissions.includes(key)`. Admin short-circuits at `user_type === 'admin'`.

---

## Checklist

- [ ] Constant + CATALOG entry in `core/permissions_catalog.py`
- [ ] Key added to correct `ROLE_BUNDLES` entries
- [ ] `python manage.py seed_rbac` run in every environment
- [ ] `HasPermissionKey.of(...)` on the backend view
- [ ] `permService.can(...)` guarding UI button/route
- [ ] Test added in `core/tests/test_rbac.py`

---

## Effective permissions formula

```
effective = (union of all assigned Role.permission_keys)
          + user.extra_permissions
          - user.revoked_permissions

# Admin / superuser: skip formula → return ALL_KEYS
```
