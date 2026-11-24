"""Serializers: convert models <-> JSON and validate input."""
from django.utils.crypto import get_random_string
from django.utils import timezone
from rest_framework import serializers
from django.db import transaction
from .models import (Distributor, DistributorProduct, NumberSequence, ProformaInvoice, PurchaseOrder,
                     PurchaseOrderItem, Receipt, Customer, Product, Quotation, QuotationItem, QuotationRevision, Target, User)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "is_active", "password"]

    def create(self, data):
        pw = data.pop("password", None)
        user = User(**data)
        user.set_password(pw or get_random_string(16))
        user.save()
        return user

    def update(self, inst, data):
        pw = data.pop("password", None)
        for k, v in data.items():
            setattr(inst, k, v)
        if pw:
            inst.set_password(pw)
        inst.save()
        return inst


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class TargetSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.username", read_only=True)
    class Meta:
        model = Target
        fields = "__all__"


class ItemSerializer(serializers.ModelSerializer):
    taxable = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    tax = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationItem
        fields = ["id", "product", "description", "hsn_sac", "qty", "rate",
                  "discount_percent", "gst_percent", "taxable", "tax"]


class RevisionSerializer(serializers.ModelSerializer):
    """Used for both output (history) and input (new revision payload)."""
    items = ItemSerializer(many=True)

    class Meta:
        model = QuotationRevision
        fields = ["id", "rev_no", "subject", "terms", "notes", "subtotal", "tax_total",
                  "grand_total", "created_at", "items"]
        read_only_fields = ["rev_no", "subtotal", "tax_total", "grand_total", "created_at"]

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Add at least one line item.")
        return items


class QuotationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    latest = RevisionSerializer(source="latest_revision", read_only=True)

    class Meta:
        model = Quotation
        fields = ["id", "number", "customer", "customer_name", "owner", "owner_name", "status",
                  "is_hot", "expected_close_date", "po_number", "po_date", "lost_reason", "won_at", "created_at", "latest"]
        read_only_fields = ["number", "owner", "won_at", "created_at"]

    def update(self, inst, data):
        # Stamp the win date once, when status first becomes WON.
        if data.get("status") == "WON" and not inst.won_at:
            inst.won_at = timezone.now()
        return super().update(inst, data)


D = dict(max_digits=14, decimal_places=2, read_only=True)


class ProformaSerializer(serializers.ModelSerializer):
    quotation_number = serializers.CharField(source="quotation.number", read_only=True)
    customer_name = serializers.CharField(source="quotation.customer.name", read_only=True)
    po_number = serializers.CharField(source="quotation.po_number", read_only=True)
    total = serializers.DecimalField(**D)
    paid = serializers.DecimalField(**D)
    balance = serializers.DecimalField(**D)

    class Meta:
        model = ProformaInvoice
        fields = ["id", "number", "quotation", "quotation_number", "customer_name", "po_number",
                  "issue_date", "total", "paid", "balance"]
        read_only_fields = ["number", "quotation"]


class ReceiptSerializer(serializers.ModelSerializer):
    proforma_number = serializers.CharField(source="proforma.number", read_only=True)

    class Meta:
        model = Receipt
        fields = ["id", "number", "proforma", "proforma_number", "amount", "mode", "reference",
                  "received_on", "emailed_at", "whatsapp_at"]
        read_only_fields = ["number", "emailed_at", "whatsapp_at"]

    def validate(self, data):
        if data["amount"] <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        if data["amount"] > data["proforma"].balance:
            raise serializers.ValidationError(f"Amount exceeds balance due ({data['proforma'].balance}).")
        return data


class DistributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distributor
        fields = "__all__"


class DistributorProductSerializer(serializers.ModelSerializer):
    distributor_name = serializers.CharField(source="distributor.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_hsn = serializers.CharField(source="product.hsn_sac", read_only=True)
    product_gst = serializers.DecimalField(source="product.gst_percent", max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = DistributorProduct
        fields = "__all__"


class POItemSerializer(serializers.ModelSerializer):
    taxable = serializers.DecimalField(**D)
    tax = serializers.DecimalField(**D)

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "product", "description", "hsn_sac", "qty", "rate", "gst_percent", "taxable", "tax"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = POItemSerializer(many=True, required=False)
    distributor_name = serializers.CharField(source="distributor.name", read_only=True)
    subtotal = serializers.DecimalField(**D)
    tax_total = serializers.DecimalField(**D)
    grand_total = serializers.DecimalField(**D)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "number", "distributor", "distributor_name", "status", "order_date", "expected_delivery",
                  "reference", "notes", "terms", "items", "subtotal", "tax_total", "grand_total", "created_at"]
        read_only_fields = ["number"]

    def validate(self, data):
        if not self.instance and not data.get("items"):
            raise serializers.ValidationError("Add at least one line item.")
        dist = data.get("distributor") or (self.instance.distributor if self.instance else None)
        for it in data.get("items", []):
            p = it.get("product")
            if p and not DistributorProduct.objects.filter(distributor=dist, product=p).exists():
                raise serializers.ValidationError(f"{p.code} is not in this distributor's product list.")
        return data

    def _items(self, po, items):
        po.items.all().delete()
        for it in items:
            PurchaseOrderItem.objects.create(po=po, **it)

    def create(self, data):
        items = data.pop("items")
        with transaction.atomic():
            po = PurchaseOrder.objects.create(number=NumberSequence.next("PO", "PO"),
                                              created_by=self.context["request"].user, **data)
            self._items(po, items)
        return po

    def update(self, inst, data):
        items = data.pop("items", None)
        with transaction.atomic():
            inst = super().update(inst, data)
            if items is not None:
                self._items(inst, items)
        return inst
