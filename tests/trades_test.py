import pytest, random
from limeutils import listify
from collections import Counter

from app import ic
from app.auth import UserMod
from trades import Trade, Trader, Broker, UserBrokers
from trades.fixtures.routes import trades_init, trades_data
from tests.app.data import VERIFIED_EMAIL_DEMO



# @pytest.mark.focus
def test_add_broker(loop, tempdb, trades_fix):
    async def ab():
        await tempdb()
        await trades_fix()

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
            assert await trader.get_brokers() == []
            
            param = [
                ([], 0), (b1, 1), (b1, 1), ([b1], 1),
                ([b2], 2), ([b2], 2), (b2, 2),
                ([b1, b2, b3], 3), ([b3, b2, b1], 3), (b4, 4)
            ]
            for broker, count in param:
                broker = listify(broker)
                await trader.add_broker(broker)
            
                all_users_brokers = await trader.get_brokers()
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
def test_remove_broker(loop, tempdb, trades_fix):
    async def ab():
        await tempdb()
        await trades_fix()
        
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
                
                brokers = await trader.get_brokers(as_dict=True)
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
def test_brokers_and_primary(loop, tempdb, trades_fix):
    async def ab():
        await tempdb()
        await trades_fix()
        
        # Try for no brokers, one broker, alternating broker

        usermod_list = await UserMod.filter(is_verified=True).order_by('created_at').limit(1)
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
            assert len(await trader.get_brokers()) == 0
            
            for addbr, removebr, setpr, all_brokers, primary, unsetpr in param:
                await trader.add_broker(addbr)
                await trader.remove_broker(removebr)
                    
                if setpr:
                    await trader.set_primary(setpr.id)
                    assert (await trader.get_broker(setpr.id)).broker_id == setpr.id
                    
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
                
                if userbroker_list := await trader.get_brokers():
                    all_ids = {i.id for i in all_brokers}
                    getbrokers_ids = {i.broker_id for i in await trader.get_brokers()}
                    assert Counter(all_ids) == Counter(getbrokers_ids)
                    assert len(userbroker_list) == len(all_brokers)

    loop.run_until_complete(ab())
    
    
@pytest.mark.focus
def test_stash(loop, tempdb, trades_fix):
    async def ab():
        await tempdb()
        await trades_fix()
        
    loop.run_until_complete(ab())


# @pytest.mark.focus
def test_wallet(loop, tempdb, trades_fix):
    pass