# 优化与修复总表

[文档导航](README.md) · [性能预算](performance.md) · [Shader 细节](shaders.md) · [验证范围](validation.md)

截至 2026-11-06，以当前源码、离线 shader 收据与稳定素材验证为依据。优化不只指提高帧率，也包括减少峰值内存、读盘、重复解码、等待、写卡与资源失败。下列“已实现”不等于已在所有实机场景测得收益。

## 默认策略与来源

- 没有 `optimization-profile.txt` 时，[Vita 入口](../knife/knife/src/vita_entry.rs)自动选择 `IMPLEMENTED`。普通玩家无需创建 TXT 文件，离线 shader 与新增专用变体默认生效。
- [开关注册表](../knife/knife-perf/src/optimizations.rs)有 **29 项**。开关只是路径许可，驱动准入、输入状态和显存预算仍决定实际使用。
- 月姬 `tsukihime` feature 启用 `vita-stable`：静态前缀与目标轮换预算为 **0**。它们仍在共享代码和开关表中，但本月姬配置不分配对应可选目标，不能列为已启用的额外缓存。
- `archive-glow-bounds` 属于魔夜书库界面，保留共享实现，不把它当作月姬页面优化。
- 性能迁移来源固定为魔夜 `perf/render` 的 `46fc68859918c5107eeee534c8c00a05654301be`；UI 轴限制修复另参考固定提交 `86c1fd8`。不声称已包含未来提交或所有魔夜专用功能。

## 全部 29 项开关

### 资源读取与图片准备（10 项）

| 开关 | 减少的工作 / 实现 | 生效边界 |
| --- | --- | --- |
| `shared-atlas` | 共享图集来源与有界归档范围，减少整段复制和重复加载 | 由实际归档 / 索引 / 范围识别 owner，不合并不同内容 |
| `gxt-ready` | 已就绪 GXT 直接进入上传 / 重载路径 | 保留格式和尺寸检查；调色所需 CPU 展开仍可能发生 |
| `decode-owner` | 解码后的原生 owner 传递到后续处理，减少中间 RGBA 拷贝 | owner 必须覆盖实际切片与生命周期 |
| `gray-r8` | 适用的灰度数据使用单通道 R8 | 仅满足灰度路径契约的输入，不把普通彩图转灰 |
| `animation-window` | 只预测活跃动画附近三个位点，限制预取变体数 | 不改脚本、运动回调和真实动画计算 |
| `grade-cache` | 有界缓存 CPU 调色结果与灰度基底 | 以源、调色参数和语言分片区分；压力时淘汰 |
| `stream-index` | 固定资源流索引减少反复解析 / 定位 | 索引绑定配套素材；保留常规解析回退 |
| `coalesce-bake` | 合并已审计的连续调色 / 变换设置，在使用屏障前统一准备 | 源读取、快照、运动和其他指令为屏障，不能跨越 |
| `resource-io-cache` | 有界缓存归档读取结果，减少重复 seek / read / inflate | 不替代范围校验和文件身份检查 |
| `ui-source-prefetch` | 有界预取 UI 图集来源，降低首次使用等待 | 依赖共享图集路径；非无限制提前解码整套 UI |

主要源码：[assets.rs](../knife/knife/src/assets.rs)、[调色缓存](../knife/knife/src/graded_cache.rs)、[归档缓存](../knife/knife-core/src/format/archive_cache.rs)、[game.rs](../knife/knife/src/game.rs)。

### GXM 提交、内存与绘制（12 项）

| 开关 | 减少的工作 / 实现 | 生效边界 |
| --- | --- | --- |
| `batch-arena` | 批次拥有顶点 / 参数 arena，减少逐绘制重置 | arena 在 GPU 完成前保持有效，是异步提交的前置条件 |
| `async-submit` | 有界异步提交，减少全局 CPU 等待 | 依赖 batch arena，保留完成序列与显示队列上限 |
| `compact-stream` | 适用绘制使用紧凑顶点数据 | 输入必须能表达在对应布局中，否则完整布局 |
| `dependency-graph` | 使用资源依赖与完成序列，缩小同步范围 | 依赖 batch arena + async submit；保留读写依赖 |
| `source-rename` | 源更新时有界换用存储，减少等待在途读者 | 不覆盖 GPU 尚在使用的存储；有 owner / 内存上限 |
| `texture-pool` | 纹理切片池化与复用，减少每纹理独立物理页开销 | 切片与 256 KiB 物理页分开计费，回收不能破坏在途引用 |
| `group-fused` | 将允许的分组合成与舞台路径融合 | 保留 alpha、遮罩、绘制顺序；不适用时原路径 |
| `ps-fetch` | 使用原生目标颜色读取路径，减少对应快照中转 | 需要 shader / 驱动能力与混合契约准入 |
| `direct-stage` | 满足条件时直接复用 / 使用舞台结果，减少额外合成 | 不能跳过所需后处理或改变目标内容 |
| `group-batch` | 复用 / 合批符合条件的保留分组输出，减少舞台 pass | 本稳定配置最多 2 项 / 4 MiB，超过预算回退 |
| `plain-forcealpha` | 为无额外效果的 force-alpha 绘制选择已有专用路径 | 输入、软裁剪与混合条件须满足原生契约 |
| `blend-chain` | 16 种两层混合组合使用专用程序，减少中间处理 | 操作为 2 / 11 / 13 / 19；逐层 UV、顺序和量化保持，不满足则回退 |

主要源码：[Vita renderer](../knife/knife-render/src/vita.rs)、[GXM 后端](../knife/vita/gxm_backend.c)、[GPU 生命周期](../knife/vita/gpu_lifetime.inc)、[特效后端](../knife/vita/effects_backend.inc)、[混合链](../knife/knife-render/src/vita_blend_chain.rs)。

### 输出复用、UI 与专用 shader（7 项）

| 开关 | 减少的工作 / 实现 | 当前月姬边界 |
| --- | --- | --- |
| `stage-prefix` | 缓存静态舞台前缀，动态后缀继续绘制 | **稳定预算为 0**，保留共享实现及测试 |
| `ui-pass-cache` | 复用完整清屏 UI producer 的输出判断 | 元数据上限 256 KiB / 16 项；弱引用，不额外保存整图 |
| `archive-glow-bounds` | 缩小魔夜书库 glow 绘制区域 | **魔夜专用 UI**，不列为月姬界面收益 |
| `producer-reuse` | 根据完整输入、源版本和目标版本复用剧情输出 | 源、几何或效果变化即失效重绘 |
| `async-rebake` | CPU worker 准备新图片，整组就绪后一次发布 | generation 必须匹配，等待时保留完整旧画面；脚本屏障 PC 可重试 |
| `target-ring` | 完整重绘舞台 / 合成目标可有界轮换，降低等待 | **稳定预算为 0**；历史内容 / noise 不允许任意轮换 |
| `shader-specialization` | 63 个专用变体减少无用波纹、裁剪、文字、模糊与混合分支 | 默认开启；逐绘制检查输入和已链接状态，不适用时原程序 |

主要源码：[producer reuse](../knife/knife/src/game/producer_reuse.rs)、[异步整组发布](../knife/knife/src/game/rebake_cohort.rs)、[UI pass cache](../knife/knife/src/game/ui_pass_cache.rs)、[stage prefix](../knife/knife/src/game/stage_prefix.rs)、[离线 shader](../knife/vita/offline_shaders.c)。

## 不依赖单独开关的专项优化

| 项目 | 当前做法 | 证据与限制 |
| --- | --- | --- |
| 全部特效离线化 | 109 个 GXP 内嵌，包括基础绘制、全部引擎特效入口、16 个混合组合和 63 个专用变体 | [清单](evidence/offline-shaders.json)；不需运行时编译器和磁盘 shader cache，驱动注册 / patch 仍在设备执行 |
| 稳定素材预处理 | 23,177 条扫描、15,901 条按比例缩小；选中语言后 RGBA 行距 ≤512 KiB、单轴 ≤960、压缩载荷 ≤512 KiB | [预处理](evidence/stability-preprocessing.json)；有损重采样 / DXT 重编码，UI / 字体 / 分页缩略图除外 |
| 精确 P8 / RGB24 | 完整 RGBA ≤256 色且能省物理页时使用 P8；不透明多色使用 RGB24，否则 RGBA8 | 含半透明与透明像素 RGB；不减色，不额外建整图中间副本；原生压缩 GXT 不反向扩大为 P8 |
| 真实显存预留 | 准入取得实际存储，上传接管同一份预留；压力时有界 LRU 淘汰 | 区分预算 / 物理页不足与描述符 / 映射错误，后者不得无限重试；帧引用始终 pin |
| 缓存生命周期 | 换图前释放可选目标、分组和近期文字缓存的所有权 | 已记录纹理由命令编码器 / GPU 完成 fence 保活，不提前销毁 |
| 分段文字缓存 | 稳定的 8 字片段可缓存，完成后合并整段 | key 包含 alpha、描边、页版本、UV 与像素相位；预算 4 MiB / 16 项 |
| 音效准备 | CPU worker 与保留 PC 的 VM 屏障、有界 PCM 缓存 | 延迟时间仅消费一次，资源就绪再继续；缓存与临时 pin 可能共享 owner |
| 影片 owner 线程 | 一个持续线程管理打开、轮询、控制和关闭 | 主线程完成 GPU 取样才归还帧租约；缓存 3 MiB |
| 启动检查 | 107 个关键文件的精确长度与 CRC 分级检查，复用 8192 字节缓冲 | 大文件只读首尾各 4096 字节；不是整包 SHA 验证 |
| 大文件读取 | SDK SceUID + 64 位 SceOff、同步 seek/read，绕过 newlib 32 位 off_t 截断 | ARMv7 可执行文件仍为 32 位；保留短读、范围和精确大小检查 |
| 实时日志 | 有界后台队列、UTF-8 分片、5 秒性能窗口 | 默认开启；不逐帧写卡，不把 CPU 提交耗时当作 GPU 时间 |
| 存档保护 | 临时提交、备份、回读校验与恢复 | 保存位置固定在独立月姬目录，清理工具不操作玩家存档 |

## 迄今的显示与功能修复

| 问题 / 调整 | 当前处理 |
| --- | --- |
| 四语言与字体资源冗余 | 仅 JA / ZC，保留原 ID 0 / 2，默认简中；动态文字使用指定主字体并保留补充字形 |
| Music 列表、时间和音量缺字 | 主字体优先，避免两字补充字体成为主字体 |
| CG 列表空白 | 修复 KIMG / KATL 加载路径，保持原资源编号与解锁语义 |
| 缩略图严重模糊 | R4 分页：每语言 28 页、每页 6×12 格、每格 116×66，日中共 3960 个有效格位，保留原 ID |
| 标题 / 三角菜单按钮消失 | 修复宽长 GXT 准入：单轴 2048、像素预算仍为 960×1080；覆盖 24 图集 / 438 成员，避免一成员拒绝导致整组失败 |
| CG 单侧浅灰边 | 增加摇杆 ±16 死区；SELECT 提供保持比例的铺满模式；非 16:9 图片原本可能有留边 |
| parts 加载路径 | GXT 按原生格式处理，避免误走 PNG / JPEG 解码 |
| 错误致谢图和播放时间 | 正确 @Zarathustra / @lisen 图片，30 + 420 + 30 帧，60 Hz 约 8 秒，保留跳过 |
| 按键与目录 | A→○、B→×；数据根统一 TSUKIHIME-RE；TITLE ID KNIF00541 |
| 素材失败后定位困难 | 保留具体资源状态 / 错误记录和 VitaDeck 控制台；不能把资源失败悄悄当作加载成功 |

## 收益与验收的边界

稳定素材相对上一高清包减少约 **1.75 GiB** 数据；这是离线包大小变化，不是同等数值的显存释放。普通 960×540 图的 RGBA 新页从 2 MiB 降为 512 KiB，已知失败立绘从 4 MiB 降为 512 KiB；多 owner、UI、目标与驱动仍共同决定峰值。

shader 静态主指令流缩短可查[指令表](shaders.md)，不能直接换算 FPS。宿主有界测试、编译产物身份和 SDK doubles 的作用范围见[验证记录](validation.md)。稳定配置全套仍有 5 项测试依赖旧缓存预算；当前没有本版完整实机 GPU 时间、像素一致性或全路线稳定性结论。
