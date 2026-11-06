# 性能、内存与日志

[优化总表](optimizations.md)列出全部机制；本文维护当前默认配置、预算和设备采样方法。来源提交及历史修复不重复散落在多份文档中。

## 默认开启

[Vita 入口](../knife/knife/src/vita_entry.rs)在没有 `optimization-profile.txt` 时直接选择全部已实现开关。当前 29 项包含 `shader-specialization`；正常安装无需任何 TXT。已有自定义 profile 会继续覆盖默认值，开发者复测时应记录该事实。

开关许可不等于额外内存常驻。月姬启用 `vita-stable`，`stage-prefix` 与 `target-ring` 的预算为 0；魔夜专用书库裁切也不作用于月姬页面。通用与专用 shader 根据驱动和输入选择，详情见[Shader](shaders.md)。

## 内存上限

来源为 [memory_budget.rs](../knife/knife-perf/src/memory_budget.rs)、原生 owner 与内核准入。数字是上限 / 余量条件，不是启动预分配量，也不能简单相加当作实机峰值。

| 类别 | 当前上限 / 条件 |
| --- | --- |
| newlib 普通堆 | 256 MiB；包 ATTRIBUTE2=12 |
| CPU 编码源 / 调色结果 | 64 MiB / 32 MiB |
| CPU 调色基底 | 3 MiB |
| 音效缓存 / 临时 pin | 各 16 MiB，可共享 PCM owner |
| 音效准备 | 检查 40 MiB 普通堆余量，任务编码和 PCM 另有限额 |
| CPU 压力 / 目标余量 | 32 MiB / 48 MiB |
| UI pass 元数据 | 256 KiB、最多 16 项，不另存整图 |
| GPU resource / source 预算 | 56 MiB / 32 MiB，按各自 owner 与准入路径计费 |
| GPU 文字缓存 | 4 MiB、最多 16 项 |
| GPU 分组缓存 | 4 MiB、最多 2 项 |
| 可选静态前缀 / stage、canvas spare | 0 / 0 |
| CDRAM 压力 / 可选缓存准入余量 | 16 MiB / 8 MiB，条件检查而非占用 |
| 影片 RGBA 帧缓存 | 3 MiB |
| 剧情单图最坏 RGBA 行距占用 | 512 KiB，来自离线素材策略 |
| 受保护 UI 最大 RGBA 新页 | 4 MiB，不套用剧情上限 |

## 纹理存储与生命周期

1. 原生 DXT1 / DXT5 GXT 保留压缩上传。CPU 调色或其他软件取样确实需要 RGBA 时，不能拿压缩文件大小代替展开开销。
2. 不可变 CPU 图片按完整 RGBA 计色。≤256 色且索引、调色板合计能比 RGB24 / RGBA8 至少省一个 256 KiB 页时用 P8；高色数不透明图用 RGB24，其余保持 RGBA8。透明像素 RGB 和半透明 alpha 均保留，不做减色。
3. P8 索引行距按 8 像素对齐，256×4 字节调色板按 64 字节边界放在同一分配中。直接从 RGBA owner 写入最终存储，不另建整图 RGB / 索引副本。
4. 准入取得真实存储，上传接管同一份预留。切片、8 像素行距与 256 KiB 新物理页分别计量；不足时有界淘汰可重载且未被帧 pin 的资源。
5. 换图前释放可选离屏、分组、静态前缀和最近文字缓存所有权；已记录纹理由命令编码器及 GPU 完成 fence 保活。必需舞台、合成、noise / 历史目标保留。
6. 新图片按整组和 generation 发布，等待时保留完整旧画面。不可恢复的描述符、映射或释放错误仍报错，不进行无限重试。

单张 512 KiB 上限使 40 层旧新两版图片在“一层一版一张”的假设下最多 40 MiB；此数字不包括 UI、必需目标、驱动和其他 owner。48 MiB 宿主压力夹具通过仅证明指定集合，不代表全游戏最大峰值。

## VitaDeck 实时日志

当前包默认启用后台控制台和性能窗口。使用已配置好的 CatLog 与 VitaDeck 日志接收端：先开启接收，再启动 `KNIF00541`。FTP 负责文件传输；日志为独立通道。本地曾使用 FTP 1337、日志接收 8080，它们是用户环境配置，不是引擎强制端口。

普通 Rust 日志最多 2048 字节加换行，超过原生 900 字节记录限额时按 UTF-8 分片。后台队列最多 3 批 / 192 KiB，每批最多 96 KiB；拥塞丢整批并计数。性能窗口每 5 秒输出，游戏不持续生成 `performance.log`，需要时在 VitaDeck 保存捕获内容。

调试覆盖规则：先查数据根 `perf-enable.txt`，再查 `assets/perf-enable.txt`；不存在使用编译默认，内容 `1` 开启，其他值关闭。它只控制性能采样，不控制启动 / UI / 错误日志。构建时 `KNIFE_VITA_QUIET=1` 可静音，`KNIFE_PERF_CONSOLE=0` 可关闭默认采样。**这些是可选开发覆盖，玩家无需创建。**

## 比较方法与工具边界

- 记录 VPK / manifest hash、语言、存档、操作序列、采样时长和自定义 profile；使用相同重场景比较。
- 分开看读盘、解压、解码、CPU 提交、同步等待与 GPU 耗时。CPU submit 数值不等于 GPU 像素处理时间；音频主动暂停也不等于缺样。
- shader A/B 只关闭新增专用变体时，按[Shader 手册](shaders.md)操作；两组都使用离线程序。
- 当前保留原始日志接收与引擎计数。旧 `read-vita-performance.py` 链依赖缺失模块，旧 Artemis 汇总器只消费已删除调查目录，已从仓库移除；不再宣传它们为当前可用分析入口。
- 尚无本版月姬完整设备 FPS、功耗、GPU 时间或内存峰值对比，不引用魔夜数据作为本版结果。宿主结果见[验证](validation.md)。
