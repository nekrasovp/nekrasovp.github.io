Title: Pseudo instrument
Author: Nekrasov Pavel
Date: 2018-06-05 14:00
Category: Trading
Tags: trading, pseudo instrument
Slug: pseudo-instrument
Summary: Because arbitrage usually traded on several different instruments, the first thing to do is to define a pseudo instrument, which is a combination of instruments.

This post is based on [High Frequency Trading and Probability Theory - Zhaodong Wang](https://ru.scribd.com/document/346123211/High-Frequency-Trading-and-Probability-Theory-Zhaodong-Wang)

Because arbitrage usually traded on several different instruments, the
first thing to do is to define a pseudo instrument, which is a combination of
instruments. Then, we calculate the market data of this pseudo instrument.
Lets go to the calendar spread example for XBT Futures on BitMEX. Because we hope to
trade on the difference of XBTH18 and XBTM18( XBTH18 refers to XBT(Bitcoin), 
Expiration month — H (march), M(june) [https://www.bitmex.com/app/seriesGuide/XBT](https://www.bitmex.com/app/seriesGuide/XBT)),
we use this definition of the combination. Suppose that the data below is the 
current market data of these two instruments.

| Instrument ID | Last Price    | Bid Price  | Bid Volume | Ask Price | Ask Volume
| ------------- |:-------------:| -----:|-----:|-----:|-----:|
| 1. (XBTM18)     | 8300.5 | 8288.0 | 33 | 8300.0 | 5000
| 2. (XBTH18)     | 8130.0 | 8101.5 | 150 | 8103.0 | 13212


There we use top of order book data for example.

Now we should consider the suitable market data for the combination, lets call it C. 
For the last price, it should be the trade price of the last trade, and for the
combination, it should be the difference of the last trade between these two
instruments. Therefore, it should be 8300.5 - 8130.0 = 170.5

```bash
C_last_price = Instr(1).last_price - Instr(2).last_price
```

Now we should consider the bid price and ask price. If we want to buy
a lot of the combination, we should buy 1 lot of XBTM18 and sell 1 lot of
XBTH18. To sell 1 lot of combination means to sell 1 lot of XBTM18 and buy
1 lot of XBTH18. So we need to create pseudo lot function for each trade.

The bid price of the combination should be the price of
selling 1 lot of combination using the counterparty price, which means to
sell 1 lot of XBTM18 and to buy 1 lot of XBTH18 both using the counterparty
prices, and these prices should be the bid price of XBTM18 and the ask price of
XBTH18. Therefore, the bid price of the combination should be the difference
between them, that is: 8288.0 - 8103.0 = 185.0
```bash
C_bid_price = Instr(1).bid_price - Instr(2).ask_price
```
In the same way, the ask price of the combination should be 8300.0 - 8101.5 = 198.5
```bash
C_ask_price = Instr(1).ask_price - Instr(2).bid_price
```
Then we should calculate the bid volume and ask volume. The bid
volume should be the maximum volume we can sell on the counterparty
price at that time. Consider the combination: How many lots can we
sell at 186.5? It should be the minimal of bid volume of XBTM18 and ask
volume of XBTH18, that is min{33, 13212} = 33. And the ask volume should be
min{5000, 150} = 150.
```bash
C_bid_vol = min(Instr(1).bid_volume,Instr(2).ask_volume) 
C_ask_vol = min(Instr(1).ask_volume,Instr(2).bid_volume) 
```
Therefore, the current market data of combination should be as follows:

|Last Price | Bid Price | Bid Volume | Ask Price | Ask Volume
| --------- |:---------:| -----:|-----:|-----:|
|170.5 | 185.0 | 33 | 198.5 | 150


Based on this calculation, we have a new market data for the combination:
all the fields have a similar meaning for a single instrument. Then, we can
do analysis and trading based on this market data, just as if it were a normal
single instrument. 

We can scale with the same technique into depth of order book. 