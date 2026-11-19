# audit —— 本轮取证与链路验收

| 文件 | 内容 |
|---|---|
| `fact_source_ledger.csv` | 278 行「事实—来源」台账（财务/成本/出栏/现金成本/行业/来源登记） |
| `ledger_summary.json` | 台账行数与状态分布 |
| `fact_source_review.md` | 核对方法、状态定义、抽样结果、发现的问题、冲突与未解决项 |
| `source_status.json` | S-01～S-14 的结构化快照（由登记册解析） |
| `pdf_evidence.json` | 3 份三季报的 URL、披露日、页数、SHA256（原件未入库） |
| `pdf_matches.json` | PDF 字面匹配记录（科目 → 页码），使台账可离线重现 |
| `gen_ledger.py` | 台账生成脚本（有 PDF 则现场解析，否则读 `pdf_matches.json`） |
| `field_mapping.md` | 28 个字段的原始科目、期间、单位与公式 |
| `chain_validation.md` | 全链命令、退出码、哈希、差异与边界 |

## 状态口径（摘要）

`原文一致` / `可解释口径差异` / `实质冲突` / `仅二手` / `原文未取得（仅登记来源）` / `未找到`。
接口 200、站点主页、搜索摘要**不升级**任何状态。

## 台账覆盖范围（如实说明）

台账只覆盖以上 6 类事实（15 家财务关键科目、成本、出栏、现金成本、6 项行业读数、来源登记）。
**未覆盖**：交易性金融资产（图 6 使用）、EVENTS 负面事件、估值（PB/预测）、效率（PSY/MSY）、
管理层评估等研究数据层事实——这些仍以 `research_data_v2.py` 的来源标注为准，未逐条核验。
程序自动生成台账 ≠ 人工核对完成；原文核验仅 3 家三季报抽样（38/39 命中）。

## 复跑

```bash
py -3.12 audit/gen_ledger.py                 # 用已固化的 PDF 匹配记录
py -3.12 audit/gen_ledger.py --pdf-dir <dir> # 现场解析 PDF（需 PyMuPDF）
```

台账与 `ledger_summary.json` 应保持同一 SHA256（当前 `95eea00e…`）。
