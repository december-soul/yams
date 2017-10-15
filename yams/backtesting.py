import os
import imp
import csv
import json
import time
import logging
import threading

import arrow
from operator import itemgetter

from libyams.utils import get_conf
from libyams.tickerdata import parse_ticker_dataframe

import pprint

pp = pprint.PrettyPrinter(indent=2)

__author__ = "tbl"
__copyright__ = "tbl 2017"
__version__ = "0.1.0"

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()

plugins = {}

ticker_min_dict = {
    'FiveMin': 5,
    'ThirtyMin': 30,
    'Hour': 60,
    'Day': 1440
}

CSV_ll = []


def json_handler(x):
    return str(x)


#
#
#
def calc_percentage(base, p):
    return float(base + ((base / 100) * p))


#
#
#
def calcIndicatorsAndBackTest(pair, fn, tick):
    # just test 30m strategies for now
    if not tick == 'ThirtyMin':
        return

    logger.info("backtesting %s at %s" % (fn, tick))

    data = []
    with open(fn, 'r') as jsonfile:
        data = json.load(jsonfile)
        jsonfile.close()

    for p in plugins[tick]:
        logger.info("bt with plugin: %s" % (p['name']))

        plugin_exec = imp.load_module(p['name'], *p["info"])
        dataframe, info = plugin_exec.populate_indicators_and_buy_signal(parse_ticker_dataframe(data))

        for idx, row in dataframe.iterrows():
            # print row['cci14']

            if row['buy'] == 1:
                logger.debug("signal at idx(%s) for cur(%s) tick(%s) strategy(%s) time(%s)" % (
                idx, pair, tick, p['name'], row['date']))

                percentages = {
                    # '3': {
                    #     'num': 3,
                    #     'price': calc_percentage(row['close'], 3),
                    #     'price_idx': idx
                    # },
                    '5': {
                        'num': 5,
                        'price': calc_percentage(row['close'], 5),
                        'price_idx': idx
                    },
                    # '7': {
                    #     'num': 7,
                    #     'price': calc_percentage(row['close'], 7),
                    #     'price_idx': idx
                    # },
                    # '10': {
                    #     'num': 10,
                    #     'price': calc_percentage(row['close'], 10),
                    #     'price_idx': idx
                    # },
                    # '15': {
                    #     'num': 15,
                    #     'price': calc_percentage(row['close'], 15),
                    #     'price_idx': idx
                    # },
                    # '20': {
                    #     'num': 20,
                    #     'price': calc_percentage(row['close'], 20),
                    #     'price_idx': idx
                    # },
                }

                # threePercentProfit = [c for i, c in dataframe.loc[idx:].iterrows() if c['close'] >= threePercent]

                for pk in percentages.keys():
                    ll = [(i, c) for i, c in dataframe.loc[idx:].iterrows() if c['close'] >= percentages[pk]['price']]

                    if len(ll) > 0:
                        percentages[pk]['profit'] = ll[0][1]['close']
                        percentages[pk]['profit_date'] = ll[0][1]['date']
                        percentages[pk]['profit_idx'] = ll[0][0]
                    else:
                        percentages[pk]['profit'] = 'NONE'
                        percentages[pk]['profit_date'] = 'NONE'
                        percentages[pk]['profit_idx'] = 'NONE'

                logger.debug("buy at    %1.8f" % (row['close']))
                for pk in ['5']:
                    idiff = 'NONE'
                    tdiff = 'NONE'
                    if not percentages[pk]['profit'] is 'NONE':
                        idiff = percentages[pk]['profit_idx'] - percentages[pk]['price_idx']
                        tdiff = arrow.get(dataframe.loc[percentages[pk]['profit_idx']]['date']) - arrow.get(
                            dataframe.loc[percentages[pk]['price_idx']]['date'])

                    logger.debug("profit of %1.8f (%2s%%) is reached at %s (%s ticks || %s h || idx: %s)" % (
                    percentages[pk]['price'], pk, percentages[pk]['profit_date'], idiff, tdiff,
                    percentages[pk]['profit_idx']))

                    if CONFIG['backtesting']['csv_format_enabled']:
                        CSV_ll.append([
                            str(pair),
                            str(tick),
                            str(p['name']),
                            str(row['close']),
                            str(percentages[pk]['price']),
                            str(pk),
                            str(percentages[pk]['profit_date']),
                            str(idiff),
                            str(tdiff)
                        ])

                logger.debug("-" * 5)

    logger.info("finished backtesting %s at %s" % (fn, tick))
    time.sleep(.5)


#
# MAiN
#
if __name__ == "__main__":

    if not CONFIG['bittrex']['enabled']:
        logger.info("please enable bittrex exchange in config!")
        import sys

        sys.exit(0)

    # logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)

    # load plugins and save them in list
    PluginFolder = "./plugins"
    for t in CONFIG["plugins"]:
        plugins[t] = []
        for p in CONFIG["plugins"][t]:
            plugins[t].append({
                "name": p,
                "info": imp.find_module(p, [PluginFolder])
            })

    path = "/data/"
    for f in os.listdir(path):
        pair, short, tick, _ = f.split('__')
        fn = os.path.join(path, f)

        CSV_ll = [[
            "pair",
            "tick",
            "plugin",
            "close",
            "current",
            "percentage",
            "profit_date",
            "idx_diff",
            "time_diff"
        ]]

        calcIndicatorsAndBackTest(pair, fn, tick)

        fn = os.path.join("/data", "bt_data__%s.csv" % (pair))
        # with open(fn, 'wb') as csvfile:
        #     spamwriter = csv.writer(csvfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        #     spamwriter.writerow(";".join(CSV_ll))
        #     csvfile.close()

        with open(fn, 'w') as outfile:
            for line in CSV_ll:
                outfile.write("%s\n" % ";".join(line))

            outfile.close()
