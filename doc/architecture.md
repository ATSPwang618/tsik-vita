# 架构与运行契约

[文档导航](README.md) · [优化总表](optimizations.md) · [预算](performance.md)

## 工作区职责

| 路径 | 职责 |
| --- | --- |
| `knife/knife` | 剧情 VM、舞台、UI、文字、输入、存档和资源调度 |
| `knife/knife-core` | HED / NAM / MRG、NX、KIMG / KATL / GXT、字体与脚本解析；Vita 文件 IO |
| `knife/knife-render` / `knife-render-api` | 桌面 WGPU、Vita GXM 与共享绘制契约 |
| `knife/knife-platform-vita` | 平台初始化、素材启动检查、存储、图像 worker、原生音视频封装 |
| `knife/knife-audio` / `knife-perf` | 音频、优化 mask、计数与内存预算 |
| `knife/vita` | C / GXM、Cg / GXP、原生解码、SDK 依赖及 LiveArea |
| `knife/kdu`、`knife/probes`、`tools/probes` | 素材工具与开发 / 回归探针 |

入口是 [vita_entry.rs](../knife/knife/src/vita_entry.rs)。月姬通过 `tsukihime` feature 选择，自动启用稳定预算。TITLE ID 为 `KNIF00541`，数据根为 `ux0:data/TSUKIHIME-RE`。默认选中简体中文 ID 2，日文为 ID 0。

## 资源读取链

~~~text
配套素材清单 / 生成索引
  → 启动精确长度与分级 CRC 检查
  → SDK 文件句柄 + 归档范围 / NX 解压
  → KIMG 或 KATL / 选中语言
  → GXT 压缩上传，或有界 CPU 解码 / 调色
  → 真实纹理存储预留 + owner
  → 帧 pin / 提交 / GPU 完成后回收
~~~

启动 profile 绑定 107 个关键文件：小文件完整 CRC，大文件精确长度与首尾各 4096 字节 CRC，复用 8192 字节缓冲。它检测常见缺失 / 错配，不等价于整包 SHA。

Vita [原生文件层](../knife/knife-core/src/file_io_native.rs)持有 SceUID，经 `sceIoLseek` 使用 64 位文件位置；每个归档的 seek/read 受同一 mutex 保护。程序仍是 ARMv7 32 位。范围、短读、索引和解压预算保持检查；桌面可继续使用 mmap。

KIMG 区分逻辑宽高、物理宽高、编码与 payload；KATL 保存成员。脚本逻辑尺寸和坐标不随纹理降采样改变。图集 / 流索引从最终素材生成并绑定同一清单 hash。

## 线程、状态与生命周期

| Owner | 工作与约束 |
| --- | --- |
| 主线程 | 游戏状态、UI、GXM 调用和显示提交；CPU worker 不调用 GXM |
| 图像 worker | 有界读盘 / 解码；异步 rebake 只在整组完成且 generation 一致时发布 |
| VM 屏障 | 准备未完成时保留 PC，资源就绪后重试；延迟时间不能重复消费 |
| 音效 / 音频线程 | 有界准备、混音与 AudioOut 队列 |
| 影片线程 | 持续拥有原生解码器，主线程 GPU 取样完成后 ACK 帧租约 |
| 命令编码器与完成 fence | 保活已记录纹理；释放缓存引用不能让 GPU 在途资源提前销毁 |

换图 / 调色前释放可选缓存所有权，为旧新图片同驻留让出空间。必要画布及历史效果目标保留。输出复用必须核对输入、源内容版本和目标版本，不以“上一帧看似相同”判断。

纹理准入保留一份真实存储，匹配上传直接接管。干净的预算 / 物理页不足允许有界回收；描述符、映射、不确定释放错误继续失败。池切片与物理页分别计费；详见[性能与内存](performance.md)。

## 渲染与 shader

场景 / 合成画布为 960×540，显示输出为 960×544。物理纹理可以是长图、分片或图集，不能统一拉伸成整屏。剧情图离线最坏 RGBA 行距上限为 512 KiB，UI / 字体 / 分页缩略图另按格式预算检查。

月姬使用 `offline_shaders.c` 和两个生成头，内嵌 109 个程序。专用 shader 在验证输入、驱动准入和混合状态后选择，不适用时走同类通用程序。设备仍执行 program check / 注册 / patch。共享非月姬构建保留运行时 shader 编译源码，不能按月姬单一 feature 将其误判为死代码。

## 存储、语言与输入

- `saves/` 保存配置、进度和存档，保留临时提交、备份、回读核验与恢复。
- 数据根的 `resource-error.json` 用于资源失败定位。当前月姬离线 shader 不再读写旧 shader cache。
- A / B / X / Y 对应 ○ / × / □ / △；摇杆 ±16 死区。菜单操作、快存许可仍由游戏状态决定。
- 双语言 ID、原归档 ID、分页缩略图映射、字体和 8 秒致谢是月姬契约，不能由魔夜专用 UI 默认值覆盖。

格式研究另见 [engine-writeup.md](../knife/engine-writeup.md) 与 [knife/doc](../knife/doc)。这些资料保留来源与研究边界；当前包验收以[验证手册](validation.md)为准。
