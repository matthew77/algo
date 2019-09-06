import talib
import numpy as np
from vnpy.trader.object import BarData

from vnpy.app.cta_strategy import (
    CtaTemplate,
    TickData
)


class BollingerBotStrategy(CtaTemplate):
    """基于布林通道的交易策略"""
    # className = 'BollingerBotStrategy'
    author = u'Liang'

    # 策略参数
    bollLength = 28  # 通道窗口数
    entryDev = 3.2  # 开仓偏差
    exitDev = 1.2  # 平仓偏差
    trailingPrcnt = 0.4  # 移动止损百分比
    maLength = 10  # 过滤用均线窗口
    initDays = 10  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量

    # 策略变量
    bar = None  # 1分钟K线对象
    barMinute = ""  # K线当前的分钟
    fiveBar = None  # 1分钟K线对象

    bufferSize = 40  # 需要缓存的数据的大小
    bufferCount = 0  # 目前已经缓存了的数据的计数
    highArray = np.zeros(bufferSize)  # K线最高价的数组
    lowArray = np.zeros(bufferSize)  # K线最低价的数组
    closeArray = np.zeros(bufferSize)  # K线收盘价的数组

    bollMid = 0  # 布林带中轨
    bollStd = 0  # 布林带宽度
    entryUp = 0  # 开仓上轨
    exitUp = 0  # 平仓上轨

    maFilter = 0  # 均线过滤
    maFilter1 = 0  # 上一期均线

    intraTradeHigh = 0  # 持仓期内的最高点
    longEntry = 0  # 多头开仓
    longExit = 0  # 多头平仓

    orderList = []  # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    parameters = [
                 'bollLength',
                 'entryDev',
                 'exitDev',
                 'trailingPrcnt',
                 'maLength',
                 'initDays',
                 'fixedSize']

    # 变量列表，保存了变量的名称
    variables = [
               'bollMid',
               'bollStd',
               'entryUp',
               'exitUp',
               'intraTradeHigh',
               'longEntry',
               'shortEntry']

    # ----------------------------------------------------------------------
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """Constructor"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

    # ----------------------------------------------------------------------
    def on_init(self):
        """初始化策略（必须由用户继承实现）"""
        self.write_log('策略初始化')

        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.load_bar(self.initDays)
        # for bar in initData:
        #    self.on_bar(bar)

        self.put_event()

    # ----------------------------------------------------------------------
    def on_start(self):
        """启动策略（必须由用户继承实现）"""
        self.write_log('策略启动')
        self.put_event()

    # ----------------------------------------------------------------------
    def on_stop(self):
        """停止策略（必须由用户继承实现）"""
        self.write_log('策略停止')
        self.put_event()

    # ----------------------------------------------------------------------
    def on_tick(self, tick: TickData):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 聚合为1分钟K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:
            if self.bar:
                self.on_bar(self.bar)

            bar = BarData(datetime=tick.datetime,
                          exchange=tick.exchange,
                          gateway_name=tick.gateway_name,
                          symbol=tick.symbol)

            # bar.vt_symbol = tick.vt_symbol
            # bar.symbol = tick.symbol
            # bar.exchange = tick.exchange

            bar.open_price = tick.last_price
            bar.high_price = tick.last_price
            bar.low_price = tick.last_price
            bar.close_price = tick.last_price

            # bar.date = tick.date
            # bar.time = tick.time
            bar.datetime = tick.datetime  # K线的时间设为第一个Tick的时间

            self.bar = bar  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute  # 更新当前的分钟
        else:  # 否则继续累加新的K线
            bar = self.bar  # 写法同样为了加快速度

            bar.high_price = max(bar.high_price, tick.last_price)
            bar.low_price = min(bar.low_price, tick.last_price)
            bar.close_price = tick.last_price

    # ----------------------------------------------------------------------
    def on_bar(self, bar: BarData):
        """收到Bar推送（必须由用户继承实现）"""
        # 如果当前是一个5分钟走完
        # ZL: 通过改变 +1 可以实现非标时间bar
        if (bar.datetime.minute + 1) % 5 == 0:
            # 如果已经有聚合5分钟K线
            if self.fiveBar:
                # 将最新分钟的数据更新到目前5分钟线中
                fiveBar = self.fiveBar
                fiveBar.high_price = max(fiveBar.high_price, bar.high_price)
                fiveBar.low_price = min(fiveBar.low_price, bar.low_price)
                fiveBar.close_price = bar.close_price

                # 推送5分钟线数据
                self.onFiveBar(fiveBar)

                # 清空5分钟线数据缓存
                self.fiveBar = None
        else:
            # 如果没有缓存则新建
            if not self.fiveBar:
                # fiveBar = BarData()
                fiveBar = BarData(datetime=bar.datetime,
                                  exchange=bar.exchange,
                                  gateway_name=bar.gateway_name,
                                  symbol=bar.symbol)

                # fiveBar.vtSymbol = bar.vtSymbol
                # fiveBar.symbol = bar.symbol
                # fiveBar.exchange = bar.exchange

                fiveBar.open_price = bar.open_price
                fiveBar.high_price = bar.high_price
                fiveBar.low_price = bar.low_price
                fiveBar.close_price = bar.close_price

                # fiveBar.date = bar.datetime
                # fiveBar.time = bar.time
                fiveBar.datetime = bar.datetime

                self.fiveBar = fiveBar
            else:
                fiveBar = self.fiveBar
                fiveBar.high_price = max(fiveBar.high_price, bar.high_price)
                fiveBar.low_price = min(fiveBar.low_price, bar.low_price)
                fiveBar.close_price = bar.close_price

    # ----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancel_order(orderID)
        self.orderList = []

        # 保存K线数据
        self.closeArray[0:self.bufferSize - 1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize - 1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize - 1] = self.lowArray[1:self.bufferSize]

        self.closeArray[-1] = bar.close_price
        self.highArray[-1] = bar.high_price
        self.lowArray[-1] = bar.low_price

        self.bufferCount += 1
        if self.bufferCount < self.bufferSize:
            return

        # 计算指标数值
        self.bollMid = talib.MA(self.closeArray, self.bollLength)[-1]
        self.bollStd = talib.STDDEV(self.closeArray, self.bollLength)[-1]
        self.entryUp = self.bollMid + self.bollStd * self.entryDev
        self.exitUp = self.bollMid + self.bollStd * self.exitDev

        # ZL: 快速均线
        maArray = talib.MA(self.closeArray, self.maLength)
        self.maFilter = maArray[-1]
        self.maFilter1 = maArray[-2]

        # 判断是否要进行交易

        # 当前无仓位，发送OCO开仓委托
        if self.pos == 0:
            self.intraTradeHigh = bar.high_price
            # ZL: 5 min bar close price 高于 快速均线，并且快速均线上行
            if bar.close_price > self.maFilter and self.maFilter > self.maFilter1:
                # 买入价格设置为entry BB的上沿
                self.longEntry = self.entryUp
                # ZL: stop buy order。上穿时买入
                orderID = self.buy(self.longEntry, self.fixedSize, True)
                # ZL:
                for i in orderID:
                    self.orderList.append(i)
                #self.orderList.append(orderID)

        # 持有多头仓位
        elif self.pos > 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high_price)
            # ZL: 退出的位置是 近期的高点下跌某个制定的%
            self.longExit = self.intraTradeHigh * (1 - self.trailingPrcnt / 100)
            # ZL： 同 exit BB的上沿比较，找较小的作为退出/止损点
            self.longExit = min(self.longExit, self.exitUp)
            # ZL: stop sell order。下穿卖出
            orderID = self.sell(self.longExit, abs(self.pos), True)
            # ZL:
            for i in orderID:
                self.orderList.append(i)
            # self.orderList.append(orderID)

        # 发出状态更新事件
        self.put_event()

        # ----------------------------------------------------------------------

    def on_order(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def on_trade(self, trade):
        # 发出状态更新事件
        self.put_event()

    # ----------------------------------------------------------------------
    def on_stop_order(self, so):
        """停止单推送"""
        pass


if __name__ == "__main__":
    import os
    os.chdir('C:\\myproject\\vn_trader_pro_workspace')
    from vnpy.app.cta_strategy.backtesting import BacktestingEngine, OptimizationSetting
    from datetime import datetime

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol="CN50_USD.HUOBI",
        interval="1m",
        start=datetime(2019, 1, 1),
        end=datetime(2019, 4, 30),
        rate=0.3 / 10000,
        slippage=0.2,
        size=300,
        pricetick=0.2,
        capital=1_000_000,
    )
    engine.add_strategy(BollingerBotStrategy, {})
    engine.load_data()
    engine.run_backtesting()
    df = engine.calculate_result()
    engine.calculate_statistics()
    engine.show_chart()
