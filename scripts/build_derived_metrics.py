# -*- coding: utf-8 -*-
"""从财报三表原始数据生成完整中间指标（derived_metrics.json，28 字段/家）。

定位
----
本文件取代 `compute_metrics.py` 成为**推荐链路**的中间指标生成器：
`compute_metrics.py` 是 2026-11 的早期版本，只输出 17 个字段，缺少
`利润表扩展_*`、`资产负债表扩展_*`、`期间费用_*`、`生产性生物资产_*`、
`在建工程_*` 等 11 个字段，不能直接供 `compute_v3.py` 使用。旧文件保留原样，
仅作历史参考。

输入与口径
----------
- 输入：`data/raw/<code>.json`，为新浪财经接口返回的交易所定期报告原始科目
  （`fzb` 资产负债表、`lrb` 利润表、`llb` 现金流量表），每期带
  `rType`（合并期末）、`is_audit`（是否审计）、`publish_date`（披露日）。
- 金额单位：元 → 亿元（/1e8），四舍五入保留 2 位。
- 时点 vs 累计：资产负债表为期末时点值；利润表/现金流量表为**年内累计值**。
- 单季差分：Q2 = 半年累计 − Q1 累计；Q3 = 前三季累计 − 半年累计；Q1 累计即单季。
- 有息负债 = 短期借款 + 应付短期债券 + 一年内到期的非流动负债
  + 长期借款 + 应付债券（不含租赁负债、长期应付款；单列）。
- 固定资产净额 = 固定资产原值 − 累计折旧 − 固定资产减值准备
  （接口同时给出“固定资产净值”，但不扣减值，本仓库统一按扣减值口径）。
- 缺失与 0 严格区分：科目返回 null 记为 null，不按 0 计；求和时 null 跳过，
  全为 null 则输出 null。**例外（如实说明）**：资产负债率/流动比率的分子缺失时按 0
  参与（仅分母存在即计算）；有息负债各分量全空时输出 None。
- 同名科目保留首次出现（接口存在重复行；个别科目首条为空、后续有值，见
  audit/field_mapping.md §6 的已知缺口）。

补录层
------
`--supplement` 指向 JSON：`{code: {字段路径: {value, source, date, retrieved_at, note}}}`，
仅当自动计算值为 null 时填入，且不会覆盖已有值（覆盖需显式 `--allow-override`，
默认报错退出）。每条补录会写入 `--supplement-audit` 指定的审计文件。
无补录时不需要该参数。

用法
----
    python build_derived_metrics.py --raw ../data/raw --out ../build/derived_metrics.json
    python build_derived_metrics.py --raw ../data/raw --out out.json --supplement ../data/supplements/xxx.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    "利息收入": "利息收入", "净利润": "净利润",
    # 接口实际科目名为「归属于母公司所有者的净利润」；旧映射写成「…股东的净利润」
    # 导致 15 家该字段全为 null（未被评分使用）。此处按实际科目取数，并保留别名回退。
    "归母净利润": ("归属于母公司所有者的净利润", "归属于母公司股东的净利润"),
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

# 利润表扩展（沿用发布版的 9 个字段）
PL_EXT_FIELDS = {
    "销售费用": "销售费用", "管理费用": "管理费用", "研发费用": "研发费用",
    "所得税费用": "所得税费用", "资产减值损失": "资产减值损失",
    "信用减值损失": "信用减值损失", "公允价值变动收益": "公允价值变动收益",
    "投资收益": "投资收益", "营业外支出": "营业外支出",
}

# 资产负债表扩展（固定资产净额按“原值-累计折旧-减值准备”计算，其余按科目名取数）
BS_EXT_FIELDS = {
    "生产性生物资产": "生产性生物资产", "在建工程": "在建工程合计",
    "固定资产净额": None, "累计折旧": "累计折旧", "固定资产原值": "固定资产原值",
    "商誉": "商誉", "其他应收款": "其他应收款", "预付款项": "预付款项",
}

PERIODS = ["20260930", "20260630", "20260331", "20251231", "20250930", "20250630"]
REQUIRED_PERIOD = "20260930"


def num(v):
    """接口值 → float；空值/空串/None 一律返回 None（不当作 0）。"""
    if v is None or v == "" or v == "None":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def table(rec: dict, src: str, period: str) -> dict:
    """把某一期某张表转成 {科目名: 元}，同名科目保留首次出现的值。"""
    obj = rec.get("reports", {}).get(src, {}).get(period)
    if not obj:
        return {}
    out = {}
    for it in obj.get("data", []) or []:
        t = it.get("item_title")
        if t and t not in out:
            out[t] = num(it.get("item_value"))
    return out


def to_yi(d: dict, title: str):
    v = d.get(title)
    return None if v is None else round(v / YI, 2)


def pick(d: dict, mapping: dict) -> dict:
    """按映射取数；映射值可为科目名或候选科目名元组（取首个存在的）。"""
    out = {}
    for k, t in mapping.items():
        if isinstance(t, (tuple, list)):
            out[k] = None
            for cand in t:
                if cand in d:
                    out[k] = to_yi(d, cand)
                    break
        else:
            out[k] = to_yi(d, t)
    return out


def s(*vals):
    """安全求和：None 跳过；全 None 返回 None。"""
    xs = [v for v in vals if v is not None]
    return round(sum(xs), 2) if xs else None


def fixed_asset_net(bs_yuan: dict):
    """固定资产净额 = 原值 − 累计折旧 − 固定资产减值准备（先按元相减，再转亿元四舍五入）。"""
    orig = bs_yuan.get("固定资产原值")
    dep = bs_yuan.get("累计折旧")
    imp = bs_yuan.get("固定资产减值准备")
    if orig is None or dep is None:
        return None
    return round((orig - dep - (imp or 0.0)) / YI, 2)


def load_raw(raw_dir: Path) -> dict:
    files = sorted(raw_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"[error] {raw_dir} 下没有 *.json，请确认 --raw 指向 data/raw")
    out = {}
    for fp in files:
        rec = json.loads(fp.read_text(encoding="utf-8"))
        if "code" not in rec or "reports" not in rec:
            raise SystemExit(f"[error] {fp} 缺少 code/reports 字段，不是受支持的原始三表文件")
        if not rec["reports"].get("fzb", {}).get(REQUIRED_PERIOD):
            raise SystemExit(f"[error] {rec['code']} 缺少 {REQUIRED_PERIOD} 资产负债表")
        out[rec["code"]] = rec
    return out


def build_company(rec: dict) -> dict:
    code, name = rec["code"], rec["name"]
    tbs = {p: table(rec, "fzb", p) for p in PERIODS}
    tpl = {p: table(rec, "lrb", p) for p in PERIODS}
    tcf = {p: table(rec, "llb", p) for p in PERIODS}

    bs = {p: pick(tbs[p], BS_FIELDS) for p in PERIODS if tbs[p]}
    pl = {p: pick(tpl[p], PL_FIELDS) for p in PERIODS if tpl[p]}
    cf = {p: pick(tcf[p], CF_FIELDS) for p in PERIODS if tcf[p]}

    def debt(p):
        b = bs.get(p, {})
        st_parts = [b.get("短期借款"), b.get("应付短期债券"),
                    b.get("一年内到期的非流动负债")]
        lt_parts = [b.get("长期借款"), b.get("应付债券")]
        # 有任一非空分量才求和（None 跳过）；全空输出 None，不按 0 计
        st = s(*st_parts) if any(v is not None for v in st_parts) else None
        lt = s(*lt_parts) if any(v is not None for v in lt_parts) else None
        tot = s(st, lt)
        cash = b.get("货币资金")
        total_assets = b.get("总资产")
        return {
            "短期有息负债": st, "长期有息负债": lt, "有息负债合计": tot,
            "货币资金": cash,
            "净有息负债": round(tot - cash, 2) if (tot is not None and cash is not None) else None,
            "租赁负债(单列)": b.get("租赁负债"), "长期应付款(单列)": b.get("长期应付款"),
            "资产负债率_pct": (round((b.get("总负债") or 0) / total_assets * 100, 2)
                          if total_assets else None),
            "流动比率": (round((b.get("流动资产") or 0) / (b.get("流动负债") or 1), 2)
                     if b.get("流动负债") else None),
            "有息负债率_pct": (round(tot / total_assets * 100, 2)
                          if tot is not None and total_assets else None),
            "短期有息占比_pct": (round(st / tot * 100, 2) if tot else None),
            "现金覆盖短期有息_pct": (round(cash / st * 100, 2)
                               if cash is not None and st else None),
        }

    d_now, d_prev_q, d_prev_y, d_year_start = (debt(p) for p in
        ["20260930", "20260630", "20250930", "20251231"])

    int_exp = pl.get("20260930", {}).get("利息费用")
    avg_debt = None
    if d_now["有息负债合计"] is not None and d_year_start["有息负债合计"] is not None:
        avg_debt = round((d_now["有息负债合计"] + d_year_start["有息负债合计"]) / 2, 2)
    fin_cost = (round(int_exp * 4 / 3 / avg_debt * 100, 2)
                if (int_exp is not None and avg_debt) else None)

    def broad(p):
        b = bs.get(p, {})
        return s(debt(p)["有息负债合计"], b.get("租赁负债") or 0, b.get("长期应付款") or 0)

    b_now, b_start = broad("20260930"), broad("20251231")
    avg_broad = round((b_now + b_start) / 2, 2) if (b_now is not None and b_start is not None) else None
    fin_cost_broad = (round(int_exp * 4 / 3 / avg_broad * 100, 2)
                      if (int_exp is not None and avg_broad) else None)
    lease_pct = (round(((bs.get("20260930", {}).get("租赁负债") or 0) +
                        (bs.get("20260930", {}).get("长期应付款") or 0)) / b_now * 100, 2)
                 if b_now else None)
    distorted = bool(lease_pct is not None and lease_pct >= 15)

    def single(field, p_now, p_prev):
        a = cf.get(p_now, {}).get(field)
        b = cf.get(p_prev, {}).get(field) if p_prev else None
        if a is None:
            return None
        if p_prev and b is None:
            return None
        return round(a - b, 2) if p_prev else a

    cf_q = {}
    for f in ["经营现金流净额", "投资现金流净额", "筹资现金流净额"]:
        cf_q[f] = {
            "2026Q1": cf.get("20260331", {}).get(f),
            "2026Q2": single(f, "20260630", "20260331"),
            "2026Q3": single(f, "20260930", "20260630"),
        }

    c = cf.get("20260930", {})
    ocf, capex = c.get("经营现金流净额"), c.get("资本开支")

    pl_ext = {p: pick(tpl[p], PL_EXT_FIELDS) for p in ("20260930", "20250930")}
    bs_ext = {}
    for p in ("20260930", "20251231"):
        row = {}
        for k, title in BS_EXT_FIELDS.items():
            row[k] = fixed_asset_net({
                "固定资产原值": num(tbs[p].get("固定资产原值")),
                "累计折旧": num(tbs[p].get("累计折旧")),
                "固定资产减值准备": num(tbs[p].get("固定资产减值准备")),
            }) if k == "固定资产净额" else to_yi(tbs[p], title)
        bs_ext[p] = row

    fee_detail = {k: pl_ext["20260930"].get(k) for k in ("销售费用", "管理费用", "研发费用")}
    fee_detail["财务费用"] = pl.get("20260930", {}).get("财务费用")

    return {
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
        "融资成本": {
            "前三季度利息费用_亿元": int_exp,
            "年化利息费用_亿元": round(int_exp * 4 / 3, 2) if int_exp is not None else None,
            "平均有息负债_亿元": avg_debt, "估算融资成本_pct": fin_cost,
            "广义平均有息负债_亿元": avg_broad, "广义估算融资成本_pct": fin_cost_broad,
            "租赁负债占广义有息_pct": lease_pct, "主口径失真": distorted,
            "前三季度财务费用_亿元": pl.get("20260930", {}).get("财务费用"),
        },
        "现金流": {
            "前三季度经营_亿元": ocf, "前三季度投资_亿元": c.get("投资现金流净额"),
            "前三季度筹资_亿元": c.get("筹资现金流净额"), "资本开支_亿元": capex,
            "自由现金流_亿元": (round(ocf - capex, 2)
                          if (ocf is not None and capex is not None) else None),
            "销售回款_亿元": c.get("销售回款"), "取得借款_亿元": c.get("取得借款收到现金"),
            "偿还债务_亿元": c.get("偿还债务支付现金"), "单季现金流_亿元": cf_q,
        },
        "利润表扩展_2026前三季度": pl_ext["20260930"],
        "利润表扩展_2025前三季度": pl_ext["20250930"],
        "资产负债表扩展_2026Q3": bs_ext["20260930"],
        "资产负债表扩展_2025年末": bs_ext["20251231"],
        "期间费用_2026前三季度_亿元": s(fee_detail["销售费用"], fee_detail["管理费用"],
                                  fee_detail["研发费用"], fee_detail["财务费用"]),
        "期间费用_亿元_明细": fee_detail,
        "所得税费用_2026前三季度_亿元": pl_ext["20260930"].get("所得税费用"),
        "生产性生物资产_2026Q3_亿元": bs_ext["20260930"].get("生产性生物资产"),
        "生产性生物资产_2025年末_亿元": bs_ext["20251231"].get("生产性生物资产"),
        "在建工程_2026Q3_亿元": bs_ext["20260930"].get("在建工程"),
        "在建工程_2025年末_亿元": bs_ext["20251231"].get("在建工程"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="raw 三表 → derived_metrics.json（28 字段/家）")
    ap.add_argument("--raw", required=True, help="原始三表目录（data/raw）")
    ap.add_argument("--out", required=True, help="输出 derived_metrics.json 路径（仓库外或 build/）")
    ap.add_argument("--supplement", help="可选：有来源的人工补录层 JSON")
    ap.add_argument("--supplement-audit", help="补录审计输出路径（默认与 --out 同目录）")
    ap.add_argument("--allow-override", action="store_true",
                    help="允许补录覆盖已计算值（默认禁止）")
    args = ap.parse_args()

    raw_dir = Path(args.raw).resolve()
    out = Path(args.out).resolve()
    print(f"[input] raw: {raw_dir}")
    print(f"[output] derived: {out}")

    raws = load_raw(raw_dir)
    print(f"[info] 读取 {len(raws)} 家公司，报告期 {REQUIRED_PERIOD}")

    result = {}
    for code in sorted(raws):
        result[code] = build_company(raws[code])

    supplements = {}
    if args.supplement:
        sp = Path(args.supplement).resolve()
        supplements = json.loads(sp.read_text(encoding="utf-8"))
        print(f"[input] supplement: {sp}（{len(supplements)} 家）")

    applied = []
    for code, fields in supplements.items():
        if code not in result:
            raise SystemExit(f"[error] 补录层包含未知公司 {code}")
        for path, item in fields.items():
            node = result[code]
            keys = path.split(".")
            for k in keys[:-1]:
                if k not in node or not isinstance(node[k], dict):
                    raise SystemExit(f"[error] 补录路径 {code}.{path} 不存在")
                node = node[k]
            last = keys[-1]
            if last not in node:
                raise SystemExit(f"[error] 补录字段 {code}.{path} 不在输出 schema 中")
            if node[last] is not None and not args.allow_override:
                raise SystemExit(f"[error] {code}.{path} 已有值 {node[last]}，"
                                 f"补录会覆盖；如确需覆盖请加 --allow-override")
            node[last] = item["value"]
            applied.append({"code": code, "field": path, **item})

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] 写出 {out}（{len(result)} 家 × {len(result[next(iter(result))])} 字段）")

    audit = Path(args.supplement_audit) if args.supplement_audit else out.with_name("supplement_audit.json")
    if supplements:
        audit.write_text(json.dumps(applied, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[ok] 补录 {len(applied)} 项，审计写入 {audit}")
    elif audit.exists():
        print(f"[info] 未使用补录层，保留既有审计文件 {audit}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
