"""A fake Claude for self-checks, tests and offline demos.

It never calls the network. It answers from the dataset's answer key (ground_truth.json):
- vision requests get the transcription of the last PDF the notebook opened;
- structured-output requests get the invoice as an ideal reader would extract it;
- auditor requests compare a draft invoice with the answer key and flag differences;
- tool-use requests behave like a simple, deterministic agent.

`FakeAnthropic` mimics `anthropic.Anthropic`; `FakeChatModel` mimics a LangChain chat model.
The fake is deliberately simple. It is good enough to check that your code handles responses
correctly; it is not a model, so real-model behaviour can differ.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any

from .config import data_dir

# ----------------------------------------------------------------- shared "brain"

_LAST_PDF: dict[str, str | None] = {"path": None}
_GT_CACHE: dict[str, Any] = {}
IMAGE_TOKENS = 1600
ID_PATTERNS = {"po": re.compile(r"\bPO-\d{4}\b"), "supplier": re.compile(r"\bS\d{2}\b"),
               # supplier tax IDs: GSTIN (India), EIN (US), VAT ID (Germany), Business Number (Canada)
               "tax_id": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b|\b\d{2}-\d{7}\b"
                                    r"|\bDE\d{9}\b|\b\d{9} RT\d{4}\b")}


def note_pdf_opened(path: str) -> None:
    _LAST_PDF["path"] = str(path)


def ground_truth() -> list[dict]:
    path = data_dir() / "ground_truth.json"
    key = str(path)
    if key not in _GT_CACHE:
        if not path.exists():
            from .data.generate import ensure_dataset
            ensure_dataset()
        _GT_CACHE[key] = json.loads(path.read_text())["invoices"]
    return _GT_CACHE[key]


def tokens(text: str) -> int:
    return max(1, len(text) // 4)


def find_record(text: str) -> dict | None:
    """The invoice whose number (and date, if present) appears in the text."""
    best, best_score = None, 0
    for r in ground_truth():
        inv = r["invoice"]
        score = 0
        if inv["invoice_number"] in text:
            score += 2
            if inv["invoice_date"] in text:
                score += 1
        if score > best_score:
            best, best_score = r, score
    return best


def record_for_pdf(path: str | None) -> dict | None:
    if not path:
        return None
    name = str(path).replace("\\", "/").split("/")[-1]
    for r in ground_truth():
        if r["file"].endswith(name):
            return r
    return None


def _block_text(block: Any) -> str:
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        t = block.get("type")
        if t == "text":
            return block.get("text", "")
        if t == "tool_result":
            c = block.get("content", "")
            return c if isinstance(c, str) else " ".join(_block_text(x) for x in c)
        if t == "tool_use":
            return json.dumps(block.get("input", {}))
        return ""
    for attr in ("text",):  # SDK objects
        if hasattr(block, attr):
            return getattr(block, attr)
    return ""


def _content_blocks(msg: dict) -> list:
    c = msg.get("content", "")
    return [c] if isinstance(c, str) else list(c)


def _is_image(block: Any) -> bool:
    return isinstance(block, dict) and block.get("type") in ("image", "image_url", "document")


def all_text(system: Any, messages: list[dict]) -> str:
    parts = []
    if system:
        parts.append(system if isinstance(system, str) else " ".join(_block_text(b) for b in system))
    for m in messages:
        parts.extend(_block_text(b) for b in _content_blocks(m))
    return "\n".join(parts)


FILLER = ("Here is what that looks like in practice. A model call is an HTTP request with a model name, a system "
          "prompt, a list of messages and a token limit. The response carries content blocks, a stop reason and "
          "token usage. Everything a framework adds is built from these few fields, which is why reading the raw "
          "JSON first makes every later abstraction easier to debug. ")


def text_reply(prompt: str) -> str:
    long = any(w in prompt.lower() for w in ("long", "detail", "essay", "explain", "describe", "list ", "story"))
    if not long:
        return "(fake model) " + FILLER.split(". ")[1].strip() + "."
    return "(fake model) " + (FILLER * 8).strip()


class Brain:
    """Decides what the fake model says. Returns (blocks, stop_reason, usage)."""

    calls = 0

    def respond(self, *, system=None, messages, tools=None, max_tokens=1024, model="fake") -> tuple[list[dict], str, dict]:
        Brain.calls += 1
        prompt = all_text(system, messages)
        in_tok = tokens(prompt) + tokens(json.dumps(tools or []))
        last = messages[-1] if messages else {"content": ""}
        images = [b for b in _content_blocks(last) if _is_image(b)]
        in_tok += IMAGE_TOKENS * len(images)

        if images:
            rec = record_for_pdf(_LAST_PDF["path"])
            if rec is None:
                text = "(fake model) I can see an image, but the fake model only knows the course invoices."
            else:
                pages = rec["transcription"][:len(images)]
                text = "\n\n".join(pages)
            return self._text(text, max_tokens, in_tok)

        if tools:
            call = self._next_tool_call(messages, tools)
            if call:
                name, args = call
                block = {"type": "tool_use", "id": f"toolu_fake_{uuid.uuid4().hex[:12]}", "name": name, "input": args}
                return [block], "tool_use", {"input_tokens": in_tok, "output_tokens": tokens(json.dumps(args)) + 20}
            return self._text(self._report(messages), max_tokens, in_tok)

        if any(isinstance(b, dict) and b.get("type") == "tool_result" for m in messages for b in _content_blocks(m)):
            return self._text(self._report(messages), max_tokens, in_tok)
        return self._text(text_reply(prompt), max_tokens, in_tok)

    @staticmethod
    def _text(text: str, max_tokens: int, in_tok: int):
        out_tok = tokens(text)
        stop = "end_turn"
        if out_tok > max_tokens:
            text, out_tok, stop = text[: max_tokens * 4], max_tokens, "max_tokens"
        return [{"type": "text", "text": text}], stop, {"input_tokens": in_tok, "output_tokens": out_tok}

    @staticmethod
    def _calls_so_far(messages: list[dict]) -> list[tuple[str, str]]:
        done = []
        for m in messages:
            for b in _content_blocks(m):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    done.append((b["name"], json.dumps(b.get("input", {}), sort_keys=True)))
                elif hasattr(b, "type") and getattr(b, "type") == "tool_use":
                    done.append((b.name, json.dumps(b.input, sort_keys=True)))
        return done

    def _next_tool_call(self, messages: list[dict], tools: list[dict]) -> tuple[str, dict] | None:
        text = all_text(None, messages)
        asked = "\n".join(_block_text(b) for m in messages if m.get("role") == "user"
                          for b in _content_blocks(m) if not (isinstance(b, dict) and b.get("type") == "tool_result"))
        ids = {k: list(dict.fromkeys(p.findall(text))) for k, p in ID_PATTERNS.items()}
        ids["po"] = list(dict.fromkeys(ID_PATTERNS["po"].findall(asked)))  # only POs the user asked about
        done = set(self._calls_so_far(messages))
        for tool in tools:
            name = tool.get("name")
            schema = tool.get("input_schema") or tool.get("parameters") or {}
            required = schema.get("required") or list((schema.get("properties") or {}).keys())[:1]
            if not required:
                continue
            args = {}
            for prop in required:
                p = prop.lower()
                if "po" in p or "order" in p:
                    vals = ids["po"]
                elif "tax" in p or "gstin" in p or p == "ein":
                    vals = ids["tax_id"]
                elif "supplier" in p or "ref" in p:
                    vals = ids["supplier"] or ids["tax_id"]
                else:
                    vals = []
                if not vals:
                    args = None
                    break
                args[prop] = vals
            if not args:
                continue
            # try each candidate value in order until we find one not yet used
            first = required[0]
            for v in args[first]:
                candidate = {first: v}
                for prop in required[1:]:
                    candidate[prop] = args[prop][0]
                key = (name, json.dumps(candidate, sort_keys=True))
                if key not in done:
                    return name, candidate
        return None

    @staticmethod
    def _report(messages: list[dict]) -> str:
        results = []
        for m in messages:
            for b in _content_blocks(m):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results.append(_block_text(b)[:400])
        if not results:
            return "(fake model) Status report: no tool results were gathered."
        return "(fake model) Status report based on the tool results:\n- " + "\n- ".join(results)

    # ------------------------------------------------------------- structured output
    def structured(self, schema: type, messages: list[dict], system=None):
        Brain.calls += 1
        prompt = all_text(system, messages)
        fields = set(getattr(schema, "model_fields", {}).keys())
        rec = find_record(prompt)
        if {"decision", "flagged_fields"} <= fields:
            return schema.model_validate(self._audit(prompt, rec))
        if "invoice_number" in fields or "lines" in fields:
            if rec is None:
                raise ValueError("(fake model) could not find a course invoice number in the prompt")
            correcting = bool(re.search(r"flagged", prompt, re.I)) and rec["kind"] != "unreadable"
            data = rec["invoice"] if correcting else rec["reading"]
            return schema.model_validate(json.loads(json.dumps(data)))
        raise NotImplementedError(f"(fake model) does not know how to fill {schema.__name__}")

    @staticmethod
    def _draft_from(prompt: str) -> dict | None:
        dec = json.JSONDecoder()
        found = None
        for i, ch in enumerate(prompt):
            if ch != "{":
                continue
            try:
                obj, _ = dec.raw_decode(prompt[i:])
            except ValueError:
                continue
            if isinstance(obj, dict) and "lines" in obj:
                found = obj  # keep the last draft in the prompt
        return found

    def _audit(self, prompt: str, rec: dict | None) -> dict:
        draft = self._draft_from(prompt)
        if rec is None or draft is None:
            return {"decision": "reject", "rationale": "(fake model) could not locate the draft or the source text.",
                    "flagged_fields": []}
        truth = rec["invoice"] if rec["kind"] != "unreadable" else None
        if truth is None:
            return {"decision": "reject", "rationale": "(fake model) the source text is unreadable; numbers cannot be verified.",
                    "flagged_fields": ["lines"]}
        flagged = []
        for key in ("supplier_tax_id", "invoice_number", "invoice_date", "po_reference", "bill_to", "currency",
                    "bank_account", "bank_code", "subtotal", "total"):
            if key in draft and _norm(draft.get(key)) != _norm(truth.get(key)):
                flagged.append(key)
        if "tax_lines" in draft:
            d_tax = [(t.get("kind"), _norm(t.get("amount"))) for t in draft.get("tax_lines") or []]
            t_tax = [(t["kind"], _norm(t["amount"])) for t in truth["tax_lines"]]
            if d_tax != t_tax:
                flagged.append("tax_lines")
        d_lines, t_lines = draft.get("lines", []), truth["lines"]
        if len(d_lines) != len(t_lines):
            flagged.append("lines")
        else:
            for i, (a, b) in enumerate(zip(d_lines, t_lines)):
                for k in ("quantity", "unit_price", "amount", "tax_rate"):
                    if k in a and _norm(a[k]) != _norm(b[k]):
                        flagged.append(f"lines[{i}].{k}")
        if flagged:
            return {"decision": "reject", "rationale": "(fake model) these fields do not match the source text: "
                    + ", ".join(flagged), "flagged_fields": flagged}
        return {"decision": "accept", "rationale": "(fake model) every field matches the source text.",
                "flagged_fields": []}


def _norm(v):
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    if v in ("", None):
        return None
    return str(v)


BRAIN = Brain()

# ----------------------------------------------------------------- Anthropic SDK look-alike


def _to_dict(msg: Any) -> dict:
    if isinstance(msg, dict):
        return msg
    if hasattr(msg, "model_dump"):
        return msg.model_dump()
    return dict(msg)


class _Messages:
    def create(self, *, model: str, messages: list, max_tokens: int, system=None, tools=None, tool_choice=None, **kwargs):
        from anthropic.types import Message

        if isinstance(tool_choice, dict) and tool_choice.get("type") == "none":
            tools = None
        msgs = [_to_dict(m) for m in messages]
        for m in msgs:
            if isinstance(m.get("content"), list):
                m["content"] = [_to_dict(b) if not isinstance(b, (str, dict)) else b for b in m["content"]]
        blocks, stop, usage = BRAIN.respond(system=system, messages=msgs, tools=tools, max_tokens=max_tokens,
                                            model=model)
        return Message.model_validate({
            "id": f"msg_fake_{uuid.uuid4().hex[:16]}", "type": "message", "role": "assistant", "model": model,
            "content": blocks, "stop_reason": stop, "stop_sequence": None,
            "usage": {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
        })

    def count_tokens(self, *, model: str, messages: list, system=None, tools=None, **kwargs):
        from types import SimpleNamespace
        msgs = [_to_dict(m) for m in messages]
        n = tokens(all_text(system, msgs)) + tokens(json.dumps(tools or []))
        n += IMAGE_TOKENS * sum(1 for m in msgs for b in _content_blocks(m) if _is_image(b))
        return SimpleNamespace(input_tokens=n)


class FakeAnthropic:
    """Drop-in stand-in for anthropic.Anthropic() in self-checks and tests."""

    is_fake = True

    def __init__(self, *args, **kwargs):
        self.messages = _Messages()


# ----------------------------------------------------------------- LangChain look-alike

def _lc_to_anthropic(messages) -> tuple[str | None, list[dict]]:
    from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
    system, out = None, []
    for m in messages:
        if isinstance(m, SystemMessage):
            system = m.content if isinstance(m.content, str) else json.dumps(m.content)
            continue
        if isinstance(m, ToolMessage):
            out.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id,
                                                     "content": str(m.content)}]})
            continue
        role = "assistant" if isinstance(m, AIMessage) else "user"
        content = m.content
        if isinstance(m, AIMessage) and m.tool_calls:
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) and content else []
            blocks += [{"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["args"]}
                       for tc in m.tool_calls]
            content = blocks
        out.append({"role": role, "content": content})
    return system, out


def _make_fake_chat_model():
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.runnables import RunnableLambda
    from langchain_core.utils.function_calling import convert_to_openai_tool

    class FakeChatModel(BaseChatModel):
        """Stand-in for init_chat_model(...) in self-checks and tests."""

        model: str = "fake-claude"
        max_tokens: int = 1024
        bound_tools: list = []

        @property
        def _llm_type(self) -> str:
            return "fake-claude"

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            system, msgs = _lc_to_anthropic(messages)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            blocks, stop_reason, usage = BRAIN.respond(system=system, messages=msgs, tools=self.bound_tools or None,
                                                       max_tokens=max_tokens, model=self.model)
            text = "".join(b.get("text", "") for b in blocks if b["type"] == "text")
            tool_calls = [{"name": b["name"], "args": b["input"], "id": b["id"], "type": "tool_call"}
                          for b in blocks if b["type"] == "tool_use"]
            msg = AIMessage(content=text, tool_calls=tool_calls,
                            response_metadata={"stop_reason": stop_reason, "model": self.model},
                            usage_metadata={"input_tokens": usage["input_tokens"],
                                            "output_tokens": usage["output_tokens"],
                                            "total_tokens": usage["input_tokens"] + usage["output_tokens"]})
            return ChatResult(generations=[ChatGeneration(message=msg)])

        def bind_tools(self, tools, **kwargs):
            specs = []
            for t in tools:
                oa = convert_to_openai_tool(t)["function"]
                specs.append({"name": oa["name"], "description": oa.get("description", ""),
                              "input_schema": oa.get("parameters", {})})
            return self.model_copy(update={"bound_tools": specs})

        def with_structured_output(self, schema, include_raw: bool = False, **kwargs):
            model_name = self.model

            def run_raw(inp):
                from pydantic import ValidationError
                raw = AIMessage(content="", usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
                try:
                    parsed, err = run(inp), None
                except (ValidationError, ValueError) as e:
                    parsed, err = None, e
                prompt_tokens = tokens(str(inp))
                raw = AIMessage(content="", response_metadata={"model": model_name, "stop_reason": "tool_use"},
                                usage_metadata={"input_tokens": prompt_tokens, "output_tokens": 400,
                                                "total_tokens": prompt_tokens + 400})
                return {"raw": raw, "parsed": parsed, "parsing_error": err}

            def run(inp):
                from langchain_core.messages import HumanMessage
                from langchain_core.prompt_values import PromptValue
                if isinstance(inp, str):
                    messages = [HumanMessage(inp)]
                elif isinstance(inp, PromptValue):
                    messages = inp.to_messages()
                else:
                    from langchain_core.messages import convert_to_messages
                    messages = convert_to_messages(list(inp))
                system, msgs = _lc_to_anthropic(messages)
                return BRAIN.structured(schema, msgs, system=system)
            return RunnableLambda(run_raw if include_raw else run)

    return FakeChatModel


_FAKE_CHAT_CLASS = None


def FakeChatModel(**kwargs):
    global _FAKE_CHAT_CLASS
    if _FAKE_CHAT_CLASS is None:
        _FAKE_CHAT_CLASS = _make_fake_chat_model()
    allowed = {k: v for k, v in kwargs.items() if k in ("model", "max_tokens")}
    return _FAKE_CHAT_CLASS(**allowed)


def fake_init_chat_model(model: str | None = None, **kwargs):
    return FakeChatModel(model=model or "fake-claude", **kwargs)
