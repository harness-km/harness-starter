"""Week 5: generate, audit, correct."""
import json

from ..config import data_dir
from . import expect, need


def _gt(inv_id):
    gt = json.loads((data_dir() / "ground_truth.json").read_text())["invoices"]
    return next(r for r in gt if r["id"] == inv_id)


def _fixture(name):
    return json.loads((data_dir() / "fixtures" / f"{name}.json").read_text())["draft"]


def _raw(inv_id):
    return "\n\n".join(_gt(inv_id)["transcription"])


def corrections_touch_only_flagged(ns):
    """apply_corrections() changes only the flagged fields"""
    apply_corrections = need(ns, "apply_corrections", "step 4")
    draft = _fixture("misread_quantity")
    corrected = json.loads(json.dumps(_gt("INV-A")["invoice"]))
    corrected["supplier_name"] = "SOMETHING ELSE"
    merged = apply_corrections(draft, corrected, ["lines[0]"])
    expect(merged["lines"][0]["quantity"] == 30, "The flagged line should take the corrected quantity (30).")
    expect(merged["supplier_name"] == draft["supplier_name"], "An unflagged field (supplier_name) was changed.")
    expect(draft["lines"][0]["quantity"] == 3, "apply_corrections must not modify the draft passed in; copy it.")


def python_checks_flag_arithmetic(ns):
    """python_checks() flags the misread line before any model is asked"""
    python_checks = need(ns, "python_checks", "step 2")
    flags = python_checks(_fixture("misread_quantity"))
    expect(any(f.startswith("lines[0]") for f in flags), f"Expected a flag for lines[0], got {flags}")
    expect(python_checks(_gt("INV-A")["invoice"]) == [], "A correct USD invoice should produce no flags.")
    expect(python_checks(_gt("INV-10")["invoice"]) == [], "A correct INR invoice (INV-10) should produce no flags.")


def _result(ns, state):
    graph = need(ns, "extract_graph", "step 1")
    out = graph.invoke(state)
    res = out.get("result")
    expect(res is not None, "The graph's final state should contain `result` (an ExtractionResult).")
    return res


def clean_passes_first_time(ns):
    """The clean invoice is accepted first time"""
    res = _result(ns, {"raw_text": _raw("INV-A")})
    expect(res.status == "ACCEPTED" and not res.was_corrected and res.attempts == 0,
           f"Expected ACCEPTED, not corrected, 0 attempts; got {res.status}, {res.was_corrected}, {res.attempts}")


def misread_is_corrected(ns):
    """The misread quantity is corrected and re-approved (was_corrected)"""
    res = _result(ns, {"raw_text": _raw("INV-A"), "draft": _fixture("misread_quantity")})
    expect(res.status == "ACCEPTED" and res.was_corrected, f"Expected ACCEPTED with was_corrected; got {res.status}")
    expect(res.invoice.lines[0].quantity == 30, "Line 1 quantity should be corrected to 30.")


def missed_line_is_recovered(ns):
    """The line missed on page 2 is recovered"""
    res = _result(ns, {"raw_text": _raw("INV-05"), "draft": _fixture("missed_line_page2")})
    expect(res.status == "ACCEPTED" and len(res.invoice.lines) == 28, f"Expected 28 lines after correction; got {res.status}")


def unreadable_fails_after_two(ns):
    """The unreadable scan ends in EXTRACTION_FAILED after 2 attempts"""
    res = _result(ns, {"raw_text": _raw("INV-13")})
    expect(res.status == "EXTRACTION_FAILED" and res.attempts == 2,
           f"Expected EXTRACTION_FAILED after 2 attempts; got {res.status} after {res.attempts}")
    expect(res.invoice is None, "A failed extraction must not return an invoice.")


def one_schema_every_branch(ns):
    """Every branch returns the same ExtractionResult schema"""
    cls = need(ns, "ExtractionResult", "step 1")
    for state in ({"raw_text": _raw("INV-A")}, {"raw_text": _raw("INV-13")}):
        res = _result(ns, state)
        expect(isinstance(res, cls), f"Expected an ExtractionResult, got {type(res).__name__}")


CHECKS = [corrections_touch_only_flagged, python_checks_flag_arithmetic, clean_passes_first_time,
          misread_is_corrected, missed_line_is_recovered, unreadable_fails_after_two, one_schema_every_branch]
