from omoide.search import (
    build_fts_expression,
    highlight_positions,
    make_snippet,
    parse_query,
)


def test_parse_query_filters():
    query = parse_query("timeout app:chrome kind:image since:7d pin:true")
    assert query.text == "timeout"
    assert query.apps == ["chrome"]
    assert query.kinds == ["image"]
    assert query.since_days == 7
    assert query.pinned_only is True
    assert query.terms == ["timeout"]


def test_fts_expression_is_quoted():
    assert build_fts_expression('foo bar"baz') == '"foo"* AND "barbaz"*'
    assert build_fts_expression("   ") is None


def test_highlight_positions_do_not_overlap():
    ranges = highlight_positions("the timeout is a timeout", ["timeout", "time"])
    assert ranges == [(4, 11), (17, 24)]


def test_snippet_centres_on_match():
    text = "x" * 300 + "needle" + "y" * 300
    snippet = make_snippet(text, ["needle"])
    assert "needle" in snippet
    assert len(snippet) <= 264
