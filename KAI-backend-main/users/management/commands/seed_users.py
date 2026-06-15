from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Seeds the database with dummy user accounts'

    def handle(self, *args, **options):
        User = get_user_model()

        users_to_create = [
            {"email": "john.employee@example.com", "password": "password123", "first_name": "John", "last_name": "Doe", "role": "Employee", "sub_position": "Proposal Writer"},
            {"email": "jane.vp@example.com", "password": "password123", "first_name": "Jane", "last_name": "Smith", "role": "Employee", "sub_position": "Senior VP"},
            {"email": "client@example.com", "password": "password123", "first_name": "Acme", "last_name": "Corp", "role": "Client", "sub_position": None},
        ]

        created_count = 0
        for ud in users_to_create:
            if not User.objects.filter(email=ud["email"]).exists():
                User.objects.create_user(
                    email=ud["email"],
                    password=ud["password"],
                    first_name=ud["first_name"],
                    last_name=ud["last_name"],
                    role=ud["role"],
                    sub_position=ud["sub_position"]
                )
                self.stdout.write(self.style.SUCCESS(f"Created user: {ud['email']}"))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"User already exists: {ud['email']}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {created_count} dummy users.'))
