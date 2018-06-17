#!/usr/bin/env python3
import unittest
import os
import json
import tempfile
from lnd import Lncli
import lncli
import qr

CMDS = lncli.cmds()
PAY_REQ = json.loads(CMDS['addinvoice'])['pay_req']


class TestLnd(unittest.TestCase):

    def setUp(self):
        self.ln = Lncli()

    def test_aliases(self):
        self.assertTrue(len(self.ln.aliases))

    def test_commands(self):
        self.ln.info()
        self.ln.pay(PAY_REQ)
        self.ln.pay(PAY_REQ, '0.001')
        self.ln.pay('lightning:' + PAY_REQ)
        self.ln.add()
        self.ln.add('123')
        self.ln.add('0.001')
        self.ln.add('1.23')  # Should raise an error but ./lncli does not support it
        self.ln.balance()
        self.ln.channels()
        self.ln.feereport()
        self.ln.is_pay_req(PAY_REQ)


class TestQr(unittest.TestCase):

    def test_encode(self):
        _, name = tempfile.mkstemp(prefix='unsafepaytests')
        with open(name, 'wb') as fd:
            qr.encode(PAY_REQ, fd)
        os.remove(name)

    def test_decode(self):
        _, name = tempfile.mkstemp(prefix='unsafepaytests')
        with open(name, 'wb') as fd:
            qr.encode(PAY_REQ, fd)
        self.assertEqual(qr.decode(name), PAY_REQ)
        os.remove(name)


if __name__ == '__main__':
    unittest.main()
