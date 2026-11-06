# 当前稳定版素材

## 身份与目录

唯一正式本地素材为 `dist/TSUKIHIME-RE/assets/`，设备位置为 `ux0:data/TSUKIHIME-RE/assets/`。16,764 个数据文件共 **2,427,075,112 字节**，另加 2,762,525 字节清单，总计约 2.26 GiB。相对上一版减少 1,878,446,080 字节，约 1.75 GiB。没有保留第二套高清资源树。

```text
schema: knife-540p-assets-v1
method: native-540p-encoded-unorm-v2
color_contract: encoded-unorm8-v1
codecs: 1, 2, 7, 9
stability policy: story-rgba512k-axis960-v1
manifest SHA-256: 0c4188c923f744870d660a384e0c55f59f1d3e3d8997e9baf6150a5eb7e0fc75
paired build: tsukihime540-stable-20261102
```

源数据为使用者自备的 Switch 海外版 base＋update v1.0.1，程序 build ID `d10d239aade1d526`。原 NSP 的已记录 SHA-256 为 `baa737bd23d880afd64c1ad29209a7ca14d5d02c1aac1b4d24aa73833104c795`。原始数据不是仓库交付物；已删除解包临时目录，需要重新恢复高清资源时应从原 NSP 重新解包。

## 提前降低剧情纹理占用

按照用户授权，本版主动降低剧情与 CG 的物理分辨率，替代上一版 R4 恢复后的高像素剧情图片。固定约束覆盖 `w_allpac`、`w_allpaccg`、`w_allpacml`、`allpachd` 的所有 KIMG／KATL 图片条目：选择语言后，单张 `align8(width) × height × 4` 最多 **524,288 字节**，单轴最多 960，原生压缩载荷也最多 512 KiB。512 KiB 恰好是两个 256 KiB CDRAM 页；不依赖图片是否适合调色板或 RGB24。

扫描 23,177 个剧情图片条目，其中 15,901 个超限项已按比例缩小，复扫无超限项。未超限的图片保持原编码字节。保留逻辑宽高、脚本坐标、归档 ID、语言槽与 alpha 通道；透明边缘参与重采样，双语言分别处理，避免串入另一语言。缩小的 GXT 会重新进行 DXT 编码，细节与像素值会损失，这是本版的明确取舍。

| 例子 | 上一版物理尺寸 | 当前物理尺寸 | RGBA 新页占用 |
| --- | --- | --- | --- |
| 普通 16:9 整屏图片 | 960×540 | 480×270 | 2 MiB → 512 KiB |
| 实机失败资源 `AOK_A_21_00_N01_03_03` | 1020×1016 | 360×359 | 4 MiB → 512 KiB |
| 双语立绘示例，每种语言独立 | 946×853 | 378×341 | 含行距最多 512 KiB |

40 个逻辑图层的旧新两版图片，在每层每版一张 RGBA 的前提下共不超过 40 MiB；这不包括 UI、必需离屏目标、其它缓存或驱动，不能据此承诺所有实机演出绝无分配失败。缓存与生命周期的配套修改见[性能说明](performance.md#内存上限)。

| 归档 | 缩小条目 | 旧 MRG 字节 | 新 MRG 字节 |
| --- | --- | --- | --- |
| `w_allpac` | 14,765 | 2,475,186,176 | 819,984,384 |
| `w_allpaccg` | 1,024 | 291,788,800 | 98,576,384 |
| `w_allpacml` | 112 | 57,913,344 | 27,881,472 |
| `allpachd` | 0（无图片条目） | 未改变 | 未改变 |

完整前后统计、变更文件 hash 与限制见[预处理证据](evidence/stability-preprocessing.json)。

## UI、双语言、字体与开场

`w_allui`、字体、分页 CG 缩略图、`parts` 和媒体流没有跟随剧情大图统一降采样。UI 图集索引除外层清单 hash 外与上一版逐字节一致；24 个图集／438 成员及日中标题和菜单的 60 个状态区通过离线检查。UI 个别成员仍可能使用 4 MiB RGBA 新页，**剧情的 512 KiB 上限不适用于这些图集**。

保留 R4 的 28 页 CG 缩略图，每页 6×12 格，物理 696×792、单格 116×66，维持原 36×55 排列的索引映射；两语言共 3960 格。剧情中的 CG 大图已降采样，列表小图清晰度不随之改变。森林原图 1404×844 并非 16:9，显示比例与摇杆死区见[排错说明](troubleshooting.md#cg-两侧浅灰边)。

仅保留 JA/ZC，原始 ID 0/2 对应两个物理语言槽；默认简体中文。动态文字共用 `arshanghaisonggbpro_lt.otf`，补充“嗞、觍”等字形及特殊符号；音乐页主字体优先。`parts` 保持正确的 @Zarathustra／@lisen 致谢图，30 帧淡入＋420 帧停留＋30 帧淡出，按 60 Hz 合计约 8 秒，保留跳过。

解码器仍支持既有 UI 宽长 GXT：单边最多 2048、物理像素最多 `960×1080`；单次 CPU RGBA 解码最多 `4×960×1080` 字节。普通 PNG/JPEG 仍限 960×1080。不要混用 codec8／预烘焙 sRGB 历史素材。无损 P8／RGB24 上传优化继续生效，但它不能代替此次离线降分辨率。

## 升级范围

完全退出游戏，安装当前 VPK，配套覆盖素材文件。覆盖传输应替换旧文件，不能追加或保留旧尾部；不要修改存档或配置。

| 原版本 | 操作 |
| --- | --- |
| 已为本页清单对应的稳定包 | 后续同素材引擎更新可只更新匹配 VPK |
| 上一版 R4／无损存储／CDRAM 修复包 | 当前 VPK＋下列 7 个文件 |
| 正确致谢／8 秒开场的 R3 双语言包 | 7 文件之外再覆盖当前 `w_allui.hed`、`w_allui.mrg` |
| 更早 R3，致谢图有误或尚未加入 | 上述之外再覆盖当前 `parts.hed`、`parts.mrg` |
| 四语言／旧字体或无法确认版本 | 当前完整 `assets/`，保留存档 |

7 文件为 `w_allpac.hed`、`w_allpac.mrg`、`w_allpaccg.hed`、`w_allpaccg.mrg`、`w_allpacml.hed`、`w_allpacml.mrg`、`vita-540p-assets.json`。长度与 hash 记录在[当前验证](evidence/current-validation.json)的 `stable_assets.data_update_files`。只更新 VPK 会被精确素材检查拒绝；旧高清引擎也不应搭配新清单。

## 预处理与后续验证

`tools/stabilize-tsukihime-assets.py` 默认只读扫描；加 `--apply` 才原地处理。需要 Pillow／NumPy、原生 GXT 辅助编解码工具以及现有双语海外表。处理时只同时创建一个临时 MRG，小型事务记录支持 MRG／HED／清单替换中断后继续，不复制整个素材树。可重复执行，合格素材不再转码。

```sh
python3 -B tools/stabilize-tsukihime-assets.py --report .work/stable-preview.json
# 明确要应用到现有包时：
python3 -B tools/stabilize-tsukihime-assets.py --apply --report .work/stable-apply.json
```

任何实际改动后须重新生成 `generate_vita_asset_profile_tsukihime_540.py`、`generate-vita-atlas-index.py`、`generate-vita-stream-index.py` 的源码元数据，并构建匹配 VPK；三个索引已为当前包同步。完整 hash／解码审计见[验证](validation.md)，只读校对可执行：

```sh
python3 tools/generate_vita_asset_profile_tsukihime_540.py --check
python3 tools/generate-vita-atlas-index.py dist/TSUKIHIME-RE/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs --archive w_allui --check
```

`restore_tsukihime_quality.py` 是历史高清恢复工具，需要原 romfs、UI cache 和 kdu；不要直接覆盖当前稳定包。若未来恢复高清资源，必须再做稳定预处理和整包验证。其它转换工具与复现边界见[工具索引](../tools/README.md)，当前没有验证“一条命令从任意 NSP 重建”的通用入口。
