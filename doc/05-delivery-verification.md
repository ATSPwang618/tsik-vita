# 交付验证记录（tsik-vita，2026-10-31 会话）

> 本文记录本次交付的**可复核证据**：产物、哈希、命令与输出。所有命令都可在本仓库根目录重跑。
> 标记：**[实测]** 本机本次会话实际执行并得到该输出；**[未验证]** 无设备/像素证据。

## 1. 交付物清单

| 交付物 | 路径 | 证据 |
|---|---|---|
| PS Vita VPK（月姬 540p，真实 profile） | `release/knife-vita-tsukihime-540p.vpk` | 6,723,076 B，SHA-256 `df49c9c5e8353029d473a6bf8734e66de6b1185b3bd4594d811ad33afc232e09` |
| 构建目录 | `.work/vita/game-release-tsukihime-540p/` | `eboot.bin`/`knife.elf`/`knife.velf`/`param.sfo`/`knife.map`/`vita-game-release-build.json` |
| 构建日志 | `.work/logs/vita/game-release-tsukihime-540p-build.log` | 完整 cargo/CMake/vita-pack-vpk 输出 |
| 构建收据 | `.work/vita/game-release-tsukihime-540p/vita-game-release-build.json` | 工具链身份、逐文件 SHA、`runtime_verified:false`、`hardware_verified:false` |
| 引擎源码/工具 | `knife/`、`tools/` | 见 doc/02 的改动清单 |
| 文档 | `doc/00`–`doc/04`、根 `README.md` | 移植流程/解包/引擎/构建/素材链 |
| 540p 预处理产物（阶段 B） | `dist/Tsukihime-540p-x64/assets/` | kdu compact 输出（本会话运行，见 §4） |
| **最终 540p native codec9 素材包** | `dist/Tsukihime-540p-Vita/assets/` | 16,832 文件 + manifest，4,030,192,342 B（3.75 GiB）；manifest sha256 `933fa16c…4010e`（见 §4A） |
| 内嵌元数据（F） | `.work/assets/f-meta/` 与 `knife/` 内三件套 | profile 175 文件 / atlas 40 图集 736 成员 / stream 16,601 条；由 mofa 生成器产出并内嵌 |
| NSP 解包数据（本地，不入库） | `.work/nsp/romfs`、`.work/nsp/exefs-*`、清单 | 见 doc/01 |

## 2. 构建验证（实测）

### 2.1 环境

```text
Windows 11 → WSL pocket-ubuntu（root）
VitaSDK /opt/vitasdk：GCC 15.2.0（hard-float）
Rust nightly-2026-05-28 + rust-src；CMake 3.28.3；Ninja 1.11.1；Python 3.12.3
独立缓存：KNIFE_VITA_CACHE=/root/.cache/knife-vita-tsik（避免与 mofa-vita 的 CMakeCache 冲突）
```

### 2.2 月姬 VPK 构建

```bash
wsl.exe -d pocket-ubuntu -- bash /mnt/d/AI-CODEX/tsik-vita/.work/logs/lead-rebuild-both.sh
# 其中: python3 tools/build-vita.py --native --variant tsukihime540 game release
```

输出关键行（实测）：

```text
Finished `vita` profile [optimized] target(s) in 1.36s
PASS: KNIF00541 ATTRIBUTE2=12; 21 engine-only entries; no game data
published .../release/knife-vita-tsukihime-540p.vpk (6674061 bytes)
df49c9c5e8353029d473a6bf8734e66de6b1185b3bd4594d811ad33afc232e09 .../release/knife-vita-tsukihime-540p.vpk
```

### 2.3 包内容与 param.sfo（用 Python 独立复核）

```text
VPK 内容：eboot.bin；sce_sys/{param.sfo, icon0.png, pic0.png, livearea/contents/{bg.png,startup.png,template.xml}}；
          sce_module/{libshacccg.suprx, SceShaccCgExt-NOTICE.txt}；LICENSE；licenses/native-dependencies/*
param.sfo：TITLE_ID=KNIF00541；APP_VER=00.01；ATTRIBUTE2=12；TITLE='TSUKIHIME A piece of blue glass moon 540p'
```

复核命令：

```powershell
py -3 tools\check-vita-package.py release\knife-vita-tsukihime-540p.vpk KNIF00541 --release
py -3 -c "import zipfile; [print(i.filename) for i in zipfile.ZipFile(r'release\knife-vita-tsukihime-540p.vpk').infolist()]"
```

### 2.4 WoH 回归（证明改动不破坏原变体）

```text
python3 tools/build-vita.py --native --variant native540 game release
→ PASS: KNIF00540 ATTRIBUTE2=12; 21 engine-only entries; no game data
→ VPK 6,729,132 B（已移存 .work/baseline/，release/ 仅保留月姬交付 VPK）
```

### 2.5 Windows 入口（WSL 参数转发修复）

```powershell
py -3 tools\build-vita.py --check
→ ... Check: ready
  Selected WSL: pocket-ubuntu
```

旧代码在 WSL 2.5.10 上因 `wsl.exe` 吞单反斜杠而无法选择发行版；`tools/build-vita.py::wsl_path()`
改为先转正斜杠后已实测通过（参见 doc/03 §3.2）。

## 3. 目标数据验证（实测）

| 项 | 值 |
|---|---|
| NSP | 24,712,645,184 B，SHA-256 `baa737bd23d880afd64c1ad29209a7ca14d5d02c1aac1b4d24aa73833104c795` |
| base program NCA | `3ab52681…`，standard crypto，base exefs build id `b825b1746fa69a0a` |
| update program NCA | `9e7b0506…`，titlekey crypto（票据 0x180 明文 key 仅运行时读取），update exefs build id **`d10d239aade1d526`** |
| 引擎目标 build | `knife/knife-core/src/exe.rs` `OVERSEAS.build_id = d10d239aade1d526` → **完全一致** |
| 合并 romfs | base 1.0.0 + update 1.0.1（BKTR），16,835 文件 / 24,528,451,944 B（22.84 GiB） |
| 素材 census | w_allpac 29,267 项 / 27,982 BNTX + 1,273 JPEG；w_allpaccg 1,521 项；w_allpacml 344 项（语言条带）；w_allui 48 项、40 个多纹理 BNTX；allpachd 14,765 项（多为空占位） |

## 4. 540p 预处理（阶段 B）说明

按 mofa-vita `create_540p` 的同一方法（kdu compact：解 BNTX/JPEG → Lanczos/预乘 alpha 缩放 → BC7/JPEG 重编码 →
NXCX 包装 → .hed/.nam/.mrg 三元组），本会话对月姬海外版数据执行了 960×540 预处理：

| 归档 | 参数 | 说明 |
|---|---|---|
| `w_allpac` | `--scale 0.375 --strips 1` | 剧情图像；scale 由 exe 图像表 logical 尺寸与纹理尺寸实测推导（doc/04 §3） |
| `w_allpaccg` | `--scale 0.375 --strips 1` | 画廊 CG |
| `w_allpacml` | `--scale 0.375 --strips 4` | 多语言条带（每语言竖向一条） |
| `allpachd` | `--scale 0.75 --strips 1` | HD 归档（海外版绝大多数条目为空占位） |

本轮为 Stage B（对应 mofa-vita 链路 B 步），**四个图像归档全部转换成功（实测）**：

| 归档 | 参数 | 结果 |
|---|---|---|
| `w_allpac` | scale 0.375 / strips 1 | 29,267 项、21,876 项缩放，输出 3,113,119,744 B（2.90 GiB），830.8 s |
| `w_allpaccg` | scale 0.375 / strips 1 | 1,521 项、1,024 项缩放，输出 361,834,496 B（345 MiB），82.0 s |
| `w_allpacml` | scale 0.375 / strips 4 | 344 项、277 项缩放，输出 44,212,224 B（42.2 MiB），16.6 s |
| `allpachd` | scale 0.75 / strips 1 | 14,765 项、0 项缩放（空占位/4×4），输出 9,607,168 B，0.7 s |

产物已按 mofa-vita 的 `dist/<name>-540p-x64/assets` 约定整理为 **`dist/Tsukihime-540p-x64/assets/`**
（16,836 文件 / 8.41 GiB：转换后的四个图像归档 + 原样复制的 `stream/`、`movie/`、12 个语言字体目录、
`allscr.mrg`、`script_text.mrg`、`knife1.bfsar`、`exfont_nx01.bffnt`、saveicon/parts 等，以及待 C 步转换的原始 `w_allui.mrg`），
并写有 `dist/Tsukihime-540p-x64/asset-build.json`（stage=B、逐归档输出字节、pending 列表、`complete:false`）。
`w_allpac` 约 7,168 项保持原始字节（`DUMMY` 4×4 占位、`THUM*`/`GALLERY_FC_TH` 缩略图），符合预期；
逐项 kind/编码/逻辑-物理尺寸记录在各归档的 `.compact.tsv`。

kdu compact 的月姬适配（本仓库源码 `knife/kdu/src/compact.rs`，三处修正已集成）：
1. 归档允许列表加入 `w_allpac`/`w_allpaccg`/`allpachd`/`w_allpacml`/`w_allpachdml`/`w_allui`（+ WoH 原名）；
2. 缩略图保留从“THUMSP_TOP 之后全部保留”的位置启发式，改为按名字保留 `THUM*`/`GALLERY_FC_TH`
   （月姬的 THUMSP_TOP 位于归档中部，位置规则会错误保留一半条目）；
3. `*ml` 归档中同名的较小变体高度可能不被语言数整除：改为该条目退化为整体等比缩放，避免整档中止。

## 4A. 阶段 C–F 完成结果（实测）

| 阶段 | 结果 |
|---|---|
| C portable/KATL + 媒体 | w_allui 742 纹理 → 40 KATL（6 KIMG、2 保留）；w_allpacml 277 条带 PNG；16,601 `.opus`→`.ogg`（782 s）；134 MP4→960×540 H.264（417 s，326 MB） |
| D GXT codec8 | 23,603 项预烘焙（w_allpac：1,284 DXT1 + 20,405 DXT5 + 7,417 保留；与 mofa `pack_dxt_540.py` 同规则：DXT1 全不透明 / DXT5 含 alpha、`offline_alter` 预烘焙、条带/BORDER_PARTS 保留） |
| E codec9 | mofa `migrate-vita-native-color.py` 路径：23,603 slots（w_allpac 715 s、w_allpaccg 65 s、w_allui 14 s、parts 0.2 s），`alpha_exact=true`，加权 MAE ≈0.3–1.1/255 |
| E′ | 26 个 w_allpac 语言条带变体 → codec2 PNG（mofa 条带规则）；w_allui BORDER_PARTS KATL 按 r7 布局 NX 包装 |
| 最终包 | 16,832 文件 / 4,027,446,641 B + manifest 2,745,701 B = 4,030,192,342 B（3.75 GiB）；每个文件 size+SHA-256 对 manifest 复验通过 |
| manifest | schema `knife-540p-assets-v1` / method `native-540p-encoded-unorm-v2` / color_contract `encoded-unorm8-v1` / render=display=composite 960×540 / languages `[ja,en,zc,zt]` / codecs `[1,2,7,9]` |
| 纹理类型核验 | 全包 KATL 成员直方图：codec9 **21,389**、codec7 **2,214**、codec2 **321**，**无 3/4/8** |
| mofa 校验 | `vita-game-gxt.py::validate_gxt`：D 阶段 codec8 **23,603/23,603 pass**、最终 codec9 **21,389/21,389 pass**，0 fail；GXT 头与 WoH r7 硬件验证包逐字段一致（tag 0x00545847、ver 0x10000003、count 1、off 64、palette 0xffffffff、layout 0xa0000000、fmt 0x85000000/0x87000000、mip 1、rpad 000000） |
| F 元数据 | profile（175 关键文件/25,458,232 B，绑定 manifest sha `933fa16c…`）、atlas 索引（40 图集/736 成员/472 GXT）、stream 索引（16,601 条）——已安装进 `knife/` 并重建 VPK |

**与 mofa-vita 原链的偏差**（背景见 doc/04 §11）：D1 三个剧情归档跳过 C portable 直接由 D 解码 stage-B BC7（运行时类型/契约不变）；D2 `psp2gxt` 是 Sony SDK 时代专有工具、本机不可得，codec8 GXT 由 Pillow DDS + 本仓库 GXT 写入器生成，但逐项通过 mofa `validate_gxt` 并与 WoH r7 参考头一致；D3 无 WoH 专用 graded keep-list（已实测 Tsukihime STEC 12,900 / SNX2 1,678 / SNX3 845 / SBAS 943，engine codec9 CPU 路径覆盖，风险为 CPU 开销）；D5 26 条带变体按 mofa 规则保留 codec2。

## 5. 未验证项（必须如实保留）

1. **未在 PS Vita 真机或 Vita3K 运行过本 VPK**；包检查仅证明包结构/SFO/LiveArea/编译器身份合法。
2. **素材包与真实 profile/atlas/stream 已生成并内嵌，但未在 PS Vita 真机或 Vita3K 上验证启动/画面/性能**：
   0.375 缩放的画质、CPU BC7/JPEG 解码帧时间、显存峰值、SceAvPlayer/SceAudio 兼容性都需设备或模拟器证据。
3. 0.375 缩放的画质、CPU BC7/JPEG 解码帧时间、显存峰值均未在设备上测量。
4. LiveArea 图与 template 文案为本会话生成的占位内容，非官方美术。
5. 存档跨版本（base 1.0.0 ↔ update 1.0.1）兼容性未验证。

## 6. 复现最短路径

```bash
# 1) 环境
wsl.exe -d pocket-ubuntu -- bash -c 'cd /mnt/d/AI-CODEX/tsik-vita && export KNIFE_VITA_CACHE=/root/.cache/knife-vita-tsik && python3 tools/build-vita.py --native game release'  # 或按 doc/03
# 2) 月姬 VPK
wsl.exe -d pocket-ubuntu -- bash /mnt/d/AI-CODEX/tsik-vita/.work/logs/lead-rebuild-both.sh   # 含 native540 回归
# 3) NSP 解包（需自备 prod.keys）
py -3 tools\hactool\extract_tsukihime.py   # base exefs/romfs；update 需 doc/01 §5 的 --titlekey 步骤
# 4) 540p 预处理（阶段 B）
#    见 doc/04 §7.2 或本文件 §4 的参数表
```
