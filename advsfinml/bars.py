import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

data = pd.read_csv('C:\\tmpwork\\data\\trade_20181127.csv')
# append few more days
data = data.append(pd.read_csv('C:\\tmpwork\\data\\trade_20181128.csv'))
data = data.append(pd.read_csv('C:\\tmpwork\\data\\trade_20181129.csv'))
data = data[data.symbol == 'XBTUSD']
# timestamp parsing, convert string to time
data['timestamp'] = data.timestamp.map(lambda t: datetime.strptime(t[:-3], '%Y-%m-%dD%H:%M:%S.%f'))


def compute_vwap(df):
    q = df['foreignNotional']
    p = df['price']
    vwap = np.sum(p*q) / np.sum(q)
    df['vwap'] = vwap


data_timeidx = data.set_index('timestamp')
data_time_grp = data_timeidx.groupby(pd.Grouper(freq='15Min'))
num_time_bars = len(data_time_grp)
data_time_vwap = data_time_grp.apply(compute_vwap)