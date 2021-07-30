import pytest, random
from limeutils import listify

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
            
                all_users_brokers = await trader.get_brokers(as_instance=True)
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
                
                brokers = await trader.get_brokers()
                assert len(brokers) == count
                
                if brokers and remove:
                    remaining_ids = {i.get('broker_id') for i in brokers}
                    removed_ids = {i.id for i in listify(remove)}
                    assert not removed_ids <= remaining_ids
    
            assert not await trader.has_primary()
            assert not await trader.has_brokers()
            assert not await trader.get_primary()
            
    loop.run_until_complete(ab())
    

@pytest.mark.focus
def test_primary(loop, tempdb, trades_fix):
    async def ab():
        await tempdb()
        await trades_fix()
        
        # Try for no brokers, one broker, alternating broker
        
    loop.run_until_complete(ab())
    
    
# @pytest.mark.focus
def test_stash(loop, tempdb, trades_fix):
    pass


# @pytest.mark.focus
def test_walllet(loop, tempdb, trades_fix):
    pass