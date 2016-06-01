# USBInterface.py
#
# Contains class definition for USBInterface.
import struct
from umap2.core.usb import interface_class_to_descriptor_type, DescriptorType
from umap2.core.usb_base import USBBaseActor
from umap2.fuzz.wrappers import mutable


class USBInterface(USBBaseActor):
    name = "generic USB interface"

    def __init__(
        self, app, interface_number, interface_alternate, interface_class,
        interface_subclass, interface_protocol, interface_string_index,
        endpoints=None, descriptors=None, cs_interfaces=None
    ):
        super(USBInterface, self).__init__(app)
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

        for e in self.endpoints:
            e.set_interface(self)

        self.device_class = None

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
        self.debug(('received GET_DESCRIPTOR req %d, index %d, language 0x%04x, length %d' % (dtype, dindex, lang, n)))
        # TODO: handle KeyError
        response = self.descriptors[dtype]
        if callable(response):
            response = response(dindex)

        if response:
            n = min(n, len(response))
            self.configuration.device.app.send_on_endpoint(0, response[:n])
            self.verbose('sent %d bytes in response' % (n))

    def handle_set_interface_request(self, req):
        self.debug("received SET_INTERFACE request")
        self.configuration.device.app.stall_ep0()
        # self.configuration.device.app.send_on_endpoint(0, b'')

    # Table 9-12 of USB 2.0 spec (pdf page 296)
    @mutable('interface_descriptor')
    def get_descriptor(self):

        bLength = 9
        bDescriptorType = 4
        bNumEndpoints = len(self.endpoints)

        d = struct.pack(
            '<BBBBBBBBB',
            bLength,          # length of descriptor in bytes
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
            d += e.get_descriptor()

        for e in self.endpoints:
            d += e.get_descriptor()

        return d
