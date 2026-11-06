#!/usr/bin/env python3
"""Build/check the complete authored GXM inventory with a user-supplied psp2cgc.

No compiler module or commercial game assets are emitted. --check needs only
Python and verifies checked-in bytes; compiling requires the local compiler.
"""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'knife/vita/shaders/effects.cg'
HEADER = ROOT / 'knife/vita/shaders/generated/effects.h'
RECEIPT = ROOT / 'doc/evidence/offline-shaders.json'
BASE = ['sprite', 'noalpha', 'forcealpha', 'fill', 'text', 'rim_text',
        'mono', 'nega', 'transition', 'rule', 'blur', 'alter', 'present',
        'present_srgb', 'ps', 'group_composite', 'sprite_mask']
OPTIONAL = {17: 'ps_fetch', 18: 'ps19_fetch', 19: 'ps19_group_fetch',
            20: 'ps11_fetch', 21: 'ps13_fetch', 22: 'sprite_plain',
            23: 'ps19_plain_fetch', 25: 'ps2_fetch', 26: 'forcealpha_plain',
            28: 'rim_text_batched'}
PLAIN = [0, 1, 2, 3, 6, 7, 9, 16]
FLAGS = ['-O3', '-bestprecision', '-nofastmath', '-nofastint', '-W3',
         '-Werror', '-Wperf', '-Wsuppress=7302', '-nofx', '-nocolor', '-lang', 'en']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory():
    entries = [dict(name='vs_main', entry='vs_main', shader=None,
                    defines=['KNIFE_VERTEX_SHADER=1'])]
    entries += [dict(name='fs_' + name, entry='fs_' + name, shader=i, defines=[])
                for i, name in enumerate(BASE)]
    for i, name in OPTIONAL.items():
        defines = ['KNIFE_RUNTIME_NATIVE_FETCH=1', 'KNIFE_RUNTIME_PS_SPECIALIZED=1'] if 'fetch' in name else []
        entries.append(dict(name='fs_' + name, entry='fs_' + name, shader=i, defines=defines))
    for pair in range(16):
        a, b = (2, 11, 13, 19)[pair // 4], (2, 11, 13, 19)[pair % 4]
        entries.append(dict(name=f'chain_{a}_{b}', entry='fs_ps_chain2_fetch', shader=32 + pair,
                            defines=['KNIFE_RUNTIME_NATIVE_FETCH=1', 'KNIFE_RUNTIME_PS_SPECIALIZED=1',
                                     f'KNIFE_CHAIN_OP_A={a}', f'KNIFE_CHAIN_OP_B={b}']))
    for offset, shader in enumerate(PLAIN):
        entries.append(dict(name=f'plain_{BASE[shader]}', entry='fs_' + BASE[shader], shader=48 + offset,
                            defines=['KNIFE_PLAIN_IMAGE=1'], fallback=shader))
    for mode in range(4):
        entries.append(dict(name=f'text_{mode}', entry='fs_text', shader=56 + mode,
                            defines=[f'KNIFE_TEXT_FILTER={mode // 2}', f'KNIFE_TEXT_BORDER={mode % 2}'], fallback=4))
    for mode in range(3):
        entries.append(dict(name=f'blur_{mode}', entry='fs_blur', shader=60 + mode,
                            defines=[f'KNIFE_BLUR_MODE={mode}'], fallback=10))
    for op in range(1, 25):
        entries.append(dict(name=f'ps_{op}', entry='fs_ps', shader=63 + op,
                            defines=[f'KNIFE_PS_OP={op}'], fallback=14))
        entries.append(dict(name=f'fetch_{op}', entry='fs_ps_fetch', shader=87 + op,
                            defines=[f'KNIFE_PS_OP={op}', 'KNIFE_RUNTIME_NATIVE_FETCH=1'], fallback=17))
    # Basic quad copies/presentation are part of the inventory too.
    for stage in ('v', 'f'):
        entries.append(dict(name=f'quad_{stage}', entry='main', shader=None,
                            defines=[], source=f'knife/vita/shaders/quad_{stage}.cg'))
    return entries


def reflect(data, vertex=False, native=False):
    def u32(at):
        return struct.unpack_from('<I', data, at)[0]
    def relative(at, length):
        start = at + struct.unpack_from('<i', data, at)[0]
        if start < 0 or start + length > u32(8):
            raise ValueError('GXP relative range out of bounds')
        return start
    if len(data) < 156 or len(data) > 1048576 or data[:4] != b'GXP\0':
        raise ValueError('Invalid GXP size/magic')
    size, flags = u32(8), u32(20)
    if size > len(data) or len(data) - size > 3 or any(data[size:]) or bool(flags & 1) == vertex:
        raise ValueError('Invalid GXP padding/stage')
    # Op18 overwrites the destination, so the compiler legitimately eliminates
    # FRAGCOLOR input (0x80). Native register output (0x40) must still remain.
    if bool(flags & 0xc0) != native or (native and not flags & 0x40):
        raise ValueError('Invalid framebuffer fetch flags')
    count = u32(60)
    if not count:
        raise ValueError('Empty instruction stream')
    relative(64, count * 8)
    varying = relative(44, 32)
    if not vertex and data[varying + 10:varying + 12] != bytes([7 if native else 1, 4]):
        raise ValueError('Invalid fragment output ABI')
    params, table = [], relative(40, u32(36) * 16)
    uniforms = {'uTex0Size': 2, 'uTex1Size': 2, 'uSoftLutSize': 2,
                'uQuadHx': 4, 'uQuadHy': 4, 'tu.params': 4, 'tu.params2': 4}
    for i in range(u32(36)):
        at = table + i * 16
        start = relative(at, 1)
        end = data.find(b'\0', start, size)
        if end < start or end - start > 96:
            raise ValueError('Invalid parameter string')
        name = data[start:end].decode('ascii')
        category, kind = data[at + 4] & 15, data[at + 4] >> 4
        components, container = data[at + 5] & 15, data[at + 5] >> 4
        resource = u32(at + 12)
        if category > 2 or u32(at + 8) != 1 or (category != 0 and kind != 0):
            raise ValueError('Unsupported parameter ABI')
        if category == 1 and (uniforms.get(name) != components or container != 14 or resource + components > u32(100)):
            raise ValueError('Uniform contract mismatch: ' + name)
        samplers = {'tex0': 0, 'tex1': 1, 'tex2': 2, 'soft_lut': 3, 'uTexture': 0}
        if category == 2 and (name not in samplers or resource != samplers[name] or (native and resource == 1)):
            raise ValueError('Sampler contract mismatch: ' + name)
        params.append(dict(name=name, category=category, components=components, resource=resource))
    return dict(primary_instructions=count, bytes=len(data), flags=flags, parameters=params)


def compile_one(compiler, spec, source, output):
    vertex = spec['entry'] == 'vs_main' or spec['name'] == 'quad_v'
    args = [str(compiler), '-profile', 'sce_vp_psp2' if vertex else 'sce_fp_psp2',
            '-entry', spec['entry'], *FLAGS, *['-D' + d for d in spec['defines']], '-o', str(output), str(source)]
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(result.stdout.decode(errors='replace'))
    data = output.read_bytes()
    return data, reflect(data, vertex, 'fetch' in spec['entry'])


def emit_array(symbol, data):
    rows = [', '.join(f'0x{x:02x}' for x in data[i:i + 12]) for i in range(0, len(data), 12)]
    return (f'_Alignas(4) static const unsigned char {symbol}[] = {{\n' +
            ''.join('    ' + row + ',\n' for row in rows) + '};\n' +
            f'static const unsigned int {symbol}_size = sizeof({symbol});\n')


def inputs():
    paths = [SOURCE, Path(__file__).resolve(), ROOT / 'knife/knife-render/src/shader.wgsl',
             ROOT / 'knife/vita/shaders/quad_v.cg', ROOT / 'knife/vita/shaders/quad_f.cg']
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in paths}


def check():
    record = json.loads(RECEIPT.read_text())
    if record['inputs'] != inputs() or record['inventory'] != inventory():
        raise ValueError('Offline shader sources/inventory changed; recompile offline shaders')
    for path, sha in record['headers'].items():
        if digest((ROOT / path).read_bytes()) != sha:
            raise ValueError('Offline shader header modified: ' + path)
    print(f"PASS: {len(record['shaders'])} offline programs match exact sources and generated bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--baseline-source', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check()
        return
    if not args.compiler or not args.compiler.is_file():
        parser.error('--compiler must point to your local psp2cgc executable')
    output = ROOT / '.work/vita/offline-shaders'
    output.mkdir(parents=True, exist_ok=True)
    header = ['/* Generated authored GXP; do not edit. */\n#ifndef KNIFE_OFFLINE_EFFECTS_H\n#define KNIFE_OFFLINE_EFFECTS_H\n']
    quad = ['/* Generated authored GXP; do not edit. */\n#ifndef KNIFE_OFFLINE_QUAD_H\n#define KNIFE_OFFLINE_QUAD_H\n']
    records, table = [], []
    for spec in inventory():
        source = ROOT / spec.get('source', 'knife/vita/shaders/effects.cg')
        data, meta = compile_one(args.compiler, spec, source, output / (spec['name'] + '.gxp'))
        repeat, _ = compile_one(args.compiler, spec, source, output / 'repeat.gxp')
        if data != repeat:
            raise ValueError('Nondeterministic compiler output: ' + spec['name'])
        symbol = 'knife_' + ('' if 'source' in spec else 'effects_') + spec['name'] + '_gxp'
        (quad if 'source' in spec else header).append(emit_array(symbol, data))
        if spec['shader'] is not None:
            table.append(f"    case {spec['shader']}: return {symbol};\n")
        record = dict(**spec, sha256=digest(data), repeated_identical=True, **meta)
        if args.baseline_source and 'source' not in spec and 'fallback' not in spec:
            _, before = compile_one(args.compiler, spec, args.baseline_source, output / 'baseline.gxp')
            record['before_primary_instructions'] = before['primary_instructions']
        records.append(record)
        print(spec['name'], meta['primary_instructions'], 'instructions', len(data), 'bytes', flush=True)
    by_id = {r['shader']: r for r in records if r['shader'] is not None}
    for r in records:
        if 'fallback' in r:
            r['before_primary_instructions'] = by_id[r['fallback']].get('before_primary_instructions', by_id[r['fallback']]['primary_instructions'])
    header += ['static inline const void *knife_offline_effect(unsigned int shader) {\n    switch (shader) {\n',
               *table, '    default: return 0;\n    }\n}\n#endif\n']
    quad.append('#endif\n')
    HEADER.write_bytes(''.join(header).encode())
    quad_path = HEADER.with_name('shaders.h')
    quad_path.write_bytes(''.join(quad).encode())
    report = dict(schema=1, inputs=inputs(), inventory=inventory(),
                  baseline_source_sha256=digest(args.baseline_source.read_bytes()) if args.baseline_source else None,
                  compiler_sha256=digest(args.compiler.read_bytes()), flags=FLAGS,
                  compiler_version=subprocess.check_output([str(args.compiler), '-version']).decode(errors='replace').strip(),
                  headers={p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in (HEADER, quad_path)},
                  shaders=records, total_gxp_bytes=sum(r['bytes'] for r in records),
                  hardware_verified=False, pixel_equivalence_verified=False,
                  note='Instruction counts are static program size, not GPU timing; drivers still validate and patch GXP.')
    RECEIPT.write_bytes((json.dumps(report, indent=2) + '\n').encode())
    check()


if __name__ == '__main__':
    main()
