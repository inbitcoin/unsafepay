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

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_aliases(self):
        self.assertTrue(len(self.ln.aliases))
        # null string alias
        pub = '03aa434d9ff5d5470033aa654f201dbbdce79955c61e9e48a6674d203ae3b689f5'
        self.assertEqual(self.ln._alias(pub), pub)

        mani = '03db61876a9a50e5724048170aeb14f0096e503def38dc149d2a4ca71efd95a059'
        self.assertEqual(self.ln._alias(mani), 'mani_al_cielo')

        false = '020000000000000000000000000000000000000000000000000000000000000000'
        self.assertEqual(self.ln._alias(false), false)

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_private_chs(self):
        self.assertIn('\U0001f512', ''.join(self.ln.channels('037163149da6fbddd6e8')))
        self.assertNotIn('\U0001f512', ''.join(self.ln.channels('mani_al_cielo')))
        self.assertIn('\U0001f512', self.ln.chs())

        # Private channels do not have links to the explorer
        self.assertNotIn('1ml.com', ''.join(self.ln.channels('037163149da6fbddd6e8')))

    def test_commands(self):
        self.ln.info()
        self.ln.uri()
        self.ln.add()
        self.ln.add('123')
        self.ln.add('0.001')
        self.ln.balance()
        self.assertIsInstance(self.ln.channels(pending=False), list)
        self.assertIsInstance(self.ln.channels(pending=True), list)
        self.assertIsInstance(self.ln.pending(), list)
        self.ln.chs()
        self.ln.feereport()
        self.ln.is_pay_req(PAY_REQ)

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_mock_commands(self):

        self.ln.pay(PAY_REQ)
        self.ln.pay(PAY_REQ, '0.001')
        self.ln.pay(PROTOCOL + PAY_REQ)
        self.assertEqual(len(self.ln.add('1.23')), 2)
        r_hash = '8692a0415ec87a56b6d79a485cf0aad99e118974e23bc4c627e038c91cf46668'
        self.assertTrue(self.ln.payment(r_hash))
        self.assertTrue(self.ln.payment())
        self.assertEqual(len(self.ln.channels(pending=False)), 6)
        self.assertEqual(len(self.ln.channels(pending=True)), 7)
        self.assertEqual(len(self.ln.pending()), 1)
        self.assertEqual(len(self.ln.channels('no-one', False)), 0)
        self.assertEqual(len(self.ln.channels('al_cielo', False)), 1)
        self.assertEqual(len(self.ln.channels('03db61876a', False)), 1)
        self.assertEqual(len(self.ln.channels('02cdf83ef8', True)), 1)

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
