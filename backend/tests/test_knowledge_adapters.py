from app.services.knowledge.adapters.base import Concept, FieldCaps


def test_concept_defaults():
    c = Concept(concept_id="knowledge/x", type="Note", source="native")
    assert c.tags == []
    assert c.frontmatter == {}
    assert c.body == ""


def test_fieldcaps_shape():
    fc = FieldCaps(writable={"title": "native"}, readonly=["concept_id"])
    assert fc.writable["title"] == "native"
    assert "concept_id" in fc.readonly
