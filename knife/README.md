# knife · 月姬 Vita 引擎工作区

[简体中文](../README.md) · [English](../README.en.md) · [技术文档](../doc/README.md)

本目录是 tsik-vita 的 Rust / 原生 C 引擎工作区，基于 knife 0.9.4，参考 mofa-vita。玩家安装、按键、截图和致谢统一见根 README；优化与修复集中在[优化总表](../doc/optimizations.md)。

| 目录 | 职责 |
| --- | --- |
| `knife/` | VM、舞台、UI、文字、输入与资源调度 |
| `knife-core/` | 归档、脚本、图像、字体及 SDK 大文件 IO |
| `knife-render/`、`knife-render-api/` | 桌面 WGPU / Vita GXM 与绘制契约 |
| `knife-platform-vita/` | 平台、启动检查、存储、图像 / 音视频封装 |
| `knife-audio/`、`knife-perf/` | 音频、性能计数、29 项优化注册与稳定预算 |
| `vita/` | 原生后端、离线 shader、vendor 依赖与 LiveArea |
| `kdu/`、`probes/` | 转换器和开发探针 |

当前 Vita 目标为 ARMv7 32 位，场景 / 合成 960×540；JA / ZC 默认 ID 2。64 位 SDK 文件位置解决大归档寻址，不改变指针宽度。月姬内嵌离线 GXP 并默认开启已实现优化；共享非月姬与桌面路径仍保留，不能按单一 feature 删除其他实现。

Vita 构建从仓库根 `tools/build-vita.py` 进入，详见[构建](../doc/build.md)。桌面可在本目录使用 `cargo +1.99.0 build --locked --release -p knife`，但需要匹配桌面素材，Linux 还需 GStreamer 开发库。Vita 不读取 [knife.ini.example](knife.ini.example)。

保留生成索引、GXP 头与 `vita/vendor/`，它们都是构建输入；Cargo target 属于缓存。来源见 [UPSTREAM.txt](UPSTREAM.txt)，许可证见 [LICENSE](LICENSE) 和 vendor；上游格式研究见 [engine-writeup.md](engine-writeup.md) 与 [doc](doc)。当前包和实机待验收边界以[验证手册](../doc/validation.md)为准。
