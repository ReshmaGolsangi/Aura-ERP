from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from erp.excel_io import export_templates


class Command(BaseCommand):
    help = "Create a blank Excel file with the correct column headings for importing."

    def handle(self, *a, **o):
        out = Path(settings.BASE_DIR).parent / "exports"; out.mkdir(parents=True, exist_ok=True)
        f = out / "aura_import_template.xlsx"
        export_templates(f)
        self.stdout.write(self.style.SUCCESS(f"Template created: {f}"))
