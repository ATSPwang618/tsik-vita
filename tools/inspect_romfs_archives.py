#!/usr/bin/env python3
"""Read-only TSUKIHIME romfs archive inventory + image-header census.

# asset-pipeline-2, tsik-vita session 2026-10-31

Parses the knife .hed/.nam/.mrg triplets in an already-extracted romfs and reports,
per archive: entry counts, stored bytes, name families, NX wrapper kinds, image
container kinds (KIMG/BNTX/KATL/JPEG/PNG), physical dimensions and formats. For
BNTX it uses the same header layout as tools/create_compact.py:bntx_info (BRTI at
table entries, fmt at +28, w/h at +36); for KIMG the 32-byte header
(magic, version, logical w/h, physical w/h, codec, length). Does not decode pixels
and never writes to the romfs.

Usage: py -3 tools/inspect_romfs_archives.py [--romfs DIR] [--out DIR]
             [--sample N] [--archives a,b,...]
"""
from __future__ import annotations

import argparse
import json
import mmap
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path


def read_names(nam: Path, rows: int) -> list[str]:
    if not nam.is_file():
        return [f"#{i}" for i in range(rows)]
    data = nam.read_bytes()
    out = []
    for i in range(rows):
        raw = data[i * 32:(i + 1) * 32]
        name = raw.split(b"\0")[0].split(b"\r")[0]
        out.append(name.decode("utf-8", "replace"))
    return out


FULL_DECODE_CAP = 16 * 1024 * 1024


def nx_decode(mm, begin: int, end: int, limit: int) -> bytes:
    length, compressed = struct.unpack_from("<II", mm, begin + 4)
    payload = mm[begin + 16:min(end, begin + 16 + compressed)]
    decoder = zlib.decompressobj(31 if mm[begin:begin + 4] == b"NXGX" else 15)
    return decoder.decompress(payload, min(length, limit))


def decode_header_payload(mm, row, limit=64 * 1024) -> tuple[bytes, str]:
    """Return (decoded head bytes, wrapper kind); decodes fully only when the BNTX/KATL
    header needs bytes beyond the first `limit` decoded bytes."""
    sector, stored, _unpacked = row
    begin = sector * 2048
    end = begin + stored * 2048
    if not stored or begin >= len(mm):
        return b"", "empty"
    head = mm[begin:min(end, begin + 64)]
    magic = head[:4]
    if magic in (b"NXCX", b"NXGX"):
        wrapper = magic.decode()
        try:
            data = nx_decode(mm, begin, end, limit)
        except Exception:
            return b"", wrapper + "-error"
        if data[:4] == b"KATL":
            try:
                data = nx_decode(mm, begin, end, FULL_DECODE_CAP)
            except Exception:
                pass
        elif data[:4] == b"BNTX" and len(data) >= 64:
            try:
                count = struct.unpack_from("<I", data, 36)[0]
                table = struct.unpack_from("<Q", data, 40)[0]
                if table + count * 8 > len(data):
                    data = nx_decode(mm, begin, end, FULL_DECODE_CAP)
            except Exception:
                pass
        return data, wrapper
    return bytes(mm[begin:min(end, begin + limit)]), "raw"


def kimg_info(data: bytes):
    if len(data) < 32 or data[:4] != b"KIMG":
        return None
    _magic, version, lw, lh, w, h, codec, length = struct.unpack_from("<4s7I", data)
    return {"container": "KIMG", "version": version, "logical": [lw, lh], "physical": [w, h],
            "codec": codec, "payload_bytes": length}


def bntx_info(data: bytes):
    if len(data) < 64 or data[:4] != b"BNTX":
        return None
    try:
        count = struct.unpack_from("<I", data, 36)[0]
        table = struct.unpack_from("<Q", data, 40)[0]
        textures = []
        for i in range(min(count, 64)):
            brti = struct.unpack_from("<Q", data, table + i * 8)[0]
            fmt = struct.unpack_from("<I", data, brti + 28)[0]
            w, h = struct.unpack_from("<II", data, brti + 36)
            p = struct.unpack_from("<Q", data, brti + 96)[0]
            try:
                n = struct.unpack_from("<H", data, p)[0]
                name = data[p + 2:p + 2 + n].decode("utf-8", "replace")
            except Exception:
                name = f"#{i}"
            textures.append({"name": name, "width": w, "height": h,
                             "format": hex(fmt), "srgb": (fmt & 255) == 6})
        return {"container": "BNTX", "texture_count": count, "textures": textures}
    except Exception as exc:  # malformed header: report, never fail the census
        return {"container": "BNTX", "error": str(exc), "textures": []}


def katl_info(data: bytes):
    if len(data) < 12 or data[:4] != b"KATL":
        return None
    version, count = struct.unpack_from("<II", data, 4)
    p = 12
    members = []
    try:
        for _ in range(count):
            nl, il = struct.unpack_from("<II", data, p)
            p += 8
            name = data[p:p + nl].decode("utf-8", "replace")
            p += nl
            member = data[p:p + il]
            p += il
            members.append({"name": name, "bytes": il, "kimg": kimg_info(member)})
        return {"container": "KATL", "version": version, "members": members}
    except Exception as exc:
        return {"container": "KATL", "error": str(exc), "members": members}


def jpeg_dimensions(data: bytes):
    """Parse width/height from the first SOF marker of a JPEG payload."""
    try:
        i = 2
        while i + 4 <= len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            length = struct.unpack_from(">H", data, i + 2)[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack_from(">HH", data, i + 5)
                return [int(w), int(h)]
            i += 2 + length
    except Exception:
        pass
    return None


def classify(data: bytes):
    if not data:
        return {"container": "empty"}
    for fn in (kimg_info, bntx_info, katl_info):
        info = fn(data)
        if info:
            return info
    if data[:2] == b"\xff\xd8":
        dims = jpeg_dimensions(data)
        return {"container": "JPEG", **({"physical": dims} if dims else {})}
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            w, h = struct.unpack_from(">II", data, 16)
            return {"container": "PNG", "physical": [w, h]}
        except Exception:
            return {"container": "PNG"}
    if data[:4] in (b"KATL", b"KIMG", b"BNTX"):
        return {"container": data[:4].decode("latin1")}
    return {"container": "data"}


def archive_report(romfs: Path, name: str, sample: int) -> dict:
    hed = romfs / f"{name}.hed"
    mrg = romfs / f"{name}.mrg"
    nam = romfs / f"{name}.nam"
    rows_all = list(struct.iter_unpack("<IHH", hed.read_bytes()))
    terminal = next((i for i, r in enumerate(rows_all) if r[0] == 0xFFFFFFFF), len(rows_all))
    rows = rows_all[:terminal]
    names = read_names(nam, terminal)
    ext = Counter()
    families = defaultdict(int)
    wrappers = Counter()
    containers = Counter()
    codecs = Counter()
    formats = Counter()
    physical = Counter()
    multi_texture = 0
    total_stored = 0
    records = []
    with mrg.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        thumb_positions = {nm: i for i, nm in enumerate(names) if "THUM" in nm.upper()}
        strip_candidates = Counter()
        order = list(range(len(rows)))
        if sample and sample < len(order):
            step = max(1, len(order) // sample)
            order = order[::step][:sample]
        for i in order:
            nm = names[i]
            suffix = nm.rsplit(".", 1)[-1].upper() if "." in nm else "NONE"
            ext[suffix] += 1
            family = "".join(ch for ch in nm.split(".")[0] if not ch.isdigit()) or "DIGITS"
            families[family[:24]] += 1
            row = rows[i]
            total_stored += row[1] * 2048
            data, wrapper = decode_header_payload(mm, row)
            wrappers[wrapper] += 1
            info = classify(data)
            containers[info["container"]] += 1
            if info.get("codec") is not None:
                codecs[info["codec"]] += 1
            if info.get("container") == "KIMG":
                physical[tuple(info["physical"])] += 1
            elif info.get("container") == "BNTX":
                if info.get("texture_count", 0) > 1:
                    multi_texture += 1
                for t in info.get("textures", []):
                    formats[t["format"]] += 1
                    physical[(t["width"], t["height"])] += 1
            records.append({"index": i, "name": nm, "wrapper": wrapper, "info": info})
        # Vertical language-strip candidates: BNTX heights divisible by 4 (or 3/2)
        for rec in records:
            info = rec["info"]
            textures = []
            if info.get("container") == "BNTX":
                textures = info.get("textures", [])
            elif info.get("container") == "KIMG":
                textures = [{"width": info["physical"][0], "height": info["physical"][1]}]
            for t in textures:
                h = t.get("height", 0)
                if h and h % 4 == 0 and h >= 4:
                    strip_candidates[4] += 1
                if h and h % 3 == 0:
                    strip_candidates[3] += 1
    return {
        "archive": name,
        "entries": len(rows),
        "nam_bytes": nam.stat().st_size if nam.is_file() else 0,
        "hed_bytes": hed.stat().st_size,
        "mrg_bytes": mrg.stat().st_size,
        "stored_bytes_sampled": total_stored,
        "sampled": len(order),
        "extensions": dict(ext.most_common(12)),
        "name_families": dict(sorted(families.items(), key=lambda kv: -kv[1])[:15]),
        "wrappers": dict(wrappers),
        "containers": dict(containers),
        "kimg_codecs": dict(sorted(codecs.items())),
        "bntx_formats": dict(sorted(formats.items())),
        "physical_top": [{"size": list(k), "count": v} for k, v in physical.most_common(15)],
        "bntx_multi_texture": multi_texture,
        "strip_candidate_heights": dict(sorted(strip_candidates.items())),
        "thumb_positions": thumb_positions,
        "records": records,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--romfs", type=Path, default=Path(".work/nsp/romfs"))
    ap.add_argument("--out", type=Path, default=Path(".work/assets/inventory"))
    ap.add_argument("--sample", type=int, default=0,
                    help="sample every N-th entry (0 = every entry)")
    ap.add_argument("--archives", help="comma separated archive base names; default: every .hed with .mrg/.nam")
    args = ap.parse_args()
    romfs = args.romfs.resolve()
    if not (romfs / "w_allpac.nam").is_file():
        raise SystemExit(f"no w_allpac.nam under {romfs}; merged romfs not ready")
    if args.archives:
        names = [n.strip() for n in args.archives.split(",") if n.strip()]
    else:
        names = sorted(p.stem for p in romfs.glob("*.hed")
                       if (romfs / (p.stem + ".mrg")).is_file())
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {"romfs": str(romfs), "archives": []}
    for name in names:
        report = archive_report(romfs, name, args.sample)
        summary["archives"].append({k: v for k, v in report.items() if k != "records"})
        (args.out / f"{name}.inventory.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "records"}, ensure_ascii=False))
    (args.out / "archives-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
