import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kc_portal.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from hrms.models import LeaveRequest

User = get_user_model()
manager = User.objects.filter(role='Manager').first() or User.objects.create_user(email='manager@example.com', password='pw', role='Manager')

client = APIClient()
client.force_authenticate(user=manager)

response = client.post('/api/hrms/leave/requests/apply/', {
    'leave_type': 'sick',
    'from_date': '2026-06-20',
    'to_date': '2026-06-21',
    'total_days': 2,
    'reason': 'Test reason'
})

print("Status:", response.status_code)
print("Data:", response.json() if response.status_code in [200, 201, 400] else response.content)
