from app.services.knowledge.linkparse import extract_links


def test_absolute_link_resolves_and_strips_md():
    body = "See [orders](/tasks/42.md) now."
    assert extract_links(body, "projects/7") == ["tasks/42"]


def test_relative_link_resolved_against_base_dir():
    body = "See [sibling](./other.md) and [up](../tables/x.md)."
    # base_id projects/7/notes -> dir projects/7
    assert extract_links(body, "projects/7/notes") == ["projects/7/other", "projects/tables/x"]


def test_external_links_ignored():
    body = "Docs at [site](https://example.com/page) and [a](/knowledge/a.md)."
    assert extract_links(body, "knowledge/root") == ["knowledge/a"]


def test_anchor_fragment_stripped():
    body = "[x](/tasks/9.md#schema)"
    assert extract_links(body, "x") == ["tasks/9"]


def test_dedupes_preserving_order():
    body = "[a](/k/a.md) [a again](/k/a.md) [b](/k/b.md)"
    assert extract_links(body, "k/root") == ["k/a", "k/b"]
