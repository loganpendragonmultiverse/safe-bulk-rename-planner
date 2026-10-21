# Changelog

## [1.1.2] - 2026-10-21

- Preserve requested case-only rename spelling after containment verification on Windows.
- Validate typed manifests/journals and portable destinations, refuse reparse ancestors and protect report/manifest outputs with exclusive creation.
- Recheck source/staged content and refuse occupied temporary paths. Repair caught-failure rollback for partial rename cycles and record interrupted/rolled-back status truthfully.
- Bind hashing metadata within each OS API, retain all original regressions and add real native link/junction/case fixtures.
- Ship complete authority docs, license and an executable example with both distributions.

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
