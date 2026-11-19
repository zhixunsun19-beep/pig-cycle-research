# -*- coding: utf-8 -*-
"""替代图表的自动验收：文件、XML、文字标签、关键数值与字体回退。

用法：python chartgen/verify_charts.py [--out chartgen/out]
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NS = "{http://www.w3.org/2000/svg}"

CHECKS = {
    "chart_01_quadrant_matrix": {
        "title": "图1",
        "texts": ["50.56", "53.92", "牧原股份", "唐人神", "新五丰", "A 穿越型", "D 弱势型"],
    },
    "chart_02_sow_inventory": {
        "title": "图2",
        "texts": ["3602", "3900", "3750", "2026Q3末"],
    },
    "chart_03_complete_cost": {
        "title": "图3",
        "texts": ["11.40", "8.60", "12.42", "唐人神"],
    },
    "chart_04_output_volume": {
        "title": "图4",
        "texts": ["牧原股份", "温氏股份", "2025 全年实际"],
    },
    "chart_05_financial_safety": {
        "title": "图5",
        "texts": ["75", "150", "天邦食品", "温氏股份"],
    },
    "chart_06_debt_and_cash": {
        "title": "图6",
        "texts": ["短期有息", "长期有息", "货币资金"],
    },
    "chart_07_cash_runway_heatmap": {
        "title": "图7",
        "texts": ["149.7", "9.2", "无消耗", "极端压力", "强势复苏"],
    },
    "chart_08_price_sensitivity": {
        "title": "图8",
        "texts": ["93.09", "牧原股份", "市值"],
    },
    "chart_09_output_increase_10pct": {
        "title": "图9",
        "texts": ["-26.06", "无法测算", "8.60"],
    },
    "chart_10_score_components": {
        "title": "图10",
        "texts": ["未评分", "A1", "B5", "牧原股份"],
    },
}


def svg_text(path: Path) -> str:
    tree = ET.parse(path)
    return "".join(t.text or "" for t in tree.iter(f"{NS}text"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "chartgen/out"))
    args = ap.parse_args()
    out = Path(args.out)
    fails = []
    for name, spec in CHECKS.items():
        svg, png = out / f"{name}.svg", out / f"{name}.png"
        if not svg.exists() or not png.exists():
            fails.append(f"{name}: 缺少 svg/png")
            continue
        if svg.stat().st_size < 5000 or png.stat().st_size < 8000:
            fails.append(f"{name}: 文件过小，疑似空图")
        try:
            text = svg_text(svg)
        except ET.ParseError as e:
            fails.append(f"{name}: SVG XML 解析失败 {e}")
            continue
        if spec["title"] not in text:
            fails.append(f'{name}: 缺少标题「{spec["title"]}」')
        for t in spec["texts"]:
            if t not in text:
                fails.append(f"{name}: 缺少文本「{t}」")
        if "□" in text or "�" in text:
            fails.append(f"{name}: 出现缺字占位符")
        raw = svg.read_text(encoding="utf-8")
        if "Microsoft YaHei" not in raw:
            fails.append(f"{name}: 未声明中文字体回退")
        print(f'[ok] {name}: text={len(text)} png={png.stat().st_size // 1024}KB')

    if fails:
        print(f"\n[FAIL] {len(fails)} 项")
        for f in fails:
            print("  -", f)
        return 1
    print(f"\n[done] 10 张图通过结构/文本/数值断言")
    return 0


if __name__ == "__main__":
    sys.exit(main())
