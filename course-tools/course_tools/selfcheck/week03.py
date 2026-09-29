"""Week 3: tools and the agent loop."""
import json
import sqlite3

from ..config import data_dir
from ..fake import Brain
from . import expect, need


def _db():
    return sqlite3.connect(data_dir() / "distributor.db")


def goods_receipt_matches(ns):
    """get_goods_receipt('PO-1001') returns received quantities per line (30 and 40)"""
    fn = need(ns, "get_goods_receipt", "step 2")
    out = fn("PO-1001")
    received = [ln.get("received") for ln in out.get("lines", [])] if isinstance(out, dict) else []
    expect(received == [30, 40], f"Expected received quantities [30, 40] for PO-1001's two lines, got: "
                                 f"{json.dumps(out, default=str)[:300]}")


def unknown_po_is_explicit(ns):
    """get_purchase_order('PO-9999') says 'PO-9999 not found'"""
    fn = need(ns, "get_purchase_order", "step 2")
    out = fn("PO-9999")
    expect("PO-9999 not found" in json.dumps(out, default=str),
           "Return an explicit error like {'error': 'PO-9999 not found. ...'}, never an empty result.")


def injection_is_refused(ns):
    """get_purchase_order() refuses an injected ID instead of running it"""
    fn = need(ns, "get_purchase_order", "step 2")
    out = fn("PO-1001' OR '1'='1")
    text = json.dumps(out, default=str)
    con = _db()
    n = con.execute("select count(*) from purchase_orders").fetchone()[0]
    con.close()
    expect("PO-1002" not in text, f"The injected ID returned other purchase orders (the table has {n}). Validate "
                                  "the ID with a pattern and use ? placeholders.")
    expect("error" in text.lower(), "An invalid ID should return an explicit error.")


def supplier_lookup_works(ns):
    """get_supplier() finds a supplier by ID, by EIN (US) and by GSTIN (India)"""
    fn = need(ns, "get_supplier", "step 2")
    con = _db()
    ein = con.execute("select tax_id from suppliers where supplier_id='S01'").fetchone()[0]
    gstin = con.execute("select tax_id from suppliers where supplier_id='S07'").fetchone()[0]
    con.close()
    a, b, c = fn("S01"), fn(ein), fn(gstin)
    expect("Pinecrest" in json.dumps(a) and "Pinecrest" in json.dumps(b),
           "get_supplier should accept 'S01' or its EIN.")
    expect("Sahyadri" in json.dumps(c), "get_supplier should also accept an Indian supplier's GSTIN.")
    expect("USD" in json.dumps(a) and "INR" in json.dumps(c), "Return each supplier's currency.")


def purchase_order_has_currency(ns):
    """get_purchase_order() returns the PO's currency and buyer company"""
    fn = need(ns, "get_purchase_order", "step 2")
    us, india = fn("PO-1001"), fn("PO-1003")
    expect(us.get("currency") == "USD" and us.get("entity_id") == "US",
           f"PO-1001 is a USD order for the US company; got currency={us.get('currency')}, entity_id={us.get('entity_id')}.")
    expect(india.get("currency") == "INR" and india.get("entity_id") == "IN",
           f"PO-1003 is an INR order for the Indian company; got currency={india.get('currency')}.")


def loop_stops_with_report(ns):
    """run_agent() stops at max_steps and still returns a status report"""
    run_agent = need(ns, "run_agent", "step 3")
    tools = need(ns, "TOOLS", "step 2")
    messages = [{"role": "user", "content": "Has PO-1001 been fully received, and has it been invoiced?"}]
    before = Brain.calls
    out = run_agent(messages, tools, max_steps=1)
    calls = Brain.calls - before
    expect(isinstance(out, str) and out.strip(), "run_agent should return the final text.")
    expect(calls == 2, f"With max_steps=1 expect 2 model calls (one step + one final report without tools), got {calls}.")


def loop_answers_question(ns):
    """run_agent() uses the tools to answer the PO-1001 question"""
    run_agent = need(ns, "run_agent", "step 3")
    tools = need(ns, "TOOLS", "step 2")
    messages = [{"role": "user", "content": "Has PO-1001 been fully received, and has it been invoiced?"}]
    run_agent(messages, tools, max_steps=8)
    used = [b.get("name") if isinstance(b, dict) else getattr(b, "name", None)
            for m in messages if m["role"] == "assistant" and isinstance(m["content"], list)
            for b in m["content"] if (b.get("type") if isinstance(b, dict) else getattr(b, "type", "")) == "tool_use"]
    expect("get_goods_receipt" in used, f"Expected a get_goods_receipt call in the trace; tools used: {used}. "
                                        "Is the tool result appended to messages each turn?")


CHECKS = [goods_receipt_matches, unknown_po_is_explicit, injection_is_refused, supplier_lookup_works,
          purchase_order_has_currency,
          loop_stops_with_report, loop_answers_question]
