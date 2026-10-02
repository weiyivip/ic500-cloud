#!/bin/bash
# ============================================================
# IC500 云端测试版 - 生成报告 + 部署到 Vercel
# ------------------------------------------------------------
# 用法：
#   ./deploy_to_vercel.sh premarket   # 盘前
#   ./deploy_to_vercel.sh postclose   # 盘后
#   ./deploy_to_vercel.sh swing       # 中长线
#
# 前提：服务器上已安装 vercel CLI 并登录
#   npm i -g vercel
#   vercel login
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SLOT="$1"
if [ -z "$SLOT" ]; then
  echo "用法: $0 {premarket|postclose|swing}"
  exit 1
fi

# 加载 .env
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "========================================"
echo "IC500 云端报告 - 时段: $SLOT"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 1. 生成报告
python3 generate_with_llm.py --slot "$SLOT"

echo ""
echo "===== 部署到 Vercel ====="

# 2. 部署 output 目录到 Vercel
cd output
vercel --prod --yes 2>&1 | tee /tmp/vercel_deploy.log

# 提取部署 URL
DEPLOY_URL=$(grep -oP 'https://[^\s]+\.vercel\.app' /tmp/vercel_deploy.log | head -1)
echo ""
echo "✅ 部署完成"
echo "报告地址: ${DEPLOY_URL}"
echo "自定义域名: https://ic500.weiyivip.top/"
