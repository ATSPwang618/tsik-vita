# 构建环境与可复现命令

> 本文记录本次会话（2026-10-31）在本机实际验证过的 PS Vita 构建环境、命令、耗时与产物哈希。
> **[实测]** = 本机本次会话输出；**[未验证]** = 无设备证据。

## 1. 环境事实（实测）

| 项 | 值 |
|---|---|
| 宿主 | Windows 11（amd64），D: 盘（NTFS）为工作区 |
| 构建宿主 | WSL 2，发行版 `pocket-ubuntu`，Linux 6.6.87.2-microsoft-standard-WSL2，x86_64，root |
| Windows Python | 3.13（`py -3`），`tools/build-vita.py` 的 Windows 入口 |
| WSL Python | 3.12.3（`python3`），实际构建入口 |
| Rust | `nightly-2026-05-28`（rustc 1.98.0-nightly, 2026-05-27）+ `rust-src`，位于 `/root/.cargo` |
| VitaSDK | `/opt/vitasdk`，GCC 15.2.0（hard-float 默认），CMake 3.28.3，Ninja 1.11.1 |
| 工具 | `arm-vita-eabi-*`、`vita-elf-create`、`vita-make-fself`、`vita-mksfoex`、`vita-pack-vpk` 齐备 |
| 环境体检 | `tools/build-vita.py --check --native --json` → `"ready": true`，`base_missing: []`，`rust.missing: []` |

## 2. 缓存隔离（本机已踩坑并修复）

`mofa-vita` 的构建缓存 `/root/.cache/knife-vita` 里 CMakeCache 指向 `/mnt/d/AI-CODEX/mofa-vita/knife/vita`；
在 `tsik-vita` 里复用它会在 native CMake 配置阶段报：

```
CMake Error: The source ".../tsik-vita/knife/vita/CMakeLists.txt" does not match the source
".../mofa-vita/knife/vita/CMakeLists.txt" used to generate cache.
```

**解决（本次采用）**：为 tsik-vita 使用独立的 cargo target 缓存：

```bash
export KNIFE_VITA_CACHE=/root/.cache/knife-vita-tsik
```

首次构建需要重编全部依赖（本机约 45–60 秒，因为 cargo registry 与 rustup 已预热；从零联网环境会明显更久）。
不要删除 mofa-vita 的旧缓存，也不要让两个项目共用同一 target 目录。

## 3. 可复现命令（实测可用）

### 3.1 WSL 原生入口（推荐，本次实际使用）

```bash
# 月姬 540p（TITLE KNIF00541）
wsl.exe -d pocket-ubuntu -- bash /mnt/d/AI-CODEX/tsik-vita/.work/logs/lead-tsukihime-build.sh
# 内容：cd /mnt/d/AI-CODEX/tsik-vita
#       export VITASDK=/opt/vitasdk KNIFE_VITA_CACHE=/root/.cache/knife-vita-tsik KNIFE_VITA_VARIANT=tsukihime540
#       python3 tools/build-vita.py --native game release
```

### 3.2 Windows 入口（已修复 WSL 参数转发，实测 `--check` 通过）

```powershell
py -3 tools\build-vita.py --check
py -3 tools\build-vita.py --variant tsukihime540 game release
py -3 tools\build-vita.py --variant native540 game release   # WoH 回归
```

WSL 2.5.10 的 `wsl.exe` 在转发 argv 时会吞掉单反斜杠，导致旧版 `wsl_path()` 把
`D:\AI-CODEX\...` 变成 `D:AI-CODEX...`，Windows 入口无法选择发行版。
修复：`tools/build-vita.py::wsl_path()` 先把路径转成正斜杠再调用 `wslpath -u`。修复后
`py -3 tools\build-vita.py --check` 输出 `Selected WSL: pocket-ubuntu` / `Check: ready`。

### 3.3 产物与自动检查

构建脚本会依次自动执行：`vita-elf-create` → `vita-make-fself` → `vita-mksfoex`
（TITLE_ID/APP_VER/ATTRIBUTE2）→ `vita-pack-vpk` → `tools/check-vita-package.py`
→ `tools/vita-build-receipt.py` → 复制 VPK 到 `release/` 并打印 SHA-256。

## 4. 本次构建结果（实测）

### 4.1 WoH 基线（改动前，验证工具链）

| 项 | 值 |
|---|---|
| 命令 | `KNIFE_VITA_CACHE=/root/.cache/knife-vita-tsik python3 tools/build-vita.py --native game release`（VARIANT 默认 native540） |
| 耗时 | 15:56:50 开始 → 15:57:50 结束（约 60 s；cargo 编译 51.3 s） |
| VPK | `.work/vita/game-release-540p/knife-vita-game-540p.vpk` = 7,019,059 B |
| SHA-256 | `292e1a5f7fefaeb9a67c9a6c9ea0d824ee725a9351b93832482bcd6441ed05e0` |
| 包检查 | `PASS: KNIF00540 ATTRIBUTE2=12; 21 engine-only entries; no game data` |

### 4.2 月姬 540p（本次交付 VPK）

| 项 | 值 |
|---|---|
| 命令 | `KNIFE_VITA_VARIANT=tsukihime540 ... python3 tools/build-vita.py --native game release` |
| 耗时 | 14:59:48 开始 → 15:00:40 结束（约 52 s；cargo 编译 44.2 s） |
| 构建目录 | `.work/vita/game-release-tsukihime-540p/`（eboot.bin / knife.elf / knife.velf / param.sfo / knife.map / 收据） |
| VPK | `.work/vita/game-release-tsukihime-540p/knife-vita-tsukihime-540p.vpk`，自动复制到 `release/` |
| 包检查 | `PASS: KNIF00541 ATTRIBUTE2=12; 21 engine-only entries; no game data` |
| 收据 | `.work/vita/game-release-tsukihime-540p/vita-game-release-build.json`（含逐文件 SHA、工具链身份、`runtime_verified:false`） |
| 最终 VPK | `release/knife-vita-tsukihime-540p.vpk` = **6,723,076 B**，SHA-256 `df49c9c5e8353029d473a6bf8734e66de6b1185b3bd4594d811ad33afc232e09`（真实素材 profile 175 文件 + atlas 索引 40 图集/736 成员 + stream 索引 16,601 条已内嵌；`--variant tsukihime540` CLI 路径实测；包检查 PASS） |
| WoH 回归 | 同一份源码 `--variant native540`：`release/` 中 WoH VPK 6,729,132 B，包检查 PASS；已移存 `.work/baseline/knife-vita-game-540p-postpatch.vpk`，`release/` 只保留月姬交付 VPK |

## 5. 磁盘与临时数据（本机）

| 数据 | 位置 | 大小/说明 |
|---|---|---|
| 原始 NSP | `switch原版游戏/…nsp` | 24,712,645,184 B（23.0 GiB） |
| NCA 中间产物 | `.work/nsp/nca/` | 约 24.6 GiB（解包后删除，可用 `tools/hactool/extract_tsukihime.py` 重建） |
| 合并 romfs（base 1.0.0 + update 1.0.1） | `.work/nsp/romfs/` | 约 22.9 GiB、约 1.68 万文件 |
| exefs | `.work/nsp/exefs-base/`、`.work/nsp/exefs-update/` | 各约 20 MB；update 的 NSO build id = `d10d239aade1d526` |
| 构建缓存 | `/root/.cache/knife-vita-tsik`（WSL 内） | 数 GB，不要与 mofa-vita 缓存混用 |

NSP 解包细节与校验见 [01-nsp-inventory.md](01-nsp-inventory.md)。

## 6. 故障排查（本次新增/沿用）

| 现象 | 处理 |
|---|---|
| `CMake Error: source ... does not match ... used to generate cache` | 设置独立 `KNIFE_VITA_CACHE`（§2） |
| Windows：`WSL path conversion failed` / 无法选择发行版 | 更新到本仓库的 `wsl_path()` 修复，或直接在 WSL 内用 `--native` 构建 |
| `Missing or modified bundled compiler` | `knife/vita/vendor/shacccg/libshacccg.suprx` 被改/缺失，从仓库恢复 |
| `Missing build tool: …` | VitaSDK 工具不在 PATH（WSL 内应为 `/opt/vitasdk/bin`） |
| 包检查报 TITLE/ATTRIBUTE2/540p 不符 | 确认 `--variant tsukihime540` 与 `KNIF00541` 配套；不要手改 param.sfo 后不重装 |
| 设备 `ASSETS REQUIRED` | 素材根/清单缺失或版本不符，见根 README §3 与 doc/04 |
