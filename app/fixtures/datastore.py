

collection_list = [
    dict(name='Shortlist', tier='equity', is_global=True),
    dict(name='Active', tier='equity', is_global=True),
]

taxonomy_dict = {
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
    'trade_tags': [
        dict(name='recommended', is_global=True),
        dict(name='not-now', is_global=True),
        dict(name='invest-soon', is_global=True),
    ]
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