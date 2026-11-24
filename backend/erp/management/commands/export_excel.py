from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from erp.excel_io import export_all


class Command(BaseCommand):
    help = "Export masters, quotations, billing and purchase orders to one Excel file."

    def add_arguments(self, p):
        p.add_argument("--out", default=str(Path(settings.BASE_DIR).parent / "exports"))

    def handle(self, *a, **o):
        out = Path(o["out"]); out.mkdir(parents=True, exist_ok=True)
        f = out / f"aura_export_{datetime.now():%Y%m%d_%H%M}.xlsx"
        export_all(f)
        self.stdout.write(self.style.SUCCESS(f"Exported to {f}"))
