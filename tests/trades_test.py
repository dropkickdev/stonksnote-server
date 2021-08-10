import pytest, random, pytz
from limeutils import listify
from collections import Counter
from datetime import datetime
from tortoise import Tortoise
from tortoise.query_utils import Q

from app import ic
from app.auth import UserMod, Option
from trades import Trade, Trader, Broker, UserBrokers, Stash, Mark, Equity
from trades.fixtures.routes import trades_init, trades_data
from tests.app.data import VERIFIED_EMAIL_DEMO



# @pytest.mark.focus
def test_add_broker(loop, tempdb, trades_fx):
    async def ab():
        await tempdb()
        await trades_fx()

        usermod_list = await UserMod.filter(is_verified=True).order_by('created_at')
        for usermod in usermod_list:
            # ic(usermod.display, usermod.id)
            trader = Trader(usermod)
            
            broker_list = await Broker.all()
            random.shuffle(broker_list)
            b1, b2, b3, b4, *_ = broker_list
    
            assert not await trader.has_primary()
            assert not await trader.has_brokers()
            assert await trader.get_primary() is None
            assert await trader.get_userbrokers() == []
            
            param = [
                ([], 0), (b1, 1), (b1, 1), ([b1], 1),
                ([b2], 2), ([b2], 2), (b2, 2),
                ([b1, b2, b3], 3), ([b3, b2, b1], 3), (b4, 4)
            ]
            for broker, count in param:
                broker = listify(broker)
                await trader.add_broker(broker)
            
                all_users_brokers = await trader.get_userbrokers()
                assert len(all_users_brokers) == count
                
                for i in all_users_brokers:
                    # ic(vars(i))
                    assert isinstance(i, UserBrokers)
                    assert i.user_id == usermod.id                                          # noqa
    
            assert not await trader.has_primary()
            assert await trader.has_brokers()
            assert not await trader.get_primary()

    loop.run_until_complete(ab())


# @pytest.mark.focus
def test_remove_broker(loop, tempdb, trades_fx):
    async def ab():
        await tempdb()
        await trades_fx()
        
        usermod_list = await UserMod.filter(is_verified=True).order_by('created_at').limit(2)
        for usermod in usermod_list:
            trader = Trader(usermod)
            broker_list = await Broker.all().limit(9)
            await trader.add_broker(broker_list)
            
            assert not await trader.has_primary()
            assert await trader.has_brokers()
            assert len(broker_list) == 9
            
            param = [
                (broker_list[0], 8), (broker_list[0], 8), ([broker_list[0]], 8), ([], 8),
                (broker_list[1:3], 6), (broker_list[3:5], 4), (broker_list[5], 3), ([], 3),
                (broker_list[6:], 0), ([], 0),
            ]
            for remove, count in param:
                await trader.remove_broker(remove)
                
                brokers = await trader.get_userbrokers(as_dict=True)
                assert len(brokers) == count

                if brokers and remove:
                    remaining_ids = {i.get('broker_id') for i in brokers}
                    removed_ids = {i.id for i in listify(remove)}
                    assert not removed_ids <= remaining_ids
    
            assert not await trader.has_primary()
            assert not await trader.has_brokers()
            assert not await trader.get_primary()
            
    loop.run_until_complete(ab())
    

# @pytest.mark.focus
def test_brokers_and_primary(loop, tempdb, trades_fx):
    async def ab():
        await tempdb()
        await trades_fx()
        
        # Try for no brokers, one broker, alternating broker

        usermod_list = await UserMod.filter(is_verified=True).order_by('created_at').limit(3)
        broker_list = await Broker.all().limit(9)
        b1, b2, b3, *_ = broker_list
        
        param = [
            (b1, None, None, [b1], None, None),
            (b1, None, None, [b1], None, None),
            ([b1], None, None, [b1], None, None),
            (None, b1, None, [], None, None),
            ([b1, b2], [], None, [b1, b2], None, None),
            ([b2, b3], [], None, [b1, b2, b3], None, None),
            ([b1, b2, b3], [], None, [b1, b2, b3], None, None),
            
            (None, None, b1, [b1, b2, b3], b1, None),
            (None, None, b2, [b1, b2, b3], b2, None),
            (None, None, b3, [b1, b2, b3], b3, None),
            (None, b3, None, [b1, b2], None, None),
            
            (None, [b1, b2], None, [], None, None),
            ([b1, b2, b3], None, b1, [b1, b2, b3], b1, None),
            ([], [], None, [b1, b2, b3], b1, None),
            ([], [b2, b3], None, [b1], b1, None),
            (b3, b1, None, [b3], None, None),
            
            (b2, [], b2, [b2, b3], b2, None),
            ([], [], None, [b2, b3], None, b2),
            ([], [], b2, [b2, b3], None, b2),
            ([], [], b3, [b2, b3], b3, None),
            ([], [], None, [b2, b3], None, b3),
            ([], [], b3, [b2, b3], b3, None),
            ([], b3, None, [b2], None, None),
            ([], None, b2, [b2], b2, None),
        ]
        
        for usermod in usermod_list:
            trader = Trader(usermod)
            
            assert not await trader.has_brokers()
            assert not await trader.has_primary()
            assert not await trader.get_primary()
            assert len(await trader.get_userbrokers()) == 0
            
            for addbr, removebr, setpr, all_brokers, primary, unsetpr in param:
                await trader.add_broker(addbr)
                await trader.remove_broker(removebr)
                    
                if setpr:
                    await trader.set_primary(setpr.id)
                    assert (await trader.find_userbroker(setpr.id)).broker_id == setpr.id
                    
                if primary:
                    userbroker = await trader.get_primary()
                    assert isinstance(userbroker, UserBrokers)
                    assert userbroker.is_primary
                    assert userbroker.user_id == usermod.id
                    assert userbroker.broker_id == primary.id
                    
                if unsetpr:
                    await trader.unset_primary()
                    assert await trader.get_primary() == primary
                    
                assert await trader.has_brokers() == bool(all_brokers)
                assert await trader.has_primary() == bool(primary)
                
                if userbroker_list := await trader.get_userbrokers():
                    all_ids = {i.id for i in all_brokers}
                    getbrokers_ids = {i.broker_id for i in await trader.get_userbrokers()}
                    assert Counter(all_ids) == Counter(getbrokers_ids)
                    assert len(userbroker_list) == len(all_brokers)

    loop.run_until_complete(ab())
    
    
# @pytest.mark.focus
def test_marks(loop, tempdb, trades_fx):
    async def ab():
        await tempdb()
        await trades_fx()

        usermod_list = await UserMod.filter(is_verified=True).order_by('created_at').limit(1)
        equity_list = await Equity.all().only('id')
        e1, e2, e3, e4, *_ = equity_list
        
        for usermod in usermod_list:
            trader = Trader(usermod)
            active_equities = []
            
            count = await Mark.filter(author=usermod).count()
            assert count == 0
            
            param = [
                (e1.id, None, 1), (e1.id, None, 1), ([e2.id, e3.id], None, 3),
                ([e1.id, e4.id], None, 4), (None, None, 0),
                ([e1.id], [], 1), ([e1.id, e2.id], e1.id, 1),
                (None, [e2.id], 0), ([e1.id, e2.id, e3.id], [], 3),
                ([], e3.id, 2), (None, [e1.id, e2.id, e3.id, e4.id], 0),
            ]
            for addlist, removelist, count in param:
                
                if not addlist and not removelist and not count:
                    await trader.clear_marks()
                    active_equities = []
                else:
                    await trader.add_mark(addlist)
                    if addlist:
                        active_equities.extend(listify(addlist))
                        
                    await trader.remove_mark(removelist)
                    if removelist:
                        active_equities = list(set(active_equities) - set(listify(removelist)))
                        
                    active_equities = list(set(active_equities))
                    
                assert len(await trader.get_marks()) == count
                
                allmarks = await Mark.filter(author=usermod, is_active=True)\
                                     .values_list('equity_id', flat=True)
                assert Counter(allmarks) == Counter(active_equities)
        
    loop.run_until_complete(ab())


@pytest.mark.focus
def test_trades(loop, tempdb, trades_fx):
    async def ab():
        await tempdb()
        await trades_fx()
        
        usermod_list = await UserMod.filter(is_verified=True).order_by('created_at').limit(2)
        e1, e2, e3, *_ = await Equity.all().only('id')
        broker_list = await Broker.all().only('id').limit(3)
        random.shuffle(broker_list)
        
        for usermod in usermod_list:
            trader = Trader(usermod)
            
            param = [
                (broker_list, [450, 100, 250, 300], [150, 10, 140]),
                (None, [100, 0, 30, 370], [50, 20, 170]),
                (None, [0, 0, 0, 370], [0, 0, 170]),
                (None, [0, 0, 100, 270], [0, 100, 70]),
                (None, [0, 0, 100_000, 0], [0, 999, 0]),
            ]
            for addbrokers, account1, account2 in param:
                dep1, dep2, with1, wallet1 = account1
                dep3, with2, wallet2 = account2
                
                if addbrokers:
                    await trader.add_broker(addbrokers[:2])
                    await trader.add_broker(addbrokers[2])
                    
                ub1, ub2, ub3 = await trader.get_userbrokers()
                await trader.set_primary(ub2.broker_id)
                userbroker = await trader.get_userbroker()
                assert userbroker.broker_id == ub2.broker_id
                
                await trader.deposit(dep1)
                await trader.deposit(dep2)
                total = await trader.withdraw(with1)
                assert total == float(wallet1)
                
                await trader.deposit(dep3, ub3.broker_id)
                total = await trader.withdraw(with2, ub3.broker_id)
                assert total == float(wallet2)
                
                assert await trader.get_wallet(ub1.broker_id) == float(0)
                assert await trader.get_wallet() == float(wallet1)
                assert await trader.get_wallet(ub3.broker_id) == float(wallet2)

            # for equity, ecount, addshares, removeshares, totalshares in param:
            #     pass
        
    loop.run_until_complete(ab())
        

# @pytest.mark.focus
def test_wallet(loop, tempdb, trades_fx):
    pass


# # @pytest.mark.focus
# def test_querynull(loop, db):
#     async def ab():
#         # await Demox.create(deleted_at=None)
#         # await Demox.create(deleted_at=None)
#         # x = await Demox.create(deleted_at=None)
#         # # ic(type(x), x, vars(x))
#         # await x.soft_delete()
#         # await Demox.create(deleted_at=None)
#         # x = await Demox.create(deleted_at=None)
#         # await x.soft_delete()
#
#         # await Demo.bulk_create([
#         #     Demo(deleted_at=None),
#         #     Demo(deleted_at=None),
#         #     Demo(deleted_at=datetime.utcnow()),
#         #     Demo(deleted_at=None),
#         #     Demo(deleted_at=datetime.now(tz=pytz.UTC)),
#         # ])
#
#         # y = await Demo.og.all().values_list('deleted_at', flat=True)
#         # ic(y)
#         # x = Demo.og.filter(deleted_at__isnull=True).count()
#         # ic(x.sql())
#         # ic(await x)
#         # x = Demo.og.filter(deleted_at__not_isnull=True).count()
#         # ic(x.sql())
#         # ic(await x)
#         # x = Demo.og.filter(deleted_at__isnull=False).count()
#         # ic(x.sql())
#         # ic(await x)
#         # x = Demo.og.filter(~Q(deleted_at__isnull=True)).count()
#         # ic(x.sql())
#         # ic(await x)
#         # x = Demo.og.filter(Q(deleted_at__isnull=False)).count()
#         # ic(x.sql())
#         # ic(await x)
#
#         # conn = Tortoise.get_connection('default')
#         # count = await conn.execute_query_dict(
#         #     'SELECT COUNT(*) count FROM demo WHERE deleted_at IS NOT NULL'            # noqa
#         # )
#         # ic(count)
#
#         # x = await Option.all().count()
#         # ic(x)
#         # x = await Option.og.all().count()
#         # ic(x)
#
#         # ic('foo')
#         pass
#
#     loop.run_until_complete(ab())
    