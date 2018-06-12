"""
Create a mock of lighter_pb2_grpc.LightningStub(channel)

fixtures.yaml example:

lightning_stub:
- call: channelbalance
  args:
   balance: 2100.22
  return: ChannelBalanceResponse
  tag:
  - ok
"""
from unittest.mock import Mock
from collections import defaultdict
import lighter_pb2 as pb
import yaml_lighter as yaml

FIXTURES_FILE = 'fixtures.yaml'


def load():
    with open(FIXTURES_FILE, 'rt') as fd:
        return yaml.load(fd, Loader=yaml.Loader)


def fixture_init(raw):
    """Init python object from raw data"""

    # FIXME: returntype is a workaround
    if 'returntype' in raw and isinstance(raw['returntype'], str) and \
            hasattr(pb, raw['returntype']):
        kwargs = raw.get('return', {})
        assert isinstance(kwargs, dict)
        return getattr(pb, raw['returntype'])(**kwargs)
    else:
        return raw['return']


def get_lightning_stub(mock, *tags):
    """
    Setup the mock as a LightningStub object with fixtures in FIXTURES_FILE
    """
    if not tags:
        tags = (None, )
    data = load()
    # Check required params
    assert all('call' in x for x in data['lightning_stub'])
    assert all('return' in x for x in data['lightning_stub'])

    dynamic = len(tags) > 1
    return_values = {}
    side_effects = defaultdict(list)

    for tag in tags:
        # For every tag we can have only one answer for each call
        tag_side_effects = {}
        for fix in data['lightning_stub']:
            call = fix['call']
            # Select all fixtures without tags
            # Select tagged fixtures only if caller tag in fixture tags
            if not fix.get('tag') or tag in fix.get('tag', []):
                # 0. construct response
                response = fixture_init(fix)
                # 1. Save responses
                if dynamic:
                    # Keep only the last response for a call for each tag
                    tag_side_effects[call] = response
                else:
                    if isinstance(response, Exception):
                        side_effects[call] = response
                    else:
                        return_values[call] = response
        for call, value in tag_side_effects.items():
            side_effects[call].append(value)
    # 2. Add responses to mock
    for call, value in return_values.items():
        getattr(mock, call).return_value = value
    for call, value in side_effects.items():
        getattr(mock, call).side_effect = value
    return mock


if __name__ == "__main__":
    stub = Mock()
    get_lightning_stub(stub)
    assert stub.walletbalance().balance == 82.8
    assert stub.getinfo().alias == 'mock'
    assert isinstance(stub.listchannels().channels[0], pb.Channel)
    assert len(stub.listinvoices().invoices) > 0
    assert len(stub.listpayments().payments) > 0
    assert len(stub.listpeers().peers) > 0
    assert len(stub.listtransactions().transactions) > 0

    stub = Mock()
    get_lightning_stub(stub, 'nobalance')
    assert stub.walletbalance().balance == 0
    assert stub.channelbalance().balance == 0
    assert stub.getinfo().alias == 'mock'
