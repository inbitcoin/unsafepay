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
import sys
from unittest import mock
from PIL import Image
try:
    from pyzbar.pyzbar import decode as zdecode, ZBarSymbol
except ImportError:
    zdecode = lambda *args, **kwargs: []
    ZBarSymbol = mock.Mock()
    print('pyzbar not found', file=sys.stderr)
import qrcode


def decode(file_name):
    data = zdecode(Image.open(file_name), symbols=[ZBarSymbol.QRCODE])
    if not len(data):
        return

    return str(data[0].data, 'ascii')


def encode(text, stream):
    img = qrcode.make(text)
    img.save(stream)
