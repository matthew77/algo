from vnpy.trader.utility import ArrayManager
from vnpy.trader.constant import (Direction, Offset)
from collections import defaultdict

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
        """ 买入开仓；
            先传入计算好的停止单价格，缓存开仓委托的价格和手数，发出投资组合的多开委托，基于最后一次加仓价格计算止损离场位置。
            关键字：开仓 """
        price = self.calculate_trade_price(Direction.LONG, price)

        self.open(price, volume)
        self.new_signal(Direction.LONG, Offset.OPEN, price, volume)

        # 以最后一次加仓价格，加上两倍N计算止损
        self.long_stop = price - self.atr_volatility * 2

    def sell(self, price, volume):
        """ 卖出平仓；
            先传入计算好的停止单价格，缓存平仓委托的价格，发出投资组合空平的委托
            关键字：平仓 """
        price = self.calculate_trade_price(Direction.SHORT, price)
        volume = abs(self.unit)

        self.close(price)
        self.new_signal(Direction.SHORT, Offset.CLOSE, price, volume)

    def short(self, price, volume):
        """卖出开仓
            先传入计算好的停止单价格，缓存开仓委托的价格和手数，发出投资组合的空开委托，基于最后一次加仓价格计算止损离场位置。
            关键字：开仓 """
        price = self.calculate_trade_price(Direction.SHORT, price)

        self.open(price, -volume)
        self.new_signal(Direction.SHORT, Offset.OPEN, price, volume)

        # 以最后一次加仓价格，加上两倍N计算止损
        self.short_stop = price + self.atr_volatility * 2

    def cover(self, price, volume):
        """买入平仓；
            先传入计算好的停止单价格，缓存平仓委托的价格，发出投资组合多平的委托。
            关键字：平仓 """
        price = self.calculate_trade_price(Direction.LONG, price)
        volume = abs(self.unit)

        self.close(price)
        self.new_signal(Direction.LONG, Offset.CLOSE, price, volume)

    def open(self, price, change):
        """ 开仓
            计算累计开仓手数 / 单位头寸，调用TurtleResult类定义的open函数计算开仓平均成本。"""
        self.unit += change

        if not self.result:
            self.result = TurtleResult()
        self.result.open(price, change)

    def close(self, price):
        """平仓
            调用TurtleResult类定义的close函数计算单笔开平仓交易盈亏。创建列表专门缓存开平仓交易盈亏。"""
        self.unit = 0

        self.result.close(price)
        self.result_list.append(self.result)
        self.result = None

    def get_last_pnl(self):
        """ 获取上一笔交易的盈亏；
            在开平仓交易盈亏列表中获取上一笔交易的盈亏"""
        if not self.result_list:
            return 0

        result = self.result_list[-1]
        return result.pnl

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


class TurtlePortfolio:
    """海龟组合"""

    def __init__(self, engine):
        """Constructor， 初始化海龟投资组合的组合市值（即账户资金）和多空头持仓，创建多个字典分别缓存海龟信号、每个品种持仓情况、
            交易中的信号、合约大小、单位头寸规模、真实持仓量。"""
        self.engine = engine

        self.signal_dict = defaultdict(list)

        self.unit_dict = {}  # 每个品种的持仓情况
        self.total_long = 0  # 总的多头持仓
        self.total_short = 0  # 总的空头持仓

        self.trading_dict = {}  # 交易中的信号字典

        self.size_dict = {}  # 合约大小字典
        self.multiplier_dict = {}  # 按照波动幅度计算的委托量单位字典
        self.pos_dict = {}  # 真实持仓量字典

        self.portfolio_value = 0  # 组合市值

    def init(self, portfolio_value, vt_symbol_list, size_dict):
        """ 传入组合市值和合约大小字典，调用TurtleSignal类来产生短周期版本和
            长周期版的交易信号（包括入场，止盈，止损），同时缓存到信号字典中。 """
        self.portfolio_value = portfolio_value
        self.size_dict = size_dict

        for vt_symbol in vt_symbol_list:
            signal1 = TurtleSignal(self, vt_symbol, 20, 10, 20, True)  # 短周期
            signal2 = TurtleSignal(self, vt_symbol, 55, 20, 20, False)  # 长周期

            l = self.signal_dict[vt_symbol]
            l.append(signal1)
            l.append(signal2)

            self.unit_dict[vt_symbol] = 0
            self.pos_dict[vt_symbol] = 0

    def on_bar(self, bar):
        """ 根据信号字典产生具体交易委托 """
        for signal in self.signal_dict[bar.vt_symbol]:
            signal.on_bar(bar)

    def new_signal(self, signal, direction, offset, price, volume):
        """ 对交易信号进行过滤，符合条件的才发单执行
            先计算单位头寸规模，然后若委托指令是开仓需要检查上一次是否盈利，若无盈利发出买入/卖空委托；若委托指令是平仓，
            需要注意平仓量不能超过空头持仓。同时注意单品种和组合持仓都不能超过上限。"""
        unit = self.unit_dict[signal.vt_symbol]

        # 如果当前无仓位，则重新根据波动幅度计算委托量单位
        if not unit:
            size = self.size_dict[signal.vt_symbol]
            risk_value = self.portfolio_value * 0.01
            multiplier = risk_value / (signal.atr_volatility * size)
            multiplier = int(round(multiplier, 0))
            self.multiplier_dict[signal.vt_symbol] = multiplier
        else:
            multiplier = self.multiplier_dict[signal.vt_symbol]

        # 开仓
        if offset == Offset.OPEN:
            # 检查上一次是否为盈利
            # ZL：？？？短周期适用？？？
            if signal.profit_check:
                pnl = signal.get_Last_pnl()
                if pnl > 0:
                    return

            # 买入
            if direction == Direction.LONG:
                # 组合持仓不能超过上限
                if self.total_long >= MAX_DIRECTION_POS:
                    return

                # 单品种持仓不能超过上限
                if self.unit_dict[signal.vt_symbol] >= MAX_PRODUCT_POS:
                    return
            # 卖出
            else:
                if self.total_short <= -MAX_DIRECTION_POS:
                    return

                if self.unit_dict[signal.vt_symbol] <= -MAX_PRODUCT_POS:
                    return
        # 平仓
        else:
            if direction == Direction.LONG:
                # 必须有空头持仓
                if unit >= 0:
                    return

                # 平仓数量不能超过空头持仓
                volume = min(volume, abs(unit))
            else:
                if unit <= 0:
                    return

                volume = min(volume, abs(unit))

        # 获取当前交易中的信号，如果不是本信号，则忽略
        current_signal = self.trading_dict.get(signal.vt_symbol, None)
        if current_signal and current_signal is not signal:
            return

        # 开仓则缓存该信号的交易状态
        if offset == Offset.OPEN:
            self.trading_dict[signal.vt_symbol] = signal
        # 平仓则清除该信号
        else:
            self.trading_dict.pop(signal.vt_symbol)

        self.send_order(signal.vt_symbol, direction, offset, price, volume, multiplier)

    def send_order(self, vt_symbol, direction, offset, price, volume, multiplier):
        """ 计算单品种持仓和整体持仓，向回测引擎中发单记录 """
        # 计算合约持仓
        if direction == Direction.LONG:
            self.unit_dict[vt_symbol] += volume
            self.pos_dict[vt_symbol] += volume * multiplier
        else:
            self.unit_dict[vt_symbol] -= volume
            self.pos_dict[vt_symbol] -= volume * multiplier

        # 计算总持仓
        self.total_long = 0
        self.total_short = 0

        for unit in self.unit_dict.values():
            if unit > 0:
                self.total_long += unit
            elif unit < 0:
                self.total_short += unit

        # 向回测引擎中发单记录
        self.engine.send_order(vt_symbol, direction, offset, price, volume * multiplier)
