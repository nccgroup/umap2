# USBEndpoint.py
#
# Contains class definition for USBEndpoint.
import struct
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.helpers import mutable


class USBEndpoint(USBBaseActor):
    name = 'Endpoint'
    direction_out = 0x00
    direction_in = 0x01

    transfer_type_control = 0x00
    transfer_type_isochronous = 0x01
    transfer_type_bulk = 0x02
    transfer_type_interrupt = 0x03

    sync_type_none = 0x00
    sync_type_async = 0x01
    sync_type_adaptive = 0x02
    sync_type_synchronous = 0x03

    usage_type_data = 0x00
    usage_type_feedback = 0x01
    usage_type_implicit_feedback = 0x02

    def __init__(
            self, app, phy, number, direction, transfer_type, sync_type,
            usage_type, max_packet_size, interval, handler, cs_endpoints=None,
            usb_class=None, usb_vendor=None):
        '''
        :param app: umap2 application
        :param phy: physical connection
        :param number: endpoint number
        :param direction: endpoint direction (direction_in/direction_out)
        :param transfer_type: one of USBEndpoint.transfer_type\*
        :param sync_type: one of USBEndpoint.sync_type\*
        :param usage_type: on of USBEndpoint.usage_type\*
        :param max_packet_size: maximum size of a packet
        :param interval: TODO
        :type handler:
            func(data) -> None if direction is out,
            func() -> None if direction is IN
        :param handler: interrupt handler for the endpoint
        :param cs_endpoints: list of class-specific endpoints (default: None)
        :param usb_class: USBClass instance (default: None)
        :param usb_vendor: USB device vendor (default: None)

        .. note:: OUT endpoint is 1, IN endpoint is either 2 or 3
        '''
        super(USBEndpoint, self).__init__(app, phy)
        self.number = number
        self.direction = direction
        self.transfer_type = transfer_type
        self.sync_type = sync_type
        self.usage_type = usage_type
        self.max_packet_size = max_packet_size
        self.interval = interval
        self.handler = handler
        self.interface = None
        self.usb_class = usb_class
        self.usb_vendor = usb_vendor
        self.cs_endpoints = [] if cs_endpoints is None else cs_endpoints

        self.request_handlers = {
            0: self.handle_get_status,
            1: self.handle_clear_feature_request,
        }

    def handle_clear_feature_request(self, req):
        self.interface.phy.send_on_endpoint(0, b'')

    def handle_get_status(self, req):
        self.info('in GET_STATUS of endpoint %d' % self.number)
        self.phy.send_on_endpoint(0, b'\x00\x00')

    def send(self, data):
        self.phy.send_on_endpoint(self.number, data)

    # see Table 9-13 of USB 2.0 spec (pdf page 297)
    @mutable('endpoint_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):
        address = (self.number & 0x0f) | (self.direction << 7)
        attributes = (
            (self.transfer_type & 0x03) |
            ((self.sync_type & 0x03) << 2) |
            ((self.usage_type & 0x03) << 4)
        )
        bLength = 7
        bDescriptorType = 5
        wMaxPacketSize = self._get_max_packet_size(usb_type)
        d = struct.pack(
            '<BBBBHB',
            bLength,
            bDescriptorType,
            address,
            attributes,
            wMaxPacketSize,
            self.interval
        )
        for cs in self.cs_endpoints:
            d += cs.get_descriptor()
        return d

    def _get_max_packet_size(self, usb_type):
        if usb_type == 'highspeed':
            return 512
        return self.max_packet_size
