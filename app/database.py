# -*- coding: utf-8 -*-
# Create Time: 11/09 2021
# Author: Yunquan (Clooney) Gu
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db


class FireBase:
    def __init__(self):
        cred = credentials.Certificate('./moonshot-ccfe7-firebase-adminsdk-eb11p-969fc7457f.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://moonshot-ccfe7-default-rtdb.firebaseio.com/'
        })
        self.coin_ref = db.reference('Coins')
        # print(self.coin_ref.get())

    def get_all(self):
        return self.coin_ref.get()

    def update_coin(self, token, body):
        self.coin_ref.update({
            token: body
        })

    def add_coin(self, body):
        self.coin_ref.update(body)

    def update_price(self, coin_name, price):
        self.coin_ref.child(coin_name).child('market_data').update({'current_price': price})


if __name__ == '__main__':
    fb = FireBase()

    # Clear all coins
    fb.coin_ref.set({})

    # print(fb.get_all().keys())