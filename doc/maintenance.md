# 仓库维护与磁盘

## 目录约定

| 路径 | 用途与保留策略 |
| --- | --- |
| `knife/` | 引擎、原生后端、生成的运行索引、探针与许可证；保留 |
| `tools/` | 构建／转换／检查工具和测试；可执行辅助工具按实际需要本地准备 |
| `doc/` | 当前技术说明及小型验证记录；不放全资源、批量截图或编译日志 |
| `项目截图/` | README 使用的玩家实机截图及原问题记录 |
| `dist/TSUKIHIME-RE/assets/` | 唯一最终素材包，Git 忽略；保留 |
| `release/` | 只放最终 `knife-vita-tsukihime-540p.vpk`，Git 忽略；保留 |
| `.work/` | 临时转换、解包、编译、日志、调查；可丢弃，不放唯一源码、密钥或存档 |
| `knife/target/`、`__pycache__/` | 可重建缓存；清理 |

原始 NSP、工具链、模拟器和用户密钥放在仓库外，不复制整套游戏作为备份。转换时逐个归档替换，完成后删除失败 `.partial` 和旧 attempt。

## 清理命令

```sh
python3 tools/clean-project.py          # 查看选定路径和逻辑大小
python3 tools/clean-project.py --apply  # 删除已列出的临时内容
```

脚本只选择 `.work/`、仓库内 Rust target、Python 缓存、两个已解压工具的下载 ZIP，以及旧工具生成的 `doc/logs/` 和 `doc/` 顶层 JSON／log 报告；不选择 `dist/`、`release/`、Git 历史、`doc/evidence/` 或 vendor 依赖。长期记录须存入 `doc/evidence/`。目录链接只删除链接本身，不遍历目标。`--keep-work NAME` 可在进行中的任务里保留一个 `.work` 直接子目录。

外部 WSL 编译缓存不在脚本自动范围内。本机曾使用 `/root/.cache/knife-vita-tsik`、`/root/.cache/knife-vita-tsik-audit-host`，本次单独核对并清除；不要用通配符清理其它项目或整个 Cargo registry。删除缓存会让下次编译变慢，不影响现有 VPK。

WSL 虚拟磁盘内释放的空间不一定立即使 Windows 上的 VHDX 缩小，因此把“缓存内容已删除”和“宿主磁盘实际空闲增加”分开报告。本次没有压缩或重置整个 WSL 发行版。

## 本次整理

2026-11-02 首次整理前，仓库逻辑大小约 44.57 GiB，其中 `.work` 约 40.29 GiB：合并 romfs、三次双语言 attempt、旧 portable 包、失败归档和各阶段编译产物是主要来源。当时 `dist` 约 4.01 GiB。当前稳定版原地缩小剧情图片，数据与清单约 2.26 GiB，只保留这一套；最终 `release/` 仅保留默认名的稳定版 VPK。

已将当前构建与关键验证事实收敛到 `doc/evidence/`，删除旧魔夜拷贝文档、早期计划／旧包交付表、原始日志和多余证据。根 README、引擎说明和工具索引只指向当前文档。

首次整理统计见[清理收据](evidence/repository-cleanup.json)的原始字段；本次稳定版清理补充于同文件的 `latest_stable_cleanup` 及[当前验证](evidence/current-validation.json)。WSL 缓存按逻辑字节记录，未把 VHDX 自动缩小作为完成条件。

## 后续更新规则

- 换包时同步根 README 的 build tag／字节数／hash 与当前构建收据。
- 素材改变时先生成 profile／atlas／stream 索引，再构建对应 VPK。
- 旧 hash 只用于明确的历史证据，不再把多个日期的包都称为“当前包”。
- 构建输入、vendor 静态库和生成 shader／索引不能当缓存删；用户的外部 NSP、存档和密钥不由清理工具操作。
- 修改默认留在本地；只有用户明确要求推送时才写远端，不自动发布 Release。
