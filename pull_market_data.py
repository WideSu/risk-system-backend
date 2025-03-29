
# 导入moomoo-api
import moomoo as ft

# 实例化行情上下文对象
quote_ctx = ft.OpenQuoteContext(host="127.0.0.1", port=11111)

# 上下文控制
quote_ctx.start()              # 开启异步数据接收
quote_ctx.set_handler(ft.TickerHandlerBase())  # 设置用于异步处理数据的回调对象(可派生支持自定义)

# 低频数据接口
market = ft.Market.HK
code = 'HK.00123'
code_list = [code]
print(quote_ctx.get_market_snapshot(code_list))                              # 获取市场快照

# 停止异步数据接收
quote_ctx.stop()

# 关闭对象
quote_ctx.close()

# 实例化港股交易上下文对象
trade_hk_ctx = ft.OpenHKTradeContext(host="127.0.0.1", port=11111)

# 交易接口列表
# print(trade_hk_ctx.unlock_trade(password='123456'))                # 解锁接口
# print(trade_hk_ctx.accinfo_query(trd_env=ft.TrdEnv.SIMULATE))      # 查询账户信息
# print(trade_hk_ctx.place_order(price=1.1, qty=2000, code=code, trd_side=ft.TrdSide.BUY, order_type=ft.OrderType.NORMAL, trd_env=ft.TrdEnv.SIMULATE))  # 下单接口
# print(trade_hk_ctx.order_list_query(trd_env=ft.TrdEnv.SIMULATE))      # 查询订单列表
# print(trade_hk_ctx.position_list_query(trd_env=ft.TrdEnv.SIMULATE))    # 查询持仓列表

trade_hk_ctx.close()