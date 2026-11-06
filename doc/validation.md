# 交付身份与验证

[文档导航](README.md) · [证据索引](evidence/README.md) · [优化总表](optimizations.md)

本页把当前产物、历史素材验证、本轮仓库维护检查与实机缺口分开。构建收据保留生成时事实；其中旧分支、远端和临时目录字段不是当前仓库状态。

## 当前本地 VPK

| 项目 | 值 |
| --- | --- |
| 路径 | `release/knife-vita-tsukihime-540p.vpk` |
| build tag | `tsukihime540-offline-shaders-20261106` |
| 大小 | 5,385,822 字节 |
| TITLE ID / APP_VER / ATTRIBUTE2 | KNIF00541 / 00.01 / 12 |
| 目标 | `armv7-sony-vita-newlibeabihf`，ELF32 ARM |
| 程序 | 109 个内嵌离线 GXM 程序，其中 63 个新增专用变体 |
| 包成员 | 20 个引擎成员，不含游戏数据或运行时 compiler module |

~~~text
VPK SHA-256:
732a8b147b2d87c3139bffb99db2566745d99cba2bad200c46199fe9c3c9bba9
eboot SHA-256:
aace269b6f74ec345345e6c9477c829bf3559cd0562518f22f5be8f522a5103b
assets/vita-540p-assets.json SHA-256:
0c4188c923f744870d660a384e0c55f59f1d3e3d8997e9baf6150a5eb7e0fc75
~~~

[构建收据](evidence/current-build.json)记录当时 332 个源码 / 工具输入、包成员和编译参数。[当前验证摘要](evidence/current-validation.json)记录对应检查。不能用旧稳定包的 328 个输入 / 21 个成员描述这个离线 shader 包。

## 2026-11-06 离线 shader 阶段

| 验证项 | 已记录结果 |
| --- | --- |
| 清单、二进制结构、输入 hash、指令缩减 | Python 4 项通过；109 个程序各编译两次字节一致 |
| 原生 C 拷贝 / shader 路由 | 28 案例、6,287 检查通过，ASan / UBSan |
| 原生特效输入 | 877 案例、2,631 检查通过；5 个预期失败的负向突变被正确识别 |
| renderer 默认 assets-540p | 127 项通过 |
| stable 80 层压力专项 | 1 项通过 |
| stable 内存 / profile 模块 | 3 项通过 |
| ARM / 打包 | ELF32 ARM、332 输入 hash、20 成员 SHA / CRC、5 个 LiveArea 文件核对通过；无运行时 compiler 符号 |

证据：[测试摘要](evidence/offline-shader-tests.txt)、[shader 清单](evidence/offline-shaders.json)。以上为该阶段结果，本次文档重写不冒充重新运行过所有原生 / Rust 测试。

**未通过配置必须保留：** renderer 全套使用 `assets-540p,knife-perf/vita-stable` 时为 **122 通过 / 5 失败**。失败测试假定旧的静态前缀 / 分组 / spare 缓存预算；稳定配置关闭或缩小这些预算。默认配置通过、压力专项通过，不能代替稳定配置全套通过。名称和原因见[摘要的 nonpassing_configuration](evidence/current-validation.json)。本次仓库整理未修改这些测试或运行时预算。

## 2026-11-02 稳定素材阶段

| 验证项 | 已记录结果 |
| --- | --- |
| 整包身份 | 16,764 个数据文件完整 hash；清单与生成索引一致 |
| 剧情上限 | 23,177 条扫描、15,901 条降采样、复扫 0 超限 |
| 正式解码 | 813 次 PNG / 语言分片解码，23,113 张 GXT 解码 |
| 实际尺寸 | 3,606 种物理布局的上传与回收后重载；包含池化开 / 关与 P8 / RGB24 |
| UI | 24 图集 / 438 成员、236 GXT 解码、日中标题 / 菜单 60 状态区可见 alpha |
| 48 MiB 宿主压力 | 80 张各 512 KiB 的旧新 RGBA、两个 960×540 必需目标、2 MiB UI 同驻留并提交 |
| 平台 / helper / 素材 | 平台 68、月姬 / 日志 helper 69、Python 素材 23 项通过 |
| 原生存储 | 预留 12 案例 / 154 检查；P8 / RGB24 39 / 587；压缩上传 87 / 1,104；ASan / UBSan，SDK doubles |
| 启动检查 | 107 个关键文件，共读取 13,168,938 字节；宿主文件系统检查 |

证据：[稳定素材验证](evidence/stable-assets-validation.json)、[预处理](evidence/stability-preprocessing.json)、[尺寸审计](evidence/image-size-audit.json)。历史无损候选不能当作当前同时驻留的显存节省；其他历史阶段见[证据索引](evidence/README.md)。

## 本次仓库整理的检查

本轮不修改游戏运行时代码、shader 生成字节或 dist 素材，未重新打包。维护脚本及文档重写的实际检查、删除清单、当前输入差异和产物身份记录在[仓库整理收据](evidence/repository-maintenance-20261106.json)。

离线转换工具 `migrate-vita-native-color.py` 删除了两个无调用 helper，因此与旧构建收据的该工具 hash 不同；旧收据保持原样。它不参与运行时执行，现有 VPK 和素材清单 hash 保持不变。无需为文档和维护清理重新构建一个同内容 VPK。

## 复现入口

从仓库根执行，输出写入 `.work/`；不复制整个 dist。

~~~sh
python3 -B -m unittest discover -s tools -p 'test_clean_project.py'
python3 -B -m unittest discover -s tools -p 'test_offline_shaders.py'
python3 -B -m unittest discover -s tools -p 'test_tsukihime_*.py'
python3 tools/compile-vita-offline-shaders.py --check
python3 tools/generate_vita_asset_profile_tsukihime_540.py --check
python3 tools/generate-vita-atlas-index.py dist/TSUKIHIME-RE/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs --archive w_allui --check
python3 tools/check-vita-package.py release/knife-vita-tsukihime-540p.vpk KNIF00541 --release
~~~

Linux / WSL 原生与 Rust 测试（需对应工具链和 SDK）：

~~~sh
bash tools/test-vita-reservation.sh
bash tools/test-vita-lossless.sh
bash tools/test-vita-compressed.sh
bash tools/test-vita-gxm-copy.sh
bash tools/test-vita-effects-inputs.sh
cargo +1.99.0 test --offline --locked --manifest-path knife/Cargo.toml -p knife-perf --features vita-stable --lib
cargo +1.99.0 test --release --offline --locked --manifest-path knife/Cargo.toml -p knife-render --features assets-540p --lib -- --test-threads=1
cargo +1.99.0 test --release --offline --locked --manifest-path knife/Cargo.toml -p knife-render --features assets-540p,knife-perf/vita-stable --lib stable_pack_eighty -- --test-threads=1
~~~

全素材解码需先由正式 C decoder 源码构建宿主库，再运行 `verify-tsukihime-runtime-assets.py --decoder ... --report .work/... --layouts .work/...`；布局 TSV 用 `KNIFE_IMAGE_LAYOUTS` 交给 renderer。真实双语 / 图集探针说明见 [tools/probes/tsukihime-bilingual](../tools/probes/tsukihime-bilingual/README.md)。涉及全局优化 mask 的渲染测试使用单线程。

## 实机待验收

- 当前包启动、两种语言、title / 菜单 / 各鉴赏页面与实际日志接收。
- 用户失败点 scene=1、pc=5309，后半段剧情 / CG、影片和长时间运行。
- 代表性特效的 GPU 像素读回与 shader A/B GPU 时间、功耗、实际内存峰值。
- 稳定 feature 全套测试的预算假设修正与重跑。

`hardware_verified`、`gpu_timing_verified`、`gpu_pixel_equivalence_verified` 仍为 false。SDK doubles 不执行 GPU；本地检查不能证明全流程通关或永久零分配失败。完整桌面游戏验证还受 GStreamer 依赖限制，不能拿共享宿主测试代替。
