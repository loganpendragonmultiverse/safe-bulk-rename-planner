"""Real links and native case changes; installed Windows acceptance requires no skips."""

import hashlib
import subprocess
import sys

import pytest

from rename_planner import planner


@pytest.mark.parametrize("link_kind", ["symlink", "junction"])
@pytest.mark.parametrize("position", ["root", "ancestor", "imported", "journal"])
def test_real_unsafe_path_refusal(tmp_path, link_kind, position):
    if link_kind == "junction" and sys.platform != "win32":
        pytest.skip("actual Windows junction fixture")
    root = tmp_path / "tree"
    root.mkdir()
    source = root / "a file.txt"
    source.write_bytes(b"original")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "child").mkdir()
    external = outside / "a file.txt"
    external.write_bytes(b"outside")
    plan = planner.create_plan(root, " ", "-")
    link = root / "alias" if position == "imported" else tmp_path / "link"
    destination = root if position == "root" else outside
    if link_kind == "junction":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(destination)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert link.lstat().st_file_attributes & 0x400
    else:
        try:
            link.symlink_to(destination, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"actual symlink capability unavailable: {error}")
    journal = tmp_path / "journal.json"
    with pytest.raises(ValueError, match="symlink|reparse"):
        if position == "root":
            planner.create_plan(link, " ", "-")
        elif position == "ancestor":
            planner.create_plan(link / "child", " ", "-")
        elif position == "journal":
            planner.apply_plan(plan, link / "journal.json")
        else:
            imported = planner.Plan(
                str(root),
                "",
                "",
                False,
                (
                    planner.Rename(
                        "alias/a file.txt",
                        "alias/a-file.txt",
                        7,
                        hashlib.sha256(b"outside").hexdigest(),
                    ),
                ),
            )
            planner.apply_plan(imported, journal)
    assert source.read_bytes() == b"original" and external.read_bytes() == b"outside"
    assert not journal.exists() and not (outside / "journal.json").exists()


def test_case_only_apply_and_undo_preserve_bytes(tmp_path):
    source = tmp_path / "name.txt"
    source.write_bytes(b"source")
    plan = planner.create_plan(tmp_path, "name", "NAME")
    planner.apply_plan(plan, tmp_path / "apply.json")
    assert (tmp_path / "NAME.txt").read_bytes() == b"source"
    assert "NAME.txt" in [p.name for p in tmp_path.iterdir()]
    planner.undo_plan(plan, tmp_path / "undo.json")
    assert source.read_bytes() == b"source"
    assert "name.txt" in [p.name for p in tmp_path.iterdir()]


def test_unicode_normalization_collision_is_rejected(tmp_path):
    existing = tmp_path / "e\u0301.txt"
    existing.write_bytes(b"untouched")
    source = tmp_path / "other.txt"
    source.write_bytes(b"source")
    with pytest.raises(ValueError, match="collision"):
        planner.create_plan(tmp_path, "other", "é")
    assert existing.read_bytes() == b"untouched" and source.read_bytes() == b"source"
