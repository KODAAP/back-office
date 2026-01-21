from django.core.mail import send_mail

from celery import shared_task


@shared_task
def send_email_task(subject, message, recipient_list, from_email=None, **kwargs):
    """Tâche asynchrone pour envoyer des emails"""
    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        **kwargs,
    )
