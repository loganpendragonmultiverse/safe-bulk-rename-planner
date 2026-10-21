from __future__ import annotations

import json
import os
import re
import stat
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .review import save_journal
from .safety import (
    MAX_JSON,
    MAX_RECORDS,
    destination,
    hash_file,
    inside,
    no_links,
    portable_target,
    read_json,
    relative_name,
    typed_record,
)


@dataclass(frozen=True, slots=True)
class Rename:
    source: str
    target: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Plan:
    root: str
    pattern: str
    replacement: str
    recursive: bool
    renames: tuple[Rename, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "root": self.root,
            "pattern": self.pattern,
            "replacement": self.replacement,
            "recursive": self.recursive,
            "renames": [item.to_dict() for item in self.renames],
        }


def create_plan(
    root: Path,
    pattern: str,
    replacement: str,
    recursive: bool = False,
    exclude: tuple[str, ...] = (),
) -> Plan:
    if (
        type(recursive) is not bool
        or not isinstance(exclude, tuple)
        or any(not isinstance(name, str) for name in exclude)
    ):
        raise ValueError(
            "recursive must be boolean and exclude must be a tuple of relative names"
        )
    for name in exclude:
        relative_name(name)
    directory = no_links(root).resolve()
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    try:
        expression = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid match expression: {exc}") from exc
    files: list[Path] = []
    stack = [directory]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or getattr(metadata, "st_file_attributes", 0) & 0x400
                ):
                    continue
                path = Path(entry.path)
                if stat.S_ISDIR(metadata.st_mode):
                    if recursive:
                        stack.append(path)
                elif stat.S_ISREG(metadata.st_mode):
                    files.append(path)
                    if len(files) > MAX_RECORDS:
                        raise ValueError("Plan exceeds 10,000 candidate files")
                else:
                    raise ValueError("Only regular files can be planned")
    files.sort(key=lambda path: str(path.relative_to(directory)).casefold())
    renames: list[Rename] = []
    for source in files:
        if _relative(directory, source) in exclude:
            continue
        try:
            new_name = expression.sub(replacement, source.name)
        except (re.error, IndexError) as error:
            raise ValueError(f"Invalid replacement expression: {error}") from error
        if new_name == source.name:
            continue
        portable_target(new_name)
        target = source.with_name(new_name)
        size, digest = hash_file(source)
        renames.append(
            Rename(
                _relative(directory, source),
                _relative(directory, target),
                size,
                digest,
            )
        )
    _validate_collisions(directory, renames)
    return Plan(str(directory), pattern, replacement, recursive, tuple(renames))


def _validate_plan(plan: Plan) -> None:
    if (
        not isinstance(plan, Plan)
        or not isinstance(plan.root, str)
        or not Path(plan.root).is_absolute()
    ):
        raise ValueError("Manifest root must be an absolute local directory")
    if (
        type(plan.recursive) is not bool
        or not isinstance(plan.pattern, str)
        or not isinstance(plan.replacement, str)
    ):
        raise ValueError(
            "Manifest pattern/replacement/recursive fields have invalid types"
        )
    if not isinstance(plan.renames, tuple) or len(plan.renames) > MAX_RECORDS:
        raise ValueError("Manifest must contain at most 10,000 rename records")
    for item in plan.renames:
        if not isinstance(item, Rename):
            raise TypeError("Invalid rename record")
        typed_record(item.to_dict(), ("source", "target"))
        root = no_links(Path(plan.root)).resolve()
        inside(root, item.source)
        inside(root, item.target)
        portable_target(Path(item.target).name)
        if Path(item.source).parent != Path(item.target).parent:
            raise ValueError("Renames must preserve each file's original directory")
        if item.source == item.target:
            raise ValueError("Source and target must differ")


def write_manifest(plan: Plan, output: Path) -> None:
    _validate_plan(plan)
    content = json.dumps(plan.to_dict(), indent=2) + "\n"
    if len(content.encode("utf-8")) > MAX_JSON:
        raise ValueError("Rendered manifest exceeds 8 MiB")
    target = destination(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    no_links(target)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content)


def load_manifest(path: Path) -> Plan:
    payload = read_json(path)
    if (
        not isinstance(payload, dict)
        or type(payload.get("schema_version")) is not int
        or payload["schema_version"] != 1
        or not isinstance(payload.get("renames"), list)
    ):
        raise ValueError("Unsupported or invalid rename manifest")
    if len(payload["renames"]) > MAX_RECORDS:
        raise ValueError("Manifest exceeds 10,000 records")
    for item in payload["renames"]:
        typed_record(item, ("source", "target"))
    if not isinstance(payload.get("root"), str):
        raise TypeError("Manifest root must be an absolute local directory")
    plan = Plan(
        payload["root"],
        payload.get("pattern", ""),
        payload.get("replacement", ""),
        payload.get("recursive", False),
        tuple(
            Rename(item["source"], item["target"], item["size"], item["sha256"])
            for item in payload["renames"]
        ),
    )
    _validate_plan(plan)
    return plan


def apply_plan(plan: Plan, journal: Path | None = None) -> None:
    _execute(plan, undo=False, journal=journal)


def undo_plan(plan: Plan, journal: Path | None = None) -> None:
    _execute(plan, undo=True, journal=journal)


def _execute(plan: Plan, undo: bool, journal: Path | None = None) -> None:
    _validate_plan(plan)
    _reject_symlinks(Path(plan.root).absolute())
    root = Path(plan.root).resolve()
    if not root.is_dir():
        raise ValueError(f"Manifest root is not a directory: {root}")
    operations = [
        (item.target, item.source, item) if undo else (item.source, item.target, item)
        for item in plan.renames
    ]
    _validate_collisions(
        root, [Rename(a, b, item.size, item.sha256) for a, b, item in operations]
    )
    occupied_sources = {
        unicodedata.normalize("NFC", source).casefold() for source, _, _ in operations
    }
    for source_name, target_name, item in operations:
        source = _inside(root, source_name)
        target = _inside(root, target_name)
        if source.parent != target.parent:
            raise ValueError("Renames must preserve each file's original directory")
        if not source.is_file() or source.is_symlink():
            raise ValueError(
                f"Expected source file is missing or unsafe: {source_name}"
            )
        if hash_file(source) != (item.size, item.sha256):
            raise ValueError(f"File changed since the plan was created: {source_name}")
        if (target.exists() or target.is_symlink()) and unicodedata.normalize(
            "NFC", target_name
        ).casefold() not in occupied_sources:
            raise ValueError(f"Target already exists: {target_name}")

    journal_data: dict[str, Any] = {
        "tool": "safe-bulk-rename-planner",
        "schema_version": 1,
        "root": str(root),
        "status": "prepared",
        "undo": undo,
        "operations": [
            {
                "source": source,
                "target": target,
                "temporary": str(
                    Path(source).with_name(f".rename-planner-{uuid.uuid4().hex}.tmp")
                ),
                "size": item.size,
                "sha256": item.sha256,
                "phase": "pending",
            }
            for source, target, item in operations
        ],
    }
    if len(json.dumps(journal_data, indent=2).encode("utf-8")) > MAX_JSON:
        raise ValueError("Journal exceeds 8 MiB")
    if journal:
        journal = destination(journal)
        if journal.resolve() in {
            _inside(root, n) for a, b, _ in operations for n in (a, b)
        }:
            raise ValueError("journal must not replace any source or target")
        save_journal(journal, journal_data, initial=True)
    staged: list[tuple[Path, Path, Path]] = []
    try:
        for index, (source_name, target_name, _) in enumerate(operations):
            source = _inside(root, source_name)
            target = _inside(root, target_name)
            temporary = _inside(root, journal_data["operations"][index]["temporary"])
            if temporary.exists() or temporary.is_symlink():
                raise ValueError("Temporary staging path already exists")
            if hash_file(source) != (
                operations[index][2].size,
                operations[index][2].sha256,
            ):
                raise ValueError("Source changed before staging")
            os.replace(source, temporary)
            staged.append((temporary, target, source))
            journal_data["operations"][index]["phase"] = "staged"
            if journal:
                save_journal(journal, journal_data)
        for index, (temporary, target, _) in enumerate(staged):
            if target.exists() or target.is_symlink():
                raise ValueError(f"Target appeared during staging: {target.name}")
            expected = operations[index][2]
            if hash_file(temporary) != (expected.size, expected.sha256):
                raise ValueError("Staged file changed before commit")
            os.replace(temporary, target)
            journal_data["operations"][index]["phase"] = "committed"
            if journal:
                save_journal(journal, journal_data)
        journal_data["status"] = "complete"
        if journal:
            save_journal(journal, journal_data)
    except (OSError, ValueError):
        # Clear every successfully committed target back to its recorded temporary
        # before restoring originals, so a cycle cannot occupy another original.
        rollback_complete = True
        for index, (temporary, target, original) in reversed(list(enumerate(staged))):
            item = operations[index][2]
            try:
                if not temporary.exists() and target.exists():
                    if hash_file(target) != (item.size, item.sha256):
                        rollback_complete = False
                        continue
                    os.replace(target, temporary)
            except (OSError, ValueError):
                rollback_complete = False
        for index, (temporary, target, original) in reversed(list(enumerate(staged))):
            item = operations[index][2]
            try:
                if (
                    temporary.exists()
                    and not original.exists()
                    and not original.is_symlink()
                ):
                    if hash_file(temporary) != (item.size, item.sha256):
                        rollback_complete = False
                        continue
                    os.replace(temporary, original)
                if not original.exists() or hash_file(original) != (
                    item.size,
                    item.sha256,
                ):
                    rollback_complete = False
                else:
                    journal_data["operations"][index]["phase"] = "rolled-back"
            except (OSError, ValueError):
                rollback_complete = False
        journal_data["status"] = "rolled-back" if rollback_complete else "interrupted"
        if journal:
            try:
                save_journal(journal, journal_data)
            except (OSError, ValueError):
                pass  # Original I/O error remains primary; inspection uses hashes.
        raise


def _validate_collisions(root: Path, renames: list[Rename]) -> None:
    source_keys = {
        unicodedata.normalize("NFC", item.source).casefold() for item in renames
    }
    if len(source_keys) != len(renames):
        raise ValueError("Source names collide under Unicode NFC and case folding")
    target_keys: set[str] = set()
    for item in renames:
        key = unicodedata.normalize("NFC", item.target).casefold()
        if key in target_keys:
            raise ValueError(f"Multiple files would be renamed to {item.target}")
        target_keys.add(key)
        target = _inside(root, item.target)
        for existing in target.parent.iterdir():
            existing_key = unicodedata.normalize(
                "NFC", _relative(root, existing)
            ).casefold()
            if existing_key == key and key not in source_keys:
                raise ValueError(
                    f"Target already exists (Unicode/case collision): {item.target}"
                )
        if target.exists() and key not in source_keys:
            raise ValueError(f"Target already exists: {item.target}")


def _reject_symlinks(path: Path) -> None:
    no_links(path)


def _inside(root: Path, relative: str) -> Path:
    return inside(root, relative)


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    return hash_file(path)[1]
