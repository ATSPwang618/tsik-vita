# Authored GXM shaders

The Tsukihime Vita build embeds all 109 programs: basic quad, engine effects,
framebuffer-fetch and blend-chain paths, and 63 specialized variants.
`effects.cg` and `quad_v.cg` / `quad_f.cg` are the authored inputs;
`generated/effects.h` and `generated/shaders.h` are required build inputs.

Run from the repository root:

~~~sh
python3 tools/compile-vita-offline-shaders.py --check
python3 tools/compile-vita-offline-shaders.py --compiler /path/to/psp2cgc
python3 tools/generate-runtime-shaders.py
python3 -B -m unittest discover -s tools -p 'test_offline_shaders.py'
~~~

The single offline generator owns both headers and the inventory receipt. Each
program is compiled twice and checked for identical bytes, bounded GXP layout,
reflection, stage and parameter contracts. CMake rejects stale generated output.
Checking existing files does not need a compiler. Supply the compiler locally;
never copy it or Sony runtime modules into the repository.

The two older partial PowerShell generators have been retired.
`generate-runtime-shaders.py` remains necessary for the shared non-Tsukihime
runtime compilation path; it is not the default Tsukihime route.

Offline compilation does not replace device-side program checking, registration
and patching. Static instruction counts are not GPU frame-time measurements.
See the [shader guide](../../../doc/shaders.md) and
[inventory receipt](../../../doc/evidence/offline-shaders.json).
