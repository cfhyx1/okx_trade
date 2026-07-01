 
import hmac
import base64
import hashlib
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import time
from urllib.parse import urlencode

class OKXClient:
    """OKX交易所API客户端，封装了OKX交易所的API调用"""

    def __init__(self, api_key: str, secret_key: str, passphrase: str, 
                 base_url: str = "https://www.okx.com", is_demo: bool = False):
        """
        初始化OKX客户端

        Args:
            api_key: OKX API密钥，需要在OKX官网申请
            secret_key: OKX API密钥，与API Key配对使用
            passphrase: OKX API口令，创建API时设置的
            base_url: OKX API基础URL，默认为官方API地址
            is_demo: 是否为模拟交易模式，True为模拟交易，False为真实交易
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.base_url = base_url
        self.is_demo = is_demo
        self.session = requests.Session()

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """
        生成API签名，用于API请求的认证

        Args:
            timestamp: 请求时间戳，ISO 8601格式
            method: HTTP请求方法，如GET、POST、DELETE等
            request_path: API请求路径，如/api/v5/account/balance
            body: 请求体内容，POST请求时使用

        Returns:
            使用HMAC-SHA256算法生成的签名结果
        """
        # 构造签名字符串
        if body:
            message = timestamp + method + request_path + body
        else:
            message = timestamp + method + request_path

        # 使用HMAC-SHA256算法生成签名
        mac = hmac.new(
            bytes(self.secret_key, encoding="utf8"),
            bytes(message, encoding="utf-8"),
            digestmod=hashlib.sha256
        )
        d = mac.digest()
        return base64.b64encode(d).decode()

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                 data: Optional[Dict] = None) -> Dict:
        """
        发送API请求的内部方法，处理请求签名和发送

        Args:
            method: HTTP请求方法，如GET、POST、DELETE等
            endpoint: API端点，如/api/v5/account/balance
            params: URL查询参数，用于GET请求
            data: 请求体数据，用于POST/DELETE请求

        Returns:
            API响应数据，JSON格式

        Raises:
            Exception: 当API请求失败时抛出异常
        """
        # 生成请求时间戳
        timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
        # 将请求数据转换为JSON字符串
        body = json.dumps(data) if data else ""

        # 校验 API 凭证是否存在且非空白
        def _is_empty(s):
            return s is None or (isinstance(s, str) and s.strip() == "")
        if _is_empty(self.api_key) or _is_empty(self.secret_key) or _is_empty(self.passphrase):
            raise ValueError("API凭证缺失或为空。请在配置中设置 API_KEY、SECRET_KEY 和 PASSPHRASE。")

        # 将查询参数序列化并包含在签名的 request_path 中（OKX 要求签名时包含 query string）
        query_string = ""
        if params:
            # urlencode with doseq to handle list values correctly
            query_string = "?" + urlencode(params, doseq=True)

        request_path_for_sign = endpoint + query_string

        # 生成签名并设置请求头
        sign = self._generate_signature(timestamp, method, request_path_for_sign, body)
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

        # 如果是模拟交易模式，添加模拟交易标识
        if self.is_demo:
            headers["x-simulated-trading"] = "1"

        # 构造完整的请求URL（不要把 query 拼接到 url，这里交给 requests 处理）
        url = self.base_url + endpoint

        try:
            # 根据不同的HTTP方法发送请求
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                response = self.session.post(url, headers=headers, data=body, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, data=body, timeout=10)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            # 检查HTTP响应状态码，如果非200则抛出异常
            response.raise_for_status()
            # 返回JSON格式的响应数据
            return response.json()

        except requests.exceptions.RequestException as e:
            # 捕获请求异常并重新抛出
            raise Exception(f"API请求失败: {str(e)}")

    def get_account_balance(self) -> Dict:
        """
        获取账户余额信息

        Returns:
            包含账户余额信息的字典，包括账户总资产、可用余额、冻结余额等

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "details": [
                            {
                                "ccy": "BTC",
                                "availBal": "1.234",
                                "cashBal": "1.234",
                                "crossLiab": "0",
                                "eq": "1.234",
                                "imr": "0",
                                "interest": "0",
                                "maxLoanable": "0",
                                "mgnRatio": "0",
                                "notionalLcy": "12345.67",
                                "uLt": "0",
                                "upl": "0",
                                "uplLiab": "0"
                            }
                        ],
                        "info": {
                            "acctLv": "1",
                            "bal": "1.234",
                            "eq": "1.234",
                            "eqUsd": "12345.67",
                            "ival": "0",
                            "maxLoan": "0",
                            "mgnRatio": "0",
                            "uLt": "0"
                        }
                    }
                ]
            }
        """
        endpoint = "/api/v5/account/balance"
        return self._request("GET", endpoint)

    def get_positions(self, inst_type: Optional[str] = None) -> Dict:
        """
        获取持仓信息

        Args:
            inst_type: 产品类型，可选值为:
                - SWAP: 永续合约
                - FUTURES: 期货
                - OPTION: 期权
                - SPOT: 现货
                如果不指定，则返回所有类型的持仓信息

        Returns:
            持仓信息字典，包含所有持仓的详细信息

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "posId": "1234567890",
                        "pos": "1",
                        "posSide": "long",
                        "instType": "SWAP",
                        "markPx": "45000",
                        "lastPx": "45100",
                        "lastSz": "0.001",
                        "tradeId": "1234567890",
                        "pnl": "10",
                        "upl": "100",
                        "instFamily": "BTC-USDT",
                        "lever": "10",
                        "mgnMode": "cross",
                        "adl": 0,
                        "ccy": "USDT",
                        "margin": "100",
                        "notionalUsd": "45000",
                        "uTime": "1625097600000"
                    }
                ]
            }
        """
        endpoint = "/api/v5/account/positions"
        params = {"instType": inst_type} if inst_type else {}
        return self._request("GET", endpoint, params=params)

    def place_order(self, inst_id: str, td_mode: str, side: str, ord_type: str, 
                    sz: str, ccy: Optional[str] = None, pos_side: Optional[str] = None,
                    reduce_only: bool = False, tp_trigger_px: Optional[str] = None,
                    tp_ord_px: Optional[str] = None, sl_trigger_px: Optional[str] = None,
                    sl_ord_px: Optional[str] = None) -> Dict:
        """
        下单，支持市价单和限价单，并可设置止盈止损

        Args:
            inst_id: 产品ID，如 "BTC-USDT-SWAP" 表示BTC永续合约
            td_mode: 交易模式，可选值为:
                - cross: 全仓模式
                - isolated: 逐仓模式
                - cash: 现货模式
            side: 订单方向，可选值为:
                - buy: 买入/开多
                - sell: 卖出/开空
            ord_type: 订单类型，可选值为:
                - market: 市价单，以市场最优价格成交
                - limit: 限价单，以指定价格或更优价格成交
            sz: 委托数量，字符串格式，如 "0.01"
            ccy: 保证金币种，如 "USDT"，通常不需要指定
            pos_side: 持仓方向，可选值为:
                - long: 多头方向
                - short: 空头方向
                - net: 净持仓模式
                仅适用于多空持仓分离的合约
            reduce_only: 是否只减仓，True表示只能减少现有持仓
            tp_trigger_px: 止盈触发价，当价格达到此价格时触发止盈单
            tp_ord_px: 止盈委托价，止盈单的委托价格
            sl_trigger_px: 止损触发价，当价格达到此价格时触发止损单
            sl_ord_px: 止损委托价，止损单的委托价格

        Returns:
            下单结果，包含订单ID等关键信息

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "ordId": "1234567890",
                        "clOrdId": "client-order-id",
                        "tag": "",
                        "px": "0",
                        "sz": "0.01",
                        "side": "buy",
                        "ordType": "market",
                        "state": "live",
                        "fillSz": "0",
                        "fillPx": "",
                        "feeCcy": "",
                        "fee": "",
                        "rebateCcy": "",
                        "rebate": "",
                        "tradeId": "",
                        "tgtCcy": "",
                        "category": "",
                        "pnl": "",
                        "source": "api",
                        "ts": "1625097600000"
                    }
                ]
            }
        """
        endpoint = "/api/v5/trade/order"

        # 构造下单请求数据
        data = {
            "instId": inst_id,
            "tdMode": td_mode,
            "side": side,
            "ordType": ord_type,
            "sz": sz
        }

        # 添加可选参数
        if ccy:
            data["ccy"] = ccy
        if pos_side:
            data["posSide"] = pos_side
        if reduce_only:
            data["reduceOnly"] = "true"
        if tp_trigger_px:
            data["tpTriggerPx"] = tp_trigger_px
        if tp_ord_px:
            data["tpOrdPx"] = tp_ord_px
        if sl_trigger_px:
            data["slTriggerPx"] = sl_trigger_px
        if sl_ord_px:
            data["slOrdPx"] = sl_ord_px

        # 发送下单请求
        return self._request("POST", endpoint, data=data)

    def cancel_order(self, inst_id: str, ord_id: str) -> Dict:
        """
        撤销指定的订单

        Args:
            inst_id: 产品ID，如 "BTC-USDT-SWAP"
            ord_id: 订单ID，通过place_order下单后返回的ordId

        Returns:
            撤单结果，包含撤单是否成功的状态信息

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "ordId": "1234567890",
                        "code": "0",
                        "msg": "",
                        "sCode": "0",
                        "sMsg": ""
                    }
                ]
            }
        """
        endpoint = "/api/v5/trade/cancel-order"
        data = {"instId": inst_id, "ordId": ord_id}
        return self._request("POST", endpoint, data=data)

    def get_order_history(self, inst_id: Optional[str] = None, 
                          state: Optional[str] = None) -> Dict:
        """
        获取历史订单记录

        Args:
            inst_id: 产品ID，如 "BTC-USDT-SWAP"，如果不指定则返回所有产品的订单
            state: 订单状态，可选值为:
                - live: 未完成（包括部分成交）
                - partially_filled: 部分成交
                - filled: 已完成
                - canceled: 已撤销
                - live_canceled: 已撤销但未完全成交的订单
                - all: 所有状态
                如果不指定state，则默认返回live和partially_filled状态的订单

        Returns:
            历史订单信息，包含订单的详细信息

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "ordId": "1234567890",
                        "clOrdId": "client-order-id",
                        "tag": "",
                        "px": "45000",
                        "sz": "0.01",
                        "side": "buy",
                        "ordType": "limit",
                        "state": "filled",
                        "fillSz": "0.01",
                        "fillPx": "45000",
                        "feeCcy": "USDT",
                        "fee": "0.0001",
                        "rebateCcy": "",
                        "rebate": "",
                        "tradeId": "1234567890",
                        "tgtCcy": "",
                        "category": "",
                        "pnl": "",
                        "source": "api",
                        "ts": "1625097600000"
                    }
                ]
            }
        """
        endpoint = "/api/v5/trade/orders-history"
        params = {}
        if inst_id:
            params["instId"] = inst_id
        if state:
            params["state"] = state

        return self._request("GET", endpoint, params=params)

    def get_ticker(self, inst_id: str) -> Dict:
        """
        获取产品行情信息，包括最新价、买一价、卖一价等

        Args:
            inst_id: 产品ID，如 "BTC-USDT-SWAP" 表示BTC永续合约

        Returns:
            行情信息，包含最新价、买一价、卖一价、24小时成交量等

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "last": "45000",
                        "lastSz": "0.01",
                        "askPx": "45001",
                        "askSz": "0.5",
                        "bidPx": "44999",
                        "bidSz": "0.3",
                        "open24h": "44000",
                        "high24h": "46000",
                        "low24h": "43000",
                        "vol24h": "1000",
                        "volCcy24h": "45000000",
                        "sodUtc0": "44500",
                        "sodUtc8": "44500",
                        "ts": "1625097600000"
                    }
                ]
            }
        """
        endpoint = "/api/v5/market/ticker"
        params = {"instId": inst_id}
        return self._request("GET", endpoint, params=params)

    def get_candlesticks(self, inst_id: str, bar: str = "1H", 
                         limit: str = "100", after: Optional[str] = None,
                         before: Optional[str] = None) -> Dict:
        """
        获取K线数据，用于技术分析

        Args:
            inst_id: 产品ID，如 "BTC-USDT-SWAP"
            bar: K线周期，可选值为:
                - 1m: 1分钟
                - 3m: 3分钟
                - 5m: 5分钟
                - 15m: 15分钟
                - 30m: 30分钟
                - 1H: 1小时
                - 2H: 2小时
                - 4H: 4小时
                - 6H: 6小时
                - 12H: 12小时
                - 1D: 1天
                - 1W: 1周
                - 1M: 1月
            limit: 返回数量，最大300
            after: 请求此时间戳之前的数据，格式为ISO 8601时间戳
            before: 请求此时间戳之后的数据，格式为ISO 8601时间戳

        Returns:
            K线数据，包含开盘价、最高价、最低价、收盘价、成交量等

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    [
                        "1625097600000",  // 时间戳
                        "44000",          // 开盘价
                        "46000",          // 最高价
                        "43000",          // 最低价
                        "45000",          // 收盘价
                        "100",            // 成交量
                        "4500000"         // 成交额
                    ],
                    ...
                ]
            }
        """
        endpoint = "/api/v5/market/candles"
        params = {
            "instId": inst_id,
            "bar": bar,
            "limit": limit
        }

        if after:
            params["after"] = after
        if before:
            params["before"] = before

        return self._request("GET", endpoint, params=params)

    def get_account_config(self) -> Dict:
        """
        获取账户配置信息

        Returns:
            账户配置信息，包括账户类型、交易模式、杠杆设置等

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "acctLv": "1",
                        "algoClOrdId": "",
                        "category": "algo",
                        "ctAlgoClOrdId": "",
                        "ctCcy": "BTC",
                        "ctVal": "1",
                        "maxCancelAllSize": "100",
                        "maxOrdPx": "100000",
                        "maxSz": "10",
                        "maxTriggerOpenOrdPx": "100000",
                        "maxTriggerOpenSz": "10",
                        "maxTriggerOrdPx": "100000",
                        "maxTriggerSz": "10",
                        "mgnMode": "cross",
                        "ordAlgoSz": "",
                        "payCcy": "",
                        "postOnly": "0",
                        "tdMode": "cash",
                        "tgtCcy": "",
                        "uTime": "1625097600000"
                    }
                ]
            }
        """
        endpoint = "/api/v5/account/config"
        return self._request("GET", endpoint)

    def set_leverage(self, inst_id: str, lever: str, mgn_mode: str, 
                     pos_side: Optional[str] = None) -> Dict:
        """
        设置杠杆倍数，仅适用于合约和期权产品

        Args:
            inst_id: 产品ID，如 "BTC-USDT-SWAP"
            lever: 杠杆倍数，字符串格式，如 "5" 表示5倍杠杆
            mgn_mode: 保证金模式，可选值为:
                - cross: 全仓模式
                - isolated: 逐仓模式
            pos_side: 持仓方向，可选值为:
                - long: 多头方向
                - short: 空头方向
                - net: 净持仓模式
                仅适用于多空持仓分离的合约，如果不指定则适用于所有方向

        Returns:
            设置结果，包含设置是否成功的状态信息

        示例返回:
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "lever": "10",
                        "mgnMode": "cross",
                        "uplLiab": "0",
                        "uplRatio": "0",
                        "posSide": "long",
                        "category": "",
                        "code": "0",
                        "msg": "",
                        "sCode": "0",
                        "sMsg": ""
                    }
                ]
            }
        """
        endpoint = "/api/v5/account/set-leverage"
        data = {
            "instId": inst_id,
            "lever": lever,
            "mgnMode": mgn_mode
        }

        if pos_side:
            data["posSide"] = pos_side

        return self._request("POST", endpoint, data=data)
