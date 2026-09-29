"""Week 2: reading and structuring invoices."""
import copy
import json

from pydantic import ValidationError

from ..config import data_dir
from . import expect, need

SIX = ["INV-A", "INV-04", "INV-05", "INV-06", "INV-07", "INV-24"]


def _truth(inv_id):
    gt = json.loads((data_dir() / "ground_truth.json").read_text())["invoices"]
    return next(r for r in gt if r["id"] == inv_id)


def _path(inv_id):
    return data_dir() / "invoices" / f"{inv_id}.pdf"


def _raises_validation(fn):
    try:
        fn()
    except ValidationError:
        return True
    return False


def schema_accepts_valid_invoice(ns):
    """Invoice accepts correct invoices in USD (INV-A) and INR (INV-10)"""
    Invoice = need(ns, "Invoice", "step 2")
    inv = Invoice.model_validate(_truth("INV-A")["invoice"])
    expect(abs(inv.total - 3360) < 0.01 and inv.currency == "USD", "INV-A should validate: USD, total 3,360.00.")
    inr = Invoice.model_validate(_truth("INV-10")["invoice"])
    expect(inr.currency == "INR" and [t.kind for t in inr.tax_lines] == ["IGST"],
           "INV-10 should validate: INR, one IGST tax line.")


def schema_validators_catch_errors(ns):
    """The three validators catch line arithmetic, totals and a bad tax ID"""
    Invoice = need(ns, "Invoice", "step 2")
    good = _truth("INV-A")["invoice"]
    bad_line = copy.deepcopy(good)
    bad_line["lines"][0]["quantity"] = 3
    expect(_raises_validation(lambda: Invoice.model_validate(bad_line)),
           "Quantity 3 × $96.00 ≠ $2,880.00 should fail the line validator.")
    bad_total = copy.deepcopy(good)
    bad_total["total"] = 3500
    expect(_raises_validation(lambda: Invoice.model_validate(bad_total)),
           "A total that is not subtotal + tax should fail.")
    bad_tax = copy.deepcopy(_truth("INV-10")["invoice"])
    bad_tax["tax_lines"][0]["amount"] += 50
    expect(_raises_validation(lambda: Invoice.model_validate(bad_tax)),
           "An INR invoice whose IGST does not add up to the total should fail.")
    bad_id = copy.deepcopy(good)
    bad_id["supplier_tax_id"] = "13-NOT-AN-EIN"
    expect(_raises_validation(lambda: Invoice.model_validate(bad_id)), "A malformed tax ID should fail.")


def read_invoice_transcribes(ns):
    """read_invoice() returns the invoice text"""
    read_invoice = need(ns, "read_invoice", "step 1")
    text = read_invoice(_path("INV-A"))
    expect(isinstance(text, str) and "PBC-10412" in text, "The transcription should contain INV-A's number.")


def read_invoice_fails_on_truncation(ns):
    """read_invoice() fails loudly when the reply is truncated (the Break-it)"""
    read_invoice = need(ns, "read_invoice", "step 1")
    err_cls = need(ns, "TruncatedOutputError", "step 1")
    try:
        read_invoice(_path("INV-05"), max_tokens=200)
    except err_cls:
        return
    except TypeError as e:
        raise AssertionError(f"read_invoice() must accept max_tokens=...: {e}")
    raise AssertionError("A two-page invoice read with max_tokens=200 returned normally: page 2 was silently lost.")


def six_invoices_valid_or_named_error(ns):
    """Each of the six invoices returns a correct Invoice or a named validation error"""
    read_invoice = need(ns, "read_invoice", "step 1")
    structure_invoice = need(ns, "structure_invoice", "step 3")
    problems = []
    for inv_id in SIX:
        truth = _truth(inv_id)["invoice"]
        try:
            inv = structure_invoice(read_invoice(_path(inv_id)))
        except ValidationError:
            continue
        except NotImplementedError:
            raise
        except Exception as e:  # frameworks sometimes wrap the ValidationError
            cause = e.__cause__ or e.__context__
            if isinstance(cause, ValidationError):
                continue
            problems.append(f"{inv_id}: {type(e).__name__}")
            continue
        if abs(inv.total - truth["total"]) > 1 or inv.invoice_number != truth["invoice_number"]:
            problems.append(f"{inv_id}: returned an Invoice with wrong values (silently wrong)")
        if inv_id == "INV-07" and inv.po_reference:
            problems.append("INV-07 has no PO reference; po_reference should be empty, not invented")
    expect(not problems, "; ".join(problems))


def currency_check_flags_disagreement(ns):
    """check_currency() trusts matching invoices and flags a '$' that is really Canadian"""
    Invoice = need(ns, "Invoice", "step 2")
    check_currency = need(ns, "check_currency", "step 3b")
    for inv_id in ["INV-A", "INV-05", "INV-20", "INV-40"]:
        r = _truth(inv_id)
        msg = check_currency(Invoice.model_validate(r["reading"]), "\n".join(r["transcription"]))
        expect(msg is None, f"{inv_id}: the extracted currency matches the document, but check_currency said: {msg}")
    r = _truth("INV-24")
    msg = check_currency(Invoice.model_validate(r["reading"]), "\n".join(r["transcription"]))
    expect(bool(msg), "INV-24 was read as USD, but its GST/HST details point to CAD: check_currency should flag it.")
    mixed = Invoice.model_validate(_truth("INV-A")["reading"])
    expect(bool(check_currency(mixed, "Total due (US$): 3,360.00\nTotal (EUR): 3,100.00")),
           "A document showing both US$ and EUR should be flagged.")


CHECKS = [schema_accepts_valid_invoice, schema_validators_catch_errors, read_invoice_transcribes,
          read_invoice_fails_on_truncation, six_invoices_valid_or_named_error, currency_check_flags_disagreement]
