import json
import logging
import talib.abstract as ta

from wrapt import synchronized

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

info_msg = """*Strategy 'STRAT 2'*
EMA33: %s
SAR: %s
ADX: %s    
"""


@synchronized
def populate_indicators_and_buy_signal(dataframe):
    dataframe['ema'] = ta.EMA(dataframe, timeperiod=33)
    dataframe['sar'] = ta.SAR(dataframe, 0.02, 0.22)
    dataframe['adx'] = ta.ADX(dataframe)

    prev_sar = dataframe['sar'].shift(1)
    prev_close = dataframe['close'].shift(1)
    prev_sar2 = dataframe['sar'].shift(2)
    prev_close2 = dataframe['close'].shift(2)

    # wait for stable turn from bearish to bullish market
    dataframe.loc[
        (dataframe['close'] > dataframe['sar']) &
        (prev_close > prev_sar) &
        (prev_close2 < prev_sar2),
        'swap'
    ] = 1

    # consider prices above ema to be in upswing
    dataframe.loc[dataframe['ema'] <= dataframe['close'], 'upswing'] = 1

    dataframe.loc[
        (dataframe['upswing'] == 1) &
        (dataframe['swap'] == 1) &
        (dataframe['adx'] > 25), # adx over 25 tells there's enough momentum
        'buy'] = 1

    dataframe.loc[dataframe['buy'] == 1, 'buy_price'] = dataframe['close']

    return dataframe, info_msg % (dataframe.iloc[-1]['ema'], dataframe.iloc[-1]['sar'], dataframe.iloc[-1]['adx'])


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
