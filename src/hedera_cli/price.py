import requests
import json


def get_Hbar_price(others=False):
    "doc: https://www.coingecko.com/api/documentations/v3#/"
    url = 'https://api.coingecko.com/api/v3/coins/hedera-hashgraph'
    params = {'localization': 'en',
              'tickers': 'false',
              'market_data': 'true',
              'community_data': 'false',
              'developer_data': 'false',
              'sparkline': 'false'}
    r = requests.get(url, params=params)
    data = r.json()
    if others:
        return data['market_data']['current_price']
    else:
        return data['market_data']['current_price']['usd']
