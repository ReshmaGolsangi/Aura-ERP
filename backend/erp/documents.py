"""Builds each business document (PDF + email/WhatsApp details) and sends it."""
import re
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import money
from .pdf import build_pdf, build_po_pdf


def tax_lines(tax, party_state):
    """Intra-state => CGST+SGST halves; inter-state => IGST."""
    if (party_state or "").strip().lower() == settings.COMPANY_STATE.lower():
        half = money(tax / 2)
        return [("CGST", half), ("SGST", tax - half)]
    return [("IGST", tax)]


def party(o):
    return [o.name, o.contact_person, o.address, ", ".join(x for x in [getattr(o, "city", ""), o.state] if x),
            f"GSTIN: {o.gstin}" if o.gstin else "", f"Ph: {o.phone}" if o.phone else ""]


def _items(qs):
    return [dict(desc=i.description, hsn=i.hsn_sac, qty=i.qty, rate=i.rate,
                 disc=getattr(i, "discount_percent", 0), gst=i.gst_percent, amount=i.taxable) for i in qs]


def _safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name)


def quotation_doc(q):
    r = q.latest_revision
    totals = [("Sub Total", r.subtotal)] + tax_lines(r.tax_total, q.customer.state) + [("Total", r.grand_total)]
    pdf = build_pdf("QUOTATION",
        [("Quotation No", q.number), ("Revision", f"R{r.rev_no}"), ("Date", r.created_at.strftime("%d-%m-%Y")),
         ("Valid till", (r.created_at + timedelta(days=15)).strftime("%d-%m-%Y")), ("Sales person", q.owner.get_full_name() or q.owner.username)],
        "Quote To", party(q.customer), _items(r.items.all()), totals,
        [("Subject", r.subject), ("Terms & Conditions", r.terms), ("Notes", r.notes)])
    return dict(filename=_safe(f"{q.number}-R{r.rev_no}") + ".pdf", pdf=pdf, email=q.customer.email, phone=q.customer.phone,
                subject=f"Quotation {q.number} (R{r.rev_no}) from {settings.COMPANY_NAME}",
                body=f"Dear {q.customer.contact_person or q.customer.name},\n\nPlease find our quotation {q.number} (R{r.rev_no}) attached.\n\nRegards,\n{settings.COMPANY_NAME}")


def proforma_doc(p):
    q, r = p.quotation, p.revision
    totals = [("Sub Total", r.subtotal)] + tax_lines(r.tax_total, q.customer.state) + [("Total", r.grand_total)]
    if p.paid:
        totals = totals[:-1] + [("Total", r.grand_total), ("Paid", p.paid), ("Balance Due", p.balance)]
    pdf = build_pdf("PROFORMA INVOICE",
        [("Proforma No", p.number), ("Date", p.issue_date.strftime("%d-%m-%Y")), ("Quotation Ref", f"{q.number}-R{r.rev_no}"),
         ("Customer PO No", q.po_number), ("Customer PO Date", q.po_date.strftime("%d-%m-%Y") if q.po_date else "")],
        "Bill To", party(q.customer), _items(r.items.all()), totals,
        [("Bank Details", settings.COMPANY_BANK.replace("|", "\n")), ("Terms & Conditions", r.terms)])
    return dict(filename=_safe(p.number) + ".pdf", pdf=pdf, email=q.customer.email, phone=q.customer.phone,
                subject=f"Proforma Invoice {p.number} from {settings.COMPANY_NAME}",
                body=f"Dear {q.customer.contact_person or q.customer.name},\n\nThank you for your PO {q.po_number}. Please find proforma invoice {p.number} attached.\n\nRegards,\n{settings.COMPANY_NAME}")


def receipt_doc(rc):
    p = rc.proforma; q = p.quotation
    pdf = build_pdf("PAYMENT RECEIPT",
        [("Receipt No", rc.number), ("Date", rc.received_on.strftime("%d-%m-%Y")), ("Mode", rc.mode),
         ("Reference", rc.reference), ("Against", p.number)],
        "Received From", party(q.customer),
        [dict(desc=f"Payment against proforma {p.number}", qty=1, rate=rc.amount, gst=0, amount=rc.amount)],
        [("Amount Received", rc.amount), ("Proforma Total", p.total), ("Balance Due", p.balance)],
        [("Note", "Thank you for your payment.")])
    return dict(filename=_safe(rc.number) + ".pdf", pdf=pdf, email=q.customer.email, phone=q.customer.phone,
                subject=f"Payment receipt {rc.number} from {settings.COMPANY_NAME}",
                body=f"Dear {q.customer.contact_person or q.customer.name},\n\nWe have received Rs. {rc.amount}. Receipt {rc.number} is attached.\n\nRegards,\n{settings.COMPANY_NAME}")


def po_doc(po):
    """Zoho-style purchase order (see pdf.build_po_pdf)."""
    d = po.distributor
    intra = (d.state or "").strip().lower() == settings.COMPANY_STATE.lower()
    pdf = build_po_pdf(
        po.number,
        [("Order Date", po.order_date.strftime("%d/%m/%Y")),
         ("Expected Delivery", po.expected_delivery.strftime("%d/%m/%Y") if po.expected_delivery else ""),
         ("Reference", po.reference), ("Status", po.get_status_display())],
        party(d),
        [settings.COMPANY_NAME] + settings.COMPANY_ADDRESS.split("\n") + [f"GSTIN: {settings.COMPANY_GSTIN}"],
        _items(po.items.all()), intra, notes=po.notes, terms=po.terms)
    return dict(filename=_safe(po.number) + ".pdf", pdf=pdf, email=d.email, phone=d.phone,
                subject=f"Purchase Order {po.number} from {settings.COMPANY_NAME}",
                body=f"Dear {d.contact_person or d.name},\n\nPlease find purchase order {po.number} attached. Kindly confirm.\n\nRegards,\n{settings.COMPANY_NAME}")


def _phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    return "91" + digits if len(digits) == 10 else digits


def send_email(d):
    m = EmailMessage(d["subject"], d["body"], to=[d["email"]])
    m.attach(d["filename"], d["pdf"], "application/pdf")
    m.send(fail_silently=False)


def send_whatsapp(d):
    """Returns (sent, link). Uses Meta WhatsApp Cloud API if configured, else a click-to-chat link.
    NOTE: Meta only allows free-form documents within 24h of the customer's last message;
    otherwise you need an approved template (ask me to add it once you have one)."""
    phone = _phone(d["phone"])
    link = f"https://wa.me/{phone}?text={quote(d['body'])}" if phone else ""
    if not (settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_ID and phone):
        return False, link
    base = f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_ID}"
    h = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
    up = requests.post(base + "/media", headers=h, data={"messaging_product": "whatsapp", "type": "application/pdf"},
                       files={"file": (d["filename"], d["pdf"], "application/pdf")}, timeout=30)
    up.raise_for_status()
    msg = requests.post(base + "/messages", headers=h, timeout=30, json={
        "messaging_product": "whatsapp", "to": phone, "type": "document",
        "document": {"id": up.json()["id"], "filename": d["filename"], "caption": d["body"][:900]}})
    msg.raise_for_status()
    return True, link


class DocMixin:
    """Adds GET <id>/pdf/ and POST <id>/send/ to any viewset. Set doc_builder = staticmethod(fn)."""
    doc_builder = None

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        d = self.doc_builder(self.get_object())
        resp = HttpResponse(d["pdf"], content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="{d["filename"]}"'
        return resp

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        obj = self.get_object(); d = self.doc_builder(obj)
        channels = request.data.get("channels", ["email", "whatsapp"])
        msgs, wa_sent, link = [], False, ""
        if "email" in channels:
            if not d["email"]:
                msgs.append("No email address on record")
            else:
                try:
                    send_email(d); msgs.append(f"Email sent to {d['email']}")
                    if hasattr(obj, "emailed_at"):
                        obj.emailed_at = timezone.now(); obj.save(update_fields=["emailed_at"])
                except Exception as e:
                    msgs.append(f"Email failed: {e}")
        if "whatsapp" in channels:
            try:
                wa_sent, link = send_whatsapp(d)
                msgs.append("WhatsApp sent" if wa_sent else "WhatsApp not configured / no phone: use the chat link")
                if wa_sent and hasattr(obj, "whatsapp_at"):
                    obj.whatsapp_at = timezone.now(); obj.save(update_fields=["whatsapp_at"])
            except Exception as e:
                msgs.append(f"WhatsApp failed: {e}")
        return Response({"message": " | ".join(msgs), "whatsapp_sent": wa_sent, "whatsapp_link": link})
