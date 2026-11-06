"""Restore image density from original romfs, with one temporary archive at a time.

Requires the user's existing romfs, kdu and (for UI) indexed BNTX PNG cache.
Keeps archive indices, logical dimensions, bilingual strip order and UNORM bytes.
No complete extracted-image directory or second resource tree is produced.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import zlib

import numpy as np
from PIL import Image, ImageFile
from vita_image_metadata import CAP, image_info, images_in

ImageFile.MAXBLOCK = 16 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
SECTOR = 2048
PIXELS = 960 * 1080  # Also bounds the CPU fallback for STEC / raw sampling.


def quality_size(width, height, *, png=False):
    """Half-source oversampling, never below a fitted 540p frame unless bounded.

    A tall sprite or an animation strip is not a complete screen. GXT supports
    2048 on either axis; retain that shape within the existing RGBA work budget.
    Small source variants keep all original pixels, instead of scaling by .375.
    """
    factor = min(1.0, max(0.5, min(960 / width, 540 / height)))
    factor = min(factor, (960 if png else 2048) / width,
                 (1080 if png else 2048) / height, math.sqrt(PIXELS / (width * height)))
    return max(1, math.floor(width * factor)), max(1, math.floor(height * factor))


def kimg(image, logical, codec):
    image = image.convert('RGBA')
    if codec in (2, 7):
        output = io.BytesIO()
        image.save(output, 'PNG', compress_level=6)
        payload = output.getvalue()
    else:
        payload = gxt(image)
    result = struct.pack('<4s7I', b'KIMG', 1, *logical, *image.size, codec, len(payload)) + payload
    image_info(result)
    return result


def gxt(image):
    # Encode original encoded-UNORM RGB once. No Alter bake / inverse round trip.
    w, h = image.size
    bw, bh = max(4, 1 << (w - 1).bit_length()), max(4, 1 << (h - 1).bit_length())
    padded = Image.fromarray(np.pad(np.asarray(image), ((0, bh-h), (0, bw-w), (0, 0)), mode='edge'))
    opaque = image.getchannel('A').getextrema() == (255, 255)
    bpe, codec, fmt = (8, 'DXT1', 0x85000000) if opaque else (16, 'DXT5', 0x87000000)
    out = io.BytesIO()
    padded.save(out, 'DDS', pixel_format=codec)
    encoded = out.getvalue()
    if encoded[84:88] != codec.encode() or len(encoded)-128 != bw*bh*bpe//16:
        raise ValueError('DDS encoding contract')
    payload = native().swizzle(encoded[128:], bw//4, bh//4, bpe)
    return (struct.pack('<8I', 0x00545847, 0x10000003, 1, 64, len(payload), 0, 0, 0)
            + struct.pack('<6IHHB3s', 64, len(payload), 0xffffffff, 0, 0xa0000000,
                          fmt, w, h, 1, b'\0'*3) + payload)


_native = None
def native():
    global _native
    if _native is None:
        spec = importlib.util.spec_from_file_location('native_color', ROOT/'tools/migrate-vita-native-color.py')
        _native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_native)
    return _native


def atlas(items):
    result = bytearray(b'KATL' + struct.pack('<II', 1, len(items)))
    for name, data in items:
        label = name.encode()
        result.extend(struct.pack('<II', len(label), len(data)) + label + data)
    if len(result) > CAP:
        raise ValueError(f'atlas exceeds existing Vita read budget: {len(result)}')
    return bytes(result)


def thumbnail_pages(source):
    if source.size != (5544, 4840):
        raise ValueError('unexpected original CG sheet')
    result = []
    for first in range(0, 36*55, 72):
        page = Image.new('RGBA', (6*116, 12*66))
        for local in range(min(72, 36*55-first)):
            cell = first+local
            x, y = (cell % 36)*154, (cell//36)*88
            thumb = source.crop((x, y, x+154, y+88)).resize((116, 66), Image.Resampling.LANCZOS)
            page.paste(thumb, ((local % 6)*116, (local//6)*66))
        result.append((f'cg_thumb_page_{first//72}', kimg(page, (6*154, 12*88), 7)))
    return atlas(result)


def unpack(data, *, original=False):
    if data[:4] not in (b'NXCX', b'NXGX'):
        return data
    length, compressed = struct.unpack_from('<II', data, 4)
    if (not original and length > CAP) or compressed+16 > len(data):
        raise ValueError('NX bounds')
    raw = zlib.decompress(data[16:16+compressed], 31 if data[:4] == b'NXGX' else 15)
    # Original NXGX declared sizes include padding; current compact lengths are exact.
    if not original and len(raw) != length:
        raise ValueError('NX length')
    return raw


def pack(data):
    if len(data) > CAP:
        raise ValueError('Vita entry read budget')
    compressed = zlib.compress(data, 1)
    return struct.pack('<4sIII', b'NXCX', len(data), len(compressed), 0) + compressed


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def rows(root, archive):
    data = (root/f'{archive}.hed').read_bytes()
    values = list(struct.iter_unpack('<IHH', data))
    end = next(i for i, v in enumerate(values) if v[0] == 0xffffffff)
    return values[:end], data[end*8:]


def read_at(stream, row):
    sector, count, _ = row
    stream.seek(sector*SECTOR)
    data = stream.read(count*SECTOR)
    if len(data) != count*SECTOR:
        raise ValueError('archive extent')
    return data


def members(raw):
    if raw[:4] == b'KIMG':
        return [('', raw[:image_info(raw)['envelope_bytes']])]
    if raw[:4] != b'KATL':
        return []
    result, p = [], 12
    version, count = struct.unpack_from('<II', raw, 4)
    if version != 1: raise ValueError('atlas version')
    for _ in range(count):
        nl, il = struct.unpack_from('<II', raw, p); p += 8
        name = raw[p:p+nl].decode(); p += nl
        result.append((name, raw[p:p+il])); p += il
    if p != len(raw): raise ValueError('atlas extent')
    return result


def source_image(args, archive, index, source_bytes):
    data = unpack(source_bytes, original=True)
    if data[:4] != b'BNTX':
        return Image.open(io.BytesIO(data)).convert('RGBA')
    # kdu decodes BC7 and the Switch block-linear layout. Remove every temporary
    # decoded source immediately, including on conversion failure.
    with tempfile.TemporaryDirectory(prefix='image-', dir=args.scratch) as temp:
        path = Path(temp)/'source.png'
        subprocess.run([str(args.kdu), '--romfs', str(args.romfs), 'extract', archive,
                        f'#{index}', str(path), '--indexed'], check=True, stdout=subprocess.DEVNULL)
        return Image.open(path.with_name('source_0.png')).convert('RGBA')


def improve(raw, source, *, strips=1, ui=False):
    info = image_info(raw)
    lw, lh = info['logical']; old_w, old_h = info['physical']
    width, rows_ = source.width, source.height // (4 if strips == 2 else 1)
    if strips == 2 and (lw != source.width or lh//2 != source.height//4):
        raise ValueError('original bilingual strip dimensions')
    if strips == 1 and (lw, lh) != source.size:
        raise ValueError('original and compact logical dimensions differ')
    target = quality_size(width, rows_, png=strips > 1)
    if target[0] < old_w*1.2 and target[1]*strips < old_h*1.2:
        return raw, None
    output = Image.new('RGBA', (target[0], target[1]*strips))
    for dest, original in enumerate((0, 2) if strips == 2 else (0,)):
        top = source.height*original//4 if strips == 2 else 0
        piece = source.crop((0, top, width, top+rows_))
        output.paste(piece.resize(target, Image.Resampling.LANCZOS), (0, target[1]*dest))
    # UI and bilingual PNG retain their current colour contract. GPU-native GXT
    # permits tall sprites without raising the ordinary PNG/JPEG decoder bounds.
    png = strips > 1 or (ui and target[0] <= 960 and target[1] <= 1080)
    codec = (2 if info['codec'] in (1, 2) else 7) if png else 9
    result = kimg(output, (lw, lh), codec)
    if target[0]*target[1] > PIXELS:
        raise ValueError('CPU fallback work budget')
    return result, dict(before=info['physical'], physical=list(output.size),
                        logical=[lw, lh], source=list(source.size), codec=codec, strips=strips)


def restore_entry(args, archive, index, name, old, original):
    data = unpack(old)
    if name.startswith('CG_THUMB_PARTS_') and data[:4] == b'KIMG':
        with Image.open(args.ui_cache/f'{index}_0.png') as source:
            value = thumbnail_pages(source.convert('RGBA'))
        return pack(value), [dict(index=index, name=name, paged_thumbnails=28)], value
    items = members(data)
    if not items: return old, [], data
    # The UI cache holds original members in their original BNTX order.
    if archive == 'w_allui':
        converted, changes = [], []
        for k, (label, image) in enumerate(items):
            info = image_info(image)
            lw, lh = info['logical']
            target = quality_size(lw, lh)
            if target[0] >= info['physical'][0]*1.2 or target[1] >= info['physical'][1]*1.2:
                with Image.open(args.ui_cache/f'{index}_{k}.png') as source:
                    image, change = improve(image, source.convert('RGBA'), ui=True)
                if change: changes.append(dict(index=index, name=name, member=label, **change))
            converted.append((label, image))
        value = atlas(converted) if data[:4] == b'KATL' else converted[0][1]
        return (pack(value) if changes else old), changes, value
    if len(items) != 1: raise ValueError('unexpected story atlas')
    image = items[0][1]; info = image_info(image)
    source_data = unpack(original, original=True)
    # Original logical metrics are the original texture dimensions, except that
    # the bilingual package removed English and traditional Chinese strips.
    n = 2 if archive == 'w_allpacml' and source_data[:4] == b'BNTX' and info['logical'][1] > 100 else 1
    lw, lh = info['logical']
    target = quality_size(lw, lh//n, png=n > 1)
    if target[0] < info['physical'][0]*1.2 and target[1]*n < info['physical'][1]*1.2:
        return old, [], data
    source = source_image(args, archive, index, original)
    n = 2 if source.height//4 == lh//2 and source.width == lw else 1
    value, change = improve(image, source, strips=n)
    return (pack(value) if change else old), ([dict(index=index, name=name, **change)] if change else []), value


def restore_archive(args, archive, manifest):
    old_rows, tail = rows(args.assets, archive)
    source_rows, _ = rows(args.romfs, archive)
    names = (args.assets/f'{archive}.nam').read_bytes()
    if len(source_rows) != len(old_rows): raise ValueError('archive index mismatch')
    temp = args.assets/f'{archive}.mrg.quality-partial'
    if temp.exists(): raise ValueError(f'unfinished archive requires inspection: {temp}')
    changes, new_hed, seen = [], bytearray(), {}
    summary = collections.Counter()
    begin = time.monotonic()
    with (args.assets/f'{archive}.mrg').open('rb') as current, (args.romfs/f'{archive}.mrg').open('rb') as source, temp.open('wb') as output:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for first in range(0, len(old_rows), args.jobs):
                pending = []
                for index in range(first, min(first+args.jobs, len(old_rows))):
                    name = names[index*32:(index+1)*32].split(b'\0')[0].split(b'\r')[0].decode()
                    key = (old_rows[index], source_rows[index])
                    # Preserve aliases; no duplicated source PNGs or new archive data.
                    if key in seen:
                        pending.append((index, key, None)); continue
                    future = pool.submit(restore_entry, args, archive, index, name,
                                         read_at(current, old_rows[index]), read_at(source, source_rows[index]))
                    pending.append((index, key, future))
                for index, key, future in pending:
                    if key in seen:
                        new_hed.extend(seen[key]); continue
                    try:
                        encoded, reports, raw = future.result()
                    except Exception as error:
                        raise RuntimeError(f'{archive}[{index}]: {error}') from error
                    record = struct.pack('<IHH', output.tell()//SECTOR, math.ceil(len(encoded)/SECTOR),
                                         math.ceil(len(raw)/SECTOR) if reports else old_rows[index][2])
                    output.write(encoded); output.write(b'\0'*(-len(encoded) % SECTOR))
                    seen[key] = record; new_hed.extend(record)
                    changes.extend(reports)
                    for _, info in images_in(raw):
                        summary['images'] += 1; summary['pixels'] += math.prod(info['physical'])
                        summary[f'codec_{info["codec"]}'] += 1
                    summary['atlases'] += raw[:4] == b'KATL'
                if first % (args.jobs*64) == 0:
                    print(f'{archive}: {first}/{len(old_rows)}, {len(changes)} restored, {output.tell()/1048576:.1f} MiB, {time.monotonic()-begin:.0f}s', flush=True)
        output.flush(); os.fsync(output.fileno())
    new_hed.extend(tail)
    if not changes:
        temp.unlink(); return dict(archive=archive, images=0)
    # Both old files remain intact until the new archive has been fully encoded.
    hed_partial = args.assets/f'{archive}.hed.quality-partial'
    hed_partial.write_bytes(new_hed)
    before_bytes = (args.assets/f'{archive}.mrg').stat().st_size
    temp.replace(args.assets/f'{archive}.mrg'); hed_partial.replace(args.assets/f'{archive}.hed')
    for entry in manifest['files']:
        if entry['path'] in (f'{archive}.mrg', f'{archive}.hed'):
            p = args.assets/entry['path']; entry.update(bytes=p.stat().st_size, sha256=sha_file(p))
    row = next(r for r in manifest['archives'] if r['name'] == archive)
    row.update(bytes=(args.assets/f'{archive}.mrg').stat().st_size,
               pixels=summary['pixels'], images=summary['images'], atlases=summary['atlases'],
               textures=summary['images'], codecs={k[6:]:v for k,v in summary.items() if k.startswith('codec_')})
    report = dict(archive=archive, before_bytes=before_bytes, after_bytes=row['bytes'],
                  restored=len(changes), elapsed_s=round(time.monotonic()-begin, 2), changes=changes)
    report_path = args.scratch/f'{archive}-quality.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    manifest.setdefault('quality_restoration', {})[archive] = dict(
        restored=len(changes), source='original-romfs', policy='half-source-or-screen-fit-bounded-v1',
        report_sha256=sha_file(report_path), rgba_pixel_budget=PIXELS, max_gxt_dimension=2048)
    manifest['statistics'].update(files=len(manifest['files']), bytes=sum(f['bytes'] for f in manifest['files']))
    manifest['statistics'].update(textures=sum(a['textures'] for a in manifest['archives']),
                                  pixels=sum(a['pixels'] for a in manifest['archives']))
    # Texture/pixel counters before this revision were accumulated across stages.
    # Report only current rewritten archives here instead of retaining that stale total.
    manifest['quality_restoration_summary'] = dict(
        archives=list(manifest['quality_restoration']),
        restored=sum(a['restored'] for a in manifest['quality_restoration'].values()),
        source_preserved=True, hardware_verified=False)
    marker = args.assets/'vita-540p-assets.json'
    marker.with_suffix('.quality-partial').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    marker.with_suffix('.quality-partial').replace(marker)
    print(f'{archive}: committed {len(changes)} changes; {before_bytes} -> {row["bytes"]} bytes', flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--romfs', type=Path, required=True)
    p.add_argument('--kdu', type=Path, required=True)
    p.add_argument('--ui-cache', type=Path, required=True)
    p.add_argument('--scratch', type=Path, required=True)
    p.add_argument('--archives', nargs='+', default=['w_allui', 'w_allpaccg', 'w_allpac', 'w_allpacml'])
    p.add_argument('--jobs', type=int, default=4)
    args = p.parse_args()
    if not 1 <= args.jobs <= 8: raise ValueError('jobs must be 1..8')
    args.kdu = args.kdu.resolve(); args.scratch.mkdir(parents=True, exist_ok=True)
    native()  # initialize before threads
    manifest = json.loads((args.assets/'vita-540p-assets.json').read_bytes())
    if manifest['method'] != 'native-540p-encoded-unorm-v2': raise ValueError('expected native UNORM pack')
    if args.assets.resolve() == args.romfs.resolve(): raise ValueError('source must remain read-only')
    for archive in args.archives:
        if archive in manifest.get('quality_restoration', {}):
            print(archive, 'already restored; skipped', flush=True); continue
        restore_archive(args, archive, manifest)


if __name__ == '__main__': main()
