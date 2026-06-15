from django.core.management.base import BaseCommand
from core.models import Role
from core.permissions_catalog import ROLE_BUNDLES


class Command(BaseCommand):
    help = "Seed the system roles (Employee, Manager, HR Manager, Admin) with permission bundles."

    def handle(self, *args, **options):
        for name, keys in ROLE_BUNDLES.items():
            role, created = Role.objects.update_or_create(
                name=name,
                defaults={'permission_keys': list(keys), 'is_system': True,
                          'description': f'System role: {name}'},
            )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} role: {name} ({len(keys)} perms)"))
        self.stdout.write(self.style.SUCCESS("RBAC seed complete."))
