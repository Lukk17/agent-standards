"""Tests for .metrics/tools/quality_loop/edn.py: reading the score files the three tools write."""

import pytest
from tests.quality_loop_support import QUALITY_TOOLS  # noqa: F401  puts quality_loop on the path

from quality_loop import edn

CRAP = """{:entries [
  {:name "is_adult", :namespace "sample.rules", :complexity 1, :coverage 100.0, :crap 1.0}
  {:name "messy", :namespace "sample.rules", :complexity 7, :coverage nil, :crap nil}
]}
"""

MUTATE = (
    '{:version 1 :source "src/a.py" :outcomes {"[\\"src/a.py\\",\\"a\\",\\"defn/f\\",3,5,\\">=\\",\\">\\"]" :survived}'
    ' :forms [{:id "defn/f" :end-line 9 :killed 0 :survived 1}]}'
)


def test_a_crapper_snapshot_reads_as_maps_with_plain_key_lookups():
    data = edn.loads(CRAP)

    first, second = data["entries"]
    assert (first["name"], first["complexity"], first["coverage"]) == ("is_adult", 1, 100.0)
    assert second["crap"] is None


def test_a_mutator_snapshot_keeps_its_escaped_json_keys_and_keyword_values():
    data = edn.loads(MUTATE)

    ((mutation, status),) = data["outcomes"].items()
    assert mutation == '["src/a.py","a","defn/f",3,5,">=",">"]'
    assert status == "survived"
    assert isinstance(status, edn.Keyword)
    assert data["forms"][0]["end-line"] == 9


@pytest.mark.parametrize(("text", "value"), [("true", True), ("false", False), ("-2", -2), ("1e3", 1000.0), ("; note\n[]", [])])
def test_atoms_and_comments(text, value):
    assert edn.loads(text) == value


@pytest.mark.parametrize("text", ['"open', "{:a}", "[1 2", "#inst \"x\"", "1 2", "", "  ; only a comment"])
def test_text_outside_the_subset_is_refused(text):
    with pytest.raises(edn.EdnError):
        edn.loads(text)
