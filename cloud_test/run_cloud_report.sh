#!/bin/bash
# ============================================================
# IC500 云端测试版 - 本地定时执行入口
# ------------------------------------------------------------
# 用法：
#   ./run_cloud_report.sh premarket   # 盘前
#   ./run_cloud_report.sh postclose   # 盘后
#   ./run_cloud_report.sh swing       # 中长线五日预判
#
# 功能：
#   1. 调用 LLM 生成报告
#   2. 自动 commit + push 到 Git 仓库
#
# 环境变量（在脚本同目录的 .env 文件中配置，或直接写死）：
#   LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SLOT="$1"
if [ -z "$SLOT" ]; then
  echo "用法: $0 {premarket|postclose|swing}"
  exit 1
fi

# 加载 .env（如果存在）
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "========================================"
echo "IC500 云端报告生成 - 时段: $SLOT"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 1. 生成报告
python3 generate_with_llm.py --slot "$SLOT"

echo ""
echo "===== 提交到仓库 ====="

# 2. 提交并推送
git config user.name "IC500 Cloud Bot"
git config user.email "cloud-bot@ic500.local"
git add output/

if git diff --cached --quiet; then
  echo "无新产物，跳过 commit"
else
  git commit -m "[cloud] IC500 ${SLOT} 报告 $(date +%Y%m%d)"
  if git push origin main 2>&1; then
    echo "✅ 推送成功"
  else
    echo "❌ 推送失败，请检查 Git 凭据和远程仓库配置"
    exit 1
  fi
fi

echo ""
echo "✅ 完成: $SLOT 报告已生成并推送"
