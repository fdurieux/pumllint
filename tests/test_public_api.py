"""Guard the package's public API surface (pumllint/__init__.py)."""

_SRC = (
    "@startuml Flow\ntitle Flow\nparticipant Alice\nparticipant Bob\n"
    "Alice -> Bob : greet()\nBob --> Alice : ack\n@enduml\n"
)


def test_package_exposes_the_public_api():
    import pumllint

    for name in pumllint.__all__:
        assert hasattr(pumllint, name), f"pumllint.{name} missing"
    assert pumllint.__version__


def test_public_api_lints_and_scores_end_to_end():
    import pumllint

    diagrams = pumllint.parse_source(_SRC, "t.puml")
    groups = pumllint.Engine({}).lint_diagrams_grouped(diagrams)
    results = pumllint.score_groups(groups, active_profile="codegen")
    _, maturity = results[0]
    assert isinstance(maturity, pumllint.MaturityResult)
    assert maturity.level == 5  # clean diagram, profile active
    assert "Level 5" in pumllint.get_reporter("text").render_maturity(results)
