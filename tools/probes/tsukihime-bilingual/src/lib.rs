#![allow(dead_code)]
#[path="../../../../knife/knife/src/languages.rs"] mod languages;
#[path="../../../../knife/knife/src/savedata.rs"] mod savedata;
#[path="../../../../knife/knife/src/save_tables.rs"] mod save_tables;
#[path="../../../../knife/knife/src/ui_images.rs"] mod ui_images;
#[path="../../../../knife/knife/src/vita_log.rs"] mod vita_log;
#[cfg(test)]
#[path="../../../../knife/knife-platform-vita/src/console_worker.rs"] mod console_worker;
#[path="../../../../knife/knife/src/controller_axis.rs"] mod controller_axis;
#[path="../../../../knife/knife/src/game/rebake_cohort.rs"] mod rebake_cohort;
#[path="../../../../knife/knife/src/game/sound_barrier.rs"] mod sound_barrier;
#[path="../../../../knife/knife/src/movie/owner.rs"] mod movie_owner;
#[path="../../../../knife/knife/src/gallery_table.rs"] mod gallery_table;
#[cfg(feature="tsukihime")]
#[path="../../../../knife/knife/src/ui/startup_credits.rs"] mod startup_credits;
mod assets {
 std::thread_local! { pub static TEST_WITCH: std::cell::Cell<bool> = const { std::cell::Cell::new(false) }; }
 pub fn witch()->bool { TEST_WITCH.get() }
}
#[path="../../../../knife/knife-platform-vita/src/storage.rs"] pub mod storage_impl;
mod save {
 pub fn file()->std::path::PathBuf { std::path::PathBuf::from("unused-probe-save") }
 pub use crate::storage_impl as storage;
}

#[cfg(all(test, feature="tsukihime"))]
mod gallery_resource_tests {
 use super::{languages,ui_images,gallery_table};
 use ab_glyph::{Font,FontArc};
 use knife_core::format::{archive::{Archive,ArchiveLimits},compact};
 use std::path::PathBuf;

 fn assets() -> Option<PathBuf> { std::env::var_os("KNIFE_GALLERY_ASSETS").map(PathBuf::from) }

 #[test]
 fn music_titles_and_numeric_panel_have_actual_glyph_outlines_in_both_languages() {
  let Some(root)=assets() else { return };
  let fonts=languages::system_font_suffixes().iter().map(|suffix| {
   FontArc::try_from_vec(std::fs::read(root.join(languages::bilingual_font_file(suffix).unwrap())).unwrap()).unwrap()
  }).collect::<Vec<_>>();
  let archive=Archive::open_file_with_limits(&root,"w_allui",ArchiveLimits::VITA).unwrap();
  let raw=archive.read(archive.find_stem("SYSMES_TEXT_ML").unwrap()).unwrap();
  for slot in 0..2 {
   let table=u64::from_le_bytes(raw[16+slot*8..24+slot*8].try_into().unwrap()) as usize;
   let mut all=String::from("0123456789:%？？？");
   for &(_,id,_,_) in gallery_table::MUSIC {
    let offset=table+id as usize*8;
    let start=u64::from_le_bytes(raw[offset..offset+8].try_into().unwrap()) as usize;
    let end=start+raw[start..].iter().position(|&b|b==0).unwrap();
    all.push_str(std::str::from_utf8(&raw[start..end]).unwrap());
   }
   for ch in all.chars().filter(|ch| !ch.is_whitespace() && !ch.is_control() && *ch!='^') {
    let font=fonts.iter().find(|font|font.glyph_id(ch).0!=0).unwrap_or_else(||panic!("system slot {slot}: missing U+{:04X} {ch}",ch as u32));
    assert!(font.outline_glyph(font.glyph_id(ch).with_scale(30.0)).is_some(),"system slot {slot}: no outline for {ch}");
   }
  }
 }

 #[test]
 fn cg_thumbnails_have_enough_pixels_for_the_vita_grid() {
  let Some(root)=assets() else { return };
  let archive=Archive::open_file_with_limits(&root,"w_allui",ArchiveLimits::VITA).unwrap();
  for stem in ["CG_THUMB_PARTS_JA","CG_THUMB_PARTS_ZC"] {
   let raw=archive.read(archive.find_stem(stem).unwrap()).unwrap();
   let images=ui_images::compact_images(stem,&raw).unwrap();
   // A 115x65.5 screen cell needs approximately this many real pixels.
   // Keeping only logical 5544x4840 dimensions allowed the old 17x10 cells.
   assert_eq!(images.len(),28);
   for id in 0..36*55 {
    let (name,src)=ui_images::cg_thumb_source(id,true);
    let (_,data)=images.iter().find(|(n,_)|*n==name).unwrap();
    let image=compact::parse(data).unwrap();
    assert!(src[0]+src[2] <= image.logical[0] as f32);
    assert!(src[1]+src[3] <= image.logical[1] as f32);
    assert!(image.size[0] as f32*src[2]/image.logical[0] as f32 >= 115.0);
    assert!(image.size[1] as f32*src[3]/image.logical[1] as f32 >= 65.0);
    assert!(image.size[0]<=960 && image.size[1]<=1080);
    assert_eq!(image.encoding,compact::Encoding::PngUnorm);
   }
  }
 }
}

#[cfg(all(test, feature="tsukihime"))]
mod startup_pack_tests {
 use knife_core::format::{archive::{Archive,ArchiveLimits},compact};
 #[test]
 fn real_startup_image_loads_through_the_production_archive_parser() {
  let Some(root)=std::env::var_os("KNIFE_STARTUP_ASSETS") else { return };
  let archive=Archive::open_file_with_limits(std::path::Path::new(&root),"parts",ArchiveLimits::VITA).unwrap();
  let raw=archive.read(crate::startup_credits::PARTS_INDEX).unwrap();
  let image=compact::parse(&raw).unwrap();
  assert_eq!(image.logical,[1920,1080]);
  assert_eq!(image.size,[960,544]);
  assert_eq!(image.encoding,compact::Encoding::PngUnorm);
  assert!(image.payload.starts_with(b"\x89PNG\r\n\x1a\n"));
  assert!(raw.len()<256*1024);
 }
}

#[cfg(test)] mod real_pack_tests {
 use super::languages;
 use knife_core::format::{script::ScriptText,archive::{Archive,ArchiveLimits}};
 use std::{path::PathBuf,collections::BTreeSet};
 use ab_glyph::{Font,FontArc};
 #[test] fn real_scripts_ui_and_font_outlines_cover_both_languages() {
  let Some(root)=std::env::var_os("KNIFE_BILINGUAL_ASSETS") else { return };
  let root=PathBuf::from(root);
  let old=PathBuf::from(std::env::var_os("KNIFE_BILINGUAL_SOURCE").unwrap());
  let profile=languages::Profile::load(&root).unwrap().unwrap();
  let script=std::fs::read(root.join("script_text.mrg")).unwrap();
  let original=std::fs::read(old.join("script_text.mrg")).unwrap();
  let main=FontArc::try_from_vec(std::fs::read(root.join("fonts/main.ttf")).unwrap()).unwrap();
  let fallback=FontArc::try_from_vec(std::fs::read(root.join("fonts/fallback.otf")).unwrap()).unwrap();
  let ui=Archive::open_file_with_limits(&root,"w_allui",ArchiveLimits::VITA).unwrap();
  let sys=ui.read(ui.find_stem("SYSMES_TEXT_ML").unwrap()).unwrap();
  assert_eq!(u32::from_le_bytes(sys[0..4].try_into().unwrap()),2);
  for prefix in ["CONF_PARTS","DISP_PARTS","MENU_PARTS","TITLE_PARTS","GALLERY_PARTS","CG_THUMB_PARTS"] {
   assert!(ui.find_stem(&format!("{prefix}_JA")).is_some());
   assert!(ui.find_stem(&format!("{prefix}_ZC")).is_some());
   assert!(ui.find_stem(&format!("{prefix}_EN")).is_none());
   assert!(ui.find_stem(&format!("{prefix}_ZT")).is_none());
  }
  for id in [0,2] {
   let slot=profile.slot(id);
   let parsed=ScriptText::parse(&script,slot).unwrap();
   let reference=ScriptText::parse(&original,id).unwrap();
   assert_eq!(parsed.len(),43972);assert_eq!(parsed.len(),reference.len());
   let mut chars=BTreeSet::new();
   for i in 0..parsed.len() { assert_eq!(parsed.get(i),reference.get(i));chars.extend(parsed.get(i).unwrap().chars()); }
   let table=u64::from_le_bytes(sys[16+slot*8..24+slot*8].try_into().unwrap()) as usize;
   let count=u32::from_le_bytes(sys[4..8].try_into().unwrap()) as usize;
   for i in 0..count {
    let off=u64::from_le_bytes(sys[table+i*8..table+i*8+8].try_into().unwrap()) as usize;
    let end=off+sys[off..].iter().position(|&b|b==0).unwrap();
    chars.extend(std::str::from_utf8(&sys[off..end]).unwrap().chars());
   }
   let mut fallback_chars=Vec::new();let mut outlines=0;
   for c in chars { if c.is_control()||c.is_whitespace()||c=='\u{feff}' {continue}
    let font=if main.glyph_id(c).0!=0 {&main} else {fallback_chars.push(c);&fallback};
    assert_ne!(font.glyph_id(c).0,0,"missing U+{:04X}",c as u32);
    assert!(font.outline_glyph(font.glyph_id(c).with_scale(40.0)).is_some(),"no outline U+{:04X}",c as u32);outlines+=1;
   }
   if id==0 {assert!(fallback_chars.is_empty())}else{assert_eq!(fallback_chars,vec!['嗞','觍'])}
   println!("original language ID {id}: {} exact lines, {outlines} valid outlines, {} fallback glyphs",parsed.len(),fallback_chars.len());
  }
 }
}
