# IC500 API Configuration

## API Endpoints

### Production URLs (Replace with your actual domain)
```
Base URL: http://114.55.55.139/ic500

# 推荐路径（盘中分析）：直接下载最新文件
GET http://114.55.55.139/ic500/download_json.php?file=live_summary.json

# 可选路径：获取文件列表（包含元信息）
GET http://114.55.55.139/ic500/get_latest_json.php

# Get latest N files
GET http://114.55.55.139/ic500/get_latest_json.php?count=10

# Get all files
GET http://114.55.55.139/ic500/get_latest_json.php?all=true

# Download specific JSON file
GET http://114.55.55.139/ic500/download_json.php?file=<filename>

# View file list (HTML)
GET http://114.55.55.139/ic500/json_viewer.php
```

## Data Files

### Required Files

1. **live_summary.json** - 最新盘面摘要数据
   - 包含实时价格、技术指标、趋势判断等
   - 包含双合约数据（主力合约+持有合约）
   - 包含基差信息和到期提醒
   - 通过API自动获取，无需手动配置路径

2. **live_summary_YYYYMMDD_HHMM.json** - 历史盘面数据
   - 按时间戳保存的历史记录
   - 用于历史数据分析和回测

3. **prompt_output.txt** - 生成的提示词输出
   - 由live_service.py自动生成
   - 包含完整的交易分析建议
   - 包含持有合约价格修正说明

### Prompt Template

提示词模板已完整嵌入到SKILL.md中，包含：
- 盘中盯盘系统规则
- 盘后复盘系统规则
- 数据格式说明
- 输出要求

## Usage in Skill

When this skill is invoked, the AI should:

1. **Fetch Data（推荐路径）**
   ```bash
   # 盘中分析：直接下载最新文件（一步法）
   curl http://114.55.55.139/ic500/download_json.php?file=live_summary.json
   ```

2. **可选路径（需要文件元信息）**
   ```bash
   # 获取文件列表
   curl http://114.55.55.139/ic500/get_latest_json.php
   ```

3. **Parse Response**
   ```json
   {
     "success": true,
     "latest_file": {
       "filename": "live_summary_20260720_1430.json",
       "download_url": "http://114.55.55.139/ic500/download_json.php?file=...",
       "file_time": "2026-07-20 14:30:15"
     }
   }
   ```

4. **Download JSON（如果使用两步法）**
   ```bash
   curl "http://114.55.55.139/ic500/download_json.php?file=live_summary_20260720_1430.json"
   ```

5. **Apply Trading Rules**
   - AI会直接从SKILL.md中读取完整的交易规则
   - 根据时间判断使用盘中规则或盘后规则
   - 无需额外配置路径

6. **Generate Analysis**
   - Based on data and prompt rules
   - Follow the four-layer timeframe system
   - Apply five-dimensional scoring
   - Output standardized recommendations

## Response Format

### Success Response
```json
{
  "success": true,
  "latest_file": {
    "filename": "live_summary_20260720_1430.json",
    "download_url": "http://114.55.55.139/ic500/download_json.php?file=...",
    "file_time": "2026-07-20 14:30:15",
    "file_size": 12345,
    "file_size_readable": "12.05 KB"
  },
  "returned_count": 1,
  "total_count": 120,
  "files": [...]
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "data": null
}
```

## CORS Headers

All API endpoints include CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

## Rate Limiting

- No rate limiting currently implemented
- Please use responsibly
- Recommended: Maximum 1 request per minute

## Data Freshness

- **Update frequency**: Every minute during trading hours
- **Trading hours**: 09:30-11:30, 13:00-15:00 Beijing Time (UTC+8)
- **After hours**: Data not updated until next trading session

## Dual Contract Architecture

The system uses a dual contract architecture:

1. **Main Contract** (KQ.m@CFFEX.IC)
   - Purpose: Technical analysis
   - Benefits: Complete historical data, accurate trend analysis
   - Used for: 3H/60min/5min/Tick analysis

2. **Holding Contract** (e.g., IC2609)
   - Purpose: Actual trading operations
   - Benefits: Real executable prices, accurate liquidity information
   - Used for: Entry prices, stop-loss, target prices

3. **Basis Adjustment**
   - All technical analysis based on main contract
   - All operational recommendations based on holding contract
   - Price recommendations automatically adjusted: Holding Price = Main Price - Basis

## Contract Expiry Management

- Contracts are monitored for expiry
- Warning issued 10 days before expiry
- Manual contract switching required via config.py
- Update HOLDING_SYMBOL and HOLDING_EXPIRY_DATE in config.py

## Notes

1. API地址已配置为生产环境：`http://114.55.55.139/ic500`
2. 如需更换服务器，请修改所有文件中的API地址
3. Check file permissions for data directories
4. Monitor disk space for historical JSON files