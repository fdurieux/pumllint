"""The two arms (pre-registration §7): one generator call each, JSON mode.

Budget guard: MAX_CALLS and a dollar ceiling over the API's usage field,
priced at the list rates recorded below (read 2026-10-30; the record
quotes measured tokens, the dollars are an estimate).
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
RECORD_MODEL = "gpt-5.1-2025-11-13"  # the model of the scored run; the record's figures are this model's
# The demo's Arms mode may call another model through KG_ARMS_MODEL (a legacy model's
# rate limit on a new organisation blocked the governed prompt there); such runs are a
# deviation the demo page names, and they never write into results/.
MODEL = os.environ.get("KG_ARMS_MODEL") or RECORD_MODEL
MAX_CALLS = 90
CEILING_USD = 25.0
PRICE_IN, PRICE_OUT = 1.25 / 1e6, 10.0 / 1e6  # USD per token, the record model's list price read 2026-10-30

_lock = threading.Lock()
_state = {"calls": 0, "usd": 0.0, "usage": []}


class BudgetExceeded(RuntimeError):
    pass


def policy() -> str:
    return (HERE / "policy.md").read_text(encoding="utf-8")


def prompt(name: str) -> str:
    return (HERE / "prompts" / f"{name}.md").read_text(encoding="utf-8")


def baseline_documents(kit: dict[str, str], order: list[str]) -> str:
    parts = []
    for path in order:
        if path in kit:
            parts.append(f"=== {path} ===\n{kit[path]}\n")
    return "\n".join(parts)


def call(system: str, user: str, *, tag: str) -> dict:
    with _lock:
        if _state["calls"] >= MAX_CALLS:
            raise BudgetExceeded(f"MAX_CALLS={MAX_CALLS}")
        if _state["usd"] >= CEILING_USD:
            raise BudgetExceeded(f"ceiling ${CEILING_USD}")
        _state["calls"] += 1
    # the scored run went through the session proxy, which injected the key and
    # ignored the placeholder; outside it (the demo container, a laptop) the key
    # comes from the environment and is never written to disk
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY") or "proxy-injected", max_retries=0)
    t0 = time.time()
    attempts = 0
    while True:
        attempts += 1
        try:
            # streamed, because the session proxy cuts a non-streaming call that stays
            # silent too long (the OpenWiki record's finding, 2026-10-28); the chunks are
            # concatenated and usage is taken from the final chunk
            stream = client.chat.completions.create(
                model=MODEL, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                stream=True, stream_options={"include_usage": True},
            )
            parts, usage_obj, model_name = [], None, MODEL
            for chunk in stream:
                if chunk.usage:
                    usage_obj = chunk.usage
                if getattr(chunk, "model", None):
                    model_name = chunk.model
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    parts.append(chunk.choices[0].delta.content)
            if usage_obj is None:
                raise RuntimeError("stream ended without a usage chunk")
            break
        except Exception as e:  # noqa: BLE001 — transient 5xx/429 from the proxy; retried, counted
            if attempts >= 4:
                raise
            with _lock:
                _state.setdefault("retries", []).append({"tag": tag, "attempt": attempts, "error": str(e)[:200]})
            time.sleep(5 * attempts)
    dt = time.time() - t0
    u = usage_obj
    usd = u.prompt_tokens * PRICE_IN + u.completion_tokens * PRICE_OUT
    rec = {"tag": tag, "model": model_name, "attempts": attempts, "streamed": True, "prompt_tokens": u.prompt_tokens,
           "completion_tokens": u.completion_tokens, "seconds": round(dt, 1), "usd_est": round(usd, 4)}
    with _lock:
        _state["usd"] += usd
        _state["usage"].append(rec)
    raw = "".join(parts)
    try:
        parsed = json.loads(raw)
        parse_error = None
    except json.JSONDecodeError as e:
        parsed, parse_error = None, str(e)
    return {"raw": raw, "parsed": parsed, "parse_error": parse_error, "usage": rec}


def usage() -> dict:
    return {"calls": _state["calls"], "usd_est": round(_state["usd"], 4), "retries": list(_state.get("retries", [])),
            "per_call": list(_state["usage"])}
