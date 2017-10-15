import os
import imp
import json
import time
import Queue
import logging
import threading

import arrow
from operator import itemgetter

from apscheduler.schedulers.background import BackgroundScheduler

from libyams.utils import get_conf
from libyams.telegram_bot import TelegramHandler
from libyams.tickerdata import get_market_summary, btrx_get_ticker, get_btc_usd, parse_ticker_dataframe

import pprint
pp = pprint.PrettyPrinter(indent=2)


__author__ = "tbl"
__copyright__ = "tbl 2017"
__version__ = "0.1.0"

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()

# queue_recv = Queue.Queue()
queue_anal = Queue.Queue()

# thrds_recv = []
thrds_anal = []

plugins = {}

ticker_min_dict = {
    'FiveMin': 5,
    'ThirtyMin': 30,
    'Hour': 60,
    'Day': 1440
}

msg_buysignal = """BUY SIGNAL for *%s*!

BUY: %1.8f
SELL  (3%%): %1.8f
SELL  (5%%): %1.8f
SELL (10%%): %1.8f

Tick: %s
%s

URL: https://bittrex.com/Market/Index?MarketName=%s
"""

msg_price_chg = """price of *%s* dropped *%4.2f%%* within the last %s hours!

From: %1.8f To : %1.8f

URL: https://bittrex.com/Market/Index?MarketName=%s
"""


#
# analysis thread
#
class CalcIndicators(threading.Thread):
    def __init__(self, pair, fn, tick):
        threading.Thread.__init__(self)
        self.pair = pair
        self.fn = fn
        self.tick = tick
        self.name = "-CalcIndicators-%s_%s" % (self.pair, self.tick)

    def run(self):
        logger.debug("analyzing %s at %s" % (self.fn, self.tick))

        data = []
        with open(self.fn, 'r') as jsonfile:
            data = json.load(jsonfile)
            jsonfile.close()

        #
        # check for last price drop
        #
        if self.tick == "FiveMin":
            dataframe = parse_ticker_dataframe(data)
            latest = dataframe.iloc[-1]

            old_val = float(dataframe.iloc[-2]['close'])
            new_val = float(dataframe.iloc[-1]['close'])
            diff = float(((old_val - new_val) / old_val) * -100)

            if abs(diff) > 10 and diff < 0:
                tdiff = arrow.utcnow() - arrow.get(latest['date'])
                msg = msg_price_chg % ( self.pair, diff, tdiff,

                                        old_val, new_val,

                                        self.pair
                                    )

                logger.info(msg)
                if CONFIG['telegram']['enabled']:
                    TelegramHandler.send_msg(msg)

        else:
            #
            # check for signals from plugins
            #
            for p in plugins[self.tick]:
                logger.debug("analysing with plugin: %s" % (p['name']))

                plugin_exec = imp.load_module(p['name'], *p["info"])
                dataframe, info = plugin_exec.populate_indicators_and_buy_signal(parse_ticker_dataframe(data))

                # print info

                signal = False
                latest = dataframe.iloc[-1]

                if latest['buy'] == 1:
                    signal = True

                logger.info('buy_trigger: %s (pair=%s, tick=%s, strat=%s, signal=%s)', latest['date'], self.pair, self.tick, p['name'], signal)
                # logger.debug(latest)

                if signal:
                    threePercent = latest['close'] + ((latest['close']/100) * 3)
                    fivePercent = latest['close'] + ((latest['close']/100) * 5)
                    tenPercent = latest['close'] + ((latest['close']/100) * 10)

                    msg = msg_buysignal % ( self.pair,

                                            latest['close'],
                                            threePercent,
                                            fivePercent,
                                            tenPercent,

                                            self.tick,
                                            info,

                                            self.pair
                                        )

                    logger.info(msg)
                    if CONFIG['telegram']['enabled']:
                        TelegramHandler.send_msg(msg)

        logger.debug("finished analyzing %s at %s" % (self.fn, self.tick))
        time.sleep(.5)


#
# thread for saving data
#
class SaveTickerData(threading.Thread):
    def __init__(self, pair, tick):
        threading.Thread.__init__(self)
        self.pair = pair
        self.tick = tick
        self.name = "-SaveTickerData-%s_%s" % (self.pair, self.tick)


    def run(self):
        # TODO: check for exceptions
        logger.debug("receiving data for %s at %s" % (self.pair, self.tick))

        new_tickerdata = sorted(btrx_get_ticker(self.pair, self.tick), key=itemgetter('T'))
        fn = os.path.join("/data", "%s__%s__%s__raw.json" % (self.pair, CONFIG['bittrex']['short'], self.tick))

        ticker_dict = {}
        for obj in new_tickerdata:
            if obj['T'] not in ticker_dict:
                ticker_dict[obj['T']] = obj

        # if old data exist, merge new data into it
        if os.path.exists(fn):
            with open(fn, 'r') as jsonfile:
                old_tickerdata = json.load(jsonfile)
                jsonfile.close()

            for obj in old_tickerdata:
                if obj['T'] not in ticker_dict:
                    ticker_dict[obj['T']] = obj

        tickerdata = sorted(ticker_dict.values(), key=itemgetter('T'))

        # # check if we got new data, if not re-add pulling
        # tdiff = arrow.utcnow() - arrow.get(tickerdata[-1]['T'])
        # max_min = ticker_min_dict[CONFIG["checks"]["pricediff"]["ticks"]] + 1
        #
        # pp.pprint("*" * 30)
        # pp.pprint(self.pair)
        # pp.pprint(arrow.utcnow())
        # pp.pprint(arrow.get(tickerdata[-1]['T']))
        # pp.pprint(tdiff.total_seconds()/60)
        # pp.pprint(max_min)
        # pp.pprint("*" * 30)
        #
        # if tdiff > datetime.timedelta(minutes=max_min):
        #     logger.debug(">>>>>>>>>>>>>>>>>>>>> re-adding %s for receiving data at %s" % (self.pair, self.tick))
        #
        #     queue_recv.put({
        #         'todo': 'recv',
        #         'pair': self.pair,
        #         'tick': self.tick,
        #     })
        # else:

        logger.debug("save data for %s at %s" % (self.pair, self.tick))
        # save data - simply as json file! TODO: save in db // Django ORM
        with open(fn, 'w') as outfile:
            json.dump(tickerdata, outfile, indent=2)
            outfile.close()

        queue_anal.put({
            'todo': 'analyse',
            'pair': self.pair,
            'tick': self.tick,
            'fn': fn
        })

        logger.debug("finished receiving data for %s at %s" % (self.pair, self.tick))
        time.sleep(.5)


#
# get related currencies
#
def get_related_currencies():
    rel_curr = []
    btc_usd_price = get_btc_usd()

    # filter out related currencies
    for c in get_market_summary():
        if c['Market']['MarketName'] not in CONFIG["bittrex"]["blacklist"]:
            val = c['Summary']['Last'] * btc_usd_price
            if CONFIG["bittrex"]["min_price_usd"] < val < CONFIG["bittrex"]["max_price_usd"]:
                if CONFIG["bittrex"]["stake_currency_enabled"]:
                    if c['Market']['BaseCurrency'] == CONFIG["bittrex"]["stake_currency"]:
                        rel_curr.append(c)
                else:
                    rel_curr.append(c)

    return rel_curr


#
# data receiving method
#
def receive_data(tick="hour"):

    if not tick in ticker_min_dict.keys():
        logger.info("tick time not supported!")
        return False

    thrds = []

    logger.debug("getting related currencies from market summary")
    for cur in get_related_currencies():
        pair = cur['Summary']['MarketName']

        # TODO: check for thread timeout
        if len(thrds) >= CONFIG["general"]["threads_recv"]:
            for x in thrds:
                x.join()
                thrds.remove(x)

        t = SaveTickerData(pair, tick)
        thrds.append(t)
        t.start()

        if not CONFIG["general"]["production"]:
            return

    for x in thrds:
        x.join()
        thrds.remove(x)

    return True


#
# worker thread for analysis
#
class workerThread(threading.Thread):
    def __init__(self, q):
        threading.Thread.__init__(self)
        self.queue = q
        self.name = "-WorkerThread-"

    def run(self):
        # TODO: check for exceptions
        logger.debug("starting analysis worker thread")
        while True:
            itm = self.queue.get()  # if there is no item, this will wait

            logger.debug("processing item %s" % itm['pair'])

            # TODO: check for thread timeout
            if itm['todo'] == 'analyse':
                if len(thrds_anal) >= CONFIG["general"]["threads_anal"]:
                    for x in thrds_anal:
                        x.join()
                        thrds_anal.remove(x)

                t = CalcIndicators(itm['pair'], itm['fn'], itm['tick'])
                thrds_anal.append(t)
                t.start()

            # if itm['todo'] == 'recv':
            #     if len(thrds_recv) >= CONFIG["general"]["num_threads"]:
            #         for x in thrds_recv:
            #             x.join()
            #             thrds_recv.remove(x)
            #
            #     t = SaveTickerData(itm['pair'], itm['tick'])
            #     thrds_recv.append(t)
            #     t.start()

            self.queue.task_done()
            logger.debug("finished processing item %s" % itm['pair'])


#
# MAiN
#
if __name__ == "__main__":

    if not CONFIG["general"]["production"]:
        logger.info(">>> DEVELOPMENT MODE, NO SCHEDULING <<<")

    if not CONFIG['bittrex']['enabled']:
        logger.info("please enable bittrex exchange in config!")
        import sys

        sys.exit(0)

    # set log level
    if CONFIG['general']['logging'] == 'info':
        logger.setLevel(logging.INFO)

    if CONFIG['general']['logging'] == 'debug':
        logger.setLevel(logging.DEBUG)

    if CONFIG['telegram']['enabled']:
        TelegramHandler.listen()
        TelegramHandler.send_msg('*Status:* `scanner started`')

    # load plugins and save them in list
    PluginFolder = "./plugins"
    for t in CONFIG["plugins"]:
        plugins[t] = []
        for p in CONFIG["plugins"][t]:
            plugins[t].append({
                "name": p,
                "info": imp.find_module(p, [PluginFolder])
            })
    # logger.debug(plugins)

    # start thread for getting item from queue_anal
    t1 = workerThread(queue_anal)
    t1.start()

    # t2 = workerThread(queue_recv)
    # t2.start()

    # # execute data receiver for the first time to bootstrap data
    # receive_data("FiveMin")
    # for s in CONFIG["schedulers"]:
    #     receive_data(s)

    # production mode: set scheduling of executing receiver methods
    if CONFIG["general"]["production"]:
        scheduler = BackgroundScheduler()

        # wait some seconds until data is finished aggregating at bittrex-side
        scheduler.add_job(receive_data, 'cron', minute="*/5", second="13", args=["FiveMin"])

        for s in CONFIG["schedulers"]:
            if not s in ticker_min_dict.keys():
                logger.info("unsupported ticker time")
                import sys
                sys.exit(1)

            if s == "ThirtyMin":
                scheduler.add_job(receive_data, 'cron', minute="*/30", second="21", args=[s])

            if s == "Daily":
                scheduler.add_job(receive_data, 'cron', hour="*/0", minute="1", args=[s])

        scheduler.start()

        try:
            # This is here to simulate application activity (which keeps the main thread alive).
            while True:
                time.sleep(2)

        except (KeyboardInterrupt, SystemExit):
            # Not strictly necessary if daemonic mode is enabled but should be done if possible
            scheduler.shutdown()
