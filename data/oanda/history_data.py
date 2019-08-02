# load history data from Oanda api
import data.oanda.config as oanda_cfg


def load_available_instrument():
    config = oanda_cfg.make_config_instance()
    account_id = config.active_account
    api = config.create_context()
    response = api.account.instruments(account_id)
    instruments = response.get("instruments", "200")
    instruments.sort(key=lambda i: i.name)
    ###???没必要吧？？？先期也就是找几个可以入围的品种就行了。

