#!/usr/bin/env python3
"""Read-only PNG/JPEG RGBA audit, including each original JA/ZC language slot.

Only exact colour identities qualify. This measures a possible decoded/baked
upload, not the already compressed GXT path or simultaneous resident memory.
"""
import argparse
import collections
import importlib.util
import io
import json
import mmap
import struct
from pathlib import Path
from PIL import Image
import numpy as np

spec=importlib.util.spec_from_file_location('repair',Path(__file__).with_name('repair-tsukihime-assets.py'))
repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)

def audit(root):
    strips=repair.strip_names(repair.ROOT/'knife/knife/data/exe_tables_overseas.bin')
    counts=collections.Counter(); examples=[]
    for archive in repair.ARCHIVES:
        hed=(root/f'{archive}.hed').read_bytes()
        nam_path=root/f'{archive}.nam';nam=nam_path.read_bytes() if nam_path.is_file() else None
        with (root/f'{archive}.mrg').open('rb') as source,mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as mm:
            for i,(sector,stored,_) in enumerate(struct.iter_unpack('<IHH',hed)):
                if sector==0xffffffff: break
                if not stored: continue
                raw=repair.unpack(mm[sector*2048:(sector+stored)*2048])
                entry=nam[i*32:(i+1)*32].split(b'\0')[0].split(b'\r')[0].decode() if nam else f'#{i}'
                members=[]
                if raw[:4]==b'KATL':
                    n,=struct.unpack_from('<I',raw,8); pos=12
                    for _ in range(n):
                        nl,il=struct.unpack_from('<II',raw,pos);pos+=8
                        name=raw[pos:pos+nl].decode();pos+=nl
                        members.append((name,raw[pos:pos+il],1));pos+=il
                    if pos!=len(raw): raise ValueError('atlas extent')
                elif raw[:4]==b'KIMG':
                    name=entry.rsplit('.',1)[0]
                    members=[(name,raw,2 if name.split('_')[0].upper() in strips else 1)]
                for name,data,slots in members:
                    _,_,_,w,h,codec,length=struct.unpack_from('<7I',data,4)
                    if codec==9: continue
                    if codec not in (1,2,7): raise ValueError(f'unsupported codec {codec}')
                    with Image.open(io.BytesIO(data[32:32+length])) as src:
                        rgba=np.asarray(src.convert('RGBA'))
                    if rgba.shape!=(h,w,4) or h%slots: raise ValueError('layout mismatch')
                    for slot in range(slots):
                        px=rgba[slot*(h//slots):(slot+1)*(h//slots)]
                        counts['decoded_slots']+=1
                        opaque=bool(np.all(px[:,:,3]==255)); counts['opaque' if opaque else 'alpha']+=1
                        semi=bool(np.any((px[:,:,3]>0)&(px[:,:,3]<255)));counts['semitransparent']+=semi
                        # Count every RGBA bit, including RGB under transparent alpha.
                        colors=int(np.unique(px.copy().view('<u4')).size)
                        if colors<=256:
                            counts['exact_palette_slots']+=1
                            pitch=((w+7)&~7)*(h//slots)
                            indexed=((pitch+63)&~63)+1024
                            before=(pitch*(3 if opaque else 4)+262143)//262144*262144
                            after=(indexed+262143)//262144*262144
                            if after<before:
                                counts['selected_palette_slots']+=1
                                counts['selected_palette_opaque' if opaque else 'selected_palette_alpha']+=1
                                counts['selected_palette_semitransparent']+=semi
                                if len(examples)<12: examples.append(dict(archive=archive,name=name,language_slot=slot,
                                    physical=[w,h//slots],colors=colors,opaque=opaque,semitransparent=semi,
                                    old_page_bytes=before,indexed_page_bytes=after))
        print(archive,dict(counts),flush=True)
    return dict(status='PASS',scope='all PNG/JPEG decoded RGBA and JA/ZC slots; exact colours, no rewriting',
        hardware_verified=False,counts=dict(counts),examples=examples)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets',type=Path);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();result=audit(args.assets)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
