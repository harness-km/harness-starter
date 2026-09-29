"""Week 4: the invoice graph in LangGraph."""
import json

from ..config import data_dir
from ..fake import Brain
from . import expect, need


def _path(inv_id):
    return str(data_dir() / "invoices" / f"{inv_id}.pdf")


def _run(ns, inv_id):
    graph = need(ns, "graph", "step 3")
    return graph.invoke({"file": _path(inv_id)})


def inv_a_end_to_end(ns):
    """INV-A runs end to end: supplier S01, PO-1001, goods receipt 30 and 40"""
    out = _run(ns, "INV-A")
    text = json.dumps({k: out.get(k) for k in ("supplier", "purchase_order", "goods_receipt")}, default=str)
    expect("S01" in text and "PO-1001" in text, f"Expected supplier S01 and PO-1001 in the final state: {text[:300]}")
    expect('"received": 30' in text and '"received": 40' in text,
           "Expected the goods receipt quantities (30, 40) in the final state.")
    expect(out.get("status") == "ready_for_matching", f"status should be 'ready_for_matching', got {out.get('status')!r}")


def fewer_model_calls(ns):
    """The graph uses only two model calls for INV-A (read + structure)"""
    before = Brain.calls
    _run(ns, "INV-A")
    calls = Brain.calls - before
    expect(calls == 2, f"Expected 2 model calls (read, structure); got {calls}. Lookups should be plain code.")


def missing_po_goes_to_exception(ns):
    """An invoice with no PO reference (INV-07) ends at 'exception'"""
    out = _run(ns, "INV-07")
    expect(out.get("status") == "exception", f"INV-07 status should be 'exception', got {out.get('status')!r}")


def unknown_supplier_goes_to_exception(ns):
    """An unknown supplier (INV-15) ends at 'exception'"""
    out = _run(ns, "INV-15")
    expect(out.get("status") == "exception", f"INV-15 status should be 'exception', got {out.get('status')!r}")


CHECKS = [inv_a_end_to_end, fewer_model_calls, missing_po_goes_to_exception, unknown_supplier_goes_to_exception]
