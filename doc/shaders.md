# 离线 shader 与像素运算精简

[文档导航](README.md) · [优化总表](optimizations.md) · [验证](validation.md)

## 当前默认

月姬构建使用 `offline_shaders.c`，把 **109 个 GXM 程序**嵌入 eboot；不加载运行时编译器，不读写磁盘 shader cache，不在 VPK 中携带 `libshacccg.suprx`。**离线程序与新增专用变体默认启用，不需要 TXT。**

| 程序组 | 数量 |
| --- | ---: |
| 基础 quad 顶点 / 片元 | 2 |
| 基础特效：顶点入口 + 17 个片元入口 | 18 |
| 已有快速入口 | 10 |
| 双层混合组合 | 16 |
| 新增专用变体：图片 8 + 文字 4 + 模糊 3 + 快照混合 24 + fetch 混合 24 | 63 |
| 合计 | 109 |

清单覆盖本项目 Cg 入口、WGSL 顶点 / 片元入口与全部 24 种 PsOp。它是引擎特效路径清单覆盖，不是全部游戏演出的实机验收。生成 GXP 总计 208,696 字节，详情见[离线收据](evidence/offline-shaders.json)。

## 精简内容

| 路径 | 原主指令数 | 专用程序 | 适用条件 |
| --- | ---: | ---: | --- |
| 图片 / 灰度 / 反色 / 规则 / 组遮罩 | 146–166 | 8–29 | 所有顶点横纵波纹振幅为 0、无软裁剪；保留 premultiply |
| 普通文字 | 61 | 7 / 9 | 同次绘制 bordered 与 box-filter 标志一致 |
| 4×4 滤波文字 | 61 | 47 / 49 | 保留 16 次滤波采样，去掉冗余初始采样与标志分支 |
| 三种模糊 | 63 | 31 / 38 / 37 | mode 已确认为 0 / 1 / 2；保留 sigma、tap、边界、归一化与 alpha |
| 24 种快照混合 | 614 | 158–297 | PsOp 预先确定，其余 haze / soft / rule / group 参数动态处理 |
| 24 种目标颜色读取混合 | 577 | 163–251 | 独立 framebuffer-fetch 路径，保留 UNORM8 量化与透明早退 |

这些是 **GXP 静态主指令流长度**，包含分支体，不能换算每像素实际执行量、GPU 时间或 FPS 提升比例。编译选项保持 `-O3 -bestprecision -nofastmath -nofastint`，没有全局改 half，也没有删减模糊采样。

## 准入、回退与内存

设备仍需 program check、注册和 shader-patcher 链接。必需基础程序优先准备；新增程序在固定 patcher 池内尝试准入。缺失、链接失败、输入不适用或混合状态不满足时，逐绘制回退到同类通用程序。快照与 framebuffer-fetch 不互相误替换。

变体增加程序与 MAIN 元数据，不创建额外纹理，也不扩大 CDRAM 纹理预算。离线化减少编译依赖和启动编译工作；专用变体才负责减少相应绘制中的无用运算。这两项收益应分别验收。

## 生成与校验

生成头是正式构建输入；常规打包无需编译器。修改 Cg 后，从仓库根执行：

~~~sh
python3 tools/compile-vita-offline-shaders.py --compiler /path/to/psp2cgc
python3 tools/generate-runtime-shaders.py
python3 tools/compile-vita-offline-shaders.py --check
python3 -B -m unittest discover -s tools -p 'test_offline_shaders.py'
~~~

Windows 也可使用 `py -3` 并指定本地 exe。每个程序编译两次并比较字节，校验 GXP 大小、阶段、指令范围、sampler、F32 uniform 与 native UCHAR4 输出；`--check` 无需编译器，核对源码、生成器、清单和两个头文件。CMake 拒绝过期输出。

唯一完整编译入口为 `compile-vita-offline-shaders.py`。旧部分生成器已删除，避免生成不完整头文件。`generate-runtime-shaders.py` 保留共享非月姬 runtime 路径所需源码，不能误删。编译器与 Sony 模块不复制进仓库。

## 可选开发者 A/B

正常玩家无需操作。若要只关闭新增 63 个变体，可以在 `ux0:data/TSUKIHIME-RE/optimization-profile.txt` 写入 `all -shader-specialization`，重启；删除这个自定义文件即可恢复默认，或改为 `all`。既有自定义白名单需要显式包含 `shader-specialization`。

两组都使用离线程序。启动日志应有 `mode=offline runtime_compile=0 cache_io=0`；`offline_shader_specialization` 的 admitted 最多 63，不足时结合 shader capabilities 和错误日志判断驱动准入。

当前没有本版实机 GPU 时间、像素读回或全演出回归。宿主测试覆盖路由、各混合模式、文字 / 模糊条件、坏输入和回退，但 SDK doubles 不执行 GPU。已有稳定素材只更新 VPK；旧素材按[配套范围](assets.md#升级范围)更新。
