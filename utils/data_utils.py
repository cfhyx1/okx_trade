
"""
数据处理工具模块，提供数据转换和处理功能
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union

def parse_candlesticks_data(candlesticks_data: List[List]) -> pd.DataFrame:
    """
    将OKX返回的K线数据转换为DataFrame（兼容 OKX 不同列数返回）

    Args:
        candlesticks_data: OKX API返回的K线数据，是一个二维列表

    Returns:
        包含K线数据的DataFrame，列名为:
        - timestamp: 时间戳
        - open: 开盘价
        - high: 最高价
        - low: 最低价
        - close: 收盘价
        - volume: 成交量
        - volume_ccy: 成交额
    """
    # 定义目标列名（保留前7列）
    columns = ["timestamp", "open", "high", "low", "close", "volume", "volume_ccy"]

    # 规范化输入：只取每行的前7个值，若不足则用 None 填充；忽略非序列行
    normalized = []
    for row in candlesticks_data or []:
        if not isinstance(row, (list, tuple)):
            continue
        sliced = list(row[:7])
        if len(sliced) < 7:
            sliced += [None] * (7 - len(sliced))
        normalized.append(sliced)

    # 若没有数据则返回空 DataFrame
    if not normalized:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(normalized, columns=columns)

    # 转换数据类型（容错）
    for col in ["open", "high", "low", "close", "volume", "volume_ccy"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 将时间戳转换为datetime（容错）
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors='coerce')

    # 设置timestamp为索引
    df.set_index("timestamp", inplace=True)

    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算常用技术指标，仅使用pandas和numpy，不依赖TA-Lib

    Args:
        df: 包含OHLCV数据的DataFrame

    Returns:
        添加了技术指标的DataFrame
    """
    # 计算简单移动平均线
    df["sma_5"] = df["close"].rolling(window=5).mean()
    df["sma_10"] = df["close"].rolling(window=10).mean()
    df["sma_20"] = df["close"].rolling(window=20).mean()
    df["sma_50"] = df["close"].rolling(window=50).mean()

    # 计算指数移动平均线
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()

    # 计算MACD
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    # 计算RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # 计算布林带
    df["bb_middle"] = df["close"].rolling(window=20).mean()
    bb_std = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
    df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

    # 计算ATR (平均真实波幅)
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df["atr"] = true_range.rolling(window=14).mean()

    return df

def format_position_data(position: Dict) -> Dict:
    """
    格式化持仓数据，使其更易读

    Args:
        position: 原始持仓数据

    Returns:
        格式化后的持仓数据
    """
    formatted = {
        "交易对": position.get("instId", ""),
        "持仓方向": position.get("posSide", ""),
        "持仓数量": float(position.get("pos", 0)),
        "持仓均价": float(position.get("avgPx", 0)),
        "当前价格": float(position.get("markPx", 0)),
        "浮动盈亏": float(position.get("upl", 0)),
        "实现盈亏": float(position.get("pnl", 0)),
        "保证金": float(position.get("margin", 0)),
        "杠杆": position.get("lever", ""),
        "保证金模式": position.get("mgnMode", ""),
        "更新时间": position.get("uTime", "")
    }

    return formatted

def format_balance_data(balance: Dict) -> Dict:
    """
    格式化账户余额数据，使其更易读

    Args:
        balance: 原始余额数据

    Returns:
        格式化后的余额数据
    """
    formatted = {
        "账户类型": balance.get("acctLv", ""),
        "账户余额": float(balance.get("bal", 0)),
        "账户总资产": float(balance.get("eq", 0)),
        "账户权益(USDT)": float(balance.get("eqUsd", 0)),
        "保证金": float(balance.get("imr", 0)),
        "未实现盈亏": float(balance.get("ival", 0)),
        "最大可借": float(balance.get("maxLoan", 0)),
        "保证金率": float(balance.get("mgnRatio", 0)),
        "持仓保证金": float(balance.get("margin", 0)),
        "更新时间": balance.get("uTime", "")
    }

    return formatted
