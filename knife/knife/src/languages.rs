//! Optional distribution language policy. Save/script IDs remain the original IDs.
use anyhow::{Context, Result, ensure};
use std::{collections::HashMap, path::Path};

pub struct Profile {
    ids: Vec<usize>,
    pub aliases: HashMap<String, Vec<String>>,
}

impl Profile {
    pub fn load(root: &Path) -> Result<Option<Self>> {
        let path = root.join("language-profile.txt");
        if !path.exists() { return Ok(None); }
        let text = std::fs::read_to_string(path).context("reading language profile")?;
        let mut lines = text.lines();
        ensure!(lines.next() == Some("knife-languages-v1"), "unknown language profile");
        let ids = lines.map(|line| {
            line.split('\t').next().context("missing language ID")?.parse::<usize>().context("invalid language ID")
        }).collect::<Result<Vec<_>>>()?;
        ensure!(ids == [1, 2] || ids == [0, 2], "unsupported compact language IDs");
        let mut aliases: HashMap<String, Vec<String>> = HashMap::new();
        // JA/ZC retains the Japanese atlas used for positional aliases. The older
        // EN/ZC distribution needs its exported sidecar because JA was removed.
        let alias_text = if ids == [0, 2] { String::new() } else {
            std::fs::read_to_string(root.join("ui-aliases.tsv")).context("reading UI aliases")?
        };
        for line in alias_text.lines() {
            let (base, name) = line.split_once('\t').context("invalid UI alias")?;
            aliases.entry(base.to_ascii_uppercase()).or_default().push(name.to_string());
        }
        Ok(Some(Self { ids, aliases }))
    }

    pub fn resolve(&self, word: i16, system: i16) -> usize {
        if self.japanese_chinese() { return normalize_tsukihime_language(word) as usize; }
        let id = if word < 0 || word > 3 { system } else { word };
        if id == 2 || id == 3 { 2 } else { 1 }
    }

    pub fn japanese_chinese(&self) -> bool { self.ids == [0, 2] }

    pub fn slot(&self, id: usize) -> usize {
        self.ids.iter().position(|&value| value == id).unwrap_or(0)
    }

    pub fn cycle(&self, id: usize, forward: bool) -> i16 {
        let slot = self.slot(id);
        self.ids[(slot + if forward { 1 } else { self.ids.len() - 1 }) % self.ids.len()] as i16
    }
}

/// Persist original script IDs; unsupported old languages migrate to Chinese.
pub fn normalize_tsukihime_language(word: i16) -> i16 {
    if word == 0 { 0 } else { 2 }
}

/// Visual order is independent of physical archive slots and saved IDs.
pub fn menu_ids() -> &'static [usize] {
    if cfg!(feature = "tsukihime") { &[2, 0] } else { &[0, 1, 2, 3] }
}

pub fn menu_slot(id: usize) -> usize {
    menu_ids().iter().position(|&value| value == id).unwrap_or(0)
}

/// Files of a JA/ZC font set; the subset supplements the primary font.
pub fn bilingual_font_file(suffix: &str) -> Option<&'static str> {
    match suffix { "" | "3" => Some("fonts/main.ttf"), "2" => Some("fonts/fallback.otf"), _ => None }
}

pub fn system_font_suffixes() -> &'static [&'static str] {
    // In the bilingual pack, suffix 2 contains only two supplemental glyphs.
    // System text needs the same primary font as dialogue, then that subset.
    if cfg!(feature = "tsukihime") { &["", "2"] } else { &["2"] }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(feature = "tsukihime")]
    #[test]
    fn menu_has_only_chinese_then_japanese_without_renumbering_ids() {
        assert_eq!(menu_ids(), [2, 0]);
        assert_eq!((menu_slot(2), menu_slot(0)), (0, 1));
    }
    #[test]
    fn japanese_chinese_profile_keeps_save_ids_and_defaults_to_chinese() {
        let p = Profile { ids: vec![0, 2], aliases: HashMap::new() };
        assert_eq!((p.resolve(0, 1), p.resolve(2, 1)), (0, 2));
        for old in [-32768, -1, 1, 3, 4, 32767] {
            assert_eq!(p.resolve(old, 0), 2, "unsupported saved ID {old}");
        }
        assert_eq!((p.slot(0), p.slot(2)), (0, 1));
        for forward in [false, true] {
            assert_eq!(p.cycle(0, forward), 2);
            assert_eq!(p.cycle(2, forward), 0);
        }
    }
    #[test]
    fn japanese_chinese_profile_loads_without_removed_japanese_alias_sidecar() {
        let root = std::env::temp_dir().join(format!("knife-ja-zc-{}", std::process::id()));
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(root.join("language-profile.txt"), "knife-languages-v1\n0\tja\n2\tzc\n").unwrap();
        let loaded = Profile::load(&root);
        std::fs::remove_file(root.join("language-profile.txt")).unwrap();
        std::fs::remove_dir(&root).unwrap();
        assert_eq!(loaded.unwrap().unwrap().ids, [0, 2]);
    }
    fn profile() -> Profile { Profile { ids: vec![1, 2], aliases: HashMap::new() } }
    #[test]
    fn legacy_save_ids_are_mapped_without_renumbering_chengkong() {
        let p = profile();
        assert_eq!((p.resolve(1, 0), p.resolve(2, 0)), (1, 2));
        assert_eq!((p.resolve(0, 0), p.resolve(3, 0)), (1, 2));
        assert_eq!((p.resolve(-1, 3), p.resolve(-1, 0)), (2, 1));
        assert_eq!((p.slot(1), p.slot(2)), (0, 1));
    }
    #[test]
    fn language_arrows_visit_only_english_and_chengkong_in_both_directions() {
        let p = profile();
        for forward in [false, true] {
            assert_eq!(p.cycle(1, forward), 2);
            assert_eq!(p.cycle(2, forward), 1);
        }
    }
}
