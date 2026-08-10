from celery import shared_task

from apps.pharmacy.models import Medicine


@shared_task
def low_stock_alerts():
    """Notify pharmacists about low-stock medicines."""
    from apps.accounts.models import Role, User
    from apps.core.services import notify

    low = [m for m in Medicine.objects.all() if m.is_low_stock]
    if not low:
        return "No low stock"
    pharmacists = User.objects.filter(role__code=Role.CODE_PHARMACIST)
    names = ", ".join(m.name for m in low[:10])
    for pharmacist in pharmacists:
        notify(pharmacist, "Low stock alert",
               f"The following medicines are at or below reorder level: {names}",
               notification_type="low_stock", link="/pharmacy")
    return f"Alerted {pharmacists.count()} pharmacists about {len(low)} medicines"
