# TSUKIHIME 海外版 960×540 素材转换链（实测计划）

> 状态：**实测 + 计划**。本文件给出从合法自备的 Switch 海外版 NSP（base 1.0.0 + update 1.0.1，build `d10d239aade1d526`）到
> PS Vita 960×540 素材包的完整有序命令、逐归档参数、必须的源码改动、实测吞吐与时间/磁盘投影，以及
> “引擎-only / MVP / 完整 GXT codec9 包”的决策建议。所有数字来自本会话实测（标注处除外）。
>
> 实测环境：Windows 11 + WSL2 `pocket-ubuntu`；kdu 由 WSL 交叉编译为 `x86_64-pc-windows-gnu`；
> 数据源：`.work/nsp/romfs`（合并 romfs，16,835 文件 / 22.84 GiB）；参考实现：`mofa-vita` 的 WoH 540p 链（doc/08 §5-6）。
> 版权：游戏数据、字体、音视频权利归权利人；转换产物仅供持有正版的用户本机使用，仓库不包含游戏数据。

---

## 0. 结论摘要（先看这里）

| 项 | 结论 |
|---|---|
| 引擎目标 build | merge 后的 update exefs NSO `main` build id = `d10d239aade1d526` = `knife/knife-core/src/exe.rs` 的 `OVERSEAS.build_id`（base NSO 为 `b825b1746fa69a0a`，不用于运行）。引擎已支持 `Build::Overseas`（`w_allpac.nam` 探测，`assets.rs:395-534`），无需改脚本机/渲染。 |
| 归档命名 | 实际数据只有 `w_allpac`、`w_allpaccg`、`w_allpacml`、`w_allui`、`allpachd`（HD，无 `w_` 前缀）、`allpachdml`（Overseas 不用）、`parts`（Overseas 引擎不打开）。**不存在** `w_allpachd` / `w_allpachdml`；kdu 允许列表必须加入 `allpachd`。 |
| 翻译 MOD | **不需要**。官方 zc/en 字体在数据内：`zc/arshanghaisonggbpro_lt.otf`（19.2 MB）、`zt/SungASC-Medium.TTF`（9.05 MB）等 12 个字体（`en*`/`ja*`/`zc*`/`zt*` 各 1 文件，共 ~73 MB），直接从 romfs 原样复制。也不需要从固件提取 Nintendo 共享字体。 |
| kdu 允许列表 | 已按提议集成到 `knife/kdu/src/compact.rs`（见 §6.1），但需再修正一处：`w_allpachd`→`allpachd`。 |
| 缩略图启发式 | **必须改**：kdu 用 “第一个 `THUMSP_TOP` 之后全部保留” 的位置启发式；`w_allpac` 的 `THUMSP_TOP` 在**索引 14,658（整档中部）**，会把 29,267 条中的 14,609 条原样拷贝（不缩放）。改为按名字保留 `THUM*`。 |
| 多纹理 BNTX | `w_allui` 48 条中有 40 条是多纹理 BNTX（最多 73 纹理/条，共 701 纹理）：kdu compact 的 `ensure!(textures.len()==1)` 会直接报错。**w_allui 不走 kdu compact**，走 WoH 同款 `create_compact`（`kdu export-bntx` → portable PNG/KATL）路径。 |
| 语言条带 | `w_allpacml` 为 4 语言竖条带（物理高 = 4×单语言高，如 1892×6828 / 4=1707），`--strips 4`。`w_allui` 不是条带而是**按语言拆分的独立图**（`*_JA/_EN/_ZC/_ZT`）。官方数据含 ja/en/zc/zt 四语言。 |
| 规模 | `w_allpac` 29,267 条（27,982 BNTX + 1,273 JPEG + 12 data；7,294 个 4×4 占位、3 个 THUM、1,282 data/PNG/MZP 保留）；转换条目约 **21,917**。 |
| kdu 实测吞吐 | 8 jobs、scale 0.5：**52–53 Mpx/s（源像素）**，12.6–13.9 图/s；两个不同区域采样一致。 |
| 投影（scale 0.5） | `w_allpac` ≈ **16 分钟**（50.08 Gpx 源像素）/ 输出 ≈ **11.9 GB**；`w_allpaccg` ≈ 1.5 分钟 / ≈0.9 GB；`w_allpacml` ≈ 24 s / ≈0.31 GB；`allpachd` <2 s。 |
| 投影（scale 0.375，推荐） | 时间基本不变（解码为主，≈15–16 分钟总量），输出约 **×0.56**：`w_allpac` ≈6.6 GB、`w_allpaccg` ≈0.5 GB、`w_allpacml` ≈0.17 GB。 |
| 完整链可行性 | kdu 阶段 ~16–18 分钟可完成；但后续 portable（PNG/KATL + 16,601 opus→ogg + 134 mp4→H.264）、GXT codec8、codec9 迁移、三件套元数据与 VPK 合计估计 **60–100 分钟机器时间、峰值约 20–30 GB 磁盘**——本会话剩余时间不可行。建议本会话交付引擎-only VPK + 本文档；完整包下一时段按 §7 顺序执行（可断点续跑）。 |
| 建议 | 先交付**引擎-only VPK（已完成并 PASS）**；若必须“能进标题/序章”的 MVP，用 §7.2 的 compact-BC7 包（~20–25 分钟，跳过 DXT/codec9），但 Vita 上 CPU 解 BC7/JPEG 的性能与本会话均未验证；**完整可玩包必须走 §7.3 的完整 GXT codec9 链**。 |

---

## 1. 前提与输入（实测值）

| 输入 | 值 |
|---|---|
| NSP | `switch原版游戏/TSUKIHIME A piece of blue glass moon [B+U65536].nsp`，24,712,645,184 B（PFS0，10 条目） |
| base program NCA | `3ab52681b30ddd44ff15a06b4959859f.nca`，24,603,131,904 B，Standard crypto，base exefs build id `b825b1746fa69a0a` |
| update program NCA | `9e7b05062ec013dcd3390e521d02427b.nca`，108,475,392 B，**Titlekey crypto**，Rights ID `010057A01E4D48000000000000000012` |
| titlekey | 本 dump 的 ticket 在 `+0x180` 存明文 16 B；运行期从 `.tik` 读取后以 `--titlekey=` 传给 hactool，**不落盘、不写文档** |
| 合并 romfs | `.work/nsp/romfs`，16,835 文件 / 24,528,451,944 B（22.84 GiB）；`w_allpac.nam` 存在 → 引擎判定 `Build::Overseas` |
| 原始归档 | `w_allpac.mrg` 16,748,290,048 B（注意不是 base-only 的 16,754,061,312 B：update 补丁改了部分条目）、`w_allpaccg` 2,074,607,616、`w_allpacml` 197,275,648、`w_allui` 191,707,136、`allpachd` 9,607,168、`allpachdml` 137,216、`parts` 411,648 |
| 共享数据 | `knife1.bfsar` 405,170,048；`allscr.mrg` 9,584,960；`script_text.mrg` 12,601,368；`exfont_nx01.bffnt` 42,720；`shader/` 59 文件 509,240；`stream/` 16,601 个 `.opus`（1,179,214,412 B）；`movie/` 134 个 `.mp4`（3,623,696,240 B）；12 个语言字体目录（~73 MB） |
| 工具 | kdu.exe（`cargo +1.99.0 build --locked --release -p kdu --target x86_64-pc-windows-gnu`，WSL/mingw）；hactool（`tools/hactool/hactool.exe`，2020 版，**无 `--tik`**，需 `--titlekey=`） |

### 1.1 合并 romfs 提取（本次已执行，命令保留以便复现）

```bash
# 在 WSL 内、.work/nsp 目录。先解 base（普通 crypto），再解 update（Titlekey；--basenca 合并补丁）。
cd /mnt/d/AI-CODEX/tsik-vita/.work/nsp
KEYS='C:\Users\26241\AppData\Roaming\Ryujinx\system\prod.keys'
../../tools/hactool/hactool.exe -k "$KEYS" --disablekeywarns -t nca \
    --basenca=nca/3ab52681b30ddd44ff15a06b4959859f.nca \
    --titlekey="$TITLEKEY" \
    --romfsdir=romfs nca/9e7b05062ec013dcd3390e521d02427b.nca
# TITLEKEY = python3 -c "import sys;d=open('nca/010057a01e4d48000000000000000012.tik','rb').read();print(d[0x180:0x190].hex())"
# 注意：旧 extract_tsukihime.py 不带 --titlekey，会得到空 romfs + "section corrupted"；用上面的命令修正。
```

---

## 2. 逐归档实测画像（census，read-only）

脚本：`.work/assets/scripts/inspect_archives.py`（建议转正为 `tools/inspect_romfs_archives.py`）。
输出：`.work/assets/inventory/*.inventory.json`、`archives-summary.json`、`romfs-files.json`。

| 归档 | entries | 容器构成 | BNTX 格式（纹理数） | 尺寸画像 | THUM 位置 | multi-texture |
|---|---|---|---|---|---|---|
| `w_allpac` | 29,267 | 27,982 BNTX + 1,273 JPEG + 6 PNG + 6 data；NXGZ 20,688 / NXZ 7,294 / raw 1,285 | `0x2006`×27,925、`0x1d01`×49、`0xb06`×8 | 7,294×4×4 占位；大图 2576×1456×420、2592×1472、1420×860…；最大 2,624×2,896 | `THUMSP_TOP`=14,658（之后 14,609 条） | 0 |
| `w_allpaccg` | 1,521 | 920 BNTX + 600 JPEG；`GALLERY_FC_TH` 495 条 NXGZ 缩略图 | `0x2006`×920 | CG 2560×1620/2560×2000/3000×1440/4000×2614/4961×3780…；缩略图 430×243×491 | `THUMCG_TOP`=1,025（`GALLERY_FC_TH` 1,026..1,520） | 0 |
| `w_allpacml` | 344 | 339 BNTX + 5 data；NXGZ 329 | `0x2006`×290、`0x1d01`×49 | **4 语言条带**：1892×6828×62（单语言 1892×1707）、1920×4320×27、1280×2880×8、1404×3376…；另有 49 个 RULE 1280×720 | `THUMSP_TOP`=196；`IMG` 区间 52–191 与 199–338（THUM 在中间！） | 0 |
| `w_allui` | 48 | 46 BNTX（701 纹理）+ 1 DAT + 1 BIN；NXGZ 42 / NXCX 4 | `0x2006`×701、`0xb06`×5 | 1920×1080×75、1707×488、1332×452、4095×39、424×264…；按 `_JA/_EN/_ZC/_ZT` 拆图 | `CG_THUMB_PARTS_*`=43–46 | **40 条**（每图集 20/73 个纹理，含 `dummy` 4×4） |
| `allpachd` | 14,765 | **14,705 `NOFILE.EXISTS` 空占位** + 49 RULE(1280×720 BNTX) + 8 | `0x1d01`×49、`0x2006`×5 | RULE 1280×720；其它 4×4 | `THUMSP_TOP`=14,759 | 0 |
| `allpachdml` | 67 | 63 DUMMY(4×4 BNTX) + 4 data | `0x2006`×63 | 4×4 | 63–65 | 0 |
| `parts` | 5 | 5 BNTX（无 `.nam`，按索引） | `0x2006`×5 | 1920×1080 | — | 0 |

关键判读：

1. **`w_allpac` 的 THUM 在中部**：索引 0..14,657 是 BG/立绘/特效，`14,658–14,660` 是 `THUMSP_TOP/THUMBG_TOP/THUMSTAND_TOP`，其后的 14,609 条继续是立绘（`SIE_*/ARU_*/Z*/IMG…`）。**位置启发式在此归档会保留一半档案不缩放**，必须改成按名字 `THUM*` 保留（`w_allpac` 仅 3 条、`w_allpaccg` 1 条、`w_allpacml` 3 条、`w_allui` 4 条 `CG_THUMB_PARTS_*`）。
2. **多纹理只在 `w_allui`**：kdu compact 的 `convert()`（`compact.rs:74-81`）对 `textures.len()!=1` 直接 `ensure!` 报错；因此 `w_allui` 不进 kdu compact，改走 portable/KATL 链（WoH 的 `create_compact.py` 对 `allui` 就是这么做的：`kdu export-bntx` → `encode_portable` → `KATL`）。
3. **`allpachd` 几乎为空**：14,705 条 `NOFILE.EXISTS`（stored=0）→ kdu 原样保留（0 字节），实际只有 49 张 RULE + 少量 data，几乎不花时间。
4. **`allpachdml` / `parts` 对 Overseas 引擎无用**：`assets.rs:533` 只在 `Build::Witch` 打开 `allpachdml`；`image_archives()`（`assets.rs:772`）对 Overseas = `[w_allpac, w_allpacml, w_allpaccg, w_allui, allpachd]`，不含 `parts`。**素材包不必包含** `allpachdml.mrg/hed/nam` 与 `parts.mrg/hed`（引擎启动校验只查清单列出的文件；但为最小化风险也可原样带上，总量 <0.6 MB）。

---

## 3. 缩放/条带选择（实测推导）

### 3.1 设计空间与实测比例

用 update exefs 的 `main`（hactool `--uncompressed` 解出 10,261,816 B 的 flat NSO）跑
`kdu tables --exe <uncompressed_main> --all` 得到 14,744 条图像**逻辑尺寸**（f32），抽 649 个场景 id。
与归档 BNTX 物理尺寸按名字（去扩展名）匹配（脚本 `.work/assets/scripts/analyze_scale.py`）：

- `w_allpac`：21,918 条可匹配；物理/逻辑宽高比中位数 **2.0**（分簇 0.37/0.38 与 2.25 见下），主簇
  `scale_for_0.75 = 0.75·logical/physical` ≈ **0.375**（7,334 条 0.38 + 5,977 条 0.37）。
- `w_allpacml`：280 条匹配，主簇同样 0.375（109 条 0.38 + 85 条 2.25 + 27 条 0.25 + 27 条 1.5）。
- `w_allpaccg`/`w_allui`/`allpachd`：CG/UI/规则图不在 exe 图像表（脚本按名字加载），无法直接匹配。
- 逻辑尺寸直方图（exe 表）：1288×732×420、1280×724×277、702×424×270、640×362×89、1296×740×82…
  即海外版设计空间是 **1280×720 级**（`w_allpac` 的整屏 BG `IMG0000` 逻辑 1280×728、物理 2560×1449 = 2×）。

**推导**：Switch 海外版全屏内容的源纹理物理尺寸约为逻辑设计尺寸的 **2×**；Vita 渲染目标是 960×540
（=1280×720 × 0.75），因此“屏幕像素 1:1”的重采样系数 = **0.75 / 2 = 0.375**。
这就是 WoH 链里 `jallpac 0.75`（源物理 1280）的海外版等价物。

### 3.2 建议参数（可调，取 scale 越小越省内存/存储）

| 归档 | `--scale` | `--strips` | 理由 |
|---|---|---|---|
| `w_allpac` | **0.375**（质量优先可 0.5） | 1 | 主簇物理=2×逻辑 → 540p 屏幕 1:1；0.5 会得到 1280 宽（1.33× 超采样，输出 ×1.78 存储） |
| `w_allpaccg` | **0.375** | 1 | CG 物理 2560×1620 等，全屏显示；与 `w_allpac` 同基准 |
| `w_allpacml` | **0.375** | **4** | 4 语言竖条带；kdu 按 `--strips 4` 先切条再各自缩放（保证 BC7 块不跨语言） |
| `allpachd` | **0.75** | 1 | RULE 源物理 1280×720（设计尺寸 1:1），0.75 → 960×540 |
| `w_allui` | 不做 kdu 缩放（native） | — | 多纹理，走 portable/KATL；如需省内存后续在 create_compact/pack_dxt 增加 0.5 缩放（源码改动，见 §6.4） |
| `allpachdml`/`parts` | 不处理 | — | Overseas 引擎不用 |

> 风险：`w_allpac` 中约 4,300 条“低分辨率立绘”（物理 ≈ 逻辑/3，簇 2.25）在 0.375 下会变成逻辑/8，
> 相对 Switch 的 3× 放大变成 6× 放大，画质下降明显；0.5 可缓解但存储约 11.9 GB。
> 这是 kdu compact 只支持“整档单一 scale”的固有限制；若要兼顾，需要给 kdu 加“按条目类别两档 scale”的源码改动（未实现）。

---

## 4. kdu compact 实测（bounded smoke，非全量）

工具：`.work/assets/tools/kdu-smoke.exe` = `knife/kdu` 源码副本 + 允许列表（与本次集成一致）+ 仅用于测量的
`KDU_SAMPLE_START/KDU_SAMPLE_COUNT` 窗口与 `SMOKE` 统计行；转换核心与 `kdu.exe` 相同。原始 `kdu.exe` 仍可复现构建。

采样命令（实际执行）：

```powershell
$env:KDU_SAMPLE_START='59';  $env:KDU_SAMPLE_COUNT='400'   # BG/JPEG 区
.work\assets\tools\kdu-smoke.exe --romfs .work\nsp\romfs compact w_allpac .work\assets\smoke\w_allpac-400 --scale 0.5 --jobs 8 --strips 1
$env:KDU_SAMPLE_START='9000'; $env:KDU_SAMPLE_COUNT='400'  # 立绘/BC7 区
.work\assets\tools\kdu-smoke.exe --romfs .work\nsp\romfs compact w_allpac .work\assets\smoke\w_allpac-sprites --scale 0.5 --jobs 8 --strips 1
```

| 采样区 | 条目 | 源像素 | 输出 | 耗时 | 图/s | 源 Mpx/s | 输出 MB/s |
|---|---|---|---|---|---|---|---|
| 59–459（BG/JPEG 为主，301 jpeg + 99 bc7） | 400 | 1,689.85 Mpx | 181,729,280 B | 31.83 s | 12.57 | **53.09** | 5.71 |
| 9000–9400（立绘/BC7 为主） | 400 | 1,498.26 Mpx | 109,662,208 B | 28.77 s | **13.90** | 52.07 | 3.81 |

`.compact.tsv` 实测（`w_allpac-400`）：`kind` 只有 `jpeg` 与 `bc7`；KIMG 逻辑尺寸=源物理尺寸、
物理=0.5×（例：`IMG0000.JPG` 2560×1449 → 1280×725；`IMG0001.NXGZ` 3560×1440 → 1780×720）；
`w_allpacml` 需 `--strips 4`。输出外层均为 `NXCX`（zlib）包装，KIMG 编码为 `1 (Jpeg)` 或 `3/4 (Bc7Srgb/Bc7Unorm)`，
**没有 codec9**（codec9 只出现在后续 GXT 迁移阶段）。

### 4.1 全量投影（scale 0.5 与 0.375）

源像素来自 census（BNTX 纹理像素 + JPEG SOF 尺寸，`project_workload.py` + `jpeg_census.py`）；
吞吐取 52.5 Mpx/s（两次采样平均）。

| 归档 | 可转条目 | 源像素 | 0.5 时间 | 0.5 输出 | 0.375 输出（估） |
|---|---|---|---|---|---|
| `w_allpac` | 21,917（20,646 BNTX + 1,271 JPEG；7,336 占位 + 3 THUM + 1,282 data 保留） | 50,081.5 Mpx | **≈954 s（15.9 min）** | ≈11.9 GB（BC7 1 B/px + JPEG） | ≈6.6 GB |
| `w_allpaccg` | 1,519（919 BNTX + 600 JPEG） | 4,640.4 Mpx | ≈88 s（1.5 min） | ≈0.90 GB | ≈0.50 GB |
| `w_allpacml` | 326（strips=4） | 1,234.8 Mpx | ≈24 s | ≈0.31 GB | ≈0.17 GB |
| `allpachd` | 49 | 45.2 Mpx | <2 s | ≈11 MB | ≈6 MB |
| **合计（kdu 阶段）** | **~23,811** | **~56.0 Gpx** | **≈1,070 s（~17.8 min）** | **≈13.1 GB** | **≈7.3 GB** |

> 说明：输出字节按实测 mix 外推（BC7=1 B/px、JPEG≈0.18 B/px 目标像素）；0.375 的耗时不减半（源解码 +
> Lanczos + zlib 仍占主导，且 decode 与 scale 无关），预计 **15–17 分钟**；磁盘峰值需按 §7 顺序控制。

---

## 5. 后续阶段成本（本会话未全量实测，按链长与 WoH 参考估算）

| 阶段 | 工具 | 输入→输出 | 估计时间 | 估计输出 |
|---|---|---|---|---|
| B kdu compact 4 档 | `kdu.exe compact` | romfs → compact 档（KIMG BC7/JPEG+NXCX） | ~18 min | 7.3 GB（0.375） |
| C portable | `create_compact.py` | compact → PNG/JPEG/KATL/Ogg/H.264 | 20–40 min（16,601 opus→ogg、134 mp4→960×540 是大头） | **未知，PNG 可能远大于 B**；保守 10–20 GB |
| D GXT codec8 | `pack_dxt_540.py`（改） | portable → DXT1/5 预烘焙 GXT | 10–20 min | ~½ B 量级 |
| E codec9 | `migrate-vita-native-color.py`（改） | codec8 → codec9（第二次有损 DXT），jobs=2 | 10–20 min | 与 D 同量级 |
| F 元数据 | 3 个生成器（见 §6.5） | 素材包 → 3 个 .rs/.txt | 1–2 min（含全量 SHA-256 读盘） | — |
| G VPK | `build-vita.py --variant tsukihime540 game release` | 源码 → VPK | 2–4 min | — |

峰值磁盘：B（7.3 GB）+ C（~10–20 GB）+ D/E（各 4–7 GB）叠加时可能 20–30 GB。当前 free ≈56.6 GB，
够但需要**逐阶段删除中间产物**（B→C 后可删 B，C→D 后可删 C…）。

---

## 6. 必须的源码/工具改动（Lead 集成，精确清单）

### 6.1 `knife/kdu/src/compact.rs`（已集成允许列表，仍需 3 处修正）

1. **已集成（本次）** 允许列表（原 line 112，现 line ~114-117）：
   ```rust
   ensure!(matches!(name, "w_allpac" | "w_allpaccg" | "w_allpachd" | "w_allpacml" | "w_allpachdml" | "w_allui"
       | "jallpac" | "jallpachd" | "allpacml" | "allpachdml"), "...");
   ```
   **修正**：实际数据是 `allpachd`（无前缀），不存在 `w_allpachd`/`w_allpachdml`。建议改为：
   `"w_allpac" | "w_allpaccg" | "w_allpacml" | "w_allui" | "allpachd" | "jallpac" | "jallpachd" | "allpacml" | "allpachdml"`。
2. **缩略图启发式（必须改）**：删掉
   ```rust
   let thumbnail_start = a.entries().iter().position(|e| e.name.starts_with("THUMSP_TOP")).unwrap_or(a.entries().len());
   ```
   与 `convert()` 的 `index >= thumbnail_start` 分支，改为**按名字**：`e.name.starts_with("THUM")`（`w_allpaccg`
   的 495 条 `GALLERY_FC_TH` 缩略图建议也按名保留，否则会重新编码 430×243 图，代价不大但无意义）。
3. **多纹理**：保持 `ensure!(textures.len()==1)` 不变（w_allui 不走 kdu）；若将来要让 kdu 直接吃 `w_allui`，
   需新增“多纹理 → KATL”编码分支（参考 `create_540p.py` 的 `convert_atlas`），属于新功能，非本链阻塞。
4. 测量用 `KDU_SAMPLE_START/COUNT` 与 `SMOKE` 行只存在于 `.work/assets/kdu-smoke/` 副本，**不要集成**。

### 6.2 `tools/create_540p.py`（TSUKIHIME 变体或参数化）

- `ARCHIVES` 改为：
  ```python
  ARCHIVES = [('w_allpac', 0.375, 1), ('w_allpaccg', 0.375, 1),
              ('w_allpacml', 0.375, 4), ('allpachd', 0.75, 1)]
  ```
- 去掉 MOD 必需（`required` 集合与 `--mod` 参数）：官方数据已含 zc/en 字体，**无汉化 MOD 步骤**；
  `golden` 校验改为对 TSUKIHIME 自身的 `asset-build.json`。
- 输出目录/清单名按 TSUKIHIME（如 `dist/Witch-on-the-Holy-Night-*` → `dist/Tsukihime-*`，`doc/540p-assets.json` → `doc/540p-assets-tsukihime.json`）。

### 6.3 `tools/create_compact.py`

- `ARCHIVES` 改为：`[('w_allpac',1),('w_allpaccg',1),('w_allpacml',4),('w_allui',1),('allpachd',1)]`；
  **不要**包含 `parts`/`allpachdml`。
- `prepare_bntx` 用 `kdu-compact.exe`（= kdu 同一 binary，`export-bntx`）；`w_allui` 多纹理会被导出为
  `<index>_<k>.png`、`convert_entry` 自动聚成 `KATL`（`archive=='w_allui'` 分支已存在，把 `'allui'` 判断改成集合即可）。
- `convert_entry` 的 `force_png = archive == 'allui'` → 改为 `archive in ('allui','w_allui')`。
- 音频：`stream/` 16,601 个 `.opus`（`nopus_to_ogg`）；电影：`movie/` 134 个 `.mp4` 全部 `scale=960:540:flags=lanczos`，
  文件名带 `_en/_zc/_zt` 变体也一并转（与 WoH 相同）。
- 语言标签：`export_image` 的 `('ja','en','zc','zt')` 4 条带假设对 `w_allpacml` 成立。

### 6.4 `tools/pack_dxt_540.py` / `make-vita-assets.py` / `create_native540.py` / `migrate-vita-native-color.py`

- 归档列表统一改为 TSUKIHIME 五档（见 §6.3）。
- `make-vita-assets.py`：`DEFAULT_ARCHIVES="w_allpac,w_allpaccg,w_allpacml,w_allui,allpachd"`；
  `--keep` 文件需为 TSUKIHIME 重新生成（WoH 的 `graded-images.txt` 是按 WoH 图名筛选的）：至少保留
  `RULE_*`（1280×720 规则/遮罩，WoH 也是 keep）与 `BORDER_PARTS` 类 CPU 读回图集；建议先用“全部转换 + 抽检”跑通，再按截图补 keep。
- `create_native540.py`：`ARCHIVES`/`SHARED`/`SHARED_DIRS` 改为 TSUKIHIME：
  `ARCHIVES=['w_allpac','w_allpaccg','w_allpacml','w_allui','allpachd']`；
  `SHARED=['allscr.mrg','script_text.mrg','knife1.bfsar','exfont_nx01.bffnt']`；
  `SHARED_DIRS=['en','en2','en3','ja','ja2','ja3','zc','zc2','zc3','zt','zt2','zt3','movie','shader','stream']`；
  `LANGUAGES=['ja','en','zc','zt']`（官方数据）；`LOOSE_IMAGES` 改为 `saveicon*.tga` + `titlemenu_(c)type-moon.tga`
  （`corp.tga` 不存在于 TSUKIHIME romfs）。
- `migrate-vita-native-color.py`：`ARCHIVES` 同上；`probe()` 的 `jallpac.hed` 改 `w_allpac.hed`；
  结尾 `assert receipt['converted_slots']==22176` 必须改为 TSUKIHIME 实际值（或参数化/去掉）。
- `pack_dxt_540.py`：`--archives` 默认值、`rewritten` 集合与 `convert_archive()` 的来源目录按 TSUKIHIME 改；
  `KEEP_ATLAS`（`BORDER_PARTS.NXZ`）在 TSUKIHIME 不存在 → 需实测确定 CPU 读回图集（候选：`MASK_TOP`、`BG_TOP` 等 atlas 类）。
- `w_allui` 缩放（可选）：目前 portable 阶段保持 native；若要省面积，在 `create_compact.encode_portable` 增加目标尺寸
  （w_allui 全屏 UI 1920×1080 → 0.5），并同步 KATL 成员 logical/physical。**这是新功能，本会话未实现**。

### 6.5 元数据三件套（TSUKIHIME 变体）

```bash
# 素材包生成后（<PACK>/assets 下应有 vita-540p-assets.json）
python3 tools/generate_vita_asset_profile_tsukihime_540.py --assets <PACK>/assets          # --provisional 为空 profile
python3 tools/generate-vita-atlas-index.py <PACK>/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs
python3 tools/generate-vita-stream-index.py <PACK>/assets/vita-540p-assets.json knife/knife/data/vita_stream_index_tsukihime_540p.txt
python3 tools/build-vita.py --variant tsukihime540 game release
```

Genprofile 生成器必须按 TSUKIHIME 实际值放宽/替换旧断言：`streams == 9470` → **16,601**（`stream/` 文件数）；
`languages == ['en','zc']` → `['ja','en','zc','zt']`；`codecs ⊆ {1,2,7,9}` 保留（codec9 迁移后成立）；
schema/method/color_contract 保持与引擎契约一致（`knife-540p-assets-v1` / `native-540p-encoded-unorm-v2` /
`encoded-unorm8-v1`），否则 `asset_profile_540p` 的启动校验链不一致。`w_allui` 的 KATL 索引生成器当前硬编码
`allui.hed/nam/mrg` → TSUKIHIME 变体需改读 `w_allui.*`（`generate-vita-atlas-index.py:20`）。

---

## 7. 有序执行命令（下一时段直接照做）

前置：`.work/nsp/romfs` 已存在（合并版）；`tools/kdu.exe`、`tools/kdu-compact.exe` 由 repo 源码构建
（`bash .work/assets/scripts/build-kdu-windows.sh`，sha256 见 §8.1）；`ffmpeg`/`ffprobe` 在 PATH。

### 7.1 目标目录约定（建议，与 WoH 对齐）

```
.work/assets/b-compact/      # kdu compact 输出（5 档 .mrg/.hed/.nam/.compact.tsv）
.work/assets/c-portable/     # create_compact 输出（assets/ + media-manifests/ + image-source/）
.work/assets/d-dxt/          # pack_dxt_540 输出（GXT codec8）
.work/assets/e-codec9/       # migrate 输出 + vita-540p-assets.json（native-540p-encoded-unorm-v2）
```

### 7.2 MVP：compact-BC7 包（~20–25 分钟，跳过 DXT/codec9；性能未验证）

```bash
# 1) kdu compact（B）。STOP: 当前 repo kdu 的 THUM 位置启发式会保留 w_allpac 一半条目 → 必须先修 §6.1-2。
mkdir -p .work/assets/b-compact
for a in "w_allpac 0.375 1" "w_allpaccg 0.375 1" "w_allpacml 0.375 4" "allpachd 0.75 1"; do
  set -- $a
  .work/assets/tools/kdu.exe --romfs .work/nsp/romfs compact "$1" .work/assets/b-compact \
      --scale "$2" --strips "$3" --jobs 8
done
# 2) 共享文件原样复制：allscr.mrg script_text.mrg knife1.bfsar exfont_nx01.bffnt
#    12 个语言字体目录、movie/、shader/、stream/（MVP 可先不转 stream/movie：能进标题/序章即可验证）
# 3) 清单：先用 create_native540 变体（--manifest-only 不行，需要真实转换记录）或用简化 manifest
#    写 vita-540p-assets.json（schema/ render/display/composite 契约字段需齐全，codecs 按实际 [1,2,3,4,7]）
# 4) 生成器：profile 生成器需允许 codecs 含 3/4（见 §6.5），atlas/stream 索引同 §6.5
# 5) python3 tools/build-vita.py --variant tsukihime540 game release
```

风险：Vita 上 CPU 解 BC7（bcdec）+ JPEG 的帧时间未验证；不改 GXT 时 `gxt_native` 快速路径全部失效，
初期只能验证“能进标题/菜单/文本”，不适合作为最终交付。

### 7.3 完整包：GXT codec9（推荐，估计 60–100 分钟，可断点续跑）

```bash
# B. kdu compact（同 7.2-1；0.375；w_allpac≈16 min，可断点：kdu 输出 .partial 存在时需人工清理后重跑）
# C. portable（改好的 create_compact）：python -u tools/create_compact.py --jobs 6 --ffmpeg <ffmpeg>
#    → 生成 PNG/JPEG/KATL + media-manifests；音频 16,601→ogg、电影 134→960x540 H.264
# D. GXT codec8：python -u tools/make-vita-assets.py --compact <C>/assets --out .work/assets/d-dxt --jobs 8 --keep <tsukihime-keep.txt>
# E. codec9：python -u tools/migrate-vita-native-color.py --source <D> --output .work/assets/e-codec9 --jobs 2
# F. 元数据：见 §6.5（三个生成器，先 --check 后写入）
# G. VPK：python3 tools/build-vita.py --variant tsukihime540 game release
#    然后 tools/check-vita-package.py 自动 PASS；拷 assets/ 到 ux0:data/knife-tsukihime-540p/assets/
```

每阶段结束删除上一阶段中间产物（B→C 后删 B、C→D 后删 C……），保证峰值 <30 GB。

---

## 8. 实测脚本与产物（可转正到 tools/）

### 8.1 工具构建（已验证）

| 产物 | sha256 | 说明 |
|---|---|---|
| `.work/assets/tools/kdu.exe`（repo 源码，已含允许列表） | `9a40b7a910da8a1ba9fc48cbfb8c51580b3ba579a6cc3a5edc17199ae84257f7` | WSL：`cargo +1.99.0 build --locked --release -p kdu --target x86_64-pc-windows-gnu -j 6`（CARGO_TARGET_DIR=~/.cache/knife-windows-x64，mingw gcc/g++） |
| `.work/assets/tools/kdu-smoke.exe`（测量副本） | `fac34d11980ecd5232919a8d3dc97aa0d8f54fc8206524bcdfa6d492a39e7b46` | 允许列表 + `KDU_SAMPLE_START/COUNT` + `SMOKE` 行；不集成 |
| 构建脚本 | `.work/assets/scripts/build-kdu-windows.sh`、`build-kdu-smoke.sh` | 建议转正为 `tools/build-kdu-windows.sh`（或在 `build-windows.sh` 里已有 `--kdu` 基础上加 `--kdu-smoke`） |

### 8.2 建议转正的分析脚本（均在 `.work/assets/scripts/`）

| 脚本 | 建议路径 | 用途 |
|---|---|---|
| `inspect_archives.py` | `tools/inspect_romfs_archives.py` | 只读 census：条目数、容器/编码/尺寸、多纹理、THUM 位置、条带候选 |
| `romfs_inventory.py` | `tools/inventory_romfs.py` | romfs 文件清单 JSON + 目录汇总 |
| `jpeg_census.py` | 合并进 `inspect_romfs_archives.py` | JPEG SOF 尺寸统计（投影用） |
| `analyze_scale.py` | `tools/analyze_asset_scale.py` | exe 逻辑尺寸 × 归档物理尺寸 → 缩放系数推导 |
| `project_workload.py` | 合并进 `analyze_asset_scale.py` | 每档可转条目/源像素投影 + 时间估算 |
| `romfs_inventory_summary.py` | 合并进 `inventory_romfs.py` | 摘要打印 |
| `extract-merged-romfs.sh` | Lead 已有等价脚本 | hactool `--basenca --titlekey` 合并提取 |

---

## 9. 未验证项与风险

1. **完整链未端到端跑过**：D（GXT codec8）/E（codec9）/C（portable）在本会话未全量执行；§5 的时间/体积是估算。
2. **Vita 运行未验证**：无真机/Vita3K 证据；MVP compact-BC7 的 CPU 解码性能、完整 GXT 包的内存/帧率均未测。
3. **`w_allui` 多纹理**：portable/KATL 路径未实测；KATL 索引生成器对 `w_allui` 的 `logical/physical` 契约需生成后 `--check` 验证。
4. **0.375 画质**：低分辨率立绘簇（物理≈逻辑/3）在 0.375 下会明显变糊；需真机/截图抽检，必要时提至 0.5 或给 kdu 加两档 scale。
5. **`RULE_*`/遮罩类**：需实测确认是否必须原样保留（WoH 用 keep list；TSUKIHIME 的 `0x1d01` 49 条疑似同类）。
6. **update 补丁差异**：`w_allpac.mrg` 合并后比 base 小 5.77 MB（部分条目被补丁替换）；素材必须来自合并 romfs（本链即如此），不要用 base-only。
7. **电影/音频转换参数**：`create_compact.py` 的 H.264 CRF22/960×540 与 Opus 48 kHz 参数沿用 WoH；Vita 硬件解码兼容性未验证。
8. **磁盘**：峰值按 §5 估算 20–30 GB；本会话 free ≈56.6 GB，下一时段需逐阶段清理中间产物。


---

## 10. Lead 集成状态更新（2026-10-31 会话末）

§6.1 列出的 kdu 适配已全部集成进本仓库 `knife/kdu/src/compact.rs`（源码为唯一事实来源）：

1. 允许列表：`w_allpac | w_allpaccg | allpachd | w_allpacml | w_allpachdml | w_allui` + WoH 四个原名
   （实际 HD 归档是 `allpachd`，无 `w_` 前缀）。
2. 缩略图保留规则：由“THUMSP_TOP 之后全部保留”的位置启发式改为按名字保留 `THUM*` 与 `GALLERY_FC_TH`
   （月姬 `w_allpac` 的 THUMSP_TOP 在 29,267 项的第 14,658 项，位置规则会错误保留约一半条目不缩放）。
3. `*ml` 归档同名小变体高度不被语言数整除时，该条目退化为整体等比缩放（避免整个归档中止）。

Windows kdu.exe 已按仓库源码重建（`tools/build-kdu-windows.sh`，sha256 见 `.work/assets/logs/`），
并已用 §7.2 的参数完成**阶段 B（540p 图像预处理）**：

| 归档 | 参数 | 实测结果（2026-10-31） |
|---|---|---|
| `allpachd` | scale 0.75 / strips 1 | 完成：14,765 项、0 项缩放（该档海外版绝大多数为空占位/4×4），输出 9.2 MiB，0.7 s |
| `w_allpacml` | scale 0.375 / strips 4 | 完成：344 项、277 项缩放，输出 42.2 MiB，16.6 s |
| `w_allpaccg` | scale 0.375 / strips 1 | 完成：1,521 项、1,024 项缩放，输出 345.1 MiB，82.0 s |
| `w_allpac` | scale 0.375 / strips 1 | 完成：29,267 项、21,876 项缩放，输出 2,968.9 MiB，830.8 s（13.8 min） |

合计 kdu compact 输出约 3.35 GiB；`.work/assets/logs/stageB-w_allpac.log` 等为完整进度记录。
`w_allpac` 中约 7,168 项保持原始字节（`DUMMY` 4×4 占位与 `THUM*`/`GALLERY_FC_TH` 缩略图），
符合“占位/缩略图不重缩放”的预期；`.compact.tsv` 记录每项 kind（jpeg/bc7/original）与逻辑/物理尺寸。

阶段 B 产物已整理到 **`dist/Tsukihime-540p-x64/assets/`**（16,836 文件 / 8.41 GiB，含原样复制的
`stream/`、`movie/`、字体、`allscr.mrg`、`script_text.mrg`、`knife1.bfsar` 与待 C 步转换的原始 `w_allui.mrg`），
并写有 `dist/Tsukihime-540p-x64/asset-build.json`（stage=B、逐归档输出字节、pending 列表、`complete:false`）。
目录约定与 mofa-vita 的 `dist/<name>-540p-x64/assets` 一致。
**阶段 C–G（portable/KATL、DXT/GXT codec9、清单与 profile/atlas/stream 三件套、VPK 重建）尚未执行**，
执行顺序与命令见 §7.3；`w_allui` 必须走 create_compact 的 export-bntx→portable→KATL 路径（§6.3）。

---

## 11. 本次会话 C–F 执行记录（asset-pipeline）

> 本节记录 2026-10-31 会话实际执行的 C→F 阶段：脚本、实测耗时/体积、与 mofa-vita 参考链的**全部偏差**
> （Lead 批准记录）、mofa 校验器结果、GXT 头字段对照、STEC/SNX 分析、磁盘与最终元数据。命令均可复现；
> 所有数字为本机实测（Windows 11 + WSL2 `pocket-ubuntu`，16 逻辑核）。§2–§4 保持原样未改。

### 11.1 阶段实现与产物路径

| 阶段 | 脚本（本仓库 `.work/assets/scripts/`） | 输出目录 | 说明 |
|---|---|---|---|
| C | `stage_c.py`（改编自 `tools/create_compact.py` + `compact_media.py`） | `.work/assets/c-portable/{assets,media-manifests}` | w_allui→KATL、w_allpacml→portable PNG（条带保持）、parts→portable KIMG；16,601 opus→ogg；134 mp4→960×540 H.264；其余文件硬链接 |
| D | `stage_d.py`（改编自 `tools/pack_dxt_540.py` + `create_native540.py`） | `.work/assets/d-dxt/assets` | DXT1（全不透明）/DXT5（含 alpha）、`vita-game-gxt.py::offline_alter`、GXT codec8、manifest `native-540p-preserve-logical-v1` |
| E | `stage_e.py` + `stage_e_core.py`（= `tools/migrate-vita-native-color.py` + 参数化） | `.work/assets/e-codec9/assets` | codec8→codec9 `GxtNativeUnorm`（mofa migrate 路径），manifest→`native-540p-encoded-unorm-v2` |
| E′ | `patch_strips_png.py`、`_fix_katl_nx.py` | 最终包（就地） | 26 条 w_allpac 条带变体→codec2 PNG；w_allui 保留 KATL 改 NX 包装 |
| 最终 | `finalize_pack.py` | `dist/Tsukihime-540p-Vita/assets` | 按 manifest 逐文件 MOVE 到最终包，校验 bytes+sha256，全档 codec 扫描 |
| 校验 | `validate_gxt_pack.py`（调用 mofa `vita-game-gxt.py::validate_gxt`） | `.work/assets/logs/validate-*.json` | 对每个 codec8/9 GXT 跑 mofa 官方校验器 |
| F | `stage_f.py` | `.work/assets/f-meta/` | profile / atlas index / stream index（基于最终包） |

### 11.2 阶段 C 实测

| 项 | 结果 | 耗时 |
|---|---|---|
| `w_allui` | 742 BNTX 纹理 → 40 KATL + 6 KIMG，2 条保留；61,769,728 B | 26.1 s |
| `w_allpacml` | 277 条 4 语言条带 → portable PNG（codec2），67 条保留；55,898,112 B | 12.8 s |
| `parts` | 5 条 BNTX → portable KIMG；182,272 B | 0.2 s |
| `stream/` | 16,601 个 Nintendo Opus（无损 remux→Ogg，再 libopus 48k 单声道/80k 立体声 VBR，48 kHz） | 782 s（与 D 并行争用） |
| `movie/` | 134 个 → 960×540 lanczos / libx264 `preset medium` / CRF22 / yuv420p / `-c:a copy` / faststart | 417 s，输出 325,920,794 B |
| 其他运行时文件 | 16,735 个（12 套字体、bsfar、脚本、shader、tga 等）硬链接，0 字节额外占用 | — |

C 目录合计 **16,826 文件 / 1,692,678,918 B**。音视频参数与 `create_compact.py` 完全一致，仅 `--jobs` 按主机核数放宽。

### 11.3 阶段 D 实测（codec8）

| 归档 | 输出 | DXT1 | DXT5 | keep | 耗时 |
|---|---|---|---|---|---|
| `w_allpac` | 13,584,185,344 B | 1,284 | 20,405 | 7,417 | 594.7 s |
| `w_allpaccg` | 1,230,055,424 B | 598 | 418 | 497 | 31.8 s |
| `w_allui` | 286,355,456 B | 33 | 690 | 20 members kept | 11.9 s |
| `w_allpacml` | 56,377,344 B | 0 | 0 | 344（C 的 codec2 条带保持） | 0.4 s |
| `parts` | 2,631,680 B | 5 | 0 | 0 | 0.1 s |
| `allpachd` | 9,607,168 B | 0 | 0 | 60（BC4 掩码/占位，无图像可转） | 1.3 s |

D 包 **16,832 文件 / 16,745,444,721 B**（含媒体硬链接）；manifest `knife-540p-assets-v1` /
`native-540p-preserve-logical-v1` / `languages=["ja","en","zc","zt"]`，实际 codec 集合 `[2,3,8]`
（3 = 26 条 w_allpac 条带变体，E′ 处理；见 §11.5）。D 总耗时 ≈ 11.5 min（含 manifest 51 s）。

### 11.4 阶段 E 实测（codec9）

| 归档 | entries | codec9 转换（含 KATL 成员） | unchanged | 耗时 |
|---|---|---|---|---|
| `w_allpac` | 29,267 | 21,850 | 7,417 | 715.2 s |
| `w_allpaccg` | 1,521 | 1,024 | 497 | 65.2 s |
| `w_allpacml` | 344 | 0（条带全部保留 codec2） | 344 | 0.1 s |
| `w_allui` | 48 | 724 成员 | 3 | 14.1 s |
| `parts` | 5 | 5 | 0 | 0.2 s |
| `allpachd` | 14,765 | 0 | 61（+14,704 空别名） | 0.03 s |
| **合计** | | **23,603**（= D 的 codec8 数） | | **≈795 s（13.3 min）+ manifest 16 s** |

- 命令：`python .work/assets/scripts/stage_e.py --jobs 8`（mofa `migrate` 核心，jobs 上限从 2 放宽到 8；
  `assert converted_slots==22176` 改为 TSUKIHIME 实测值校验）。
- manifest：`native-540p-encoded-unorm-v2` / `encoded-unorm8-v1` / codecs_field `[1,2,7,9]` /
  `languages=["ja","en","zc","zt"]` / `composite=[960,540]`；收据 `.work/assets/e-codec9/native-color-migration.json`
  （`alpha_exact:true`、`second_lossy_DXT_encoding:true`、`lossless_recovery:false`，与 mofa E 语义一致）。
- 质量（receipt `quality`，RGBA 加权 MAE / max）：`w_allpac` 0.879/0.649/0.867/0（max 231/231/239/0）、
  `w_allpaccg` 1.081/0.771/1.045/0、`w_allui` 0.316/0.328/0.360/0、`parts` 0.399/0.403/0.405/0；alpha 逐字节不变。
- **无损回退策略生效**：2,214 个成员因 premult 误差超阈值写为 codec7 PNG_UNORM（mofa 同策略），
  最终 codec 直方图见 §11.6。
- E 阶段归档字节（NXCX 压缩后）：`w_allpac` 2,083,346,432 → E′ 后 2,067,834,880 B；`w_allpaccg` 278,759,424 B；
  `w_allpacml` 56,354,816 B；`w_allui` 37,081,088 → NX 包装后 38,553,600 B；`parts` 120,832 B；`allpachd` 9,590,784 B。

### 11.5 与 mofa-vita 参考链的偏差（逐项记录，均已获 Lead 确认）

**偏差 D1：`w_allpac`/`w_allpaccg`/`allpachd` 跳过 C 阶段 portable 转换，D 直接读取阶段-B 的 BC7/JPEG KIMG。**
- 理由：mofa 的 C 阶段兼做“可编辑 PNG/JPEG 图像源”和“把 BNTX 变成 D 可吃的 codec1/2”；TSUKIHIME 官方译文在
  数据内、不需要编辑图像源；D 现可直接解码 BC7，少一次 JPEG-q88 往返，省约 5 GB 中间盘及约 8 分钟。
- 运行时契约不变：DXT1 不透明 / DXT5 含 alpha、GXT codec8→migrate codec9、PNG codec2 条带保留、
  manifest schema/method/color_contract 与 r7 一致。
- 风险：中间像素来源不同（少一次有损步骤，画质不劣于参考链）；最终运行格式/类型无差异。
- **不得描述为 mofa 默认链**；需要严格复刻 mofa 原链时，按 §6.3/§7.3 先对三条故事归档执行 C portable 再跑 D/E。

**偏差 D2：codec8 GXT 由 Pillow DDS（BC1/BC3）+ 本仓库 GXT swizzle 写入器生成，而非 psp2gxt。**
- 证据：psp2gxt 是 Sony SDK 期专有工具，不在现代 VitaSDK/vdpm；本机检查 `D:\AI-CODEX\mofa-vita`、`D:\PSV`、
  reverse-tools、`/opt/vitasdk`（只有头 `psp2/gxt.h`，无二进制）均无该工具（Lead 复核确认）。
- 字节契约验证：mofa 自己的 `vita-game-gxt.py::validate_gxt` 全量校验通过（§11.6），GXT 头字段与硬件验证过的
  WoH r7 codec9 包逐字段一致（§11.6 表）。
- 最终 codec9 仍由 **mofa `migrate-vita-native-color.py` 路径**产出（Pillow DDS + `native-color-blocks.c` refiner +
  同一 swizzle），与 WoH 迁移链一致；仅 codec8 中间产物生成器不同。
- 风险：codec8 的 DXT 块决策与 psp2gxt 存在编码器级差异；E 以目标像素重拟合 RGB 端点并保留 alpha 块。

**偏差 D3：没有 TSUKIHIME 版 graded keep-list（mofa `tools/graded-images.txt` 为 WoH 专用，4,342 项）。**
- TSUKIHIME 549 场景实测命令用量：`STEC` 12,900、`SNX2` 1,678、`SNX3` 845、`SBAS` 943；`SNX4`（8,758）在 Switch
  引擎即被忽略，`FANX`（2,741）只做预加载。mofa keep 名单按 WoH 图像名人工筛选，不能直接套用。
- 安全性依据：`knife/knife/src/assets.rs` 的 `GxtNativeUnorm` 分支在 `grade.cpu()`/`strip`/`raw` 时调用
  `gxt_decode::rgba8_rows`（覆盖 STEC/SNX、语言条带、原始采样），调色在 CPU 解码后按原语义执行；`BORDER_PARTS`
  （CPU soft-clip LUT）保持 portable 编码，BC4/BNTX 掩码保持原编码。
- 风险＝运行时性能（调色图像每次 CPU 解一次 GXT，结果进 graded cache），不是颜色正确性；真机帧率未测。
- 若需要可仿照 WoH 从 `allscr` 的 STEC/SNX/SBAS 参数自动生成 TSUKIHIME keep 名单，再重跑 D/E。

**偏差 D4：E 的（仅报告性）quality 指标裁剪。** mofa 原版对每张图计算 `np.quantile(p99/p999)` 与 black/white
合成 MAE（O(pixels·log)），2.3 万张图下 8 worker 迁移不可行（实测约 0.5 s/图）。现保留决定“无损回退”的
`premult_max_rgb` / `premult_above32_pixels` / `mae` / `max`，仅把 `premult_pixel_p99_p999`、`opaque_max_rgb`、
`composite_*_mae` 写成常量占位并标记 `metrics_reduced:true`。codec9 回退策略与编码路径不变。

**偏差 D5（B 阶段残留的处理）：26 条 w_allpac 语言条带变体在 B 被按普通图缩放（strips=1），D 中为 codec3
（不在契约内）。E′ 阶段按 mofa“条带保持 portable 编码”的规则无损重编码为 **codec2 PNG**（同一扩展名/物理尺寸），
并更新 manifest。最终 codec 直方图无 3/4/8。**

### 11.6 mofa 官方校验器结果与 GXT 头字段对照

`validate_gxt_pack.py` = 调用 mofa `tools/vita-game-gxt.py::validate_gxt`（检查 tag/ver/count、palette/flags/padding、
dims、single mip、format id、kind/layout、exact range、payload length、zero alignment tail），逐条扫描所有归档
（含 KATL 成员）：

| 扫描对象 | codec8/9 总数 | pass | fail | 实测 codec 直方图（每张图/成员） |
|---|---|---|---|---|
| 阶段 D 包（codec8） | 23,603 | **23,603** | **0** | 8: 23,603；2: 295；3: 26（E′ 前） |
| 最终包（codec9） | 21,389 | **21,389** | **0** | 9: 21,389；7: 2,214；2: 321 |

- 最终包 **不含 codec 3/4/8**；`{2,7,9} ⊆ {1,2,7,9}`，manifest `codecs` 字段为 mofa r7 固定值 `[1,2,7,9]`。
- 日志：`.work/assets/logs/validate-d.json`、`.work/assets/logs/validate-final-pack.json`（各 33.3 s / 42.4 s）。
- 补充修复：w_allui 的保留 KATL（BORDER_PARTS，CPU soft-clip LUT）原先为 raw+扇区填充，mofa atlas 生成器要求
  KATL 精确 envelope，已按 mofa r7 做法改为 NXCX 包装（参考包 `BORDER_PARTS.NXZ` 亦为 NX 包装）。

**GXT 头字段对照（mofa 硬件验证 WoH r7 codec9 参考 vs 本包）：**

```
# mofa-vita r7（硬件验证）示例：allui KATL 成员 codec9
KIMG logical=608x420 phys=608x420 codec=9
  tag=0x00545847 ver=0x10000003 count=1 off=64 size=524288
  palette=0xffffffff flags=0 layout=0xa0000000 fmt=0x87000000 dims=608x420 mip=1 rpad=000000
# 本包最终 codec9 示例
w_allpaccg: KIMG logical=2560x1440 phys=960x540 codec=9
  tag=0x00545847 ver=0x10000003 count=1 off=64 size=524288
  palette=0xffffffff flags=0 layout=0xa0000000 fmt=0x85000000 dims=960x540 mip=1 rpad=000000
w_allpaccg: KIMG logical=3200x1440 phys=1200x540 codec=9
  tag=0x00545847 ver=0x10000003 count=1 off=64 size=2097152
  palette=0xffffffff flags=0 layout=0xa0000000 fmt=0x87000000 dims=1200x540 mip=1 rpad=000000
```

tag/version/count/offset/size/palette/flags/layout(`0xa0000000`=2684354560)/format(`0x85000000`=2231369728 DXT1、
`0x87000000`=2264924160 DXT5)/mip(`1`)/rpad 与参考包一致。完整对照脚本与日志：
`.work/assets/scripts/compare_gxt_headers.py`、`.work/assets/logs/gxt-compare*.txt`。

### 11.7 磁盘与时间

- 阶段 B 树 `dist/Tsukihime-540p-x64/assets`（8.41 GiB）全程未动；`.work/nsp/romfs` 未动。
- C 1.69 GB → D 14.47 GB（16,832 文件）→ E 归档（NXCX 压缩后）约 2.5 GB。
- 最终包 `dist/Tsukihime-540p-Vita/assets`：**16,832 文件 / 4,027,446,641 B（3.75 GiB）**，
  `vita-540p-assets.json` 2,745,701 B，**SHA-256 `933fa16cbf868d4f075a8df7dd0a6a348f9043fec20a77231429d1dc8694010e`**。
- 组装策略：E 完成 → mofa 校验 → **删除 `.work/assets/d-dxt`（释放 14.5 GB）** → `finalize_pack.py` 以 MOVE 方式
  组装（无第二份拷贝，媒体保留在包内）→ F。全程 free 未低于 5 GB（峰值最低约 26 GB free，最终 free 41.3 GB）。
- 实测总时长：C 约 21 min（图像 39 s + 音频 782 s + 视频 417 s，部分并行）、D 约 11.5 min、E 约 13.5 min、
  E′ 6 s、finalize 44 s、F 3 s；合计约 **50 min 机器时间**（不含阶段 B 14 min 与本会话前期调查）。

### 11.8 阶段 F：元数据三件套（`.work/assets/f-meta/`）

| 生成物 | 文件 | 大小 | 实测内容 |
|---|---|---|---|
| 启动 profile | `asset_profile_tsukihime_540p.rs` | 20,261 B | 175 个关键文件、启动读取 25,458,232 B、单 8,192 B 缓冲；绑定 manifest SHA-256 `933fa16c…` |
| atlas index | `vita_atlas_index_tsukihime_540p.rs` | 152,330 B | 40 个 KATL、736 成员（472 个 codec9 GXT 元数据、264 个 PNG/其他）；manifest 绑定 + `source_sha256` |
| stream index | `vita_stream_index_tsukihime_540p.txt` | 482,741 B | 16,601 条 stream 文件名，首行 `# knife-stream-index-v1 <manifest sha>` |

- 三个生成器均为 mofa 原脚本/Lead 的 TSUKIHIME profile 生成器（`tools/generate_vita_asset_profile_tsukihime_540.py`），
  仅把 atlas 生成器的 `allui.*` 改为 `w_allui.*`；全部断言通过（schema/method/color_contract/codecs⊆{1,2,7,9}、
  `streams=16,601 ≤ 32,768`）。
- 交接：Lead 将上述三个文件安装到 `knife/knife-platform-vita/src/asset_profile_tsukihime_540p.rs`、
  `knife/knife/data/vita_atlas_index_tsukihime_540p.rs`、`knife/knife/data/vita_stream_index_tsukihime_540p.txt`
  后重建 VPK。175 个关键文件（WoH r7 为 37 个）是因为 TSUKIHIME 文件数 16,832（WoH 9,564）；如启动耗时超标，
  可在 profile 生成器中进一步精简关键文件集合（非本次阻塞项）。

### 11.9 本次交付状态

- **已完成**：kdu 允许列表适配后的 Windows 构建（`.work/assets/tools/kdu.exe`，sha256 `5295d79c…`，含可选
  `compact --limit`）；阶段 B 产物验证（KIMG codec/码数/尺寸/条带）；C、D、E、E′、最终包组装、mofa 全量 GXT 校验、
  F 三件套。
- **未验证（需真机/Vita3K）**：最终包在 PS Vita 上的启动、读盘性能与帧率；codec9 CPU 解码在调色/条带路径的实际耗时；
  0.375 缩放画质（低分辨率立绘簇见 §3.2 风险）；H.264/Opus 在 SceAvPlayer/SceAudio 的兼容性。
- 发布身份仍按 Lead 方案（KNIF00541 / `ux0:data/knife-tsukihime-540p`），素材根为最终包 `assets/`。
