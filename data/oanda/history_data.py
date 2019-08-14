from datetime import datetime
import pandas as pd

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
    # Value	Description
    # S5	5 second candlesticks, minute alignment
    # S10	10 second candlesticks, minute alignment
    # S15	15 second candlesticks, minute alignment
    # S30	30 second candlesticks, minute alignment
    # M1	1 minute candlesticks, minute alignment
    # M2	2 minute candlesticks, hour alignment
    # M4	4 minute candlesticks, hour alignment
    # M5	5 minute candlesticks, hour alignment
    # M10	10 minute candlesticks, hour alignment
    # M15	15 minute candlesticks, hour alignment
    # M30	30 minute candlesticks, hour alignment
    # H1	1 hour candlesticks, hour alignment
    # H2	2 hour candlesticks, day alignment
    # H3	3 hour candlesticks, day alignment
    # H4	4 hour candlesticks, day alignment
    # H6	6 hour candlesticks, day alignment
    # H8	8 hour candlesticks, day alignment
    # H12	12 hour candlesticks, day alignment
    # D	    1 day candlesticks, day alignment
    # W	    1 week candlesticks, aligned to start of week
    # M	    1 month candlesticks, aligned to first day of the month
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
    #               NOTE: for this function, only single character is allowed!!!
    #
    # for more detailed description: http://developer.oanda.com/rest-live-v20/instrument-ep/
    config = oanda_cfg.make_config_instance()
    api = config.create_context()
    # Fetch the candles
    response = api.instrument.candles(instrument, **kwargs)
    if response.status != 200:
        raise Exception(response.body)

    header = ["Time", "Open", "High", "Low", "Close", "Volume"]
    df = pd.DataFrame(columns=header)
    candles = response.get("candles", 200)
    for candle in candles:
        rec = list()
        # time
        rec.append(candle.time)
        for price in ["mid", "bid", "ask"]:
            c = getattr(candle, price, None)
            if c is None:
                continue
            rec.append(c.o)
            rec.append(c.h)
            rec.append(c.l)
            rec.append(c.c)
            break
        # volume
        rec.append(candle.volume)
        # add the record into dataframe
        df.loc[len(df)] = rec
    return df


if __name__ == "__main__":
    # instruments = load_available_instrument()
    # for i in instruments:
    #     print(i.name)
    #
    instrument = 'CN50_USD'
    kwargs = dict()
    kwargs["granularity"] = 'M1'
    kwargs["fromTime"] = '2019-01-01T00:00:00.000000000Z'
    df = load_candle(instrument, **kwargs)
    print(df.loc[0])

