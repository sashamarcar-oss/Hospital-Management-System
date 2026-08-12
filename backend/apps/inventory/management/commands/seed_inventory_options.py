from django.core.management.base import BaseCommand

from apps.inventory.models import Supplier


DEFAULT_SUPPLIERS = [
    {
        "name": "Global Medical Supplies",
        "contact_person": "",
        "phone": "",
        "email": "",
        "address": "",
        "is_active": True,
    },
]


class Command(BaseCommand):
    help = "Create any missing default inventory suppliers without altering existing suppliers."

    def handle(self, *args, **options):
        created = 0
        for supplier in DEFAULT_SUPPLIERS:
            _, was_created = Supplier.objects.get_or_create(
                name=supplier["name"], defaults=supplier
            )
            created += was_created

        self.stdout.write(
            self.style.SUCCESS(
                f"Inventory options ready: {Supplier.objects.count()} suppliers total ({created} created)."
            )
        )
