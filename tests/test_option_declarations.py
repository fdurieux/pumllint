"""Hold ``catalog.toml``'s option declaration to the reads in the rule bodies.

Every rule class carries ``option_keys`` (catalog ``options`` plus each
``lexicons`` entry as ``<k>`` and ``extra_<k>``) and ``dormant_unless``.
``config.config_warnings`` trusts that declaration to disclose typo'd option
keys, and ``--list-rules`` trusts ``dormant_unless`` for its DORMANT tag — so
the declaration must match what ``check()`` actually reads, in both
directions. Issue #33 found ``accept_detach`` documented twice and read
nowhere; this is the guard it asked for, from the declaration's side.

Reads are recovered from the module's AST: ``self.options.get("k")``,
``self.options["k"]``, ``"k" in self.options``, ``self.pattern_option("k")``,
``self.lexicon("k")`` (two keys), and a module-level helper that receives
``self.options`` as an argument (the XD pack's ``_authoritative`` /
``_distinct``), recursed into with the receiver rebound to its parameter.
Only string-literal keys count, so the dynamic reads inside the base helpers
(``pattern_option``, ``lexicon``) are invisible here by construction — their
callers are the read sites. Base classes are walked too, so an inherited
``check()`` counts for the subclass.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from pumllint.config import GENERIC_RULE_KEYS
from pumllint.rules import _CATALOG, OPTION_TYPES, discover

_TREES: dict[str, ast.Module] = {}


def _tree(module_name: str) -> ast.Module:
    if module_name not in _TREES:
        path = Path(sys.modules[module_name].__file__)
        _TREES[module_name] = ast.parse(path.read_text(encoding="utf-8"))
    return _TREES[module_name]


def _class_def(tree: ast.Module, name: str) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _function_def(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _self_options(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "options"
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _keys_read(body: ast.AST, is_options, tree: ast.Module, depth: int = 0) -> set[str]:
    keys: set[str] = set()
    for node in ast.walk(body):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func = node.func
            if func.attr == "get" and is_options(func.value) and node.args:
                k = _literal(node.args[0])
                if k:
                    keys.add(k)
            elif (
                func.attr in ("pattern_option", "lexicon")
                and isinstance(func.value, ast.Name)
                and func.value.id == "self"
                and node.args
            ):
                k = _literal(node.args[0])
                if k:
                    keys.add(k)
                    if func.attr == "lexicon":
                        keys.add(f"extra_{k}")
        elif isinstance(node, ast.Subscript) and is_options(node.value):
            k = _literal(node.slice)
            if k:
                keys.add(k)
        elif (
            isinstance(node, ast.Compare)
            and any(isinstance(op, ast.In) for op in node.ops)
            and any(is_options(c) for c in node.comparators)
        ):
            k = _literal(node.left)
            if k:
                keys.add(k)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and depth < 2:
            fn = _function_def(tree, node.func.id)
            if fn is None:
                continue
            for i, arg in enumerate(node.args):
                if is_options(arg) and i < len(fn.args.args):
                    param = fn.args.args[i].arg
                    keys |= _keys_read(
                        fn,
                        lambda n, p=param: isinstance(n, ast.Name) and n.id == p,
                        tree,
                        depth + 1,
                    )
    return keys


def _reads(cls) -> set[str]:
    keys: set[str] = set()
    for base in cls.__mro__:
        if not base.__module__.startswith("pumllint.rules"):
            continue
        tree = _tree(base.__module__)
        node = _class_def(tree, base.__name__)
        if node is not None:
            keys |= _keys_read(node, _self_options, tree)
    return keys


def _all_reads() -> dict[str, set[str]]:
    return {rid: _reads(cls) for rid, cls in discover().items()}


def test_every_option_a_rule_reads_is_declared():
    """A read the catalog does not declare would be *disclosed as a typo*."""
    problems = {}
    for rid, cls in discover().items():
        undeclared = _reads(cls) - cls.option_keys - GENERIC_RULE_KEYS
        if undeclared:
            problems[rid] = sorted(undeclared)
    assert not problems, f"read but not declared in catalog.toml: {problems}"


def test_every_declared_option_is_read():
    """A declaration nothing reads is #33's `accept_detach` all over again.

    ``dormant_unless`` keys count as read: ``Rule.dormant`` reads them, and a
    gated rule may have no other read of its own gate (SEQ010).
    """
    problems = {}
    for rid, cls in discover().items():
        unread = cls.option_keys - _reads(cls) - set(cls.dormant_unless)
        if unread:
            problems[rid] = sorted(unread)
    assert not problems, f"declared in catalog.toml but never read: {problems}"


def test_the_ast_walk_is_not_vacuous():
    """If the walker silently stopped seeing reads, both tests above would
    pass for the wrong reason — pin the shapes it must recognise."""
    reads = _all_reads()
    assert sum(len(v) for v in reads.values()) >= 40, reads
    assert reads["GEN004"] == {"pattern", "per_kind"}  # .get
    assert reads["GEN005"] == {"max", "per_type"}  # `in` test + subscript
    assert reads["SEQ008"] == {"max_nesting_depth", "max"}  # nested .get
    assert reads["SEQ107"] == {"failure_keywords", "extra_failure_keywords"}  # lexicon
    assert reads["CLS001"] == {"class_pattern", "member_pattern"}  # pattern_option
    assert reads["XD001"] == {"authoritative", "distinct"}  # module-level helpers
    assert reads["GEN001"] == set()  # takes no options


# --- types (2026-09-07: `options` became a `name = "type"` table, the source
# of pumllint/schemas/config.schema.json) ---------------------------------------

_LITERAL_TYPES = {
    bool: {"boolean"},
    int: {"integer", "number"},
    float: {"number"},
    str: {"string", "regex"},
    list: {"list"},
    tuple: {"list"},
    dict: {"map", "map-integer", "map-regex"},
}


def _default_literals(cls) -> dict[str, object]:
    """``self.options.get("k", <literal>)`` / ``self.pattern_option("k", <literal>)``
    defaults that are plain literals — the code's own word on the option's type."""
    found: dict[str, object] = {}
    for base in cls.__mro__:
        if not base.__module__.startswith("pumllint.rules"):
            continue
        node = _class_def(_tree(base.__module__), base.__name__)
        if node is None:
            continue
        for call in ast.walk(node):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)):
                continue
            is_get = call.func.attr == "get" and _self_options(call.func.value)
            is_helper = (
                call.func.attr == "pattern_option"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "self"
            )
            if not (is_get or is_helper) or len(call.args) < 2:
                continue
            key = _literal(call.args[0])
            if key is None:
                continue
            try:
                found.setdefault(key, ast.literal_eval(call.args[1]))
            except ValueError:
                pass  # a name (DEFAULT_MAX, _SIGNATURE.pattern): no literal to check
    return found


def test_every_declared_option_has_a_type_from_the_vocabulary():
    for rid, cls in discover().items():
        assert set(cls.option_types) == cls.option_keys, rid
        for key, kind in cls.option_types.items():
            assert kind in OPTION_TYPES, (rid, key, kind)
        for lx in _CATALOG[rid].get("lexicons", ()):
            assert cls.option_types[lx] == cls.option_types[f"extra_{lx}"] == "list"


def test_declared_types_agree_with_the_code_defaults():
    """Where a rule spells its default as a literal, the catalog's type must be
    the literal's — a wrong type would make the config schema validate a
    config wrongly, the one way this declaration can lie."""
    checked = 0
    for rid, cls in discover().items():
        for key, default in _default_literals(cls).items():
            if default is None:
                continue  # "unset" carries no type
            kind = cls.option_types[key]
            assert kind in _LITERAL_TYPES[type(default)], (rid, key, kind, default)
            checked += 1
    assert checked >= 10, checked


def test_dormant_unless_keys_are_declared_options():
    for rid, meta in _CATALOG.items():
        gate = set(meta.get("dormant_unless", ()))
        legal = set(meta.get("options", ())) | {
            k for lx in meta.get("lexicons", ()) for k in (lx, f"extra_{lx}")
        }
        assert gate <= legal, f"{rid}: dormant_unless {sorted(gate - legal)} not in options"


def test_the_gated_rules_are_exactly_the_five_the_record_names():
    gated = sorted(rid for rid, cls in discover().items() if cls.dormant_unless)
    assert gated == ["ACT006", "GEN006", "GEN007", "SEQ010", "UC002"], gated
