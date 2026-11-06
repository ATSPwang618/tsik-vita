# Tsukihime bilingual regression probe

This small host crate imports the production language, save-layout and storage
modules without the desktop game's GStreamer or rendering dependencies. Only the
build selector and unused default save pathname are supplied by the harness.

It also imports the production rebake cohort helpers, delayed-sound rules and
generic movie owner. Their tests cover generation cancellation, paused-step
ownership, timer rules and GPU frame acknowledgements with a host decoder probe;
they do not run the Vita VM or AvPlayer. Set `KNIFE_GALLERY_ASSETS` and
`KNIFE_STARTUP_ASSETS` to the current R4 assets directory to exercise actual
fonts, gallery pages and startup images in the current resource tests.

The production `vita_log` bridge and bounded console worker are also imported:
tests check severity filtering, bounded UTF-8 records, control-character handling,
queue order and oversized-batch rejection. They do not contact CatLog or a Vita.

Run from the repository root with Rust 1.99.0:

```sh
cargo +1.99.0 test --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml --features tsukihime
cargo +1.99.0 test --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml
cargo +1.99.0 run --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml --example verify_ui_atlases -- dist/TSUKIHIME-RE/assets
```

The optional historical language-conversion comparison additionally uses
`KNIFE_BILINGUAL_ASSETS` and `KNIFE_BILINGUAL_SOURCE` (the pre-conversion R2 pack).
Those old resource trees are no longer retained in this repository. Supply them
externally if that comparison is needed; without the variables it returns without
exercising those inputs. Current R4 gallery/startup tests use the variables above
and the single retained `dist/TSUKIHIME-RE/assets` pack.

These are host checks. They do not exercise GXM, the actual settings interaction,
or the font's appearance on a Vita display.

`verify_ui_atlases` reads every KATL in the shipped UI archive, checks physical
dimensions and decodes each native GXT using production parsers. It also checks
visible alpha in all five title and system-menu button cells, in three states
and both languages (60 cells). The renderer crate's tests register the complete
generated UI table through the actual renderer API, catching whole-atlas load
rejections independently of the image decoder. No extra image files are written.

Current commands and evidence scope: [validation](../../../doc/validation.md).
