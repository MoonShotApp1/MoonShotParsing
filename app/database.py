# -*- coding: utf-8 -*-
# Create Time: 11/09 2021
# Author: Yunquan (Clooney) Gu
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db


class FireBase:
    def __init__(self,
                 certificate_file: str,
                 firebase_url: str):
        cred = credentials.Certificate(certificate_file)
        firebase_admin.initialize_app(cred, {
            'databaseURL': firebase_url
        })

        # Reference to the coins
        self.coin_ref = db.reference('Coins')

        # All coins
        self.all_coins = self.coin_ref.get()

    def get_all(self):
        # Get all the coin information
        self.all_coins = self.coin_ref.get()
        return self.all_coins

    def update_coin(self, token_id, body):
        # Update a coin
        self.coin_ref.update({
            token_id: body
        })

    def update_price(self, coin_name, price):
        self.coin_ref.child(coin_name).update({'market_data-current_price': price})
