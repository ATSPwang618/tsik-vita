# tsik-vita 对照 mofa-vita 的特性完整性审计

> 本文保留修复前的审计结论。用户随后授权修复，R2 的改动、素材解码验证和交付身份见 [10-resource-repair-r2.md](10-resource-repair-r2.md)。用户已报告旧版实机运行时的素材阻断；R2 的设备复测仍待完成。

审计日期：2026-10-31。目标：`D:/AI-CODEX/tsik-vita`；基准：`D:/AI-CODEX/mofa-vita`。

**结论：当前 tsik-vita 不能认定为已经完整移植并兑现 mofa-vita 当前版本的全部 Vita 特性。** 大部分引擎和原生平台实现已继承，但发现两项高优先级缺口：月姬素材哈希没有贯穿平台构建脚本，导致内嵌 atlas/stream 索引快速路径失效；最新音效内存修复未同步。素材转换工具、构建默认值、诊断收据和月姬 feature 回归也尚未闭环。已有 VPK/素材通过离线结构与完整性核验，仍缺月姬实机运行证据。

本次只做审计、运行现有测试和隔离探针，新增报告与审计证据；未修改引擎/素材/原有 VPK，未提交或推送。文档中旧会话的操作建议仅作为被审计资料，不作为本次执行指令。

## 1. 基准身份与审计边界

| 项目 | 本次观察 |
|---|---|
| mofa 分支 | `perf/render`，工作区干净 |
| mofa HEAD | `143499848bdb6ec08a08b5b12b997cf7aea3d762`，`fix(vita): 限制音效缓存并处理 PCM 内存分配失败` |
| mofa 远端 | 只读 `git ls-remote --heads origin perf/render` 返回相同 SHA |
| tsik 版本控制 | 项目顶层及 `knife/` 未发现 Git 元数据，`git status` 返回 not a git repository；当前只能按文件哈希和已有构建收据识别快照 |
| 比对范围 | mofa 的全部 486 个受版本控制文件；逐文件 SHA-256，比对实际工作树；另外检查月姬新增源码、元数据、工具及本地交付物 |
| 文件结果 | **458 相同，26 不同，2 缺失**；文件一致数量不等于功能覆盖率 |
| 月姬现有 VPK | `release/knife-vita-tsukihime-540p.vpk`，6,723,076 B，SHA-256 `df49c9c5e8353029d473a6bf8734e66de6b1185b3bd4594d811ad33afc232e09` |
| 已有构建收据 | `source_files` 301 条全部与当前文件哈希匹配；`runtime_verified=false`，`hardware_verified=false` |

两项目都基于 knife 0.9.4；`knife/UPSTREAM.txt` 相同。tsik 的 `assets.rs`、音频三个源文件和两个性能源文件与 mofa 的 `1434998` 父提交逐字节相同，说明这部分停留在最新音效补丁之前。

基准自身的证据边界也要保留：mofa 的 [已知限制](07-已知限制与未验证项.md) 明确区分历史实机捕获与当前 960×540 代码，当前分辨率性能及部分着色器优化仍待新设备证据。这不改变 mofa 作为工程基准的地位；历史成绩不能直接转作月姬当前 VPK 的验收结果。

## 2. 特性对照矩阵

| 特性 | 对照结果 | 本次能得出的结论 |
|---|---|---|
| 原生 GXM、GPU 生命周期、同步、copy、shader 扩展、native 影片与音频输出 | 原生实现及依赖相同；`knife/vita/` 的差异仅为 4 张 LiveArea 图片和 template 文案 | 源码继承；实机效果不能由相同文件自动推出 |
| Renderer facade、Vita 渲染后端、render API | 10 个基准文件全部相同 | 540p feature 下宿主 renderer **97 项通过** |
| 960×540 scene/composite、960×544 scanout | 相同渲染实现；正式月姬构建启用 `assets-540p` | 源码配置成立；收据中的 480×270 字段是错误元数据，见 F04 |
| 堆、栈、时钟、内存预算、帧 pacing、watchdog | 平台 C 和主要预算/监测实现继承 | newlib 256 MiB、libc 4 MiB、444/222/222 MHz 请求路径相同；音效预算例外，见 F02 |
| PS 混合、group-fused、async-submit、批次 arena、依赖图、资源改名、纹理池 | 渲染和调度实现相同 | 实现已继承；PS fetch/像素等价仍需设备能力与画面证据 |
| shared-atlas、GXT ready、UI 缓存及定向预热 | 代码和月姬元数据存在 | **atlas 元数据注册与定向预热被错误 manifest 阻断**，其余共享缓存回退实现仍存在，见 F01 |
| 图像 worker、预取、动画窗口、资源 I/O、source/graded cache、灰度 R8 | 对应实现继承 | 静态覆盖；月姬素材工作集的峰值/耗时待设备验证 |
| text cache、字形页、stage-prefix、group-batch | 相同实现 | 静态覆盖；不能宣称月姬全流程已验证命中与像素正确 |
| Ogg Opus、BFSAR、独立流通道、AudioOut worker、混音与影片音轨 | 主体相同 | 音频宿主 **20 项通过**；stream 索引加速受 F01 影响；音效内存受 F02 影响 |
| 方向键、双摇杆、前触屏、快存快读、auto/skip、backlog | `vita_input.rs` 及相关游戏/UI 代码相同 | 映射已继承；月姬具体界面操作待实机验收 |
| 剧情 VM、选择/跳转、转场、文字/字体、菜单、画廊、音乐、影片、结局、流程图 | 引擎与 `Build::Overseas` 分支保留 | `knife-core` **46 项通过**；不能替代月姬路线/章节覆盖 |
| 存档布局、原子写入、备份/恢复、坏档保护 | 主要实现相同，月姬切换独立根路径 | 平台测试 **65 通过、1 失败**；失败为测试旧路径写死，见 F05 |
| 中文 ID2、数据识别、exe tables | 继承海外版逻辑，月姬使用 `w_*` 与 `knife1.bfsar` | 目标特有的正确差异；四语言素材存在不等于发布版允许切换四种语言 |
| 打包、SELF/SFO、许可证、shader 编译器/依赖 | 对应流程继承，身份改为 `KNIF00541` | 现有 VPK 包检查 PASS；默认入口和收据尚有 F04/F06 |
| 素材制作、元数据再生、性能分析 | 公共脚本大部分原样继承，月姬适配部分藏于 `.work/` | **尚未形成可独立复现和验收的完整工具链**，见 F03/F08 |

`knife-perf/src/optimizations.rs` 的 **20 个优化开关定义及 IMPLEMENTED 掩码完全相同**。这仅证明实现/开关被复制，不能证明每条优化在月姬构建与素材组合下实际生效；F01 就是已复现的反例。

魔夜专属故事和 UI（例如 `Build::Witch` 下的 teatime/专属菜单）与月姬原有 `Build::Overseas` UI 应保留各自分支。工程特性应对齐基准，游戏专属内容不应为了文件一致而混入月姬。

## 3. 已确认的问题

### F01 / P1：平台 manifest 仍绑定魔夜，月姬索引快速路径失效

证据链：

1. `knife/knife-platform-vita/src/asset_check.rs:61` 已选择月姬 profile；其清单哈希为 `933fa16cbf868d4f075a8df7dd0a6a348f9043fec20a77231429d1dc8694010e`。
2. **`knife/knife-platform-vita/build.rs:16` 只判断 `CARGO_FEATURE_ASSETS_540P`，没有判断 `CARGO_FEATURE_TSUKIHIME`**，读取 `asset_profile_540p.rs` 并生成 `audit::ASSET_MANIFEST`。
3. 新宿主构建及现有 ARM cache 的 `perf_names.rs` 均生成魔夜哈希 `a66a1318a147a901c7f76e9868e04f0551131f1128bb8dc591c242402de79d41`。
4. `assets.rs:517/975/1576/1617` 把该哈希传给音频 resolver、atlas 注册和预热。
5. `vita_atlas_index.rs:22` 遇哈希不等立即返回 None；`vita_stream_index.rs:16` 不接受错误哈希的首行，resolver 不建立内嵌索引。

隔离探针引用**真实生产索引函数、真实月姬内嵌索引、实际 build.rs 生成常量**，仅为 atlas 入参提供最小类型外壳；输出：

```text
generated_manifest=a66a1318...9d41
stream_actual=None; stream_correct=Some(".../stream/15aEDSample.ogg")
atlas_actual=false; atlas_correct=true
CONFIRMED: current manifest disables both embedded index paths
```

影响：40 个 atlas/736 个成员无法走预生成元数据注册路径，标题/剧情 UI 定向预热提前退出；16,601 条音频文件名索引不会命中，文件查找回退到有界 memo/stat。共享 atlas 缓存及常规加载仍存在，因此这项证据证明的是快速路径被关闭，不能据此断言一定无法启动或一定出现音频错误。

整改要求：build.rs、启动校验、atlas/stream 三者必须使用同一个变体 profile；补齐对应 rerun-if-changed，并验证月姬和魔夜两套 manifest 都能命中各自索引。单独重新生成索引无法修复当前问题。

### F02 / P1：未同步 mofa 最新音效内存补丁

缺少 `knife/knife-audio/src/pcm_cache.rs` 与 `knife/knife-audio/tests/fwav_memory.rs`；同时缺少这次提交在 `assets.rs`、`bfsar.rs`、`codec.rs`、`knife-perf` 和 `vita_entry.rs` 中的配套更改。

| mofa `1434998` | 当前 tsik |
|---|---|
| `PcmCache` 按实际 frames capacity 计费，16 MiB 预算，LRU 只回收空闲 Arc | `assets.rs:383` 为 HashMap，约 257 个名称后整体 clear，未按 PCM 字节预算管理 |
| 内存压力先回收空闲音效，必要时回收其它 CPU cache 后重试一次 | `assets.rs:946` 不回收音效；`sound_effect` 没有对应分配恢复路径 |
| FWAV 直接写最终交错 PCM，用 try_reserve_exact 返回可恢复错误 | `bfsar.rs:396/424` 先构建每通道浮点数组，再收集最终 PCM；普通分配失败可能终止进程 |
| sound_cache_bytes/entries 与周期 build_identity | 缺少这些新增观测项 |

复用基准原有 FWAV 回归测试，链接本次编译的 tsik `knife_audio`，第一组 4,097 帧 mono 样本得到大块申请 **49,164 B，基准要求 32,776 B**，测试退出 101。测试在额外分配断言处失败，**未执行后面的模拟 OOM 分支**。

这是已确认的源码/回归差异。它意味着长剧情音效缓存、峰值内存和失败恢复不达到当前基准；本次没有观测到真实 Vita 崩溃，不能将风险表述为已复现的设备崩溃。

整改要求：以该提交为完整单元同步音效缓存、解码分配、内存回收、指标与回归测试，再验证长音效、多音效和低内存恢复。

### F03 / P2：月姬素材流程没有全部落入公共工具

本次实际执行 README/doc 所指的公共命令：

```bash
python tools/generate-vita-atlas-index.py dist/Tsukihime-540p-Vita/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs --check
```

结果：`KeyError: 'allui.hed'`。`tools/generate-vita-atlas-index.py:20-24` 仍硬编码魔夜 `allui.*`，月姬文件名是 `w_allui.*`。

实际生成当前有效索引的是 `.work/assets/scripts/stage_f.py` 临时替换公共脚本后生成的 `generate-atlas-tsukihime.py`。为该临时脚本补上 `PYTHONPATH=tools` 后，检查通过：40 atlas、736 members、472 GXT、264 other。

关键转换流程还依赖 `.work/assets/scripts/stage_c.py`、`stage_d.py`、`stage_e.py`、`stage_e_core.py`、`stage_f.py`、`finalize_pack.py` 及条带修补脚本；`.gitignore:3` 忽略整个 `.work/`。公共 `create_540p.py`、`create_native540.py`、`migrate-vita-native-color.py` 等仍有魔夜默认路径/归档。当前素材产物存在且核验通过，但不能据此称公共源码已经提供完整月姬复现流程。

整改要求：将必要适配归并进 `tools/` 正式入口，显式参数化 archive/build/languages/scale；在独立输出目录从自备输入重跑到 profile/atlas/stream 生成，避免依赖历史临时替换。

### F04 / P2：诊断身份与构建收据仍有魔夜/临时字段

`vita_entry.rs:69/372/376` 仍输出 `tsukihime-540p-provisional` 和“convert assets and regenerate ... before play”，尽管现有月姬 profile 已真实生成。

`tools/vita-build-receipt.py:139/156` 没有适配 `KNIF00541`。现有收据同时包含：

```json
{
  "title_id": "KNIF00541",
  "assets": "external ux0:data/knife-woh/assets; no game assets in VPK",
  "fixed_render_resolution": {"scene": [480,270], "composite": [960,540]},
  "scene_pixels": [960,540]
}
```

实际 feature 对应的渲染源码为 960×540；这里是记录错误，不是证实游戏运行在 270p。F01 还会导致运行日志报出魔夜素材哈希。整改需让根路径、feature 列表、manifest、分辨率与正式 profile 标签从同一变体定义产生。

### F05 / P2：月姬 feature 下平台回归失败

开启 `knife-platform-vita/tsukihime` 和 `assets-540p` 后，平台现有 66 项测试中 **65 通过、1 失败**：

```text
storage::tests::namespaces_default_to_dev_and_require_an_explicit_production_setting
left:  ux0:data/knife-tsukihime-dev/saves/witch/savedata000
right: ux0:data/knife-woh-dev/saves/witch/savedata000
```

`storage.rs:550` 的期待值仍写死魔夜，实际路径已切换月姬。此失败本身不证明存档运行损坏；它证明变体适配后尚未维护通过的回归矩阵。整改应对照各变体常量验证开发/正式隔离，并运行月姬存取、备份与恢复流程。

### F06 / P2：默认构建身份与缓存没有按月姬项目收口

`tools/build-vita.sh:17` 默认仍为 `native540`，所以没有环境覆盖时 `python tools/build-vita.py game release` 构建魔夜 `KNIF00540`。当前月姬需显式 `--variant tsukihime540`；feature/正式身份在 release game 分支接线，不能把同名 dev 命令自动视作月姬。

脚本第 8 行默认 target cache 仍为共享 `~/.cache/knife-vita`。本机该缓存确有指向 mofa 源码目录的 CMakeCache；`doc/03-build-env.md` 已记录此冲突，并要求手动 `KNIFE_VITA_CACHE=/root/.cache/knife-vita-tsik`。整改应保留显式魔夜回归选项，让月姬项目默认身份和缓存目录匹配自身。

### F07 / 验收缺口：没有当前月姬实机运行证据

已有收据明确 `runtime_verified=false`、`hardware_verified=false`。`doc/evidence/12-hardware-render-evidence.json` 与 mofa 原文件逐字节相同，记录的是 `KNIF00540`、`mofa-perf-console-20261030-r2` 等历史魔夜捕获，不能转作月姬证明。

当前不能确认的项目包括：冷启动/标题/首段剧情、中文布局、章节与两路线、影片音画同步、触控/按键、多次保存恢复、长时间运行内存、PS fetch 能力和 540p 帧时间。验收应绑定本次 VPK SHA、月姬素材 manifest SHA、设备/固件、时钟、scene/PC 和优化掩码。

### F08 / 基准遗留的工具缺口：性能分析依赖未随项目提供

`tools/test-vita-performance.py` 本次执行报 `ModuleNotFoundError: No module named 'vita_audit_log'`。`tools/vita_audit_log.py` 与 `tools/render-audit/compare-hardware.py` 在两项目中均缺失，且被 `.gitignore` 忽略。mofa 自身文档也已说明此限制。

这是继承基准时带入的工程限制，不是 tsik 新增的运行时回归。要用相同标准验收月姬性能，仍需把必要分析工具和可公开的输入格式收口，并在干净环境跑通。

## 4. 本次重新执行的验证

| 检查 | 实际结果 | 边界 |
|---|---|---|
| 全部基准受版本控制文件 SHA-256 | 458 相同 / 26 不同 / 2 缺失 | 不是游玩覆盖率 |
| `tools/build-vita.py --check` | WSL pocket-ubuntu、VitaSDK GCC 15.2.0、nightly-2026-05-28 + rust-src：ready | 本次未重建/覆盖正式 VPK |
| 现有 VPK 包检查 | `KNIF00541 ATTRIBUTE2=12; 21 engine-only entries; no game data` PASS | 不证明能启动或正确渲染 |
| 素材全量核验 | **16,832 文件，4,027,446,641 B，大小/SHA 全匹配，无额外文件** | 与清单一致不等于与原 Switch 全流程语义等价 |
| 素材 manifest | 2,745,701 B，SHA `933fa16c...4010e`；schema/method/color 与基准契约一致 | 另见 F01 的运行时错误身份 |
| 全量 GXT 结构验证 | **21,389 / 21,389 PASS**；codec9 21,389、codec7 2,214、codec2 321，无 codec3/4/8 | 字节布局合法不证明像素与原游戏一致 |
| 月姬 profile `--check` | PASS；175 关键文件、25,458,232 B 启动校验读量 | mofa 为 37 关键文件，启动成本需设备测量 |
| 月姬 atlas/stream 内容 | 临时适配生成器的 atlas `--check` PASS；stream 与从清单重新推导的文本完全相同 | 正式入口失败，运行时索引被 F01 阻断 |
| 音频宿主测试 | **20 通过** | 不含缺失的 mofa 新音效回归 |
| core 宿主测试 | **46 通过**（36 unit + 9 archive + 1 range） | 不证明月姬所有脚本已执行 |
| perf 宿主测试 | **2 通过** | 不含设备性能测量 |
| 月姬平台测试 | **65 通过 / 1 失败** | 详见 F05 |
| 540p renderer 宿主测试 | **97 通过** | 使用 CPU SDK double，无真实 GXM 像素/时序 |
| 生产索引隔离探针 | 证实错误 manifest 拒绝 atlas/stream，正确 manifest 接受 | 无 GXM 调用；atlas 入参类型为最小外壳 |
| mofa FWAV 回归链接 tsik decoder | **失败**，49,164 B vs 32,776 B | 在 scratch 分配断言处失败，未运行模拟 OOM |
| 性能分析器测试 | **失败**，缺 `vita_audit_log` | 两项目共同限制 |

宿主测试使用 WSL `pocket-ubuntu`，`cargo +nightly-2026-05-28`，`--locked --offline`，独立审计缓存 `/root/.cache/knife-vita-tsik-audit-host`。首次联合测试在平台失败后停止，renderer 随后单独执行；未把未运行的后续测试计作通过。

## 5. 已知素材方法差异与验收要求

月姬不是把魔夜文件改名：海外版 `w_allpac/w_allpaccg/w_allpacml/w_allui`、官方四语言、`knife1.bfsar`、不同 exe tables 与图片 logical/physical 比例必须按月姬数据处理。现有 `doc/04-asset-pipeline-plan.md` 记录了 0.375 主图缩放、跳过部分中间 portable 步骤、替代 DXT 编码器、没有月姬 graded keep-list、26 个条带变体补转 PNG 等差异。

本次核实了最终字节契约和全部文件完整性，也确认 codec9 的 CPU grade/strip/raw 回退实现存在；**没有完成原图/缩放图逐像素对照或全剧情图像采样**。因此不把这些差异直接断言为画面错误，也不沿用旧文档“颜色一定正确/画质不劣”的无设备结论。需重点验收调色/亮暗/遮罩/透明边缘、多语言条带、低分辨率立绘与 CG，以及 CPU 解码/grade 峰值。

## 6. 对齐与实机验收顺序

1. 修正 F01：统一月姬 manifest 选择与构建失效追踪，要求真实 atlas/stream 注册命中，再跑魔夜回归。
2. 同步 F02：完整接入 mofa `1434998` 的 PCM 缓存、分配与恢复逻辑及已有回归。
3. 收口 F03/F06：正式月姬素材工具、默认构建身份、缓存隔离；从独立输出目录再生三件元数据。
4. 修正 F04/F05/F08：真实诊断身份、收据、feature 测试矩阵和性能分析工具；之后重建并重新包检查。
5. 冷启动并保留标题/首段剧情证据；核对 `KNIF00541`、manifest、960×540、时钟和优化能力。
6. 验收中文/UI/触控/按键、auto/skip/backlog/语音回放，save/load/quick/backup/坏档恢复。
7. 覆盖两路线与主要章节、选择/流程图、CG/音乐/影片/结局；确认跨场景和返回标题后的资源释放。
8. 长时间游玩并反复打开 UI/播放音效/切换影片，采集 heap/cache/underrun 和帧时间；分开评价 540p 普通剧情、复杂 PS/组混合和 CPU grade 场景。

判定完成的条件应同时包括：**基准实现无未说明遗漏、月姬绑定正确、公共构建/素材流程可复现、回归通过、当前 VPK 与当前素材有实机验收证据**。本次状态尚未达到这一条件。

## 7. 审计证据位置

- 稳定摘要：[13-mofa-parity-audit.json](evidence/13-mofa-parity-audit.json)。
- 全文件差异与哈希：`.work/audit/mofa-file-parity.json`。
- 全素材哈希结果：`.work/audit/assets-verification.json`。
- GXT 全量结果：`.work/audit/gxt-verification.json`。
- 宿主与渲染日志：`.work/audit/host-tests.log`、`renderer-tests.log`。
- 索引与音效复现：`.work/audit/manifest-probe.log`、`baseline-fwav-test.log`，驱动脚本 `run_parity_probes.py`。

审计产生的 `.work/audit/` 是可再生证据输出，不是正式构建或素材生产的必要输入。
