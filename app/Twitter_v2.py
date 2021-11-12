import asyncio
import datetime
import re

from Scweet.scweet import scrape
from loguru import logger
from pycoingecko import CoinGeckoAPI

from app.database import FireBase

coin_pattern = re.compile(r"[$][a-zA-Z]+")


class Twitter:
    def __init__(self,
                 start_time: datetime.datetime,
                 db: FireBase
                 ):
        self.last_execute_time = start_time - datetime.timedelta(days=1)
        self.db = db
        self.cg = CoinGeckoAPI()
        self.coin_list = self.cg.get_coins_list()

    async def acquire_hot_coins_list(self):
        # Parsing data from twitter
        tweets_df = scrape(
            words=['coin', 'token', 'crypto', 'metaverse', 'defi', 'nft', 'dao', 'bitcoin', 'eth', 'binance'],
            since=self.last_execute_time.strftime('%Y-%m-%d'),
            # since="2021-11-08",
            headless=False,
            interval=1, display_type="Top", lang="en")

        # Find coin from messages
        hot_coin_set = set()
        for Embedded_text in tweets_df['Embedded_text']:
            hot_coin_set.update(coin_pattern.findall(Embedded_text))
        logger.info(f"update hot_coin_set: {hot_coin_set}")
        self.last_execute_time = datetime.datetime.now() - datetime.timedelta(days=1)

        # hot_coin_set = ['argo', 'boat', 'dogebonk', 'dogecoin', 'feg-token', 'floki-inu', 'ftx-token', 'handshake',
        #                 'heroverse', 'insight-protocol', 'robotina', 'saja', 'shibalana', 'solana', 'xdollar']
        await asyncio.gather(*[self._lookup_coins(c) for c in hot_coin_set])

    def update_coin(self, coin_name, target_coin):
        logger.info(f'update {coin_name}, {target_coin}')
        body = {}
        _id = body['id'] = target_coin['id']
        body['symbol'] = target_coin['symbol']
        body['name'] = target_coin['name']
        for key in target_coin['platforms']:
            if key:
                body['platforms'] = key
                body['address'] = target_coin['platforms'][key]
                break

        body['categories'] = target_coin["categories"]

        for size in target_coin['image']:
            body[f'image-{size}'] = target_coin['image'][size]

        for webpage in target_coin['links']:
            if isinstance(target_coin['links'][webpage], str):
                body[f'links-{webpage}'] = target_coin['links'][webpage]
            elif isinstance(target_coin['links'][webpage], list):
                body[f'links-{webpage}'] = target_coin['links'][webpage][0]

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

        body['public_interest'] = target_coin['public_interest_score']

        self.db.add_coin({
            _id: body
        })

    async def _lookup_coins(self, coin: str):
        coin_name = coin.strip("$").lower()
        logger.info(f"Lookup coin[{coin_name}]")

        target_coin, volume = None, -1

        for coin in self.coin_list:
            if coin_name in [coin['name'], coin['symbol'], coin['id']]:
                info = self.cg.get_coin_by_id(coin['id'])
                if info['market_data']['total_volume']['usd'] > volume:
                    volume = info['market_data']['total_volume']['usd']
                    target_coin = info

        logger.info(target_coin)
        if target_coin and target_coin not in self.coin_list:
            logger.info(f'Add coin {coin_name}')
            self.update_coin(coin_name, target_coin)

    async def update_all_coins_detail(self):
        allCoins = self.db.get_all()
        logger.info(f'update coin price')
        prices = self.cg.get_price(','.join(c for c in allCoins if c), 'usd')
        logger.info(prices)
        for coin_name in prices:
            self.db.update_price(coin_name, prices[coin_name]['usd'])
