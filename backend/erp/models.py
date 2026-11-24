"""Data models: users, masters, auto-numbering, quotations (with revisions), targets."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models import Sum

TWO = Decimal("0.01")


def money(v):
    """Round to 2 decimals (paise)."""
    return Decimal(v).quantize(TWO, rounding=ROUND_HALF_UP)


def fiscal_year(on=None):
    """Indian FY (Apr-Mar) label, e.g. '2026-27'."""
    on = on or date.today()
    start = on.year if on.month >= 4 else on.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


class User(AbstractUser):
    """Login user. ADMIN sees everything; SALES sees only own quotations."""
    ROLES = [("ADMIN", "Admin"), ("SALES", "Sales Staff")]
    role = models.CharField(max_length=10, choices=ROLES, default="SALES")

    @property
    def is_admin_role(self):
        return self.role == "ADMIN" or self.is_superuser


class NumberSequence(models.Model):
    """One running counter per (document type, financial year). Resets each April."""
    key = models.CharField(max_length=20)
    fy = models.CharField(max_length=10)
    last = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("key", "fy")

    @classmethod
    def next(cls, key, prefix, on=None):
        """Return next number like AUR/QT/2026-27/0001. Row-locked => no duplicates."""
        fy = fiscal_year(on)
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(key=key, fy=fy)
            seq.last += 1
            seq.save()
        return f"{settings.COMPANY_PREFIX}/{prefix}/{fy}/{seq.last:04d}"


class Customer(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    hsn_sac = models.CharField("HSN/SAC", max_length=12, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Quotation(models.Model):
    """Header. Number never changes; each edit adds a QuotationRevision."""
    STATUS = [("DRAFT", "Draft"), ("SENT", "Sent"), ("NEGOTIATION", "Negotiation"),
              ("WON", "Won (PO received)"), ("LOST", "Lost")]
    number = models.CharField(max_length=40, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="quotations")
    status = models.CharField(max_length=12, choices=STATUS, default="DRAFT")
    is_hot = models.BooleanField(default=False)
    expected_close_date = models.DateField(null=True, blank=True)
    won_at = models.DateTimeField(null=True, blank=True)
    lost_reason = models.CharField(max_length=200, blank=True)
    po_number = models.CharField("Customer PO no.", max_length=60, blank=True)
    po_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def latest_revision(self):
        return self.revisions.order_by("-rev_no").first()

    def __str__(self):
        return self.number


class QuotationRevision(models.Model):
    """Full snapshot of a quotation. Only the highest rev_no counts in the funnel."""
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="revisions")
    rev_no = models.PositiveIntegerField()
    subject = models.CharField(max_length=200, blank=True)
    terms = models.TextField(blank=True, default="Payment: 100% advance. Prices are exclusive of GST unless stated.")
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)   # before GST
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("quotation", "rev_no")
        ordering = ["-rev_no"]

    def recompute(self):
        """Recalculate totals from line items."""
        items = list(self.items.all())
        self.subtotal = sum((i.taxable for i in items), Decimal("0"))
        self.tax_total = sum((i.tax for i in items), Decimal("0"))
        self.grand_total = self.subtotal + self.tax_total
        self.save(update_fields=["subtotal", "tax_total", "grand_total"])


class QuotationItem(models.Model):
    revision = models.ForeignKey(QuotationRevision, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    description = models.CharField(max_length=300)
    hsn_sac = models.CharField(max_length=12, blank=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)

    @property
    def taxable(self):
        return money(self.qty * self.rate * (1 - self.discount_percent / 100))

    @property
    def tax(self):
        return money(self.taxable * self.gst_percent / 100)


class Target(models.Model):
    """Annual sales target (ex-GST) per staff member per financial year."""
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fy = models.CharField(max_length=10, default=fiscal_year)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        unique_together = ("staff", "fy")


# ======================= Phase 2: Proforma + Receipts =======================
class ProformaInvoice(models.Model):
    """Created from a WON quotation. Freezes the revision that was current at PO time."""
    number = models.CharField(max_length=40, unique=True, editable=False)
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, related_name="proformas")
    revision = models.ForeignKey(QuotationRevision, on_delete=models.PROTECT)
    issue_date = models.DateField(default=date.today)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def total(self):
        return self.revision.grand_total

    @property
    def paid(self):
        return self.receipts.aggregate(s=Sum("amount"))["s"] or Decimal("0")

    @property
    def balance(self):
        return self.total - self.paid


class Receipt(models.Model):
    MODES = [("NEFT/RTGS", "NEFT/RTGS"), ("UPI", "UPI"), ("CHEQUE", "Cheque"), ("CASH", "Cash"), ("CARD", "Card")]
    number = models.CharField(max_length=40, unique=True, editable=False)
    proforma = models.ForeignKey(ProformaInvoice, on_delete=models.PROTECT, related_name="receipts")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    mode = models.CharField(max_length=12, choices=MODES, default="NEFT/RTGS")
    reference = models.CharField("UTR / Cheque no.", max_length=80, blank=True)
    received_on = models.DateField(default=date.today)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    emailed_at = models.DateTimeField(null=True, blank=True)
    whatsapp_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


# ======================= Phase 3: Distributors + Purchase Orders =======================
class Distributor(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DistributorProduct(models.Model):
    """Which products a distributor supplies, and our buying (cost) price."""
    distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE, related_name="products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("distributor", "product")


class PurchaseOrder(models.Model):
    STATUS = [("DRAFT", "Draft"), ("SENT", "Sent"), ("CONFIRMED", "Confirmed"),
              ("RECEIVED", "Received"), ("CANCELLED", "Cancelled")]
    number = models.CharField(max_length=40, unique=True, editable=False)
    distributor = models.ForeignKey(Distributor, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=STATUS, default="DRAFT")
    order_date = models.DateField(default=date.today)
    expected_delivery = models.DateField(null=True, blank=True)
    reference = models.CharField("Customer / quotation ref", max_length=100, blank=True)
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True, default="Payment as per agreed terms. Delivery to registered address.")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def subtotal(self):
        return sum((i.taxable for i in self.items.all()), Decimal("0"))

    @property
    def tax_total(self):
        return sum((i.tax for i in self.items.all()), Decimal("0"))

    @property
    def grand_total(self):
        return self.subtotal + self.tax_total


class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    description = models.CharField(max_length=300)
    hsn_sac = models.CharField(max_length=12, blank=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18)

    @property
    def taxable(self):
        return money(self.qty * self.rate)

    @property
    def tax(self):
        return money(self.taxable * self.gst_percent / 100)
