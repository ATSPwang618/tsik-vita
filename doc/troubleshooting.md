# 故障定位

[文档导航](README.md) · [当前包 / 素材身份](validation.md) · [素材配套](assets.md)

先记录 build tag、VPK / 清单 hash、语言、章节 / PC、操作步骤与截图。保留玩家存档、VitaDeck 捕获日志和 `resource-error.json`；不先删校验或改清单。

## 启动检查

| 提示 | 首先检查 |
| --- | --- |
| `MISSING FILE OR FOLDER` | `ux0:data/TSUKIHIME-RE/assets/` 是否完整、是否多套目录 |
| `WRONG FILE SIZE` | 具体文件长度与配套清单；是否使用修复大文件 IO 的当前 VPK |
| `WRONG ASSET VERSION` | VPK 与清单是否配套，有无混入旧高清、旧语言或魔夜资源 |
| `FILE READ FAILED` | 文件可读性、传输、存储介质、日志中的失败范围 |
| `ENGINE PROFILE ERROR` | 源码生成 profile 与素材是否匹配，是否重新构建了正确 VPK |

当前稳定主归档为 819,984,384 字节。历史 2,475,186,176 字节归档曾被 newlib 32 位 off_t 截断，导致实机报错；现用 SDK `sceIoOpen/Read/Lseek/Close`，文件位置是 64 位，**ARMv7 程序仍是 32 位**。修复覆盖启动检查和 MRG 读取，不是仅放宽长度比较。证据见[大文件诊断](evidence/large-file-diagnosis.json)和[ARM seek](evidence/native-seek-arm.txt)。

## 标题 / 三角菜单按钮看不见，但输入有声音

先检查日志是否出现 `UI atlas ready` 或 `ui textures` 错误，再核对语言、图集版本和尺寸。

R4 恢复了宽长图，旧准入仍按宽 ≤960、高 ≤1080 拒绝。例如 `title_bg0` 为 1335×633，`flow_thumb_all_zc` 为 1040×832；单个成员登记失败会使整组 UI 加载失败，输入与音效仍能运行。

当前 GXT 单轴上限改为 2048、总像素仍 ≤960×1080。旧规则拒绝 15 个成员，影响 9 图集；修复后离线检查覆盖全部 24 图集 / 438 成员，日中 title / menu 60 个状态区有可见 alpha。剧情 512 KiB 限制不套用于 UI。若仍复现，保留具体页面 / 状态 / 日志，而非把所有按钮图再次统一缩小。

## 音乐列表、CG 和字体

| 表现 | 已知原因与当前处理 |
| --- | --- |
| Music 列表、时间、音量无字 | 旧补充字体只有两个字形却被优先选择；当前主字体优先。复现时核对字体包、语言和解锁状态 |
| CG 列表空白 | 早期 KIMG / KATL 加载路径不匹配；当前匹配格式加载，不重排原资源 ID |
| 缩略图严重模糊 | 旧图集整页缩小过度；R4 使用分页缩略图。只换 VPK 不会改善旧资源文件 |
| 剧情部分图片不再高清 | 当前稳定策略主动按最坏 RGBA 512 KiB 降采样，属于明确画质取舍，不是所有图都应为 960×540 |
| UI / 缩略图仍很糊 | 这些未随稳定剧情预处理统一缩小，先核对配套 R4 图集与分页资源 |

版本升级范围见[素材手册](assets.md#升级范围)。

## CG 两侧浅灰边

森林原图 1404×844 不为 16:9，完整适配后约 898.3×540，灰底查看器左右各约 30.9 像素。旧摇杆中心漂移可使留边集中一侧；代码已加 ±16 死区，但截图不能证明当时的摇杆读数。

SELECT 可切换保持比例的铺满显示，代价是裁掉部分上下内容。不要为去边拉伸原图，或把所有长立绘强制转成整屏比例。

## 剧情暂停：资源加载失败

已知 scene=1、pc=5309 故障资源 `AOK_A_21_00_N01_03_03` 的原始错误为 `effects texture CDRAM allocation: 0x80024309`，对应物理页不足。旧物理尺寸 1020×1016，RGBA 新页需 4 MiB；附近空闲总量 15 MiB 不代表该次物理分配必然成功，也不足以证明具体碎片分布。

当前采取三层处理：

1. 真实存储预留，有界回收未被在途帧引用的可重载纹理；区分物理页不足与不可恢复 SDK 错误。
2. 换图前释放可选缓存所有权；已经记录的 GPU 资源由完成 fence 保活，旧新图片整组发布。
3. 提前缩小所有超限剧情素材；该图片变为 360×359，RGBA 新页为 512 KiB。`parts` 中 GXT 也按正确原生格式处理。

确认当前 VPK 与[配套素材](assets.md#升级范围)一致，保留存档再复测。现有完整离线扫描和压力夹具不是实机已经跨过故障点的证据；本版尚待该场景和长时间运行验证。原始记录见[CDRAM 诊断](evidence/cdram-diagnosis.json)。

## 没有实时日志或优化未启用

- VitaDeck 先开日志接收，确认 CatLog 为已工作的配置；FTP 连通不证明日志通道连通。
- 启动月姬 TITLE ID `KNIF00541`，核对日志 tag `tsukihime540-offline-shaders-20261106`。
- 正常不需要 TXT。若先前创建过 `perf-enable.txt` 或 `optimization-profile.txt`，检查是否覆盖了默认配置；开发选项详见[性能](performance.md)。
- 离线包不读取旧 shader cache；日志应有 `mode=offline`。专用变体准入不足时结合 shader capabilities 与错误日志排查，见[Shader](shaders.md)。
- 上一 `tsukihime540-ui-log-20261102` 的玩家日志证明那一版链路曾有输出，不等于当前包已重新实测。

SDK doubles、宿主解码和编译通过的边界见[验证记录](validation.md)。当前清理不改变运行时程序，也没有绕过任何故障检查。
