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
from pumllint.rules import _CATALOG, discover

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
