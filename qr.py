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
