#!/usr/bin/env python3
"""Correlate Switch exe image tables (logical layout dims, float) with romfs archive
BNTX physical dims to derive the per-archive scale factor for a 960x540 pack.

# asset-pipeline-2, tsik-vita session 2026-10-31

Design space hypothesis: the overseas build's logical canvas is 1280x720, so a
960x540 Vita render target means physical = 0.75 * logical. HD archives may use
1920x1080 logical (physical = 0.5 * logical).

Inputs (run from the repository root):
  .work/assets/inventory/exe-tables-overseas.txt  (kdu tables --all output; UTF-16 or UTF-8)
  .work/assets/inventory/<archive>.inventory.json (tools/inspect_romfs_archives.py output)
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "knife").is_dir():
            return parent
    return Path.cwd()


ROOT = repo_root()
INV = ROOT / ".work/assets/inventory"
ARCHIVES = ["w_allpac", "w_allpaccg", "w_allpacml", "w_allui", "allpachd", "allpachdml", "parts"]


def read_text_any(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def load_tables() -> dict[str, tuple[float, float, float, float, int]]:
    tables: dict[str, tuple[float, float, float, float, int]] = {}
    for line in read_text_any(INV / "exe-tables-overseas.txt").splitlines():
        parts = line.split()
        if len(parts) != 6:
            continue
        try:
            w, h, cx, cy = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            kind = int(parts[5])
        except ValueError:
            continue
        tables.setdefault(parts[0].upper(), (w, h, cx, cy, kind))
    return tables


def summarize(values: list[float], digits: int = 3) -> dict:
    if not values:
        return {}
    values = sorted(values)
    n = len(values)
    return {"count": n,
            "min": round(values[0], digits),
            "p10": round(values[n // 10], digits),
            "median": round(statistics.median(values), digits),
            "p90": round(values[(n * 9) // 10], digits),
            "max": round(values[-1], digits)}


def main() -> None:
    tables = load_tables()
    print(f"exe image records: {len(tables)}")
    design = Counter((round(w), round(h)) for w, h, _cx, _cy, _k in tables.values())
    print("logical size histogram (top 15):")
    for (w, h), count in design.most_common(15):
        print(f"  {w}x{h}: {count}")
    kinds = Counter(k for *_v, k in tables.values())
    print("kind histogram:", dict(sorted(kinds.items())))

    out: dict = {"exe_images": len(tables),
                 "logical_histogram": [{"size": list(k), "count": v} for k, v in design.most_common(40)],
                 "kind_histogram": dict(sorted(kinds.items())),
                 "archives": {}}
    for archive in ARCHIVES:
        path = INV / f"{archive}.inventory.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        ratios: list[float] = []
        ratios_w: list[float] = []
        ratios_h: list[float] = []
        scale_075: list[float] = []
        scale_050: list[float] = []
        matched = unmatched = multi = skipped = 0
        sample = []
        for rec in data.get("records", []):
            info = rec.get("info", {})
            name = rec["name"]
            stem = name.rsplit(".", 1)[0].upper()
            if name.upper().startswith("NOFILE") or info.get("container") == "empty":
                continue
            table = tables.get(stem)
            if not table:
                unmatched += 1
                continue
            matched += 1
            lw, lh = table[0], table[1]
            textures = info.get("textures") or []
            if info.get("container") == "BNTX" and len(textures) > 1:
                multi += 1
                continue
            if not textures and info.get("container") == "KIMG":
                textures = [{"width": info["physical"][0], "height": info["physical"][1]}]
            if not textures or lw <= 1 or lh <= 1:
                skipped += 1
                continue
            pw, ph = textures[0]["width"], textures[0]["height"]
            if pw < 8 or ph < 8:
                skipped += 1
                continue
            ratios.append(pw / lw)
            ratios_w.append(pw / lw)
            ratios_h.append(ph / lh)
            scale_075.append(0.75 * lw / pw)
            scale_050.append(0.5 * lw / pw)
            sample.append({"name": name, "logical": [round(lw, 2), round(lh, 2)],
                           "physical": [pw, ph], "ratio": [round(pw / lw, 3), round(ph / lh, 3)],
                           "scale_for_075": round(0.75 * lw / pw, 3),
                           "scale_for_050": round(0.5 * lw / pw, 3)})
        out["archives"][archive] = {
            "entries": data.get("entries"), "matched": matched, "unmatched": unmatched,
            "multi_texture_skipped": multi, "small_skipped": skipped,
            "physical_over_logical": summarize(ratios),
            "ratio_w_rounded": dict(Counter(round(r, 2) for r in ratios_w).most_common(8)),
            "ratio_h_rounded": dict(Counter(round(r, 2) for r in ratios_h).most_common(8)),
            "scale_for_075": summarize(scale_075),
            "scale_for_075_rounded": dict(Counter(round(r, 2) for r in scale_075).most_common(8)),
            "scale_for_050_rounded": dict(Counter(round(r, 2) for r in scale_050).most_common(8)),
            "sample_pairs": sample[:12],
        }
        print(f"\n=== {archive}: entries={data.get('entries')} matched={matched} unmatched={unmatched} multi={multi} small={skipped}")
        print("  phys/logical:", out["archives"][archive]["physical_over_logical"])
        print("  0.75*logical/physical (target 960 from 1280 design):", out["archives"][archive]["scale_for_075"])
        print("  scale_for_075 rounded:", out["archives"][archive]["scale_for_075_rounded"])
        for pair in sample[:5]:
            print("   ", pair)
    (INV / "scale-analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                             encoding="utf-8")


if __name__ == "__main__":
    main()
