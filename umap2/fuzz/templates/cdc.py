'''
CDC Device tempaltes
'''
from kitty.model import UInt8, LE16, BitField
from kitty.model import Repeat
from generic import Descriptor
from enum import _DescriptorTypes


class _CDC_DescriptorSubTypes:  # CDC Functional Descriptors

    '''Descriptor sub types [usbcdc11.pdf table 25]'''

    HEADER_FUNCTIONAL = 0
    CALL_MANAGMENT = 1
    ABSTRACT_CONTROL_MANAGEMENT = 2
    DIRECT_LINE_MANAGEMENT = 3
    TELEPHONE_RINGER = 4
    TELEPHONE_CALL = 5
    UNION_FUNCTIONAL = 6
    COUNTRY_SELECTION = 7
    TELEPHONE_OPERATIONAL_MODES = 8
    USB_TERMINAL = 9
    NETWORK_CHANNEL_TERMINAL = 0xa
    PROTOCOL_UNIT = 0xb
    EXTENSION_UNIT = 0xc
    MULTI_CHANNEL_MANAGEMENT = 0xd
    CAPI_CONTROL_MANAGEMENT = 0xe
    ETHERNET_NETWORKING = 0xf
    ATM_NETWORKING = 0x10
    # 0x11-0xff reserved


cdc_header_functional_descriptor = Descriptor(
    name='cdc_header_functional_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_CDC_DescriptorSubTypes.HEADER_FUNCTIONAL),
        LE16(name='bcdCDC', value=0xffff)
    ])


cdc_call_management_functional_descriptor = Descriptor(
    name='cdc_call_management_functional_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_CDC_DescriptorSubTypes.CALL_MANAGMENT),
        BitField(name='bmCapabilities', value=0, length=8),
        UInt8(name='bDataInterface', value=0)
    ])


# TODO: Missing descriptors for subtypes 3,4,5

cdc_abstract_control_management_functional_descriptor = Descriptor(
    name='cdc_abstract_control_management_functional_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_CDC_DescriptorSubTypes.ABSTRACT_CONTROL_MANAGEMENT),
        BitField(name='bmCapabilities', value=0, length=8)
    ])


cdc_union_functional_descriptor = Descriptor(
    name='cdc_union_functional_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_CDC_DescriptorSubTypes.UNION_FUNCTIONAL),
        UInt8(name='bMasterInterface', value=0),
        Repeat(UInt8(name='bSlaveInterfaceX', value=0), 0, 251)
    ])


# TODO: Missing descriptors 7,8,9,10,11,12,13,14

cdc_ethernet_networking_functional_descriptor = Descriptor(
    name='cdc_ethernet_networking_functional_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_CDC_DescriptorSubTypes.ETHERNET_NETWORKING),
        UInt8(name='iMACAddress', value=0),
        BitField(name='bmEthernetStatistics', value=0xffffffff, length=32),
        LE16(name='wMaxSegmentSize', value=1514),
        LE16(name='wNumberMCFilters', value=0),
        UInt8(name='bNumberPowerFilters', value=0)
    ])
