# API Testing Guide

This guide explains how to test the KAI Portal API, including the JWT authentication workflow and the various HRMS modules (Attendance, Leave, Payroll).

## 1. Swagger UI Documentation
The API documentation is automatically generated and provides an interactive interface for testing endpoints.
You can access it at: **http://localhost:8000/api/schema/swagger-ui/**

---

## 2. Authentication Workflow

The API uses JSON Web Tokens (JWT) for authentication. Here is how to test endpoints that require you to be logged in (like `/auth/user/me/` or HRMS routes).

### Step 1: Obtain a Token
1. Go to the Swagger UI at `http://localhost:8000/api/schema/swagger-ui/`.
2. Scroll down to the **`auth`** section and find the `POST /auth/login/` endpoint.
3. Click **Try it out**.
4. In the "Request body", enter the email and password of one of the test accounts (see below).
   ```json
   {
     "email": "john.employee@example.com",
     "password": "password123"
   }
   ```
5. Click **Execute**.
6. In the Server response, you will receive a JSON object containing an `"access"` token and a `"refresh"` token. Copy the long string inside the `"access"` token (without the quotes).

### Step 2: Authorize in Swagger UI
1. Scroll to the very top of the Swagger UI page.
2. Click the green **Authorize** button (or the padlock icon next to any secured endpoint).
3. In the "Value" field, type `Bearer ` followed by a space, and then paste your access token.
   - Example: `Bearer eyJhbGciOiJIUzI1NiIsInR5c...`
4. Click **Authorize** and then **Close**.

---

## 3. Testing via cURL (Examples)

If you prefer testing directly from your terminal, here are examples for all major workflows.

### A. Authentication
First, retrieve your token and export it as a variable so you can use it in subsequent requests:
```bash
# Login to get the token
TOKEN_JSON=$(curl -s -X POST http://localhost:8000/auth/login/ -H "Content-Type: application/json" -d '{"email": "john.employee@example.com", "password": "password123"}')
export TOKEN=$(echo $TOKEN_JSON | grep -o '"access":"[^"]*' | cut -d'"' -f4)

# Test token via the "Me" endpoint
curl -X GET http://localhost:8000/auth/user/me/ -H "Authorization: Bearer $TOKEN"
```

### B. Attendance Module
```bash
# Clock In
curl -X POST http://localhost:8000/api/hrms/attendance/clock-in/ -H "Authorization: Bearer $TOKEN"

# Clock Out (Calculates working hours automatically)
curl -X POST http://localhost:8000/api/hrms/attendance/clock-out/ -H "Authorization: Bearer $TOKEN"

# View Attendance History
curl -X GET http://localhost:8000/api/hrms/attendance/records/ -H "Authorization: Bearer $TOKEN"
```

### C. Leave Management Module
```bash
# Check Leave Quotas (Dynamically generates the 12 sick / 12 casual / 15 earned balance)
curl -X GET http://localhost:8000/api/hrms/leave/balance/ -H "Authorization: Bearer $TOKEN"

# Apply for Leave
curl -X POST http://localhost:8000/api/hrms/leave/requests/apply/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"leave_type": "casual", "from_date": "2026-07-01", "to_date": "2026-07-02", "total_days": 2.0, "reason": "Family Trip"}'

# Admin Only: Approve or Reject a Leave Request
curl -X PATCH http://localhost:8000/api/hrms/leave/requests/1/status/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'
```

### D. Payroll & Compensation Module
```bash
# Apply for Salary Advance
curl -X POST http://localhost:8000/api/hrms/payroll/advances/apply/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": "5000.00", "reason": "Medical emergency", "proposed_recovery_months": 2, "monthly_recovery_amount": "2500.00"}'

# Admin Only: Create Compensation Profile
curl -X POST http://localhost:8000/api/hrms/payroll/compensation/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"employee_id": 8, "monthly_base_salary": "25000.00", "overtime_multiplier": "2.0"}'

# Admin Only: Trigger Automated Payroll Run (Calculates Overtime & Deductions)
curl -X POST http://localhost:8000/api/hrms/payroll/run/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"month": 6, "year": 2026}'

# View Generated Payroll Slips
curl -X GET http://localhost:8000/api/hrms/payroll/slips/ -H "Authorization: Bearer $TOKEN"

# Download PDF Salary Slip
curl -X GET http://localhost:8000/api/hrms/payroll/slips/1/download/ -H "Authorization: Bearer $TOKEN" --output slip.pdf
```

### E. Employee Directory Module
```bash
# Admin Only: List All Employees (includes compensation and leave balances)
curl -X GET http://localhost:8000/api/hrms/view_employee/ -H "Authorization: Bearer $ADMIN_TOKEN"

# Admin Only: View Specific Employee Details
curl -X GET http://localhost:8000/api/hrms/view_employee/8/ -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 4. Generating Test Accounts (Dummy Users)

If you need to quickly populate the database with test accounts for frontend testing, you can use the **Seed Dummy Users** utility. This logic is built into the backend using a custom Django Management Command.

### Option 1: Via the Django Admin Panel (Recommended)
1. Go to the Django Admin portal at `http://localhost:8000/admin/`.
2. Log in using the superuser credentials (`admin@example.com` / `admin`).
3. Click on **Users** under the USERS section to view the list of accounts.
4. In the top right corner, click the green **"Seed Dummy Users"** button.
5. The system will automatically generate the dummy accounts and flash a success message.

### Option 2: Via the Terminal
If you are working in the terminal or inside Docker, you can trigger the custom management command directly:
```bash
docker-compose exec web python manage.py seed_users
```

### The Generated Accounts
The utility will create the following accounts (if they don't already exist). The password for all generated dummy accounts is **`password123`**.

| Email | Role | Sub-position | Name | Password |
|-------|------|--------------|------|----------|
| `john.employee@example.com` | Employee | Proposal Writer | John Doe | `password123` |
| `jane.vp@example.com` | Employee | Senior VP | Jane Smith | `password123` |
| `client@example.com` | Client | (None) | Acme Corp | `password123` |
| `admin@example.com` | Superuser | (None) | Admin | `admin` |
