"""The resource meter: tokens, cost and latency per stage."""
from __future__ import annotations

import time
from contextlib import contextmanager

from .config import PRICES_PER_MTOK


def usage_numbers(usage) -> tuple[int, int]:
    """Input and output tokens from an SDK Usage object, a LangChain usage_metadata dict, or a plain dict."""
    if usage is None:
        return 0, 0
    if isinstance(usage, dict):
        return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)


def price(model: str) -> tuple[float, float]:
    for key, value in PRICES_PER_MTOK.items():
        if model.startswith(key):
            return value
    raise KeyError(f"No price for model {model!r}. Known: {list(PRICES_PER_MTOK)}")


class Meter:
    """Record one row per model call; report by stage.

    meter = Meter()
    meter.record("read", response.usage, model)
    meter.report()
    """

    def __init__(self):
        self.rows: list[dict] = []
        self._t0: float | None = None

    def record(self, stage: str, usage, model: str, seconds: float | None = None) -> dict:
        tin, tout = usage_numbers(usage)
        pin, pout = price(model)
        row = {"stage": stage, "model": model, "input_tokens": tin, "output_tokens": tout,
               "cost_usd": round(tin / 1e6 * pin + tout / 1e6 * pout, 6), "seconds": seconds}
        self.rows.append(row)
        return row

    @contextmanager
    def timer(self):
        t0 = time.perf_counter()
        box = {}
        yield box
        box["seconds"] = round(time.perf_counter() - t0, 2)

    def reset(self) -> None:
        self.rows.clear()

    def total(self) -> dict:
        return {"calls": len(self.rows), "input_tokens": sum(r["input_tokens"] for r in self.rows),
                "output_tokens": sum(r["output_tokens"] for r in self.rows),
                "cost_usd": round(sum(r["cost_usd"] for r in self.rows), 6)}

    def report(self):
        import pandas as pd
        if not self.rows:
            return pd.DataFrame(columns=["stage", "model", "calls", "input_tokens", "output_tokens", "cost_usd"])
        df = pd.DataFrame(self.rows)
        out = df.groupby(["stage", "model"], sort=False).agg(
            calls=("stage", "size"), input_tokens=("input_tokens", "sum"),
            output_tokens=("output_tokens", "sum"), cost_usd=("cost_usd", "sum")).reset_index()
        return out
