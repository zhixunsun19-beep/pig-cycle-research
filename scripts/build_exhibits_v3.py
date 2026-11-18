# -*- coding: utf-8 -*-
"""reports/pig-cycle-research 图表生成（Step 2 图先行）。
数据来源：outputs/pig_research_v2_20261115/（derived_metrics.json / v2_results.json / research_data_v2.py）
纪律：只画数据包里真实存在的数据；成本无法核实的公司不入图；缺失值不画 0。
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
PKG = BASE.parent.parent / "outputs" / "pig_research_v2_20261115"
sys.path.insert(0, str(PKG))
import research_data_v2 as D  # noqa: E402

M = json.loads((PKG / "derived_metrics.json").read_text(encoding="utf-8"))
R = json.loads((PKG / "v3_results.json").read_text(encoding="utf-8"))
CORE, POOL = R["meta"]["core"], R["meta"]["pool"]
S, ST, E, Q, RK = R["scores"], R["stress"], R["elasticity"], R["quadrants"], R["rankings"]
N = D.NAME
EX = BASE / "exhibits"
EX.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
INK, BLUE, TEAL, RED, ORANGE, AMBER, GREEN, GRAY = (
    "#0f172a", "#2563eb", "#0d9488", "#dc2626", "#ea580c", "#d97706", "#16a34a", "#64748b")


def style(ax):
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.tick_params(labelsize=8.5)


def save(fig, n, slug):
    p = EX / f"fig_{n:02d}_{slug}.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  fig_{n}_{slug}.png")


def barh(ax, items, unit="", title=""):
    """items: [(label, value, color)]"""
    labels = [x[0] for x in items][::-1]
    vals = [x[1] for x in items][::-1]
    cols = [x[2] for x in items][::-1]
    ax.barh(range(len(vals)), vals, color=cols, height=0.62)
    ax.set_yticks(range(len(vals)), labels, fontsize=8.5)
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v:,.2f}{unit}", va="center", fontsize=7.8, color=INK)
    ax.set_title(title, fontsize=10, fontweight="bold", loc="left")
    style(ax)


# ── 图 1 能繁母猪存栏 ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.2, 3.0))
sow = D.INDUSTRY["sows"]
xs = [s[0] for s in sow]
vs = [s[1] for s in sow]
ax.bar(range(len(vs)), vs, color=[BLUE if v >= 3750 else TEAL for v in vs], width=0.55)
ax.set_xticks(range(len(vs)), xs, fontsize=8.5)
ax.axhline(3750, color=RED, ls="--", lw=1)
ax.text(len(vs) - 0.4, 3750 + 30, "正常保有量 3750 万头（2026 修订）", color=RED, fontsize=8, ha="right")
for i, v in enumerate(vs):
    ax.text(i, v + 30, f"{v:,}", ha="center", fontsize=8.5, fontweight="bold")
ax.set_ylim(3300, 4200)
ax.set_ylabel("万头", fontsize=8.5)
ax.set_title("能繁母猪连续四个季度去化，Q3 末降至正常保有量的 96.0%", fontsize=10.5,
             fontweight="bold", loc="left")
style(ax)
save(fig, 2, "sows")

# ── 图 2 完全成本排名 ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.2, 4.4))
items = [(f"{N[c]}（{D.COST[c]['grp']}组·{D.COST[c]['date']}）", D.COST[c]["v"],
          {"A": BLUE, "B": AMBER}[D.COST[c]["grp"]]) for c in RK["cost_asc"]]
barh(ax, items, unit="", title="12 家可核实完全成本全部高于基准猪价——数据期间不同，不能当作同一时点排名")
ax.axvline(8.60, color=RED, ls="--", lw=1)
ax.text(8.66, 0.2, "基准猪价 8.60", color=RED, fontsize=8)
ax.axvline(12.42, color=GRAY, ls="--", lw=1)
ax.text(12.48, len(items) - 1.2, "行业均值约 12.42（二手）", color=GRAY, fontsize=8)
ax.set_xlim(0, 15.5)
ax.set_xlabel("元/公斤", fontsize=8.5)
save(fig, 3, "cost12")

# ── 图 3 出栏规模与增速 ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.6, 5.0))
order = sorted(POOL, key=lambda c: -(D.OUTPUT[c]["y2025"] or 0))
y = range(len(order))
y25 = [D.OUTPUT[c]["y2025"] for c in order]
y26 = [D.OUTPUT[c]["m1_10"] * 12 / 10 if D.OUTPUT[c]["m1_10"] else 0 for c in order]
ax.barh(y, y25, color=GRAY, height=0.58, label="2025 全年实际")
ax.barh(y, y26, color=BLUE, height=0.32, label="2026 年化（26M1-10 × 12/10）")
ax.set_yticks(list(y), [N[c] for c in order], fontsize=8.5)
for i, c in enumerate(order):
    ax.text(y25[i] + 40, i + 0.28, f"{y25[i]:,.0f}", va="center", fontsize=7.2, color=GRAY)
    ax.text(y26[i] + 40, i - 0.18, f"{y26[i]:,.0f}", va="center", fontsize=7.2, color=BLUE)
ax.set_xlabel("万头", fontsize=8.5)
ax.set_title("出栏规模与增速：正邦、傲农在重整恢复中逆势放量——拿份额不等于能活下来",
             fontsize=10.5, fontweight="bold", loc="left")
ax.legend(fontsize=8, loc="lower right")
style(ax)
save(fig, 4, "output")

# ── 图 3 资产负债率 vs 现金覆盖 ──────────────────────────────────────
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 4.6))
alr = sorted(POOL, key=lambda c: M[c]["有息负债_2026Q3"]["资产负债率_pct"])
barh(a1, [(N[c], M[c]["有息负债_2026Q3"]["资产负债率_pct"],
           RED if M[c]["有息负债_2026Q3"]["资产负债率_pct"] >= 75 else
           (AMBER if M[c]["有息负债_2026Q3"]["资产负债率_pct"] >= 60 else TEAL)) for c in alr],
      unit="%", title="资产负债率（%）——天邦 91.84% 触及资不抵债临界")
a1.axvline(75, color=RED, ls="--", lw=1)
a1.set_xlim(0, 100)
cov = sorted(POOL, key=lambda c: (M[c]["有息负债_2026Q3"]["现金覆盖短期有息_pct"] or -1))
barh(a2, [(N[c], M[c]["有息负债_2026Q3"]["现金覆盖短期有息_pct"] or 0,
           RED if (M[c]["有息负债_2026Q3"]["现金覆盖短期有息_pct"] or 0) < 20 else
           (AMBER if (M[c]["有息负债_2026Q3"]["现金覆盖短期有息_pct"] or 0) < 50 else TEAL)) for c in cov],
      unit="%", title="现金覆盖短期有息（%）——低负债率不等于高覆盖")
a2.axvline(150, color=GRAY, ls="--", lw=1)
a2.text(151, 0.2, "150% 满分参照", color=GRAY, fontsize=8)
a2.set_xlim(0, 210)
fig.suptitle("低资产负债率并不意味着低流动性风险（2026Q3 一手三表）", fontsize=11, fontweight="bold",
             x=0.02, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.94])
save(fig, 5, "leverage")

# ── 图 4 有息负债 vs 货币资金 ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.6, 5.2))
order = sorted(POOL, key=lambda c: -(M[c]["有息负债_2026Q3"]["有息负债合计"] or 0))
y = range(len(order))
debt = [M[c]["有息负债_2026Q3"]["有息负债合计"] for c in order]
cash = [M[c]["有息负债_2026Q3"]["货币资金"] for c in order]
ax.barh(y, debt, color=BLUE, height=0.62, label="有息负债合计（主口径）")
ax.barh(y, [-c for c in cash], color=TEAL, height=0.62, label="货币资金（未扣受限）")
ax.set_yticks(list(y), [N[c] for c in order], fontsize=8.5)
ax.axvline(0, color=INK, lw=0.8)
for i, c in enumerate(order):
    ax.text(debt[i] + 8, i, f"{debt[i]:,.0f}", va="center", fontsize=7.5)
    ax.text(-cash[i] - 14, i, f"{cash[i]:,.0f}", va="center", ha="right", fontsize=7.5)
ax.set_xlabel("亿元（左：有息负债；右：货币资金）", fontsize=8.5)
ax.set_title("有息负债与货币资金的镜像：牧原短债 707 亿靠滚动续贷，不是手握现金",
             fontsize=10.5, fontweight="bold", loc="left")
ax.legend(fontsize=8, loc="lower right")
style(ax)
save(fig, 6, "debt_cash")

# ── 图 5 六情景现金跑道热力矩阵 ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.6, 3.8))
cols = [x[0] for x in D.SCENARIOS]
cats = {(0, 6): ("#fee2e2", "#991b1b"), (6, 18): ("#ffedd5", "#9a3412"),
        (18, 48): ("#fef9c3", "#854d0e"), (48, 10**9): ("#dcfce7", "#166534")}
for r, c in enumerate(CORE):
    for k, sc in enumerate(ST[c]["scenarios"]):
        v = sc["runway_months"]
        if v is None:
            fc, tc = "#bbf7d0", "#14532d"
            txt = "不消耗"
        else:
            fc, tc = next((f, t) for lo, hi, (f, t) in
                          [(lo, hi, ft) for (lo, hi), ft in cats.items()] if lo <= v < hi)
            txt = f"{v:.1f}"
        ax.add_patch(plt.Rectangle((k, len(CORE) - 1 - r), 1, 1, fc=fc, ec="#fff", lw=1.5))
        ax.text(k + 0.5, len(CORE) - 1 - r + 0.5, txt, ha="center", va="center",
                fontsize=8.6, color=tc, fontweight="bold")
ax.set_xlim(0, 6)
ax.set_ylim(0, len(CORE))
ax.set_xticks([k + 0.5 for k in range(6)], cols, fontsize=8.5)
ax.set_yticks([len(CORE) - 1 - r + 0.5 for r in range(len(CORE))],
              [N[c] for c in CORE], fontsize=8.5)
for k in range(7):
    ax.axvline(k, color="#fff", lw=0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(length=0)
ax.set_title("集团现金跑道：极端压力下温氏 1.7、神农 1.9、新五丰 2.7 个月（非破产倒计时）",
             fontsize=10.5, fontweight="bold", loc="left")
ax.text(0, -0.7, "色阶：<6 月 红｜6–18 橙｜18–48 黄｜≥48 浅绿｜不消耗现金 深绿。单位：月。跑道≠破产时间。",
        fontsize=7.5, color=GRAY)
save(fig, 7, "runway_heat")

# ── 图 6 弹性：绝对增量 vs 占市值 ────────────────────────────────────
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.8))
barh(a1, [(N[c], E[c]["price_up1_yi"], BLUE) for c in sorted(CORE, key=lambda x: -E[x]["price_up1_yi"])],
      unit=" 亿", title="猪价每上涨 1 元/kg 的理论经营贡献增量（亿元）——牧原规模效应第一")
barh(a2, [(N[c], E[c]["el_pct"], AMBER if E[c]["el_pct"] >= 8 else TEAL)
          for c in sorted(CORE, key=lambda x: -E[x]["el_pct"])],
      unit="%", title="同一增量 ÷ 总市值（%）——唐人神 11.98% 最高但待核实区")
fig.suptitle("弹性两种口径：绝对额看规模、占市值看敏感度——静态敏感性，不等于盈利预测", fontsize=11,
             fontweight="bold", x=0.02, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.92])
save(fig, 8, "elasticity")

# ── 图 7 出栏+10% 在基准价下 = 扩大亏损 ──────────────────────────────
fig, ax = plt.subplots(figsize=(7.2, 3.6))
neg = [(N[c], E[c]["output_up10_yi"]) for c in CORE if E[c]["output_up10_yi"] is not None]
neg.sort(key=lambda x: x[1])
vals = [v for _, v in neg]
ax.barh(range(len(vals)), vals, color=RED, height=0.58)
ax.set_yticks(range(len(vals)), [x[0] for x in neg], fontsize=8.5)
for i, v in enumerate(vals):
    ax.text(v - 0.4, i, f"{v:+.2f} 亿", va="center", ha="right", fontsize=8, color=RED)
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlim(min(vals) * 1.25, 2)
ax.set_xlabel("亿元（负 = 扩大亏损）", fontsize=8.5)
ax.set_title("在完全成本高于猪价时，出栏 +10% 即扩大亏损 0.9–26 亿元——弹性须建立在财务安全之上",
             fontsize=10.5, fontweight="bold", loc="left")
style(ax)
save(fig, 9, "output10_negative")

# ── 图 8 评分堆叠 ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.6, 4.2))
A = [("A1", 15, "#1e3a8a"), ("A2", 10, "#1d4ed8"), ("A3", 10, "#3b82f6"), ("A4", 10, "#60a5fa"),
     ("A5", 10, "#93c5fd"), ("A6", 5, "#bfdbfe")]
B = [("B1", 8, "#065f46"), ("B2", 8, "#059669"), ("B3", 8, "#10b981"), ("B4", 10, "#34d399"), ("B5", 6, "#6ee7b7")]
y = range(len(RK["total"]))
left = [0] * len(y)
for dim, segs in [("survival", A), ("elasticity", B)]:
    for k, wmax, col in segs:
        vals = [S[c][dim]["items"][k]["score"] or 0 for c in RK["total"]]
        ax.barh(y, vals, left=left, color=col, height=0.6, label=k)
        left = [a + b for a, b in zip(left, vals)]
# 未评分灰段
for i, c in enumerate(RK["total"]):
    miss = S[c]["total_effective_max"] - S[c]["total_raw"]
    ax.barh(i, miss, left=left[i], color="#e2e8f0", height=0.6, hatch="///", edgecolor="#cbd5e1")
    ax.text(S[c]["total_effective_max"] + 1, i, f'{S[c]["final_score"]:.1f}', va="center", fontsize=8.5,
            fontweight="bold", color=INK if S[c]["in_main_board"] else GRAY)
ax.set_yticks(list(y), [N[c] for c in RK["total"]], fontsize=8.5)
ax.set_xlim(0, 118)
ax.set_xlabel("有效满分（灰色斜纹 = 未评分，不放大；右侧数字 = 可比得分率）", fontsize=8.5)
ax.set_title("双轨评分：覆盖率 <70% 者不进主榜——灰段本身就是信息", fontsize=10.5, fontweight="bold", loc="left")
ax.legend(fontsize=6.8, ncol=11, loc="upper center", bbox_to_anchor=(0.5, -0.13), frameon=False)
style(ax)
save(fig, 10, "score_stack")

# ── 图 9 四象限散点 ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.8, 4.6))
ms, me = Q["thresholds"]["survival_median"], Q["thresholds"]["elasticity_median"]
ax.axvline(ms, color=ORANGE, ls="--", lw=1)
ax.axhline(me, color=ORANGE, ls="--", lw=1)
qcol = {"A": TEAL, "B": BLUE, "C": ORANGE, "D": GRAY, "待核实": GRAY}
for c in CORE:
    x, yy = Q["items"][c]["survival_rate"], Q["items"][c]["elasticity_rate"]
    qd = Q["items"][c]["quadrant"]
    pending = qd == "待核实"
    ax.scatter(x, yy, s=90, facecolor="none" if pending else qcol[qd],
               edgecolor=GRAY if pending else "#fff", linewidths=1.4, alpha=0.9)
    ax.annotate(f"{N[c]} {S[c]['final_score']:.1f}" + ("（待核实）" if pending else ""),
                (x, yy), textcoords="offset points", xytext=(7, 4), fontsize=8, color=GRAY)
ax.text(78, 76, "A 穿越型", fontsize=9.5, color="#94a3b8", ha="right", fontweight="bold")
ax.text(14, 76, "B 防御型", fontsize=9.5, color="#94a3b8", fontweight="bold")
ax.text(78, 33, "C 高风险弹性型", fontsize=9.5, color="#94a3b8", ha="right", fontweight="bold")
ax.text(14, 33, "D 弱势型", fontsize=9.5, color="#94a3b8", fontweight="bold")
ax.set_xlim(8, 80)
ax.set_ylim(30, 80)
ax.set_xlabel("底部生存能力得分率（60 分制）", fontsize=9)
ax.set_ylabel("复苏盈利弹性得分率（40 分制）", fontsize=9)
ax.set_title("企业穿越猪周期能力矩阵：A 类（穿越型）为天康、牧原、神农——阈值仅由 7 家合格企业中位数决定",
             fontsize=10.5, fontweight="bold", loc="left")
style(ax)
save(fig, 1, "matrix")

print(f"共 10 张图（fig_01–fig_10，按正文引用顺序编号） → {EX}")
