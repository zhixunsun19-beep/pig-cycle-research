# -*- coding: utf-8 -*-
"""替代制图工程：用 v3 模型输出与 chart_data 重建 10 张发布图（独立目录）。

说明
----
本工程**不是**原发布图的源工程（原 v5 制图工程未随仓库提供，仅有成品 SVG），
而是可维护的替代实现：数据、口径、标签与断言可核对，风格接近但不承诺像素级一致。
输出写入 `chartgen/out/`，不触碰 `figures/` 与 `report/report.html`。

用法
----
    python chartgen/build_charts.py
    python chartgen/build_charts.py --v3 data/processed/v3_results.json \
        --data data/processed/chart_data --out chartgen/out
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patches  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
FAILS: list[str] = []


def expect(cond: bool, msg: str):
    if not cond:
        FAILS.append(msg)
        print(f"[FAIL] {msg}")


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(v):
    if v in (None, "", "—", "None"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def setup_style():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                                       "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.fonttype"] = "none"      # 文字保留为文本，便于编辑
    plt.rcParams["font.size"] = 9
    plt.rcParams["axes.edgecolor"] = "#888888"
    plt.rcParams["axes.linewidth"] = 0.8


def save(fig, out: Path, name: str):
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.svg", bbox_inches="tight")
    fig.savefig(out / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# ── 图1 象限矩阵 ───────────────────────────────────────────────────────
def chart_01(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "score_quadrants.csv")
    th = v3["quadrants"]["thresholds"]
    sx, sy = th["survival_median"], th["elasticity_median"]
    expect(len(rows) == 9, f"图1 应为 9 家，实际 {len(rows)}")
    expect(len([r for r in rows if r["是否进入正式四象限"] == "是"]) == 7,
           "图1 合格企业应为 7 家")

    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    for r in rows:
        x, y = fnum(r["底部生存得分率(%)"]), fnum(r["复苏盈利弹性得分率(%)"])
        ok = r["是否进入正式四象限"] == "是"
        ax.scatter(x, y, s=46, facecolors="#1f6feb" if ok else "white",
                   edgecolors="#1f6feb", linewidths=1.2, zorder=3)
        dx, dy, ha = 5, 6, "left"
        if y > 62:                     # 顶部点标签下移，避开标题
            dx, dy = 5, -16
        if x < 20:                     # 最左侧点标签右移
            dx, dy, ha = 9, 2, "left"
        if r["公司"] == "新希望":       # 左下点标签左移，避开相邻点
            dx, dy, ha = -8, -12, "right"
        ax.annotate(f'{r["公司"]}\n{r["最终综合得分"]}', (x, y), xytext=(dx, dy),
                    textcoords="offset points", fontsize=7, ha=ha,
                    color="#222222" if ok else "#666666")
    ax.axvline(sx, ls="--", lw=0.9, color="#999999")
    ax.axhline(sy, ls="--", lw=0.9, color="#999999")
    ax.set_xlim(8, 68)
    ax.set_ylim(38, 70)
    ax.text(0.02, 0.97, "C 高风险弹性型", transform=ax.transAxes, fontsize=8, color="#666666",
            va="top")
    ax.text(0.98, 0.97, "A 穿越型", transform=ax.transAxes, fontsize=8, color="#1f6feb",
            ha="right", va="top")
    ax.text(0.02, 0.03, "D 弱势型", transform=ax.transAxes, fontsize=8, color="#666666")
    ax.text(0.98, 0.03, "B 防御型", transform=ax.transAxes, fontsize=8, color="#666666",
            ha="right")
    ax.set_xlabel("底部生存能力得分率（%）")
    ax.set_ylabel("复苏盈利弹性得分率（%）")
    ax.set_title(f"图1 企业穿越猪周期能力矩阵（阈值 {sx}% / {sy}%）")
    ax.grid(alpha=0.15)
    save(fig, out, "chart_01_quadrant_matrix")


# ── 图2 能繁母猪存栏 ───────────────────────────────────────────────────
def chart_02(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "sow_inventory.csv")
    expect(len(rows) == 5, f"图2 观测点应为 5 个，实际 {len(rows)}")
    labels = [r["报告期"] for r in rows]
    vals = [fnum(r["能繁母猪存栏(万头)"]) for r in rows]
    expect(vals[-1] == 3602, f"图2 末点应为 3602，实际 {vals[-1]}")

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(labels, vals, marker="o", color="#c0392b", lw=1.8, label="能繁母猪存栏")
    for x, y in zip(labels, vals):
        ax.annotate(str(int(y)), (x, y), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=8)
    ax.axhline(3900, ls="--", lw=0.9, color="#e67e22", label="旧正常保有量 3900")
    ax.axhline(3750, ls="--", lw=0.9, color="#27ae60", label="2026 修订 3750")
    ax.set_ylabel("能繁母猪存栏（万头）")
    ax.set_title("图2 能繁母猪存栏变化（5 个披露时点，无月度连续序列）")
    ax.legend(fontsize=7, loc="lower left")
    ax.grid(axis="y", alpha=0.15)
    save(fig, out, "chart_02_sow_inventory")


# ── 图3 完全成本 ───────────────────────────────────────────────────────
def chart_03(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "cost.csv")
    have = [r for r in rows if fnum(r["最新完全成本(元/kg)"]) is not None]
    miss = [r["公司"] for r in rows if fnum(r["最新完全成本(元/kg)"]) is None]
    expect(len(rows) == 15, f"图3 样本应为 15 家，实际 {len(rows)}")
    expect(len(have) == 12, f"图3 有成本数值应为 12 家，实际 {len(have)}")

    have.sort(key=lambda r: fnum(r["最新完全成本(元/kg)"]))
    names = [r["公司"] for r in have]
    vals = [fnum(r["最新完全成本(元/kg)"]) for r in have]
    colors = ["#1f6feb" if r["可比性分组"] == "A" else "#9aa7b8" for r in have]

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.barh(names, vals, color=colors, height=0.62)
    for i, (v, r) in enumerate(zip(vals, have)):
        ax.text(v + 0.08, i, f'{v:.2f}（{r["统计期间"]}）', va="center", fontsize=7)
    ax.axvline(8.60, ls="--", lw=1.0, color="#c0392b", label="基准猪价 8.60")
    ax.axvline(12.42, ls=":", lw=1.0, color="#7f8c8d", label="二手参考均值 12.42")
    ax.set_xlim(0, 16.2)
    ax.set_xlabel("完全成本（元/kg）")
    ax.set_title("图3 已披露完全成本（12 家；期间跨 2026-03 至 10 月）")
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2,
              frameon=False)
    ax.text(0.01, -0.26, "未核实、不展示数值：" + "、".join(miss),
            transform=ax.transAxes, fontsize=7, color="#c0392b")
    save(fig, out, "chart_03_complete_cost")


# ── 图4 出栏量 ─────────────────────────────────────────────────────────
def chart_04(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "output_volume.csv")
    expect(len(rows) == 15, f"图4 样本应为 15 家，实际 {len(rows)}")
    rows.sort(key=lambda r: -(fnum(r["2025全年实际出栏(万头)"]) or 0))
    names = [r["公司"] for r in rows]
    y25 = [fnum(r["2025全年实际出栏(万头)"]) or 0 for r in rows]
    y26 = [fnum(r["2026年化出栏(万头,估算)"]) or 0 for r in rows]
    for r, a in zip(rows, y26):
        m = fnum(r["26M1-10累计实际出栏(万头)"])
        if m:
            expect(abs(m * 1.2 - a) < 0.15, f'图4 {r["公司"]} 年化不等于 1-10 月×1.2')

    x = range(len(names))
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.bar([i - 0.2 for i in x], y25, width=0.4, color="#9ec5fe", label="2025 全年实际")
    changed = [r["2025口径"] != r["2026口径"] for r in rows]
    ax.bar([i + 0.2 for i in x], y26, width=0.4, color="#1f6feb", label="2026 年化（估算）",
           hatch=["///" if c else "" for c in changed], edgecolor="white", linewidth=0)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("出栏量（万头）")
    ax.set_title("图4 上市公司生猪出栏规模（2026 为 1-10 月线性年化）")
    ax.legend(fontsize=7)
    ax.text(0.01, -0.30, "斜线：2025/2026 统计口径不一致（含仔猪、并表或控股口径变化），不宜直接算同比",
            transform=ax.transAxes, fontsize=6.5, color="#555555")
    ax.grid(axis="y", alpha=0.15)
    save(fig, out, "chart_04_output_volume")


# ── 图5 资产负债率与现金覆盖 ───────────────────────────────────────────
def chart_05(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "financial_safety.csv")
    expect(len(rows) == 15, f"图5 样本应为 15 家，实际 {len(rows)}")
    rows.sort(key=lambda r: -(fnum(r["资产负债率(%)"]) or 0))
    names = [r["公司"] for r in rows]
    lev = [fnum(r["资产负债率(%)"]) or 0 for r in rows]
    cov = [fnum(r["现金覆盖短期有息(%)"]) for r in rows]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.2, 4.6), sharey=True)
    c1 = ["#c0392b" if v >= 75 else "#1f6feb" for v in lev]
    a1.barh(names, lev, color=c1, height=0.62)
    a1.axvline(75, ls="--", lw=1.0, color="#c0392b")
    a1.set_xlabel("资产负债率（%），75% 为报告参考线")
    a1.set_title("资产负债率")
    a1.invert_yaxis()

    cov_plot = [v if v is not None else 0 for v in cov]
    c2 = ["#c0392b" if (v is not None and v < 20) else "#1f6feb" for v in cov]
    a2.barh(names, cov_plot, color=c2, height=0.62)
    a2.axvline(150, ls="--", lw=1.0, color="#27ae60")
    a2.axvline(20, ls=":", lw=1.0, color="#c0392b")
    for i, v in enumerate(cov):
        if v is None:
            a2.text(1, i, "未取到", va="center", fontsize=6, color="#c0392b")
    a2.set_xlabel("货币资金 ÷ 短期有息（%），150% 为评分满分参考")
    a2.set_title("现金覆盖短期有息")
    fig.suptitle("图5 资产负债率与现金覆盖（2026-09-30，未扣受限资金）", fontsize=10)
    fig.tight_layout()
    save(fig, out, "chart_05_financial_safety")


# ── 图6 有息负债结构 ───────────────────────────────────────────────────
def chart_06(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "debt_and_cash.csv")
    expect(len(rows) == 15, f"图6 样本应为 15 家，实际 {len(rows)}")
    for r in rows:
        st, lt = fnum(r["短期有息负债(亿元)"]), fnum(r["长期有息负债(亿元)"])
        tot = fnum(r["有息负债合计(亿元)"])
        if None not in (st, lt, tot):
            expect(abs(st + lt - tot) < 0.03,
                   f'图6 {r["公司"]} 有息合计 ≠ 短期+长期（{st}+{lt}≠{tot}）')
    rows.sort(key=lambda r: -(fnum(r["有息负债合计(亿元)"]) or 0))
    names = [r["公司"] for r in rows]
    st = [fnum(r["短期有息负债(亿元)"]) or 0 for r in rows]
    lt = [fnum(r["长期有息负债(亿元)"]) or 0 for r in rows]
    cash = [fnum(r["货币资金(亿元)"]) or 0 for r in rows]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 4.6), sharey=True)
    a1.barh(names, st, color="#1f4e9c", label="短期有息")
    a1.barh(names, lt, left=st, color="#9ec5fe", label="长期有息")
    a1.set_xlabel("有息负债（亿元）")
    a1.set_title("有息负债结构（不含租赁负债/长期应付款）")
    a1.legend(fontsize=7)
    a1.invert_yaxis()

    a2.barh(names, cash, color="#27ae60", height=0.62)
    a2.set_xlabel("货币资金（亿元）")
    a2.set_title("账面货币资金（未扣受限资金）")
    fig.suptitle("图6 有息负债结构与货币资金（2026-09-30）", fontsize=10)
    fig.tight_layout()
    save(fig, out, "chart_06_debt_and_cash")


# ── 图7 现金跑道热力图 ─────────────────────────────────────────────────
def chart_07(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "cash_runway_scenarios.csv")
    companies = v3["meta"]["core"]
    scenarios = ["极端压力", "深度悲观", "悲观", "基准", "温和复苏", "强势复苏"]
    expect(len(rows) == len(companies) * len(scenarios),
           f"图7 应为 {len(companies)}×{len(scenarios)} 格，实际 {len(rows)}")
    grid, annot = [], []
    for c in companies:
        line, texts = [], []
        for s in scenarios:
            r = next((x for x in rows if x["代码"] == c and x["情景"] == s), None)
            v = fnum(r["现金跑道(月)"]) if r else None
            line.append(v if v is not None else math.nan)
            texts.append("无消耗" if (r and r["无净现金消耗标记"] == "是") else
                         (f"{v:.1f}" if v is not None else "—"))
        grid.append(line)
        annot.append(texts)
    # 与 v3 结果交叉核对（牧原 基准/极端）
    st = v3["stress"]["002714"]["scenarios"]
    base = next(x for x in st if x["delta"] == 0)["runway_months"]
    ext = next(x for x in st if abs(x["delta"] + 3) < 1e-9)["runway_months"]
    expect(abs(base - 149.7) < 0.15 and abs(ext - 9.2) < 0.15, "图7 牧原跑道与 v3 不一致")

    def bucket(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "#27ae60"     # 无净现金消耗
        if v < 6:
            return "#c0392b"
        if v < 18:
            return "#e67e22"
        if v < 48:
            return "#f1c40f"
        return "#a9dfbf"

    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    for i, c in enumerate(companies):
        for j, s in enumerate(scenarios):
            v = grid[i][j]
            color = bucket(v)
            ax.add_patch(patches.Rectangle((j, i), 1, 1, facecolor=color, edgecolor="white"))
            ax.text(j + 0.5, i + 0.5, annot[i][j], ha="center", va="center", fontsize=7,
                    color="#333333")
    ax.set_xlim(0, len(scenarios))
    ax.set_ylim(len(companies), 0)
    ax.set_xticks([j + 0.5 for j in range(len(scenarios))])
    ax.set_xticklabels([f"{s}" for s in scenarios], fontsize=7)
    name_map = {x["代码"]: x["公司"] for x in rows}
    ax.set_yticks([i + 0.5 for i in range(len(companies))])
    ax.set_yticklabels([name_map.get(c, c) for c in companies], fontsize=7)
    ax.set_title("图7 集团现金跑道（月）：6 情景 × 9 家核心公司")
    ax.text(0, -0.10, "红<6｜橙 6–18｜黄 18–48｜浅绿≥48｜深绿=模型下无净现金消耗；集团口径，非破产倒计时",
            transform=ax.transAxes, fontsize=6.5, color="#555555")
    save(fig, out, "chart_07_cash_runway_heatmap")


# ── 图8 猪价+1 元理论增量 ─────────────────────────────────────────────
def chart_08(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "elasticity.csv")
    expect(len(rows) == 9, f"图8 样本应为 9 家，实际 {len(rows)}")
    rows.sort(key=lambda r: -(fnum(r["猪价+1元理论贡献增量(亿元)"]) or 0))
    names = [r["公司"] for r in rows]
    inc = [fnum(r["猪价+1元理论贡献增量(亿元)"]) or 0 for r in rows]
    pct = [fnum(r["单位市值弹性(%)"]) or 0 for r in rows]
    for r in rows:
        exp = round((fnum(r["年化出栏(万头)"]) or 0) * 120 * 1.0 / 1e4, 2)
        expect(abs(exp - (fnum(r["猪价+1元理论贡献增量(亿元)"]) or 0)) < 0.06,
               f'图8 {r["公司"]} 增量公式不符')

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.2, 4.0), sharey=True)
    colors = ["#1f6feb" if r["正式排名资格"] == "具备" else "#9aa7b8" for r in rows]
    a1.barh(names, inc, color=colors, height=0.62)
    for i, v in enumerate(inc):
        a1.text(v + max(inc) * 0.01, i, f"{v:.2f}", va="center", fontsize=7)
    a1.set_xlim(0, max(inc) * 1.18)
    a1.set_xlabel("理论经营贡献增量（亿元）")
    a1.set_title("猪价 +1 元/kg")
    a1.invert_yaxis()
    a2.barh(names, pct, color=colors, height=0.62)
    for i, v in enumerate(pct):
        a2.text(v + max(pct) * 0.01, i, f"{v:.2f}%", va="center", fontsize=7)
    a2.set_xlim(0, max(pct) * 1.25)
    a2.set_xlabel("占 2026-11-13 总市值（%）")
    a2.set_title("相对市值弹性")
    fig.suptitle("图8 猪价每上涨 1 元/kg 的理论贡献（静态敏感性，非盈利预测）", fontsize=10)
    fig.tight_layout()
    save(fig, out, "chart_08_price_sensitivity")


# ── 图9 出栏+10% 损益变化 ─────────────────────────────────────────────
def chart_09(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "output_increase_10pct.csv")
    expect(len(rows) == 9, f"图9 样本应为 9 家，实际 {len(rows)}")
    rows.sort(key=lambda r: (fnum(r["出栏+10%理论损益变化(亿元)"]) or 0))
    names = [r["公司"] for r in rows]
    vals = [fnum(r["出栏+10%理论损益变化(亿元)"]) for r in rows]
    plot = [v if v is not None else 0 for v in vals]
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.barh(names, plot, color="#c0392b", height=0.6)
    lo = min([v for v in vals if v is not None] + [0])
    ax.set_xlim(lo * 1.18, 1.0)
    for i, v in enumerate(vals):
        if v is None:
            ax.text(0.5, i, "成本未披露，无法测算", va="center", fontsize=7, color="#c0392b")
        else:
            inside = abs(v) > abs(lo) * 0.25
            if inside:
                ax.text(v * 0.5, i, f"{v:.2f}", va="center", ha="center", fontsize=7,
                        color="white")
            else:
                ax.text(v - 0.25, i, f"{v:.2f}", va="center", ha="right", fontsize=7,
                        color="#333333")
    ax.axvline(0, lw=0.8, color="#333333")
    ax.set_xlabel("理论损益变化（亿元）；负值 = 亏损扩大")
    ax.set_title("图9 基准猪价 8.60 元/kg 下出栏 +10% 的理论损益变化")
    save(fig, out, "chart_09_output_increase_10pct")


# ── 图10 评分构成热力图 ───────────────────────────────────────────────
def chart_10(v3: dict, data: Path, out: Path):
    rows = load_csv(data / "score_components.csv")
    companies = v3["meta"]["core"]
    items = [("A1", 15), ("A2", 10), ("A3", 10), ("A4", 10), ("A5", 10), ("A6", 5),
             ("B1", 8), ("B2", 8), ("B3", 8), ("B4", 10), ("B5", 6)]
    expect(len(rows) == len(companies) * len(items),
           f"图10 应为 {len(companies)}×{len(items)} 条，实际 {len(rows)}")
    expect(sum(w for _, w in items) == 100, "图10 权重合计应为 100")

    idx = {(r["代码"], r["项代码"]): r for r in rows}
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    for i, c in enumerate(companies):
        for j, (code, w) in enumerate(items):
            r = idx.get((c, code))
            ok = r is not None and r["是否可得"] == "是" and fnum(r["得分"]) is not None
            ratio = (fnum(r["得分"]) / w) if ok else 0
            color = plt.cm.Blues(0.15 + 0.75 * ratio) if ok else "#eeeeee"
            ax.add_patch(patches.Rectangle((j, i), 1, 1, facecolor=color, edgecolor="white"))
            if ok:
                ax.text(j + 0.5, i + 0.5, f"{ratio*100:.0f}%", ha="center", va="center",
                        fontsize=6.5, color="#111111" if ratio < 0.6 else "white")
            else:
                ax.add_patch(patches.Rectangle((j, i), 1, 1, facecolor="none",
                                               edgecolor="#999999", hatch="///", lw=0))
                ax.text(j + 0.5, i + 0.5, "未评分", ha="center", va="center", fontsize=5.5,
                        color="#666666")
    ax.set_xlim(0, len(items))
    ax.set_ylim(len(companies), 0)
    ax.set_xticks([j + 0.5 for j in range(len(items))])
    ax.set_xticklabels([f"{c}\n{w}" for c, w in items], fontsize=7)
    ax.set_yticks([i + 0.5 for i in range(len(companies))])
    ax.set_yticklabels([next((r["公司"] for r in rows if r["代码"] == c), c) for c in companies],
                       fontsize=7)
    ax.set_title("图10 评分构成（格内为得分/权重；斜线=未评分，不按 0 分理解）")
    save(fig, out, "chart_10_score_components")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v3", default=str(REPO / "data/processed/v3_results.json"))
    ap.add_argument("--data", default=str(REPO / "data/processed/chart_data"))
    ap.add_argument("--out", default=str(REPO / "chartgen/out"))
    args = ap.parse_args()
    v3 = json.loads(Path(args.v3).read_text(encoding="utf-8"))
    data = Path(args.data)
    out = Path(args.out)
    print(f"[input] v3: {Path(args.v3).resolve()}")
    print(f"[input] chart_data: {data.resolve()}")
    print(f"[output] {out.resolve()}")

    setup_style()
    for fn in (chart_01, chart_02, chart_03, chart_04, chart_05,
               chart_06, chart_07, chart_08, chart_09, chart_10):
        fn(v3, data, out)
        print(f"[ok] {fn.__name__}")

    if FAILS:
        print(f"\n[FAIL] {len(FAILS)} 项数据断言未通过")
        for f in FAILS:
            print("  -", f)
        return 1
    print("\n[done] 10 张图已输出，全部数据断言通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
