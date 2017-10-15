# YaMS - Yet another MarketScanner

This piece of code pulls data from an exchange and adds some indicators to the stream. When there is a buy signal, 
based on the strategy you've add as a plugin, you can send out a message via Telegram. There is also the possibility
to test your strategies.

# Features
- Supported Exchanges:
  - Bittrex (via REST-Api)
- Send messages to Telegram
- create your own strategy as plugin
- Backtest all your strategies, based on your data


# Development
- add config
```cp sample.config.yml config.yml```
- edit config
- start YaMS container
```
docker build -t yams_img -f docker/Dockerfile_yams . && \
mkdir -p data-btrx && \
docker run --rm -it --name yams_cont -v `pwd`/data-btrx:/data yams_img /yams/start.sh
```
- start Backtesting
```
docker build -t yams_img -f docker/Dockerfile_yams . && \
mkdir -p data-btrx && \
docker run --rm -it --name yams_cont -v `pwd`/data-btrx:/data yams_img /yams/start_backtesting.sh
```

# Production
- add config
```cp sample.config.yml config.yml```
- edit config
- start YaMS container in daemon mode
```
docker build -t yams_img -f docker/Dockerfile_yams . && \
mkdir -p data-btrx && \
docker run --rm -d -it --name yams_cont -v `pwd`/data-btrx:/data yams_img /yams/start.sh
```

# TODO
## Short-Term
- if error getting ticker data -> send to telegram chat
- renaming T -> time, etc. <<< do it in receivers
- first check for validity of data, else retrieve data again
  - check for if latest['time'] < ticker_len, to make sure that current data is received, if not put pair back to working queue
- graceful shutdown
- optimize backtesting
  - buy price: last_price + 0.00000001 and sell at 5%
- move to db persistence

## Long-Term
- do we need to sync time every minute in docker container?!
- move from pull-data from exchg to pubsub/websocket

# Contributing
Feel like there is a feature missing? I welcome your pull requests! Few pointers for contributions:

- Create your PR against the `master` branch
- If you are unsure, discuss the feature on `btc-echo.de` slack in room `#tools` or in a [issue](https://github.com/YaMSorg/yams/issues) before a PR

# Donations
Feel like you wanna honor my work? That's awesome! Here are the wallets you can send your donation to me:

* BTC: 1DtiU3RXGsNGAdMy3dUuojS1aC5b9Lwhgb
* ETH: 0xd7e3d15ead57b1d02d96fa1ca34d036274685d38
* XVG: D7wzNjWrtznvQ5vRgApTsGA4p6c61K7592
