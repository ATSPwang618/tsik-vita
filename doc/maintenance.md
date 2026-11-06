# 仓库维护与空间管理

[文档导航](README.md) · [工具索引](../tools/README.md) · [本轮整理收据](evidence/repository-maintenance-20261106.json)

## 目录约定

| 路径 | 职责 / 保留规则 |
| --- | --- |
| `knife/` | 引擎、原生后端、生成索引 / shader、探针与许可证；保留构建输入 |
| `tools/` | 构建、转换、验证与测试；公共转换模块按调用关系保留 |
| `doc/` | 当前技术手册；优化集中到 optimizations，包身份集中到 validation |
| `doc/evidence/` | 小型、分阶段证据；旧诊断注明版本，历史收据不改写 |
| `项目截图/` | README 实机截图及原问题观察，不当作当前性能证明 |
| `dist/TSUKIHIME-RE/assets/` | 唯一配套素材树，Git 忽略，不再复制第二套 |
| `release/` | 只保留最终 VPK；不存提取出的重复 eboot、日志或中间包 |
| `.work/` | 可重建的转换、构建、调查输出；不能放唯一源码、密钥或存档 |
| Cargo target / Python cache | 可重建，完成验证后按下述工具清理 |

原始 NSP、SDK、Rust 工具链、模拟器和密钥放在仓库外。改写资源时使用已有逐归档事务，完成后回收临时文件；不要通过复制整棵 dist 制造长期冗余。

## 本轮清理内容

2026-11-06 整理以当前源码与已验证 VPK 为边界：

- 删除 2 个已被完整离线编译器取代的部分 shader PowerShell 生成器。
- 删除 2 个旧魔夜 compact / 270p 交付报告生成器、2 个绑定旧魔夜资源 / 存档临时路径的 release 观察入口。
- 删除依赖缺失模块的旧性能读取器及其测试、只消费已删除 Artemis 调查目录的汇总器。
- 删除离线转换模块中无调用的 `rgb565` / `quant565` Python helper；真正使用的原生 C 编码函数保留。
- 将已完成稳定素材计划并入素材、优化、验证手册，移除单独旧计划；保留支撑当前机制的历史证据。
- 确认 `release/eboot.bin` 与 VPK 内成员逐字节一致后删除这份 10,001,967 字节重复文件。
- 清理工具补齐独立 Cargo probe 工作区的 target 清理，并用测试覆盖。

不是按文件名带旧版、魔夜或 test 就删除。共享非月姬 renderer、格式解析、现用工具导入的历史转换模块、探针、vendor 与许可证仍有职责，保留。完整删除清单、逻辑字节与新验证结果见[本轮收据](evidence/repository-maintenance-20261106.json)。此前 40 GiB 级缓存清理记录只属于[旧任务](evidence/repository-cleanup.json)，不计入本轮。

## 清理入口

~~~sh
python3 tools/clean-project.py
python3 tools/clean-project.py --apply
# 工作未完成时保留一个 .work 直接子目录
python3 tools/clean-project.py --keep-work active-task --apply
~~~

预览输出列出具体路径、逻辑字节与文件数。自动范围：

- `.work/`、`knife/target/`。
- `tools/` / `knife/` 内紧邻 Cargo.toml 的嵌套 target；没有 manifest 的同名目录不删除。
- Python / pytest 缓存、旧工具临时 `doc/logs/` 和 doc 顶层 JSON / log。
- 两个固定路径的已解压工具下载 ZIP。

不选择 dist、release、Git 历史、doc/evidence、源码或 vendor。目录链接只删除选中的链接本身，不遍历外部目标；越界父目录拒绝。当前没有外部 WSL 构建缓存的自动清理逻辑，不用通配符删其他工程缓存或 Cargo registry。

删除 WSL 内文件不保证 Windows VHDX 自动缩小。报告“删除逻辑字节”和“宿主磁盘实际空闲增长”应分开，本轮不压缩 / 重置 WSL。

## 文档与交付更新规则

1. 中文 `README.md` 与英文 `README.en.md` 同步安装步骤、控制、特性、默认行为和验证边界；保留截图与署名。
2. 新优化加入 `doc/optimizations.md`；注册表增减时更新 29 项清单。预算修改同步 performance，shader 修改同步 shaders。
3. 换 VPK 才更新其构建收据与身份；只改文档 / 工具不伪造新的 ARM 构建结果。
4. 素材变化必须先生成 startup / atlas / stream 元数据并重建配套 VPK，再做完整校验；旧 hash 放在注明版本的历史记录中。
5. 检查 Markdown 本地链接、代码语法、对应回归、包身份与清理预览。一次测试失败不能靠删除结果变成“全通过”。
6. 默认所有改动留本地。用户明确说推送时才推指定分支，不自动 force、不动其他分支 / 标签、不自动发布 Release。推送前后读取远端引用并报告。
