from pathlib import Path

from rename_planner.planner import apply_plan, create_plan, load_manifest, undo_plan, write_manifest


def test_preview_does_not_rename_files(tmp_path: Path) -> None:
    (tmp_path / "Final Copy.txt").write_text("hello", encoding="utf-8")
    plan = create_plan(tmp_path, r"\s+", "-")
    assert plan.renames[0].target == "Final-Copy.txt"
    assert (tmp_path / "Final Copy.txt").exists()


def test_apply_and_undo_verify_content(tmp_path: Path) -> None:
    original = tmp_path / "chapter 01.txt"
    original.write_text("chapter", encoding="utf-8")
    plan = create_plan(tmp_path, r"\s+", "-")
    manifest = tmp_path / "plan.json"
    write_manifest(plan, manifest)
    loaded = load_manifest(manifest)
    apply_plan(loaded)
    assert (tmp_path / "chapter-01.txt").read_text(encoding="utf-8") == "chapter"
    undo_plan(loaded)
    assert original.read_text(encoding="utf-8") == "chapter"


def test_collision_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "one copy.txt").write_text("one", encoding="utf-8")
    (tmp_path / "one-copy.txt").write_text("existing", encoding="utf-8")
    try:
        create_plan(tmp_path, r"\s+", "-")
    except ValueError as exc:
        assert "Target already exists" in str(exc)
    else:
        raise AssertionError("Expected collision detection")


def test_changed_file_cannot_be_applied(tmp_path: Path) -> None:
    source = tmp_path / "draft 1.txt"
    source.write_text("first", encoding="utf-8")
    plan = create_plan(tmp_path, r"\s+", "-")
    source.write_text("changed", encoding="utf-8")
    try:
        apply_plan(plan)
    except ValueError as exc:
        assert "changed since" in str(exc)
    else:
        raise AssertionError("Expected hash verification")


def test_unsafe_filename_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "draft.txt").write_text("first", encoding="utf-8")
    try:
        create_plan(tmp_path, r"draft", "../escape")
    except ValueError as exc:
        assert "unsafe filename" in str(exc)
    else:
        raise AssertionError("Expected unsafe replacement validation")
