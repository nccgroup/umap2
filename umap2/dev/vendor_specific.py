'''
Contains class definitions to implement a Vendor Specific USB Device.
'''
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
            usb_class=USBVendorSpecificClass(app, phy),
            usb_vendor=USBVendorSpecificVendor(app, phy)
        )

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
            handler=self.global_handler,
            usb_class=USBVendorSpecificClass(self.app, self.phy),
            usb_vendor=USBVendorSpecificVendor(self.app, self.phy)
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

    def global_handler(self, data=None):
        if data is not None:
            self.usb_function_supported()


usb_device = USBVendorSpecificDevice
