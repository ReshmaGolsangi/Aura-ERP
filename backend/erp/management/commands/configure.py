"""Asks questions in the terminal and saves the answers to backend/.env (used by the CONFIGURE .bat files)."""
import getpass
from django.core.management.base import BaseCommand
from erp.envfile import read_env, write_env

GROUPS = {
    "company": [
        ("COMPANY_NAME", "Company name", ""), ("COMPANY_ADDRESS", "Address (type | for a new line)", ""),
        ("COMPANY_GSTIN", "GSTIN", ""), ("COMPANY_STATE", "Your state (e.g. Maharashtra) - decides CGST/SGST vs IGST", ""),
        ("COMPANY_EMAIL", "Company email", ""), ("COMPANY_PHONE", "Phone", ""),
        ("COMPANY_BANK", "Bank details (type | between lines)", ""), ("COMPANY_LOGO", "Logo file full path (optional, PNG/JPG)", "")],
    "email": [
        ("EMAIL_HOST", "SMTP server (Gmail: smtp.gmail.com, Office365: smtp.office365.com)", ""),
        ("EMAIL_PORT", "SMTP port (587 normally, 465 for SSL)", ""), ("EMAIL_HOST_USER", "SMTP username (your email)", ""),
        ("EMAIL_HOST_PASSWORD", "SMTP password / app password", "secret"), ("DEFAULT_FROM_EMAIL", "Send emails from (address)", "")],
    "whatsapp": [
        ("WHATSAPP_TOKEN", "WhatsApp Cloud API access token", "secret"), ("WHATSAPP_PHONE_ID", "WhatsApp phone number ID", "")],
}
TIPS = {"email": "Gmail needs an App Password (Google Account > Security > App passwords), not your normal password.",
        "whatsapp": "Leave blank to skip. Without these the Send button gives a WhatsApp chat link instead."}


class Command(BaseCommand):
    help = "Interactive configuration: company | email | whatsapp"

    def add_arguments(self, p):
        p.add_argument("group", choices=list(GROUPS))

    def handle(self, *a, **o):
        env = read_env()
        self.stdout.write(TIPS.get(o["group"], "") + "\nPress Enter to keep the value shown in [brackets].\n")
        for key, label, flag in GROUPS[o["group"]]:
            cur = env.get(key, "")
            shown = "hidden" if (flag == "secret" and cur) else cur.replace("\\n", " | ")
            prompt = f"{label} [{shown}]: " if cur else f"{label}: "
            val = (getpass.getpass(prompt) if flag == "secret" else input(prompt)).strip()
            if val:
                env[key] = val.replace("|", "\\n") if key == "COMPANY_ADDRESS" else val
        write_env(env)
        self.stdout.write(self.style.SUCCESS("Saved. Restart the app (close the black windows and run START_APP.bat) to apply."))
