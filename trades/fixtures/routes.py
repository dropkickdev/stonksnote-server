import pytz, random
from datetime import datetime, timedelta
from fastapi import APIRouter
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from pydantic import EmailStr
from fastapi_users.user import get_create_user

from app import ic
from app.settings import settings as s
from app.tests.data import VERIFIED_EMAIL_DEMO
from app.auth import Taxonomy as Taxo
from trades.fixtures import fixturedata as fx
from trades.models import Broker, Owner, Equity, Mark, Trade
from app.auth import UserMod, UserCreate, userdb, UserDB, Group, finish_account_setup



tradesdevrouter = APIRouter()


@tradesdevrouter.get('/users', summary='Add more users for dev use only')
async def addusers():
    try:
        async with in_transaction():
            groups = await Group.filter(name__in=s.USER_GROUPS)
            
            # User n
            for num in range(1, random.randint(1, 15)):
                userdata = UserCreate(email=EmailStr(f'devuser-{num}@gmail.com'),
                                      password='pass123')
                create_user = get_create_user(userdb, UserDB)
                created_user = await create_user(userdata, safe=True)
                user = await UserMod.get(pk=created_user.id)
                user.is_verified = True
                await user.save()
                await user.groups.add(*groups)
                await finish_account_setup(user)
                
        return 'SUCCESS: Dev users'
    except Exception as e:
        ic(e)



@tradesdevrouter.get('/trades', summary='Trades data: Brokers, Owners, Equity, Marks, and Trades')
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

            usermod_list = await UserMod.filter(is_verified=True).only('id')
            tickers = await Equity.all().only('id')
            broker = await Broker.get(name='COL FINANCIAL GROUP, INC.').only('id')

            # Marks
            expires = datetime.now(tz=pytz.UTC) + timedelta(days=2)
            for usermod in usermod_list:
                ll = []
                for _ in range(random.randint(1, 10)):
                    idx = random.randint(0, len(tickers) - 1)
                    ll.append(Mark(expires=expires, equity=tickers[idx], author=usermod))
                await Mark.bulk_create(ll)

            # Trades
            for usermod in usermod_list:
                ll = []
                for _ in range(random.randint(1, 15)):
                    equity = tickers[random.randint(0, len(tickers) - 1)]
                    marketprice = random.randint(100, 999) / 100
                    shares = random.randint(100, 10_000)
                    gross = marketprice * shares
                    fees = gross * 0.00295
                    total = gross + fees
        
                    ll.append(Trade(user=usermod, equity=equity, broker=broker, action='buy',
                                    author=usermod, marketprice=marketprice, shares=shares,
                                    gross=gross, fees=fees, total=total))
                await Trade.bulk_create(ll)
                
        return 'SUCCESS: Trades init'
    except OperationalError as e:
        ic(e)