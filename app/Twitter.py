# -*- coding: utf-8 -*-
# Create Time: 11/12 2021
# Author: Yunquan (Clooney) Gu
import asyncio

import tweepy
from loguru import logger
from pycoingecko import CoinGeckoAPI

from app.config import API_KEY, API_KEY_SECRET, COIN_PATTERN, COIN_QUERY
from app.database import FireBase


class Twitter:
    def __init__(self, db: FireBase, count=100):
        self.db = db
        self.cg = CoinGeckoAPI()
        self.coin_list = self.cg.get_coins_list()

        auth = tweepy.AppAuthHandler(API_KEY, API_KEY_SECRET)
        self.api = tweepy.API(auth, wait_on_rate_limit=True)
        self.since_id = None
        self.count = count

    async def acquire_hot_coins_list(self):
        logger.info("Parsing data from twitter")
        count = 0
        hot_coin_set = set()

        # Keep searching until reach the set count
        while count < self.count:
            result = self.api.search_tweets(q=' OR '.join(COIN_QUERY) + '-filter:retweets',
                                            lang='en',
                                            result_type='recent',
                                            count=100,
                                            since_id=self.since_id)
            # since_id in search api means search twitters start from 'since_id'
            # so we need to set the since_id as the max_id from the last result
            self.since_id = result.max_id

            count += len(result)
            for tw in result:
                hot_coin_set.update(COIN_PATTERN.findall(tw.text))

                # Sometime, the coins hide in hashtags
                for hashtag in tw.entities['hashtags']:
                    hot_coin_set.add(hashtag['text'])

        logger.info(f"update hot_coin_set: {hot_coin_set}")
        await asyncio.gather(*[self._lookup_coins(c) for c in hot_coin_set])

    async def _lookup_coins(self, coin: str):
        # Look up coin information by coingecko api
        # There may be coins with the same name, just grab the one with the biggest volume

        coin_name = coin.strip("$").lower()
        logger.info(f"Lookup coin[{coin_name}]")

        target_coin, volume = None, -1

        for coin in self.coin_list:

            # coin name can be in 'name' 'symbol' and 'id' field
            if coin_name in [coin['name'], coin['symbol'], coin['id']]:
                info = self.cg.get_coin_by_id(coin['id'])
                if info['market_data']['total_volume']['usd'] > volume:
                    volume = info['market_data']['total_volume']['usd']
                    target_coin = info

        # Update the database, even if the coin already in the database
        if target_coin:
            logger.info(f'Add coin {target_coin["id"]}')
            self.update_coin(target_coin)

    def update_coin(self, target_coin):
        logger.info(f'update {target_coin["id"]}')
        body = {}

        _id = body['id'] = target_coin['id']
        body['symbol'] = target_coin['symbol']
        body['name'] = target_coin['name']
        body['categories'] = target_coin["categories"]

        # Retrieve the platform of the coin(only one)
        for key in target_coin['platforms']:
            if key:
                body['platforms'] = key
                body['address'] = target_coin['platforms'][key]
                break

        # Retrieve the icon of the coin(three size)
        for size in target_coin['image']:
            body[f'image-{size}'] = target_coin['image'][size]

        # Retrieve the website of the coin
        for webpage in target_coin['links']:
            if isinstance(target_coin['links'][webpage], str):
                body[f'links-{webpage}'] = target_coin['links'][webpage]
            elif isinstance(target_coin['links'][webpage], list):
                body[f'links-{webpage}'] = target_coin['links'][webpage][0]

        # Retrieve the market data(1)
        for item in ['price_change_24h',
                     'price_change_percentage_24h',
                     'price_change_percentage_7d',
                     'price_change_percentage_14d',
                     'price_change_percentage_30d',
                     'price_change_percentage_60d',
                     'price_change_percentage_200d',
                     'market_cap_change_24h',
                     'market_cap_change_percentage_24h',
                     'market_cap_rank',
                     'total_supply',
                     'max_supply']:
            body[f'market_data-{item}'] = target_coin['market_data'].get(item, None)

        # Retrieve the market data(2)
        for item in ['current_price',
                     'high_24d',
                     'low_24d',
                     'market_cap',
                     'price_change_24h_in_currency',
                     'price_change_percentage_1h_in_currency',
                     'price_change_percentage_24h_in_currency',
                     'price_change_percentage_7d_in_currency',
                     'price_change_percentage_14d_in_currency',
                     'price_change_percentage_30d_in_currency',
                     'price_change_percentage_60d_in_currency',
                     'price_change_percentage_200d_in_currency',
                     'price_change_percentage_1y_in_currency',
                     'market_cap_change_24h_in_currency',
                     'market_cap_change_percentage_24h_in_currency']:
            body[f'market_data-{item}'] = target_coin['market_data'].get(item, {'usd': None}).get('usd', None)

        # Retrieve the public interest for sorting
        body['public_interest'] = target_coin['public_interest_score']

        self.db.update_coin(
            token_id=_id,
            body=body
        )

    async def update_all_coins_detail(self):
        allCoins = self.db.get_all()
        logger.info(f'update coin price')

        # query for price with coingecko api
        current_prices = self.cg.get_price(','.join(c for c in allCoins if c), 'usd')
        logger.info(current_prices)

        self.db.coin_ref.update(
            {
                f"{coin_name}/market_data-current_price": current_prices[coin_name].get('usd', -1)
                for coin_name in current_prices
            }
        )
