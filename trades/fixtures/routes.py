import pytz, random
from datetime import datetime, timedelta
from fastapi import APIRouter
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction

from app import ic
from app.tests.data import VERIFIED_EMAIL_DEMO
from app.auth import Taxonomy as Taxo
from trades.fixtures import fixturedata as fx
from trades.models import Broker, Owner, Equity, Mark
from app.auth import UserMod



tradesdevrouter = APIRouter()


@tradesdevrouter.get('/trades', summary='Init for Trades')
async def init():
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
                
            # Marks
            tickers = await Equity.all().only('id')
            expires = datetime.now(tz=pytz.UTC) + timedelta(days=2)
            ll = []
            for _ in range(9):
                idx = random.randint(0, len(tickers) - 1)
                ll.append(Mark(expires=expires, equity=tickers[idx], author=usermod))
            await Mark.bulk_create(ll)
            
        return 'SUCCESS: Trades'
    except OperationalError as e:
        ic(e)
