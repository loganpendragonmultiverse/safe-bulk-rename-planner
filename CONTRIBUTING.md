# Contributing

Bug reports, focused feature proposals, documentation improvements, and pull requests are welcome. Please open an issue before a large behavior change.

For code changes:

1. Fork the repository and create a focused branch.
2. Install with `python -m pip install -e . pytest build`.
3. Add or update tests, especially for collisions, rollback, traversal, and changed-file behavior.
4. Run `python -m pytest` and `python -m build`.
5. Update the README and changelog when public behavior changes.
6. Submit a pull request explaining the problem, approach, safety impact, and verification performed.

Do not add implicit apply behavior, automatic overwrites, telemetry, or network access. A maintainer reviews every pull request; passing checks do not guarantee merge.
