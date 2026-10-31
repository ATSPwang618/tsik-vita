#!/usr/bin/env python3
"""Inventory an extracted romfs tree (path, bytes) into JSON + per-directory summary.

# asset-pipeline-2, tsik-vita session 2026-10-31

Usage: py -3 tools/inventory_romfs.py [ROMFS_DIR] [OUT_JSON]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".work/nsp/romfs")
out = Path(sys.argv[2] if len(sys.argv) > 2 else ".work/assets/inventory/romfs-files.json")
files = []
total = 0
for path in sorted(root.rglob("*")):
    if path.is_file():
        size = path.stat().st_size
        total += size
        files.append({"path": path.relative_to(root).as_posix(), "bytes": size})
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"root": str(root), "files": len(files), "bytes": total, "entries": files},
                          ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"files={len(files)} bytes={total:,} ({total / 2**30:.2f} GiB) -> {out}")
by_dir = defaultdict(lambda: [0, 0])
for entry in files:
    parts = entry["path"].split("/")
    key = "/".join(parts[:2]) if len(parts) > 2 else (parts[0] if len(parts) > 1 else "(root)")
    by_dir[key][0] += 1
    by_dir[key][1] += entry["bytes"]
for key in sorted(by_dir):
    count, size = by_dir[key]
    print(f"{key:34s} {count:7d} {size:>14,}")
print("--- root files ---")
for entry in sorted((e for e in files if "/" not in e["path"]), key=lambda e: -e["bytes"]):
    print(f"{entry['bytes']:>14,}  {entry['path']}")
