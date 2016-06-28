'''
Tempaltes related to generic enumeration stage
'''
# fields
from kitty.model import LE16, UInt8, BitField, String, RandomBytes
# containers
from kitty.model import Template, Container, List
# dynamic fields
from kitty.model import ElementCount, SizeInBytes
# encoders
from kitty.model import StrEncodeEncoder, ENC_INT_LE
from generic import Descriptor, SubDescriptor


class _DescriptorTypes:

    '''Descriptor types [Section 9.4, table 9.5]'''

    DEVICE = 0x1
    CONFIGURATION = 0x2
    STRING = 0x3
    INTERFACE = 0x4
    ENDPOINT = 0x5
    DEVICE_QUALIFIER = 0x6
    OTHER_SPEED_CONFIGURATION = 0x7
    INTERFACE_POWER = 0x8
    HID = 0x21
    HID_REPORT = 0x22
    CS_INTERFACE = 0x24  # usbcdc11.pdf table 24
    CS_ENDPOINT = 0x25  # usbcdc11.pdf table 24
    HUB = 0x29


# Device descriptor
# Section 9.6.1, page 261
device_descriptor = Descriptor(
    name='device_descriptor',
    descriptor_type=_DescriptorTypes.DEVICE,
    fields=[
        LE16(name='bcdUSB', value=0x0100),  # USB 2.0 is reported as 0x0200, USB 1.1 as 0x0110 and USB 1.0 as 0x0100
        UInt8(name='bDeviceClass', value=0),
        UInt8(name='bDeviceSubClass', value=0),
        UInt8(name='bDeviceProtocol', value=0),
        UInt8(name='bMaxPacketSize', value=64),  # valid sizes: 8,16,32,64
        LE16(name='idVendor', value=0),
        LE16(name='idProduct', value=0),
        LE16(name='bcdDevice', value=0),
        UInt8(name='iManufacturer', value=0),
        UInt8(name='iProduct', value=0),
        UInt8(name='iSerialNumber', value=0),
        UInt8(name='bNumConfigurations', value=0)
    ])

# Device qualifier descriptor
# Section 9.6.2, page 264
device_qualifier_descriptor = Descriptor(
    name='device_qualifier_descriptor',
    descriptor_type=_DescriptorTypes.DEVICE_QUALIFIER,
    fields=[
        LE16(name='bcdUSB', value=0x0100),  # USB 2.0 is reported as 0x0200, USB 1.1 as 0x0110 and USB 1.0 as 0x0100
        UInt8(name='bDeviceClass', value=0),
        UInt8(name='bDeviceSubClass', value=0),
        UInt8(name='bDeviceProtocol', value=0),
        UInt8(name='bMaxPacketSize', value=0),  # valid sizes: 8,16,32,64
        UInt8(name='bNumConfigurations', value=0),
        UInt8(name='bReserved', value=0)
    ])

# Configuration descriptor
# Section 9.6.3, page 265
configuration_descriptor = Template(
    name='configuration_descriptor',
    fields=[
        UInt8(name='bLength', value=9),
        UInt8(name='bDescriptorType', value=_DescriptorTypes.CONFIGURATION),
        SizeInBytes(name='wTotalLength', sized_field='/', length=16, encoder=ENC_INT_LE),
        ElementCount(name='bNumInterfaces', depends_on='interfaces', length=8),
        UInt8(name='bConfigurationValue', value=1),
        UInt8(name='iConfiguration', value=0),
        BitField(name='bmAttributes', value=0, length=8),
        UInt8(name='bMaxPower', value=1),
        List(name='interfaces', fields=[
            Container(name='iface and eps', fields=[
                SubDescriptor(
                    name='interface_descriptor',
                    descriptor_type=_DescriptorTypes.INTERFACE,
                    fields=[
                        UInt8(name='bInterfaceNumber', value=0),
                        UInt8(name='bAlternateSetting', value=0),
                        ElementCount(name='bNumEndpoints', depends_on='endpoints', length=8),
                        UInt8(name='bInterfaceClass', value=0x08),
                        UInt8(name='bInterfaceSubClass', value=0x06),
                        UInt8(name='bInterfaceProtocol', value=0x50),
                        UInt8(name='iInterface', value=0),
                        List(name='endpoints', fields=[
                            SubDescriptor(
                                name='endpoint_descriptor',
                                descriptor_type=_DescriptorTypes.ENDPOINT,
                                fields=[
                                    UInt8(name='bEndpointAddress', value=1),
                                    BitField(name='bmAttributes', value=0, length=8),
                                    LE16(name='wMaxPacketSize', value=0x40),
                                    UInt8(name='bInterval', value=0)
                                ])
                        ]),
                    ])
            ]),
        ]),
    ])


# Other_Speed_Configuration descriptor
# Section 9.6.4, page 267
other_speed_configuration_descriptor = Descriptor(
    name='other_speed_configuration_descriptor',
    descriptor_type=_DescriptorTypes.OTHER_SPEED_CONFIGURATION,
    fields=[
        LE16(name='wTotalLength', value=0xffff),  # TODO: real default size
        UInt8(name='bNumInterfaces', value=0xff),  # TODO: real default size
        UInt8(name='bConfigurationValue', value=0xff),  # TODO: real default size
        UInt8(name='iConfiguration', value=0xff),
        BitField(name='bmAttributes', value=0, length=8),
        UInt8(name='bMaxPower', value=0xff)
    ])


# Endpoint descriptor
# Section 9.6.6, page 269
endpoint_descriptor = Descriptor(
    name='endpoint_descriptor',
    descriptor_type=_DescriptorTypes.ENDPOINT,
    fields=[
        UInt8(name='bEndpointAddress', value=0),
        BitField(name='bmAttributes', value=0, length=8),
        LE16(name='wMaxPacketSize', value=65535),
        UInt8(name='bInterval', value=0)
    ])


# String descriptor (regular and zero)
# Section 9.6.7, page 273
string_descriptor = Descriptor(
    name='string_descriptor',
    descriptor_type=_DescriptorTypes.STRING,
    fields=[
        String(name='bString', value='hello_kitty', encoder=StrEncodeEncoder('utf_16_le'), max_size=254 / 2)
    ])


string_descriptor_zero = Descriptor(
    name='string_descriptor_zero',
    descriptor_type=_DescriptorTypes.STRING,
    fields=[
        RandomBytes(name='lang_id', min_length=0, max_length=253, step=3, value='\x04\x09')
    ])

hub_descriptor = Descriptor(
    name='hub_descriptor',
    descriptor_type=_DescriptorTypes.HUB,
    fields=[
        UInt8(name='bNbrPorts', value=4),
        BitField(name='wHubCharacteristics', value=0xe000, length=16),
        UInt8(name='bPwrOn2PwrGood', value=0x32),
        UInt8(name='bHubContrCurrent', value=0x64),
        UInt8(name='DeviceRemovable', value=0),
        UInt8(name='PortPwrCtrlMask', value=0xff)
    ])


# TODO: usbcsendpoint_descriptor
# TODO: usbcsinterface_descriptor
