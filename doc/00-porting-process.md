# 魔法使之夜 PS Vita 移植流程调研 → 月姬重制版移植方法

> 本文是本仓库 `tsik-vita`（《月姬 -A piece of blue glass moon-》PS Vita 移植）的流程基线。
> 第 1–7 节是对参考项目 **mofa-vita**（《魔法使之夜》Switch 版 → PS Vita 移植）移植流程的阅读整理；
> 第 8 节起说明把同一方法迁移到月姬重制版时本仓库的落地方案。
> 参考项目路径：`D:\AI-CODEX\mofa-vita`（只读）。参考文档：`doc/01-架构总览.md` … `doc/08-素材与安装.md`（由 mofa-vita 原样复制而来）。
> 标记约定：**[代码]** 可在源码/脚本核对；**[未验证]** 本仓库无设备或像素证据。

---

## 1. 为什么是“重写引擎”而不是“打包原版”

Switch 版《魔法使之夜》与《月姬 -A piece of blue glass moon-》运行在同一个自研引擎（内部名 `nexl`）上：脚本是
`allscr.mrg` 里的扁平 `_CMD(args);` 指令流，舞台是 40 层图像栈，绘制到 1920×1080 画布，声音走 nn::atk，存档是固定布局的
`savedata`。Vita 无法直接执行 Switch 的 NSO（ARMv8 AArch64 + Horizon OS 系统调用 + NVN 图形）。

mofa-vita 的路线是：**基于 [AuroraWright/knife](https://github.com/AuroraWright/knife) 0.9.4 的 Rust 重实现引擎，新增
PS Vita 平台层与 GXM C 后端**，完整重放原引擎的脚本机、舞台、文字、声音、存档与菜单，素材则离线转换成 Vita 可读格式。
Vita 包只含引擎（约 7 MB VPK），游戏素材按契约单独复制到 `ux0:data/.../assets/`，编译 VPK 不需要素材。

**[代码]** 引擎写作范围见 `knife/engine-writeup.md`：549 个场景、1,035,614 条命令、42,601 条消息、93 条指令族、
40 层舞台、BFSAR + Opus 音频、140 槽存档，以及海外版（英/中）差异。同一份代码还识别《魔法使之夜》数据
（`jallpac.nam`）并用 `Build::Witch` 分支运行。

## 2. 目录规范（mofa-vita 的工程布局）

| 路径 | 内容 | 说明 |
|---|---|---|
| `README.md` | 项目说明/构建/安装/素材契约/操作表 | 发布入口 |
| `doc/` | 技术文档：架构、渲染、构建、资源、优化、性能、限制、素材 | 文档与代码同步维护 |
| `knife/` | Rust 工作区：`knife`(游戏)、`knife-core`(格式)、`knife-render`(+`-api`)、`knife-platform-vita`、`knife-audio`、`knife-perf`、`kdu`(数据工具)、`vita/`(原生 C 后端) | 唯一事实来源 |
| `tools/` | 构建与素材脚本：`build-vita.py/.sh/.ps1`、`create_540p.py`、`make-vita-assets.py`、`generate_*`、`check-vita-package.py` 等 | 从项目根执行 |
| `release/` | 构建产物 `*.vpk` | 每次成功构建自动发布 |
| `.work/` | 本地构建目录/日志/缓存（不入库） | `.work/vita/<mode>/`、`.work/logs/vita/` |
| `dist/` | 本机自备素材与转换中间产物（不入库） | `dist/<name>-540p-Vita/assets` |
| `.gitignore` | 排除 `dist/`、`.work/`、`release/`、`*.vpk`、saves 等 | 游戏数据与工具链不入库 |

构建收据（`vita-*-build.json`）记录工具链身份、逐文件 SHA-256、源码清单与 `runtime_verified:false/hardware_verified:false`；
`check-vita-package.py` 强制检查 VPK 内容白名单、`param.sfo` 身份、ATTRIBUTE2 与 LiveArea 图。

## 3. 移植流程总览（A → G）

**[代码]** `doc/08-素材与安装.md §5` 给出的素材链（工具均在 `tools/`）：

```
A. NSP + 固件 ──prepare_game.py──▶ 原始 romfs assets（含共享系统字体）
B. 540p 缩放/汉化 ──create_540p.py──▶ dist/...-540p-x64/assets      (kdu compact，逐归档)
C. 运行时归档 ──create_compact.py──▶ dist/...-Compact-x64/assets    (compact 运行时归档 + 审计)
D. Vita 纹理 ──make-vita-assets.py──▶ DXT1/DXT5 + native540 清单
E. codec9 迁移 ──migrate-vita-native-color.py──▶ GXT native UNORM（r7 契约）
F. 内嵌元数据 ──generate_vita_asset_profile_540.py / generate-vita-atlas-index.py / generate-vita-stream-index.py
G. 重新构建 VPK ──build-vita.py game release
```

构建链（`doc/03-构建与工具链.md`）：

```
python3 tools/build-vita.py --check        # 只读体检：SDK/Rust/CMake/Ninja/vendor 哈希
python3 tools/build-vita.py game release   # 正式包
```

Windows 上由 `build-vita.py` 自动分派到 WSL；固定 Rust `nightly-2026-05-28` + `rust-src`，VitaSDK（GCC/newlib/stubs/
vita-elf-create/vita-pack-vpk），7 个静态库与 `libshacccg.suprx` 随仓库校验 SHA-256。构建产物：
`.work/vita/game-release-540p/{eboot.bin,knife.elf,knife.velf,param.sfo,*.vpk,收据}` 与 `release/knife-vita-game-540p.vpk`
（TITLE ID `KNIF00540`）。

## 4. 引擎侧 Vita 适配要点

| 主题 | 做法 | 参考 |
|---|---|---|
| 画布/分辨率 | 脚本/图像逻辑坐标保持 1920×1080；物理 scene/composite 固定 960×540，扫描输出 960×544（上下各 2px） | `doc/01` §5 |
| 纹理 | 新增 KIMG/KATL 容器；Vita 用 GXT（PVRTC4/DXT1/DXT5）借用视图，不解压；CPU 兜底解码只服务调色/语言条带 | `doc/01` §7、`doc/04` |
| 渲染 | C 后端 `gxm_backend.c` + `effects_backend.inc` + 运行时 Cg 编译与磁盘缓存；batch/依赖图/纹理池/渲染目标 | `doc/02` |
| 线程 | 只有主线程碰 GXM；image worker、audio stream worker、AudioOut、console worker、watchdog 各自有界 | `doc/01` §4 |
| 预算 | 主 newlib 堆上限 256 MiB；缓存按需；ATTRIBUTE2=12 扩大 MAIN 内存 | `doc/03` §4.3、`doc/08` §3 |
| 时钟 | ARM 444 / BUS 222 / GPU 222 MHz；固定 60 Hz 逻辑帧 | `doc/01` §3 |
| 输入 | 手柄 + 前触摸：×确认 ○取消 □回想 △菜单 L/R 自动/快进 START/SELECT 快存/快读 | 根 `README.md` §操作 |
| 存档 | 与 Switch 版逐字节兼容的 `savedata`；`ux0:data/knife-woh-540p/saves/` | `doc/08` §2 |
| 素材启动校验 | 内嵌 profile 只做“关键文件个数 + 长度 + 首/末 4 KiB CRC”，不读全包 | `doc/08` §1 |

## 5. 素材契约（WoH r7）

| 项 | 值 |
|---|---|
| 清单 | `assets/vita-540p-assets.json`（1,534,377 B，SHA-256 `a66a1318…9d41`） |
| schema / method | `knife-540p-assets-v1` / `native-540p-encoded-unorm-v2` |
| 编码 | codec {1,2,7,9}；codec9 = `GxtNativeUnorm`（原生块编码、UNORM 采样） |
| 语言 | `["en","zc"]`（本机发布固定中文 ID2） |
| 启动校验 | 37 个关键文件、3,872,692 B、单 8,192 B 缓冲 |
| 容器 | 仍是 `.hed/.nam/.mrg` 三元组（0x800 扇区），只是条目换成 KIMG/GXT |

## 6. 构建/发布验证

1. `build-vita.py --check` 通过；2. `build-vita.py game release` 构建；3. 自动 `check-vita-package.py`
（TITLE ID/APP_VER/ATTRIBUTE2/SELF magic/引擎-only/LiveArea 尺寸与索引色/shader 编译器 SHA）；4. 自动写构建收据；
5. 复制 VPK 到 `release/` 并打印 SHA-256；6. （可选）`tools/verify-vita.mjs` 在 Vita3K 做端到端验证。

## 7. 从 WoH 迁移到月姬重制版的差异（本仓库要解决的问题）

| 面 | WoH（mofa-vita） | 月姬海外版（本仓库） | 影响 |
|---|---|---|---|
| 构建识别 | `jallpac.nam` → `Build::Witch` | `w_allpac.nam` → `Build::Overseas` | 引擎已有 `exe_tables_overseas.bin`（878,806 B），代码可识别 |
| 剧情图档 | `jallpac`(6.3GB)、`jallpachd`(12.8GB) | `w_allpac`、`w_allpachd` | kdu compact 目前只允许 4 个 WoH 归档名，需扩展 |
| CG 图档 | 无独立 CG 档（HD 档兼用） | `w_allpaccg`(1.9GB) | 引擎 `allpaccg` 分支已有 |
| UI/系统文本 | `allui`（71MB，替换为汉化 MOD） | `w_allui`（约 71MB，官方英/中） | 需压缩为 Vita 归档 |
| 脚本 | `allscr` 249 场景 | `w_allscr`/`allscr` 549 场景 | 引擎已支持 |
| 文本 | `script_text` 4 语言（含汉化 MOD） | `script_text` 海外版多语言 | 引擎已支持 `$` 引用 |
| 音频 | `witch.bfsar`(219MB) + `stream/`(728MB) | `knife1.bfsar`(386MB) + `stream/`(1.1GB) | 引擎按 build 选择 |
| 影片 | `movie/` 925MB | `movie/` 1.6GB | MP4 原生播放（SceAvPlayer） |
| 字体 | 每语言一套（MOD 提供 2 套） | `ja/en/zc/zt` 各一套 + Switch 共享系统字体 | 中文用官方 zc 字体；UI 系统字体需固件 |
| 素材规模 | 约 20GB 原始 → 8GB Vita 包 | 约 23GB 原始 → 预计 8–10GB Vita 包 | 转换耗时以小时计 |
| 发布身份 | KNIF00540 / `knife-woh-540p` | 本项目：KNIF00541 / `knife-tsukihime-540p` | 数据根、存档目录、TITLE 必须分开 |

**结论**：同一套方法可以迁移，但必须重做素材链（B–F 的归档清单/参数/元数据），并给构建脚本增加月姬变体；
引擎代码本身大部分已具备海外版路径。第 8 节给出本仓库的落地顺序。

## 8. 本仓库（tsik-vita）的落地顺序

1. **NSP 解包**：`prod.keys` + hactool 解 base/update NCA → 合并 romfs（`w_allpac.nam` 存在 → Overseas），
   解 exefs `uncompressed_main`（NSO）用于校验 exe 表；清单见 `doc/01-nsp-inventory.md`。
2. **构建基线**：先在原版（WoH 配置）上复现 VPK，证明 WSL/VitaSDK/Rust 链可用；见 `doc/03-build-env.md`。
3. **引擎变体**：新增 `tsukihime540` 变体——`KNIFE_VITA_VARIANT=tsukihime`，TITLE `KNIF00541`，数据根
   `ux0:data/knife-tsukihime-540p`，VPK `knife-vita-tsukihime-540p.vpk`；`vita_entry.rs` 按编译期 feature 选路径，
   资产校验换用 `asset_profile_tsukihime_540p.rs`（由生成器从最终素材包生成）；见 `doc/02-engine-port-plan.md`。
4. **素材链**：扩展 kdu compact 的归档允许列表（海外版 `w_allpac`/`w_allpacml`/`w_allpachd`/`w_allpachdml` 等），
   绕过汉化 MOD 步骤（官方中文在数据内），按 D→E→F 生成 GXT native540 包与三元组元数据；
   见 `doc/04-asset-pipeline-plan.md`。
5. **重新生成内嵌元数据**：profile / atlas index / stream index 三件套，随后重建 VPK 让元数据进入 eboot。
6. **安装**：VPK 装到 Vita（TITLE `KNIF00541`），把 `assets/` 复制到 `ux0:data/knife-tsukihime-540p/assets/`，
   从 LiveArea 启动；存档在 `ux0:data/knife-tsukihime-540p/saves/`。
7. **验证**：VPK 侧 `check-vita-package.py`（必须通过）；素材侧 profile `--check`；运行时用 Vita3K 或真机，
   在文档中逐项标注 [已验证]/[未验证]。

> 本仓库首版交付范围以 `VERSION.md` / 根 `README.md` 的“交付状态”为准：引擎 VPK 必须先构建完成并通过包检查；
> 素材包是否在本次交付内完成，以实际产物与文档记录为准，不用推测替代证据。

## 9. 本仓库实测结果（2026-10-31，补充）

| 步骤 | 实测结果 |
|---|---|
| 环境 | WSL `pocket-ubuntu` + VitaSDK `/opt/vitasdk`（GCC 15.2.0）+ Rust `nightly-2026-05-28`，`--check` ready；Windows 入口因 WSL 参数转发 bug 修好后同样可用（doc/03） |
| NSP 解包 | PFS0 → 10 个条目；base program NCA 24.6 GB（standard crypto）+ update program NCA 108 MB（titlekey crypto，票据明文 titlekey 只运行时读取）；base+update 合并 romfs = 16,835 文件 / 24,528,451,944 B；NSP SHA-256 `baa737bd…c795`（doc/01） |
| 版本对齐 | update exefs NSO build id = `d10d239aade1d526` = 引擎 `OVERSEAS` 常量，**无需重做 exe 表**；base（`b825b174…`）是旧版本，仅作数据底 |
| 引擎改动 | 新增 `tsukihime` feature + `KNIF00541`/`knife-tsukihime-540p` 变体；数据根/存档根/素材 profile/boot 文案/atlas+stream 索引按 feature 切换（doc/02） |
| VPK | `release/knife-vita-tsukihime-540p.vpk` 6,723,076 B，SHA-256 `11bf160d…d2c3c`；`check-vita-package.py` PASS（KNIF00541/ATTRIBUTE2=12/21 引擎条目/无游戏数据）；LiveArea 为月姬占位图 + 文案 |
| 回归 | `--variant native540`（WoH）同源码构建 + 包检查 PASS |
| 素材 | **完整 540p native codec9 素材包已完成**：`dist/Tsukihime-540p-Vita/assets/`（16,832 文件 + manifest，3.75 GiB；manifest sha `933fa16c…`；codecs [1,2,7,9]，直方图 9:21,389 / 7:2,214 / 2:321；mofa validate_gxt codec8/最终 codec9 全部通过）；阶段 B–F 按 mofa-vita 链路执行，偏差见 doc/04 §11；真实 profile/atlas/stream 已内嵌并重建 VPK；**真机运行未验证** |

结论：**“按 mofa-vita 方法把月姬 NSP 移植打包成 VPK”的引擎侧已完成并验证**；
剩余的是素材转换（已完成分析/测量与工具链搭建）与运行时验证，属于后续迭代，状态在 README §1/§8 与 doc/04 中如实标注。
