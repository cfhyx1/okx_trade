
import pandas as pd
import numpy as np
from typing import Dict, Optional
from .base_strategy import BaseStrategy

class RSIStrategy(BaseStrategy):
    """RSI策略，基于相对强弱指标(RSI)的超买超卖信号进行交易"""

    def __init__(self, config: Dict):
        """
        初始化RSI策略

        Args:
            config: 策略配置，应包含STRATEGY_PARAMS字典，其中:
                - rsi_period: RSI计算周期，默认为14
                - rsi_overbought: RSI超买阈值，默认为70
                - rsi_oversold: RSI超卖阈值，默认为30
        """
        super().__init__(config)
        # 从配置中获取RSI参数
        self.period = config.get("STRATEGY_PARAMS", {}).get("rsi_period", 14)
        self.overbought = config.get("STRATEGY_PARAMS", {}).get("rsi_overbought", 70)
        self.oversold = config.get("STRATEGY_PARAMS", {}).get("rsi_oversold", 30)

    def calculate_rsi(self, data: pd.DataFrame) -> pd.Series:
        """
        计算RSI指标

        RSI (Relative Strength Index) 是一种动量指标，用于衡量价格变动的速度和变化，
        数值范围在0-100之间，通常认为:
        - RSI > 70: 超买区域，价格可能回调
        - RSI < 30: 超卖区域，价格可能反弹

        Args:
            data: K线数据，至少需要包含"close"列（收盘价）

        Returns:
            RSI序列，与输入数据长度相同
        """
        # 计算价格变化
        delta = data["close"].diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)  # 上涨部分，下跌部分设为0
        loss = -delta.where(delta < 0, 0)  # 下跌部分，上涨部分设为0

        # 计算平均涨跌幅，使用简单移动平均
        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()

        # 计算相对强弱(RS)和RSI值
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def generate_signal(self, data: pd.DataFrame) -> Optional[str]:
        """
        根据RSI指标生成交易信号

        当RSI从超卖区域(≤30)上升时生成买入信号，
        当RSI从超买区域(≥70)下降时生成卖出信号

        Args:
            data: K线数据，至少需要包含"close"列（收盘价）

        Returns:
            交易信号:
            - "buy": 当RSI从超卖区域上升时生成买入信号
            - "sell": 当RSI从超买区域下降时生成卖出信号
            - None: 无信号或数据不足
        """
        # 确保数据足够计算RSI
        if len(data) < self.period + 1:
            return None

        # 计算RSI指标
        data["rsi"] = self.calculate_rsi(data)

        # 获取最新和前一条数据
        latest = data.iloc[-1]
        prev = data.iloc[-2]

        # 判断RSI是否从超卖区域上升（买入信号）
        rsi_oversold_cross = (prev["rsi"] <= self.oversold and 
                             latest["rsi"] > self.oversold)

        # 判断RSI是否从超买区域下降（卖出信号）
        rsi_overbought_cross = (prev["rsi"] >= self.overbought and 
                               latest["rsi"] < self.overbought)

        # 根据信号返回交易方向
        if rsi_oversold_cross:
            return "buy"  # 从超卖区域上升，买入信号
        elif rsi_overbought_cross:
            return "sell"  # 从超买区域下降，卖出信号
        else:
            return None  # 无信号

    def validate_signal(self, signal: str, current_position: Optional[Dict]) -> bool:
        """
        验证交易信号是否有效，考虑当前持仓情况

        Args:
            signal: 交易信号，"buy" 或 "sell"
            current_position: 当前持仓信息，包含持仓方向等信息

        Returns:
            信号是否有效，True表示有效，False表示无效
        """
        # 如果没有持仓，任何信号都有效
        if not current_position:
            return True

        # 如果有多头持仓，只有卖出信号有效（平仓）
        if current_position["posSide"] == "long":
            return signal == "sell"

        # 如果有空头持仓，只有买入信号有效（平仓）
        if current_position["posSide"] == "short":
            return signal == "buy"

        return False  # 其他情况视为无效信号
