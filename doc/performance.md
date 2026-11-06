# 性能迁移与内存

参考魔夜已发布的 [`perf/render` 提交 46fc68859918c5107eeee534c8c00a05654301be](https://github.com/ATSPwang618/mofa-vita/commit/46fc68859918c5107eeee534c8c00a05654301be)。迁移使用固定 Git 对象，未将参考目录未提交文件作为来源。共同代码接近 `1434998` 基线，本次纳入之后适用的系统页面与剧情调度优化。

## 迁移范围

| 优化 | 实现与边界 |
| --- | --- |
| 剧情输出复用 | `game/producer_reuse.rs` 按完整输入、源内容和目标版本判断；几何、效果或源变化后重绘 |
| 两层混合 | `vita_blend_chain.rs` 与 Cg 同步；保持 UV／运算顺序，非仿射和不支持输入回退 |
| 文字缓存 | 稳定的 8 字片段后可合并整段；逐字 alpha、描边、字体页版本、UV 与像素相位进入 key |
| 异步 rebake | 有界 image worker，整组就绪且 generation 匹配才发布；等待时保留旧画面 |
| 音效准备 | 独立 CPU worker，PC 保留的脚本屏障，延迟声音时间只消费一次 |
| 影片 owner | 持续线程拥有原生解码器；GPU 完成取样后归还原生表面租约 |
| UI producer | 可复用完整清屏的系统页面目标；元数据有界且弱引用，不另存一份图片 |
| 目标轮换 | 仅对完整重绘 stage／canvas 创建可选 spare，不轮换保留历史内容的 noise |
| 资源 IO | 分语言调色基底、预热与固定 stream 索引；MRG 统一使用修复后的 SDK 大文件读取 |

上游魔夜书库 glow 裁切、标题读档页等专用逻辑不能直接等同于月姬菜单优化。JA/ZC 选择、R4 缩略图、字体、目录、8 秒致谢、○／× 映射和失败记录均保留。

UI 回归修复另外参考本地魔夜固定提交 `86c1fd8` 的 `defer_source` 范围校验：原生压缩 GXT 可在任一轴达到 2048，但物理像素仍不得超过 `960×1080`；PNG/JPEG 仍限 `960×1080`，画布仍为 960×540。月姬 R4 中 15 个成员超出旧轴限制，会导致所在 9 个图集整组加载失败；这不是所有按钮图片本身变透明。实际素材与回归范围见[验证](validation.md)。

默认 `all` 启用 29 个已实现开关，含本次 `shader-specialization`；自定义 `optimization-profile.txt` 只启用列入的项，实际列表以 `knife-perf/src/optimizations.rs` 为准。109 个离线程序、63 个专用变体、静态指令对比及 A/B 方法见[离线 shader](shaders.md)。离线化消除启动编译，专用变体减少对应绘制的无用运算；实机 GPU 时间需另行采样。

## 内存上限

这些是按需分配／淘汰的上限与准入条件，不能直接相加当作实机峰值。

| 项目 | 上限或准入 |
| --- | --- |
| newlib 普通堆 | 256 MiB；ATTRIBUTE2=12 |
| CPU 编码源／调色结果 | 64 MiB／32 MiB |
| CPU 调色基底 | 3 MiB |
| 音效缓存／临时 pin | 各 16 MiB，可共享 PCM owner |
| 音效准备 | 检查 40 MiB 普通堆余量，编码与 PCM 另有限额 |
| UI pass 元数据 | 256 KiB，最多 16 项 |
| 文字缓存 | 4 MiB，最多 16 项 |
| 分组输出缓存 | 4 MiB，最多 2 项 |
| 可选 stage／canvas spare、静态前缀 | 本月姬稳定 profile 均为 0 |
| 内核 CDRAM 压力余量／可选缓存准入余量 | 16 MiB／8 MiB，条件检查而非实际预占 |
| 影片 RGBA 帧缓存 | 3 MiB |
| R4 CPU RGBA 解码 | 单次最多 `4×960×1080` 字节 |
| 剧情／CG 单图最坏 RGBA 新页 | 512 KiB，含行距和页对齐；压缩源最多同量 |
| 受保护 UI 的最大 RGBA 新页 | 4 MiB；未将整个包强制缩到剧情上限 |

CDRAM 空闲总字节只是采样信息。当前准入会真正保留下一张纹理需要的存储，上传直接接管；干净的物理页分配失败也进入既有有界 LRU 回收。预留最多一份，不建立额外的整图 GPU 副本。描述符／映射／不确定释放错误保持失败；全帧 pin 与既有缓存预算继续生效。此项已离线验证，未给出新包的实机帧率／峰值改善结论。

稳定参数由 `knife-perf/vita-stable` 提供，只随月姬 feature 启用；共享魔夜 profile 保持原参数。每组演出换图／调色准备开始时，先释放可选 stage/canvas spare、分组／前缀缓存和最近的文字缓存所有权，再准备新图片。命令编码器持有已记录的原生纹理，GPU 完成取样前仍由原生 fence 保活。必要的 stage、主合成、group／noise／历史效果目标保留，缓存缺失按原路径重绘。

此次离线预处理覆盖所有剧情图片，直接限制最坏展开与调色像素量；不靠 DXT 的文件大小推断显存。23,177 个图片条目中缩小 15,901 个，详见[素材说明](assets.md)。48 MiB 宿主纹理预算下，80 张各 512 KiB 的旧新 RGBA 图片、两个 960×540 必需目标和一张 2 MiB UI 同时保留并提交通过；该夹具不代表真实所有 owner 的最高同时驻留量，驱动与实机验收仍独立。

其余预算和压力条件以 `knife-perf/src/memory_budget.rs`、原生 owner 计数和内核空闲内存检查为准。JNI／Android 运行时不在此项目路径中，实际后端为直接 GXM。

## 无损纹理存储

不可变 CPU 调色图片在上传前按完整 RGBA 计色。最多 256 色、且索引加调色板比 RGB24／RGBA8 至少少用一个 256 KiB CDRAM 页时，使用原生 `P8_ABGR`。每个调色板条目保留四个 8 位通道，包含半透明与完全透明像素的 RGB；不合并透明颜色、不减色、不改尺寸。超过 256 色的不透明图片使用原生 RGB24，其他透明图片保持 RGBA8。

P8 的索引行距按 8 像素对齐，256×4 字节调色板按 SDK 的 64 字节边界排列，两者属于同一个原生分配。RGB24／P8 从原 RGBA owner 直接写进 CDRAM，不额外建立一整张 RGB／索引缓冲。首次准入、上传、缓存计费与淘汰后重载保持同一存储格式；调色板计入预留和池化切片。动态图片、字库覆盖图、渲染目标仍使用原来的可写格式。

| 历史高清包的无损上传例子（本版已降分辨率） | 原 RGBA 新页 | 优化后新页 |
| --- | --- | --- |
| `IMG2459` 简体／日文分片，960×540，252／245 个完整 RGBA 色，含半透明 | 2 MiB | P8 512 KiB |
| 1020×1016 不透明多色回归夹具 | 4 MiB | RGB24 3 MiB |

上一版无损存储审计覆盖 23,113 张 GXT 和 813 个 PNG/JPEG／语言分片，其中 275 个源条目符合当时的 P8 条件。当前稳定素材另经全部 GXT 解码，290 个选中语言候选符合条件，其中 242 个带 alpha、237 个有半透明。候选不是同时驻留内存，也不代表每个源条目一定走 CPU 调色；实际上传重新检查调色后的像素。运行时原生 DXT1／DXT5 GXT 保持直接压缩上传，不转成较大的 P8；本次离线缩小的 GXT 已重新编码，不能再称整套素材无损。原生 C packing/readback、SDK doubles 与全部实际尺寸回归通过，尚无新包实机 GPU 采样、峰值／帧率结论。历史无损阶段数据见[审计记录](evidence/lossless-textures.json)，本次统计与包身份见[当前验证](evidence/current-validation.json)及[预处理证据](evidence/stability-preprocessing.json)。

## VitaDeck 实时日志

当前月姬正式构建默认 `KNIFE_VITA_QUIET=0`、`KNIFE_PERF_CONSOLE=1`，与魔夜当前本地交付的显式开关一致。`vita_log.rs` 把 `tracing` 的 INFO/WARN/ERROR 接入原有 `audit::console` 后台队列；`DevLog` 的启动／运行里程碑也进入控制台，DEV 的文件输出保持独立。UI 登记成功记录图集和绑定数，失败记录图集、成员、尺寸与原因。DEBUG/TRACE 不发送。

输出路径是 **`sceClibPrintf → CatLog → VitaDeck 日志页`**。FTP 是传输文件的另一个连接。当前本机 VitaDeck 配置的 FTP 端口 1337、日志端口 8080，实际端口以接收端配置为准。沿用魔夜已配置的 CatLog；本项目不会自动安装插件、修改 taiHEN 配置或启动新的网络服务。用 VitaDeck 启动月姬时 TITLE ID 应为 `KNIF00541`。

普通运行记录最多 2048 字节加换行；超过原生 900 字节单条上限时复用 `console_codec` 的 UTF-8 分片。队列最多 3 批／192 KiB，每批最多 96 KiB，拥塞丢整批并计数；这些 Rust 日志由后台执行 printf，不因接收端断开持续写卡。游戏不自动生成 `performance.log`，需在 VitaDeck 保存捕获内容。

性能窗口每 5 秒输出。启动时先查 `ux0:data/TSUKIHIME-RE/perf-enable.txt`，再查 `assets/perf-enable.txt`；不存在则用编译默认，`1` 开启，其它值关闭，根目录文件优先，重启生效。此开关只控制性能采样，不关闭普通运行／UI 警告。开发者可在编译时指定 `KNIFE_VITA_QUIET=1` 完全静音，或 `KNIFE_PERF_CONSOLE=0` 关闭默认性能采样。当前包收据记录了实际开关。

## 采样与验证限制

`summarize-vita-artemis-performance.py` 处理设备采样；字段 schema 以源码与样本匹配为准。stream 缺样计数不包含主动暂停，CPU 提交耗时不能当作 GPU 像素完成耗时。宿主日志桥接测试和 ARM 构建不能证明当前设备 CatLog 链路已接收新包，实机连接仍需复测。

共享性能分析工具仍有既有缺口：`read-vita-performance.py`／`test-vita-performance.py` 依赖当前仓库未提供的 `vita_audit_log.py` 与 `tools/render-audit/compare-hardware.py`。这些文件在清理前已缺失，不能宣称此分析入口能在干净检出下直接运行。保留相关源码供补齐依赖；本次不将缺失依赖的测试计为通过。

历史宿主渲染后端曾错误地把 rim28 的逐顶点描边和 chain27 的第二层 UV 视为全批共享，现按实际 C 输入契约检查。渲染测试切换全局 mask，必须 `--test-threads=1`。

目前没有本次月姬优化的完整设备 FPS／功耗／内存峰值证据，不引用魔夜的帧率作为月姬结果。当前验证及保留证据见[validation.md](validation.md)。
