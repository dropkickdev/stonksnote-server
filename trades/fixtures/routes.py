import random, pytz
from datetime import datetime, timedelta
from fastapi import APIRouter
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from pydantic import EmailStr
from fastapi_users.user import get_create_user

from app import ic
from app.settings import settings as s
from tests.app.data import VERIFIED_EMAIL_DEMO
from app.auth import Taxonomy as Taxo
from trades import Trader
from trades.fixtures import fixturedata as fx
from trades.models import Broker, Owner, Equity, Trade, Mark
from app.auth import UserMod, UserCreate, userdb, UserDB, Group, finish_account_setup



tradesdevrouter = APIRouter()


@tradesdevrouter.get('/trades_init', summary='Trades data: Brokers, Owners, and Equity')
async def trades_init():
    try:
        async with in_transaction():
            usermod = await UserMod.get(email=VERIFIED_EMAIL_DEMO).only('id')
            
            # Brokers
            ll = []
            for i in fx.brokers_list:
                ll.append(Broker(**i, author=usermod))
            await Broker.bulk_create(ll)

            # Owners and Equity
            exchange = await Taxo.get(tier='exchange', name='PSE')
            for i in fx.owner_equity_list:
                owner = await Owner.create(**i.get('owner'), author=usermod)
                ll = []
                for j in i.get('equity', []):
                    ll.append(Equity(**j, owner=owner, author=usermod, exchange=exchange))
                await Equity.bulk_create(ll)
            
        return 'SUCCESS: Trades init'
    except OperationalError as e:
        ic(e)
        
@tradesdevrouter.get('/trades_data', summary='Marks and Trades data')
async def trades_data():
    try:
        async with in_transaction():
            usermod_list = await UserMod.filter(is_verified=True).only('id', 'currency')
            equity_list = await Equity.all().only('id')
            
            brokers = [await Broker.get(name='COL FINANCIAL GROUP, INC.').only('id'),
                       await Broker.get(name='UNITED PACIFIC SECURITIES').only('id'),
                       await Broker.get(name='CITICORP SECURITIES (RP)').only('id')]

            # Marks
            expires = datetime.now(tz=pytz.UTC) + timedelta(days=2)
            for usermod in usermod_list:
                ll = []
                for _ in range(random.randint(1, 30)):
                    equity = random.choice(equity_list)
                    # TODO: Duplicate Mark find a way to fix this unless it's really allawed
                    ll.append(Mark(expires=expires, equity=equity, author=usermod))
                await Mark.bulk_create(ll)

            # # Trades
            # for usermod in usermod_list:
            #     trader = Trader(usermod)
            #     await trader.add_broker(brokers)
            #     await trader.set_primary(random.choice(brokers).id)
            #
            #     for _ in range(1, 50):
            #         equity = random.choice(equity_list)
            #         price = random.randint(100, 999) / 100
            #         shares = random.randint(100, 10_000)
            #
            #         if random.choice([0, 1]):
            #             await trader.buy(equity, shares, price)
            #         else:
            #             await trader.sell(equity, shares, price)

        return 'SUCCESS: Trades data'
    except Exception as e:
        ic(e)