#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IC500 本地 vs 云端 对账脚本
==========================
用于节后实盘对账：对比本地任务与云端任务生成的报告，逐字段检查一致性。

用法：
  python3 diff_reports.py <local_summary.json> <cloud_summary.json>

说明：
  - 两个输入均为 *_summary.json（build 脚本生成的数据摘要）
  - 浮点字段允许 ±0.01 容差
  - 输出 PASS / FAIL 及差异明细
"""
import json
import sys

TOLERANCE = 0.01  # 浮点容差

NUMERIC_FIELDS = [
    "last_close", "open", "high", "low", "last", "change_pct",
    "ma5", "ma10", "ma20", "ma60",
    "macd_dif", "macd_dea", "macd_hist", "rsi14",
]
LIST_FIELDS = ["supports", "resistances"]
EXACT_FIELDS = ["trade_date", "symbol", "is_trading"]


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def cmp_num(a, b):
    if a is None or b is None:
        return a == b
    return abs(float(a) - float(b)) <= TOLERANCE


def main():
    if len(sys.argv) != 3:
        print("用法: python3 diff_reports.py <local_summary.json> <cloud_summary.json>")
        sys.exit(2)

    local = load(sys.argv[1])
    cloud = load(sys.argv[2])

    print("=" * 60)
    print(f"本地: {sys.argv[1]}")
    print(f"云端: {sys.argv[2]}")
    print("=" * 60)

    passed = 0
    failed = 0
    diffs = []

    # 精确字段
    for f in EXACT_FIELDS:
        lv, cv = local.get(f), cloud.get(f)
        ok = lv == cv
        print(f"  [{'✓' if ok else '✗'}] {f:14s}  本地={lv}  云端={cv}")
        if ok: passed += 1
        else: failed += 1; diffs.append(f)

    # 数值字段
    for f in NUMERIC_FIELDS:
        lv, cv = local.get(f), cloud.get(f)
        ok = cmp_num(lv, cv)
        tag = "✓" if ok else "✗"
        print(f"  [{tag}] {f:14s}  本地={lv}  云端={cv}  {'(容差内)' if ok and lv!=cv else ''}")
        if ok: passed += 1
        else: failed += 1; diffs.append(f)

    # 列表字段
    for f in LIST_FIELDS:
        lv, cv = local.get(f, []), cloud.get(f, [])
        ok = len(lv) == len(cv) and all(cmp_num(a, b) for a, b in zip(lv, cv))
        print(f"  [{'✓' if ok else '✗'}] {f:14s}  本地={lv}  云端={cv}")
        if ok: passed += 1
        else: failed += 1; diffs.append(f)

    print("=" * 60)
    if failed == 0:
        print(f"✅ 对账通过：{passed} 项全部一致（数值容差 ±{TOLERANCE}）")
        sys.exit(0)
    else:
        print(f"❌ 对账失败：{passed} 通过 / {failed} 不一致")
        print(f"   差异字段: {', '.join(diffs)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
