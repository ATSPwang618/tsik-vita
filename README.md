# tsik-vita · 月姬 PS Vita 移植版

**简体中文** | [English](README.en.md)

将《月姬 -A piece of blue glass moon-》移植到 **PlayStation Vita / PS TV**。基于 [AuroraWright/knife](https://github.com/AuroraWright/knife) 0.9.4，参考 [mofa-vita](https://github.com/ATSPwang618/mofa-vita) 的 Vita 工程；使用 Rust 游戏逻辑与原生 GXM 渲染，目标为 **ARMv7 32 位**。

场景与合成画布为 **960×540**，输出到 **960×544**。当前交付使用稳定素材与完整离线 shader：**默认开启已实现优化，无需创建任何 TXT 开关文件**。部分优化还受显存预算、绘制条件和驱动能力约束。

> 源码仓库不包含游戏数据、字体原件或 VPK。请使用自行合法取得、与本项目配套的素材。当前 ARM 构建和有界宿主测试已通过；尚无本版全路线实机验收或 GPU 性能提升测量。

## 项目截图

玩家提供的 PS Vita 实机截图，拍摄于 2026-10-31。截图早于当前离线 shader 版；叠层帧率仅代表拍摄时的场景。

| 主界面气泡 | LiveArea |
| --- | --- |
| ![主界面气泡](项目截图/2026-10-31-203113.jpg) | ![LiveArea](项目截图/2026-10-31-203123.jpg) |

| 标题画面 | 简体中文剧情 |
| --- | --- |
| ![标题画面](项目截图/2026-10-31-203203.jpg) | ![简体中文剧情](项目截图/2026-10-31-203307.jpg) |

## 主要特性

- **日中双语**：仅简体中文与日本語，新配置默认简体中文，保留原语言 ID 2 / 0；动态文字共用指定字体及补充字形。
- **游戏功能**：剧情、选项、设置、存读档、快存快读、自动播放、快进、回看，以及 CG / Music / Flowchart / Movie / Ending List；鉴赏内容依进度解锁。
- **Vita 操作**：实体按键、双摇杆、前触摸、原生音频和影片；A 对应 ○，B 对应 ×。
- **致谢开场**：先显示正确的 @Zarathustra / @lisen 致谢图，淡入、停留、淡出合计约 8 秒。
- **独立数据目录**：素材、存档、配置和资源错误记录集中在 `ux0:data/TSUKIHIME-RE/`；支持 VitaDeck / CatLog 实时控制台输出。

## 已落地的优化

| 方向 | 当前实现 |
| --- | --- |
| 离线特效 | 109 个内嵌 GXM 程序，包含 63 个按绘制状态选择的专用变体；无需运行时 shader 编译器或缓存文件 |
| 像素运算 | 精简无波纹图片、文字、模糊及 24 种混合模式的不必要分支，保留原程序回退 |
| 剧情显存 | 提前处理全部剧情图片：23,177 条扫描，15,901 条降采样；单图最坏 RGBA 行距占用不超过 512 KiB |
| 无损存储 | 合适的不可变 RGBA 图片使用精确 P8 调色板或 RGB24；包含透明及半透明；原生 GXT 保留压缩上传 |
| 缓存与调度 | 渲染输出复用、分段文字缓存、异步整组换图、音效准备、影片 owner 线程和有界资源缓存 |
| 稳定预算 | 文字 / 分组缓存各 4 MiB；可选目标轮换与静态前缀预算为 0；换图前释放可选缓存所有权 |
| UI 与读取 | 修复宽长图集拒绝、音乐字体、CG 加载与分页缩略图；SDK 大文件读取修复保持 ARM32 |

**剧情大图降采样有画质损失。** UI、字体和分页 CG 缩略图不随剧情图统一缩小。P8 / RGB24 上传本身保持输入像素，不代表整套素材无损。完整 29 项开关、适用范围和证据见[优化总表](doc/optimizations.md)。

## 安装

1. 完全退出游戏，使用 VitaShell 安装本地 `release/knife-vita-tsukihime-540p.vpk`。
2. 将配套的 `dist/TSUKIHIME-RE/assets/` 整体复制到 `ux0:data/TSUKIHIME-RE/assets/`，不要多套一层目录。
3. 启动游戏。默认简体中文，需要日文时在设置切换并保存。

~~~text
ux0:data/TSUKIHIME-RE/
├── assets/                 # 配套素材
├── saves/                  # 存档、配置与进度
└── resource-error.json     # 资源加载失败时生成
~~~

素材对应 **Switch 海外版 base + update v1.0.1**，源程序 build ID 为 `d10d239aade1d526`。原始 NSP / romfs 不能直接替代转换后的素材。正常游玩不需要创建优化或日志开关文件。版本配套与开发者转换约定见[素材手册](doc/assets.md)。

## 按键

| Vita 输入 | 常用操作 |
| --- | --- |
| ○ / A | 确认、推进；消息隐藏时先恢复消息窗 |
| × / B | 取消、返回；剧情中先停止快进，否则切换消息窗 |
| □ / X | 打开或关闭回看 |
| △ / Y | 打开或关闭系统菜单 |
| L / R | 剧情自动播放 / 快进；菜单按页面切换项目 |
| 方向键 / 右摇杆 | 菜单导航；剧情方向键 ↑ 打开模式面板 |
| 左摇杆 | 列表、CG、流程图滚动；中心 ±16 死区 |
| 前触摸 | 点击、拖动；剧情顶部可打开模式面板 |
| START | 影片鉴赏中跳过影片 |
| SELECT | CG 查看切换为保持比例的铺满显示，会裁掉部分边缘 |

快存快读使用剧情模式面板的 **Q.SAVE / Q.LOAD** 或系统菜单，并受剧情存档许可及已有快存状态限制。

## 日志与排错

当前包默认输出控制台日志。先在 VitaDeck 开启日志接收，再启动游戏；CatLog 配置可沿用已正常工作的魔夜环境。FTP 负责传文件，与实时日志是独立通道。通过 VitaDeck 启动时使用 **TITLE ID `KNIF00541`**。

报错时保留具体文件名、剧情位置、语言、截图与资源错误记录。不要通过删除检查或手改清单绕过版本校验。参见[排错手册](doc/troubleshooting.md)和[日志与预算](doc/performance.md)。

## 当前交付与验证

| 项目 | 当前值 |
| --- | --- |
| 构建标识 | `tsukihime540-offline-shaders-20261106` |
| VPK | 5,385,822 字节，约 5.14 MiB |
| TITLE ID / APP_VER | `KNIF00541` / `00.01` |
| 架构 | `armv7-sony-vita-newlibeabihf`，ELF32 ARM |
| 素材 | 16,764 个数据文件及清单，约 2.26 GiB |
| 最新 shader 回归 | Python 4 项；原生路由 28 案例 / 6,287 检查；输入校验 877 案例 / 2,631 检查 |
| 渲染验证边界 | 默认配置 127 项通过；稳定配置压力夹具通过；稳定配置全套仍有 5 项预算假设不匹配，未标为全通过 |

当前包、素材 hash、分阶段测试和待完成的实机验证集中维护在[验证记录](doc/validation.md)。2026-11-06 仓库整理不改变游戏程序或素材，也没有重新打包或发布 Release。

## 开发与文档

从仓库根目录执行：

~~~sh
python3 tools/build-vita.py --check
python3 tools/build-vita.py --variant tsukihime540 game release
python3 tools/check-vita-package.py release/knife-vita-tsukihime-540p.vpk KNIF00541 --release
~~~

Windows 可用 `py -3`，或运行 `tools/build-vita.ps1 -Variant tsukihime540`。环境、离线模式及源码生成文件见[构建手册](doc/build.md)。

| 文档 | 内容 |
| --- | --- |
| [技术文档导航](doc/README.md) | 按安装、开发、排错和维护查找 |
| [优化总表](doc/optimizations.md) | 全部 29 项开关及历次专项优化、修复与限制 |
| [架构](doc/architecture.md) · [素材](doc/assets.md) | 资源、坐标、线程、双语言与转换契约 |
| [性能与内存](doc/performance.md) · [Shader](doc/shaders.md) | 默认行为、预算、离线程序与开发者 A/B |
| [验证](doc/validation.md) · [排错](doc/troubleshooting.md) | 可复现证据与实机待验收项 |
| [仓库维护](doc/maintenance.md) · [工具索引](tools/README.md) | 目录职责、清理范围及工具依赖 |

本地仅保留一套 `dist/` 素材和最终 VPK。使用 `python3 tools/clean-project.py` 预览缓存清理，确认输出后增加 `--apply` 执行。默认仅修改本地；只有用户明确要求推送时才写远端。

## 致谢与许可证

感谢 **@Zarathustra、@lisen** 长期付出，感谢 **AuroraWright / knife**、**mofa-vita**，以及提供实机测试、截图和反馈的玩家。

引擎沿用 [MPL 2.0](knife/LICENSE)，源码来源见 [UPSTREAM.txt](knife/UPSTREAM.txt)。第三方原生依赖的许可证保留在 `knife/vita/vendor/`。游戏、美术、音视频、字体与汉化资源归各自权利人所有。
