# -*- coding: utf-8 -*-
"""v3 计算引擎（A2 去重计分 + 合格口径四象限）：可得性矩阵 → 60/40 双轨评分 → 6 情景压力测试 → 弹性 → 四象限。
所有数字从 derived_metrics.json（一手三表）与 research_data_v2.py 取，不手写、不填补。
相对 v2 的两处模型修订：
① A2 改为「现金成本竞争力」：仅当公司以一手口径披露现金成本时评分，缺失一律未评分——
   修复 v2 中 A2=完全成本−基准猪价 与 A1 同源导致的重复计分；
② 正式四象限的中位数阈值仅用覆盖率≥70% 且未触发风险上限的企业计算，
   待核实区企业不参与阈值、不获得正式象限标签。
输出 v3_results.json；v2_results.json 原样保留供新旧对比。
"""
import json
import re
import statistics
from pathlib import Path

import research_data_v2 as D

BASE = Path(__file__).resolve().parent
M = json.loads((BASE / "derived_metrics.json").read_text(encoding="utf-8"))

CORE = [c for c, _ in D.CORE]
POOL = [c for c, _ in D.POOL]
W = D.BENCH["weight_kg"]
P0 = D.BENCH["base"]


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def g(d, k, default=None):
    v = d.get(k)
    return v if v is not None else default


def first_num(s):
    if not isinstance(s, str):
        return None
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_eff(code):
    e = D.EFFICIENCY.get(code)
    if not e:
        return {}
    out = {}
    out["psy"] = first_num(e.get("psy"))
    out["fcr"] = e.get("fcr") if isinstance(e.get("fcr"), (int, float)) else None
    out["survival"] = first_num(e.get("survival"))
    out["mode"] = e.get("mode")
    out["driver"] = e.get("driver")
    return out


# ── 可得性矩阵 ───────────────────────────────────────────────────────
AVAIL_ITEMS = [
    ("完全成本", "COST", "成本表（互动平台/调研纪要/媒体）"),
    ("现金成本", "CASH_COST", "公司披露或调研纪要"),
    ("实际出栏量", "OUTPUT", "公司月度销售简报/第三方库"),
    ("分业务拆分", "SEGMENTS", "半年报分部/调研纪要"),
    ("PSY/料肉比/成活率", "EFFICIENCY", "调研纪要（多为片段）"),
    ("2027逐笔到期债务", "DEBT_2027", "可转债募集说明书/财报附注"),
    ("估值 PE/PB/总市值", "VALUATION", "腾讯行情 2026-11-13 收盘"),
    ("PS-TTM/EV-EBITDA", "VALUATION_PS", "未取到（接口与附注均不提供）"),
    ("机构盈利预测", "FORECASTS", "券商研报（预测，非实际）"),
    ("管理层经营质量证据", "MANAGEMENT", "公告/调研/研报"),
    ("三表主表（15家全覆盖）", "FIN", "新浪财经原始财报三表 2026-09-30"),
    ("受限货币资金", "RESTRICTED", "未取到（属财报附注）"),
    ("折旧摊销/EBITDA", "DA", "未取到（现金流量表无补充资料）"),
]


def availability():
    out = {}
    for code in POOL:
        cost = D.COST.get(code, {})
        rows = []
        rows.append(("完全成本", "可核实" if cost.get("v") is not None else "未披露",
                     cost.get("level", ""), cost.get("grp", ""), cost.get("date", "")))
        rows.append(("现金成本", "可核实" if code in D.CASH_COST else "未披露",
                     D.CASH_COST.get(code, {}).get("level", ""), "口径不一", ""))
        rows.append(("实际出栏量", "可核实", D.OUTPUT[code]["level"], "", ""))
        rows.append(("分业务拆分", "可核实" if code in D.SEGMENTS else "不适用/未取到",
                     D.SEGMENTS.get(code, {}).get("level", ""), "", ""))
        eff = parse_eff(code)
        n_eff = sum(1 for k in ["psy", "fcr", "survival"] if eff.get(k) is not None)
        rows.append(("PSY/料肉比/成活率", f"部分可核实({n_eff}/3)" if n_eff else "未披露", "", "", ""))
        rows.append(("2027逐笔到期债务", "可核实" if code in D.DEBT_2027 else "无法核实", "", "", ""))
        rows.append(("估值 PE/PB/总市值", "可核实", "行情接口", "", D.PRICE_DATE))
        rows.append(("PS-TTM/EV-EBITDA", "无法核实", "", "", ""))
        rows.append(("机构盈利预测", "可核实" if code in D.FORECASTS else "未取到", "预测·非一手", "", ""))
        rows.append(("管理层经营质量证据", "可核实" if code in D.MANAGEMENT else "未取到", "定性", "", ""))
        rows.append(("三表主表", "可核实", "一手", "", D.REPORT_PERIOD))
        rows.append(("受限货币资金", "无法核实", "", "", ""))
        rows.append(("折旧摊销/EBITDA", "无法核实", "", "", ""))
        out[code] = rows
    return out


# ── 60/40 评分 ──────────────────────────────────────────────────────
A_ITEMS = [("A1", "长期完全成本竞争力", 15), ("A2", "现金成本与盈亏平衡能力", 10),
           ("A3", "有息负债及债务结构", 10), ("A4", "现金储备和短期偿债能力", 10),
           ("A5", "经营现金流和自由现金流", 10), ("A6", "2027年及以后债务压力", 5)]
B_ITEMS = [("B1", "PSY、MSY及生产效率", 8), ("B2", "现有产能和未来出栏兑现能力", 8),
           ("B3", "单位成本下降空间", 8), ("B4", "猪价上涨后的利润弹性", 10),
           ("B5", "管理能力与经营质量", 6)]


def score_one(code, key, w):
    """返回 (score|None, evidence, level, confidence)"""
    d = M[code]
    debt = d["有息负债_2026Q3"]
    bs = d["资产负债表"]
    cf = d["现金流"]
    cost = D.COST.get(code, {}).get("v")
    ta = g(bs, "总资产")
    cash = g(debt, "货币资金")

    if key == "A1":
        if cost is None:
            return None, "完全成本未披露/口径冲突无法消解，不参与排名；成本仅管理层目标或同比幅度", "缺失", "低"
        s = clamp((14.0 - cost) / (14.0 - 11.2) * 15, 0, 15)
        c = D.COST[code]
        return round(s, 2), (f"完全成本 {cost} 元/kg（{c['date']}，{c['level']}，{c['grp']}组），"
                             f"线性映射 (14.0−成本)/(14.0−11.2)×15；口径：{c['cal']}"), c["level"], "高" if c["level"] == "一手" else "中"

    if key == "A2":
        cc = D.CASH_COST.get(code)
        if cc is None:
            return None, ("现金成本未披露。注：卖一头猪的账面亏损（A1 完全成本口径）与实际现金消耗（A2 现金成本口径）"
                          "是两个不同问题，v2 曾用完全成本重复代理两者，本版已修复——现金成本缺失不默认获得高分，标记未评分"), "缺失", "低"
        if cc["level"] != "一手":
            return None, (f"现金成本仅有{cc['level']}口径读数（{cc['v']} 元/kg，{cc['cal']}），未经公司正式披露核实，"
                          f"不参与评分，数值在第 4/6 章单列展示"), "缺失", "低"
        gap = cc["v"] - P0
        s = clamp((5.5 - gap) / 3.0 * 10, 0, 10)
        return round(s, 2), (f"现金成本 {cc['v']} 元/kg（{cc['date']}，{cc['level']}，{cc['cal']}）− 基准猪价 {P0} = "
                             f"现金缺口 {gap:.2f} 元/kg，映射 (5.5−缺口)/3.0×10"), cc["level"], "中"

    if key == "A3":
        ar = g(debt, "资产负债率_pct")
        net = g(debt, "净有息负债")
        nr = (net / ta) if (net is not None and ta) else None
        f1 = clamp((85 - ar) / 40) if ar is not None else 0
        f2 = clamp((0.40 - nr) / 0.35) if nr is not None else 0
        s = 10 * (0.5 * f1 + 0.5 * f2)
        return round(s, 2), (f"资产负债率 {ar}%（一手三表）、净有息/总资产 {nr*100:.2f}%（自行测算）；"
                             f"f1=(85−负债率)/40、f2=(0.40−净有息率)/0.35，各占50%"), "一手+测算", "高"

    if key == "A4":
        cov = g(debt, "现金覆盖短期有息_pct")
        cr = g(debt, "流动比率")
        f1 = clamp(cov / 150) if cov is not None else 0
        f2 = clamp((cr - 0.5) / 1.0) if cr is not None else 0
        s = 10 * (0.7 * f1 + 0.3 * f2)
        return round(s, 2), (f"现金覆盖短期有息 {cov}%、流动比率 {cr}（一手三表）；"
                             f"f1=覆盖/150、f2=(流动比率−0.5)，权重70/30。"
                             f"⚠️现金未扣受限资金（附注未取到），属偏乐观口径"), "一手", "中"

    if key == "A5":
        ocf = g(cf, "前三季度经营_亿元")
        fcf = g(cf, "自由现金流_亿元")
        r1 = (ocf / ta) if (ocf is not None and ta) else None
        r2 = (fcf / ta) if (fcf is not None and ta) else None
        f1 = clamp((r1 + 0.05) / 0.10) if r1 is not None else 0
        f2 = clamp((r2 + 0.05) / 0.10) if r2 is not None else 0
        s = 10 * (0.6 * f1 + 0.4 * f2)
        return round(s, 2), (f"前三季度经营现金流 {ocf} 亿（/总资产 {r1*100:.2f}%）、自由现金流 {fcf} 亿（{r2*100:.2f}%）；"
                             f"映射 (r+0.05)/0.10，权重60/40。自由现金流=经营现金流−资本开支"), "一手+测算", "高"

    if key == "A6":
        if code in D.DEBT_2027:
            principal = sum(i["principal"] for i in D.DEBT_2027[code]["items"])
            ratio = principal / cash if cash else None
            s = 5 * clamp(1 - ratio / 4) if ratio is not None else 0
            det = "；".join(f"{i['name']} {i['due']} {i['principal']}亿" for i in D.DEBT_2027[code]["items"])
            return round(s, 2), (f"可核实到期：{det}；合计 {principal} 亿 / 货币资金 {cash} 亿 = {ratio:.2f}×，"
                                 f"映射 5×(1−倍数/4)"), "一手", "高"
        cov = g(debt, "现金覆盖短期有息_pct")
        proxy = clamp(cov / 150) if cov is not None else 0
        s = 5 * proxy * 0.6
        return round(s, 2), (f"2027 逐笔到期本金/利息【无法核实】（附注仅按 1年内/1-2年/2-5年 分桶，贷款可续贷）。"
                             f"改用代理：现金覆盖短期有息 {cov}%/150 × 5 × 0.6（打6折，不默认优秀）。"
                             f"⚠️不能替代到期结构分析"), "代理", "低"

    if key == "B1":
        e = parse_eff(code)
        parts, ev = [], []
        if e.get("psy") is not None:
            parts.append(clamp((e["psy"] - 24) / 8)); ev.append(f"PSY {e['psy']}")
        if e.get("fcr") is not None:
            parts.append(clamp((2.9 - e["fcr"]) / 0.5)); ev.append(f"料肉比 {e['fcr']}")
        if e.get("survival") is not None:
            parts.append(clamp((e["survival"] - 80) / 13)); ev.append(f"成活率 {e['survival']}%")
        if not parts:
            return None, "PSY/MSY/料肉比/成活率 均无公司级可核实数值（未披露或仅为管理层目标）", "缺失", "低"
        s = 8 * sum(parts) / len(parts)
        return round(s, 2), (f"可核实子项 {len(parts)}/3：{'、'.join(ev)}；各子项标准化后等权平均×8。"
                             f"PSY 目标值（如傲农28.5、巨星长期33）不参与打分"), "片段", "中"

    if key == "B2":
        bio0 = g(d, "生产性生物资产_2025年末_亿元")
        bio1 = g(d, "生产性生物资产_2026Q3_亿元")
        o = D.OUTPUT[code]
        annual = o["m1_10"] * 12 / 10 if o["m1_10"] else None
        r1 = (bio1 / bio0) if (bio0 and bio1 is not None) else None
        r2 = (annual / o["y2025"]) if (annual and o["y2025"]) else None
        f1 = clamp((r1 - 0.6) / 0.5) if r1 is not None else 0
        f2 = clamp((r2 - 0.7) / 0.5) if r2 is not None else 0
        s = 8 * (0.5 * f1 + 0.5 * f2)
        return round(s, 2), (f"生产性生物资产 {bio0}→{bio1} 亿（比值 {r1:.2f}，代理能繁母猪产能保全）；"
                             f"26M1-10 累计 {o['m1_10']} 万头线性年化 {annual:.1f} 万头 / 2025 全年 {o['y2025']} 万头 = {r2:.2f}。"
                             f"⚠️口径：{o.get('note','') or '无'}"), "一手+测算", "中"

    if key == "B3":
        if cost is None:
            return None, "完全成本缺失，无法计算剩余下降空间", "缺失", "低"
        drop = D.COST_DROP.get(code, {}).get("v")
        f2 = clamp((cost - 11.0) / 3.0)
        if drop is None:
            s = 8 * (0.6 * 0.0 + 0.4 * f2)
            ev = (f"已验证年内降本【无法核实】（{D.COST_DROP.get(code,{}).get('basis','无连续读数')}）；"
                  f"理论剩余空间 (成本−11.0)/3.0={f2:.2f}。仅40%权重可评，置信度低")
            conf = "低"
        else:
            f1 = clamp(drop / 1.0)
            s = 8 * (0.6 * f1 + 0.4 * f2)
            ev = (f"已验证降本 {drop} 元/kg（{D.COST_DROP[code]['basis']}）→f1={f1:.2f}；"
                  f"理论剩余空间 (成本−11.0)/3.0={f2:.2f}→f2。权重60/40。"
                  f"⚠️剩余空间为理论值，不等于兑现能力；成本高的企业此项反而高")
            conf = "中"
        return round(s, 2), ev, "片段+测算", conf

    if key == "B4":
        o = D.OUTPUT[code]
        annual = o["m1_10"] * 12 / 10 if o["m1_10"] else None
        delta_yi = annual * W / 1e4 if annual else None   # 猪价+1元/kg 的利润增量(亿元)
        mcap = D.VALUATION[code]["mcap"]
        el_pct = delta_yi / mcap * 100 if delta_yi is not None else None
        s = 10 * clamp(el_pct / 12) if el_pct is not None else 0
        return round(s, 2), (f"猪价+1元/kg → 利润增量 {delta_yi:.2f} 亿元（年化出栏 {annual:.1f} 万头 × {W}kg × 1元）；"
                             f"/总市值 {mcap} 亿 = {el_pct:.2f}%，映射 弹性%/12 × 10。"
                             f"⚠️弹性按单位市值标准化，小市值+高出栏者天然更高，不代表生存能力"), "测算", "中"

    if key == "B5":
        m = D.MANAGEMENT.get(code)
        if not m:
            return None, "管理层经营质量证据未取到（风险观察池不单独评分）", "缺失", "低"
        return m["score"], f"定性评分（满分6），依据：{m['text']}", "定性", "中"

    raise KeyError(key)


def score_all():
    out = {}
    for code in CORE:
        rec = {"A": {}, "B": {}}
        for dim, items, letter in [("survival", A_ITEMS, "A"), ("elasticity", B_ITEMS, "B")]:
            raw, eff_max, details = 0.0, 0.0, {}
            for key, label, w in items:
                s, ev, level, conf = score_one(code, key, w)
                details[key] = dict(label=label, weight=w, score=s, evidence=ev,
                                    level=level, confidence=conf, available=s is not None)
                if s is not None:
                    raw += s; eff_max += w
            rec[dim] = dict(items=details, raw=round(raw, 2), effective_max=round(eff_max, 2),
                            rate=round(raw / eff_max * 100, 2) if eff_max else None,
                            coverage=round(eff_max / (60 if dim == "survival" else 40) * 100, 2))
        total_raw = rec["survival"]["raw"] + rec["elasticity"]["raw"]
        total_max = rec["survival"]["effective_max"] + rec["elasticity"]["effective_max"]
        rec["total_raw"] = round(total_raw, 2)
        rec["total_effective_max"] = round(total_max, 2)
        rec["coverage_pct"] = round(total_max, 2)
        rec["comparable_score"] = round(total_raw / total_max * 100, 2) if total_max else None
        rec["confidence"] = ("高" if rec["coverage_pct"] >= 85 else
                             "中" if rec["coverage_pct"] >= 70 else "低")
        cap = D.RISK_CAP.get(code)
        rec["cap"] = cap
        rec["final_score"] = min(rec["comparable_score"], cap["cap"]) if cap else rec["comparable_score"]
        rec["in_main_board"] = (rec["coverage_pct"] >= 70 and cap is None)
        out[code] = rec
    return out


# ── 6 情景压力测试（9 家核心，统一假设）────────────────────────────────
def stress_one(code, delta, cost):
    """以实际披露的前三季度经营现金流年化为基准，只叠加猪价变动的增量现金流。
    严禁用账面净利润当现金消耗代理：9M2026 牧原经营现金流 +29.83 亿但归母 −93.19 亿，
    差额主要是折旧等非现金项；用净利润会严重高估现金消耗。
    """
    d = M[code]
    debt = d["有息负债_2026Q3"]
    cf = d["现金流"]
    o = D.OUTPUT[code]
    annual = o["m1_10"] * 12 / 10 if o["m1_10"] else None
    price = P0 + delta
    # 利润水平值需要完全成本；成本缺失则一律标 None，不用行业均值代填。
    unit = (price - cost) if cost is not None else None
    per_head = (unit * W) if unit is not None else None
    profit = (per_head * annual / 1e4) if (per_head is not None and annual) else None
    # 增量现金流 = Δ猪价 × 出栏量 × 均重，不依赖成本水平，故成本缺失公司仍可做情景测算。
    delta_yi = delta * W * annual / 1e4 if annual else None
    ocf9 = g(cf, "前三季度经营_亿元")
    ocf_annual = ocf9 * 4 / 3 if ocf9 is not None else None     # 年化（简化，忽略季节性）
    ocf_scen = (ocf_annual + delta_yi) if (ocf_annual is not None and delta_yi is not None) else None
    capex9 = g(cf, "资本开支_亿元")
    capex_annual = capex9 * 4 / 3 if capex9 is not None else None
    maint = capex_annual * 0.5 if capex_annual is not None else None  # 假设50%为维持性、扩产部分在压力下可暂停
    fcf_scen = (ocf_scen - maint) if (ocf_scen is not None and maint is not None) else None
    burn = max(0.0, -fcf_scen) if fcf_scen is not None else 0.0
    monthly = burn / 12
    cash = g(debt, "货币资金")
    runway = (cash / monthly) if monthly > 0.001 else None
    known = code in D.DEBT_2027
    principal = sum(i["principal"] for i in D.DEBT_2027[code]["items"]) if known else None
    gap = (max(0.0, principal - (cash or 0) - max(0.0, ocf_scen or 0)) if known else None)
    return dict(name=[s[0] for s in D.SCENARIOS if s[1] == delta][0], delta=delta,
                price=round(price, 2), unit_margin=(round(unit, 2) if unit is not None else None),
                per_head=(round(per_head, 0) if per_head is not None else None),
                annual_profit_yi=(round(profit, 2) if profit is not None else None),
                delta_vs_base_yi=round(delta_yi, 2) if delta_yi is not None else None,
                ocf_annual_yi=round(ocf_annual, 2) if ocf_annual is not None else None,
                ocf_scen_yi=round(ocf_scen, 2) if ocf_scen is not None else None,
                maint_capex_yi=round(maint, 2) if maint is not None else None,
                fcf_scen_yi=round(fcf_scen, 2) if fcf_scen is not None else None,
                monthly_burn_yi=round(monthly, 2), runway_months=(round(runway, 1) if runway is not None else None),
                debt_gap_yi=round(gap, 2) if gap is not None else None)


def stress_all():
    out = {}
    for code in CORE:
        cost = D.COST.get(code, {}).get("v")
        d = M[code]
        o = D.OUTPUT[code]
        annual = o["m1_10"] * 12 / 10 if o["m1_10"] else None
        out[code] = dict(
            available=cost is not None,
            reason=("完全成本未披露/口径冲突无法消解：养殖板块利润水平值不测算、不用行业均值代填；"
                    "但猪价变动的增量现金流 = ΔP × 出栏量 × 均重，与成本水平无关，故 6 情景现金流与现金跑道仍可测算"
                    if cost is None else ""),
            cost=cost, cost_level=(D.COST[code]["level"] if cost is not None else "缺失"),
            cost_group=(D.COST[code]["grp"] if cost is not None else "C"),
            annual_heads_wan=round(annual, 1) if annual else None,
            annual_basis=f"26M1-10 累计 {o['m1_10']} 万头 × 12/10 线性年化；口径：{o['cal26']}",
            cash=g(d["有息负债_2026Q3"], "货币资金"),
            capex_9m=g(d["现金流"], "资本开支_亿元"),
            ocf_9m=g(d["现金流"], "前三季度经营_亿元"),
            debt_2027_known=code in D.DEBT_2027,
            scenarios=[stress_one(code, delta, cost) for _, delta in D.SCENARIOS])
    return out


# ── 复苏弹性测算 ─────────────────────────────────────────────────────
def elasticity_all():
    out = {}
    for code in CORE:
        o = D.OUTPUT[code]
        annual = o["m1_10"] * 12 / 10 if o["m1_10"] else None
        cost = D.COST.get(code, {}).get("v")
        mcap = D.VALUATION[code]["mcap"]
        e1 = 1 * W * annual / 1e4 if annual else None
        e2 = 2 * W * annual / 1e4 if annual else None
        c1 = 1 * W * annual / 1e4 if annual else None
        grow10 = 0.1 * (P0 - cost) * W * annual / 1e4 if (annual and cost is not None) else None
        corn10 = cost * D.BENCH["feed_share"] * 0.65 * 0.10 if cost is not None else None
        meal10 = cost * D.BENCH["feed_share"] * 0.125 * 0.10 if cost is not None else None
        corn_profit = -corn10 * W * annual / 1e4 if (corn10 is not None and annual) else None
        meal_profit = -meal10 * W * annual / 1e4 if (meal10 is not None and annual) else None
        psy = parse_eff(code).get("psy")
        psy1_cost = -(cost * 0.22 / psy) if (cost is not None and psy) else None
        psy1_profit = -psy1_cost * W * annual / 1e4 if (psy1_cost is not None and annual) else None
        out[code] = dict(annual_heads_wan=round(annual, 1) if annual else None,
                         price_up1_yi=round(e1, 2) if e1 else None,
                         price_up2_yi=round(e2, 2) if e2 else None,
                         cost_down1_yi=round(c1, 2) if c1 else None,
                         output_up10_yi=round(grow10, 2) if grow10 is not None else None,
                         corn_up10_cost=round(corn10, 3) if corn10 is not None else None,
                         corn_up10_profit_yi=round(corn_profit, 2) if corn_profit is not None else None,
                         meal_up10_cost=round(meal10, 3) if meal10 is not None else None,
                         meal_up10_profit_yi=round(meal_profit, 2) if meal_profit is not None else None,
                         psy=psy, psy_up1_cost=round(psy1_cost, 3) if psy1_cost is not None else None,
                         psy_up1_profit_yi=round(psy1_profit, 2) if psy1_profit is not None else None,
                         mcap=mcap, el_pct=round(e1 / mcap * 100, 2) if e1 else None)
    return out


# ── 四象限 ──────────────────────────────────────────────────────────
def quadrants(S):
    """正式四象限仅使用覆盖率 ≥70% 且未触发风险上限的企业；
    待核实区企业不参与中位数阈值计算，也不获得正式 A–D 象限标签。"""
    qualified = [c for c in CORE
                 if S[c]["coverage_pct"] >= 70 and c not in D.RISK_CAP]
    sr = [S[c]["survival"]["rate"] for c in qualified if S[c]["survival"]["rate"] is not None]
    er = [S[c]["elasticity"]["rate"] for c in qualified if S[c]["elasticity"]["rate"] is not None]
    ms, me = statistics.median(sr), statistics.median(er)
    out = {}
    for c in CORE:
        s = S[c]["survival"]["rate"] or 0
        e = S[c]["elasticity"]["rate"] or 0
        if c not in qualified:
            out[c] = dict(quadrant="待核实", survival_rate=s, elasticity_rate=e, qualified=False,
                          note=f"覆盖率 {S[c]['coverage_pct']:.0f}% <70%，不参与正式四象限与中位数阈值计算")
            continue
        q = ("A" if (s >= ms and e >= me) else "B" if (s >= ms and e < me)
             else "C" if (s < ms and e >= me) else "D")
        note = "触发风险上限，强制不进入 A 类" if c in D.RISK_CAP else ""
        out[c] = dict(quadrant=q, survival_rate=s, elasticity_rate=e, qualified=True, note=note)
    return dict(thresholds=dict(survival_median=round(ms, 2), elasticity_median=round(me, 2),
                                qualified_count=len(qualified)), items=out)


# ── 排名 ────────────────────────────────────────────────────────────
def rankings(S, Q, ST):
    def by(key):
        return sorted(CORE, key=lambda c: -(key(c) if key(c) is not None else -1))
    surv = by(lambda c: S[c]["survival"]["rate"])
    elas = by(lambda c: S[c]["elasticity"]["rate"])
    total = by(lambda c: S[c]["final_score"])
    costs = [c for c in CORE if D.COST[c]["v"] is not None]
    cost_asc = sorted(costs, key=lambda c: D.COST[c]["v"])          # 成本从低到高（竞争力）
    cost_desc = sorted(costs, key=lambda c: -D.COST[c]["v"])
    debt_asc = sorted(CORE, key=lambda c: M[c]["有息负债_2026Q3"]["资产负债率_pct"])
    return dict(survival=surv, elasticity=elas, total=total,
                cost_asc=cost_asc, cost_desc=cost_desc, debt_asc=debt_asc,
                main_board=[c for c in total if S[c]["in_main_board"]],
                pending=[c for c in total if not S[c]["in_main_board"]])


def main():
    A = availability()
    S = score_all()
    ST = stress_all()
    E = elasticity_all()
    Q = quadrants(S)
    R = rankings(S, Q, ST)
    result = dict(meta=dict(scoring_version="v3", today=D.TODAY, price_date=D.PRICE_DATE, report_period=D.REPORT_PERIOD,
                            bench=P0, weight_kg=W, scenarios=D.SCENARIOS,
                            core=CORE, pool=POOL,
                            a_weights=dict((k, w) for k, _, w in A_ITEMS),
                            b_weights=dict((k, w) for k, _, w in B_ITEMS)),
                  availability=A, scores=S, stress=ST, elasticity=E, quadrants=Q, rankings=R)
    (BASE / "v3_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写出 v3_results.json｜核心 {len(CORE)} 家 / 全池 {len(POOL)} 家")
    print("\n=== 综合评分（可比得分率，0–100）===")
    print(f"{'公司':<8}{'生存':>8}{'弹性':>8}{'原始分':>9}{'有效满分':>10}{'覆盖率':>9}{'可比得分':>10}{'最终':>8}{'置信':>6}{'象限':>6}{'主榜':>6}")
    for c in R["total"]:
        s = S[c]
        print(f"{D.NAME[c]:<8}{s['survival']['rate']:>8}{s['elasticity']['rate']:>8}{s['total_raw']:>9}"
              f"{s['total_effective_max']:>10}{s['coverage_pct']:>9}{s['comparable_score']:>10}"
              f"{s['final_score']:>8}{s['confidence']:>6}{Q['items'][c]['quadrant']:>6}{'是' if s['in_main_board'] else '否':>6}")
    print("\n=== 基准情景压力测试（猪价 8.60 元/kg）===")
    print(f"{'公司':<8}{'成本':>7}{'年化出栏':>11}{'养殖利润亿':>12}{'月耗现金亿':>12}{'现金跑道月':>12}")
    for c in CORE:
        st = ST[c]
        b = [x for x in st["scenarios"] if x["delta"] == 0][0]
        rw = b["runway_months"]
        cost_s = f"{st['cost']:.2f}" if st["cost"] is not None else "—"
        prof = f"{b['annual_profit_yi']:.2f}" if b["annual_profit_yi"] is not None else "无法测算"
        print(f"{D.NAME[c]:<8}{cost_s:>7}{st['annual_heads_wan']:>11}{prof:>12}"
              f"{b['monthly_burn_yi']:>12}{('不消耗现金' if rw is None else f'{rw:.1f}'):>12}")
    print("\n=== 弹性：猪价 +1 元/kg 利润增量（亿元） / 占市值 ===")
    f2v = lambda x: f"{x:>7.2f}" if isinstance(x, (int, float)) else f"{'—':>7}"
    for c in sorted(CORE, key=lambda x: -(E[x]["el_pct"] or 0)):
        print(f"  {D.NAME[c]:<8} +{E[c]['price_up1_yi']:>7.2f} 亿   {E[c]['el_pct']:>6.2f}%   "
              f"出栏+10%在基准价下 {f2v(E[c]['output_up10_yi'])} 亿")


if __name__ == "__main__":
    main()
