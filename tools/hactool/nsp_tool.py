#!/usr/bin/env python3
"""PFS0/NSP inventory and extraction helper (no keys, no decryption).

The NSP is a plain PFS0 container. This tool reads the entry table, prints a
JSON inventory (optionally with SHA-256 of every entry), and extracts entries
to a directory, hashing while streaming. It never touches key material.

Usage:
  py -3 nsp_tool.py list   <nsp> [--hash] [--json out.json]
  py -3 nsp_tool.py extract <nsp> --outdir DIR [--include REGEX] [--exclude REGEX]
                                    [--manifest out.json] [--hash-existing]

Exit codes: 0 ok, 2 invalid container, 3 I/O/selection failure.
"""

import argparse
import hashlib
import json
import re
import struct
import sys
import time
from pathlib import Path

BLOCK = 8 * 1024 * 1024
MAX_ENTRIES = 10000
MAX_NAMES = 16 * 1024 * 1024


class Pfs0:
    def __init__(self, path):
        self.path = Path(path)
        self.size = self.path.stat().st_size
        with self.path.open("rb") as f:
            header = f.read(16)
            if len(header) != 16:
                raise ValueError("short PFS0 header")
            magic, count, names_size, _reserved = struct.unpack("<4sIII", header)
            if magic != b"PFS0":
                raise ValueError(f"not a PFS0 container (magic {magic!r})")
            if count > MAX_ENTRIES or names_size > MAX_NAMES:
                raise ValueError("implausible PFS0 header limits")
            table = f.read(count * 24)
            if len(table) != count * 24:
                raise ValueError("short PFS0 entry table")
            names = f.read(names_size)
            if len(names) != names_size:
                raise ValueError("short PFS0 name table")
            self.data_offset = 16 + count * 24 + names_size
            self.entries = []
            for index in range(count):
                offset, size, name_offset, _ = struct.unpack_from("<QQII", table, index * 24)
                end = names.find(b"\0", name_offset)
                if end < 0:
                    end = names_size
                try:
                    name = names[name_offset:end].decode("utf-8")
                except UnicodeDecodeError:
                    name = names[name_offset:end].decode("utf-8", "replace")
                if (
                    not name
                    or Path(name).name != name
                    or any(ch in name for ch in "/\\:")
                ):
                    raise ValueError(f"unsafe PFS0 entry name: {name!r}")
                if self.data_offset + offset + size > self.size:
                    raise ValueError(f"entry {name} extends beyond file")
                self.entries.append(
                    {"index": index, "name": name, "offset": offset, "bytes": size}
                )

    def read_entry(self, entry, digest=None, writer=None, progress=None):
        """Stream one entry; update digest and/or write to writer."""
        remaining = entry["bytes"]
        with self.path.open("rb") as f:
            f.seek(self.data_offset + entry["offset"])
            while remaining:
                block = f.read(min(BLOCK, remaining))
                if not block:
                    raise ValueError(f"unexpected EOF in entry {entry['name']}")
                if digest is not None:
                    digest.update(block)
                if writer is not None:
                    writer.write(block)
                remaining -= len(block)
                if progress is not None:
                    progress(entry, entry["bytes"] - remaining)


def sha256_entry(pfs, entry):
    digest = hashlib.sha256()
    pfs.read_entry(entry, digest=digest)
    return digest.hexdigest()


def cmd_list(args):
    pfs = Pfs0(args.nsp)
    started = time.monotonic()
    records = []
    total = 0
    for entry in pfs.entries:
        record = dict(entry)
        record["sha256"] = sha256_entry(pfs, entry) if args.hash else None
        records.append(record)
        total += entry["bytes"]
        print(
            f'[{entry["index"]:2d}] {entry["name"]}  {entry["bytes"]:,} bytes'
            + (f'  {record["sha256"]}' if record["sha256"] else ""),
            flush=True,
        )
    inventory = {
        "path": str(pfs.path),
        "bytes": pfs.size,
        "pfs0_data_offset": pfs.data_offset,
        "entry_count": len(pfs.entries),
        "entries_bytes": total,
        "sha256_complete": bool(args.hash),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "entries": records,
    }
    text = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(text, encoding="utf-8")
        print(f"wrote {args.json}", flush=True)
    else:
        print(text, flush=True)
    return 0


def cmd_extract(args):
    pfs = Pfs0(args.nsp)
    include = re.compile(args.include) if args.include else None
    exclude = re.compile(args.exclude) if args.exclude else None
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    selected = [
        entry
        for entry in pfs.entries
        if (include is None or include.search(entry["name"]))
        and (exclude is None or not exclude.search(entry["name"]))
    ]
    if not selected:
        print("no entries matched selection", file=sys.stderr)
        return 3
    print(
        f"extracting {len(selected)}/{len(pfs.entries)} entries, "
        f"{sum(e['bytes'] for e in selected):,} bytes -> {outdir}",
        flush=True,
    )

    manifest_path = Path(args.manifest) if args.manifest else outdir / "manifest.pfs0.json"
    prior = {}
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            prior = {r["name"]: r for r in payload.get("entries", [])}
        except (ValueError, KeyError):
            prior = {}

    records = []
    started = time.monotonic()
    next_report = started + 10.0
    for entry in selected:
        target = outdir / entry["name"]
        cached = prior.get(entry["name"])
        if (
            args.reuse
            and cached
            and cached.get("bytes") == entry["bytes"]
            and target.is_file()
            and target.stat().st_size == entry["bytes"]
            and not args.rehash
        ):
            print(f'reusing {entry["name"]} ({entry["bytes"]:,} bytes)', flush=True)
            records.append(cached)
            continue
        digest = hashlib.sha256()
        partial = target.with_name(target.name + ".partial")

        def progress(ent, done, _entry=entry, _started=started):
            nonlocal next_report
            now = time.monotonic()
            if now >= next_report:
                elapsed = now - _started
                rate = done / elapsed if elapsed > 0 else 0
                pct = done / ent["bytes"] * 100 if ent["bytes"] else 100
                print(
                    f'{ent["name"]}: {done:,}/{ent["bytes"]:,} bytes ({pct:.1f}%), '
                    f"{rate / (1024 * 1024):.1f} MiB/s, elapsed {elapsed:.0f}s",
                    flush=True,
                )
                next_report = now + 10.0

        with partial.open("wb") as output:
            pfs.read_entry(entry, digest=digest, writer=output, progress=progress)
        partial.replace(target)
        record = {
            "index": entry["index"],
            "name": entry["name"],
            "bytes": entry["bytes"],
            "sha256": digest.hexdigest(),
        }
        records.append(record)
        print(f'{entry["name"]}: done, sha256 {record["sha256"]}', flush=True)

    payload = {
        "source": str(pfs.path),
        "source_bytes": pfs.size,
        "extracted_bytes": sum(r["bytes"] for r in records),
        "extracted_at_unix": int(time.time()),
        "entries": records,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"extracted {len(records)} entries, {payload['extracted_bytes']:,} bytes, "
        f"{time.monotonic() - started:.1f}s; manifest {manifest_path}",
        flush=True,
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    lst = sub.add_parser("list", help="inventory PFS0 entries")
    lst.add_argument("nsp")
    lst.add_argument("--hash", action="store_true", help="compute SHA-256 of every entry")
    lst.add_argument("--json", help="write inventory JSON here instead of stdout")
    lst.set_defaults(func=cmd_list)

    ext = sub.add_parser("extract", help="extract PFS0 entries")
    ext.add_argument("nsp")
    ext.add_argument("--outdir", required=True)
    ext.add_argument("--include", help="regex; only matching names")
    ext.add_argument("--exclude", help="regex; skip matching names")
    ext.add_argument("--manifest", help="manifest JSON path")
    ext.add_argument("--reuse", action="store_true", help="reuse manifest entries whose file exists")
    ext.add_argument("--rehash", action="store_true", help="force re-hash even when reusing")
    ext.set_defaults(func=cmd_extract)

    args = parser.parse_args()
    try:
        return args.func(args)
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
