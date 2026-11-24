"""API views: masters (CRUD), quotations, funnel and dashboard."""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Max, OuterRef, Subquery
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .documents import DocMixin, quotation_doc
from .models import (Customer, NumberSequence, Product, Quotation, QuotationItem,
                     QuotationRevision, Target, User, fiscal_year)
from .serializers import (CustomerSerializer, ProductSerializer, QuotationSerializer,
                          RevisionSerializer, TargetSerializer, UserSerializer)

OPEN = ["DRAFT", "SENT", "NEGOTIATION"]


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_admin_role)


class AdminWriteOnly(permissions.BasePermission):
    """Everyone logged in can read; only admins can change."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.method in permissions.SAFE_METHODS or request.user.is_admin_role


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by("username")
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AdminWriteOnly]


class TargetViewSet(viewsets.ModelViewSet):
    queryset = Target.objects.all()
    serializer_class = TargetSerializer
    permission_classes = [IsAdmin]


def visible(user, qs):
    """Admins see all quotations; sales staff only their own."""
    return qs if user.is_admin_role else qs.filter(owner=user)


def with_value(qs):
    """Annotate each quotation with the ex-GST value of its LATEST revision only."""
    latest = QuotationRevision.objects.filter(quotation=OuterRef("pk")).order_by("-rev_no")
    return qs.annotate(latest_value=Subquery(latest.values("subtotal")[:1]))


def add_revision(quotation, data, user):
    """Create the next revision (R1, R2, ...) with its items and totals."""
    rev_no = (quotation.revisions.aggregate(m=Max("rev_no"))["m"] or 0) + 1
    rev = QuotationRevision.objects.create(
        quotation=quotation, rev_no=rev_no, created_by=user,
        subject=data.get("subject", ""), notes=data.get("notes", ""),
        **({"terms": data["terms"]} if data.get("terms") else {}))
    for it in data["items"]:
        QuotationItem.objects.create(revision=rev, **it)
    rev.recompute()
    return rev


class QuotationViewSet(DocMixin, viewsets.ModelViewSet):
    serializer_class = QuotationSerializer
    doc_builder = staticmethod(quotation_doc)

    def get_queryset(self):
        qs = Quotation.objects.select_related("customer", "owner")
        return visible(self.request.user, qs)

    def create(self, request, *args, **kwargs):
        head = QuotationSerializer(data=request.data)
        head.is_valid(raise_exception=True)
        body = RevisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        owner = request.user
        if request.user.is_admin_role and request.data.get("owner"):
            owner = User.objects.get(pk=request.data["owner"])
        with transaction.atomic():
            q = head.save(owner=owner, number=NumberSequence.next("QUO", "QT"))
            add_revision(q, body.validated_data, request.user)
        return Response(QuotationSerializer(q).data, status=201)

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        """POST new line items => creates revision R(n+1). Old revisions stay stored."""
        q = self.get_object()
        body = RevisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        with transaction.atomic():
            add_revision(q, body.validated_data, request.user)
        return Response(QuotationSerializer(q).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(RevisionSerializer(self.get_object().revisions.all(), many=True).data)


def fy_start(fy):
    return date(int(fy[:4]), 4, 1)


@api_view(["GET"])
def me(request):
    u = request.user
    return Response({"id": u.id, "username": u.username, "name": u.get_full_name() or u.username,
                     "role": "ADMIN" if u.is_admin_role else "SALES"})


@api_view(["GET"])
def funnel(request):
    """Live funnel. Only the latest revision of each quotation is counted."""
    qs = with_value(visible(request.user, Quotation.objects.select_related("owner")))
    stages, staff = defaultdict(lambda: [0, Decimal(0)]), defaultdict(lambda: defaultdict(Decimal))
    monthly = defaultdict(lambda: {"quoted": Decimal(0), "won": Decimal(0)})
    hot = [0, Decimal(0)]
    fy = fiscal_year()
    for q in qs:
        v = q.latest_value or Decimal(0)
        stages[q.status][0] += 1
        stages[q.status][1] += v
        s = staff[q.owner.username]
        if q.status in OPEN:
            s["open_count"] += 1; s["open_value"] += v
            if q.is_hot:
                s["hot_count"] += 1; s["hot_value"] += v; hot[0] += 1; hot[1] += v
        if q.status == "WON":
            s["won_value"] += v
        if fiscal_year(q.created_at.date()) == fy:
            monthly[q.created_at.strftime("%Y-%m")]["quoted"] += v
        if q.status == "WON" and q.won_at and fiscal_year(q.won_at.date()) == fy:
            monthly[q.won_at.strftime("%Y-%m")]["won"] += v
    return Response({
        "stages": [{"status": k, "count": c, "value": val} for k, (c, val) in stages.items()],
        "hot": {"count": hot[0], "value": hot[1]},
        "by_staff": [{"staff": k, **v} for k, v in staff.items()],
        "monthly": [{"month": k, **v} for k, v in sorted(monthly.items())],
    })


@api_view(["GET"])
def dashboard(request):
    """Per-staff dashboard: target, achieved, remaining and PIP (logic pending)."""
    user = request.user
    if user.is_admin_role and request.query_params.get("staff"):
        user = User.objects.get(pk=request.query_params["staff"])
    fy = fiscal_year()
    target = Target.objects.filter(staff=user, fy=fy).first()
    won = with_value(Quotation.objects.filter(owner=user, status="WON", won_at__date__gte=fy_start(fy)))
    achieved = sum((q.latest_value or Decimal(0) for q in won), Decimal(0))
    tgt = target.amount if target else Decimal(0)
    return Response({
        "staff": user.username, "fy": fy, "target": tgt, "achieved": achieved,
        "remaining": max(tgt - achieved, Decimal(0)),
        "achieved_percent": round(achieved / tgt * 100, 1) if tgt else 0,
        "pip": None,            # TODO: plug in incentive slabs once logic is provided
        "pip_remaining": None,  # TODO: amount still needed to reach next PIP slab
    })


# ======================= Phase 2 & 3 views =======================
from django.shortcuts import get_object_or_404
from rest_framework import mixins
from .documents import po_doc, proforma_doc, receipt_doc
from .models import Distributor, DistributorProduct, ProformaInvoice, PurchaseOrder, Receipt
from .serializers import (DistributorProductSerializer, DistributorSerializer, ProformaSerializer,
                          PurchaseOrderSerializer, ReceiptSerializer)

class ProformaViewSet(DocMixin, mixins.CreateModelMixin, mixins.ListModelMixin,
                      mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ProformaSerializer
    doc_builder = staticmethod(proforma_doc)

    def get_queryset(self):
        qs = ProformaInvoice.objects.select_related("quotation__customer", "revision")
        return qs if self.request.user.is_admin_role else qs.filter(quotation__owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """POST {quotation, po_number, po_date}. Quotation must be WON; snapshots its latest revision."""
        q = get_object_or_404(visible(request.user, Quotation.objects.all()), pk=request.data.get("quotation"))
        if q.status != "WON":
            return Response({"detail": "Mark the quotation as WON (PO received) first."}, status=400)
        if not request.data.get("po_number"):
            return Response({"detail": "Customer PO number is required."}, status=400)
        with transaction.atomic():
            q.po_number = request.data["po_number"]
            q.po_date = request.data.get("po_date") or None
            q.save()
            p = ProformaInvoice.objects.create(number=NumberSequence.next("PI", "PI"), quotation=q,
                                               revision=q.latest_revision, created_by=request.user)
        return Response(ProformaSerializer(p).data, status=201)


class ReceiptViewSet(DocMixin, mixins.CreateModelMixin, mixins.ListModelMixin,
                     mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ReceiptSerializer
    doc_builder = staticmethod(receipt_doc)

    def get_queryset(self):
        qs = Receipt.objects.select_related("proforma__quotation__customer")
        return qs if self.request.user.is_admin_role else qs.filter(proforma__quotation__owner=self.request.user)

    def perform_create(self, serializer):
        # Staff may only record receipts against their own proformas.
        if not self.request.user.is_admin_role and serializer.validated_data["proforma"].quotation.owner != self.request.user:
            raise PermissionDenied("Not your proforma.")
        with transaction.atomic():
            serializer.save(number=NumberSequence.next("RCT", "RC"), created_by=self.request.user)


class DistributorViewSet(viewsets.ModelViewSet):
    queryset = Distributor.objects.all()
    serializer_class = DistributorSerializer
    permission_classes = [IsAdmin]


class DistributorProductViewSet(viewsets.ModelViewSet):
    serializer_class = DistributorProductSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = DistributorProduct.objects.select_related("distributor", "product")
        d = self.request.query_params.get("distributor")
        return qs.filter(distributor_id=d) if d else qs


class PurchaseOrderViewSet(DocMixin, viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("distributor").prefetch_related("items")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAdmin]
    doc_builder = staticmethod(po_doc)
