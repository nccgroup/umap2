# USBCSEndpoint.py
#
# Contains class definition for USBCSEndpoint.
import struct
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.helpers import mutable


class USBCSEndpoint(USBBaseActor):

    def __init__(self, app, cs_config):
        super(USBCSEndpoint, self).__init__(app)
        self.cs_config = cs_config
        self.number = self.cs_config[1]
        self.interface = None
        self.device_class = None
        self.request_handlers = {
            1: self.handle_clear_feature_request
        }

    def handle_clear_feature_request(self, req):
        self.interface.app.send_on_endpoint(0, b'')

    def set_interface(self, interface):
        self.interface = interface

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    @mutable('usbcsendpoint_descriptor')
    def get_descriptor(self):
        if self.cs_config[0] == 0x01:  # EP_GENERAL
            bLength = 7
            bDescriptorType = 37  # CS_ENDPOINT
            bDescriptorSubtype = 0x01  # EP_GENERAL
            bmAttributes, bLockDelayUnits, wLockDelay = struct.unpack('<BBB', self.cs_config[2:5])
        d = struct.pack(
            '<BBBBBH',
            bLength,
            bDescriptorType,
            bDescriptorSubtype,
            bmAttributes,
            bLockDelayUnits,
            wLockDelay,
        )
        return d
