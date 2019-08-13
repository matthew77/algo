# load history data from Oanda api
import data.oanda.config as oanda_cfg


def load_available_instrument():
    config = oanda_cfg.make_config_instance()
    account_id = config.active_account
    api = config.create_context()
    response = api.account.instruments(account_id)
    instruments = response.get("instruments", "200")
    instruments.sort(key=lambda i: i.name)
    return instruments
    # ???没必要吧？？？先期也就是找几个可以入围的品种就行了。


def load_candle(instrument, **kwargs):
    # instrument - Name of the Instrument [required]
    #
    # **kwargs includes:
    # granularity - The granularity of the candlesticks to fetch [default=S5]
    #
    # smooth -      A flag that controls whether the candlestick is “smoothed” or not. A smoothed candlestick uses the
    #               previous candle’s close price as its open price, while an unsmoothed candlestick uses the first
    #               price from its time range as its open price. [default=False]
    # count -       The number of candlesticks to return in the reponse. Count should not be specified if both the start and
    #               end parameters are provided, as the time range combined with the graularity will determine the number of
    #               candlesticks to return. [default=500, maximum=5000]
    # fromTime -    The start of the time range to fetch candlesticks for.
    #
    # toTime -      The end of the time range to fetch candlesticks for.
    #
    # alignmentTimezone
    #
    # price -       The Price component(s) to get candlestick data for. Can contain any combination of the
    #               characters “M” (midpoint candles) “B” (bid candles) and “A” (ask candles). [default=M]
    #
    # for more detailed description: http://developer.oanda.com/rest-live-v20/instrument-ep/
    config = oanda_cfg.make_config_instance()
    api = config.create_context()
    # Fetch the candles
    response = api.instrument.candles(instrument, **kwargs)
    if response.status != 200:
        raise Exception(response.body)
    candles = response.get("candles", 200)



if __name__ == "__main__":
    instruments = load_available_instrument()
    for i in instruments:
        print(i.name)
