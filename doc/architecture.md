# 当前架构

## 工作区

| 位置 | 职责 |
| --- | --- |
| `knife/knife` | 月姬 VM、剧情、舞台、UI、文字、输入与缓存调度 |
| `knife/knife-core` | HED/NAM/MRG、NX、KIMG/KATL、字体和脚本解析；Vita 大文件 IO |
| `knife/knife-render`、`knife-render-api` | 桌面 WGPU／Vita GXM 与共享绘制契约 |
| `knife/knife-platform-vita` | 平台初始化、启动素材检查、存储、图像 worker、原生音视频封装 |
| `knife/knife-audio` | 音频资源、混音与流式准备 |
| `knife/knife-perf` | 优化 mask、计数、内存预算与采样 |
| `knife/vita` | C/GXM、Cg、原生解码、SDK 依赖和 LiveArea |
| `knife/kdu`、`knife/probes`、`tools/probes` | 转换器、开发探针与有界回归 |

入口为 `knife/knife/src/vita_entry.rs`；月姬分支由 `tsukihime` feature 选择。当前 TITLE ID 为 `KNIF00541`，运行数据根为 `ux0:data/TSUKIHIME-RE`，JA/ZC 原始语言 ID 为 0/2，默认 2。

## 资源与文件

启动检查只用一个 8192 字节缓冲：小型关键文件校验完整 CRC，大文件比较精确长度及首尾各 4096 字节 CRC。107 个关键文件绑定当前素材清单；这不是整包 hash 检查。

MRG 的偏移以 `u64` 表达，单条记录从 HED 扇区索引计算。Vita 使用 `file_io_native.rs` 的 SDK 只读句柄，通过 `sceIoLseek` 读写位置，解决 newlib 有符号 32 位 `off_t` 对超过 2 GiB 归档的截断。每个归档的 seek/read 由同一个 mutex 保护，索引和正文界限、解压预算均保留。桌面仍可使用 mmap。

KIMG 保存逻辑尺寸、物理尺寸、编码和精确 payload；KATL 保存图集成员。GXT 可直接上传，CPU 回退服务调色、语言条带与软件取样。图集及流资源索引由最终素材生成，均绑定同一清单 hash。

当前月姬稳定包离线限定全部剧情图片的最坏 RGBA 行距占用为 512 KiB，缩小物理像素而保留逻辑尺寸。UI／字体／分页缩略图保持原有分辨率。`tsukihime` 启用 `knife-perf/vita-stable` 收紧可选缓存；换图前让出可选目标及文字缓存所有权，已记录的原生纹理继续由命令编码器与完成 fence 保活。详见[素材](assets.md)与[性能预算](performance.md#内存上限)。

纹理准入通过 `kv_gxm_texture_reserve` 持有一份真实像素存储，匹配的后续上传直接接管；池化／非池化均支持，替换预留或关闭 owner 时释放。CDRAM 物理页不足和干净的预算拒绝允许有界回收未被待提交帧引用的纹理；映射、描述符和不确定释放错误继续上报，不能盲目重试。缓存的 slice charge、8 像素行距和新物理页的 256 KiB 对齐分别计量。

## 线程与渲染

- 主线程拥有游戏状态、UI、GXM 调用与显示提交；CPU worker 不直接操作 GXM。
- 图像 worker 有界读盘／解码；异步 rebake 仅在整组完成、generation 仍一致时发布，等待期间保留完整旧画面。
- 音效 worker 负责准备；VM 屏障保留原 PC 并在资源就绪后重试。音频流与 AudioOut 有独立的有界队列。
- 影片打开、轮询、控制与关闭由持续 owner 线程处理；主线程完成 GPU 取样后才 ACK 原生帧租约。
- 缓存与可选目标轮换按真实输入、源内容版本和目标版本判定；预算是上限，不是启动时全部预分配。

脚本逻辑坐标保持原游戏语义，scene／composite 为 960×540，显示输出 960×544。逻辑图像尺寸不等于纹理像素尺寸，不应对长立绘、动画条带和缩略图整页再做统一的整屏缩放。

## 存储与输入

存档位于统一数据根的 `saves/`，保留备份、临时提交、回读核验和恢复流程。资源失败记录为根目录的 `resource-error.json`。当前月姬 shader 全部内嵌 GXP，不再使用旧版 `shader-cache/`；详见[离线 shader](shaders.md)。磁盘清理工具不操作设备数据。

Vita ○ 映射 A、× 映射 B、□ 映射 X、△ 映射 Y，摇杆中心死区为 ±16。JA/ZC 选择、约 8 秒致谢开场与 R4 CG 页面由月姬适配负责，不能被魔夜专用 UI 默认值覆盖。

详见[性能预算](performance.md)、[素材契约](assets.md)及[排错](troubleshooting.md)。
