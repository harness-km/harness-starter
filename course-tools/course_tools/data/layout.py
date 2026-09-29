"""What is printed on an invoice, as text. The PDF renderer and the transcription both use this,
so the PDF and the ground-truth reading always agree.

The template follows the supplier's country (an Indian GST tax invoice, a US invoice, a German
export invoice, a Canadian invoice). The currency label follows what the supplier printed.
"""
from __future__ import annotations

DEFAULT_LABEL = {"IN": "Rs.", "US": "$", "DE": "EUR", "CA": "$"}

TEMPLATES = {
    "IN": {"title": "TAX INVOICE", "tax_id": "GSTIN", "item": "HSN", "unit": "Rate ({c})",
           "amount": "Taxable Value ({c})", "rate": "GST %", "subtotal": "Taxable total",
           "total": "Invoice total ({c})", "bank": ("A/c No", "IFSC"),
           "terms": "Terms: payment within 30 days of receipt of goods."},
    "US": {"title": "INVOICE", "tax_id": "EIN", "item": "Item No.", "unit": "Unit Price ({c})",
           "amount": "Amount ({c})", "rate": "Tax %", "subtotal": "Subtotal", "total": "Total due ({c})",
           "bank": ("Account", "ABA routing"), "terms": "Terms: Net 30."},
    "DE": {"title": "INVOICE / RECHNUNG", "tax_id": "VAT ID", "item": "Art. No.", "unit": "Unit Price ({c})",
           "amount": "Amount ({c})", "rate": "VAT %", "subtotal": "Net total", "total": "Total ({c})",
           "bank": ("IBAN", "BIC"), "terms": "Terms: 30 days net. Export delivery to the United States."},
    "CA": {"title": "INVOICE", "tax_id": "GST/HST No.", "item": "Item No.", "unit": "Unit Price ({c})",
           "amount": "Amount ({c})", "rate": "Tax %", "subtotal": "Subtotal", "total": "Total ({c})",
           "bank": ("Account", "Transit-Institution"), "terms": "Terms: Net 30."},
}

TAX_LABEL = {"CGST": "CGST", "SGST": "SGST", "IGST": "IGST"}


def money(x: float, indian: bool = False) -> str:
    """1234567.5 -> 1,234,567.50 (or 12,34,567.50 with Indian digit grouping)."""
    neg = x < 0
    whole, frac = f"{abs(x):.2f}".split(".")
    if indian and len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    elif not indian:
        whole = f"{int(whole):,}"
    return ("-" if neg else "") + whole + "." + frac


def _rate(r: float) -> str:
    return f"{r:g}"


def tax_row_label(t: dict, country: str) -> str:
    kind = t["kind"]
    if kind in TAX_LABEL:
        return TAX_LABEL[kind]
    if kind == "SALES_TAX":
        return f"Sales tax ({_rate(t['rate'])}%)" if t["amount"] else "Sales tax (resale certificate on file)"
    if kind == "VAT":
        return f"VAT {_rate(t['rate'])}% (export outside the EU)"
    return f"GST/HST {_rate(t['rate'])}% (zero-rated export)"


def document(inv: dict, sup: dict, entity: dict, label: str | None = None) -> dict:
    """All the printed text of one invoice, grouped by where it sits on the page."""
    country = sup.get("country", "IN")
    tpl = TEMPLATES[country]
    c = label or DEFAULT_LABEL[country]
    indian = c == "Rs."
    fmt = lambda x: money(x, indian)  # noqa: E731
    buyer = f"Buyer {entity['tax_id_type']}: {entity['tax_id']}"
    if country == "IN":
        buyer += f"   Place of supply: {entity['region']} ({entity['region_code']})"
    elif country == "US" and sup.get("supplier_id") != "S06":
        buyer += "   Resale certificate on file"
    rows = [[str(i + 1), ln["description"], ln["item_code"], str(ln["quantity"]), fmt(ln["unit_price"]),
             fmt(ln["amount"]), _rate(ln["tax_rate"])] for i, ln in enumerate(inv["lines"])]
    totals = [(tpl["subtotal"], fmt(inv["subtotal"]))]
    totals += [(tax_row_label(t, country), fmt(t["amount"])) for t in inv["tax_lines"]]
    acct, code = tpl["bank"]
    return {
        "supplier": inv["supplier_name"],
        "supplier_line": f"{sup.get('city', '')}, {sup.get('region', '')}   {tpl['tax_id']}: {inv['supplier_tax_id']}",
        "email": f"Email: {sup.get('email', '')}",
        "title": tpl["title"],
        "meta": (f"Invoice No: {inv['invoice_number']}", f"Invoice Date: {inv['invoice_date']}",
                 f"PO Ref: {inv['po_reference'] or ''}"),
        "bill_to": f"Bill to: {inv['bill_to']}, {entity['address']}",
        "buyer": buyer,
        "columns": ["#", "Description", tpl["item"], "Qty", tpl["unit"].format(c=c), tpl["amount"].format(c=c),
                    tpl["rate"]],
        "rows": rows,
        "totals": totals,
        "total": (tpl["total"].format(c=c), fmt(inv["total"])),
        "bank": f"{acct}: {inv['bank_account']}   {code}: {inv['bank_code']}",
        "terms": tpl["terms"],
    }
