"""Build the Tsukihime JA/ZC pack in a fresh directory; never edit the source.

Requires Pillow and fontTools. Original save IDs 0/2 map to physical slots 0/1.
Archive entry numbers never move. Each retained language stripe is pixel exact.
"""
import argparse
import collections
import hashlib
import importlib.util
import io
import json
import mmap
import os
import re
import struct
import sys
import zlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import vita_image_metadata as metadata

ROOT = Path(__file__).resolve().parents[1]
KEEP = (0, 2)
OLD_FONT_DIRS = {f'{lang}{suffix}' for lang in ('ja','en','zc','zt') for suffix in ('','2','3')}
spec = importlib.util.spec_from_file_location('repair', Path(__file__).with_name('repair-tsukihime-assets.py'))
repair = importlib.util.module_from_spec(spec); spec.loader.exec_module(repair)

def commit(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.partial')
    temp.write_bytes(data); temp.replace(path)

def json_bytes(value): return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()

def png_kimg(image, logical, encoding=7):
    out = io.BytesIO(); image.save(out, 'PNG', optimize=True, compress_level=6)
    payload = out.getvalue()
    return struct.pack('<4s7I', b'KIMG', 1, *logical, *image.size, encoding, len(payload)) + payload

def select_strip(raw):
    magic, v, lw, lh, w, h, codec, length = struct.unpack_from('<4s7I', raw)
    assert magic == b'KIMG' and v == 1 and codec in (1,2,7,9) and min(h,lh)>=4, (lw,lh,w,h,codec)
    if codec==9:
        spec=importlib.util.spec_from_file_location('native_color',ROOT/'tools/migrate-vita-native-color.py')
        native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
        original,size,_,_=native.gxt_decode(raw[32:32+length]);assert size==(w,h)
        original=original.crop((0,0,w,h))
    else:
        original=Image.open(io.BytesIO(raw[32:32+length])).convert('RGBA')
    with original:
        original = original.convert('RGBA')
        rows=h//4
        out = Image.new('RGBA', (w, rows*2))
        for slot, lang in enumerate(KEEP):
            top=lang*h//4
            out.paste(original.crop((0,top,w,top+rows)), (0,slot*rows))
        data = png_kimg(out, (lw, lh//4*2), 7 if codec in (7,9) else 2)
        with Image.open(io.BytesIO(data[32:])) as check:
            for slot, lang in enumerate(KEEP):
                top=lang*h//4
                assert check.crop((0,slot*rows,w,(slot+1)*rows)).tobytes() == original.crop((0,top,w,top+rows)).tobytes()
        return data

def unpack_mzp(data):
    assert data[:6] == b'mrgd00'
    count, = struct.unpack_from('<H',data,6); base = 8+count*8; out=[]
    for i in range(count):
        sector, off, sectors, low = struct.unpack_from('<4H',data,8+i*8)
        start = base+(sector<<11)+(off&4095)+((off>>12)<<27)
        size = low if sectors == 0 else ((sectors-1)//32)*65536+low
        assert start+size <= len(data)
        out.append(data[start:start+size])
    return out

def pack_mzp(blocks):
    header = bytearray(b'mrgd00'+struct.pack('<H',len(blocks))+bytes(len(blocks)*8)); payload=bytearray()
    for i, block in enumerate(blocks):
        off, size = len(payload), len(block); large,low=divmod(size,65536)
        assert off < 134217728 and size < 134217728
        struct.pack_into('<4H',header,8+i*8,off//2048,off%2048,large*32+1 if large else 0,low)
        payload.extend(block)
    out=bytes(header+payload); assert unpack_mzp(out) == blocks
    return out

def select_script(raw):
    blocks=unpack_mzp(raw); assert len(blocks)==10
    return pack_mzp([blocks[2*k+j] for k in KEEP for j in (0,1)])

def sysmes_rows(raw):
    languages,count=struct.unpack_from('<II',raw); out=[]
    for slot in range(languages):
        table,=struct.unpack_from('<Q',raw,16+8*slot); rows=[]
        for i in range(count):
            off,=struct.unpack_from('<Q',raw,table+8*i); rows.append(raw[off:raw.index(0,off)])
        out.append(rows)
    return out

def pack_sysmes(header, rows):
    n,count=len(rows),len(rows[0]);out=bytearray(header[:16]+bytes(n*8+n*count*8))
    struct.pack_into('<II',out,0,n,count)
    for slot, row in enumerate(rows):
        assert len(row)==count
        table=16+n*8+slot*count*8;struct.pack_into('<Q',out,16+slot*8,table)
        for i,value in enumerate(row):
            struct.pack_into('<Q',out,table+8*i,len(out));out.extend(value+b'\0')
    return bytes(out)

def select_sysmes(raw):
    rows=sysmes_rows(raw);assert len(rows)==4
    out=pack_sysmes(raw,[rows[i] for i in KEEP]);assert sysmes_rows(out)==[rows[i] for i in KEEP]
    return out

def select_guide(raw):
    count,=struct.unpack_from('<H',raw)
    assert len(raw)>=8+count*8*4
    return raw[:8]+b''.join(raw[8+i*count*8:8+(i+1)*count*8] for i in KEEP)

def remove_loose(name):
    p=Path(name)
    return p.parts[0] in OLD_FONT_DIRS or bool(re.search(r'_(en|zt)\.(mp4|tga)$',p.name,re.I))

def tombstone_name():
    return b'NOFILE.EXISTS'.ljust(30,b'\0')+b'\r\n'

def language_plate(raw, font_path):
    # Three original states, 256 px apart; two rows 88 px apart. Both atlases
    # deliberately show the same self-named language labels in the new font.
    assert struct.unpack_from('<4I',raw,8)==(760,344,760,344)
    im=Image.new('RGBA',(760,168));draw=ImageDraw.Draw(im);font=ImageFont.truetype(str(font_path),42)
    for row,text in enumerate(('简体中文','日本語')):
        for col,color in enumerate(((255,255,255,255),(0,220,255,255),(130,255,255,255))):
            x,y=col*256,row*88
            draw.ellipse((x+15,y+34,x+27,y+46),outline=color,width=2)
            draw.text((x+40,y+40),text,font=font,anchor='lm',fill=color)
    return png_kimg(im,im.size)

def make_fonts(source, output, primary, deps):
    if deps:sys.path.insert(0,str(deps.resolve()))
    from fontTools import subset
    from fontTools.ttLib import TTFont
    main=TTFont(primary);fallback_source=source/'zc/arshanghaisonggbpro_lt.otf'
    options=subset.Options();options.recalc_timestamp=False
    fallback=subset.load_font(str(fallback_source),options)
    sub=subset.Subsetter(options=options);sub.populate(unicodes=[0x55de,0x89cd]);sub.subset(fallback)
    buffer=io.BytesIO();subset.save_font(fallback,buffer,options)
    commit(output/'fonts/main.ttf',primary.read_bytes());commit(output/'fonts/fallback.otf',buffer.getvalue())
    assert set(TTFont(output/'fonts/fallback.otf').getBestCmap())=={0x55de,0x89cd}
    return dict(primary=dict(path='fonts/main.ttf',sha256=repair.file_sha(primary),bytes=primary.stat().st_size,
        internal_name=main['name'].getDebugName(1)),fallback=dict(path='fonts/fallback.otf',codepoints=['U+55DE','U+89CD'],
        source_sha256=repair.file_sha(fallback_source),bytes=len(buffer.getvalue()),sha256=repair.file_sha(output/'fonts/fallback.otf')))

def run(source, output, primary, report_path, deps=None, resume=False):
    source,output,primary=source.resolve(),output.resolve(),primary.resolve()
    assert source != output and source not in output.parents and output not in source.parents
    marker=(source/'vita-540p-assets.json').read_bytes();manifest=json.loads(marker)
    assert manifest['languages']==['ja','en','zc','zt'] and 'runtime_image_repair' in manifest
    report=dict(source_manifest_sha256=hashlib.sha256(marker).hexdigest(),hardware_verified=False,
        kept_ids=list(KEEP),menu_ids=[2,0],default_id=2,archives={},removed_files=[],rewrites=[],lossless_stripes_verified=0)
    if output.exists():
        assert resume, 'output exists; explicit --resume required'
        previous=json.loads((output/'vita-540p-assets.json').read_bytes())
        assert previous['bilingual']['source_manifest_sha256']==report['source_manifest_sha256']
    else: output.mkdir(parents=True)
    for row in manifest['files']:
        name=row['path'];p=source/name
        assert p.stat().st_size==row['bytes'] and repair.file_sha(p)==row['sha256'],name
        if remove_loose(name):report['removed_files'].append(name);continue
        dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():os.link(p,dest)
    fonts=make_fonts(source,output,primary,deps)
    strips=repair.strip_names(ROOT/'knife/knife/data/exe_tables_overseas.bin')
    for archive in repair.ARCHIVES:
        hed=(source/f'{archive}.hed').read_bytes();names_path=source/f'{archive}.nam'
        names=bytearray(names_path.read_bytes()) if names_path.exists() else None
        rows=list(struct.iter_unpack('<IHH',hed));end=next(i for i,row in enumerate(rows) if row[0]==0xffffffff)
        new_hed=bytearray();changed=0;removed=[];pixels=objects=atlases=0;codecs=collections.Counter()
        temp=output/f'{archive}.mrg.partial'
        with (source/f'{archive}.mrg').open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm,temp.open('wb') as out:
            for i,(sector,stored,unpacked) in enumerate(rows[:end]):
                name=bytes(names[i*32:(i+1)*32]).split(b'\0')[0].split(b'\r')[0].decode() if names else f'#{i}'
                data=mm[sector*2048:(sector+stored)*2048];raw=repair.unpack(data) if stored else b'';converted=raw
                if re.search(r'_(EN|ZT)\.',name,re.I):
                    removed.append(dict(index=i,name=name));converted=b'';data=b'';unpacked=0
                    names[i*32:(i+1)*32]=tombstone_name();changed+=1
                elif raw[:4]==b'KIMG' and name.split('.')[0].split('_')[0].upper() in strips:
                    converted=select_strip(raw);report['lossless_stripes_verified']+=2
                    report['rewrites'].append(dict(archive=archive,index=i,name=name,operation='four-stripes-to-ja-zc'))
                elif raw[:4]==b'KATL' and name.upper().startswith('CONF_PARTS_'):
                    pos=12;items=[]
                    for j in range(struct.unpack_from('<I',raw,8)[0]):
                        nl,il=struct.unpack_from('<II',raw,pos);pos+=8;label=raw[pos:pos+nl];pos+=nl;image=raw[pos:pos+il];pos+=il
                        if j==19:image=language_plate(image,primary)
                        items.append(struct.pack('<II',nl,len(image))+label+image)
                    assert pos==len(raw);converted=raw[:12]+b''.join(items)
                elif name.upper().startswith('SYSMES_TEXT_ML.'):
                    converted=select_sysmes(raw)
                elif name.upper().startswith('CONTHELP_TXT_UV.'):
                    converted=select_guide(raw)
                if converted != raw and converted:
                    compressed=zlib.compress(converted,1);data=struct.pack('<4sIII',b'NXCX',len(converted),len(compressed),0)+compressed
                    unpacked=(len(converted)+2047)//2048;changed+=1
                for _,info in metadata.images_in(converted):
                    objects+=1;pixels+=info['physical'][0]*info['physical'][1];codecs[info['codec']]+=1
                atlases+=converted[:4]==b'KATL'
                st=(len(data)+2047)//2048;assert max(st,unpacked)<=65535
                new_hed.extend(struct.pack('<IHH',out.tell()//2048,st,unpacked));out.write(data);out.write(bytes((-len(data))%2048))
        if changed:
            temp.replace(output/f'{archive}.mrg');commit(output/f'{archive}.hed',bytes(new_hed)+hed[end*8:])
            if names is not None:
                assert len(names)==names_path.stat().st_size
                commit(output/f'{archive}.nam',bytes(names))
        else:temp.unlink()
        summary=dict(name=archive,entries=end,bytes=(output/f'{archive}.mrg').stat().st_size,
                     pixels=pixels,images=objects,atlases=atlases,codecs=dict(codecs))
        report['archives'][archive]=dict(changed=changed,removed=removed,**summary)
        print(archive,changed,'changed;',len(removed),'removed;',objects,'images',flush=True)
    old_script=(source/'script_text.mrg').read_bytes();new_script=select_script(old_script);commit(output/'script_text.mrg',new_script)
    report['script']=dict(old_blocks=10,blocks=4,text_bytes_unchanged=True,
        retained_pair_sha256=[hashlib.sha256(block).hexdigest() for block in unpack_mzp(new_script)])
    commit(output/'language-profile.txt',b'knife-languages-v1\n0\tja\tJapanese\n2\tzc\tSimplified Chinese\n')
    commit(output/'font-profile.json',json_bytes(fonts))
    manifest['languages']=['ja','zc'];manifest['language_ids']=[0,2];manifest['default_language_id']=2
    manifest['bilingual']=dict(source_manifest_sha256=report['source_manifest_sha256'],save_ids_preserved=True,
        slot_to_language_id=[0,2],menu_ids=[2,0],font=fonts,lossless_stripes_verified=report['lossless_stripes_verified'])
    manifest['archives']=[{**a,**{k:v for k,v in report['archives'][a['name']].items() if k in ('bytes','pixels','images','atlases','codecs')}} for a in manifest['archives']]
    manifest['files']=[dict(path=p.relative_to(output).as_posix(),bytes=p.stat().st_size,sha256=repair.file_sha(p))
        for p in sorted(output.rglob('*')) if p.is_file() and p.name!='vita-540p-assets.json']
    report['fonts']=fonts;report['files']=len(manifest['files']);report['bytes']=sum(row['bytes'] for row in manifest['files'])
    commit(output/'vita-540p-assets.json',json_bytes(manifest))
    report['manifest_sha256']=repair.file_sha(output/'vita-540p-assets.json')
    commit(report_path,json_bytes(report));print('JA/ZC pack complete:',report['manifest_sha256'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--font',type=Path,required=True);p.add_argument('--fonttools-deps',type=Path);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--resume',action='store_true',help='rebuild only a prior output derived from this exact source manifest')
    a=p.parse_args();run(a.source,a.output,a.font,a.report,a.fonttools_deps,a.resume)
