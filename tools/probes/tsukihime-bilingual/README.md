# Tsukihime bilingual regression probe

This small host crate imports the production language, save-layout and storage
modules without the desktop game's GStreamer or rendering dependencies. Only the
build selector and unused default save pathname are supplied by the harness.

Run from the repository root with Rust 1.99.0:

```sh
cargo +1.99.0 test --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml --features tsukihime
cargo +1.99.0 test --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml
```

To include the real-asset check, set `KNIFE_BILINGUAL_ASSETS` to the R3 assets
directory and `KNIFE_BILINGUAL_SOURCE` to the preserved four-language R2 assets
directory before running the first command. Without those variables, the real
asset test returns without exercising game data. That test compares every line,
checks retained/removed UI atlas names, and asks the production `ab_glyph` parser
to load and outline every visible character from the JA/ZC script and SYSMES.

These are host checks. They do not exercise GXM, the actual settings interaction,
or the font's appearance on a Vita display.
