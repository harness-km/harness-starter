"""Week 1: raw API calls, ask(), cost_of()."""
from types import SimpleNamespace

from ..config import MODELS
from . import expect, need

LONG_PROMPT = ("Explain in detail, step by step, how a supplier invoice moves from arrival to payment in a "
               "distributor's accounts payable team, including every check along the way.")


def ask_returns_text(ns):
    """ask() returns the reply as a string"""
    ask = need(ns, "ask", "step 3")
    out = ask("Say hello in five words.")
    expect(isinstance(out, str) and out.strip(), f"ask() should return a non-empty string, got {type(out).__name__}.")


def ask_raises_on_truncation(ns):
    """ask() raises TruncatedOutputError when the reply is cut off at max_tokens"""
    ask = need(ns, "ask", "step 3")
    err_cls = need(ns, "TruncatedOutputError", "step 3")
    try:
        ask(LONG_PROMPT, max_tokens=20)
    except err_cls:
        return
    except TypeError as e:
        raise AssertionError(f"ask() must accept max_tokens=...: {e}")
    raise AssertionError("ask(..., max_tokens=20) on a long prompt returned normally. Check response.stop_reason.")


def cost_matches_hand_calculation(ns):
    """cost_of() matches a hand calculation (SDK usage object and LangChain dict)"""
    cost_of = need(ns, "cost_of", "step 5")
    usage = SimpleNamespace(input_tokens=1000, output_tokens=500)
    got = cost_of(usage, MODELS["haiku"])
    expect(abs(got - 0.0035) < 1e-9, f"1,000 in + 500 out on Haiku should cost USD 0.0035, got {got}.")
    got2 = cost_of({"input_tokens": 2_000_000, "output_tokens": 100_000}, MODELS["sonnet"])
    expect(abs(got2 - 5.0) < 1e-6, f"2M in + 100k out on Sonnet should cost USD 5.00, got {got2}. "
                                   "Does cost_of handle a dict (LangChain's usage_metadata)?")


CHECKS = [ask_returns_text, ask_raises_on_truncation, cost_matches_hand_calculation]
