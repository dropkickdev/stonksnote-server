import pytest, random

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
        
        usermod = await UserMod.get(email=VERIFIED_EMAIL_DEMO)
        trader = Trader(usermod)
        b1, b2, b3, b4, *_ = await Broker.all()

        assert not await trader.has_primary()
        assert not await trader.has_brokers()
        assert await trader.get_primary() is None
        assert await trader.get_brokers() == []
        
        param = [
            ([], 0), (b1, 1), ([b2], 2), (b1, 2), ([b2], 2),
            ([b1, b2, b3], 3), ([b3, b2, b1], 3), (b4, 4)
        ]
        for broker, count in param:
            await trader.add_broker(broker)
        
            dbbrokers = await trader.get_brokers(as_instance=True)
            assert len(dbbrokers) == count
            
            for i in dbbrokers:
                assert isinstance(i, Broker)
                assert i.ubs_record.user_id == usermod.id

        assert not await trader.has_primary()
        assert await trader.has_brokers()
        assert not await trader.get_primary()

    loop.run_until_complete(ab())


# @pytest.mark.focus
def test_remove_broker(loop, tempdb, trades_fix):
    async def ab():
        await tempdb()
        await trades_fix()
        
        usermod = await UserMod.get(email=VERIFIED_EMAIL_DEMO)
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
            assert len(await trader.get_brokers()) == count

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