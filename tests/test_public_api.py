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
    engine = pumllint.Engine({})
    groups = engine.lint_diagrams_grouped(diagrams)
    # Passing the engine makes its profile the C7 source of truth: no codegen
    # rules ran here, so Level 5 is honestly out of reach (cap at 4).
    results = pumllint.score_groups(groups, engine=engine)
    _, maturity = results[0]
    assert isinstance(maturity, pumllint.MaturityResult)
    assert maturity.level == 4
    assert "Level 4" in pumllint.get_reporter("text").render_maturity(results)
