# 工具索引

从仓库根运行工具。当前产品是月姬 Vita 540p；本目录还保留上游共享格式、桌面和探针工具，它们有被其它脚本调用的依赖关系，不按名称相似就删除源码。

## 常用入口

| 工作 | 入口 |
| --- | --- |
| Vita 环境／构建 | `build-vita.py`、`build-vita.ps1`、`build-vita.sh` |
| 正式包检查 | `check-vita-package.py` |
| 全部离线 shader | `compile-vita-offline-shaders.py --compiler <psp2cgc>`；`--check` 只读验证；`test_offline_shaders.py` 检查清单／二进制／指令缩减，见[说明](../doc/shaders.md) |
| 安全预览／清理缓存 | `clean-project.py`，增加 `--apply` 执行 |
| 月姬启动 profile | `generate_vita_asset_profile_tsukihime_540.py --check` |
| 图集索引 | `generate-vita-atlas-index.py ... --archive w_allui --check` |
| 流索引 | `generate-vita-stream-index.py` |
| 性能日志 | `summarize-vita-artemis-performance.py`；`read-vita-performance.py` 的缺失本地依赖见性能文档 |
| 实际双语言／CG 探针 | `probes/tsukihime-bilingual/` |
| 实际 UI／按钮 alpha 检查 | 同一探针的 `--example verify_ui_atlases -- dist/TSUKIHIME-RE/assets`，24 图集逐成员检查 |
| 原生 CDRAM 预留／故障注入 | `test-vita-reservation.sh`，真实 C 分配器＋显式 SDK doubles，池化开／关 |
| 无损 RGB24／RGBA 调色板 | `test-vita-lossless.sh`，生产 C 精确打包／读回、256 alpha、物理预留转移和故障回滚，ASan／UBSan；不执行 GPU |
| 全图透明度／精确色数审计 | `audit-lossless-png.py assets --report ...`（Pillow／NumPy），以及 bilingual probe 的 `audit_lossless_textures` Rust example（GXT）；只读，不生成第二套资源 |
| 整包尺寸／行距／页对齐 | `verify-tsukihime-runtime-assets.py --layouts ...`，输出临时 TSV 供 `KNIFE_IMAGE_LAYOUTS` 渲染宿主回归使用 |

## 素材工具

| 阶段 | 文件与前置条件 |
| --- | --- |
| NSP／romfs 检查 | `hactool/`、`nstool/`、`inventory_romfs.py`、`inspect_romfs_archives.py`；自行准备原始 dump 和工具／密钥路径 |
| compact／媒体 | `create_compact.py`、`compact_media.py`；需上游匹配输入和 ffmpeg 等本地工具 |
| 原生 GXT | `make-vita-assets.py`、`migrate-vita-native-color.py`、`native-color-blocks.c` |
| 资源修复 | `repair-tsukihime-assets.py`、`vita_image_metadata.py` |
| JA/ZC 与字体 | `make-tsukihime-ja-zc.py`，需要原始主字体和 fonttools |
| 稳定剧情预处理 | `stabilize-tsukihime-assets.py --report ...` 只读，`--apply` 原地缩小超限图；512 KiB 最坏 RGBA、一个临时归档、可恢复事务；需要现有双语表与 Pillow／NumPy／GXT 工具 |
| R4 像素密度（历史高清恢复） | `restore_tsukihime_quality.py`，需要原始 romfs／UI PNG cache 和 kdu |
| 离线校验 | `verify-tsukihime-runtime-assets.py`，全包 hash＋正式 C decoder；GXT CPU 验证还需相应原生探针 |

`tools/kdu.exe`、`hactool.exe`、`nstool.exe` 是本地辅助二进制，不提交 Git；当前保留以便再转换。重复 ZIP 和未使用的 `unpack-vita-assets.exe` 已移除，后者源码仍在 `knife/kdu/src/bin/`，需要时可重编。

## 兼容与测试

`create_270p.py`、`create_540p.py`、`create_native540.py`、`package_*`、`build-windows.sh`、`build-compact.*`、`build-540p.ps1` 等保留上游／桌面格式支持，并非当前稳定包的一键重建步骤。当前稳定包有固定 RGBA 上限，勿直接用旧统一缩放链或高清恢复工具覆盖它。

`test_*`、`test-vita-*`、`vita-*-evidence.*`、`verify-vita-*` 覆盖图片、shader 输入、缓存、设备日志与探针契约，按目标选择运行。`test_clean_project.py` 验证清理路径、保留目录及链接不外溢。

旧 `cleanup-obsolete-assets.ps1` 依赖魔夜桌面包和已不存在的历史收据，已删除。当前 Vita 构建日志与产物写 `.work/`；部分兼容工具仍向 `doc/logs/` 或 `doc/` 顶层 JSON 输出临时报表，这些也由清理工具选择。需要长期保留的当前验证事实整理到 `doc/evidence/`。

完整说明见[构建](../doc/build.md)、[素材](../doc/assets.md)和[验证](../doc/validation.md)。
