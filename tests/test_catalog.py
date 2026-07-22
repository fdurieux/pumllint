"""Guard the rule metadata catalog against the code that consumes it.

The declarative half of every rule lives in ``pumllint/rules/catalog.toml``;
``@register`` stamps it onto the class. These tests keep catalog and registry
in lock-step so a rule can never ship with missing, extra, or malformed
metadata.
"""

from pumllint.model import Dimension, Severity
from pumllint.rules import _CATALOG, discover

_REQUIRED_FIELDS = {"name", "description", "severity", "dimension", "applies_to"}
_VALID_SEVERITIES = {s.value for s in Severity}
_VALID_DIMENSIONS = {d.value for d in Dimension}


def test_every_registered_rule_has_a_catalog_entry():
    registered = set(discover())
    catalogued = set(_CATALOG)
    assert registered == catalogued, {
        "registered_without_entry": sorted(registered - catalogued),
        "catalogued_without_rule": sorted(catalogued - registered),
    }


def test_catalog_entries_are_well_formed():
    for rid, meta in _CATALOG.items():
        missing = _REQUIRED_FIELDS - set(meta)
        assert not missing, f"{rid} missing fields: {sorted(missing)}"
        assert meta["severity"] in _VALID_SEVERITIES, f"{rid}: bad severity {meta['severity']!r}"
        assert meta["dimension"] in _VALID_DIMENSIONS, f"{rid}: bad dimension {meta['dimension']!r}"
        assert meta["dimension"] != Dimension.SYNTAX.value, f"{rid}: DIM-SYN is a gate, not a rule dimension"
        assert isinstance(meta["applies_to"], list) and meta["applies_to"], f"{rid}: applies_to must be a non-empty list"
        assert isinstance(meta.get("profiles", []), list), f"{rid}: profiles must be a list"


def test_catalog_metadata_is_stamped_onto_the_class():
    for rid, cls in discover().items():
        meta = _CATALOG[rid]
        assert cls.name == meta["name"]
        assert cls.description == meta["description"]
        assert cls.default_severity == Severity(meta["severity"])
        assert cls.dimension == Dimension(meta["dimension"])
        assert cls.applies_to == tuple(meta["applies_to"])
        assert cls.profiles == tuple(meta.get("profiles", ()))


def test_rule_names_are_unique():
    names = [meta["name"] for meta in _CATALOG.values()]
    assert len(names) == len(set(names)), "duplicate rule names in catalog"
