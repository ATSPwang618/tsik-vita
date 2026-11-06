# 构建与依赖

## 环境

- Windows＋WSL、Linux 或 macOS；构建入口为仓库根 `tools/build-vita.py`。
- Python 3.9+、CMake 3.20+、Ninja、Bash、Git、VitaSDK。
- Vita Rust 工具链固定 `nightly-2026-05-28`＋`rust-src`，目标 `armv7-sony-vita-newlibeabihf`。
- 宿主工具／测试使用 `knife/rust-toolchain.toml` 指定的 Rust 1.99.0。

本机已验证 WSL `pocket-ubuntu`、VitaSDK `/opt/vitasdk`、GCC 15.2.0。这是本机路径，不是其它机器的安装要求。

原生依赖的头文件、静态库、来源清单和许可证保留在 `knife/vita/vendor/dependencies/`；shader 扩展在 `knife/vita/vendor/shacccg-ext/`。这些是构建输入，不属于可删除的编译缓存。

月姬默认构建直接使用内嵌的 109 个离线 GXP，不需要 `libshacccg.suprx`，VPK 也不携带该模块。修改 shader 源码后需自行提供本地 `psp2cgc` 重新生成；CMake 会校验全部生成文件身份。命令与边界见[离线 shader](shaders.md)。上游其它 variant 的历史运行时编译路径仍单独保留。

素材转换另需 Pillow／NumPy、kdu 及相应原始数据工具；编译 VPK 本身不需要重新解包游戏，也不需要再次复制 `dist`。

## 命令

从仓库根执行：

```sh
python3 tools/build-vita.py --check
KNIFE_VITA_OFFLINE=1 python3 tools/build-vita.py --variant tsukihime540 game release
python3 tools/check-vita-package.py release/knife-vita-tsukihime-540p.vpk KNIF00541 --release
```

Windows 使用 `py -3` 替代 `python3`，或：

```powershell
./tools/build-vita.ps1 -Check
./tools/build-vita.ps1 -Variant tsukihime540 -Mode game -BuildKind release
```

`--check` 为只读探测。正常构建可能安装缺失的固定 Rust 工具链；`KNIFE_VITA_OFFLINE=1` 禁止自动下载。`--sdk`／`VITASDK` 选择 SDK，Windows 的 `--wsl` 选择发行版，`KNIFE_VITA_CACHE` 可选择缓存目录。

正式构建 feature 为 `vita-gxm,assets-540p,tsukihime`，TITLE ID 为 `KNIF00541`，`ATTRIBUTE2=12`。newlib 堆上限 256 MiB；SDK 文件位置 `SceOff` 为 64 位，程序指针和目标架构仍为 32 位。

月姬正式包默认启用后台控制台（`KNIFE_VITA_QUIET=0`、`KNIFE_PERF_CONSOLE=1`），不启用 DEV 同步文件日志或运行帧数上限。可显式覆盖编译变量；VitaDeck/CatLog 使用见[性能与日志](performance.md#vitadeck-实时日志)。

## 产物与清理

最终包为 `release/knife-vita-tsukihime-540p.vpk`。构建日志、ELF、map、SELF、临时 VPK 和收据写入 `.work/vita/game-release-tsukihime-540p/`；Rust cache 可能在仓库外。

当前离线 shader 版使用默认 VPK 文件名，交付 build tag 为 `tsukihime540-offline-shaders-20261106`（构建时通过 `KNIFE_BUILD_TAG` 指定）。`tsukihime` feature 同时启用 `knife-perf/vita-stable`，沿用 2026-11-02 稳定素材与可选缓存预算。已有稳定素材仅更新 VPK；原高清素材仍按[升级范围](assets.md#升级范围)处理。

发布前验证包结构、成员 SHA／CRC、当前 `sce_sys` 以及素材 profile／atlas／stream 索引。只修改文档或清理缓存，无需重建当前已验证 VPK。今后换包时，将对应的小型收据更新到 `doc/evidence/`，不要把过期包 hash 当成当前值。

磁盘紧张时用[维护说明](maintenance.md)清理中间产物。清理编译缓存后下次构建会重新编译，SDK、Rust 工具链和依赖仍可复用。

## 桌面与探针

`build-windows.sh`、`build-compact.*`、`build-540p.ps1` 是桌面／兼容开发入口，不是当前 Vita 打包入口。桌面资源不能直接用 Vita GXT 包替代；Linux 桌面构建还需要 GStreamer 开发库。本机此前完整桌面游戏测试因此受限，没有计为通过。

宿主与设备探针命令见[验证说明](validation.md)，源码工作区见 [knife/README.md](../knife/README.md)。
