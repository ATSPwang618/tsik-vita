# 验证记录索引

[文档导航](../README.md) · [当前验证结论](../validation.md)

这里保存可追溯的小型记录，不存整套素材、VPK、构建缓存或批量原始日志。记录中的 `as_of` / build tag / hash 决定适用版本；旧文件名含 current 不意味着它永远代表最新结果。不要因文档整理而改写历史事实。

| 记录 | 阶段与用途 |
| --- | --- |
| [current-build.json](current-build.json) | 2026-11-06 离线 shader VPK 构建输入、参数、包成员与哈希；分支 / 远端是当时快照 |
| [current-validation.json](current-validation.json) | 同一包的有界验证；保留稳定配置 5 项失败及 hardware=false |
| [offline-shaders.json](offline-shaders.json) | 109 个 GXP 的源码、工具、反射、重复编译和指令数 |
| [offline-shader-tests.txt](offline-shader-tests.txt) | 该 shader 阶段的原生与宿主测试摘要 |
| [stable-assets-validation.json](stable-assets-validation.json) | 2026-11-02 稳定素材与配套旧 VPK 的验证，非当前离线 shader 包身份 |
| [stability-preprocessing.json](stability-preprocessing.json) | 剧情 512 KiB 策略、15,901 条变更、前后哈希、事务与 7 文件更新 |
| [image-size-audit.json](image-size-audit.json) | 稳定包的物理尺寸 / 行距 / UI 例外与旧失败资源 |
| [current-test-results.txt](current-test-results.txt) | 历史分阶段原始测试摘要；按条目日期读取，不作为本轮全部重跑 |
| [lossless-textures.json](lossless-textures.json) | 上一高清包的 P8 / RGB24 候选与存储验证；素材身份已被稳定包替换 |
| [r4-asset-verification.json](r4-asset-verification.json) / [r4-gxt-decode.txt](r4-gxt-decode.txt) | R4 高清恢复与 UI / GXT 检查，稳定版保留 UI / 缩略图但缩小剧情图 |
| [cdram-diagnosis.json](cdram-diagnosis.json) | 用户实机物理页不足故障与原始身份，非新包已跨过故障点的证明 |
| [large-file-diagnosis.json](large-file-diagnosis.json) / [native-seek-arm.txt](native-seek-arm.txt) | 大归档截断诊断与 ARM / SDK 文件位置证据 |
| [performance-baseline.json](performance-baseline.json) | 固定魔夜提交的移植验证范围，不是本版月姬 FPS 结论 |
| [repository-cleanup.json](repository-cleanup.json) | 早期大目录 / 稳定素材清理事实，不用作本次释放大小 |
| [offline-shader-cleanup.json](offline-shader-cleanup.json) | 上一 shader 任务的缓存回收，WSL 内容减少不代表 VHDX 自动缩小 |
| [repository-maintenance-20261106.json](repository-maintenance-20261106.json) | 本轮冗余脚本 / 重复 eboot / 死 helper 清理、文档重写与新检查 |

旧 `.work` 路径可能已经清理。原记录保留路径用于说明当时证据来源，不声称临时文件还在，也不从历史通过数推导当前实机状态。清理工具保护本目录；必要的历史诊断保留在这里，废弃可执行报告生成器由 Git 历史保留。
