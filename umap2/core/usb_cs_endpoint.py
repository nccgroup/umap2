'''
Class-Specific endpoint (used in USB Audio)
'''
import struct
from umap2.core.usb import DescriptorType
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.helpers import mutable


class USBCSEndpoint(USBBaseActor):

    name = 'CSEndpoint'

    def __init__(self, name, app, phy, cs_config):
        '''
        :param name: Name of the endpoint
        :param app: Umap2 application
        :param phy: Physical connection
        :param cs_config: Containing class specific config
        '''
        super(USBCSEndpoint, self).__init__(app, phy)
        self.name = name
        self.cs_config = cs_config
        self.interface = None
        self.device_class = None
        self.request_handlers = {
            1: self.handle_clear_feature_request
        }

    def handle_clear_feature_request(self, req):
        self.interface.phy.send_on_endpoint(0, b'')

    def set_interface(self, interface):
        self.interface = interface

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    @mutable('usbcsendpoint_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        descriptor_type = DescriptorType.cs_endpoint
        length = len(self.cs_config) + 2
        response = struct.pack('BB', length, descriptor_type) + self.cs_config
        return response
