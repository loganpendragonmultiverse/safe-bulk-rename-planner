# Development handoff

The public contract is preview-first and reversible. Never add implicit apply behavior, directory renaming, silent collision resolution, or automatic overwrites. Every feature release must update tests, version metadata, `CHANGELOG.md`, README descriptions and limitations, GitHub release copy, repository metadata, and the Forge catalog together.

Initial verification covers preview immutability, apply/undo, collision rejection, changed-file rejection, and path traversal rejection.

## 1.1.0 improvement session

Repair formatting and add visual per-file selection, Unicode/case collision review, interruption journals and read-only recovery inspection.

--exclude omits an exact relative source name. The local HTML review can uncheck files and download a selected manifest; --apply-manifest applies that reviewed input only after fresh collision and content-hash checks. Unicode NFC/case-fold collisions are rejected and original directories are preserved. CLI apply/undo creates a new journal beside the manifest, or uses --journal with a new path. The journal records every planned temporary path before changes and advances after staging/commit. --inspect-recovery JOURNAL compares current source/temporary/target hashes without moving anything, including a crash between a move and its journal update. Interrupted recovery remains an explicit human-reviewed operation. Existing manifests/reports/journals are protected.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.
