
# OKX API配置
# 请在OKX官网申请API密钥，并填入以下字段
API_KEY = ""  # OKX API密钥
SECRET_KEY = ""  # OKX API密钥
PASSPHRASE = ""  # OKX API口令

# 交易配置
TRADING_MODE = "cross"  # 交易模式: cross(全仓) 或 isolated(逐仓)
LEVERAGE = 10  # 杠杆倍数
POSITION_SIZE = 0.01  # 每次交易的数量(BTC)
STOP_LOSS_PERCENT = 0.02  # 止损百分比，例如0.02表示2%
TAKE_PROFIT_PERCENT = 0.04  # 止盈百分比，例如0.04表示4%

# 交易对配置
TRADING_PAIR = "BTC-USDT-SWAP"  # 交易对，SWAP表示永续合约
TIMEFRAME = "1H"  # K线周期，1H表示1小时K线

# 策略参数
STRATEGY_PARAMS = {
    "short_ma": 5,   # 短期均线周期
    "long_ma": 20,   # 长期均线周期
    "rsi_period": 14,  # RSI周期
    "rsi_overbought": 70,  # RSI超买阈值
    "rsi_oversold": 30,    # RSI超卖阈值
}

# 日志配置
LOG_LEVEL = "INFO"  # 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "logs/trading.log"  # 日志文件路径
