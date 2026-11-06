//! Compact UI image containers, independent of GPU texture residency.
use anyhow::{Result, ensure};
use knife_core::format::compact;

/// The compact pack repacks 72 consecutive original cells into each 6x12 page.
/// Logical cell metrics stay 154x88; physical cells are 116x66 (115x65.5 on Vita).
/// Retain the original single-sheet path for older packs and desktop romfs.
pub fn cg_thumb_source(id: u32, paged: bool) -> (String, [f32; 4]) {
    let (name, local, cols) = if paged {
        (format!("cg_thumb_page_{}", id / 72), id % 72, 6)
    } else { ("cg_thumb_all".to_string(), id, 36) };
    (name, [(local % cols) as f32 * 154.0, (local / cols) as f32 * 88.0, 154.0, 87.0])
}

pub fn compact_images<'a>(stem: &str, data: &'a [u8]) -> Result<Vec<(&'a str, &'a [u8])>> {
    if compact::is_atlas(data) {
        return compact::parse_atlas(data);
    }
    // The CG sheet is a single image. Conversion to KIMG retains its layout
    // dimensions but has no BNTX member-name table, so restore its UI binding.
    let stem = stem.to_ascii_uppercase();
    let base = stem.rsplit_once('_')
        .filter(|(_, language)| matches!(*language, "JA" | "EN" | "ZC" | "ZT"))
        .map_or(stem.as_str(), |(base, _)| base);
    ensure!(base == "CG_THUMB_PARTS", "unknown single-image UI resource: {stem}");
    let image = compact::parse(data)?;
    let end = compact::HEADER_SIZE + image.payload.len();
    Ok(vec![("cg_thumb_all", &data[..end])])
}
