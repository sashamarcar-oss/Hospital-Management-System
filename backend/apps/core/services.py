from django.db import transaction

from apps.core.models import AuditLog, Notification


def audit_log(
    user,
    action,
    module,
    record="",
    object_id=None,
    request=None,
    previous_value=None,
    new_value=None,
    description="",
):
    """Create an audit log entry for a sensitive action."""
    ip_address = None
    user_agent = ""
    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

    return AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        record=record[:255],
        object_id=object_id,
        ip_address=ip_address,
        user_agent=user_agent,
        previous_value=previous_value,
        new_value=new_value,
        description=description,
    )


def notify(recipient, title, message, notification_type=Notification.TYPE_GENERAL, link="", related_module="", related_object_id=None, priority=Notification.PRIORITY_NORMAL):
    """Persist an in-app notification and queue email only after its transaction commits."""
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        type=notification_type,
        link=link,
        related_module=related_module,
        related_object_id=related_object_id,
        priority=priority,
    )
    transaction.on_commit(lambda notification_id=notification.id: _queue_notification_email(notification_id))
    return notification


def _queue_notification_email(notification_id):
    try:
        from apps.core.tasks import send_notification_email

        send_notification_email.apply_async(args=[notification_id], retry=False)
    except Exception:
        # In-app delivery is already committed; email can be retried independently.
        pass


def notify_many(recipients, title, message, notification_type=Notification.TYPE_GENERAL, link=""):
    with transaction.atomic():
        for recipient in recipients:
            notify(recipient, title, message, notification_type, link)
