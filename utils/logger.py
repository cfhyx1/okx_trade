"""
日志工具模块，提供统一的日志记录功能
"""
import logging
import os
from datetime import datetime

def setup_logger(log_file=None, log_level="INFO"):
    """
    设置日志记录器

    Args:
        log_file: 日志文件路径，如果为None则使用默认路径
        log_level: 日志级别，如DEBUG, INFO, WARNING, ERROR

    Returns:
        logger: 配置好的日志记录器
    """
    # 创建logs目录（如果不存在）
    if log_file is None:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, f"trading_{datetime.now().strftime('%Y%m%d')}.log")

    # 确保 log_file 的父目录存在（当用户传入带目录的路径时）
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger("okx_auto_trading")
    logger.setLevel(getattr(logging, log_level.upper()))

    # 避免重复添加handler
    if not logger.handlers:
        # 创建文件handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper()))

        # 创建控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 创建formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 设置formatter
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加handler
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger