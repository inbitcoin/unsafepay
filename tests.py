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
import tempfile
from time import time
from unittest import skipIf, skip
from unittest.mock import patch, Mock
import re
from commands import Commands
from fiat_rate import Fiat, RateError
import qr
from mocker import load, get_lightning_stub


PAY_REQ = load()['pay_req']
PROTOCOL = 'lightning:'
PRIVATE = '\U0001f512'
ACTIVE = '\u26a1\ufe0f'
NACTIVE = '\U0001f64a'

# TODO
# [x] payment <preimage>
# [ ] payment
# [x] node_uri
# [ ] aliases
# [ ] pending
# [ ] channels(pending=True)
# [x] private channels
# [x] n/active channels
# [ ] compile lighter.proto
# [ ] use python-telegram-bot
#     example: gitlab.inbitcoin.it/zoe/bot_template


def build_lighterer_mock(*tags):
    cls = Mock()
    lit = get_lightning_stub(Mock(), *tags)
    cls.return_value = lit
    return cls


class TestLighterer(unittest.TestCase):

    def setUp(self):
        cls = build_lighterer_mock()
        with patch('lighterer.Lighterer', cls):
            self.commands = Commands('fake', 0, None, None)

    def test_aliases(self):
        # null string alias
        pub = ('03aa434d9ff5d5470033aa654f201dbbd'
               'ce79955c61e9e48a6674d203ae3b689f5')
        self.assertEqual(self.commands._alias(pub, pub), pub)
        self.assertNotEqual(self.commands._alias(pub), pub)

        # mani = ('03db61876a9a50e5724048170aeb14f00'
        #         '96e503def38dc149d2a4ca71efd95a059')
        # self.assertEqual(self.commands._alias(mani), 'mani_al_cielo')

        false = ('020000000000000000000000000000000'
                 '000000000000000000000000000000000')
        self.assertEqual(self.commands._alias(false, false), false)

        with open('cities.txt', 'rt') as fd:
            cities = [x.strip() for x in fd.readlines()]
        self.assertIn(self.commands._alias(false).split(maxsplit=1)[1], cities)

        CITYSCAPE = '\U0001f3d9'
        CITY_DUSK = '\U0001f306'
        # TODO: test both conditions
        if self.commands.aliases:
            self.assertEqual(self.commands._alias(false).split()[0], CITY_DUSK)
        else:
            self.assertEqual(self.commands._alias(false).split()[0], CITYSCAPE)

    def test_cities_file(self):
        """cities.txt must be ascii encoded"""
        with open('cities.txt', 'rt') as fd:
            data = fd.readlines()
        for city in data:
            try:
                city.encode('ascii')
            except UnicodeEncodeError:
                self.fail('{} is not ascii encoded'.format(city.strip()))

    def test_private_chs(self):
        self.assertNotIn(PRIVATE, ''.join(
            self.commands.channels()))
        self.assertNotIn(PRIVATE, self.commands.chs())

        cls = build_lighterer_mock('private')
        with patch('lighterer.Lighterer', cls):
            private = Commands('fake', 0, None, None)

        self.assertIn(PRIVATE, ''.join(
            private.channels()))
        self.assertIn(PRIVATE, private.chs())

    def test_active_flag(self):
        """chs and channels commands are involved"""

        # Case 0: all the channels are active

        output = '\n'.join(self.commands.channels())
        occ_channels = output.count(ACTIVE)
        self.assertIn(ACTIVE, output)
        self.assertNotIn(NACTIVE, output)

        output = self.commands.chs()
        occ_chs = output.count(ACTIVE)
        self.assertIn(ACTIVE, output)
        self.assertNotIn(NACTIVE, output)

        self.assertEqual(occ_channels, occ_chs)

        # Case 1: 1 active ch and 1 not active ch
        # channels and chs call get:
        # - all channels
        # - active channels

        cls = build_lighterer_mock(None, 'active')
        with patch('lighterer.Lighterer', cls):
            active = Commands('fake', 0, None, None)

        output = '\n'.join(active.channels())

        self.assertEqual(output.count(ACTIVE), 1)
        self.assertEqual(output.count(NACTIVE), 1)

    @patch('requests.get')
    def test_commands(self, mock_get):
        mock_get.return_value = FakeRequests()

        uri = self.commands._lit.getinfo().node_uri
        self.assertIn(uri, self.commands.info())
        self.assertIn(uri, self.commands.uri())
        self.commands.add()
        self.commands.add('123')
        self.commands.add('0.001')
        self.commands.add('7')
        self.commands.add('6.7€')
        self.commands.add('6.8e')
        self.commands.add('6.9E')
        self.commands.balance()
        self.assertIsInstance(self.commands.channels(pending=False), list)
        # Not implemented
        # self.assertIsInstance(self.commands.channels(pending=True), list)
        self.assertIsInstance(self.commands.pending(), list)
        self.commands.chs()
        self.commands.is_pay_req(PAY_REQ)
        assert re.match('^(bc|tb)1', self.commands.address())

        self.commands.pay(PAY_REQ)
        self.commands.pay(PAY_REQ, '0.001')
        self.commands.pay(PAY_REQ, '7')
        self.commands.pay(PAY_REQ, '6.7€')
        self.commands.pay(PAY_REQ, '6.8e')
        self.commands.pay(PAY_REQ, '6.9E')
        self.commands.pay(PROTOCOL + PAY_REQ)
        self.assertEqual(len(self.commands.add('1.23')), 2)
        self.assertEqual(len(self.commands.channels(pending=False)), 2)
        # self.assertEqual(len(self.commands.channels(pending=True)), 7)
        # self.assertEqual(len(self.commands.pending()), 1)
        self.assertEqual(len(self.commands.channels('no-one', False)), 0)
        self.assertEqual(len(self.commands.channels('03db61876a9a50e5', False)),
                         1)
        self.assertEqual(len(self.commands.channels('03db61876a', False)), 1)

    def test_cmd_payment(self):
        PAID = '\U0001f44d'
        NOT_PAID = '\U0001f44e'
        NOT_FOUND = 'Invoice not found'
        # Random r hash. Mock does not check the hash value
        r_hash = '86' * 32
        no_hash = '67' * 32
        self.assertIn(PAID, self.commands.payment(r_hash))
        self.assertIn(PAID, self.commands.payment())

        cls = build_lighterer_mock('notfound')
        with patch('lighterer.Lighterer', cls):
            notfound = Commands('fake', 0, None, None)

        self.assertIn(NOT_FOUND, notfound.payment(no_hash))

        # Load unpaid mock
        cls = build_lighterer_mock('unpaid')
        with patch('lighterer.Lighterer', cls):
            unpaid = Commands('fake', 0, None, None)

        self.assertIn(NOT_PAID, unpaid.payment(r_hash))
        self.assertIn(NOT_PAID, unpaid.payment())

        # TODO: check the order of invoices
        r_last = cls().listinvoices()[0].payment_hash

        self.assertIn(self.commands.payment().split()[0], (PAID, NOT_PAID))
        self.assertIn(r_last, self.commands.payment())

        # Expiration tests
        # TODO: next version of payment command
        # self.assertIn('Expired on', self.commands.payment())
        # self.assertNotIn('Settled on', self.commands.payment())
        # self.assertNotIn('Expires', self.commands.payment(r_hash))
        # self.assertIn('Settled on', self.commands.payment(r_hash))

    def test_decode(self):

        enc_payreq = self.commands.add('1.23')[0]
        dec_payreq = self.commands.decode(enc_payreq)
        # self.assertIn('To ', dec_payreq) -> Aliases are not supported yet
        self.assertIn('Pubkey ', dec_payreq)
        self.assertIn('Amount ', dec_payreq)
        self.assertIn('Description ', dec_payreq)
        self.assertIn('Created on ', dec_payreq)
        self.assertIn('Expires ', dec_payreq)  # TODO: test expired

        # Optional outputs
        cls = build_lighterer_mock('nodescription')
        with patch('lighterer.Lighterer', cls):
            nodesc = Commands('fake', 0, None, None)

        dec_payreq = nodesc.decode(enc_payreq)
        self.assertNotIn('Description ', dec_payreq)

        # TODO: implement aliases
        # Test: invoice without alias
        # self.assertNotIn('To ', dec_payreq)

    def test_decode_error(self):

        cls = build_lighterer_mock('error')
        with patch('lighterer.Lighterer', cls):
            error = Commands('fake', 0, None, None)
        self.assertIn('This is not a payment request', error.decode('No'))


class TestQr(unittest.TestCase):

    def test_encode(self):
        _, name = tempfile.mkstemp(prefix='unsafepaytests')
        with open(name, 'wb') as fd:
            qr.encode(PAY_REQ, fd)
        os.remove(name)

    @skipIf(isinstance(qr.ZBarSymbol, Mock), 'pyzbar not found')
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


class FakeRateError:
    """Rate is not available"""
    def json(self):
        raise Exception


class TestFiatRate(unittest.TestCase):

    CACHE = {'eur': (3000, time())}

    def setUp(self):
        cls = build_lighterer_mock()
        with patch('lighterer.Lighterer', cls):
            self.commands = Commands('fake', 0, None, None)

    def test_cached(self):

        fiat = Fiat()
        # Import cache
        fiat._cache = self.CACHE

        self.assertEqual(fiat.get_rate(), self.CACHE['eur'][0])
        self.assertEqual(fiat.to_fiat(1), 0)
        self.assertEqual(fiat.to_fiat(0.001 * 1e8),
                         0.001 * self.CACHE['eur'][0])
        self.assertEqual(fiat.to_satoshis(5),
                         int(5 / self.CACHE['eur'][0] * 1e8))
        self.assertRegex(fiat.to_fiat_str(1), '^\d*\.\d{2} €')
        self.assertRegex(fiat.to_fiat_str(7), '^\d*\.\d{2} €')
        self.assertRegex(fiat.to_fiat_str(1000), '^\d*\.\d{2} €')

    @patch('requests.get')
    def test_kraken_mock(self, mock_get):

        mock_get.return_value = FakeRequests()
        expected_price = float(FakeRequests.DATA['result']['XXBTZEUR']['c'][0])

        fiat = Fiat()
        self.assertAlmostEqual(fiat.get_rate(), expected_price)

    @patch('requests.get')
    def test_kraken_mock_error(self, mock_get):
        mock_get.return_value = FakeRateError()

        fiat = Fiat()
        with self.assertRaises(RateError):
            fiat.get_rate()

    @patch('requests.get')
    def test_commands_with_rate(self, mock_get):
        mock_get.return_value = FakeRequests()

        self.assertIn('€', self.commands.info())
        self.commands.uri()
        self.commands.add()
        self.commands.add('123')
        self.commands.add('0.001')
        self.commands.add('7')
        self.assertIsInstance(self.commands.add('6.7€'), tuple)
        self.assertIsInstance(self.commands.add('6.8e'), tuple)
        self.assertIsInstance(self.commands.add('6.9E'), tuple)
        self.assertIn('€', self.commands.balance())
        self.assertIsInstance(self.commands.channels(pending=False), list)
        # self.assertIsInstance(self.commands.channels(pending=True), list)
        # self.assertIsInstance(self.commands.pending(), list)
        self.assertIn('€', self.commands.chs())
        self.assertTrue(self.commands.is_pay_req(PAY_REQ))
        self.assertTrue(re.match('^(bc|tb)1', self.commands.address()))

    @patch('requests.get')
    def test_commands_without_rate(self, mock_get):
        mock_get.return_value = FakeRateError()

        self.assertNotIn('€', self.commands.info())
        self.assertEqual(mock_get.call_count, 1)
        mock_get.reset_mock()
        self.commands.uri()
        self.commands.add()
        self.commands.add('123')
        self.commands.add('0.001')
        self.commands.add('7')
        with self.assertRaises(RateError):
            self.commands.add('6.7€')
        self.assertEqual(mock_get.call_count, 1)
        mock_get.reset_mock()
        with self.assertRaises(RateError):
            self.commands.add('6.8e')
        self.assertEqual(mock_get.call_count, 1)
        mock_get.reset_mock()
        with self.assertRaises(RateError):
            self.commands.add('6.9E')
        self.assertEqual(mock_get.call_count, 1)
        mock_get.reset_mock()
        self.assertNotIn('€', self.commands.balance())
        self.assertIsInstance(self.commands.channels(pending=False), list)
        # self.assertIsInstance(self.commands.channels(pending=True), list)
        # self.assertIsInstance(self.commands.pending(), list)
        self.assertNotIn('€', self.commands.chs())
        self.assertTrue(self.commands.is_pay_req(PAY_REQ))
        self.assertTrue(re.match('^(bc|tb)1', self.commands.address()))


if __name__ == '__main__':
    unittest.main()
