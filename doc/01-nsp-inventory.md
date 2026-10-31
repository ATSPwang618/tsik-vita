# NSP 解包清单（TSUKIHIME A piece of blue glass moon，Switch 海外版）

> 数据来源：使用者自备的 `switch原版游戏/TSUKIHIME A piece of blue glass moon [B+U65536].nsp`。
> 本文件只记录包的**结构与哈希**，不包含密钥和游戏内容；原始 NSP/解包数据不入库。
> 标记：**[实测]** 本次会话实际输出；**[未验证]** 无独立复核。

## 1. 输入

| 项 | 值 |
|---|---|
| 文件 | `switch原版游戏/TSUKIHIME A piece of blue glass moon [B+U65536].nsp` |
| 大小 | 24,712,645,184 B（23.02 GiB） |
| SHA-256 | `baa737bd23d880afd64c1ad29209a7ca14d5d02c1aac1b4d24aa73833104c795` |
| 容器 | PFS0，10 个条目（ticket/cert/2×cnmt/6×NCA） |
| 标题 | Base `010057a01e4d4000`，Update `010057a01e4d4800`（版本 65536 = v1.0.1） |
| 判读 | `w_allpac.nam` 存在 → 海外版（`Build::Overseas`），与日版 `allpac` 数据不同 |

## 2. PFS0 内容（实测）

| 条目 | 大小 (B) | 内容类型 | 说明 |
|---|---|---|---|
| `…00000012.tik` | 704 | Ticket | 本 dump 的 ticket 在 0x180 处以明文存放 title key（仅运行时使用，未写入本仓库） |
| `…00000012.cert` | 1,792 | Cert | |
| `929fab9c…cnmt.nca` | 3,584 | Meta | base content meta |
| `3ab52681b30ddd44ff15a06b4959859f.nca` | 24,603,131,904 | **Program (base)** | base 1.0.0：Section0 ExeFS、Section1 RomFS、Section2 PFS0 |
| `40134a5b1ec646a19990ae6c6efcc3db.nca` | 371,712 | Control | |
| `958402ae3e9ae0c3e3848401c5351457.nca` | 141,824 | Manual | |
| `bc6ed1e0…cnmt.nca` | 4,096 | Meta | update content meta |
| `9e7b05062ec013dcd3390e521d02427b.nca` | 108,475,392 | **Program (update)** | 1.0.1：Titlekey crypto（Rights ID `010057A01E4D48000000000000000012`），Section0 ExeFS、Section1 Patch RomFS（BKTR） |
| `27f1187e47700a30b8637ed2a8623fb6.nca` | 371,712 | Control | update control |
| `e0570e62cb118c31110b41f6c92c12a0.nca` | 141,824 | Manual | update manual |

### 2.1 NCA SHA-256（实测，来自 `.work/nsp/inventory.json`）

| NCA | SHA-256 |
|---|---|
| `3ab52681…` base program | `1df7fe8829224a3bffa53d20c62b9b33492a861b3dd9c95c3b6d6e83c6b325c0` |
| `9e7b0506…` update program | `9e7b05062ec013dcd3390e521d02427b83bf675ab6f3315e8977498f8b4f28e4` |
| `27f1187e…` update control | `27f1187e47700a30b8637ed2a8623fb62107b353abe34e7fb39d379ea2cb4052` |
| `40134a5b…` control | `2cf7499fae273cc96b9c1b3879f42abcca81aa281b9946ca0a33ac07c6b141e9` |
| `929fab9c…` cnmt | `1b2c8a843d5d2a8d33f66e9d537b80771e3f08ef45d6f03ec6f7d41fe1bfe830` |
| `958402ae…` manual | `60d67768b9d42e60022a84b1386c018c4dc0d62b8e3b532d407080d6db403e5a` |
| `bc6ed1e0…` cnmt | `bc6ed1e0cc1f63112c514ca61154c996d885fb168c96f053df68900469275c5b` |
| `e0570e62…` manual | `e0570e62cb118c31110b41f6c92c12a0197892610f4f53aa609e0d9e7535b15b` |

## 3. ExeFS 与引擎构建识别（关键验证）

| 项 | 值 |
|---|---|
| base exefs NSO `main` | 3,326,300 B，NSO0，build id（文件偏移 0x40 起 8 B）= `b825b1746fa69a0a` |
| **update exefs NSO `main`** | 3,325,955 B，NSO0，build id = **`d10d239aade1d526`** |
| knife `OVERSEAS` 常量 | `knife/knife-core/src/exe.rs`：`build_id = d1 0d 23 9a ad e1 d5 26` |
| 结论 | **update（v1.0.1）的 exe 正是本引擎内嵌 `knife/data/exe_tables_overseas.bin` 所对应的构建**；运行应使用 update 数据。base 的 build id 不同（旧版本），不能用于本引擎 |

## 4. 合并 RomFS（base 1.0.0 + update 1.0.1，实测）

- 大小：**24,528,451,944 B（22.84 GiB）**，**16,835 个文件**
- 顶层 29 项 + 16 个目录（`en`, `en2`, `en3`, `ja`, `ja2`, `ja3`, `movie/`, `shader/`, `stream/`, `zc`, `zc2`, `zc3`, `zt`, `zt2`, `zt3`）

### 4.1 顶层文件（按大小降序）

| 文件 | 大小 (B) | 内容 |
|---|---|---|
| `w_allpac.mrg` | 16,748,290,048 | 剧情图像（背景/立绘/效果/规则遮罩；BNTX） |
| `w_allpaccg.mrg` | 2,074,607,616 | 画廊 CG（海外版 CG 集） |
| `knife1.bfsar` | 405,170,048 | 音效 + BGM 索引（BFSAR） |
| `w_allpacml.mrg` | 197,275,648 | 多语言图像集（语言条带） |
| `w_allui.mrg` | 191,707,136 | UI 图集与系统文本（KATL/NX） |
| `script_text.mrg` | 12,601,368 | 全部消息文本（多语言） |
| `allpachd.mrg` | 9,607,168 | HD 图集（海外版较小；见 §5 待确认项） |
| `allscr.mrg` | 9,584,960 | 场景脚本（mrgd00/MZX） |
| `w_allpac.nam/.hed` | 936,576 / 234,152 | 图像名表/索引 |
| `allpachd.nam/.hed` | 472,512 / 118,136 | HD 名表/索引 |
| `parts.mrg/hed` | 411,648 / 56 | 启动 logo/警示图（无名字表） |
| `allpachdml.mrg/hed/nam` | 137,216 / 552 / 2,176 | 多语言 HD 集 |
| `w_allpaccg.nam/.hed` | 48,736 / 12,184 | CG 名表/索引 |
| `w_allpacml.nam/.hed` | 11,040 / 2,768 | 多语言剧情图像名表/索引 |
| `w_allui.nam/.hed` | 1,568 / 400 | UI 名表/索引 |
| `exfont_nx01.bffnt` | 42,720 | 特殊字形位图字体 |
| `saveicon*.tga`（4 个） | 110,636 ×4 | 存档图标（含 en/zc/zt） |
| `titlemenu_(c)type-moon.tga` | 26,156 | 标题菜单版权图 |

### 4.2 目录

| 目录 | 文件数 | 大小 (B) | 内容 |
|---|---|---|---|
| `movie/` | 134 | 3,623,696,240 | MP4（opening/ending/各语言副本） |
| `stream/` | 16,601 | 1,179,214,412 | `.opus` BGM/语音（Nintendo Opus） |
| `shader/` | 59 | 509,240 | BNSH（Vita 使用自有 GXP/Cg，不直接使用） |
| `ja`, `ja2`, `ja3` | 1 each | 6,219,156 / 3,440,840 / 5,505,232 | 剧情/UI/气泡日文字体 |
| `zc`, `zc2`, `zc3` | 1 each | 19,223,060 / 6,809,916 / 6,809,916 | 简体中文字体（AR ShangHaiSong 等） |
| `zt`, `zt2`, `zt3` | 1 each | 9,050,532 / 5,294,856 / 5,294,856 | 繁体中文字体 |
| `en`, `en2`, `en3` | 1 each | 48,420 / 108,400 / 5,481,736 | 英文字体 |

## 5. 复现命令（本次实际使用）

> hactool 为 Windows 版，命令行只接受 ASCII 相对路径；中文目录用 NTFS junction 映射为 ASCII：
> `cmd /c mklink /J .work\nsp\src "switch原版游戏"`。密钥只以路径形式传给 hactool，不复制、不写入日志。

```bat
:: 1) PFS0 → NCA（约 98 s / 24.7 GB）
tools\hactool\hactool.exe -k <prod.keys> --disablekeywarns -t pfs0 -x --outdir=nca src\*.nsp

:: 2) 读取 NCA 元数据（内容类型/title id/SDK/master key revision/section 布局）
tools\hactool\hactool.exe -k <prod.keys> --disablekeywarns -t nca -i nca\<nca>

:: 3) 解 base/update ExeFS
tools\hactool\hactool.exe -k <prod.keys> --disablekeywarns -t nca --exefsdir=exefs-base nca\3ab52681….nca
tools\hactool\hactool.exe -k <prod.keys> --disablekeywarns -t nca --titlekey=<from ticket+0x180> --exefsdir=exefs-update nca\9e7b0506….nca

:: 4) 合并 base+update RomFS（BKTR patch；约 10 min，22.84 GB）
tools\hactool\hactool.exe -k <prod.keys> --disablekeywarns -t nca ^
  --basenca=nca\3ab52681….nca --titlekey=<from ticket> --romfsdir=romfs nca\9e7b0506….nca

:: 5) 释放空间：删除 raw NCA 与 ticket（保留 exefs/romfs/清单）
```

封装脚本：`tools/hactool/extract_tsukihime.py`（PFS0→NCA→exefs→合并 romfs 一键；bounded、可续跑、不记录密钥）。
本次实际还用了 `.work/nsp/extract-merged-romfs2.sh`（合并步骤的独立脚本）。

## 6. 安全与清理

- 密钥只以 `-k <prod.keys 路径>` 形式传给 hactool；解包日志与文档不含密钥值。
- `.tik`（含明文 title key）与全部 raw NCA 在合并 romfs 校验完成后删除；`inventory.json` 保留 NCA SHA-256 便于复现。
- romfs 与 exefs 位于 `.work/`（不入库）；仓库不包含任何游戏数据。

## 7. 待确认项（影响素材转换）

1. **`allpachd.mrg` 仅 9.6 MB**：海外版 HD 画廊图可能主要放在 `w_allpaccg`，`allpachd` 仅少量图/或全为不可转换条目；
   需要素材转换侧的 census（条目数、BNTX 维度、NX 包装）确认。
2. **语言条带**：`w_allpacml`/`allpachdml` 与 `w_allui` 中部分图像按语言竖向堆叠（海外版 `build +67 bit1`），
   转换时必须保留条带（strips=语言数）或同步改语言映射。
3. **字体**：游戏数据自带 ja/zc/zt/en 三套字体；UI 菜单在 Switch 上使用系统共享字体，Vita 侧菜单实现是否需要固件字体
   需在素材/运行时阶段确认（mofa-vita 使用固件字体提取）。
