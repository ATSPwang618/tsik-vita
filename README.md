# tsik-vita · 月姬 PS Vita 移植版

《月姬 -A piece of blue glass moon-》的 **PlayStation Vita** 引擎移植，基于 [AuroraWright/knife](https://github.com/AuroraWright/knife) 0.9.4，以 [mofa-vita](https://github.com/ATSPwang618/mofa-vita) 的实机工程为参考。使用 Rust 游戏逻辑和原生 GXM 后端，场景／合成画布为 **960×540**，输出到 **960×544** 屏幕。

**当前交付：2026-11-06，全部离线 shader 与像素运算精简版。** 内嵌 109 个 GXM 程序，覆盖全部引擎特效入口及混合组合；新增 63 个按绘制条件选择的专用变体，减少无用波纹／裁剪、文字、模糊和混合模式分支。无需启动时编译，也不需要 shader 编译器模块。沿用 2026-11-02 的稳定素材、512 KiB 剧情 RGBA 上限与缓存回收策略，本次未修改素材清晰度。程序仍为 **ARMv7 32 位**；已有稳定素材只需更新 VPK。编译与宿主验证不代表实机 GPU 加速幅度或全路线稳定性，详见[shader 说明](doc/shaders.md)。

## 项目截图

以下为玩家提供的 PS Vita 实机截图，拍摄于 2026-10-31；监控叠层中的帧率只代表对应场景。

| 主界面气泡 | LiveArea |
| --- | --- |
| ![主界面气泡](项目截图/2026-10-31-203113.jpg) | ![LiveArea](项目截图/2026-10-31-203123.jpg) |

| 标题画面 | 简体中文剧情 |
| --- | --- |
| ![游戏标题](项目截图/2026-10-31-203203.jpg) | ![中文剧情](项目截图/2026-10-31-203307.jpg) |

## 当前特性

- **双语言**：仅保留简体中文／日本語，新配置默认简体中文，选择后保存；原始语言 ID 为 2／0。
- **统一字体**：日中剧情、动态界面与回看共用 `arshanghaisonggbpro_lt.otf`，保留补充字形及特殊符号。图片内文字随对应语言美术资源显示。
- **剧情与鉴赏**：剧情推进、选项、设置、存读档、快速存读档、自动播放、快进、回看，以及 CG／Music／Flowchart／Movie／Ending List 实现；鉴赏内容依进度解锁。
- **Vita 适配**：实体按键、双摇杆、前触摸、原生音频与影片；**A→○、B→×**。
- **画质与稳定性**：保留 R4 的 UI 与 CG 缩略图分页，两语言共 3960 格保持原 ID；剧情大图按显存边界降采样，明确牺牲细节以降低峰值，逻辑坐标与图片比例保留。
- **无损纹理存储**：全 RGBA 色数不超过 256 且能节省显存页时使用 P8，透明与半透明均保留；高色数不透明调色图片用 RGB24，其余保留 RGBA8。原生压缩 GXT 沿用直接上传。
- **性能调度**：渲染输出复用、分段文字缓存、异步图片／音效准备、影片持续服务线程与有界缓存；本版关闭可选 stage／canvas spare 和静态前缀目标，文字／分组缓存各限 4 MiB，实际效果需设备采样。
- **离线 shader**：全部 GXP 内嵌，专用变体按状态准入并保留原路径回退；支持 `all -shader-specialization` 实机 A/B。
- **统一目录**：素材、存档、配置和错误记录集中在 `ux0:data/TSUKIHIME-RE/`，旧 shader cache 不再使用。
- **实时日志**：后台队列输出启动、UI 图集、警告／错误和每 5 秒性能窗口，兼容魔夜使用的 VitaDeck/CatLog 接收方式；不持续写入游戏日志文件。

## 安装与更新

1. 完全退出游戏，用 VitaShell 安装 `release/knife-vita-tsukihime-540p.vpk`。
2. 首次安装时，将本地 `dist/TSUKIHIME-RE/assets/` 整体传到 `ux0:data/TSUKIHIME-RE/assets/`，避免多套一层目录。
3. 启动游戏；默认简体中文，需要日文时在设置中切换。



```text
ux0:data/TSUKIHIME-RE/
├── assets/                 # 完整配套素材
├── saves/                  # 存档、配置及进度
└── resource-error.json     # 资源失败时生成
```

当前素材针对 **Switch 海外版合并 v1.0.1**，程序 build ID 为 `d10d239aade1d526`。。


## 操作

| Vita 输入 | 常用操作 |
| --- | --- |
| ○| 确认、推进；消息隐藏时先恢复消息窗 |
| × | 取消／返回；剧情中先停止快进，否则切换消息窗 |
| □ | 打开／关闭回看 |
| △ | 打开／关闭系统菜单 |
| L／R | 剧情自动播放／快进；菜单按当前页面切换项目 |
| 方向键／右摇杆 | 菜单导航；剧情方向键 ↑ 打开模式面板 |
| 左摇杆 | 列表、CG、流程图滚动等；中心 ±16 死区 |
| 前触摸 | 点击、拖动；剧情顶部可打开模式面板 |
| START | 影片鉴赏播放时跳过影片 |
| SELECT | CG 查看切换为保持比例的铺满显示 |

快速存读档使用剧情模式面板的 **Q.SAVE／Q.LOAD**，或系统菜单；操作受剧情存档许可与已有快存状态限制。

## VitaDeck 日志

与魔夜使用相同的 CatLog 插件和 VitaDeck「日志」接收端。FTP（本机配置为 `1337`）用于传文件，实时日志走独立通道（本机配置为 `8080`）；只有 FTP 连通不代表日志接收已经开启。先在 VitaDeck 开启日志接收，再启动月姬。若用 VitaDeck 启动应用，TITLE ID 填 **`KNIF00541`**，不要沿用魔夜的 `KNIF00540`。

本包默认打开日志；`perf-enable.txt` 为 `0` 会关闭性能采样，为 `1` 则开启，位置为 `ux0:data/TSUKIHIME-RE/`，重启生效。启动／UI／警告等普通日志独立于性能开关。完整开关、队列边界和排错见[性能与日志](doc/performance.md#vitadeck-实时日志)。

## 当前包识别

| 项目 | 当前值 |
| --- | --- |
| 本地安装包 | `release/knife-vita-tsukihime-540p.vpk` |
| 大小 | 5,385,822 字节，约 5.14 MiB |
| 构建标识 | `tsukihime540-offline-shaders-20261106` |
| 目标 | `armv7-sony-vita-newlibeabihf`，ELF32 ARM |
| TITLE ID／APP_VER | `KNIF00541`／`00.01` |
| 素材 | 16,764 个数据文件＋清单，共约 2.26 GiB |
| 素材 schema／method | `knife-540p-assets-v1`／`native-540p-encoded-unorm-v2` |
| 色彩／codec | `encoded-unorm8-v1`／1、2、7、9 |

VPK SHA-256：

```text
732a8b147b2d87c3139bffb99db2566745d99cba2bad200c46199fe9c3c9bba9
```

`assets/vita-540p-assets.json` SHA-256：

```text
0c4188c923f744870d660a384e0c55f59f1d3e3d8997e9baf6150a5eb7e0fc75
```

当前包与素材身份以本节和[构建收据](doc/evidence/current-build.json)为准。不要通过手改清单绕过校验。

## 开发与文档

从仓库根目录执行：

```sh
python3 tools/build-vita.py --check
python3 tools/build-vita.py --variant tsukihime540 game release
python3 tools/check-vita-package.py release/knife-vita-tsukihime-540p.vpk KNIF00541 --release
```

Windows 可用 `py -3` 替代 `python3`，或运行 `tools/build-vita.ps1 -Variant tsukihime540`。构建环境、原生依赖及本地模块的准备见[构建说明](doc/build.md)，不要将桌面构建入口当作 Vita 打包入口。

| 文档 | 内容 |
| --- | --- |
| [技术文档总览](doc/README.md) | 当前文档入口 |
| [架构](doc/architecture.md) | 工作区、线程、数据流与坐标契约 |
| [构建](doc/build.md) | 工具链、命令、产物与依赖 |
| [素材](doc/assets.md) | 双语言、画质、格式、升级与重建边界 |
| [性能](doc/performance.md) | 魔夜优化迁移、缓存上限与采样 |
| [验证](doc/validation.md) | 当前测试、收据与未验证范围 |
| [排错](doc/troubleshooting.md) | 大文件报错、画质、字体和设备日志 |
| [仓库维护](doc/maintenance.md) | 目录职责、磁盘清理及保留规则 |
| [工具索引](tools/README.md) | 当前常用工具与兼容工具的用途 |

本地只保留一套 `dist` 素材和一个最终 VPK；`.work`、Rust target 与 Python 缓存可重建。执行 `python3 tools/clean-project.py` 预览，增加 `--apply` 清理。原始 NSP、解包中间数据及工具链应放在仓库外，旧转换尝试不长期保留。

## 验证状态

本次渲染 **127 项**、平台 68 项、月姬／日志 helper 69 项、Python 素材 23 项、稳定内存策略 3 项通过；另有 80 张旧新 RGBA 图片与必需目标同驻留的 48 MiB 压力夹具通过。完整素材 16,764 个文件 hash、813 次正式 PNG／语言分片解码、23,113 张 GXT 解码以及 3,606 种实际尺寸的上传／重载检查通过。ARM 构建、328 个源码输入与 VPK 21 个成员核验通过。

当前包尚待实机启动、后半段剧情／CG、影片与长时间稳定性复测。已有实机截图与参考项目数据不等于本版全内容验收；详情见[验证记录](doc/validation.md)。

## 致谢与许可证

感谢 **@Zarathustra、@lisen** 对本项目的长期付出，感谢参考项目 mofa-vita、上游 knife，以及提供实机测试、问题截图和反馈的玩家。

引擎沿用 [MPL 2.0](knife/LICENSE)，来源见 [UPSTREAM.txt](knife/UPSTREAM.txt)。原生依赖许可证保留在 `knife/vita/vendor/`。游戏本体、美术、音视频、字体和汉化资源归各自权利人所有，由使用者自行准备。
