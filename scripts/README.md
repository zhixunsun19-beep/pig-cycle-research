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

## 3. 评分重算（基于已发布的中间数据，实测可跑）

本仓库可复现的是**「用 `data/processed/` 中已发布的中间数据重算 v3」**，不是「从原始财报端到端复现」。

- 输入：`../data/processed/derived_metrics.json`（28 字段/家）、`../data/processed/v1_data.json`
- 脚本：`compute_v3.py`、`research_data_v2.py`、`verify_results.py`（仅标准库）
- 上游缺口：`compute_metrics.py` 是旧版生成器，只产出 17 字段/家，缺 `生产性生物资产_*`、`在建工程_*`、`期间费用_*`、`利润表扩展_*`、`资产负债表扩展_*` 共 11 个字段；用它覆盖输入会让 `compute_v3.py` 报错。完整生成器未随仓库提供。

所有步骤在仓库外临时目录执行，不写 `scripts/` 或 `data/processed/`：

```bash
REPO="$(pwd)"          # repository root
TMP="$(mktemp -d)"     # temp dir outside the repo (PowerShell: New-Item -ItemType Directory)

# 1) copy scripts and published inputs
cp "$REPO/scripts/compute_v3.py" \
   "$REPO/scripts/research_data_v2.py" \
   "$REPO/scripts/verify_results.py" "$TMP"/
cp "$REPO/data/processed/derived_metrics.json" \
   "$REPO/data/processed/v1_data.json" "$TMP"/

# 2) recompute, then verify THIS output explicitly
cd "$TMP"
python compute_v3.py
python verify_results.py --metrics v3_results.json

# 3) compare with the published baseline
sha256sum v3_results.json "$REPO/data/processed/v3_results.json"
cmp v3_results.json "$REPO/data/processed/v3_results.json" && echo "byte-identical"
```

**实测（2026-11-19，Python 3.12.10）**：`compute_v3.py` rc=0；`v3_results.json` SHA256 `af899bc1…`；
`verify_results.py --metrics v3_results.json` → **PASS 60 / FAIL 0**（读取的是本次产物）；
与仓库 `data/processed/v3_results.json` `cmp` 无差异。运行前后仓库输入与发布结果哈希不变。

> `verify_results.py` 默认读 `../data/processed/v3_results.json`（发布件）。重算后必须加 `--metrics <本次输出>`，
> 否则校验的是发布件，不能用来证明重算通过。

> `compute_metrics.py` 仍保留作方法参考，但不要放进 v3 重算链：它只产出 17/28 字段。

## 4. 图表与 HTML 构建脚本：不承诺一键重跑

| 脚本 | 输入 | 输出 | 状态 |
|---|---|---|---|
| `build_exhibits_v3.py` | `../data/processed/` | `../figures_rebuilt/fig_*.png` | ✅ 可运行（实测 rc=0，10 张 PNG）。产物是**旧版 `fig_*` 自绘图**，与发布 `figures/chart_*`（v5 制图版）不是同一套资产，**不能替代发布图表**；`figures_rebuilt/` 已加入 `.gitignore`，不会写入 `figures/` |
| `build_html_v4.py` | `report_v4.md`（未随仓库提供） | 单文件 HTML | ❌ 中间稿缺失 |
| `fix_v61.py` | `report_v6_final.html`（未随仓库提供） | v6.1 HTML | ❌ 中间稿缺失 |
| `compute_metrics.py` | `raw/*.json` | `derived_metrics.json`（17 字段/家） | ⚠️ 旧版生成器，不兼容 v3 |

**发布图表源工程缺失**：`figures/chart_*` 的源工程与 v5 制图流程未随仓库提供，仓库内无法重建这 10 张图；可复现的是图表**数据**（`data/processed/chart_data/`），不是构建入口。

**因此本仓库不提供 `run_all.py`**——用一条命令跑通整链在当前文件集下并不成立。

## 5. 各脚本职责

| 文件 | 输入 | 输出 | 仓库内可跑 |
|---|---|---|---|
| `fetch_v2.py` | 网络 + 财报接口 | `raw/*.json` | ❌ 需外网与接口 |
| `compute_metrics.py` | `raw/*.json` | `derived_metrics.json`（17 字段/家） | ⚠️ 可运行，但**旧版生成器，不能供 v3 使用** |
| `research_data_v2.py` | `v1_data.json` | 研究数据层（被 import） | ✅ 直接可 import（回退读 `../data/processed/`，命中路径打印到 stderr） |
| `compute_v3.py` | `derived_metrics.json` + `research_data_v2.py` | `v3_results.json` | ✅ 按第 3 节复制到临时目录后可跑（已实测） |
| `verify_results.py` | `--metrics`（默认 `../data/processed/v3_results.json`） | 控制台校验 | ✅ 直接可跑（60/60） |
| `build_exhibits_v3.py` | `../data/processed/` | `../figures_rebuilt/` 10 张旧版 PNG | ✅ 可跑（需 matplotlib），**不替代发布图表** |
| `build_html_v4.py` | `report_v4.md` | HTML | ❌ 中间稿未发布 |
| `fix_v61.py` | `report_v6_final.html` | v6.1 HTML | ❌ 中间稿未发布 |

## 6. 运行环境备注

- 操作系统：脚本在 Windows 11 + Git Bash 下实测通过；纯 POSIX 路径亦可运行（未使用平台特有 API）。
- matplotlib 需中文字体（微软雅黑 / Noto Sans CJK）；缺字体时中文可能显示为方框，不影响数值。
- 脚本无硬编码的本机绝对路径（均以 `Path(__file__).parent` 定位），已通过安全扫描。
