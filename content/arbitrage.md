Title: Arbitrage
Author: Nekrasov Pavel
Date: 2018-06-06 15:00
Category: Blog
Tags: trading, arbitrage
Slug: arbitrage
Summary: Here, we will give some detail on how to do real trading using arbitrage. There are always many ways to do so, and the method below is just one of them. But the key ideas are same. 

This post is based on [High Frequency Trading and Probability Theory - Zhaodong Wang](https://ru.scribd.com/document/346123211/High-Frequency-Trading-and-Probability-Theory-Zhaodong-Wang)

"Here, we will give some detail on how to do real trading using arbitrage.
There are always many ways to do so, and the method below is just one of
them. But the key ideas are same."

1. Process of Arbitrage

    1. [Pseudo instrument](pseudo-instrument.html)
    2. Arbitrage combination and price averaging. 
    There are some ways to find a suitable arbitrage
    combination. The first is using some knowledge of economics or industry
    to find a potential combination, like the calendar spread, cross-market and
    cross-product arbitrage we have mentioned.
    The other way is just to hunt through the numerous market data and find a stable combination, and then
    try to make an explanation of it.
    The second technique is now a typical one
    for modern trading.
    After finding a combination, we should make a decision about the buy or
    sell price for this combination. The most popular way to decide is to utilize
    some kind of average history of the prices of the combination market data.
    We can base our decision on the average of the last prices, or the counterparty
    price in the different market. We can use a short period market data to
    calculate, or use a longer period one. A short period may be helpful for not
    relying so much on a stable arbitrage, such as cross-product combination,
    and a long period can be used for more stable arbitrage, such as calendar
    spread. And there are still several average methods we can choose to
    use: arithmetic average, value-added average or moving average. All these
    methods may be effective. The best method can be found only through deep
    analysis on real market data.
    3. Trading processes types are, removal and passive.
    **Removal** means to always take the counterparty price for all the legs.
    One tries to buy on ask price, and sell at bid price. It is similar to using
    combination market data. The problem is that the real orders are based on
    each leg; we cannot ensure that these legs are all traded simultaneously. If
    some legs are traded and some are not, normally we may use some deep
    price to trade for these non-traded legs, though we know that it may cause a
    miss, it is still better than keeping unbalanced positions for a long time. For
    some legs, their order book is thick, which means there are many orders in
    their order book continuously. We will not lose a lot if we have a miss on
    them. But legs with thin order books will be very dangerous. There may be
    a large gap behind the best bid or ask price, and a miss will cause serious
    loss. Therefore, one of the most popular practices in the area is to find one
    leg with the thinnest order book, and try to make a trade in this leg first. If
    the trade is made, then we shall try to trade on all other legs with thicker
    order books. In this case, we will not have a very large miss. If this leg
    cannot be traded, we can just cancel the order and do nothing with the other
    legs. We will just lose this opportunity to trade with anything, without any
    miss at all. This will be a safer way. Normally, we can predict the thickness
    of the order book by studying the market, and in most cases, the difference
    is very obvious. In some cases, we can detect the thickness in trading time,
    and make the decision on the first trading leg based on it.
    **Passive** trading is to place orders at the desired price in order book, and
    wait for counterparties to trade with them. While participating in arbitrage,
    we can only do passive trading in one leg, and after trading, remove all
    other legs. We can do so at any leg of the combination, but similar to the
    consideration of removal, we would better be passive in the leg with thinnest
    order book. There are many kinds of refinement for passive trading. Some
    are focused on getting a better price, some on placing multi-layer orders to
    minimize the time gap between order cancelling, and some on getting better
    time priority for its price level. Traders often give new ideas for these kinds
    of processes based on the understanding of the market microstructure.
    Both removal and passive trading are important processes for arbitrage.
    Removal trading is simple and safe compared with passive trading.
    But passive trading may get a better price than removal, the difference is the
    bid-ask spread of the market data of the leg performing passive trading.And
    passive trading will have much more trading opportunities. But since you
    always put some orders in the exchange, any system problem may cause
    serious result.
    
2. Different Types of Arbitrage

    1. [Calendar spread](calendar-spread.html)
    2. [Cross-market arbitrage](cross-market-arbitrage.html)
    3. Cross-product arbitrage refers to using the internal relationship
    between several products, and trading among them. Cross-product arbitrage
    is widely used in the securities market in the US and Europe. It assumes that
    they should have a similar performance for similar stocks. This might occur
    because both companies are working in same industry. One may also assume
    that stocks for corporations in one supply chain will have the opposite
    performance if the final market has no change. This kind of arbitrage is
    called alpha arbitrage. In the futures market, cross-product arbitrage is often
    used for products in one step of manufacturing. For example, we know that
    most parts of soybeans are crushed into soybean oil, and the remaining
    part is soybean meal. All these three products are traded in the Dalian
    Commodity Exchange (DCE). Below, we have a graph displaying such a
    combination. According to some domain knowledge of the industry, about
    5 units of soybean can be crushed to 1 unit of soybean oil, and the remaining
    are 4 units of soybean meals. We use the price of soybean oil (y1305), plus
    the price of soybean meal (m1305) multiplied by 4, and subtract the price
    of soybean (a1305) multiplied by 5.
