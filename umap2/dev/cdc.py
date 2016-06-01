# USBCDC.py
#
# Contains class definitions to implement a USB CDC device.

'''
.. todo:: see here re-enpoints <http://janaxelson.com/usb_virtual_com_port.htm>_
'''
from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_cs_interface import USBCSInterface
from umap2.fuzz.wrappers import mutable


class USBCDCClass(USBClass):
    name = "USB CDC class"

    def setup_local_handlers(self):
        self.local_handlers = {
            0x22: self.handle_cdc_set_control_line_state,
            0x20: self.handle_cdc_set_line_coding,
        }

    @mutable('cdc_set_control_line_state_response')
    def handle_cdc_set_control_line_state(self, req):
        return b''

    @mutable('cdc_set_line_coding_response')
    def handle_cdc_set_line_coding(self, req):
        return b''


class USBCDCInterface(USBInterface):
    name = "USB CDC interface"

    def __init__(self, int_num, app, usbclass, sub, proto):
        descriptors = {}
        self.name = USBCDCInterface.name + '(%s)' % int_num
        cs_config1 = [
            0x00,  # Header Functional Descriptor
            0x1001,  # bcdCDC
        ]

        bmCapabilities = 0x03
        bDataInterface = 0x01

        cs_config2 = [
            0x01,  # Call Management Functional Descriptor
            bmCapabilities,
            bDataInterface
        ]

        bmCapabilities = 0x06

        cs_config3 = [
            0x02,  # Abstract Control Management Functional Descriptor
            bmCapabilities
        ]

        bControlInterface = 0
        bSubordinateInterface0 = 1

        cs_config4 = [
            0x06,  # Union Functional Descriptor
            bControlInterface,
            bSubordinateInterface0
        ]

        cs_interfaces0 = [
            USBCSInterface(app, cs_config1, 2, 2, 1),
            USBCSInterface(app, cs_config2, 2, 2, 1),
            USBCSInterface(app, cs_config3, 2, 2, 1),
            USBCSInterface(app, cs_config4, 2, 2, 1)
        ]

        cs_interfaces1 = []

        endpoints0 = [
            USBEndpoint(
                app=app,
                number=0x3,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_interrupt,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0xff,
                handler=self.handle_ep3_buffer_available
            )
        ]

        endpoints1 = [
            USBEndpoint(
                app=app,
                number=0x1,
                direction=USBEndpoint.direction_out,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0x00,
                handler=self.handle_ep1_data_available
            ),
            USBEndpoint(
                app=app,
                number=0x2,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0x00,
                handler=self.handle_ep2_buffer_available
            )
        ]

        if int_num == 0:
            endpoints = endpoints0
            cs_interfaces = cs_interfaces0

        elif int_num == 1:
            endpoints = endpoints1
            cs_interfaces = cs_interfaces1

        # TODO: un-hardcode string index (last arg before "verbose")
        super(USBCDCInterface, self).__init__(
            app=app,
            interface_number=int_num,
            interface_alternate=0,
            interface_class=usbclass,
            interface_subclass=sub,
            interface_protocol=proto,
            interface_string_index=0,
            endpoints=endpoints,
            descriptors=descriptors,
            cs_interfaces=cs_interfaces
        )

        self.device_class = USBCDCClass(app)
        self.device_class.set_interface(self)

    @mutable('cdc_handle_ep1_data_available')
    def handle_ep1_data_available(self, data):
        self.logger.debug("handling", len(data), "bytes of cdc data")

    def handle_ep3_buffer_available(self):
        self.logger.debug('ep3 buffer available')

    def handle_ep2_buffer_available(self):
        self.logger.debug('ep2 buffer available')


class USBCDCDevice(USBDevice):
    name = "USB CDC device"

    def __init__(self, app, vid=0x2548, pid=0x1001, rev=0x0010, **kwargs):
        interface0 = USBCDCInterface(0, app, USBClass.CDC, 0x02, 0x01)
        interface1 = USBCDCInterface(1, app, USBClass.CDCData, 0x00, 0x00)

        config = USBConfiguration(
            app=app,
            configuration_index=1,
            configuration_string="Emulated CDC",
            interfaces=[interface0, interface1]
        )

        super(USBCDCDevice, self).__init__(
            app=app,
            device_class=USBClass.CDC,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string="Vendor",
            product_string="Product",
            serial_number_string="Serial",
            configurations=[config],
            descriptors={},
        )


usb_device = USBCDCDevice
