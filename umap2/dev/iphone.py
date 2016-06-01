# USBIphone.py
#
# Contains class definitions to implement a USB iPhone device.

from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_vendor import USBVendor
from umap2.fuzz.wrappers import mutable


class USBIphoneVendor(USBVendor):
    name = "USB iPhone vendor"

    def setup_local_handlers(self):
        self.local_handlers = {
            0x40: self.handle_40,
            0x45: self.handle_45
        }

    @mutable('40_response')
    def handle_40(self, req):
        self.info("received reset request")
        self.device.app.send_on_endpoint(0, b'')

    @mutable('45_response')
    def handle_45(self, req):
        self.info("received reset request")
        self.device.app.send_on_endpoint(0, b'\x03')


class USBIphoneClass(USBClass):
    name = "USB iPhone class"

    def setup_request_handlers(self):
        self.request_handlers = {
            0x22: self.handle_set_control_line_state,
            0x20: self.handle_set_line_coding
        }

    def handle_set_control_line_state(self, req):
        self.app.send_on_endpoint(0, b'')
        self.supported()

    def handle_set_line_coding(self, req):
        self.app.send_on_endpoint(0, b'')
        self.supported()


class USBIphoneInterface(USBInterface):
    name = "USB iPhone interface"

    def __init__(self, int_num, app, usbclass, sub, proto):
        descriptors = {}

        endpoints0 = [
            USBEndpoint(
                app,
                0x02,  # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,  # max packet size
                0x0a,  # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available  # handler function
            ),
            USBEndpoint(
                app,
                0x81,  # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,  # max packet size
                0x0a,  # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available  # handler function
            ),
            USBEndpoint(
                app,
                0x83,  # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_interrupt,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x4000,  # max packet size
                0x0a,  # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available  # handler function
            )

        ]
        endpoints1 = [
            USBEndpoint(
                app,
                0x04,  # endpoint address
                USBEndpoint.direction_out,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,  # max packet size
                0x00,  # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available  # handler function
            ),
            USBEndpoint(
                app,
                0x85,  # endpoint address
                USBEndpoint.direction_in,
                USBEndpoint.transfer_type_bulk,
                USBEndpoint.sync_type_none,
                USBEndpoint.usage_type_data,
                0x0002,  # max packet size
                0x00,  # polling interval, see USB 2.0 spec Table 9-13
                self.handle_data_available  # handler function
            )
        ]
        endpoints2 = []

        if int_num == 0:
            endpoints = endpoints0
        elif int_num == 1:
            endpoints = endpoints1
        elif int_num == 2:
            endpoints = endpoints2

        # TODO: un-hardcode string index (last arg before "verbose")
        USBInterface.__init__(
            self,
            app,
            int_num,  # interface number
            0,  # alternate setting
            usbclass,  # 3 interface class
            sub,  # 0 subclass
            proto,  # 0 protocol
            0,  # string index
            endpoints,
            descriptors
        )

        self.device_class = USBIphoneClass(app)
        self.device_class.set_interface(self)

    def handle_data_available(self, data):
        self.verbose("handling", len(data), "bytes of audio data")


class USBIphoneDevice(USBDevice):
    name = "USB iPhone device"

    def __init__(self, app, vid, pid, rev):
        int_class = 0
        int_subclass = 0
        int_proto = 0
        interface0 = USBIphoneInterface(0, app, 0x06, 0x01, 0x01)
        interface1 = USBIphoneInterface(1, app, 0xff, 0xfe, 0x02)
        interface2 = USBIphoneInterface(2, app, 0xff, 0xfd, 0x01)

        config = [
            USBConfiguration(
                app,
                1,  # index
                "iPhone",  # string desc
                [interface0, interface1, interface2]  # interfaces
            ),
            USBConfiguration(
                app,
                2,  # index
                "iPhone",  # string desc
                [interface0, interface1, interface2]  # interfaces
            ),
            USBConfiguration(
                app,
                3,  # index
                "iPhone",  # string desc
                [interface0, interface1, interface2]  # interfaces
            ),
            USBConfiguration(
                app,
                4,  # index
                "iPhone",  # string desc
                [interface0, interface1, interface2]  # interfaces
            )
        ]

        USBDevice.__init__(
            self,
            app,
            int_class,  # 0 device class
            int_subclass,  # device subclass
            int_proto,  # protocol release number
            64,  # max packet size for endpoint 0
            0x05ac,  # vendor id
            0x1297,  # product id
            0x0310,  # device revision
            "Apple",  # manufacturer string
            "iPhone",  # product string
            "a9f579a7e04281fbf77fe04d06b5cc083e6eb5a3",  # serial number string
            config,
        )
        self.device_vendor = USBIphoneVendor()
        self.device_vendor.set_device(self)


usb_device = USBIphoneDevice
