#!/usr/bin/env python3
"""Pre-shrink every oversized story/CG image in the sole existing asset pack.

The limit includes RGBA row padding, regardless of native compression, alpha,
grade or palette eligibility. UI atlases/font/thumbnail pages are not resized.
One temporary archive at a time; a small journal completes interrupted paired
archive/header/manifest replacements. --apply explicitly authorizes replacement.
"""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
import io
import json
import math
import os
from pathlib import Path
import struct
import time

from PIL import Image
from restore_tsukihime_quality import (atlas,kimg,members,native,pack,read_at,rows,sha_file,unpack)
import importlib.util
from vita_image_metadata import image_info,images_in

ROOT=Path(__file__).resolve().parents[1]
ARCHIVES=('w_allpac','w_allpaccg','w_allpacml','allpachd')
LIMIT=512*1024
AXIS=960
SECTOR=2048
POLICY='story-rgba512k-axis960-v1'
spec=importlib.util.spec_from_file_location('repair',ROOT/'tools/repair-tsukihime-assets.py')
repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)

def rgba_charge(w,h):return ((w+7)&~7)*h*4
def native_charge(w,h):return max(4,1<<(w-1).bit_length())*max(4,1<<(h-1).bit_length())

def stable_size(w,h):
    if w<=0 or h<=0:raise ValueError('nonpositive image dimensions')
    factor=min(1.,AXIS/w,AXIS/h,math.sqrt(LIMIT/(w*h*4)))
    nw,nh=max(1,math.floor(w*factor)),max(1,math.floor(h*factor))
    # Pitched rows can exceed the unpitched area estimate by up to seven pixels.
    while rgba_charge(nw,nh)>LIMIT or native_charge(nw,nh)>LIMIT:
        factor*=0.998
        nw,nh=max(1,math.floor(w*factor)),max(1,math.floor(h*factor))
    return nw,nh

def reduce_image(raw,*,strips=1):
    info=image_info(raw);w,h=info['physical']
    if strips not in (1,2) or h%strips:raise ValueError('invalid language strip extent')
    target=stable_size(w,h//strips)
    if target==(w,h//strips):return raw,None
    if info['codec']==9:
        decoded,size,_,_=native().gxt_decode(raw[32:info['envelope_bytes']])
        if size!=(w,h):raise ValueError('GXT decode extent')
        decoded=decoded.crop((0,0,w,h))
    elif info['codec'] in (1,2,7):
        with Image.open(io.BytesIO(raw[32:info['envelope_bytes']])) as src:
            decoded=src.convert('RGBA')
        if decoded.size!=(w,h):raise ValueError('PNG/JPEG decode extent')
    else:raise ValueError('unsupported stable source codec')
    image=Image.new('RGBA',(target[0],target[1]*strips))
    for slot in range(strips):
        piece=decoded.crop((0,slot*(h//strips),w,(slot+1)*(h//strips)))
        image.paste(piece.resize(target,Image.Resampling.LANCZOS),(0,slot*target[1]))
    # Preserve encoded UNORM vs source-sRGB semantics. Existing GXT receives
    # another lossy DXT generation only when resized, as authorized by the user.
    codec=info['codec'] if info['codec'] in (2,7,9) else 2
    result=kimg(image,tuple(info['logical']),codec)
    actual=image_info(result)
    if rgba_charge(*target)>LIMIT or actual['logical']!=info['logical']:
        raise ValueError('stable output contract')
    if codec==9 and actual['gpu_payload_bytes']>LIMIT:raise ValueError('native output contract')
    return result,dict(before=[w,h],physical=list(image.size),logical=info['logical'],strips=strips,
        codec_before=info['codec'],codec_after=codec,
        rgba_pitch_before=rgba_charge(w,h//strips),rgba_pitch_after=rgba_charge(*target))

def process(encoded,name,strip_names):
    raw=unpack(encoded);items=members(raw)
    if not items:return encoded,[],raw
    changed=[];out=[]
    for member,image in items:
        label=member or name.rsplit('.',1)[0]
        strips=2 if raw[:4]==b'KIMG' and label.split('_')[0].upper() in strip_names else 1
        converted,change=reduce_image(image,strips=strips)
        if change:changed.append(dict(member=label,**change))
        out.append((member,converted))
    if not changed:return encoded,[],raw
    value=atlas(out) if raw[:4]==b'KATL' else out[0][1]
    return pack(value),changed,value

def write_json(path,obj):
    temp=path.with_name(path.name+'.writing')
    with temp.open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(obj,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    temp.replace(path)

def complete_transaction(assets):
    journal=assets/'.stable-transaction.json'
    if not journal.exists():return
    state=json.loads(journal.read_text(encoding='utf-8'));archive=state['archive']
    if archive not in ARCHIVES:raise ValueError('invalid transaction archive')
    for suffix in ('mrg','hed'):
        final=assets/f'{archive}.{suffix}';temp=assets/f'{archive}.{suffix}.stable-partial'
        expected=state['files'][suffix]
        candidate=temp if temp.exists() else final
        if candidate.stat().st_size!=expected['bytes'] or sha_file(candidate)!=expected['sha256']:
            raise ValueError(f'incomplete transaction requires inspection: {candidate}')
        if temp.exists():temp.replace(final)
    manifest=json.loads((assets/'vita-540p-assets.json').read_bytes())
    for row in manifest['files']:
        for suffix in ('mrg','hed'):
            if row['path']==f'{archive}.{suffix}':row.update(state['files'][suffix])
    for row in manifest['archives']:
        if row['name']==archive:row.update(state['archive_metadata'])
    stable=manifest.setdefault('stability_preprocessing',dict(policy=POLICY,rgba_pitch_limit=LIMIT,
        axis_limit=AXIS,protected=['w_allui','parts','font','stream'],archives={}))
    if stable['policy']!=POLICY:raise ValueError('different stable policy')
    stable['archives'][archive]=state['summary']
    manifest['statistics'].update(files=len(manifest['files']),bytes=sum(f['bytes'] for f in manifest['files']))
    manifest['statistics'].update(textures=sum(a['textures'] for a in manifest['archives']),
        pixels=sum(a.get('pixels',0) for a in manifest['archives']))
    manifest['verification']['files_hashed']=True
    write_json(assets/'vita-540p-assets.json',manifest)
    journal.unlink()

def rewrite_archive(assets,archive,strip_names,jobs):
    manifest=json.loads((assets/'vita-540p-assets.json').read_bytes())
    old_rows,tail=rows(assets,archive)
    nam_path=assets/f'{archive}.nam';names=nam_path.read_bytes() if nam_path.exists() else None
    temp=assets/f'{archive}.mrg.stable-partial'
    # An unjournaled file was never committed. Validate its exact workspace
    # location before removing only that disposable conversion output.
    if temp.exists():
        if temp.is_symlink() or temp.resolve().parent!=assets.resolve():raise ValueError('unsafe partial path')
        temp.unlink()
    changed=0;examples=[];new_hed=bytearray();seen={};stats=collections.Counter();begin=time.monotonic()
    maximum_before=maximum_after=0
    with (assets/f'{archive}.mrg').open('rb') as current,temp.open('wb') as output:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            for first in range(0,len(old_rows),jobs):
                pending=[]
                for index in range(first,min(first+jobs,len(old_rows))):
                    row=old_rows[index]
                    if not row[1] or row in seen:pending.append((index,row,None));continue
                    name=names[index*32:(index+1)*32].split(b'\0')[0].split(b'\r')[0].decode() if names else f'#{index}'
                    pending.append((index,row,pool.submit(process,read_at(current,row),name,strip_names)))
                for index,row,future in pending:
                    if not row[1]:new_hed.extend(struct.pack('<IHH',*row));continue
                    if row in seen:new_hed.extend(seen[row]);continue
                    try:encoded,changes,raw=future.result()
                    except Exception as error:raise RuntimeError(f'{archive}[{index}] conversion failed') from error
                    for _,info in images_in(raw):
                        stats['images']+=1;stats['pixels']+=math.prod(info['physical']);stats[f'codec_{info["codec"]}']+=1
                    stats['atlases']+=raw[:4]==b'KATL'
                    for change in changes:
                        maximum_before=max(maximum_before,change['rgba_pitch_before'])
                        maximum_after=max(maximum_after,change['rgba_pitch_after'])
                        if len(examples)<16:examples.append(dict(index=index,**change))
                    changed+=len(changes)
                    stored=math.ceil(len(encoded)/SECTOR);unpacked=math.ceil(len(raw)/SECTOR) if changes else row[2]
                    if max(stored,unpacked)>65535:raise ValueError('archive entry sector extent')
                    record=struct.pack('<IHH',output.tell()//SECTOR,stored,unpacked)
                    output.write(encoded);output.write(b'\0'*(-len(encoded)%SECTOR));seen[row]=record;new_hed.extend(record)
                if first%(jobs*64)==0:print(f'{archive}: {first}/{len(old_rows)}, {changed} resized, {output.tell()/1048576:.1f} MiB, {time.monotonic()-begin:.0f}s',flush=True)
        output.flush();os.fsync(output.fileno())
    if not changed:
        temp.unlink();print(archive,'no oversized images',flush=True);return dict(archive=archive,resized=0)
    new_hed.extend(tail);hed_partial=assets/f'{archive}.hed.stable-partial';hed_partial.write_bytes(new_hed)
    before=(assets/f'{archive}.mrg').stat().st_size
    summary=dict(resized=changed,before_archive_bytes=before,after_archive_bytes=temp.stat().st_size,
        max_changed_rgba_pitch_before=maximum_before,max_changed_rgba_pitch_after=maximum_after,
        examples=examples,hardware_verified=False)
    state=dict(archive=archive,summary=summary,files={suffix:dict(bytes=path.stat().st_size,sha256=sha_file(path))
        for suffix,path in [('mrg',temp),('hed',hed_partial)]},
        archive_metadata=dict(bytes=temp.stat().st_size,pixels=stats['pixels'],images=stats['images'],
            atlases=stats['atlases'],textures=stats['images'],
            codecs={k[6:]:v for k,v in stats.items() if k.startswith('codec_')}))
    write_json(assets/'.stable-transaction.json',state);complete_transaction(assets)
    print(f'{archive}: committed {changed} resized; {before} -> {state["files"]["mrg"]["bytes"]} bytes',flush=True)
    return dict(archive=archive,**summary)

def scan(assets,strip_names):
    counts=collections.Counter();by_archive={};maximum=0;violations=[]
    import mmap
    for archive in ARCHIVES:
        archive_rows,_=rows(assets,archive);names=(assets/f'{archive}.nam').read_bytes()
        nimages=nover=0;max_rgba=0
        with (assets/f'{archive}.mrg').open('rb') as source,mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as mm:
            for index,row in enumerate(archive_rows):
                if not row[1]:continue
                raw=unpack(mm[row[0]*SECTOR:(row[0]+row[1])*SECTOR])
                name=names[index*32:(index+1)*32].split(b'\0')[0].split(b'\r')[0].decode()
                for member,info in images_in(raw):
                    label=member or name.rsplit('.',1)[0]
                    n=2 if raw[:4]==b'KIMG' and label.split('_')[0].upper() in strip_names else 1
                    w,h=info['physical'];h//=n
                    charge=rgba_charge(w,h);nimages+=1;max_rgba=max(max_rgba,charge);maximum=max(maximum,charge)
                    if stable_size(w,h)!=(w,h):
                        nover+=1
                        if len(violations)<24:violations.append(dict(archive=archive,index=index,name=label,physical=[w,h],rgba_pitch_bytes=charge))
        by_archive[archive]=dict(images=nimages,oversized=nover,max_rgba_pitch_bytes=max_rgba)
        counts['images']+=nimages;counts['oversized']+=nover
        print(archive,by_archive[archive],flush=True)
    return dict(policy=POLICY,counts=dict(counts),archives=by_archive,max_rgba_pitch_bytes=maximum,
        rgba_pitch_limit=LIMIT,examples=violations,hardware_verified=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets',type=Path,default=ROOT/'dist/TSUKIHIME-RE/assets')
    p.add_argument('--report',type=Path,required=True);p.add_argument('--apply',action='store_true')
    p.add_argument('--jobs',type=int,default=4);args=p.parse_args()
    assets=args.assets.resolve()
    if not 1<=args.jobs<=8:raise ValueError('jobs outside 1..8')
    if args.apply:complete_transaction(assets)
    elif (assets/'.stable-transaction.json').exists():raise ValueError('finish pending transaction with --apply')
    input_manifest_sha=sha_file(assets/'vita-540p-assets.json')
    manifest=json.loads((assets/'vita-540p-assets.json').read_bytes())
    if manifest['method']!='native-540p-encoded-unorm-v2' or manifest['language_ids']!=[0,2]:raise ValueError('unexpected asset contract')
    for row in manifest['files']:
        file=assets/row['path']
        if file.stat().st_size!=row['bytes'] or sha_file(file)!=row['sha256']:raise ValueError(f'input hash mismatch {file}')
    strips=repair.strip_names(ROOT/'knife/knife/data/exe_tables_overseas.bin')
    before=scan(assets,strips);changes=[]
    if args.apply:
        native() # initialize once before concurrent GXT processing
        for archive,stats in before['archives'].items():
            if stats['oversized']:changes.append(rewrite_archive(assets,archive,strips,args.jobs))
        after=scan(assets,strips)
        if after['counts']['oversized']:raise ValueError('oversized images remain')
    else:after=None
    result=dict(status='PASS',applied=args.apply,before=before,after=after,changes=changes,
        input_manifest_sha256=input_manifest_sha,
        output_manifest_sha256=sha_file(assets/'vita-540p-assets.json'),hardware_verified=False)
    args.report.parent.mkdir(parents=True,exist_ok=True);write_json(args.report,result)
    print('PASS',args.report,flush=True)

if __name__=='__main__':main()
