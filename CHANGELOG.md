# Changelog

## [1.1.1] - 2026-10-16

Imported manifest paths are inspected in their lexical spelling before resolution. A symlink at a source, destination, root or ancestor is rejected before any rename or journal write. Containment, original-directory, Unicode/case collision, size and SHA-256 checks still apply. Normal apply/undo and read-only interruption inspection remain available. Use disposable trees for tests. Concurrent filesystem replacement remains outside the guarantee; this check does not make renames atomic or provide automatic recovery.


## 1.1.0 - 2026-09-07

- Repair formatting and add visual per-file selection, Unicode/case collision review, interruption journals and read-only recovery inspection.
- Added regression coverage for the audited behavior and invalid inputs.

## 1.0.0 - 2026-07-18

- Added non-destructive regular-expression rename previews.
- Added collision, traversal, symlink, size, and SHA-256 safety checks.
- Added manifest-required application and content-verified undo through two-phase renames.
- Added recursive opt-in, tests, packaging, and cross-platform CI.
