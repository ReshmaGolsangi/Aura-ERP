from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email to check the SMTP settings."

    def add_arguments(self, p):
        p.add_argument("to")

    def handle(self, *a, **o):
        if not getattr(settings, "EMAIL_HOST", ""):
            self.stdout.write(self.style.WARNING("No SMTP server configured: the email below only prints here, it is NOT sent."))
        try:
            send_mail("Aura ERP test email", "If you can read this, your email settings work.", settings.DEFAULT_FROM_EMAIL, [o["to"]])
        except Exception as e:
            raise CommandError(f"Email failed: {e}")
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {o['to']}"))
