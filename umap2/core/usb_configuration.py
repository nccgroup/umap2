# USBConfiguration.py
#
# Contains class definition for USBConfiguration.
import struct
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.wrappers import mutable


class USBConfiguration(USBBaseActor):

    def __init__(self, app, configuration_index, configuration_string, interfaces):
        super(USBConfiguration, self).__init__(app)
        self.configuration_index = configuration_index
        self.configuration_string = configuration_string
        self.configuration_string_index = 0
        self.interfaces = interfaces

        self.attributes = 0xe0
        self.max_power = 0x32

        self.device = None

        for i in self.interfaces:
            i.set_configuration(self)

    def set_device(self, device):
        self.device = device

    def set_configuration_string_index(self, i):
        self.configuration_string_index = i

    def get_string_by_id(self, str_id):
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
            self.configuration_index,
            self.configuration_string_index,
            self.attributes,
            self.max_power
        )
        return d + interface_descriptors
