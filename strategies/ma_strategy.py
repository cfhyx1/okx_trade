
import pandas as pd
import numpy as np
from typing import Dict, Optional
from .base_strategy import BaseStrategy

class MAStrategy(BaseStrategy):
    """移动平均线交叉策略，基于短期均线和长期均线的交叉来生成交易信号"""

    def __init__(self, config: Dict):
        """
        初始化MA策略

        Args:
            config: 策略配置，应包含STRATEGY_PARAMS字典，其中:
                - short_ma: 短期均线周期，默认为5
                - long_ma: 长期均线周期，默认为20
        """
        super().__init__(config)
        # 从配置中获取短期和长期均线周期
        self.short_period = config.get("STRATEGY_PARAMS", {}).get("short_ma", 5)
        self.long_period = config.get("STRATEGY_PARAMS", {}).get("long_ma", 20)

    def generate_signal(self, data: pd.DataFrame) -> Optional[str]:
        """
        根据移动平均线交叉生成交易信号

        Args:
            data: K线数据，至少需要包含"close"列（收盘价）

        Returns:
            交易信号:
            - "buy": 当短期均线上穿长期均线时生成买入信号
            - "sell": 当短期均线下穿长期均线时生成卖出信号
            - None: 无交叉信号或数据不足
        """
        # 确保数据足够计算长期均线
        if len(data) < self.long_period:
            return None

        # 计算短期和长期移动平均线
        data["short_ma"] = data["close"].rolling(window=self.short_period).mean()
        data["long_ma"] = data["close"].rolling(window=self.long_period).mean()

        # 获取最新和前一条数据
        latest = data.iloc[-1]
        prev = data.iloc[-2]

        # 判断均线交叉情况
        # 短期均线上穿长期均线（金叉）
        short_ma_cross_above = (prev["short_ma"] <= prev["long_ma"] and 
                               latest["short_ma"] > latest["long_ma"])
        # 短期均线下穿长期均线（死叉）
        short_ma_cross_below = (prev["short_ma"] >= prev["long_ma"] and 
                               latest["short_ma"] < latest["long_ma"])

        # 根据交叉情况返回交易信号
        if short_ma_cross_above:
            return "buy"  # 金叉，买入信号
        elif short_ma_cross_below:
            return "sell"  # 死叉，卖出信号
        else:
            return None  # 无交叉信号

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
