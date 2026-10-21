# Safe Bulk Rename Planner

Safe Bulk Rename Planner previews regular-expression filename changes, rejects collisions and unsafe destinations, and can produce a hash-bound JSON manifest before anything moves. Applying a reviewed plan uses two-phase renames, and the same manifest can undo the operation while the files still match their recorded content.

## Install

Python 3.10 or newer is required.

```bash
python -m venv .venv
python -m pip install -e .
```

## Three-minute use

Preview spaces changing to dashes:

```bash
rename-plan "C:\Downloads\Review" --match "\s+" --replace "-"
```

Save and apply the reviewed plan:

```bash
rename-plan "C:\Downloads\Review" --match "\s+" --replace "-" --output rename-manifest.json --apply
rename-plan --undo rename-manifest.json
```

Preview is the default. `--apply` is refused without an output manifest. The planner handles files only, ignores symbolic links, keeps each rename in its original directory, and supports `--recursive` when explicitly requested.

## Safety and limitations

- Existing targets, duplicate destinations, path separators, and traversal attempts are rejected before any rename.
- File size and SHA-256 must still match before apply or undo.
- The manifest records filenames and hashes; treat it as local operational data when names are sensitive.
- The tool does not rename directories, edit file contents, transliterate text, or guess naming rules.
- An operating-system or hardware failure during a rename can still require recovery from backup.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m build
```

## Project status

**Focused release scope:** preview, reviewed apply/undo and read-only interruption inspection. Focused contributions that preserve preview-first behavior and reversibility are welcome.

Released under the [MIT License](LICENSE). Contributions follow the [organization guidelines](https://github.com/loganpendragonmultiverse/.github/blob/main/CONTRIBUTING.md).

## More open-source projects

This project is part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Browse the catalog for other released tools, source repositories, live demos, and downloads.

## Version 1.1.0: reviewed improvements

Repair formatting and add visual per-file selection, Unicode/case collision review, interruption journals and read-only recovery inspection.

```bash
rename-plan ./files --match ' ' --replace '-' --output plan.json --html review.html
```

--exclude omits an exact relative source name. The local HTML review can uncheck files and download a selected manifest; --apply-manifest applies that reviewed input only after fresh collision and content-hash checks. Unicode NFC/case-fold collisions are rejected and original directories are preserved. CLI apply/undo creates a new journal beside the manifest, or uses --journal with a new path. The journal records every planned temporary path before changes and advances after staging/commit. --inspect-recovery JOURNAL compares current source/temporary/target hashes without moving anything, including a crash between a move and its journal update. Interrupted recovery remains an explicit human-reviewed operation. Existing manifests/reports/journals are protected.

## 1.1.1 — 2026-10-16

Imported manifest paths are inspected in their lexical spelling before resolution. A symlink at a source, destination, root or ancestor is rejected before any rename or journal write. Containment, original-directory, Unicode/case collision, size and SHA-256 checks still apply. Normal apply/undo and read-only interruption inspection remain available. Use disposable trees for tests. Concurrent filesystem replacement remains outside the guarantee; this check does not make renames atomic or provide automatic recovery.

## 1.1.2 — typed evidence and interruption handling

Manifests and journals validate typed integer versions, booleans, nonnegative sizes, lowercase SHA-256, portable relative paths and bounded record counts before file operations. JSON inputs and generated manifests/journals are limited to 8 MiB; plans observe at most 10,000 regular candidate files. Duplicate JSON keys and non-finite constant tokens are rejected. Files are hashed in streaming blocks, and descriptor/path metadata must remain stable within each API. Windows path/descriptor creation-time representations are not incorrectly compared to each other.

Preview skips symbolic links and Windows junction/reparse entries before traversing them. Selected roots, imported source/target paths, manifests, reports, journals and their linked ancestors are refused. Names reserved by Windows, alternate-stream separators and trailing dots/spaces are rejected on every platform. Invalid replacement groups produce an actionable CLI error. All destinations are preflighted before normal output creation; existing outputs and dangling links are refused using exclusive creation. An output error can leave a new manifest or report; inspect it and retry with fresh names.

Staging paths must be unused, and source and staged hashes are checked again before their moves. Ordinary caught I/O failures attempt a two-phase, content-checked rollback: committed targets first return to their recorded staging names, then originals are restored. This avoids a partially committed cycle blocking another original. Journals distinguish `rolled-back` from `interrupted`; a failed rollback preserves remaining data for inspection. Abrupt process termination can leave earlier journal phases, so read-only inspection compares actual hashes and never moves files. Case aliases or duplicate matching contents can require human review. Do not apply an undo manifest until the original operation completed.

Keep selected trees quiescent and retain the reviewed manifest/journal. These checks do not provide transactional filesystem snapshots, hostile-concurrency protection, hardware-failure recovery or automatic post-crash repair. No file contents are edited. Actual installed Windows link/junction/case acceptance and independent tagged-artifact review are release gates, separate from candidate source tests.

The unchanged six OS/Python3.10/3.13 runtime jobs feed the required `verify` job, which also runs formatting, lint, strict typing and dependency audit. Tag builds repeat quality/tests and produce wheel, sdist and exact two-payload `SHA256SUMS`; the checksum helper runs on the existing Python3.12 release environment. No runtime dependency or Python-floor migration is included.
