#!/usr/bin/env bash
# Exact packing/alpha, admission transfer and rollback in the production C code.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
vita_sdk=${VITASDK:-/opt/vitasdk}
build="$project/.work/lossless/native"
mkdir -p "$build"
cc -std=c11 -Wall -Wextra -Werror -O1 -g -fsanitize=address,undefined \
    -fno-omit-frame-pointer -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -idirafter "$vita_sdk/arm-vita-eabi/include" \
    "$project/knife/vita/tests/gxm_lossless_test.c" "$project/knife/vita/perf_audit.c" \
    -lm -o "$build/lossless"
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 "$build/lossless"
