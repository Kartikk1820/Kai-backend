from django.core.management.base import BaseCommand
from core.models import UserTypePermissions
from core.permissions_catalog import (
    BID_VIEW_OPPORTUNITY, BID_VIEW_BID,
    HR_VIEW_PRESENCE_ALL, HR_VIEW_DIRECTORY_TEAM,
    ROLE_BUNDLES,
)

DEFAULTS = {
    'Employee': [BID_VIEW_OPPORTUNITY, BID_VIEW_BID, HR_VIEW_PRESENCE_ALL, HR_VIEW_DIRECTORY_TEAM],
    'Manager':  list(ROLE_BUNDLES['Manager']),
    'Client':   [],
}


class Command(BaseCommand):
    help = "Seed default permission keys for each user_type into UserTypePermissions."

    def handle(self, *args, **options):
        for user_type, keys in DEFAULTS.items():
            obj, created = UserTypePermissions.objects.update_or_create(
                user_type=user_type,
                defaults={'permission_keys': list(keys)},
            )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} {user_type} ({len(keys)} perms)"
            ))
        self.stdout.write(self.style.SUCCESS("seed_user_type_permissions complete."))
