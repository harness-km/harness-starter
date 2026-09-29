"""Self-checks: run `ct.selfcheck(<week>)` in the last cell of a lab.

Checks run against the fake model by default, so they cost nothing and give the same result
for everyone. `ct.selfcheck(<week>, live=True)` repeats them against Claude.
"""
from __future__ import annotations

import contextlib
import importlib
import inspect
import traceback


class Missing(Exception):
    """A name the check needs is not defined in the notebook yet."""


class CheckFailed(AssertionError):
    pass


def need(ns: dict, name: str, step: str):
    if name not in ns:
        raise Missing(f"`{name}` is not defined yet ({step}). Run that cell first.")
    return ns[name]


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def selfcheck(week: int, ns: dict | None = None, live: bool = False, verbose: bool = False) -> bool:
    if ns is None:
        ns = inspect.currentframe().f_back.f_globals
    import os
    live = live or os.environ.get("COURSE_SELFCHECK_LIVE") == "1"
    module = importlib.import_module(f"{__name__}.week{week:02d}")
    from ..runtime import fake_model

    use_fake = not live and getattr(module, "USES_MODEL", True)
    ctx = fake_model(ns) if use_fake else contextlib.nullcontext()
    results = []
    with ctx:
        for check in module.CHECKS:
            title = (check.__doc__ or check.__name__).strip().splitlines()[0]
            try:
                check(ns)
                results.append((True, title, ""))
            except Missing as e:
                results.append((None, title, str(e)))
            except CheckFailed as e:
                results.append((False, title, str(e)))
            except NotImplementedError:
                results.append((None, title, "Still a TODO: the function raises NotImplementedError."))
            except Exception as e:  # noqa: BLE001
                detail = f"{type(e).__name__}: {e}"
                if verbose:
                    detail += "\n" + traceback.format_exc()
                results.append((False, title, detail[:600]))
    from ..config import fake_mode as _fake_env
    mode = "offline (fake model)" if (use_fake or _fake_env()) else "live (Claude)"
    print(f"Week {week} self-check, {mode}")
    for ok, title, detail in results:
        mark = "PASS" if ok else ("TODO" if ok is None else "FAIL")
        print(f"  [{mark}] {title}")
        if detail:
            print(f"         {detail}")
    passed = sum(1 for ok, _, _ in results if ok)
    print(f"{passed}/{len(results)} checks passed." + ("  All done." if passed == len(results) else ""))
    summary = getattr(module, "SUMMARY", None)
    if summary and passed == len(results):
        print(summary)
    return passed == len(results)
