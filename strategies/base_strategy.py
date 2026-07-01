
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import pandas as pd

class BaseStrategy(ABC):
    """交易策略基类，所有具体策略都应继承此类并实现其抽象方法"""

    def __init__(self, config: Dict):
        """
        初始化策略

        Args:
            config: 策略配置字典，包含交易参数、止盈止损设置等
        """
        self.config = config  # 策略配置
        self.logger = logging.getLogger(__name__)  # 日志记录器
        self.name = self.__class__.__name__  # 策略名称

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Optional[str]:
        """
        根据K线数据生成交易信号，此方法必须由子类实现

        Args:
            data: 包含OHLCV数据的DataFrame，列名通常为:
                - timestamp: 时间戳
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量

        Returns:
            交易信号，可能的值为:
            - "buy": 买入/开多信号
            - "sell": 卖出/开空信号
            - None: 无交易信号
        """
        pass

    @abstractmethod
    def validate_signal(self, signal: str, current_position: Optional[Dict]) -> bool:
        """
        验证交易信号是否有效，考虑当前持仓情况

        Args:
            signal: 交易信号，"buy" 或 "sell"
            current_position: 当前持仓信息字典，包含:
                - pos: 持仓数量
                - posSide: 持仓方向 (long/short)
                - upl: 浮动盈亏
                - pnl: 实现盈亏

        Returns:
            信号是否有效，True表示有效，False表示无效
        """
        pass

    def calculate_position_size(self, current_price: float, account_balance: float) -> float:
        """
        计算仓位大小，子类可以重写此方法实现自定义仓位管理

        Args:
            current_price: 当前市场价格
            account_balance: 账户余额

        Returns:
            建议的仓位大小
        """
        # 默认使用固定仓位大小
        return self.config.get("POSITION_SIZE", 0.01)

    def calculate_stop_loss(self, current_price: float, signal: str) -> float:
        """
        计算止损价格

        Args:
            current_price: 当前市场价格
            signal: 交易信号，"buy" 或 "sell"

        Returns:
            止损价格
        """
        # 从配置中获取止损百分比
        stop_loss_percent = self.config.get("STOP_LOSS_PERCENT", 0.02)
        # 根据交易信号计算止损价格
        if signal == "buy":
            # 买入信号，止损价格低于当前价格
            return current_price * (1 - stop_loss_percent)
        else:
            # 卖出信号，止损价格高于当前价格
            return current_price * (1 + stop_loss_percent)

    def calculate_take_profit(self, current_price: float, signal: str) -> float:
        """
        计算止盈价格

        Args:
            current_price: 当前市场价格
            signal: 交易信号，"buy" 或 "sell"

        Returns:
            止盈价格
        """
        # 从配置中获取止盈百分比
        take_profit_percent = self.config.get("TAKE_PROFIT_PERCENT", 0.04)
        # 根据交易信号计算止盈价格
        if signal == "buy":
            # 买入信号，止盈价格高于当前价格
            return current_price * (1 + take_profit_percent)
        else:
            # 卖出信号，止盈价格低于当前价格
            return current_price * (1 - take_profit_percent)
