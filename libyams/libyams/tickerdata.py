import logging
import requests as req

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger('requests.packages.urllib3').setLevel(logging.INFO)
logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)


#
#
#
def get_btc_usd():
    url = "https://api.coindesk.com/v1/bpi/currentprice.json"
    r = req.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    })
    data = r.json()

    if not data["bpi"]:
        raise RuntimeError("coindesk: {}".format(data))

    return data['bpi']['USD']['rate_float']


#
#
#
def get_market_summary():
    url = "https://bittrex.com/api/v2.0/pub/Markets/GetMarketSummaries"
    r = req.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    })
    data = r.json()
    if not data["success"]:
        raise RuntimeError("BITTREX: {}".format(data["message"]))
    return data['result']


#
# get data from BITTREX ticker, possible tick values are: onemin, thirtymin, hour, daily, weekly
#
def btrx_get_ticker(pair, tick='daily'):
    url = 'https://bittrex.com/Api/v2.0/pub/market/GetTicks'
    params = {
        'marketName': pair,
        'tickInterval': tick,
    }

    r = req.get(url, params=params, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    })

    data = r.json()
    if not data['success']:
        raise RuntimeError('BITTREX: {}'.format(data['message']))

    return data['result']


#
# update labels
#
def parse_ticker_dataframe(data):
    from pandas import DataFrame

    df = DataFrame(data) \
        .drop('BV', 1) \
        .rename(columns={'C': 'close', 'V': 'volume', 'O': 'open', 'H': 'high', 'L': 'low', 'T': 'date'}) \
        .sort_values('date')

    return df


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
        pp.pprint(btrx_get_ticker("%s-%s" % (BASE_CUR, sys.argv[1])))
