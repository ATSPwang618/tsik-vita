# 文档总览（tsik-vita）

本目录有两组文档：

## A. 本次移植的文档（tsik-vita 当前交付）

| 文档 | 内容 |
|---|---|
| [00-porting-process.md](00-porting-process.md) | 参考项目 mofa-vita 的 PS Vita 移植流程调研（目录规范、A→G 素材链、引擎适配要点）+ 迁移到月姬海外版的差异与落地顺序 |
| [01-nsp-inventory.md](01-nsp-inventory.md) | 原始 NSP 解包事实：PFS0/NCA 清单、内容类型、exe build id、romfs 目录与归档清单、磁盘占用、命令与校验 |
| [02-engine-port-plan.md](02-engine-port-plan.md) | 引擎与构建工具的月姬变体改动清单（文件/符号/当前值→新值）、验证结果、转正（素材包）剩余步骤 |
| [03-build-env.md](03-build-env.md) | 构建环境实测：WSL/VitaSDK/Rust 版本、可复现命令、缓存隔离问题与修复、构建耗时与产物哈希 |
| [04-asset-pipeline-plan.md](04-asset-pipeline-plan.md) | 月姬海外版素材 → Vita 960×540 素材包的转换链分析（kdu compact、编码/语言条带、清单/profile/索引再生成、实测与时延） |
| [05-delivery-verification.md](05-delivery-verification.md) | 本次交付的可复核证据：产物/哈希、构建与包检查输出、NSP/版本对齐、540p 预处理状态、未验证项与复现命令 |

## B. 参考文档（从 mofa-vita 复制，描述上游引擎/移植基线）

这些文件对理解引擎与参考实现仍然有效，但文中的 TITLE ID、数据根、素材版本、构建变体与 `doc/03` 的
具体数字都属于 **mofa-vita（《魔法使之夜》）**，不是本仓库月姬交付的权威值；月姬的权威值以根 `README.md`
和 A 组文档为准。

| 文档 | 内容 |
|---|---|
| [01-架构总览.md](01-架构总览.md) | 项目定位、crate 结构、Vita 帧循环/线程模型、渲染目标与坐标系、资源格式 |
| [02-渲染与GPU后端.md](02-渲染与GPU后端.md) | GXM C 后端、批次/依赖图/completion、纹理池、运行时 shader 编译与缓存 |
| [03-构建与工具链.md](03-构建与工具链.md) | 上游 `build-vita.py` 用法、SDK/Rust 探测、vendor 依赖、VPK 打包（参考基线） |
| [04-资源调度与缓存.md](04-资源调度与缓存.md) | 资源生命周期、atlas/GXT、图像 worker、音频通道、缓存预算 |
| [05-优化记录与实测数据.md](05-优化记录与实测数据.md) | 20 个优化开关的历史实测（r2/r3/r4，480×270 捕获，不等于 960×540 终版） |
| [06-性能采集与分析.md](06-性能采集与分析.md) | 性能日志格式、采集框架、分析工具 |
| [07-已知限制与未验证项.md](07-已知限制与未验证项.md) | 上游基线的已知限制与未验证清单 |
| [08-素材与安装.md](08-素材与安装.md) | WoH r7 素材包契约与从原始数据制作素材的 A→G 链路（月姬沿用方法，归档集合不同） |

## 证据与约定

- 标记约定：**[代码]** 当前源码/脚本可核对；**[实测]** 本机本次会话的构建/转换输出；**[未验证]** 无设备或像素证据。
- 构建收据（`.work/vita/game-release-tsukihime-540p/vita-game-release-build.json`）固定声明
  `runtime_verified:false`、`hardware_verified:false`：它只记录构建事实。
- 设备表现（FPS、显存、稳定性）不得用上游历史数据代替；月姬的真机数据需另行采集。
