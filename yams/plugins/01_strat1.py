import json
import logging
import talib.abstract as ta

from wrapt import synchronized

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

info_msg = """*Strategy 'STRAT 1'*
StochRSI: %s
"""


@synchronized
def populate_indicators_and_buy_signal(dataframe):
    dataframe['close_30_ema'] = ta.EMA(dataframe, timeperiod=30)
    dataframe['close_90_ema'] = ta.EMA(dataframe, timeperiod=90)

    dataframe['sar'] = ta.SAR(dataframe, 0.02, 0.2)

    stochrsi = ta.STOCHRSI(dataframe)
    dataframe['stochrsi'] = stochrsi['fastd']  # values between 0-100, not 0-1

    macd = ta.MACD(dataframe)
    dataframe['macd'] = macd['macd']
    dataframe['macds'] = macd['macdsignal']
    dataframe['macdh'] = macd['macdhist']

    dataframe.loc[
        (dataframe['stochrsi'] < 20)
        & (dataframe['macd'] > dataframe['macds'])
        & (dataframe['close'] > dataframe['sar']),
        'buy'
    ] = 1
    dataframe.loc[dataframe['buy'] == 1, 'buy_price'] = dataframe['close']

    return dataframe, info_msg % (dataframe.iloc[-1]['stochrsi'])


#
# MAiN
#
if __name__ == "__main__":
    import sys
    import pprint

    pp = pprint.PrettyPrinter(indent=2)

    BASE_CUR = "BTC"

    if len(sys.argv) < 2:
        print "usage: $0 XVG"
    else:
        from libyams.tickerdata import btrx_get_ticker, parse_ticker_dataframe

        data = btrx_get_ticker("%s-%s" % (BASE_CUR, sys.argv[1]))
        dataframe = populate_indicators_and_buy_signal(parse_ticker_dataframe(data))

        pp.pprint(dataframe)
