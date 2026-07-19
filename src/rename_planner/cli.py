from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .planner import apply_plan, create_plan, load_manifest, undo_plan, write_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rename-plan", description="Preview safe filename changes and optionally apply or undo a recorded plan.")
    parser.add_argument("directory", nargs="?", type=Path)
    parser.add_argument("--match", help="regular expression matched against each filename")
    parser.add_argument("--replace", help="regular expression replacement")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--output", type=Path, help="JSON manifest path")
    parser.add_argument("--apply", action="store_true", help="apply the reviewed plan; requires --output")
    parser.add_argument("--undo", type=Path, metavar="MANIFEST", help="undo an applied manifest after hash verification")
    args = parser.parse_args(argv)
    try:
        if args.undo:
            undo_plan(load_manifest(args.undo))
            print(f"Undid rename manifest {args.undo}")
            return 0
        if not args.directory or args.match is None or args.replace is None:
            parser.error("directory, --match, and --replace are required when not using --undo")
        if args.apply and not args.output:
            parser.error("--apply requires --output so the undo manifest is retained")
        plan = create_plan(args.directory, args.match, args.replace, args.recursive)
        if args.output:
            write_manifest(plan, args.output)
        print(json.dumps(plan.to_dict(), indent=2))
        if args.apply:
            apply_plan(plan)
            print(f"Applied {len(plan.renames)} rename(s). Undo with: rename-plan --undo {args.output}")
        else:
            print(f"Preview only: {len(plan.renames)} rename(s); no files changed.", file=sys.stderr)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"rename-plan: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
