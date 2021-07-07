import requests
import json


def get_Hbar_price():
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
    price_usd = data['market_data']['current_price']['usd']
    return price_usd
