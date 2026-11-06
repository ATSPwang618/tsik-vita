//! Read-only audit of the shipped blocks; never re-encode or extract artwork.
#![allow(dead_code)]
#[path="../../../../knife/knife-platform-vita/src/gxt.rs"] mod gxt;
#[path="../../../../knife/knife-render/src/vita_pixels.rs"] mod lossless;
use anyhow::{Context,Result,ensure};
use knife_core::format::{archive::{Archive,ArchiveLimits},compact,gxt_decode};
use std::{path::Path,collections::BTreeMap};
fn main()->Result<()> {
    let root=std::env::args().nth(1).context("assets directory")?;
    let mut formats=BTreeMap::<String,u64>::new();
    let (mut images,mut opaque,mut partial,mut rgba_pages,mut rgb_pages,mut rgba_slices,mut rgb_slices)=(0u64,0u64,0u64,0u64,0u64,0u64,0u64);
    let mut opaque_dxt5=0u64;
    let (mut palette_images,mut palette_rgba_pages,mut palette_index_pages)=(0u64,0u64,0u64);
    let (mut selected,mut selected_opaque,mut selected_alpha,mut selected_semi)=(0u64,0u64,0u64,0u64);
    let align=|v:u64,n:u64| v.div_ceil(n)*n;
    for name in ["w_allui","w_allpaccg","w_allpac","w_allpacml","allpachd","parts"] {
        let archive=Archive::open_file_with_limits(Path::new(&root),name,ArchiveLimits::VITA)?;
        for (index,entry) in archive.entries().iter().enumerate() {
            if entry.stored_sectors==0 {continue;}
            let raw=archive.read(index)?;
            let members=if compact::is_atlas(&raw){compact::parse_atlas(&raw)?}
                else if compact::is_compact(&raw){vec![(entry.name.as_str(),raw.as_slice())]}else{continue;};
            for (label,bytes) in members {
                let image=compact::parse(bytes)?;
                if image.encoding!=compact::Encoding::GxtNativeUnorm {continue;}
                let gpu=gxt::GxtTexture::parse(image.payload)?;
                *formats.entry(format!("{:?}",gpu.format)).or_default()+=1;
                let (w,h,pixels)=gxt_decode::rgba8(image.payload,4*960*1080)?;
                ensure!([w,h]==image.size,"{name}/{label}: dimensions");
                images+=1;
                let is_opaque=lossless::opaque_rgba(w,h,&pixels);
                if lossless::indexed_rgba(w,h,&pixels) {
                    selected+=1;
                    if is_opaque { selected_opaque+=1; } else {
                        selected_alpha+=1;
                        if pixels.chunks_exact(4).any(|p|p[3]>0 && p[3]<255) {selected_semi+=1;}
                    }
                }
                let mut colors=std::collections::HashSet::with_capacity(257);
                for p in pixels.chunks_exact(4) {
                    colors.insert(u32::from_le_bytes(p.try_into().unwrap()));
                    if colors.len()>256 {break;}
                }
                if colors.len()<=256 {
                    let pitch=u64::from((w+7)&!7)*u64::from(h);
                    let before=align(pitch*4,256*1024);
                    let after=align(align(pitch,64)+1024,256*1024);
                    if after<before {
                        palette_images+=1;palette_rgba_pages+=before;palette_index_pages+=after;
                        println!("PALETTE {name}/{label} {w}x{h} colors={} old_page={before} indexed_page={after}",colors.len());
                    }
                }
                if is_opaque {
                    opaque+=1;
                    let pitch=u64::from((w+7)&!7)*u64::from(h);
                    rgba_pages+=align(pitch*4,256*1024);rgb_pages+=align(pitch*3,256*1024);
                    rgba_slices+=align(pitch*4,64);rgb_slices+=align(pitch*3,64);
                    opaque_dxt5+=u64::from(gpu.format==gxt::GxtFormat::Dxt5);
                }else{partial+=1;}
                if entry.name.to_uppercase().starts_with("AOK_A_21_00_N01_03_03.") {
                    println!("device_failure_image {w}x{h} opaque={is_opaque}; alpha must stay exact");
                }
            }
        }
        println!("{name}: scanned={images} opaque={opaque} alpha={partial}");
    }
    println!("AUDIT images={images} opaque={opaque} alpha={partial} formats={formats:?} opaque_dxt5={opaque_dxt5}");
    println!("PALETTE_AUDIT exact_256_color_candidates={palette_images} old_pages_sum={palette_rgba_pages} indexed_pages_sum={palette_index_pages}");
    println!("SELECTED candidates={selected} opaque={selected_opaque} alpha={selected_alpha} semitransparent={selected_semi}");
    println!("POTENTIAL if-each-opaque-image-is-CPU-baked-once: old_page_sum={rgba_pages} new_page_sum={rgb_pages} saved_pages_sum={} old_slice_sum={rgba_slices} new_slice_sum={rgb_slices} saved_slices_sum={}",rgba_pages-rgb_pages,rgba_slices-rgb_slices);
    println!("These totals are not simultaneous resident memory. Original direct compressed GXT remains unchanged. No device verification.");
    Ok(())
}
