# 未公开文件清单（excluded_files.md）

**原则**：只排除「过程产物、历史版本、缓存、敏感/未授权内容」；所有影响**结论可复核性**的文件均已保留。
**原始研究项目未被修改**，本清单仅说明 `github_release/` 为何不含某些文件。

---

## 一、过程产物与缓存（不具公开价值）

| 文件 / 目录 | 类型 | 排除原因 | 是否有替代 |
|---|---|---|---|
| `reports/pig-cycle-research/_preview/`<br>`_preview_v5/`、`_preview_v6/`、`_preview_v61/` | 截图、打印预览、Chrome user-data | 内含 `CrashpadMetrics`、`ShaderCache`、`udd_0` 等浏览器缓存，属机器本地状态 | 打印版已保留为 `report/report_print.pdf` |
| `probe*.html`、`_fig1_render.html`、`_v61_fig1_embedded.svg` | 临时校验页 | 一次性检查脚本产物 | 无（结果为 `docs/validation/` 文字记录） |
| `*.pyc`、`__pycache__/` | 编译缓存 | 无意义二进制 | 无 |
| `qt_tmp.txt`、`frontend_dev.log`、`shots/` | 临时文件、其他项目截图 | 与本报告无关 | 无 |

## 二、历史版本（避免主版本混淆）

| 文件 | 说明 | 替代 |
|---|---|---|
| `report.html`、`report_v3_backup.html` | v3 旧版 HTML（两者字节完全相同） | `report/report.html`（v6.1） |
| `report_v4_readable.html` | v4 阅读版 | 同上 |
| `report_v5_integrated.html` | v5 图表整合版 | 同上 |
| `report_v6_final.html` | v6 复审版（图 1 内嵌仍贴反） | 同上 |
| `report.md`、`report_v4.md` | v3/v4 正文源 | `report/report.md`（v6 正文） |
| `A股生猪养殖穿越周期研究_对比版_20261115.pdf` | 早期 8 页对比版 | `report/report_print.pdf` |

> 版本演进完整记录保留在 `CHANGELOG.md` 与 `docs/validation/change_log.md`，不需要靠堆叠旧文件来体现。

## 三、历史构建脚本（非当前执行入口）

| 文件 | 排除原因 |
|---|---|
| `build_report.py`、`build_report_v3.py`、`edit_report_v4.py`、`edit_report_v6.py` | v2–v4 阶段的报告生成/改稿脚本，已被 `build_html_v4.py` + `fix_v61.py` 取代 |
| `integrate_v5_charts.py`、`build_v6_final.py` | v5/v6 的图表整合与构建脚本，依赖未发布的中间文件 |
| `build_pdf_v2.py`、`report_v2.py`、`compute_v2.py`、`compute_extra.py` | v2 阶段脚本，当前评分以 v3 为准 |
| `docs` 中未列出的中间 md | 与最终报告重复或已合并 |

> 保留的 7 个脚本见 `scripts/`，职责与可运行性在 `scripts/README.md` 中逐项说明。

## 四、重复数据（去重）

| 被排除 | 原因 | 保留位置 |
|---|---|---|
| `outputs/pig_research_v4_chart_package/source/original_files/raw/*.json`（15 个，10.5 MB） | 与 `outputs/.../raw/` **完全重复** | `data/raw/`（仅一份） |
| 图表包 `source/original_files/` 内的 v3_results / v2_results / derived_metrics / research_data_v2.py / compute_v3.py | 与主数据目录重复 | `data/processed/`、`scripts/` |
| `exhibits/`（旧 PNG 目录） | 已被 `figures/` 取代 | `figures/*.png` |

## 五、敏感与未授权（安全红线）

| 类型 | 处理 |
|---|---|
| `.env` / 任何真实密钥 / Token / 私钥 | **不复制、不扫描进仓库**；`.gitignore` 已拦截 |
| 本机绝对路径（`C:\Users\...`） | 发布件中为 **0 处**（脚本统一用 `Path(__file__).parent`） |
| 券商研报原文、媒体全文、付费数据库导出 | 未收录，仅在来源登记中引用名称与链接 |
| 个人信息（邮箱、手机号、账户标识） | 扫描 0 处真实命中（272 处「手机号」为财报金额误报） |

## 六、可选精简项（非排除，供你决定）

| 项 | 体积 | 影响 |
|---|---|---|
| `data/raw/`（15 个财报 JSON） | 10.5 MB | 删除后仓库约 6.5 MB；`processed/` 与报告阅读不受影响，但无法从三表重算 |
| `figures/*.png`（10 个） | 4.0 MB | 删除后仅保留 SVG；网页与报告不受影响（报告内图为内嵌） |
| `report/report_print.pdf` | 1.19 MB | 删除后读者需自行从 HTML 打印 |

如需精简，取消 `.gitignore` 中对应注释即可。
