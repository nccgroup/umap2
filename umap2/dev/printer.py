'''
Contains class definitions to implement a USB printer device.

Still not working well, linux fails to set altsetting 0 on iface 0
and then we get exception from Max342xPhy
'''
import time
import struct

from umap2.core.usb_class import USBClass
from umap2.core.usb_device import USBDevice
from umap2.core.usb_configuration import USBConfiguration
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_endpoint import USBEndpoint
from umap2.fuzz.helpers import mutable


class USBPrinterClass(USBClass):
    name = 'PrinterClass'

    def setup_local_handlers(self):
        self.local_handlers = {
            0x00: self.handle_get_device_id,
        }

    @mutable('get_device_id_response')
    def handle_get_device_id(self, req):
        device_id_dict = {
            'MFG': 'Hewlett-Packard',
            'CMD': 'PJL,PML,PCLXL,POSTSCRIPT,PCL',
            'MDL': 'HP Color LaserJet CP1515n',
            'CLS': 'PRINTER',
            'DES': 'Hewlett-Packard Color LaserJet CP1515n',
            'MEM': 'MEM=55MB',
            'COMMENT': 'RES=600x8',
        }
        device_id = ';'.join(k + ':' + v for k, v in device_id_dict.items())
        device_id += ';'
        length = struct.pack('>H', len(device_id))
        response = length + str.encode(device_id)
        return response


class USBPrinterInterface(USBInterface):
    name = 'PrinterInterface'

    def __init__(self, app, phy, int_num, usbclass, sub, proto):
        self.filename = time.strftime('%Y%m%d%H%M%S', time.localtime())
        self.filename += '.pcl'
        self.writing = False

        endpoints0 = [
            USBEndpoint(
                app=app,
                phy=phy,
                number=1,          # endpoint address
                direction=USBEndpoint.direction_out,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,      # max packet size
                interval=0x80,          # polling interval, see USB 2.0 spec Table 9-13
                handler=self.handle_data_available    # handler function
            ),
            USBEndpoint(
                app=app,
                phy=phy,
                number=2,          # endpoint address
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,      # max packet size
                interval=0,          # polling interval, see USB 2.0 spec Table 9-13
                handler=None        # handler function
            )
        ]

        endpoints1 = [
            USBEndpoint(
                app=app,
                phy=phy,
                number=1,
                direction=USBEndpoint.direction_out,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0x80,
                handler=self.handle_data_available
            ),
            USBEndpoint(
                app=app,
                phy=phy,
                number=2,
                direction=USBEndpoint.direction_in,
                transfer_type=USBEndpoint.transfer_type_bulk,
                sync_type=USBEndpoint.sync_type_none,
                usage_type=USBEndpoint.usage_type_data,
                max_packet_size=0x40,
                interval=0,
                handler=None
            )
        ]
        if int_num == 0:
            endpoints = endpoints0
        if int_num == 1:
            endpoints = endpoints1

        # TODO: un-hardcode string index (last arg before 'verbose')
        super(USBPrinterInterface, self).__init__(
            app=app,
            phy=phy,
            interface_number=int_num,
            interface_alternate=0,
            interface_class=usbclass,
            interface_subclass=sub,
            interface_protocol=proto,
            interface_string_index=0,
            endpoints=endpoints,
            device_class=USBPrinterClass(app, phy),
        )

    @mutable('handle_data_available')
    def handle_data_available(self, data):
        if not self.writing:
            self.info('Writing PCL file: %s' % self.filename)

        with open(self.filename, 'ab') as out_file:
            self.writing = True
            out_file.write(data)

        text_buffer = ''.join(chr(c) for c in data)

        if 'EOJ\n' in text_buffer:
            self.info('File write complete')
            out_file.close()
            self.writing = False


class USBPrinterDevice(USBDevice):
    name = 'PrinterDevice'

    def __init__(
        self, app, phy, vid=0x03f0, pid=0x4417, rev=0x0001,
        usbclass=USBClass.Printer, subclass=1, proto=2
    ):
        super(USBPrinterDevice, self).__init__(
            app=app,
            phy=phy,
            device_class=USBClass.Unspecified,
            device_subclass=0,
            protocol_rel_num=0,
            max_packet_size_ep0=64,
            vendor_id=vid,
            product_id=pid,
            device_rev=rev,
            manufacturer_string='Hewlett-Packard',
            product_string='HP Color LaserJet CP1515n',
            serial_number_string='00CNC2618971',
            configurations=[
                USBConfiguration(
                    app=app,
                    phy=phy,
                    index=1,
                    string='Printer',
                    interfaces=[
                        USBPrinterInterface(app, phy, 0, usbclass, subclass, proto),
                        # USBPrinterInterface(app, phy, 1, 0xff, 1, 1),
                    ]
                )
            ],
        )


usb_device = USBPrinterDevice
