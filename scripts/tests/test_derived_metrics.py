# -*- coding: utf-8 -*-
"""中间指标生成链的回归测试（unittest，零第三方依赖）。

运行：
    py -3.12 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
REPO = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import build_derived_metrics as B  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UnitTests(unittest.TestCase):
    def test_num_distinguishes_missing_and_zero(self):
        self.assertIsNone(B.num(None))
        self.assertIsNone(B.num(""))
        self.assertIsNone(B.num("None"))
        self.assertEqual(B.num("0"), 0.0)
        self.assertEqual(B.num("123.45"), 123.45)

    def test_safe_sum(self):
        self.assertIsNone(B.s(None, None))
        self.assertEqual(B.s(None, 0), 0)
        self.assertEqual(B.s(None, 1.5, 2.5), 4.0)

    def test_fixed_asset_net_rounds_from_yuan(self):
        # 原值 100 亿、折旧 40 亿、减值 0.5 亿 → 59.5 亿
        self.assertEqual(B.fixed_asset_net({
            "固定资产原值": 100e8, "累计折旧": 40e8, "固定资产减值准备": 0.5e8}), 59.5)
        # 减值缺失按 0 处理；原值/折旧缺失返回 None，不静默补 0
        self.assertEqual(B.fixed_asset_net({
            "固定资产原值": 100e8, "累计折旧": 40e8, "固定资产减值准备": None}), 60.0)
        self.assertIsNone(B.fixed_asset_net({
            "固定资产原值": None, "累计折旧": 40e8, "固定资产减值准备": None}))

    def test_table_keeps_first_duplicate(self):
        rec = {"reports": {"fzb": {"20260930": {"data": [
            {"item_title": "货币资金", "item_value": "100"},
            {"item_title": "货币资金", "item_value": "200"},
        ]}}}}
        self.assertEqual(B.table(rec, "fzb", "20260930")["货币资金"], 100.0)


class IntegrationTests(unittest.TestCase):
    """在临时目录跑真实 CLI，不改仓库文件。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "out"
        cls.cmd = [sys.executable, str(SCRIPTS / "build_derived_metrics.py"),
                   "--raw", str(REPO / "data" / "raw"), "--out", str(cls.out / "derived.json")]
        p = subprocess.run(cls.cmd, capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stdout + p.stderr

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_cli_matches_baseline_except_known_fix(self):
        """除「归母净利润」别名修正外，其余字段与发布版一致；修正不改变 v3。"""
        new = json.loads((self.out / "derived.json").read_text(encoding="utf-8"))
        base = json.loads((REPO / "data" / "processed" / "derived_metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(len(new), 15)
        self.assertEqual(sorted(new), sorted(base))
        diffs = []
        for c in base:
            self.assertEqual(len(new[c]), len(base[c]), f"{c} 字段数不一致")
            for k in base[c]:
                if new[c][k] != base[c][k]:
                    diffs.append((c, k))
        # 只允许两期利润表的“归母净利润”不同（15 家 × 2 期）
        self.assertEqual(len(diffs), 30)
        self.assertTrue(all(k in ("利润表_2026前三季度", "利润表_2025前三季度") for _, k in diffs))
        # 新值应等于原始科目「归属于母公司所有者的净利润」/1e8
        for c in base:
            rec = json.loads((REPO / "data" / "raw" / f"{c}.json").read_text(encoding="utf-8"))
            for period, raw_p in (("利润表_2026前三季度", "20260930"),
                                  ("利润表_2025前三季度", "20250930")):
                items = {i["item_title"]: i.get("item_value")
                         for i in rec["reports"]["lrb"][raw_p]["data"]}
                raw = items.get("归属于母公司所有者的净利润")
                self.assertIsNotNone(raw, f"{c} {raw_p} 缺归母净利润科目")
                self.assertAlmostEqual(new[c][period]["归母净利润"], round(float(raw) / 1e8, 2), places=2)

    def test_cli_cwd_independent(self):
        with tempfile.TemporaryDirectory() as cwd:
            out2 = Path(cwd) / "x" / "d.json"
            p = subprocess.run([sys.executable, str(SCRIPTS / "build_derived_metrics.py"),
                                "--raw", str(REPO / "data" / "raw"), "--out", str(out2)],
                               cwd=cwd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(sha256(out2), sha256(self.out / "derived.json"))

    def test_supplement_cannot_silently_override(self):
        with tempfile.TemporaryDirectory() as d:
            sp = Path(d) / "supp.json"
            sp.write_text(json.dumps({"002714": {"现金流.资本开支_亿元": {
                "value": 1.0, "source": "test", "date": "2026-01-01",
                "retrieved_at": "2026-11-19", "note": "test"}}}, ensure_ascii=False),
                encoding="utf-8")
            p = subprocess.run(self.cmd + ["--supplement", str(sp)],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("已有值", p.stdout + p.stderr)

    def test_supplement_fills_null_with_audit(self):
        with tempfile.TemporaryDirectory() as d:
            sp = Path(d) / "supp.json"
            audit = Path(d) / "audit.json"
            sp.write_text(json.dumps({"002714": {"资产负债表扩展_2026Q3.其他应收款": {
                "value": 3.46, "source": "测试补录", "date": "2026-09-30",
                "retrieved_at": "2026-11-19", "note": "仅测试回退逻辑"}}}, ensure_ascii=False),
                encoding="utf-8")
            out = Path(d) / "derived.json"
            p = subprocess.run([sys.executable, str(SCRIPTS / "build_derived_metrics.py"),
                                "--raw", str(REPO / "data" / "raw"), "--out", str(out),
                                "--supplement", str(sp), "--supplement-audit", str(audit)],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["002714"]["资产负债表扩展_2026Q3"]["其他应收款"], 3.46)
            logged = json.loads(audit.read_text(encoding="utf-8"))
            self.assertEqual(len(logged), 1)
            self.assertEqual(logged[0]["source"], "测试补录")

    def test_debt_missing_period_yields_none(self):
        """整个期间缺失时，有息负债字段应为 None，不得按 0 计；其他期间不受影响。"""
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "raw"
            shutil.copytree(REPO / "data" / "raw", raw)
            rec = json.loads((raw / "002714.json").read_text(encoding="utf-8"))
            del rec["reports"]["fzb"]["20260630"]
            (raw / "002714.json").write_text(
                json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            out = Path(d) / "d.json"
            p = subprocess.run([sys.executable, str(SCRIPTS / "build_derived_metrics.py"),
                                "--raw", str(raw), "--out", str(out)],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            q2 = data["002714"]["有息负债_2026Q2"]
            self.assertIsNone(q2["短期有息负债"])
            self.assertIsNone(q2["长期有息负债"])
            self.assertIsNone(q2["有息负债合计"])
            self.assertIsNone(q2["资产负债率_pct"])
            self.assertIsNotNone(data["002714"]["有息负债_2026Q3"]["有息负债合计"])
            self.assertIsNotNone(data["002714"]["有息负债_2025年末"]["有息负债合计"])

    def test_pipeline_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "chain"
            p = subprocess.run([sys.executable, str(SCRIPTS / "run_pipeline.py"),
                                "--raw", str(REPO / "data" / "raw"),
                                "--out", str(out), "--compare-baseline"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            # 中间指标因“归母净利润”修正与基线不同；v3 结果不受影响，仍字节一致
            self.assertNotEqual(man["outputs"]["derived_metrics.json"]["sha256"],
                                sha256(REPO / "data" / "processed" / "derived_metrics.json"))
            self.assertEqual(man["outputs"]["v3_results.json"]["sha256"],
                             sha256(REPO / "data" / "processed" / "v3_results.json"))
            self.assertEqual(man["baseline_comparison"]["derived"]["diff_count"], 30)
            self.assertTrue(man["baseline_comparison"]["v3"]["byte_identical"])
            self.assertIn("PASS 60 / FAIL 0", (out / "logs" / "step3_verify.log").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
