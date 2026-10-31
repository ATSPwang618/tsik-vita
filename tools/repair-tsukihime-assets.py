#!/usr/bin/env python3
"""Repair Tsukihime images outside Vita decode bounds, preserving logical sizes.

The source tree is read-only. A new output tree shares unchanged files by hard
link; rewritten archives and the manifest use new inodes. No game data in VPK.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import mmap
import os
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = ('w_allpac', 'w_allpaccg', 'w_allpacml', 'w_allui', 'allpachd', 'parts')
SECTOR = 2048
CAP = 32 * 1024 * 1024

def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

def strip_names(bundle):
    raw = zlib.decompress(bundle.read_bytes())
    if raw[:4] != b'KXT0' or raw[4:12].hex() != 'd10d239aade1d526':
        raise ValueError('expected verified Tsukihime overseas executable tables')
    count, = struct.unpack_from('<I', raw, 36)
    segments, pos = [], 40
    for _ in range(count):
        va, length = struct.unpack_from('<QI', raw, pos)
        pos += 12
        segments.append((va, raw[pos:pos+length]))
        pos += length
    if pos != len(raw):
        raise ValueError('table envelope')
    def read(va, length):
        for start, data in segments:
            if start <= va and va + length <= start + len(data):
                return data[va-start:va-start+length]
        raise ValueError(f'missing table range {va:x}')
    names = read(0x4cf9ec, 32 * 14744)
    infos = read(0x35f0b8, 72 * 14744)
    return {names[i*32:(i+1)*32].split(b'\0')[0].decode().upper()
            for i in range(14744) if infos[i*72+67] & 2}

def unpack(data):
    if data[:4] not in (b'NXCX', b'NXGX'):
        return data
    length, compressed = struct.unpack_from('<II', data, 4)
    if length > CAP or compressed + 16 > len(data):
        raise ValueError('NX bounds')
    dec = zlib.decompressobj(31 if data[:4] == b'NXGX' else 15)
    raw = dec.decompress(data[16:16+compressed], length+1)
    if len(raw) != length or not dec.eof or dec.unused_data or dec.unconsumed_tail:
        raise ValueError('NX stream')
    return raw

def repair_image(raw, name, strips, native):
    if raw[:4] != b'KIMG':
        return raw, None
    version, lw, lh, w, h, codec, length = struct.unpack_from('<7I', raw, 4)
    if version != 1 or length > len(raw)-32 or not w or not h:
        raise ValueError('KIMG envelope')
    n = 4 if name.split('_')[0].upper() in strips else 1
    if w <= 960 and h // n <= 1080:
        return raw, None
    if h % n:
        raise ValueError('uneven language strips')
    from PIL import Image
    from compact_media import encode_portable
    payload = raw[32:32+length]
    if codec == 9:
        image, size, _, _ = native.gxt_decode(payload)
        if size != (w, h):
            raise ValueError('GXT dimensions mismatch')
        image = image.crop((0, 0, w, h))
    elif codec in (1, 2, 7):
        image = Image.open(io.BytesIO(payload)).convert('RGBA')
        if image.size != (w, h):
            raise ValueError('PNG/JPEG dimensions mismatch')
    else:
        raise ValueError(f'oversized unsupported KIMG codec {codec}')
    # Use mofa's per-language 960x540 fit and preserve logical coordinates.
    # Lossless PNG keeps the decoded UNORM colour/alpha of existing codec9 art;
    # it does not run inverse Alter a second time or add another DXT generation.
    result, info = encode_portable(image, (lw, lh), srgb=codec not in (7, 9),
                                   force_png=True, strips=n)
    info.update(name=name, source_codec=codec)
    return result, info

def update_archive_summary(manifest, report, output):
    for archive in manifest['archives']:
        name = archive['name']
        archive['bytes'] = (output/f'{name}.mrg').stat().st_size
        removed = sum(row['before'][0]*row['before'][1] - row['physical'][0]*row['physical'][1]
                      for row in report['images'] if row['archive'] == name)
        archive['pixels'] -= removed
    manifest['verification']['resampled'] = bool(report['images'])

def run(source, output, report_path, resume=False):
    source, output = source.resolve(), output.resolve()
    if (output.exists() and not resume) or source == output or source in output.parents:
        raise ValueError('output must be absent and outside the source tree')
    manifest = json.loads((source/'vita-540p-assets.json').read_bytes())
    if manifest['method'] != 'native-540p-encoded-unorm-v2':
        raise ValueError('expected encoded UNORM pack; run colour migration first')
    if 'runtime_image_repair' in manifest:
        raise ValueError('source already repaired; use the preserved before-r2 pack to reproduce')
    strips = strip_names(ROOT/'knife/knife/data/exe_tables_overseas.bin')
    spec = importlib.util.spec_from_file_location('native_color', ROOT/'tools/migrate-vita-native-color.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    if not output.exists():
        output.mkdir(parents=True)
        for path in source.rglob('*'):
            dest = output/path.relative_to(source)
            if path.is_dir(): dest.mkdir(exist_ok=True)
            elif path.is_file(): os.link(path, dest)
    elif (output/'vita-540p-assets.json').read_bytes() != (source/'vita-540p-assets.json').read_bytes():
        raise ValueError('resume requires the uncommitted source manifest')
    report = dict(source=str(source), output=str(output),
                  source_manifest_sha256=file_sha(source/'vita-540p-assets.json'),
                  language_strips=len(strips), changed_files=[], images=[], archives={})
    for archive in ARCHIVES:
        hed = (source/f'{archive}.hed').read_bytes()
        nam_path = source/f'{archive}.nam'
        nam = nam_path.read_bytes() if nam_path.is_file() else None
        rows = list(struct.iter_unpack('<IHH', hed))
        end = next(i for i, row in enumerate(rows) if row[0] == 0xffffffff)
        temp = output/f'{archive}.mrg.partial'
        # Resume only an atomically committed archive pair. Reconstruct the
        # report from both byte streams, then run the full runtime verifier.
        if resume and not temp.exists() and (output/f'{archive}.hed').read_bytes() != hed:
            new_rows = list(struct.iter_unpack('<IHH', (output/f'{archive}.hed').read_bytes()))
            if len(new_rows) != len(rows): raise ValueError('resume archive table length')
            fixed = 0
            with (source/f'{archive}.mrg').open('rb') as old_file, (output/f'{archive}.mrg').open('rb') as new_file:
                for index, (old_row, new_row) in enumerate(zip(rows[:end], new_rows[:end])):
                    old_file.seek(old_row[0]*SECTOR); old = unpack(old_file.read(old_row[1]*SECTOR))
                    new_file.seek(new_row[0]*SECTOR); new = unpack(new_file.read(new_row[1]*SECTOR))
                    if old[:4] != b'KIMG' or old[:32] == new[:32]: continue
                    name = nam[index*32:(index+1)*32].split(b'\0')[0].split(b'\r')[0].decode() if nam else f'#{index}'
                    _, lw, lh, w, h, codec, _ = struct.unpack_from('<7I', old, 4)
                    _, nlw, nlh, nw, nh, nc, _ = struct.unpack_from('<7I', new, 4)
                    if (lw, lh) != (nlw, nlh) or nc not in (2, 7): raise ValueError('resume image contract')
                    report['images'].append(dict(archive=archive, index=index, name=name,
                        logical=[lw,lh], before=[w,h], physical=[nw,nh], source_codec=codec, encoding=nc,
                        strips=4 if name.split('.')[0].split('_')[0].upper() in strips else 1))
                    fixed += 1
            report['changed_files'].extend([f'{archive}.hed', f'{archive}.mrg'])
            report['archives'][archive] = dict(entries=end, repaired=fixed)
            print(archive, report['archives'][archive], 'resumed', flush=True)
            continue
        fixed, new_hed = 0, bytearray()
        with (source/f'{archive}.mrg').open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mm, temp.open('wb') as target:
            for index, (sector, stored, uncompressed) in enumerate(rows[:end]):
                name = nam[index*32:(index+1)*32].split(b'\0')[0].split(b'\r')[0].decode() if nam else f'#{index}'
                offset = target.tell()//SECTOR
                if sector*SECTOR+stored*SECTOR > len(mm): raise ValueError('archive extent')
                data = mm[sector*SECTOR:(sector+stored)*SECTOR]
                raw = unpack(data) if stored else b''
                converted, info = repair_image(raw, name.rsplit('.', 1)[0], strips, native)
                if info:
                    packed = zlib.compress(converted, 1)
                    data = struct.pack('<4sIII', b'NXCX', len(converted), len(packed), 0)+packed
                    uncompressed = (len(converted)+SECTOR-1)//SECTOR
                    fixed += 1
                    report['images'].append(dict(archive=archive, index=index, **info))
                stored = (len(data)+SECTOR-1)//SECTOR
                if stored > 65535 or uncompressed > 65535: raise ValueError('archive sector overflow')
                new_hed.extend(struct.pack('<IHH', offset, stored, uncompressed))
                target.write(data)
                target.write(b'\0' * ((-len(data)) % SECTOR))
        if fixed:
            temp.replace(output/f'{archive}.mrg')
            new_hed.extend(hed[end*8:])
            (output/f'{archive}.hed.partial').write_bytes(new_hed)
            (output/f'{archive}.hed.partial').replace(output/f'{archive}.hed')
            report['changed_files'].extend([f'{archive}.hed', f'{archive}.mrg'])
        else:
            temp.unlink()
        report['archives'][archive] = dict(entries=end, repaired=fixed)
        print(archive, report['archives'][archive], flush=True)
    for row in manifest['files']:
        if row['path'] in report['changed_files']:
            path = output/row['path']
            row.update(bytes=path.stat().st_size, sha256=file_sha(path))
    update_archive_summary(manifest, report, output)
    manifest['runtime_image_repair'] = dict(source_manifest_sha256=report['source_manifest_sha256'],
        images=len(report['images']), method='mofa-960x540-fit-preserve-logical',
        language_decode='selected-PNG-rows', unorm_reencoding='lossless-PNG-no-additional-Alter')
    marker = output/'vita-540p-assets.json'
    marker.with_suffix('.partial').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    marker.with_suffix('.partial').replace(marker)
    report['changed_files'].append(marker.name)
    report['manifest_sha256'] = file_sha(marker)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Repaired', len(report['images']), 'images; manifest', report['manifest_sha256'], flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--resume', action='store_true', help='resume an interrupted output before its final manifest commit')
    args = parser.parse_args()
    run(args.source, args.output, args.report, args.resume)
