# Development handoff

The public contract is preview-first and reversible. Never add implicit apply behavior, directory renaming, silent collision resolution, or automatic overwrites. Every feature release must update tests, version metadata, `CHANGELOG.md`, README descriptions and limitations, GitHub release copy, repository metadata, and the Forge catalog together.

Initial verification covers preview immutability, apply/undo, collision rejection, changed-file rejection, and path traversal rejection.

## 1.1.0 improvement session

Repair formatting and add visual per-file selection, Unicode/case collision review, interruption journals and read-only recovery inspection.

--exclude omits an exact relative source name. The local HTML review can uncheck files and download a selected manifest; --apply-manifest applies that reviewed input only after fresh collision and content-hash checks. Unicode NFC/case-fold collisions are rejected and original directories are preserved. CLI apply/undo creates a new journal beside the manifest, or uses --journal with a new path. The journal records every planned temporary path before changes and advances after staging/commit. --inspect-recovery JOURNAL compares current source/temporary/target hashes without moving anything, including a crash between a move and its journal update. Interrupted recovery remains an explicit human-reviewed operation. Existing manifests/reports/journals are protected.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.

## 1.1.1 — 2026-10-16

Imported manifest paths are inspected in their lexical spelling before resolution. A symlink at a source, destination, root or ancestor is rejected before any rename or journal write. Containment, original-directory, Unicode/case collision, size and SHA-256 checks still apply. Normal apply/undo and read-only interruption inspection remain available. Use disposable trees for tests. Concurrent filesystem replacement remains outside the guarantee; this check does not make renames atomic or provide automatic recovery.

## 1.1.2 contract

Preserve original tests and all protected checks. Same-file metadata comparisons use each API's own snapshots; cross-API identity and complete streamed hashes remain required. Never overwrite an occupied temporary path or restore unverified contents. Caught-error rollback stages committed targets before originals, preserving cycles. Uncaught termination remains explicit read-only inspection, not automatic recovery. Journal states must describe actual completion or incomplete rollback. All output pairs are preflighted and new reports/manifests use exclusive creation.

There was no pre-existing numeric coverage gate; run supplementary branch coverage to inspect meaningful missing behavior without replacing the original complete test command. Actual installed Windows junction/symlink/case execution remains mandatory before release; platform skips are not native acceptance.
