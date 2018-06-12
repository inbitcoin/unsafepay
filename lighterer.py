import codecs
import os
import re
import grpc
from grpc import RpcError
# TODO: write a Makefile to compile lighter_pb2.*.py files
import lighter_pb2 as pb
import lighter_pb2_grpc as pb_grpc

os.environ['GRPC_SSL_CIPHER_SUITES'] = (
    'HIGH+ECDSA:'
    'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384')


class LightererGrpc:
    def __init__(self, host, port, cert=None, macaroon=None):
        assert isinstance(host, str)
        assert isinstance(port, int) or re.match(r'^\d+$', port)
        if cert and macaroon:
            self._channel = grpc.secure_channel(
                '{}:{}'.format(host, port),
                self.credentials_init(cert, macaroon))
        else:
            self._channel = grpc.insecure_channel(
                '{}:{}'.format(host, port))
        self.stub = pb_grpc.LightningStub(self._channel)

    @staticmethod
    def credentials_init(cert, macaroon):
        """Init credentials object"""
        assert isinstance(cert, bytes)
        assert re.match(br'^[\da-f]+$', macaroon)

        def metadata_callback(_context, callback):
            callback([('macaroon', macaroon)], None)

        credentials = grpc.ssl_channel_credentials(root_certificates=cert)
        if macaroon:
            auth_creds = grpc.metadata_call_credentials(metadata_callback)
            credentials = grpc.composite_channel_credentials(
                credentials, auth_creds)
        return credentials

    @staticmethod
    def read_cert(path):
        if isinstance(path, str):
            with open(path, 'rb') as file:
                return file.read()
        return b''

    @staticmethod
    def read_macaroon(path):
        if isinstance(path, str):
            with open(path, 'rb') as fd:
                macaroon_bytes = fd.read()
            return codecs.encode(macaroon_bytes, 'hex')
        return b''

    def close_connection(self):
        self._channel.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()
        return False


class Lighterer(LightererGrpc):
    """Interface to lighter"""

    def channelbalance(self):
        request = pb.ChannelBalanceRequest()
        return self.stub.ChannelBalance(request).balance

    def checkinvoice(self, payment_hash):
        request = pb.CheckInvoiceRequest()
        request.payment_hash = payment_hash
        return self.stub.CheckInvoice(request).settled

    def createinvoice(
            self, amount_bits=None, description=None, expiry_time=None,
            min_final_cltv_expiry=None, fallback_addr=None):
        request = pb.CreateInvoiceRequest(
            amount_bits=amount_bits,
            description=description,
            expiry_time=expiry_time,
            min_final_cltv_expiry=min_final_cltv_expiry,
            fallback_addr=fallback_addr)
        return self.stub.CreateInvoice(request)

    def decodeinvoice(self, payment_request):
        assert isinstance(payment_request, str)
        request = pb.DecodeInvoiceRequest(payment_request=payment_request)
        return self.stub.DecodeInvoice(request)

    def getinfo(self):
        request = pb.GetInfoRequest()
        return self.stub.GetInfo(request)
        # try:
        #     response = stub.GetInfo(request)
        #     return response
        # except grpc.RpcError as err:
        #     print('Error raised: {}'.format(err))

    def listchannels(self, active_only=False):
        assert isinstance(active_only, bool)
        request = pb.ListChannelsRequest(active_only=active_only)
        return self.stub.ListChannels(request).channels

    def listinvoices(
            self, max_items=200, search_timestamp=None,
            search_order='ASCENDING', list_order='ASCENDING', paid=False,
            pending=False, expired=False):
        assert search_order in ('ASCENDING', 'DESCENDING')
        assert list_order in ('ASCENDING', 'DESCENDING')
        request = pb.ListInvoicesRequest(
            max_items=max_items,
            search_timestamp=search_timestamp,
            search_order=search_order,
            list_order=list_order,
            paid=paid,
            pending=pending,
            expired=expired)
        return self.stub.ListInvoices(request).invoices

    def listpayments(self):
        request = pb.ListPaymentsRequest()
        return self.stub.ListPayments(request)

    def listpeers(self):
        request = pb.ListChannelsRequest()
        return self.stub.ListPeers(request).peers

    def listtransactions(self):
        request = pb.ListTransactionsRequest()
        return self.stub.ListTransactions(request).transactions

    def newaddress(self, address_type='P2WKH'):
        assert address_type in ('P2WKH', 'NP2WKH')
        request = pb.NewAddressRequest(type=address_type)
        return self.stub.NewAddress(request).address

    def openchannel(self, node_uri, funding_bits, push_bits=0, private=False):
        assert re.match(r'[a-fA-F\d]{66}@[\da-zA-Z.-]+:\d+', node_uri)
        request = pb.OpenChannelRequest(
            node_uri=node_uri,
            funding_bits=funding_bits,
            push_bits=push_bits,
            private=private)
        return self.stub.OpenChannel(request)

    def payinvoice(
            self, payment_request, amount_bits=None, description=None,
            cltv_expiry_delta=None):
        request = pb.PayInvoiceRequest(
            payment_request=payment_request,
            amount_bits=amount_bits,
            description=description,
            cltv_expiry_delta=cltv_expiry_delta)
        return self.stub.PayInvoice(request).payment_preimage

    def payonchain(self, address, amount_bits, fee_sat_byte=None):
        request = pb.OpenChannelRequest(
            address=address,
            amount_bits=amount_bits,
            fee_sat_byte=fee_sat_byte)
        return self.stub.PayOnChain(request)

    def unlocklighter(self, password):
        # request = pb.UnlockLighterRequest(
        #     password=password)
        # return self.stub.
        raise NotImplementedError

    def walletbalance(self):
        request = pb.WalletBalanceRequest()
        return self.stub.WalletBalance(request).balance


if __name__ == "__main__":

    HOST = '127.0.0.1'
    PORT = 1708
    CERT = './certs/server.crt'
    MACAROONS = True
    MAC = './macaroons/admin.macaroon'

    cert = Lighterer.read_cert(CERT)
    macaroon = Lighterer.read_macaroon(MAC)
    with Lighterer(HOST, PORT, cert, macaroon) as lit:
        # if input('...').strip() == 'q':
        #     break
        print(lit.getinfo())
        # res = lit.checkinvoice('ab84820b5cf700bb2b11e5d9cb8a56031dd399f901ca1938354a9a8538252ced')
        # res = lit.createinvoice(100.1, "Gne", 100, 100)
        # print(res)
        # res = lit.decodeinvoice('lnbc100100n1pwwgeafpp5umpsh2drty45vq532vcda5drxrndzh36gzqpkqgtduyx5ns75n4qdq9gahx2cqzryxqzry3zdhz9j59n3myche9qjca0u9kpg85nflmqy6d7jslcu08xsl0drqq0etakq8gm93593g49smkvsxcpw66r4mhgj2w4ksygrqr2j764spfuf3uj')
        # print(res)
        # res = lit.listinvoices()
        # print(res.invoices)
        # res = lit.listtransactions()
        # for tx in res:
        #     print('TX', tx)
        # res = lit.newaddress()
        # print('a', res)
        # res = lit.newaddress('NP2WKH')
        # print('a', res)
        # res = lit.walletbalance()
        # print('bal', res)

        # import time
        # while True:
        #     chb = lit.channelbalance()
        #     wab = lit.walletbalance()
        #     print('ch', chb, wab, time.ctime())
        #     time.sleep(60*20)

    # lit.close_connection()

__all__ = [
    'Lighterer',
    'RpcError',
]
