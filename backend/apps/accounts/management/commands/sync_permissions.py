"""Sync the permission catalog and role permissions into the database.

Usage: python manage.py sync_permissions
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import Permission, Role
from apps.accounts.permission_catalog import build_catalog, permissions_for_role


class Command(BaseCommand):
    help = "Sync the permission catalog and role permissions into the database."

    def handle(self, *args, **options):
        catalog = build_catalog()
        for module, actions in catalog.items():
            for code, name in actions.items():
                Permission.objects.update_or_create(
                    code=code, defaults={"name": name, "module": module}
                )
        for code, name in Role.ROLE_CHOICES:
            role, _ = Role.objects.update_or_create(code=code, defaults={"name": name})
            role.permissions.set(
                Permission.objects.filter(code__in=permissions_for_role(code))
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {Permission.objects.count()} permissions and {Role.objects.count()} roles."
            )
        )
