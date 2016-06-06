'''
USB Configuration class.
Each instance represents a single USB configuration.
In most cases it should not be subclassed.
'''
import struct
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.wrappers import mutable


class USBConfiguration(USBBaseActor):

    name = 'USB Configuration'

    # Those attributes can be ORed
    # At least one should be selected
    ATTR_BASE = 0x80
    ATTR_SELF_POWERED = ATTR_BASE | 0x40
    ATTR_REMOTE_WAKEUP = ATTR_BASE | 0x20

    def __init__(
        self, app,
        index, string, interfaces,
        attributes=ATTR_REMOTE_WAKEUP | ATTR_SELF_POWERED,
        max_power=0x32,
    ):
        '''
        :param app: application instance
        :param index: configuration index (starts from 1)
        :param string: configuration string
        :param interfaces: list of interfaces for this configuration
        :param attributes: configuratioin attributes. one or more of USBConfiguration.ATTR_* (default: ATTR_REMOTE_WAKEUP | ATTR_SELF_POWERED)
        :param max_power: maximum power consumption of this configuration (default: 0x32)
        '''
        super(USBConfiguration, self).__init__(app)
        self._index = index
        self._string = string
        self._string_index = 0
        self.interfaces = interfaces
        self._attributes = attributes
        self._max_power = max_power
        self._device = None
        for i in self.interfaces:
            i.set_configuration(self)

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
    def get_descriptor(self):
        interface_descriptors = b''
        for i in self.interfaces:
            interface_descriptors += i.get_descriptor()
        bLength = 9
        bDescriptorType = 2
        wTotalLength = len(interface_descriptors) + 9
        bNumInterfaces = len(self.interfaces)
        d = struct.pack(
            '<BBHBBBBB',
            bLength,
            bDescriptorType,
            wTotalLength,
            bNumInterfaces,
            self._index,
            self._string_index,
            self._attributes,
            self._max_power
        )
        return d + interface_descriptors
