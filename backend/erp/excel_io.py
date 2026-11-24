"""Excel import / export (openpyxl). Export sheets use the same headers as import, so you can round-trip."""
from datetime import datetime
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import (Customer, Distributor, DistributorProduct, Product, ProformaInvoice,
                     PurchaseOrder, Quotation, Receipt)

# (header text in Excel, model field). First column is the unique key used to update existing rows.
IMPORTS = {
    "customers": dict(sheet="Customers", model=Customer, key="name", cols=[
        ("Name", "name"), ("Contact Person", "contact_person"), ("Phone", "phone"), ("Email", "email"),
        ("GSTIN", "gstin"), ("Address", "address"), ("City", "city"), ("State", "state")]),
    "products": dict(sheet="Products", model=Product, key="code", cols=[
        ("Code", "code"), ("Name", "name"), ("HSN/SAC", "hsn_sac"), ("Unit Price", "unit_price"),
        ("GST %", "gst_percent"), ("Active", "is_active"), ("Description", "description")]),
    "distributors": dict(sheet="Distributors", model=Distributor, key="name", cols=[
        ("Name", "name"), ("Contact Person", "contact_person"), ("Phone", "phone"), ("Email", "email"),
        ("GSTIN", "gstin"), ("Address", "address"), ("State", "state")]),
}
DP_SHEET, DP_HEADERS = "Distributor Products", ["Distributor", "Product Code", "Cost Price"]
KINDS = list(IMPORTS) + ["distributor_products"]


# ----------------------------- export -----------------------------
def _cell(v):
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime) and timezone.is_aware(v):
        return timezone.localtime(v).replace(tzinfo=None)
    return v


def _sheet(wb, title, headers, rows):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E3A5F")
    for r in rows:
        ws.append([_cell(v) for v in r])
    ws.freeze_panes = "A2"
    for i, h in enumerate(headers, 1):
        longest = max([len(str(h))] + [len(str(ws.cell(row=r, column=i).value or "")) for r in range(2, min(ws.max_row, 200) + 1)])
        ws.column_dimensions[get_column_letter(i)].width = min(longest + 2, 50)


def _new_wb():
    wb = Workbook()
    wb.remove(wb.active)
    return wb


def export_all(path):
    """Everything in one workbook: masters (re-importable) + quotations, billing and purchase orders."""
    wb = _new_wb()
    for spec in IMPORTS.values():
        fields = [f for _, f in spec["cols"]]
        _sheet(wb, spec["sheet"], [h for h, _ in spec["cols"]], ([getattr(o, f) for f in fields] for o in spec["model"].objects.all()))
    _sheet(wb, DP_SHEET, DP_HEADERS, ([d.distributor.name, d.product.code, d.cost_price]
           for d in DistributorProduct.objects.select_related("distributor", "product")))

    qrows = []
    for q in Quotation.objects.select_related("customer", "owner"):
        r = q.latest_revision   # only the latest revision, same as the funnel
        qrows.append([q.number, f"R{r.rev_no}" if r else "", q.customer.name, q.owner.username, q.get_status_display(),
                      q.is_hot, q.expected_close_date, r.subtotal if r else 0, r.tax_total if r else 0,
                      r.grand_total if r else 0, q.po_number, q.created_at])
    _sheet(wb, "Quotations", ["Number", "Latest Rev", "Customer", "Owner", "Status", "Hot", "Expected Close",
                              "Subtotal", "GST", "Total", "Customer PO", "Created"], qrows)
    _sheet(wb, "Proformas", ["Number", "Quotation", "Customer", "Date", "Total", "Paid", "Balance"],
           ([p.number, p.quotation.number, p.quotation.customer.name, p.issue_date, p.total, p.paid, p.balance]
            for p in ProformaInvoice.objects.select_related("quotation__customer", "revision")))
    _sheet(wb, "Receipts", ["Number", "Proforma", "Customer", "Amount", "Mode", "Reference", "Date"],
           ([r.number, r.proforma.number, r.proforma.quotation.customer.name, r.amount, r.mode, r.reference, r.received_on]
            for r in Receipt.objects.select_related("proforma__quotation__customer")))
    _sheet(wb, "Purchase Orders", ["Number", "Distributor", "Date", "Status", "Subtotal", "GST", "Total"],
           ([p.number, p.distributor.name, p.order_date, p.get_status_display(), p.subtotal, p.tax_total, p.grand_total]
            for p in PurchaseOrder.objects.select_related("distributor")))
    wb.save(path)


def export_templates(path):
    """Blank workbook with just the headers for each importable sheet."""
    wb = _new_wb()
    for spec in IMPORTS.values():
        _sheet(wb, spec["sheet"], [h for h, _ in spec["cols"]], [])
    _sheet(wb, DP_SHEET, DP_HEADERS, [])
    wb.save(path)


# ----------------------------- import -----------------------------
def _coerce(model, field, v):
    """Convert an Excel cell to the right Python type. Blank cells return None (= leave unchanged)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    f = model._meta.get_field(field)
    if isinstance(f, models.DecimalField):
        return Decimal(str(v).replace(",", "").strip())
    if isinstance(f, models.BooleanField):
        return str(v).strip().lower() in ("1", "true", "yes", "y", "active")
    if isinstance(v, float) and v.is_integer():
        v = int(v)          # phone numbers arrive as 9.8e9 floats
    return str(v).strip()


def _read(path, sheet):
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet in wb.sheetnames else wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header = [str(h).strip().lower() if h is not None else "" for h in next(rows)]
    except StopIteration:
        header = []
    return header, rows


def import_file(kind, path):
    """Returns (created, updated, errors[(excel_row, message)]). Bad rows are skipped, good rows saved."""
    created = updated = 0
    errors = []
    if kind == "distributor_products":
        header, rows = _read(path, DP_SHEET)
        want = [h.lower() for h in DP_HEADERS]
        if not all(h in header for h in want):
            raise ValueError("Columns needed: " + ", ".join(DP_HEADERS))
        ix = [header.index(h) for h in want]
        for n, row in enumerate(rows, start=2):
            vals = [row[i] if i < len(row) else None for i in ix]
            if not any(vals):
                continue
            try:
                d = Distributor.objects.get(name__iexact=str(vals[0]).strip())
                p = Product.objects.get(code__iexact=str(vals[1]).strip())
                cost = Decimal(str(vals[2] or 0).replace(",", ""))
                _, was_new = DistributorProduct.objects.update_or_create(distributor=d, product=p, defaults={"cost_price": cost})
                created, updated = created + was_new, updated + (not was_new)
            except Exception as e:
                errors.append((n, f"{e.__class__.__name__}: {e}"))
        return created, updated, errors

    spec = IMPORTS[kind]
    model, key = spec["model"], spec["key"]
    header, rows = _read(path, spec["sheet"])
    colmap = {h.lower(): f for h, f in spec["cols"]}
    idx = {i: colmap[h] for i, h in enumerate(header) if h in colmap}
    if key not in idx.values():
        raise ValueError("Missing required column: " + next(h for h, f in spec["cols"] if f == key))
    for n, row in enumerate(rows, start=2):
        try:
            data = {idx[i]: _coerce(model, idx[i], v) for i, v in enumerate(row) if i in idx}
            data = {k: v for k, v in data.items() if v is not None}
            if not data:
                continue                       # empty row
            if not data.get(key):
                raise ValueError(f"'{key}' is empty")
            with transaction.atomic():
                obj = model.objects.filter(**{key + "__iexact": data[key]}).first()
                is_new = obj is None
                if is_new:
                    obj = model(**data)
                else:
                    for k, v in data.items():
                        setattr(obj, k, v)
                obj.full_clean()
                obj.save()
            created, updated = created + is_new, updated + (not is_new)
        except Exception as e:
            errors.append((n, f"{e.__class__.__name__}: {e}"))
    return created, updated, errors
