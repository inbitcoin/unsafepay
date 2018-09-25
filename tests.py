#!/usr/bin/env python3
import unittest
import os
import json
import tempfile
from unittest import skipIf, mock
from lnd import Lncli, NodeException
import lncli
import qr

CMDS = lncli.cmds()
PROTOCOL = 'lightning:'
PAY_REQ = json.loads(CMDS['addinvoice'])['pay_req']
LNCLI_MOCK = os.environ['PATH'].startswith('.:')  # launch with: PATH=.:$PATH ./tests.py


class TestLnd(unittest.TestCase):

    def setUp(self):
        self.ln = Lncli()

    def test_aliases(self):
        self.assertTrue(len(self.ln.aliases))

    def test_commands(self):
        self.ln.info()
        self.ln.uri()
        self.ln.add()
        self.ln.add('123')
        self.ln.add('0.001')
        self.ln.balance()
        self.assertIsInstance(self.ln.channels(False), list)
        self.assertIsInstance(self.ln.channels(True), list)
        self.ln.chs()
        self.assertIsInstance(self.ln.pending(), list)
        self.ln.feereport()
        self.ln.is_pay_req(PAY_REQ)

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_mock_commands(self):

        self.ln.pay(PAY_REQ)
        self.ln.pay(PAY_REQ, '0.001')
        self.ln.pay(PROTOCOL + PAY_REQ)
        self.ln.add('1.23')

    @unittest.skipIf(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_lncli_commands(self):

        self.assertTrue(self.ln.is_pay_req(PAY_REQ))
        self.assertTrue(self.ln.is_pay_req(PROTOCOL + PAY_REQ))
        with self.assertRaises(NodeException):
            self.ln.pay(PAY_REQ)
        with self.assertRaises(NodeException):
            self.ln.pay(PAY_REQ, '0.001')
        with self.assertRaises(NodeException):
            self.ln.pay('lightning:' + PAY_REQ)
        with self.assertRaises(NodeException):
            self.ln.add('1.23')
        with self.assertRaises(NodeException):
            self.ln.add(str(int(1e8)))


class TestQr(unittest.TestCase):

    def test_encode(self):
        _, name = tempfile.mkstemp(prefix='unsafepaytests')
        with open(name, 'wb') as fd:
            qr.encode(PAY_REQ, fd)
        os.remove(name)

    @skipIf(isinstance(qr.ZBarSymbol, mock.Mock), 'pyzbar not found')
    def test_decode(self):
        _, name = tempfile.mkstemp(prefix='unsafepaytests')
        with open(name, 'wb') as fd:
            qr.encode(PAY_REQ, fd)
        self.assertEqual(qr.decode(name), PAY_REQ)
        os.remove(name)


if __name__ == '__main__':
    unittest.main()
