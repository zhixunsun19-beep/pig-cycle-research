# -*- coding: utf-8 -*-
"""v2 补取 3 家公司一手三表（华统股份/傲农生物/大北农）。
数据源与 v1 完全一致：quotes.sina.cn CompanyFinanceService.getFinanceReport2022
输出：脚本同目录 raw/*.json（原始返回，未经加工）；使用前复制到 data/raw/
"""
import json
import time
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
RAW.mkdir(parents=True, exist_ok=True)

STOCKS = [
    ("002840", "华统股份"),
    ("603363", "傲农生物"),
    ("002385", "大北农"),
]

URL = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SOURCES = {"fzb": "资产负债表", "lrb": "利润表", "llb": "现金流量表"}


def prefix(code):
    return "sh" if code.startswith(("6", "9")) else ("bj" if code.startswith(("4", "8")) else "sz")


def fetch(code, source, num=8, retries=3):
    params = {"paperCode": prefix(code) + code, "source": source,
              "type": "0", "page": "1", "num": str(num)}
    for i in range(retries):
        try:
            r = requests.get(URL, params=params, headers=HEADERS, timeout=25)
            r.raise_for_status()
            d = r.json().get("result", {}).get("data", {}).get("report_list", {}) or {}
            if d:
                return d
        except Exception as e:
            if i == retries - 1:
                print(f"    [FAIL] {code} {source}: {type(e).__name__} {e}", flush=True)
        time.sleep(1.0 + i)
    return {}


def main():
    summary = {}
    for code, name in STOCKS:
        rec = {"code": code, "name": name, "source": "新浪财经财报三表(原始财报口径)",
               "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "reports": {}}
        for src in SOURCES:
            data = fetch(code, src)
            rec["reports"][src] = data
            periods = sorted(data.keys(), reverse=True)
            print(f"  {name}({code}) {SOURCES[src]}: {len(periods)}期 最新={periods[0] if periods else 'N/A'}", flush=True)
            time.sleep(0.35)
        (RAW / f"{code}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        summary[code] = {"name": name,
                         "fzb": sorted(rec["reports"]["fzb"].keys(), reverse=True),
                         "lrb": sorted(rec["reports"]["lrb"].keys(), reverse=True),
                         "llb": sorted(rec["reports"]["llb"].keys(), reverse=True)}
    (BASE / "fetch_summary_v2.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
