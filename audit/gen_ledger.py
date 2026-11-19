# -*- coding: utf-8 -*-
"""生成「事实—来源」核对台账（audit/fact_source_ledger.csv）。

数据来源
--------
- 财务事实：`data/raw/<code>.json` 原始三表科目（新浪财经接口转述的定期报告）。
- 研究事实：`scripts/research_data_v2.py` 中的成本/出栏/现金成本/行业常量。
- 来源登记：`sources/source_register.md`（S-01～S-14）。
- 公告原文：`--pdf-dir` 下已下载的三季报 PDF（可选）；只有在这里实际匹配到
  原始数字串才标「原文一致」，否则一律不升级。

用法
----
    python audit/gen_ledger.py
    python audit/gen_ledger.py --pdf-dir /path/to/three-quarter-reports
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import research_data_v2 as D  # noqa: E402

# 财务事实：表、科目、展示名
FIN_FIELDS = [
    ("fzb", "货币资金", "货币资金"),
    ("fzb", "短期借款", "短期借款"),
    ("fzb", "一年内到期的非流动负债", "一年内到期的非流动负债"),
    ("fzb", "长期借款", "长期借款"),
    ("fzb", "应付债券", "应付债券"),
    ("fzb", "存货", "存货"),
    ("fzb", "资产总计", "总资产"),
    ("fzb", "负债合计", "总负债"),
    ("lrb", "营业总收入", "营业收入（累计）"),
    ("lrb", "归属于母公司所有者的净利润", "归母净利润（累计）"),
    ("lrb", "营业成本", "营业成本（累计）"),
    ("llb", "经营活动产生的现金流量净额", "经营现金流净额（累计）"),
    ("llb", "购建固定资产、无形资产和其他长期资产所支付的现金", "资本开支（累计）"),
]

SRC_STATUS = {
    "接口可用": "接口可用（未解析原文）",
    "仅站点主页": "仅站点主页",
    "待补充": "未找到",
    "仓库内已核对": "仓库内已核对",
}


def num(v):
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def table(rec, src, period):
    obj = rec.get("reports", {}).get(src, {}).get(period)
    if not obj:
        return {}
    out = {}
    for it in obj.get("data", []) or []:
        t = it.get("item_title")
        if t and t not in out:
            out[t] = (num(it.get("item_value")), it.get("item_field"))
    return out


def load_matches(pdf_dir: Path | None):
    """返回 {code: {"file":..., "matches": {"fzb:科目": {"page":n}}}}。

    优先用 --pdf-dir 现场解析；未提供时读取 `audit/pdf_matches.json`（本轮已固化的
    字面匹配结果），保证台账可离线重现同一状态。
    """
    if pdf_dir and pdf_dir.exists():
        try:
            import fitz  # PyMuPDF，仅取证时需要
        except ImportError:
            print("[warn] 未安装 PyMuPDF，改用 audit/pdf_matches.json")
        else:
            out = {}
            for code, meta in {e["code"]: e for e in json.loads(
                    (REPO / "audit" / "pdf_evidence.json").read_text(encoding="utf-8"))}.items():
                tail = meta["url"].rsplit("/", 1)[-1].replace(".PDF", ".pdf")
                cand = list(pdf_dir.glob(f"*{tail}"))
                if not cand:
                    continue
                doc = fitz.open(cand[0])
                pages = [re.sub(r"\s+", "", p.get_text()) for p in doc]
                matches = {}
                rec = json.loads((REPO / "data" / "raw" / f"{code}.json").read_text(encoding="utf-8"))
                for src in ("fzb", "lrb", "llb"):
                    for it in rec["reports"][src]["20260930"]["data"]:
                        v = it.get("item_value")
                        if not v:
                            continue
                        s = f"{float(v):,.2f}"
                        for i, t in enumerate(pages, 1):
                            if s in t:
                                matches[f"{src}:{it['item_title']}"] = {"page": i, "numstr": s}
                                break
                out[code] = {"file": cand[0].name, "matches": matches}
            return out
    path = REPO / "audit" / "pdf_matches.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {c: {"file": v["file"], "matches": v["matches"]} for c, v in raw.items()}
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", help="已下载的三季报 PDF 目录（可选）")
    ap.add_argument("--out", default=str(REPO / "audit" / "fact_source_ledger.csv"))
    args = ap.parse_args()

    pdfs = load_matches(Path(args.pdf_dir).resolve() if args.pdf_dir else None)
    rows = []
    fid = 0

    def add(**kw):
        nonlocal fid
        fid += 1
        row = {"fact_id": f"F{fid:04d}"}
        row.update({k: "" for k in ("category", "s_ref", "company_code", "company", "field",
                                    "period", "value", "unit", "source_level", "source_ref",
                                    "locator", "verification", "note")})
        row.update(kw)
        rows.append(row)

    # 1) 财务事实（15 家 × 13 项）
    for fp in sorted((REPO / "data" / "raw").glob("*.json")):
        rec = json.loads(fp.read_text(encoding="utf-8"))
        code, name = rec["code"], rec["name"]
        for src, title, label in FIN_FIELDS:
            t = table(rec, src, "20260930")
            val, field = t.get(title, (None, None))
            if val is None:
                status, loc, note = "未找到", "", "接口返回该科目为空；不代表公司未披露"
            else:
                numstr = f"{val:,.2f}"
                status, loc, note = "仅二手", f"data/raw/{code}.json {src}/20260930/{title}", \
                    "接口转述交易所定期报告，未逐份公告核验"
                hit = pdfs.get(code)
                if hit:
                    m = hit["matches"].get(f"{src}:{title}")
                    if m:
                        status = "原文一致"
                        loc = f'{hit["file"]} 第{m["page"]}页；{src}/20260930/{title}'
                        note = f'PDF 字面匹配 {m["numstr"]}'
            add(category="财务", s_ref="S-01",
                company_code=code, company=name, field=label,
                period="2026-09-30" if src == "fzb" else "2026前三季度",
                value=(f"{val/1e8:.2f}" if val is not None else ""), unit="亿元",
                source_level="一手（交易所定期报告）" if status == "原文一致" else "一手·经接口转述",
                source_ref="新浪财经财报三表接口（CompanyFinanceService.getFinanceReport2022）",
                locator=loc, verification=status, note=note)

    # 2) 完全成本
    for code, name in D.POOL:
        c = D.COST.get(code)
        if not c:
            add(category="成本", s_ref="S-04", company_code=code, company=name,
                field="生猪养殖完全成本", period="", value="", unit="元/kg",
                source_level="", source_ref="", locator="",
                verification="未找到", note="研究数据层无该公司的可核实成本读数")
            continue
        lvl = c.get("level", "")
        status = "仅二手" if lvl in ("二手", "待核实") else "原文未取得（仅登记来源）"
        add(category="成本", s_ref="S-04", company_code=code, company=name,
            field="生猪养殖完全成本", period=c.get("date", ""), value=str(c.get("v", "")),
            unit="元/kg", source_level=lvl, source_ref=c.get("src", ""),
            locator=c.get("cal", ""), verification=status,
            note="口径：" + c.get("cal", "") + ("；" + c.get("note", "") if c.get("note") else ""))

    # 3) 出栏
    for code, name in D.POOL:
        o = D.OUTPUT.get(code)
        if not o:
            add(category="出栏", s_ref="S-03", company_code=code, company=name,
                field="出栏量", period="", value="", unit="万头", source_level="",
                source_ref="", locator="", verification="未找到", note="研究数据层无出栏数据")
            continue
        add(category="出栏", s_ref="S-03", company_code=code, company=name,
            field="2025 全年出栏", period="2025", value=str(o.get("y2025", "")),
            unit="万头", source_level=o.get("level", ""), source_ref=o.get("src", ""),
            locator=o.get("cal25", ""), verification="原文未取得（仅登记来源）",
            note="月度销售简报/年度报告原文本轮未逐份调阅")
        add(category="出栏", s_ref="S-03", company_code=code, company=name,
            field="2026年1-10月累计出栏", period="2026-01~10", value=str(o.get("m1_10", "")),
            unit="万头", source_level=o.get("level", ""), source_ref=o.get("src", ""),
            locator=o.get("cal26", ""), verification="原文未取得（仅登记来源）",
            note="月度销售简报原文本轮未逐份调阅")
        m = o.get("m1_10")
        add(category="出栏", s_ref="S-03", company_code=code, company=name,
            field="2026 年化出栏（计算值）", period="2026E", value=(f"{m*12/10:.1f}" if m else ""),
            unit="万头", source_level="计算", source_ref="公式：1-10月累计 × 12/10",
            locator="scripts/research_data_v2.py OUTPUT", verification="计算值",
            note="线性年化假设，非公司指引；目标区间单列")

    # 4) 现金成本（3 家）
    for code, c in D.CASH_COST.items():
        lvl = c.get("level", "")
        status = "仅二手" if lvl in ("二手", "待核实") else "原文未取得（仅登记来源）"
        add(category="现金成本", s_ref="S-04", company_code=code, company=D.NAME.get(code, ""),
            field="现金/付现成本", period=c.get("date", ""), value=str(c.get("v", "")),
            unit="元/kg", source_level=lvl, source_ref=c.get("src", ""),
            locator=c.get("cal", ""), verification=status,
            note="仅 3 家有读数，口径不一，未参与跨公司打分")

    # 5) 行业事实
    INDUSTRY_ROWS = [
        ("能繁母猪存栏", "2026Q3末", "3602", "万头", "官方·转载",
         "国家统计局/五部委（媒体转载）", "同比 −10.7%、为正常保有量 96.0%"),
        ("生猪存栏", "2026Q3末", "42533", "万头", "官方·转载",
         "五部委（媒体转载）", "同比 −2.6%"),
        ("生猪出栏", "2026前三季度", "53739", "万头", "官方·转载",
         "五部委（媒体转载）", "同比 +1.4%"),
        ("猪肉产量", "2026前三季度", "4508", "万吨", "官方·转载",
         "五部委（媒体转载）", "同比 +3.2%"),
        ("自繁自养头均亏损", "2026-11-11", "384.27", "元/头", "二手",
         "Mysteel（咨询·二手）", "用于基准猪价交叉验证"),
        ("全国外三元均价", "2026-11-13", "8.60", "元/kg", "二手",
         "中国养猪网/天源、为猪、行情宝、Mysteel 交叉区间 8.54–8.76", "压力测试基准价"),
    ]
    for field, period, value, unit, lvl, src, note in INDUSTRY_ROWS:
        add(category="行业", s_ref="S-08/S-09", company_code="", company="行业",
            field=field, period=period, value=value, unit=unit, source_level=lvl,
            source_ref=src, locator="scripts/research_data_v2.py INDUSTRY/BENCH",
            verification="仅二手", note=note)

    # 6) 来源登记（S-01～S-14）
    reg = json.loads((REPO / "audit" / "source_status.json").read_text(encoding="utf-8"))
    for item in reg:
        add(category="来源登记", s_ref=item["id"], company_code="", company="",
            field=item["name"], period="", value="", unit="",
            source_level=item["type"], source_ref=item["url"],
            locator=item["coverage"], verification=SRC_STATUS.get(item["status"], item["status"]),
            note=item.get("note", ""))

    out = Path(args.out)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "rows": len(rows),
        "by_category": {},
        "by_verification": {},
        "pdf_verified_companies": sorted(pdfs),
    }
    for r in rows:
        summary["by_category"][r["category"]] = summary["by_category"].get(r["category"], 0) + 1
        summary["by_verification"][r["verification"]] = summary["by_verification"].get(r["verification"], 0) + 1
    (out.with_name("ledger_summary.json")).write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"[ok] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
