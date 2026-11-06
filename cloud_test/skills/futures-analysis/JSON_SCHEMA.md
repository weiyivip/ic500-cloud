# IC500期货数据格式说明（live_summary.json结构）

## 使用说明

本文件详细说明了live_summary.json的所有字段及其含义。

---

## 数据时效性说明（重要）

**盘中分析（09:30-15:00）**：
- `multi_period_features`：✅ 实时数据（TqSDK 订阅，可用于盘中分析）
- `tick_analysis`：✅ 实时数据（TqSDK 订阅，可用于盘中分析）
- `database_data.daily_features`：❌ **历史数据**（昨天及以前，仅用于参考，不可用于盘中决策）
- `database_data.basis_features`：❌ **历史数据**（最近一个交易日）
- `database_data.valuation_features`：❌ **历史数据**（最近一个交易日）

**盘后分析（20:00采集后）**：
- 所有数据均为当天数据，可用于分析

**数据采集时间线**：
- 09:30-15:00：盘中交易时间
- 15:00-15:05：live_service.py 强制保存收盘数据
- 19:00：数据采集入库（`ic_future_daily`、`zz500_index_daily` 等表）

---

## 一、顶层字段

- **timestamp**: 生成时间（格式：YYYY-MM-DD HH:MM:SS，北京时间UTC+8）
- **trade_date**: 交易日期（格式：YYYYMMDD）
- **is_trading**: 是否交易时段（true/false）

---

## 二、价格信息（price）

- **current**: 当前价格
- **open**: 开盘价
- **high**: 最高价
- **low**: 最低价
- **pre_close**: 昨收价
- **change_pct**: 涨跌幅（%）

---

## 三、均线信息（ma - 分钟线）

- **ma5/ma10/ma20/ma60**: 5/10/20/60周期均线值
- **above_ma5/above_ma10/above_ma20**: 是否站在均线上方（true/false）

---

## 四、技术指标（indicators - 分钟线聚合）

- **macd.macd**: MACD值
- **macd.signal**: 信号线值
- **macd.hist**: MACD柱状值
- **macd.status**: MACD状态（bull/bear/cross_up/cross_down）
- **rsi14**: 14周期RSI值（0-100，分钟线聚合值）
- **volume_ratio**: 量比（当前 K 线成交量 / 最近20根 K 线成交量均值）
  - **注意**：盘中实时计算，可能因当前 K 线成交量低而出现 0.0 或极小值
  - **建议**：结合 `oi_change` 判断资金流向，而非单独使用
- **atr**: ATR（平均真实波幅）对象
  - **value**: ATR 值（点数）
  - **pct**: ATR 占价格百分比（ATR / close × 100）
  - **用途**：
    - 止损计算：震荡行情止损 0.15-0.25 ATR，趋势行情止损 0.25-0.4 ATR
    - 波动率判断：ATR > 50 点为高波动，< 20 点为低波动
  - **计算周期**：14（行业标准）

**注意**：`indicators.rsi14` 是分钟线聚合的 RSI 值，与 `multi_period_features.Xmin.rsi.value` 不同。
- `indicators.rsi14`：用于判断整体 RSI 状态（日线级别分析）
- `multi_period_features.Xmin.rsi.value`：用于判断特定周期的 RSI 状态（多周期分析）

---

## 五、支撑阻力位（support_resistance）

- **supports**: 支撑位数组（从强到弱）
- **resistances**: 阻力位数组（从弱到强）

---

## 六、成交量信息（volume）

- **total**: 累计成交量
- **kline_count**: 已生成的K线数量

---

## 七、趋势判断（trend - 分钟线）

- **direction**: 趋势方向（up/down/sideways）
- **strength**: 趋势强度（strong/medium/weak）
- **alert**: 特殊提醒（如超买超卖警告）
- **rsi_status**: RSI状态（oversold/overbought/normal）

---

## 八、持有合约信息（holding_contract - 双合约架构）

- **symbol**: 持有合约代码（如IC2609）
- **price.current**: 持有合约当前价格（实际可操作价格）
- **price.open/high/low**: 持有合约开盘价/最高价/最低价
- **volume**: 持有合约成交量
- **open_interest**: 持有合约持仓量

**说明**：
- **持有合约**用于实际操作，提供真实的可执行价格
- **主力合约**（price字段）用于技术分析，提供完整的历史数据和趋势判断
- 所有价格建议会根据基差自动调整为持有合约的价格

---

## 九、基差信息（spread）

- **main_price**: 主力合约价格
- **holding_price**: 持有合约价格
- **spread**: 价差（点数）= 主力合约价格 - 持有合约价格
  - 负数：持有合约价格更高（升水）
  - 正数：持有合约价格更低（贴水）
- **spread_pct**: 价差百分比（%）
- **volume_ratio**: 流动性比率（持有合约成交量/主力合约成交量）
  - >0.3: 流动性良好，滑点风险低
  - <0.3: 流动性不足，滑点风险高
- **liquidity_warning**: 流动性警告（true/false）
  - true: 成交量不足，建议减小仓位

**价格修正说明**：
- 所有技术分析基于主力合约
- 所有操作建议基于持有合约
- 价格建议会自动修正：持有合约价格 = 主力合约价格 - 基差

---

## 十、到期提醒（expiry）

- **symbol**: 合约代码
- **expiry_date**: 到期日期（YYYY-MM-DD）
- **days_to_expiry**: 距离到期天数
- **expiring**: 是否即将到期（距离到期≤10天时为true）
- **warning**: 到期警告信息（即将到期时显示）

**到期处理**：
- 提前10天开始提醒
- 需要手动修改配置文件切换合约
- 参考config.py中的HOLDING_SYMBOL和HOLDING_EXPIRY_DATE

---

## 十一、外盘数据（intl_market_quotes）

### 数据说明

外盘数据用于A股开盘前参考，采集时间：每天上午08:00（北京时间）。

**数据来源**：TqSDK外盘行情（延时15分钟）

**数据时效性**：
- 盘中分析（09:30-15:00）：✅ 可用（开盘前采集）
- 盘后分析：✅ 可用（全天有效）

**主要用途**：
- A股开盘前预判
- 隔夜全球市场情绪参考
- 外资态度判断

---

### 字段说明

#### 1. A50指数（a50）- 最重要

- **symbol**: 合约代码（KQD.m@SGX.CN）
- **exchange**: 交易所（SGX）
- **market_name**: 市场名称（A50指数（新加坡））
- **last_price**: 最新价格
- **pre_close**: 昨收盘价
- **change_pct**: 涨跌幅（%）
  - >0.5%: A股大概率高开
  - <-0.5%: A股大概率低开
  - 其他: A股平开
- **amplitude_pct**: 振幅（%）
  - >2%: 高波动
  - <1%: 低波动
- **gap_pct**: 开盘跳空幅度（%）
  - >0.3%: 强势开盘
  - <-0.3%: 弱势开盘
- **quote_time**: 行情时间（北京时间）

**核心价值**：A50夜盘数据是A股开盘最直接的参考指标。

---

#### 2. 港股恒指（hsi）

- **symbol**: 合约代码（KQD.m@HKFE.HSI）
- **exchange**: 交易所（HKFE）
- **market_name**: 市场名称（恒生指数（港股））
- **last_price**: 最新价格
- **change_pct**: 涨跌幅（%）
- **quote_time**: 行情时间（北京时间）

**核心价值**：反映外资对A股的态度。

**注意**：
- 港股09:30开盘
- 08:00采集的数据是**前一日收盘数据**
- 主要用于判断外资整体态度，不用于精确预判

---

#### 3. 中国A50（china_a50）

- **symbol**: 合约代码（KQD.m@HKFE.MCA）
- **exchange**: 交易所（HKFE）
- **market_name**: 市场名称（中国A50（港股））
- **last_price**: 最新价格
- **change_pct**: 涨跌幅（%）

**核心价值**：补充A50指数，双重验证。

---

#### 4. 标普500（sp500）

- **symbol**: 合约代码（KQD.m@CME.ES）
- **exchange**: 交易所（CME）
- **market_name**: 市场名称（标普500（美股））
- **last_price**: 最新价格
- **change_pct**: 涨跌幅（%）

**核心价值**：隔夜美股走势，影响A股开盘情绪。

**注意**：美股在北京时间凌晨04:00收盘。

---

#### 5. 纳斯达克（nasdaq）

- **symbol**: 合约代码（KQD.m@CME.NQ）
- **exchange**: 交易所（CME）
- **market_name**: 市场名称（纳斯达克（美股））
- **last_price**: 最新价格
- **change_pct**: 涨跌幅（%）

**核心价值**：科技股走势，对IC（成长股）影响较大。

---

#### 6. 道琼斯（dow）

- **symbol**: 合约代码（KQD.m@CBOT.YM）
- **exchange**: 交易所（CBOT）
- **market_name**: 市场名称（道琼斯（美股））
- **last_price**: 最新价格
- **change_pct**: 涨跌幅（%）

**核心价值**：大盘股走势，反映传统行业表现。

---

#### 7. 罗素2000（russell2000）

- **symbol**: 合约代码（KQD.m@CME.RTY）
- **exchange**: 交易所（CME）
- **market_name**: 市场名称（罗素2000（美股））
- **last_price**: 最新价格
- **change_pct**: 涨跌幅（%）

**核心价值**：美股小盘股走势，与IC（中小盘股指）相关性高。

---

#### 8. 离岸人民币（usdcnh）

- **symbol**: 合约代码（KQD.m@SGX.UC）
- **exchange**: 交易所（SGX）
- **market_name**: 市场名称（离岸人民币）
- **last_price**: 最新价格（如6.7489）
- **change_pct**: 涨跌幅（%）
  - 正值：人民币贬值
  - 负值：人民币升值

**核心价值**：汇率对A股的影响（人民币贬值利空A股）。

---

#### 9. 美元指数（dxy）

- **symbol**: 合约代码（KQD.m@NYBOT.DX）
- **exchange**: 交易所（NYBOT）
- **market_name**: 市场名称（美元指数）
- **last_price**: 最新价格
- **change_pct**: 涨跌幅（%）

**核心价值**：美元强弱对全球资产配置的影响。

---

### 使用建议

#### 开盘前分析（09:00-09:30）

**优先级排序**：
1. **A50指数**：最直接的A股开盘参考
2. **港股恒指**：外资态度判断
3. **罗素2000**：小盘股风险偏好（与IC相关）
4. **标普500/纳斯达克**：隔夜美股情绪
5. **离岸人民币**：汇率影响

**综合判断方法**：
- A50涨跌幅 >0.3% + 港股涨 >0 → A股偏多
- A50涨跌幅 <-0.3% + 港股跌 >-0.3% → A股偏空
- 其他情况 → A股震荡

---

#### 盘中分析（09:30-15:00）

外盘数据主要作为**辅助参考**，不作为核心决策依据。

**使用场景**：
- 验证开盘预判的准确性
- 监控外盘走势变化（如A50日盘走势）
- 调整风险偏好

---

## 十二、数据库历史数据（database_data）

### 1. 日线特征（daily_features）

- **future**: 期货日线特征（均线、MACD、RSI、布林带、成交量）
- **index**: 中证500指数日线特征（均线、MACD、RSI、布林带、成交量）

---

### 2. 5分钟周期特征（5min - 实时数据）

- **price**: 当前价格、最高价、最低价
- **ma**: 均线（MA5、MA10、MA20）、均线排列方向、价格位置
- **macd**: MACD指标（macd、signal、hist、status）
- **rsi**: RSI指标对象
  - **rsi.value**: RSI值（0-100）
  - **rsi.status**: RSI状态（overbought/oversold/normal）
- **volume**: 成交量（当前成交量、20周期平均成交量）

---

### 3. 多周期特征（multi_period_features）

- **30min**: 30分钟周期特征
  - 均线（MA5、MA10、MA20、MA60）
  - MACD指标（macd、signal、hist、status）
  - RSI指标对象（rsi.value、rsi.status）
  - 布林带（band.high、band.low、band.position、band.trend、band.strength）
- **60min**: 60分钟周期特征（结构同30min）
- **180min**: 180分钟周期特征（结构同30min）

**注意**：所有周期的 RSI 都是对象结构（rsi.value、rsi.status），与 indicators.rsi14 不同。

---

### 4. 基差特征（basis_features）

- **current_basis**: 当前基差（期货价格-现货价格）
- **basis_rate**: 基差率（%）
- **basis_percentile**: 基差历史分位数（0-100）
- **basis_level**: 基差水平（high/medium/low）

---

### 5. 估值特征（valuation_features）

- **pe.value**: 市盈率（PE）
- **pe.percentile**: PE历史分位数（0-100）
- **pe.status**: PE状态（overvalued/fair/undervalued）
- **pb.value**: 市净率（PB）
- **pb.percentile**: PB历史分位数（0-100）
- **pb.status**: PB状态（overvalued/fair/undervalued）

---

### 6. 综合评分（composite_score - 五维量化打分）

**注意：这是独立于五层周期的评分系统**

- **total_score**: 综合得分（0-100）
- **market_type**: 市场类型（bull/bear/sideways）
- **market_desc**: 市场描述（中文）
- **dimensions**: 各维度得分
  - **basis_index**: 基差分析得分
  - **volume_price**: 量价关系得分
  - **capital_flow**: 资金流向得分
  - **volatility**: 波动率得分
  - **oversold_correct**: 超买超卖得分

---

### 7. 资金流向（capital_flow）

- **north_money**: 北向资金数据
- **margin**: 融资融券数据

---

### 8. 近期日线数据（recent_daily）

最近5个交易日的日线数据（开盘、最高、最低、收盘、成交量、持仓量、涨跌幅、振幅）

---

### 9. Tick分析（tick_analysis）

- **oi_change**: 持仓量变化
- **oi_trend**: 持仓趋势（increase/decrease/stable）
- **buy_sell_ratio**: 买卖比例
- **volume_trend**: 成交量趋势（expand/shrink/stable）
- **market_quality**: 市场质量（trend/fake_breakout/oscillation）

---

### 10. 中证500指数数据（zz500_index）

中证500指数的日线数据（开盘、最高、最低、收盘、成交量、均线等）

---

## 十二、数据使用注意事项

1. **时区**：所有时间为北京时间（UTC+8）
2. **价格单位**：指数点
3. **成交量单位**：手数
4. **持仓量单位**：手数
5. **数据来源**：
   - 实时数据：TqSDK
   - 历史数据：数据库
6. **更新频率**：盘中每分钟更新一次