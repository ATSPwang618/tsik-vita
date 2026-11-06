# knife · 月姬 Vita 引擎工作区

本目录为 `tsik-vita` 的 Rust／原生引擎工作区，基于 knife 0.9.4，参考 mofa-vita 的 Vita 适配。安装、当前包 hash 和操作说明统一见[项目根 README](../README.md)。

| 目录 | 职责 |
| --- | --- |
| `knife/` | 剧情 VM、舞台、UI、文字、输入与异步调度 |
| `knife-core/` | 归档／脚本／图像／字体格式，以及 SDK 大文件 IO |
| `knife-render/`、`knife-render-api/` | 桌面 WGPU／Vita GXM 和共享契约 |
| `knife-platform-vita/` | 平台、启动检查、存储与原生音视频 |
| `knife-audio/`、`knife-perf/` | 音频、性能计数和缓存预算 |
| `vita/` | C 后端、shader、vendor 构建依赖及 LiveArea |
| `kdu/`、`probes/` | 转换器与开发探针 |

当前月姬构建使用 960×540 场景／合成画布，简体中文／日文可选，默认 ID2，另一个 ID 为 0。程序是 ARMv7 32 位，SDK 文件偏移可用 64 位。原生构建入口位于上一层 `tools/`，从仓库根执行，详见[构建说明](../doc/build.md)。

桌面开发可在本目录用 `cargo +1.99.0 build --locked --release -p knife`，运行时指定匹配的桌面素材。Linux 另需 GStreamer 开发库；Vita GXT 素材不能直接混作桌面资源。配置示例见 [knife.ini.example](knife.ini.example)，Vita 入口不读取此配置。

格式机制见 [engine-writeup.md](engine-writeup.md) 与 [doc](doc)，来源见 [UPSTREAM.txt](UPSTREAM.txt)，许可证见 [LICENSE](LICENSE) 和原生 `vita/vendor/`。这些源码与 vendor 输入保留，`target/` 属于可重建缓存。
