import sys

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts, Roles & Permissions"

    def ready(self):
        import apps.accounts.signals  # noqa: F401
        self._seed_default_admin()

    def _is_management_command(self):
        if len(sys.argv) < 2:
            return False
        return sys.argv[1] in {
            "makemigrations",
            "migrate",
            "collectstatic",
            "shell",
            "dbshell",
            "test",
            "startapp",
            "startproject",
            "createsuperuser",
            "changepassword",
            "flush",
            "loaddata",
            "dumpdata",
            "inspectdb",
        }

    def _seed_default_admin(self):
        if self._is_management_command():
            return

        try:
            from django.conf import settings
            from django.db.utils import OperationalError, ProgrammingError

            from apps.accounts.models import Permission, Role, User
            from apps.accounts.permission_catalog import build_catalog, permissions_for_role
        except (ImportError, OperationalError, ProgrammingError):
            return

        try:
            self._sync_permissions_and_roles(Permission, Role, build_catalog, permissions_for_role)
            self._create_admin_user(settings, User, Role)
        except Exception:
            return

    def _sync_permissions_and_roles(self, Permission, Role, build_catalog, permissions_for_role):
        catalog = build_catalog()
        for module, actions in catalog.items():
            for code, name in actions.items():
                Permission.objects.update_or_create(
                    code=code,
                    defaults={"name": name, "module": module},
                )

        for code, name in Role.ROLE_CHOICES:
            role, _ = Role.objects.update_or_create(code=code, defaults={"name": name})
            role.permissions.set(
                Permission.objects.filter(code__in=permissions_for_role(code))
            )

    def _create_admin_user(self, settings, User, Role):
        username = settings.SEED_ADMIN_USERNAME
        if not username:
            return

        admin_role = Role.objects.filter(code=Role.CODE_SUPER_ADMIN).first()
        if not admin_role:
            return

        admin, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": settings.SEED_ADMIN_EMAIL,
                "first_name": "System",
                "last_name": "Administrator",
                "is_superuser": True,
                "is_staff": True,
                "is_active": True,
                "role": admin_role,
            },
        )

        changed = False
        if created:
            admin.set_password(settings.SEED_ADMIN_PASSWORD)
            changed = True

        if not admin.is_superuser:
            admin.is_superuser = True
            changed = True
        if not admin.is_staff:
            admin.is_staff = True
            changed = True
        if not admin.is_active:
            admin.is_active = True
            changed = True
        if admin.role_id != admin_role.id:
            admin.role = admin_role
            changed = True

        if changed:
            admin.save()
