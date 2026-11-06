//! Offline check of the actual R4 UI archive and title/menu button alpha cells.
//! This uses production archive/KATL/GXT parsers, not a GPU pixel simulation.
#![allow(dead_code)]
#[path="../../../../knife/knife-platform-vita/src/gxt.rs"] mod gxt;
use anyhow::{Context, Result, ensure};
use knife_core::format::{archive::{Archive, ArchiveLimits}, compact, gxt_decode};
use std::path::Path;

fn main() -> Result<()> {
    let root = std::env::args().nth(1).context("assets directory")?;
    let archive = Archive::open_file_with_limits(Path::new(&root), "w_allui", ArchiveLimits::VITA)?;
    let (mut atlases, mut images, mut compressed, mut cells, mut old_rejections) = (0, 0, 0, 0, 0);
    for (index, entry) in archive.entries().iter().enumerate() {
        if entry.stored_sectors == 0 { continue; }
        let data = archive.read(index)?;
        if !compact::is_atlas(&data) { continue; }
        atlases += 1;
        for (label, data) in compact::parse_atlas(&data)? {
            let image = compact::parse(data)?;
            let [w, h] = image.size;
            images += 1;
            if image.encoding != compact::Encoding::GxtNativeUnorm {
                ensure!(w <= 960 && h <= 1080, "PNG/JPEG axis limit: {} / {label}", entry.name);
                continue;
            }
            compressed += 1;
            if w > 960 || h > 1080 {
                old_rejections += 1;
                println!("OLD_REJECTION {} / {label}: {w}x{h}", entry.name);
            }
            ensure!(w <= 2048 && h <= 2048 && u64::from(w)*u64::from(h) <= 960*1080,
                "R4 GXT limits: {} / {label}", entry.name);
            let gpu = gxt::GxtTexture::parse(image.payload)?;
            let (dw, dh, pixels) = gxt_decode::rgba8(image.payload, 4*960*1080)?;
            ensure!([dw, dh] == image.size && [gpu.width as u32, gpu.height as u32] == image.size,
                "GPU/CPU dimensions: {} / {label}", entry.name);
            // The game's real UV cells, including normal/focus/selected states.
            let rows: Vec<[u32; 4]> = if label == "titlemenu" {
                [24, 112, 200, 288, 376].into_iter().flat_map(|y|
                    (0..3).map(move |col| [24 + col*312, y, 296, 72])).collect()
            } else if label == "menu_btn_ja" && entry.name.starts_with("MENU_PARTS_") {
                (0..5).flat_map(|row| (0..3).map(move |col|
                    [24 + col*240, 24 + row*104, 224, 88])).collect()
            } else { Vec::new() };
            for [x, y, width, height] in rows {
                ensure!(x + width <= image.logical[0] && y + height <= image.logical[1], "button UV bounds");
                let [x0, y0, x1, y1] = [x*w/image.logical[0], y*h/image.logical[1],
                    (x+width)*w/image.logical[0], (y+height)*h/image.logical[1]];
                let visible = (y0..y1).flat_map(|py| (x0..x1).map(move |px| (py*w+px) as usize))
                    .filter(|&p| pixels[p*4+3] > 16).count();
                ensure!(visible > 8, "empty button cell: {} / {label} {x},{y} {width}x{height}", entry.name);
                cells += 1;
            }
        }
    }
    ensure!(cells == 60, "all five title/menu buttons, three states, both languages");
    println!("PASS atlases={atlases} members={images} gxt_decodes={compressed} visible_button_cells={cells} old_rejections={old_rejections}; hardware_verified=false");
    Ok(())
}
