"""Week 2: reading and structuring invoices."""
import copy
import json

from pydantic import ValidationError

from ..config import data_dir
from . import expect, need

FIVE = ["INV-A", "INV-04", "INV-05", "INV-06", "INV-07"]


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
    """Invoice accepts a correct invoice (INV-A)"""
    Invoice = need(ns, "Invoice", "step 2")
    inv = Invoice.model_validate(_truth("INV-A")["invoice"])
    expect(abs(inv.total - 92040) < 0.01, "INV-A should validate with total 92,040.")


def schema_validators_catch_errors(ns):
    """The three validators catch line arithmetic, totals and a bad GSTIN"""
    Invoice = need(ns, "Invoice", "step 2")
    good = _truth("INV-A")["invoice"]
    bad_line = copy.deepcopy(good)
    bad_line["lines"][0]["quantity"] = 12
    expect(_raises_validation(lambda: Invoice.model_validate(bad_line)),
           "Quantity 12 × 450 ≠ 54,000 should fail the line validator.")
    bad_total = copy.deepcopy(good)
    bad_total["total"] = 95000
    expect(_raises_validation(lambda: Invoice.model_validate(bad_total)),
           "A total that is not taxable value + tax should fail.")
    bad_gstin = copy.deepcopy(good)
    bad_gstin["supplier_gstin"] = "29-NOT-A-GSTIN"
    expect(_raises_validation(lambda: Invoice.model_validate(bad_gstin)), "A malformed GSTIN should fail.")


def read_invoice_transcribes(ns):
    """read_invoice() returns the invoice text"""
    read_invoice = need(ns, "read_invoice", "step 1")
    text = read_invoice(_path("INV-A"))
    expect(isinstance(text, str) and "SBP/26-27/0412" in text, "The transcription should contain INV-A's number.")


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


def five_invoices_valid_or_named_error(ns):
    """Each of the five invoices returns a correct Invoice or a named validation error"""
    read_invoice = need(ns, "read_invoice", "step 1")
    structure_invoice = need(ns, "structure_invoice", "step 3")
    problems = []
    for inv_id in FIVE:
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


CHECKS = [schema_accepts_valid_invoice, schema_validators_catch_errors, read_invoice_transcribes,
          read_invoice_fails_on_truncation, five_invoices_valid_or_named_error]
