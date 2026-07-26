"""Acceptance-oracle child: execute ONE scenario against ONE generated artifact.

Runs sandboxed (invoked with `python -I`, sockets disabled, stdin closed,
killed by the parent on timeout). Fully standalone — the scenario spec
arrives base64-JSON on argv, so no repo imports are needed under -I.

    python -I runner_child.py <artifact.py> <b64(spec)>

Prints exactly one JSON line on the LAST stdout line (artifact module-level
prints are swallowed):

    {"stage": ..., "passed": bool, "outcome_class": ..., "entry": ...,
     "calls": [...], "configs_applied": {...}, "detail": ...}

Stages, in the order they can occur:
    import_error | no_entry | construct_error | crash |
    wrong_outcome | missing_call | forbidden_call | pass
(`timeout` is stamped by the parent when it kills the child.)

Adapter rules (pre-registered in EVIDENCE.md — change only with a re-freeze):
- Every public method of every module-defined class is wrapped to record
  (class, method) calls; stub configs then REPLACE matching methods.
- Error stubs raise the artifact's OWN exception class when one matches
  `exc_like` (so typed error modeling is honored); otherwise they return the
  spec's failure object (return-style modeling), or None for db-find
  not-found when the spec says so.
- A stub config that matches nothing is recorded in configs_applied as
  false — the scenario still runs; the mismatch surfaces as failed checks.
- Entry resolution: module-level `handle(...)` first (pinned Phase B
  artifacts, outcome-only scoring decided by the parent), then a class
  matched by `entry_cls_like` (constructor params filled with module
  classes matched by name, else protean objects), then module functions
  matched by `entry_func_like`.
- Outcome classification is lexicon-based over the serialized return value
  or exception; failure tokens win over success tokens (conservative for
  success claims). Bare True => success-weak, bare False/None =>
  failure-weak, used only when no token matches.
"""

from __future__ import annotations

import base64
import contextlib
import functools
import inspect
import io
import json
import sys


# ---------------------------------------------------------------- proteans

class ProteanNum(int):
    """An int that tolerates attribute/key/call access (returns itself)."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self

    def __getitem__(self, key):
        return self

    def __call__(self, *a, **k):
        return self


class ProteanObj:
    """Duck-typed value: configured fields win, everything else is benign."""

    def __init__(self, fields=None, truthy=True):
        object.__setattr__(self, "_fields", dict(fields or {}))
        object.__setattr__(self, "_truthy", bool(truthy))

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        f = object.__getattribute__(self, "_fields")
        if name in f:
            return f[name]
        if name == "get":
            return lambda k, d=None: f.get(k, d if k not in f else f[k])
        return ProteanNum(1)

    def __getitem__(self, key):
        f = object.__getattribute__(self, "_fields")
        return f[key] if key in f else ProteanNum(1)

    def __contains__(self, key):
        return True

    def __bool__(self):
        return object.__getattribute__(self, "_truthy")

    def __str__(self):
        f = object.__getattribute__(self, "_fields")
        return "ProteanObj(%s)" % ", ".join(f"{k}={v!r}" for k, v in f.items())

    __repr__ = __str__


def build_value(spec):
    """Materialize a stub return value from its JSON spec."""
    if spec is None:
        return None
    if isinstance(spec, dict) and spec.get("_protean") == "num":
        return ProteanNum(spec["value"])
    if isinstance(spec, dict) and spec.get("_protean") == "obj":
        return ProteanObj(spec.get("fields", {}), truthy=spec.get("truthy", True))
    return spec


# ---------------------------------------------------------------- matching

def norm(name: str) -> str:
    return name.lower().replace("_", "").replace("-", "")


def like(name: str, patterns) -> bool:
    n = norm(name)
    return any(norm(p) in n for p in patterns)


# ---------------------------------------------------------------- outcome

def serialize_outcome(value) -> str:
    parts = []
    try:
        parts.append(str(value))
    except Exception:
        pass
    try:
        parts.append(repr(value))
    except Exception:
        pass
    d = getattr(value, "__dict__", None)
    if isinstance(d, dict):
        try:
            parts.append(str(d))
        except Exception:
            pass
    if isinstance(value, dict):
        parts.append(" ".join(f"{k}={v}" for k, v in value.items()))
    return " | ".join(parts).lower()


def classify(text: str, value, lex) -> str:
    if any(t in text for t in lex["failure"]):
        return "failure"
    if any(t in text for t in lex["success"]):
        return "success"
    if value is True:
        return "success"
    if value is False or value is None:
        return "failure"
    return "unknown"


# ---------------------------------------------------------------- main

def run(artifact_path: str, spec: dict) -> dict:
    out = {
        "stage": "pass", "passed": False, "outcome_class": None,
        "entry": None, "calls": [], "configs_applied": {}, "detail": "",
    }
    calls: list = []

    # 1. sandbox: no network, ever
    import socket

    def _no_net(*a, **k):  # noqa: ANN001
        raise RuntimeError("network disabled in acceptance sandbox")

    socket.socket = _no_net  # type: ignore[assignment]
    if hasattr(socket, "create_connection"):
        socket.create_connection = _no_net  # type: ignore[assignment]

    # 2. import the artifact (its prints and demo output are swallowed)
    import importlib.util

    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            mspec = importlib.util.spec_from_file_location("artifact", artifact_path)
            module = importlib.util.module_from_spec(mspec)
            # dataclasses & friends look their module up in sys.modules
            sys.modules["artifact"] = module
            mspec.loader.exec_module(module)
    except BaseException as e:  # noqa: BLE001 — SystemExit from demo code included
        out["stage"] = "import_error"
        out["detail"] = f"{type(e).__name__}: {e}"[:300]
        return out

    own_classes = {
        name: cls for name, cls in inspect.getmembers(module, inspect.isclass)
        if getattr(cls, "__module__", "") == "artifact"
    }
    own_excs = {
        name: cls for name, cls in own_classes.items()
        if issubclass(cls, BaseException)
    }

    # 3. instrument: record every public method call on every own class
    def recorder(cls_name, meth_name, fn):
        @functools.wraps(fn)
        def wrapped(*a, **k):
            calls.append([cls_name, meth_name])
            return fn(*a, **k)
        return wrapped

    for cname, cls in own_classes.items():
        if issubclass(cls, BaseException):
            continue
        for mname, attr in list(vars(cls).items()):
            if mname.startswith("_") or not inspect.isfunction(attr):
                continue
            try:
                setattr(cls, mname, recorder(cname, mname, attr))
            except (AttributeError, TypeError):
                pass

    # 4. apply scenario stubs
    stubbed: set = set()
    for i, cfg in enumerate(spec.get("stubs", [])):
        applied = []
        for cname, cls in own_classes.items():
            if issubclass(cls, BaseException):
                continue
            if cfg.get("cls_like") != ["*"] and not like(cname, cfg["cls_like"]):
                continue
            for mname in list(vars(cls)):
                if mname.startswith("_") or not like(mname, cfg["method_like"]):
                    continue
                if not callable(getattr(cls, mname, None)):
                    continue

                def make_stub(cn, mn, c=cfg):
                    def stub(self, *a, **k):  # noqa: ANN001
                        calls.append([cn, mn])
                        if c["action"] == "raise":
                            for ename, ecls in own_excs.items():
                                if like(ename, c.get("exc_like", [])):
                                    raise ecls(c.get("exc_msg", ename))
                            fb = c.get("raise_fallback", "return_failure")
                            if fb == "return_none":
                                return None
                            if fb == "runtime_error":
                                raise RuntimeError(c.get("exc_msg", "error"))
                            return build_value(c.get("failure_value"))
                        return build_value(c.get("value"))
                    return stub

                setattr(cls, mname, make_stub(cname, mname))
                stubbed.add((cname, mname))
                applied.append(f"{cname}.{mname}")
        out["configs_applied"][cfg.get("name", f"stub{i}")] = applied

    # 5. resolve the entry point
    entry_fn, entry_desc = None, None
    handle = getattr(module, "handle", None)
    if inspect.isfunction(handle):
        entry_fn = lambda: handle(dict(spec.get("request", {})))  # noqa: E731
        entry_desc = "handle()"
    if entry_fn is None:
        candidates = []
        for phase, pats in ((0, spec["entry_cls_like"]), (1, spec.get("entry_cls_fallback", []))):
            for cname, cls in own_classes.items():
                if not issubclass(cls, BaseException) and like(cname, pats):
                    candidates.append((phase, cname, cls))
        for _, cname, cls in sorted(candidates, key=lambda t: t[0]):
            try:
                instance = instantiate(cls, own_classes, spec)
            except Exception as e:  # noqa: BLE001
                out["stage"] = "construct_error"
                out["detail"] = f"{cname}: {type(e).__name__}: {e}"[:300]
                continue
            meth = find_entry_method(cls, spec["entry_method_like"], stubbed)
            if meth is None:
                continue
            bound = getattr(instance, meth)
            entry_fn = lambda b=bound: b(*make_args(b, spec))  # noqa: E731
            entry_desc = f"{cname}.{meth}"
            out["stage"] = "pass"  # clear an earlier construct_error
            break
    if entry_fn is None:
        for fname, fn in inspect.getmembers(module, inspect.isfunction):
            if fn.__module__ == "artifact" and not fname.startswith("_") \
                    and like(fname, spec.get("entry_func_like", [])):
                entry_fn = lambda f=fn: f(*make_args(f, spec))  # noqa: E731
                entry_desc = f"{fname}()"
                out["stage"] = "pass"
                break
    if entry_fn is None:
        if out["stage"] != "construct_error":
            out["stage"] = "no_entry"
        out["calls"] = calls
        return out
    out["entry"] = entry_desc

    # 6. run the flow
    lex = spec["lexicons"]
    exc = value = None
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            value = entry_fn()
    except BaseException as e:  # noqa: BLE001
        exc = e

    if exc is not None:
        # A builtin exception's TYPE name is not a semantic signal (else
        # AttributeError would read as "error" => failure); classify those
        # on the message alone. Module-defined exception names ARE semantic
        # (PaymentError, PolicyLapsedError, ...).
        import builtins
        tname = type(exc).__name__
        if hasattr(builtins, tname):
            text = str(exc).lower()
        else:
            text = f"{tname}: {exc}".lower()
        oc = classify(text, None, lex)
        text = f"{tname}: {exc}".lower()  # detail always keeps the type
        if oc == "unknown":
            out["stage"] = "crash"
            out["outcome_class"] = "crash"
            out["detail"] = text[:300]
            out["calls"] = calls
            return out
    else:
        text = serialize_outcome(value)
        oc = classify(text, value, lex)
    out["outcome_class"] = oc
    out["detail"] = text[:300]

    # 7. verdict: outcome expectation, then interaction checks
    expect = spec["expect"]
    ok = True
    if expect == "success":
        ok = oc == "success"
    elif expect == "failure":
        specific = [t.lower() for t in spec.get("failure_like", [])]
        ok = oc == "failure" and (not specific or any(t in text for t in specific))
    elif expect == "decision":
        ok = oc in ("success", "failure")
    # expect == "any": outcome unconstrained
    if not ok:
        out["stage"] = "wrong_outcome"

    # Pre-registered rule: interaction checks need the class-per-participant
    # shape; a handle()-entry artifact without it is scored on outcome only.
    n_plain_classes = sum(
        1 for c in own_classes.values() if not issubclass(c, BaseException))
    do_call_checks = spec.get("check_calls", True)
    if entry_desc == "handle()" and n_plain_classes < 2:
        do_call_checks = False
        out["call_checks_skipped"] = True
    if ok and do_call_checks:
        for req in spec.get("must_call", []):
            if not any(
                (req["cls_like"] == ["*"] or like(c, req["cls_like"]))
                and like(m, req["method_like"]) for c, m in calls
            ):
                ok = False
                out["stage"] = "missing_call"
                out["detail"] = f"missing {req['method_like']}; " + out["detail"]
                break
    if ok and do_call_checks:
        for req in spec.get("must_not_call", []):
            if any(
                (req["cls_like"] == ["*"] or like(c, req["cls_like"]))
                and like(m, req["method_like"]) for c, m in calls
            ):
                ok = False
                out["stage"] = "forbidden_call"
                out["detail"] = f"forbidden {req['method_like']}; " + out["detail"]
                break

    out["passed"] = ok
    if ok:
        out["stage"] = "pass"
    out["calls"] = calls[:200]
    return out


def best_class_match(pname, own_classes, exclude):
    """Score-ranked constructor-param -> class match: exact beats longest
    containment (so order_db resolves to OrderDB, never Order)."""
    scored = []
    npn = norm(pname)
    for cn, c in own_classes.items():
        if issubclass(c, BaseException) or c is exclude:
            continue
        ncn = norm(cn)
        if ncn == npn:
            score = 1000
        elif ncn in npn:
            score = 100 + len(ncn)
        elif npn in ncn:
            score = 50 + len(npn)
        else:
            continue
        scored.append((score, cn, c))
    return max(scored)[2] if scored else None


def instantiate(cls, own_classes, spec, depth=0):
    """cls() if possible, else fill required params by name-matched classes.

    Unmatched constructor params get a ProteanObj (never the entry-arg
    table: a ctor param named `customer` must tolerate method calls, which
    a plain string from the table would not).
    """
    try:
        return cls()
    except TypeError:
        pass
    if depth > 2:
        return ProteanObj()
    sig = inspect.signature(cls.__init__)
    args = []
    for pname, p in list(sig.parameters.items())[1:]:  # skip self
        if p.default is not inspect.Parameter.empty:
            continue
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        match = best_class_match(pname, own_classes, exclude=cls)
        if match is not None:
            args.append(instantiate(match, own_classes, spec, depth + 1))
        else:
            args.append(ProteanObj())
    return cls(*args)


def find_entry_method(cls, patterns, stubbed):
    ranked = []
    for mname in dir(cls):
        if mname.startswith("_") or (cls.__name__, mname) in stubbed:
            continue
        if not callable(getattr(cls, mname, None)):
            continue
        n = norm(mname)
        for rank, pat in enumerate(patterns):
            if norm(pat) in n:
                ranked.append((rank, mname))
                break
    return min(ranked)[1] if ranked else None


def make_named_arg(pname, spec):
    table = spec.get("args", {})
    n = norm(pname)
    for key, valspec in table.items():
        if norm(key) in n or n in norm(key):
            return build_value(valspec)
    return ProteanObj()


def make_args(fn, spec):
    sig = inspect.signature(fn)
    args = []
    for pname, p in sig.parameters.items():
        if pname == "self" or p.default is not inspect.Parameter.empty:
            continue
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        args.append(make_named_arg(pname, spec))
    return args


def main() -> int:
    artifact, b64 = sys.argv[1], sys.argv[2]
    spec = json.loads(base64.b64decode(b64))
    try:
        result = run(artifact, spec)
    except BaseException as e:  # noqa: BLE001 — the child must always report
        result = {
            "stage": "harness_error", "passed": False, "outcome_class": None,
            "entry": None, "calls": [], "configs_applied": {},
            "detail": f"{type(e).__name__}: {e}"[:300],
        }
    sys.stdout.write("\n" + json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
