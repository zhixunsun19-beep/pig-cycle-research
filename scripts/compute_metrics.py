# -*- coding: utf-8 -*-
"""从 14 家猪企财报三表原始数据计算研究指标。

口径（严格按研究需求定义，全部可复现）：
- 金额单位：元 → 亿元（/1e8），保留 2 位小数。
- 资产负债表为期末时点值；利润表/现金流量表为「年内累计值」。
- 单季差分：Q3 = 2026-09-30 累计 - 2026-06-30 累计；Q2 = 2026-06-30 - 2026-03-31；Q1 = 2026-03-31。
- 短期有息负债 = 短期借款 + 应付短期债券 + 一年内到期的非流动负债
  （注：主表无法拆分「一年内到期的租赁负债」，该科目整体计入，存在轻微高估，已在报告标注）
- 长期有息负债 = 长期借款 + 应付债券
- 有息负债合计(主口径) = 短期有息 + 长期有息（不含租赁负债、长期应付款，避免重复）
- 租赁负债、长期应付款单独列示（长期应付款可能含专项应付款/政府补助等非有息项）
- 净有息负债 = 有息负债合计 - 货币资金
  （受限货币资金需查财报附注，本次数据源未覆盖，故未扣除，属偏乐观口径）
- 估算融资成本 = 前三季度利息费用 × 4/3 ÷ 期初期末平均有息负债
  （利息费用为费用化口径，不含资本化利息；期初期末两点平均为简化处理）
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"

YI = 1e8

BS_FIELDS = {
    "总资产": "资产总计", "总负债": "负债合计", "流动资产": "流动资产合计",
    "流动负债": "流动负债合计", "货币资金": "货币资金", "应收账款": "应收账款",
    "应收票据": "应收票据", "存货": "存货", "交易性金融资产": "交易性金融资产",
    "短期借款": "短期借款", "应付票据": "应付票据", "应付账款": "应付账款",
    "应付短期债券": "应付短期债券", "一年内到期的非流动负债": "一年内到期的非流动负债",
    "其他流动负债": "其他流动负债", "长期借款": "长期借款", "应付债券": "应付债券",
    "租赁负债": "租赁负债", "长期应付款": "长期应付款",
    "长期应付款合计": "长期应付款合计", "其他非流动负债": "其他非流动负债",
    "生产性生物资产": "生产性生物资产", "所有者权益合计": "所有者权益(或股东权益)合计",
    "归母股东权益": "归属于母公司股东权益合计", "非流动负债合计": "非流动负债合计",
}

PL_FIELDS = {
    "营业收入": "营业总收入", "财务费用": "财务费用", "利息费用": "利息费用",
    "利息收入": "利息收入", "净利润": "净利润", "归母净利润": "归属于母公司股东的净利润",
    "营业成本": "营业成本", "营业利润": "营业利润",
}

CF_FIELDS = {
    "经营现金流净额": "经营活动产生的现金流量净额",
    "投资现金流净额": "投资活动产生的现金流量净额",
    "筹资现金流净额": "筹资活动产生的现金流量净额",
    "资本开支": "购建固定资产、无形资产和其他长期资产所支付的现金",
    "销售回款": "销售商品、提供劳务收到的现金",
    "取得借款收到现金": "取得借款收到的现金",
    "发行债券收到现金": "发行债券收到的现金",
    "偿还债务支付现金": "偿还债务支付的现金",
    "分配股利利息支付现金": "分配股利、利润或偿付利息所支付的现金",
    "现金净增加额": "现金及现金等价物净增加额",
}

PERIODS = ["20260930", "20260630", "20260331", "20251231", "20250930", "20250630"]


def num(v):
    if v is None or v == "" or v == "None":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def table(rec, src, period):
    obj = rec["reports"].get(src, {}).get(period)
    if not obj:
        return {}
    out = {}
    for it in obj.get("data", []) or []:
        t = it.get("item_title")
        if t and t not in out:
            out[t] = num(it.get("item_value"))
    return out


def pick(d, mapping, unit=YI):
    return {k: (round(d[v] / unit, 2) if d.get(v) is not None else None)
            for k, v in mapping.items()}


def g(d, k, default=None):
    v = d.get(k)
    return v if v is not None else default


def s(*vals):
    """安全求和：None 视为 0；全部为 None 返回 None"""
    xs = [v for v in vals if v is not None]
    return round(sum(xs), 2) if xs else None


def main():
    result = {}
    for fp in sorted(RAW.glob("*.json")):
        rec = json.loads(fp.read_text(encoding="utf-8"))
        code, name = rec["code"], rec["name"]
        bs = {p: pick(table(rec, "fzb", p), BS_FIELDS) for p in PERIODS if table(rec, "fzb", p)}
        pl = {p: pick(table(rec, "lrb", p), PL_FIELDS) for p in PERIODS if table(rec, "lrb", p)}
        cf = {p: pick(table(rec, "llb", p), CF_FIELDS) for p in PERIODS if table(rec, "llb", p)}

        def debt(p):
            b = bs.get(p, {})
            st = s(g(b, "短期借款", 0), g(b, "应付短期债券", 0), g(b, "一年内到期的非流动负债", 0))
            lt = s(g(b, "长期借款", 0), g(b, "应付债券", 0))
            tot = s(st, lt)
            cash = g(b, "货币资金")
            return {
                "短期有息负债": st, "长期有息负债": lt, "有息负债合计": tot,
                "货币资金": cash,
                "净有息负债": round(tot - cash, 2) if (tot is not None and cash is not None) else None,
                "租赁负债(单列)": g(b, "租赁负债"), "长期应付款(单列)": g(b, "长期应付款"),
                "资产负债率_pct": (round(g(b, "总负债", 0) / g(b, "总资产", 1) * 100, 2)
                                if g(b, "总资产") else None),
                "流动比率": (round(g(b, "流动资产", 0) / g(b, "流动负债", 1), 2)
                           if g(b, "流动负债") else None),
                "有息负债率_pct": (round(tot / g(b, "总资产", 1) * 100, 2)
                                if tot is not None and g(b, "总资产") else None),
                "短期有息占比_pct": (round(st / tot * 100, 2) if tot else None),
                "现金覆盖短期有息_pct": (round(cash / st * 100, 2)
                                    if cash is not None and st else None),
            }

        d_now, d_prev_q, d_prev_y, d_year_start = (debt(p) for p in
            ["20260930", "20260630", "20250930", "20251231"])

        # 融资成本：前三季度累计利息费用年化 / 期初期末平均有息负债
        int_exp = g(pl.get("20260930", {}), "利息费用")
        avg_debt = None
        if d_now["有息负债合计"] is not None and d_year_start["有息负债合计"] is not None:
            avg_debt = round((d_now["有息负债合计"] + d_year_start["有息负债合计"]) / 2, 2)
        fin_cost = (round(int_exp * 4 / 3 / avg_debt * 100, 2)
                    if (int_exp is not None and avg_debt) else None)

        # 广义口径：把单独列示的租赁负债、长期应付款也纳入计息负债分母。
        # 主口径按定义不含这两项，但租赁负债同样计息，占比高的公司主口径会失真。
        def broad(p):
            d = debt(p)
            return s(d["有息负债合计"], g(bs.get(p, {}), "租赁负债", 0),
                     g(bs.get(p, {}), "长期应付款", 0))
        b_now, b_start = broad("20260930"), broad("20251231")
        avg_broad = round((b_now + b_start) / 2, 2) if (b_now is not None and b_start is not None) else None
        fin_cost_broad = (round(int_exp * 4 / 3 / avg_broad * 100, 2)
                          if (int_exp is not None and avg_broad) else None)
        lease_pct = (round((g(bs.get("20260930", {}), "租赁负债", 0) +
                            g(bs.get("20260930", {}), "长期应付款", 0)) / b_now * 100, 2)
                     if b_now else None)
        distorted = bool(lease_pct is not None and lease_pct >= 15)

        # 现金流单季差分（累计 → 单季）
        def single(field, p_now, p_prev):
            a, b = cf.get(p_now, {}).get(field), cf.get(p_prev, {}).get(field)
            return round(a - b, 2) if (a is not None and b is not None) else None

        cf_q = {k: {q: single(k, *pair) for q, pair in {
            "2026Q1": ("20260331", None), "2026Q2": ("20260630", "20260331"),
            "2026Q3": ("20260930", "20260630")}.items()}
            for k in ["经营现金流净额", "投资现金流净额", "筹资现金流净额"]}
        # Q1 累计即单季
        cf_q["经营现金流净额"]["2026Q1"] = cf.get("20260331", {}).get("经营现金流净额")
        cf_q["投资现金流净额"]["2026Q1"] = cf.get("20260331", {}).get("投资现金流净额")
        cf_q["筹资现金流净额"]["2026Q1"] = cf.get("20260331", {}).get("筹资现金流净额")

        c = cf.get("20260930", {})
        ocf, capex = g(c, "经营现金流净额"), g(c, "资本开支")
        result[code] = {
            "name": name, "code": code, "报告期": "2026-09-30",
            "资产负债表": bs.get("20260930", {}),
            "资产负债表_2026H1": bs.get("20260630", {}),
            "资产负债表_2025年末": bs.get("20251231", {}),
            "资产负债表_2025Q3": bs.get("20250930", {}),
            "利润表_2026前三季度": pl.get("20260930", {}),
            "利润表_2025前三季度": pl.get("20250930", {}),
            "现金流量表_2026前三季度": c,
            "现金流量表_2025前三季度": cf.get("20250930", {}),
            "有息负债_2026Q3": d_now, "有息负债_2026Q2": d_prev_q,
            "有息负债_2025Q3": d_prev_y, "有息负债_2025年末": d_year_start,
            "融资成本": {"前三季度利息费用_亿元": int_exp, "年化利息费用_亿元":
                        (round(int_exp * 4 / 3, 2) if int_exp is not None else None),
                        "平均有息负债_亿元": avg_debt, "估算融资成本_pct": fin_cost,
                        "广义平均有息负债_亿元": avg_broad, "广义估算融资成本_pct": fin_cost_broad,
                        "租赁负债占广义有息_pct": lease_pct, "主口径失真": distorted,
                        "前三季度财务费用_亿元": g(pl.get("20260930", {}), "财务费用")},
            "现金流": {"前三季度经营_亿元": ocf, "前三季度投资_亿元": g(c, "投资现金流净额"),
                    "前三季度筹资_亿元": g(c, "筹资现金流净额"), "资本开支_亿元": capex,
                    "自由现金流_亿元": (round(ocf - capex, 2) if (ocf is not None and capex is not None) else None),
                    "销售回款_亿元": g(c, "销售回款"), "取得借款_亿元": g(c, "取得借款收到现金"),
                    "偿还债务_亿元": g(c, "偿还债务支付现金"),
                    "单季现金流_亿元": cf_q},
        }

    out = BASE / "derived_metrics.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写出 {out}  公司数={len(result)}\n")
    print(f"{'公司':<8}{'总资产':>9}{'总负债':>9}{'负债率%':>8}{'短有息':>9}{'长有息':>9}{'有息合计':>9}{'货币资金':>9}{'净有息':>9}{'融资成本%':>9}{'经营现金':>9}")
    for code, r in result.items():
        b, d, f, c = r["资产负债表"], r["有息负债_2026Q3"], r["融资成本"], r["现金流"]
        fmt = lambda x: f"{x:>9.2f}" if isinstance(x, (int, float)) else f"{'-':>9}"
        print(f"{r['name']:<8}{fmt(g(b,'总资产'))}{fmt(g(b,'总负债'))}{fmt(d['资产负债率_pct'])}"
              f"{fmt(d['短期有息负债'])}{fmt(d['长期有息负债'])}{fmt(d['有息负债合计'])}"
              f"{fmt(d['货币资金'])}{fmt(d['净有息负债'])}{fmt(f['估算融资成本_pct'])}{fmt(c['前三季度经营_亿元'])}")


if __name__ == "__main__":
    main()
