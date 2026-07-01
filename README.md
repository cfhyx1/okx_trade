# OKX自动交易程序

这是一个基于Python的OKX自动交易程序，支持多种交易策略，包括移动平均线交叉策略和RSI策略。

## 功能特点

- 支持OKX交易所API接口
- 内置多种交易策略（MA、RSI）
- 自动止盈止损功能
- 风险控制机制
- 完整的日志记录
- 支持模拟交易和真实交易

## 目录结构

```
okx_auto_trad/
├── config/               # 配置文件目录
│   ├── __init__.py
│   └── config.py        # 配置文件
├── core/                 # 核心交易逻辑
│   ├── __init__.py
│   ├── okx_client.py    # OKX API客户端
│   └── trading_engine.py # 交易引擎
├── strategies/           # 交易策略
│   ├── __init__.py
│   ├── base_strategy.py # 策略基类
│   ├── ma_strategy.py   # 移动平均线策略
│   └── rsi_strategy.py  # RSI策略
├── utils/                # 工具函数
│   ├── __init__.py
│   ├── logger.py        # 日志工具
│   └── data_utils.py    # 数据处理工具
├── logs/                 # 日志目录
├── main.py               # 主程序入口
├── requirements.txt     # 依赖包
└── README.md            # 项目说明
```

## 安装与使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

编辑 `config/config.py` 文件，填入您的OKX API密钥：

```python
# OKX API配置
# 请在OKX官网申请API密钥，并填入以下字段
API_KEY = "your_api_key_here"  # OKX API密钥
SECRET_KEY = "your_secret_key_here"  # OKX API密钥
PASSPHRASE = "your_passphrase_here"  # OKX API口令
```

### 3. 运行程序

```bash
# 使用默认的MA策略运行
python main.py

# 指定使用RSI策略运行
python main.py RSI
```

## 策略说明

### 移动平均线策略 (MA)

基于短期均线和长期均线的交叉来生成交易信号：
- 当短期均线上穿长期均线时，生成买入信号
- 当短期均线下穿长期均线时，生成卖出信号

### RSI策略

基于相对强弱指标(RSI)的超买超卖信号进行交易：
- 当RSI从超卖区域(≤30)上升时，生成买入信号
- 当RSI从超买区域(≥70)下降时，生成卖出信号

## 风险提示

- 自动交易存在资金损失风险，请谨慎使用
- 建议先在模拟交易模式下测试策略
- 请确保充分理解代码逻辑后再进行真实交易
- 市场行情剧烈波动时，程序可能无法及时响应
- 请合理设置止盈止损，控制风险

## 注意事项

1. 确保API密钥权限正确，需要开通交易权限
2. 建议先在模拟交易环境下测试
3. 程序运行时会生成日志文件，保存在logs目录下
4. 如需停止程序，请使用Ctrl+C中断

## 开发者信息

本项目仅供学习和研究使用，不构成任何投资建议。

## 版本历史

- v1.0.0: 初始版本，支持MA和RSI两种策略
