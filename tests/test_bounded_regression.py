import json

import pytest

from rename_planner.cli import main
from rename_planner.planner import create_plan


@pytest.mark.parametrize("ancestor", [False, True])
def test_imported_symlink_is_rejected_without_any_write(tmp_path, capsys, ancestor):
    root = tmp_path / "tree"
    root.mkdir()
    real = root / "real"
    real.mkdir()
    (real / "a file.txt").write_text("synthetic")
    plan = create_plan(real, " ", "-").to_dict()
    plan["root"] = str(root)
    link = root / "alias"
    try:
        link.symlink_to(
            real if ancestor else real / "a file.txt", target_is_directory=ancestor
        )
    except OSError:
        pytest.skip("symlink creation is unavailable")
    plan["renames"][0]["source"] = "alias/a file.txt" if ancestor else "alias"
    plan["renames"][0]["target"] = "alias/a-file.txt" if ancestor else "real/a-file.txt"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(plan))
    before = {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }
    journal = tmp_path / "journal.json"
    assert main(["--apply-manifest", str(manifest), "--journal", str(journal)]) == 2
    assert "symlink" in capsys.readouterr().err.lower()
    assert not journal.exists()
    assert link.is_symlink()
    assert before == {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }
