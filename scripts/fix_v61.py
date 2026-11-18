# -*- coding: utf-8 -*-
"""V6.1 定点修复：图1内嵌SVG角标 / 成本表四格 / 正邦+36%。
基于 report_v6_final.html 最小修改 → report_v6_1_reviewed.html。
同时同步 report_v6.md 与 exhibits_v5 外部 SVG，保持源与成品一致。
"""
import re, base64
from pathlib import Path

BASE = Path(__file__).parent
V6 = BASE / "report_v6_final.html"
OUT = BASE / "report_v6_1_reviewed.html"
MD = BASE / "report_v6.md"
EXT_SVG = BASE / "exhibits_v5" / "chart_01_quadrant_matrix.svg"

h = V6.read_text(encoding="utf-8")

# ── 修复1：图1 内嵌 SVG 四角标签 ─────────────────────────────────
uris = list(re.finditer(r'src="data:image/svg\+xml;base64,([^"]+)"', h))
assert len(uris) == 10, f"期望 10 个内嵌 SVG，实际 {len(uris)}"
m0 = uris[0]
svg = base64.b64decode(m0.group(1)).decode("utf-8")
assert "高风险弹性型" in svg and "防御型" in svg, "索引0不是图1"

# 交换主标（左上 B ↔ 右下 C），副标同步交换
for old, new in [("B 防御型", "C 高风险弹性型")]:
    assert svg.count(old) == 1
for old in ["C 高风险弹性型", "生存能力较强，复苏弹性一般", "复苏弹性较高，底部承压较大"]:
    assert svg.count(old) == 1, f"{old} 出现 {svg.count(old)} 次"

svg = svg.replace("B 防御型", "__MAIN_LT__")
svg = svg.replace("C 高风险弹性型", "B 防御型")
svg = svg.replace("__MAIN_LT__", "C 高风险弹性型")

svg = svg.replace("生存能力较强，复苏弹性一般", "__SUB_LT__")
svg = svg.replace("复苏弹性较高，底部承压较大", "生存能力较强，复苏弹性一般")
svg = svg.replace("__SUB_LT__", "复苏弹性较高，底部承压较大")

# 复核坐标未被改动：主标 B 应在右下、C 在左上
def corner_of(s, kw):
    i = s.find(kw)
    seg = s[max(0, i - 320):i]
    tr = re.findall(r'translate\(([\d.]+)[ ,]([\d.]+)\)', seg)
    if not tr:
        return None
    x, y = float(tr[-1][0]), float(tr[-1][1])
    return ("左上" if (x < 480 and y < 300) else "右上" if (x >= 480 and y < 300)
            else "左下" if x < 480 else "右下")

assert corner_of(svg, "C 高风险弹性型") == "左上", "C 应在左上"
assert corner_of(svg, "B 防御型") == "右下", "B 应在右下"
assert corner_of(svg, "A 穿越型") == "右上", "A 应在右上"
assert corner_of(svg, "D 弱势型") == "左下", "D 应在左下"

new_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
h = h[:m0.start()] + f'src="data:image/svg+xml;base64,{new_b64}"' + h[m0.end():]
print("[1] 图1 内嵌 SVG 角标已交换：左上C / 右上A / 右下B / 左下D")

# ── 修复2：成本表四家公司字段恢复 ───────────────────────────────
COST_FIX = [
    ("<td>深交所互动易 2026-07；策略会转录 2026-03-02（Re</td>",
     "<td>深交所互动易 2026-07；策略会转录 2026-03-02（Reportify，非正式公告）</td>",
     "华统股份"),
    ("<td>投资者关系活动记录表 2026-10-29（8家机构调研，同花顺转载</td>",
     "<td>投资者关系活动记录表 2026-10-29（8家机构调研，同花顺转载）</td>",
     "天康生物"),
    ("<td>肉猪养殖综合成本（含代养费；Q3账面约12.2，剔除肉猪跌价准备后约12.0</td>",
     "<td>肉猪养殖综合成本（含代养费；Q3账面约12.2，剔除肉猪跌价准备后约12.0）</td>",
     "温氏股份"),
    ("<td>2026三季报 / 北京商报 2026-11-10（媒体转述，非一手</td>",
     "<td>2026三季报 / 北京商报 2026-11-10（媒体转述，非一手）</td>",
     "天邦食品"),
]
for old, new, name in COST_FIX:
    assert h.count(old) == 1, f"{name} 成本字段匹配 {h.count(old)} 次"
    h = h.replace(old, new)
print("[2] 成本表四家字段已恢复（括号闭合、来源完整）")

# ── 修复3：正邦 +36% → 线性年化 27.3% ───────────────────────────
OLD_ZB = "正邦（+36%）"
NEW_ZB = ("正邦（2025 年实际出栏 853.69 万头，2026 年 1—10 月累计 905.75 万头线性年化 "
          "1086.9 万头，年化增幅约 27.3%，为线性估算、非全年实际同比、未计季节性）")
assert h.count(OLD_ZB) == 1, f"正邦+36% 匹配 {h.count(OLD_ZB)} 次"
h = h.replace(OLD_ZB, NEW_ZB)
print("[3] 正邦 +36% 已改为可核实的线性年化 27.3% 表述")

# ── 版本号：标题与页脚标注 v6.1 ─────────────────────────────────
h = h.replace("<title>A 股生猪养殖企业穿越周期研究（v5 图表整合版）</title>",
              "<title>A 股生猪养殖企业穿越周期研究（v6.1 修订版）</title>")
h = h.replace("研究版本 v3.0　·　文字 v4.0　·　图表整合 v5.0",
              "研究版本 v3.0　·　文字 v4.0　·　图表整合 v5.0　·　复审修订 v6.1")
h = h.replace("版本 v5.0（图表整合版）｜研究版本 v3.0｜生成日期 2026-11-17",
              "版本 v6.1（复审修订版）｜研究版本 v3.0｜修订日期 2026-11-17")

OUT.write_text(h, encoding="utf-8")
print(f"[写出] {OUT.name}  {len(h)/1024:.1f} KB")

# ── 同步源 md（成本表4行 + 正邦段）───────────────────────────
if MD.exists():
    md = MD.read_text(encoding="utf-8")
    md_reps = [
        ("策略会转录 2026-03-02（Re |", "策略会转录 2026-03-02（Reportify，非正式公告） |"),
        ("（8家机构调研，同花顺转载 |", "（8家机构调研，同花顺转载） |"),
        ("剔除肉猪跌价准备后约12.0 |", "剔除肉猪跌价准备后约12.0） |"),
        ("（媒体转述，非一手 |", "（媒体转述，非一手） |"),
        ("正邦（+36%）", NEW_ZB),
    ]
    n_ok = 0
    for old, new in md_reps:
        if md.count(old) == 1:
            md = md.replace(old, new); n_ok += 1
        else:
            print(f"  [md 跳过] {old[:30]} 命中 {md.count(old)}")
    MD.write_text(md, encoding="utf-8")
    print(f"[同步] report_v6.md  {n_ok}/{len(md_reps)} 处")

# ── 同步外部 SVG（exhibits_v5）──────────────────────────────
if EXT_SVG.exists():
    es = EXT_SVG.read_text(encoding="utf-8")
    if corner_of(es, "B 防御型") == "左上":
        es = es.replace("B 防御型", "__M__").replace("C 高风险弹性型", "B 防御型").replace("__M__", "C 高风险弹性型")
        es = es.replace("生存能力较强，复苏弹性一般", "__S__").replace("复苏弹性较高，底部承压较大", "生存能力较强，复苏弹性一般").replace("__S__", "复苏弹性较高，底部承压较大")
        EXT_SVG.write_text(es, encoding="utf-8")
        print("[同步] exhibits_v5/图1 外部 SVG 已交换角标")
    else:
        print("[同步] exhibits_v5/图1 外部 SVG 已是修正版")
