# 月姬 Vita R2：资源加载阻断修复

本次依据用户的实机故障报告修复 `tsik-vita`，继续以 `mofa-vita` 提交 `143499848bdb6ec08a08b5b12b997cf7aea3d762` 为共享平台基线。用户截图是设置页，没有错误原文或脚本位置，因此无法把某一张图片直接认定为截图所处卡点；下列故障均来自本地可重复验证。

## 已确认的问题与修复

1. 修复前，生产 C 解码器拒绝了素材包中 205 张 PNG，均返回 `KV_IMAGE_DIMENSIONS (-4)`。其中 97 张普通图片超过宽 960 / 高 1080 边界，108 张属于四语言纵向条带，整张解码时超过边界。文件哈希正确不代表运行时可用。
2. 另有 5,544 张 codec9 GXT 超过上述边界。普通绘制可能使用 GPU 路径，但需要 CPU 调色或读取像素时会触发尺寸、输出预算或 GPU 尺寸限制。R2 总计修复 5,641 张越界普通图片：`w_allpac` 5,406 张、`w_allpaccg` 235 张。沿用 mofa 的 960×540 等比约束，保留 KIMG 的逻辑宽高与定位。缩放后的 UNORM 结果保存为无损 PNG7，不再执行 inverse Alter，也不再引入一轮 DXT 有损压缩。其代价是这些图片进入 PNG 解码路径，设备上的加载时间与缓存压力需要复测。
3. 四语言 PNG 改为逐行读取全文件，只保留所选语言的行。保持原来的 960×1080 输出边界与 4.25 MiB 解码工作预算；仍检查所有行和末尾 CRC。原有普通 PNG/JPEG 的边界没有放宽。CPU 调色缓存按当前语言的输出大小预留预算。
4. `knife-platform-vita/build.rs` 优先选择月姬 profile，使启动检查、`ASSET_MANIFEST`、40 个 UI atlas / 736 个成员和 16,601 个 stream 名称绑定同一个清单。公开 atlas 生成器支持自动识别 `w_allui`，不再依赖 `.work` 中的替换脚本。
5. 同步 mofa 最新音效修复：单次 PCM 分配、16 MiB 缓存、空闲缓存回收、低内存处理及分配失败回归；保留月姬的数据根与存档命名空间。
6. 默认构建改为月姬，默认缓存目录独立于 mofa。月姬 feature 同时启用 540p，修正存档测试、构建收据中的素材路径/语言/分辨率/feature、旧 provisional 标签。
7. quiet 正式包也会在资源第一次失败时写入 `ux0:data/knife-tsukihime-540p/resource-error.json`，记录资源名、场景、PC 和错误。正常帧不增加这项文件写入；失败仍保留脚本位置，不跳过剧情指令。

## 验证与边界

| 检查 | 结果 |
|---|---|
| 修复前实际生产解码器 | 205 / 205 张问题 PNG 返回 -4，证据保存在 `.work/repair-20261031/native-failures-before.json` |
| 最终素材 SHA-256 与大小 | 16,832 个文件，4,103,480,689 B，全部匹配 |
| 最终真实 PNG 解码 | 8,988 次成功，覆盖 303 张条带的全部四语言选择；包含分配所有权和输出尺寸验证 |
| 最终 GXT | 15,845 张结构、格式、载荷、尺寸和运行时输出边界验证成功；这项全量检查没有执行每张 GXT 的 CPU 像素解码 |
| 原生 C | ASan / UBSan、Adam7、透明度、四语言选择、完整 CRC、预算、逐分配失败注入全部通过；Vita ARM 编译与静态链接通过 |
| Rust 回归 | 音效/性能 27 项、平台月姬 66 项与默认 66 项、解码所有权 13 项、GXT CPU 5 项与上传 8 项通过；CPU 测试中可选的外部真实图片 fixture 未提供 |
| 素材工具 | 4 项合成回归通过，覆盖源文件保留、逻辑尺寸、透明度、语言边界及没有 `parts.nam` 的归档 |
| VPK | 完整 ARM release 构建、SELF / SFO / LiveArea / shader 编译器 / 21 个纯引擎条目的检查通过 |
| 桌面整游戏测试 | WSL 缺少 GStreamer 开发库，host 整游戏测试未执行完毕；不得计作通过。Vita release 构建不依赖该库，已完成 |
| 实机 | 旧版故障由用户观察；R2 尚未进行设备运行或通关验证 |

四语言读取测试和全量 PNG 验证使用与 Vita 相同的 C 源码。主机测试无法证明设备驱动行为、休眠恢复、音视频全流程或整部剧情可完成。R2 不宣称已经完成 mofa 全特性的实机等价验证。

## 安装

使用 `release/tsukihime-540p-r2/` 的安装包和素材补丁，具体文件大小及 SHA-256 见该目录的 `SHA256SUMS.txt`、`delivery.json` 与 [证据](evidence/14-resource-repair-r2.json)。**新 VPK 与新素材清单必须配套升级。**

1. 退出游戏，备份 `ux0:data/knife-tsukihime-540p/saves/`。
2. 在电脑解压素材补丁，将 `assets/` 中 5 个文件覆盖到 `ux0:data/knife-tsukihime-540p/assets/`：`w_allpac.hed`、`w_allpac.mrg`、`w_allpaccg.hed`、`w_allpaccg.mrg`、`vita-540p-assets.json`。其余素材沿用原包。不要删除 `saves/`。
3. 安装 R2 VPK，覆盖升级同一 TITLE_ID `KNIF00541`；不需要卸载原应用。
4. 启动后读入卡点前的存档，重试原场景。如果再次失败，保留错误画面和 `resource-error.json` 的内容。

完整修复素材目录现为 `dist/Tsukihime-540p-Vita/assets/`，原素材保留在 `dist/Tsukihime-540p-Vita-before-r2/assets/`；原源码与 VPK 的本地快照保留在 `.work/repair-20261031/before-source-and-release.zip`。

## 复现

```sh
# Python 需要 Pillow、NumPy。输出必须不存在，输入保持只读。
python3 tools/repair-tsukihime-assets.py \
  dist/Tsukihime-540p-Vita-before-r2/assets <new-pack>/assets \
  --report <new-pack>/repair.json
python3 tools/generate_vita_asset_profile_tsukihime_540.py --assets <new-pack>/assets
python3 tools/generate-vita-atlas-index.py <new-pack>/assets knife/knife/data/vita_atlas_index_tsukihime_540p.rs
python3 tools/generate-vita-stream-index.py <new-pack>/assets/vita-540p-assets.json knife/knife/data/vita_stream_index_tsukihime_540p.txt
KNIFE_BUILD_TAG=tsukihime540-r2-20261031-resource-fix bash tools/build-vita.sh game release
```

`tools/verify-tsukihime-runtime-assets.py` 接收由生产 C 源编译的主机共享库，可重复进行全量哈希、实际 PNG/JPEG 解码和 GXT 边界检查。证据目录记录本次具体日志的 SHA-256。

本次所有修改和产物均留在本地；`tsik-vita` 没有 Git 元数据，未创建提交或分支；参考 `mofa-vita` 工作区保持干净，未执行任何推送。
