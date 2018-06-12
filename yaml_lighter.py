"""
Teach to yaml how to create lighter objects.
How: copy an object and change:
 - name
 - yaml tag
 - return type
"""

from yaml import *
import lighter_pb2 as pb
from commands import RpcError


class RpcErrorException(YAMLObject):
    yaml_tag = '!RpcError'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return RpcError(data['message'])


class Channel(YAMLObject):
    yaml_tag = '!Channel'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.Channel(**data)


class ChannelBalanceResponse(YAMLObject):
    yaml_tag = '!ChannelBalanceResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.ChannelBalanceResponse(**data)


class CheckInvoiceResponse(YAMLObject):
    yaml_tag = '!CheckInvoiceResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.CheckInvoiceResponse(**data)


class CreateInvoiceResponse(YAMLObject):
    yaml_tag = '!CreateInvoiceResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.CreateInvoiceResponse(**data)


class DecodeInvoiceResponse(YAMLObject):
    yaml_tag = '!DecodeInvoiceResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.DecodeInvoiceResponse(**data)


class GetInfoResponse(YAMLObject):
    yaml_tag = '!GetInfoResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.GetInfoResponse(**data)


class ListChannelsResponse(YAMLObject):
    yaml_tag = '!ListChannelsResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.ListChannelsResponse(**data)


class ListInvoicesResponse(YAMLObject):
    yaml_tag = '!ListInvoicesResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.ListInvoicesResponse(**data)


class ListPaymentsResponse(YAMLObject):
    yaml_tag = '!ListPaymentsResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.ListPaymentsResponse(**data)


class ListPeersResponse(YAMLObject):
    yaml_tag = '!ListPeersResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.ListPeersResponse(**data)


class ListTransactionsResponse(YAMLObject):
    yaml_tag = '!ListTransactionsResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.ListTransactionsResponse(**data)


class Transaction(YAMLObject):
    yaml_tag = '!Transaction'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.Transaction(**data)


class NewAddressResponse(YAMLObject):
    yaml_tag = '!NewAddressResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.NewAddressResponse(**data)


class OpenChannelResponse(YAMLObject):
    yaml_tag = '!OpenChannelResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.OpenChannelResponse(**data)


class PayInvoiceResponse(YAMLObject):
    yaml_tag = '!PayInvoiceResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.PayInvoiceResponse(**data)


class PayOnChainResponse(YAMLObject):
    yaml_tag = '!PayOnChainResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.PayOnChainResponse(**data)


class WalletBalanceResponse(YAMLObject):
    yaml_tag = '!WalletBalanceResponse'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.WalletBalanceResponse(**data)


class Invoice(YAMLObject):
    yaml_tag = '!Invoice'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.Invoice(**data)


class Payment(YAMLObject):
    yaml_tag = '!Payment'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.Payment(**data)


class Peer(YAMLObject):
    yaml_tag = '!Peer'

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_mapping(node)
        return pb.Peer(**data)
