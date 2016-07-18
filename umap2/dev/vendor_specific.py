'''
Contains class definitions to implement a Vendor Specific USB Device.
'''
from umap2.core.usb import State
from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_vendor import USBVendor
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface


class USBVendorSpecificVendor(USBVendor):
    name = 'VendorSpecificVendor'

    def setup_local_handlers(self):
        self.local_handlers = {
            x: self.handle_generic for x in range(256)
        }

    def handle_generic(self, req):
        self.always('Generic handler - req: %s' % req)


class USBVendorSpecificClass(USBClass):
    name = 'VendorSpecificClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            x: self.handle_generic for x in range(256)
        }

    def handle_generic(self, req):
        self.always('Generic handler - req: %s' % req)


class USBVendorSpecificInterface(USBInterface):
    name = 'VendorSpecificInterface'

    def __init__(self, app, phy, num=0, interface_alternate=0, endpoints=[]):
        # TODO: un-hardcode string index
        super(USBVendorSpecificInterface, self).__init__(
            app=app,
            phy=phy,
            interface_number=num,
            interface_alternate=interface_alternate,
            interface_class=USBClass.VendorSpecific,
            interface_subclass=1,
            interface_protocol=1,
            interface_string_index=0,
            endpoints=endpoints,
            device_class=USBVendorSpecificClass(app, phy)
        )
        # hack - some weird devices ask the interface for class or vendor requests...
        self.device_vendor = USBVendorSpecificVendor(app, phy, self)
        self.device_class = USBVendorSpecificClass(app, phy)

    def handle_buffer_available(self):
        pass

    def handle_data_available(self, data):
        self.usb_function_supported()
        return

    def handle_set_interface_request(self, req):
        self.always('set interface request')
        self.usb_function_supported()


class USBVendorSpecificDevice(USBDevice):
    name = 'VendorSpecificDevice'

    def __init__(self, app, phy, vid, pid, rev=1, **kwargs):
        self.app = app
        self.phy = phy
        super(USBVendorSpecificDevice, self).__init__(
            app=app,
            phy=phy,
            device_class=USBClass.VendorSpecific,
            device_subclass=1,
            protocol_rel_num=1,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='UMAP2. VID:0x%04x' % vid,
            product_string='UMAP2. PID:0x%04x' % pid,
            serial_number_string='123456',
            configurations=[
                USBConfiguration(
                    app=app,
                    phy=phy,
                    index=1,
                    string='Vendor Specific Conf',
                    interfaces=self.get_interfaces(),
                    attributes=USBConfiguration.ATTR_SELF_POWERED,
                )
            ],
        )

        self.device_vendor = USBVendorSpecificVendor(app, phy, self)
        self.device_class = USBVendorSpecificClass(app, phy)

        # HACK 1 - sometime we dont get the set_configuration request - so we go ahead and set it ahead of time...

        self.configuration = self.configurations[self.config_num]
        self.state = State.configured

        # collate endpoint numbers
        for i in self.configuration.interfaces:
            for e in i.endpoints:
                self.endpoints[e.number] = e
        # HACK 2 - added ep0 to the endpoint list - as it was addresses by a device...
        self.endpoints[0] = self.get_endpoint(0, USBEndpoint.direction_out, USBEndpoint.transfer_type_interrupt)

        # HACK 3 - adding vendor and class handlers to each endpoint
        for ep in self.endpoints.values():
            ep.device_vendor = USBVendorSpecificVendor(app, phy, self)
            ep.device_class = USBVendorSpecificClass(app, phy)

    def get_endpoint(self, num, direction, transfer_type, max_packet_size=0x40):
        return USBEndpoint(
            app=self.app,
            phy=self.phy,
            number=num,
            direction=direction,
            transfer_type=transfer_type,
            sync_type=USBEndpoint.sync_type_none,
            usage_type=USBEndpoint.usage_type_data,
            max_packet_size=max_packet_size,
            interval=1,
            handler=self.global_handler
        )

    def get_interfaces(self):
        return [USBVendorSpecificInterface(self.app, self.phy, num=0,  # must be zero for btusb
                endpoints=[
                    self.get_endpoint(1, USBEndpoint.direction_in, USBEndpoint.transfer_type_interrupt),
                    self.get_endpoint(1, USBEndpoint.direction_out, USBEndpoint.transfer_type_interrupt),
                    self.get_endpoint(2, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(2, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(3, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous),
                    self.get_endpoint(3, USBEndpoint.direction_out, USBEndpoint.transfer_type_isochronous),
                    self.get_endpoint(4, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(4, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk),
                    self.get_endpoint(5, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous, max_packet_size=0x10),
                    self.get_endpoint(5, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk, max_packet_size=0x20),
                ]),
                ]

    def get_interface_for_ttusbir(self):
        return [USBVendorSpecificInterface(self.app, self.phy, num=0,  # must be zero for btusb
                endpoints=[
                    self.get_endpoint(1, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous, max_packet_size=0x10),
                    self.get_endpoint(2, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk, max_packet_size=0x20),
                ]),
                ]

    def global_handler(self, data=None):
        if data is not None:
            self.usb_function_supported()

    def __get_interfaces(self):
        '''
        :return: list of interfaces
        ep1 - OUT - int, bulk, iso
        ep2,3 - IN - int, bulk, iso
        '''
        ep1_options = [None]
        ep2_options = [None]
        ep3_options = [None]

        ep1_options += [self.get_endpoint(num, direction, transfer_type) for (num, direction, transfer_type) in
                        [(1, USBEndpoint.direction_out, USBEndpoint.transfer_type_interrupt),
                            (1, USBEndpoint.direction_out, USBEndpoint.transfer_type_bulk),
                            # (1, USBEndpoint.direction_out, USBEndpoint.transfer_type_isochronous)
                         ]
                        ]
        ep2_options += [self.get_endpoint(num, direction, transfer_type) for (num, direction, transfer_type) in
                        [(2, USBEndpoint.direction_in, USBEndpoint.transfer_type_interrupt),
                        (2, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
                        # (2, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous)
                         ]
                        ]
        # # ep3_options += [self.get_endpoint(num, direction, transfer_type) for (num, direction, transfer_type) in
        #                 [(3, USBEndpoint.direction_in, USBEndpoint.transfer_type_interrupt),
        #                 (3, USBEndpoint.direction_in, USBEndpoint.transfer_type_bulk),
        #                 # (3, USBEndpoint.direction_in, USBEndpoint.transfer_type_isochronous)
        #                  ]
        #                 ]
        interfaces = []
        if_num = 0
        for ep1 in ep1_options:
            for ep2 in ep2_options:
                for ep3 in ep3_options:
                    interfaces.append(USBVendorSpecificInterface(self.app, self.phy, num=if_num, endpoints=[ep for ep in [ep1, ep2, ep3] if ep]))
                    if_num += 1
        return interfaces

usb_device = USBVendorSpecificDevice
