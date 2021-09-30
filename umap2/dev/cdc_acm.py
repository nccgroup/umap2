'''
Implement a Communication Device Class (CDC) Abstract Control Class (ACM)
device.
The specification for this device may be found in CDC120-20101113-track.pdf
and in PSTN120.pdf.
'''
import struct
from binascii import unhexlify
from umap2.core.usb_interface import USBInterface
from umap2.core.usb_class import USBClass
from umap2.core.usb_endpoint import USBEndpoint
from umap2.dev.cdc import USBCDCDevice
from umap2.dev.cdc import CommunicationClassSubclassCodes
from umap2.dev.cdc import CommunicationClassProtocolCodes
from umap2.dev.cdc import DataInterfaceClassProtocolCodes
from umap2.dev.cdc import FunctionalDescriptor as FD


class USBCdcAcmDevice(USBCDCDevice):

    name = 'CDC ACM Device'

    bControlSubclass = CommunicationClassSubclassCodes.AbstractControlModel
    bControlProtocol = CommunicationClassProtocolCodes.AtCommands_v250
    bDataProtocol = DataInterfaceClassProtocolCodes.NoClassSpecificProtocolRequired

    def __init__(self, app, phy, vid=0x2548, pid=0x1001, rev=0x0010, cs_interfaces=None, cdc_cls=None, bmCapabilities=0x01, **kwargs):
        if cdc_cls is None:
            cdc_cls = self.get_default_class(app, phy)
        cs_interfaces = [
            # Header Functional Descriptor
            FD(app, phy, FD.Header, b'\x01\x01'),
            # Call Management Functional Descriptor
            FD(app, phy, FD.CM, struct.pack('BB', bmCapabilities, USBCDCDevice.bDataInterface)),
            FD(app, phy, FD.ACM, struct.pack('B', bmCapabilities)),
            FD(app, phy, FD.UN, struct.pack('BB', USBCDCDevice.bControlInterface, USBCDCDevice.bDataInterface)),
        ]
        interfaces = [
            USBInterface(
                app=app, phy=phy,
                interface_number=self.bDataInterface,
                interface_alternate=0,
                interface_class=USBClass.CDCData,
                interface_subclass=self.bDataSubclass,
                interface_protocol=self.bDataProtocol,
                interface_string_index=0,
                endpoints=[
                    USBEndpoint(
                        app=app,
                        phy=phy,
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
                        phy=phy,
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
                usb_class=cdc_cls
            )
        ]
        super(USBCdcAcmDevice, self).__init__(
            app, phy,
            vid=vid, pid=pid, rev=rev,
            interfaces=interfaces, cs_interfaces=cs_interfaces, cdc_cls=cdc_cls,
            bmCapabilities=0x03, **kwargs
        )
        self.receive_buffer = b''

    def handle_ep1_data_available(self, data):
        '''
        print the AT commands only upon new line
        '''
        self.receive_buffer += data
        if b'\r' in self.receive_buffer:
            lines = self.receive_buffer.split(b'\r')
            self.receive_buffer = lines[-1]
            for l in lines[:-1]:
                self.info('received line: %s' % l)

    def handle_ep2_buffer_available(self):
        # send ARP
        self.debug('in handle ep2 buffer available')
        self.send_on_endpoint(
            2,
            unhexlify('ffffffffffffaabbccddeeff08060001080006040001600308aaaaaac0a80065000000000000c0a80100')
        )


usb_device = USBCdcAcmDevice
