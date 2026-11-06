# 工具索引

[项目 README](../README.md) · [构建](../doc/build.md) · [素材](../doc/assets.md) · [验证](../doc/validation.md)

从仓库根运行。当前产品是月姬 Vita 540p；工具分为当前交付入口、公共转换组件和有限探针。需要自备的素材 / SDK / 二进制不应靠复制整套历史工作目录解决。

## 当前交付与维护

| 工作 | 入口 / 依赖 |
| --- | --- |
| 构建环境、VPK | `build-vita.py`，PowerShell / Bash 包装为 `build-vita.ps1`、`build-vita.sh` |
| 包结构检查 | `check-vita-package.py`，核对 TITLE / SFO / 成员 |
| 完整离线 shader | `compile-vita-offline-shaders.py`；`--check` 无需编译器，重编使用自备 psp2cgc |
| 共享 runtime shader 源码生成 | `generate-runtime-shaders.py`，保留非月姬 variant 的构建需求 |
| 启动 / atlas / stream 索引 | `generate_vita_asset_profile_tsukihime_540.py`、`generate-vita-atlas-index.py`、`generate-vita-stream-index.py` |
| 构建输入收据 | `vita-build-receipt.py`，历史收据不随文档编辑改写 |
| 缓存清理 | `clean-project.py` 默认预览，`--apply` 执行；保护素材、VPK、Git、证据与 vendor |

`release/` 只留最终 VPK，临时输出写 `.work/`。本地 `kdu.exe`、`hactool.exe`、`nstool.exe` 是转换辅助工具，不提交 Git，也不打进 VPK。

## 素材处理

| 阶段 | 工具 / 边界 |
| --- | --- |
| 自备原始数据检查 | `hactool/extract_tsukihime.py`、`hactool/nsp_tool.py`、`inventory_romfs.py`、`inspect_romfs_archives.py` |
| 公共图像 / 媒体 | `compact_media.py`、`create_compact.py` 等；需匹配输入与对应媒体工具 |
| 原生 GXT 编码 | `make-vita-assets.py`、`migrate-vita-native-color.py`、`native-color-blocks.c`；后两者也被其他转换器导入 |
| 资源格式 / 尺寸修复 | `repair-tsukihime-assets.py`、`vita_image_metadata.py` |
| JA / ZC 与字体 | `make-tsukihime-ja-zc.py`，自备字体，依赖 fonttools 等 |
| 稳定剧情预处理 | `stabilize-tsukihime-assets.py`，默认只读、`--apply` 原地事务改写；Pillow / NumPy / GXT 工具 |
| 历史高清恢复组件 | `restore_tsukihime_quality.py`，公共函数仍被当前工具和测试引用；完整恢复需原 romfs / UI cache / kdu，不直接覆盖稳定包 |
| 全图精确色数 / alpha 审计 | `audit-lossless-png.py` 和 bilingual probe 的 `audit_lossless_textures`；只读统计不生成第二套资源 |
| 全包解码与物理布局 | `verify-tsukihime-runtime-assets.py`，正式宿主 C decoder；可输出 layouts TSV 给 renderer 回归 |

旧 compact / 270p / native540、语言精简和桌面工具保留为受测试的公共格式链及兼容开发入口。它们不是“当前稳定素材一键重建器”，不能直接拿旧默认路径覆盖月姬数据。当前没有验证从任意 NSP 一步生成正式素材的通用命令。

## 回归与探针

| 范围 | 入口 |
| --- | --- |
| 目录清理边界 / 链接 / 嵌套 probe target | `test_clean_project.py` |
| shader 清单 / 二进制损坏 / 静态指令数 | `test_offline_shaders.py` |
| JA / ZC、质量、稳定预处理、事务 / 幂等 | `test_tsukihime_*.py` |
| 真实双语表、字体、CG、UI alpha | [tsukihime-bilingual](probes/tsukihime-bilingual/README.md)，examples 下的实际资源探针 |
| 原生预留 / P8 / RGB24 / 压缩上传 | `test-vita-reservation.sh`、`test-vita-lossless.sh`、`test-vita-compressed.sh` |
| 原生拷贝 / shader 路由与输入 | `test-vita-gxm-copy.sh`、`test-vita-effects-inputs.sh` |
| 图片、字形、present / viewport | `test-vita-image-*`、`test-vita-glyph-pages.sh`、`test-vita-gxm-*` 等按目标运行 |
| 共享模拟器证据 helper | `vita-*-evidence.mjs` 及相应测试；有限观察不是完整实机验收 |
| 桌面 / 兼容构建 | `build-windows.sh`、`build-compact.*`、`build-540p.ps1`；需相应桌面素材与依赖 |

回归有明确依赖和范围，不能因为脚本存在就宣称所有入口都能在空环境运行。设备采样目前通过 VitaDeck / CatLog 保存原始捕获；当前不提供已验证的通用日志汇总 CLI。

## 已移除的失效入口

- 两个旧部分 shader PowerShell 生成器：由完整 109 程序生成器取代。
- 旧 compact / 270p 交付报告写入器、两份固定魔夜 release 观察脚本：依赖旧包、已删除临时 fixture 或旧版语言布局。
- 旧性能读取器与测试：依赖仓库未提供的 `vita_audit_log.py` / `render-audit/compare-hardware.py`。
- 旧 Artemis 性能汇总器：绑定已删除的固定调查路径，不是当前日志分析工具。

删除原因和文件身份见[本轮整理收据](../doc/evidence/repository-maintenance-20261106.json)。历史代码在 Git 中可追溯，不在当前目录保存重复旧版本。
