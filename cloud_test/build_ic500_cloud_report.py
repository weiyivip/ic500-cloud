#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IC500 盘前简报 - 云端测试版生成脚本
====================================
【隔离保证】
  - 仅从 114.55.55.139 读取数据（HTTP GET），绝不写入远端
  - 所有产物写入本脚本所在目录下的 output/ 子目录
  - 所有输出文件名带 _cloud 后缀，与本地任务完全隔离
  - 仅依赖 Python 标准库，无需额外安装

用法：
  python3 build_ic500_cloud_report.py            # 正常生成
  python3 build_ic500_cloud_report.py --dry-run  # 仅解析不写文件
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ---------- 配置 ----------
DATA_URL = "http://114.55.55.139/ic500/download_json.php?file=live_summary.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
MAX_RETRY = 3
RETRY_DELAY = 5  # seconds
TIMEOUT = 30


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [cloud] {msg}", flush=True)


def download_json():
    """带重试地下载 JSON 数据。"""
    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            log(f"下载数据（第 {attempt}/{MAX_RETRY} 次）...")
            req = urllib.request.Request(DATA_URL, headers={"User-Agent": "IC500-CloudTest/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            log(f"下载成功，数据大小 {len(raw)} 字节")
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
            last_err = e
            log(f"下载失败: {e}")
            if attempt < MAX_RETRY:
                log(f"等待 {RETRY_DELAY}s 后重试...")
                time.sleep(RETRY_DELAY)
    raise RuntimeError(f"数据下载失败，已重试 {MAX_RETRY} 次: {last_err}")


def get(d, *keys, default=None):
    """安全链式取值。"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def fmt(v, nd=2):
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def build_report(data):
    """解析字段并生成 HTML。返回 (html_str, date_compact, summary_dict)。"""
    price = get(data, "price", default={}) or {}
    ma = get(data, "ma", default={}) or {}
    indicators = get(data, "indicators", default={}) or {}
    macd = get(indicators, "macd", default={}) or {}
    holding = get(data, "holding_contract", default={}) or {}
    holding_price = get(holding, "price", default={}) or {}
    sr = get(data, "support_resistance", default={}) or {}
    spread = get(data, "spread", default={}) or {}

    trade_date = get(data, "trade_date", default="")
    timestamp = get(data, "timestamp", default="")
    is_trading = get(data, "is_trading", default=False)

    last_close = get(price, "pre_close")
    open_px = get(price, "open")
    high_px = get(price, "high")
    low_px = get(price, "low")
    change_pct = get(price, "change_pct")

    symbol = get(holding, "symbol", default="N/A")
    last_px = get(holding_price, "current")

    ma5 = get(ma, "ma5")
    ma10 = get(ma, "ma10")
    ma20 = get(ma, "ma20")
    ma60 = get(ma, "ma60")

    macd_dif = get(macd, "macd")
    macd_dea = get(macd, "signal")
    macd_hist = get(macd, "hist")
    macd_status = get(macd, "status", "")

    rsi6 = None  # 数据源未提供
    rsi14 = get(indicators, "rsi14")

    supports = get(sr, "supports", default=[]) or []
    resistances = get(sr, "resistances", default=[]) or []

    spread_val = get(spread, "spread")
    liq_warning = get(spread, "liquidity_warning", False)

    # 涨跌幅
    chg_pct = change_pct
    if chg_pct is None and last_close and last_px:
        try:
            chg_pct = (float(last_px) - float(last_close)) / float(last_close) * 100
        except Exception:
            chg_pct = None

    chg_sign = "+" if (chg_pct is not None and chg_pct >= 0) else ""
    chg_color = "#e74c3c" if (chg_pct is not None and chg_pct >= 0) else "#27ae60"

    # 均线排列
    ma_bull = all(v is not None for v in (ma5, ma10, ma20, ma60)) and ma5 > ma10 > ma20 > ma60
    ma_bear = all(v is not None for v in (ma5, ma10, ma20, ma60)) and ma5 < ma10 < ma20 < ma60
    if ma_bull:
        ma_align, ma_align_color = "多头排列", "#e74c3c"
    elif ma_bear:
        ma_align, ma_align_color = "空头排列", "#27ae60"
    else:
        ma_align, ma_align_color = "纠缠/震荡", "#7f8c8d"

    macd_text = "金叉/多头" if macd_status == "bull" else ("死叉/空头" if macd_status == "bear" else "中性")
    macd_color = "#e74c3c" if macd_status == "bull" else ("#27ae60" if macd_status == "bear" else "#7f8c8d")

    def rsi_state(v):
        if v is None:
            return "N/A", "#7f8c8d"
        if v >= 80: return "超买", "#e74c3c"
        if v >= 60: return "偏强", "#e67e22"
        if v >= 40: return "中性", "#7f8c8d"
        if v >= 20: return "偏弱", "#16a085"
        return "超卖", "#27ae60"

    rsi14_state, rsi14_color = rsi_state(rsi14)

    # 日期
    try:
        dt = datetime.strptime(str(trade_date), "%Y%m%d")
        date_dash = dt.strftime("%Y-%m-%d")
        date_compact = dt.strftime("%Y%m%d")
    except Exception:
        date_dash = str(trade_date)
        date_compact = str(trade_date)

    # 一句话观点
    parts = []
    if ma_bull: parts.append("均线多头，趋势偏多")
    elif ma_bear: parts.append("均线空头，趋势偏空")
    else: parts.append("均线纠缠，震荡格局")
    if macd_status == "bull": parts.append("MACD 红柱，动能偏多")
    elif macd_status == "bear": parts.append("MACD 绿柱，动能偏空")
    if rsi14 is not None:
        if rsi14 >= 60: parts.append("RSI 偏强")
        elif rsi14 <= 40: parts.append("RSI 偏弱")
        else: parts.append("RSI 中性")
    parts.append(f"关注 {fmt(supports[0]) if supports else 'N/A'} 支撑 / {fmt(resistances[0]) if resistances else 'N/A'} 阻力")
    one_liner = "；".join(parts) + "。"

    trading_badge = "交易中" if is_trading else "休市/非交易时段"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IC500 盘前简报 {date_dash}（云端测试版）</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f4f6f9; color: #2c3e50; line-height: 1.6; }}
  .container {{ max-width: 820px; margin: 0 auto; }}
  header {{ background: linear-gradient(135deg, #1a3a5c 0%, #2c5282 100%); color: #fff; padding: 24px 28px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.12); }}
  header h1 {{ margin: 0; font-size: 22px; font-weight: 600; }}
  header .meta {{ margin-top: 8px; font-size: 13px; opacity: 0.85; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; background: rgba(255,255,255,0.2); margin-left: 8px; }}
  .cloud-tag {{ background: #f093fb; color: #fff; }}
  section {{ background: #fff; margin-top: 16px; padding: 20px 24px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  section h2 {{ margin: 0 0 14px 0; font-size: 16px; color: #34495e; border-left: 4px solid #3498db; padding-left: 10px; }}
  .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px 24px; }}
  .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .cell .label {{ color: #7f8c8d; font-size: 12px; }}
  .cell .value {{ font-size: 18px; font-weight: 600; margin-top: 2px; }}
  .chg {{ color: {chg_color}; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #ecf0f1; }}
  th {{ color: #7f8c8d; font-weight: 500; font-size: 12px; }}
  .view {{ background: #eaf4fc; border-left: 4px solid #3498db; padding: 14px 18px; border-radius: 6px; font-size: 15px; }}
  footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #95a5a6; }}
  .warn {{ color: #e67e22; font-weight: 600; }}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>IC500 盘前简报 {date_dash}（云端测试版）</h1>
  <div class="meta">
    数据时间：{timestamp}
    <span class="badge">{trading_badge}</span>
    <span class="badge">合约 {symbol}</span>
    <span class="badge cloud-tag">☁ CLOUD TEST</span>
  </div>
</header>

<section>
  <h2>基本行情</h2>
  <div class="grid-4">
    <div class="cell"><div class="label">昨收</div><div class="value">{fmt(last_close)}</div></div>
    <div class="cell"><div class="label">今开</div><div class="value">{fmt(open_px)}</div></div>
    <div class="cell"><div class="label">最新价（{symbol}）</div><div class="value">{fmt(last_px)}</div></div>
    <div class="cell"><div class="label">涨跌幅</div><div class="value chg">{chg_sign}{fmt(chg_pct)}%</div></div>
  </div>
  <div class="grid" style="margin-top:12px;">
    <div class="cell"><div class="label">最高 / 最低</div><div class="value">{fmt(high_px)} / {fmt(low_px)}</div></div>
    <div class="cell"><div class="label">主力-持仓价差</div><div class="value">{fmt(spread_val)} 点{'' if not liq_warning else ' <span class="warn">流动性告警</span>'}</div></div>
  </div>
</section>

<section>
  <h2>技术指标</h2>
  <table>
    <tr><th>均线</th><th>数值</th><th>状态</th></tr>
    <tr><td>MA5</td><td>{fmt(ma5)}</td><td>{'价格上方' if (last_px and ma5 and last_px > ma5) else '价格下方'}</td></tr>
    <tr><td>MA10</td><td>{fmt(ma10)}</td><td>{'价格上方' if (last_px and ma10 and last_px > ma10) else '价格下方'}</td></tr>
    <tr><td>MA20</td><td>{fmt(ma20)}</td><td>{'价格上方' if (last_px and ma20 and last_px > ma20) else '价格下方'}</td></tr>
    <tr><td>MA60</td><td>{fmt(ma60)}</td><td>{'价格上方' if (last_px and ma60 and last_px > ma60) else '价格下方'}</td></tr>
    <tr><td>排列</td><td colspan="2" style="color:{ma_align_color};font-weight:600;">{ma_align}</td></tr>
  </table>
  <table>
    <tr><th>指标</th><th>DIF</th><th>DEA</th><th>HIST</th><th>状态</th></tr>
    <tr><td>MACD</td><td>{fmt(macd_dif)}</td><td>{fmt(macd_dea)}</td><td style="color:{macd_color};">{fmt(macd_hist)}</td><td style="color:{macd_color};font-weight:600;">{macd_text}</td></tr>
  </table>
  <table>
    <tr><th>指标</th><th>数值</th><th>状态</th></tr>
    <tr><td>RSI14</td><td>{fmt(rsi14)}</td><td style="color:{rsi14_color};font-weight:600;">{rsi14_state}</td></tr>
    <tr><td>RSI6</td><td>{fmt(rsi6) if rsi6 is not None else '数据源未提供'}</td><td>—</td></tr>
  </table>
</section>

<section>
  <h2>关键价位</h2>
  <div style="margin-bottom:8px;"><span style="color:#7f8c8d;font-size:12px;">前高 / 前低：</span><span style="font-size:18px;font-weight:600;">{fmt(high_px)} / {fmt(low_px)}</span></div>
  <table>
    <tr><th>类型</th><th>价位 1</th><th>价位 2</th><th>价位 3</th></tr>
    <tr><td>阻力位</td><td style="color:#e74c3c;">{fmt(resistances[0]) if len(resistances)>0 else '—'}</td><td style="color:#e74c3c;">{fmt(resistances[1]) if len(resistances)>1 else '—'}</td><td style="color:#e74c3c;">{fmt(resistances[2]) if len(resistances)>2 else '—'}</td></tr>
    <tr><td>支撑位</td><td style="color:#27ae60;">{fmt(supports[0]) if len(supports)>0 else '—'}</td><td style="color:#27ae60;">{fmt(supports[1]) if len(supports)>1 else '—'}</td><td style="color:#27ae60;">{fmt(supports[2]) if len(supports)>2 else '—'}</td></tr>
  </table>
</section>

<section>
  <h2>盘前观点</h2>
  <div class="view">{one_liner}</div>
</section>

<footer>云端测试 · 数据来源 114.55.55.139/ic500/ · 本报告由 GitHub Actions 自动化生成，仅供测试参考</footer>
</div>
</body>
</html>
"""

    summary = {
        "trade_date": trade_date,
        "date_dash": date_dash,
        "symbol": symbol,
        "last_close": last_close,
        "open": open_px,
        "high": high_px,
        "low": low_px,
        "last": last_px,
        "change_pct": chg_pct,
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
        "macd_dif": macd_dif, "macd_dea": macd_dea, "macd_hist": macd_hist,
        "rsi14": rsi14,
        "supports": supports, "resistances": resistances,
        "is_trading": is_trading,
    }
    return html, date_compact, summary


def main():
    dry_run = "--dry-run" in sys.argv

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log(f"输出目录: {OUTPUT_DIR}")
    log(f"数据源: {DATA_URL}")

    # 1. 下载
    try:
        data = download_json()
    except RuntimeError as e:
        log(f"严重错误: {e}")
        sys.exit(1)

    # 2. 生成
    html, date_compact, summary = build_report(data)

    # 3. 输出摘要
    log("=" * 50)
    log("【云端解析摘要】")
    for k, v in summary.items():
        log(f"  {k:14s} = {v}")
    log("=" * 50)

    if dry_run:
        log("dry-run 模式，不写文件")
        return

    # 4. 写文件（带 _cloud 后缀）
    html_path = os.path.join(OUTPUT_DIR, f"ic500_cloud_test_{date_compact}.html")
    json_path = os.path.join(OUTPUT_DIR, f"ic500_cloud_summary_{date_compact}.json")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log(f"HTML 报告: {html_path}")
    log(f"数据摘要: {json_path}")
    log("云端测试版生成完成 ✓")


if __name__ == "__main__":
    main()
