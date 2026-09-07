import json
from pathlib import Path

import pytest

import rename_planner.planner as planner
from rename_planner.cli import main
from rename_planner.review import inspect_journal, render_html


def test_journal_interruption_is_inspectable_without_mutating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "a file.txt"
    source.write_text("content", encoding="utf-8")
    plan = planner.create_plan(tmp_path, " ", "-")
    journal = tmp_path / "journal.json"
    replace = planner.os.replace

    def interrupted(src, dst):
        replace(src, dst)
        if Path(src) == source:
            raise KeyboardInterrupt("simulate abrupt process stop after first move")

    monkeypatch.setattr(planner.os, "replace", interrupted)
    with pytest.raises(KeyboardInterrupt):
        planner.apply_plan(plan, journal)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    inspection = inspect_journal(journal)
    locations = inspection["operations"][0]["locations"]
    assert next(v for v in locations if v["location"] == "temporary")[
        "matches_expected_hash"
    ]
    assert not inspection["operations"][0]["review_required"]
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_selected_manifest_apply_undo_and_visual(tmp_path: Path) -> None:
    (tmp_path / "a file.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b file.txt").write_text("b", encoding="utf-8")
    manifest, html = tmp_path / "plan.json", tmp_path / "review.html"
    assert (
        main(
            [
                str(tmp_path),
                "--match",
                " ",
                "--replace",
                "-",
                "--exclude",
                "b file.txt",
                "--output",
                str(manifest),
                "--html",
                str(html),
            ]
        )
        == 0
    )
    assert "Download selected manifest" in html.read_text(encoding="utf-8")
    assert len(planner.load_manifest(manifest).renames) == 1
    assert main(["--apply-manifest", str(manifest)]) == 0
    assert (tmp_path / "a-file.txt").read_text(encoding="utf-8") == "a"
    assert (tmp_path / "b file.txt").is_file()
    assert main(["--inspect-recovery", str(manifest) + ".journal.json"]) == 0
    assert main(["--undo", str(manifest)]) == 0
    assert (tmp_path / "a file.txt").is_file()
    assert "Unicode NFC" in render_html(planner.load_manifest(manifest).to_dict())


def test_unicode_collisions_and_journal_escape(tmp_path: Path) -> None:
    (tmp_path / "e\u0301.txt").write_text("one", encoding="utf-8")
    (tmp_path / "source.txt").write_text("two", encoding="utf-8")
    with pytest.raises(ValueError, match="collision"):
        planner.create_plan(tmp_path, "source", "é")
    journal = tmp_path / "bad.json"
    journal.write_text(
        json.dumps(
            {
                "tool": "safe-bulk-rename-planner",
                "root": str(tmp_path),
                "operations": [
                    {"source": "../outside", "target": "x", "temporary": "y"}
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="leaves"):
        inspect_journal(journal)
