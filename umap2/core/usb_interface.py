'''
USB Interface class.
Each instance represents a single USB interface.
This is a base class, and should be subclassed.
'''
import struct
from umap2.core.usb import interface_class_to_descriptor_type, DescriptorType
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.helpers import mutable


class USBInterface(USBBaseActor):
    name = 'Interface'

    def __init__(
        self, app, phy, interface_number, interface_alternate, interface_class,
        interface_subclass, interface_protocol, interface_string_index,
        endpoints=None, descriptors=None, cs_interfaces=None,
        usb_class=None, usb_vendor=None,
    ):
        '''
        :param app: umap2 application
        :param phy: physical connection
        :param interface_number: interface number
        :param interface_alternate: alternate settings
        :param interface_class: interface class
        :param interface_subclass: interface subclass
        :param interface_protocol: interface protocol
        :param interface_string_index: interface string index
        :param endpoints: list of endpoints for this interface (default: None)
        :param descriptors: dictionary of descriptor handlers for the interface (default: None)
        :param cs_interfaces: list of class specific interfaces (default: None)
        :param usb_class: USB device class (default: None)
        :param usb_vendor: USB device vendor (default: None)
        '''
        super(USBInterface, self).__init__(app, phy)
        self.number = interface_number
        self.alternate = interface_alternate
        self.iclass = interface_class
        self.subclass = interface_subclass
        self.protocol = interface_protocol
        self.string_index = interface_string_index

        self.endpoints = [] if endpoints is None else endpoints
        self.descriptors = {} if descriptors is None else descriptors
        self.cs_interfaces = [] if cs_interfaces is None else cs_interfaces

        self.descriptors[DescriptorType.interface] = self.get_descriptor

        self.request_handlers = {
            0x06: self.handle_get_descriptor_request,
            0x0b: self.handle_set_interface_request
        }

        self.configuration = None

        self.usb_class = usb_class
        self.usb_vendor = usb_vendor

        for e in self.endpoints:
            e.interface = self
            if self.usb_class is None:
                self.usb_class = e.usb_class
            if self.usb_vendor is None:
                self.usb_vendor = e.usb_vendor

        if self.usb_class:
            self.usb_class.interface = self
        if self.usb_vendor:
            self.usb_vendor.interface = self

    def set_configuration(self, config):
        self.configuration = config

    # USB 2.0 specification, section 9.4.3 (p 281 of pdf)
    # HACK: blatant copypasta from USBDevice pains me deeply
    def handle_get_descriptor_request(self, req):
        dtype = (req.value >> 8) & 0xff
        dindex = req.value & 0xff
        lang = req.index
        n = req.length

        response = None
        self.debug(('Received GET_DESCRIPTOR req %d, index %d, language 0x%04x, length %d' % (dtype, dindex, lang, n)))
        # TODO: handle KeyError
        response = self.descriptors[dtype]
        if callable(response):
            response = response(dindex)

        if response:
            self.phy.send_on_endpoint(0, response)
            self.verbose('sent %d bytes in response' % (n))

    def handle_set_interface_request(self, req):
        self.debug('Received SET_INTERFACE request')
        self.phy.stall_ep0()

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    @mutable('interface_descriptor')
    def get_descriptor(self, usb_type='fullspeed', valid=False):

        bLength = 9
        bDescriptorType = DescriptorType.interface
        bNumEndpoints = len(self.endpoints)

        d = struct.pack(
            '<BBBBBBBBB',
            bLength,  # length of descriptor in bytes
            bDescriptorType,  # descriptor type 4 == interface
            self.number,
            self.alternate,
            bNumEndpoints,
            self.iclass,
            self.subclass,
            self.protocol,
            self.string_index
        )

        if self.iclass:
            iclass_desc_num = interface_class_to_descriptor_type(self.iclass)
            if iclass_desc_num:
                desc = self.descriptors[iclass_desc_num]
                if callable(desc):
                    desc = desc()
                d += desc

        for e in self.cs_interfaces:
            d += e.get_descriptor(usb_type, valid)

        for e in self.endpoints:
            d += e.get_descriptor(usb_type, valid)

        return d
