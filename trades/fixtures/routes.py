from fastapi import APIRouter
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction

from app import ic
from app.tests.data import VERIFIED_EMAIL_DEMO
from trades.fixtures import fixturedata as fx
from trades.models import Broker, Owner, Equity
from app.auth import UserMod



tradesdevrouter = APIRouter()


@tradesdevrouter.get('/basics')
async def basics():
    try:
        async with in_transaction():
            usermod = await UserMod.get(email=VERIFIED_EMAIL_DEMO).only('id')
            
            # Brokers
            ll = []
            for i in fx.brokers_list:
                ll.append(Broker(**i, author=usermod))
            await Broker.bulk_create(ll)

            # Owners and Equity
            ll = []
            for i in fx.owner_equity_list:
                owner = await Owner.create(**i.get('owner', author=usermod))
                for j in i.get('equity'):
                    eq = await Equity.create(**j, owner=owner, author=usermod)
            
        return 'SUCCESS'
    except OperationalError as e:
        ic(e)
