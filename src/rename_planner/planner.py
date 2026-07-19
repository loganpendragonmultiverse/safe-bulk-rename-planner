from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


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
        return {"schema_version": 1, "root": self.root, "pattern": self.pattern, "replacement": self.replacement, "recursive": self.recursive, "renames": [item.to_dict() for item in self.renames]}


def create_plan(root: Path, pattern: str, replacement: str, recursive: bool = False) -> Plan:
    directory = root.expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    try:
        expression = re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid match expression: {exc}") from exc
    candidates = directory.rglob("*") if recursive else directory.iterdir()
    files = sorted((path for path in candidates if path.is_file() and not path.is_symlink()), key=lambda path: str(path.relative_to(directory)).casefold())
    renames: list[Rename] = []
    for source in files:
        new_name = expression.sub(replacement, source.name)
        if new_name == source.name:
            continue
        if not new_name or new_name in {".", ".."} or Path(new_name).name != new_name or "/" in new_name or "\\" in new_name:
            raise ValueError(f"Replacement creates an unsafe filename for {source.name!r}: {new_name!r}")
        target = source.with_name(new_name)
        renames.append(Rename(_relative(directory, source), _relative(directory, target), source.stat().st_size, _sha256(source)))
    _validate_collisions(directory, renames)
    return Plan(str(directory), pattern, replacement, recursive, tuple(renames))


def write_manifest(plan: Plan, output: Path) -> None:
    destination = output.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> Plan:
    source = path.expanduser().resolve()
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("renames"), list):
        raise ValueError("Unsupported or invalid rename manifest")
    renames = tuple(Rename(str(item["source"]), str(item["target"]), int(item["size"]), str(item["sha256"])) for item in payload["renames"])
    return Plan(str(payload["root"]), str(payload.get("pattern", "")), str(payload.get("replacement", "")), bool(payload.get("recursive")), renames)


def apply_plan(plan: Plan) -> None:
    _execute(plan, undo=False)


def undo_plan(plan: Plan) -> None:
    _execute(plan, undo=True)


def _execute(plan: Plan, undo: bool) -> None:
    root = Path(plan.root).resolve()
    if not root.is_dir():
        raise ValueError(f"Manifest root is not a directory: {root}")
    operations = [(item.target, item.source, item) if undo else (item.source, item.target, item) for item in plan.renames]
    occupied_sources = {source.casefold() for source, _, _ in operations}
    for source_name, target_name, item in operations:
        source = _inside(root, source_name)
        target = _inside(root, target_name)
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Expected source file is missing or unsafe: {source_name}")
        if source.stat().st_size != item.size or _sha256(source) != item.sha256:
            raise ValueError(f"File changed since the plan was created: {source_name}")
        if target.exists() and target_name.casefold() not in occupied_sources:
            raise ValueError(f"Target already exists: {target_name}")

    staged: list[tuple[Path, Path, Path]] = []
    try:
        for index, (source_name, target_name, _) in enumerate(operations):
            source = _inside(root, source_name)
            target = _inside(root, target_name)
            temporary = source.with_name(f".rename-planner-{uuid.uuid4().hex}-{index}.tmp")
            os.replace(source, temporary)
            staged.append((temporary, target, source))
        for temporary, target, _ in staged:
            os.replace(temporary, target)
    except OSError:
        for temporary, target, original in reversed(staged):
            current = temporary if temporary.exists() else target
            if current.exists() and not original.exists():
                os.replace(current, original)
        raise


def _validate_collisions(root: Path, renames: list[Rename]) -> None:
    source_keys = {item.source.casefold() for item in renames}
    target_keys: set[str] = set()
    for item in renames:
        key = item.target.casefold()
        if key in target_keys:
            raise ValueError(f"Multiple files would be renamed to {item.target}")
        target_keys.add(key)
        target = _inside(root, item.target)
        if target.exists() and key not in source_keys:
            raise ValueError(f"Target already exists: {item.target}")


def _inside(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Manifest path leaves its root: {relative}")
    return target


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
