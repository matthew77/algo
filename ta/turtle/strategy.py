from vnpy.trader.utility import ArrayManager
from vnpy.trader.constant import (Direction, Offset)

# TODO:
# 原版海龟策略规定了4个维度的单位头寸限制，分别是
#
# 单个市场：头寸上限是4个
# 高度关联的多个市场：单个方向头寸单位不超过6个
# 松散关联的多个市场：某一个方向上的头寸单位不超过10个
# 单个方向：最多12个 ??? 什么情况下可以达到12？？？


MAX_PRODUCT_POS = 4         # 单品种最大持仓
MAX_DIRECTION_POS = 10      # 单方向最大持仓


class TurtleResult:
    """ 用于计算单笔开平仓交易盈亏，是海龟策略中判断“若上一笔盈利当前信号无效”的基础 """
    def __init__(self):
        """初始化单位头寸，开仓均价，平仓均价和单笔开平仓交易盈亏数"""
        self.unit = 0
        self.entry = 0                  # 开仓均价
        self.exit = 0                   # 平仓均价
        self.pnl = 0                    # 盈亏

    def open(self, price, change):
        """开仓或者加仓, 先计算开仓累计成本，然后统计开仓平均成本"""
        cost = self.unit * self.entry    # 计算之前的开仓成本
        cost += change * price          # 加上新仓位的成本
        self.unit += change              # 加上新仓位的数量
        self.entry = cost / self.unit    # 计算新的平均开仓成本

    def close(self, price):
        """平仓, 缓存平仓均价，统计单笔开平仓交易盈亏"""
        self.exit = price
        self.pnl = self.unit * (self.exit - self.entry)


class TurtleSignal:
    """ 用于产生海龟策略交易信号，包括入场，止损，止盈委托价格与目标仓位 """

    def __init__(self, portfolio, vt_symbol,
                 entry_window, exit_window, atr_window,
                 profit_check=False):
        """Constructor， 初始化海龟信号的策略参数（默认不检查上一笔盈亏，默认缓存60根K线）"""
        self.portfolio = portfolio  # 投资组合

        self.vt_symbol = vt_symbol  # 合约代码
        self.entry_window = entry_window  # 入场通道周期数
        self.exit_window = exit_window  # 出场通道周期数
        self.atr_window = atr_window  # 计算ATR周期数
        self.profit_check = profit_check  # 是否检查上一笔盈利

        self.am = ArrayManager(60)  # K线容器

        self.atr_volatility = 0  # ATR波动率
        self.entry_up = 0  # 入场通道
        self.entry_down = 0
        self.exit_up = 0  # 出场通道
        self.exit_down = 0

        self.long_entry1 = 0  # 多头入场位
        self.long_entry2 = 0
        self.long_entry3 = 0
        self.long_entry4 = 0
        self.long_stop = 0  # 多头止损位

        self.short_entry1 = 0  # 空头入场位
        self.short_entry2 = 0
        self.short_entry3 = 0
        self.short_entry4 = 0
        self.short_stop = 0  # 空头止损位

        self.unit = 0  # 信号持仓
        self.result = None  # 当前的交易
        self.result_list = []  # 交易列表
        self.bar = None  # 最新K线

    def on_bar(self, bar):
        """ 缓存足够K线后，开始计算相关技术指标，判断交易信号 """
        self.bar = bar
        self.am.update_bar(bar)
        if not self.am.inited:
            return
        self.generate_signal(bar)
        self.calulate_indicator()

    def generate_signal(self, bar):
        """
        判断交易信号
        要注意在任何一个数据点：buy/sell/short/cover只允许执行一类动作

        负责交易信号的判断，平仓信号与开仓信号是分开的：优先检查平仓，没有仓位或者持有多头仓位的时候，在设置好入场位做多或加仓；
        没有仓位或者持有空头仓位的时候，在设置好入场位做空或者加仓
        """
        # 如果指标尚未初始化，则忽略
        # 在 calculate_indicator里面初始化，初始化的时候，所有long+short 1,2,3,4都计算完成且不会变了。
        if not self.long_entry1:
            return

        # 优先检查平仓
        if self.unit > 0:
            long_exit = max(self.long_stop, self.exit_down)

            if bar.low <= long_exit:
                self.sell(long_exit)
                return
        elif self.unit < 0:
            short_exit = min(self.short_stop, self.exit_up)
            if bar.high >= short_exit:
                self.cover(short_exit)
                return

        # 没有仓位或者持有多头仓位的时候，可以做多（加仓）
        if self.unit >= 0:
            trade = False

            if bar.high >= self.long_entry1 and self.unit < 1:
                self.buy(self.long_entry1, 1)
                trade = True

            if bar.high >= self.long_entry2 and self.unit < 2:
                self.buy(self.long_entry2, 1)
                trade = True

            if bar.high >= self.long_entry3 and self.unit < 3:
                self.buy(self.long_entry3, 1)
                trade = True

            if bar.high >= self.long_entry4 and self.unit < 4:
                self.buy(self.long_entry4, 1)
                trade = True

            if trade:
                return

        # 没有仓位或者持有空头仓位的时候，可以做空（加仓）
        if self.unit <= 0:
            if bar.low <= self.short_entry1 and self.unit > -1:
                self.short(self.short_entry1, 1)

            if bar.low <= self.short_entry2 and self.unit > -2:
                self.short(self.short_entry2, 1)

            if bar.low <= self.short_entry3 and self.unit > -3:
                self.short(self.short_entry3, 1)

            if bar.low <= self.short_entry4 and self.unit > -4:
                self.short(self.short_entry4, 1)

    def calculate_indicator(self):
        """ 计算技术指标
            负责计算指标的产生，包括计算入场和止盈离场的唐奇安通道上下轨，判断到有单位持仓后，
            计算ATR指标并且设定随后8个入场位置（做多4个和做空4个），同时初始化离场价格。
        """
        self.entry_up, self.entry_down = self.am.donchian(self.entry_window)
        self.exit_up, self.exit_down = self.am.donchian(self.exit_window)

        # 有持仓后，ATR波动率和入场位等都不再变化
        if not self.unit:
            self.atr_volatility = self.am.atr(self.atr_window)

            self.long_entry1 = self.entry_up
            self.long_entry2 = self.entry_up + self.atr_volatility * 0.5
            self.long_entry3 = self.entry_up + self.atr_volatility * 1
            self.long_entry4 = self.entry_up + self.atr_volatility * 1.5
            self.long_stop = 0  # 只有等第一笔买入时才能计算

            self.short_entry1 = self.entry_down
            self.short_entry2 = self.entry_down - self.atr_volatility * 0.5
            self.short_entry3 = self.entry_down - self.atr_volatility * 1
            self.short_entry4 = self.entry_down - self.atr_volatility * 1.5
            self.short_stop = 0 # 只有等第一笔卖出时才能计算

    def new_signal(self, direction, offset, price, volume):
        """ 定义海龟投资组合的发单委托，分别是多空方向、开仓平仓、停止单价格、合约手数。 """
        # ??? 最终的交易是在portfolio class 里完成的吗？？？
        self.portfolio.new_signal(self, direction, offset, price, volume)

    def buy(self, price, volume):
        """ 买入开仓； 先传入计算好的停止单价格，缓存开仓委托的价格和手数，发出投资组合的多开委托，基于最后一次加仓价格计算止损离场位置。"""
        price = self.calculate_trade_price(Direction.LONG, price)

        self.open(price, volume)
        self.new_signal(Direction.LONG, Offset.OPEN, price, volume)

        # 以最后一次加仓价格，加上两倍N计算止损
        self.long_stop = price - self.atrVolatility * 2

    def sell(self, price, volume):
        """先传入计算好的停止单价格，缓存平仓委托的价格，发出投资组合空平的委托"""
        pass

    def short(self, price, volume):
        """先传入计算好的停止单价格，缓存开仓委托的价格和手数，发出投资组合的空开委托，基于最后一次加仓价格计算止损离场位置。"""

    def cover(self, price, volume):
        """先传入计算好的停止单价格，缓存平仓委托的价格，发出投资组合多平的委托。"""

    def open(self, price, change):
        """计算累计开仓手数 / 单位头寸，调用TurtleResult类定义的open函数计算开仓平均成本。"""

    def close(self, price):
        """调用TurtleResult类定义的close函数计算单笔开平仓交易盈亏。创建列表专门缓存开平仓交易盈亏。"""

    def get_last_pnl(self):
        """在开平仓交易盈亏列表中获取上一笔交易的盈亏"""

    def calculate_trade_price(self, direction, price):
        """计算成交价格； 设置停止单价格，要求买入时，停止单成交的最优价格不能低于当前K线开盘价；
        卖出时，停止单成交的最优价格不能高于当前K线开盘价"""
        # 买入时，停止单成交的最优价格不能低于当前K线开盘价
        if direction == Direction.LONG:
            # ZL: 如果开盘的时候突破了通道，则只能以开盘的价格来成交
            # 这里关键字是：停止单
            trade_price = max(self.bar.open, price)
        # 卖出时，停止单成交的最优价格不能高于当前K线开盘价
        else:
            trade_price = min(self.bar.open, price)

        return trade_price
