# 文件清单（file_inventory.md）

**盘点时间**：2026-11-18｜**对应报告**：v6.1（评分口径 v3）
**说明**：以 `github_release/` 实际存在的文件为准逐项核对；同类文件（如 15 份财报）合并一行并注明命名规则。
**总计**：100 个文件，约 16.9 MB。

图例：公开 = `✅ 计划公开` / `⚠️ 需确认`；必要 = 是否属于「读懂报告 / 核对数字 / 复算」所必需；处理 = `保留` / `改写路径` / `去重` / `排除`。

---

## 一、根目录（7）

| 文件名 | 类型 | 用途 | 版本 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|---|
| `README.md` | MD | 中文主版：首屏、差异、结论、快速开始、边界、许可 | v6.1 | ✅ | 是 | 重写（qiangshou GitHub README 模式） |
| `README_EN.md` | MD | 英文版，顶部与中文版互链 | v6.1 | ✅ | 是 | 新写 |
| `CHANGELOG.md` | MD | v3→v6.1 版本演进与模型修订 | v6.1 | ✅ | 是 | 新写 |
| `CITATION.cff` | CFF | 引用元数据（作者待填） | v6.1 | ✅ | 否 | 新写 |
| `LICENSE` | MD | 许可范围说明（非统一授权） | — | ⚠️ | 是 | 新写 |
| `.gitignore` | 配置 | 排除缓存/密钥/临时文件 | — | ✅ | 是 | 新写 |
| `file_inventory.md` | MD | 本清单 | — | ✅ | 否 | 新写 |

## 二、报告 `report/`（4）

| 文件名 | 类型 | 用途 | 版本 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|---|
| `report.html` | HTML | **最终报告**，单文件、10 图 base64 内嵌 | v6.1 | ✅ | 是 | 保留＋链接改写（`exhibits_v5/`→`../figures/` 等） |
| `report.md` | MD | 报告正文源 | v6.1 | ✅ | 是 | 保留 |
| `report_notes.md` | MD | 版本、阅读入口、检查范围限定、已知问题 | v6.1 | ✅ | 否 | 新写 |
| `report_print.pdf` | PDF | 22 页打印版 | v6.1 | ✅ | 否 | 保留 |

## 三、图表 `figures/`（21）

| 文件名 | 类型 | 用途 | 版本 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|---|
| `chart_01_quadrant_matrix.svg` / `.png` | SVG/PNG | 图1 企业穿越猪周期能力矩阵 | **角标修正版** | ✅ | 是 | SVG 保留；PNG **由修正版 SVG 重新渲染**（原 PNG 为旧角标） |
| `chart_02_sow_inventory.svg` / `.png` | SVG/PNG | 图2 能繁母猪存栏（5 观测点） | 原版 | ✅ | 是 | 保留 |
| `chart_03_complete_cost.svg` / `.png` | SVG/PNG | 图3 12 家完全成本（期间不一） | 原版 | ✅ | 是 | 保留 |
| `chart_04_output_volume.svg` / `.png` | SVG/PNG | 图4 出栏规模（2026 为年化） | 原版 | ✅ | 是 | 保留 |
| `chart_05_financial_safety.svg` / `.png` | SVG/PNG | 图5 资产负债率与现金覆盖 | 原版 | ✅ | 是 | 保留 |
| `chart_06_debt_and_cash.svg` / `.png` | SVG/PNG | 图6 有息负债结构与货币资金 | 原版 | ✅ | 是 | 保留 |
| `chart_07_cash_runway_heatmap.svg` / `.png` | SVG/PNG | 图7 六情景集团现金跑道 | 原版 | ✅ | 是 | 保留 |
| `chart_08_price_sensitivity.svg` / `.png` | SVG/PNG | 图8 猪价 +1 元理论贡献 | 原版 | ✅ | 是 | 保留 |
| `chart_09_output_increase_10pct.svg` / `.png` | SVG/PNG | 图9 出栏 +10% 理论损益 | 原版 | ✅ | 是 | 保留 |
| `chart_10_score_components.svg` / `.png` | SVG/PNG | 图10 评分构成（得分率版） | **得分率版** | ✅ | 是 | 保留 |
| `README.md` | MD | 10 图标题、单位、口径、颜色语义 | — | ✅ | 否 | 新写 |

## 四、数据 `data/`（46）

### 4.1 `processed/`（25）

| 文件名 | 类型 | 用途 | 版本 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|---|
| `v3_results.json` | JSON | **评分/压力测试/弹性/四象限唯一来源** | v3 | ✅ | 是 | 保留 |
| `v2_results.json` | JSON | v2 旧评分（仅供新旧对比，不可互比） | v2 | ✅ | 否 | 保留并标注 |
| `derived_metrics.json` | JSON | 15 家三表衍生指标 | v3 输入 | ✅ | 是 | 保留 |
| `v1_data.json` | JSON | v1 研究数据层（`research_data_v2.py` 依赖） | v1 | ✅ | 是（复算） | 补充收录（上轮遗漏） |
| `VERSION_NOTES.md` | MD | v2/v3 版本说明与 9 家得分差异（不改旧值） | v3 | ✅ | 是 | 新增（本次核查） |
| `v2_成本排名与口径_15家.csv` | CSV | 成本、期间、口径、来源 | 定稿 | ✅ | 是 | 保留原名 |
| `v2_股票池核验与出栏量_15家.csv` | CSV | 池核验、出栏、分部拆分 | 定稿 | ✅ | 是 | 保留原名 |
| `v2_财务安全与偿债_15家.csv` | CSV | 负债率、有息负债、覆盖 | 定稿 | ✅ | 是 | 保留原名 |
| `v2_六情景压力测试_9家核心.csv` | CSV | 9 家 × 6 情景 | 定稿 | ✅ | 是 | 保留原名 |
| `v2_复苏盈利弹性与估值_9家核心.csv` | CSV | 弹性、市值、估值 | 定稿 | ✅ | 是 | 保留原名 |
| `v2_综合评分与四象限_9家核心.csv` | CSV | 评分明细与象限 | 定稿 | ✅ | 是 | 保留原名 |
| `v2_指标可得性矩阵_15家.csv` | CSV | 195 项指标可得性 | 定稿 | ✅ | 是 | 保留原名 |
| `v2_行业供需关键读数.csv` | CSV | 能繁、出栏、进口等 | 定稿 | ✅ | 是 | 保留原名（表头错位已在文档说明） |
| `v2_负面事件_池内全量.csv` | CSV | 15 家事件库 | 定稿 | ✅ | 是 | 保留原名 |
| `chart_data/*.csv`（11 个） | CSV | 10 张图的制图源数据（含可得性矩阵，故 11 个） | v3 | ✅ | 否 | 保留 |

> `v2_` 前缀是**产出批次编号**，不是评分版本；评分版本以 `v3_results.json` 为准。

### 4.2 `raw/`（15）⚠️ 需确认

| 文件名 | 类型 | 用途 | 版本 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|---|
| `000048.json` `000876.json` `001201.json` `002100.json` `002124.json` `002157.json` `002385.json` `002567.json` `002714.json` `002840.json` `300498.json` `600975.json` `603363.json` `603477.json` `605296.json` | JSON | 15 家 × 8 期三表原始科目 | 一手 | ⚠️ | 是（仅复算） | 保留；可按 `.gitignore` 整目录排除 |

### 4.3 `metadata/`（6）与 `README.md`

| 文件名 | 类型 | 用途 | 版本 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|---|
| `data_dictionary.md` | MD | 字段定义、单位、来源层 | — | ✅ | 是 | 保留 |
| `formulas.md` | MD | 评分与情景公式 | — | ✅ | 是 | 保留 |
| `source_register.md` | MD | 来源索引（指向 `sources/`） | — | ✅ | 是 | 新写（指针） |
| `data_quality_issues.md` | MD | 20 条问题台账 | — | ✅ | 是 | 保留 |
| `source_periods.md` | MD | 各数据期间与来源 | — | ✅ | 是 | 保留 |
| `missing_data.md` | MD | 缺失清单 | — | ✅ | 是 | 保留 |
| `README.md` | MD | 数据目录使用说明（含五条约束） | — | ✅ | 是 | 新写 |

## 五、脚本 `scripts/`（10）

| 文件名 | 类型 | 用途 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|
| `verify_results.py` | PY | **可直接运行的 60 项校验**（实测全过） | ✅ | 是 | 新写＋实测 |
| `compute_v3.py` | PY | 评分 + 压力测试 + 四象限 | ✅ | 是 | 保留（实测重算一致） |
| `compute_metrics.py` | PY | 三表 → 衍生指标 | ✅ | 是 | 保留 |
| `research_data_v2.py` | PY | 研究数据层 | ✅ | 是 | 保留 |
| `fetch_v2.py` | PY | 批量取三表（需网络） | ✅ | 否 | 保留 |
| `build_exhibits_v3.py` | PY | 生成 10 图（路径依赖原项目） | ✅ | 否 | 保留并标注不可直接跑 |
| `build_html_v4.py` | PY | MD → 单文件 HTML | ✅ | 否 | 保留并标注 |
| `fix_v61.py` | PY | v6.1 定点修复 | ✅ | 否 | 保留并标注 |
| `requirements.txt` | TXT | 依赖与实测版本 | ✅ | 是 | 新写 |
| `README.md` | MD | 环境、复现边界、脚本职责 | ✅ | 是 | 新写 |

## 六、文档 `docs/`（10）

| 文件名 | 类型 | 用途 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|
| `methodology.md` | MD | 数据分层、公式、六情景、跑道限制 | ✅ | 是 | 保留（原 `appendix/methodology`；原工程目录未随仓库提供） |
| `scoring_framework.md` | MD | v3 评分细则与 v2→v3 对比 | ✅ | 是 | 保留（原 `appendix/scoring-rules`；原工程目录未随仓库提供） |
| `assumptions.md` | MD | 全部非披露假设与偏差方向 | ✅ | 是 | 新写 |
| `validation/data_validation.md` | MD | 数据清单、A2、正邦核验、一致性 | ✅ | 是 | 保留 |
| `validation/resource_validation.md` | MD | 资源完整性实测 | ✅ | 是 | 保留 |
| `validation/review_findings.md` | MD | 问题清单（含上轮结论更正） | ✅ | 是 | 保留 |
| `validation/change_log.md` | MD | 详细修改记录 | ✅ | 否 | 保留 |
| `validation/quality-review.md` | MD | v3 百分制验收（95 分） | ✅ | 否 | 保留并标注为 v3 视角 |
| `validation/publication_audit.md` | MD | 公开发布安全与合规审查 | ✅ | 是 | 新写 |
| `validation/excluded_files.md` | MD | 未公开文件清单及原因 | ✅ | 是 | 新写 |

## 七、来源 `sources/`（1）

| 文件名 | 类型 | 用途 | 公开 | 必要 | 处理 |
|---|---|---|---|---|---|
| `source_register.md` | MD | S-01～S-14 登记，URL 三档状态 | ✅ | 是 | 保留（原名 `source-register.md`，已统一为下划线） |

---

## 八、未纳入本仓库的文件

完整清单与原因见 [`docs/validation/excluded_files.md`](docs/validation/excluded_files.md)。摘要：

- 过程产物：`_preview*/`（含 Chrome 缓存）、`probe*.html`、`*.pyc`；
- 历史版本：`report.html`、`report_v3_backup.html`、`report_v4_readable.html`、`report_v5_integrated.html`、`report_v6_final.html`、`report.md`、`report_v4.md`；
- 历史脚本：`build_report*.py`、`edit_report*.py`、`integrate_v5_charts.py`、`compute_v2.py` 等；
- 重复数据：图表包 `source/original_files/raw/`（与 `data/raw/` 完全重复，10.5 MB）、旧 `exhibits/`；
- 敏感内容：`.env`、任何密钥、本机路径（发布件中为 0 处）。

## 九、统计

| 目录 | 文件数 | 说明 |
|---|---:|---|
| 根目录 | 7 | 入口与元数据（中英双语） |
| `report/` | 4 | HTML / MD / 笔记 / PDF |
| `figures/` | 21 | 10 对图 + 1 说明 |
| `data/` | 47 | processed 25 + raw 15 + metadata 6 + README 1 |
| `scripts/` | 10 | 8 脚本 + 依赖 + 说明 |
| `docs/` | 10 | 3 方法 + 7 验证 |
| `sources/` | 1 | 来源登记 |
| **合计** | **100** | 约 16.9 MB |
