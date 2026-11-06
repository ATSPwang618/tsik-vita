# 素材、画质与配套关系

[文档导航](README.md) · [优化总表](optimizations.md) · [验证](validation.md)

## 唯一素材树

本地只保留 `dist/TSUKIHIME-RE/assets/`，设备对应 `ux0:data/TSUKIHIME-RE/assets/`。16,764 个数据文件共 2,427,075,112 字节，加 2,762,525 字节清单，约 **2.26 GiB**；相对上一高清包减少 1,878,446,080 字节，约 **1.75 GiB**。

~~~text
schema: knife-540p-assets-v1
method: native-540p-encoded-unorm-v2
color_contract: encoded-unorm8-v1
codecs: 1, 2, 7, 9
stability policy: story-rgba512k-axis960-v1
manifest SHA-256:
0c4188c923f744870d660a384e0c55f59f1d3e3d8997e9baf6150a5eb7e0fc75
~~~

稳定素材产生于 2026-11-02，2026-11-06 离线 shader VPK 沿用这一清单；当前包身份见[验证](validation.md)。源数据为自行准备的 Switch 海外版 base + update v1.0.1，程序 build ID `d10d239aade1d526`。原始 NSP / romfs 不随仓库交付，也不能直接替代转换后的素材。

## 剧情大图的固定上限

针对所有 `w_allpac`、`w_allpaccg`、`w_allpacml`、`allpachd` 图片条目，在选中语言后检查：

- `align8(width) × height × 4 ≤ 524288`，单轴 ≤960。
- 原生压缩 payload 也不超过 512 KiB。
- 超限项按比例缩小，逻辑尺寸、脚本坐标、归档 ID、语言槽与 alpha 保留；合格项原编码字节不动。
- 双语言分别重采样，避免相邻语言污染；GXT 缩小后重新进行 DXT 编码。

扫描 23,177 条，15,901 条降采样，复扫 0 超限。**这是主动牺牲细节降低峰值的有损处理**，不是高清无损重压缩。GPU 的 P8 / RGB24 无损上传是另一层优化，不能替代这个最坏展开上限。

| 归档 | 缩小条目 | 旧 MRG 字节 | 当前 MRG 字节 |
| --- | ---: | ---: | ---: |
| `w_allpac` | 14,765 | 2,475,186,176 | 819,984,384 |
| `w_allpaccg` | 1,024 | 291,788,800 | 98,576,384 |
| `w_allpacml` | 112 | 57,913,344 | 27,881,472 |
| `allpachd` | 0，无图片条目 | 未改 | 未改 |

普通 960×540 图变为 480×270，RGBA 新页 2 MiB→512 KiB；已知失败资源 `AOK_A_21_00_N01_03_03` 从 1020×1016 变为 360×359，新页 4 MiB→512 KiB。原始逻辑坐标不变。证据见[预处理](evidence/stability-preprocessing.json)与[尺寸审计](evidence/image-size-audit.json)。

## 不跟随剧情降采样的资源

| 类别 | 当前契约 |
| --- | --- |
| UI 图集 | 24 图集 / 438 成员；保留 R4 尺寸与可见 alpha，不按剧情上限统一缩小 |
| CG 缩略图 | 每语言 28 页，每页 6×12 格，物理 696×792，单格 116×66；按原 36×55 编号映射，两语言 3960 个有效格位 |
| 字体 | JA / ZC 使用指定主字体 `arshanghaisonggbpro_lt.otf`，保留补充字形和特殊符号；音乐页主字体优先 |
| 语言 | 仅 JA / ZC，原始 ID 0 / 2 对应两个物理槽，新配置默认简中 |
| parts / 开场 | 正确 @Zarathustra / @lisen 图片，淡入 30 + 停留 420 + 淡出 30 帧，60 Hz 约 8 秒，可跳过 |
| 音视频 | 保留配套原生流路径，本次稳定预处理不重编码媒体 |

UI 的 GXT 可单轴达到 2048，但总物理像素仍 ≤960×1080。PNG / JPEG 轴范围仍为 960×1080，单次 CPU RGBA 解码 ≤4×960×1080 字节。个别 UI 的 RGBA 新页可达 4 MiB，不能把剧情 512 KiB 上限扩大解释为全包通用上限。

## 升级范围

退出游戏后安装匹配 VPK，并覆盖所需素材；覆盖不能追加或留下旧文件尾部。保留玩家存档与配置。

| 原素材状态 | 需要更新 |
| --- | --- |
| 已匹配本页稳定清单 | 同清单引擎更新只安装 VPK |
| 上一版 R4 / 无损存储 / CDRAM 修复包 | VPK 与下列 7 文件 |
| R3，致谢图与 8 秒时长已正确 | 7 文件之外，加当前 `w_allui.hed` / `w_allui.mrg` |
| 更早 R3，致谢图或开场未修正 | 以上再加 `parts.hed` / `parts.mrg` |
| 四语言、旧字体或版本不确定 | 使用完整配套 assets，保留存档 |

7 文件为 `w_allpac.hed`、`w_allpac.mrg`、`w_allpaccg.hed`、`w_allpaccg.mrg`、`w_allpacml.hed`、`w_allpacml.mrg`、`vita-540p-assets.json`。历史更新清单在[稳定素材验证](evidence/stable-assets-validation.json)，前后哈希在[预处理收据](evidence/stability-preprocessing.json)。不能通过手改清单把不匹配资源伪装成当前版本。

## 开发者转换流程

~~~sh
# 默认只读扫描
python3 -B tools/stabilize-tsukihime-assets.py --report .work/stable-preview.json
# 仅在确实需要改写配套素材时执行
python3 -B tools/stabilize-tsukihime-assets.py --apply --report .work/stable-apply.json
~~~

需要 Pillow / NumPy、原生 GXT 工具和匹配的双语数据。工具逐个归档处理，同时只创建一个临时 MRG；事务记录支持 MRG / HED / manifest 中断后配套恢复。重复执行不再转码合格项。

素材实际变更后，生成 startup profile、atlas index、stream index，再构建配套 VPK。检查入口：

~~~sh
python3 tools/generate_vita_asset_profile_tsukihime_540.py --check
python3 tools/generate-vita-atlas-index.py dist/TSUKIHIME-RE/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs --archive w_allui --check
~~~

旧高清恢复工具 `restore_tsukihime_quality.py` 仍为现用工具提供公共图像 / 编码函数，保留源码；其完整恢复入口需要原 romfs、UI cache、kdu，不能直接覆盖稳定包。整个转换链尚未证明能用一条命令处理任意 NSP。见[工具索引](../tools/README.md)和[验证命令](validation.md)。
