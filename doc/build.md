# 构建与交付

[文档导航](README.md) · [工具索引](../tools/README.md) · [当前包身份](validation.md)

## 所需环境

| 用途 | 依赖 |
| --- | --- |
| 构建 / 配套验证工具 | Python 3.11+（本机 3.13）、CMake 3.20+、Ninja、Bash、Git、VitaSDK |
| Vita Rust | `nightly-2026-05-28` + rust-src，目标 `armv7-sony-vita-newlibeabihf` |
| 宿主 Rust | `knife/rust-toolchain.toml` 指定 Rust 1.99.0 |
| 素材转换 / Python 素材测试 | Pillow、NumPy；部分字体处理需要 fonttools，媒体需要 ffmpeg，GXT 需相应工具 |
| 重编 shader | 自行提供本地 psp2cgc；仅校验现有生成文件不需要编译器 |

本机曾验证 WSL `pocket-ubuntu`、VitaSDK `/opt/vitasdk`、GCC 15.2.0；这是记录路径，不要求其他机器采用同一路径。Windows 入口可调用 WSL，Linux / macOS 使用对应本地环境。

`knife/vita/vendor/` 内的头文件、静态库、来源和许可证是构建输入。生成 shader 头、startup profile、atlas / stream 索引也是构建输入，不能当缓存删除。仓库不提供编译器、Sony 运行时模块、密钥或商业游戏数据。

## 常用命令

从仓库根执行：

~~~sh
python3 tools/build-vita.py --check
# 需要已备齐依赖；禁止构建入口自动下载
KNIFE_VITA_OFFLINE=1 python3 tools/build-vita.py --variant tsukihime540 game release
python3 tools/check-vita-package.py release/knife-vita-tsukihime-540p.vpk KNIF00541 --release
~~~

Windows：

~~~powershell
./tools/build-vita.ps1 -Check
./tools/build-vita.ps1 -Variant tsukihime540 -Mode game -BuildKind release
~~~

`--check` 只探测环境。常规构建可安装缺失的固定 Rust 工具链，`KNIFE_VITA_OFFLINE=1` 禁止自动下载。`VITASDK` / `--sdk` 选择 SDK，Windows `--wsl` 选择发行版，`KNIFE_VITA_CACHE` 指定构建缓存。

正式 feature 为 `vita-gxm,assets-540p,tsukihime`，TITLE ID `KNIF00541`，ATTRIBUTE2=12。月姬 feature 引入稳定预算。程序是 ELF32 ARM；SDK 的 64 位文件位置不改变 CPU 架构。

## Shader 与生成文件

普通月姬 VPK 构建直接使用内嵌的 109 个 GXP，不需要 `libshacccg.suprx`。CMake 会验证生成文件与输入身份。修改 Cg 后使用唯一入口 `compile-vita-offline-shaders.py`；修改共享运行时源码时同步 `generate-runtime-shaders.py`。完整命令与回归见[Shader 手册](shaders.md)。

旧的两个部分 PowerShell shader 生成器已经移除，避免覆盖完整清单。非月姬 variant 仍保留自己的 runtime shader 路径，不因本项目默认离线化而删去公共后端。

## 打包默认与产物

- 最终产物：`release/knife-vita-tsukihime-540p.vpk`；release 仅保留最终 VPK。
- 构建中间目录：`.work/vita/game-release-tsukihime-540p/`，包含日志、ELF、map、SELF、临时 VPK 和收据；Rust cache 可在外部。
- 当前交付 tag：`tsukihime540-offline-shaders-20261106`，通过 `KNIFE_BUILD_TAG` 指定；不要把同一 tag 当作任何修改后产物的证明。
- 默认后台控制台开启，`KNIFE_VITA_QUIET=0`、`KNIFE_PERF_CONSOLE=1`；无 DEV 逐帧文件日志与运行帧数上限。普通玩家不需要开关 TXT。
- 只构建 VPK 不需要复制 dist 或重新解包游戏。素材实际变化才需要重新生成配套索引。

## 交付核验

核对 ELF 架构、包 TITLE / SFO、ZIP 成员 SHA / CRC、当前 LiveArea、输入清单，以及素材 profile / atlas / stream 的一致性。当前已验证产物身份集中在[验证手册](validation.md)。

2026-11-06 本次整理只调整文档与维护 / 离线转换工具，运行时代码、shader 字节、LiveArea 和素材未改，保留现有 VPK。构建收据是产生时的不可变事实，维护工具的后续清理不能通过改写旧收据冒充重新构建。

## 桌面、探针与清理

`build-windows.sh`、`build-compact.*`、`build-540p.ps1` 保留桌面 / 兼容入口，不是月姬 Vita 打包入口。桌面不能混用当前 Vita GXT 素材；Linux 完整桌面游戏构建还需 GStreamer 开发库，缺失时不能报完整桌面验证通过。

宿主探针按[验证手册](validation.md)选择。完成后运行 `python3 tools/clean-project.py` 预览，`--apply` 删除可重建缓存；外部工具链和 WSL 缓存不由该工具擅自删除。版本控制保持本地，用户明确要求推送后才操作远端。
