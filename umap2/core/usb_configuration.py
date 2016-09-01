'''
USB Configuration class.
Each instance represents a single USB configuration.
In most cases it should not be subclassed.
'''
import struct
from umap2.core.usb_base import USBBaseActor
from umap2.core.usb import DescriptorType
from umap2.fuzz.helpers import mutable


class USBConfiguration(USBBaseActor):

    name = 'Configuration'

    # Those attributes can be ORed
    # At least one should be selected
    ATTR_BASE = 0x80
    ATTR_SELF_POWERED = ATTR_BASE | 0x40
    ATTR_REMOTE_WAKEUP = ATTR_BASE | 0x20

    def __init__(
        self, app, phy,
        index, string, interfaces,
        attributes=ATTR_SELF_POWERED,
        max_power=0x32,
    ):
        '''
        :param app: Umap2 application
        :param phy: Physical connection
        :param index: configuration index (starts from 1)
        :param string: configuration string
        :param interfaces: list of interfaces for this configuration
        :param attributes: configuratioin attributes. one or more of USBConfiguration.ATTR_* (default: ATTR_SELF_POWERED)
        :param max_power: maximum power consumption of this configuration (default: 0x32)
        '''
        super(USBConfiguration, self).__init__(app, phy)
        self._index = index
        self._string = string
        self._string_index = 0
        self.interfaces = interfaces
        self._attributes = attributes
        self._max_power = max_power
        self._device = None
        self.usb_class = None
        self.usb_vendor = None
        for i in self.interfaces:
            i.set_configuration(self)
            # this is fool-proof against weird drivers
            if i.usb_class is not None:
                self.usb_class = i.usb_class
            if i.usb_vendor is not None:
                self.usb_vendor = i.usb_vendor

    def set_device(self, device):
        '''
        :param device: usb device
        '''
        self._device = device

    def set_string_index(self, string_index):
        '''
        :param string_index: configuration string index
        '''
        self._string_index = string_index

    def get_string(self):
        '''
        :return: the configuration string
        '''
        return self._string

    def get_string_by_id(self, str_id):
        '''
        :param str_id: string id
        :return: string with id of str_id
        '''
        s = super(USBConfiguration, self).get_string_by_id(str_id)
        if not s:
            for iface in self.interfaces:
                s = iface.get_string_by_id(str_id)
                if s:
                    break
        return s

    @mutable('configuration_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        '''
        Get the configuration descriptor.
        The configuration descriptor is composed of one or more
        interface descriptors.

        :return: a string of the entire configuration descriptor
        '''
        interface_descriptors = b''
        for i in self.interfaces:
            interface_descriptors += i.get_descriptor(usb_type, valid)
        bLength = 9  # always 9
        bDescriptorType = DescriptorType.configuration
        wTotalLength = len(interface_descriptors) + 9
        bNumInterfaces = len(self.interfaces)
        d = struct.pack(
            '<BBHBBBBB',
            bLength,
            bDescriptorType,
            wTotalLength & 0xffff,
            bNumInterfaces,
            self._index,
            self._string_index,
            self._attributes,
            self._max_power
        )
        return d + interface_descriptors

    @mutable('other_speed_configuration_descriptor')
    def get_other_speed_descriptor(self, usb_type='fullspeed', valid=False):
        '''
        Get the other speed configuration descriptor.
        We implement it the same as configuration descriptor,
        only with different descriptor type.

        :return: a string of the entire other speed configuration descriptor
        '''
        interface_descriptors = b''
        for i in self.interfaces:
            interface_descriptors += i.get_descriptor(usb_type, valid)
        bLength = 9  # always 9
        bDescriptorType = DescriptorType.other_speed_configuration
        wTotalLength = len(interface_descriptors) + 9
        bNumInterfaces = len(self.interfaces)
        d = struct.pack(
            '<BBHBBBBB',
            bLength,
            bDescriptorType,
            wTotalLength & 0xffff,
            bNumInterfaces,
            self._index,
            self._string_index,
            self._attributes,
            self._max_power
        )
        return d + interface_descriptors
