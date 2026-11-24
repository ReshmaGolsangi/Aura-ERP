"""One PDF layout (Zoho-style) reused for quotation, proforma, receipt and purchase order."""
import os
import re
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BLUE = colors.HexColor("#1e3a5f")
_base = getSampleStyleSheet()["Normal"]
N = ParagraphStyle("n", parent=_base, fontSize=9, leading=12)
SM = ParagraphStyle("sm", parent=_base, fontSize=8.5, leading=11)
RIGHT = ParagraphStyle("r", parent=N, alignment=2)

# Default logo location: backend/assets/aura-logo.png (this file lives in backend/erp/)
DEFAULT_LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "aura-logo.png")


def logo_flowable(width=38 * mm, height=16 * mm):
    """Return a reportlab Image of the company logo, or None if no logo file is found.
    Uses settings.COMPANY_LOGO if set and valid, otherwise backend/assets/aura-logo.png."""
    for path in (getattr(settings, "COMPANY_LOGO", ""), DEFAULT_LOGO):
        if path and os.path.exists(str(path)):
            return Image(str(path), width=width, height=height, kind="proportional", hAlign="LEFT")
    return None


def fmt(v):
    """Indian digit grouping: 1,23,456.00 (Helvetica has no rupee glyph, so we print 'Rs.')."""
    v = Decimal(v or 0).quantize(Decimal("0.01"))
    i, d = f"{abs(v):.2f}".split(".")
    if len(i) > 3:
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", i[:-3])
        i = head + "," + i[-3:]
    return ("-" if v < 0 else "") + i + "." + d


def P(text, style=N):
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)


def build_pdf(title, meta, party_title, party_lines, items, totals, blocks=()):
    """meta: [(label, value)]; items: [dict(desc,hsn,qty,rate,disc,gst,amount)];
    totals: [(label, Decimal)] with the last row shown bold; blocks: [(heading, text)]."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm, title=title)
    s = settings
    left_text = Paragraph(f"<b><font size=14>{escape(s.COMPANY_NAME)}</font></b><br/>"
                          f"{escape(s.COMPANY_ADDRESS).replace(chr(10), '<br/>')}<br/>GSTIN: {escape(s.COMPANY_GSTIN)}<br/>"
                          f"{escape(s.COMPANY_EMAIL)} | {escape(s.COMPANY_PHONE)}", SM)
    left = [left_text]
    logo = logo_flowable()
    if logo:
        left.insert(0, logo)
        left.insert(1, Spacer(1, 3))
    right = Paragraph(f"<para align=right><b><font size=16 color='#1e3a5f'>{escape(title)}</font></b></para>", N)
    el = [Table([[left, right]], colWidths=[112 * mm, 70 * mm],
                style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 1.2, BLUE)]), Spacer(1, 8)]

    party = Paragraph(f"<b>{escape(party_title)}</b><br/>" + "<br/>".join(escape(x) for x in party_lines if x), N)
    metap = Paragraph("<br/>".join(f"<b>{escape(k)}:</b> {escape(str(v))}" for k, v in meta if v not in (None, "")), N)
    el += [Table([[party, metap]], colWidths=[100 * mm, 82 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]), Spacer(1, 10)]

    rows = [["#", "Description", "HSN/SAC", "Qty", "Rate", "Disc%", "GST%", "Amount"]]
    for n, it in enumerate(items, 1):
        rows.append([n, P(it["desc"], SM), it.get("hsn", ""), f"{Decimal(it['qty']):g}", fmt(it["rate"]),
                     f"{Decimal(it.get('disc', 0)):g}", f"{Decimal(it.get('gst', 0)):g}", fmt(it["amount"])])
    t = Table(rows, colWidths=[8 * mm, 66 * mm, 20 * mm, 14 * mm, 24 * mm, 12 * mm, 12 * mm, 26 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])]))
    el += [t, Spacer(1, 8)]

    trows = [[k, "Rs. " + fmt(v)] for k, v in totals]
    tt = Table(trows, colWidths=[45 * mm, 35 * mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                            ("LINEABOVE", (0, -1), (-1, -1), 0.8, BLUE)]))
    el += [tt, Spacer(1, 12)]
    for h, text in blocks:
        if text:
            el += [Paragraph(f"<b>{escape(h)}</b><br/>" + escape(text).replace("\n", "<br/>"), SM), Spacer(1, 6)]
    el.append(Paragraph("<font color='#64748b'>This is a computer-generated document.</font>", SM))
    doc.build(el)
    return buf.getvalue()


# ======================= Zoho-style Purchase Order =======================
_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
         "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below100(n):
    return _ONES[n] if n < 20 else _TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")


def _below1000(n):
    s = ""
    if n >= 100:
        s = _ONES[n // 100] + " Hundred"
        n %= 100
        if n:
            s += " "
    return s + (_below100(n) if n else "")


def inr_words(amount):
    """4500.50 -> 'Indian Rupee Four Thousand Five Hundred and Fifty Paise Only' (lakh/crore system)."""
    r, p = divmod(int((Decimal(amount) * 100).quantize(Decimal("1"))), 100)
    parts = []
    for div, name in ((10 ** 7, "Crore"), (10 ** 5, "Lakh"), (1000, "Thousand")):
        q, r = divmod(r, div)
        if q:
            parts.append(_below1000(q) + " " + name)
    if r:
        parts.append(_below1000(r))
    text = " ".join(parts) or "Zero"
    return f"Indian Rupee {text}" + (f" and {_below100(p)} Paise" if p else "") + " Only"


def build_po_pdf(po_no, meta, vendor_lines, deliver_lines, items, intra_state, notes="", terms=""):
    """Zoho Books style purchase order. items: dicts(desc,hsn,qty,rate,gst,amount[taxable]).
    intra_state=True -> CGST+SGST columns, else IGST column."""
    s = settings
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm, title=f"Purchase Order {po_no}")
    GREY = colors.HexColor("#64748b")
    el = []

    # --- header: company (left) | "Purchase Order" + PO# (right) ---
    comp = [Paragraph(f"<b><font size=13>{escape(s.COMPANY_NAME)}</font></b><br/>"
                      f"{escape(s.COMPANY_ADDRESS).replace(chr(10), '<br/>')}<br/>GSTIN {escape(s.COMPANY_GSTIN)}<br/>"
                      f"{escape(s.COMPANY_EMAIL)}", SM)]
    logo = logo_flowable()
    if logo:
        comp.insert(0, logo)
        comp.insert(1, Spacer(1, 3))
    title = Paragraph("<para align=right><font size=20>Purchase Order</font><br/>"
                      f"<font size=10 color='#64748b'>PO# </font><b><font size=11>{escape(po_no)}</font></b></para>", N)
    el += [Table([[comp, title]], colWidths=[100 * mm, 82 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]),
           Spacer(1, 4), Table([[""]], colWidths=[182 * mm], rowHeights=[1], style=[("LINEABOVE", (0, 0), (-1, 0), 0.8, GREY)]),
           Spacer(1, 6)]

    # --- vendor | deliver to | order details ---
    def block(head, lines):
        return Paragraph(f"<font color='#64748b' size=8>{escape(head)}</font><br/>" +
                         "<br/>".join(escape(x) for x in lines if x), N)
    det = Paragraph("<br/>".join(f"<font color='#64748b'>{escape(k)}:</font> {escape(str(v))}" for k, v in meta if v), N)
    el += [Table([[block("VENDOR ADDRESS", vendor_lines), block("DELIVER TO", deliver_lines), det]],
                 colWidths=[62 * mm, 62 * mm, 58 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]), Spacer(1, 10)]

    # --- line items with tax columns ---
    two = Decimal("0.01")
    def tax_of(it):
        return (Decimal(it["amount"]) * Decimal(it["gst"]) / 100).quantize(two)
    if intra_state:
        head = ["#", "Item & Description", "HSN/SAC", "Qty", "Rate", "CGST\n%", "CGST\nAmt", "SGST\n%", "SGST\nAmt", "Amount"]
        widths = [8, 50, 17, 13, 20, 11, 17, 11, 17, 18]
    else:
        head = ["#", "Item & Description", "HSN/SAC", "Qty", "Rate", "IGST\n%", "IGST\nAmt", "Amount"]
        widths = [8, 62, 18, 14, 24, 14, 22, 20]
    rows, rate_tax, sub, tax_sum = [head], {}, Decimal(0), Decimal(0)
    for n, it in enumerate(items, 1):
        t = tax_of(it); g = Decimal(it["gst"]); sub += Decimal(it["amount"]); tax_sum += t
        rate_tax[g] = rate_tax.get(g, Decimal(0)) + t
        base = [n, P(it["desc"], SM), it.get("hsn", ""), f"{Decimal(it['qty']):g}", fmt(it["rate"])]
        if intra_state:
            c = (t / 2).quantize(two)
            rows.append(base + [f"{g / 2:g}%", fmt(c), f"{g / 2:g}%", fmt(t - c), fmt(it["amount"])])
        else:
            rows.append(base + [f"{g:g}%", fmt(t), fmt(it["amount"])])
    tb = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1)
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3c3d3a")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("ALIGN", (3, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#e2e8f0"))]))
    el += [tb, Spacer(1, 8)]

    # --- totals (grouped by GST rate, like Zoho: 'CGST9 (9%)') ---
    trows = [["Sub Total", fmt(sub)]]
    for g in sorted(rate_tax):
        if intra_state:
            c = (rate_tax[g] / 2).quantize(two)
            trows += [[f"CGST{g / 2:g} ({g / 2:g}%)", fmt(c)], [f"SGST{g / 2:g} ({g / 2:g}%)", fmt(rate_tax[g] - c)]]
        else:
            trows.append([f"IGST{g:g} ({g:g}%)", fmt(rate_tax[g])])
    grand = sub + tax_sum
    trows.append(["Total", "Rs. " + fmt(grand)])
    tt = Table(trows, colWidths=[40 * mm, 32 * mm])
    tt.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
                            ("LINEABOVE", (0, -1), (-1, -1), 0.6, GREY)]))
    words = Paragraph(f"<font color='#64748b' size=8>Total In Words</font><br/><i>{escape(inr_words(grand))}</i>", N)
    el += [Table([[words, tt]], colWidths=[108 * mm, 74 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]), Spacer(1, 12)]

    # --- notes, terms, signature ---
    for h, text in (("Notes", notes), ("Terms & Conditions", terms)):
        if text:
            el += [Paragraph(f"<font color='#64748b' size=8>{h}</font><br/>" + escape(text).replace("\n", "<br/>"), SM), Spacer(1, 6)]
    sign = Table([[Paragraph(f"For <b>{escape(s.COMPANY_NAME)}</b>", SM)], [""], [Paragraph("Authorized Signature", SM)]],
                 colWidths=[60 * mm], rowHeights=[8 * mm, 16 * mm, 6 * mm], hAlign="RIGHT",
                 style=[("LINEABOVE", (0, 2), (0, 2), 0.6, GREY)])
    el += [Spacer(1, 10), sign]
    doc.build(el)
    return buf.getvalue()