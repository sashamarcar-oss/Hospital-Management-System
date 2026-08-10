from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.core.models import Notification


@shared_task(bind=True, max_retries=3)
def send_notification_email(self, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return

    if notification.email_sent:
        return

    try:
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient.email],
            fail_silently=True,
        )
        notification.email_sent = True
        notification.save(update_fields=["email_sent"])
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
