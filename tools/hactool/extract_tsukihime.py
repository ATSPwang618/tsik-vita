#!/usr/bin/env python3
"""Extract the user's own TSUKIHIME NSP into NCAs, update exefs and merged romfs.

Run from the project root:  py -3 tools/hactool/extract_tsukihime.py [--nca-only] [--romfs-only]

The NSP is a merged base+update PFS0. hactool handles the update BKTR through
`--basenca=<base program NCA>` while extracting the update program's romfs, which
is the merged base+update romfs. Keys are read from the Ryujinx installation and
are only passed on the hactool command line; they are never copied or logged.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / ".work" / "nsp"
HACTOOL = ROOT / "tools" / "hactool" / "hactool.exe"
KEYS = Path(r"C:\Users\26241\AppData\Roaming\Ryujinx\system\prod.keys")
LOG = WORK / "logs"


def run(args, log_name, timeout=None):
    LOG.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with (LOG / log_name).open("w", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen(
            [str(HACTOOL), "-k", str(KEYS), "--disablekeywarns", *args],
            cwd=str(WORK), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        lines = []
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            lines.append(line)
            if len(lines) % 200 == 0:
                print(line.rstrip(), flush=True)
        code = process.wait(timeout=timeout)
    elapsed = time.monotonic() - started
    print(f"[{log_name}] exit={code} elapsed={elapsed:.1f}s", flush=True)
    if code != 0:
        raise SystemExit(f"hactool failed for {log_name}: exit {code}; see {LOG / log_name}")
    return "".join(lines)


def nsp_path():
    candidates = sorted((WORK / "src").glob("*.nsp"))
    if not candidates:
        raise SystemExit("no NSP under .work/nsp/src (junction to switch原版游戏 missing?)")
    return candidates[0]


def extract_ncas():
    nca_dir = WORK / "nca"
    nca_dir.mkdir(parents=True, exist_ok=True)
    print("=== hactool: extracting PFS0 entries (NCAs) ===", flush=True)
    run(["-t", "pfs0", "-x", "--outdir=nca", str(nsp_path())], "pfs0-extract.log")


def nca_info():
    records = []
    for path in sorted((WORK / "nca").glob("*")):
        if path.suffix not in (".nca", ".tik", ".cert"):
            continue
        if path.suffix != ".nca":
            continue
        text = run(["-t", "nca", "-i", f"nca/{path.name}"], f"nca-info-{path.name[:16]}.log")
        record = {"file": path.name, "bytes": path.stat().st_size,
                  "sha256": sha256(path)}
        title = re.search(r"Title ID:\s*([0-9a-fA-F]{16})", text)
        kind = re.search(r"Content Type:\s*(.+)", text)
        program_id = re.search(r"Program Id:\s*([0-9a-fA-F]{16})", text, re.IGNORECASE)
        record["title_id"] = title.group(1) if title else None
        record["content_type"] = kind.group(1).strip() if kind else None
        record["program_id"] = program_id.group(1) if program_id else None
        records.append(record)
        print(record, flush=True)
    return records


def sha256(path):
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choose_programs(records):
    programs = [r for r in records if (r["content_type"] or "").lower().startswith("program")]
    if not programs:
        raise SystemExit("no program NCA found")
    programs.sort(key=lambda r: r["bytes"], reverse=True)
    base = programs[0]
    update = programs[1] if len(programs) > 1 else programs[0]
    return base, update


def extract_exefs(program, name):
    out = WORK / name
    if out.exists():
        print(f"{name} already exists; reusing (delete to refresh)", flush=True)
        return out
    out.mkdir(parents=True, exist_ok=True)
    run(["-t", "nca", "--exefsdir=" + name, f"nca/{program['file']}"], f"exefs-{name}.log")
    return out


def extract_romfs(base, update):
    romfs = WORK / "romfs"
    romfs.mkdir(parents=True, exist_ok=True)
    print(f"=== merged romfs: update program {update['file']} + base {base['file']} ===", flush=True)
    run(["-t", "nca", "--basenca=" + f"nca/{base['file']}",
         "--romfsdir=romfs", f"nca/{update['file']}"], "romfs-merge.log")


def build_id(exefs_dir):
    main = exefs_dir / "main"
    if not main.is_file():
        return None
    with main.open("rb") as stream:
        header = stream.read(0x60)
    if header[:4] != b"NSO0":
        return None
    return header[0x40:0x48].hex()


def inventory(records, base, update):
    romfs = WORK / "romfs"
    files = [p for p in romfs.rglob("*") if p.is_file()]
    entries = []
    total = 0
    for path in files:
        size = path.stat().st_size
        total += size
        entries.append({"path": path.relative_to(romfs).as_posix(), "bytes": size})
    entries.sort(key=lambda e: e["bytes"], reverse=True)
    manifest = {
        "nsp": str(nsp_path()),
        "nsp_bytes": nsp_path().stat().st_size,
        "ncas": records,
        "base_program": base,
        "update_program": update,
        "exefs_build_id_base": build_id(WORK / "exefs-base"),
        "exefs_build_id_update": build_id(WORK / "exefs-update"),
        "knife_overseas_build_id": "d10d239aade1d526",
        "romfs_files": len(files),
        "romfs_bytes": total,
        "romfs_top": entries[:80],
        "has_w_allpac_nam": (romfs / "w_allpac.nam").is_file(),
    }
    (WORK / "inventory.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main():
    if not HACTOOL.is_file():
        raise SystemExit(f"missing hactool: {HACTOOL}")
    if not KEYS.is_file():
        raise SystemExit(f"missing keys: {KEYS}")
    nca_only = "--nca-only" in sys.argv
    romfs_only = "--romfs-only" in sys.argv
    if not romfs_only:
        extract_ncas()
    records = nca_info()
    base, update = choose_programs(records)
    print(f"base program   = {base['file']} ({base['bytes']:,} B)")
    print(f"update program = {update['file']} ({update['bytes']:,} B)")
    if not nca_only:
        extract_exefs(base, "exefs-base")
        extract_exefs(update, "exefs-update")
        extract_romfs(base, update)
    manifest = inventory(records, base, update)
    print(json.dumps({k: manifest[k] for k in
                      ("exefs_build_id_base", "exefs_build_id_update",
                       "knife_overseas_build_id", "romfs_files", "romfs_bytes",
                       "has_w_allpac_nam")}, indent=2), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
