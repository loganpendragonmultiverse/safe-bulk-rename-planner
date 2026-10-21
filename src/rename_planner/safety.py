"""Lexical path and typed local evidence checks shared by plans and journals."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

MAX_RECORDS = 10000
MAX_JSON = 8 * 1024 * 1024


def no_links(path: Path) -> Path:
    path = path.expanduser().absolute()
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(
                "Paths must not use a symlink, junction or reparse ancestor"
            )
    return path


def relative_name(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or "\x00" in value
    ):
        raise ValueError(
            "Manifest path leaves its root or is not a portable relative name"
        )
    if value.startswith("/") or any(
        part in {"", ".", ".."} for part in value.split("/")
    ):
        raise ValueError("Manifest path leaves its root")
    return value


def inside(root: Path, relative: Any) -> Path:
    lexical = no_links(root / relative_name(relative))
    target = lexical.resolve()
    if root not in target.parents:
        raise ValueError("Manifest path leaves its root")
    # Resolution proves containment, but on Windows it may adopt the spelling
    # of an existing case-insensitive match. Keep the requested rename spelling.
    return lexical


def portable_target(name: str) -> None:
    stem = name.split(".", 1)[0].upper()
    if (
        not name
        or name in {".", ".."}
        or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name)
        or name.endswith((".", " "))
        or stem
        in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
            *(f"COM{i}" for i in "¹²³"),
            *(f"LPT{i}" for i in "¹²³"),
        }
    ):
        raise ValueError(f"Replacement creates an unsafe filename: {name!r}")


def typed_record(item: Any, paths: tuple[str, ...]) -> None:
    if not isinstance(item, dict):
        raise TypeError("Rename records must be objects")
    for key in paths:
        relative_name(item.get(key))
    if type(item.get("size")) is not int or item["size"] < 0:
        raise ValueError("Recorded size must be a nonnegative integer")
    if not isinstance(item.get("sha256"), str) or not re.fullmatch(
        "[0-9a-f]{64}", item["sha256"]
    ):
        raise ValueError(
            "Recorded SHA-256 must contain 64 lowercase hexadecimal digits"
        )


def hash_file(path: Path) -> tuple[int, str]:
    path = no_links(path)
    initial = path.stat()
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError("Expected a regular source file")
    digest = hashlib.sha256()
    count = 0
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != (
            initial.st_dev,
            initial.st_ino,
        ):
            raise ValueError("File changed before hashing")
        while True:
            block = handle.read(min(1024 * 1024, initial.st_size - count + 1))
            if not block:
                break
            count += len(block)
            if count > initial.st_size:
                raise ValueError("File grew during hashing")
            digest.update(block)
        after = os.fstat(handle.fileno())
    current = path.stat()

    def identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )

    if (
        identity(before) != identity(after)
        or identity(initial) != identity(current)
        or count != initial.st_size
        or count != after.st_size
    ):
        raise ValueError("File changed during hashing")
    return count, digest.hexdigest()


def read_json(path: Path) -> Any:
    path = no_links(path)
    if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > MAX_JSON:
        raise ValueError("JSON input must be a regular file of at most 8 MiB")
    initial = path.stat()
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or (metadata.st_dev, metadata.st_ino) != (
            initial.st_dev,
            initial.st_ino,
        ):
            raise ValueError("JSON input changed before regular-file admission")
        raw = handle.read(MAX_JSON + 1)
    if len(raw) > MAX_JSON:
        raise ValueError("JSON input exceeds 8 MiB")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def constant(value: str) -> Any:
        raise ValueError(f"Non-finite JSON value: {value}")

    try:
        return json.loads(
            raw.decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=constant
        )
    except RecursionError as error:
        raise ValueError("JSON nesting exceeds supported limit") from error


def destination(path: Path) -> Path:
    target = no_links(path).resolve()
    if target.exists() or target.is_symlink():
        raise ValueError("Output already exists")
    return target
