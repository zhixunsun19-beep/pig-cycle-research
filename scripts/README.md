# 脚本目录（scripts/）

## 1. 环境

- Python **3.12.10**（实测版本）
- 依赖：`pip install -r requirements.txt`
  - `matplotlib==3.11.0`（仅图表生成脚本需要）
  - `markdown==3.10.2`（仅 HTML 构建脚本需要）
  - `requests==2.33.0`（仅 `fetch_v2.py` 取数需要）
- **`verify_results.py` 只用标准库，无需安装任何依赖即可运行。**

## 2. 最快验证（推荐先跑这个）

```bash
python verify_results.py
```

读取 `../data/processed/v3_results.json`，逐项核对报告公开的关键数字与内部一致性：
A2 未评分 9/9、有效满分 50/35、`comparable_score` 可复算、`final_score` 与 cap 规则一致、
7 家最终得分、待核实企业的覆盖率与象限、阈值 50.56/53.92、六情景与关键跑道等。

**实测结果：PASS 60 / FAIL 0。** 若失败会打印具体项并返回退出码 1。

## 3. 评分链复现（实测可跑）

脚本按「数据与脚本同目录」设计。把数据放到脚本目录后即可重算：

```bash
# 在 scripts/ 下准备数据
cp -r ../data/raw ./raw
cp ../data/processed/v1_data.json ../data/processed/derived_metrics.json ./

python compute_metrics.py     # 可选：从 raw/ 三表重算 derived_metrics.json
python compute_v3.py          # 生成 v3_results.json（评分 + 压力测试 + 四象限）
python verify_results.py      # 60 项校验
```

**实测（2026-11-18，Python 3.12.10，隔离副本）**：`compute_v3.py` rc=0，重算产出与仓库
`data/processed/v3_results.json` **字节级完全一致**（SHA256 `af899bc1…` 相同，0 字段差异），阈值同为
50.56 / 53.92、合格企业 7 家。`verify_results.py` 在同一副本与仓库实际目录下均为 **60/60 PASS**。

> `compute_metrics.py` 会覆盖同目录的 `derived_metrics.json`；在脚本目录操作，不影响仓库 `data/`。

## 4. 图表与 HTML 构建脚本：不承诺一键重跑

以下脚本依赖原研究项目的中间文件或固定目录，**仓库内不能直接运行**，仅作为方法透明化保留：

| 脚本 | 依赖 | 说明 |
|---|---|---|
| `build_exhibits_v3.py` | 读取 `../data/processed/`，输出到 `../figures_rebuilt/`（本次已适配） | 可运行（实测 rc=0，10 张 PNG），但生成的是**旧版 `fig_*` 自绘图**，与正式 `figures/chart_*`（v5 制图版）不是同一套资产，不能用于替换发布图表 |
| `build_html_v4.py` | 读取 `report_v4.md`（v4 中间稿，未随仓库发布） | 生成单文件 HTML；仓库提供成品 `report/report.html` |
| `fix_v61.py` | 读取 `report_v6_final.html`（v6 中间稿，未发布） | v6.1 定点修复（图1角标/成本表/正邦） |

**因此本仓库不提供 `run_all.py`**——用一条命令跑通整链在当前文件集下并不成立，写了就是虚假承诺。
图表可复现的是**数据**（`data/processed/chart_data/`），不是构建入口。

## 5. 各脚本职责

| 文件 | 输入 | 输出 | 仓库内可跑 |
|---|---|---|---|
| `fetch_v2.py` | 网络 + 财报接口 | `raw/*.json` | ❌ 需外网与接口 |
| `compute_metrics.py` | `raw/*.json` | `derived_metrics.json` | ⚠️ 复制 `raw/` 后 |
| `research_data_v2.py` | `v1_data.json` | 研究数据层（被 import） | ⚠️ 复制数据后 |
| `compute_v3.py` | `derived_metrics.json` + `research_data_v2.py` | `v3_results.json` | ✅ 复制数据后（已实测） |
| `verify_results.py` | `../data/processed/v3_results.json` | 控制台校验 | ✅ 直接可跑（60/60） |
| `build_exhibits_v3.py` | 原项目 `outputs/` 路径 | 10 张图 | ❌ 需改路径 |
| `build_html_v4.py` | `report_v4.md` | HTML | ❌ 中间稿未发布 |
| `fix_v61.py` | `report_v6_final.html` | v6.1 HTML | ❌ 中间稿未发布 |

## 6. 运行环境备注

- 操作系统：脚本在 Windows 11 + Git Bash 下实测通过；纯 POSIX 路径亦可运行（未使用平台特有 API）。
- matplotlib 需中文字体（微软雅黑 / Noto Sans CJK）；缺字体时中文可能显示为方框，不影响数值。
- 脚本无硬编码的本机绝对路径（均以 `Path(__file__).parent` 定位），已通过安全扫描。
