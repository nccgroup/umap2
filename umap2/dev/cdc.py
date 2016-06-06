'''
Contains class definitions to implement a USB CDC device.

.. todo:: see here re-enpoints <http://janaxelson.com/usb_virtual_com_port.htm>_
'''
from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.core.usb_cs_interface import USBCSInterface
from umap2.fuzz.helpers import mutable


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


class USBCommunicationInterface(USBInterface):

    name = "USB Communication Interface"

    def __init__(self, app, int_num, data_iface_num):
        bmCapabilities = 0x03
        bControlInterface = int_num
        bDataInterface = data_iface_num
        super(USBCommunicationInterface, self).__init__(
            app=app,
            interface_number=int_num,
            interface_alternate=0,
            interface_class=USBClass.CDC,
            interface_subclass=0x02,
            interface_protocol=0x01,
            interface_string_index=0,
            endpoints=[
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
            ],
            cs_interfaces=[
                # Header Functional Descriptor
                USBCSInterface(app, [0x00, 0x1001], 2, 2, 1),
                # Call Management Functional Descriptor
                USBCSInterface(app, [0x01, bmCapabilities, bDataInterface], 2, 2, 1),
                USBCSInterface(app, [0x02, bmCapabilities], 2, 2, 1),
                USBCSInterface(app, [0x06, bControlInterface, bDataInterface], 2, 2, 1)
            ],
            device_class=USBCDCClass(app)
        )

    def handle_ep3_buffer_available(self):
        self.logger.debug('ep3 buffer available')


class USBCDCDataInterface(USBInterface):
    name = "USB CDC Data interface"

    def __init__(self, app, int_num):
        # TODO: un-hardcode string index (last arg before "verbose")
        super(USBCDCDataInterface, self).__init__(
            app=app,
            interface_number=int_num,
            interface_alternate=0,
            interface_class=USBClass.CDCData,
            interface_subclass=0,
            interface_protocol=0,
            interface_string_index=0,
            endpoints=[
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
            ],
            device_class=USBCDCClass(app)
        )

    @mutable('cdc_handle_ep1_data_available')
    def handle_ep1_data_available(self, data):
        self.logger.debug("handling %#x bytes of cdc data" % (len(data)))

    def handle_ep2_buffer_available(self):
        self.logger.debug('ep2 buffer available')


class USBCDCDevice(USBDevice):
    name = "USB CDC device"

    def __init__(self, app, vid=0x2548, pid=0x1001, rev=0x0010, **kwargs):
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
            configurations=[
                USBConfiguration(
                    app=app,
                    index=1,
                    string="Emulated CDC",
                    interfaces=[
                        USBCommunicationInterface(app, 0, 1),
                        USBCDCDataInterface(app, 1)
                    ]
                )
            ],
        )


usb_device = USBCDCDevice
