"""Notebook start-up: dataset, API key, and (for tests) the fake model."""
from __future__ import annotations

import contextlib
import os
import sys
from types import SimpleNamespace

from . import fake
from .config import MODELS, data_dir, fake_mode, in_colab

_PATCHED: dict = {}


def _track_pdf_opens() -> None:
    """Remember which PDF was opened last, so the fake model knows which invoice it is 'looking at'."""
    for modname in ("pymupdf",):
        try:
            mod = __import__(modname)
        except Exception:
            continue
        if getattr(mod.open, "_course_tracked", False):
            continue
        original = mod.open

        def tracked(*args, _orig=original, **kwargs):
            target = args[0] if args else kwargs.get("filename")
            if isinstance(target, (str, os.PathLike)):
                fake.note_pdf_opened(str(target))
            return _orig(*args, **kwargs)

        tracked._course_tracked = True
        mod.open = tracked


def install_fake_model() -> None:
    """Replace anthropic.Anthropic and init_chat_model with fakes (used when COURSE_FAKE_LLM=1)."""
    import anthropic
    import langchain.chat_models as lcm

    if not _PATCHED:
        _PATCHED["anthropic"] = anthropic.Anthropic
        _PATCHED["init_chat_model"] = lcm.init_chat_model
    anthropic.Anthropic = fake.FakeAnthropic
    lcm.init_chat_model = fake.fake_init_chat_model
    try:
        import langchain_anthropic
        _PATCHED.setdefault("ChatAnthropic", langchain_anthropic.ChatAnthropic)
        langchain_anthropic.ChatAnthropic = lambda **kw: fake.FakeChatModel(**kw)
    except ImportError:
        pass


def remove_fake_model() -> None:
    if not _PATCHED:
        return
    import anthropic
    import langchain.chat_models as lcm
    anthropic.Anthropic = _PATCHED["anthropic"]
    lcm.init_chat_model = _PATCHED["init_chat_model"]
    if "ChatAnthropic" in _PATCHED:
        import langchain_anthropic
        langchain_anthropic.ChatAnthropic = _PATCHED["ChatAnthropic"]
    _PATCHED.clear()


@contextlib.contextmanager
def fake_model(ns: dict | None = None):
    """Temporarily run everything against the fake model, including a notebook's globals."""
    already = bool(_PATCHED)
    install_fake_model()
    saved = {}
    if ns is not None:
        for name, value in (("client", fake.FakeAnthropic()), ("llm", fake.FakeChatModel(model=MODELS["sonnet"]))):
            if name in ns:
                saved[name] = ns[name]
                ns[name] = value
        import anthropic
        import langchain.chat_models as lcm
        for name, value in (("Anthropic", anthropic.Anthropic), ("init_chat_model", lcm.init_chat_model)):
            if name in ns:
                saved[name] = ns[name]
                ns[name] = value
    try:
        yield
    finally:
        if ns is not None:
            ns.update(saved)
        if not already:
            remove_fake_model()


def _load_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    if in_colab():
        try:
            from google.colab import userdata
            key = userdata.get("ANTHROPIC_API_KEY")
        except Exception:
            key = None
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key
    return key


def bootstrap(quiet: bool = False) -> SimpleNamespace:
    """Run at the top of every lab: data ready, key loaded (never printed), fake model if requested."""
    from .data.generate import ensure_dataset

    _track_pdf_opens()
    out = ensure_dataset()
    key = _load_key()
    offline = fake_mode()
    if offline:
        install_fake_model()
    env = SimpleNamespace(data=out, db=out / "distributor.db", invoices=out / "invoices",
                          fixtures=out / "fixtures", models=MODELS, offline=offline, key_loaded=bool(key))
    if not quiet:
        mode = "OFFLINE (fake model)" if offline else ("key loaded" if key else "NO API KEY FOUND")
        print(f"Dataset: {out}")
        print(f"Models:  haiku={MODELS['haiku']}  sonnet={MODELS['sonnet']}  opus={MODELS['opus']}")
        print(f"Claude:  {mode}")
        if not key and not offline:
            print("  -> Add ANTHROPIC_API_KEY in Colab Secrets (key icon, left sidebar) and turn on Notebook access.",
                  file=sys.stderr)
    return env
