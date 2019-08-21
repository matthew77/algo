from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager
)


class DemoStrategy(CtaTemplate):
    """演示用的简单双均线"""
    author = 'Demo'
    # parameters definition
    fast_window = 10
    slow_window = 20

    # variable definition
    fast_ma_t = 0.0
    fast_ma_t_minus_1 = 0.0
    slow_ma_t = 0.0
    slow_ma_t_minus_1 = 0.0

    # labels for parameters and variables
    parameters = ['fast_window', 'slow_window']
    variables = ['fast_ma_t', 'fast_ma_t_minus_1', 'slow_ma_t', 'slow_ma_t_minus_1']

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        # K线合成器：从Tick合成分钟K线用
        self.bg = BarGenerator(self.on_bar)
        # 时间序列容器：计算技术指标用
        self.am = ArrayManager()

    def on_init(self):
        """ 当策略被初始化时调用该函数。"""
        self.write_log('策略初始化')
        # 加载10天的历史数据用于初始化回放
        self.load_bar(10)

    def on_start(self):
        """ 当策略被启动时调用该函数。 """
        self.write_log('策略启动')
        # 通知图形界面更新（策略最新状态）
        # 不调用该函数则界面不会变化
        self.put_event()

    def on_stop(self):
        """ 当策略被停止时调用该函数。 """
        self.write_log('策略停止')
        self.put_event()

    def on_tick(self, tick: TickData):
        """通过该函数收到Tick推送。"""
        # tick: TickData --- specify the tick has data type as TickData
        # e.g. def splitComma(line: str) -> str:  you can also specify the return type as well.
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """ 通过该函数收到新的1分钟K线推送。 """
        am = self.am  # just for saving typing self.
        # 更新K线到时间序列容器中
        am.update_bar(bar)
        # 若缓存的K线数量尚不够计算技术指标，则直接返回
        if not am.inited:
            return
        # 计算快速均线
        fast_ma = am.sma(self.fast_window, array=True)
        self.fast_ma_t = fast_ma[-1]  # T时刻数值
        self.fast_ma_t_minus_1 = fast_ma[-2]  # T-1时刻数值
        # 计算慢速均线
        slow_ma = am.sma(self.slow_window, array=True)
        self.slow_ma_t = slow_ma[-1]
        self.slow_ma_t_minus_1 = slow_ma[-2]
        # 判断是否金叉
        cross_over = (self.fast_ma_t > self.slow_ma_t and
                      self.fast_ma_t_minus_1 < self.slow_ma_t_minus_1)
        # 判断是否死叉
        cross_below = (self.fast_ma_t < self.slow_ma_t and
                       self.fast_ma_t_minus_1 > self.slow_ma_t_minus_1)

        if cross_over:
            # 为了保证成交，在K线收盘价上加5发出限价单
            # TODO: 应该是相对形式更合理，如乘以1.05
            price = bar.close_price + 5
            # 当前无仓位，则直接开多
            if self.pos == 0:
                self.buy(price, 1)  # 只买入一个单位
            # 当前持有空头仓位，则先平空，再开多
            elif self.pos < 0:
                self.cover(price, 1)
                self.buy(price, 1)

        if cross_below:
            # 为了保证成交，在K线收盘价上减5发出限价单
            # TODO: 应该是相对形式更合理，如乘以0.95
            price = bar.close_price - 5
            # 当前无仓位，则直接开空
            if self.pos == 0:
                self.short(price, 1)
            # 当前持有多头仓位，则先平多，再开空
            elif self.pos > 0:
                self.sell(price, 1)
                self.short(price, 1)

        self.put_event()

    def on_order(self, order: OrderData):
        """ 通过该函数收到委托状态更新推送。 """
        pass

    def on_trade(self, trade: TradeData):
        """ 通过该函数收到成交推送。 """
        # 成交后策略逻辑仓位发生变化，需要通知界面更新。
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """ 通过该函数收到本地停止单推送。 """
        pass
