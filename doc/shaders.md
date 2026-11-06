# 离线 shader 与像素运算精简

2026-11-06 的月姬包使用原生 GXM 离线程序。109 个程序全部嵌入 `eboot.bin`：2 个基础复制程序、18 个基础特效程序（含顶点入口）、10 个已有快速入口、16 个双层混合组合，以及 63 个新增专用变体。清单覆盖本项目 Cg 的全部入口与 WGSL 的全部顶点／片元入口，24 种 PsOp 在快照和原生目标颜色读取两条路径中均有覆盖。这是引擎支持的全部特效路径覆盖，不是全游戏脚本实机通关证明。

月姬构建使用 `offline_shaders.c`，不调用运行时编译器、不读取或写入 `shader-cache`，不在 VPK 中携带 `libshacccg.suprx`。驱动仍须在启动时执行 `sceGxmProgramCheck`、注册和 patch；离线编译不能预先代替设备驱动的这些工作。既有快速路径可能因驱动拒绝而回退。

## 精简范围

| 路径 | 原程序主指令数 | 专用程序主指令数 | 选择边界 |
| --- | ---: | ---: | --- |
| 图像／灰度／反色／规则／组遮罩 | 146–166 | 8–29 | 每个顶点横纵波纹振幅为 0，软裁剪关闭；仍保留 premultiply 标志 |
| 普通文字 | 61 | 7／9 | 同一绘制中 bordered 与 box-filter 标志一致 |
| 4×4 滤波文字 | 61 | 47／49 | 保留全部 16 个滤波采样，移除初始冗余采样与运行时标志分支 |
| 三种模糊模式 | 63 | 31／38／37 | CPU 已验证 mode 为 0、1、2；保留 sigma、tap 数、边界、归一化和 alpha 公式 |
| 24 种快照混合 | 614 | 158–297 | PsOp 在绘制前已确定；其余 haze／soft／rule／group 参数仍动态处理 |
| 24 种原生目标颜色混合 | 577 | 163–251 | 与快照路径分别编译；保留 UNORM8 打包与零透明度早退 |

这些数字是 GXP 主指令流长度，含分支体，不是每个像素实际执行的指令数，也不是 GPU 时间或 FPS 提升比例。完整逐项数字与 compiler/source SHA 见[离线构建记录](evidence/offline-shaders.json)。

所有程序继续使用 `-O3 -bestprecision -nofastmath -nofastint`，未全局切到 half，未删模糊采样，未修改素材尺寸。新增程序在启动时尝试链接；缺失、链接失败、状态不适用或混合状态未准备好时，逐绘制回退原有同类程序。快照读取与 framebuffer-fetch 不会互相误替换。必需的基础程序在新增专用程序前准备，继续使用原来的固定 shader-patcher 池；程序表会增加少量 MAIN 元数据，并不创建纹理或增加 CDRAM 纹理预算。

## 实机 A/B

默认 `all` 开启 `shader-specialization`。在 `ux0:data/TSUKIHIME-RE/optimization-profile.txt` 写入以下内容并重启，可关闭本次新增的 63 个专用变体，其余优化保留：

```text
all -shader-specialization
```

恢复 `all` 并重启即重新开启。两种配置都使用离线程序，因此可以将首次编译等待与持续 GPU 负载分开比较。已有自定义优化列表必须显式加入 `shader-specialization` 才启用新增变体。

VitaDeck/CatLog 启动输出应有 `mode=offline runtime_compile=0 cache_io=0` 和 `offline_shader_specialization` 的 `admitted` 数；最多 63，不足表示部分程序未获驱动准入，应结合 `shader_capabilities` 和错误日志检查。相同存档、输入、时长与重场景的性能窗口才适合对比；尚未取得本版实机 GPU 耗时、像素读回或完整演出回归结果。

## 构建与校验

离线 GXP 已作为源码生成文件保留，普通 VPK 构建不需要本地 shader 编译器。修改 Cg 后使用自己已有的 `psp2cgc` 重建：

```powershell
python -B tools/compile-vita-offline-shaders.py --compiler <本地psp2cgc.exe路径>
python -B tools/generate-runtime-shaders.py
python -B tools/test_offline_shaders.py
```

编译器路径只用于本地执行；不复制编译器或 SDK 模块。每个程序编译两次并比较字节，检查 GXP 尺寸、阶段、指令范围、sampler 单元、F32 uniform 与 native UCHAR4 输出。`--check` 校验源码、生成器、清单和生成头身份；CMake 会拒绝过期程序。不要再用旧的 `compile-vita-effects.ps1` 覆盖月姬头文件，它只覆盖早期基础入口，随后构建校验会拒绝。

测试包括实际 C 路由的全顶点判断、24 个混合模式、3 个模糊模式、4 个文字组合、拒绝／未链接回退及优化开关；Python 验证覆盖清单、编译元数据、损坏二进制拒绝和每个新增变体的指令缩减。宿主 SDK doubles 不执行 GPU，不能代替实机验证。

从 2026-11-02 稳定素材版升级，只需安装新 VPK；`dist` 素材未修改。更旧素材版仍按[素材升级范围](assets.md#升级范围)更新。设备上遗留的 shader-cache 本版不会使用，无需为了本次安装重传素材或缓存。
