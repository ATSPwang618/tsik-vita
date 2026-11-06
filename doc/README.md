# 技术文档导航

[中文 README](../README.md) · [English README](../README.en.md) · [工具索引](../tools/README.md)

本文档描述当前月姬 Vita 工程。详细技术手册使用中文；安装、特性、操作和交付边界在中英 README 中对应维护。参考魔夜的实现时固定来源提交，不把魔夜实机结果当作月姬本版验收。

## 按任务查找

| 需要做什么 | 文档 |
| --- | --- |
| 查看迄今全部优化与修复 | [优化总表](optimizations.md)：29 项开关、专项修复、默认行为和证据 |
| 理解引擎、线程、资源与生命周期 | [架构](architecture.md) |
| 构建 VPK、更新生成文件 | [构建](build.md) |
| 核对素材、画质、双语言与升级 | [素材](assets.md) |
| 检查显存预算、日志与调度 | [性能与内存](performance.md) |
| 修改特效、编译离线程序、比较专用路径 | [Shader](shaders.md) |
| 查看包身份、通过项、失败项及复现命令 | [验证](validation.md) |
| 排查缺图、素材错误、白边、日志问题 | [排错](troubleshooting.md) |
| 清理目录、维护文档或准备本地交付 | [仓库维护](maintenance.md) |

## 当前状态的唯一职责

- **安装与游玩**：根目录中英 README，不堆叠历史升级过程。
- **优化清单**：`optimizations.md`，列出机制与生效边界；预算放在 `performance.md`，shader 指令表放在 `shaders.md`。
- **当前包身份和测试范围**：`validation.md`；原始构建、素材和历史诊断记录放在 `doc/evidence/`。
- **源码格式研究**：[engine-writeup.md](../knife/engine-writeup.md) 与 [knife/doc](../knife/doc)，保留上游机制资料，不作为当前交付说明。

已完成的稳定素材实施计划并入素材、优化与验证手册，不再单独维护旧任务清单。失效的旧魔夜交付报告入口及旧部分 shader 生成器已移除；恢复历史文件可使用 Git 历史，不在目录中另存旧副本。

## 证据阅读顺序

1. [当前构建收据](evidence/current-build.json)与[当前验证摘要](evidence/current-validation.json)：2026-11-06 离线 shader 包；收据中的分支和远端字段是生成时快照。
2. [离线 shader 清单](evidence/offline-shaders.json)与[对应测试摘要](evidence/offline-shader-tests.txt)：109 个程序和本轮有界测试。
3. [稳定素材验证](evidence/stable-assets-validation.json)、[预处理](evidence/stability-preprocessing.json)与[尺寸审计](evidence/image-size-audit.json)：2026-11-02 素材阶段。
4. [证据索引](evidence/README.md)：其余历史诊断、清理记录和适用边界。

源码核对、宿主测试、ARM 构建、设备观察分别陈述。部分测试通过不能改写为全套通过；没有实机证据就不修改 `hardware_verified:false`。旧收据中已清理的临时路径只用于追溯，不能承诺文件仍存在。
