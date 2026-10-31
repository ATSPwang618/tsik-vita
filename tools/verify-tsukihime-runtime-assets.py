#!/usr/bin/env python3
"""Check every pack hash and decode PNG/JPEG with the production C decoder.

Build a host shared library from image_decode.c, jpeg_hw.c and perf_audit.c, then
pass it with --decoder. This verifies offline compatibility, not Vita gameplay.
"""
import argparse
import collections
import ctypes
import hashlib
import importlib.util
import json
import mmap
import struct
from pathlib import Path
import vita_image_metadata as metadata

spec = importlib.util.spec_from_file_location('repair', Path(__file__).with_name('repair-tsukihime-assets.py'))
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)

class Image(ctypes.Structure):
    _fields_ = [('width', ctypes.c_uint32), ('height', ctypes.c_uint32),
                ('stride', ctypes.c_uint32), ('length', ctypes.c_uint32), ('pixels', ctypes.c_void_p)]

def verify(assets, decoder):
    lib = ctypes.CDLL(str(decoder.resolve()))
    args = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(Image)]
    lib.kv_image_decode_bounded.argtypes = args + [ctypes.c_uint32]
    lib.kv_image_decode_strip_bounded.argtypes = args + [ctypes.c_uint32]*3
    lib.kv_image_free.argtypes = [ctypes.POINTER(Image)]
    strips = repair.strip_names(repair.ROOT/'knife/knife/data/exe_tables_overseas.bin')
    marker = (assets/'vita-540p-assets.json').read_bytes()
    manifest = json.loads(marker)
    language_count = len(manifest['languages'])
    if language_count not in (2,4): raise ValueError('unsupported language count')
    if language_count == 2:
        if manifest.get('language_ids') != [0,2]: raise ValueError('expected original JA/ZC IDs')
        if (assets/'language-profile.txt').read_text().splitlines()[1:] != ['0\tja\tJapanese','2\tzc\tSimplified Chinese']:
            raise ValueError('language profile does not match physical slots')
    total_bytes = 0
    for row in manifest['files']:
        path = assets/row['path']
        if path.stat().st_size != row['bytes'] or repair.file_sha(path) != row['sha256']:
            raise ValueError(f'manifest mismatch: {row["path"]}')
        total_bytes += row['bytes']
    counts = collections.Counter()
    archives = {}
    for archive in repair.ARCHIVES:
        hed = (assets/f'{archive}.hed').read_bytes()
        nam_path = assets/f'{archive}.nam'
        nam = nam_path.read_bytes() if nam_path.is_file() else None
        entries = 0
        with (assets/f'{archive}.mrg').open('rb') as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for index, (sector, stored, _) in enumerate(struct.iter_unpack('<IHH', hed)):
                if sector == 0xffffffff: break
                entries += 1
                if not stored: continue
                if (sector+stored)*2048 > len(mm): raise ValueError('archive extent')
                raw = repair.unpack(mm[sector*2048:(sector+stored)*2048])
                entry = nam[index*32:(index+1)*32].split(b'\0')[0].split(b'\r')[0].decode() if nam else f'#{index}'
                # KATL member names own their metadata; they are never language stacks.
                if raw[:4] == b'KATL':
                    images = []
                    count, = struct.unpack_from('<I', raw, 8)
                    pos = 12
                    for _ in range(count):
                        nl, il = struct.unpack_from('<II', raw, pos); pos += 8
                        name = raw[pos:pos+nl].decode(); pos += nl
                        images.append((name, raw[pos:pos+il], 1)); pos += il
                    if pos != len(raw): raise ValueError('KATL envelope')
                elif raw[:4] == b'KIMG':
                    name = entry.rsplit('.', 1)[0]
                    images = [(name, raw, language_count if name.split('_')[0].upper() in strips else 1)]
                else: continue
                for name, data, n in images:
                    try:
                        info = metadata.image_info(data)
                        w, h = info['physical']
                        if w > 960 or h//n > 1080: raise ValueError('runtime dimension bound')
                        codec = info['codec']
                        counts[f'codec_{codec}'] += 1
                        if codec == 9: continue
                        if codec not in (1, 2, 7): raise ValueError('unsupported production codec')
                        payload = data[32:info['envelope_bytes']]
                        buffer = ctypes.create_string_buffer(payload)
                        for k in range(n):
                            image = Image()
                            try:
                                status = (lib.kv_image_decode_strip_bounded(buffer, len(payload), ctypes.byref(image), k, n, 4*960*1080)
                                          if n > 1 else lib.kv_image_decode_bounded(buffer, len(payload), ctypes.byref(image), 4*960*1080))
                                if status != 0: raise ValueError(f'native decode status {status}, language {k}/{n}')
                                if (image.width, image.height, image.length) != (w, h//n, w*(h//n)*4):
                                    raise ValueError('native output layout mismatch')
                                counts['native_decodes'] += 1
                                counts['native_rgba_bytes'] += image.length
                            finally: lib.kv_image_free(ctypes.byref(image))
                        if n > 1: counts['language_images'] += 1
                    except Exception as error:
                        raise ValueError(f'{archive}[{index}] {entry}/{name}: {error}') from error
        archives[archive] = entries
        print(archive, entries, dict(counts), flush=True)
    return dict(status='PASS', scope='offline hashes + production PNG/JPEG decode + bounded GXT metadata',
                hardware_verified=False, asset_manifest_sha256=hashlib.sha256(marker).hexdigest(),
                files=len(manifest['files']), bytes=total_bytes, archives=archives, counts=dict(counts),
                decoder_sha256=repair.file_sha(decoder))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets', type=Path)
    parser.add_argument('--decoder', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.assets, args.decoder)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
