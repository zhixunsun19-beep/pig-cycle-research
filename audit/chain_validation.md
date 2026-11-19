# 生成链验收记录（raw → 中间指标 → v3 → 校验）

## 1. 环境与依赖

| 项 | 值 |
|---|---|
| OS | Windows 11（10.0.26100） |
| Python | 3.12.10（`py -3.12`） |
| 第三方依赖 | **计算链零依赖**（纯标准库）；图表需 `matplotlib 3.11.0`；台账 PDF 解析可选 `PyMuPDF` |
| 网络 | 计算链**不联网**；来源取证与 PDF 下载为一次性人工动作 |

## 2. 一键入口

```bash
py -3.12 scripts/run_pipeline.py \
  --raw data/raw \
  --out /tmp/chain_run \
  --compare-baseline
```

执行顺序（子进程，逐步记录退出码与日志）：

1. `scripts/build_derived_metrics.py --raw data/raw --out <out>/derived_metrics.json`
2. `scripts/compute_v3.py --derived <out>/derived_metrics.json --out <out>/v3_results.json`
3. `scripts/verify_results.py --metrics <out>/v3_results.json`
4. 可选：与 `data/processed` 发布件做**事后**字段比较（不作计算输入）

产物与日志：`<out>/manifest.json`、`<out>/logs/step1..3.log`、`<out>/baseline_diff.json`。

## 3. 本次实际运行（2026-11-19 18:44 +08:00）

| 项 | 结果 |
|---|---|
| 输出目录 | `C:\Users\15094\AppData\Local\Temp\pr1_work\chain2` |
| step1 build_derived | rc=0 |
| step2 compute_v3 | rc=0 |
| step3 verify_results | rc=0，**PASS 60 / FAIL 0**（读取的是本次新产物） |
| `derived_metrics.json` | `24044ca24815b8c0caac602d513aef630b109da30d2fba5f5dcdd4abdb8fb3de`（133,824 B） |
| `v3_results.json` | `af899bc10fa4c838d74d19f0e35922c0e75d3cbdb7c4e6e2909fb998a3d6f393`（100,796 B） |

**计算输入边界**：只读取 `data/raw/*.json` 与 `research_data_v2.py`（其 `v1_data.json`
研究数据层来自 `data/processed/`）。**未**把发布版 `derived_metrics.json` 或
`v3_results.json` 作为计算输入；两者仅在 `--compare-baseline` 时于计算完成后读取。

## 4. 与发布版的逐字段比较

| 对象 | 发布版 SHA256 | 本次 SHA256 | 字节一致 | 差异字段数 |
|---|---|---|---|---:|
| `derived_metrics.json` | `7a5c7c15…` | `24044ca2…` | 否 | **30** |
| `v3_results.json` | `af899bc1…` | `af899bc1…` | **是** | **0** |

30 个差异**全部**位于两处：

```
<code>/利润表_2026前三季度/归母净利润
<code>/利润表_2025前三季度/归母净利润
```

即 15 家 × 2 期。发布版为 `null`，本次为实际值（牧原 2026 前三季度 = −93.19 亿元）。
原因与影响见 `fact_source_review.md` §5.1：旧映射的科目名少了「所有」二字；
`compute_v3.py` 未使用该字段，故 **v3 结果与阈值完全不变**（50.56 / 53.92、合格 7 家）。

## 5. 测试

```bash
py -3.12 -m unittest discover -s scripts/tests -v
# Ran 9 tests ... OK
```

覆盖：缺失 vs 0、安全求和、固定资产净额（元级相减）、重复科目取首条、
CLI 与基线逐字段比对（仅允许 30 个预期差异）、跨工作目录一致性、
补录层拒绝覆盖、补录层填充空值并写审计、端到端链路（v3 字节一致 + 60/60）。

## 6. 旧生成器的身份

`scripts/compute_metrics.py` 保留原文件与 `17 字段` 输出能力，但：

- 文件头已加「历史版本，不供 v3 使用」说明；
- 推荐链（`run_pipeline.py`）不调用它；
- 其输出缺 11 个扩展字段，直接喂 `compute_v3.py` 会因缺 `生产性生物资产_*` 报错。

## 7. 发布资产未被改动

运行前后：

| 文件/目录 | SHA256（聚合） |
|---|---|
| `data/processed/derived_metrics.json` | `7a5c7c15…`（未变） |
| `data/processed/v3_results.json` | `af899bc1…`（未变） |
| `data/processed/v1_data.json` | `e254c951…`（未变） |
| `figures/`（21 文件） | `1eb4010f…`（未变） |

## 8. 仍存在的限制

- 中间指标可 100% 由 raw 重算，但 raw 本身是**接口转述**的定期报告；12 家未逐份对照公告 PDF。
- 补录层机制已就绪，但本轮无需补录（raw 覆盖全部 28 字段），`supplement_audit.json` 未生成。
- **字段取值不完整（继承自旧版提取规则，本轮未改）**：利息收入因同名科目「首条优先」
  多数为空（112 处）；其他应收款 2026Q3 未回退「(合计)」而系统性为空（15 家）。
  详见 `field_mapping.md` §7。
- **图表输入边界**：`chartgen/` 仅图 1/7/8/10 读取流水线 v3 产物；图 2/3/4/5/6/9
  锚定发布版 `chart_data/*.csv`，不随重算自动更新。
- 评分结论不变，不代表「事实已全面核验」。
