//! Check shipped pixels through the same GXT parser and CPU fallback as Vita.
#![allow(dead_code)]
#[path="../../../../knife/knife-platform-vita/src/gxt.rs"] mod gxt;
use anyhow::{Context, Result, ensure};
use knife_core::format::{archive::{Archive, ArchiveLimits}, compact, gxt_decode};
use std::path::Path;

fn main() -> Result<()> {
    let root = std::env::args().nth(1).context("assets directory")?;
    let export = std::env::args().nth(2);
    let mut count = 0usize;
    let mut pixels = 0u64;
    let mut max_rgba = 0usize;
    for name in ["w_allui", "w_allpaccg", "w_allpac", "w_allpacml", "allpachd", "parts"] {
        let archive = Archive::open_file_with_limits(Path::new(&root), name, ArchiveLimits::VITA)?;
        for (index, entry) in archive.entries().iter().enumerate() {
            if entry.stored_sectors == 0 { continue; }
            let data = archive.read(index).with_context(|| format!("{name}[{index}]"))?;
            let images = if compact::is_atlas(&data) { compact::parse_atlas(&data)? }
                else if compact::is_compact(&data) { vec![(entry.name.as_str(), data.as_slice())] }
                else { continue; };
            for (label, data) in images {
                let image = compact::parse(data)?;
                if image.encoding != compact::Encoding::GxtNativeUnorm { continue; }
                let gpu = gxt::GxtTexture::parse(image.payload)
                    .with_context(|| format!("GPU {name}[{index}] {label}"))?;
                let (w, h, rgba) = gxt_decode::rgba8(image.payload, 4*960*1080)
                    .with_context(|| format!("CPU {name}[{index}] {label}"))?;
                ensure!([w,h] == image.size && (w,h) == (u32::from(gpu.width),u32::from(gpu.height)), "GPU/CPU dimensions");
                ensure!(rgba.len() == w as usize*h as usize*4, "RGBA layout");
                count += 1; pixels += u64::from(w)*u64::from(h); max_rgba = max_rgba.max(rgba.len());
                if name == "w_allpaccg" && entry.name.starts_with("IMG3864.") {
                    if let Some(ref folder) = export {
                        std::fs::write(Path::new(folder).join("forest-gxt.rgba"), &rgba)?;
                        std::fs::write(Path::new(folder).join("forest-gxt-size.txt"), format!("{w} {h}\n"))?;
                    }
                }
            }
        }
        println!("{name}: cumulative {count} GPU headers and CPU decodes; {pixels} pixels; max RGBA {max_rgba} bytes");
    }
    println!("PASS; hardware_verified=false");
    Ok(())
}
