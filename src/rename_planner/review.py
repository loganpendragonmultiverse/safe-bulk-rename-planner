"""Local visual plans and non-mutating interruption inspection."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .safety import (
    MAX_JSON,
    MAX_RECORDS,
    hash_file,
    inside,
    no_links,
    read_json,
    typed_record,
)


def save_journal(path: Path, payload: dict[str, Any], *, initial: bool = False) -> None:
    path = no_links(path).resolve()
    content = json.dumps(payload, indent=2)
    if len(content.encode("utf-8")) > MAX_JSON:
        raise ValueError("Serialized journal exceeds 8 MiB")
    if initial:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        return
    if not path.is_file():
        raise ValueError("Existing journal is missing or not a regular file")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inspect_journal(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if (
        not isinstance(payload, dict)
        or payload.get("tool") != "safe-bulk-rename-planner"
        or not isinstance(payload.get("operations"), list)
    ):
        raise ValueError("Invalid rename journal")
    if (
        not isinstance(payload.get("root"), str)
        or not Path(payload["root"]).is_absolute()
    ):
        raise ValueError("Journal root must be an absolute local directory")
    root = no_links(Path(payload["root"])).resolve()
    if not root.is_dir() or len(payload["operations"]) > MAX_RECORDS:
        raise ValueError("Invalid journal root or excessive operation count")
    # Containment is checked even for malformed legacy records, before any read.
    for item in payload["operations"]:
        if not isinstance(item, dict):
            raise TypeError("Journal operations must be objects")
        for key in ("source", "temporary", "target"):
            inside(root, item.get(key))
    if (
        type(payload.get("schema_version")) is not int
        or payload["schema_version"] != 1
        or type(payload.get("undo")) is not bool
        or payload.get("status")
        not in {"prepared", "complete", "rolled-back", "interrupted"}
    ):
        raise ValueError("Unsupported journal schema, status or undo flag")
    inspections = []
    sources: set[str] = set()
    targets: set[str] = set()
    temporaries: set[str] = set()
    for item in payload["operations"]:
        typed_record(item, ("source", "temporary", "target"))
        if item.get("phase") not in {"pending", "staged", "committed", "rolled-back"}:
            raise ValueError("Invalid journal operation phase")
        if (
            Path(item["source"]).parent != Path(item["target"]).parent
            or Path(item["source"]).parent != Path(item["temporary"]).parent
        ):
            raise ValueError("Journal paths must preserve their original directory")
        for key, seen in (
            ("source", sources),
            ("target", targets),
            ("temporary", temporaries),
        ):
            if item[key] in seen:
                raise ValueError("Duplicate journal paths")
            seen.add(item[key])
        locations = []
        for key in ("source", "temporary", "target"):
            location = inside(root, item[key])
            matches = location.is_file() and hash_file(location) == (
                item["size"],
                item["sha256"],
            )
            locations.append(
                {
                    "location": key,
                    "path": item[key],
                    "exists": location.exists(),
                    "matches_expected_hash": matches,
                }
            )
        inspections.append(
            {
                "source": item["source"],
                "locations": locations,
                "review_required": sum(v["matches_expected_hash"] for v in locations)
                != 1,
            }
        )
    if temporaries & (sources | targets):
        raise ValueError("Temporary journal paths overlap sources or targets")
    return {
        "recorded_status": payload["status"],
        "operations": inspections,
        "boundary": "Inspection only. Crash windows are resolved from current hashes; no recovery rename is performed.",
    }


def render_html(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan).replace("<", "\\u003c").replace("&", "\\u0026")
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rename plan review</title>
<style>body{font:17px system-ui;max-width:1050px;margin:auto;padding:22px;background:#f5f1e8;color:#203442}article{background:white;padding:20px;border:1px solid #abc;border-radius:12px;margin:15px 0}p,label{overflow-wrap:anywhere}article{min-width:0}button,input{font:inherit;padding:10px}</style>
<h1>Rename plan review</h1><p>Review original and proposed names. Uncheck files to omit them and download a new manifest. Nothing is renamed in this page. Unicode NFC and case-fold collisions are rejected by the CLI; case-only renames use temporary staging.</p><main id="rows"></main><button id="download">Download selected manifest</button><p id="status" role="status"></p>
<script type="application/json" id="data">"""
        + payload
        + """</script><script>
const plan=JSON.parse(document.getElementById('data').textContent),selected=new Set(plan.renames.map((_,i)=>i));
for(const [i,item] of plan.renames.entries()){const article=document.createElement('article'),label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=true;check.addEventListener('change',()=>check.checked?selected.add(i):selected.delete(i));label.append(check,document.createTextNode(' Include '+item.source));article.append(label);const before=document.createElement('p'),after=document.createElement('p');before.textContent='Before: '+item.source;after.textContent='After: '+item.target;article.append(before,after);
if(item.source.toLowerCase()===item.target.toLowerCase()||item.source.normalize('NFC')===item.target.normalize('NFC')){const note=document.createElement('p');note.textContent='Case-only or Unicode-normalization change: inspect the exact spelling.';article.append(note);}document.getElementById('rows').append(article);}
document.getElementById('download').addEventListener('click',()=>{const output={...plan,renames:plan.renames.filter((_,i)=>selected.has(i))};const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='reviewed-rename-plan.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('status').textContent='Downloaded a new manifest. Apply with --apply-manifest after review; collision and hash checks run again.';});</script></html>"""
    )
