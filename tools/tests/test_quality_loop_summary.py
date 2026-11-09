"""Tests for .metrics/tools/quality_loop/summary.py: the worst scores, as plain text."""

import json

from tests.quality_loop_support import write

from quality_loop import summary


def crap_entry(name, crap, coverage=50.0, complexity=3):
    return f'{{:name "{name}", :namespace "m", :complexity {complexity}, :coverage {coverage}, :crap {crap}}}'


def test_crap_is_listed_worst_first_with_robert_martins_bands(tmp_path):
    entries = [crap_entry("fine", 4.0), crap_entry("bad", 42.5), crap_entry("meh", 12.0), crap_entry("off", "nil")]
    write(tmp_path, ".metrics/crap.edn", "{:entries [" + " ".join(entries) + "]}")

    lines = summary.crap_section(tmp_path, limit=10)

    assert lines[0] == "CRAP (.metrics/crap.edn): 4 functions, 1 over 30, 1 from 10 to 30"
    assert len(lines) == 4
    assert lines[1].endswith("m.bad  must fix, over 30")
    assert lines[2].endswith("m.meh  over the goal of 10")
    assert lines[3].endswith("m.fine")


def test_the_bands_start_above_30_and_at_10(tmp_path):
    entries = [crap_entry("thirty", 30.0), crap_entry("ten", 10.0), crap_entry("nine", 9.9)]
    write(tmp_path, ".metrics/crap.edn", "{:entries [" + " ".join(entries) + "]}")

    lines = summary.crap_section(tmp_path, limit=3)

    assert lines[0].endswith("3 functions, 0 over 30, 2 from 10 to 30")
    assert [line.rsplit("m.", 1)[1] for line in lines[1:]] == ["thirty  over the goal of 10", "ten  over the goal of 10", "nine"]


def test_exactly_the_limit_needs_no_more_line(tmp_path):
    write(tmp_path, ".metrics/crap.edn", "{:entries [" + " ".join(crap_entry(f"f{i}", i) for i in range(2)) + "]}")

    assert len(summary.crap_section(tmp_path, limit=2)) == 3


def test_a_long_list_is_cut_at_the_limit(tmp_path):
    write(tmp_path, ".metrics/crap.edn", "{:entries [" + " ".join(crap_entry(f"f{i}", i) for i in range(5)) + "]}")

    lines = summary.crap_section(tmp_path, limit=2)

    assert len(lines) == 4
    assert lines[-1] == "  and 3 more"


def test_only_duplicate_pairs_at_or_above_the_review_line_are_listed(tmp_path):
    pair = '{{:score {score} :left {{:file "a.py" :start-line 1 :end-line 5}} :right {{:file "b.py" :start-line 7 :end-line 11}}}}'
    scores = (0.9, 0.82, 0.5)
    write(tmp_path, ".metrics/dry.edn", "{:candidates [" + "".join(pair.format(score=s) for s in scores) + "]}")

    lines = summary.dry_section(tmp_path, limit=1)

    assert lines == [
        "Duplicates (.metrics/dry.edn): 2 pairs at or above 0.82",
        "  0.90  a.py:1-5  and  b.py:7-11",
        "  and 1 more",
    ]


def test_a_surviving_mutant_is_named_by_file_line_function_and_change(tmp_path):
    write(tmp_path, "src/a.py", "x = 1\n\ndef f(age):\n    return age >= 18\n")
    offset = (tmp_path / "src/a.py").read_bytes().index(b">=")
    mutation = json.dumps(["src/a.py", "a", "defn/f", offset, offset + 2, ">=", ">"], separators=(",", ":"))
    escaped = mutation.replace("\\", "\\\\").replace('"', '\\"')
    killed = escaped.replace("defn/f", "defn/g")
    write(
        tmp_path,
        ".metrics/mutate/a.edn",
        f'{{:outcomes {{"{escaped}" :survived "{killed}" :killed}} :forms [{{:uncovered 2}} {{:id "defn/g"}}]}}',
    )

    lines = summary.mutate_section(tmp_path, limit=10)

    assert lines == ["Mutants (.metrics/mutate/): 1 survived, 2 sites no test reaches", "  src/a.py:4  f  >= -> >"]


def test_a_project_not_measured_yet_is_told_how_to_measure(tmp_path):
    text = summary.render(tmp_path, limit=10)

    assert text.count("Run .metrics/tools/run measure.") == 3
