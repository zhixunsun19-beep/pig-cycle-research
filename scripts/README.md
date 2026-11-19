# 脚本目录（scripts/）

## 1. 环境

- Python **3.12.10**（实测版本）
- 计算链（`run_pipeline.py` / `build_derived_metrics.py` / `compute_v3.py` /
  `verify_results.py`）**只用标准库**，不需要 `pip install`。
- 仅以下脚本需要第三方依赖（`pip install -r requirements.txt`）：
  - `matplotlib==3.11.0`：`build_exhibits_v3.py`、`../chartgen/build_charts.py`
  - `markdown==3.10.2`：`build_html_v4.py`
  - `requests==2.33.0`：`fetch_v2.py`

## 2. 最快验证（推荐先跑这个）

```bash
python verify_results.py
```

读取 `../data/processed/v3_results.json`（发布件），逐项核对报告公开的关键数字与内部一致性：
A2 未评分 9/9、有效满分 50/35、`comparable_score` 可复算、`final_score` 与 cap 规则一致、
7 家最终得分、待核实企业的覆盖率与象限、阈值 50.56/53.92、六情景与关键跑道等。

**实测结果：PASS 60 / FAIL 0。** 若失败会打印具体项并返回退出码 1。

## 3. 全链重算（raw → 中间指标 → v3 → 校验）

```bash
python run_pipeline.py --raw ../data/raw --out ../build/chain --compare-baseline
```

链路（每步独立子进程，退出码与日志写入输出目录）：

1. `build_derived_metrics.py`：原始三表 → `derived_metrics.json`（**28 字段/家**）
2. `compute_v3.py --derived ... --out ...`：评分、压力测试、弹性、四象限
3. `verify_results.py --metrics ...`：60 项校验，**校验本次新产物**
4. `--compare-baseline`：与 `data/processed` 发布件做事后字段比较（不作输入）

**实测（2026-11-19，Python 3.12.10）**：

| 对象 | 结果 |
|---|---|
| `derived_metrics.json` | `24044ca2…`（与发布版 `7a5c7c15…` 差 30 个字段位置，均为「归母净利润」修正） |
| `v3_results.json` | `af899bc1…`，与发布件**字节一致** |
| `verify_results.py` | PASS 60 / FAIL 0 |
| 测试 | `python -m unittest discover -s tests -v` → 9/9 OK |

说明：

- **计算输入不包含**发布版 `derived_metrics.json` / `v3_results.json`；研究数据层
  `v1_data.json` 从 `../data/processed/` 读取（成本/出栏/事件/估值），属输入而非结果。
- 旧版 `compute_metrics.py` 只输出 17 字段，**不供 v3 使用**；保留作历史参考。
- 补录层：`--supplement <json>`，仅在自动值为 `null` 时填充，禁止静默覆盖，
  并写出 `supplement_audit.json`。本轮 raw 已覆盖全部字段，未使用补录。

详见 `../audit/chain_validation.md`、`../audit/field_mapping.md`。

## 4. 图表工程：原发布图源工程未找回

- `build_exhibits_v3.py`（旧）：生成 `fig_*` 自绘图到 `../figures_rebuilt/`，
  与发布 `figures/chart_*` **不是同一套资产**，不能替代发布图。
- `../chartgen/build_charts.py`（本轮新增）：**替代**制图工程，读取
  `../data/processed/v3_results.json` 与 `chart_data/*.csv`，输出 10 张
  `chart_*` SVG/PNG 到 `../chartgen/out/`；带数据断言，不触碰 `figures/`。
- 原 v5 制图工程未随仓库提供（仅有成品 SVG 与 `chart_notes.md`）；
  `chartgen` 是**替代实现**，不称为「恢复原工程」。

```bash
python ../chartgen/build_charts.py
python ../chartgen/verify_charts.py
```

## 5. 各脚本职责

| 文件 | 输入 | 输出 | 仓库内可跑 |
|---|---|---|---|
| `run_pipeline.py` | `data/raw` + `v1_data.json` | 中间指标、v3、日志、manifest | ✅ 直接可跑（本轮实测） |
| `build_derived_metrics.py` | `data/raw/*.json`（+可选补录） | `derived_metrics.json`（28 字段） | ✅ 直接可跑（本轮实测） |
| `compute_v3.py` | `--derived`（默认同目录） | `--out`（默认同目录） | ✅ 指定路径即可跑 |
| `verify_results.py` | `--metrics`（默认发布件） | 控制台校验 | ✅ 直接可跑（60/60） |
| `compute_metrics.py` | `raw/*.json` | 17 字段的旧版 derived | ⚠️ 历史版本，**不供 v3** |
| `research_data_v2.py` | `v1_data.json` | 研究数据层（被 import） | ✅ 直接 import（命中路径打印到 stderr） |
| `fetch_v2.py` | 网络 + 财报接口 | `raw/*.json` | ❌ 需外网与接口 |
| `build_exhibits_v3.py` | `../data/processed/` | `../figures_rebuilt/` 旧版 `fig_*` | ✅ 可跑，**不替代发布图** |
| `build_html_v4.py` | `report_v4.md` | HTML | ❌ 中间稿未发布 |
| `fix_v61.py` | `report_v6_final.html` | v6.1 HTML | ❌ 中间稿未发布 |
| `tests/` | — | unittest | ✅ 9/9 通过 |

## 6. 运行环境备注

- 操作系统：Windows 11 + Git Bash 下实测通过；纯 POSIX 路径亦可运行（未使用平台特有 API）。
- matplotlib 需中文字体（微软雅黑 / Noto Sans CJK）；缺字体时中文可能显示为方框，不影响数值。
- 脚本无硬编码的本机绝对路径（均以 `Path(__file__).parent` 定位）。
- 除 `run_pipeline.py` 会写 `--out` 指定目录外，其余脚本只在显式输出路径写文件。
