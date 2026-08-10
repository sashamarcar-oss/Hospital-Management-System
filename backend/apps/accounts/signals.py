from django.db.models.signals import post_save

from apps.accounts.models import User


def ensure_superuser_role(sender, instance, created, **kwargs):
    """Give new superusers the Super Admin role automatically."""
    if created and instance.is_superuser and not instance.role:
        from apps.accounts.models import Role

        role = Role.objects.filter(code=Role.CODE_SUPER_ADMIN).first()
        if role:
            instance.role = role
            instance.save(update_fields=["role"])


post_save.connect(ensure_superuser_role, sender=User)
