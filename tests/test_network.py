import asyncio
import tempfile
import unittest

from electrum_grs import constants
from electrum_grs.simple_config import SimpleConfig
from electrum_grs import blockchain
from electrum_grs.interface import Interface, ServerAddr, ChainResolutionMode
from electrum_grs.crypto import sha256
from electrum_grs.util import OldTaskGroup
from electrum_grs import util

from . import ElectrumTestCase


CRM = ChainResolutionMode


class MockNetwork:

    def __init__(self, config: SimpleConfig):
        self.config = config
        self.asyncio_loop = util.get_asyncio_loop()
        self.taskgroup = OldTaskGroup()
        self.proxy = None

class MockInterface(Interface):
    def __init__(self, config: SimpleConfig):
        self.config = config
        network = MockNetwork(config)
        super().__init__(network=network, server=ServerAddr.from_str('mock-server:50000:t'))
        self.q = asyncio.Queue()
        self.blockchain = blockchain.Blockchain(config=self.config, forkpoint=0,
                                                parent=None, forkpoint_hash=constants.net.GENESIS, prev_hash=None)
        self.tip = 12
        self.blockchain._size = self.tip + 1

    async def get_block_header(self, height: int, *, mode: ChainResolutionMode) -> dict:
        assert self.q.qsize() > 0, (height, mode)
        item = await self.q.get()
        print("step with height", height, item)
        assert item['block_height'] == height, (item['block_height'], height)
        assert mode in item['mock'], (mode, item)
        return item

    async def run(self):
        return


class TestNetwork(ElectrumTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        constants.BitcoinRegtest.set_as_network()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        constants.BitcoinMainnet.set_as_network()

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.config = SimpleConfig({'electrum_path': self.electrum_path})
        self.interface = MockInterface(self.config)

    async def test_fork_noconflict(self):
        blockchain.blockchains = {}
        self.interface.q.put_nowait({'block_height': 8, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: False}})
        def mock_connect(height):
            return height == 6
        self.interface.q.put_nowait({'block_height': 7, 'mock': {CRM.BACKWARD:1,'check': lambda x: False, 'connect': mock_connect, 'fork': self.mock_fork}})
        self.interface.q.put_nowait({'block_height': 2, 'mock': {CRM.BACKWARD:1,'check':lambda x: True, 'connect': lambda x: False}})
        self.interface.q.put_nowait({'block_height': 4, 'mock': {CRM.BINARY:1,'check':lambda x: True, 'connect': lambda x: True}})
        self.interface.q.put_nowait({'block_height': 5, 'mock': {CRM.BINARY:1,'check':lambda x: True, 'connect': lambda x: True}})
        self.interface.q.put_nowait({'block_height': 6, 'mock': {CRM.BINARY:1,'check':lambda x: True, 'connect': lambda x: True}})
        ifa = self.interface
        res = await ifa.sync_until(8, next_height=7)
        self.assertEqual((CRM.FORK, 8), res)
        self.assertEqual(self.interface.q.qsize(), 0)

    async def test_fork_conflict(self):
        blockchain.blockchains = {7: {'check': lambda bad_header: False}}
        self.interface.q.put_nowait({'block_height': 8, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: False}})
        def mock_connect(height):
            return height == 6
        self.interface.q.put_nowait({'block_height': 7, 'mock': {CRM.BACKWARD:1,'check': lambda x: False, 'connect': mock_connect, 'fork': self.mock_fork}})
        self.interface.q.put_nowait({'block_height': 2, 'mock': {CRM.BACKWARD:1,'check':lambda x: True, 'connect': lambda x: False}})
        self.interface.q.put_nowait({'block_height': 4, 'mock': {CRM.BINARY:1,'check':lambda x: True, 'connect': lambda x: True}})
        self.interface.q.put_nowait({'block_height': 5, 'mock': {CRM.BINARY:1,'check':lambda x: True, 'connect': lambda x: True}})
        self.interface.q.put_nowait({'block_height': 6, 'mock': {CRM.BINARY:1,'check':lambda x: True, 'connect': lambda x: True}})
        ifa = self.interface
        res = await ifa.sync_until(8, next_height=7)
        self.assertEqual((CRM.FORK, 8), res)
        self.assertEqual(self.interface.q.qsize(), 0)

    async def test_can_connect_during_backward(self):
        blockchain.blockchains = {}
        self.interface.q.put_nowait({'block_height': 8, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: False}})
        def mock_connect(height):
            return height == 2
        self.interface.q.put_nowait({'block_height': 7, 'mock': {CRM.BACKWARD:1, 'check': lambda x: False, 'connect': mock_connect, 'fork': self.mock_fork}})
        self.interface.q.put_nowait({'block_height': 2, 'mock': {CRM.BACKWARD:1, 'check': lambda x: False, 'connect': mock_connect, 'fork': self.mock_fork}})
        self.interface.q.put_nowait({'block_height': 3, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: True}})
        self.interface.q.put_nowait({'block_height': 4, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: True}})
        ifa = self.interface
        res = await ifa.sync_until(8, next_height=4)
        self.assertEqual((CRM.CATCHUP, 5), res)
        self.assertEqual(self.interface.q.qsize(), 0)

    def mock_fork(self, bad_header):
        forkpoint = bad_header['block_height']
        b = blockchain.Blockchain(config=self.config, forkpoint=forkpoint, parent=None,
                                  forkpoint_hash=sha256(str(forkpoint)).hex(), prev_hash=sha256(str(forkpoint-1)).hex())
        return b

    async def test_chain_false_during_binary(self):
        blockchain.blockchains = {}
        self.interface.q.put_nowait({'block_height': 8, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: False}})
        mock_connect = lambda height: height == 3
        self.interface.q.put_nowait({'block_height': 7, 'mock': {CRM.BACKWARD:1, 'check': lambda x: False, 'connect': mock_connect}})
        self.interface.q.put_nowait({'block_height': 2, 'mock': {CRM.BACKWARD:1, 'check': lambda x: True,  'connect': mock_connect}})
        self.interface.q.put_nowait({'block_height': 4, 'mock': {CRM.BINARY:1, 'check': lambda x: False, 'fork': self.mock_fork, 'connect': mock_connect}})
        self.interface.q.put_nowait({'block_height': 3, 'mock': {CRM.BINARY:1, 'check': lambda x: True, 'connect': lambda x: True}})
        self.interface.q.put_nowait({'block_height': 5, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: True}})
        self.interface.q.put_nowait({'block_height': 6, 'mock': {CRM.CATCHUP:1, 'check': lambda x: False, 'connect': lambda x: True}})
        ifa = self.interface
        res = await ifa.sync_until(8, next_height=6)
        self.assertEqual((CRM.CATCHUP, 7), res)
        self.assertEqual(self.interface.q.qsize(), 0)


if __name__ == "__main__":
    constants.BitcoinRegtest.set_as_network()
    unittest.main()
