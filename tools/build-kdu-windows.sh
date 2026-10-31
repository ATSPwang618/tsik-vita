#!/usr/bin/env bash
# Build kdu.exe (x86_64-pc-windows-gnu) from the tsik-vita knife workspace.
# asset-pipeline-2, tsik-vita session 2026-10-31
#
# Run INSIDE WSL pocket-ubuntu from anywhere:  bash tools/build-kdu-windows.sh
# Writes the exe to .work/assets/tools/kdu.exe (never modifies tracked sources).
# Requires: rust toolchain 1.99.0 with x86_64-pc-windows-gnu target, mingw-w64
# gcc/g++, and the knife workspace Cargo.lock. Override the cache with
# KNIFE_KDU_CACHE and job count with KNIFE_KDU_JOBS.
set -euo pipefail

ROOT="${KNIFE_TASK_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT="$ROOT/.work/assets/tools"
CACHE="${KNIFE_KDU_CACHE:-$HOME/.cache/knife-windows-x64}"

export PATH="$HOME/.cargo/bin:$PATH"
export CARGO_TARGET_DIR="$CACHE"
export CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER=x86_64-w64-mingw32-gcc
export CC_x86_64_pc_windows_gnu=x86_64-w64-mingw32-gcc
export CXX_x86_64_pc_windows_gnu=x86_64-w64-mingw32-g++
export AR_x86_64_pc_windows_gnu=x86_64-w64-mingw32-ar
export CMAKE_GENERATOR=Ninja

cd "$ROOT/knife"
mkdir -p "$OUT"
echo "START $(date -Is) cache=$CACHE"
cargo +1.99.0 build --locked --release -p kdu --target x86_64-pc-windows-gnu -j "${KNIFE_KDU_JOBS:-6}"
cp -v "$CACHE/x86_64-pc-windows-gnu/release/kdu.exe" "$OUT/kdu.exe"
sha256sum "$OUT/kdu.exe"
echo "DONE $(date -Is)"
