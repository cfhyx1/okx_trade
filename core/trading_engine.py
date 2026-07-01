
import logging
from typing import Dict, Optional, List
from datetime import datetime
import time
from .okx_client import OKXClient

class TradingEngine:
    """交易引擎类，负责执行交易逻辑，包括下单、平仓、风险管理等操作"""

    def __init__(self, client: OKXClient, config: Dict):
        """
        初始化交易引擎

        Args:
            client: OKX API客户端实例，用于与OKX交易所交互
            config: 交易配置字典，包含交易对、杠杆、止盈止损等参数
        """
        self.client = client  # OKX API客户端
        self.config = config  # 交易配置
        self.logger = logging.getLogger(__name__)  # 日志记录器
        self.current_position = None  # 当前持仓信息
        self.last_order_time = None  # 上次下单时间
        self.is_running = False  # 交易引擎运行状态

    def initialize(self) -> bool:
        """
        初始化交易引擎，设置杠杆并获取当前持仓

        Returns:
            初始化是否成功，True表示成功，False表示失败
        """
        try:
            # 设置杠杆倍数
            self.client.set_leverage(
                inst_id=self.config["TRADING_PAIR"],  # 交易对
                lever=str(self.config["LEVERAGE"]),   # 杠杆倍数
                mgn_mode=self.config["TRADING_MODE"]  # 保证金模式
            )

            # 获取当前持仓信息
            positions = self.client.get_positions(inst_type="SWAP")
            if positions and "data" in positions:
                # 遍历持仓，找出当前交易对的持仓
                for pos in positions["data"]:
                    if pos["instId"] == self.config["TRADING_PAIR"] and float(pos["pos"]) != 0:
                        self.current_position = pos
                        self.logger.info(f"当前持仓: {pos}")

            self.logger.info("交易引擎初始化完成")
            return True

        except Exception as e:
            self.logger.error(f"交易引擎初始化失败: {str(e)}")
            return False

    def get_current_price(self) -> Optional[float]:
        """
        获取当前价格

        Returns:
            当前价格，如果获取失败则返回None
        """
        try:
            # 获取行情信息
            ticker = self.client.get_ticker(self.config["TRADING_PAIR"])
            if ticker and "data" in ticker and len(ticker["data"]) > 0:
                # 返回最新价格
                return float(ticker["data"][0]["last"])
            return None
        except Exception as e:
            self.logger.error(f"获取当前价格失败: {str(e)}")
            return None

    def place_market_order(self, side: str, size: float, 
                           stop_loss: Optional[float] = None,
                           take_profit: Optional[float] = None) -> Optional[str]:
        """
        下市价单，支持设置止盈止损

        Args:
            side: 买卖方向，可选值为 "buy" (买入/开多) 或 "sell" (卖出/开空)
            size: 交易数量，如 0.01 表示0.01个BTC
            stop_loss: 止损价格，如果为None则根据配置自动计算
            take_profit: 止盈价格，如果为None则根据配置自动计算

        Returns:
            订单ID，如果下单失败则返回None
        """
        try:
            # 获取当前价格
            current_price = self.get_current_price()
            if not current_price:
                self.logger.error("无法获取当前价格")
                return None

            # 如果没有指定止损价格，根据配置计算
            if stop_loss is None:
                # 如果是买入，止损价格低于当前价格；如果是卖出，止损价格高于当前价格
                stop_loss = current_price * (1 - self.config["STOP_LOSS_PERCENT"] if side == "buy" 
                                           else 1 + self.config["STOP_LOSS_PERCENT"])

            # 如果没有指定止盈价格，根据配置计算
            if take_profit is None:
                # 如果是买入，止盈价格高于当前价格；如果是卖出，止盈价格低于当前价格
                take_profit = current_price * (1 + self.config["TAKE_PROFIT_PERCENT"] if side == "buy" 
                                             else 1 - self.config["TAKE_PROFIT_PERCENT"])

            # 确定持仓方向
            pos_side = "long" if side == "buy" else "short"

            # 下单
            result = self.client.place_order(
                inst_id=self.config["TRADING_PAIR"],  # 交易对
                td_mode=self.config["TRADING_MODE"],  # 交易模式
                side=side,  # 买卖方向
                ord_type="market",  # 市价单
                sz=str(size),  # 交易数量
                pos_side=pos_side,  # 持仓方向
                sl_trigger_px=str(stop_loss),  # 止损触发价
                sl_ord_px=str(stop_loss),  # 止损委托价
                tp_trigger_px=str(take_profit),  # 止盈触发价
                tp_ord_px=str(take_profit)  # 止盈委托价
            )

            if result and "data" in result and len(result["data"]) > 0:
                order_id = result["data"][0]["ordId"]
                self.logger.info(f"订单已提交: {side} {size} {self.config['TRADING_PAIR']}, "
                               f"订单ID: {order_id}, 止损: {stop_loss}, 止盈: {take_profit}")
                self.last_order_time = datetime.now()
                return order_id
            else:
                self.logger.error(f"下单失败: {result}")
                return None

        except Exception as e:
            self.logger.error(f"下单异常: {str(e)}")
            return None

    def close_position(self, pos_side: Optional[str] = None) -> bool:
        """
        平仓，可以平掉指定方向的持仓或所有持仓

        Args:
            pos_side: 指定要平掉的持仓方向，可选值为:
                - long: 多头持仓
                - short: 空头持仓
                - None: 平掉所有方向的持仓

        Returns:
            是否成功，True表示成功，False表示失败
        """
        try:
            # 获取持仓信息
            positions = self.client.get_positions(inst_type="SWAP")
            if not positions or "data" not in positions:
                self.logger.error("无法获取持仓信息")
                return False

            success = True
            # 遍历所有持仓
            for pos in positions["data"]:
                # 只处理当前交易对的持仓
                if pos["instId"] == self.config["TRADING_PAIR"] and float(pos["pos"]) != 0:
                    # 如果指定了持仓方向，只处理匹配方向的持仓
                    if pos_side and pos["posSide"] != pos_side:
                        continue

                    # 确定平仓方向：多头持仓用卖出平仓，空头持仓用买入平仓
                    side = "sell" if pos["posSide"] == "long" else "buy"
                    # 获取持仓数量
                    size = abs(float(pos["pos"]))

                    # 下平仓单
                    result = self.client.place_order(
                        inst_id=self.config["TRADING_PAIR"],  # 交易对
                        td_mode=self.config["TRADING_MODE"],  # 交易模式
                        side=side,  # 平仓方向
                        ord_type="market",  # 市价单
                        sz=str(size),  # 平仓数量
                        pos_side=pos["posSide"],  # 持仓方向
                        reduce_only=True  # 设置为只减仓
                    )

                    if result and "data" in result and len(result["data"]) > 0:
                        self.logger.info(f"平仓成功: {pos['posSide']} {size} {self.config['TRADING_PAIR']}")
                    else:
                        self.logger.error(f"平仓失败: {result}")
                        success = False

            return success

        except Exception as e:
            self.logger.error(f"平仓异常: {str(e)}")
            return False

    def update_position(self) -> None:
        """
        更新当前持仓信息，从OKX服务器获取最新的持仓数据
        """
        try:
            # 获取持仓信息
            positions = self.client.get_positions(inst_type="SWAP")
            if positions and "data" in positions:
                # 遍历持仓，找出当前交易对的持仓
                for pos in positions["data"]:
                    if pos["instId"] == self.config["TRADING_PAIR"] and float(pos["pos"]) != 0:
                        self.current_position = pos
                        return
                # 如果没有持仓，将持仓信息设为None
                self.current_position = None
        except Exception as e:
            self.logger.error(f"更新持仓信息失败: {str(e)}")

    def get_position_info(self) -> Optional[Dict]:
        """
        获取当前持仓信息

        Returns:
            当前持仓信息字典，如果没有持仓则返回None
        """
        # 更新持仓信息后返回
        self.update_position()
        return self.current_position

    def get_account_balance(self) -> Optional[Dict]:
        """
        获取账户余额信息

        Returns:
            账户余额信息字典，包含账户总资产、可用余额等
        """
        try:
            balance = self.client.get_account_balance()
            if balance and "data" in balance and len(balance["data"]) > 0:
                # 返回第一个账户的余额信息
                return balance["data"][0]
            return None
        except Exception as e:
            self.logger.error(f"获取账户余额失败: {str(e)}")
            return None

    def check_risk(self) -> bool:
        """
        检查风险控制，确保交易安全

        Returns:
            是否可以继续交易，True表示可以继续，False表示不能继续
        """
        try:
            # 检查账户余额
            balance = self.get_account_balance()
            if not balance:
                return False

            # 检查是否有足够的保证金
            total_eq = float(balance.get("totalEq", 0))
            if total_eq <= 0:
                self.logger.error("账户余额不足")
                return False

            # 检查最近是否有订单，避免频繁下单
            if self.last_order_time:
                time_since_last_order = (datetime.now() - self.last_order_time).total_seconds()
                if time_since_last_order < 60:  # 限制60秒内不能重复下单
                    self.logger.info("距离上次下单时间过短")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"风险检查失败: {str(e)}")
            return False

    def stop(self) -> None:
        """
        停止交易引擎，将is_running设为False，停止交易循环
        """
        self.is_running = False
        self.logger.info("交易引擎已停止")
