import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rename_planner import planner, safety
from rename_planner.cli import main
from rename_planner.review import inspect_journal


def cycle(root):
    root.mkdir()
    (root / "a").write_bytes(b"A")
    (root / "b").write_bytes(b"B")
    return planner.Plan(
        str(root),
        "",
        "",
        False,
        tuple(
            planner.Rename(a, b, 1, hashlib.sha256(value).hexdigest())
            for a, b, value in [("a", "b", b"A"), ("b", "a", b"B")]
        ),
    )


def test_cycles_and_undo_preserve_exact_bytes(tmp_path):
    plan = cycle(tmp_path / "tree")
    planner.apply_plan(plan, tmp_path / "apply.json")
    assert (Path(plan.root) / "a").read_bytes() == b"B"
    assert (Path(plan.root) / "b").read_bytes() == b"A"
    planner.undo_plan(plan, tmp_path / "undo.json")
    assert (Path(plan.root) / "a").read_bytes() == b"A"
    assert (Path(plan.root) / "b").read_bytes() == b"B"


def test_partial_cycle_commit_rolls_back_in_two_phases(tmp_path, monkeypatch):
    plan = cycle(tmp_path / "tree")
    original = planner.os.replace
    failed = False

    def replace(source, target):
        nonlocal failed
        if (
            not failed
            and Path(source).name.startswith(".rename-planner-")
            and Path(target).name == "a"
        ):
            failed = True
            raise OSError("synthetic second final move failure")
        return original(source, target)

    monkeypatch.setattr(planner.os, "replace", replace)
    journal = tmp_path / "journal.json"
    with pytest.raises(OSError, match="synthetic"):
        planner.apply_plan(plan, journal)
    assert failed
    assert {file.name: file.read_bytes() for file in Path(plan.root).iterdir()} == {
        "a": b"A",
        "b": b"B",
    }
    assert json.loads(journal.read_text())["status"] == "rolled-back"
    assert inspect_journal(journal)["recorded_status"] == "rolled-back"


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("recursive", "false"),
        ("root", None),
        ("renames", {}),
        ("renames", [{}]),
    ],
)
def test_manifest_types_fail_before_any_write(tmp_path, field, value):
    source = tmp_path / "a file.txt"
    source.write_bytes(b"a")
    data = planner.create_plan(tmp_path, " ", "-").to_dict()
    data[field] = value
    manifest = tmp_path / "plan.json"
    manifest.write_text(json.dumps(data))
    journal = tmp_path / "journal.json"
    assert main(["--apply-manifest", str(manifest), "--journal", str(journal)]) == 2
    assert source.read_bytes() == b"a" and not journal.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", "../outside"),
        ("target", "/outside"),
        ("target", "a:b"),
        ("size", True),
        ("size", -1),
        ("sha256", "x"),
        ("sha256", 1),
    ],
)
def test_manifest_records_are_typed_and_relative(tmp_path, field, value):
    (tmp_path / "a file.txt").write_bytes(b"a")
    data = planner.create_plan(tmp_path, " ", "-").to_dict()
    data["renames"][0][field] = value
    manifest = tmp_path / "plan.json"
    manifest.write_text(json.dumps(data))
    with pytest.raises((TypeError, ValueError)):
        planner.load_manifest(manifest)
    assert (tmp_path / "a file.txt").read_bytes() == b"a"


@pytest.mark.parametrize(
    "name",
    [
        "CON",
        "NUL.txt",
        "COM1.log",
        "LPT9",
        "x:",
        "name.",
        "name ",
        "a?b",
        "x\n",
        "COM¹.txt",
        "COM²",
        "COM³.log",
        "LPT¹.txt",
        "LPT²",
        "LPT³.log",
    ],
)
def test_portable_destinations_are_not_windows_aliases(tmp_path, name):
    (tmp_path / "a").write_bytes(b"a")
    with pytest.raises(ValueError, match="unsafe filename"):
        planner.create_plan(tmp_path, "a", name)
    assert (tmp_path / "a").read_bytes() == b"a"


def test_replacement_group_error_is_actionable(tmp_path, capsys):
    (tmp_path / "a").write_bytes(b"a")
    assert main([str(tmp_path), "--match", "a", "--replace", r"\g<missing>"]) == 2
    assert "replacement" in capsys.readouterr().err


def test_dangling_manifest_and_html_are_preserved(tmp_path):
    source = tmp_path / "a file.txt"
    source.write_bytes(b"a")
    missing = tmp_path / "missing"
    link = tmp_path / "output"
    try:
        link.symlink_to(missing)
    except OSError:
        pytest.skip("actual symlink capability unavailable")
    plan = planner.create_plan(tmp_path, " ", "-")
    with pytest.raises(ValueError, match="symlink"):
        planner.write_manifest(plan, link)
    assert (
        main([str(tmp_path), "--match", " ", "--replace", "-", "--html", str(link)])
        == 2
    )
    assert link.is_symlink() and not missing.exists() and source.exists()


def test_existing_journal_preflight_does_not_create_manifest(tmp_path):
    (tmp_path / "a file.txt").write_bytes(b"a")
    journal = tmp_path / "journal.json"
    journal.write_bytes(b"existing")
    manifest = tmp_path / "plan.json"
    assert (
        main(
            [
                str(tmp_path),
                "--match",
                " ",
                "--replace",
                "-",
                "--apply",
                "--output",
                str(manifest),
                "--journal",
                str(journal),
            ]
        )
        == 2
    )
    assert not manifest.exists() and journal.read_bytes() == b"existing"


def test_temporary_collision_is_not_replaced(tmp_path, monkeypatch):
    source = tmp_path / "a file.txt"
    source.write_bytes(b"a")
    plan = planner.create_plan(tmp_path, " ", "-")
    temporary = tmp_path / ".rename-planner-fixed.tmp"
    temporary.write_bytes(b"unrelated")
    monkeypatch.setattr(planner.uuid, "uuid4", lambda: SimpleNamespace(hex="fixed"))
    with pytest.raises(ValueError, match="Temporary"):
        planner.apply_plan(plan)
    assert source.read_bytes() == b"a" and temporary.read_bytes() == b"unrelated"


def test_changed_stage_never_commits_wrong_content(tmp_path, monkeypatch):
    source = tmp_path / "a file.txt"
    source.write_bytes(b"a")
    plan = planner.create_plan(tmp_path, " ", "-")
    original = planner.os.replace

    def replace(a, b):
        result = original(a, b)
        if Path(a) == source:
            Path(b).write_bytes(b"changed")
        return result

    monkeypatch.setattr(planner.os, "replace", replace)
    journal = tmp_path / "journal.json"
    with pytest.raises(ValueError, match="Staged"):
        planner.apply_plan(plan, journal)
    assert not (tmp_path / "a-file.txt").exists()
    assert json.loads(journal.read_text())["status"] == "interrupted"
    assert inspect_journal(journal)["operations"][0]["review_required"]
    assert next(tmp_path.glob(".rename-planner-*.tmp")).read_bytes() == b"changed"


def test_stat_api_ctime_difference_is_not_a_change(tmp_path, monkeypatch):
    file = tmp_path / "file"
    file.write_bytes(b"unchanged")
    original = safety.os.fstat

    def fstat(fd):
        value = original(fd)
        return SimpleNamespace(
            st_mode=value.st_mode,
            st_dev=value.st_dev,
            st_ino=value.st_ino,
            st_size=value.st_size,
            st_mtime_ns=value.st_mtime_ns,
            st_ctime_ns=value.st_ctime_ns + 1,
        )

    monkeypatch.setattr(safety.os, "fstat", fstat)
    assert safety.hash_file(file) == (9, hashlib.sha256(b"unchanged").hexdigest())


@pytest.mark.parametrize(
    "field,value", [("schema_version", True), ("undo", 1), ("status", "unknown")]
)
def test_journal_top_level_types(tmp_path, field, value):
    plan = cycle(tmp_path / "tree")
    journal = tmp_path / "journal.json"
    planner.apply_plan(plan, journal)
    data = json.loads(journal.read_text())
    data[field] = value
    journal.write_text(json.dumps(data))
    before = {p.name: p.read_bytes() for p in Path(plan.root).iterdir()}
    with pytest.raises(ValueError):
        inspect_journal(journal)
    assert before == {p.name: p.read_bytes() for p in Path(plan.root).iterdir()}


@pytest.mark.parametrize(
    "field,value",
    [("phase", "invalid"), ("size", False), ("sha256", "bad"), ("temporary", "a")],
)
def test_journal_record_types_and_overlap(tmp_path, field, value):
    plan = cycle(tmp_path / "tree")
    journal = tmp_path / "journal.json"
    planner.apply_plan(plan, journal)
    data = json.loads(journal.read_text())
    data["operations"][0][field] = value
    journal.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        inspect_journal(journal)


def test_strict_json_rejects_duplicate_keys_and_nonobject(tmp_path):
    file = tmp_path / "input.json"
    for content in [
        "[]",
        '{"schema_version":1,"schema_version":1}',
        '{"schema_version":NaN}',
    ]:
        file.write_text(content)
        with pytest.raises(ValueError):
            planner.load_manifest(file)


@pytest.mark.parametrize("initial", [True, False])
def test_actual_pretty_journal_limit_precedes_create_or_replace(
    tmp_path, monkeypatch, initial
):
    from rename_planner import review

    payload = {"nested": [{"name": "x" * 20} for _ in range(3)]}
    compact = len(json.dumps(payload).encode())
    pretty = len(json.dumps(payload, indent=2).encode())
    assert pretty > compact
    monkeypatch.setattr(review, "MAX_JSON", (compact + pretty) // 2)
    journal = tmp_path / "journal.json"
    if not initial:
        journal.write_bytes(b"existing journal")
    before = {file.name: file.read_bytes() for file in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="Serialized journal"):
        review.save_journal(journal, payload, initial=initial)
    assert before == {file.name: file.read_bytes() for file in tmp_path.iterdir()}


def test_initial_journal_limit_does_not_rename_sources(tmp_path, monkeypatch):
    from rename_planner import review

    source = tmp_path / "a file.txt"
    source.write_bytes(b"source")
    plan = planner.create_plan(tmp_path, " ", "-")
    monkeypatch.setattr(review, "MAX_JSON", 1)
    journal = tmp_path / "journal.json"
    with pytest.raises(ValueError, match="Serialized journal"):
        planner.apply_plan(plan, journal)
    assert source.read_bytes() == b"source"
    assert not journal.exists() and not (tmp_path / "a-file.txt").exists()


def test_containment_resolution_preserves_requested_target_spelling(
    tmp_path, monkeypatch
):
    from rename_planner.safety import inside

    (tmp_path / "name.txt").write_bytes(b"source")
    original = type(tmp_path).resolve

    def canonical_existing_spelling(path, *args, **kwargs):
        if path.parent == tmp_path and path.name == "NAME.txt":
            return tmp_path / "name.txt"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(type(tmp_path), "resolve", canonical_existing_spelling)
    target = inside(tmp_path, "NAME.txt")
    assert target.name == "NAME.txt"
    assert target.parent == tmp_path
