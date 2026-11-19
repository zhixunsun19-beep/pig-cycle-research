# -*- coding: utf-8 -*-
"""一条命令跑完整链路：raw 三表 → derived_metrics → v3_results → 60 项校验。

边界
----
- 计算输入只有：`--raw` 指向的原始三表、`research_data_v2.py` 的研究数据层
  （其 `v1_data.json` 从仓库 `data/processed/` 读取）、可选补录层。
- **不会**把发布版 `data/processed/derived_metrics.json` 或 `v3_results.json`
  作为计算输入；它们只在 `--compare-baseline` 时作为事后比较基线读取。
- 所有产物写入 `--out` 目录（默认 `build/chain_YYYYmmdd_HHMMSS`），不覆盖
  `data/`、`figures/`、`report/` 下的发布资产。

用法
----
    python scripts/run_pipeline.py --raw data/raw --out build/chain
    python scripts/run_pipeline.py --raw data/raw --out build/chain --compare-baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], log: Path) -> int:
    print("[run]", " ".join(cmd))
    with log.open("w", encoding="utf-8") as f:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace")
        f.write(p.stdout)
    tail = "\n".join(p.stdout.strip().splitlines()[-6:])
    if tail:
        print(tail)
    print(f"[exit] {p.returncode}  (log: {log})")
    return p.returncode


def diff_json(a_path: Path, b_path: Path) -> list[tuple]:
    a = json.loads(a_path.read_text(encoding="utf-8"))
    b = json.loads(b_path.read_text(encoding="utf-8"))
    out: list[tuple] = []

    def walk(x, y, p=""):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                if k not in x:
                    out.append((p + "/" + k, "missing_in_new", None, y[k]))
                elif k not in y:
                    out.append((p + "/" + k, "missing_in_baseline", x[k], None))
                else:
                    walk(x[k], y[k], p + "/" + k)
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                out.append((p, "len", len(x), len(y)))
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, f"{p}[{i}]")
        else:
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                if abs(x - y) > 1e-9:
                    out.append((p, "numeric", x, y))
            elif x != y:
                out.append((p, "value", x, y))

    walk(a, b)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="raw → derived → v3 → verify 一键链路")
    ap.add_argument("--raw", default=str(REPO / "data" / "raw"), help="原始三表目录")
    ap.add_argument("--out", required=True, help="输出目录（建议 build/...，不要指向 data/）")
    ap.add_argument("--supplement", help="可选：有来源的人工补录层")
    ap.add_argument("--compare-baseline", action="store_true",
                    help="与 data/processed 发布件做事后字段比较（不作为计算输入）")
    args = ap.parse_args()

    raw = Path(args.raw).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    logs = out / "logs"
    logs.mkdir(exist_ok=True)

    derived = out / "derived_metrics.json"
    v3 = out / "v3_results.json"
    py = sys.executable
    manifest = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "executable": py,
        "platform": platform.platform(),
        "raw_dir": str(raw),
        "out_dir": str(out),
        "commands": [],
    }

    print(f"[env] {platform.platform()} | Python {sys.version.split()[0]}")
    print(f"[input] raw: {raw}")
    print(f"[output] dir: {out}")

    cmd1 = [py, str(SCRIPTS / "build_derived_metrics.py"), "--raw", str(raw), "--out", str(derived)]
    if args.supplement:
        cmd1 += ["--supplement", str(Path(args.supplement).resolve()),
                 "--supplement-audit", str(out / "supplement_audit.json")]
    manifest["commands"].append({"cmd": cmd1, "log": "logs/step1_build_derived.log"})
    if run(cmd1, logs / "step1_build_derived.log") != 0:
        print("[FAIL] 中间指标生成失败，链路中止")
        return 1

    cmd2 = [py, str(SCRIPTS / "compute_v3.py"), "--derived", str(derived), "--out", str(v3)]
    manifest["commands"].append({"cmd": cmd2, "log": "logs/step2_compute_v3.log"})
    if run(cmd2, logs / "step2_compute_v3.log") != 0:
        print("[FAIL] v3 计算失败，链路中止")
        return 1

    cmd3 = [py, str(SCRIPTS / "verify_results.py"), "--metrics", str(v3)]
    manifest["commands"].append({"cmd": cmd3, "log": "logs/step3_verify.log"})
    if run(cmd3, logs / "step3_verify.log") != 0:
        print("[FAIL] 60 项校验未通过")
        return 1

    manifest["outputs"] = {
        "derived_metrics.json": {"sha256": sha256(derived), "bytes": derived.stat().st_size},
        "v3_results.json": {"sha256": sha256(v3), "bytes": v3.stat().st_size},
    }
    raw_files = sorted(raw.glob("*.json"))
    manifest["inputs"] = {
        "raw_count": len(raw_files),
        "raw_sha256": {p.name: sha256(p) for p in raw_files},
        "v1_data": {
            "path": str(REPO / "data" / "processed" / "v1_data.json"),
            "sha256": sha256(REPO / "data" / "processed" / "v1_data.json"),
        },
    }
    if args.supplement:
        sp = Path(args.supplement).resolve()
        manifest["inputs"]["supplement"] = {"path": str(sp), "sha256": sha256(sp)}

    if args.compare_baseline:
        baseline_derived = REPO / "data" / "processed" / "derived_metrics.json"
        baseline_v3 = REPO / "data" / "processed" / "v3_results.json"
        cmp_info = {}
        for label, new, base in [("derived", derived, baseline_derived),
                                 ("v3", v3, baseline_v3)]:
            d = diff_json(new, base)
            cmp_info[label] = {
                "baseline": str(base),
                "baseline_sha256": sha256(base),
                "new_sha256": sha256(new),
                "byte_identical": sha256(new) == sha256(base),
                "diff_count": len(d),
                "diffs": [{"path": p, "kind": k, "new": x, "baseline": y} for p, k, x, y in d[:200]],
            }
        (out / "baseline_diff.json").write_text(
            json.dumps(cmp_info, ensure_ascii=False, indent=1), encoding="utf-8")
        for k, v in cmp_info.items():
            print(f"[compare] {k}: byte_identical={v['byte_identical']} diff={v['diff_count']}")
        manifest["baseline_comparison"] = {
            k: {kk: vv for kk, vv in v.items() if kk != "diffs"} for k, v in cmp_info.items()
        }

    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print(f"\n[done] 产物与清单：{out}")
    print(f"  derived: {manifest['outputs']['derived_metrics.json']['sha256']}")
    print(f"  v3     : {manifest['outputs']['v3_results.json']['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
