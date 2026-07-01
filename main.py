"""
OKX自动交易程序主入口
"""
import os
import sys
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from config.config import *
from core.okx_client import OKXClient
from core.trading_engine import TradingEngine
from strategies.ma_strategy import MAStrategy
from strategies.rsi_strategy import RSIStrategy
from utils.logger import setup_logger
from utils.data_utils import parse_candlesticks_data, calculate_indicators


class AutoTradingBot:
    """自动交易机器人"""

    def __init__(self, strategy_name: str = "MA"):
        """
        初始化自动交易机器人

        Args:
            strategy_name: 策略名称，可选值为 "MA" 或 "RSI"
        """
        # 设置日志
        self.logger = setup_logger(LOG_FILE, LOG_LEVEL)
        self.logger.info("=" * 50)
        self.logger.info("OKX自动交易程序启动")
        self.logger.info(f"策略: {strategy_name}")
        self.logger.info(f"交易对: {TRADING_PAIR}")
        self.logger.info("=" * 50)

        # 初始化OKX客户端
        self.client = OKXClient(
            api_key=API_KEY,
            secret_key=SECRET_KEY,
            passphrase=PASSPHRASE,
            is_demo=True  # 设置为False进行真实交易
        )

        # 初始化交易引擎
        self.trading_engine = TradingEngine(self.client, {
            "TRADING_PAIR": TRADING_PAIR,
            "TRADING_MODE": TRADING_MODE,
            "LEVERAGE": LEVERAGE,
            "POSITION_SIZE": POSITION_SIZE,
            "STOP_LOSS_PERCENT": STOP_LOSS_PERCENT,
            "TAKE_PROFIT_PERCENT": TAKE_PROFIT_PERCENT,
            "STRATEGY_PARAMS": STRATEGY_PARAMS
        })

        # 初始化策略
        if strategy_name.upper() == "MA":
            self.strategy = MAStrategy({
                "POSITION_SIZE": POSITION_SIZE,
                "STOP_LOSS_PERCENT": STOP_LOSS_PERCENT,
                "TAKE_PROFIT_PERCENT": TAKE_PROFIT_PERCENT,
                "STRATEGY_PARAMS": STRATEGY_PARAMS
            })
        elif strategy_name.upper() == "RSI":
            self.strategy = RSIStrategy({
                "POSITION_SIZE": POSITION_SIZE,
                "STOP_LOSS_PERCENT": STOP_LOSS_PERCENT,
                "TAKE_PROFIT_PERCENT": TAKE_PROFIT_PERCENT,
                "STRATEGY_PARAMS": STRATEGY_PARAMS
            })
        else:
            self.logger.error(f"不支持的策略: {strategy_name}")
            raise ValueError(f"不支持的策略: {strategy_name}")

        # 初始化交易引擎
        if not self.trading_engine.initialize():
            self.logger.error("交易引擎初始化失败，程序退出")
            sys.exit(1)

    def run(self) -> None:
        """运行自动交易程序"""
        self.logger.info("自动交易程序开始运行...")
        self.trading_engine.is_running = True

        try:
            while self.trading_engine.is_running:
                try:
                    # 获取K线数据
                    candlesticks = self.client.get_candlesticks(
                        inst_id=TRADING_PAIR,
                        bar=TIMEFRAME,
                        limit="100"
                    )

                    if not candlesticks or "data" not in candlesticks:
                        self.logger.error("获取K线数据失败")
                        time.sleep(60)
                        continue

                    # 解析K线数据
                    df = parse_candlesticks_data(candlesticks["data"])

                    # 计算技术指标
                    df = calculate_indicators(df)

                    # 打印当前交易对实时价格（实时价格每个循环都会记录）
                    current_price = self.trading_engine.get_current_price()
                    if current_price is not None:
                        self.logger.info(f"实时价格: {current_price}")
                    else:
                        self.logger.warning("无法获取实时价格")

                    # 生成交易信号
                    signal = self.strategy.generate_signal(df)

                    # 获取当前持仓
                    current_position = self.trading_engine.get_position_info()

                    # 验证信号
                    if signal and self.strategy.validate_signal(signal, current_position):
                        # 检查风险
                        if not self.trading_engine.check_risk():
                            self.logger.warning("风险检查未通过，跳过本次交易")
                            time.sleep(60)
                            continue

                        # 获取当前价格
                        current_price = self.trading_engine.get_current_price()
                        if not current_price:
                            self.logger.error("获取当前价格失败")
                            time.sleep(60)
                            continue

                        # 计算仓位大小
                        account_balance = self.trading_engine.get_account_balance()
                        position_size = self.strategy.calculate_position_size(
                            current_price,
                            float(account_balance.get("eqUsd", 0)) if account_balance else 0
                        )

                        # 计算止盈止损价格
                        stop_loss = self.strategy.calculate_stop_loss(current_price, signal)
                        take_profit = self.strategy.calculate_take_profit(current_price, signal)

                        # 执行交易
                        self.logger.info(f"生成交易信号: {signal}")
                        self.logger.info(f"当前价格: {current_price}")
                        self.logger.info(f"仓位大小: {position_size}")
                        self.logger.info(f"止损价格: {stop_loss}")
                        self.logger.info(f"止盈价格: {take_profit}")

                        # 下单
                        order_id = self.trading_engine.place_market_order(
                            side=signal,
                            size=position_size,
                            stop_loss=stop_loss,
                            take_profit=take_profit
                        )

                        if order_id:
                            self.logger.info(f"下单成功，订单ID: {order_id}")
                        else:
                            self.logger.error("下单失败")

                    # 等待下一个周期
                    self.logger.info(f"等待下一个周期... 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    time.sleep(30)  # 每30秒检查一次

                except Exception as e:
                    self.logger.error(f"交易循环异常: {str(e)}")
                    time.sleep(60)

        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在停止交易...")
            self.trading_engine.stop()
            self.logger.info("交易程序已停止")
            sys.exit(0)

        except Exception as e:
            self.logger.error(f"交易程序异常: {str(e)}")
            self.trading_engine.stop()
            sys.exit(1)


def main():
    """主函数"""
    # 检查命令行参数
    strategy = "MA"  # 默认使用MA策略
    if len(sys.argv) > 1:
        strategy = sys.argv[1].upper()

    # 创建并运行自动交易机器人
    bot = AutoTradingBot(strategy)
    bot.run()


if __name__ == "__main__":
    main()
