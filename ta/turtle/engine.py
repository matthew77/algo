from collections import OrderedDict, defaultdict

class BackTestingEngine:
    """组合类CTA策略回测引擎"""

    def __init__(self):
        """Constructor"""
        self.portfolio = None

        # 合约配置信息
        self.vt_symbol_list = []
        self.size_dict = {}  # 合约大小字典
        self.price_tick_dict = {}  # 最小价格变动字典
        self.variable_commission_dict = {}  # 变动手续费字典
        self.fixed_commission_dict = {}  # 固定手续费字典
        self.slippage_dict = {}  # 滑点成本字典

        self.portfolio_value = 0
        self.start_dt = None
        self.end_dt = None
        self.current_dt = None

        self.data_dict = OrderedDict()
        self.trade_dict = OrderedDict()

        self.result = None
        self.result_list = []
