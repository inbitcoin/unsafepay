#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# unsafepay - because Telegram could empty your channels
# Copyright (C) 2018-2019  Martino Salvetti
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import unittest
import os
import json
import tempfile
from time import time
from os import environ
from unittest import skipIf, mock
from unittest.mock import patch
from lnd import Lncli, NodeException
from fiat_rate import Fiat
import lncli
import qr

CMDS = lncli.cmds()
PROTOCOL = 'lightning:'
PAY_REQ = json.loads(CMDS['addinvoice'][0])['pay_req']
LNCLI_MOCK = os.environ['PATH'].startswith('.:')  # launch with: PATH=.:$PATH ./tests.py


class MockIndex:
    PRE = 'LNCLI_MOCK_INDEX__'

    @classmethod
    def set(cls, cmd, index):
        environ[cls.PRE + cmd] = str(index)

    @classmethod
    def clean(cls):
        for var in environ:
            if var.startswith(cls.PRE):
                del environ[var]

    @classmethod
    def get(cls, cmd):
        if cls.PRE + cmd in environ:
            return int(environ[cls.PRE + cmd])
        return 0


class TestLnd(unittest.TestCase):

    def setUp(self):
        self.ln = Lncli()

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_aliases(self):
        self.assertTrue(len(self.ln.aliases))
        # null string alias
        pub = '03aa434d9ff5d5470033aa654f201dbbdce79955c61e9e48a6674d203ae3b689f5'
        self.assertEqual(self.ln._alias(pub, pub), pub)
        self.assertNotEqual(self.ln._alias(pub), pub)

        mani = '03db61876a9a50e5724048170aeb14f0096e503def38dc149d2a4ca71efd95a059'
        self.assertEqual(self.ln._alias(mani), 'mani_al_cielo')

        false = '020000000000000000000000000000000000000000000000000000000000000000'
        self.assertEqual(self.ln._alias(false, false), false)

        with open('cities.txt', 'rt') as fd:
            cities = [x.strip() for x in fd.readlines()]
        self.assertIn(self.ln._alias(false).split(maxsplit=1)[1], cities)

        CITYSCAPE = '\U0001f3d9'
        CITY_DUSK = '\U0001f306'
        if self.ln.aliases:
            self.assertEqual(self.ln._alias(false).split()[0], CITY_DUSK)
        else:
            self.assertEqual(self.ln._alias(false).split()[0], CITYSCAPE)

    def test_cities_file(self):
        """cities.txt must be ascii encoded"""
        with open('cities.txt', 'rt') as fd:
            data = fd.readlines()
        for city in data:
            try:
                city.encode('ascii')
            except UnicodeEncodeError:
                self.fail('{} is not ascii encoded'.format(city.strip()))

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_private_chs(self):
        self.assertIn('\U0001f512', ''.join(self.ln.channels('037163149da6fbddd6e8')))
        self.assertNotIn('\U0001f512', ''.join(self.ln.channels('mani_al_cielo')))
        self.assertIn('\U0001f512', self.ln.chs())

        # Private channels do not have links to the explorer
        self.assertNotIn('1ml.com', ''.join(self.ln.channels('037163149da6fbddd6e8')))

    @patch('requests.get')
    def test_commands(self, mock_get):
        mock_get.return_value = FakeRequests()

        self.ln.info()
        self.ln.uri()
        self.ln.add()
        self.ln.add('123')
        self.ln.add('0.001')
        self.ln.add('7')
        self.ln.add('6.7€')
        self.ln.add('6.8e')
        self.ln.add('6.9E')
        self.ln.balance()
        self.assertIsInstance(self.ln.channels(pending=False), list)
        self.assertIsInstance(self.ln.channels(pending=True), list)
        self.assertIsInstance(self.ln.pending(), list)
        self.ln.chs()
        self.ln.feereport()
        self.ln.is_pay_req(PAY_REQ)
        self.ln.address().startswith('bc1')

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_getinfo_missed_uris(self):
        self.ln.info()
        MockIndex.set('getinfo', 1)
        self.ln.info()

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    @patch('requests.get')
    def test_mock_commands(self, mock_get):
        mock_get.return_value = FakeRequests()

        self.ln.pay(PAY_REQ)
        self.ln.pay(PAY_REQ, '0.001')
        self.ln.pay(PAY_REQ, '7')
        self.ln.pay(PAY_REQ, '6.7€')
        self.ln.pay(PAY_REQ, '6.8e')
        self.ln.pay(PAY_REQ, '6.9E')
        self.ln.pay(PROTOCOL + PAY_REQ)
        self.assertEqual(len(self.ln.add('1.23')), 2)
        r_hash = '8692a0415ec87a56b6d79a485cf0aad99e118974e23bc4c627e038c91cf46668'
        self.assertTrue(self.ln.payment(r_hash))
        self.assertTrue(self.ln.payment())
        r_last = 'db1e21e569986d9f498d0667e97b743b114b4e1161d36f8260ecf7551ce6f1b1'
        self.assertIn(r_last, self.ln.payment())
        self.assertNotIn(r_hash, self.ln.payment(r_hash))
        # Expiration tests
        self.assertIn('Expired on', self.ln.payment())
        self.assertNotIn('Settled on', self.ln.payment())
        self.assertNotIn('Expires', self.ln.payment(r_hash))
        self.assertIn('Settled on', self.ln.payment(r_hash))
        self.assertEqual(len(self.ln.channels(pending=False)), 6)
        self.assertEqual(len(self.ln.channels(pending=True)), 7)
        self.assertEqual(len(self.ln.pending()), 1)
        self.assertEqual(len(self.ln.channels('no-one', False)), 0)
        self.assertEqual(len(self.ln.channels('al_cielo', False)), 1)
        self.assertEqual(len(self.ln.channels('03db61876a', False)), 1)
        self.assertEqual(len(self.ln.channels('02cdf83ef8', True)), 1)

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_mock_decode(self):

        enc_payreq = self.ln.add('1.23')[0]
        dec_payreq = self.ln.decode(enc_payreq)
        self.assertIn('To ', dec_payreq)
        self.assertIn('Pubkey ', dec_payreq)
        self.assertIn('Amount ', dec_payreq)
        self.assertIn('Description ', dec_payreq)
        self.assertIn('Created on ', dec_payreq)
        self.assertIn('Expired on ', dec_payreq)

        # Optional outputs
        MockIndex.set('decodepayreq', 1)
        dec_payreq = self.ln.decode(enc_payreq)
        self.assertNotIn('To ', dec_payreq)
        self.assertNotIn('Description ', dec_payreq)

    @unittest.skipIf(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_decode(self):
        error = self.ln.decode('No')
        self.assertIn('This is not a payment request', error)

    @unittest.skipIf(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_lncli_commands(self):

        self.assertTrue(self.ln.is_pay_req(PAY_REQ))
        self.assertTrue(self.ln.is_pay_req(PROTOCOL + PAY_REQ))
        self.assertIn('invoice expired', self.ln.pay(PAY_REQ))
        self.assertIn('invoice expired', self.ln.pay(PAY_REQ, '0.001'))
        self.assertIn('invoice expired', self.ln.pay('lightning:' + PAY_REQ))
        with self.assertRaises(NodeException):
            self.ln.add('1.23')
        with self.assertRaises(NodeException):
            self.ln.add(str(int(1e8)))

    @unittest.skipUnless(LNCLI_MOCK, "Differences between ./lncli and lncli")
    def test_payment_path(self):

        def count_lines(string):
            return len(string.split('\n'))

        MockIndex.set('payinvoice', 0)
        self.assertEqual(count_lines(self.ln.pay(PAY_REQ)), 3)
        # Amount: 0.0xxxxxxx btc
        # Fee: x.xxx sat
        # # hops: x

        MockIndex.set('payinvoice', 1)
        self.assertEqual(count_lines(self.ln.pay(PAY_REQ)), 3 + 1 + 2)
        # Amount: 0.0xxxxxxx btc
        # Fee: x.xxx sat
        # # hops: x
        # Path:
        # Alias0
        # Alias1


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


class FakeRequests:
    """We should use mock here"""
    DATA = {
        'error': [],
        'result': {'XXBTZEUR': {
            'a': ['3184.60000', '14', '14.000'],
            'b': ['3184.50000', '3', '3.000'],
            'c': ['3184.50000', '0.22166006'],
            'h': ['3198.70000', '3198.70000'],
            'l': ['3145.70000', '3145.70000'],
            'o': '3186.90000',
            'p': ['3174.51858', '3174.90884'],
            't': [12463, 13595],
            'v': ['3591.35599872', '3810.41919298']}
        }
    }

    def json(self):
        return self.DATA


class FiatRate(unittest.TestCase):

    CACHE = {'eur': (3000, time())}

    def test_cached(self):

        fiat = Fiat()
        # Import cache
        fiat._cache = self.CACHE

        self.assertEqual(fiat.get_rate(), self.CACHE['eur'][0])
        self.assertEqual(fiat.to_fiat(1), 0)
        self.assertEqual(fiat.to_fiat(0.001 * 1e8), 0.001 * self.CACHE['eur'][0])
        self.assertEqual(fiat.to_satoshis(5), int(5 / self.CACHE['eur'][0] * 1e8))
        self.assertRegex(fiat.to_fiat_str(1), '^\d*\.\d{2} €')
        self.assertRegex(fiat.to_fiat_str(7), '^\d*\.\d{2} €')
        self.assertRegex(fiat.to_fiat_str(1000), '^\d*\.\d{2} €')

    @patch('requests.get')
    def test_kraken_mock(self, mock_get):

        mock_get.return_value = FakeRequests()
        expected_price = float(FakeRequests.DATA['result']['XXBTZEUR']['c'][0])

        fiat = Fiat()
        self.assertAlmostEqual(fiat.get_rate(), expected_price)


if __name__ == '__main__':
    unittest.main()
