# chartgen —— 发布图表的替代制图工程

## 这是什么，不是什么

- **是**：一个可维护、可重复执行的制图工程，读取 v3 模型结果与 `chart_data/*.csv`，
  生成与原报告同主题、同数据的 10 张 `chart_*` SVG/PNG。
- **不是**：原发布图的源工程。原 v5 制图工程未随仓库提供（仓库内只有成品 SVG、
  `chart_notes.md` 与集成脚本），因此本工程是**替代实现**，不能称为「恢复原工程」。

原成品与说明的位置（仓库外，仅本机）：`outputs/pig_research_v4_charts/`。
仓库内发布资产：`figures/chart_01..10.{svg,png}`。

## 用法

```bash
py -3.12 chartgen/build_charts.py        # 输出到 chartgen/out/
py -3.12 chartgen/verify_charts.py       # 结构/文本/数值断言
```

依赖：Python 3.12 + `matplotlib==3.11.0`；中文字体使用 `Microsoft YaHei / SimHei /
Noto Sans CJK SC` 回退。无网络依赖。

## 输入与版本

| 输入 | 版本/基准 |
|---|---|
| `data/processed/v3_results.json` | 评分 v3；财务 2026-09-30；行情 2026-11-13 |
| `data/processed/chart_data/*.csv` | 与发布报告同源导出（v3） |

构建前会断言关键不变量（公司数、阈值、公式、排序、缺失处理），任一不满足即整体失败。

## 10 张图的对应关系

见 [`chart_spec.md`](chart_spec.md)（逐图：数据文件、字段、单位、筛选、排序、阈值、注释、来源）。

## 与原发布图的差异

- **数据一致**：数值取自同一 `v3_results.json` / `chart_data`，断言覆盖关键数字。
- **视觉不同**：配色、字号、留白由本工程重排；不追求像素级复刻。
- **实现不同**：原图为外部矢量工具产出；本工程用 matplotlib 输出可编辑 SVG
  （`svg.fonttype=none`，文字保留为文本）。
- **不覆盖**：输出只在 `chartgen/out/`，不写 `figures/`，不改 `report/report.html`
  的内嵌图。

## 已实现的验收

- 10 个 SVG 均可被 XML 解析，标题与关键文本存在，无缺字占位符；
- PNG 渲染文件非空（54–138 KB）；
- 数据断言：象限 9 家/合格 7 家、末点 3602、成本 12 家有值/3 家缺、
  出栏年化 = 1–10 月 × 1.2、短期+长期=有息合计、跑道 149.7/9.2、
  +1 元增量公式、评分 9×11 且权重合计 100。

## 未完成 / 限制

- 未与原 SVG 做逐像素比对；只保证数据与关键标注一致。
- 原图特有的装饰元素（渐变、阴影、注释引线）未复刻。
- 未生成「新版报告预览」HTML；本轮不替换历史 HTML/PDF。
