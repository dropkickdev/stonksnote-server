from app import settings as s

collection_default = [
    dict(name='Shortlist', category='equity', is_locked=True),
    dict(name='Active', category='equity', is_locked=True),
]

# taxonomy_default = [
#     # Tags
#     dict(name='recommended'),
#     dict(name='not-now'),
#     dict(name='invest-soon'),
# ]

taxo_heads = ['markheader', 'exchange', 'tags', 'sector', 'industry', 'currency']

taxo_global = {
    'exchange': [
        dict(name='PSE', label='Philippine Stock Exchange', is_global=True),
        dict(name='SGX', label='Singapore Exchange', is_global=True),
        dict(name='NYSE', label='New York Stock Exchange', is_global=True),
        dict(name='NYSEP', label='NYSE Preferred Shares', is_global=True),
        dict(name='NASDAQ', label='Nasdaq Stock Market', is_global=True),
        dict(name='ARCA', label='ARCA & MKT', is_global=True),
        dict(name='OTC', label='OTC Markets', is_global=True),
        dict(name='FX', label='Forex', is_global=True),
        dict(name='CRYPTO', label='Cryptocurrency', is_global=True),
    ],
    'sector': [
        dict(name='Financials', is_global=True),
        dict(name='Idustrial', is_global=True),
        dict(name='Holding Firms', is_global=True),
        dict(name='Property', is_global=True),
        dict(name='Services', is_global=True),
        dict(name='Mining and Oil', is_global=True),
        dict(name='Small, Medium, and Emerging Board', is_global=True),
        dict(name='ETF', is_global=True),
    ],
    'industry': [],
    'currency': ['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'HKD', 'NZD', 'SEK',
                 'KRW', 'SGD', 'MOK', 'MXN', 'INR', 'RUB', 'ZAR', 'TRY', 'BRL', 'TWD', 'DKK',
                 'PLN', 'THB', 'IDR', 'HUF', 'CZK', 'ILS', 'CLP', 'PHP', 'AED', 'COP', 'SAR',
                 'MYR', 'RON']
    # 'stages': {
    #     'buy_stage': [
    #         dict(label='Buying', is_global=True, description='The buying process'),
    #
    #         dict(name='Shortlist', is_global=True, sort=1,
    #              description='Potential stock to BUY'),
    #         dict(name='Getting close', description='Stock is approaching your entry point',
    #              is_global=True, sort=2),
    #         dict(name='Ready to BUY', description='Stock is just above your entry point',
    #              is_global=True, sort=3),
    #         dict(name='BUY now', is_global=True, sort=4,
    #              description='Waiting for the right moment to BUY'),
    #     ],
    #     'sell_stage': [
    #         dict(label='Selling', is_global=True, description='The selling process'),
    #
    #         dict(name='Shortlist', is_global=True, sort=1,
    #              description='Potential stock to SELL'),
    #         dict(name='Getting close', description='Stock is approaching your entry point',
    #              is_global=True, sort=2),
    #         dict(name='Ready to SELL', description='Stock is just above your entry point',
    #              is_global=True, sort=3),
    #         dict(name='SELL now', is_global=True, sort=4,
    #              description='Waiting for the right moment to SELL'),
    #     ],
    # },
    
}
options_dict = {
    'site': {
        'sitename': s.SITE_NAME,
        'siteurl': s.SITE_URL,
        'author': 'DropkickDev',
        'last_update': '',
        'max_upload': 3,        # MB
    },
    'admin': {
        'access_token': s.ACCESS_TOKEN_EXPIRE,
        'refresh_token': s.REFRESH_TOKEN_EXPIRE,
        'refresh_token_cutoff': s.REFRESH_TOKEN_CUTOFF,
        'verify_email': s.VERIFY_EMAIL
    },
    # For each user
    'user': {
        'theme': 'light',
        'email_notifications': True,
        'language': 'en',
        'show_currency_symbol': True,
        'date_format': '%Y-%m-%d %H:%M:%S',
        'currency': ''
    },
}