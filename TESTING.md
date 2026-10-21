# Testing

Install development tools with `python -m pip install -e ".[dev]"`. Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, and `python -m build`. CI also audits dependencies and runs the supported OS/Python matrix.

## 1.1.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Repair formatting and add visual per-file selection, Unicode/case collision review, interruption journals and read-only recovery inspection.

## 1.1.1 — 2026-10-16

Imported manifest paths are inspected in their lexical spelling before resolution. A symlink at a source, destination, root or ancestor is rejected before any rename or journal write. Containment, original-directory, Unicode/case collision, size and SHA-256 checks still apply. Normal apply/undo and read-only interruption inspection remain available. Use disposable trees for tests. Concurrent filesystem replacement remains outside the guarantee; this check does not make renames atomic or provide automatic recovery.

Regression tests use synthetic inputs and disposable trees. Run the complete suite and inspect built wheel/source documentation before preparing a draft PR.

## 1.1.2 acceptance

Keep all original assertions and complete `pytest`, formatting, lint, typing, build, dependency audit and supported CI checks. Regressions cover typed/nonobject manifests, malformed journals, relative containment, Windows reserved filenames, replacement-group errors, occupied staging paths, changed staged bytes, partial-cycle rollback and read-only incomplete recovery. Use actual disposable files and verify exact before/after contents; do not weaken fixtures to satisfy a platform.

Install wheel and sdist separately into fresh environments outside the checkout. Confirm site-packages provenance, actual console preview/apply/undo/inspection and installed README/DEVELOPMENT/TESTING/CHANGELOG/LICENSE/example bytes. Run the full original suite before focused native fixtures. `tests/test_native_paths.py` has ten cases: four real junction refusals, four real symlink refusals, native case-only apply/undo and Unicode collision. Windows must execute all ten with zero skips for both exact-tag distributions. Linux executes the six portable cases and records four Windows-only junction skips. Source and operational input bytes must remain unchanged where refusal is expected. Browser review must verify long literal filenames and selected-manifest download in the installed-generated HTML.
