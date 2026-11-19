#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_results.py —— 报告关键数字回归校验（无需重跑整套模型）

只读取 data/processed/v3_results.json，逐项核对报告公开的关键数字与内部一致性。
这是本仓库中**确实可直接运行**的部分；完整模型重跑需按 scripts/README.md 放置数据。

用法：
    python verify_results.py
    python verify_results.py --metrics ../data/processed/v3_results.json
退出码：0 全部通过；1 存在失败项。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CASES = {  # 代码 -> (公司, 报告 final_score)
    "002100": ("天康生物", 61.76),
    "002714": ("牧原股份", 57.62),
    "605296": ("神农集团", 56.84),
    "002840": ("华统股份", 49.02),
    "603477": ("巨星农牧", 48.54),
    "300498": ("温氏股份", 47.49),
    "000876": ("新希望", 44.72),
}
PENDING = {"002567": ("唐人神", 67.0), "600975": ("新五丰", 59.0)}
RUNWAY = {  # 代码 -> (基准, 极端压力) 月
    "002714": (149.7, 9.2),
    "300498": (5.0, 1.7),
    "000876": (None, 40.1),
}
EPS = 0.02
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, f"{label}{('  [' + detail + ']') if detail and not ok else ''}"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", default=str(Path(__file__).parent.parent / "data" / "processed" / "v3_results.json"))
    args = ap.parse_args()

    path = Path(args.metrics)
    if not path.exists():
        print(f"[ERROR] 找不到 {path}")
        return 1
    R = json.loads(path.read_text(encoding="utf-8"))
    S, Q, ST = R["scores"], R["quadrants"], R["stress"]
    core = R["meta"]["core"]

    # 1. 结构
    check(len(core) == 9, "核心池 9 家", str(len(core)))
    check(len(S) == 9, "评分覆盖 9 家", str(len(S)))

    # 2. A2 未评分且未计 0 分
    a2 = [S[c]["survival"]["items"]["A2"] for c in core]
    n_na = sum(1 for i in a2 if not i["available"])
    check(n_na == 9, "A2 未评分 9/9", str(n_na))
    check(all(i["score"] is None for i in a2), "A2 缺失未按 0 分处理")

    # 3. 生存维度有效满分：A2 的 10 分未计入 → 合格企业 50；待核实企业缺更多项 → 35
    qualified = [c for c in core if c not in PENDING]
    check(all(abs(S[c]["survival"]["effective_max"] - 50.0) < 1e-6 for c in qualified),
          "合格企业生存有效满分 = 50",
          str(sorted({S[c]["survival"]["effective_max"] for c in qualified})))
    check(all(abs(S[c]["survival"]["effective_max"] - 35.0) < 1e-6 for c in PENDING),
          "待核实企业生存有效满分 = 35",
          str(sorted({S[c]["survival"]["effective_max"] for c in PENDING})))

    # 4. comparable_score 可由 raw / effective_max 复算
    for c in core:
        s = S[c]
        if not s["total_effective_max"]:
            continue
        calc = round(s["total_raw"] / s["total_effective_max"] * 100, 2)
        check(abs(calc - s["comparable_score"]) <= EPS,
              f"comparable_score 可复算 {c}", f"{calc} vs {s['comparable_score']}")

    # 5. final_score = min(comparable, cap)
    for c in core:
        s = S[c]
        cap = s.get("cap")
        expect = min(s["comparable_score"], cap["cap"]) if cap else s["comparable_score"]
        check(abs(expect - s["final_score"]) <= EPS, f"final_score 与 cap 规则一致 {c}")

    # 6. 报告公开的 7 家最终得分
    for code, (name, exp) in CASES.items():
        check(abs(S[code]["final_score"] - exp) <= 0.01, f"{name} final_score = {exp}",
              f"{S[code]['final_score']}")

    # 7. 待核实企业：覆盖率 < 70%，象限标「待核实」，不进主榜
    for code, (name, cov) in PENDING.items():
        s = S[code]
        check(abs(s["coverage_pct"] - cov) <= 0.6, f"{name} 覆盖率 ≈ {cov}%", f"{s['coverage_pct']}")
        check(s["coverage_pct"] < 70, f"{name} 覆盖率 < 70%")
        check(Q["items"][code]["quadrant"] == "待核实", f"{name} 象限 = 待核实", Q["items"][code]["quadrant"])
        check(not s["in_main_board"], f"{name} 不进正式主榜")

    # 8. 象限阈值与合格企业数
    th = Q["thresholds"]
    check(abs(th["survival_median"] - 50.56) <= 0.01, "生存中位数 50.56", str(th["survival_median"]))
    check(abs(th["elasticity_median"] - 53.92) <= 0.01, "弹性中位数 53.92", str(th["elasticity_median"]))
    check(th["qualified_count"] == 7, "合格企业 7 家", str(th["qualified_count"]))

    # 9. 六情景与关键跑道
    for c in core:
        check(len(ST[c]["scenarios"]) == 6, f"{c} 六情景完整", str(len(ST[c]["scenarios"])))
    for code, (base, extreme) in RUNWAY.items():
        sc = ST[code]["scenarios"]
        base_sc = next((x for x in sc if abs(x["delta"]) < 1e-9), None)
        if base is not None and base_sc is not None:
            check(abs(base_sc["runway_months"] - base) <= 0.15,
                  f"{CASES.get(code, (code,))[0]} 基准跑道 {base}",
                  f"{base_sc['runway_months']}")
        # 极端压力 = 猪价 -3 元/kg（delta = -3）
        ext = next((x for x in sc if abs(x["delta"] + 3.0) < 1e-9), None)
        check(ext is not None, f"{code} 存在极端压力情景")
        if ext is not None:
            check(abs(ext["runway_months"] - extreme) <= 0.15,
                  f"{CASES.get(code, (code,))[0]} 极端压力跑道 {extreme}", f"{ext['runway_months']}")

    # 10. 无空值泄漏
    check(all(S[c]["final_score"] is not None for c in core), "final_score 无空值")

    ok = sum(1 for p, _ in results if p)
    print(f"数据文件: {path}")
    print(f"校验结果: PASS {ok} / FAIL {len(results) - ok}（共 {len(results)} 项）\n")
    for p, label in results:
        if not p:
            print(f"  FAIL  {label}")
    if ok != len(results):
        return 1
    print("  全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
