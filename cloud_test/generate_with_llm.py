#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IC500 云端报告生成器（LLM 驱动）
================================
与本地 TRAE 原理一致：读取 skill 规则文档 + 实时行情数据，
调用 LLM API 生成 HTML 报告。

用法：
  python3 generate_with_llm.py --slot premarket   # 盘前（日内短线）
  python3 generate_with_llm.py --slot postclose   # 盘后（日内短线）
  python3 generate_with_llm.py --slot swing       # 中长线五日预判

环境变量：
  LLM_API_KEY    - LLM API Key（必填）
  LLM_BASE_URL   - API 地址（默认 https://api.openai.com/v1）
  LLM_MODEL      - 模型名（默认 gpt-4o-mini）
  DATA_URL       - 数据源地址（有默认值）

隔离保证：
  - 仅从 114.55.55.139 读取数据
  - 产物写入 cloud_test/output/，文件名带 _cloud 后缀
  - 规则文件读取自 cloud_test/skills/
"""
import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

DEFAULT_DATA_URL = "http://114.55.55.139/ic500/download_json.php?file=live_summary.json"
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-4o-mini"

# 各时段对应的规则文件和系统提示
SLOT_CONFIG = {
    "premarket": {
        "name": "盘前",
        "skill_files": [
            "daytrading/SKILL.md",
            "daytrading/references/daily_workflow.md",
            "futures-analysis/TRADING_RULES.md",
            "futures-analysis/OUTPUT_FORMAT.md",
        ],
        "trigger_words": "盘前分析 / 次日计划",
        "output_suffix": "morning",
        "system_hint": "你是 IC500 中证500股指期货盘前分析专家。请严格按照提供的 Skill 规则，基于实时行情数据生成盘前简报 HTML 报告。",
    },
    "swing": {
        "name": "中长线五日预判",
        "skill_files": [
            "swing-trading/SKILL.md",
            "swing-trading/references/market_regime.md",
            "swing-trading/references/trend_analysis.md",
            "swing-trading/references/price_levels.md",
            "swing-trading/references/position_management.md",
            "futures-analysis/TRADING_RULES.md",
            "futures-analysis/OUTPUT_FORMAT.md",
        ],
        "trigger_words": "中长线分析 / 波段交易 / 五日预判 / 多日持仓",
        "output_suffix": "swing",
        "system_hint": "你是 IC500 中证500股指期货中长线趋势分析专家。请严格按照提供的 Skill 规则（五步法：市场体制判定→趋势持续性评估→关键价位→交易方案→持仓管理），基于日线级别行情数据生成 3-10 天中长线五日预判 HTML 报告。",
    },
    "postclose": {
        "name": "盘后",
        "skill_files": [
            "daytrading/SKILL.md",
            "daytrading/references/daily_workflow.md",
            "daytrading/references/trend_verdict.md",
            "daytrading/references/execution_playbook.md",
            "daytrading/references/pattern_traps.md",
            "futures-analysis/TRADING_RULES.md",
            "futures-analysis/OUTPUT_FORMAT.md",
        ],
        "trigger_words": "盘后复盘 / 日终复盘",
        "output_suffix": "postclose",
        "system_hint": "你是 IC500 中证500股指期货盘后复盘专家。请严格按照提供的 Skill 规则，基于实时行情数据生成完整的盘后复盘 HTML 报告（包含10大板块）。",
    },
}


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [cloud-llm] {msg}", flush=True)


def download_json(url, max_retry=3, delay=5, timeout=30):
    last_err = None
    for attempt in range(1, max_retry + 1):
        try:
            log(f"下载数据（第 {attempt}/{max_retry} 次）...")
            req = urllib.request.Request(url, headers={"User-Agent": "IC500-CloudTest/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            log(f"下载成功，{len(raw)} 字节")
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
            last_err = e
            log(f"下载失败: {e}")
            if attempt < max_retry:
                time.sleep(delay)
    raise RuntimeError(f"数据下载失败: {last_err}")


def load_skill_files(slot):
    """读取该时段所需的所有规则文件，合并为一个大字符串。"""
    config = SLOT_CONFIG[slot]
    parts = []
    for rel_path in config["skill_files"]:
        full_path = os.path.join(SKILLS_DIR, rel_path)
        if not os.path.exists(full_path):
            log(f"⚠ 规则文件缺失: {rel_path}（将跳过，可能影响报告质量）")
            continue
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        parts.append(f"===== {rel_path} =====\n{content}")
    if not parts:
        raise RuntimeError(f"时段 {slot} 没有可用的规则文件，请将 skill 文件放入 {SKILLS_DIR}/")
    return "\n\n".join(parts)


def call_llm(api_key, base_url, model, system_prompt, user_prompt, max_tokens=16000):
    """调用 OpenAI 兼容的 LLM API。"""
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    log(f"调用 LLM: model={model}, base_url={base_url}")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API 错误 {e.code}: {body[:500]}")
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败: {e}")

    elapsed = time.time() - start
    content = result["choices"][0]["message"]["content"]
    log(f"LLM 返回成功，耗时 {elapsed:.1f}s，输出 {len(content)} 字符")
    return content


def extract_html(text):
    """从 LLM 输出中提取 HTML（可能被 markdown 代码块包裹）。"""
    text = text.strip()
    # 去掉 ```html ... ``` 包裹
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首行 ```html 或 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # 去掉末尾 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def main():
    parser = argparse.ArgumentParser(description="IC500 云端 LLM 报告生成器")
    parser.add_argument("--slot", required=True, choices=["premarket", "swing", "postclose"],
                        help="时段: premarket(盘前) / swing(中长线) / postclose(盘后)")
    parser.add_argument("--dry-run", action="store_true", help="只构建 prompt 不调用 LLM")
    args = parser.parse_args()

    slot = args.slot
    config = SLOT_CONFIG[slot]

    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    model = os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL)
    data_url = os.environ.get("DATA_URL", DEFAULT_DATA_URL)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not api_key and not args.dry_run:
        log("错误: 未设置 LLM_API_KEY 环境变量")
        sys.exit(1)

    # 1. 下载数据
    data = download_json(data_url)
    trade_date = data.get("trade_date", datetime.now().strftime("%Y%m%d"))
    try:
        date_compact = datetime.strptime(str(trade_date), "%Y%m%d").strftime("%Y%m%d")
    except Exception:
        date_compact = str(trade_date)

    # 2. 加载规则
    log(f"加载 {config['name']} 时段规则文件...")
    rules = load_skill_files(slot)
    log(f"规则文本总长度: {len(rules)} 字符")

    # 3. 构建 prompt
    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    system_prompt = config["system_hint"] + "\n\n输出要求：直接返回完整的 HTML 报告（<!DOCTYPE html> 开头，</html> 结尾），不要任何解释文字。HTML 需包含完整的 CSS 样式，中文内容，适合移动端阅读。页脚标注：云端测试 · 数据来源 114.55.55.139/ic500/"

    user_prompt = f"""【交易时段】{config['name']}（{config['trigger_words']}）
【交易日期】{trade_date}

===== Skill 规则文档 =====
{rules}

===== 实时行情数据（JSON）=====
{data_json}

请根据以上规则和数据，生成 {config['name']} 报告的完整 HTML。"""

    if args.dry_run:
        prompt_path = os.path.join(OUTPUT_DIR, f"prompt_{config['output_suffix']}_{date_compact}.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(f"=== SYSTEM ===\n{system_prompt}\n\n=== USER ===\n{user_prompt}")
        log(f"dry-run: prompt 已保存到 {prompt_path}")
        return

    # 4. 调用 LLM
    try:
        response = call_llm(api_key, base_url, model, system_prompt, user_prompt)
    except RuntimeError as e:
        log(f"严重错误: {e}")
        sys.exit(1)

    # 5. 提取并保存 HTML（注入 Vercel Analytics）
    html = extract_html(response)
    if not html.startswith("<!DOCTYPE") and not html.startswith("<html"):
        log("⚠ 警告: LLM 输出不以 HTML 标签开头，可能格式有误")

    # 注入 Vercel Analytics 脚本（在 </body> 或 </html> 前）
    analytics_script = '<script defer src="https://cdn.vercel-analytics.com/v1/script.js" data-token="ic500-weiyivip"></script>'
    if "</body>" in html:
        html = html.replace("</body>", f"{analytics_script}\n</body>")
    elif "</html>" in html:
        html = html.replace("</html>", f"{analytics_script}\n</html>")
    else:
        html = html + analytics_script

    out_path = os.path.join(OUTPUT_DIR, f"ic500_cloud_{config['output_suffix']}_{date_compact}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    log(f"报告已生成: {out_path}")
    log(f"文件大小: {len(html)} 字符")


if __name__ == "__main__":
    main()
