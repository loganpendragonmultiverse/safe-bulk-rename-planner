# Development handoff

The public contract is preview-first and reversible. Never add implicit apply behavior, directory renaming, silent collision resolution, or automatic overwrites. Every feature release must update tests, version metadata, `CHANGELOG.md`, README descriptions and limitations, GitHub release copy, repository metadata, and the Forge catalog together.

Initial verification covers preview immutability, apply/undo, collision rejection, changed-file rejection, and path traversal rejection.
