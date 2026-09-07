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
python -m pip install -e . pytest build
python -m pytest
python -m build
```

## Project status

**Feature complete for v1.0.** Focused contributions that preserve preview-first behavior and reversibility are welcome.

Released under the [MIT License](LICENSE). Contributions follow the [organization guidelines](https://github.com/loganpendragonmultiverse/.github/blob/main/CONTRIBUTING.md).

## More open-source projects

This project is part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Browse the catalog for other released tools, source repositories, live demos, and downloads.

## Version 1.1.0: reviewed improvements

Repair formatting and add visual per-file selection, Unicode/case collision review, interruption journals and read-only recovery inspection.

```bash
rename-plan ./files --match ' ' --replace '-' --output plan.json --html review.html
```

--exclude omits an exact relative source name. The local HTML review can uncheck files and download a selected manifest; --apply-manifest applies that reviewed input only after fresh collision and content-hash checks. Unicode NFC/case-fold collisions are rejected and original directories are preserved. CLI apply/undo creates a new journal beside the manifest, or uses --journal with a new path. The journal records every planned temporary path before changes and advances after staging/commit. --inspect-recovery JOURNAL compares current source/temporary/target hashes without moving anything, including a crash between a move and its journal update. Interrupted recovery remains an explicit human-reviewed operation. Existing manifests/reports/journals are protected.
