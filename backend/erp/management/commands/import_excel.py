from django.core.management.base import BaseCommand, CommandError
from erp.excel_io import KINDS, import_file


class Command(BaseCommand):
    help = "Import customers / products / distributors / distributor_products from an Excel file."

    def add_arguments(self, p):
        p.add_argument("kind", choices=KINDS)
        p.add_argument("file")

    def handle(self, *a, **o):
        try:
            c, u, errs = import_file(o["kind"], o["file"])
        except Exception as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(f"Created: {c}   Updated: {u}   Skipped with errors: {len(errs)}"))
        for row, msg in errs[:25]:
            self.stdout.write(self.style.WARNING(f"  Excel row {row}: {msg}"))
