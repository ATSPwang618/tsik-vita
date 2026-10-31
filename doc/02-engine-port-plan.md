# 引擎与构建工具的月姬海外版改动

> 状态：**[代码已实现并构建通过]**。本文件记录把 mofa-vita（WoH Vita 移植）的引擎/工具改成
> TSUKIHIME 海外版 960×540 变体（TITLE `KNIF00541`）的全部改动，以及验证结果与转正剩余步骤。
> 基线：`mofa-vita` 工作树（引擎 = AuroraWright/knife 0.9.4 + mofa-vita Vita 后端）。

## 0. 结论

- 引擎代码本身已支持 `Build::Overseas`（识别 `w_allpac.nam`，使用 `knife/data/exe_tables_overseas.bin`），
  因此 Vita 移植只需要**换发布身份、数据根、保存根、素材校验 profile 与 atlas/stream 元数据**，不需要改脚本机/舞台/渲染/音频。
- 关键外部对齐已验证：NSP 内 update 程序 NCA 的 exe NSO build id = `d10d239aade1d526`，
  与引擎内嵌 `exe_tables_overseas.bin` 的目标 build **逐字节同一构建**（见 doc/01）。
- 月姬 VPK 已构建并通过 `check-vita-package.py`（TITLE `KNIF00541`、ATTRIBUTE2=12、21 个引擎条目、无游戏数据）。
- 原 WoH 变体（`native540`）在同一份源码中保留，可回归构建（见 §4）。

## 1. Cargo feature / 编译期开关

| 文件 | 改动 |
|---|---|
| `knife/knife/Cargo.toml` | 新增 feature `tsukihime = ["knife-platform-vita/tsukihime"]`；与 `vita-gxm`、`assets-540p` 一起启用 |
| `knife/knife-platform-vita/Cargo.toml` | 新增 feature `tsukihime = []` |

使用 `cfg(feature = "tsukihime")` 即可在 knife / platform-vita 两个 crate 中切换月姬身份。
构建命令由 `tools/build-vita.sh` 自动加 `--features vita-gxm,assets-540p,tsukihime`。

## 2. 引擎内改动（运行时）

| 文件 | 符号/位置 | 改动 |
|---|---|---|
| `knife/knife-platform-vita/src/asset_check.rs` | profile include 选择 | `feature=tsukihime` → `include!("asset_profile_tsukihime_540p.rs")`；其余维持 270p/540p 分支 |
| `knife/knife-platform-vita/src/asset_profile_tsukihime_540p.rs` | 新文件（当前为临时空 profile） | 真实 profile 由 `tools/generate_vita_asset_profile_tsukihime_540.py --assets <pack>/assets` 生成；空 profile 只用于引擎-only 构建 |
| `knife/knife-platform-vita/src/boot_error.rs` | `PACK_DESCRIPTION` / `ASSETS_ROOT` | 月姬构建显示 `THIS ENGINE USES THE TSUKIHIME 960 X 540 ASSET PACK.` 与 `ux0:data/knife-tsukihime-540p/assets` |
| `knife/knife-platform-vita/src/storage.rs` | `DEV_SAVE_ROOT` / `PRODUCTION_SAVE_ROOT` | 月姬：`ux0:data/knife-tsukihime-dev/saves` / `ux0:data/knife-tsukihime-540p/saves`；WoH 保留原路径 |
| `knife/knife/src/vita_entry.rs` | `ASSETS` / `PERF_ROOT` | 月姬：`ux0:data/knife-tsukihime-540p/assets` 与 `ux0:data/knife-tsukihime-540p` |
| `knife/knife/src/vita_entry.rs` | perf 日志 profile 字段 | 月姬构建写 `tsukihime-540p-provisional`，启动后用真实 profile 时应改为 `tsukihime-540p` 并同步 README/收据 |
| `knife/knife/src/vita_entry.rs` | `ASSETS profile=…` / `ASSETS verified …` 日志 | 月姬构建输出 TSUKIHIME 文案 |
| `knife/knife/src/vita_atlas_index.rs` | KATL 索引 include | 月姬 → `knife/knife/data/vita_atlas_index_tsukihime_540p.rs`（当前空索引，禁用嵌入式 KATL 快路径，保留有界归档回退） |
| `knife/knife/src/vita_stream_index.rs` | stream 索引 include | 月姬 → `knife/knife/data/vita_stream_index_tsukihime_540p.txt`（当前仅 schema 行） |

**不修改**的部分（有意为之）：
- 语言固定中文 ID（2）：`assets.rs resolve_language/next_language`、`savedata.rs set_language` 中
  `cfg!(all(target_os="vita", feature="assets-540p"))` 的两个分支同时服务两个 540p 变体；月姬官方数据含中文条带，
  固定 ID2 与 mofa-vita 的发布约定一致。
- `Build::Overseas` 的脚本机/舞台/菜单/存档/画廊/流程分支全部使用上游既有实现；
  `exe_tables_overseas.bin` 已包含对应的镜像表、场景表、运动表、行宽表等。

## 3. 构建/打包工具改动

| 文件 | 改动 |
|---|---|
| `tools/build-vita.sh` | `KNIFE_VITA_VARIANT` 增加 `tsukihime540`：TITLE「TSUKIHIME A piece of blue glass moon 540p」、TITLE ID `KNIF00541`、`--features vita-gxm,assets-540p,tsukihime`、输出 `.work/vita/game-release-tsukihime-540p/` 与 `release/knife-vita-tsukihime-540p.vpk`、ATTRIBUTE2=12、`KNIFE_VITA_SCENE_PIXELS=960,540` |
| `tools/build-vita.py` | 新增 `--variant native540\|tsukihume540\|270p`（写入 `KNIFE_VITA_VARIANT` 并随 `KNIFE_*` 传入 WSL） |
| `tools/build-vita.ps1` | 新增 `-Variant` 转发 |
| `tools/build-vita.py` `wsl_path()` | **修复本机 WSL 2.5.10 参数转发吞反斜杠导致 Windows 入口无法选择发行版**：转为正斜杠后再 `wslpath -u` |
| `tools/check-vita-package.py` | 540p 级 TITLE ID 集合加入 `KNIF00541`（ATTRIBUTE2 期望 12、release TITLE 必须含 `540p`） |
| `tools/generate_vita_asset_profile_tsukihime_540.py` | 新增：从月姬素材包清单生成 `asset_profile_tsukihime_540p.rs`；`--provisional` 写空 profile；`--check` 校验工作树一致性 |

## 4. 验证结果（本次会话实测）

| 验证 | 结果 |
|---|---|
| 原 WoH 基线构建（改动前） | `knife-vita-game-540p.vpk` 7,019,059 B，sha256 `292e1a5f…d05e0`，`check-vita-package.py` PASS（KNIF00540/ATTRIBUTE2=12） |
| 月姬变体构建 | `release/knife-vita-tsukihime-540p.vpk`，**6,723,076 B**，SHA-256 `df49c9c5e8353029d473a6bf8734e66de6b1185b3bd4594d811ad33afc232e09`，`check-vita-package.py` **PASS**（`KNIF00541 ATTRIBUTE2=12; 21 engine-only entries; no game data`）；构建命令使用文档化的 `python3 tools/build-vita.py --variant tsukihime540 game release` |
| WoH 回归（改动后） | `--variant native540` 构建 + 包检查 PASS（6,729,132 B），证明月姬改动未破坏原 WoH 变体 |
| 海外版 exe 对齐 | NSP update exefs NSO build id `d10d239aade1d526` = 引擎 `OVERSEAS.build_id`；base 为 `b825b1746fa69a0a`（不同版本，不用于运行） |
| Windows 构建入口 | `py -3 tools\build-vita.py --check` 修复后能选择 `pocket-ubuntu` 并报 `Check: ready` |
| 真机/Vita3K | **[未验证]**：本次无设备证据 |

## 5. 转正为“可完整游玩”的剩余步骤

> 进度（2026-10-31 会话末）：**步骤 0–3 已完成** —— 阶段 B（540p 图像预处理）与阶段 C–F（portable/KATL、音频/影片、DXT codec8、mofa migrate codec9、清单与 profile/atlas/stream 元数据）均已执行；最终素材包 `dist/Tsukihime-540p-Vita/assets/`（16,832 文件 / 3.75 GiB，manifest sha `933fa16c…`，codec 直方图 9:21,389 / 7:2,214 / 2:321），真实 profile 已内嵌并重建 VPK（`release/knife-vita-tsukihime-540p.vpk`，6,723,076 B，SHA-256 `df49c9c5…2e09`）。剩余仅为真机/Vita3K 运行验证与画质/性能实测。
0. **（已完成）阶段 B 540p 预处理**：kdu compact（w_allpac 0.375/strips1、w_allpaccg 0.375/strips1、
   w_allpacml 0.375/strips4、allpachd 0.75/strips1），结果与耗时见 doc/05 §4。
1. 按 doc/04 §7.3 执行阶段 C–E：portable/KATL（含 `w_allui`、音频→Ogg、影片→960×540）、DXT、GXT codec9。
2. 重新生成三件套内嵌元数据：
   ```bash
   python3 tools/generate_vita_asset_profile_tsukihime_540.py --assets <pack>/assets
   python3 tools/generate-vita-atlas-index.py <pack>/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs
   python3 tools/generate-vita-stream-index.py <pack>/assets/vita-540p-assets.json knife/knife/data/vita_stream_index_tsukihime_540p.txt
   ```
3. 重新构建并重跑包检查：`python3 tools/build-vita.py --variant tsukihime540 game release`。
4. 用 Vita3K 或真机启动，录制首帧/标题/序章证据，并把 `doc/03` 的 `runtime_verified` 从 false 改为实测结论。
5. 视需要更换 LiveArea 占位图为正式美术；更换后必须重跑 `check-vita-package.py`（PNG 必须索引色、尺寸固定）。

## 6. 风险与注意

- **素材 profile 契约（已转正）**：`asset_profile_tsukihime_540p.rs` 现由真实素材包生成（175 个关键文件、25,458,232 B 启动读取，绑定 manifest sha `933fa16c…`）；错误/混包素材会在启动校验阶段被拦下。
- **语言条带**：海外版 `*ml` 归档与 UI 图集是“每语言一条竖条带”。若素材转换丢弃了非中文条带，
  需要同步修改 `languages`/条带映射，否则运行时按条带切图会错位。见 doc/04。
- **存档**：`savedata000` 是 Switch 布局；与 WoH 一致的“逐字节兼容”只在同一 build 内成立，
  跨版本（base 1.0.0 ↔ update 1.0.1）不保证可互换。
- **ATTRIBUTE2=12 只在安装时生效**：改 SFO 后必须覆盖安装。
