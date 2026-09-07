"""Local visual plans and non-mutating interruption inspection."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def save_journal(path: Path, payload: dict[str, Any], *, initial: bool = False) -> None:
    if initial:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inspect_journal(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("tool") != "safe-bulk-rename-planner"
        or not isinstance(payload.get("operations"), list)
    ):
        raise ValueError("Invalid rename journal")
    root = Path(payload["root"]).resolve()
    inspections = []
    for item in payload["operations"]:
        locations = []
        for key in ("source", "temporary", "target"):
            location = (root / item[key]).resolve()
            if root not in location.parents:
                raise ValueError("Journal path leaves the original root")
            matches = False
            if location.is_file() and not location.is_symlink():
                digest = hashlib.sha256()
                with location.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                matches = (
                    location.stat().st_size == item["size"]
                    and digest.hexdigest() == item["sha256"]
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
    return {
        "recorded_status": payload.get("status"),
        "operations": inspections,
        "boundary": "Inspection only. Crash windows are resolved from current hashes; no recovery rename is performed.",
    }


def render_html(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan).replace("<", "\\u003c").replace("&", "\\u0026")
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rename plan review</title>
<style>body{font:17px system-ui;max-width:1050px;margin:auto;padding:22px;background:#f5f1e8;color:#203442}article{background:white;padding:20px;border:1px solid #abc;border-radius:12px;margin:15px 0}p{overflow-wrap:anywhere}button,input{font:inherit;padding:10px}</style>
<h1>Rename plan review</h1><p>Review original and proposed names. Uncheck files to omit them and download a new manifest. Nothing is renamed in this page. Unicode NFC and case-fold collisions are rejected by the CLI; case-only renames use temporary staging.</p><main id="rows"></main><button id="download">Download selected manifest</button><p id="status" role="status"></p>
<script type="application/json" id="data">"""
        + payload
        + """</script><script>
const plan=JSON.parse(document.getElementById('data').textContent),selected=new Set(plan.renames.map((_,i)=>i));
for(const [i,item] of plan.renames.entries()){const article=document.createElement('article'),label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=true;check.addEventListener('change',()=>check.checked?selected.add(i):selected.delete(i));label.append(check,document.createTextNode(' Include '+item.source));article.append(label);const before=document.createElement('p'),after=document.createElement('p');before.textContent='Before: '+item.source;after.textContent='After: '+item.target;article.append(before,after);
if(item.source.toLowerCase()===item.target.toLowerCase()||item.source.normalize('NFC')===item.target.normalize('NFC')){const note=document.createElement('p');note.textContent='Case-only or Unicode-normalization change: inspect the exact spelling.';article.append(note);}document.getElementById('rows').append(article);}
document.getElementById('download').addEventListener('click',()=>{const output={...plan,renames:plan.renames.filter((_,i)=>selected.has(i))};const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='reviewed-rename-plan.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('status').textContent='Downloaded a new manifest. Apply with --apply-manifest after review; collision and hash checks run again.';});</script></html>"""
    )
