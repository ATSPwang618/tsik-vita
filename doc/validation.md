# 当前验证与交付身份

当前包为 `release/knife-vita-tsukihime-540p.vpk`，构建标识 **`tsukihime540-offline-shaders-20261106`**，5,385,822 字节，SHA-256：

```text
732a8b147b2d87c3139bffb99db2566745d99cba2bad200c46199fe9c3c9bba9
```

目标为 `armv7-sony-vita-newlibeabihf`，ELF32 ARM，TITLE ID `KNIF00541`、APP_VER `00.01`、ATTRIBUTE2=12。配套素材为 `story-rgba512k-axis960-v1`，清单 SHA-256 为 `0c4188c923f744870d660a384e0c55f59f1d3e3d8997e9baf6150a5eb7e0fc75`。上版 R4／无损存储包用户需要更新 VPK 和 7 个数据文件，详见[升级范围](assets.md#升级范围)。

## 2026-11-06 离线 shader 验证

109 个程序全部重复离线编译，生成字节一致，源码与生成头身份核验通过；63 个新增变体逐项静态指令数少于通用入口。实际 C 路由／回退测试 28 案例、6,287 检查通过，输入测试 877 案例、2,631 检查及 5 个负向 mutation 对照通过；Python 二进制／清单／指令检查 4 项通过。默认 assets-540p 渲染全套 127 项通过，稳定 feature 的 80 图压力用例单独通过，稳定预算／优化开关 3 项通过。

额外运行全套 `vita-stable` 配置得到 122 通过／5 失败：这 5 项原有测试要求前缀／分组／余量缓存按普通预算工作，与此前稳定配置主动关闭或缩减缓存的策略不一致。未修改这些无关测试或放宽产品预算，也未将该次运行计为全套通过。名称和范围保留于[当前验证收据](evidence/current-validation.json)。

ARMv7 安装包构建通过，332 个源码输入身份、20 个包成员 SHA／CRC、LiveArea 文件及 ELF32 ARM 已核对；最终 ELF 不含运行时编译函数，VPK 不含 `.suprx`。本次素材未修改，仅复核清单身份；下表是 2026-11-02 的素材验证记录，不能冒充本次重新扫描。shader 像素等价、设备驱动 patch 成功率、GPU 耗时与全路线演出尚未在实机验证。详细入口和 A/B 见[shader 文档](shaders.md)，输出摘要见[本次测试摘要](evidence/offline-shader-tests.txt)。

## 2026-11-02 稳定素材验证（沿用）

原始收据保留于[稳定素材验证](evidence/stable-assets-validation.json)。

| 检查 | 新运行的结果 |
| --- | --- |
| 预处理扫描 | 23,177 个剧情图片条目，15,901 个超限项已缩小；复扫 0 超限；语言选择后含行距 RGBA 和新页均 ≤512 KiB |
| 全包完整性 | 16,764 个文件 hash 一致，2,427,075,112 字节（不含清单）；未生成重复素材树 |
| 实际解码 | 正式 C PNG/JPEG／语言选择 813 次；23,113 张 GXT 的正式头解析与 CPU 解码通过，含 `parts` |
| 运行时最大值 | 剧情 RGBA 新页最多 524,288 字节；受保护 UI 全包最大新页 4,194,304 字节；两者范围不同 |
| 原失败点图片 | 逻辑 2591×2582 保留，物理 1020×1016 → 360×359；RGBA 新页 4 MiB → 512 KiB，直接 GXT 新页 256 KiB |
| 预处理测试 | 稳定上限、alpha、双语分段、合格项不转码、alias、断点配套恢复与幂等性；合并 Python 素材测试 23 项通过 |
| 稳定缓存策略 | `vita-stable` 下内存／性能模块 3 项通过；文字／分组各 4 MiB、可选 spare／前缀为 0、压力余量 16 MiB |
| 渲染与重载 | 127 项通过，含 3,606 种实际物理尺寸的初次上传与回收后重载、池化开／关、P8／RGB24、物理分配故障处理 |
| 最近文字缓存生命周期 | 归还缓存所有权后，已记录纹理仍存活至提交／完成，随后销毁；下次绘制回退到字形路径 |
| 旧新图片压力 | 48 MiB 宿主纹理预算，80 张各 512 KiB RGBA＋两个 960×540 必需目标＋2 MiB UI 同驻留并提交，池化开／关均通过；另在稳定 feature 下运行通过 |
| 原生 C 真代码 | 预留 12 案例／154 检查、RGB24/P8 39／587、压缩上传 87／1104；ASan／UBSan；外部 SDK 调用为 doubles，不执行 GPU |
| UI 保留 | 24 图集、438 成员、236 GXT 解码、日中标题／菜单 60 状态区有可见 alpha；索引除清单 hash 外与上版逐字节一致 |
| 双语与平台 | 月姬／日志 helper 69 项、平台 68 项通过，包含实际字体、CG 缩略图与 8 秒开场 |
| 配套构建 | ARMv7 构建通过，328 个源码输入 hash、21 个 VPK 成员 CRC／SHA 以及 5 个 LiveArea 文件逐一匹配；profile／atlas／stream 清单身份一致 |
| 实际启动文件检查 | 107 个关键文件通过，共读取 13,168,938 字节；为宿主文件系统检查，不是设备启动 |

80 图压力夹具只验证指定 owner 集合和分配边界，不能证明所有脚本演出的设备峰值。P8 候选以实际像素重新计色，不能把候选统计当作同时节省的显存。

## 沿用的历史修复与证据

- 旧实机日志 scene=1／pc=5309 报 `0x80024309`（CDRAM 物理页不足），不能只看附近的空闲总字节推断某次分配成功，也不能仅凭日志证明具体碎片分布。真实存储预留、有界 LRU 与帧 pin 的修复保留；见[诊断](evidence/cdram-diagnosis.json)。
- 上版 R4 图集曾因旧轴限制拒绝 15 个成员、影响 9 图集。当前保留宽长 GXT 边界修复，未统一压低 UI。历史 R4 数据见[r4-asset-verification.json](evidence/r4-asset-verification.json)和[r4-gxt-decode.txt](evidence/r4-gxt-decode.txt)。
- 无损上传优化的完整 RGBA 调色板、RGB24、页预留转移与回滚继续使用；[lossless-textures.json](evidence/lossless-textures.json)记录的是上一套高清素材和旧包身份，本次素材已主动有损降采样。
- 大文件阶段核心 51、平台 68、渲染 112、helper 66 等历史结果及 32 位 seek 反例保留于[测试摘要](evidence/current-test-results.txt)；ARM 仍是 32 位，SDK 文件位置为 64 位。见[大文件诊断](evidence/large-file-diagnosis.json)和[ARM seek](evidence/native-seek-arm.txt)。
- 固定魔夜 `46fc688` 的迁移验证见[性能摘要](evidence/performance-baseline.json)。历史数字不冒充本轮重跑。

## 复现入口

以下在 Linux／WSL 根目录运行，需要对应固定工具链与宿主依赖。验证顺序为源清单／配套索引、正式解码、实际尺寸渲染回归、ARM 打包；不需要复制整个素材树。

```sh
python3 -B -m unittest discover -s tools -p 'test_tsukihime_*.py'
cargo +1.99.0 test --offline --locked --manifest-path knife/Cargo.toml -p knife-perf --features vita-stable --lib
bash tools/test-vita-reservation.sh
bash tools/test-vita-lossless.sh
bash tools/test-vita-compressed.sh
# 先从 image_decode.c / jpeg_hw.c / perf_audit.c 构建宿主 decoder.so。
python3 -B tools/verify-tsukihime-runtime-assets.py dist/TSUKIHIME-RE/assets --decoder .work/stability/decoder.so --report .work/stability/image-size-audit.json --layouts .work/stability/layouts.tsv
KNIFE_IMAGE_LAYOUTS="$PWD/.work/stability/layouts.tsv" cargo +1.99.0 test --release --offline --locked --manifest-path knife/Cargo.toml -p knife-render --features assets-540p --lib -- --test-threads=1
cargo +1.99.0 test --release --offline --locked --manifest-path knife/Cargo.toml -p knife-render --features assets-540p,knife-perf/vita-stable --lib stable_pack_eighty -- --test-threads=1
cargo +1.99.0 run --release --offline --locked --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml --example audit_lossless_textures -- dist/TSUKIHIME-RE/assets
cargo +1.99.0 run --offline --locked --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml --example verify_ui_atlases -- dist/TSUKIHIME-RE/assets
cargo +1.99.0 test --offline --locked --manifest-path knife/Cargo.toml -p knife-platform-vita --features tsukihime --lib -- --test-threads=1
KNIFE_GALLERY_ASSETS="$PWD/dist/TSUKIHIME-RE/assets" KNIFE_STARTUP_ASSETS="$PWD/dist/TSUKIHIME-RE/assets" cargo +1.99.0 test --offline --locked --manifest-path tools/probes/tsukihime-bilingual/Cargo.toml --features tsukihime
python3 tools/generate_vita_asset_profile_tsukihime_540.py --check
python3 tools/generate-vita-atlas-index.py dist/TSUKIHIME-RE/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs --archive w_allui --check
python3 tools/check-vita-package.py release/knife-vita-tsukihime-540p.vpk KNIF00541 --release
```

## 设备验证边界

本版未实际操作 Vita，未标记已跨过用户失败点，也未宣称全路线、所有 UI／影片或长时间稳定性验收通过。全部新结果为离线测试和 ARM 包检查；`runtime_verified`／`hardware_verified` 保持 false。降低像素占用和收紧缓存是风险控制，不能消除任意驱动错误、其他 owner 峰值或未来未验证的演出组合。

完整桌面游戏测试此前受缺少 GStreamer 开发库限制，共享性能分析入口也有[未提供的依赖](performance.md#采样与验证限制)，均未计为通过。原始 NSP 转换还需要匹配输入与本机工具。

本次事实保留于[构建收据](evidence/current-build.json)、[当前验证](evidence/current-validation.json)、[预处理报告](evidence/stability-preprocessing.json)、[整包尺寸](evidence/image-size-audit.json)和[测试摘要](evidence/current-test-results.txt)。收据中的旧 `.work` artifact 路径用于身份追溯，临时文件会按磁盘约定清理。
