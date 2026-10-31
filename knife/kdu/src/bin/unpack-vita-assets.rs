//! One-off extractor: unpack Vita native-540p asset archives into per-archive
//! original-name files (images decoded to PNG/JPEG, other payloads retained).
//!
//! Usage:
//!   unpack-vita-assets --assets <...\Witch-on-the-Holy-Night-Chengkong-540p-Vita\assets>
//!                       --out    <...\Witch-on-the-Holy-Night-Chengkong-540p-Compact-image-source>
use anyhow::{Context, Result};
use clap::Parser;
use image::ExtendedColorType;
use knife_core::format::{archive::Archive, bntx, bntx_decode, compact, gxt_decode};
use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Parser)]
struct Cli {
    /// assets directory containing <archive>.hed/.nam/.mrg
    #[arg(long)]
    assets: PathBuf,
    /// output root
    #[arg(long)]
    out: PathBuf,
    /// comma separated archives
    #[arg(long, default_value = "allpachdml,allpacml,jallpac,jallpachd,allui,parts")]
    archives: String,
}

#[derive(Default)]
struct Counts {
    entries: u64,
    files: u64,
    skipped: u64,
    errors: u64,
    bytes: u64,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    fs::create_dir_all(&cli.out)?;
    let started = std::time::Instant::now();
    let names: Vec<String> = cli.archives.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
    let mut top = String::new();
    top.push_str("{\n  \"profile\": \"vita-native540-unpack-v1\",\n");
    let _ = writeln!(top, "  \"source\": {},", json_str(&cli.assets.to_string_lossy()));
    let _ = writeln!(top, "  \"generated_at_unix\": {},", unix_now());
    top.push_str("  \"layout\": \"<archive>/<original entry stem>.<png|jpg|...>\",\n  \"archives\": [\n");
    let mut total = Counts::default();
    for (ai, name) in names.iter().enumerate() {
        eprintln!("== {name}");
        let archive = Archive::open(&cli.assets, name)
            .with_context(|| format!("opening archive {name}"))?;
        let out_dir = cli.out.join(name);
        fs::create_dir_all(&out_dir)?;
        let mut counts = Counts::default();
        let mut entries_json = String::new();
        entries_json.push_str("{\n");
        let _ = writeln!(entries_json, "  \"archive\": {},", json_str(name));
        entries_json.push_str("  \"entries\": [\n");
        let mut first = true;
        for (index, entry) in archive.entries().iter().enumerate() {
            counts.entries += 1;
            let label = entry.name.clone();
            let label_upper = label.to_ascii_uppercase();
            if label_upper == "NOFILE.EXISTS" || label_upper.is_empty() && archive.entries()[index].stored_sectors == 0 {
                counts.skipped += 1;
                continue;
            }
            let data = match archive.read(index) {
                Ok(v) => v,
                Err(e) => {
                    counts.errors += 1;
                    eprintln!("  err {index} {label}: {e:#}");
                    continue;
                }
            };
            if data.is_empty() {
                counts.skipped += 1;
                continue;
            }
            let stem = if label.is_empty() { format!("{index:05}") } else { stem_of(&label) };
            if stem.eq_ignore_ascii_case("DUMMY") {
                counts.skipped += 1;
                continue;
            }
            if stem.is_empty() {
                counts.entries += 0;
            }
            let mut record = EntryRecord::new(index, &label);
            if let Err(e) = extract_payload(&data, &out_dir, &stem, index, &mut record, &mut counts) {
                counts.errors += 1;
                eprintln!("  err {index} {label}: {e:#}");
                continue;
            }
            if record.outputs.is_empty() {
                counts.skipped += 1;
                continue;
            }
            if index % 500 == 0 { eprintln!("   {name}: {index}/{}", archive.entries().len()); }
            if !first {
                entries_json.push_str(",\n");
            }
            first = false;
            record.write_json(&mut entries_json);
        }
        entries_json.push_str("\n  ]\n}\n");
        fs::write(out_dir.join("manifest.json"), &entries_json)?;
        let _ = writeln!(
            top,
            "    {{\"name\": {}, \"entries\": {}, \"files\": {}, \"skipped\": {}, \"errors\": {}, \"bytes\": {}, \"manifest\": {}}}{}",
            json_str(name), counts.entries, counts.files, counts.skipped, counts.errors, counts.bytes,
            json_str(&format!("{name}/manifest.json")),
            if ai + 1 == names.len() { "" } else { "," }
        );
        total.entries += counts.entries;
        total.files += counts.files;
        total.skipped += counts.skipped;
        total.errors += counts.errors;
        total.bytes += counts.bytes;
        eprintln!(
            "   done: entries={} files={} skipped={} errors={}",
            counts.entries, counts.files, counts.skipped, counts.errors
        );
    }
    top.push_str("  ],\n");
    let _ = writeln!(top, "  \"total_entries\": {},", total.entries);
    let _ = writeln!(top, "  \"total_files\": {},", total.files);
    let _ = writeln!(top, "  \"total_skipped\": {},", total.skipped);
    let _ = writeln!(top, "  \"total_errors\": {},", total.errors);
    let _ = writeln!(top, "  \"total_bytes\": {},", total.bytes);
    let _ = writeln!(top, "  \"elapsed_seconds\": {:.1}", started.elapsed().as_secs_f64());
    top.push_str("}\n");
    fs::write(cli.out.join("manifest.json"), &top)?;
    eprintln!(
        "ALL DONE entries={} files={} skipped={} errors={} bytes={} elapsed={:.1}s",
        total.entries, total.files, total.skipped, total.errors, total.bytes, started.elapsed().as_secs_f64()
    );
    Ok(())
}

fn extract_payload(
    data: &[u8],
    dir: &Path,
    stem: &str,
    index: usize,
    record: &mut EntryRecord,
    counts: &mut Counts,
) -> Result<()> {
    if compact::is_atlas(data) {
        let members = compact::parse_atlas(data).context("KATL atlas")?;
        let mut n = 0usize;
        for (member, image) in members {
            if member.eq_ignore_ascii_case("dummy") || image.is_empty() {
                continue;
            }
            let member_stem = format!("{stem}__{}", safe_stem(member));
            let mut sub = EntryRecord::new(index, &record.name);
            let written = extract_compact(image, dir, &member_stem, index * 1000 + n, &mut sub, counts)?;
            if written {
                n += 1;
                record.absorb(sub, &format!("{member_stem}.{}", ""));
            }
        }
        if n == 0 {
            return Ok(());
        }
        return Ok(());
    }
    if compact::is_compact(data) {
        extract_compact(data, dir, stem, index, record, counts)?;
        return Ok(());
    }
    if bntx::is_bntx(data) {
        return extract_bntx(data, dir, stem, index, record, counts);
    }
    // Retained non-image payload: keep original extension when it is not an NX wrapper.
    let ext = match label_ext(&record.name) {
        Some(e) if !matches!(e.as_str(), "nxz" | "nxgz") => e,
        _ => "bin".to_string(),
    };
    let path = unique_path(dir, stem, &ext);
    fs::write(&path, data).with_context(|| format!("writing {}", path.display()))?;
    counts.files += 1;
    counts.bytes += data.len() as u64;
    record.outputs.push((path.file_name().unwrap().to_string_lossy().into_owned(), "raw".into(), data.len(), None));
    Ok(())
}

fn extract_compact(
    data: &[u8],
    dir: &Path,
    stem: &str,
    serial: usize,
    record: &mut EntryRecord,
    counts: &mut Counts,
) -> Result<bool> {
    let img = compact::parse(data).context("KIMG")?;
    record.logical = Some([img.logical[0], img.logical[1]]);
    record.physical = Some([img.size[0], img.size[1]]);
    record.encoding = Some(encoding_name(img.encoding).to_string());
    match img.encoding {
        compact::Encoding::Jpeg => {
            let path = unique_path(dir, stem, "jpg");
            fs::write(&path, img.payload)?;
            counts.files += 1;
            counts.bytes += img.payload.len() as u64;
            record.outputs.push((path.file_name().unwrap().to_string_lossy().into_owned(), "JPEG".into(), img.payload.len(), None));
        }
        compact::Encoding::Png | compact::Encoding::PngUnorm => {
            let path = unique_path(dir, stem, "png");
            fs::write(&path, img.payload)?;
            counts.files += 1;
            counts.bytes += img.payload.len() as u64;
            record.outputs.push((path.file_name().unwrap().to_string_lossy().into_owned(), "PNG".into(), img.payload.len(), None));
        }
        compact::Encoding::Bc7Srgb | compact::Encoding::Bc7Unorm => {
            let texture = img.texture().context("BC7 texture")?;
            let rgba = bntx_decode::to_rgba8(&texture).context("BC7 decode")?;
            let path = unique_path(dir, stem, "png");
            image::save_buffer(&path, &rgba, texture.width, texture.height, ExtendedColorType::Rgba8)?;
            counts.files += 1;
            counts.bytes += fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
            record.outputs.push((path.file_name().unwrap().to_string_lossy().into_owned(), encoding_name(img.encoding).into(), 0, record.physical));
        }
        compact::Encoding::GxtNativeUnorm | compact::Encoding::GxtAlterSrgb => {
            let (w, h, rgba) = gxt_decode::rgba8(img.payload, 256 * 1024 * 1024).context("GXT decode")?;
            let path = unique_path(dir, stem, "png");
            image::save_buffer(&path, &rgba, w, h, ExtendedColorType::Rgba8)?;
            counts.files += 1;
            counts.bytes += fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
            record.outputs.push((path.file_name().unwrap().to_string_lossy().into_owned(), "GXT-PNG".into(), 0, Some([w, h])));
        }
        _ => {
            let path = unique_path(dir, stem, "bin");
            fs::write(&path, img.payload)?;
            counts.files += 1;
            counts.bytes += img.payload.len() as u64;
            record.outputs.push((path.file_name().unwrap().to_string_lossy().into_owned(), "unknown-raw".into(), img.payload.len(), None));
        }
    }
    let _ = serial;
    Ok(true)
}

fn extract_bntx(
    data: &[u8],
    dir: &Path,
    stem: &str,
    _index: usize,
    record: &mut EntryRecord,
    counts: &mut Counts,
) -> Result<()> {
    let textures = bntx::parse(data).context("BNTX")?;
    for (k, texture) in textures.iter().enumerate() {
        let rgba = bntx_decode::to_rgba8(texture).context("BNTX decode")?;
        let texture_stem = safe_stem(&texture.name);
        let name = if texture_stem.is_empty() { format!("{stem}__{k}") } else { format!("{stem}__{texture_stem}") };
        let path = unique_path(dir, &name, "png");
        image::save_buffer(&path, &rgba, texture.width, texture.height, ExtendedColorType::Rgba8)?;
        counts.files += 1;
        counts.bytes += fs::metadata(&path).map(|m| m.len()).unwrap_or(0);
        record.outputs.push((
            path.file_name().unwrap().to_string_lossy().into_owned(),
            "BNTX-PNG".into(),
            0,
            Some([texture.width, texture.height]),
        ));
    }
    Ok(())
}

struct EntryRecord {
    index: usize,
    name: String,
    logical: Option<[u32; 2]>,
    physical: Option<[u32; 2]>,
    encoding: Option<String>,
    outputs: Vec<(String, String, usize, Option<[u32; 2]>)>,
}

impl EntryRecord {
    fn new(index: usize, name: &str) -> Self {
        Self { index, name: name.to_string(), logical: None, physical: None, encoding: None, outputs: Vec::new() }
    }
    fn absorb(&mut self, other: EntryRecord, _hint: &str) {
        self.outputs.extend(other.outputs);
        if self.encoding.is_none() { self.encoding = other.encoding; }
        if self.logical.is_none() { self.logical = other.logical; }
        if self.physical.is_none() { self.physical = other.physical; }
    }
    fn write_json(&self, out: &mut String) {
        let _ = write!(out, "    {{\"index\": {}, \"name\": {}, ", self.index, json_str(&self.name));
        if let Some(v) = self.logical { let _ = write!(out, "\"logical\": [{}, {}], ", v[0], v[1]); }
        if let Some(v) = self.physical { let _ = write!(out, "\"physical\": [{}, {}], ", v[0], v[1]); }
        if let Some(e) = &self.encoding { let _ = write!(out, "\"encoding\": {}, ", json_str(e)); }
        out.push_str("\"files\": [");
        for (i, (path, kind, bytes, size)) in self.outputs.iter().enumerate() {
            if i > 0 { out.push_str(", "); }
            let _ = write!(out, "{{\"path\": {}, \"kind\": {}, \"bytes\": {}", json_str(path), json_str(kind), bytes);
            if let Some(v) = size { let _ = write!(out, ", \"size\": [{}, {}]", v[0], v[1]); }
            out.push('}');
        }
        out.push_str("]}");
    }
}

fn unique_path(dir: &Path, stem: &str, ext: &str) -> PathBuf {
    let mut path = dir.join(format!("{stem}.{ext}"));
    let mut n = 2;
    while path.exists() {
        path = dir.join(format!("{stem}__{n}.{ext}"));
        n += 1;
    }
    path
}

fn stem_of(name: &str) -> String {
    let base = name.rsplit_once('.').map_or(name, |(s, _)| s);
    safe_stem(base)
}

fn label_ext(name: &str) -> Option<String> {
    name.rsplit_once('.').map(|(_, e)| e.to_ascii_lowercase())
}

fn safe_stem(name: &str) -> String {
    let mut out = String::new();
    for ch in name.chars() {
        if ch.is_ascii_alphanumeric() || matches!(ch, '_' | '-' | '.' | ' ' | '(' | ')' | '+' | '!' | '#') {
            out.push(ch);
        } else {
            out.push('_');
        }
    }
    let out = out.trim_matches(|c: char| c == '.' || c == ' ').to_string();
    if out.len() > 120 { out[..120].to_string() } else { out }
}

fn encoding_name(e: compact::Encoding) -> &'static str {
    match e {
        compact::Encoding::Jpeg => "Jpeg",
        compact::Encoding::Png => "Png",
        compact::Encoding::Bc7Srgb => "Bc7Srgb",
        compact::Encoding::Bc7Unorm => "Bc7Unorm",
        compact::Encoding::PngUnorm => "PngUnorm",
        compact::Encoding::GxtAlterSrgb => "GxtAlterSrgb",
        compact::Encoding::GxtNativeUnorm => "GxtNativeUnorm",
    }
}

fn json_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => { let _ = write!(out, "\\u{:04x}", c as u32); }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn unix_now() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}
