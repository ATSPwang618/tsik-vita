//! Compact UI image containers, independent of GPU texture residency.
use anyhow::{Result, ensure};
use knife_core::format::compact;

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
