# 月姬 Vita 技术文档

本目录只维护当前 `tsik-vita` 的实现和交付状态。魔夜是移植参考，不能把参考项目的 TITLE ID、数据目录、素材版本或帧率直接套用到月姬。

| 文档 | 用途 |
| --- | --- |
| [architecture.md](architecture.md) | 源码职责、线程、资源读取、渲染与存储 |
| [build.md](build.md) | Vita 构建环境、依赖、命令和产物 |
| [assets.md](assets.md) | 当前稳定素材上限、UI／双语言与升级 |
| [performance.md](performance.md) | 固定上游提交、迁移范围、预算和采样 |
| [shaders.md](shaders.md) | 全部离线特效、像素运算精简、编译与实机 A/B |
| [validation.md](validation.md) | 当前包身份、验证摘要及实机限制 |
| [troubleshooting.md](troubleshooting.md) | 启动检查、大文件 IO、显示与日志问题 |
| [maintenance.md](maintenance.md) | 仓库结构、可清理数据与磁盘维护 |

[根 README](../README.md) 面向安装与游玩；[工具索引](../tools/README.md) 面向开发者。引擎格式研究保留在 [engine-writeup.md](../knife/engine-writeup.md) 和 [knife/doc](../knife/doc)，这些是机制参考，不是当前交付身份。

## 验证记录

- [当前构建收据](evidence/current-build.json)：固定实际源码输入、参数、包成员和哈希。
- [离线 shader](evidence/offline-shaders.json)：109 个程序的重复编译、源码身份、参数与指令数。
- [稳定预处理](evidence/stability-preprocessing.json)：剧情图片上限、15,901 个变更条目、7 文件更新范围与缓存参数。
- [整包尺寸审计](evidence/image-size-audit.json)：当前实际尺寸、原失败图片及 UI 例外。
- [无损纹理审计](evidence/lossless-textures.json)：历史高清包的调色板候选与包身份；RGB24/P8 原生规则继续沿用。
- [当前验证结果](evidence/current-validation.json)及[离线 shader 测试摘要](evidence/offline-shader-tests.txt)：本次构建与回归及未通过的配置范围。
- [稳定素材验证](evidence/stable-assets-validation.json)及[历史测试摘要](evidence/current-test-results.txt)：2026-11-02 素材、压力与全包验证。
- [R4 素材验证](evidence/r4-asset-verification.json)及[GXT 解码记录](evidence/r4-gxt-decode.txt)：沿用的画质阶段证据。
- [性能迁移验证摘要](evidence/performance-baseline.json)：固定到魔夜 `46fc688` 的原验证范围。
- [大文件诊断](evidence/large-file-diagnosis.json)及[ARM seek 反汇编](evidence/native-seek-arm.txt)：设备只读身份检查与 SDK 接口证据。

收据保留的是产生时的事实；其中旧 `.work` 路径对应的中间文件已清理，不承诺这些文件仍在。当前最终 VPK 在本地 `release/`，素材在本地 `dist/`。两者不提交到源码仓库。

标记原则：源码核对、宿主测试、ARM 构建、设备观察分别陈述。`hardware_verified:false` 不得因编译成功而改成 true。
